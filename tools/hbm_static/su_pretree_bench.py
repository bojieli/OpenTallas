#!/usr/bin/env python3
"""Stimulus + expected scalars for rtl/test/hbm_accel/generic/tb_hbm_su_red_pretree.sv (HH-6 / HBM-SURED 10-18).

Reductions at production shape and the edge cases: Qwen softmax exp_sum / max (8192 words), DS engram.ss (20480),
q_norm-like 128, a partial 300 / 40 / 5 words, MAX 200, values with mixed exponents (order-sensitive), -0, subnormals.
Words beyond a block's cnt carry garbage (the pre-tree must ignore them).  Lowered by su_pretree_lower.Schedule; every
expected value is hdc_golden_v41.csum / canonical max (asserted equal to the lowered tree value).
    python3 tools/hbm_static/su_pretree_bench.py OUTDIR   -> stim.mem, exps.mem, plusargs.txt
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import su_pretree_lower as L  # noqa: E402


def vals(rng, n, kind):
    m = rng.standard_normal(n).astype(np.float32) * np.exp2(rng.integers(-12, 12, n)).astype(np.float32)
    if kind == "max":
        m = m - np.float32(3.0)
    u = m.view(np.uint32).copy()
    sel = rng.random(n)
    u[sel < 0.01] = 0x80000000                                  # -0
    u[(sel >= 0.01) & (sel < 0.02)] = rng.integers(1, 1 << 23, int(((sel >= 0.01) & (sel < 0.02)).sum()))  # subnormal
    return u


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261018)
    S = L.Schedule()
    t = 10
    cases = [("sum", 8192), ("max", 8192), ("sum", 20480), ("sum", 128), ("sum", 300), ("sum", 40), ("sum", 5),
             ("max", 200), ("sum", 1), ("sum", 1000)]
    for i, (kind, n) in enumerate(cases):
        t = S.lower(kind, vals(rng, n, kind), 0x200 + i, t)
        t = max(t, max(S.exps[-1][0] - L.PT_RED + 1, t))            # next reduction's arrivals after this export
    ne = max(max(S.red), max(S.tree)) + 40
    W = 48 + 74 + 128 + 4096
    with open(out / "stim.mem", "w") as f:
        for e in range(ne):
            v = 0
            if e in S.tree:
                mx, cnt, blk = S.tree[e]
                xs = [int(x) for x in blk] + [int(x) for x in rng.integers(0, 1 << 32, L.BLOCK - len(blk), dtype=np.uint64)]
                v |= L.tree_cmd_word(mx, cnt) << (W - 48)
                v |= ((1 << 128) - 1) << 4096
                for w, x in enumerate(xs):
                    v |= (x & 0xffffffff) << (32 * w)
            else:
                for w in range(L.BLOCK):                             # idle lanes: garbage, no tree_cmd
                    v |= int(rng.integers(0, 1 << 32, dtype=np.uint64)) << (32 * w)
            if e in S.red:
                v |= L.red_cmd_word(S.red[e]) << (4096 + 128)
            f.write(f"{v:0{W // 4}x}\n")
    with open(out / "exps.mem", "w") as f:
        for e, tag, val in S.exps:
            f.write(f"{e:08x}{tag:08x}{val:08x}\n")
    (out / "plusargs.txt").write_text(f"+NE={ne} +NEXP={len(S.exps)}\n")
    blocks = len(S.tree)
    print(f"edges {ne} blocks {blocks} exports {len(S.exps)} reducer ops {len(S.red)}")
    for (kind, n), (e, tag, val) in zip(cases, S.exps):
        print(f"  {kind} n={n}: export red_cmd edge {e} value {val:08x}")


if __name__ == "__main__":
    main()
