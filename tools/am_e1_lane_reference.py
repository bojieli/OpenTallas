#!/usr/bin/env python3
"""The AM-E1 lane association, as an exact Python reference.

This is the numeric oracle for the group modes of the pipelined contraction
lane (``rtl/abi3/ot_a3_lane_pipelined.sv``; ``docs/CHIP_ARCHITECTURE_DESIGN.md``
section 4.3, association AM-E1).  For one output element and one K-block the
lane computes, in ascending k, in groups of g:

    acc <- RNE32(acc + sum_{j < g} p_j)        p_j = a_{k+j} * w_{k+j}, exact

with the accumulator starting at +0.0, every product exact, the g products of
a group summed exactly, and one binary32 round-to-nearest-even per group.  For
g = 1 the product itself is first rounded to binary32 (which can only act in
the subnormal range) and canonicalised to +0.0 when exactly zero, which makes
g = 1 exactly ``bf16_bf16_fp32_sequential_rne_v1`` restricted to the block --
the contract ``runtime/sim/backend.py::sequential_matmul_binary32`` executes
and ``rtl/abi3/ot_a3_mac_lane.sv`` transcribes.

Authorities, and how each is used:

* ``runtime/reference/formats.py`` decodes every storage code exactly
  (``fractions.Fraction``) and provides ``encode_binary32_rne``, the exact
  rational-to-binary32 rounding.  Every product and every group sum here is a
  ``Fraction``; the accumulate is ``encode_binary32_rne(acc + S)``: one
  rounding of the exact sum.  (Rounding the exact sum through a host float64
  first would be two roundings and is not done; where the exact sum happens to
  be representable in float64 the result is additionally checked against
  ``np.float32`` so the model is pinned to numpy's binary32 RNE.)
* ``runtime/sim/engines/tensor.py::_operand`` applies an E8M0 block scale as
  ``np.multiply(value, scale, dtype=np.float32)``; the same call is made here,
  so a scaled operand that lands in the binary32 subnormal range is rounded to
  that grid exactly as the functional simulator rounds it, and one that leaves
  binary32 is refused.
* The fault classes are the sequential lane's (``rtl/abi3/ot_a3_engine_pkg.sv``);
  the fault *details* are the pipelined lane's (``rtl/abi3/ot_a3_lane_pkg.sv``),
  one per failure mode, with the same priority order the RTL applies inside a
  group: a nonfinite or reserved operand (a before b, ascending j), then a
  reserved scale (a before b), then a scale application leaving binary32
  (a before b, ascending j), then a product leaving binary32, then an
  accumulation leaving it.

Nothing here is a model of the pipeline: the schedule helpers at the bottom
only derive which output elements each lane has written when it stops on a
fault, from the order in which each lane visits its work.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import DType  # noqa: E402
from runtime.reference import formats as exact  # noqa: E402

# -- fault details, transcribed from rtl/abi3/ot_a3_lane_pkg.sv ----------------
DETAIL_NONE = 0
DETAIL_A_NONFINITE = 1
DETAIL_B_NONFINITE = 2
DETAIL_A_RESERVED = 3
DETAIL_B_RESERVED = 4
DETAIL_SCALE_A_RESERVED = 5
DETAIL_SCALE_B_RESERVED = 6
DETAIL_SCALE_A_RANGE = 7
DETAIL_SCALE_B_RANGE = 8
DETAIL_PRODUCT_RANGE = 9
DETAIL_ACCUMULATE_RANGE = 10
DETAIL_SHAPE = 11
DETAIL_ALIGNER = 12

DETAIL_NAMES = {
    DETAIL_NONE: "none",
    DETAIL_A_NONFINITE: "operand_a_nonfinite_bf16",
    DETAIL_B_NONFINITE: "operand_b_nonfinite_bf16",
    DETAIL_A_RESERVED: "operand_a_reserved_e4m3fn",
    DETAIL_B_RESERVED: "operand_b_reserved_e4m3fn",
    DETAIL_SCALE_A_RESERVED: "scale_a_reserved_e8m0",
    DETAIL_SCALE_B_RESERVED: "scale_b_reserved_e8m0",
    DETAIL_SCALE_A_RANGE: "scale_a_application_range",
    DETAIL_SCALE_B_RANGE: "scale_b_application_range",
    DETAIL_PRODUCT_RANGE: "product_range",
    DETAIL_ACCUMULATE_RANGE: "accumulate_range",
    DETAIL_SHAPE: "shape",
    DETAIL_ALIGNER: "aligner",
}

# -- error classes, transcribed from rtl/abi3/ot_a3_engine_pkg.sv ---------------
ERR_NONE = 0
ERR_OPERAND_NONFINITE = 1
ERR_PRODUCT_RANGE = 2
ERR_ACCUMULATE_RANGE = 3
ERR_SCALE_RANGE = 6
ERR_SHAPE = 7


def error_code_of_detail(detail: int) -> int:
    if detail == DETAIL_NONE:
        return ERR_NONE
    if detail in (DETAIL_A_NONFINITE, DETAIL_B_NONFINITE, DETAIL_A_RESERVED,
                  DETAIL_B_RESERVED, DETAIL_SCALE_A_RESERVED,
                  DETAIL_SCALE_B_RESERVED):
        return ERR_OPERAND_NONFINITE
    if detail in (DETAIL_SCALE_A_RANGE, DETAIL_SCALE_B_RANGE):
        return ERR_SCALE_RANGE
    if detail == DETAIL_PRODUCT_RANGE:
        return ERR_PRODUCT_RANGE
    if detail == DETAIL_ACCUMULATE_RANGE:
        return ERR_ACCUMULATE_RANGE
    return ERR_SHAPE


SUPPORTED_FORMATS = (int(DType.BF16), int(DType.FP8_E4M3FN), int(DType.MXFP4_E2M1))
BLOCK_FORMATS = (int(DType.FP8_E4M3FN), int(DType.MXFP4_E2M1))


def element_width(dtype: int) -> int:
    return {int(DType.BF16): 16, int(DType.FP8_E4M3FN): 8, int(DType.MXFP4_E2M1): 4}[int(dtype)]


# -- exact decode tables ------------------------------------------------------
_DECODE_CACHE: dict[int, tuple[Fraction | None, ...]] = {}


def _decode_table(dtype: int) -> tuple[Fraction | None, ...]:
    dtype = int(dtype)
    table = _DECODE_CACHE.get(dtype)
    if table is not None:
        return table
    if dtype == int(DType.BF16):
        decoder, count = exact.decode_bf16, 1 << 16
    elif dtype == int(DType.FP8_E4M3FN):
        decoder, count = exact.decode_e4m3fn, 1 << 8
    elif dtype == int(DType.MXFP4_E2M1):
        decoder, count = exact.decode_e2m1, 1 << 4
    else:
        raise ValueError(f"unsupported storage format {dtype:#x}")
    entries: list[Fraction | None] = []
    for code in range(count):
        decoded = decoder(code)
        entries.append(decoded.value if decoded.finite else None)
    table = tuple(entries)
    _DECODE_CACHE[dtype] = table
    return table


def decode_code(dtype: int, code: int) -> Fraction | None:
    """Exact value of one storage code, or None for NaN / infinity / reserved."""
    return _decode_table(dtype)[int(code)]


def scale_of_code(code: int) -> Fraction | None:
    """Exact E8M0 scale, or None for the reserved code 0xff."""
    decoded = exact.decode_e8m0(int(code))
    return decoded.value if decoded.finite else None


_F32_CACHE: dict[Fraction, np.float32] = {}


def _as_float32(value: Fraction) -> np.float32:
    """A value every supported format decodes to is exact in binary32."""
    cached = _F32_CACHE.get(value)
    if cached is None:
        cached = np.float32(float(value))
        if Fraction(float(cached)) != value:
            raise RuntimeError(f"{value} is not exact in binary32")
        _F32_CACHE[value] = cached
    return cached


def fold_scale(value: Fraction, scale: Fraction) -> Fraction | None:
    """Apply a block scale with np.float32 semantics; None if it leaves binary32.

    ``runtime/sim/engines/tensor.py::_operand`` computes
    ``np.multiply(values, scales, dtype=np.float32)``; this is that call on one
    element.  The product of an exact binary32 value and a power of two is
    exact unless it falls below the binary32 subnormal grid (rounded, ties to
    even, by the float32 multiply) or above 2**128 (infinite: refused).
    """
    if value == 0:
        return Fraction(0)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        scaled = np.multiply(_as_float32(value), _as_float32(scale), dtype=np.float32)
    if not np.isfinite(scaled):
        return None
    return Fraction(float(scaled))


def round_binary32(value: Fraction) -> tuple[bool, Fraction]:
    """One binary32 RNE of an exact value: (overflowed, rounded value)."""
    try:
        code = exact.encode_binary32_rne(value)
    except exact.NumericReferenceError:
        return True, Fraction(0)
    decoded = exact.decode_binary32(code)
    assert decoded.value is not None
    return False, decoded.value


def binary32_code(value: Fraction) -> int:
    return exact.encode_binary32_rne(value)


def scale_index(row: int, column: int, depth: int, block: int, block_rows: int) -> int:
    """Amendment A15's E8M0 code index; identical to both lanes' function."""
    rows_per_block = block_rows if block_rows else 1
    elements_per_block = block if block else 1
    return (row // rows_per_block) * (depth // elements_per_block) + column // elements_per_block


# -- one element's chain --------------------------------------------------------
@dataclass(frozen=True)
class ElementResult:
    """One output element under AM-E1.

    ``acc_code`` is the finished binary32 accumulator when ``detail`` is
    DETAIL_NONE; otherwise ``fault_group`` is the k-group index at which the
    chain stopped (``fault_k`` its first k) and ``acc_code`` the accumulator
    before that group.
    """
    acc_code: int
    detail: int
    fault_group: int
    fault_k: int
    groups_completed: int


@dataclass(frozen=True)
class LaneCase:
    rows: int
    cols: int
    depth: int
    dtype_a: int
    dtype_b: int
    group: int
    a_codes: np.ndarray          # [rows, depth] storage codes
    b_codes: np.ndarray          # [cols, depth] storage codes
    scales_a: np.ndarray | None  # E8M0 codes, A15 order, or None
    scales_b: np.ndarray | None
    block_a: int
    block_b: int
    block_rows_a: int
    block_rows_b: int
    out_fp32: bool

    def k_groups(self) -> int:
        return (self.depth + self.group - 1) // self.group


def shape_admissible(case: LaneCase) -> bool:
    """The pipelined lane's start-time admission, transcribed from the RTL."""
    if case.rows == 0 or case.cols == 0 or case.depth == 0:
        return False
    if case.dtype_a not in SUPPORTED_FORMATS or case.dtype_b not in SUPPORTED_FORMATS:
        return False
    if case.group not in (1, 2, 4):
        return False
    if case.group != 1 and (case.dtype_a == int(DType.BF16) or case.dtype_b == int(DType.BF16)):
        return False
    if case.group == 4 and int(DType.MXFP4_E2M1) not in (case.dtype_a, case.dtype_b):
        return False
    for enabled, block in ((case.scales_a is not None, case.block_a),
                           (case.scales_b is not None, case.block_b)):
        if enabled and (block == 0 or block % case.group != 0 or case.depth % block != 0):
            return False
    return True


