#!/usr/bin/env python3
"""S81U-MIX: fixtures for tb_s81sl_ve from tools/hdc_golden_v41 (ARITH chunk8): one beat (64 elements) x 4 copies.
Partials = csum over the beat (the golden's aligned 64-element subtree); out = to_bf16(add(h, mul(gate, v))).
Usage: ve_golden.py OUTDIR [--seed N]"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdc_golden_v41 as g  # noqa: E402

g.set_arith("chunk8")
F = np.float32


def hexw(a):
    return [f"{int(x):08x}" for x in np.asarray(a, dtype=F).view(np.uint32)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    h = g.to_bf16(rng.standard_normal((4, 64)).astype(F) * F(2.0))
    h[0, 5] = F(0.0); h[2, 17] = F(-0.0)
    k = (rng.standard_normal((4, 64)) * 0.7).astype(F)
    w = (rng.standard_normal((4, 64)) * 0.1).astype(F)
    v = rng.standard_normal(64).astype(F)
    gate = rng.uniform(0.01, 0.99, 4).astype(F)
    p = []
    for j in range(4):
        p += [g.reduce_sum_c(g.mul(h[j], h[j])), g.reduce_sum_c(g.mul(k[j], k[j])),
              g.reduce_sum_c(g.mul(g.mul(h[j], w[j]), k[j]))]
    y = np.stack([g.to_bf16(g.add(h[j], g.mul(gate[j], v))) for j in range(4)])
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    for name, arr in (("h", h), ("k", k), ("w", w), ("v", v), ("g", gate), ("p", np.array(p, dtype=F)), ("y", y)):
        (o / f"{name}.mem").write_text("\n".join(hexw(np.asarray(arr).reshape(-1))) + "\n")
    print("wrote", o)


if __name__ == "__main__":
    main()
