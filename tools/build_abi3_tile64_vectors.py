#!/usr/bin/env python3
"""Build the operand images and expectations for the T64 tile campaign.

One suite, ``tile64``, for ``results/rtl/abi3_tile64.json``: every case is one
tile operation (rows, cols, K) that ``rtl/abi3/ot_a3_tile64.sv`` runs as a
static sequence of K-block operations over its eight LQ8s, and whose 64
partials per K-block the checkers capture and then feed, column by column,
through the RE8 endpoint (``rtl/abi3/ot_a3_tree_endpoint_fp32.sv``, beside the
tile in the top) in the chained shapes of the K-block tree.  The expectation
for every partial is the exact AM-E1 model (``tools/am_e1_lane_reference.py``)
run per lane per K-block (item 1 of the association), and the expectation for
every tree root is ``re8_chain`` over those partials (item 2), asserted equal
to ``reduction.ordered_sum(PAIRWISE_TREE)``; ``tile_output`` (item 4, the
output stage's single rounding) is recorded in the manifest and not checked
against RTL, because no output-stage RTL exists.

Column rule (the tile's): lane (j, i) = LQ8 j lane i owns global column
64 c + 8 j + i for its local column c in [0, cols / 64).

Images:

``t64_stream.hex``    the weight stream: one 1024-bit word per tile lane-op
                      cycle (as 32 lines of 32 bits, low word first), K-blocks
                      in order; inside a K-block the LQ8
                      issue-order rule (row, lane-pass of L interleaved local
                      columns, k-group, column within the pass); LQ8 j at
                      bits [128 j +: 128], lane i at [16 i +: 16], code j at
                      [j * width +: width]
``t64_ws.hex``        the weight scale table: one 512-bit word (16 lines of
                      32 bits) per (K-block, lane-local A15 index
                      c * (128 / block_b) + kb); byte 8 j + i is lane (j, i)'s code
``t64_act.hex``       the activation image the H-tree model broadcasts: per
                      case, K-block slices of rows x ceil(depth_b / g) 64-bit
                      words (two lines each) at a stride of rows x ceil(128 / g)
``t64_act_scale.hex`` the activation E8M0 slices, one code per line
``t64_case.hex``      one record per case (layout in rtl/test/tb_a3_tile64.sv)
``t64_expect.hex``    per lane, per K-block, per element: the binary32 partial;
                      then per (row, column): the tree root
``t64_meta.hex``      case count and the campaign totals

Images are regenerated deterministically at campaign time from the seed;
``testdata/rtl/abi3_tile64/manifest_<profile>_L<L>_W<source>.json`` pins
their digests.
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
    BF16, E2M1, FP8, WINDOWS, bf16_window, e2m1_random, e8m0_random, fp8_random, hex_lines,
    lane_case, pack_words,
)

SCHEMA = "opentallas.rtl.abi3_tile64_vectors.v1"
LQ8S = 8
LANES = 8
TILE_LANES = LQ8S * LANES
KBLOCK = am.KBLOCK
LEAVES = 8
CASE_STRIDE = 320
META_WORDS = 12
REGION_WORDS = 8192           # rtl/test/a3_tile64_top.sv REGION_WORDS
RING_WORDS = 32               # STAGING_BUFFERS x STAGING_BYTES / 128 at the vehicle
ACT_WORDS = 2048              # the tile's activation FIFO (two slices)
ACT_SCALE_WORDS = 64
UNWRITTEN = 0xDEADBEEF
DONT_CARE = 0xFFFFFFFF
FLAG_RATE = 0x1
FLAG_FAULT = 0x2
FLAG_REFUSED = 0x4
FLAG_BLOCK_UNCHECKED = 0x8    # the faulting K-block's partials are not specified (a tile-level fault)
FLAG_SDN_LIMIT = 0x10
FLAG_SDN_IGNORE_CREDIT = 0x20
STREAM_BITS_PER_LANE = 16

# Tile-level details, transcribed from rtl/abi3/ot_a3_tile64.sv
DETAIL_BLOCK_COLUMNS = 16
DETAIL_BLOCK_STREAM_WIDTH = 17
DETAIL_TILE_COLUMNS = 18
DETAIL_TILE_KBLOCK = 19
DETAIL_TILE_OUT_FORMAT = 20
DETAIL_TILE_STAGING_UNDERRUN = 21
DETAIL_TILE_ACT_RANGE = 22
DETAIL_TILE_STAGING_OVERRUN = 23
DETAIL_NAMES = dict(am.DETAIL_NAMES)
DETAIL_NAMES.update({
    DETAIL_BLOCK_COLUMNS: "block_columns_not_multiple_of_lanes",
    DETAIL_BLOCK_STREAM_WIDTH: "block_stream_width",
    DETAIL_TILE_COLUMNS: "tile_columns_not_multiple_of_64",
    DETAIL_TILE_KBLOCK: "tile_kblock",
    DETAIL_TILE_OUT_FORMAT: "tile_out_format",
    DETAIL_TILE_STAGING_UNDERRUN: "tile_staging_underrun",
    DETAIL_TILE_ACT_RANGE: "tile_act_range",
    DETAIL_TILE_STAGING_OVERRUN: "tile_staging_overrun",
})
MANIFEST_DIR = ROOT / "testdata/rtl/abi3_tile64"


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------
@dataclass
class TileCase:
    name: str
    note: str
    rows: int
    cols: int
    depth: int
    dtype_a: int
    dtype_b: int
    group: int
    a_codes: np.ndarray
    b_codes: np.ndarray                     # [cols, depth] global columns
    scales_a: np.ndarray | None = None
    scales_b: np.ndarray | None = None      # global A15 order
    block_a: int = 0
    block_b: int = 0
    block_rows_a: int = 0
    block_rows_b: int = 0
    kblock: int = KBLOCK
    out_fp32: bool = False                  # the output stage's dtype (recorded only)
    op_out_fp32: int = 1                    # what the descriptor says (0 provokes the refusal)
    rate: bool = False
    expect_detail: int | None = None
    expect_kblock: int | None = None
    expect_lq8: int | None = None
    expect_lane: int | None = None
    mode_name: str | None = None
    sdn_limit: int | None = None            # words the SDN delivers (None: all)
    sdn_ignore_credit: bool = False
    act_base: int = 0                       # op_a_base (nonzero provokes DETAIL_TILE_ACT_RANGE)
    shape: str | None = None
    distinguishes: bool = False
    # filled by the builder
    case_id: int = -1
    blocks: int = 0
    refused: bool = False
    tile_fault_detail: int = 0              # a run-time tile fault (21..23) expected in block 0
    partials: list[list[list[int]]] = field(default_factory=list)   # [block][lane][element]
    obs: list[list[am.Observable]] = field(default_factory=list)   # [block][lane]
    error_code: int = 0
    error_detail: int = 0
    error_kblock: int = 0
    error_lq8: int = 0
    error_lane: int = 0
    blocks_written: int = 0
    written_in_fault_block: list[int] = field(default_factory=list)
    lq8_codes: list[int] = field(default_factory=list)
    lq8_details: list[int] = field(default_factory=list)
    lane_codes: list[int] = field(default_factory=list)
    lane_details: list[int] = field(default_factory=list)
    out_count: int = 0
    mac_count: int = 0
    product_count: int = 0
    underruns: int = DONT_CARE
    stream_consumed: int = DONT_CARE
    roots: list[int] = field(default_factory=list)                 # row-major, tree-checked cases
    outputs: list[tuple[int, bool]] = field(default_factory=list)  # tile_output per root
    tree_checked: bool = False
    tree_vectors: int = 0
    words_per_block: list[int] = field(default_factory=list)
    a_base: int = 0
    a_stride: int = 0
    sa_base: int = 0
    sa_stride: int = 0
    w_base: int = 0
    w_words: int = 0
    ws_base: int = 0
    ws_stride: int = 0
    out_base: int = 0
    out_stride: int = 0
    act_img_base: int = 0
    act_slice_full: int = 0
    act_slice_last: int = 0
    scale_img_base: int = 0
    scale_slice_full: int = 0
    scale_slice_last: int = 0
    expect_partial_offset: int = 0
    expect_root_offset: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def cols_per_lane(self) -> int:
        return self.cols // TILE_LANES

    @property
    def window(self) -> int:
        return self.rows * self.cols_per_lane

    def depth_of(self, b: int) -> int:
        return min(self.kblock, self.depth - b * self.kblock)

    def kgroups(self, b: int) -> int:
        return (self.depth_of(b) + self.group - 1) // self.group


def tile_cols(pattern: np.ndarray, cols: int) -> np.ndarray:
    assert cols % pattern.shape[0] == 0
    return np.tile(pattern, (cols // pattern.shape[0], 1))


# Per-profile geometry.  ``full`` is the design's own contract set (decode K = 4,096 and
# 12,288, the prefill roof at rows = 16); ``contract`` is the set the two-simulator campaign
# records -- every contract shape, at a size the slower simulator can run: the tile evaluates
# 64 lanes every cycle and Icarus Verilog 11 simulates it about 150x slower than the pinned
# Verilator (measured, this session: the full set is 93 s of Verilator and hours of Icarus),
# so the two-simulator record keeps the shapes and shortens K, the row count and the tail
# rather than dropping a format or a fault.  ``quick`` is the development set and the one the
# secondary builds (STAGING_IN_TILE = 0, WEIGHT_SOURCE = 1) use to exercise their generate
# branches.  The fault cases are the same in every profile.
PROFILE_GEOMETRY: dict[str, dict[str, Any]] = {
    "quick": {"worked_depth": 1024, "decode": [(192, 256), (64, 256)], "prefill": (2, 192, 256),
              "batch": (2, 64, 256), "extras": None, "tail": None, "k12288": False},
    "contract": {"worked_depth": 4096, "decode": [(192, 1024), (64, 1024)], "prefill": (4, 192, 512),
                 "batch": (2, 64, 512), "extras": (64, 512), "tail": (64, 1088), "k12288": False},
    "full": {"worked_depth": 4096, "decode": [(192, 4096), (64, 1024)], "prefill": (16, 192, 1024),
             "batch": (4, 64, 1024), "extras": (64, 1024), "tail": (192, 4160), "k12288": True},
}


def build_cases(rng: np.random.Generator, profile: str, weight_source: int) -> list[TileCase]:
    cases: list[TileCase] = []
    narrow = WINDOWS["narrow"]

    def add(name, note, rows, cols, depth, a, b, *, dtype_a=BF16, dtype_b=BF16, group=1, kblock=KBLOCK,
            rate=False, expect_detail=None, expect_kblock=None, expect_lq8=None, expect_lane=None,
            mode_name=None, out_fp32=False, op_out_fp32=1, scales_a=None, scales_b=None, block_a=0,
            block_b=0, block_rows_a=0, block_rows_b=0, sdn_limit=None, sdn_ignore_credit=False,
            act_base=0, shape=None, distinguishes=False):
        a = np.ascontiguousarray(a).reshape(rows, depth) if rows * depth else np.zeros((rows, depth), dtype=np.uint16)
        b = np.ascontiguousarray(b).reshape(cols, depth) if cols * depth else np.zeros((cols, depth), dtype=np.uint16)
        cases.append(TileCase(
            name=name, note=note, rows=rows, cols=cols, depth=depth, dtype_a=dtype_a, dtype_b=dtype_b,
            group=group, a_codes=a, b_codes=b,
            scales_a=None if scales_a is None else np.ascontiguousarray(scales_a, dtype=np.uint8),
            scales_b=None if scales_b is None else np.ascontiguousarray(scales_b, dtype=np.uint8),
            block_a=block_a, block_b=block_b, block_rows_a=block_rows_a, block_rows_b=block_rows_b,
            kblock=kblock, out_fp32=out_fp32, op_out_fp32=op_out_fp32, rate=rate, expect_detail=expect_detail,
            expect_kblock=expect_kblock, expect_lq8=expect_lq8, expect_lane=expect_lane, mode_name=mode_name,
            sdn_limit=sdn_limit, sdn_ignore_credit=sdn_ignore_credit, act_base=act_base, shape=shape,
            distinguishes=distinguishes,
        ))

    def scaled_fp8(rows, cols, depth, group, dtype_a=FP8, dtype_b=FP8, block_b=32, block_a=128, block_rows_b=0):
        a = fp8_random(rng, (rows, depth)) if dtype_a == FP8 else e2m1_random(rng, (rows, depth))
        b = fp8_random(rng, (cols, depth)) if dtype_b == FP8 else e2m1_random(rng, (cols, depth))
        rpb = block_rows_b if block_rows_b else 1
        sa = e8m0_random(rng, rows * (depth // block_a), 120, 134)
        sb = e8m0_random(rng, ((cols + rpb - 1) // rpb) * (depth // block_b), 120, 134)
        return dict(a=a, b=b, dtype_a=dtype_a, dtype_b=dtype_b, group=group, scales_a=sa, scales_b=sb,
                    block_a=block_a, block_b=block_b, block_rows_b=block_rows_b)

    geom = PROFILE_GEOMETRY[profile]

    # -- the worked example of section 4.3 as a tile column ------------------------------------
    depth = geom["worked_depth"]
    blocks = depth // KBLOCK
    a = np.full((1, depth), 0x3F80, dtype=np.uint16)                       # 1.0 everywhere
    b = bf16_window(rng, (64, depth), *narrow)
    b[0, :] = 0
    b[0, 0] = 0x4B80                                                       # 2**24 at k = 0
    b[0, 128::128] = 0x3F80                                                # 1.0 at the head of blocks 1..B-1
    add("worked_example_column", f"column 0: P_0 = 2**24, P_1..P_{blocks - 1} = 1.0 -> the tree's root; "
        "a sequential chain over K would absorb every 1.0 at 2**24; the other 63 columns random", 1, 64,
        depth, a, b, distinguishes=True, shape=f"decode K={depth}")

    # -- decode shapes (rows = 1) -----------------------------------------------------------------------
    for cols, depth in geom["decode"]:
        rate = cols == 192
        add(f"decode_bf16_1x{cols}x{depth}", f"BF16 g = 1, {cols} columns, K = {depth}: {depth // KBLOCK} K-blocks",
            1, cols, depth, bf16_window(rng, (1, depth), *narrow), bf16_window(rng, (cols, depth), *narrow),
            rate=rate, shape=f"decode K={depth}")
        p = scaled_fp8(1, cols, depth, 2)
        add(f"decode_fp8_g2_1x{cols}x{depth}", f"FP8 x FP8 g = 2, activation block 128, weight block 32, K = {depth}",
            1, cols, depth, p["a"], p["b"], dtype_a=FP8, dtype_b=FP8, group=2, scales_a=p["scales_a"],
            scales_b=p["scales_b"], block_a=128, block_b=32, rate=rate, shape=f"decode K={depth}")
        p = scaled_fp8(1, cols, depth, 4, dtype_a=FP8, dtype_b=E2M1)
        add(f"decode_mxfp4_g4_1x{cols}x{depth}", f"FP8 activations x E2M1 weights g = 4, blocks 128 / 32, K = {depth}",
            1, cols, depth, p["a"], p["b"], dtype_a=FP8, dtype_b=E2M1, group=4, scales_a=p["scales_a"],
            scales_b=p["scales_b"], block_a=128, block_b=32, rate=rate, shape=f"decode K={depth}")
    if geom["k12288"]:
        add("decode_bf16_1x192x12288", "BF16 g = 1, 192 columns, K = 12,288: 96 K-blocks, the 12 -> 6 -> 3 -> 2 -> 1 tree",
            1, 192, 12288, bf16_window(rng, (1, 12288), *narrow), bf16_window(rng, (192, 12288), *narrow),
            rate=True, shape="decode K=12288")
    if geom["tail"]:
        cols, depth = geom["tail"]
        add(f"decode_bf16_short_tail_1x{cols}x{depth}",
            f"K = {depth}: {depth // KBLOCK} full K-blocks and a final block of {depth % KBLOCK} (unscaled)",
            1, cols, depth, bf16_window(rng, (1, depth), *narrow), bf16_window(rng, (cols, depth), *narrow),
            shape=f"decode K={depth}")
    if geom["extras"]:
        cols, depth = geom["extras"]
        p = scaled_fp8(1, cols, depth, 2, block_rows_b=4)
        add("decode_fp8_g2_a15_rows4", "A15 weight scales shared by 4 consecutive global columns", 1, cols, depth,
            p["a"], p["b"], dtype_a=FP8, dtype_b=FP8, group=2, scales_a=p["scales_a"], scales_b=p["scales_b"],
            block_a=128, block_b=32, block_rows_b=4, shape=f"decode K={depth}")
        add(f"decode_bf16_out_bf16_1x{cols}x{depth}", "the output stage's BF16 rounding recorded for every root",
            1, cols, depth, bf16_window(rng, (1, depth), *narrow), bf16_window(rng, (cols, depth), *narrow),
            out_fp32=False, shape=f"decode K={depth}")
    # -- batch decode and the prefill contract shape -------------------------------------------------------
    rows, cols, depth = (*geom["batch"],) if len(geom["batch"]) == 3 else (geom["batch"][0], geom["batch"][1], 0)
    add(f"batch_bf16_{rows}x{cols}x{depth}", f"rows = {rows}: the lane's row-serial schedule, weights "
        "re-streamed per row", rows, cols, depth, bf16_window(rng, (rows, depth), *narrow),
        bf16_window(rng, (cols, depth), *narrow), shape=f"batch K={depth}")
    rows, cols, depth = geom["prefill"]
    p = scaled_fp8(rows, cols, depth, 2)
    add(f"prefill_fp8_g2_{rows}x{cols}x{depth}", f"the prefill contract shape (rows = {rows}, {cols} columns, "
        f"K = {depth}) at the lane roof, row-serial: section 4.5's activation-block-stationary schedule is "
        "not in the lane", rows, cols, depth, p["a"], p["b"], dtype_a=FP8, dtype_b=FP8, group=2,
        scales_a=p["scales_a"], scales_b=p["scales_b"], block_a=128, block_b=32, rate=True,
        shape=f"prefill K={depth}")
    # -- the qualification schedule: one K-block of K ------------------------------------------------------------
    add("qualification_kblock_k_2x64x256", "op_kblock = K: one K-block of 256, one leaf per column", 2, 64, 256,
        bf16_window(rng, (2, 256), *narrow), bf16_window(rng, (64, 256), *narrow), kblock=256,
        shape="qualification K=256")

    # -- faults: the tile's refusals ---------------------------------------------------------------------------------
    add("fault_tile_columns", "96 columns: refused before K-block 0", 1, 96, 256, bf16_window(rng, (1, 256), *narrow),
        bf16_window(rng, (96, 256), *narrow), expect_detail=DETAIL_TILE_COLUMNS, mode_name="tile_columns")
    add("fault_tile_kblock_value", "op_kblock = 64 is neither 128 nor K", 1, 64, 256, bf16_window(rng, (1, 256), *narrow),
        bf16_window(rng, (64, 256), *narrow), kblock=64, expect_detail=DETAIL_TILE_KBLOCK, mode_name="tile_kblock_value")
    p = scaled_fp8(1, 64, 256, 2)
    scales_a_short = e8m0_random(rng, 1 * (320 // 128 + 1), 120, 134)
    add("fault_tile_kblock_scaled_short_tail", "K = 320 on a scaled format: the short final block is refused", 1, 64,
        320, fp8_random(rng, (1, 320)), fp8_random(rng, (64, 320)), dtype_a=FP8, dtype_b=FP8, group=2,
        scales_a=scales_a_short, block_a=128, expect_detail=DETAIL_TILE_KBLOCK, mode_name="tile_kblock_scaled_short_tail")
    p = scaled_fp8(1, 64, 256, 2, block_b=48)
    add("fault_tile_kblock_block_not_dividing", "a weight scale block of 48 does not divide 128", 1, 64, 256, p["a"],
        p["b"], dtype_a=FP8, dtype_b=FP8, group=2, scales_a=p["scales_a"], scales_b=p["scales_b"], block_a=128,
        block_b=48, expect_detail=DETAIL_TILE_KBLOCK, mode_name="tile_kblock_block_not_dividing")
    add("fault_tile_out_format", "op_out_fp32 = 0: the tile emits binary32 partials only", 1, 64, 256,
        bf16_window(rng, (1, 256), *narrow), bf16_window(rng, (64, 256), *narrow), op_out_fp32=0,
        expect_detail=DETAIL_TILE_OUT_FORMAT, mode_name="tile_out_format")
    # -- faults: run-time tile faults ---------------------------------------------------------------------------------------
    if weight_source == 0:
        add("fault_tile_staging_underrun", "the SDN delivers half of K-block 0 and stops: the lanes read unfilled ring "
            "words, the tile counts the underruns and fails closed after the K-block", 1, 64, 512,
            bf16_window(rng, (1, 512), *narrow), bf16_window(rng, (64, 512), *narrow),
            expect_detail=DETAIL_TILE_STAGING_UNDERRUN, sdn_limit=64, mode_name="tile_staging_underrun")
        add("fault_tile_staging_overrun", "the SDN ignores its credit: a write lands on an unread ring word", 1, 64,
            512, bf16_window(rng, (1, 512), *narrow), bf16_window(rng, (64, 512), *narrow),
            expect_detail=DETAIL_TILE_STAGING_OVERRUN, sdn_ignore_credit=True, mode_name="tile_staging_overrun")
    add("fault_tile_act_range", "op_a_base places the activation slice beyond the FIFO", 1, 64, 256,
        bf16_window(rng, (1, 256), *narrow), bf16_window(rng, (64, 256), *narrow), act_base=ACT_WORDS - 16,
        expect_detail=DETAIL_TILE_ACT_RANGE, mode_name="tile_act_range")
    # -- faults: LQ8 and lane faults propagated through the tile -----------------------------------------------------------
    nan_a = bf16_window(rng, (1, 1024), *narrow)
    nan_a[0, 5 * 128 + 7] = 0x7F80
    add("fault_lane_shared_activation_block5", "an infinity at k = 647 of the shared activation: every lane faults "
        "in K-block 5, K-blocks 0..4 are written, no K-block 6", 1, 64, 1024, nan_a,
        bf16_window(rng, (64, 1024), *narrow), expect_detail=am.DETAIL_A_NONFINITE, expect_kblock=5, expect_lq8=0,
        expect_lane=0, mode_name="lane_operand_a_nonfinite")
    nan_b = bf16_window(rng, (128, 1024), *narrow)
    nan_b[64 + 8 * 3 + 5, 3 * 128 + 2] = 0xFFC0
    add("fault_lane_weight_column_block3", "a NaN in global column 93 (lane (3, 5), local column 1) at k = 386: that "
        "lane faults in K-block 3, the other 63 complete K-block 3, no K-block 4", 1, 128, 1024,
        bf16_window(rng, (1, 1024), *narrow), nan_b, expect_detail=am.DETAIL_B_NONFINITE, expect_kblock=3,
        expect_lq8=3, expect_lane=5, mode_name="lane_operand_b_nonfinite")
    ovf_a = bf16_window(rng, (1, 256), 100, 110)
    ovf_b = bf16_window(rng, (64, 256), 100, 110)
    ovf_a[0, :128] = 0x5F00
    ovf_b[8 * 6 + 1, :128] = 0x5F00
    add("fault_lane_accumulate_block0", "an accumulation overflow in lane (6, 1) during K-block 0", 1, 64, 256,
        ovf_a, ovf_b, expect_detail=am.DETAIL_ACCUMULATE_RANGE, expect_kblock=0, expect_lq8=6, expect_lane=1,
        mode_name="lane_accumulate_range")
    p = scaled_fp8(1, 64, 256, 2)
    sb = p["scales_b"].copy()
    sb[am.scale_index(8 * 2 + 4, 128, 256, 32, 0)] = 0xFF
    add("fault_lane_scale_b_reserved_block1", "the reserved E8M0 code on lane (2, 4)'s weight scale in K-block 1",
        1, 64, 256, p["a"], p["b"], dtype_a=FP8, dtype_b=FP8, group=2, scales_a=p["scales_a"], scales_b=sb,
        block_a=128, block_b=32, expect_detail=am.DETAIL_SCALE_B_RESERVED, expect_kblock=1, expect_lq8=2,
        expect_lane=4, mode_name="lane_scale_b_reserved")
    add("fault_lq8_stream_width", "E2M1 activations against FP8 weights at g = 4: every LQ8 refuses (four weight "
        "codes do not fit 2 B per lane), reported as K-block 0, LQ8 0", 1, 64, 256, e2m1_random(rng, (1, 256)),
        fp8_random(rng, (64, 256)), dtype_a=E2M1, dtype_b=FP8, group=4, expect_detail=DETAIL_BLOCK_STREAM_WIDTH,
        expect_kblock=0, expect_lq8=0, expect_lane=0, mode_name="lq8_stream_width")
    # after the faults, a clean operation: the tile's state does not leak
    add("clean_after_faults_1x64x512", "a clean operation after the fault cases", 1, 64, 512,
        bf16_window(rng, (1, 512), *narrow), bf16_window(rng, (64, 512), *narrow), shape="decode K=512")
    return cases


# ---------------------------------------------------------------------------
# Expectations
# ---------------------------------------------------------------------------
def lane_of(j: int, i: int) -> int:
    return j * LANES + i


_SUB_CACHE: dict[tuple[int, int], am.LaneCase] = {}


def block_subcase(case: TileCase, block: int) -> am.LaneCase:
    """The whole tile's case restricted to K-block ``block`` (cached per case)."""
    key = (id(case), block)
    sub = _SUB_CACHE.get(key)
    if sub is None:
        full = lane_case(case.rows, case.cols, case.depth, case.dtype_a, case.dtype_b, case.group, case.a_codes,
                         case.b_codes, scales_a=case.scales_a, scales_b=case.scales_b, block_a=case.block_a,
                         block_b=case.block_b, block_rows_a=case.block_rows_a, block_rows_b=case.block_rows_b,
                         out_fp32=True)
        sub = am.block_case(full, block, case.kblock)
        _SUB_CACHE[key] = sub
    return sub


