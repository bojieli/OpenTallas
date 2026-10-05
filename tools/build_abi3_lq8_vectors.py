#!/usr/bin/env python3
"""Build the operand images and expectations for the LQ8 lane block campaign.

One suite, ``lq8``, for ``results/rtl/abi3_lq8.json``: every case is a block
contraction over ``cols`` columns, ``cols`` a multiple of LANES, that the
block ``rtl/abi3/ot_a3_lq8.sv`` runs once and that the checkers then run
LANES more times on the single qualified lane ``rtl/abi3/ot_a3_lane_pipelined.sv``
-- once per block lane, on that lane's own column-major weight image and
lane-local scale image.  The expectation for every element is the exact
AM-E1 model (``tools/am_e1_lane_reference.py``) evaluated on each lane's own
column set; for g = 1 the reassembled block result is additionally
cross-checked against the functional simulator's
``sequential_matmul_binary32`` on the *global* operands, which pins the
column permutation and the scale-table expansion to the simulator.

Column assignment (the block's rule): lane i owns block columns
c * LANES + i for its local columns c in [0, cols / LANES).

Images:

``lq8_m0.hex``      activation words, one 64-bit word per k-group per row
                    (the lane's own layout; shared by the block and the
                    reference runs)
``lq8_m2.hex``      activation E8M0 codes, one per 32-bit word, A15 order
``lq8_w.hex``       the weight stream: one 128-bit word per block lane-op in
                    the lanes' issue order (row, pass of L interleaved local
                    columns, k-group, column within the pass); lane i's g
                    codes at bits [16 i +: 16], code j at [j * width +: width]
``lq8_ws.hex``      the weight scale table: one 64-bit word per lane-local
                    E8M0 index c * (depth / block_b) + k / block_b; byte i is
                    lane i's code, looked up in the global A15 table for
                    block column c * LANES + i
``lq8_m1.hex``      per lane, the column-major weight words the single lane
                    reads (local column c at c * k_groups + kg)
``lq8_m3.hex``      per lane, the lane-local E8M0 codes, one per 32-bit word
``lq8_expect.hex``  per lane, per output element, [output word, accumulator]
``lq8_case.hex``    one record per case (layout in rtl/test/tb_a3_lq8.sv)
``lq8_meta.hex``    case count and the campaign totals

Images are regenerated deterministically at campaign time from the seed;
``testdata/rtl/abi3_lq8/manifest_<profile>_L<L>.json`` pins their digests.
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

import tools.am_e1_lane_reference as am  # noqa: E402
from tools.build_abi3_lane_vectors import (  # noqa: E402
    BF16, E2M1, FP8, WINDOWS, bf16_window, e2m1_random, e8m0_random, fp8_random,
    hex_lines, lane_case, numpy_sequential, pack_words,
)

SCHEMA = "opentallas.rtl.abi3_lq8_vectors.v1"
LANES = 8
CASE_STRIDE = 128
META_WORDS = 12
REGION_WORDS = 16384          # rtl/test/a3_lq8_top.sv REGION_WORDS
UNWRITTEN = 0xDEADBEEF
FLAG_RATE = 0x1
FLAG_FAULT = 0x2
FLAG_BLOCK_REFUSED = 0x4
STREAM_BITS_PER_LANE = 16

# Block-level details, transcribed from rtl/abi3/ot_a3_lq8.sv
DETAIL_BLOCK_COLUMNS = 16
DETAIL_BLOCK_STREAM_WIDTH = 17
DETAIL_NAMES = dict(am.DETAIL_NAMES)
DETAIL_NAMES[DETAIL_BLOCK_COLUMNS] = "block_columns_not_multiple_of_lanes"
DETAIL_NAMES[DETAIL_BLOCK_STREAM_WIDTH] = "block_stream_width"

MANIFEST_DIR = ROOT / "testdata/rtl/abi3_lq8"


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------
@dataclass
class BlockCase:
    name: str
    note: str
    rows: int
    cols: int
    depth: int
    dtype_a: int
    dtype_b: int
    group: int
    a_codes: np.ndarray
    b_codes: np.ndarray                 # [cols, depth], block columns
    scales_a: np.ndarray | None = None
    scales_b: np.ndarray | None = None  # global A15 order over block columns
    block_a: int = 0
    block_b: int = 0
    block_rows_a: int = 0
    block_rows_b: int = 0
    out_fp32: bool = False
    run_reference: bool = True
    rate: bool = False
    expect_detail: int | None = None
    expect_lane: int | None = None
    mode_name: str | None = None
    distinguishes_sequential: bool = False
    numpy_cross_check: bool = True
    # filled by the builder
    case_id: int = -1
    refused: bool = False
    lanes: list[am.LaneCase] = field(default_factory=list)
    results: list[am.CaseResult] = field(default_factory=list)
    lane_obs: list[am.Observable] = field(default_factory=list)
    block: am.Observable | None = None
    error_lane: int = 0
    a_base: int = 0
    scale_a_base: int = 0
    w_base: int = 0
    ws_base: int = 0
    b_bases: list[int] = field(default_factory=list)
    scale_b_bases: list[int] = field(default_factory=list)
    out_base: int = 0
    expect_offset: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def cols_per_lane(self) -> int:
        return self.cols // LANES

    @property
    def window(self) -> int:
        return self.rows * self.cols_per_lane


def tile_cols(pattern: np.ndarray, cols: int) -> np.ndarray:
    """Block column C takes pattern row C % len(pattern)."""
    assert cols % pattern.shape[0] == 0
    return np.tile(pattern, (cols // pattern.shape[0], 1))


def build_cases(rng: np.random.Generator, profile: str) -> list[BlockCase]:
    cases: list[BlockCase] = []

    def add(name, note, rows, cols, depth, a, b, *, dtype_a=BF16, dtype_b=BF16, group=1,
            run_reference=True, rate=False, expect_detail=None, expect_lane=None, mode_name=None,
            out_fp32=False, numpy_cross_check=True, distinguishes=False, scales_a=None,
            scales_b=None, block_a=0, block_b=0, block_rows_a=0, block_rows_b=0):
        a = np.ascontiguousarray(a).reshape(rows, depth) if rows * depth else np.zeros((rows, depth), dtype=np.uint16)
        b = np.ascontiguousarray(b).reshape(cols, depth) if cols * depth else np.zeros((cols, depth), dtype=np.uint16)
        cases.append(BlockCase(
            name=name, note=note, rows=rows, cols=cols, depth=depth, dtype_a=dtype_a,
            dtype_b=dtype_b, group=group, a_codes=a, b_codes=b,
            scales_a=None if scales_a is None else np.ascontiguousarray(scales_a, dtype=np.uint8),
            scales_b=None if scales_b is None else np.ascontiguousarray(scales_b, dtype=np.uint8),
            block_a=block_a, block_b=block_b, block_rows_a=block_rows_a, block_rows_b=block_rows_b,
            out_fp32=out_fp32, run_reference=run_reference, rate=rate, expect_detail=expect_detail,
            expect_lane=expect_lane, mode_name=mode_name, distinguishes_sequential=distinguishes,
            numpy_cross_check=numpy_cross_check,
        ))

    narrow = WINDOWS["narrow"]

    # -- shape corners: every relation between local columns and L, and K ------------
    for rows, cols, depth in ((1, 8, 1), (1, 8, 2), (1, 16, 1), (2, 8, 1), (1, 24, 5),
                              (1, 32, 3), (1, 40, 7), (1, 56, 2), (1, 64, 9), (2, 72, 4),
                              (3, 40, 7), (2, 48, 1), (4, 24, 13)):
        add(f"shape_{rows}x{cols}x{depth}",
            f"{rows} x {depth} against {cols} x {depth}: {cols // LANES} local columns per lane",
            rows, cols, depth, bf16_window(rng, (rows, depth), *narrow),
            bf16_window(rng, (cols, depth), *narrow))

    # -- the sequential lane's directed cases, widened to LANES lanes -----------------
    add("bf16_small", "4 x 16 against 64 x 16", 4, 64, 16,
        bf16_window(rng, (4, 16), *narrow), bf16_window(rng, (64, 16), *narrow))
    add("bf16_tile_edge", "9 x 33 against 72 x 33: nine local columns, three passes", 9, 72, 33,
        bf16_window(rng, (9, 33), *narrow), bf16_window(rng, (72, 33), *narrow))
    add("bf16_saturating", "accumulators inside binary32 and outside BF16: half the outputs saturate",
        3, 32, 2, np.tile(np.array([0x5F7F, 0x5D80], dtype=np.uint16), (3, 1)),
        tile_cols(np.array([[0x5F7F, 0x5DCC], [0x5F7F, 0x5DCC], [0x3F80, 0x4000], [0xBF80, 0x4040]],
                           dtype=np.uint16), 32))
    zero_a = np.zeros((4, 8), dtype=np.uint16)
    zero_a[:, ::2] = 0x8000
    zero_b = bf16_window(rng, (48, 8), *narrow)
    zero_b[:, 1::2] = 0x8000
    add("bf16_signed_zero", "every product is a signed exact zero: every result is +0", 4, 48, 8,
        zero_a, zero_b)
    add("bf16_reduction_order", "a small leading product then an exact cancellation", 4, 32, 3,
        np.array([[0x3F80, 0x4700, 0x4700], [0x4000, 0x4700, 0x4700],
                  [0x4080, 0x4700, 0x4700], [0x4100, 0x4700, 0x4700]], dtype=np.uint16),
        tile_cols(np.array([[0x3F80, 0x4700, 0xC700], [0x3F80, 0x3F80, 0x3F80],
                            [0x4000, 0x4700, 0xC700], [0xBF80, 0x4700, 0xC700]], dtype=np.uint16), 32))
    add("bf16_wide_reduction", "a 256-deep reduction on every lane", 2, 32, 256,
        bf16_window(rng, (2, 256), *narrow), bf16_window(rng, (32, 256), *narrow))

    # -- the retained subnormal paths -------------------------------------------------
    add("bf16_subnormal_operands", "BF16 subnormal operands on both sides", 2, 24, 8,
        bf16_window(rng, (2, 8), 0, 0), bf16_window(rng, (24, 8), 0, 0))
    add("bf16_subnormal_products", "products in the binary32 subnormal range", 3, 24, 16,
        bf16_window(rng, (3, 16), 50, 70), bf16_window(rng, (24, 16), 50, 70))
    add("bf16_rounded_products", "products below the 2**-149 grid", 3, 24, 16,
        bf16_window(rng, (3, 16), 0, 20), bf16_window(rng, (24, 16), 40, 70))
    add("bf16_subnormal_ties", "half-ulp products on the subnormal grid: ties to even", 2, 16, 4,
        np.array([[0x0001, 0x0003, 0x0001, 0x0003], [0x0003, 0x0001, 0x0001, 0x0001]], dtype=np.uint16),
        tile_cols(np.array([[0x3800, 0x3800, 0x3800, 0x3800], [0x3800, 0x3800, 0xB800, 0x3800]],
                           dtype=np.uint16), 16))
    add("bf16_subnormal_accumulation", "sums inside and across the binary32 subnormal range", 2, 16, 64,
        bf16_window(rng, (2, 64), 60, 66), bf16_window(rng, (16, 64), 60, 66))
    add("bf16_cancellation_to_zero", "exact cancellation inside the chain returns +0", 2, 16, 4,
        np.array([[0x4200, 0x4200, 0x3F80, 0x3F80], [0xC200, 0x4200, 0x4000, 0xC000]], dtype=np.uint16),
        tile_cols(np.array([[0x3F80, 0xBF80, 0x3F80, 0xBF80], [0x3F80, 0x3F80, 0x3F80, 0x3F80]],
                           dtype=np.uint16), 16))
    add("bf16_near_overflow", "accumulations near 2**128 without leaving binary32", 2, 16, 3,
        np.array([[0x7E80, 0x7E80, 0x7E00], [0x7F00, 0xFF00, 0x7F7F]], dtype=np.uint16),
        tile_cols(np.array([[0x3F80, 0x3F80, 0x3F80], [0x3F80, 0x3F80, 0xBF80]], dtype=np.uint16), 16))
    add("bf16_huge_exponents", "operands at the top of the BF16 range", 2, 24, 2,
        bf16_window(rng, (2, 2), 160, 185), bf16_window(rng, (24, 2), 160, 185))
    add("bf16_tiny_exponents", "operands at the bottom of the BF16 range", 2, 24, 12,
        bf16_window(rng, (2, 12), 1, 40), bf16_window(rng, (24, 12), 1, 40))

    # -- the seeded spread ----------------------------------------------------------------
    for index, (name, (low, high)) in enumerate(WINDOWS.items()):
        if name == "huge":
            continue
        add(f"spread_{name}", f"seeded spread, exponent window {low}..{high}", 5, 48, 40 + 7 * index,
            bf16_window(rng, (5, 40 + 7 * index), low, high),
            bf16_window(rng, (48, 40 + 7 * index), low, high))
    add("spread_mixed_signs_same_magnitude", "same-magnitude operands of random sign", 4, 32, 96,
        bf16_window(rng, (4, 96), 127, 127), bf16_window(rng, (32, 96), 127, 127))
    add("spread_fp32_partials", "binary32 partial output on every lane", 3, 40, 20,
        bf16_window(rng, (3, 20), *narrow), bf16_window(rng, (40, 20), *narrow), out_fp32=True)

    # -- the other formats at g = 1, and the scale table ----------------------------------
    add("fp8_fp8_g1", "FP8 on both sides at g = 1", 4, 64, 32,
        fp8_random(rng, (4, 32)), fp8_random(rng, (64, 32)), dtype_a=FP8, dtype_b=FP8)
    add("fp8_reduction_order_g1", "the order-sensitive construction on the FP8 path", 3, 24, 3,
        np.array([[0x01, 0x7E, 0x7E], [0x02, 0x7E, 0x7E], [0x04, 0x7E, 0x7E]], dtype=np.uint8),
        tile_cols(np.array([[0x38, 0x7E, 0xFE], [0x38, 0x38, 0x38], [0x40, 0x7E, 0xFE]], dtype=np.uint8), 24),
        dtype_a=FP8, dtype_b=FP8)
    add("fp8_k_major_g1", "64 x 128 over a 4-deep reduction: 16 local columns per lane", 64, 128, 4,
        fp8_random(rng, (64, 4), 0, 7), fp8_random(rng, (128, 4), 0, 7), dtype_a=FP8, dtype_b=FP8)
    add("mxfp4_fp8_block_scaled_g1", "E2M1 activations and FP8 weights with 32-element blocks, g = 1",
        4, 64, 64, e2m1_random(rng, (4, 64)), fp8_random(rng, (64, 64)), dtype_a=E2M1, dtype_b=FP8,
        scales_a=e8m0_random(rng, 4 * 2, 120, 134), scales_b=e8m0_random(rng, 64 * 2, 120, 134),
        block_a=32, block_b=32)
    add("fp8_a15_block_rows4_g1",
        "A15 weight scales shared by 4 consecutive block columns (inside one stream word)", 3, 64, 64,
        bf16_window(rng, (3, 64), *narrow), fp8_random(rng, (64, 64)), dtype_a=BF16, dtype_b=FP8,
        scales_b=e8m0_random(rng, 16 * 2, 120, 134), block_b=32, block_rows_b=4)
    add("fp8_a15_block_rows16_g1",
        "A15 weight scales shared by 16 consecutive block columns (two local columns per lane)",
        3, 64, 64, bf16_window(rng, (3, 64), *narrow), fp8_random(rng, (64, 64)), dtype_a=BF16,
        dtype_b=FP8, scales_b=e8m0_random(rng, 4 * 2, 120, 134), block_b=32, block_rows_b=16)
    add("fp8_a15_block_rows3_g1", "an A15 row block that does not divide the lane count", 2, 48, 32,
        bf16_window(rng, (2, 32), *narrow), fp8_random(rng, (48, 32)), dtype_a=BF16, dtype_b=FP8,
        scales_b=e8m0_random(rng, 16 * 1, 120, 134), block_b=32, block_rows_b=3)
    add("bf16_scaled_subnormal_pin",
        "np.float32 pin: a scaled BF16 operand below the binary32 subnormal grid is rounded to it",
        2, 16, 32, bf16_window(rng, (2, 32), 1, 30), bf16_window(rng, (16, 32), 120, 130),
        scales_a=np.array([100, 90, 20, 0], dtype=np.uint8), block_a=16)
    add("bf16_scaled_both_sides", "E8M0 scales on both BF16 operands, g = 1", 2, 24, 32,
        bf16_window(rng, (2, 32), *narrow), bf16_window(rng, (24, 32), *narrow),
        scales_a=e8m0_random(rng, 2 * 2, 100, 150), scales_b=e8m0_random(rng, 24 * 2, 100, 150),
        block_a=16, block_b=16)

    # -- group modes: g set by the weight format --------------------------------------------
    for rows, cols, depth in ((1, 8, 2), (1, 8, 1), (1, 24, 5), (2, 32, 16), (3, 56, 31), (4, 64, 64)):
        add(f"fp8_g2_{rows}x{cols}x{depth}", f"FP8 x FP8 at g = 2, {rows} x {cols} x {depth}",
            rows, cols, depth, fp8_random(rng, (rows, depth)), fp8_random(rng, (cols, depth)),
            dtype_a=FP8, dtype_b=FP8, group=2)
    add("fp8_g2_extremes", "448 and 2**-9 mixed inside groups", 3, 24, 16,
        rng.choice(np.array([0x7E, 0x01, 0xFE, 0x81, 0x38, 0x08], dtype=np.uint8), size=(3, 16)),
        rng.choice(np.array([0x7E, 0x01, 0xFE, 0x81, 0x38, 0x08], dtype=np.uint8), size=(24, 16)),
        dtype_a=FP8, dtype_b=FP8, group=2)
    add("fp8_g2_group_cancellation", "p0 = -p1 inside every group", 2, 16, 8,
        np.tile(np.array([0x48, 0x48], dtype=np.uint8), (2, 4)),
        np.tile(np.array([0x50, 0xD0], dtype=np.uint8), (16, 4)), dtype_a=FP8, dtype_b=FP8, group=2)
    dist_a = np.full((1, 86), 0x7E, dtype=np.uint8)
    dist_b = np.full((8, 86), 0x7E, dtype=np.uint8)
    dist_a[0, 84], dist_b[:, 84] = 0x3C, 0x38
    dist_a[0, 85], dist_b[:, 85] = 0x30, 0xB8
    add("fp8_g2_distinguishes_association",
        "acc above 2**24 then the group (1.5, -0.5): one rounding per group on every lane",
        1, 8, 86, dist_a, dist_b, dtype_a=FP8, dtype_b=FP8, group=2, distinguishes=True)
    add("fp8_g2_scaled_block32", "g = 2 with 32-element blocks on both sides", 4, 48, 64,
        fp8_random(rng, (4, 64)), fp8_random(rng, (48, 64)), dtype_a=FP8, dtype_b=FP8, group=2,
        scales_a=e8m0_random(rng, 4 * 2, 110, 140), scales_b=e8m0_random(rng, 48 * 2, 110, 140),
        block_a=32, block_b=32)
    add("fp8_g2_scaled_block128_a15", "activation block 128, weight 128 x 4 (A15)", 4, 64, 128,
        fp8_random(rng, (4, 128)), fp8_random(rng, (64, 128)), dtype_a=FP8, dtype_b=FP8, group=2,
        scales_a=e8m0_random(rng, 4, 115, 135), scales_b=e8m0_random(rng, 16, 115, 135),
        block_a=128, block_b=128, block_rows_b=4)
    add("fp8_g2_scaled_tiny", "2**-127 scales on 2**-9 operands", 2, 16, 32,
        fp8_random(rng, (2, 32), 0, 2), fp8_random(rng, (16, 32), 0, 2), dtype_a=FP8, dtype_b=FP8,
        group=2, scales_a=np.array([0, 5], dtype=np.uint8), block_a=32)
    add("fp8_g2_fp32_out", "binary32 partial output at g = 2", 2, 24, 16, fp8_random(rng, (2, 16)),
        fp8_random(rng, (24, 16)), dtype_a=FP8, dtype_b=FP8, group=2, out_fp32=True)
    add("e2m1_fp8_g2_deepseek_pair",
        "the DeepSeek pair on the block: MXFP4 activations, FP8 weights, 32-element blocks, g = 2",
        4, 64, 64, e2m1_random(rng, (4, 64)), fp8_random(rng, (64, 64)), dtype_a=E2M1, dtype_b=FP8,
        group=2, scales_a=e8m0_random(rng, 4 * 2, 120, 134), scales_b=e8m0_random(rng, 64 * 2, 120, 134),
        block_a=32, block_b=32)
    for rows, cols, depth in ((1, 8, 4), (1, 8, 3), (1, 16, 7), (2, 40, 32), (3, 48, 45), (4, 64, 64)):
        add(f"mxfp4_g4_{rows}x{cols}x{depth}", f"FP8 x E2M1 weights at g = 4, {rows} x {cols} x {depth}",
            rows, cols, depth, fp8_random(rng, (rows, depth)), e2m1_random(rng, (cols, depth)),
            dtype_a=FP8, dtype_b=E2M1, group=4)
    add("e2m1_e2m1_g4", "E2M1 on both sides at g = 4", 2, 32, 32, e2m1_random(rng, (2, 32)),
        e2m1_random(rng, (32, 32)), dtype_a=E2M1, dtype_b=E2M1, group=4)
    add("mxfp4_g4_scaled_block32", "FP8 activations, E2M1 weights, 32-element blocks both sides", 4, 64, 64,
        fp8_random(rng, (4, 64)), e2m1_random(rng, (64, 64)), dtype_a=FP8, dtype_b=E2M1, group=4,
        scales_a=e8m0_random(rng, 4 * 2, 120, 134), scales_b=e8m0_random(rng, 64 * 2, 120, 134),
        block_a=32, block_b=32)
    add("mxfp4_g4_scaled_a15", "FP8 block 128 against E2M1 with a 32 x 4 A15 block", 4, 64, 128,
        fp8_random(rng, (4, 128)), e2m1_random(rng, (64, 128)), dtype_a=FP8, dtype_b=E2M1, group=4,
        scales_a=e8m0_random(rng, 4, 115, 135), scales_b=e8m0_random(rng, 16 * 4, 115, 135),
        block_a=128, block_b=32, block_rows_b=4)
    add("mxfp4_g4_group_cancellation", "groups 1 x (6, -6, 3, -3): exact zero group sums", 2, 16, 8,
        np.full((2, 8), 0x38, dtype=np.uint8),
        np.tile(np.array([0x7, 0xF, 0x5, 0xD], dtype=np.uint8), (16, 2)), dtype_a=FP8, dtype_b=E2M1,
        group=4)
    dist4_a = np.full((1, 6248), 0x7E, dtype=np.uint8)
    dist4_b = np.full((8, 6248), 0x7, dtype=np.uint8)
    dist4_a[0, 6244:6248] = [0x38, 0x38, 0x38, 0x38]
    dist4_b[:, 6244:6248] = [0x3, 0x9, 0x0, 0x0]
    add("mxfp4_g4_distinguishes_association",
        "acc above 2**24 then the group (1.5, -0.5, 0, 0) = +1.0, a tie rounded once, on every lane",
        1, 8, 6248, dist4_a, dist4_b, dtype_a=FP8, dtype_b=E2M1, group=4, distinguishes=True)
    add("mxfp4_g4_fp32_out", "binary32 partial output at g = 4", 2, 24, 16, fp8_random(rng, (2, 16)),
        e2m1_random(rng, (24, 16)), dtype_a=FP8, dtype_b=E2M1, group=4, out_fp32=True)
    add("mxfp4_g4_subnormal_pin", "scaled operands and sums in the binary32 subnormal range", 2, 16, 32,
        fp8_random(rng, (2, 32), 0, 3), e2m1_random(rng, (16, 32)), dtype_a=FP8, dtype_b=E2M1,
        group=4, scales_a=np.array([0, 0], dtype=np.uint8),
        scales_b=np.tile(np.array([0, 1], dtype=np.uint8), 8), block_a=32, block_b=32)

    # -- every failure mode, on the shared side (every lane) and on one lane's column ------
    nonfinite_a = bf16_window(rng, (2, 8), *narrow)
    nonfinite_a[0, 0] = 0x7F80
    add("fault_operand_a_nonfinite", "a BF16 infinity in the shared activation: every lane traps at once",
        2, 24, 8, nonfinite_a, bf16_window(rng, (24, 8), *narrow),
        expect_detail=am.DETAIL_A_NONFINITE, expect_lane=0, mode_name="nonfinite_bf16_operand_a")
    nonfinite_b = bf16_window(rng, (24, 8), *narrow)
    nonfinite_b[5, 0] = 0xFFC0
    add("fault_operand_b_nonfinite", "a BF16 NaN in block column 5: lane 5 traps, the others complete",
        2, 24, 8, bf16_window(rng, (2, 8), *narrow), nonfinite_b,
        expect_detail=am.DETAIL_B_NONFINITE, expect_lane=5, mode_name="nonfinite_bf16_operand_b")
    reserved_a = fp8_random(rng, (2, 8))
    reserved_a[0, 0] = 0x7F
    add("fault_operand_a_reserved", "the reserved E4M3FN code 0x7f in the shared activation", 2, 24, 8,
        reserved_a, fp8_random(rng, (24, 8)), dtype_a=FP8, dtype_b=FP8,
        expect_detail=am.DETAIL_A_RESERVED, expect_lane=0, mode_name="reserved_e4m3fn_operand_a")
    reserved_b = fp8_random(rng, (24, 8))
    reserved_b[3, 0] = 0xFF
    add("fault_operand_b_reserved", "the reserved E4M3FN code 0xff in block column 3", 2, 24, 8,
        fp8_random(rng, (2, 8)), reserved_b, dtype_a=FP8, dtype_b=FP8,
        expect_detail=am.DETAIL_B_RESERVED, expect_lane=3, mode_name="reserved_e4m3fn_operand_b")
    add("fault_scale_a_reserved", "the reserved E8M0 code in the shared activation scales", 2, 24, 32,
        fp8_random(rng, (2, 32)), fp8_random(rng, (24, 32)), dtype_a=FP8, dtype_b=FP8,
        scales_a=np.array([0xFF, 127], dtype=np.uint8), block_a=32,
        expect_detail=am.DETAIL_SCALE_A_RESERVED, expect_lane=0, mode_name="reserved_e8m0_scale_a")
    scale_b_reserved = np.full((24,), 127, dtype=np.uint8)
    scale_b_reserved[6] = 0xFF
    add("fault_scale_b_reserved", "the reserved E8M0 code in block column 6's weight scale", 2, 24, 32,
        fp8_random(rng, (2, 32)), fp8_random(rng, (24, 32)), dtype_a=FP8, dtype_b=FP8,
        scales_b=scale_b_reserved, block_b=32,
        expect_detail=am.DETAIL_SCALE_B_RESERVED, expect_lane=6, mode_name="reserved_e8m0_scale_b")
    add("fault_scale_a_range", "2**127 x 448 on the shared side: the scale application overflows",
        2, 24, 32, np.full((2, 32), 0x7E, dtype=np.uint8), bf16_window(rng, (24, 32), *narrow),
        dtype_a=FP8, dtype_b=BF16, scales_a=np.full((2,), 254, dtype=np.uint8), block_a=32,
        expect_detail=am.DETAIL_SCALE_A_RANGE, expect_lane=0, mode_name="scale_application_range_a")
    scale_b_range = np.full((24,), 127, dtype=np.uint8)
    scale_b_range[7] = 254
    add("fault_scale_b_range", "the same on block column 7's weight scale", 2, 24, 32,
        bf16_window(rng, (2, 32), *narrow), np.full((24, 32), 0x7E, dtype=np.uint8),
        dtype_a=BF16, dtype_b=FP8, scales_b=scale_b_range, block_b=32,
        expect_detail=am.DETAIL_SCALE_B_RANGE, expect_lane=7, mode_name="scale_application_range_b")
    add("fault_product_range", "the largest finite BF16 squared leaves binary32", 2, 24, 4,
        np.full((2, 4), 0x7F7F, dtype=np.uint16), np.full((24, 4), 0x7F7F, dtype=np.uint16),
        expect_detail=am.DETAIL_PRODUCT_RANGE, expect_lane=0, mode_name="product_range")
    add("fault_accumulate_range", "finite products whose ascending-K sum leaves binary32", 2, 24, 4,
        np.full((2, 4), 0x5F00, dtype=np.uint16), np.full((24, 4), 0x5F00, dtype=np.uint16),
        expect_detail=am.DETAIL_ACCUMULATE_RANGE, expect_lane=0, mode_name="accumulate_range")
    add("fault_shape_zero_depth", "a degenerate extent is refused by every lane", 2, 24, 0,
        np.zeros((2, 0), dtype=np.uint16), np.zeros((24, 0), dtype=np.uint16),
        expect_detail=am.DETAIL_SHAPE, expect_lane=0, mode_name="shape", numpy_cross_check=False)

    # -- late faults: each lane's written set is its own -------------------------------------
    late_a = bf16_window(rng, (3, 6), *narrow)
    late_a[1, 4] = 0x7F80
    add("fault_late_operand", "an infinity at row 1, k 4 of the shared activation: row 0 is written",
        3, 56, 6, late_a, bf16_window(rng, (56, 6), *narrow), expect_detail=am.DETAIL_A_NONFINITE,
        expect_lane=0)
    late_b = bf16_window(rng, (56, 6), *narrow)
    late_b[42, 2] = 0x7F80
    add("fault_late_column", "an infinity in block column 42 (lane 2, local 5), k 2",
        2, 56, 6, bf16_window(rng, (2, 6), *narrow), late_b, expect_detail=am.DETAIL_B_NONFINITE,
        expect_lane=2)
    late_acc_a = bf16_window(rng, (2, 5), 100, 110)
    late_acc_b = bf16_window(rng, (40, 5), 100, 110)
    late_acc_a[1, :] = 0x5F00
    late_acc_b[25, :] = 0x5F00
    add("fault_late_accumulate", "an accumulation overflow at row 1, block column 25 (lane 1, local 3)",
        2, 40, 5, late_acc_a, late_acc_b, expect_detail=am.DETAIL_ACCUMULATE_RANGE, expect_lane=1)
    two_b = bf16_window(rng, (56, 6), *narrow)
    two_b[42, 2] = 0xFFC0                     # lane 2, local 5, k 2: NaN
    two_b[6, :] = 0x7F7F                      # lane 6, local 0: every product overflows
    add("fault_two_lanes_two_modes",
        "lane 6 leaves binary32 at its first product, lane 2 meets a NaN later: the block reports "
        "lane 2 (the lowest index) and every lane keeps its own class and detail",
        2, 56, 6, bf16_window(rng, (2, 6), *narrow), two_b, expect_detail=am.DETAIL_B_NONFINITE,
        expect_lane=2)
    late_g2 = fp8_random(rng, (56, 12))
    late_g2[38, 9] = 0x7F                     # lane 6, local 4, group 4
    add("g2_fault_late", "a reserved code in block column 38 (lane 6, local 4), group 4",
        2, 56, 12, fp8_random(rng, (2, 12)), late_g2, dtype_a=FP8, dtype_b=FP8, group=2,
        expect_detail=am.DETAIL_B_RESERVED, expect_lane=6)

    # -- the block's own refusals, placed after an operation that left every lane
    # with non-zero counters and lane 6 with a class: a refused operation must
    # report zero counters and no lane class, not the previous operation's.
    add("fault_block_columns", "12 columns on 8 lanes: refused by the block before any lane starts",
        2, 12, 8, bf16_window(rng, (2, 8), *narrow), bf16_window(rng, (12, 8), *narrow),
        expect_detail=DETAIL_BLOCK_COLUMNS, expect_lane=0, mode_name="block_columns",
        run_reference=False, numpy_cross_check=False)
    add("fault_block_stream_width",
        "E2M1 activations against FP8 weights at g = 4: four weight codes do not fit 2 B per lane",
        2, 16, 8, e2m1_random(rng, (2, 8)), fp8_random(rng, (16, 8)), dtype_a=E2M1, dtype_b=FP8,
        group=4, expect_detail=DETAIL_BLOCK_STREAM_WIDTH, expect_lane=0, mode_name="block_stream_width",
        run_reference=False, numpy_cross_check=False)

    if profile == "full":
        # -- the normal-range BF16 sweep: 1,507,328 products over the block ------------------
        for index, (rows, cols, depth, window) in enumerate(
                ((8, 64, 1024, "narrow"), (8, 64, 1024, "wide"), (8, 64, 512, "same"),
                 (4, 48, 1024, "mixed"))):
            low, high = WINDOWS[window]
            add(f"sweep_{index}_{window}_{rows}x{cols}x{depth}",
                f"normal-range BF16 sweep block {index}: {rows} x {cols} outputs over K = {depth}, "
                f"exponent window {low}..{high}", rows, cols, depth,
                bf16_window(rng, (rows, depth), low, high), bf16_window(rng, (cols, depth), low, high))
        # -- the block rate in every g ------------------------------------------------------------
        add("rate_bf16_8x48x1024", "block rate at g = 1: 8 x 48 outputs over K = 1024", 8, 48, 1024,
            bf16_window(rng, (8, 1024), *narrow), bf16_window(rng, (48, 1024), *narrow), rate=True)
        add("rate_fp8_g2_8x48x1024", "block rate at g = 2", 8, 48, 1024, fp8_random(rng, (8, 1024)),
            fp8_random(rng, (48, 1024)), dtype_a=FP8, dtype_b=FP8, group=2, rate=True)
        add("rate_mxfp4_g4_8x48x1024", "block rate at g = 4 (E2M1 weights)", 8, 48, 1024,
            fp8_random(rng, (8, 1024)), e2m1_random(rng, (48, 1024)), dtype_a=FP8, dtype_b=E2M1,
            group=4, rate=True)
    else:
        add("rate_bf16_4x48x256", "block rate at g = 1 (quick)", 4, 48, 256,
            bf16_window(rng, (4, 256), *narrow), bf16_window(rng, (48, 256), *narrow), rate=True)
        add("rate_fp8_g2_4x48x256", "block rate at g = 2 (quick)", 4, 48, 256, fp8_random(rng, (4, 256)),
            fp8_random(rng, (48, 256)), dtype_a=FP8, dtype_b=FP8, group=2, rate=True)
        add("rate_mxfp4_g4_4x48x256", "block rate at g = 4 (quick)", 4, 48, 256, fp8_random(rng, (4, 256)),
            e2m1_random(rng, (48, 256)), dtype_a=FP8, dtype_b=E2M1, group=4, rate=True)
    return cases


# ---------------------------------------------------------------------------
# The block's lane split and the expectations
# ---------------------------------------------------------------------------
def lane_split(case: BlockCase) -> list[am.LaneCase]:
    """Lane i's own case: block columns c * LANES + i, lane-local scale table."""
    cpl = case.cols_per_lane
    lanes: list[am.LaneCase] = []
    for i in range(LANES):
        b_local = np.ascontiguousarray(case.b_codes[i::LANES]) if case.cols else np.zeros((0, case.depth), dtype=np.uint16)
        scales_local = None
        if case.scales_b is not None:
            per_col = case.depth // case.block_b if case.block_b else 0
            table = np.zeros((cpl * per_col,), dtype=np.uint8)
            if case.block_b and case.depth % case.block_b == 0:
                for c in range(cpl):
                    for kb in range(per_col):
                        table[c * per_col + kb] = case.scales_b[am.scale_index(
                            c * LANES + i, kb * case.block_b, case.depth, case.block_b,
                            case.block_rows_b)]
            scales_local = table
        lanes.append(lane_case(case.rows, cpl, case.depth, case.dtype_a, case.dtype_b, case.group,
                               case.a_codes, b_local, scales_a=case.scales_a, scales_b=scales_local,
                               block_a=case.block_a, block_b=case.block_b,
                               block_rows_a=case.block_rows_a, block_rows_b=0,
                               out_fp32=case.out_fp32))
    return lanes


