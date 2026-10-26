#!/usr/bin/env python3
"""RTL-BUILD-S81: fixtures for tb_s81dv_xfin16e (xfin ENG mode) from tools/hdc_golden_v41 (ARITH chunk8).
Engram copy j (D = 5120): hh = csum(h*h), kk = csum(k*k), dd = csum((h*w)*k) -- the three sums of Model.engram_layer.
Vector v = kind * 4 + copy (kind 0 hh, 1 kk, 2 dd).  p.mem: 12 x 80 beat partials (the golden's aligned 64-element
subtree csum, as ot_s81sl_ve emits them), index v * 80 + beat; t.mem: the 12 golden csum totals over D.
Usage: xfin_eng_golden.py OUTDIR [--seed N]"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdc_golden_v41 as g  # noqa: E402

g.set_arith("chunk8")
F = np.float32
D, NB = 5120, 80


def hexw(a):
    return [f"{int(x):08x}" for x in np.asarray(a, dtype=F).reshape(-1).view(np.uint32)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    h = g.to_bf16((rng.standard_normal((4, D)) * 2.0).astype(F))
    k = (rng.standard_normal((4, D)) * 0.7).astype(F)
    w = (rng.standard_normal((4, D)) * 0.1).astype(F)
    for j in range(4):                                   # signed zeros in every operand
        idx = rng.choice(D, 24, replace=False)
        h[j, idx[:8]] = F(0.0); h[j, idx[8:16]] = F(-0.0); k[j, idx[16:20]] = F(-0.0); w[j, idx[20:]] = F(-0.0)
    prods = {}
    for j in range(4):
        prods[(0, j)] = g.mul(h[j], h[j])
        prods[(1, j)] = g.mul(k[j], k[j])
        prods[(2, j)] = g.mul(g.mul(h[j], w[j]), k[j])
    p = np.zeros((12, NB), dtype=F); t = np.zeros(12, dtype=F)
    for kind in range(3):
        for j in range(4):
            v = kind * 4 + j
            x = prods[(kind, j)]
            t[v] = g.reduce_sum_c(x)
            for b in range(NB):
                p[v, b] = g.reduce_sum_c(x[b * 64:(b + 1) * 64])
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    (o / "p.mem").write_text("\n".join(hexw(p)) + "\n")
    (o / "t.mem").write_text("\n".join(hexw(t)) + "\n")
    print("wrote", o, "totals", " ".join(hexw(t)))


if __name__ == "__main__":
    main()
