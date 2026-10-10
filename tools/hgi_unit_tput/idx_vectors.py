#!/usr/bin/env python3
"""IDX unit THROUGHPUT vectors (hgi-1010/g): back-to-back IDX records with the real DS-V4.1 1M per-die shapes.

  route.top6        IDX.TOPK  A VM FP32 n 384 (router scores + bias) -> O VM U32 6 ids, k 6, param[12] ascending ids
                    (every die, every layer; header 0x90800102200010060000... from the exported L0 program)
  row_gather.owned  IDX.OWNED A = SELIDX (U32, kk = 512 / 2048 selected ids), O = OWNL (U32, RG_SLOTS 64),
                    R = SELT (U32, kk), D = MCNT (U32, 2); param = KEY_BLOCK 8 | TP 96 << 8 | c 2 << 16
                    (compiler 6dd28b4a7, G24 software ROW_GATHER)
IDX.MERGE is not emitted by the production lowering (the compiler uses COLL.TOPK_MERGE), so no production record exists.
Golden: hgi_sim.machine.topk_ids (the simulator's unit) and tools/hgi_idx_owned_vectors.golden (G24 list golden).
Price: hgi_sim.ds_native_timing.NativeCost: TOPK = walk(route) 283.008 (exported L0 meta, src_gf); OWNED = measured
{512: 1227, 2048: 4510} (the NativeCost table).
Output: recs.txt lines "<op> <k|K> <die> <cost x1000> <a> <o> <r> <d> <nA> <nO> <nR> <nD> <hdr hex>" + per record
a_<i>.mem (input words) and e_<i>.mem ({addr, word} expected writes).
"""
import argparse
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from hgi_sim.machine import topk_ids  # noqa: E402
from hgi_idx_owned_vectors import golden as owned_golden  # noqa: E402

TOPK_HDR = 0x90800102200010060000000000000000
OWNED_PRICE = {512: 1227.0, 2048: 4510.0}


def owned_hdr(B, G, c):
    h = 9 << 124 | 3 << 118 | 0b0111001 << 93          # unit 9, op 3, operands A, D, O, R
    return h | B << 64 | G << 72 | c << 80


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261010)
    lines = []
    k = 0

    def emit(op, kk, die, cost, a, o, r, d, na, no, nr, nd, hdr, words, exp):
        nonlocal k
        np.savetxt(out / f'a_{k}.mem', np.asarray(words, np.uint32), fmt='%08x')
        (out / f'e_{k}.mem').write_text(''.join(f'{ad:08x}{int(w):08x}\n' for ad, w in exp))
        lines.append(f'{op} {kk} {die} {int(round(cost * 1000))} {a} {o} {r} {d} {na} {no} {nr} {nd} {hdr:032x} {len(exp)}')
        k += 1

    # production VM bases: router 88128 -> 88512 (L0 meta); OWNED: SELIDX / OWNL / SELT / MCNT (synthetic, aligned)
    for j in range(6):
        v = (rng.standard_normal(384) * 0.7 + rng.normal(0, .1)).astype(np.float32)
        if j == 2:                                      # ties: the lowest index must win
            v[[10, 200, 383]] = v.max() + 1
            v[[5, 6]] = v.max()
        a, o = 88128 + 1024 * j, 88512 + 1024 * j
        ids = topk_ids(v, 6, True)
        emit(2, 6, 0, 283.008, a, o, 0, 0, 384, 6, 0, 0, TOPK_HDR, v.view(np.uint32),
             [(o + i, x) for i, x in enumerate(ids)])
    for j, (K, die) in enumerate(((512, 0), (2048, 37), (512, 95))):
        ids = rng.choice(1 << 20, size=K, replace=False).astype(np.uint32)
        O, R, M, ND = owned_golden(ids, 8, 96, die, 2)
        a, oo, r, d = 120000 + 8192 * j, 160000 + 1024 * j, 170000 + 8192 * j, 200000 + 64 * j
        exp = [(oo + i, x) for i, x in enumerate(O)] + [(r + i, x) for i, x in enumerate(R)] + [(d, M), (d + 1, ND)]
        emit(3, K, die, OWNED_PRICE[K], a, oo, r, d, K, 64, K, 2, owned_hdr(8, 96, 2), ids, exp)
    (out / 'recs.txt').write_text(f'{len(lines)}\n' + '\n'.join(lines) + '\n')
    print(f'{len(lines)} records')


if __name__ == '__main__':
    main()
