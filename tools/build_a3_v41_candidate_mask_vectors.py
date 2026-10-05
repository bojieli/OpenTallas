#!/usr/bin/env python3
"""Build the images and expectations for the ROUTE.CANDIDATE_MASK campaign.

``rtl/abi3/ot_a3_route_candidate_mask.sv`` expands chosen candidate-block ids
into the per-position admission mask ``ROUTE.INDEX_TOPK`` takes in slot 3
(AM-E10, DeepSeek-V4.1-Flash).  The expected masks here come from
``runtime/reference/candidate_pool.py::select_candidate_mask``, which is written
from the pinned sources (SRC-DSV41-FLASH-MODEL, -CONFIG, -REPORT) and not from
the RTL; the two checkers re-derive the same masks a third and fourth time, in
Verilog and in C++, from the id image alone.

Images:
  ``cm_case.hex``    one 16-word record per case (layout in the manifest)
  ``cm_ids.hex``     the chosen-block id operand memory
  ``cm_expect.hex``  the reference mask words, per case
  ``cm_meta.hex``    case count and campaign totals

Every case names the GEOMETRY it runs on.  The top elaborates five of them --
including BLOCK = 1, a BLOCK that is not a power of two, and one with the
pinned-last-block rule switched off -- so a frozen-geometry regression shows up
as a failing case rather than as a shape the block silently refuses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import Route  # noqa: E402
from runtime.reference.candidate_pool import (  # noqa: E402
    CANDIDATE_MASK_ABSENT_ID,
    CANDIDATE_MASK_CONTRACT,
    CandidateMaskError,
    select_candidate_mask,
)

SCHEMA = "opentallas.rtl.a3_v41_candidate_mask_vectors.v1"

#: Imported, not transcribed: a sub-opcode that appears as a number here and as
#: another number in the RTL package is exactly the disagreement the campaign's
#: registry check exists to catch.  Route.BLOCK_MAX is the neighbouring
#: sub-opcode the wrong-sub-opcode case uses.
SUBOP_CANDIDATE_MASK = int(Route.CANDIDATE_MASK)
SUBOP_BLOCK_MAX = int(Route.BLOCK_MAX)
ABSENT = CANDIDATE_MASK_ABSENT_ID
WORD_BITS = 32
CASE_STRIDE = 16
DONT_CHECK = 0xFFFFFFFF

#: Image sizes declared by ``rtl/test/a3_candidate_mask_top.sv``.
CASE_WORDS = 1024
IDS_WORDS = 16384
EXPECT_WORDS = 65536
META_WORDS = 8
CAP_WORDS = 32768

#: The geometry table the top elaborates.  Mirrored, never assumed: each case
#: checks ``obs_param_*`` against the row it named, so a table that drifts from
#: the top's parameters fails the campaign instead of being believed.
GEOMETRIES = [
    {"geom": 0, "block": 8, "max_width": 1048576, "max_ids": 2048, "pin": 1,
     "note": "DeepSeek-V4.1-Flash: blocks of 8 over a 1,048,576-position context"},
    {"geom": 1, "block": 1, "max_width": 4096, "max_ids": 4096, "pin": 1,
     "note": "degenerate block: one position per block, the mask is the id set"},
    {"geom": 2, "block": 3, "max_width": 4095, "max_ids": 1365, "pin": 1,
     "note": "block size that is not a power of two"},
    {"geom": 3, "block": 16, "max_width": 8192, "max_ids": 512, "pin": 1,
     "note": "wider block"},
    {"geom": 4, "block": 8, "max_width": 4096, "max_ids": 2048, "pin": 0,
     "note": "the V4.1 block with the pinned-last-block rule switched off"},
]

ERR_NONE = 0
ERR_INDEX_RANGE = 4
ERR_SHAPE = 7

DET_NONE = 0
DET_SUBOP = 1
DET_WIDTH_ZERO = 2
DET_WIDTH_MAX = 3
DET_ID_COUNT_MAX = 4
DET_BLOCK_MISMATCH = 5
DET_ID_RANGE = 6
DET_POPULATION = 7

DETAIL_NAMES = {
    DET_NONE: "none",
    DET_SUBOP: "sub-opcode is not ROUTE.CANDIDATE_MASK",
    DET_WIDTH_ZERO: "width is zero",
    DET_WIDTH_MAX: "width above the elaborated MAX_WIDTH",
    DET_ID_COUNT_MAX: "id count above the elaborated MAX_IDS",
    DET_BLOCK_MISMATCH: "descriptor block size differs from the elaborated BLOCK",
    DET_ID_RANGE: "a block id lies outside the block count of this position axis",
    DET_POPULATION: "admitted population above the declared bound",
}


def hex_lines(values: list[int], digits: int = 8) -> str:
    return "".join(f"{value & 0xffffffff:0{digits}x}\n" for value in values)


def case(name: str, geom: int, width: int, ids: list[int], *, note: str,
         cfg_block: int = 0, max_pop: int = 0, out_base: int = 0,
         subop: int = SUBOP_CANDIDATE_MASK, id_count: int | None = None,
         expect_code: int = ERR_NONE, expect_detail: int = DET_NONE,
         expect_slot: int = 0, expect_value: int = 0) -> dict[str, Any]:
    return {"name": name, "geom": geom, "width": width, "ids": list(ids),
            "note": note, "cfg_block": cfg_block, "max_pop": max_pop,
            "out_base": out_base, "subop": subop,
            "id_count": len(ids) if id_count is None else id_count,
            "expect_code": expect_code, "expect_detail": expect_detail,
            "expect_slot": expect_slot, "expect_value": expect_value}


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    add = cases.append

    # -- geometry 0, the V4.1 block ----------------------------------------
    add(case("pin_only_one_block", 0, 8, [],
             note="no id at all: the pinned last block is still admitted, which "
                  "is the whole rule in one case"))
    add(case("pin_only_single_position", 0, 1, [],
             note="a one-position axis: one block, short by seven, admitted"))
    add(case("pin_only_partial_block", 0, 7, [],
             note="the -inf padding: the last block covers [0, 7), not [0, 8)"))
    add(case("two_ids_partial_tail", 0, 33, [0, 2],
             note="blocks 0 and 2 chosen, block 4 pinned and one position long"))
    add(case("contiguous_ids_one_bitmap_word", 0, 1024, list(range(32)),
             note="32 ids in one bitmap word back to back: the read-modify-write "
                  "hazard the ingest forwarding path exists for"))
    add(case("strided_ids_distinct_bitmap_words", 0, 1024,
             [i * 32 for i in range(4)],
             note="ids in four different bitmap words: no forwarding needed"))
    add(case("duplicate_ids", 0, 100, [3, 3, 3, 1],
             note="ids are a set: a repeated id admits its block once"))
    add(case("unsorted_ids", 0, 100, [11, 2, 0],
             note="descending and unsorted: order does not matter"))
    add(case("absent_slots", 0, 4096, [ABSENT, 5, ABSENT, 100, 511, ABSENT],
             note="A3_NO_ID slots are empty top-k slots and admit nothing"))
    add(case("id_is_the_pinned_block", 0, 64, [7],
             note="the id names the block the pin already admitted: counted once"))
    add(case("repeated_pinned_block", 0, 64, [7, 7, 7, 7],
             note="the same id four times in a row, onto the pinned bit: the "
                  "forwarding path must not double-count the population"))
    add(case("declared_block_size_carried", 0, 256, [0, 1, 30],
             cfg_block=8,
             note="a descriptor that carries block=8 is checked, not reinterpreted"))
    add(case("out_base_offset", 0, 256, [1, 2], out_base=7,
             note="out_addr is out_base + word index, not the word index"))
    add(case("pool_exactly_at_the_bound", 0, 16384, list(range(2048)),
             max_pop=16384,
             note="the whole 2,048-block pool over a 16,384-position axis: the "
                  "population is exactly the bound candidate_pool_bound states"))
    add(case("v41_full_context", 0, 1048576, [(i * 61) % 131072 for i in range(2048)],
             note="the V4.1 geometry at its published extent: 2,048 chosen blocks "
                  "over 1,048,576 positions, 32,768 mask words at one word per cycle"))
    add(case("bound_met_with_the_pin_counted", 0, 262144,
             [i * 5 for i in range(2047)] + [32767],
             max_pop=16384,
             note="2,047 chosen blocks plus the pinned last block is exactly "
                  "16,384 admitted positions: the bound is satisfiable only when "
                  "the pin is budgeted for"))

    # -- geometry 0, refusals ----------------------------------------------
    add(case("refuse_width_zero", 0, 0, [], expect_code=ERR_SHAPE,
             expect_detail=DET_WIDTH_ZERO,
             note="a zero-position axis has no mask"))
    add(case("refuse_width_above_max", 0, 1048577, [], expect_code=ERR_SHAPE,
             expect_detail=DET_WIDTH_MAX, expect_value=1048577,
             note="one position above the elaborated MAX_WIDTH: the bound is the "
                  "parameter, not a literal"))
    add(case("refuse_id_count_above_max", 0, 4096, [], id_count=2049,
             expect_code=ERR_SHAPE, expect_detail=DET_ID_COUNT_MAX,
             expect_value=2049,
             note="one id above the elaborated MAX_IDS"))
    add(case("refuse_block_size_mismatch", 0, 4096, [0], cfg_block=7,
             expect_code=ERR_SHAPE, expect_detail=DET_BLOCK_MISMATCH,
             expect_value=7,
             note="a descriptor that carries a block size the elaboration does "
                  "not implement is refused rather than reinterpreted"))
    add(case("refuse_wrong_subop", 0, 4096, [0], subop=SUBOP_BLOCK_MAX,
             expect_code=ERR_SHAPE, expect_detail=DET_SUBOP,
             expect_value=SUBOP_BLOCK_MAX,
             note="ROUTE.BLOCK_MAX is the neighbouring sub-opcode and is not this "
                  "block's work"))
    add(case("refuse_first_id_out_of_range", 0, 64, [8],
             expect_code=ERR_INDEX_RANGE, expect_detail=DET_ID_RANGE,
             expect_slot=0, expect_value=8,
             note="a 64-position axis has eight blocks, so id 8 names a block "
                  "this axis does not have"))
    add(case("refuse_third_id_out_of_range", 0, 64, [0, 1, 9],
             expect_code=ERR_INDEX_RANGE, expect_detail=DET_ID_RANGE,
             expect_slot=2, expect_value=9,
             note="the refusal names the offending slot, and no mask word is "
                  "written before it"))
    add(case("refuse_population_above_bound", 0, 262144,
             [i * 5 for i in range(2048)], max_pop=16384,
             expect_code=ERR_SHAPE, expect_detail=DET_POPULATION,
             expect_value=16392,
             note="2,048 chosen blocks plus a pinned block that none of them "
                  "named is 16,392 positions, above the 16,384 bound: refused "
                  "before the first output word"))

    # -- geometry 1, BLOCK = 1 ---------------------------------------------
    add(case("block1_sparse", 1, 64, [0, 5, 63],
             note="one position per block: the mask is the id set itself, and "
                  "one bitmap word expands to exactly one output word"))
    add(case("block1_dense", 1, 4096, list(range(0, 4000, 4)),
             note="1,000 ids at BLOCK = 1: the emit loop consumes a bitmap word "
                  "every cycle and still retires one output word per cycle"))
    add(case("block1_pin_is_last_position", 1, 33, [32],
             note="at BLOCK = 1 the pinned block is the newest position"))

    # -- geometry 2, BLOCK = 3, not a power of two -------------------------
    add(case("block3_partial_tail", 2, 10, [0, 2],
             note="ceil(10/3) = 4 blocks, the pinned one covering [9, 10): a "
                  "block size that is not a power of two and a tail that is not "
                  "a multiple of it"))
    add(case("block3_full_extent", 2, 4095, [1364],
             note="the id names the block the pin admits, at the elaborated "
                  "MAX_WIDTH of a non-power-of-two geometry"))
    add(case("block3_spread", 2, 100, [0, 1, 2, 33],
             note="blocks of three across a 100-position axis"))

    # -- geometry 3, BLOCK = 16 --------------------------------------------
    add(case("block16_ends", 3, 8192, [0, 511],
             note="first and last block of a 16-wide geometry"))
    add(case("block16_partial_tail", 3, 100, [1],
             note="ceil(100/16) = 7 blocks, the pinned one covering [96, 100)"))

    # -- geometry 4, the pin switched off ----------------------------------
    add(case("unpinned_one_id", 4, 100, [0],
             note="the same shape as a pinned case, without the rule: 8 admitted "
                  "positions instead of 12.  This is what the pinned-last-block "
                  "rule is worth"))
    add(case("unpinned_no_ids", 4, 100, [],
             note="no ids and no pin: an all-zero mask, which is the only way "
                  "this block emits one"))
    add(case("unpinned_last_block_chosen", 4, 4096, [511],
             note="with the last block chosen by the top-k, pinned and unpinned "
                  "agree"))
    return cases


def evaluate(entry: dict[str, Any]) -> None:
    """Fill in the reference answer, or record that the case is a refusal."""
    geom = GEOMETRIES[entry["geom"]]
    entry["geometry_note"] = geom["note"]
    entry["block"] = geom["block"]
    entry["pin"] = geom["pin"]
    if entry["expect_code"] != ERR_NONE and entry["expect_detail"] != DET_POPULATION:
        entry["words"] = []
        entry["population"] = DONT_CHECK
        entry["blocks"] = DONT_CHECK
        return
    try:
        result = select_candidate_mask(
            entry["ids"],
            width=entry["width"],
            block=geom["block"],
            word_bits=WORD_BITS,
            pin_last_block=bool(geom["pin"]),
            max_population=entry["max_pop"] or None,
        )
    except CandidateMaskError as exc:
        if entry["expect_detail"] != DET_POPULATION:
            raise
        # The reference refuses for the same reason the block does; the
        # population it reports is the one the block latches in error_value.
        unbounded = select_candidate_mask(
            entry["ids"], width=entry["width"], block=geom["block"],
            word_bits=WORD_BITS, pin_last_block=bool(geom["pin"]))
        entry["words"] = []
        entry["population"] = unbounded["population"]
        entry["blocks"] = unbounded["admitted_block_count"]
        entry["reference_refusal"] = str(exc)
        if entry["expect_value"] != unbounded["population"]:
            raise RuntimeError(
                f"{entry['name']}: declared error_value {entry['expect_value']} "
                f"is not the reference population {unbounded['population']}")
        return
    if entry["expect_code"] != ERR_NONE:
        raise RuntimeError(f"{entry['name']}: expected a refusal, the reference passed")
    entry["words"] = list(result["words"])
    entry["population"] = result["population"]
    entry["blocks"] = result["admitted_block_count"]
    entry["pinned_block"] = result["pinned_block"]
    entry["block_count"] = result["block_count"]


def emit(cases: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    ids_image: list[int] = []
    expect_image: list[int] = []
    records: list[int] = []
    summaries: list[dict[str, Any]] = []
    totals = {"cases": len(cases), "mask_words": 0, "ids": 0, "refusals": 0,
              "admitted_positions": 0}
    for case_id, entry in enumerate(cases):
        evaluate(entry)
        entry["case_id"] = case_id
        entry["ids_base"] = len(ids_image)
        ids_image.extend(entry["ids"])
        entry["expect_base"] = len(expect_image)
        expect_image.extend(entry["words"])
        totals["mask_words"] += len(entry["words"])
        totals["ids"] += len(entry["ids"])
        totals["refusals"] += 1 if entry["expect_code"] else 0
        if entry["population"] != DONT_CHECK:
            totals["admitted_positions"] += entry["population"]
        if entry["out_base"] + len(entry["words"]) > CAP_WORDS:
            raise RuntimeError(
                f"{entry['name']}: {len(entry['words'])} words at out_base "
                f"{entry['out_base']} does not fit the top's capture window")
        record = [
            entry["geom"], entry["subop"], entry["width"], entry["id_count"],
            entry["cfg_block"], entry["max_pop"], entry["ids_base"],
            entry["out_base"], entry["expect_code"], entry["expect_detail"],
            entry["expect_slot"], entry["expect_value"], len(entry["words"]),
            entry["population"], entry["blocks"], entry["expect_base"],
        ]
        assert len(record) == CASE_STRIDE
        records.extend(record)
        summaries.append({
            "id": case_id, "name": entry["name"], "note": entry["note"],
            "geometry": entry["geom"], "geometry_note": entry["geometry_note"],
            "block": entry["block"], "pin_last_block": entry["pin"],
            "width": entry["width"], "id_count": entry["id_count"],
            "distinct_ids": len({i for i in entry["ids"] if i != ABSENT}),
            "cfg_block": entry["cfg_block"], "max_population": entry["max_pop"],
            "out_base": entry["out_base"], "subopcode": entry["subop"],
            "expect_error_code": entry["expect_code"],
            "expect_error_detail": entry["expect_detail"],
            "expect_error_detail_name": DETAIL_NAMES[entry["expect_detail"]],
            "expect_error_slot": entry["expect_slot"],
            "expect_error_value": entry["expect_value"],
            "expect_mask_words": len(entry["words"]),
            "expect_population": entry["population"],
            "expect_blocks": entry["blocks"],
        })
    meta = [len(cases), totals["mask_words"], totals["ids"], totals["refusals"],
            len(GEOMETRIES), CASE_STRIDE, WORD_BITS, totals["admitted_positions"]]

    def pad(values: list[int], size: int, name: str) -> list[int]:
        if len(values) > size:
            raise RuntimeError(
                f"{name} needs {len(values)} words, the top declares {size}")
        return values + [0] * (size - len(values))

    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "cm_case.hex": hex_lines(pad(records, CASE_WORDS, "cm_case.hex")),
        "cm_ids.hex": hex_lines(pad(ids_image, IDS_WORDS, "cm_ids.hex")),
        "cm_expect.hex": hex_lines(pad(expect_image, EXPECT_WORDS, "cm_expect.hex")),
        "cm_meta.hex": hex_lines(pad(meta, META_WORDS, "cm_meta.hex")),
    }
    digests = {}
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
        digests[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    marker = (f"PASS: A3 V41 candidate mask cases={len(cases)} "
              f"words={totals['mask_words']} population={totals['admitted_positions']}")
    return {
        "schema": SCHEMA,
        "contract": CANDIDATE_MASK_CONTRACT,
        "polarity": "set_bit_admits_position",
        "case_stride": CASE_STRIDE,
        "word_bits": WORD_BITS,
        "geometries": GEOMETRIES,
        "totals": totals,
        "image_sha256": digests,
        "image_words": {"cm_case.hex": len(records), "cm_ids.hex": len(ids_image),
                        "cm_expect.hex": len(expect_image), "cm_meta.hex": len(meta)},
        "required_marker_prefix": marker,
        "reference": ("runtime/reference/candidate_pool.py::select_candidate_mask, "
                      "written from SRC-DSV41-FLASH-MODEL, -CONFIG and -REPORT; "
                      "re-derived independently in rtl/test/tb_a3_candidate_mask.sv "
                      "and rtl/test/a3_candidate_mask_harness.cpp from cm_ids.hex"),
        "case_record": [
            "geometry", "subopcode", "width", "id_count", "cfg_block",
            "max_population", "ids_base", "out_base", "expect_error_code",
            "expect_error_detail", "expect_error_slot", "expect_error_value",
            "expect_mask_words", "expect_population", "expect_blocks",
            "expect_base",
        ],
        "detail_names": {str(k): v for k, v in DETAIL_NAMES.items()},
        "cases": summaries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args(argv)
    manifest = emit(build_cases(), args.out_dir)
    if args.manifest is not None:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"cases={manifest['totals']['cases']} "
          f"mask_words={manifest['totals']['mask_words']} "
          f"ids={manifest['totals']['ids']} "
          f"refusals={manifest['totals']['refusals']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
