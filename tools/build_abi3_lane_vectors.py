#!/usr/bin/env python3
"""Build the operand images and expectations for the pipelined lane gates.

Two suites, one per artifact:

``d1``      BF16, g = 1, K_BLOCK = K, run on both the pipelined lane and the
            untouched sequential lane ``rtl/abi3/ot_a3_mac_lane.sv``: the
            directed corners and negative cases the sequential lane was
            qualified on (transcribed from ``tools/build_abi3_engine_vectors.py``),
            a seeded spread of exponent windows, the 1,500,149-product
            normal-range BF16 sweep, every range exit, and one long
            steady-state run for gate D2.  The expectation for every element is
            the exact AM-E1 model (``tools/am_e1_lane_reference.py``), which
            for g = 1 is the sequential contract, cross-checked against the
            functional simulator's own ``sequential_matmul_binary32``.
``groups``  FP8 x FP8 at g = 2 and MXFP4 x FP8 at g = 4 (plus E2M1 x E2M1 and
            E2M1 x E4M3FN at g = 2), scaled and unscaled, against the AM-E1
            model only -- no RTL reference exists for the group association --
            with directed cases that provably distinguish one rounding per
            group from one rounding per product, every fault mode in group
            form, the np.float32 subnormal pin, and a steady-state run per g.

Images are regenerated deterministically at campaign time from the seeds
below; ``testdata/rtl/abi3_lane_pipelined/<suite>/manifest_L<L>.json`` pins
their digests so a change to this builder or to the model is a visible change
to the evidence.

Operand word layout: one 64-bit word per k-group holds g storage codes, code j
at bits [j * width +: width] (BF16 16, E4M3FN 8, E2M1 4); g = 1 is one code in
the low bits, the sequential lane's own layout.  Scales are one E8M0 code per
32-bit word in amendment A15 order.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import DType  # noqa: E402
from runtime.sim import formats as sim_formats  # noqa: E402
from runtime.sim.backend import sequential_matmul_binary32  # noqa: E402
import tools.am_e1_lane_reference as am  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_lane_pipelined_vectors.v1"
CASE_STRIDE = 40
META_WORDS = 8
UNWRITTEN = 0xDEADBEEF
FLAG_RATE = 0x1
FLAG_FAULT = 0x2

BF16 = int(DType.BF16)
FP8 = int(DType.FP8_E4M3FN)
E2M1 = int(DType.MXFP4_E2M1)

SWEEP_PRODUCTS = 1_500_149
MANIFEST_DIR = ROOT / "testdata/rtl/abi3_lane_pipelined"


# ---------------------------------------------------------------------------
# Operand generators
# ---------------------------------------------------------------------------
def bf16_window(rng: np.random.Generator, shape: tuple[int, ...],
                exponent_low: int, exponent_high: int) -> np.ndarray:
    """Random BF16 codes with exponent field in [low, high], random sign and fraction."""
    sign = rng.integers(0, 2, size=shape, dtype=np.uint64)
    exponent = rng.integers(exponent_low, exponent_high + 1, size=shape, dtype=np.uint64)
    fraction = rng.integers(0, 128, size=shape, dtype=np.uint64)
    return ((sign << 15) | (exponent << 7) | fraction).astype(np.uint16)


def fp8_random(rng: np.random.Generator, shape: tuple[int, ...],
               exponent_low: int = 0, exponent_high: int = 15) -> np.ndarray:
    """Random finite E4M3FN codes (the reserved 0x7f / 0xff are replaced)."""
    codes = rng.integers(0, 256, size=shape, dtype=np.uint64).astype(np.uint8)
    exponent = (codes >> 3) & 0xF
    codes = np.where(exponent < exponent_low,
                     (codes & 0x87) | (exponent_low << 3), codes).astype(np.uint8)
    codes = np.where(((codes >> 3) & 0xF) > exponent_high,
                     (codes & 0x87) | (exponent_high << 3), codes).astype(np.uint8)
    codes[codes == 0x7F] = 0x38
    codes[codes == 0xFF] = 0xB8
    return codes


def e2m1_random(rng: np.random.Generator, shape: tuple[int, ...]) -> np.ndarray:
    return rng.integers(0, 16, size=shape, dtype=np.uint64).astype(np.uint8)


def e8m0_random(rng: np.random.Generator, count: int, low: int, high: int) -> np.ndarray:
    return rng.integers(low, high + 1, size=(count,), dtype=np.uint64).astype(np.uint8)


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------
@dataclass
class Case:
    name: str
    note: str
    lane: am.LaneCase
    run_reference: bool
    rate: bool = False
    expect_detail: int | None = None       # a fault case declares its mode
    mode_name: str | None = None            # failure-mode label for gate D5
    distinguishes_sequential: bool = False  # group case must differ from g = 1
    numpy_cross_check: bool = True
    # filled by the builder
    case_id: int = -1
    a_base: int = 0
    b_base: int = 0
    scale_a_base: int = 0
    scale_b_base: int = 0
    out_base: int = 0
    expect_offset: int = 0
    result: am.CaseResult | None = None
    dut: am.Observable | None = None
    ref: am.Observable | None = None
    extras: dict[str, Any] = field(default_factory=dict)


def lane_case(rows: int, cols: int, depth: int, dtype_a: int, dtype_b: int, group: int,
              a_codes: np.ndarray, b_codes: np.ndarray, *, scales_a=None, scales_b=None,
              block_a: int = 0, block_b: int = 0, block_rows_a: int = 0,
              block_rows_b: int = 0, out_fp32: bool = False) -> am.LaneCase:
    a_codes = np.ascontiguousarray(a_codes).reshape(rows, depth) if rows * depth else np.zeros((rows, depth), dtype=np.uint16)
    b_codes = np.ascontiguousarray(b_codes).reshape(cols, depth) if cols * depth else np.zeros((cols, depth), dtype=np.uint16)
    return am.LaneCase(
        rows=rows, cols=cols, depth=depth, dtype_a=dtype_a, dtype_b=dtype_b,
        group=group, a_codes=a_codes, b_codes=b_codes,
        scales_a=None if scales_a is None else np.ascontiguousarray(scales_a, dtype=np.uint8),
        scales_b=None if scales_b is None else np.ascontiguousarray(scales_b, dtype=np.uint8),
        block_a=block_a, block_b=block_b, block_rows_a=block_rows_a,
        block_rows_b=block_rows_b, out_fp32=out_fp32,
    )


def sweep_plan(products: int) -> list[tuple[int, int, int, str]]:
    """Decompose the sweep into (rows, cols, depth, window) with the exact total."""
    plan = [
        (16, 16, 1800, "narrow"),   # activation-like exponents 118..137
        (16, 16, 1800, "wide"),     # exponents 64..185: every product normal
        (16, 16, 1800, "same"),     # exponents 125..130: cancellation-prone sums
    ]
    used = sum(r * c * d for r, c, d, _ in plan)
    remaining = products - used
    assert remaining > 0
    depth = remaining // 49
    plan.append((7, 7, depth, "mixed"))
    tail = remaining - 49 * depth
    if tail:
        plan.append((1, 1, tail, "narrow"))
    assert sum(r * c * d for r, c, d, _ in plan) == products
    return plan


WINDOWS = {
    "narrow": (118, 137),
    "wide": (64, 185),
    "same": (125, 130),
    "mixed": (100, 150),
    "tiny": (1, 40),
    "huge": (180, 254),
}


def build_d1_cases(rng: np.random.Generator, profile: str) -> list[Case]:
    cases: list[Case] = []

    def add(name, note, rows, cols, depth, a, b, *, dtype_a=BF16, dtype_b=BF16, group=1,
            run_reference=True, rate=False, expect_detail=None, mode_name=None,
            out_fp32=False, numpy_cross_check=True, **scales):
        cases.append(Case(
            name=name, note=note,
            lane=lane_case(rows, cols, depth, dtype_a, dtype_b, group, a, b,
                           out_fp32=out_fp32, **scales),
            run_reference=run_reference, rate=rate, expect_detail=expect_detail,
            mode_name=mode_name, numpy_cross_check=numpy_cross_check,
        ))

    # -- directed shape corners: every relation between cols and L, and K --------
    for rows, cols, depth in ((1, 1, 1), (1, 1, 2), (1, 2, 1), (2, 1, 1), (1, 3, 5),
                              (1, 4, 3), (1, 5, 7), (1, 7, 2), (1, 8, 9), (2, 9, 4),
                              (3, 5, 7), (2, 6, 1), (4, 3, 13)):
        add(f"shape_{rows}x{cols}x{depth}",
            f"{rows} x {depth} against {cols} x {depth}: pass and chain boundaries",
            rows, cols, depth,
            bf16_window(rng, (rows, depth), *WINDOWS["narrow"]),
            bf16_window(rng, (cols, depth), *WINDOWS["narrow"]))

    # -- the sequential lane's own directed cases (tools/build_abi3_engine_vectors.py)
    add("bf16_small", "4 x 16 against 8 x 16: the ordinary contraction", 4, 8, 16,
        bf16_window(rng, (4, 16), *WINDOWS["narrow"]), bf16_window(rng, (8, 16), *WINDOWS["narrow"]))
    add("bf16_tile_edge", "9 x 33 against 65 x 33: crosses every tile edge", 9, 65, 33,
        bf16_window(rng, (9, 33), *WINDOWS["narrow"]), bf16_window(rng, (65, 33), *WINDOWS["narrow"]))
    add("bf16_saturating",
        "accumulators inside binary32 and outside BF16: six of twelve outputs saturate",
        3, 4, 2,
        np.tile(np.array([0x5F7F, 0x5D80], dtype=np.uint16), (3, 1)),
        np.array([[0x5F7F, 0x5DCC], [0x5F7F, 0x5DCC], [0x3F80, 0x4000], [0xBF80, 0x4040]],
                 dtype=np.uint16))
    zero_a = np.zeros((4, 8), dtype=np.uint16)
    zero_a[:, ::2] = 0x8000
    zero_b = bf16_window(rng, (6, 8), *WINDOWS["narrow"])
    zero_b[:, 1::2] = 0x8000
    add("bf16_signed_zero", "every product is a signed exact zero: the result is +0", 4, 6, 8,
        zero_a, zero_b)
    add("bf16_reduction_order",
        "a small leading product then an exact cancellation: ascending-K returns zero",
        4, 4, 3,
        np.array([[0x3F80, 0x4700, 0x4700], [0x4000, 0x4700, 0x4700],
                  [0x4080, 0x4700, 0x4700], [0x4100, 0x4700, 0x4700]], dtype=np.uint16),
        np.array([[0x3F80, 0x4700, 0xC700], [0x3F80, 0x3F80, 0x3F80],
                  [0x4000, 0x4700, 0xC700], [0xBF80, 0x4700, 0xC700]], dtype=np.uint16))
    add("bf16_wide_reduction", "a 256-deep reduction", 2, 4, 256,
        bf16_window(rng, (2, 256), *WINDOWS["narrow"]), bf16_window(rng, (4, 256), *WINDOWS["narrow"]))

    # -- the retained subnormal paths ----------------------------------------------
    add("bf16_subnormal_operands",
        "BF16 subnormal operands (exponent field 0) on both sides, exact products",
        2, 3, 8, bf16_window(rng, (2, 8), 0, 0), bf16_window(rng, (3, 8), 0, 0))
    add("bf16_subnormal_products",
        "products in the binary32 subnormal range: exact where the grid holds them",
        3, 3, 16, bf16_window(rng, (3, 16), 50, 70), bf16_window(rng, (3, 16), 50, 70))
    add("bf16_rounded_products",
        "products below the 2**-149 grid: rounded to it, ties to even, or to zero",
        3, 3, 16, bf16_window(rng, (3, 16), 0, 20), bf16_window(rng, (3, 16), 40, 70))
    # Exact ties on the subnormal grid: 3 * 2**-150 rounds to 2 * 2**-149,
    # 1 * 2**-150 rounds to zero (even).  0x0001 is 2**-133, 0x0003 is 3 * 2**-133.
    add("bf16_subnormal_ties",
        "products of exactly half an ulp of the subnormal grid: ties to even",
        2, 2, 4,
        np.array([[0x0001, 0x0003, 0x0001, 0x0003], [0x0003, 0x0001, 0x0001, 0x0001]], dtype=np.uint16),
        np.array([[0x3800, 0x3800, 0x3800, 0x3800], [0x3800, 0x3800, 0xB800, 0x3800]], dtype=np.uint16))
    add("bf16_subnormal_accumulation",
        "sums that stay in the binary32 subnormal range and cross into the normal range",
        2, 2, 64, bf16_window(rng, (2, 64), 60, 66), bf16_window(rng, (2, 64), 60, 66))
    add("bf16_cancellation_to_zero", "exact cancellation inside the chain returns +0",
        2, 2, 4,
        np.array([[0x4200, 0x4200, 0x3F80, 0x3F80], [0xC200, 0x4200, 0x4000, 0xC000]], dtype=np.uint16),
        np.array([[0x3F80, 0xBF80, 0x3F80, 0xBF80], [0x3F80, 0x3F80, 0x3F80, 0x3F80]], dtype=np.uint16))
    add("bf16_near_overflow", "accumulations near 2**128 without leaving binary32",
        2, 2, 3,
        np.array([[0x7E80, 0x7E80, 0x7E00], [0x7F00, 0xFF00, 0x7F7F]], dtype=np.uint16),
        np.array([[0x3F80, 0x3F80, 0x3F80], [0x3F80, 0x3F80, 0xBF80]], dtype=np.uint16))
    add("bf16_huge_exponents", "operands at the top of the BF16 range, few products",
        2, 3, 2, bf16_window(rng, (2, 2), 160, 185), bf16_window(rng, (3, 2), 160, 185))
    add("bf16_tiny_exponents", "operands at the bottom of the BF16 range", 2, 3, 12,
        bf16_window(rng, (2, 12), 1, 40), bf16_window(rng, (3, 12), 1, 40))

    # -- the seeded spread: exponent windows, moderate shapes -------------------------
    for index, (name, (low, high)) in enumerate(WINDOWS.items()):
        if name in ("huge",):
            continue
        add(f"spread_{name}", f"seeded spread, exponent window {low}..{high}",
            5, 6, 40 + 7 * index,
            bf16_window(rng, (5, 40 + 7 * index), low, high),
            bf16_window(rng, (6, 40 + 7 * index), low, high))
    add("spread_mixed_signs_same_magnitude",
        "same-magnitude operands of random sign: heavy cancellation in every chain",
        4, 4, 96, bf16_window(rng, (4, 96), 127, 127), bf16_window(rng, (4, 96), 127, 127))
    add("spread_fp32_partials", "binary32 partial output (cfg_out_fp32), pipelined lane only",
        3, 5, 20, bf16_window(rng, (3, 20), *WINDOWS["narrow"]),
        bf16_window(rng, (5, 20), *WINDOWS["narrow"]), run_reference=False, out_fp32=True)

    # -- the sequential contract on the other formats, g = 1 ---------------------------
    add("fp8_fp8_g1", "FP8 E4M3FN on both sides under g = 1: exact decode, exact products",
        4, 8, 32, fp8_random(rng, (4, 32)), fp8_random(rng, (8, 32)), dtype_a=FP8, dtype_b=FP8)
    add("fp8_reduction_order_g1", "the order-sensitive construction on the FP8 path",
        3, 3, 3,
        np.array([[0x01, 0x7E, 0x7E], [0x02, 0x7E, 0x7E], [0x04, 0x7E, 0x7E]], dtype=np.uint8),
        np.array([[0x38, 0x7E, 0xFE], [0x38, 0x38, 0x38], [0x40, 0x7E, 0xFE]], dtype=np.uint8),
        dtype_a=FP8, dtype_b=FP8)
    add("fp8_k_major_g1", "64 x 128 over a 4-deep reduction", 64, 128, 4,
        fp8_random(rng, (64, 4), 0, 7), fp8_random(rng, (128, 4), 0, 7), dtype_a=FP8, dtype_b=FP8)
    add("mxfp4_fp8_block_scaled_g1",
        "MXFP4 E2M1 activations and FP8 weights with 32-element E8M0 blocks, g = 1",
        4, 8, 64, e2m1_random(rng, (4, 64)), fp8_random(rng, (8, 64)),
        dtype_a=E2M1, dtype_b=FP8,
        scales_a=e8m0_random(rng, 4 * 2, 120, 134), scales_b=e8m0_random(rng, 8 * 2, 120, 134),
        block_a=32, block_b=32)
    add("fp8_a15_block_rows_g1",
        "amendment A15's two-dimensional scale block, one code per 4 x 32 weight tile",
        3, 8, 64, bf16_window(rng, (3, 64), *WINDOWS["narrow"]), fp8_random(rng, (8, 64)),
        dtype_a=BF16, dtype_b=FP8, scales_b=e8m0_random(rng, 2 * 2, 120, 134),
        block_b=32, block_rows_b=4)
    add("bf16_scaled_subnormal_pin",
        "np.float32 pin: a scaled BF16 operand lands below the binary32 subnormal grid and "
        "is rounded to it before the product",
        2, 2, 32, bf16_window(rng, (2, 32), 1, 30), bf16_window(rng, (2, 32), 120, 130),
        scales_a=np.array([100, 90, 20, 0], dtype=np.uint8), block_a=16)
    add("bf16_scaled_both_sides", "E8M0 scales on both BF16 operands, g = 1", 2, 3, 32,
        bf16_window(rng, (2, 32), *WINDOWS["narrow"]), bf16_window(rng, (3, 32), *WINDOWS["narrow"]),
        scales_a=e8m0_random(rng, 2 * 2, 100, 150), scales_b=e8m0_random(rng, 3 * 2, 100, 150),
        block_a=16, block_b=16)

    # -- every range exit, first offender in the first output -------------------------
    nonfinite_a = bf16_window(rng, (2, 8), *WINDOWS["narrow"])
    nonfinite_a[0, 0] = 0x7F80
    add("fault_operand_a_nonfinite", "a BF16 infinity in operand A", 2, 3, 8,
        nonfinite_a, bf16_window(rng, (3, 8), *WINDOWS["narrow"]),
        expect_detail=am.DETAIL_A_NONFINITE, mode_name="nonfinite_bf16_operand_a")
    nonfinite_b = bf16_window(rng, (3, 8), *WINDOWS["narrow"])
    nonfinite_b[0, 0] = 0xFFC0
    add("fault_operand_b_nonfinite", "a BF16 NaN in operand B", 2, 3, 8,
        bf16_window(rng, (2, 8), *WINDOWS["narrow"]), nonfinite_b,
        expect_detail=am.DETAIL_B_NONFINITE, mode_name="nonfinite_bf16_operand_b")
    reserved_a = fp8_random(rng, (2, 8))
    reserved_a[0, 0] = 0x7F
    add("fault_operand_a_reserved", "the reserved E4M3FN code 0x7f in operand A", 2, 3, 8,
        reserved_a, fp8_random(rng, (3, 8)), dtype_a=FP8, dtype_b=FP8,
        expect_detail=am.DETAIL_A_RESERVED, mode_name="reserved_e4m3fn_operand_a")
    reserved_b = fp8_random(rng, (3, 8))
    reserved_b[0, 0] = 0xFF
    add("fault_operand_b_reserved", "the reserved E4M3FN code 0xff in operand B", 2, 3, 8,
        fp8_random(rng, (2, 8)), reserved_b, dtype_a=FP8, dtype_b=FP8,
        expect_detail=am.DETAIL_B_RESERVED, mode_name="reserved_e4m3fn_operand_b")
    add("fault_scale_a_reserved", "the reserved E8M0 code 0xff in operand A's scales", 2, 3, 32,
        fp8_random(rng, (2, 32)), fp8_random(rng, (3, 32)), dtype_a=FP8, dtype_b=FP8,
        scales_a=np.array([0xFF, 127], dtype=np.uint8), block_a=32,
        expect_detail=am.DETAIL_SCALE_A_RESERVED, mode_name="reserved_e8m0_scale_a")
    add("fault_scale_b_reserved", "the reserved E8M0 code 0xff in operand B's scales", 2, 3, 32,
        fp8_random(rng, (2, 32)), fp8_random(rng, (3, 32)), dtype_a=FP8, dtype_b=FP8,
        scales_b=np.array([0xFF, 127, 127], dtype=np.uint8), block_b=32,
        expect_detail=am.DETAIL_SCALE_B_RESERVED, mode_name="reserved_e8m0_scale_b")
    add("fault_scale_a_range", "a legal E8M0 2**127 against 448: the scale application overflows",
        2, 3, 32, np.full((2, 32), 0x7E, dtype=np.uint8), bf16_window(rng, (3, 32), *WINDOWS["narrow"]),
        dtype_a=FP8, dtype_b=BF16, scales_a=np.full((2,), 254, dtype=np.uint8), block_a=32,
        expect_detail=am.DETAIL_SCALE_A_RANGE, mode_name="scale_application_range_a")
    add("fault_scale_b_range", "the same on operand B",
        2, 3, 32, bf16_window(rng, (2, 32), *WINDOWS["narrow"]), np.full((3, 32), 0x7E, dtype=np.uint8),
        dtype_a=BF16, dtype_b=FP8, scales_b=np.full((3,), 254, dtype=np.uint8), block_b=32,
        expect_detail=am.DETAIL_SCALE_B_RANGE, mode_name="scale_application_range_b")
    add("fault_product_range", "the largest finite BF16 squared leaves binary32", 2, 3, 4,
        np.full((2, 4), 0x7F7F, dtype=np.uint16), np.full((3, 4), 0x7F7F, dtype=np.uint16),
        expect_detail=am.DETAIL_PRODUCT_RANGE, mode_name="product_range")
    add("fault_accumulate_range", "finite products whose ascending-K sum leaves binary32",
        2, 3, 4, np.full((2, 4), 0x5F00, dtype=np.uint16), np.full((3, 4), 0x5F00, dtype=np.uint16),
        expect_detail=am.DETAIL_ACCUMULATE_RANGE, mode_name="accumulate_range")
    add("fault_shape_zero_depth", "a degenerate extent is refused by both lanes", 2, 3, 0,
        np.zeros((2, 0), dtype=np.uint16), np.zeros((3, 0), dtype=np.uint16),
        expect_detail=am.DETAIL_SHAPE, mode_name="shape", numpy_cross_check=False)

    # -- late faults: the written set is deterministic per lane ----------------------
    late_a = bf16_window(rng, (3, 6), *WINDOWS["narrow"])
    late_b = bf16_window(rng, (7, 6), *WINDOWS["narrow"])
    late_a[1, 4] = 0x7F80
    add("fault_late_operand", "an infinity at row 1, k 4: earlier passes are written", 3, 7, 6,
        late_a, late_b, expect_detail=am.DETAIL_A_NONFINITE)
    late_b2 = bf16_window(rng, (7, 6), *WINDOWS["narrow"])
    late_b2[5, 2] = 0x7F80
    add("fault_late_column", "an infinity in column 5, k 2: the passes before it are written",
        2, 7, 6, bf16_window(rng, (2, 6), *WINDOWS["narrow"]), late_b2,
        expect_detail=am.DETAIL_B_NONFINITE)
    late_acc_a = bf16_window(rng, (2, 5), 100, 110)
    late_acc_b = bf16_window(rng, (5, 5), 100, 110)
    late_acc_a[1, :] = 0x5F00
    late_acc_b[3, :] = 0x5F00
    add("fault_late_accumulate", "an accumulation overflow in the last row's second pass",
        2, 5, 5, late_acc_a, late_acc_b, expect_detail=am.DETAIL_ACCUMULATE_RANGE)

    if profile == "full":
        # -- the 1,500,149-product normal-range sweep -----------------------------------
        for index, (rows, cols, depth, window) in enumerate(sweep_plan(SWEEP_PRODUCTS)):
            low, high = WINDOWS[window]
            add(f"sweep_{index}_{window}_{rows}x{cols}x{depth}",
                f"normal-range BF16 sweep block {index}: {rows} x {cols} outputs over K = {depth}, "
                f"exponent window {low}..{high}",
                rows, cols, depth, bf16_window(rng, (rows, depth), low, high),
                bf16_window(rng, (cols, depth), low, high))
        # -- gate D2: one long steady-state run ---------------------------------------------
        add("rate_bf16_32x48x1024",
            "gate D2: 32 x 48 outputs over K = 1024 (1,572,864 lane-ops, 512 passes of 48 columns)",
            32, 48, 1024, bf16_window(rng, (32, 1024), *WINDOWS["narrow"]),
            bf16_window(rng, (48, 1024), *WINDOWS["narrow"]), run_reference=False, rate=True)
    else:
        add("rate_bf16_4x12x256", "gate D2 (quick profile): 4 x 12 outputs over K = 256",
            4, 12, 256, bf16_window(rng, (4, 256), *WINDOWS["narrow"]),
            bf16_window(rng, (12, 256), *WINDOWS["narrow"]), run_reference=False, rate=True)
    return cases


def build_group_cases(rng: np.random.Generator, profile: str) -> list[Case]:
    cases: list[Case] = []

    def add(name, note, rows, cols, depth, a, b, *, dtype_a, dtype_b, group, rate=False,
            expect_detail=None, mode_name=None, distinguishes=False, out_fp32=False, **scales):
        cases.append(Case(
            name=name, note=note,
            lane=lane_case(rows, cols, depth, dtype_a, dtype_b, group, a, b,
                           out_fp32=out_fp32, **scales),
            run_reference=False, rate=rate, expect_detail=expect_detail, mode_name=mode_name,
            distinguishes_sequential=distinguishes, numpy_cross_check=False,
        ))

    # -- FP8 x FP8, g = 2 ----------------------------------------------------------------
    for rows, cols, depth in ((1, 1, 2), (1, 1, 1), (1, 3, 5), (2, 4, 16), (3, 7, 31), (4, 8, 64)):
        add(f"fp8_g2_{rows}x{cols}x{depth}", f"FP8 x FP8 at g = 2, {rows} x {cols} x {depth}"
            + (" (short final group)" if depth % 2 else ""),
            rows, cols, depth, fp8_random(rng, (rows, depth)), fp8_random(rng, (cols, depth)),
            dtype_a=FP8, dtype_b=FP8, group=2)
    add("fp8_g2_extremes", "448 and 2**-9 mixed inside groups: the full aligner span", 3, 3, 16,
        rng.choice(np.array([0x7E, 0x01, 0xFE, 0x81, 0x38, 0x08], dtype=np.uint8), size=(3, 16)),
        rng.choice(np.array([0x7E, 0x01, 0xFE, 0x81, 0x38, 0x08], dtype=np.uint8), size=(3, 16)),
        dtype_a=FP8, dtype_b=FP8, group=2)
    add("fp8_g2_group_cancellation", "p0 = -p1 inside every group: exact zero group sums", 2, 2, 8,
        np.tile(np.array([0x48, 0x48], dtype=np.uint8), (2, 4)),
        np.tile(np.array([0x50, 0xD0], dtype=np.uint8), (2, 4)),
        dtype_a=FP8, dtype_b=FP8, group=2)
    # One rounding per group versus one per product.  Chain: 84 products of
    # 448 * 448 raise the accumulator above 2**24 (ulp 2); then the group
    # (1.5, -0.5) sums to +1.0, a tie that rounds to even under AM-E1, while
    # per-product rounding rounds +1.5 up first and then cannot come back.
    dist_a = np.full((1, 86), 0x7E, dtype=np.uint8)
    dist_b = np.full((1, 86), 0x7E, dtype=np.uint8)
    dist_a[0, 84], dist_b[0, 84] = 0x3C, 0x38     # 1.5 * 1.0
    dist_a[0, 85], dist_b[0, 85] = 0x30, 0xB8     # 0.5 * -1.0
    add("fp8_g2_distinguishes_association",
        "acc above 2**24 then the group (1.5, -0.5): AM-E1 rounds the exact +1.0 to even; "
        "per-product rounding does not -- this case must differ from the sequential contract",
        1, 1, 86, dist_a, dist_b, dtype_a=FP8, dtype_b=FP8, group=2, distinguishes=True)
    add("fp8_g2_scaled_block32", "FP8 x FP8 at g = 2 with 32-element E8M0 blocks on both sides",
        4, 6, 64, fp8_random(rng, (4, 64)), fp8_random(rng, (6, 64)), dtype_a=FP8, dtype_b=FP8,
        group=2, scales_a=e8m0_random(rng, 4 * 2, 110, 140), scales_b=e8m0_random(rng, 6 * 2, 110, 140),
        block_a=32, block_b=32)
    add("fp8_g2_scaled_block128_a15", "activation block 128, weight 128 x 4 rows (A15)", 4, 8, 128,
        fp8_random(rng, (4, 128)), fp8_random(rng, (8, 128)), dtype_a=FP8, dtype_b=FP8, group=2,
        scales_a=e8m0_random(rng, 4, 115, 135), scales_b=e8m0_random(rng, 2, 115, 135),
        block_a=128, block_b=128, block_rows_b=4)
    add("fp8_g2_scaled_tiny", "scales of 2**-127 on 2**-9 operands: exact binary32 subnormals",
        2, 2, 32, fp8_random(rng, (2, 32), 0, 2), fp8_random(rng, (2, 32), 0, 2), dtype_a=FP8,
        dtype_b=FP8, group=2, scales_a=np.array([0, 5], dtype=np.uint8), block_a=32)
    add("fp8_g2_fp32_out", "binary32 partial output at g = 2", 2, 3, 16, fp8_random(rng, (2, 16)),
        fp8_random(rng, (3, 16)), dtype_a=FP8, dtype_b=FP8, group=2, out_fp32=True)
    add("e2m1_fp8_g2", "E2M1 x E4M3FN at g = 2 (a 2 x 4 product through the 4 x 4 field)", 3, 4, 32,
        e2m1_random(rng, (3, 32)), fp8_random(rng, (4, 32)), dtype_a=E2M1, dtype_b=FP8, group=2)

    # -- MXFP4 x FP8, g = 4 ---------------------------------------------------------------
    for rows, cols, depth in ((1, 1, 4), (1, 1, 3), (1, 2, 7), (2, 5, 32), (3, 6, 45), (4, 8, 64)):
        add(f"mxfp4_g4_{rows}x{cols}x{depth}", f"E2M1 x E4M3FN at g = 4, {rows} x {cols} x {depth}"
            + (" (short final group)" if depth % 4 else ""),
            rows, cols, depth, e2m1_random(rng, (rows, depth)), fp8_random(rng, (cols, depth)),
            dtype_a=E2M1, dtype_b=FP8, group=4)
    add("mxfp4_g4_weights_e2m1", "E4M3FN activations against E2M1 weights: the E2M1 side is B",
        3, 5, 32, fp8_random(rng, (3, 32)), e2m1_random(rng, (5, 32)), dtype_a=FP8, dtype_b=E2M1,
        group=4)
    add("e2m1_e2m1_g4", "E2M1 on both sides at g = 4", 2, 4, 32, e2m1_random(rng, (2, 32)),
        e2m1_random(rng, (4, 32)), dtype_a=E2M1, dtype_b=E2M1, group=4)
    add("mxfp4_g4_deepseek_pair",
        "the released DeepSeek MoE pair: MXFP4 activations and FP8 weights, 32-element blocks",
        4, 8, 64, e2m1_random(rng, (4, 64)), fp8_random(rng, (8, 64)), dtype_a=E2M1, dtype_b=FP8,
        group=4, scales_a=e8m0_random(rng, 4 * 2, 120, 134), scales_b=e8m0_random(rng, 8 * 2, 120, 134),
        block_a=32, block_b=32)
    add("mxfp4_g4_scaled_a15", "MXFP4 block 32 against FP8 with a 128 x 4 A15 block", 4, 8, 128,
        e2m1_random(rng, (4, 128)), fp8_random(rng, (8, 128)), dtype_a=E2M1, dtype_b=FP8, group=4,
        scales_a=e8m0_random(rng, 4 * 4, 115, 135), scales_b=e8m0_random(rng, 2, 115, 135),
        block_a=32, block_b=128, block_rows_b=4)
    add("mxfp4_g4_group_cancellation", "groups (6, -6, 3, -3) x 1: exact zero group sums",
        2, 2, 8, np.tile(np.array([0x7, 0xF, 0x5, 0xD], dtype=np.uint8), (2, 2)),
        np.full((2, 8), 0x38, dtype=np.uint8), dtype_a=E2M1, dtype_b=FP8, group=4)
    # 6244 products of 6 x 448 = 2688 (1561 groups, every partial sum exact)
    # raise the accumulator to 16,783,872, above 2**24 where the ulp is 2 and
    # the mantissa is even; the last group (1.5, -0.5, 0, 0) x 1.0 sums to
    # exactly +1.0: half an ulp, a tie, rounded to even under AM-E1.  Rounded
    # per product, +1.5 goes up to acc + 2 and -0.5 cannot bring it back.
    dist4_a = np.full((1, 6248), 0x7, dtype=np.uint8)          # 6.0
    dist4_b = np.full((1, 6248), 0x7E, dtype=np.uint8)         # 448
    dist4_a[0, 6244:6248] = [0x3, 0x9, 0x0, 0x0]               # 1.5, -0.5, 0, 0
    dist4_b[0, 6244:6248] = [0x38, 0x38, 0x38, 0x38]           # 1.0
    add("mxfp4_g4_distinguishes_association",
        "acc above 2**24 then the group (1.5, -0.5, 0, 0) = +1.0: rounded once it is a tie to "
        "even; per product it drifts up -- must differ from the sequential contract",
        1, 1, 6248, dist4_a, dist4_b, dtype_a=E2M1, dtype_b=FP8, group=4, distinguishes=True)
    add("mxfp4_g4_fp32_out", "binary32 partial output at g = 4", 2, 3, 16,
        e2m1_random(rng, (2, 16)), fp8_random(rng, (3, 16)), dtype_a=E2M1, dtype_b=FP8, group=4,
        out_fp32=True)

    # -- np.float32 subnormal pin in a group mode ---------------------------------------------
    # 2**-127 scales on E2M1 0.5 give 2**-128: exact; on the accumulate side
    # the group sums stay subnormal, so the one rounding is on the grid.
    add("mxfp4_g4_subnormal_pin", "scaled operands and sums in the binary32 subnormal range",
        2, 2, 32, e2m1_random(rng, (2, 32)), fp8_random(rng, (2, 32), 0, 3), dtype_a=E2M1,
        dtype_b=FP8, group=4, scales_a=np.array([0, 1], dtype=np.uint8),
        scales_b=np.array([0, 0], dtype=np.uint8), block_a=32, block_b=32)

    # -- every fault mode in group form -------------------------------------------------------
    r_a = fp8_random(rng, (2, 8))
    r_a[0, 1] = 0x7F
    add("g2_fault_operand_a_reserved", "reserved E4M3FN in the second element of the first group",
        2, 3, 8, r_a, fp8_random(rng, (3, 8)), dtype_a=FP8, dtype_b=FP8, group=2,
        expect_detail=am.DETAIL_A_RESERVED, mode_name="reserved_e4m3fn_operand_a")
    r_b = fp8_random(rng, (3, 8))
    r_b[0, 0] = 0xFF
    add("g2_fault_operand_b_reserved", "reserved E4M3FN in operand B", 2, 3, 8,
        fp8_random(rng, (2, 8)), r_b, dtype_a=FP8, dtype_b=FP8, group=2,
        expect_detail=am.DETAIL_B_RESERVED, mode_name="reserved_e4m3fn_operand_b")
    add("g2_fault_scale_a_reserved", "reserved E8M0 in operand A's scales", 2, 3, 32,
        fp8_random(rng, (2, 32)), fp8_random(rng, (3, 32)), dtype_a=FP8, dtype_b=FP8, group=2,
        scales_a=np.array([0xFF, 127], dtype=np.uint8), block_a=32,
        expect_detail=am.DETAIL_SCALE_A_RESERVED, mode_name="reserved_e8m0_scale_a")
    add("g4_fault_scale_b_reserved", "reserved E8M0 in operand B's scales at g = 4", 2, 3, 32,
        e2m1_random(rng, (2, 32)), fp8_random(rng, (3, 32)), dtype_a=E2M1, dtype_b=FP8, group=4,
        scales_b=np.array([0xFF, 127, 127], dtype=np.uint8), block_b=32,
        expect_detail=am.DETAIL_SCALE_B_RESERVED, mode_name="reserved_e8m0_scale_b")
    add("g2_fault_scale_a_range", "2**127 x 448 leaves binary32 in the scale application", 2, 3, 32,
        np.full((2, 32), 0x7E, dtype=np.uint8), fp8_random(rng, (3, 32)), dtype_a=FP8, dtype_b=FP8,
        group=2, scales_a=np.full((2,), 254, dtype=np.uint8), block_a=32,
        expect_detail=am.DETAIL_SCALE_A_RANGE, mode_name="scale_application_range_a")
    add("g4_fault_scale_b_range", "the same on operand B at g = 4", 2, 3, 32,
        e2m1_random(rng, (2, 32)), np.full((3, 32), 0x7E, dtype=np.uint8), dtype_a=E2M1, dtype_b=FP8,
        group=4, scales_b=np.full((3,), 254, dtype=np.uint8), block_b=32,
        expect_detail=am.DETAIL_SCALE_B_RANGE, mode_name="scale_application_range_b")
    add("g2_fault_product_range",
        "448 x 2**119 on both sides: every scaled operand is inside binary32, their product is not",
        2, 3, 32, np.full((2, 32), 0x7E, dtype=np.uint8), np.full((3, 32), 0x7E, dtype=np.uint8),
        dtype_a=FP8, dtype_b=FP8, group=2, scales_a=np.full((2,), 246, dtype=np.uint8),
        scales_b=np.full((3,), 246, dtype=np.uint8), block_a=32, block_b=32,
        expect_detail=am.DETAIL_PRODUCT_RANGE, mode_name="product_range")
    add("g4_fault_accumulate_range",
        "6 x 448 x 2**113 products, four per group: the third group's sum leaves binary32",
        2, 3, 32, np.full((2, 32), 0x7, dtype=np.uint8), np.full((3, 32), 0x7E, dtype=np.uint8),
        dtype_a=E2M1, dtype_b=FP8, group=4, scales_b=np.full((3,), 240, dtype=np.uint8), block_b=32,
        expect_detail=am.DETAIL_ACCUMULATE_RANGE, mode_name="accumulate_range")
    add("g2_fault_shape_bf16_in_group", "a BF16 operand in a group mode is refused fail-closed",
        2, 3, 8, bf16_window(rng, (2, 8), *WINDOWS["narrow"]), fp8_random(rng, (3, 8)),
        dtype_a=BF16, dtype_b=FP8, group=2, expect_detail=am.DETAIL_SHAPE, mode_name="shape")
    add("g4_fault_shape_no_e2m1", "g = 4 without an E2M1 operand is refused", 2, 3, 8,
        fp8_random(rng, (2, 8)), fp8_random(rng, (3, 8)), dtype_a=FP8, dtype_b=FP8, group=4,
        expect_detail=am.DETAIL_SHAPE)
    add("g2_fault_shape_block_not_multiple", "a scale block that is not a multiple of g", 2, 3, 6,
        fp8_random(rng, (2, 6)), fp8_random(rng, (3, 6)), dtype_a=FP8, dtype_b=FP8, group=2,
        scales_a=np.array([127, 127], dtype=np.uint8), block_a=3,
        expect_detail=am.DETAIL_SHAPE)
    late = fp8_random(rng, (7, 12))
    late[4, 9] = 0x7F
    add("g2_fault_late", "a reserved code in column 4, group 4: earlier passes are written",
        2, 7, 12, fp8_random(rng, (2, 12)), late, dtype_a=FP8, dtype_b=FP8, group=2,
        expect_detail=am.DETAIL_B_RESERVED)

    # -- gate D2 in each group mode --------------------------------------------------------------
    if profile == "full":
        add("rate_fp8_g2_16x48x1024", "gate D2 at g = 2: 16 x 48 outputs over K = 1024", 16, 48, 1024,
            fp8_random(rng, (16, 1024)), fp8_random(rng, (48, 1024)), dtype_a=FP8, dtype_b=FP8,
            group=2, rate=True)
        add("rate_mxfp4_g4_16x48x1024", "gate D2 at g = 4: 16 x 48 outputs over K = 1024", 16, 48, 1024,
            e2m1_random(rng, (16, 1024)), fp8_random(rng, (48, 1024)), dtype_a=E2M1, dtype_b=FP8,
            group=4, rate=True)
    else:
        add("rate_fp8_g2_4x12x256", "gate D2 at g = 2 (quick)", 4, 12, 256, fp8_random(rng, (4, 256)),
            fp8_random(rng, (12, 256)), dtype_a=FP8, dtype_b=FP8, group=2, rate=True)
        add("rate_mxfp4_g4_4x12x256", "gate D2 at g = 4 (quick)", 4, 12, 256, e2m1_random(rng, (4, 256)),
            fp8_random(rng, (12, 256)), dtype_a=E2M1, dtype_b=FP8, group=4, rate=True)
    return cases


# ---------------------------------------------------------------------------
# Expectations
# ---------------------------------------------------------------------------
def numpy_sequential(case: am.LaneCase) -> np.ndarray:
    """The functional simulator's own g = 1 evaluation of this case, binary32 codes."""
    def operand(codes: np.ndarray, dtype: int, scales, block, block_rows) -> np.ndarray:
        values = sim_formats.widen(dtype, codes)
        if scales is None:
            return values
        rows, depth = values.shape
        row_block = max(int(block_rows), 1)
        per_row = depth // block
        tiles = sim_formats.decode_e8m0(np.asarray(scales, dtype=np.uint8)).reshape(rows // row_block, per_row)
        expanded = np.repeat(tiles, row_block, axis=0)
        flat = values.reshape(rows, per_row, block)
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            scaled = np.multiply(flat, expanded[:, :, None], dtype=np.float32)
        if not np.all(np.isfinite(scaled)):
            raise FloatingPointError("scale application left binary32")
        return scaled.reshape(values.shape)

    left = operand(case.a_codes, case.dtype_a, case.scales_a, case.block_a, case.block_rows_a)
    right = operand(case.b_codes, case.dtype_b, case.scales_b, case.block_b, case.block_rows_b)
    if np.any(np.isnan(left)) or np.any(np.isnan(right)):
        raise FloatingPointError("nonfinite operand")
    return sequential_matmul_binary32(left, right).view(np.uint32)


def evaluate_cases(cases: list[Case], adder_stages: int) -> None:
    for case in cases:
        result = am.evaluate(case.lane) if am.shape_admissible(case.lane) else am.CaseResult([], [], [], [])
        case.result = result
        case.dut = am.pipelined_observable(case.lane, result, adder_stages)
        case.ref = am.sequential_observable(case.lane, result) if case.run_reference else None
        if case.run_reference and case.lane.group != 1:
            raise RuntimeError(f"{case.name}: the sequential reference is a g = 1 lane")
        if case.expect_detail is not None and case.dut.error_detail != case.expect_detail:
            raise RuntimeError(
                f"{case.name}: expected fault detail {case.expect_detail}, model gives "
                f"{case.dut.error_detail}"
            )
        if case.expect_detail is None and case.dut.error_code != 0:
            raise RuntimeError(f"{case.name}: unexpected fault {case.dut.error_detail}")
        # The functional simulator's own evaluation must agree with the exact
        # model on every g = 1 case that does not fault.
        if (case.numpy_cross_check and case.lane.group == 1 and case.dut.error_code == 0
                and case.lane.rows and case.lane.cols and case.lane.depth):
            via_numpy = numpy_sequential(case.lane).reshape(-1)
            exact_codes = np.array(result.acc_words, dtype=np.uint32)
            canonical = np.where(via_numpy == 0x80000000, 0, via_numpy)
            if not np.array_equal(canonical, exact_codes):
                differing = int(np.count_nonzero(canonical != exact_codes))
                raise RuntimeError(
                    f"{case.name}: {differing} accumulators differ between the exact AM-E1 model "
                    "and runtime.sim.backend.sequential_matmul_binary32"
                )
            case.extras["numpy_cross_check"] = "sequential_matmul_binary32 agrees on every accumulator"
        if case.distinguishes_sequential:
            sequential = am.sequential_chain_acc(case.lane, 0, 0)
            am_e1 = result.acc_words[0]
            if sequential is None or sequential == am_e1:
                raise RuntimeError(
                    f"{case.name}: this case was meant to distinguish AM-E1 from the sequential "
                    f"association but gives {am_e1:#010x} under both"
                )
            case.extras["sequential_association_acc"] = f"{sequential:#010x}"
            case.extras["am_e1_acc"] = f"{am_e1:#010x}"


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
def pack_words(codes: np.ndarray, dtype: int, group: int) -> list[int]:
    """One 64-bit word per k-group per row, codes packed low-first."""
    width = am.element_width(dtype)
    rows, depth = codes.shape
    groups = (depth + group - 1) // group
    words: list[int] = []
    for row in range(rows):
        row_codes = [int(c) for c in codes[row]]
        for kg in range(groups):
            word = 0
            for j in range(group):
                k = kg * group + j
                if k < depth:
                    word |= (row_codes[k] & ((1 << width) - 1)) << (j * width)
            words.append(word)
    return words


def hex_lines(values: list[int], digits: int) -> str:
    return "".join(f"{value:0{digits}x}\n" for value in values)


def emit(cases: list[Case], out_dir: Path, adder_stages: int, suite: str, profile: str,
         seed: int) -> dict[str, Any]:
    m0: list[int] = []
    m1: list[int] = []
    m2: list[int] = []
    m3: list[int] = []
    expect: list[int] = []
    records: list[int] = []
    out_pointer = 0
    totals = {"lane_ops": 0, "products": 0, "outputs": 0, "faults": 0,
              "reference": 0, "ref_outputs": 0}
    summaries: list[dict[str, Any]] = []
    for case_id, case in enumerate(cases):
        lane = case.lane
        case.case_id = case_id
        case.a_base = len(m0)
        m0.extend(pack_words(lane.a_codes, lane.dtype_a, lane.group))
        case.b_base = len(m1)
        m1.extend(pack_words(lane.b_codes, lane.dtype_b, lane.group))
        case.scale_a_base = len(m2)
        if lane.scales_a is not None:
            m2.extend(int(c) for c in lane.scales_a)
        case.scale_b_base = len(m3)
        if lane.scales_b is not None:
            m3.extend(int(c) for c in lane.scales_b)
        window = lane.rows * lane.cols
        case.out_base = out_pointer
        out_pointer += window
        case.expect_offset = len(expect)
        assert case.result is not None and case.dut is not None
        for element in range(window):
            expect.append(case.result.out_words[element] if element < len(case.result.out_words) else 0)
            expect.append(case.result.acc_words[element] if element < len(case.result.acc_words) else 0)
        dut = case.dut
        ref = case.ref
        flags = (FLAG_RATE if case.rate else 0) | (FLAG_FAULT if dut.error_code else 0)
        record = [
            lane.rows, lane.cols, lane.depth, lane.dtype_a, lane.dtype_b, lane.group,
            case.a_base, case.b_base,
            1 if lane.scales_a is not None else 0, 1 if lane.scales_b is not None else 0,
            lane.block_a, lane.block_b, lane.block_rows_a, lane.block_rows_b,
            case.scale_a_base, case.scale_b_base, case.out_base, 1 if lane.out_fp32 else 0,
            dut.error_code, dut.error_detail, dut.out_count, dut.saturations, dut.lane_ops,
            dut.products, dut.written,
            1 if ref is not None else 0,
            ref.error_code if ref else 0, ref.out_count if ref else 0,
            ref.saturations if ref else 0, ref.lane_ops if ref else 0, ref.written if ref else 0,
            case.expect_offset, flags, case_id, window,
        ]
        record.extend([0] * (CASE_STRIDE - len(record)))
        records.extend(record)
        totals["lane_ops"] += dut.lane_ops
        totals["products"] += dut.products
        totals["outputs"] += dut.written
        totals["faults"] += 1 if dut.error_code else 0
        totals["reference"] += 1 if ref else 0
        totals["ref_outputs"] += ref.written if ref else 0
        summaries.append({
            "id": case_id, "name": case.name, "note": case.note,
            "rows": lane.rows, "cols": lane.cols, "depth": lane.depth,
            "dtype_a": lane.dtype_a, "dtype_b": lane.dtype_b, "group": lane.group,
            "scaled_a": lane.scales_a is not None, "scaled_b": lane.scales_b is not None,
            "block_a": lane.block_a, "block_b": lane.block_b,
            "block_rows_a": lane.block_rows_a, "block_rows_b": lane.block_rows_b,
            "out_fp32": lane.out_fp32, "run_reference": ref is not None, "rate": case.rate,
            "products": lane.rows * lane.cols * lane.depth,
            "mode_name": case.mode_name,
            "expected": {
                "pipelined": dut.__dict__,
                "sequential": ref.__dict__ if ref else None,
            },
            "extras": case.extras,
        })
    meta = [len(cases), totals["lane_ops"], totals["products"], totals["outputs"],
            totals["faults"], totals["reference"], CASE_STRIDE, totals["ref_outputs"]]
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "lane_m0.hex": hex_lines(m0, 16),
        "lane_m1.hex": hex_lines(m1, 16),
        "lane_m2.hex": hex_lines(m2 or [0], 8),
        "lane_m3.hex": hex_lines(m3 or [0], 8),
        "lane_case.hex": hex_lines(records, 8),
        "lane_expect.hex": hex_lines(expect or [0], 8),
        "lane_meta.hex": hex_lines(meta, 8),
    }
    digests: dict[str, str] = {}
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
        digests[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    rate_lines = [
        {"case": case.case_id, "lane_ops": case.dut.lane_ops, "products": case.dut.products}
        for case in cases if case.rate and case.dut is not None
    ]
    modes: dict[str, dict[str, Any]] = {}
    for case in cases:
        if case.mode_name and case.dut is not None:
            modes.setdefault(case.mode_name, {
                "case": case.case_id, "name": case.name,
                "error_code": case.dut.error_code, "error_detail": case.dut.error_detail,
                "detail_name": am.DETAIL_NAMES.get(case.dut.error_detail, "?"),
            })
    marker = (
        f"PASS: ABI3 pipelined lane cases={len(cases)} lane_ops={totals['lane_ops']} "
        f"products={totals['products']} outputs={totals['outputs']} faults={totals['faults']} "
        f"reference_cases={totals['reference']} reference_outputs={totals['ref_outputs']}"
    )
    manifest = {
        "schema": SCHEMA,
        "suite": suite,
        "profile": profile,
        "seed": seed,
        "adder_stages": adder_stages,
        "case_stride": CASE_STRIDE,
        "unwritten_sentinel": UNWRITTEN,
        "geometry": {
            "m0_words": len(m0), "m1_words": len(m1), "m2_words": len(m2), "m3_words": len(m3),
            "result_words": out_pointer, "expect_words": len(expect), "case_words": len(records),
        },
        "totals": totals,
        "sweep_products": SWEEP_PRODUCTS if suite == "d1" and profile == "full" else None,
        "sweep_plan": sweep_plan(SWEEP_PRODUCTS) if suite == "d1" and profile == "full" else None,
        "required_marker_prefix": marker,
        "rate_cases": rate_lines,
        "failure_modes": modes,
        "image_sha256": digests,
        "cases": summaries,
        "reference": {
            "model": "tools/am_e1_lane_reference.py",
            "numeric_authority": "runtime/reference/formats.py (fractions.Fraction, encode_binary32_rne)",
            "scale_semantics": "runtime/sim/engines/tensor.py::_operand (np.multiply dtype=float32)",
            "g1_cross_check": "runtime/sim/backend.py::sequential_matmul_binary32",
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                           encoding="utf-8")
    return manifest


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("d1", "groups"), required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--adder-stages", type=int, default=3)
    parser.add_argument("--profile", choices=("quick", "full"), default="full")
    parser.add_argument("--seed", type=int, default=20260904)
    parser.add_argument("--write-manifest", action="store_true",
                        help="also copy the manifest into testdata/rtl/abi3_lane_pipelined")
    args = parser.parse_args(argv)
    rng = np.random.default_rng(args.seed)
    cases = build_d1_cases(rng, args.profile) if args.suite == "d1" else build_group_cases(rng, args.profile)
    evaluate_cases(cases, args.adder_stages)
    manifest = emit(cases, args.out_dir, args.adder_stages, args.suite, args.profile, args.seed)
    if args.write_manifest:
        target = MANIFEST_DIR / args.suite / f"manifest_{args.profile}_L{args.adder_stages}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"manifest -> {target}")
    print(f"{args.suite}: {len(cases)} cases, {manifest['totals']['lane_ops']} lane-ops, "
          f"{manifest['totals']['products']} products -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
