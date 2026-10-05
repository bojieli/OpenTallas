#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_route_biased_topk.sv``, from the reference itself.

Unlike the other generators in this directory, this one does not transcribe the
rule -- it CALLS it.  ``runtime.sim.engines.route._topk`` needs a live
EngineContext, but the two lines that decide the answer do not:

    keys  = np.add(scores, bias, dtype=np.float32)
    order = np.argsort(-keys, axis=-1, kind="stable")[:, :topk]

so those exact expressions are evaluated here on the same widened BF16 operands
the engine reads.  A stable argsort on the NEGATED key is what makes ties go to
the LOWER expert id, and that is the one property a hand-written expectation
would most plausibly get backwards.

THE WEIGHTS ARE THE UNBIASED SCORES.  ``selected = take_along_axis(scores,
order)`` indexes the scores, not the keys.  Case ``bias_reorders`` exists to make
that non-vacuous: its bias changes which experts win AND the emitted weights
differ from the keys of those same experts, so an engine that wrote the biased
key would fail on it while passing every other case here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import DType   # noqa: E402
from runtime.sim import formats            # noqa: E402


def bf16(values) -> np.ndarray:
    """The BF16 codes of ``values``, round-to-nearest-even, as the store holds."""
    raw = np.asarray(values, dtype=np.float32).view(np.uint32)
    #: RNE on the truncated 16 bits, which is what the exporter does.
    rounded = (raw + 0x7FFF + ((raw >> 16) & 1)) >> 16
    return rounded.astype(np.uint32)


def widen(codes: np.ndarray) -> np.ndarray:
    """The exact float32 value of a BF16 code -- a shift, never a rounding."""
    return (codes.astype(np.uint32) << 16).view(np.float32)


#: THE SHIPPED FRAME IS FP32, which this engine first got wrong.  Read off the
#: descriptor tables at HEAD: every shipped ROUTE.BIASED_TOPK carries FP32
#: scores, an FP32 [experts] bias, U32 selected ids and FP32 selected weights,
#: at 256 experts and k=6 (V4.1: 384 experts, same k).  The BF16 cases stay
#: because the engine admits both operand widths, and the widening is the one
#: place a signed zero can be lost.
#:
#: (name, groups, experts, topk, has_bias, bias_broadcast, weight_fp32,
#:  operand_fp32, seed)
CASES = (
    ("basic",            2,  8, 3, 1, 1, 0, 0, 11),
    ("bias_reorders",    1,  8, 3, 1, 1, 0, 0,  0),   # built explicitly below
    ("tie_lower_id",     1,  8, 4, 1, 1, 0, 0,  0),   # built explicitly below
    ("negatives",        3, 12, 4, 1, 1, 0, 0, 23),
    ("per_group_bias",   3, 12, 4, 1, 0, 0, 0, 29),
    ("k_eq_experts",     2,  6, 6, 1, 1, 0, 0, 31),
    ("no_bias",          2, 10, 4, 0, 0, 0, 0, 37),
    ("weights_fp32",     2, 10, 4, 1, 1, 1, 0, 41),
    #: Minus zero, whose handling differs between the two WEIGHT dtypes. Both
    #: variants select it, so each pins its own dtype's rule.
    ("signed_zero",      1,  4, 2, 0, 0, 0, 0,  0),   # built explicitly below
    ("signed_zero_fp32", 1,  4, 2, 0, 0, 1, 0,  0),   # built explicitly below
    #: The shipped gate's k at a legible expert count; the walk is one expert
    #: per cycle either way, so 32 exercises it exactly as 256 would.
    ("shipped_k6",       4, 32, 6, 1, 1, 0, 0, 43),
    #: THE SHIPPED FRAME ITSELF: FP32 in, FP32 bias, FP32 weights out, k=6.
    ("shipped_fp32",     4, 32, 6, 1, 1, 1, 1, 47),
    ("fp32_negatives",   3, 16, 4, 1, 1, 1, 1, 53),
    ("fp32_per_group",   3, 16, 4, 1, 0, 1, 1, 59),
    ("fp32_no_bias",     2, 12, 4, 0, 0, 1, 1, 61),
    #: An FP32 score whose BF16 narrowing is a REAL rounding, so the weight path
    #: is not the identity it is on every BF16-operand case.
    ("fp32_bf16_out",    2, 12, 4, 1, 1, 0, 1, 67),
    #: A -0 score under FP32 operands: the key must not be turned into +0 by an
    #: identity add, and the FP32 weight must keep the sign.
    ("fp32_signed_zero", 1,  4, 2, 0, 0, 1, 1,  0),   # built explicitly below
)


