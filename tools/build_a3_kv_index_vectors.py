#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_kv_index.sv``, from the reference's own decode.

The rules are transcribed from ``runtime.sim.engines.attention._sparse_index_rows``
rather than invented, and the two that are easy to get wrong each get a case that
only they fail:

``interleaved``   a live lane AFTER a pad lane. ABI 3.0 amendment A6 fixes padding
                  as one TRAILING RUN, so the reference requires
                  ``all(valid[:count])``. An implementation that merely counted
                  the live lanes would accept this and silently drop a row, which
                  is why counting and the trailing-run check are separate.
``wrapped_order`` live rows in DESCENDING order, which ROUTE.WINDOW_INDEX really
                  emits once a decode cursor passes the ring's last slot. The
                  reference says "the engine therefore must not silently sort
                  here", and rejecting the wrap is what once made every
                  uncompressed sparse layer trap at decode position 128. This
                  case is ADMITTED, and its mask is the proof that order is not
                  a refusal.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.sim.engines.attention import PAD_INDEX  # noqa: E402

SLOTS = 64
KV_ROWS = 512


def block_for(name: str, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pad = np.uint32(PAD_INDEX)
    row = np.full(SLOTS, pad, dtype=np.uint32)
    if name == "full":
        return rng.integers(0, KV_ROWS, size=SLOTS, dtype=np.uint32)
    if name == "trailing_pad":
        row[:11] = rng.integers(0, KV_ROWS, size=11, dtype=np.uint32)
        return row
    if name == "one_live":
        row[0] = np.uint32(7)
        return row
    if name == "wrapped_order":
        #: Descending: a circular window read after the cursor wrapped.
        row[:16] = np.arange(120, 104, -1, dtype=np.uint32)
        return row
    if name == "duplicate_rows":
        #: The reference does not deduplicate; two lanes may name one row.
        row[:8] = np.uint32(33)
        return row
    if name == "boundary_row":
        row[:4] = np.array([0, KV_ROWS - 1, 1, KV_ROWS - 2], dtype=np.uint32)
        return row
    # -- refusals -------------------------------------------------------------
    if name == "interleaved":
        row[:5] = rng.integers(0, KV_ROWS, size=5, dtype=np.uint32)
        row[2] = pad                     # a live lane follows a pad lane
        return row
    if name == "out_of_range":
        row[:6] = rng.integers(0, KV_ROWS, size=6, dtype=np.uint32)
        row[3] = np.uint32(KV_ROWS)      # exactly at the bound
        return row
    if name == "all_padding":
        return row
    raise AssertionError(name)


CASES = (
    ("full", 11, True),
    ("trailing_pad", 13, True),
    ("one_live", 17, True),
    ("wrapped_order", 19, True),
    ("duplicate_rows", 23, True),
    ("boundary_row", 29, True),
    ("interleaved", 31, False),
    ("out_of_range", 37, False),
    ("all_padding", 41, False),
)


def decode(row: np.ndarray):
    """The reference's rules: mask, count, and why it would refuse."""
    valid = row != np.uint32(PAD_INDEX)
    count = int(np.count_nonzero(valid))
    trailing = bool(np.all(valid[:count]))
    live = row[valid]
    in_range = bool(live.size == 0 or int(live.max()) < KV_ROWS)
    return valid, count, trailing, in_range


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lines = [str(len(CASES)), str(KV_ROWS)]
    for index, (name, seed, admit) in enumerate(CASES):
        row = block_for(name, seed)
        valid, count, trailing, in_range = decode(row)
        ok = trailing and in_range and count > 0
        assert ok == admit, (name, ok, admit)
        (args.out / f"idx_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in row) + "\n")
        mask = "".join("1" if v else "0" for v in valid[::-1]) if ok else "0" * SLOTS
        lines.append(f"{name} {int(ok)} {count if ok else 0} {mask}")

    (args.out / "cases.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(CASES)} cases to {args.out} (kv_rows={KV_ROWS})")
    for index, (name, seed, admit) in enumerate(CASES):
        row = block_for(name, seed)
        valid, count, trailing, in_range = decode(row)
        why = [] if admit else (
            ([] if trailing else ["padding interleaves"]) +
            ([] if in_range else ["index at or past kv_rows"]) +
            ([] if count else ["no live lane"]))
        print(f"   {name:16s} admit={int(admit)} live={count:2d}"
              + (f"  refused: {', '.join(why)}" if why else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