def element_chain(case: LaneCase, row: int, col: int) -> ElementResult:
    """Run one output element's K chain under AM-E1."""
    g = case.group
    depth = case.depth
    table_a = _decode_table(case.dtype_a)
    table_b = _decode_table(case.dtype_b)
    a_row = case.a_codes[row]
    b_col = case.b_codes[col]
    acc = Fraction(0)
    acc_code = 0
    groups = case.k_groups()
    for kg in range(groups):
        k0 = kg * g
        count = min(g, depth - k0)
        detail = DETAIL_NONE
        values_a: list[Fraction] = []
        values_b: list[Fraction] = []
        # operands, a before b, ascending j
        for j in range(count):
            va = table_a[int(a_row[k0 + j])]
            vb = table_b[int(b_col[k0 + j])]
            if va is None and detail == DETAIL_NONE:
                detail = (DETAIL_A_NONFINITE if case.dtype_a == int(DType.BF16)
                          else DETAIL_A_RESERVED)
            if vb is None and detail == DETAIL_NONE:
                detail = (DETAIL_B_NONFINITE if case.dtype_b == int(DType.BF16)
                          else DETAIL_B_RESERVED)
            values_a.append(va if va is not None else Fraction(0))
            values_b.append(vb if vb is not None else Fraction(0))
        # scales: reserved codes
        scale_a = scale_b = None
        if detail == DETAIL_NONE and case.scales_a is not None:
            code = int(case.scales_a[scale_index(row, k0, depth, case.block_a, case.block_rows_a)])
            scale_a = scale_of_code(code)
            if scale_a is None:
                detail = DETAIL_SCALE_A_RESERVED
        if detail == DETAIL_NONE and case.scales_b is not None:
            code = int(case.scales_b[scale_index(col, k0, depth, case.block_b, case.block_rows_b)])
            scale_b = scale_of_code(code)
            if scale_b is None:
                detail = DETAIL_SCALE_B_RESERVED
        # scale application, a before b, ascending j
        if detail == DETAIL_NONE:
            for j in range(count):
                if scale_a is not None:
                    folded = fold_scale(values_a[j], scale_a)
                    if folded is None:
                        detail = DETAIL_SCALE_A_RANGE
                        break
                    values_a[j] = folded
                if scale_b is not None:
                    folded = fold_scale(values_b[j], scale_b)
                    if folded is None:
                        detail = DETAIL_SCALE_B_RANGE
                        break
                    values_b[j] = folded
        # products
        group_sum = Fraction(0)
        if detail == DETAIL_NONE:
            for j in range(count):
                product = values_a[j] * values_b[j]
                if g == 1:
                    overflow, product = round_binary32(product)
                else:
                    overflow, _ = round_binary32(product)
                if overflow:
                    detail = DETAIL_PRODUCT_RANGE
                    break
                group_sum += product
        # accumulate: one rounding of the exact sum
        if detail == DETAIL_NONE:
            total = acc + group_sum
            try:
                new_code = exact.encode_binary32_rne(total)
            except exact.NumericReferenceError:
                detail = DETAIL_ACCUMULATE_RANGE
            else:
                # Pin to np.float32 where float64 holds the exact sum: then
                # np.float32(float(total)) is one rounding of the same value.
                as_double = float(total)
                if Fraction(as_double) == total:
                    with np.errstate(over="ignore", under="ignore"):
                        via_numpy = np.float32(as_double)
                    if not np.isfinite(via_numpy) or int(via_numpy.view(np.uint32)) != (
                            new_code if new_code & 0x7FFFFFFF else 0):
                        # np.float32 keeps -0.0; the contract canonicalises.
                        if not (new_code == 0 and float(via_numpy) == 0.0):
                            raise RuntimeError(
                                f"exact binary32 RNE {new_code:#010x} disagrees with "
                                f"np.float32 {int(via_numpy.view(np.uint32)):#010x}"
                            )
                acc_code = new_code
                acc = exact.decode_binary32(new_code).value or Fraction(0)
        if detail != DETAIL_NONE:
            return ElementResult(acc_code, detail, kg, k0, kg)
    return ElementResult(acc_code, DETAIL_NONE, -1, -1, groups)