def operands(name, groups, experts, has_bias, bias_broadcast, operand_fp32,
             seed):
    """The score and bias codes, in whichever width the frame declares."""
    if name == "bias_reorders":
        #: Expert 5 has the lowest score of the three the bias promotes, so the
        #: emitted weight ordering is NOT the key ordering.
        scores = np.array([[0.5, 0.25, 0.75, 0.125, 1.5, 0.0625, 0.375, 0.875]])
        bias = np.array([[0.0, 0.0, 0.0, 0.0, -2.0, 4.0, 0.0, 0.0]])
    elif name.endswith("signed_zero") or name.startswith("signed_zero"):
        #: -0 at index 0 and +0 at index 1 compare EQUAL, so the tie rule puts
        #: -0 first and k=2 selects both. The emitted weights then contain a -0
        #: on the FP32 path and a canonicalised +0 on the BF16 path.
        scores = np.array([[-0.0, 0.0, -1.0, -2.0]])
        bias = np.zeros((1, 4))
    elif name == "tie_lower_id":
        #: Four exact ties at 0.5 and a second pair at 0.25, so the tie rule is
        #: tested both inside the selected set and at its boundary.
        scores = np.array([[0.5, 0.25, 0.5, 0.25, 0.5, 0.125, 0.5, 0.0625]])
        bias = np.zeros((1, 8))
    else:
        rng = np.random.default_rng(seed)
        scores = rng.uniform(-2.0, 2.0, size=(groups, experts))
        bias = rng.uniform(-1.0, 1.0,
                           size=(1 if bias_broadcast else groups, experts))
    if not has_bias:
        bias = np.zeros((1, experts))
    if operand_fp32:
        #: The binary32 code itself, which is what the shipped views carry: no
        #: rounding happens on the way in, unlike the BF16 path.
        return (np.ascontiguousarray(scores, dtype=np.float32).view(np.uint32),
                np.ascontiguousarray(bias, dtype=np.float32).view(np.uint32))
    return bf16(scores), bf16(bias)


def expected(score_codes, bias_codes, topk, has_bias, operand_fp32):
    """The reference's own two lines, on the widened codes."""
    lift = (lambda c: np.ascontiguousarray(c, dtype=np.uint32).view(np.float32)) \
        if operand_fp32 else widen
    scores = lift(score_codes)
    if has_bias:
        bias = lift(bias_codes)
        keys = np.add(scores, bias, dtype=np.float32)
    else:
        keys = scores.copy()
    assert np.all(np.isfinite(keys)), "a case must not need the trap path"
    order = np.argsort(-keys, axis=-1, kind="stable")[:, :topk]
    selected = np.take_along_axis(scores, order, axis=1)
    return order.astype(np.uint32), selected


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lines = [str(len(CASES))]
    reorder_proof = None
    for index, (name, groups, experts, topk, has_bias, bcast, wfp32,
                ofp32, seed) in enumerate(CASES):
        score_codes, bias_codes = operands(name, groups, experts, has_bias,
                                           bcast, ofp32, seed)
        order, selected = expected(score_codes, bias_codes, topk, has_bias,
                                   ofp32)

        if name == "bias_reorders":
            #: Prove the case does what it claims, or the suite is decorative.
            keys = np.add(widen(score_codes), widen(bias_codes),
                          dtype=np.float32)
            sel_keys = np.take_along_axis(keys, order, axis=1)
            unbiased_order = np.argsort(-widen(score_codes), axis=-1,
                                        kind="stable")[:, :topk]
            reorder_proof = {
                "bias_changes_the_selected_set":
                    sorted(order[0].tolist()) != sorted(unbiased_order[0].tolist()),
                "weights_differ_from_keys":
                    not np.array_equal(sel_keys, selected),
            }

        #: One 32-bit word per element: scores and bias as BF16 codes, the ids as
        #: U32, the weights as the store's code (BF16 low half, or FP32).
        (args.out / f"score_{index}.hex").write_text(
            "\n".join(f"{c:08x}" for c in score_codes.reshape(-1)) + "\n")
        (args.out / f"bias_{index}.hex").write_text(
            "\n".join(f"{c:08x}" for c in bias_codes.reshape(-1)) + "\n")
        (args.out / f"expid_{index}.hex").write_text(
            "\n".join(f"{v:08x}" for v in order.reshape(-1)) + "\n")
        #: The narrowing is the REFERENCE's own, not a transcription of it. The
        #: two dtypes disagree on minus zero -- BF16 canonicalises it, FP32 keeps
        #: it -- and calling formats.narrow is the only way to be sure which.
        dtype = int(DType.FP32) if wfp32 else int(DType.BF16)
        narrowed, _ = formats.narrow(dtype, selected)
        array = np.asarray(narrowed)
        codes = array.reshape(-1).view(np.uint32 if wfp32 else np.uint16)
        (args.out / f"expwgt_{index}.hex").write_text(
            "\n".join(f"{int(v):08x}" for v in codes) + "\n")

        lines.append(f"{name} {groups} {experts} {topk} {has_bias} {bcast} "
                     f"{wfp32} {ofp32}")

    (args.out / "cases.txt").write_text("\n".join(lines) + "\n")
    assert reorder_proof and all(reorder_proof.values()), \
        f"the bias_reorders case is vacuous: {reorder_proof}"
    print(f"wrote {len(CASES)} cases to {args.out}")
    print(f"non-vacuity of bias_reorders: {reorder_proof}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
