#!/usr/bin/env python3
"""Directed-random IDX.TOPK records for ot_hgi_idx_tk2 (el1013 redesign-idx), in the tb_hgi_idx_unit vector format
(tools/hgi_idx_unit_vectors.py): what CF-TOPK and the production records do not exercise -- unaligned A / O / R bases,
rows that share a sector (stride not a multiple of 8), outputs that span two sectors, n < 8, heavy ties, -0 / +0,
+-inf, denormals, R present / absent, both orders, and NaN (must fault).  Golden: hgi_sim.machine.topk_ids.
  idx_tk2_vectors.py OUTDIR [count]  -> OUTDIR/vec_<i>.{rec,vmin,vmout}.mem, OUTDIR/list.txt"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hgi_sim.machine import topk_ids  # noqa: E402

SPECIAL = np.array([0x00000000, 0x80000000, 0x7f800000, 0xff800000, 0x00000001, 0x80000001, 0x3f800000, 0xbf800000,
                    0x7f7fffff, 0xff7fffff], np.uint32)


def desc(fmt, base, n, m, stride):
    return 1 | fmt << 2 | base << 8 | n << 48 | m << 68 | stride << 88


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 96
    rng = np.random.default_rng(20261013)
    lines = []
    for i in range(cnt):
        n = int(rng.choice([1, 2, 3, 5, 7, 8, 9, 15, 16, 17, 33, 64, 100, 257, 384]))
        k = int(rng.integers(1, min(8, n) + 1)); m = int(rng.integers(1, 4))
        order = int(rng.integers(0, 2)); has_r = int(rng.integers(0, 2)); nan = i % 16 == 15
        a = 1024 + int(rng.integers(0, 16)); a_str = n + int(rng.integers(0, 10))
        o = 100000 + int(rng.integers(0, 16)); o_str = k + int(rng.integers(0, 10))
        r = 150000 + int(rng.integers(0, 16)); r_str = k + int(rng.integers(0, 10))
        mode = int(rng.integers(0, 3))
        if mode == 0:                                   # heavy ties among a few values incl. -0 / +0 / inf
            v = rng.choice(SPECIAL, size=(m, n))
        elif mode == 1:                                 # small integer grid: ties across lanes
            v = rng.integers(-3, 4, size=(m, n)).astype(np.float32).view(np.uint32)
        else:
            v = rng.standard_normal((m, n)).astype(np.float32).view(np.uint32)
        v = np.ascontiguousarray(v, np.uint32)
        if nan:
            v[m - 1, int(rng.integers(0, n))] = 0x7fc00001 if i % 32 == 15 else 0xff800001
        hdr = 9 << 124 | 2 << 118 | (0b0010001 | has_r << 5) << 93 | order << 76 | k << 64
        d = {'A': desc(0, a, n, m, a_str), 'O': desc(5, o, k, m, o_str)}
        nn = {'A': n, 'O': k}
        if has_r:
            d['R'] = desc(0, r, k, m, r_str); nn['R'] = k
        bus = 1 | hdr << 1
        pos = 129
        for name in 'ABOR':
            bus |= d.get(name, 0) << pos; pos += 256
        for name in 'ABOR':
            bus |= nn.get(name, 0) << pos; pos += 21
        (out / f'vec_{i}.rec.mem').write_text(f'{bus:0310x}\n')
        vmin = [(a + row * a_str + j, int(v[row, j])) for row in range(m) for j in range(n)]
        vmin = list({ad: x for ad, x in vmin}.items())
        vmout = []
        if not nan:
            for row in range(m):
                ids = topk_ids(v[row].view(np.float32), k, bool(order))
                vmout += [(o + row * o_str + j, int(x)) for j, x in enumerate(ids)]
                if has_r:
                    vmout += [(r + row * r_str + j, int(v[row, x])) for j, x in enumerate(ids)]
        (out / f'vec_{i}.vmin.mem').write_text(''.join(f'{ad:05x}{x:08x}\n' for ad, x in vmin) + 'fffffffffffff\n')
        (out / f'vec_{i}.vmout.mem').write_text(''.join(f'{ad:05x}{x:08x}\n' for ad, x in vmout) + 'fffffffffffff\n')
        lines.append(f"{i} {1 if nan else 0} tk2r{i}_n{n}_k{k}_m{m}_o{order}_r{has_r}_a{a % 8}_s{a_str}_mode{mode}")
    (out / 'list.txt').write_text(f'{cnt}\n' + '\n'.join(lines) + '\n')
    print(cnt, 'vectors')


if __name__ == '__main__':
    main()