def stream_fits(case: TileCase) -> bool:
    """The LQ8's stream-width rule: g weight codes fit 2 B per lane."""
    return am.element_width(case.dtype_b) * case.group <= STREAM_BITS_PER_LANE


def lane_block_case(case: TileCase, block: int, j: int, i: int) -> am.LaneCase:
    """Lane (j, i)'s own case for K-block ``block``: its columns, its scale table slice."""
    sub = block_subcase(case, block)
    cpl = case.cols_per_lane
    columns = [64 * c + 8 * j + i for c in range(cpl)]
    b_local = np.ascontiguousarray(sub.b_codes[columns])
    scales_local = None
    if sub.scales_b is not None:
        per_col = sub.depth // case.block_b if case.block_b and sub.depth % case.block_b == 0 else 0
        table = np.zeros((cpl * per_col,), dtype=np.uint8)
        for c in range(cpl):
            for kb in range(per_col):
                table[c * per_col + kb] = sub.scales_b[am.scale_index(
                    columns[c], kb * case.block_b, sub.depth, case.block_b, case.block_rows_b)]
        scales_local = table
    return lane_case(case.rows, cpl, sub.depth, case.dtype_a, case.dtype_b, case.group, sub.a_codes, b_local,
                     scales_a=sub.scales_a, scales_b=scales_local, block_a=case.block_a, block_b=case.block_b,
                     block_rows_a=case.block_rows_a, block_rows_b=0, out_fp32=True)


