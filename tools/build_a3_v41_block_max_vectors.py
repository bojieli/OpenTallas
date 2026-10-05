#!/usr/bin/env python3
"""Build the ROUTE.BLOCK_MAX vector images from the independent reference.

Every expected block score in the images comes from
``runtime.reference.candidate_pool.block_max_rows`` -- the reference written
from the operator semantics of
docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md section 5 row 2, with no
knowledge of rtl/abi3/ot_a3_route_block_max.sv.  Nothing here reads the RTL,
the compiler or the functional simulator.

Four images, consumed unchanged by both checkers
(rtl/test/tb_a3_route_block_max.sv on Icarus, rtl/test/a3_route_block_max_harness.cpp
on the pinned Verilator 5.050):

  bm_meta.hex    geometry, strides and the campaign totals
  bm_case.hex    one CASE_STRIDE record per case
  bm_vec.hex     one VEC_STRIDE record per driven block
  bm_expect.hex  one EXP_STRIDE record per expected output, in output order

The geometry is an argument in every case: --block, --exponent-bits,
--mantissa-bits, --max-blocks and --cmp-stages default to the V4.1 candidate
pool (8 binary32 scores per block, 2,048 blocks per row, one register stage per
comparator level) and the campaign builds five further shapes with the same
code path, including a non-power-of-two block and a BF16 score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.candidate_pool import (  # noqa: E402
    BLOCK_MAX_NUMERIC_CONTRACT,
    BLOCK_MAX_V41_BLOCK,
    BLOCK_MAX_V41_EXPONENT_BITS,
    BLOCK_MAX_V41_MANTISSA_BITS,
    BLOCK_MAX_V41_ROW_BLOCKS,
    block_max_padding_code,
    block_max_rows,
)

LAYOUT_VERSION = 1
MAGIC = 0x424D4158  # "BMAX"
META_WORDS = 32
CASE_STRIDE = 10
EXP_STRIDE = 4
#: harness-side lane words; unrelated to the block's geometry (see the
#: verification top).  A block wider than this cannot be driven by the images.
LANES_MAX = 16
VEC_HEADER_WORDS = 4
VEC_STRIDE = VEC_HEADER_WORDS + LANES_MAX

CASE_FLAG_RATE = 0x1
CASE_FLAG_FAULT = 0x2
VEC_FLAG_ROW_LAST = 0x1

#: detail codes of rtl/abi3/ot_a3_route_block_max.sv, and the ot_a3_engine_pkg
#: classes they carry.  Named here because a structural refusal has no numeric
#: reference: it is a property of the descriptor, asserted by construction.
DETAIL_NONE = 0
DETAIL_VALID_COUNT = 1
DETAIL_PARTIAL_NOT_LAST = 2
DETAIL_ROW_BLOCKS = 3
DETAIL_SCORE_NAN = 4
ERR_NONE = 0
ERR_OPERAND_NONFINITE = 1
ERR_SHAPE = 7
DETAIL_CLASS = {
    DETAIL_NONE: ERR_NONE,
    DETAIL_VALID_COUNT: ERR_SHAPE,
    DETAIL_PARTIAL_NOT_LAST: ERR_SHAPE,
    DETAIL_ROW_BLOCKS: ERR_SHAPE,
    DETAIL_SCORE_NAN: ERR_OPERAND_NONFINITE,
}


class Format:
    """One sign-magnitude IEEE interchange score format."""

    def __init__(self, exponent_bits: int, mantissa_bits: int) -> None:
        self.exponent_bits = exponent_bits
        self.mantissa_bits = mantissa_bits
        self.width = 1 + exponent_bits + mantissa_bits
        if self.width > 32:
            raise SystemExit("a score wider than 32 bits does not fit a harness lane word")
        self.exp_all_ones = (1 << exponent_bits) - 1
        self.bias = (1 << (exponent_bits - 1)) - 1

    def code(self, sign: int, exponent: int, mantissa: int) -> int:
        return (sign << (self.exponent_bits + self.mantissa_bits)) | (
            exponent << self.mantissa_bits) | mantissa

    @property
    def neg_inf(self) -> int:
        return block_max_padding_code(self.exponent_bits, self.mantissa_bits)

    @property
    def pos_inf(self) -> int:
        return self.code(0, self.exp_all_ones, 0)

    @property
    def neg_zero(self) -> int:
        return self.code(1, 0, 0)

    def nan(self, sign: int = 0) -> int:
        return self.code(sign, self.exp_all_ones, 1 << (self.mantissa_bits - 1))

    def specials(self) -> list[int]:
        """Codes at every class boundary of the format, both signs."""

        out: list[int] = []
        for sign in (0, 1):
            out.extend([
                self.code(sign, 0, 0),                               # zero
                self.code(sign, 0, 1),                               # least subnormal
                self.code(sign, 0, (1 << self.mantissa_bits) - 1),   # greatest subnormal
                self.code(sign, 1, 0),                               # least normal
                self.code(sign, self.bias, 0),                       # one
                self.code(sign, self.bias, 1),                       # one, next up
                self.code(sign, self.exp_all_ones - 1,
                          (1 << self.mantissa_bits) - 1),            # greatest finite
                self.code(sign, self.exp_all_ones, 0),               # infinity
            ])
        return out

    def random_code(self, rng: random.Random) -> int:
        """A random non-NaN code; exponents cluster near the bias, then spread."""

        while True:
            sign = rng.getrandbits(1)
            if rng.random() < 0.65:
                exponent = max(0, min(self.exp_all_ones,
                                      self.bias + rng.randint(-3, 3)))
            else:
                exponent = rng.randint(0, self.exp_all_ones)
            mantissa = rng.getrandbits(self.mantissa_bits)
            code = self.code(sign, exponent, mantissa)
            if exponent == self.exp_all_ones and mantissa:
                continue
            return code


class Builder:
    def __init__(self, block: int, fmt: Format, max_blocks: int, cmp_stages: int,
                 seed: int, rate_blocks: int) -> None:
        self.block = block
        self.fmt = fmt
        self.max_blocks = max_blocks
        self.cmp_stages = cmp_stages
        self.rng = random.Random(seed)
        self.seed = seed
        self.rate_blocks = min(rate_blocks, max_blocks)
        self.vectors: list[dict[str, Any]] = []
        self.expects: list[dict[str, int]] = []
        self.cases: list[dict[str, Any]] = []
        self.next_tag = 1

    # ----- image assembly ------------------------------------------------
    def _push_vector(self, lanes: list[int], valid_count: int, row_last: bool, tag: int,
                     idle_before: int) -> None:
        if len(lanes) > LANES_MAX:
            raise SystemExit(f"block {len(lanes)} exceeds the harness lane words {LANES_MAX}")
        self.vectors.append({
            "valid_count": valid_count,
            "row_last": bool(row_last),
            "tag": tag,
            "idle_before": idle_before,
            "lanes": list(lanes),
        })

    def _push_expect(self, score: int, block_id: int, row_last: bool, tag: int) -> None:
        self.expects.append({
            "score": score, "block_id": block_id,
            "row_last": 1 if row_last else 0, "tag": tag,
        })

    def _open_case(self, name: str, note: str) -> dict[str, Any]:
        case = {
            "id": len(self.cases),
            "name": name,
            "note": note,
            "flags": 0,
            "vec_base": len(self.vectors),
            "exp_base": len(self.expects),
            "err_code": ERR_NONE,
            "err_detail": DETAIL_NONE,
            "err_block_id": 0,
            "err_tag": 0,
        }
        self.cases.append(case)
        return case

    def _close_case(self, case: dict[str, Any]) -> None:
        case["vec_count"] = len(self.vectors) - case["vec_base"]
        case["exp_count"] = len(self.expects) - case["exp_base"]

    def _tag(self) -> int:
        tag = self.next_tag
        self.next_tag = (self.next_tag + 1) & 0xFFFF
        if self.next_tag == 0:
            self.next_tag = 1
        return tag

    # ----- cases ---------------------------------------------------------
    def add_rows_case(self, name: str, note: str, rows: list[list[int]], *,
                      idle: int = 0, rate: bool = False, junk_padding: bool = False) -> None:
        """A case that drives whole rows and expects the reference's blocks."""

        case = self._open_case(name, note)
        if rate:
            case["flags"] |= CASE_FLAG_RATE
        expected = block_max_rows(rows, self.block,
                                  exponent_bits=self.fmt.exponent_bits,
                                  mantissa_bits=self.fmt.mantissa_bits)
        for row, row_expected in zip(rows, expected):
            tag = self._tag()
            block_count = len(row_expected)
            for index in range(block_count):
                chunk = row[index * self.block:(index + 1) * self.block]
                lanes = list(chunk)
                while len(lanes) < self.block:
                    #: the block is told the real extent and pads internally;
                    #: junk_padding proves that what is left on a padding lane
                    #: -- here a NaN, the one code the operator refuses on a
                    #: real lane -- cannot reach the result.
                    lanes.append(self.fmt.nan(1) if junk_padding else 0)
                self._push_vector(lanes, len(chunk), index == block_count - 1, tag,
                                  idle if index else 0)
                self._push_expect(row_expected[index], index, index == block_count - 1, tag)
        self._close_case(case)

    def add_fault_case(self, name: str, note: str, detail: int,
                       prefix_blocks: list[list[int]], bad: dict[str, Any],
                       trailing: int = 2) -> None:
        """Blocks that retire, one refused block, then blocks that must be ignored."""

        case = self._open_case(name, note)
        case["flags"] |= CASE_FLAG_FAULT
        case["err_detail"] = detail
        case["err_code"] = DETAIL_CLASS[detail]
        tag = self._tag()
        #: the retiring prefix is one row's leading blocks, so its expected
        #: values still come from the reference.
        if prefix_blocks:
            flat = [code for chunk in prefix_blocks for code in chunk]
            expected = block_max_rows([flat], self.block,
                                      exponent_bits=self.fmt.exponent_bits,
                                      mantissa_bits=self.fmt.mantissa_bits)[0]
            if len(expected) != len(prefix_blocks):
                raise SystemExit("the refusal prefix must be whole blocks")
            for index, chunk in enumerate(prefix_blocks):
                self._push_vector(list(chunk), len(chunk), False, tag, 0)
                self._push_expect(expected[index], index, False, tag)
        lanes = list(bad["lanes"])
        while len(lanes) < self.block:
            lanes.append(0)
        #: the refused block's own index and tag, which the block latches.
        case["err_block_id"] = len(prefix_blocks)
        case["err_tag"] = tag
        self._push_vector(lanes, bad["valid_count"], bad.get("row_last", False), tag, 0)
        #: blocks after the refusal: legal in every way, and never accepted.
        for _ in range(trailing):
            self._push_vector([self.fmt.random_code(self.rng) for _ in range(self.block)],
                              self.block, False, self._tag(), 0)
        self._close_case(case)

    def add_row_bound_case(self) -> None:
        """MAX_BLOCKS blocks retire; the next block of the same row is refused."""

        case = self._open_case(
            "row_bound",
            f"a row of exactly MAX_BLOCKS = {self.max_blocks} blocks retires, and the "
            "block after it is refused with DETAIL_BLOCK_MAX_ROW_BLOCKS")
        case["flags"] |= CASE_FLAG_FAULT
        case["err_detail"] = DETAIL_ROW_BLOCKS
        case["err_code"] = DETAIL_CLASS[DETAIL_ROW_BLOCKS]
        tag = self._tag()
        row = [self.fmt.random_code(self.rng) for _ in range(self.max_blocks * self.block)]
        expected = block_max_rows([row], self.block,
                                  exponent_bits=self.fmt.exponent_bits,
                                  mantissa_bits=self.fmt.mantissa_bits)[0]
        for index in range(self.max_blocks):
            chunk = row[index * self.block:(index + 1) * self.block]
            self._push_vector(list(chunk), self.block, False, tag, 0)
            self._push_expect(expected[index], index, False, tag)
        case["err_block_id"] = self.max_blocks
        case["err_tag"] = tag
        self._push_vector([self.fmt.random_code(self.rng) for _ in range(self.block)],
                          self.block, False, tag, 0)
        for _ in range(2):
            self._push_vector([self.fmt.random_code(self.rng) for _ in range(self.block)],
                              self.block, True, self._tag(), 0)
        self._close_case(case)

    def build(self) -> None:
        block = self.block
        fmt = self.fmt
        rng = self.rng

        self.add_rows_case(
            "full_blocks",
            "three rows whose length is a whole number of blocks, random codes",
            [[fmt.random_code(rng) for _ in range(4 * block)] for _ in range(3)])

        partial_lengths = sorted({3 * block + 1, 2 * block + max(1, block - 1),
                                  block + 1, 1, max(1, block - 1)})
        self.add_rows_case(
            "partial_final_block",
            "rows whose length is not a multiple of BLOCK: the final block is reduced "
            "over its real positions and the tail is never dropped",
            [[fmt.random_code(rng) for _ in range(length)] for length in partial_lengths])

        self.add_rows_case(
            "all_negative",
            "a row in which every score is negative, including negative infinity: a zero "
            "pad would win here and the reference's negative-infinity pad does not",
            [[fmt.code(1, rng.randint(1, fmt.exp_all_ones - 1),
                       rng.getrandbits(fmt.mantissa_bits)) for _ in range(2 * block)]
             + [fmt.neg_inf] * max(1, block - 1)])

        self.add_rows_case(
            "all_padding_value",
            "a row of negative infinity only: every block score is negative infinity",
            [[fmt.neg_inf] * (2 * block)])

        lanes_rows: list[list[int]] = []
        for lane in range(block):
            row = [fmt.code(1, fmt.bias, 0)] * block          # every lane -1.0
            row[lane] = fmt.code(0, fmt.bias, 0)              # the winner, +1.0
            lanes_rows.append(row)
        self.add_rows_case(
            "max_at_each_lane",
            "one row per lane, the maximum on that lane only: every leaf of the tree is "
            "shown to reach the result",
            lanes_rows)

        self.add_rows_case(
            "signed_zero",
            "every arrangement of negative and positive zero in a block, up to the block "
            "width: max(-0.0, +0.0) is +0.0 and max(-0.0, -0.0) is -0.0",
            [[fmt.neg_zero if (pattern >> lane) & 1 else fmt.code(0, 0, 0)
              for lane in range(block)]
             for pattern in range(min(1 << block, 64))])

        specials = fmt.specials()
        special_rows: list[list[int]] = []
        for start in range(0, len(specials), max(1, block // 2)):
            row = [specials[(start + offset) % len(specials)] for offset in range(block)]
            special_rows.append(row)
        self.add_rows_case(
            "class_boundaries",
            "rotations of the format's class boundaries: zeros, least and greatest "
            "subnormal, least normal, one, greatest finite, both infinities",
            special_rows)

        self.add_rows_case(
            "ties",
            "blocks whose scores are all equal, at several codes: the winning code is that "
            "code, and a tie needs no tie-break",
            [[code] * block for code in (fmt.code(0, fmt.bias, 0), fmt.neg_inf,
                                         fmt.pos_inf, fmt.code(1, fmt.bias, 7 % (1 << fmt.mantissa_bits)))])

        self.add_rows_case(
            "idle_between_blocks",
            "the same shape as full_blocks with three idle cycles between blocks: the "
            "per-block latency is unchanged by a gap in the stream",
            [[fmt.random_code(rng) for _ in range(3 * block)] for _ in range(2)],
            idle=3)

        if block > 1:
            self.add_rows_case(
                "nan_on_padding_lane",
                "a partial final block whose padding lanes carry a NaN: padding lanes are "
                "never inspected, so the block retires and the result is the reference's",
                [[fmt.random_code(rng) for _ in range(2 * block + 1)],
                 [fmt.random_code(rng) for _ in range(block + max(1, block // 2))]],
                junk_padding=True)

        self.add_rows_case(
            "rate_stream",
            f"one row of {self.rate_blocks} blocks driven back to back: initiation interval 1",
            [[fmt.random_code(rng) for _ in range(self.rate_blocks * block)]],
            rate=True)

        prefix = [[fmt.random_code(rng) for _ in range(block)] for _ in range(2)]
        self.add_fault_case(
            "valid_count_zero",
            "an extent of zero is refused: the reference emits ceil(N / BLOCK) blocks and "
            "never an all-padding block",
            DETAIL_VALID_COUNT, prefix,
            {"lanes": [fmt.random_code(rng) for _ in range(block)], "valid_count": 0})

        self.add_fault_case(
            "valid_count_over_block",
            "an extent above BLOCK is refused rather than truncated into a legal one",
            DETAIL_VALID_COUNT, prefix,
            {"lanes": [fmt.random_code(rng) for _ in range(block)],
             "valid_count": block + 1})

        if block > 1:
            self.add_fault_case(
                "partial_not_row_last",
                "a short block that is not row-last is refused: only a final block is "
                "partial under the reference, and accepting an interior short block would "
                "shift every block index after it",
                DETAIL_PARTIAL_NOT_LAST, prefix,
                {"lanes": [fmt.random_code(rng) for _ in range(block)],
                 "valid_count": block - 1, "row_last": False})

        self.add_fault_case(
            "nan_on_real_lane",
            "a NaN on a real lane is refused: the order is not total on NaNs",
            DETAIL_SCORE_NAN, prefix,
            {"lanes": [fmt.nan(0) if lane == min(block - 1, 1) else fmt.random_code(rng)
                       for lane in range(block)],
             "valid_count": block})

        self.add_row_bound_case()

        self.add_rows_case(
            "after_clear",
            "a plain row after every refusal case: clear restores the block and the row's "
            "block index restarts at zero",
            [[fmt.random_code(rng) for _ in range(2 * block)]])

    # ----- emission ------------------------------------------------------
    def totals(self) -> dict[str, int]:
        return {
            "blocks": len(self.expects),
            "positions": sum(
                self.vectors[case["vec_base"] + index]["valid_count"]
                for case in self.cases
                for index in range(case["exp_count"])),
            "rows": sum(1 for expect in self.expects if expect["row_last"]),
            "faults": sum(1 for case in self.cases if case["flags"] & CASE_FLAG_FAULT),
            "rate_cases": sum(1 for case in self.cases if case["flags"] & CASE_FLAG_RATE),
        }

    def pipeline_depth(self) -> int:
        levels = 0 if self.block <= 1 else (self.block - 1).bit_length()
        return levels * self.cmp_stages + 2

    def meta(self) -> list[int]:
        totals = self.totals()
        words = [0] * META_WORDS
        words[0] = MAGIC
        words[1] = LAYOUT_VERSION
        words[2] = self.block
        words[3] = self.fmt.width
        words[4] = self.fmt.exponent_bits
        words[5] = self.fmt.mantissa_bits
        words[6] = self.cmp_stages
        words[7] = self.max_blocks
        words[8] = self.pipeline_depth()
        words[9] = len(self.cases)
        words[10] = len(self.vectors)
        words[11] = len(self.expects)
        words[12] = totals["blocks"]
        words[13] = totals["positions"]
        words[14] = totals["rows"]
        words[15] = totals["faults"]
        words[16] = VEC_STRIDE
        words[17] = CASE_STRIDE
        words[18] = EXP_STRIDE
        words[19] = LANES_MAX
        words[20] = totals["rate_cases"]
        #: latency in rising edges from the edge that ACCEPTS a block to the
        #: edge that registers its block score.  One less than the stage count,
        #: because the accepting edge is the input stage's own edge.
        words[21] = self.pipeline_depth() - 1
        return words

    def marker_prefix(self) -> str:
        totals = self.totals()
        return (f"PASS: A3 V41 BLOCK_MAX block={self.block} cmp_stages={self.cmp_stages} "
                f"cases={len(self.cases)} outputs={totals['blocks']} "
                f"faults={totals['faults']}")

    def images(self) -> dict[str, list[int]]:
        vec_words: list[int] = []
        for vector in self.vectors:
            record = [0] * VEC_STRIDE
            record[0] = vector["valid_count"]
            record[1] = VEC_FLAG_ROW_LAST if vector["row_last"] else 0
            record[2] = vector["tag"]
            record[3] = vector["idle_before"]
            for lane, code in enumerate(vector["lanes"]):
                record[VEC_HEADER_WORDS + lane] = code
            vec_words.extend(record)
        case_words: list[int] = []
        for case in self.cases:
            case_words.extend([
                case["id"], case["flags"], case["vec_base"], case["vec_count"],
                case["exp_base"], case["exp_count"], case["err_code"], case["err_detail"],
                case["err_block_id"], case["err_tag"],
            ])
        exp_words: list[int] = []
        for expect in self.expects:
            exp_words.extend([expect["score"], expect["block_id"], expect["row_last"],
                              expect["tag"]])
        return {
            "bm_meta.hex": self.meta(),
            "bm_case.hex": case_words,
            "bm_vec.hex": vec_words,
            "bm_expect.hex": exp_words,
        }

    def manifest(self, image_sha256: dict[str, str]) -> dict[str, Any]:
        return {
            "schema": "opentallas.rtl.a3_v41_block_max_vectors.v1",
            "engine": "ROUTE.BLOCK_MAX",
            "sub_opcode": "0x08",
            "ir_kind": "BLOCK_MAX",
            "numeric_contract": BLOCK_MAX_NUMERIC_CONTRACT,
            "reference": "runtime.reference.candidate_pool.block_max_rows",
            "layout_version": LAYOUT_VERSION,
            "seed": self.seed,
            "geometry": {
                "block": self.block,
                "score_w": self.fmt.width,
                "exponent_bits": self.fmt.exponent_bits,
                "mantissa_bits": self.fmt.mantissa_bits,
                "max_blocks": self.max_blocks,
                "cmp_stages": self.cmp_stages,
                "lanes_max": LANES_MAX,
                "pipeline_depth": self.pipeline_depth(),
                "output_latency_cycles": self.pipeline_depth() - 1,
                "rate_blocks": self.rate_blocks,
            },
            "strides": {"vector": VEC_STRIDE, "case": CASE_STRIDE, "expect": EXP_STRIDE,
                        "meta": META_WORDS},
            "totals": self.totals(),
            "counts": {"cases": len(self.cases), "vectors": len(self.vectors),
                       "expects": len(self.expects)},
            "required_marker_prefix": self.marker_prefix(),
            "cases": [
                {k: case[k] for k in ("id", "name", "note", "flags", "vec_base", "vec_count",
                                      "exp_base", "exp_count", "err_code", "err_detail",
                                      "err_block_id", "err_tag")}
                for case in self.cases
            ],
            "image_sha256": image_sha256,
        }


def write_images(out_dir: Path, images: dict[str, list[int]]) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    for name, words in images.items():
        text = "".join(f"{word & 0xFFFFFFFF:08x}\n" for word in words)
        path = out_dir / name
        path.write_text(text, encoding="ascii")
        digests[name] = hashlib.sha256(text.encode("ascii")).hexdigest()
    return digests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--block", type=int, default=BLOCK_MAX_V41_BLOCK)
    parser.add_argument("--exponent-bits", type=int, default=BLOCK_MAX_V41_EXPONENT_BITS)
    parser.add_argument("--mantissa-bits", type=int, default=BLOCK_MAX_V41_MANTISSA_BITS)
    parser.add_argument("--max-blocks", type=int, default=BLOCK_MAX_V41_ROW_BLOCKS)
    parser.add_argument("--cmp-stages", type=int, default=1)
    parser.add_argument("--rate-blocks", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args(argv)

    fmt = Format(args.exponent_bits, args.mantissa_bits)
    builder = Builder(args.block, fmt, args.max_blocks, args.cmp_stages, args.seed,
                      args.rate_blocks)
    builder.build()
    images = builder.images()
    digests = write_images(args.out_dir, images)
    manifest = builder.manifest(digests)
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cases": manifest["counts"]["cases"],
                      "vectors": manifest["counts"]["vectors"],
                      "expects": manifest["counts"]["expects"],
                      "totals": manifest["totals"],
                      "marker": manifest["required_marker_prefix"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
