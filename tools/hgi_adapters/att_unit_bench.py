#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): data vectors for the D4 ATT unit ot_hgi_att_unit.
Every hbm-sim CF-ATT conformance vector (Ref's dispatch: header, effective A B C O, n_B, n_C, POS1; die 0's VM / HBM
images; expected VM out), plus synthetic Qwen-shape records past one engine job (T 1,300 rows: 3 jobs, so the PV
cross-job merge runs) with the golden = hgi_sim.lib att_qk / att_pv.
--out DIR: au_case.mem {first rec, n rec, first vmi, n vmi, first hbm, n hbm, first exp, n exp} x 32;
au_rec.mem {pos1 21, n_C 21, n_B 21, O, C, B, A 256 each, header 128} (1,215 b, padded to 1,216);
au_vmi.mem / au_exp.mem {addr 32, word 32}; au_hbm.mem {sector 40, data 256}.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from hgi_sim import lib as A  # noqa: E402

F = np.float32


def pack(d):
    return (d['hdr'] | d['eff'][0] << 128 | d['eff'][1] << 384 | d['eff'][2] << 640 | d['eff'][4] << 896
            | (d['n'][1] & 0x1FFFFF) << 1152 | (d['n'][2] & 0x1FFFFF) << 1173 | (d['pos1'] & 0x1FFFFF) << 1194)


def sectors(hbm):
    """{byte addr: bytes} -> {sector: int}"""
    out = {}
    for base, b in hbm:
        assert base % 32 == 0
        b = b + bytes(-len(b) % 32)
        for q in range(0, len(b), 32):
            out[(base + q) // 32] = int.from_bytes(b[q:q + 32], 'little')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_au_tb')
    ap.add_argument('--big', type=int, default=1)
    out = Path(ap.parse_args().out)
    big = ap.parse_args().big
    out.mkdir(parents=True, exist_ok=True)
    cases, recs, vmi, hbm, exp = [], [], [], [], []

    def add(rs, vm, hb, ex):
        cases.append((len(recs), len(rs), len(vmi), len(vm), len(hbm), len(hb), len(exp), len(ex)))
        recs.extend(pack(d) for d in rs)
        vmi.extend(sorted(vm.items()))
        hbm.extend(sorted(hb.items()))
        exp.extend(sorted(ex.items()))
    for v, tr, cpl, vm in C.conformance(lambda v: v.get('row') == 'CF-ATT'):
        rs = [d for d in tr if C.unit_of(d) == 5]
        if not rs:
            continue
        die = v['dies'][0]
        hb = sectors([(a, bytes.fromhex(h)) for a, h in die['hbm_in']])
        ex = C.vm_out_of(v['expect']['dies'][0])
        add(rs, vm, hb, ex)
    if big:
        # Qwen shape: 4 lanes, hd 128, FP8 E4M3 rows, T = 1,300 (3 engine jobs), no ring, no C
        rng = np.random.default_rng(5)
        T, hd, lanes = 1300, 128, 4
        K = A.to_fp8(rng.standard_normal((T, hd)).astype(F))
        Vv = A.to_fp8(rng.standard_normal((T, hd)).astype(F))
        q = A.to_bf16(rng.standard_normal((lanes, hd)).astype(F))
        p = A.to_bf16(rng.uniform(0, 1, (lanes, T)).astype(F))
        from hgi_sim import machine as MC
        kb, vb = 1 << 34, (1 << 34) + (1 << 24)
        hb = sectors([(kb, bytes(MC.fp8_encode(K.reshape(-1)))), (vb, bytes(MC.fp8_encode(Vv.reshape(-1))))])
        vm = {}
        for h in range(lanes):
            for i in range(hd):
                vm[h * hd + i] = int(q[h, i].view(np.uint32))
            for t in range(T):
                vm[20000 + h * 1400 + t] = int(p[h, t].view(np.uint32))
        ex = {}
        for h in range(lanes):
            s = A.att_qk(q[h], K)
            for t in range(T):
                ex[40000 + h * 1400 + t] = int(F(s[t]).view(np.uint32))
            o = A.att_pv(p[h], Vv)
            for i in range(hd):
                ex[60000 + h * hd + i] = int(F(o[i]).view(np.uint32))
        prm = lanes | ((hd // 64 - 1) << 4)
        Bk = C.SV.mdesc(space=0, fmt=2, base=kb, n=T, m=1, stride=hd)
        Bv = C.SV.mdesc(space=0, fmt=2, base=vb, n=T, m=1, stride=hd)
        qk = dict(hdr=C.SV.header(5, 0, opnd=0b10011, param=prm), eff=[C.SV.mdesc(space=1, base=0, n=hd, m=lanes,
                  stride=hd), Bk, 0, 0, C.SV.mdesc(space=1, base=40000, n=T, m=lanes, stride=1400), 0, 0],
                  n=[hd, T, 0, 0, T, 0, 0], pos1=T)
        pv = dict(hdr=C.SV.header(5, 1, opnd=0b10011, param=prm), eff=[C.SV.mdesc(space=1, base=20000, n=T, m=lanes,
                  stride=1400), Bv, 0, 0, C.SV.mdesc(space=1, base=60000, n=hd, m=lanes, stride=hd), 0, 0],
                  n=[T, T, 0, 0, hd, 0, 0], pos1=T)
        add([qk, pv], vm, hb, ex)
    (out / 'au_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    (out / 'au_rec.mem').write_text(''.join(C.hexw(r, 1216) + '\n' for r in recs))
    (out / 'au_vmi.mem').write_text(''.join(f'{a:08X}{w:08X}\n' for a, w in vmi))
    (out / 'au_exp.mem').write_text(''.join(f'{a:08X}{w:08X}\n' for a, w in exp))
    (out / 'au_hbm.mem').write_text(''.join(f'{a:010X}{d:064X}\n' for a, d in hbm))
    (out / 'au_sizes.svh').write_text(f'localparam integer NCASE = {len(cases)};\nlocalparam integer NREC = {len(recs)};\n'
                                      f'localparam integer NVMI = {max(1, len(vmi))};\nlocalparam integer NHBM = {len(hbm)};\n'
                                      f'localparam integer NEXP = {len(exp)};\n')
    print(f'{len(cases)} cases, {len(recs)} records, {len(hbm)} HBM sectors, {len(exp)} expected words')


if __name__ == '__main__':
    main()