def words_per_block(case: TileCase, block: int) -> int:
    return case.rows * case.cols_per_lane * case.kgroups(block)


def evaluate_case(case: TileCase, adder_stages: int) -> None:
    L = adder_stages
    window = case.window
    # -- tile-level refusals, decided before K-block 0 ---------------------------------------
    detail = 0
    if case.cols % TILE_LANES or case.cols == 0:
        detail = DETAIL_TILE_COLUMNS
    elif case.depth == 0 or (case.kblock != KBLOCK and case.kblock != case.depth):
        detail = DETAIL_TILE_KBLOCK
    elif case.kblock == KBLOCK and case.depth % KBLOCK and (case.scales_a is not None or case.scales_b is not None):
        detail = DETAIL_TILE_KBLOCK
    elif case.kblock == KBLOCK and any(
            enabled and not (block and block & (block - 1) == 0 and block <= 128)
            for enabled, block in ((case.scales_a is not None, case.block_a), (case.scales_b is not None, case.block_b))):
        detail = DETAIL_TILE_KBLOCK
    elif not case.op_out_fp32:
        detail = DETAIL_TILE_OUT_FORMAT
    case.blocks = 1 if case.kblock == case.depth else (case.depth + KBLOCK - 1) // KBLOCK
    case.words_per_block = [words_per_block(case, b) for b in range(case.blocks)]
    case.lq8_codes = [0] * LQ8S
    case.lq8_details = [0] * LQ8S
    case.lane_codes = [0] * TILE_LANES
    case.lane_details = [0] * TILE_LANES
    case.written_in_fault_block = [0] * TILE_LANES
    if detail:
        case.refused = True
        case.error_code = am.ERR_SHAPE
        case.error_detail = detail
        case.blocks_written = 0
        case.underruns = 0
        case.stream_consumed = 0
        return

    # -- the K-block operations, lane by lane --------------------------------------------------------
    fault_block = None
    for b in range(case.blocks):
        block_partials: list[list[int]] = []
        block_obs: list[am.Observable] = []
        for lane in range(TILE_LANES):
            j, i = divmod(lane, LANES)
            if not stream_fits(case):
                # the LQ8 refuses the stream width before any lane starts
                block_obs.append(am.Observable(am.ERR_SHAPE, DETAIL_BLOCK_STREAM_WIDTH, 0, 0, 0, 0, 0))
                block_partials.append([0] * window)
                continue
            lc = lane_block_case(case, b, j, i)
            result = am.evaluate(lc) if am.shape_admissible(lc) else am.CaseResult([], [], [], [])
            obs = am.pipelined_observable(lc, result, L)
            block_obs.append(obs)
            block_partials.append([result.acc_words[e] if e < len(result.acc_words) else 0 for e in range(window)])
        case.partials.append(block_partials)
        case.obs.append(block_obs)
        if fault_block is None and any(o.error_code for o in block_obs):
            fault_block = b
            break

    # -- run-time tile faults expected in K-block 0 ---------------------------------------------------------
    tile_fault = 0
    if case.sdn_limit is not None and case.sdn_limit < case.words_per_block[0]:
        tile_fault = DETAIL_TILE_STAGING_UNDERRUN
    if case.sdn_ignore_credit:
        tile_fault = DETAIL_TILE_STAGING_OVERRUN
    if case.act_base + case.rows * case.kgroups(0) > ACT_WORDS:
        tile_fault = DETAIL_TILE_ACT_RANGE
    case.tile_fault_detail = tile_fault

    blocks_run = (fault_block + 1) if fault_block is not None else case.blocks
    if tile_fault:
        blocks_run = 1
    case.out_count = sum(o.out_count for b in range(blocks_run) for o in case.obs[b])
    case.mac_count = sum(o.lane_ops for b in range(blocks_run) for o in case.obs[b])
    case.product_count = sum(o.products for b in range(blocks_run) for o in case.obs[b])
    if tile_fault:
        case.error_code = am.ERR_SHAPE
        case.error_detail = tile_fault
        case.error_kblock = 0
        case.blocks_written = 0
        case.stream_consumed = case.words_per_block[0]
        case.underruns = (case.words_per_block[0] - case.sdn_limit) if tile_fault == DETAIL_TILE_STAGING_UNDERRUN else (
            0 if tile_fault == DETAIL_TILE_ACT_RANGE else DONT_CARE)
        if tile_fault == DETAIL_TILE_STAGING_OVERRUN:
            case.underruns = DONT_CARE
        # the lanes computed on unspecified data: their counters are still exact (no lane faults on
        # finite operands), their partials are not specified
        case.lq8_codes = [0] * LQ8S
        case.lq8_details = [0] * LQ8S
        return
    if fault_block is not None:
        obs = case.obs[fault_block]
        faulting = [lane for lane in range(TILE_LANES) if obs[lane].error_code]
        first = faulting[0]
        j, i = divmod(first, LANES)
        case.error_code = obs[first].error_code
        case.error_detail = obs[first].error_detail
        case.error_kblock = fault_block
        case.error_lq8 = j
        case.error_lane = i
        case.blocks_written = fault_block
        case.written_in_fault_block = [obs[lane].written for lane in range(TILE_LANES)]
        for lane in range(TILE_LANES):
            # an LQ8-level refusal (stream width) never starts its lanes; the LQ8
            # gates their classes off, so the tile reads zero for every lane
            if obs[lane].error_detail != DETAIL_BLOCK_STREAM_WIDTH:
                case.lane_codes[lane] = obs[lane].error_code
                case.lane_details[lane] = obs[lane].error_detail
        for jj in range(LQ8S):
            lanes_faulting = [ii for ii in range(LANES) if obs[lane_of(jj, ii)].error_code]
            if lanes_faulting:
                case.lq8_codes[jj] = obs[lane_of(jj, lanes_faulting[0])].error_code
                case.lq8_details[jj] = obs[lane_of(jj, lanes_faulting[0])].error_detail
        case.stream_consumed = DONT_CARE   # depends on the pipeline depth at which the lanes stop issuing
        case.underruns = 0
        return

    # -- no fault: every K-block written, the tree over the partials -----------------------------------------
    case.blocks_written = case.blocks
    case.underruns = 0
    case.stream_consumed = sum(case.words_per_block)
    case.tree_checked = True
    full = lane_case(case.rows, case.cols, case.depth, case.dtype_a, case.dtype_b, case.group, case.a_codes,
                     case.b_codes, scales_a=case.scales_a, scales_b=case.scales_b, block_a=case.block_a,
                     block_b=case.block_b, block_rows_a=case.block_rows_a, block_rows_b=case.block_rows_b,
                     out_fp32=case.out_fp32)
    vectors = 0
    cpl = case.cols_per_lane
    for row in range(case.rows):
        for n in range(case.cols):
            lane = n % TILE_LANES
            c = n // TILE_LANES
            leaves = [case.partials[b][lane][row * cpl + c] for b in range(case.blocks)]
            root, stages = am.re8_chain(leaves, LEAVES)
            vectors += sum(len(s["inputs"]) for s in stages)   # one leaf needs no endpoint: it is the root
            # the whole contract, independently: block_partials + re8_chain on the global case
            if case.distinguishes or (row == 0 and n < 2):
                direct = am.block_partials(full, row, n, case.kblock)
                if direct != leaves:
                    raise RuntimeError(f"{case.name}: lane-split partials of ({row}, {n}) differ from block_partials")
                if am.pairwise_tree(direct) != root:
                    raise RuntimeError(f"{case.name}: re8_chain differs from pairwise_tree at ({row}, {n})")
            case.roots.append(root)
            case.outputs.append(am.tile_output(root, case.out_fp32))
    case.tree_vectors = vectors
    if case.distinguishes:
        leaves = [case.partials[b][0][0] for b in range(case.blocks)]
        root = case.roots[0]
        sequential = am.sequential_chain_acc(full, 0, 0)
        if sequential is None or sequential == root:
            raise RuntimeError(f"{case.name}: column 0 does not distinguish the K-block tree from the sequential chain")
        case.extras["column0_block_partials"] = [f"{p:#010x}" for p in leaves[:4]] + ["..."]
        case.extras["column0_tree_root"] = f"{root:#010x}"
        case.extras["column0_sequential_over_k"] = f"{sequential:#010x}"
        # The section 4.3 worked example is stated for K = 4,096 (32 leaves): the tree gives
        # 0x4B80000F and the sequential chain over K absorbs every 1.0 at 2**24.  At a shorter K
        # the same column still distinguishes the two associations (checked above), but the
        # constants are the shorter tree's, so only the stated case is pinned to them.
        if case.depth == 4096 and (root != 0x4B80000F or sequential != 0x4B800000):
            raise RuntimeError(f"{case.name}: worked example mismatch {root:#010x} / {sequential:#010x}")


