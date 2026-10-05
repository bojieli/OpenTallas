#!/usr/bin/env python3
"""Vectors for ot_a3_attention_av_walk, from the reference's own functions.

``_accumulate_context`` and the rescale step in ``_execute_tile`` are the
authority (runtime/tensor_accelerator/sparse_attention.py). This generator does
not reimplement either: it calls ``_single_rounded_add`` for the product-add and
numpy's own binary32 multiply for the rescale, in the reference's order, so the
expectations are the contract rather than a second opinion about it.

Every case is a SEQUENCE of source blocks -- the first clearing the accumulator,
the rest rescaling it -- because that is the only way to hand the walk a nonzero
accumulator to rescale, and it is also exactly what ``_execute_tile``'s block
loop does. A single-block case would leave the rescale path untested.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.tensor_accelerator.sparse_attention import (  # noqa: E402
    _BINARY32_ZERO,
    _single_rounded_add,
)

LANES = 64
KV_ROWS = 32


def bf16(values: np.ndarray) -> np.ndarray:
    """Round-to-nearest-even narrowing to BF16 codes."""
    bits = np.ascontiguousarray(values.astype(np.float32)).view(np.uint32)
    lower = bits & np.uint32(0xFFFF)
    rounded = (bits >> np.uint32(16)).astype(np.uint32)
    up = (lower > np.uint32(0x8000)) | (
        (lower == np.uint32(0x8000)) & ((rounded & np.uint32(1)) == np.uint32(1))
    )
    return (rounded + up.astype(np.uint32)).astype(np.uint16)


def widen(codes: np.ndarray) -> np.ndarray:
    return (codes.astype(np.uint32) << np.uint32(16)).view(np.float32)


#: name, channels, blocks as (clear, rescale, mask_kind)
CASES = [
    ("two_blocks", 128, [(1, 1.0, "all"), (0, 0.5, "all")]),
    ("three_blocks", 128, [(1, 1.0, "all"), (0, 0.25, "all"), (0, 0.75, "all")]),
    #: A rescale that underflows to zero: the reference's canonicalizing add is
    #: guarded on exactly this, and the accumulator here is negative so the
    #: product would be negative zero under a multiplier that preserved it.
    ("rescale_zero", 128, [(1, 1.0, "neg"), (0, 0.0, "all")]),
    ("padding", 128, [(1, 1.0, "all"), (0, 0.5, "half")]),
    #: The smallest and largest head_dim any shipped ATTENTION.SPARSE uses.
    ("small_channels", 16, [(1, 1.0, "all"), (0, 0.5, "all")]),
    ("wide_channels", 512, [(1, 1.0, "all"), (0, 0.5, "all")]),
    ("unit_rescale", 64, [(1, 1.0, "all"), (0, 1.0, "all")]),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    header = [str(len(CASES)), str(KV_ROWS), str(LANES)]
    body: list[str] = []
    order_discriminates = []

    for index, (name, channels, blocks) in enumerate(CASES):
        rng = np.random.default_rng(0xA7 + index)
        kv_codes = bf16(rng.standard_normal((KV_ROWS, channels)) * 0.5)
        (args.out / f"kv_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in kv_codes.reshape(-1)) + "\n")

        accumulator = np.zeros(channels, dtype=np.float32)
        block_lines = []
        for b, (clear, rescale, mask_kind) in enumerate(blocks):
            rows = rng.integers(0, KV_ROWS, size=LANES).astype(np.uint32)
            scale = -1.0 if mask_kind == "neg" else 1.0
            prob_codes = bf16(np.abs(rng.standard_normal(LANES)) * 0.1 * scale)
            valid = np.ones(LANES, dtype=bool)
            if mask_kind == "half":
                valid[37:] = False
            probs = widen(prob_codes)

            if clear:
                accumulator = np.zeros(channels, dtype=np.float32)
            else:
                rescale32 = np.float32(rescale)
                accumulator = np.multiply(
                    accumulator, rescale32, dtype=np.float32)
                if rescale32 == np.float32(0.0):
                    accumulator = np.add(
                        accumulator, _BINARY32_ZERO, dtype=np.float32)

            #: Lane on the outside, every channel of one lane at once: the
            #: reference's schedule, so each channel sees ascending slot order.
            for lane in range(LANES):
                row = widen(kv_codes[int(rows[lane])]) if valid[lane] \
                    else np.zeros(channels, dtype=np.float32)
                accumulator = _single_rounded_add(
                    accumulator,
                    np.full(channels, probs[lane], dtype=np.float32),
                    row,
                )

            (args.out / f"prob_{index}_{b}.hex").write_text(
                "\n".join(f"{int(c):08x}" for c in prob_codes) + "\n")
            (args.out / f"rows_{index}_{b}.hex").write_text(
                "\n".join(f"{int(r):08x}" for r in rows) + "\n")
            mask = "".join("1" if v else "0" for v in valid[::-1])
            code = int(np.float32(rescale).view(np.uint32))
            block_lines.append(f"{clear} {code:08x} {mask}")

        #: Would a DESCENDING lane order give a different accumulator?
        forward = accumulator.copy()
        reverse = np.zeros(channels, dtype=np.float32)
        rng2 = np.random.default_rng(0xA7 + index)
        _ = bf16(rng2.standard_normal((KV_ROWS, channels)) * 0.5)
        rows0 = rng2.integers(0, KV_ROWS, size=LANES).astype(np.uint32)
        p0 = widen(bf16(np.abs(rng2.standard_normal(LANES)) * 0.1))
        for lane in reversed(range(LANES)):
            reverse = _single_rounded_add(
                reverse,
                np.full(channels, p0[lane], dtype=np.float32),
                widen(kv_codes[int(rows0[lane])]),
            )
        ascending = np.zeros(channels, dtype=np.float32)
        for lane in range(LANES):
            ascending = _single_rounded_add(
                ascending,
                np.full(channels, p0[lane], dtype=np.float32),
                widen(kv_codes[int(rows0[lane])]),
            )
        differs = bool(np.any(
            ascending.view(np.uint32) != reverse.view(np.uint32)))
        order_discriminates.append((name, differs))

        (args.out / f"acc_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in forward.view(np.uint32)) + "\n")
        body.append(f"{name} {channels} {len(blocks)}")
        body.extend(block_lines)

    (args.out / "cases.txt").write_text("\n".join(header + body) + "\n")
    assert any(d for _, d in order_discriminates), (
        "no case distinguishes ascending from descending lane order; the suite "
        "would pass on the wrong association")
    for name, differs in order_discriminates:
        print(f"  {name:<16} descending lane order differs: {differs}")
    print(f"wrote {len(CASES)} cases to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
