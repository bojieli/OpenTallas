#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_softmax_block.sv``, from the reference itself.

Every expectation CALLS ``runtime.tensor_accelerator.sparse_attention.exp_cr32``,
the correctly-rounded binary32 exponential that supplies ATTENTION.SPARSE's own
probabilities, so the authority under test is the operator's authority and not a
transcription of it. The maximum, the rescale and the offsets are the reference's
own six lines evaluated on the same codes the RTL reads.

THE FOUR CASES THAT EXIST BECAUSE THEY ARE EASY TO GET WRONG:

``first_block``        rescale must be binary32 +0, not 1.0.
``padding_lanes``      an invalid lane's probability is +0 and its offset never
                       reaches the exponential -- the reference masks it to -inf
                       and ot_a3_fp32_transcendental_cr_rne REFUSES a nonfinite
                       argument, so a block that forwarded the mask would fail
                       closed on padding.
``max_is_negative_zero``  a maximum of -0 is canonicalised to +0 before any
                       offset is formed.
``all_padding_later``  a later block with no valid lane leaves the running
                       maximum alone and every probability at +0.

``score_equals_max`` pins exp(0) == 1.0 exactly, which is the one offset the
exponential sees at the top of its domain.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.tensor_accelerator.sparse_attention import exp_cr32  # noqa: E402

LANES = 64
NEG_ZERO = np.float32(-0.0)


def case_inputs(name: str, seed: int):
    """(first, running_max, valid mask, scores) as float32/bool arrays."""
    rng = np.random.default_rng(seed)
    scores = rng.uniform(-30.0, 5.0, size=LANES).astype(np.float32)
    valid = np.ones(LANES, dtype=bool)
    if name == "first_block":
        return True, np.float32(0.0), valid, scores
    if name == "later_block":
        return False, np.float32(2.5), valid, scores
    if name == "padding_lanes":
        valid[7:] = False
        return False, np.float32(-1.0), valid, scores
    if name == "all_padding_later":
        valid[:] = False
        return False, np.float32(3.25), valid, scores
    if name == "all_padding_negative_running":
        #: A NEGATIVE running maximum, which is the only thing that catches an
        #: implementation that lets an all-padding block overwrite it. With a
        #: positive running maximum, max(+0, running) is running and a block that
        #: wrongly substituted +0 for "no valid lane" gives the right answer
        #: anyway -- every other all-padding case here is masked that way.
        valid[:] = False
        return False, np.float32(-2.5), valid, scores
    if name == "max_is_negative_zero":
        s = np.full(LANES, np.float32(-4.0), dtype=np.float32)
        s[3] = NEG_ZERO
        return True, np.float32(0.0), valid, s
    if name == "score_equals_max":
        s = np.full(LANES, np.float32(-2.0), dtype=np.float32)
        s[0] = np.float32(1.5)
        s[9] = np.float32(1.5)
        return True, np.float32(0.0), valid, s
    if name == "running_max_wins":
        #: Every block score is below the running maximum, so the maximum does
        #: not move and the rescale is exactly exp(0) = 1.0.
        return False, np.float32(6.0), valid, (scores - np.float32(12.0)).astype(np.float32)
    if name == "wide_offsets":
        s = np.linspace(-120.0, 0.0, LANES).astype(np.float32)
        return False, np.float32(0.0), valid, s
    return False, np.float32(1.0), valid, scores


CASES = (
    ("first_block", 11),
    ("later_block", 13),
    ("padding_lanes", 17),
    ("all_padding_later", 19),
    ("all_padding_negative_running", 19),
    ("max_is_negative_zero", 0),
    ("score_equals_max", 0),
    ("running_max_wins", 23),
    ("wide_offsets", 0),
)


def expected(first, running, valid, scores):
    """The reference's own six lines."""
    masked = np.where(valid, scores, np.float32(-np.inf))
    if valid.any():
        block_max = np.float32(masked.max())
    else:
        block_max = np.float32(-np.inf)
    if first:
        updated = np.float32(0.0) if block_max == 0 else block_max
        rescale = np.float32(0.0)
    else:
        updated = np.maximum(running, block_max) if valid.any() else running
        updated = np.float32(0.0) if updated == 0 else np.float32(updated)
        rescale = np.float32(exp_cr32(np.array([running - updated],
                                              dtype=np.float32))[0])
    offsets = np.where(valid, (scores - updated).astype(np.float32),
                       np.float32(-np.inf))
    probs = np.zeros(LANES, dtype=np.float32)
    live = np.flatnonzero(valid)
    if live.size:
        probs[live] = exp_cr32(np.ascontiguousarray(offsets[live]))
    return np.float32(updated), np.float32(rescale), probs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lines = [str(len(CASES))]
    for index, (name, seed) in enumerate(CASES):
        first, running, valid, scores = case_inputs(name, seed)
        updated, rescale, probs = expected(first, running, valid, scores)
        assert np.all(np.isfinite(probs)), name
        #: Every offset the RTL hands the exponential must be non-positive, or
        #: the unit refuses it -- checked here so the case set cannot contain one.
        for i in np.flatnonzero(valid):
            assert np.float32(scores[i]) - updated <= 0, (name, i)
        if not first:
            assert running - updated <= 0, name

        (args.out / f"scores_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in scores.view(np.uint32)) + "\n")
        (args.out / f"probs_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in probs.view(np.uint32)) + "\n")
        mask = "".join("1" if v else "0" for v in valid[::-1])
        lines.append(f"{name} {int(first)} {int(running.view(np.uint32)):08x} "
                     f"{int(updated.view(np.uint32)):08x} "
                     f"{int(rescale.view(np.uint32)):08x} {mask}")

    (args.out / "cases.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(CASES)} cases to {args.out}")
    for index, (name, seed) in enumerate(CASES):
        first, running, valid, scores = case_inputs(name, seed)
        u, r, p = expected(first, running, valid, scores)
        print(f"   {name:22s} first={int(first)} max={float(u):>12.6g} "
              f"rescale={float(r):>12.6g} valid={int(valid.sum()):2d} "
              f"probs[0]={float(p[0]):.6g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
