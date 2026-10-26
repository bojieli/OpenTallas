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


def kv8_rows(rng, n, hd):
    """n DS window / compressed rows through the golden's act_quant (hdc_golden_v41.quant_fp8, block 32): per-block
    magnitudes 2^-24 .. 2^14, all-zero blocks, sub-floor blocks (amax < 1e-4) -> (packed fmt 7 rows [n, 544-pitch
    bytes], the golden's qdq_fp8 values [n, hd] FP32 (BF16-valued))."""
    import hdc_golden_v41 as GV
    x = rng.standard_normal((n, hd)).astype(F)
    mag = np.exp2(rng.integers(-24, 15, (n, hd // 32))).astype(F)
    mag[rng.random((n, hd // 32)) < 0.05] = 0                          # all-zero blocks
    mag[rng.random((n, hd // 32)) < 0.05] = F(2.0 ** -40)              # below the 1e-4 amax floor
    x = (x.reshape(n, hd // 32, 32) * mag[:, :, None]).reshape(n, hd).astype(F)
    t = GV.E4M3
    pos = {float(v): i for i, v in enumerate(t[:127])}
    pitch = hd + 32
    rows, vals = [], np.zeros((n, hd), dtype=F)
    for r in range(n):
        q, e = GV.quant_fp8(x[r])
        vals[r] = GV.qdq_fp8(x[r])
        codes = bytes((pos[abs(float(v))] | (0x80 if np.signbit(v) else 0)) for v in q)
        scales = bytes(int(k) + 127 for k in e)
        assert all(0 < b < 255 for b in scales)
        rows.append(codes + scales + bytes(pitch - hd - len(scales)))
    return rows, vals


def add_kv8(add):
    """fmt 7 cases (fe-push-hgi-1010/kv8): the DS attend shape -- ring B (the 128-slot window) + C (selected compressed
    rows), hd 512, 4 lanes; QK (T 828 = 2 engine jobs) and PV over the same rows, plus a B-only partial ring.  The
    golden is hgi_sim.lib att_qk / att_pv on the golden's qdq_fp8 values of the stored rows."""
    from hgi_sim import machine as MC  # noqa: F401
    rng = np.random.default_rng(77)
    hd, lanes, M, nb, nc, pos1 = 512, 4, 128, 128, 700, 1000
    pitch = hd + 32
    ring_rows, ring_vals = kv8_rows(rng, M, hd)
    c_rows, c_vals = kv8_rows(rng, nc, hd)
    bb, cb = 1 << 34, (1 << 34) + (1 << 24)
    hb = sectors([(bb + i * pitch, r) for i, r in enumerate(ring_rows)] + [(cb + i * pitch, r) for i, r in enumerate(c_rows)])

    def rowlist(n_b, with_c):
        k = [ring_vals[(pos1 - n_b + i) & (M - 1)] for i in range(n_b)]
        return np.stack(k + (list(c_vals) if with_c else []))
    T = nb + nc
    K = rowlist(nb, True)
    q = A.to_bf16(rng.standard_normal((lanes, hd)).astype(F))
    p = A.to_bf16(rng.uniform(0, 1, (lanes, T)).astype(F))
    vm, ex = {}, {}
    for h in range(lanes):
        for i in range(hd):
            vm[h * hd + i] = int(q[h, i].view(np.uint32))
        for t in range(T):
            vm[20000 + h * 1000 + t] = int(p[h, t].view(np.uint32))
    K2 = rowlist(100, False)
    for h in range(lanes):
        s = A.att_qk(q[h], K)
        for t in range(T):
            ex[40000 + h * 1000 + t] = int(F(s[t]).view(np.uint32))
        o = A.att_pv(p[h], K)
        for i in range(hd):
            ex[60000 + h * hd + i] = int(F(o[i]).view(np.uint32))
        s2 = A.att_qk(q[h], K2)
        for t in range(100):
            ex[70000 + h * 1000 + t] = int(F(s2[t]).view(np.uint32))
    prm = lanes | ((hd // 64 - 1) << 4) | (1 << 8)                     # ring
    Bd = C.SV.mdesc(space=0, fmt=7, base=bb, n=nb, m=M, stride=pitch)
    Cd = C.SV.mdesc(space=0, fmt=7, base=cb, n=nc, m=1, stride=pitch)
    B2 = C.SV.mdesc(space=0, fmt=7, base=bb, n=100, m=M, stride=pitch)
    qk = dict(hdr=C.SV.header(5, 0, opnd=0b10111, param=prm), eff=[C.SV.mdesc(space=1, base=0, n=hd, m=lanes,
              stride=hd), Bd, Cd, 0, C.SV.mdesc(space=1, base=40000, n=T, m=lanes, stride=1000), 0, 0],
              n=[hd, nb, nc, 0, T, 0, 0], pos1=pos1)
    pv = dict(hdr=C.SV.header(5, 1, opnd=0b10111, param=prm), eff=[C.SV.mdesc(space=1, base=20000, n=T, m=lanes,
              stride=1000), Bd, Cd, 0, C.SV.mdesc(space=1, base=60000, n=hd, m=lanes, stride=hd), 0, 0],
              n=[T, nb, nc, 0, hd, 0, 0], pos1=pos1)
    qk2 = dict(hdr=C.SV.header(5, 0, opnd=0b10011, param=prm), eff=[C.SV.mdesc(space=1, base=0, n=hd, m=lanes,
               stride=hd), B2, 0, 0, C.SV.mdesc(space=1, base=70000, n=100, m=lanes, stride=1000), 0, 0],
               n=[hd, 100, 0, 0, 100, 0, 0], pos1=pos1)
    add([qk, pv, qk2], vm, hb, ex)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_au_tb')
    ap.add_argument('--big', type=int, default=1)
    ap.add_argument('--kv8', type=int, default=0, help='fe-push kv8: only the fmt 7 FP8 KV-row cases (unit KV8 = 1)')
    out = Path(ap.parse_args().out)
    big = ap.parse_args().big
    kv8 = ap.parse_args().kv8
    out.mkdir(parents=True, exist_ok=True)
    cases, recs, vmi, hbm, exp = [], [], [], [], []

    def add(rs, vm, hb, ex):
        cases.append((len(recs), len(rs), len(vmi), len(vm), len(hbm), len(hb), len(exp), len(ex)))
        recs.extend(pack(d) for d in rs)
        vmi.extend(sorted(vm.items()))
        hbm.extend(sorted(hb.items()))
        exp.extend(sorted(ex.items()))
    if kv8:
        add_kv8(add)
    for v, tr, cpl, vm in ([] if kv8 else C.conformance(lambda v: v.get('row') == 'CF-ATT')):
        rs = [d for d in tr if C.unit_of(d) == 5]
        if not rs:
            continue
        die = v['dies'][0]
        hb = sectors([(a, bytes.fromhex(h)) for a, h in die['hbm_in']])
        ex = C.vm_out_of(v['expect']['dies'][0])
        add(rs, vm, hb, ex)
    if big and not kv8:
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
