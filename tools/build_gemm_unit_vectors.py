#!/usr/bin/env python3
"""Operand images and reference results for the GEMV and GEMM compute units.

One generator serves both, so the two units are compared on the SAME arithmetic
rather than on two sets of vectors that happen to look alike:

    ot_compute_unit        NCOL=1  act.hex is one 16-bit activation per K index
    ot_compute_unit_gemm   NCOL=N  act.hex is N activations packed per K index

Expected accumulator words come from ``runtime.reference.mac_tile`` -- the
independent Python authority for the block-floating-point tile, which computes in
Python integers with no floating point anywhere -- and never from either RTL. A
disagreement is therefore a disagreement with the reference, not between two
siblings that could both be wrong the same way.

EXPONENTS ARE CHOSEN SO THE DROPPED PATH IS EXERCISED. Activations take biased
exponents in [120, 124] and most weights the same, which puts ``a_exp + b_exp`` in
[240, 248] -- inside the window [scale_exp, scale_exp + EXP_WINDOW] at
scale_exp=240. A small fraction of WEIGHTS take [104, 108] instead, so their term
falls below the window and that lane must raise ``dropped``. The rare code is in
the weight and not the activation deliberately: an out-of-window activation drops
every lane at once, which checks nothing about per-lane reporting, while an
out-of-window weight makes the mask differ between lanes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.reference.mac_tile import dot_product, to_twos_complement  # noqa: E402

#: Fraction of weight codes placed below the accumulation window.
DROP_RATE = 0.02
IN_WINDOW_EXP = (120, 124)
BELOW_WINDOW_EXP = (104, 108)


def build(k: int, lanes: int, ncol: int, acc_w: int, scale_exp: int,
          seed: int, out: Path) -> dict[str, object]:
    rng = random.Random(seed)

    def bf16(lo: int, hi: int) -> int:
        """A BF16 code with a biased exponent in [lo, hi]; sign and fraction random."""
        return (rng.getrandbits(1) << 15) | (rng.randint(lo, hi) << 7) | rng.getrandbits(7)

    acts = [[bf16(*IN_WINDOW_EXP) for _ in range(k)] for _ in range(ncol)]
    wgts = [[(bf16(*BELOW_WINDOW_EXP) if rng.random() < DROP_RATE
              else bf16(*IN_WINDOW_EXP))
             for _ in range(lanes)] for _ in range(k)]

    out.mkdir(parents=True, exist_ok=True)
    with (out / "act.hex").open("w") as f:
        for i in range(k):
            word = 0
            for n in range(ncol):
                word |= acts[n][i] << (16 * n)
            f.write(f"{word:0{4 * ncol}x}\n")
    with (out / "wgt.hex").open("w") as f:
        for i in range(k):
            for l in range(lanes):
                f.write(f"{wgts[i][l]:04x}\n")

    values: list[int] = []
    drops: list[int] = []
    for n in range(ncol):
        for l in range(lanes):
            r = dot_product([acts[n][i] for i in range(k)],
                            [wgts[i][l] for i in range(k)],
                            scale_exp=scale_exp)
            values.append(to_twos_complement(r.value, acc_w))
            drops.append(1 if r.dropped else 0)
    with (out / "exp.hex").open("w") as f:
        for v in values:
            f.write(f"{v:0{(acc_w + 3) // 4}x}\n")
    with (out / "drop.hex").open("w") as f:
        for v in drops:
            f.write(f"{v:x}\n")

    digests = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(out.glob("*.hex"))}
    return {"k": k, "lanes": lanes, "ncol": ncol, "acc_w": acc_w,
            "scale_exp": scale_exp, "seed": seed,
            "accumulators": lanes * ncol,
            "mac_per_pass": lanes * ncol * k,
            "lanes_reporting_dropped": sum(drops),
            "drop_rate": DROP_RATE,
            "reference": "runtime.reference.mac_tile.dot_product",
            "digests": digests, "directory": str(out)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=32)
    ap.add_argument("--lanes", type=int, default=16)
    ap.add_argument("--ncol", type=int, default=1)
    ap.add_argument("--acc-w", type=int, default=40)
    ap.add_argument("--scale-exp", type=int, default=240)
    ap.add_argument("--seed", type=int, default=20260914)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    record = build(a.k, a.lanes, a.ncol, a.acc_w, a.scale_exp, a.seed, Path(a.out))
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
