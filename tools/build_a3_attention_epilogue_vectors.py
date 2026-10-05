#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_attention_epilogue.sv``, from the reference.

The expectations evaluate the reference's own four closing lines
(``sparse_attention.py::_execute_tile``) with its own helpers -- ``exp_cr32`` for
the sink term and ``_narrow`` for the output codes -- so nothing about the
narrowing or the exponential is transcribed:

    sink_exp    = exp_cr32(sink - maxima)
    denominator = sums + sink_exp
    context     = accumulator / denominator
    codes       = _narrow(context)

BOTH SIGNS OF THE OFFSET ARE COVERED, which they were not when this file was
written. A sink above the row maximum used to have no correctly-rounded path --
OP_EXP_NONPOS refuses a positive argument -- so every case kept the sink at or
below the maximum and the epilogue refused the rest. That was the wrong shape:
2,680 of V4-Flash's 2,944 shipped sink logits are POSITIVE, so the refused case
was the ordinary one. ot_a3_fp32_exp_pos_cr_rne now covers x > 0 and the epilogue
selects by sign, so the cases below include positive offsets and the generator
asserts only that the offset is FINITE.

``saturating`` exists because the division can overflow BF16 while the binary32
quotient is finite, which is the one place _narrow's clamp is reachable from here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.tensor_accelerator.sparse_attention import (  # noqa: E402
    _narrow,
    exp_cr32,
)

WIDTH = 32


def case_inputs(name: str, seed: int):
    rng = np.random.default_rng(seed)
    acc = rng.uniform(-40.0, 40.0, size=WIDTH).astype(np.float32)
    maxima = np.float32(3.5)
    sums = np.float32(9.25)
    sink = np.float32(-1.0)
    if name == "typical":
        return acc, maxima, sums, sink
    if name == "sink_equals_max":
        #: offset exactly 0, so the sink term is exp(0) = 1.0.
        return acc, maxima, sums, maxima
    if name == "sink_far_below":
        return acc, maxima, sums, np.float32(-80.0)
    if name == "sink_above_max":
        #: The offset is POSITIVE -- the case the old refusal rejected, and the
        #: one 91% of shipped sink logits produce whenever the row's scaled
        #: score maximum sits below the sink.
        return acc, np.float32(-1.5), sums, np.float32(2.4927471)
    if name == "sink_above_max_small":
        return acc, np.float32(0.25), sums, np.float32(1.129465)
    if name == "sink_far_above":
        #: A large positive offset, where the sink term dominates the denominator.
        return acc, np.float32(-9.0), np.float32(0.5), np.float32(2.4927471)
    if name == "tiny_denominator":
        #: A small denominator scales every channel up; the quotient stays finite.
        return acc, maxima, np.float32(np.ldexp(1.0, -20)), np.float32(-60.0)
    if name == "saturating":
        #: A FINITE quotient that still overflows BF16. The largest finite
        #: binary32 narrows to 0x7f80, which _narrow clamps to 0x7f7f, so
        #: FLT_MAX over a denominator of one reaches the clamp while staying
        #: finite. An INFINITE quotient would not do: the reference flags a
        #: nonfinite context and refers the row to its exact oracle instead of
        #: narrowing it, so such a case tests a repair path, not a clamp.
        flt_max = np.array([0x7f7fffff], dtype=np.uint32).view(np.float32)
        big = np.full(WIDTH, flt_max[0], dtype=np.float32)
        return big, maxima, np.float32(1.0), np.float32(-100.0)
    if name == "negative_accumulator":
        return (-np.abs(acc)).astype(np.float32), maxima, sums, sink
    if name == "zero_channels":
        a = acc.copy(); a[::3] = np.float32(0.0); a[1::3] = np.float32(-0.0)
        return a, maxima, sums, sink
    return acc, maxima, sums, sink


CASES = (
    ("typical", 11),
    ("sink_equals_max", 13),
    ("sink_far_below", 17),
    ("sink_above_max", 17),
    ("sink_above_max_small", 19),
    ("sink_far_above", 23),
    ("tiny_denominator", 19),
    ("saturating", 23),
    ("negative_accumulator", 29),
    ("zero_channels", 31),
)


def expected(acc, maxima, sums, sink):
    sink_exp = np.float32(exp_cr32(np.array([sink - maxima], dtype=np.float32))[0])
    denominator = np.float32(np.add(sums, sink_exp, dtype=np.float32))
    with np.errstate(divide="ignore", invalid="ignore", over="ignore",
                     under="ignore"):
        context = np.divide(acc, denominator, dtype=np.float32)
    codes, saturated = _narrow(context)
    return sink_exp, denominator, np.asarray(codes), np.asarray(saturated)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lines = [str(len(CASES))]
    for index, (name, seed) in enumerate(CASES):
        acc, maxima, sums, sink = case_inputs(name, seed)
        #: Both signs are legal now; only a finite offset is required, which is
        #: all either exponential's domain asks.
        assert np.isfinite(sink - maxima), f"{name}: offset is not finite"
        sink_exp, denominator, codes, saturated = expected(acc, maxima, sums, sink)
        assert np.isfinite(denominator) and denominator > 0, name
        #: AND THE QUOTIENT MUST BE FINITE. The reference flags a nonfinite
        #: context and repairs the row through its exact oracle rather than
        #: narrowing it, so a case with an overflowing quotient is testing a
        #: repair path that has no RTL -- it is not a positive case. Omitting
        #: this assertion is what first put an infinite quotient in the set.
        with np.errstate(divide="ignore", invalid="ignore", over="ignore",
                         under="ignore"):
            context = np.divide(acc, denominator, dtype=np.float32)
        assert np.all(np.isfinite(context)), f"{name}: quotient overflows"

        (args.out / f"acc_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in acc.view(np.uint32)) + "\n")
        (args.out / f"codes_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in codes.astype(np.uint32)) + "\n")
        lines.append(
            f"{name} {WIDTH} {int(maxima.view(np.uint32)):08x} "
            f"{int(sums.view(np.uint32)):08x} {int(sink.view(np.uint32)):08x} "
            f"{int(sink_exp.view(np.uint32)):08x} "
            f"{int(denominator.view(np.uint32)):08x} {int(saturated.sum())}")

    (args.out / "cases.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(CASES)} cases to {args.out}")
    for index, (name, seed) in enumerate(CASES):
        acc, maxima, sums, sink = case_inputs(name, seed)
        se, den, codes, sat = expected(acc, maxima, sums, sink)
        print(f"   {name:22s} sink_exp={float(se):>12.6g} denom={float(den):>12.6g} "
              f"saturated={int(sat.sum()):2d}/{WIDTH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
