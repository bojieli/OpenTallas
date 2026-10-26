#!/usr/bin/env python3
"""RTL-BUILD-S81: fixtures for tb_s81sl_eg (the Engram scalar finish) from tools/hdc_golden_v41 (ARITH chunk8).
Each case = one copy j of Model.engram_layer: the totals hh = csum(h*h), kk = csum(k*k), dd = csum((h*w)*k) over D = 5120
and the golden gate, computed with EXACTLY engram_layer's expressions (the scalar part, lines 'rstd = ...' to 'gate = ...').
Cases: full random copies (BF16 h, FP32 k / w at engram scales, so the totals are real engram_layer totals) plus edge copies:
dot < 0, |dot| below the 1e-6 clamp, dd = +0 / -0, hh = 0 (rsqrt(eps)), large |dot| (sigmoid saturation).
Usage: eg_golden.py OUTDIR [--seed N] [--ncase N]   -> OUTDIR/{cases.mem (hh kk dd gate per line), cfg.mem (eps scale n)}"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdc_golden_v41 as g  # noqa: E402

g.set_arith("chunk8")
F = np.float32
D = 5120


def gate_of(hh, kk, dd, eps, scale):
    # Model.engram_layer, verbatim apart from the csum totals being arguments
    n = F(D)
    rstd = g.mul(g.rsqrt(g.add(g.div(hh, n), eps)), g.rsqrt(g.add(g.div(kk, n), eps)))
    dot = g.mul(g.mul(dd, rstd), scale)
    mag = g.sqrt(np.maximum(np.abs(dot), F(1e-6)).astype(F))
    return F(g.sigmoid(np.where(dot < 0, g.neg(mag), mag).astype(F))), F(dot)


def hx(x):
    return f"{int(np.asarray(x, dtype=F).view(np.uint32)):08x}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--ncase", type=int, default=24)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    eps = F(1e-6)
    scale = F(D ** -0.5)
    cases = []
    nfull = a.ncase // 2
    for _ in range(nfull):
        h = g.to_bf16((rng.standard_normal(D) * rng.uniform(0.05, 4.0)).astype(F))
        k = (rng.standard_normal(D) * rng.uniform(0.05, 2.0)).astype(F)
        w = (rng.standard_normal(D) * rng.uniform(0.01, 1.0)).astype(F)
        hh = g.reduce_sum_c(g.mul(h, h)); kk = g.reduce_sum_c(g.mul(k, k))
        dd = g.reduce_sum_c(g.mul(g.mul(h, w), k))
        cases.append((F(hh), F(kk), F(dd)))
    edge = [
        (F(5120.0), F(5120.0), F(-37.5)),            # dot < 0
        (F(5120.0), F(5120.0), F(1e-9)),             # |dot| < 1e-6 -> clamp, positive
        (F(5120.0), F(5120.0), F(-1e-9)),            # clamp, negative
        (F(3000.0), F(800.0), F(0.0)),               # dd = +0
        (F(3000.0), F(800.0), F(-0.0)),              # dd = -0 (signed zero)
        (F(0.0), F(2.0), F(0.5)),                    # hh = 0: rsqrt(eps)
        (F(1.0), F(1.0), F(4.0e3)),                  # large dot: sigmoid -> 1
        (F(1.0), F(1.0), F(-4.0e3)),                 # sigmoid -> 0
    ]
    cases += edge
    while len(cases) < a.ncase:
        cases.append((F(rng.uniform(1, 1e4)), F(rng.uniform(1, 1e4)), F(rng.standard_normal() * 100)))
    cases = cases[:max(a.ncase, nfull + len(edge))]
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    lines, nneg, nclamp = [], 0, 0
    for hh, kk, dd in cases:
        gt, dot = gate_of(hh, kk, dd, eps, scale)
        nneg += int(dot < 0); nclamp += int(abs(dot) < 1e-6)
        lines.append(f"{hx(hh)}{hx(kk)}{hx(dd)}{hx(gt)}")
    (o / "cases.mem").write_text("\n".join(lines) + "\n")
    (o / "cfg.mem").write_text(f"{hx(eps)}\n{hx(scale)}\n{len(cases):08x}\n")
    print(f"wrote {o}: {len(cases)} cases, dot<0 {nneg}, clamp {nclamp}")


if __name__ == "__main__":
    main()
