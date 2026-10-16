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
    if op in (0, 2) and False:
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
    import os
    hc_only = os.environ.get('FUSED_HC_ONLY', '0') == '1'       # debug / unit-rate: only the DS HC cases
    for v, tr, cpl, vm in ([] if hc_only else C.conformance(lambda v: v['row'] == 'CF-NORM')):
        hb = {}
        for base, hexs in v['dies'][0].get('hbm_in', []):
            b = bytes.fromhex(hexs)
            b += b'\0' * (-len(b) % 4)
            for q in range(0, len(b), 4):
                hb[(base + q) >> 2] = int.from_bytes(b[q:q + 4], 'little')
        add([d for d in tr if C.unit_of(d) == 4], vm, C.vm_out_of(v['expect']['dies'][0]), hb)
    # Qwen token ROW_NORM records with random data (hgi_sim lib.row_norm = the expected VM)
    rng = np.random.default_rng(5)
    tr, _ = C.qwen_dispatch() if not hc_only else ([], None)
    seen = set()
    for d in ([] if hc_only else tr):
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
    # DATA: DS HC_PRE_NORM / HC_POST on the stream unit vs hdc_golden_v41 (chunk8): Model.hc_pre + rmsnorm_bf16,
    # Model.hc_post (seqsum over the 4 copies, BF16 out)
    import hdc_golden_v41 as GV
    GV.set_arith("chunk8")
    def md(**kw):
        return C.SV.mdesc(**kw)

    def rec(op, eff, n, imm=0, unit=4, param=0):
        opnd = sum(1 << j for j, e in enumerate(eff) if e)
        return dict(hdr=C.SV.header(unit, op, opnd=opnd, imm_a=imm, param=param), eff=eff, n=n)
    import os
    only = int(os.environ.get('FUSED_ONLY_D', '0'))     # debug: only the HC cases of this d (-1: none)
    for D in (() if only < 0 else (only,) if only else (64, 512, 4096, 5120)):        # 5120: the DS-V4.1 HC_PRE_NORM / HC_POST d (F10)
        h = (rng.standard_normal((4, D)) * 2).astype(np.float32)
        pre = (rng.random(4) * 1.5).astype(np.float32)
        w = LB.to_bf16((1 + 0.1 * rng.standard_normal(D)).astype(np.float32))
        eps = np.float32(1e-6)
        x = GV.to_bf16(GV.seqsum([GV.mul(pre[j], h[j]) for j in range(4)]))
        y = GV.rmsnorm_bf16(x, w, eps)
        # pre must not overlap h (4 D words at 0): at D 5120 the old cb 20000 overwrote h[3][4640..4643] (bench bug)
        ab, cb, ob, bb = 0, (20000 if 4 * D <= 20000 else 4 * D + 64), 30720, 0x4_0000_0000   # ob bank phase 0 (= ab's): lane-local rule
        vin = {ab + i: int(v) for i, v in enumerate(f32w(h.reshape(-1)))}
        vin.update({cb + j: int(f32w(pre)[j]) for j in range(4)})
        gb = (f32w(w) >> 16).astype(np.uint32)
        hb = {(bb >> 2) + i // 2: int(gb[i]) | (int(gb[i + 1]) << 16 if i + 1 < D else 0) for i in range(0, D, 2)}
        if os.environ.get('FUSED_HLL', '0') == '1' and D == 5120:
            # el1011-hbm-fused GPK (compiler layout rule for the lane-local engine, d = HCD): the gain image is BF16
            # packed LANE-LOCAL: data sector s (8 elements) -> packed sector (s mod 32) + 32 floor(s / 64), half
            # (s / 32) mod 2 (words 0..3 | 4..7), element pair i // 2 in the word, low half = even element
            hb = {}
            for e in range(D):
                s_, i_ = divmod(e, 8)
                wd = (bb >> 2) + 8 * ((s_ % 32) + 32 * (s_ // 64)) + 4 * ((s_ // 32) % 2) + i_ // 2
                hb[wd] = hb.get(wd, 0) | (int(gb[e]) << (16 * (i_ % 2)))
        dd = rec(0, [md(space=1, base=ab, n=4 * D), md(space=0, fmt=1, base=bb, n=D), md(space=1, base=cb, n=4), 0,
                     md(space=1, fmt=1, base=ob, n=D), 0, 0], [4 * D, D, 4, 0, D, 0, 0], imm=int(np.float32(eps).view(np.uint32)))
        add([dd], vin, {ob + i: int(v) for i, v in enumerate(f32w(y))}, hb)
        yv = (rng.standard_normal(D) * 2).astype(np.float32)
        res = (rng.standard_normal((4, D)) * 2).astype(np.float32)
        post = (rng.random(4) * 2).astype(np.float32)
        comb = (rng.random((4, 4)) * 0.5).astype(np.float32)
        mix = [GV.seqsum([GV.mul(comb[j, k], res[j]) for j in range(4)]) for k in range(4)]
        hout = GV.to_bf16(np.stack([GV.add(GV.mul(post[k], yv), mix[k]) for k in range(4)]))
        yb, rb, mb, ob2 = 0, 8192, 40000, 51200   # y / res / out at bank phase 0 (lane-local rule)
        vin = {yb + i: int(v) for i, v in enumerate(f32w(yv))}
        vin.update({rb + i: int(v) for i, v in enumerate(f32w(res.reshape(-1)))})
        mixv = np.concatenate([post, comb.reshape(-1)])
        vin.update({mb + i: int(v) for i, v in enumerate(f32w(mixv))})
        dd = rec(2, [md(space=1, base=yb, n=D), md(space=1, base=rb, n=4 * D), md(space=1, base=mb, n=20), 0,
                     md(space=1, fmt=1, base=ob2, n=4 * D), 0, 0], [D, 4 * D, 20, 0, 4 * D, 0, 0])
        add([dd], vin, {ob2 + i: int(v) for i, v in enumerate(f32w(hout.reshape(-1)))})
    # H-MTP2 (2026-10-15): FUSED_ROWS = P -> one more DS HC_PRE_NORM case at d 5,120: the MTP verify's P positions as
    # P back-to-back per-position records (FUSED_ROWS_FORM=recs, the as-built ISA: P records, one gain, P h / pre / y)
    # or as ONE P-row record (FUSED_ROWS_FORM=rows: A.m = C.m = O.m = P with row strides, B.m = 1 broadcast gain).
    # Row p: h at p 20,480, pre at 160,000 + 8 p, y at 122,880 + 5,120 p (all bank phase 0); one GPK gain image.
    nrow = int(os.environ.get('FUSED_ROWS', '0'))
    if nrow:
        assert 1 <= nrow <= 8, 'LL P-row job supports one through eight rows'
        D = 5120
        hl = (rng.standard_normal((nrow, 4, D)) * 2).astype(np.float32)
        prel = (rng.random((nrow, 4)) * 1.5).astype(np.float32)
        w = LB.to_bf16((1 + 0.1 * rng.standard_normal(D)).astype(np.float32))
        eps = np.float32(1e-6)
        # Keep all H rows, output rows and per-row scalars disjoint for P7/P8
        # too. P6 retains the existing exact addresses and image hashes.
        HS, CS, OS = 4 * D, 8, D
        OB = nrow * HS
        CB = max(160000, OB + nrow * D + 64)
        bb = 0x4_0000_0000
        gb = (f32w(w) >> 16).astype(np.uint32)
        hb = {}
        for e in range(D):
            s_, i_ = divmod(e, 8)
            wd = (bb >> 2) + 8 * ((s_ % 32) + 32 * (s_ // 64)) + 4 * ((s_ // 32) % 2) + i_ // 2
            hb[wd] = hb.get(wd, 0) | (int(gb[e]) << (16 * (i_ % 2)))
        vin, vout, ds = {}, {}, []
        for r_ in range(nrow):
            x = GV.to_bf16(GV.seqsum([GV.mul(prel[r_, j], hl[r_, j]) for j in range(4)]))
            y = GV.rmsnorm_bf16(x, w, eps)
            vin.update({r_ * HS + i: int(v) for i, v in enumerate(f32w(hl[r_].reshape(-1)))})
            vin.update({CB + CS * r_ + j: int(f32w(prel[r_])[j]) for j in range(4)})
            vout.update({OB + OS * r_ + i: int(v) for i, v in enumerate(f32w(y))})
        if os.environ.get('FUSED_ROWS_FORM', 'recs') == 'rows':
            ds.append(rec(0, [md(space=1, base=0, n=4 * D, m=nrow, stride=HS), md(space=0, fmt=1, base=bb, n=D),
                              md(space=1, base=CB, n=4, m=nrow, stride=CS), 0,
                              md(space=1, fmt=1, base=OB, n=D, m=nrow, stride=OS), 0, 0],
                          [4 * D, D, 4, 0, D, 0, 0], imm=int(np.float32(eps).view(np.uint32))))
        else:
            for r_ in range(nrow):
                ds.append(rec(0, [md(space=1, base=r_ * HS, n=4 * D), md(space=0, fmt=1, base=bb, n=D),
                                  md(space=1, base=CB + CS * r_, n=4), 0, md(space=1, fmt=1, base=OB + OS * r_, n=D), 0, 0],
                              [4 * D, D, 4, 0, D, 0, 0], imm=int(np.float32(eps).view(np.uint32))))
        add(ds, vin, vout, hb)
    qd = [d for v, tr2, c2, vm2 in C.conformance(lambda v: v['row'] == 'CF-QDQ') for d in tr2 if C.unit_of(d) == 4]
    for d in qd:
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