def narrow_output(acc_code: int, out_fp32: bool) -> tuple[int, bool]:
    """The output word and whether it saturated."""
    if out_fp32:
        return acc_code, False
    narrowed = exact.binary32_bits_to_bf16_rne(acc_code)
    return int(narrowed.code), bool(narrowed.saturated)


@dataclass(frozen=True)
class CaseResult:
    elements: list[ElementResult]   # row-major
    out_words: list[int]
    acc_words: list[int]
    saturated: list[bool]


def evaluate(case: LaneCase) -> CaseResult:
    elements: list[ElementResult] = []
    out_words: list[int] = []
    acc_words: list[int] = []
    saturated: list[bool] = []
    for row in range(case.rows):
        for col in range(case.cols):
            result = element_chain(case, row, col)
            elements.append(result)
            if result.detail == DETAIL_NONE:
                word, sat = narrow_output(result.acc_code, case.out_fp32)
            else:
                word, sat = 0, False
            out_words.append(word)
            acc_words.append(result.acc_code)
            saturated.append(sat)
    return CaseResult(elements, out_words, acc_words, saturated)


# -- the two lanes' schedules ---------------------------------------------------
@dataclass(frozen=True)
class Observable:
    error_code: int
    error_detail: int
    out_count: int
    saturations: int
    lane_ops: int
    products: int
    written: int      # leading row-major elements written


