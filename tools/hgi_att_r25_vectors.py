#!/usr/bin/env python3
"""hgi-1010/att 2026-10-11: vectors for the R25 ATT controller bench (rtl/hbm_accel/generic/att/tb/tb_hgi_att_r25.sv).

Writes, for a list of ATT.QK / ATT.PV records (Qwen and DS shapes), the VM image (q / p rows), the HBM ATT regions
in the --attps tile-native block layout (ot_hgi_att_stager header), the record words and the golden O words from
hgi_sim's ATT arithmetic (tools/hgi_sim/lib.att_qk / att_pv == machine.u_att_qk / u_att_pv).

  python3 tools/hgi_att_r25_vectors.py --out DIR [--na 4] [--set smoke|full|tput] [--seed 1]

Layout (one stack; entry a = svc group 2a = PCs 8a .. 8a+3): NB = ceil(T/32) row blocks padded to NBp = 2^k,
RB = max(1, NBp / NA) blocks a run, entry a owns blocks [a RB, (a+1) RB); its local block lb = beta_l S + s holds rows
32 beta + r (r < 32) of slice s; row-word r -> PC 8a + r % 4, PS row rq = 8 lb + r // 4 = sectors j = 4 rq .. 4 rq + 3.
Row-word bits [575:0] = 32 x {pad, fmt, code8, scale8} (element e at 18 e).
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'hgi_sim'))
import lib as A  # noqa: E402
from hdc_golden_v41 import E4M3  # noqa: E402

F = np.float32
A_BASE, O_BASE = 0x01000, 0x20000


def p2(n):
    k = 1
    while k < n:
        k <<= 1
    return k


def bf16_rand(rng, shape, scale=1.0, pos=False):
    x = rng.standard_normal(shape).astype(F) * F(scale)
    if pos:
        x = np.abs(x)
    return A.to_bf16(x.astype(F))


def kv_rand(rng, T, hd, scaled):
    codes = rng.integers(0, 256, size=(T, hd))
    codes[(codes & 0x7F) == 0x7F] = 0x00          # no NaN codes
    sc = np.full((T, hd // 32), 127, dtype=np.int64)
    if scaled:
        sc = rng.integers(127 - 6, 127 + 4, size=(T, hd // 32))
    val = (E4M3[codes] * np.exp2(np.repeat(sc, 32, axis=1) - 127.0)).astype(F)
    return codes, sc, val


def desc(space, fmt, base, n, m, stride, ist=1):
    return (space | (fmt << 2) | (base << 8) | (n << 48) | (m << 68) | (stride << 88) | (ist << 120))


def build(rec, na, rng, region):
    kind, L, hd, T, scaled = rec
    S = hd // 32
    nb = -(-T // 32)
    nbp = p2(nb)
    rb = max(1, nbp // na)
    assert rb * S <= 127, "stream too long (nsec 12 b)"
    codes, sc, K = kv_rand(rng, T, hd, scaled)
    vm, exp = {}, {}
    if kind == 'QK':
        q = bf16_rand(rng, (L, hd))
        astr = hd + 8
        for h in range(L):
            for e in range(hd):
                vm[A_BASE + h * astr + e] = int(np.asarray(q[h, e], F).view(np.uint32))
        ostr = T + 3
        for h in range(L):
            o = A.att_qk(q[h], K)
            for t in range(T):
                exp[O_BASE + h * ostr + t] = int(np.asarray(o[t], F).view(np.uint32))
        a = desc(1, 0, A_BASE, hd, L, astr)
        o_ = desc(1, 0, O_BASE, T, L, ostr)
        op = 0
    else:
        p = bf16_rand(rng, (L, T), 0.3, pos=True)
        astr = T + 5
        for h in range(L):
            for t in range(T):
                vm[A_BASE + h * astr + t] = int(np.asarray(p[h, t], F).view(np.uint32))
        ostr = hd + 4
        for h in range(L):
            o = A.att_pv(p[h], K)
            for d in range(hd):
                exp[O_BASE + h * ostr + d] = int(np.asarray(o[d], F).view(np.uint32))
        a = desc(1, 0, A_BASE, T, L, astr)
        o_ = desc(1, 0, O_BASE, hd, L, ostr)
        op = 1
    b = desc(0, 0, region << 20, hd, T, 2048)
    hdr = (5 << 124) | (op << 118) | (0b0010011 << 93) | ((L & 0xF) << 64)
    # HBM region (row0 = region): (region, pc, j) -> 256-b sector
    hbm = {}
    for ent in range(na):
        for bl_ in range(rb):
            beta = ent * rb + bl_
            for s in range(S):
                lb = bl_ * S + s
                for r in range(32):
                    t = 32 * beta + r
                    word = 0
                    if t < T:
                        for e in range(32):
                            el = (int(codes[t, 32 * s + e]) << 8) | int(sc[t, s])   # pad 0, fmt 0
                            word |= el << (18 * e)
                    pc = 8 * ent + r % 4
                    rq = 8 * lb + r // 4
                    for k in range(4):
                        sec = (word >> (256 * k)) & ((1 << 256) - 1)
                        if sec:
                            hbm[(region * 32 + pc) * 4096 + 4 * rq + k] = sec
    return dict(hdr=hdr, a=a, b=b, c=0, o=o_, nb=T, nc=0, vm=vm, exp=exp, hbm=hbm, T=T, L=L, hd=hd, kind=kind,
                rb=rb, S=S)


SETS = {
    # (kind, lanes, hd, T, block-scaled KV)
    'smoke': [('QK', 4, 128, 40, False), ('PV', 4, 128, 40, False)],
    'full': [('QK', 4, 128, 37, False), ('PV', 4, 128, 37, False),        # Qwen GQA-4, hd 128
             ('QK', 4, 128, 300, False), ('PV', 4, 128, 300, False),
             ('QK', 1, 512, 168, True), ('PV', 1, 512, 168, True),        # DS head die: 1 lane, hd 512, FP8 x UE8M0
             ('QK', 1, 512, 5, True), ('PV', 1, 512, 5, True),
             ('QK', 2, 64, 97, False), ('PV', 3, 96, 97, False)],
    'tput': [('QK', 1, 512, 640, True), ('PV', 1, 512, 640, True),        # DS production: window 128 + top-512
             ('QK', 4, 128, 1024, False), ('PV', 4, 128, 1024, False)],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--na', type=int, default=4)
    ap.add_argument('--set', default='smoke')
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    recs = [build(r, a.na, rng, 1 + i) for i, r in enumerate(SETS[a.set])]
    with open(out / 'recs.txt', 'w') as f:
        f.write(f'{len(recs)}\n')
        for r in recs:
            f.write(f"{r['hdr']:032x} {r['a']:064x} {r['b']:064x} {r['c']:064x} {r['o']:064x} {r['nb']:x} {r['nc']:x} "
                    f"{len(r['vm']):x} {len(r['exp']):x}\n")
            for k, v in sorted(r['vm'].items()):
                f.write(f'{k:x} {v:08x}\n')
            for k, v in sorted(r['exp'].items()):
                f.write(f'{k:x} {v:08x}\n')
    with open(out / 'hbm.txt', 'w') as f:
        allh = {}
        for r in recs:
            allh.update(r['hbm'])
        f.write(f'{len(allh)}\n')
        for k, v in sorted(allh.items()):
            f.write(f'{k:x} {v:064x}\n')
    with open(out / 'manifest.txt', 'w') as f:
        for i, r in enumerate(recs):
            f.write(f"rec {i} {r['kind']} L={r['L']} hd={r['hd']} T={r['T']} RB={r['rb']} S={r['S']}\n")
    print(open(out / 'manifest.txt').read(), end='')


if __name__ == '__main__':
    main()