def check_expectation(case: TileCase) -> None:
    if case.expect_detail is not None:
        if case.error_detail != case.expect_detail:
            raise RuntimeError(f"{case.name}: expected detail {case.expect_detail}, model gives {case.error_detail}")
        if case.expect_kblock is not None and case.error_kblock != case.expect_kblock:
            raise RuntimeError(f"{case.name}: expected K-block {case.expect_kblock}, model gives {case.error_kblock}")
        if case.expect_lq8 is not None and case.error_lq8 != case.expect_lq8:
            raise RuntimeError(f"{case.name}: expected LQ8 {case.expect_lq8}, model gives {case.error_lq8}")
        if case.expect_lane is not None and case.error_lane != case.expect_lane:
            raise RuntimeError(f"{case.name}: expected lane {case.expect_lane}, model gives {case.error_lane}")
    elif case.error_code:
        raise RuntimeError(f"{case.name}: unexpected fault {DETAIL_NAMES.get(case.error_detail, case.error_detail)}")


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
def stream_words(case: TileCase, block: int, adder_stages: int) -> list[int]:
    """The stream of one K-block: one 1024-bit word per tile lane-op cycle."""
    cpl = case.cols_per_lane
    groups = case.kgroups(block)
    per_lane = []
    for lane in range(TILE_LANES):
        j, i = divmod(lane, LANES)
        lc = lane_block_case(case, block, j, i)
        per_lane.append(pack_words(lc.b_codes, case.dtype_b, case.group))
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
                    for lane, lane_words in enumerate(per_lane):
                        code = lane_words[column * groups + kg]
                        if code != (code & mask):
                            raise RuntimeError("weight codes exceed the stream width")
                        word |= code << (STREAM_BITS_PER_LANE * lane)
                    words.append(word)
    return words