EMPTY = am.CaseResult([], [], [], [])
ZERO_OBS = am.Observable(0, 0, 0, 0, 0, 0, 0)


def evaluate_cases(cases: list[BlockCase], adder_stages: int) -> None:
    for case in cases:
        width_b = am.element_width(case.dtype_b)
        if case.cols % LANES:
            case.refused = True
            detail = DETAIL_BLOCK_COLUMNS
        elif width_b * case.group > STREAM_BITS_PER_LANE:
            case.refused = True
            detail = DETAIL_BLOCK_STREAM_WIDTH
        if case.refused:
            case.lanes = []
            case.results = [EMPTY] * LANES
            case.lane_obs = [ZERO_OBS] * LANES
            case.block = am.Observable(am.ERR_SHAPE, detail, 0, 0, 0, 0, 0)
            case.error_lane = 0
            case.run_reference = False
        else:
            case.lanes = lane_split(case)
            case.results = [am.evaluate(lane) if am.shape_admissible(lane) else EMPTY
                            for lane in case.lanes]
            case.lane_obs = [am.pipelined_observable(lane, result, adder_stages)
                             for lane, result in zip(case.lanes, case.results)]
            faulting = [i for i, obs in enumerate(case.lane_obs) if obs.error_code]
            case.error_lane = faulting[0] if faulting else 0
            first = case.lane_obs[case.error_lane]
            case.block = am.Observable(
                first.error_code, first.error_detail,
                sum(o.out_count for o in case.lane_obs), sum(o.saturations for o in case.lane_obs),
                sum(o.lane_ops for o in case.lane_obs), sum(o.products for o in case.lane_obs),
                sum(o.written for o in case.lane_obs),
            )
        if case.expect_detail is not None and case.block.error_detail != case.expect_detail:
            raise RuntimeError(f"{case.name}: expected fault detail {case.expect_detail}, model gives "
                               f"{case.block.error_detail}")
        if case.expect_detail is None and case.block.error_code != 0:
            raise RuntimeError(f"{case.name}: unexpected fault {case.block.error_detail}")
        if case.expect_lane is not None and case.error_lane != case.expect_lane:
            raise RuntimeError(f"{case.name}: expected the fault on lane {case.expect_lane}, model "
                               f"gives lane {case.error_lane}")
        # g = 1 without a fault: the functional simulator on the global operands
        # must reproduce the per-lane results reassembled through the block's
        # column assignment -- this pins the permutation and the scale table.
        if (case.numpy_cross_check and case.group == 1 and case.block.error_code == 0
                and case.rows and case.cols and case.depth):
            global_case = lane_case(case.rows, case.cols, case.depth, case.dtype_a, case.dtype_b, 1,
                                    case.a_codes, case.b_codes, scales_a=case.scales_a,
                                    scales_b=case.scales_b, block_a=case.block_a, block_b=case.block_b,
                                    block_rows_a=case.block_rows_a, block_rows_b=case.block_rows_b,
                                    out_fp32=case.out_fp32)
            via_numpy = numpy_sequential(global_case).reshape(case.rows, case.cols)
            canonical = np.where(via_numpy == 0x80000000, 0, via_numpy)
            cpl = case.cols_per_lane
            reassembled = np.zeros((case.rows, case.cols), dtype=np.uint32)
            for i, result in enumerate(case.results):
                acc = np.array(result.acc_words, dtype=np.uint32).reshape(case.rows, cpl)
                reassembled[:, i::LANES] = acc
            if not np.array_equal(canonical, reassembled):
                differing = int(np.count_nonzero(canonical != reassembled))
                raise RuntimeError(f"{case.name}: {differing} accumulators differ between the block's "
                                   "reassembled AM-E1 result and sequential_matmul_binary32")
            case.extras["numpy_cross_check"] = (
                "sequential_matmul_binary32 on the global operands equals the per-lane AM-E1 results "
                "reassembled through the block's column assignment")
        if case.distinguishes_sequential:
            for i, (lane, result) in enumerate(zip(case.lanes, case.results)):
                sequential = am.sequential_chain_acc(lane, 0, 0)
                am_e1 = result.acc_words[0]
                if sequential is None or sequential == am_e1:
                    raise RuntimeError(f"{case.name}: lane {i} does not distinguish AM-E1 from the "
                                       f"sequential association ({am_e1:#010x})")
                case.extras.setdefault("sequential_association_acc", f"{sequential:#010x}")
                case.extras.setdefault("am_e1_acc", f"{am_e1:#010x}")


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
def stream_words(case: BlockCase, adder_stages: int) -> list[int]:
    """The weight stream: one word per block lane-op in the lanes' issue order."""
    cpl = case.cols_per_lane
    groups = (case.depth + case.group - 1) // case.group
    per_lane = [pack_words(lane.b_codes, case.dtype_b, case.group) for lane in case.lanes]
    mask = (1 << STREAM_BITS_PER_LANE) - 1
    words: list[int] = []
    passes = (cpl + adder_stages - 1) // adder_stages
    for _row in range(case.rows):
        for pass_index in range(passes):
            active = min(adder_stages, cpl - pass_index * adder_stages)
            for kg in range(groups):
                for ci in range(active):
                    column = pass_index * adder_stages + ci
                    word = 0
                    for i, lane_words in enumerate(per_lane):
                        code = lane_words[column * groups + kg]
                        assert code == (code & mask), "weight codes exceed the stream width"
                        word |= code << (STREAM_BITS_PER_LANE * i)
                    words.append(word)
    return words


