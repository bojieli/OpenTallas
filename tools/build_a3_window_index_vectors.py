#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_window_index.sv``, from the reference's own rule.

The expected words are computed by the rule
``runtime.sim.engines.route.window_index`` applies, transcribed here rather than
called because that engine needs a live EngineContext:

    last  = position            (causal)   or context - 1   (full)
    first = max(0, last - window + 1)
    rows  = first .. last, taken modulo the window in DECODE
    the rest of the row is padded with 0xffffffff

Both phases are generated, because they differ in exactly one place -- prefill
emits absolute KV rows and decode emits physical slots of the circular window --
and a case set with only one of them would not distinguish the two.
"""

from __future__ import annotations

import argparse
from pathlib import Path

PAD = 0xFFFFFFFF

#: (name, span, slots, window, mask_full, context, decode, positions)
CASES = (
    # The shipped shape's rule at a legible size: window 128 is 2**7, here 8.
    ("prefill_partial", 4, 8, 8, 0, 16, 0, (0, 1, 5, 9)),
    ("prefill_full",    3, 8, 8, 0, 32, 0, (7, 8, 31)),
    ("decode_wrap",     4, 8, 8, 0, 32, 1, (7, 8, 15, 20)),
    # A full mask ignores the query and looks at the whole context.
    ("full_mask",       2, 8, 8, 1, 12, 0, (3, 11)),
)


def expected(span, slots, window, mask_full, context, decode, positions):
    out = []
    candidates = 0
    for row in range(span):
        position = positions[row]
        last = (context - 1) if mask_full else position
        first = max(0, last - window + 1)
        count = last - first + 1
        rows = [(v % window) if decode else v for v in range(first, last + 1)]
        candidates += count
        out.extend(rows + [PAD] * (slots - count))
    return out, candidates


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lines = [str(len(CASES))]
    for index, (name, span, slots, window, mask_full, context, decode,
                positions) in enumerate(CASES):
        out, candidates = expected(span, slots, window, mask_full, context,
                                   decode, positions)
        (args.out / f"pos_{index}.hex").write_text(
            "".join(f"{p:08x}\n" for p in positions), encoding="utf-8")
        (args.out / f"exp_{index}.hex").write_text(
            "".join(f"{v:08x}\n" for v in out), encoding="utf-8")
        lines.append(f"{span} {slots} {window} {mask_full} {context} {decode} "
                     f"{candidates}")
        print(f"  {name:16s} span={span} slots={slots} window={window} "
              f"mask_full={mask_full} context={context} decode={decode} "
              f"candidates={candidates}")
    (args.out / "cases.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
