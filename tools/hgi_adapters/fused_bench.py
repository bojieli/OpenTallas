#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): bench vectors for ot_hgi_fused_record.
--out DIR: fu_rec.mem {n_O, n_B, n_A (3 x 21), O, C, B, A (4 x 256), header 128} (1,215 b); fu_case.mem
{kind, first rec, recs, first vmi, vmi, first vme, vme, first hbm, hbm} (9 x 32 b); fu_exp.mem a line per record
{kind 4, expected word 683} (kind 0 run on the vec, 1 norm-engine job (low 149 b), 2 quant forward (683 b), 3 refuse);
fu_vmi / fu_vme {addr, value}; fu_hbm {word address (byte / 4) 40, value 32}.
DATA: hbm-sim CF-NORM (d 4,096 BF16 out + QK-norm seg 128 FP32 out, the 3 ROW_NORM records) on the REAL vec through the
adapter + a behavioural DMA mover (HBM BF16 -> VM FP32 LOAD), VM out == the vector's expect.  Plus the Qwen token's
ROW_NORM records with random data checked against hgi_sim lib.row_norm.  FIELDS: HC_PRE_NORM / HC_POST job words, QDQ
forwarding (the CF-QDQ records).  NEGATIVE: SOFTMAX, op 7, non-contiguous A, B not BF16, seg not dividing, B.n != d.
"""
import argparse
import random
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
sys.path.insert(0, str(C.ROOT / 'tools'))
from hgi_sim import lib as LB  # noqa: E402


def f32w(x):
    return np.asarray(x, dtype=np.float32).view(np.uint32)


def rn_ref(x, g, eps, seg, obf16):
    y = LB.row_norm(x, g, eps, seg)
    if obf16:
        y = LB.to_bf16(y)
    return f32w(y)


def pack(d):
    w = d['hdr']
    for j, k in enumerate((0, 1, 2, 4)):
        w |= (d['eff'][k] & ((1 << 256) - 1)) << (128 + 256 * j)
    for j, k in enumerate((0, 1, 4)):
        w |= (d['n'][k] & 0x1FFFFF) << (1152 + 21 * j)
    return w


def kind_of(d):
    h = d['hdr']
    op = C.fld(h, 'op', C.UOP)
    if C.fld(h, 'unit', C.UOP) != 4 or op > 6 or op == 3:
        return 3, 0
    if op >= 4:
        A, O = d['eff'][0], d['eff'][4]
        return 2, 1 | h << 1 | A << 129 | O << 385 | (d['n'][0] & 0x1FFFFF) << 641 | (d['n'][4] & 0x1FFFFF) << 662
    if op in (0, 2):
        A, B, Cd, O = d['eff'][0], d['eff'][1], d['eff'][2], d['eff'][4]
        w = (C.fld(A, 'base') & 0x3FFFF) | C.fld(B, 'base') << 18 | (C.fld(Cd, 'base') & 0x3FFFF) << 58 \
            | (C.fld(O, 'base') & 0x3FFFF) << 76 | (d['n'][0] & 0x1FFFFF) << 94 | C.fld(h, 'imm_a', C.UOP) << 115 \
            | (1 if op == 2 else 0) << 147
        return 1, w
    return 0, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_fused_tb')
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    recs, exps, cases, vmi, vme, hbm = [], [], [], [], [], []

    def add(ds, vm_in=None, vm_out=None, hb=None, refuse=False):
        k0 = kind_of(ds[0])[0] if ds else 0
        kind = 3 if refuse else (0 if k0 == 0 else 1)
        cases.append((kind, len(recs), len(ds), len(vmi), len(vm_in or {}), len(vme), len(vm_out or {}), len(hbm), len(hb or {})))
        for d in ds:
            recs.append(pack(d))
            k, w = kind_of(d)
            exps.append(k << 683 | w)
        vmi.extend(sorted((vm_in or {}).items()))
        vme.extend(sorted((vm_out or {}).items()))
        hbm.extend(sorted((hb or {}).items()))
    for v, tr, cpl, vm in C.conformance(lambda v: v['row'] == 'CF-NORM'):
        hb = {}
        for base, hexs in v['dies'][0].get('hbm_in', []):
            b = bytes.fromhex(hexs)
            b += b'\0' * (-len(b) % 4)
            for q in range(0, len(b), 4):
                hb[(base + q) >> 2] = int.from_bytes(b[q:q + 4], 'little')
        add([d for d in tr if C.unit_of(d) == 4], vm, C.vm_out_of(v['expect']['dies'][0]), hb)
    # Qwen token ROW_NORM records with random data (hgi_sim lib.row_norm = the expected VM)
    rng = np.random.default_rng(5)
    tr, _ = C.qwen_dispatch()
    seen = set()
    for d in tr:
        if C.unit_of(d) != 4 or C.fld(d['hdr'], 'op', C.UOP) != 1:
            continue
        A, B, O = d['eff'][0], d['eff'][1], d['eff'][4]
        key = (C.fld(d['hdr'], 'param', C.UOP), C.fld(A, 'n'), C.fld(A, 'm'), C.fld(O, 'fmt'))
        if key in seen:
            continue
        seen.add(key)
        n, m = d['n'][0], C.fld(A, 'm')
        seg = (C.fld(d['hdr'], 'param', C.UOP) >> 6) & 0xFF
        dd = seg or n * m
        x = (rng.standard_normal(n * m) * 3).astype(np.float32)
        g = LB.to_bf16((1 + 0.2 * rng.standard_normal(dd)).astype(np.float32))
        eps = np.uint32(C.fld(d['hdr'], 'imm_a', C.UOP)).view(np.float32)
        y = rn_ref(x, g, eps, seg, C.fld(O, 'fmt') == 1)
        ab, ob, bb = C.fld(A, 'base'), C.fld(O, 'base'), C.fld(B, 'base')
        gb = (f32w(g) >> 16).astype(np.uint32)
        hb = {}
        for i in range(0, dd, 2):
            hb[(bb >> 2) + i // 2] = int(gb[i]) | (int(gb[i + 1]) << 16 if i + 1 < dd else 0)
        add([d], {ab + i: int(w) for i, w in enumerate(f32w(x))}, {ob + i: int(w) for i, w in enumerate(y)}, hb)
    # FIELDS: HC_PRE_NORM / HC_POST jobs, QDQ forwarding
    def md(**kw):
        return C.SV.mdesc(**kw)

    def rec(op, eff, n, imm=0, unit=4, param=0):
        opnd = sum(1 << j for j, e in enumerate(eff) if e)
        return dict(hdr=C.SV.header(unit, op, opnd=opnd, imm_a=imm, param=param), eff=eff, n=n)
    hcp = rec(0, [md(space=1, base=0, n=16384), md(space=0, fmt=1, base=0x4000, n=4096), md(space=1, base=20000, n=4),
                  0, md(space=1, base=30000, fmt=1, n=4096), 0, 0], [16384, 4096, 4, 0, 4096, 0, 0], imm=0x3727C5AC)
    hpo = rec(2, [md(space=1, base=100, n=4096), md(space=1, base=4196, n=16384), md(space=1, base=20004, n=20),
                  0, md(space=1, base=40000, n=16384), 0, 0], [4096, 16384, 20, 0, 16384, 0, 0])
    qd = [d for v, tr2, c2, vm2 in C.conformance(lambda v: v['row'] == 'CF-QDQ') for d in tr2 if C.unit_of(d) == 4]
    for d in [hcp, hpo] + qd:
        add([d])
    A = md(space=1, base=0, n=128, m=1)
    Bg = md(space=0, fmt=1, base=0x1000, n=128)
    O = md(space=1, base=512, n=128, m=1)
    for d in [rec(3, [A, Bg, 0, 0, O, 0, 0], [128, 128, 0, 0, 128, 0, 0]),
              rec(7, [A, Bg, 0, 0, O, 0, 0], [128, 128, 0, 0, 128, 0, 0]),
              rec(1, [md(space=1, base=0, n=128, m=2, stride=200), Bg, 0, 0, md(space=1, base=512, n=128, m=2, stride=128), 0, 0], [128, 128, 0, 0, 128, 0, 0]),
              rec(1, [A, md(space=0, fmt=0, base=0x1000, n=128), 0, 0, O, 0, 0], [128, 128, 0, 0, 128, 0, 0]),
              rec(1, [md(space=1, base=0, n=100, m=1), md(space=0, fmt=1, base=0x1000, n=64), 0, 0, md(space=1, base=512, n=100), 0, 0], [100, 64, 0, 0, 100, 0, 0], param=64 << 6),
              rec(1, [A, md(space=0, fmt=1, base=0x1000, n=64), 0, 0, O, 0, 0], [128, 64, 0, 0, 128, 0, 0]),
              rec(1, [A, Bg, 0, 0, O, 0, 0], [128, 128, 0, 0, 128, 0, 0], unit=5)]:
        add([d], refuse=True)
    (out / 'fu_rec.mem').write_text(''.join(C.hexw(r, 1215) + '\n' for r in recs))
    (out / 'fu_exp.mem').write_text(''.join(C.hexw(r, 687) + '\n' for r in exps))
    (out / 'fu_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    for nm, lst, w in (('fu_vmi', vmi, 8), ('fu_vme', vme, 8), ('fu_hbm', hbm, 10)):
        (out / f'{nm}.mem').write_text(''.join(f'{a:0{w}X}{x:08X}\n' for a, x in lst) or '0' * (w + 8) + '\n')
    (out / 'fu_sizes.svh').write_text(''.join(f'localparam integer {k} = {max(1, v)};\n' for k, v in dict(
        NREC=len(recs), NCASE=len(cases), NVMI=len(vmi), NVME=len(vme), NHBM=len(hbm)).items()))
    print(f"{len(cases)} cases, {len(recs)} records, kinds {[c[0] for c in cases]}")


if __name__ == '__main__':
    main()
