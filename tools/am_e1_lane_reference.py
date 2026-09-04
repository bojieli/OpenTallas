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


__all__ = [
    "LaneCase", "CaseResult", "ElementResult", "Observable",
    "evaluate", "element_chain", "pipelined_observable", "sequential_observable",
    "sequential_chain_acc", "shape_admissible", "narrow_output", "scale_index",
    "decode_code", "scale_of_code", "fold_scale", "error_code_of_detail",
    "element_width", "DETAIL_NAMES",
]
