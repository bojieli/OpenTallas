#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_expert_sum.sv``, from the reference engine.

The expected words are not written here: they come out of
``runtime.sim.engines.reduction.ordered_sum`` at the reduction order the shipped
descriptors declare, so the testbench compares the RTL against the same
implementation the functional device runs rather than against a second opinion
about what the reduction should be.

The case list covers what deepseek-v41-flash-rom-wafer-2 actually emits -- 4
experts weighted with no base (33 instructions) and 6 with a base and no weights
(16) -- and then the shapes it does not: one expert, the full eight, and odd
counts of five and three, which are what exercise the pairwise tree's odd tail.
Both base placements appear, because they are different numbers: with six leaves
a base folded in as a leaf meets the routed sum at the second level and a base
added afterwards meets the whole of it.
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

#: (experts, width, weights, base, base_after_terms)
CASES: tuple[tuple[int, int, bool, bool, bool], ...] = (
    (4, 8, True, False, False),    # the 33 weighted V4.1 instructions
    (6, 8, False, True, True),     # the 16 with a base, DeepSeek placement
    (6, 8, False, True, False),    # the same shape, base as a leaf
    (1, 4, True, False, False),    # one leaf: every level is a pass-through
    (8, 4, True, True, True),      # the widest tree this block builds
    (5, 6, True, False, False),    # odd at the first level
    (3, 4, False, True, True),     # odd with a trailing base
)

SEED = 20260915


def bf16(values: np.ndarray) -> np.ndarray:
    """Round binary32 to BF16 codes, round-to-nearest-even."""
    bits = np.asarray(values, dtype=np.float32).view(np.uint32)
    return (((bits + 0x7FFF + ((bits >> 16) & 1)) >> 16)).astype(np.uint16)


def unbf16(codes: np.ndarray) -> np.ndarray:
    return (np.asarray(codes, dtype=np.uint32) << 16).view(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True,
                    help="directory to write cases.txt and the hex vectors into")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    order = int(ReductionOrder.PAIRWISE_TREE)

    manifest = []
    lines = [f"{len(CASES)}"]
    for index, (experts, width, has_weights, has_base, after) in enumerate(CASES):
        values = bf16(rng.normal(0, 1, size=(experts, width)).astype(np.float32))
        weights = (bf16(rng.normal(0, 1, size=experts).astype(np.float32))
                   if has_weights else None)
        base = (bf16(rng.normal(0, 1, size=width).astype(np.float32))
                if has_base else None)

        terms = unbf16(values).astype(np.float32)
        if has_weights:
            terms = (terms * unbf16(weights).reshape(experts, 1)).astype(np.float32)
        widened = unbf16(base).astype(np.float32) if has_base else None
        stack = terms
        if has_base and not after:
            stack = np.concatenate((widened.reshape(1, width), terms), axis=0)
        total = ordered_sum(stack, order)
        if has_base and after:
            total = np.add(total, widened, dtype=np.float32)
        expected = bf16(total)

        def write(name: str, words: np.ndarray) -> None:
            (args.out / f"{name}_{index}.hex").write_text(
                "".join(f"{int(word):08x}\n" for word in np.ravel(words)),
                encoding="utf-8",
            )
        write("vals", values)
        write("wts", weights if weights is not None else np.zeros(1, np.uint16))
        write("base", base if base is not None else np.zeros(1, np.uint16))
        write("exp", expected)
        lines.append(f"{experts} {width} {int(has_weights)} {int(has_base)} "
                     f"{int(after)}")
        manifest.append({
            "base": has_base,
            "base_after_terms": after,
            "experts": experts,
            "first_expected": f"{int(expected[0]):04x}",
            "weights": has_weights,
            "width": width,
        })
    (args.out / "cases.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "cases": manifest,
        "reduction_order": "PAIRWISE_TREE",
        "reference": "runtime.sim.engines.reduction.ordered_sum",
        "schema": "opentallas.rtl.a3_expert_sum_vectors.v1",
        "seed": SEED,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
