#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_attention_denominator.sv``, from the reference.

This drives a SEQUENCE of source blocks, which is the point: the online softmax's
carried state is where implementations diverge, and a per-block test cannot see it.
Each case is a list of blocks, and the expectation walks the reference's own loop
over them with its own helpers -- ``exp_cr32`` for the exponential,
``_balanced_sum`` for the block sum -- and records the running maximum and
denominator after EVERY block, not just at the end.

    sums = RN(sums * rescale)     <- two separate roundings, not a fused
    sums = RN(sums + block_sum)      multiply-add

``rising_maxima`` and ``falling_maxima`` exist because the rescale only does work
when the maximum MOVES: a descending sequence leaves every later rescale at
exactly 1.0, so a block that forgot to apply it would still pass. The rising case
is the one that catches that, and the manifest records per case whether any
rescale differs from 1.0.
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
    _balanced_sum,
    exp_cr32,
)

LANES = 64


def blocks_for(name: str, seed: int):
    """A list of (valid mask, scores) blocks for one (row, head)."""
    rng = np.random.default_rng(seed)
    def rnd(lo, hi):
        return rng.uniform(lo, hi, size=LANES).astype(np.float32)
    ones = np.ones(LANES, dtype=bool)
    if name == "rising_maxima":
        #: Each block's maximum exceeds the last, so every rescale is < 1.
        return [(ones, rnd(-20.0, -10.0)), (ones, rnd(-8.0, -2.0)),
                (ones, rnd(0.0, 4.0)), (ones, rnd(6.0, 9.0))]
    if name == "falling_maxima":
        #: The maximum never moves after block 0, so every rescale is exactly 1.
        return [(ones, rnd(6.0, 9.0)), (ones, rnd(0.0, 4.0)),
                (ones, rnd(-8.0, -2.0))]
    if name == "single_block":
        return [(ones, rnd(-5.0, 5.0))]
    if name == "short_final_block":
        #: The last block is mostly padding, which the tree sees as +0 lanes.
        m = np.zeros(LANES, dtype=bool); m[:11] = True
        return [(ones, rnd(-3.0, 3.0)), (m, rnd(-3.0, 3.0))]
    if name == "all_padding_middle":
        m = np.zeros(LANES, dtype=bool)
        return [(ones, rnd(-3.0, 3.0)), (m, rnd(-3.0, 3.0)),
                (ones, rnd(-1.0, 5.0))]
    if name == "long_sequence":
        return [(ones, rnd(-12.0 + 2.0 * k, -8.0 + 2.0 * k)) for k in range(8)]
    return [(ones, rnd(-5.0, 5.0)), (ones, rnd(-5.0, 5.0))]


CASES = (
    ("rising_maxima", 11),
    ("falling_maxima", 13),
    ("single_block", 17),
    ("short_final_block", 19),
    ("all_padding_middle", 23),
    ("long_sequence", 29),
)


def walk(blocks):
    """The reference's own per-block loop, recording state after each block."""
    maxima = np.float32(0.0)
    sums = np.float32(0.0)
    trace = []
    for index, (valid, scores) in enumerate(blocks):
        masked = np.where(valid, scores, np.float32(-np.inf))
        block_max = np.float32(masked.max()) if valid.any() else np.float32(-np.inf)
        if index == 0:
            updated = np.float32(0.0) if block_max == 0 else block_max
            rescale = np.float32(0.0)
        else:
            updated = np.maximum(maxima, block_max) if valid.any() else maxima
            updated = np.float32(0.0) if updated == 0 else np.float32(updated)
            rescale = np.float32(exp_cr32(np.array([maxima - updated],
                                                  dtype=np.float32))[0])
        maxima = updated
        offsets = np.where(valid, (scores - maxima).astype(np.float32),
                           np.float32(-np.inf))
        probs = np.zeros(LANES, dtype=np.float32)
        live = np.flatnonzero(valid)
        if live.size:
            probs[live] = exp_cr32(np.ascontiguousarray(offsets[live]))
        block_sum = np.float32(_balanced_sum(probs.reshape(1, LANES))[0])
        sums = np.float32(np.multiply(sums, rescale, dtype=np.float32))
        sums = np.float32(np.add(sums, block_sum, dtype=np.float32))
        trace.append((valid, scores, maxima, rescale, sums))
    return trace


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lines = [str(len(CASES))]
    summary = []
    for index, (name, seed) in enumerate(CASES):
        blocks = blocks_for(name, seed)
        trace = walk(blocks)
        moved = sum(1 for (_, _, _, r, _) in trace[1:]
                    if int(np.float32(r).view(np.uint32)) != 0x3f800000)
        summary.append((name, len(trace), moved))
        lines.append(f"{name} {len(trace)}")
        for b, (valid, scores, maxima, rescale, sums) in enumerate(trace):
            (args.out / f"scores_{index}_{b}.hex").write_text(
                "\n".join(f"{int(c):08x}" for c in scores.view(np.uint32)) + "\n")
            mask = "".join("1" if v else "0" for v in valid[::-1])
            lines.append(f"  {mask} {int(np.float32(maxima).view(np.uint32)):08x} "
                         f"{int(np.float32(rescale).view(np.uint32)):08x} "
                         f"{int(np.float32(sums).view(np.uint32)):08x}")

    (args.out / "cases.txt").write_text("\n".join(lines) + "\n")
    assert any(m for _, _, m in summary), (
        "no case moves the maximum after block 0, so every rescale is 1.0 and a "
        "block that never applied it would pass")
    print(f"wrote {len(CASES)} cases to {args.out}")
    for name, n, moved in summary:
        print(f"   {name:22s} {n} blocks, {moved} with a rescale != 1.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
