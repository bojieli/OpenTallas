#!/usr/bin/env python3
"""HBM-B-RTL3c QBG bench (coordinator 0dr addition, 10-18): quantize-before-gather is bit-identical to the golden.

For every gathered tensor that feeds ONLY an FP8 block-dot linear (d4g_quadrant_1017.QBG_TAGS) at its d4g shape, each
quadrant q quantises its own contiguous slice x[q n/4 : (q+1) n/4] with the reference quantiser
hdc_golden_v41.quant_fp8 (act_quant, block 32, UE8M0 exponent: the quantiser the SM x-load runs, ot_hdc_actquant), the
ring gathers codes + exponents, and the consumer runs the block-dot on them.  Checked against the golden on the full
vector: (1) codes and exponents equal bit for bit, (2) the linear output equals hdc_golden_v41.linear_q(w, x) bit for
bit (random FP8 weights + exponents), over random, heavy-tailed, all-zero / tiny (amax floor), saturating, BF16-rounded
and tie-heavy vectors.  MUTANTS that must FAIL: a quadrant boundary off the 32 grid (+16), and a 128-block quantiser
split at the expert-intermediate slice (576 = 4.5 x 128: the block straddles quadrants).

    PYTHONPATH=tools python3 tools/hgi_sim/qbg_quant_bench_1018.py [--trials 200]
"""
import argparse
import sys

import numpy as np

import hdc_golden_v41 as G
from hdc_golden import F, to_bf16

NQ = 4
SHAPES = {"expert_intermediate_gather": 2304, "o-group": 1024, "engram.rows_gather": 6144}


def vectors(n, rng, trials):
    for t in range(trials):
        k = t % 6
        if k == 0:
            x = rng.standard_normal(n)
        elif k == 1:
            x = rng.standard_t(1.5, n) * 10.0 ** rng.integers(-6, 4)
        elif k == 2:
            x = np.zeros(n)
            x[rng.integers(0, n, 5)] = rng.standard_normal(5) * 1e-6       # amax floor blocks
        elif k == 3:
            x = rng.standard_normal(n) * 3e4                               # large magnitudes
        elif k == 4:
            x = to_bf16(rng.standard_normal(n).astype(F))                  # BF16 inputs (to_bf16(a), to_bf16(z))
        else:
            e = rng.integers(-8, 8, n)                                     # tie-heavy: E4M3 half-steps
            x = np.ldexp(1.0 + (rng.integers(0, 16, n) * 2 + 1) / 32.0, e) * rng.choice([-1, 1], n)
        yield to_bf16(np.asarray(x, dtype=F))


def quant_split(x, bounds, block=32):
    qs, es = [], []
    for a, b in zip(bounds[:-1], bounds[1:]):
        q, e = G.quant_fp8(x[a:b], block)
        qs.append(q)
        es.append(e)
    return np.concatenate(qs), np.concatenate(es)


def linear_pre(w, xq, xe):
    """the consumer's block-dot on gathered codes + exponents (linear_q with quant_fp8 replaced by the gathered values)"""
    n, k = w.q.shape
    acc = np.zeros(n, dtype=F)
    for b in range(k // 32):
        d = np.ldexp((w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(F), w.e[:, b] + xe[b]).astype(F)
        acc = G.add(acc, d)
    return to_bf16(acc)


def run(n, bounds, trials, rng, block=32, rows=8):
    bad = 0
    wq = G._e4m3_round(np.clip(rng.standard_normal((rows, n)) * 64, -448, 448))
    w = G.Q8(wq.astype(np.float64), rng.integers(-12, -4, (rows, n // 32)).astype(np.int64))
    for x in vectors(n, rng, trials):
        q0, e0 = G.quant_fp8(x)
        try:
            q1, e1 = quant_split(x, bounds, block)
            if block != 32:
                e1 = np.repeat(e1, block // 32)
        except ValueError:
            return trials                                   # the split cannot even be quantised blockwise
        if q1.shape != q0.shape or not (np.array_equal(q0.view(np.uint64), q1.view(np.uint64)) and np.array_equal(e0, e1)):
            bad += 1
            continue
        y0 = G.linear_q(w, x)
        y1 = linear_pre(w, q1, e1)
        if not np.array_equal(G.bits(np.asarray(y0, dtype=F)), G.bits(np.asarray(y1, dtype=F))):
            bad += 1
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=120)
    a = ap.parse_args()
    rng = np.random.default_rng(20261018)
    ok = True
    for name, n in SHAPES.items():
        s = n // NQ
        assert s % 32 == 0, (name, s)
        bounds = [q * s for q in range(NQ + 1)]
        bad = run(n, bounds, a.trials, rng)
        print(f"QBG {name} n={n} slice={s} (mod32 {s % 32}, mod128 {s % 128}) trials={a.trials} mismatches={bad}")
        ok &= bad == 0
    # mutants
    n = SHAPES["expert_intermediate_gather"]
    s = n // NQ
    m1 = run(n, [0, s + 16, 2 * s, 3 * s, n], a.trials, rng)
    print(f"QBG MUTANT off_grid_boundary(+16) mismatches={m1} -> {'REJECTED' if m1 else 'ESCAPED'}")
    m2 = run(n, [0, s, 2 * s, 3 * s, n], a.trials, rng, block=128) if s % 128 else 0
    print(f"QBG MUTANT block128_at_576 mismatches={m2} -> {'REJECTED' if m2 else 'ESCAPED'}")
    ok &= m1 > 0 and m2 > 0
    print("QBG_BENCH " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
