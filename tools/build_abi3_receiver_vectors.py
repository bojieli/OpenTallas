#!/usr/bin/env python3
"""Build the images and expectations for the OR64 operand-receiver campaign.

``rtl/abi3/ot_a3_operand_receiver.sv`` takes a binary32 tree root off the link,
performs the output stage's single rounding to the consumer's activation
storage format, packs the consumer's 64-bit activation word, writes it on
``ot_a3_tile64``'s activation broadcast port and advances ``act_ready_kblocks``
when a K-block slice is complete.

The expectation is a model of that contract written here -- the packing rule is
the tile's own (a slice is rows x ceil(depth_b / g) words at op_a_base +
(b mod 2) x op_a_block_stride, and word w holds the g elements of one k-group at
element_width bits each), and the rounding is
``tools/am_e1_lane_reference.py``'s binary32 -> BF16 RNE, which is the function
``rtl/ot_fp32_rne_pkg.sv`` implements and the lane's own output stage uses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_abi3_lane_vectors import hex_lines  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_receiver_vectors.v1"
CASE_STRIDE = 24
META_WORDS = 8
ACT_WORDS = 2048              # rtl/test/a3_receiver_top.sv
ROOT_WORDS = 8192
CASE_WORDS = 2048
EXPECT_WORDS = 8192
UNWRITTEN = 0xDEADBEEFDEADBEEF

FMT_BF16 = 0x10
FMT_FP8_E4M3FN = 0x20

ERR_NONE = 0
ERR_OPERAND_NONFINITE = 1
ERR_SHAPE = 7

DETAIL_RECV_FORMAT = 33
DETAIL_RECV_WINDOW = 34
DETAIL_RECV_TAG_ORDER = 35
DETAIL_RECV_ACT_RANGE = 36
DETAIL_RECV_SLICE_OVERRUN = 37
DETAIL_RECV_ROOT_NONFINITE = 38

DETAIL_NAMES = {
    0: "none",
    DETAIL_RECV_FORMAT: "recv_format",
    DETAIL_RECV_WINDOW: "recv_window",
    DETAIL_RECV_TAG_ORDER: "recv_tag_order",
    DETAIL_RECV_ACT_RANGE: "recv_act_range",
    DETAIL_RECV_SLICE_OVERRUN: "recv_slice_overrun",
    DETAIL_RECV_ROOT_NONFINITE: "recv_root_nonfinite",
}

INJ_NONE = 0
INJ_DTYPE = 1
INJ_GROUP = 2
INJ_SCALED = 3
INJ_SLICE_ZERO = 4
INJ_WINDOW = 5
INJ_TAG_ORDER = 6
INJ_ACT_RANGE = 7
INJ_SLICE_OVERRUN = 8
INJ_NONFINITE = 9


def bf16_rne(code: int) -> tuple[int, int, int]:
    """(error, saturated, bf16 code) -- rtl/ot_fp32_rne_pkg.sv fp32_to_bf16_rne."""
    if (code >> 23) & 0xFF == 0xFF:
        return 1, 0, 0
    low = code & 0xFFFF
    increment = 1 if (low > 0x8000 or (low == 0x8000 and (code >> 16) & 1)) else 0
    rounded = ((code >> 16) + increment) & 0xFFFF
    saturated = 0
    result = rounded
    if (result >> 7) & 0xFF == 0xFF:
        result = ((code >> 31) << 15) | (0xFE << 7) | 0x7F
        saturated = 1
    if result & 0x7FFF == 0:
        result = 0
    return 0, saturated, result


class Case:
    def __init__(self, name: str, note: str, *, blocks: int, slice_words: int, group: int,
                 base: int = 0, stride: int | None = None, dtype: int = FMT_BF16,
                 scaled: int = 0, roots: int | None = None, inject: int = INJ_NONE,
                 gap: int = 0, bad_tag_at: int = 0, bad_tag: int = 0,
                 window: str = "normal") -> None:
        self.name = name
        self.note = note
        self.blocks = blocks
        self.slice_words = slice_words
        self.group = group
        self.dtype = dtype
        self.scaled = scaled
        self.base = base
        self.stride = slice_words if stride is None else stride
        self.roots = blocks * slice_words * group if roots is None else roots
        self.inject = inject
        self.gap = gap
        self.bad_tag_at = bad_tag_at
        self.bad_tag = bad_tag
        self.window = window
        self.case_id = -1
        self.root_base = 0
        self.act_expect_base = 0
        self.root_codes: list[int] = []
        self.act_expect: list[int] = []
        self.expect_code = ERR_NONE
        self.expect_detail = 0
        self.expect_tag = 0
        self.expect_words = 0
        self.expect_slices = 0
        self.expect_roots = 0
        self.expect_saturations = 0
        self.act_window = 0


def build_cases() -> list[Case]:
    return [
        Case("g1_b1_w64", "the two-tile chain's own geometry: one K-block slice of "
             "64 BF16 activations at g = 1, one element per 64-bit word",
             blocks=1, slice_words=64, group=1),
        Case("g1_b2_w64", "two slices: the FIFO's two regions, alternated",
             blocks=2, slice_words=64, group=1),
        Case("g1_b3_w32", "three slices: slice 2 rewrites slice 0's region",
             blocks=3, slice_words=32, group=1),
        Case("g2_b2_w32", "g = 2: two elements per activation word",
             blocks=2, slice_words=32, group=2),
        Case("g4_b2_w16", "g = 4: four elements per activation word",
             blocks=2, slice_words=16, group=4),
        Case("g1_b1_gap3", "three idle cycles between roots: arrival rate does not "
             "change what is delivered", blocks=1, slice_words=64, group=1, gap=3),
        Case("g1_b2_base", "a nonzero op_a_base", blocks=2, slice_words=32, group=1,
             base=256, stride=32),
        Case("g1_b1_saturating", "roots at the top of binary32: the narrowing "
             "saturates and is counted, and is not a fault",
             blocks=1, slice_words=16, group=1, window="saturating"),
        Case("g1_b1_tiny", "roots below the BF16 subnormal floor: they flush to zero",
             blocks=1, slice_words=16, group=1, window="tiny"),
        Case("refuse_dtype", "an activation format that is not BF16: fp32 -> FP8 is a "
             "two-output quantisation this block does not perform",
             blocks=1, slice_words=16, group=1, dtype=FMT_FP8_E4M3FN, inject=INJ_DTYPE),
        Case("refuse_group", "g = 3", blocks=1, slice_words=16, group=3, inject=INJ_GROUP),
        Case("refuse_scaled", "a block-scaled activation: the E8M0 interleave is "
             "unwritten", blocks=1, slice_words=16, group=1, scaled=1, inject=INJ_SCALED),
        Case("refuse_slice_zero", "a slice of no words", blocks=1, slice_words=0,
             group=1, roots=0, inject=INJ_SLICE_ZERO),
        Case("refuse_window", "a slice that does not fit the activation FIFO",
             blocks=1, slice_words=64, group=1, base=ACT_WORDS - 8, inject=INJ_WINDOW),
        Case("fault_tag_order", "a root out of ascending tag order", blocks=1,
             slice_words=16, group=1, inject=INJ_TAG_ORDER, bad_tag_at=3, bad_tag=9),
        Case("fault_act_range", "the odd slice's destination outside the FIFO",
             blocks=2, slice_words=16, group=1, base=16, stride=ACT_WORDS,
             inject=INJ_ACT_RANGE),
        Case("fault_slice_overrun", "more roots than the operation's slices hold",
             blocks=1, slice_words=16, group=1, roots=20, inject=INJ_SLICE_OVERRUN),
        Case("fault_nonfinite", "a root that is not finite", blocks=1, slice_words=16,
             group=1, inject=INJ_NONFINITE),
    ]


def root_image(case: Case, rng: np.random.Generator) -> list[int]:
    n = max(case.roots, 1)
    if case.window == "saturating":
        # every second root is the largest finite binary32, which rounds up out of BF16
        base = [0x7F7FFFFF if i % 2 == 0 else 0x3F800000 + i for i in range(n)]
        return base
    if case.window == "tiny":
        return [0x00000001 + i for i in range(n)]
    sign = rng.integers(0, 2, size=n, dtype=np.uint64)
    expo = rng.integers(100, 150, size=n, dtype=np.uint64)
    frac = rng.integers(0, 1 << 23, size=n, dtype=np.uint64)
    codes = [int(c) for c in ((sign << 31) | (expo << 23) | frac)]
    if case.inject == INJ_NONFINITE:
        codes[5] = 0x7F800000            # +infinity
    return codes


def evaluate(case: Case) -> None:
    """The receiver's contract, restated: what the block must do with these roots."""
    if case.inject in (INJ_DTYPE, INJ_GROUP, INJ_SCALED):
        case.expect_code, case.expect_detail = ERR_SHAPE, DETAIL_RECV_FORMAT
        case.act_window = 0
        return
    if case.inject in (INJ_SLICE_ZERO, INJ_WINDOW):
        case.expect_code, case.expect_detail = ERR_SHAPE, DETAIL_RECV_WINDOW
        case.act_window = 0
        return

    width = 16
    g = case.group
    acc = 0
    elem = 0
    word_index = 0
    slice_index = 0
    expect_tag = 0
    words: dict[int, int] = {}
    for i, code in enumerate(case.root_codes[:case.roots]):
        tag = case.bad_tag if (case.inject == INJ_TAG_ORDER and i == case.bad_tag_at) else i
        case.expect_roots += 1
        if tag != expect_tag:
            case.expect_code, case.expect_detail = ERR_SHAPE, DETAIL_RECV_TAG_ORDER
            case.expect_tag = tag
            break
        if slice_index >= case.blocks:
            case.expect_code, case.expect_detail = ERR_SHAPE, DETAIL_RECV_SLICE_OVERRUN
            case.expect_tag = tag
            break
        error, saturated, bf = bf16_rne(code)
        if error:
            case.expect_code = ERR_OPERAND_NONFINITE
            case.expect_detail = DETAIL_RECV_ROOT_NONFINITE
            case.expect_tag = tag
            break
        word_last = (elem + 1) >= g
        dst = case.base + (case.stride if slice_index % 2 else 0) + word_index
        if word_last and dst >= ACT_WORDS:
            case.expect_code, case.expect_detail = ERR_SHAPE, DETAIL_RECV_ACT_RANGE
            case.expect_tag = tag
            break
        expect_tag = tag + 1
        case.expect_saturations += saturated
        acc |= bf << (elem * width)
        if word_last:
            words[dst] = acc
            case.expect_words += 1
            acc = 0
            elem = 0
            if word_index + 1 >= case.slice_words:
                word_index = 0
                slice_index += 1
                case.expect_slices = slice_index
            else:
                word_index += 1
        else:
            elem += 1

    span = case.slice_words + (case.stride if case.blocks > 1 else 0)
    case.act_window = min(span, ACT_WORDS - case.base) if case.base < ACT_WORDS else 0
    case.act_expect = [words.get(case.base + w, UNWRITTEN) for w in range(case.act_window)]


