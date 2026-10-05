#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_balanced_sum.sv``, from the reference itself.

The expectations CALL ``runtime.tensor_accelerator.sparse_attention._balanced_sum``
rather than transcribing it, so the association under test is the one
ATTENTION.SPARSE's softmax denominator actually uses.

THE ASSOCIATION IS THE WHOLE CONTRACT, so most of these cases exist to make a
LEFT FOLD of the same lanes give a DIFFERENT number. ``left_fold_differs`` in the
manifest records, per case, whether it does -- a case where both associations
agree proves nothing about the tree, and the suite refuses to be built if no case
discriminates.

Case ``pad_is_positive_zero`` is the one the reference's own note is about: a
short source block is zero-extended by the caller, which is exact because +0
added to a nonnegative partial leaves it alone. Its twin ``pad_is_negative_zero``
supplies -0 instead and produces the SAME sum -- measured, not assumed, and the
opposite of what one might expect from a block that cares about signed zero
elsewhere. The reason is that every real lane here is nonzero, so the -0 pad only
ever meets a nonzero partial and adding it is exact too. The two pads can differ
only where a partial is EXACTLY zero, since +0 + -0 is +0 while -0 + -0 is -0,
and no case here reaches that; the pair is kept because it bounds the claim to
what was actually checked.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.tensor_accelerator.sparse_attention import _balanced_sum  # noqa: E402

LANES = 64


def left_fold(values: np.ndarray) -> np.float32:
    """Sequential ascending, for the non-vacuity check only."""
    total = np.float32(values[0])
    for v in values[1:]:
        total = np.add(total, np.float32(v), dtype=np.float32)
    return total


def lanes_for(name: str, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if name == "all_ones":
        return np.ones(LANES, dtype=np.float32)
    if name == "one_plus_tiny":
        #: 1.0 followed by 63 ulps-of-1.0. A left fold loses every one of them;
        #: the tree accumulates them in pairs and keeps most.
        v = np.full(LANES, np.float32(np.ldexp(1.0, -24)), dtype=np.float32)
        v[0] = np.float32(1.0)
        return v
    if name == "tiny_then_one":
        v = np.full(LANES, np.float32(np.ldexp(1.0, -24)), dtype=np.float32)
        v[LANES - 1] = np.float32(1.0)
        return v
    if name == "pad_is_positive_zero":
        v = np.zeros(LANES, dtype=np.float32)
        v[:7] = rng.uniform(0.25, 4.0, size=7).astype(np.float32)
        return v
    if name == "pad_is_negative_zero":
        v = np.full(LANES, np.float32(-0.0), dtype=np.float32)
        v[:7] = rng.uniform(0.25, 4.0, size=7).astype(np.float32)
        return v
    if name == "probabilities":
        #: What the softmax actually hands it: exp of non-positive offsets, so
        #: every lane is in (0, 1] and one lane is exactly 1.0 (the row max).
        v = np.exp(-rng.uniform(0.0, 12.0, size=LANES)).astype(np.float32)
        v[rng.integers(LANES)] = np.float32(1.0)
        return v
    if name == "wide_dynamic_range":
        e = rng.integers(-60, 60, size=LANES)
        return np.array([np.ldexp(1.0, int(x)) for x in e], dtype=np.float32)
    return rng.uniform(-8.0, 8.0, size=LANES).astype(np.float32)


CASES = (
    ("all_ones", 0),
    ("one_plus_tiny", 0),
    ("tiny_then_one", 0),
    ("pad_is_positive_zero", 11),
    ("pad_is_negative_zero", 11),
    ("probabilities", 17),
    ("wide_dynamic_range", 23),
    ("signed_mixed", 29),
    ("signed_mixed_b", 31),
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lines = [str(len(CASES))]
    discriminating = 0
    notes = []
    for index, (name, seed) in enumerate(CASES):
        v = lanes_for(name, seed)
        assert v.shape == (LANES,), name
        total = np.float32(_balanced_sum(v.reshape(1, LANES))[0])
        lf = left_fold(v)
        differs = bool(total.view(np.uint32) != lf.view(np.uint32))
        discriminating += int(differs)
        notes.append({"case": name, "left_fold_differs": differs,
                      "tree": float(total), "left_fold": float(lf)})
        (args.out / f"lanes_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in v.view(np.uint32)) + "\n")
        lines.append(f"{name} {int(total.view(np.uint32)):08x}")

    (args.out / "cases.txt").write_text("\n".join(lines) + "\n")
    assert discriminating, ("no case distinguishes the balanced tree from a left "
                            "fold; the suite would pass on the wrong association")
    print(f"wrote {len(CASES)} cases to {args.out}")
    print(f"{discriminating} of {len(CASES)} distinguish the tree from a left fold")
    for n in notes:
        print(f"   {n['case']:24s} differs={str(n['left_fold_differs']):5s} "
              f"tree={n['tree']!r} left={n['left_fold']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