def pipelined_observable(case: LaneCase, result: CaseResult, adder_stages: int) -> Observable:
    """What the pipelined lane reports and writes for this case.

    The lane visits (row, pass of L columns, k-group, column within the pass)
    in that lexicographic order and commits faults in that order, so the first
    faulting lane-op in it decides everything: every pass before it is written,
    nothing from it on is, and the counters hold the lane-ops retired before it.
    """
    if not shape_admissible(case):
        return Observable(ERR_SHAPE, DETAIL_SHAPE, 0, 0, 0, 0, 0)
    L = adder_stages
    rows, cols, depth, g = case.rows, case.cols, case.depth, case.group
    groups = case.k_groups()
    tail = depth - (groups - 1) * g

    def n_active(pass_index: int) -> int:
        return min(L, cols - pass_index * L)

    fault_key = None
    fault_detail = DETAIL_NONE
    for index, element in enumerate(result.elements):
        if element.detail == DETAIL_NONE:
            continue
        row, col = divmod(index, cols)
        key = (row, col // L, element.fault_group, col % L)
        if fault_key is None or key < fault_key:
            fault_key = key
            fault_detail = element.detail
    if fault_key is None:
        written = rows * cols
        return Observable(
            ERR_NONE, DETAIL_NONE, written, sum(result.saturated),
            rows * cols * groups, rows * cols * depth, written,
        )
    row_f, pass_f, kg_f, i_f = fault_key
    written = row_f * cols + pass_f * L
    lane_ops = row_f * cols * groups
    products = row_f * cols * depth
    for pass_index in range(pass_f):
        lane_ops += n_active(pass_index) * groups
        products += n_active(pass_index) * depth
    active = n_active(pass_f)
    if kg_f < groups - 1:
        lane_ops += kg_f * active + i_f
        products += (kg_f * active + i_f) * g
    else:
        lane_ops += (groups - 1) * active + i_f
        products += (groups - 1) * active * g + i_f * tail
    return Observable(
        error_code_of_detail(fault_detail), fault_detail, written,
        sum(result.saturated[:written]), lane_ops, products, written,
    )


def sequential_observable(case: LaneCase, result: CaseResult) -> Observable:
    """What the sequential reference lane reports and writes (g = 1 only).

    It walks (row, column, k) and stops at the first fault, so every element
    before the faulting one is written and its mac_count holds the products of
    the written elements plus those of the faulting element before its fault.
    """
    if case.group != 1:
        raise ValueError("the sequential lane is a g = 1 reference")
    if case.rows == 0 or case.cols == 0 or case.depth == 0:
        return Observable(ERR_SHAPE, DETAIL_SHAPE, 0, 0, 0, 0, 0)
    for index, element in enumerate(result.elements):
        if element.detail != DETAIL_NONE:
            written = index
            macs = written * case.depth + element.fault_k
            return Observable(
                error_code_of_detail(element.detail), element.detail, written,
                sum(result.saturated[:written]), macs, macs, written,
            )
    written = case.rows * case.cols
    macs = written * case.depth
    return Observable(ERR_NONE, DETAIL_NONE, written, sum(result.saturated), macs, macs, written)


# -- the sequential association on a group case, for distinguishing tests -------
def sequential_chain_acc(case: LaneCase, row: int, col: int) -> int | None:
    """The same element under per-product rounding (g = 1 semantics).

    Used by the vector builder to prove that a directed group case actually
    distinguishes AM-E1 from the sequential association; None on any fault.
    """
    single = LaneCase(
        rows=case.rows, cols=case.cols, depth=case.depth, dtype_a=case.dtype_a,
        dtype_b=case.dtype_b, group=1, a_codes=case.a_codes, b_codes=case.b_codes,
        scales_a=case.scales_a, scales_b=case.scales_b, block_a=case.block_a,
        block_b=case.block_b, block_rows_a=case.block_rows_a,
        block_rows_b=case.block_rows_b, out_fp32=case.out_fp32,
    )
    result = element_chain(single, row, col)
    return result.acc_code if result.detail == DETAIL_NONE else None


# ---------------------------------------------------------------------------
# The K-block tree (docs/CHIP_ARCHITECTURE_DESIGN.md section 4.3, items 1-2)
# ---------------------------------------------------------------------------
# Everything above is one output element's chain over one K range.  Under the
# adopted association the chain is run per K-block of KBLOCK elements (item 1)
# and the block partials are combined by ``ReductionOrder.PAIRWISE_TREE`` over
# ascending block index (item 2), exactly as
# ``runtime/sim/engines/reduction.py::ordered_sum`` folds them:
#
#     while more than one node: fold adjacent pairs (2i, 2i+1) with one
#     binary32 RNE add each; an odd tail is carried unchanged.
#
# ``pairwise_tree`` is the exact-Fraction transcription of that recurrence and
# is asserted, code for code, against ``reduction.ordered_sum`` on numpy
# float32 leaves (``self_check``).  ``re8_chain`` is the hardware's reading of
# the same recurrence -- three consecutive levels over one aligned group of at
# most ``leaves`` nodes, one endpoint (rtl/abi3/ot_a3_tree_endpoint_fp32.sv)
# per group, endpoints chained stage by stage -- and is asserted equal to
# ``pairwise_tree`` on every call.  Neither models timing.
#
# Signed zero: no lane partial is ever -0.0 (the chain starts at +0.0 and every
# rounding canonicalises an exact zero), and the RTL endpoint canonicalises a
# -0.0 leaf at its input; the reference refuses one rather than model either
# numpy's (-0)+(-0) = -0 or the RTL's +0, because the disagreement never
# arises inside the tile + tree contract.

KBLOCK = 128

# RE8 fault details (rtl/abi3/ot_a3_tree_endpoint_fp32.sv); the classes are
# the lane's (ERR_OPERAND_NONFINITE, ERR_ACCUMULATE_RANGE, ERR_SHAPE).
DETAIL_TREE_LEAF_NONFINITE = 24
DETAIL_TREE_ADD_RANGE = 25
DETAIL_TREE_LEAF_COUNT = 26
DETAIL_NAMES[DETAIL_TREE_LEAF_NONFINITE] = "tree_leaf_nonfinite"
DETAIL_NAMES[DETAIL_TREE_ADD_RANGE] = "tree_add_range"
DETAIL_NAMES[DETAIL_TREE_LEAF_COUNT] = "tree_leaf_count"


def tree_error_code_of_detail(detail: int) -> int:
    if detail == DETAIL_TREE_LEAF_NONFINITE:
        return ERR_OPERAND_NONFINITE
    if detail == DETAIL_TREE_ADD_RANGE:
        return ERR_ACCUMULATE_RANGE
    if detail == DETAIL_TREE_LEAF_COUNT:
        return ERR_SHAPE
    return error_code_of_detail(detail)


class TreeFault(Exception):
    """A tree fault: ``detail`` (a DETAIL_TREE_* code), the level (1-based
    inside an endpoint, 0 for a leaf fault) and the node index at that level."""

    def __init__(self, detail: int, level: int, index: int) -> None:
        super().__init__(f"{DETAIL_NAMES.get(detail, detail)} at level {level} node {index}")
        self.detail = detail
        self.level = level
        self.index = index


def binary32_value(code: int) -> Fraction:
    """Exact value of a finite binary32 code; a NaN / infinity or -0.0 is refused."""
    code = int(code) & 0xFFFFFFFF
    if (code >> 23) & 0xFF == 0xFF:
        raise TreeFault(DETAIL_TREE_LEAF_NONFINITE, 0, 0)
    if code == 0x80000000:
        raise ValueError("a -0.0 leaf never arises under AM-E1; the reference refuses it")
    decoded = exact.decode_binary32(code)
    assert decoded.value is not None
    return decoded.value


def add_binary32_rne(left: int, right: int, level: int = 0, index: int = 0) -> int:
    """One binary32 RNE add of two finite codes: the exact sum rounded once.

    Where float64 holds the exact sum the result is additionally pinned to
    ``np.add(..., dtype=np.float32)``, so the model is numpy's binary32 RNE.
    A rounded result at or above 2**128 is ``TreeFault(DETAIL_TREE_ADD_RANGE)``.
    """
    total = binary32_value(left) + binary32_value(right)
    try:
        code = exact.encode_binary32_rne(total)
    except exact.NumericReferenceError as error:
        raise TreeFault(DETAIL_TREE_ADD_RANGE, level, index) from error
    as_double = float(total)
    if Fraction(as_double) == total:
        with np.errstate(over="ignore", under="ignore"):
            via_numpy = np.add(np.uint32(left).view(np.float32), np.uint32(right).view(np.float32),
                               dtype=np.float32)
        numpy_code = int(np.float32(via_numpy).view(np.uint32))
        if numpy_code == 0x80000000:
            numpy_code = 0
        if not np.isfinite(via_numpy) or numpy_code != code:
            raise RuntimeError(f"exact binary32 RNE {code:#010x} disagrees with np.add "
                               f"{numpy_code:#010x} for {left:#010x} + {right:#010x}")
    return code


def pairwise_tree_levels(codes: list[int]) -> list[list[int]]:
    """Every level of the PAIRWISE_TREE recurrence, leaves first, root last."""
    if not codes:
        raise TreeFault(DETAIL_TREE_LEAF_COUNT, 0, 0)
    current = [int(c) & 0xFFFFFFFF for c in codes]
    for code in current:
        binary32_value(code)
    levels = [list(current)]
    level = 0
    while len(current) > 1:
        level += 1
        half = len(current) // 2
        folded = [add_binary32_rne(current[2 * i], current[2 * i + 1], level, i) for i in range(half)]
        if len(current) % 2:
            folded.append(current[-1])          # the odd tail is carried, not added
        current = folded
        levels.append(list(current))
    return levels


def pairwise_tree(codes: list[int]) -> int:
    """``reduction.ordered_sum(leaves, PAIRWISE_TREE)`` on binary32 codes, exactly."""
    return pairwise_tree_levels(codes)[-1][0]


def re8_combine(codes: list[int], leaves: int = 8) -> tuple[int, list[list[int]], int]:
    """One endpoint: three levels of the recurrence over m <= ``leaves`` nodes.

    Returns (root code, [level-1 nodes, level-2 nodes, level-3 nodes], adds).
    With m = 1 the leaf passes through unchanged; a level with an odd count
    carries its last node.  ``adds`` is m - 1, the number of binary32 adds
    the endpoint performs.
    """
    count = len(codes)
    if count < 1 or count > leaves:
        raise TreeFault(DETAIL_TREE_LEAF_COUNT, 0, count)
    depth = (leaves - 1).bit_length()
    current = [int(c) & 0xFFFFFFFF for c in codes]
    for code in current:
        binary32_value(code)
    stages: list[list[int]] = []
    adds = 0
    for level in range(1, depth + 1):
        half = len(current) // 2
        folded = [add_binary32_rne(current[2 * i], current[2 * i + 1], level, i) for i in range(half)]
        adds += half
        if len(current) % 2:
            folded.append(current[-1])
        current = folded
        stages.append(list(current))
    assert len(current) == 1
    assert adds == count - 1
    return current[0], stages, adds


def re8_chain(codes: list[int], leaves: int = 8) -> tuple[int, list[dict[str, Any]]]:
    """The chained-endpoint reading of the tree, asserted equal to ``pairwise_tree``.

    Stage s takes the nodes of the previous stage in order, splits them into
    aligned groups of ``leaves``, runs one endpoint per group, and the endpoint
    outputs in ascending group index are the next stage's nodes; the chain
    stops at one node.  Returns (root, stages), each stage a dict with the
    groups' inputs, outputs and add counts.
    """
    nodes = [int(c) & 0xFFFFFFFF for c in codes]
    if not nodes:
        raise TreeFault(DETAIL_TREE_LEAF_COUNT, 0, 0)
    stages: list[dict[str, Any]] = []
    while len(nodes) > 1:
        groups = [nodes[g:g + leaves] for g in range(0, len(nodes), leaves)]
        outputs: list[int] = []
        adds: list[int] = []
        inner: list[list[list[int]]] = []
        for group in groups:
            root, levels, count = re8_combine(group, leaves)
            outputs.append(root)
            adds.append(count)
            inner.append(levels)
        stages.append({"inputs": groups, "outputs": outputs, "adds": adds, "levels": inner})
        nodes = outputs
    root = nodes[0]
    flat = pairwise_tree(codes)
    if root != flat:
        raise RuntimeError(f"re8_chain {root:#010x} differs from pairwise_tree {flat:#010x}")
    return root, stages


def block_case(case: LaneCase, block: int, kblock: int = KBLOCK) -> LaneCase:
    """The case restricted to K-block ``block``: k in [kblock * block, +kblock).

    The scale tables are sliced to the block in amendment A15's order, so the
    lane's own scale_index over the block's depth reads the same codes the
    full-K index reads for those k.
    """
    k0 = block * kblock
    k1 = min(case.depth, k0 + kblock)
    if k0 >= case.depth:
        raise ValueError(f"block {block} is beyond K = {case.depth}")
    depth = k1 - k0

    def slice_scales(scales, rows: int, block_elements: int, block_rows: int):
        if scales is None:
            return None
        if block_elements == 0 or case.depth % block_elements or kblock % block_elements or depth % block_elements:
            return scales          # inadmissible; the lane refuses it, the slice is moot
        rpb = block_rows if block_rows else 1
        row_blocks = (rows + rpb - 1) // rpb
        per_row_full = case.depth // block_elements
        per_row_block = depth // block_elements
        first = k0 // block_elements
        out = np.zeros((row_blocks * per_row_block,), dtype=np.uint8)
        for rb in range(row_blocks):
            for kb in range(per_row_block):
                out[rb * per_row_block + kb] = scales[rb * per_row_full + first + kb]
        return out

    return LaneCase(
        rows=case.rows, cols=case.cols, depth=depth, dtype_a=case.dtype_a, dtype_b=case.dtype_b,
        group=case.group,
        a_codes=np.ascontiguousarray(case.a_codes[:, k0:k1]),
        b_codes=np.ascontiguousarray(case.b_codes[:, k0:k1]),
        scales_a=slice_scales(case.scales_a, case.rows, case.block_a, case.block_rows_a),
        scales_b=slice_scales(case.scales_b, case.cols, case.block_b, case.block_rows_b),
        block_a=case.block_a, block_b=case.block_b, block_rows_a=case.block_rows_a,
        block_rows_b=case.block_rows_b, out_fp32=True,
    )


def block_count(depth: int, kblock: int = KBLOCK) -> int:
    return (depth + kblock - 1) // kblock


def block_chains(case: LaneCase, row: int, col: int, kblock: int = KBLOCK) -> list[ElementResult]:
    """One element's chain per K-block, in ascending block index (item 1)."""
    return [element_chain(block_case(case, b, kblock), row, col)
            for b in range(block_count(case.depth, kblock))]


def block_partials(case: LaneCase, row: int, col: int, kblock: int = KBLOCK) -> list[int]:
    """The binary32 block partials P_0 .. P_{B-1} of one element; every block must complete."""
    partials: list[int] = []
    for b, result in enumerate(block_chains(case, row, col, kblock)):
        if result.detail != DETAIL_NONE:
            raise RuntimeError(f"block {b} of element ({row}, {col}) faults with "
                               f"{DETAIL_NAMES.get(result.detail, result.detail)}")
        partials.append(result.acc_code)
    return partials


def tile_output(root_code: int, out_fp32: bool) -> tuple[int, bool]:
    """Item 4: one rounding of the tree's root into the output dtype."""
    return narrow_output(root_code, out_fp32)


def tile_element(case: LaneCase, row: int, col: int, kblock: int = KBLOCK,
                 leaves: int = 8) -> tuple[int, int, bool]:
    """The whole tile + tree contract for one element: (root, output word, saturated)."""
    root, _stages = re8_chain(block_partials(case, row, col, kblock), leaves)
    word, saturated = tile_output(root, case.out_fp32)
    return root, word, saturated


def self_check(trials: int = 40, max_leaves: int = 256, seed: int = 20260905) -> dict[str, int]:
    """pairwise_tree and re8_chain against reduction.ordered_sum on random float32 leaves."""
    from runtime.abi3.constants import ReductionOrder  # noqa: E402
    from runtime.sim.engines import reduction  # noqa: E402

    rng = np.random.default_rng(seed)
    compared = 0
    mismatches = 0
    for count in range(1, max_leaves + 1):
        for _trial in range(trials):
            exponents = rng.integers(-140, 101, size=count)
            mantissas = rng.random(count) + 1.0
            signs = rng.choice([-1.0, 1.0], size=count)
            values = (signs * mantissas * np.exp2(exponents.astype(np.float64))).astype(np.float32)
            zeros = rng.random(count) < 0.05
            values[zeros] = np.float32(0.0)            # +0.0 only: no leaf is ever -0.0
            leaves = [int(v) for v in values.view(np.uint32)]
            with np.errstate(over="raise", invalid="raise"):
                expected = reduction.ordered_sum(values.reshape(count, 1),
                                                 int(ReductionOrder.PAIRWISE_TREE))
            expected_code = int(np.float32(expected[0]).view(np.uint32))
            if expected_code == 0x80000000:
                expected_code = 0
            got = pairwise_tree(leaves)
            chained, _stages = re8_chain(leaves, 8)
            compared += 1
            if got != expected_code or chained != expected_code:
                mismatches += 1
    return {"compared": compared, "mismatches": mismatches, "max_leaves": max_leaves,
            "trials_per_count": trials}


def _main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="self-check the K-block tree reference")
    parser.add_argument("--trials", type=int, default=40)
    parser.add_argument("--max-leaves", type=int, default=256)
    args = parser.parse_args(argv)
    summary = self_check(args.trials, args.max_leaves)
    print(f"pairwise_tree == reduction.ordered_sum(PAIRWISE_TREE) and == re8_chain: "
          f"compared={summary['compared']} mismatches={summary['mismatches']} "
          f"(N = 1..{summary['max_leaves']}, {summary['trials_per_count']} vectors each)")
    return 0 if summary["mismatches"] == 0 else 1


__all__ = [
    "LaneCase", "CaseResult", "ElementResult", "Observable",
    "evaluate", "element_chain", "pipelined_observable", "sequential_observable",
    "sequential_chain_acc", "shape_admissible", "narrow_output", "scale_index",
    "decode_code", "scale_of_code", "fold_scale", "error_code_of_detail",
    "element_width", "DETAIL_NAMES",
    "KBLOCK", "DETAIL_TREE_LEAF_NONFINITE", "DETAIL_TREE_ADD_RANGE", "DETAIL_TREE_LEAF_COUNT",
    "TreeFault", "tree_error_code_of_detail", "binary32_value", "add_binary32_rne",
    "pairwise_tree", "pairwise_tree_levels", "re8_combine", "re8_chain", "block_case",
    "block_count", "block_chains", "block_partials", "tile_output", "tile_element", "self_check",
]


if __name__ == "__main__":
    raise SystemExit(_main())