def scale_table_words(case: BlockCase) -> list[int]:
    """The weight scale table: one word per lane-local index, byte i for lane i."""
    tables = [lane.scales_b for lane in case.lanes]
    if any(t is None for t in tables):
        return []
    length = len(tables[0])
    assert all(len(t) == length for t in tables)
    return [sum(int(tables[i][idx]) << (8 * i) for i in range(LANES)) for idx in range(length)]


def emit(cases: list[BlockCase], out_dir: Path, adder_stages: int, profile: str,
         seed: int) -> dict[str, Any]:
    m0: list[int] = []
    m2: list[int] = []
    mw: list[int] = []
    mws: list[int] = []
    m1: list[int] = []
    m3: list[int] = []
    expect: list[int] = []
    records: list[int] = []
    out_pointer = 0
    totals = {"lane_ops": 0, "products": 0, "outputs": 0, "faults": 0,
              "reference": 0, "ref_outputs": 0}
    summaries: list[dict[str, Any]] = []
    for case_id, case in enumerate(cases):
        case.case_id = case_id
        case.a_base = len(m0)
        m0.extend(pack_words(case.a_codes, case.dtype_a, case.group))
        case.scale_a_base = len(m2)
        if case.scales_a is not None:
            m2.extend(int(c) for c in case.scales_a)
        case.w_base = len(mw)
        case.ws_base = len(mws)
        case.b_bases = [0] * LANES
        case.scale_b_bases = [0] * LANES
        if not case.refused:
            mw.extend(stream_words(case, adder_stages))
            mws.extend(scale_table_words(case))
            for i, lane in enumerate(case.lanes):
                case.b_bases[i] = len(m1)
                m1.extend(pack_words(lane.b_codes, case.dtype_b, case.group))
                case.scale_b_bases[i] = len(m3)
                if lane.scales_b is not None:
                    m3.extend(int(c) for c in lane.scales_b)
        window = case.window
        case.out_base = out_pointer
        out_pointer += window
        if out_pointer > REGION_WORDS:
            raise RuntimeError("the suite's output windows exceed one result region")
        case.expect_offset = len(expect)
        for i in range(LANES):
            result = case.results[i]
            for element in range(window):
                expect.append(result.out_words[element] if element < len(result.out_words) else 0)
                expect.append(result.acc_words[element] if element < len(result.acc_words) else 0)
        block = case.block
        assert block is not None
        flags = ((FLAG_RATE if case.rate else 0) | (FLAG_FAULT if block.error_code else 0)
                 | (FLAG_BLOCK_REFUSED if case.refused else 0))
        record = [
            case.rows, case.cols, case.depth, case.dtype_a, case.dtype_b, case.group,
            case.a_base, case.w_base,
            1 if case.scales_a is not None else 0, 1 if case.scales_b is not None else 0,
            case.block_a, case.block_b, case.block_rows_a, case.block_rows_b,
            case.scale_a_base, case.ws_base, case.out_base, 1 if case.out_fp32 else 0,
            block.error_code, block.error_detail, case.error_lane, block.out_count,
            block.saturations, block.lane_ops, block.products,
            1 if case.run_reference else 0, case.cols_per_lane, case.expect_offset, flags,
            case_id, window, LANES,
        ]
        assert len(record) == 32
        record.extend(case.b_bases)
        record.extend(case.scale_b_bases)
        record.extend(o.written for o in case.lane_obs)
        record.extend(o.error_code for o in case.lane_obs)
        record.extend(o.error_detail for o in case.lane_obs)
        record.extend(o.lane_ops for o in case.lane_obs)
        record.extend(o.products for o in case.lane_obs)
        record.extend(o.out_count for o in case.lane_obs)
        record.extend(o.saturations for o in case.lane_obs)
        assert len(record) == 104
        record.extend([0] * (CASE_STRIDE - len(record)))
        records.extend(record)
        totals["lane_ops"] += block.lane_ops
        totals["products"] += block.products
        totals["outputs"] += block.written
        totals["faults"] += 1 if block.error_code else 0
        totals["reference"] += 1 if case.run_reference else 0
        totals["ref_outputs"] += block.written if case.run_reference else 0
        summaries.append({
            "id": case_id, "name": case.name, "note": case.note,
            "rows": case.rows, "cols": case.cols, "cols_per_lane": case.cols_per_lane,
            "depth": case.depth, "dtype_a": case.dtype_a, "dtype_b": case.dtype_b,
            "group": case.group, "scaled_a": case.scales_a is not None,
            "scaled_b": case.scales_b is not None, "block_a": case.block_a, "block_b": case.block_b,
            "block_rows_a": case.block_rows_a, "block_rows_b": case.block_rows_b,
            "out_fp32": case.out_fp32, "run_reference": case.run_reference, "rate": case.rate,
            "block_refused": case.refused, "products": case.rows * case.cols * case.depth,
            "stream_words": (case.rows * case.cols_per_lane
                             * ((case.depth + case.group - 1) // case.group)) if not case.refused else 0,
            "mode_name": case.mode_name,
            "expected": {
                "block": dict(block.__dict__, error_lane=case.error_lane),
                "lanes": [o.__dict__ for o in case.lane_obs],
            },
            "extras": case.extras,
        })
    meta = [len(cases), totals["lane_ops"], totals["products"], totals["outputs"],
            totals["faults"], totals["reference"], CASE_STRIDE, totals["ref_outputs"], LANES]
    meta.extend([0] * (META_WORDS - len(meta)))
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "lq8_m0.hex": hex_lines(m0, 16),
        "lq8_m2.hex": hex_lines(m2 or [0], 8),
        "lq8_w.hex": hex_lines(mw or [0], 4 * LANES),
        "lq8_ws.hex": hex_lines(mws or [0], 2 * LANES),
        "lq8_m1.hex": hex_lines(m1 or [0], 16),
        "lq8_m3.hex": hex_lines(m3 or [0], 8),
        "lq8_case.hex": hex_lines(records, 8),
        "lq8_expect.hex": hex_lines(expect or [0], 8),
        "lq8_meta.hex": hex_lines(meta, 8),
    }
    digests: dict[str, str] = {}
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
        digests[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    rate_lines = [
        {"case": case.case_id, "lane_ops": case.block.lane_ops, "products": case.block.products,
         "group": case.group}
        for case in cases if case.rate and case.block is not None
    ]
    modes: dict[str, dict[str, Any]] = {}
    for case in cases:
        if case.mode_name and case.block is not None:
            modes.setdefault(case.mode_name, {
                "case": case.case_id, "name": case.name,
                "error_code": case.block.error_code, "error_detail": case.block.error_detail,
                "error_lane": case.error_lane,
                "detail_name": DETAIL_NAMES.get(case.block.error_detail, "?"),
                "lanes": [[o.error_code, o.error_detail] for o in case.lane_obs],
            })
    marker = (
        f"PASS: ABI3 lq8 cases={len(cases)} lane_ops={totals['lane_ops']} "
        f"products={totals['products']} outputs={totals['outputs']} faults={totals['faults']} "
        f"reference_cases={totals['reference']} reference_outputs={totals['ref_outputs']}"
    )
    manifest = {
        "schema": SCHEMA,
        "suite": "lq8",
        "profile": profile,
        "seed": seed,
        "lanes": LANES,
        "adder_stages": adder_stages,
        "case_stride": CASE_STRIDE,
        "region_words": REGION_WORDS,
        "unwritten_sentinel": UNWRITTEN,
        "column_assignment": "lane i owns block columns c * LANES + i; lane-local column c",
        "stream_layout": (
            "one 16-byte word per block lane-op in the lanes' issue order (row, pass of L "
            "interleaved local columns, k-group, column within the pass); lane i's g weight codes "
            "at bits [16 i +: 16], code j at [j * width +: width]"),
        "scale_table_layout": (
            "one 8-byte word per lane-local E8M0 index c * (depth / block_b) + k / block_b; "
            "byte i holds lane i's code from the global A15 table for block column c * LANES + i"),
        "geometry": {
            "m0_words": len(m0), "m2_words": len(m2), "w_words": len(mw), "ws_words": len(mws),
            "m1_words": len(m1), "m3_words": len(m3), "result_words_per_region": out_pointer,
            "expect_words": len(expect), "case_words": len(records),
        },
        "totals": totals,
        "sweep_products": sum(c.rows * c.cols * c.depth for c in cases if c.name.startswith("sweep_")),
        "required_marker_prefix": marker,
        "rate_cases": rate_lines,
        "failure_modes": modes,
        "image_sha256": digests,
        "cases": summaries,
        "reference": {
            "model": "tools/am_e1_lane_reference.py",
            "rtl_reference": "rtl/abi3/ot_a3_lane_pipelined.sv, run once per block lane on that lane's own images",
            "numeric_authority": "runtime/reference/formats.py (fractions.Fraction, encode_binary32_rne)",
            "scale_semantics": "runtime/sim/engines/tensor.py::_operand (np.multiply dtype=float32)",
            "g1_cross_check": "runtime/sim/backend.py::sequential_matmul_binary32 on the global operands",
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                           encoding="utf-8")
    return manifest


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--adder-stages", type=int, default=3)
    parser.add_argument("--profile", choices=("quick", "full"), default="full")
    parser.add_argument("--seed", type=int, default=20260904)
    parser.add_argument("--write-manifest", action="store_true",
                        help="also copy the manifest into testdata/rtl/abi3_lq8")
    args = parser.parse_args(argv)
    rng = np.random.default_rng(args.seed)
    cases = build_cases(rng, args.profile)
    evaluate_cases(cases, args.adder_stages)
    manifest = emit(cases, args.out_dir, args.adder_stages, args.profile, args.seed)
    if args.write_manifest:
        target = MANIFEST_DIR / f"manifest_{args.profile}_L{args.adder_stages}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"manifest -> {target}")
    print(f"lq8: {len(cases)} cases, {manifest['totals']['lane_ops']} lane-ops, "
          f"{manifest['totals']['products']} products, {manifest['geometry']['w_words']} stream words "
          f"-> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