def scale_table_words(case: TileCase, block: int) -> list[int]:
    if case.scales_b is None:
        return []
    tables = []
    for lane in range(TILE_LANES):
        j, i = divmod(lane, LANES)
        tables.append(lane_block_case(case, block, j, i).scales_b)
    length = len(tables[0])
    return [sum(int(tables[lane][idx]) << (8 * lane) for lane in range(TILE_LANES)) for idx in range(length)]


def chunks32(words: list[int], width: int) -> list[int]:
    """Split ``width``-bit words into 32-bit words, low word first."""
    out: list[int] = []
    mask = (1 << 32) - 1
    for word in words:
        for k in range(width // 32):
            out.append((word >> (32 * k)) & mask)
    return out


def emit(cases: list[TileCase], out_dir: Path, adder_stages: int, profile: str, seed: int,
         weight_source: int) -> dict[str, Any]:
    stream: list[int] = []
    ws: list[int] = []
    act: list[int] = []
    act_scale: list[int] = []
    expect: list[int] = []
    records: list[int] = []
    out_pointer = 0
    totals = {"lane_ops": 0, "products": 0, "partials": 0, "faults": 0, "roots": 0, "tree_vectors": 0,
              "kblocks": 0, "stream_words": 0}
    summaries: list[dict[str, Any]] = []
    for case_id, case in enumerate(cases):
        case.case_id = case_id
        cpl = case.cols_per_lane
        window = case.window
        blocks = case.blocks
        g = case.group
        # activation slices: stride rows x ceil(kblock / g), the last block shorter
        full_words = case.rows * ((case.kblock + g - 1) // g)
        case.a_stride = full_words
        case.act_img_base = len(act)
        rpb = case.block_rows_a if case.block_rows_a else 1
        row_blocks = (case.rows + rpb - 1) // rpb
        scale_full = row_blocks * (case.kblock // case.block_a) if case.scales_a is not None and case.block_a else 0
        case.sa_stride = scale_full
        case.scale_img_base = len(act_scale)
        for b in range(blocks):
            j = 0
            lc = lane_block_case(case, b, 0, 0) if not case.refused else None
            if lc is None:
                break
            slice_words = pack_words(lc.a_codes, case.dtype_a, g)
            act.extend(slice_words)
            act.extend([0] * (full_words - len(slice_words)))
            if scale_full:
                codes = [int(c) for c in lc.scales_a] if lc.scales_a is not None else []
                act_scale.extend(codes)
                act_scale.extend([0] * (scale_full - len(codes)))
        case.act_slice_full = full_words
        case.act_slice_last = case.rows * case.kgroups(blocks - 1) if not case.refused else full_words
        case.scale_slice_full = scale_full
        case.scale_slice_last = (row_blocks * (case.depth_of(blocks - 1) // case.block_a)
                                 if scale_full and not case.refused else scale_full)
        case.a_base = case.act_base
        case.sa_base = 0
        # the stream and the scale table
        case.w_base = len(stream)
        case.ws_base = len(ws)
        case.ws_stride = (cpl * (case.kblock // case.block_b)) if (case.scales_b is not None and case.block_b
                                                                    and case.kblock % case.block_b == 0) else 0
        if not case.refused and stream_fits(case):
            for b in range(blocks):
                stream.extend(stream_words(case, b, adder_stages))
                ws.extend(scale_table_words(case, b))
        case.w_words = len(stream) - case.w_base
        # results
        case.out_base = out_pointer
        case.out_stride = window
        out_pointer += blocks * window
        if out_pointer > REGION_WORDS:
            raise RuntimeError("the suite's output windows exceed one result region")
        case.expect_partial_offset = len(expect)
        for lane in range(TILE_LANES):
            for b in range(blocks):
                for e in range(window):
                    expect.append(case.partials[b][lane][e] if b < len(case.partials) else 0)
        case.expect_root_offset = len(expect)
        expect.extend(case.roots)
        flags = ((FLAG_RATE if case.rate else 0) | (FLAG_FAULT if case.error_code else 0)
                 | (FLAG_REFUSED if case.refused else 0)
                 | (FLAG_BLOCK_UNCHECKED if case.tile_fault_detail else 0)
                 | (FLAG_SDN_LIMIT if case.sdn_limit is not None else 0)
                 | (FLAG_SDN_IGNORE_CREDIT if case.sdn_ignore_credit else 0))
        sdn_limit = case.sdn_limit if case.sdn_limit is not None else case.w_words
        record = [
            case.rows, case.cols, case.depth, case.kblock, case.dtype_a, case.dtype_b, case.group,
            1 if case.scales_a is not None else 0, case.block_a, case.block_rows_a,
            1 if case.scales_b is not None else 0, case.block_b,
            case.a_base, case.a_stride, case.sa_base, case.sa_stride,
            case.w_base, case.w_words, case.ws_base, case.ws_stride, case.out_base, case.out_stride, case.op_out_fp32,
            blocks, flags,
            case.error_code, case.error_detail, case.error_kblock, case.error_lq8, case.error_lane,
            case.out_count, case.mac_count, case.product_count, case.underruns, case.stream_consumed,
            case.expect_partial_offset, window, case.expect_root_offset, case_id,
            case.act_img_base, case.act_slice_full, case.act_slice_last,
            case.scale_img_base, case.scale_slice_full, case.scale_slice_last,
            cpl, case.blocks_written, 1 if case.tree_checked else 0, sdn_limit, case.tree_vectors,
        ]
        assert len(record) == 50
        record.extend([0] * (64 - len(record)))
        record.extend(case.lq8_codes)
        record.extend(case.lq8_details)
        record.extend(case.written_in_fault_block)
        record.extend(case.lane_codes)
        record.extend(case.lane_details)
        assert len(record) == 272
        record.extend([0] * (CASE_STRIDE - len(record)))
        records.extend(record)
        blocks_run = 0 if case.refused else (case.error_kblock + 1 if case.error_code else blocks)
        checked_partials = 0
        if not case.refused:
            checked_partials = TILE_LANES * case.blocks_written * window
            if case.error_code and not case.tile_fault_detail and case.error_kblock < blocks:
                checked_partials += sum(case.written_in_fault_block)
        totals["lane_ops"] += case.mac_count
        totals["products"] += case.product_count
        totals["partials"] += checked_partials
        totals["faults"] += 1 if case.error_code else 0
        totals["roots"] += len(case.roots)
        totals["tree_vectors"] += case.tree_vectors
        totals["kblocks"] += blocks_run
        totals["stream_words"] += case.w_words
        summaries.append({
            "id": case_id, "name": case.name, "note": case.note, "shape": case.shape,
            "rows": case.rows, "cols": case.cols, "cols_per_lane": cpl, "depth": case.depth, "kblock": case.kblock,
            "blocks": blocks, "dtype_a": case.dtype_a, "dtype_b": case.dtype_b, "group": case.group,
            "scaled_a": case.scales_a is not None, "scaled_b": case.scales_b is not None,
            "block_a": case.block_a, "block_b": case.block_b, "block_rows_a": case.block_rows_a,
            "block_rows_b": case.block_rows_b, "out_fp32": case.out_fp32, "rate": case.rate,
            "refused": case.refused, "mode_name": case.mode_name, "stream_words": case.w_words,
            "words_per_block": case.words_per_block[:4] + (["..."] if blocks > 4 else []),
            "products": case.rows * case.cols * case.depth if not case.refused else 0,
            "tree_checked": case.tree_checked, "tree_vectors": case.tree_vectors,
            "expected": {
                "error_code": case.error_code, "error_detail": case.error_detail,
                "detail_name": DETAIL_NAMES.get(case.error_detail, "?"), "error_kblock": case.error_kblock,
                "error_lq8": case.error_lq8, "error_lane": case.error_lane, "out_count": case.out_count,
                "mac_count": case.mac_count, "product_count": case.product_count,
                "staging_underruns": None if case.underruns == DONT_CARE else case.underruns,
                "stream_words_consumed": None if case.stream_consumed == DONT_CARE else case.stream_consumed,
                "blocks_written": case.blocks_written,
            },
            "output_stage": ([{"root": f"{r:#010x}", "word": f"{w:#06x}" if not case.out_fp32 else f"{w:#010x}",
                               "saturated": s} for r, (w, s) in list(zip(case.roots, case.outputs))[:3]]
                             if case.tree_checked else []),
            "extras": case.extras,
        })
    meta = [len(cases), totals["lane_ops"], totals["products"], totals["partials"], totals["faults"],
            totals["roots"], CASE_STRIDE, totals["tree_vectors"], TILE_LANES, totals["kblocks"], 0, 0]
    assert len(meta) == META_WORDS
    out_dir.mkdir(parents=True, exist_ok=True)
    # Every image is emitted as 32-bit words (wide-element memories cost Icarus
    # minutes at compile time); the top assembles the 1024-bit stream word, the
    # 512-bit scale word and the 64-bit activation word from consecutive
    # 32-bit words, low word first.
    files = {
        "t64_stream.hex": hex_lines(chunks32(stream or [0], 16 * TILE_LANES), 8),
        "t64_ws.hex": hex_lines(chunks32(ws or [0], 8 * TILE_LANES), 8),
        "t64_act.hex": hex_lines(chunks32(act or [0], 64), 8),
        "t64_act_scale.hex": hex_lines(act_scale or [0], 8),
        "t64_case.hex": hex_lines(records, 8),
        "t64_expect.hex": hex_lines(expect or [0], 8),
        "t64_meta.hex": hex_lines(meta, 8),
    }
    digests: dict[str, str] = {}
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
        digests[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    modes: dict[str, dict[str, Any]] = {}
    for case in cases:
        if case.mode_name:
            modes[case.mode_name] = {
                "case": case.case_id, "name": case.name, "error_code": case.error_code,
                "error_detail": case.error_detail, "error_kblock": case.error_kblock, "error_lq8": case.error_lq8,
                "error_lane": case.error_lane, "detail_name": DETAIL_NAMES.get(case.error_detail, "?"),
            }
    marker = (f"PASS: ABI3 tile64 cases={len(cases)} lane_ops={totals['lane_ops']} products={totals['products']} "
              f"partials={totals['partials']} faults={totals['faults']} roots={totals['roots']} "
              f"tree_vectors={totals['tree_vectors']} kblocks={totals['kblocks']}")
    manifest = {
        "schema": SCHEMA, "suite": "tile64", "profile": profile, "seed": seed, "lanes": TILE_LANES,
        "lq8s": LQ8S, "adder_stages": adder_stages, "weight_source": weight_source, "kblock": KBLOCK,
        "case_stride": CASE_STRIDE, "region_words": REGION_WORDS, "unwritten_sentinel": UNWRITTEN,
        "ring_words": RING_WORDS, "act_words": ACT_WORDS,
        "column_assignment": "lane (j, i) = LQ8 j lane i owns global column 64 c + 8 j + i for local column c",
        "stream_layout": (
            "one 128-byte word per tile lane-op cycle, K-blocks in order; inside a K-block the LQ8 issue-order "
            "rule (row, lane-pass of L interleaved local columns, k-group, column within the pass); LQ8 j at "
            "bits [128 j +: 128], lane i at [16 i +: 16], code j at [j * width +: width]"),
        "scale_table_layout": (
            "one 64-byte word per (K-block, lane-local A15 index c * (128 / block_b) + kb) at op_ws_base + "
            "b * op_ws_block_stride; byte 8 j + i is lane (j, i)'s code from the global A15 table"),
        "activation_layout": (
            "per K-block a slice of rows x ceil(depth_b / g) 64-bit words (rows contiguous at the block's "
            "k-group count), delivered by the H-tree model into FIFO slice b mod 2 at op_a_base + (b mod 2) * "
            "op_a_block_stride; E8M0 codes likewise in A15 order over the block"),
        "geometry": {"stream_words": len(stream), "ws_words": len(ws), "act_words": len(act),
                     "act_scale_words": len(act_scale), "result_words_per_region": out_pointer,
                     "expect_words": len(expect), "case_words": len(records)},
        "totals": totals,
        "required_marker_prefix": marker,
        "rate_cases": [{"case": c.case_id, "name": c.name, "lane_ops": c.mac_count, "products": c.product_count,
                        "group": c.group, "blocks": c.blocks, "rows": c.rows, "cols_per_lane": c.cols_per_lane,
                        "issue_cycles_per_block_ideal": c.rows * c.cols_per_lane * ((KBLOCK + c.group - 1) // c.group)}
                       for c in cases if c.rate],
        "failure_modes": modes, "image_sha256": digests, "cases": summaries,
        "reference": {
            "model": "tools/am_e1_lane_reference.py (element_chain per lane per K-block; re8_chain over the partials)",
            "tree_source_of_truth": "runtime/sim/engines/reduction.py::ordered_sum, ReductionOrder.PAIRWISE_TREE",
            "numeric_authority": "runtime/reference/formats.py (fractions.Fraction, encode_binary32_rne)",
            "scale_semantics": "runtime/sim/engines/tensor.py::_operand (np.multiply dtype=float32)",
            "output_stage": "tile_output (narrow_output) recorded per root in the manifest; no output-stage RTL exists",
            "golden_model": ("runtime/sim/backend.py's blocked path is numpy/BLAS matmul and has not adopted AM-E1; "
                             "the expectation is the exact reference, not the functional simulator's contraction"),
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--adder-stages", type=int, default=3)
    parser.add_argument("--profile", choices=tuple(PROFILE_GEOMETRY), default="contract")
    parser.add_argument("--weight-source", type=int, choices=(0, 1), default=0)
    parser.add_argument("--seed", type=int, default=20260905)
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args(argv)
    rng = np.random.default_rng(args.seed)
    cases = build_cases(rng, args.profile, args.weight_source)
    for case in cases:
        evaluate_case(case, args.adder_stages)
        check_expectation(case)
    manifest = emit(cases, args.out_dir, args.adder_stages, args.profile, args.seed, args.weight_source)
    if args.write_manifest:
        target = MANIFEST_DIR / f"manifest_{args.profile}_L{args.adder_stages}_W{args.weight_source}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"manifest -> {target}")
    print(f"tile64: {len(cases)} cases, {manifest['totals']['lane_ops']} lane-ops, "
          f"{manifest['totals']['kblocks']} K-blocks, {manifest['geometry']['stream_words']} stream words, "
          f"{manifest['totals']['tree_vectors']} tree vectors -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