def emit(cases: list[Case], out_dir: Path, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    roots: list[int] = []
    expect: list[int] = []
    records: list[int] = []
    totals = {"roots": 0, "words": 0, "slices": 0, "saturations": 0, "faults": 0}
    summaries: list[dict[str, Any]] = []
    for case_id, case in enumerate(cases):
        case.case_id = case_id
        case.root_codes = root_image(case, rng)
        evaluate(case)
        case.root_base = len(roots)
        roots.extend(case.root_codes)
        case.act_expect_base = len(expect)
        for value in case.act_expect:
            expect.append(value & 0xFFFFFFFF)
            expect.append((value >> 32) & 0xFFFFFFFF)
        totals["roots"] += case.expect_roots
        totals["words"] += case.expect_words
        totals["slices"] += case.expect_slices
        totals["saturations"] += case.expect_saturations
        totals["faults"] += 1 if case.expect_code else 0
        record = [
            case.blocks, case.slice_words, case.group, case.dtype, case.scaled,
            case.base, case.stride, case.root_base, case.roots, case.inject,
            case.expect_code, case.expect_detail, case.expect_tag, case.expect_words,
            case.expect_slices, case.expect_roots, case.expect_saturations,
            case.act_expect_base, case.act_window, case_id,
            case.gap, case.bad_tag_at, case.bad_tag, 0,
        ]
        assert len(record) == CASE_STRIDE
        records.extend(record)
        summaries.append({
            "id": case_id, "name": case.name, "note": case.note,
            "blocks": case.blocks, "slice_words": case.slice_words, "group": case.group,
            "dtype": case.dtype, "scaled": case.scaled, "base": case.base,
            "stride": case.stride, "roots_offered": case.roots, "gap": case.gap,
            "inject": case.inject,
            "expect_error_code": case.expect_code,
            "expect_error_detail": case.expect_detail,
            "expect_error_detail_name": DETAIL_NAMES.get(case.expect_detail, "unknown"),
            "expect_words": case.expect_words, "expect_slices": case.expect_slices,
            "expect_roots": case.expect_roots,
            "expect_saturations": case.expect_saturations,
            "activation_window_words": case.act_window,
        })
    meta = [len(cases), totals["roots"], totals["words"], totals["slices"],
            totals["saturations"], totals["faults"], ACT_WORDS, CASE_STRIDE]

    def pad(values: list[int], size: int, name: str) -> list[int]:
        if len(values) > size:
            raise RuntimeError(f"{name} needs {len(values)} words, the top declares {size}")
        return values + [0] * (size - len(values))

    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "or_root.hex": hex_lines(pad(roots, ROOT_WORDS, "or_root.hex"), 8),
        "or_case.hex": hex_lines(pad(records, CASE_WORDS, "or_case.hex"), 8),
        "or_expect.hex": hex_lines(pad(expect, EXPECT_WORDS, "or_expect.hex"), 8),
        "or_meta.hex": hex_lines(pad(meta, META_WORDS, "or_meta.hex"), 8),
    }
    digests = {}
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
        digests[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    marker = (f"PASS: ABI3 operand receiver cases={len(cases)} "
              f"words={totals['words']} slices={totals['slices']}")
    manifest = {
        "schema": SCHEMA,
        "seed": seed,
        "geometry": {"act_words": ACT_WORDS, "case_stride": CASE_STRIDE,
                     "root_words": len(roots), "expect_words": len(expect),
                     "case_words": len(records)},
        "totals": totals,
        "required_marker_prefix": marker,
        "reference": {
            "rounding": "binary32 -> BF16 round-to-nearest-even, the contract of "
                        "rtl/ot_fp32_rne_pkg.sv::fp32_to_bf16_rne, restated here",
            "packing": "ot_a3_tile64's own activation rule: a slice is "
                       "rows x ceil(depth_b / g) 64-bit words at op_a_base + "
                       "(b mod 2) x op_a_block_stride, word w holding the g "
                       "elements of one k-group at element_width bits each",
        },
        "case_record": [
            "blocks", "slice_words", "group", "dtype", "scaled", "base", "stride",
            "root_base", "roots_offered", "inject", "expect_error_code",
            "expect_error_detail", "expect_error_tag", "expect_words",
            "expect_slices", "expect_roots", "expect_saturations",
            "act_expect_base", "act_window_words", "case_id", "gap", "bad_tag_at",
            "bad_tag", "spare",
        ],
        "image_sha256": digests,
        "cases": summaries,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260908)
    args = parser.parse_args(argv)
    manifest = emit(build_cases(), args.out_dir, args.seed)
    print(f"receiver vectors: {len(manifest['cases'])} cases, "
          f"{manifest['totals']['words']} words -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
