#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_ordered_sum.sv``, from the reference engine.

Expected words come out of ``runtime.sim.engines.reduction.ordered_sum`` at
SEQUENTIAL_ASCENDING, which is the order every ORDERED_SUM in every shipped
deployment declares, so the RTL is compared against the implementation the
functional device runs.

The first case is the shipped shape -- one term with a base, which is what
deepseek-v4-flash-rom and its array sibling each emit five of.  The rest are the
shapes it does not emit: more terms, no base at all, and the full eight, which
together are what show whether the accumulator chain's inactive stages forward
or add.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import ReductionOrder  # noqa: E402
from runtime.sim.engines.reduction import ordered_sum  # noqa: E402

#: (terms, width, has_base)
CASES: tuple[tuple[int, int, bool], ...] = (
    (1, 8, True),    # the shipped shape
    (1, 4, False),   # one term, no base: the seed is the whole answer
    (2, 8, True),
    (3, 6, False),
    (5, 4, True),
    (8, 4, True),    # the deepest chain this block builds
)

SEED = 20260916


def bf16(values: np.ndarray) -> np.ndarray:
    bits = np.asarray(values, dtype=np.float32).view(np.uint32)
    return (((bits + 0x7FFF + ((bits >> 16) & 1)) >> 16)).astype(np.uint16)


def unbf16(codes: np.ndarray) -> np.ndarray:
    return (np.asarray(codes, dtype=np.uint32) << 16).view(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    order = int(ReductionOrder.SEQUENTIAL_ASCENDING)

    manifest = []
    lines = [f"{len(CASES)}"]
    for index, (terms, width, has_base) in enumerate(CASES):
        values = bf16(rng.normal(0, 1, size=(terms, width)).astype(np.float32))
        base = (bf16(rng.normal(0, 1, size=width).astype(np.float32))
                if has_base else None)
        stack = unbf16(values).astype(np.float32)
        if has_base:
            # The base enters FIRST: it is the accumulator's initial value.
            stack = np.concatenate(
                (unbf16(base).reshape(1, width).astype(np.float32), stack), axis=0
            )
        expected = bf16(ordered_sum(stack, order))

        def write(name: str, words: np.ndarray) -> None:
            (args.out / f"{name}_{index}.hex").write_text(
                "".join(f"{int(word):08x}\n" for word in np.ravel(words)),
                encoding="utf-8",
            )
        write("vals", values)
        write("base", base if base is not None else np.zeros(1, np.uint16))
        write("exp", expected)
        lines.append(f"{terms} {width} {int(has_base)}")
        manifest.append({
            "base": has_base,
            "first_expected": f"{int(expected[0]):04x}",
            "terms": terms,
            "width": width,
        })
    (args.out / "cases.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "cases": manifest,
        "reduction_order": "SEQUENTIAL_ASCENDING",
        "reference": "runtime.sim.engines.reduction.ordered_sum",
        "schema": "opentallas.rtl.a3_ordered_sum_vectors.v1",
        "seed": SEED,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
