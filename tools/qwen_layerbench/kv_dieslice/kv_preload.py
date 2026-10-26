#!/usr/bin/env python3
"""KV-TOK 10-24: HBM preload file for the kv_dieslice HBM PHY bench model (qkd_hbm3e_phy_pc4_bench.sv +HBM_PRELOAD).

Layout = CONTRACT map v2 (results/arch/qwen_kv_die_20261009/CONTRACT.md, KV write path) + MU row bits:
  row (layer, v, t) of the die's KV head (HEADS 1) = 1024 b = 4 sectors of 256 b; sector q -> stack t[8:7],
  PC {q, t[2:0]} of that stack, in-row sector {v, t[6], t[13:9], t[5:3]} (10 b), HBM row 64 + layer + 256 * user;
  in-row sector -> (bank, col): sector = ((bank >> 2) << 7) | (col << 2) | (bank & 3).
Stack index -> stack name (--stacks, default WS,WN,ES,EN) and the as-built slice split (slice k = PCs 4k..4k+3 of the stack;
partition phy_<S>_<j> holds slice k per the bind's asbuilt_map 'phy_<S>.u_s<k>' -> 'phy_<S>_<j>').  Both are checked against
the bench's +HBM_LOG write / read addresses (the RECIPE self-check) before the preload is trusted.
    kv_preload.py --kv kv.hex --ctx T --asbuilt asbuilt_map.json [--layers 0-35] [--user 0] [--stacks WS,WN,ES,EN]
                  [--skip-last] [--mut-kswap PART]  > preload.txt
kv.hex: K rows 0..T-1 then V rows 0..T-1, 128 FP8 bytes each (dim 0 = LSB byte), one 1024-b hex word per line.
--mut-kswap PART: mutant m3 -- in partition PART, every K row t is replaced by row t^1 (the preload of one slice moved).
"""
import argparse
import json
import sys


def addr(layer, v, t, q, user, stacks):
    stack = stacks[(t >> 7) & 3]
    pc = (q << 3) | (t & 7)
    sec = (v << 9) | (((t >> 6) & 1) << 8) | (((t >> 9) & 31) << 3) | ((t >> 3) & 7)
    bank = ((sec >> 7) << 2) | (sec & 3)
    col = (sec >> 2) & 31
    return stack, pc >> 2, pc & 3, bank, 64 + layer + 256 * user, col


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kv', required=True)
    ap.add_argument('--ctx', type=int, required=True)
    ap.add_argument('--asbuilt', required=True)
    ap.add_argument('--layers', default='0-35')
    ap.add_argument('--user', type=int, default=0)
    ap.add_argument('--stacks', default='WS,WN,ES,EN')
    ap.add_argument('--skip-last', action='store_true')
    ap.add_argument('--mut-kswap', default='')
    a = ap.parse_args()
    rows = [int(x, 16) for x in open(a.kv).read().split()]
    T = a.ctx
    assert len(rows) >= 2 * T, (len(rows), T)
    parts = json.load(open(a.asbuilt))['parts']
    lo, _, hi = a.layers.partition('-')
    layers = range(int(lo), int(hi or lo) + 1)
    stacks = a.stacks.split(',')
    n = 0
    for layer in layers:
        for v in (0, 1):
            for t in range(T - (1 if a.skip_last else 0)):
                for q in range(4):
                    st, k, pcl, bank, row, col = addr(layer, v, t, q, a.user, stacks)
                    part = parts[f'phy_{st}.u_s{k}']
                    src = t ^ 1 if (a.mut_kswap == part and v == 0 and (t ^ 1) < T) else t
                    d = (rows[v * T + src] >> (256 * q)) & ((1 << 256) - 1)
                    print(f'{part} {pcl} {bank} {row} {col} {d:064x}')
                    n += 1
    print(f'kv_preload: {n} sectors, layers {layers.start}-{layers.stop - 1}, T {T}, user {a.user}, stacks {stacks}',
          file=sys.stderr)


if __name__ == '__main__':
    main()
