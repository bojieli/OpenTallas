#!/usr/bin/env python3
"""Build the images and expectations for the PC64 partial-collector campaign.

``rtl/abi3/ot_a3_partial_collector.sv`` transposes ``ot_a3_tile64``'s partial
port -- one K-block at a time, 64 lanes wide -- into
``ot_a3_tree_endpoint_fp32``'s leaf port -- one output element at a time, B
K-blocks wide, in ascending block index.  This builder emits the partials, the
case table that tells the top how to present them, and the tree root of every
emitted vector, taken from ``tools/am_e1_lane_reference.py::re8_chain`` -- the
same reference ``results/rtl/abi3_re8.json`` and ``results/rtl/abi3_tile64.json``
are checked against, not a second implementation of it.

Images:
  ``pc_part.hex``    binary32 partials, indexed (block, element, lane)
  ``pc_case.hex``    one 24-word record per case (layout below)
  ``pc_expect.hex``  per case, (root, tag) of every vector the endpoint retires
  ``pc_meta.hex``    case count and the campaign totals

The expectations for the fault cases are computed here from the driver's own
rules, so a change to either the driver or the block moves a case rather than
passing quietly.
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

import tools.am_e1_lane_reference as am  # noqa: E402
from tools.build_abi3_lane_vectors import hex_lines  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_collector_vectors.v1"
TILE_LANES = 64
LEAVES = 8
SLOT_ELEMS = 2
CASE_STRIDE = 24
META_WORDS = 8
# rtl/test/a3_collector_top.sv declares these image sizes
PART_WORDS = 32768
CASE_WORDS = 2048
EXPECT_WORDS = 8192

ERR_NONE = 0
ERR_SHAPE = 7

DETAIL_COLLECT_BLOCKS = 27
DETAIL_COLLECT_WINDOW = 28
DETAIL_COLLECT_ADDR = 29
DETAIL_COLLECT_KBLOCK = 30
DETAIL_COLLECT_DUPLICATE = 31
DETAIL_COLLECT_INCOMPLETE = 32

INJ_NONE = 0
INJ_ADDR = 1
INJ_KBLOCK = 2
INJ_DUPLICATE = 3
INJ_INCOMPLETE = 4
INJ_CFG_BLOCKS_ZERO = 5
INJ_CFG_BLOCKS_WIDE = 6
INJ_CFG_ELEMS_WIDE = 7

DETAIL_NAMES = {
    DETAIL_COLLECT_BLOCKS: "collect_blocks",
    DETAIL_COLLECT_WINDOW: "collect_window",
    DETAIL_COLLECT_ADDR: "collect_addr",
    DETAIL_COLLECT_KBLOCK: "collect_kblock",
    DETAIL_COLLECT_DUPLICATE: "collect_duplicate",
    DETAIL_COLLECT_INCOMPLETE: "collect_incomplete",
}


def fp32_codes(rng: np.random.Generator, count: int, low: int, high: int) -> list[int]:
    """Random finite binary32 codes with the exponent field in [low, high]."""
    sign = rng.integers(0, 2, size=count, dtype=np.uint64)
    expo = rng.integers(low, high + 1, size=count, dtype=np.uint64)
    frac = rng.integers(0, 1 << 23, size=count, dtype=np.uint64)
    codes = ((sign << 31) | (expo << 23) | frac).astype(np.uint64)
    return [int(c) for c in codes]


class Case:
    def __init__(self, name: str, note: str, blocks: int, elems: int, mode: int,
                 inject: int = INJ_NONE, cfg_blocks: int | None = None,
                 cfg_elems: int | None = None, out_base: int = 0) -> None:
        self.name = name
        self.note = note
        self.blocks = blocks
        self.elems = elems
        self.mode = mode
        self.inject = inject
        self.cfg_blocks = blocks if cfg_blocks is None else cfg_blocks
        self.cfg_elems = elems if cfg_elems is None else cfg_elems
        self.out_base = out_base
        self.case_id = -1
        self.part_base = 0
        self.root_base = 0
        self.partials: list[int] = []
        self.roots: list[int] = []
        self.expect_code = ERR_NONE
        self.expect_detail = 0
        self.expect_lane = 0
        self.expect_slot = 0
        self.expect_vectors = 0
        self.expect_captured = 0
        self.expect_roots = 0


def build_cases() -> list[Case]:
    return [
        Case("b2_e1_lockstep", "B = 2, one element per lane: the decode geometry "
             "(rows 1, cols 64) the two-tile chain runs", 2, 1, 0),
        Case("b8_e1_lockstep", "B = 8, the endpoint's full leaf count", 8, 1, 0),
        Case("b1_e1_lockstep", "B = 1: a single K-block passes the leaf through "
             "(the endpoint's m = 1 path)", 1, 1, 0),
        Case("b5_e1_lockstep", "B = 5, an odd leaf count: the carry rule at every level",
             5, 1, 0),
        Case("b3_e2_lockstep", "B = 3 with two elements per lane: the whole 4 KiB buffer",
             3, 2, 0),
        Case("b8_e2_lockstep", "B = 8 and two elements: the buffer at capacity", 8, 2, 0),
        Case("b4_e1_perlane", "B = 4 presented one lane per cycle: the lanes' leaf "
             "stores are independent, so a staggered producer changes nothing", 4, 1, 1),
        Case("b2_e2_perlane", "B = 2, two elements, one lane per cycle", 2, 2, 1),
        Case("b3_e1_base", "a nonzero op_out_base: the element is the offset from "
             "the K-block's own base", 3, 1, 0, out_base=1024),
        Case("fault_addr", "a partial outside its K-block window", 3, 1, 0, inject=INJ_ADDR),
        Case("fault_kblock", "a K-block index at or above B", 3, 1, 0, inject=INJ_KBLOCK),
        Case("fault_duplicate", "the same leaf written twice", 3, 1, 0, inject=INJ_DUPLICATE),
        Case("fault_incomplete", "a slot ready without all B leaves", 3, 1, 0,
             inject=INJ_INCOMPLETE),
        Case("refuse_blocks_zero", "B = 0", 3, 1, 0, inject=INJ_CFG_BLOCKS_ZERO, cfg_blocks=0),
        Case("refuse_blocks_wide", "B above the endpoint's leaf count: the chained "
             "upper tree is not this block's business", 3, 1, 0,
             inject=INJ_CFG_BLOCKS_WIDE, cfg_blocks=LEAVES + 1),
        Case("refuse_elems_wide", "a window wider than the 4 KiB leaf buffer", 3, 1, 0,
             inject=INJ_CFG_ELEMS_WIDE, cfg_elems=SLOT_ELEMS + 1),
    ]


def evaluate(case: Case, rng: np.random.Generator) -> None:
    """Partials, roots and the expectation for one case."""
    total = case.blocks * case.elems * TILE_LANES
    # A mixed exponent window: some vectors cancel, some are dominated by one leaf.
    case.partials = fp32_codes(rng, total, 110, 145)
    if case.inject in (INJ_CFG_BLOCKS_ZERO, INJ_CFG_BLOCKS_WIDE, INJ_CFG_ELEMS_WIDE):
        case.expect_code = ERR_SHAPE
        case.expect_detail = (DETAIL_COLLECT_BLOCKS
                              if case.inject != INJ_CFG_ELEMS_WIDE
                              else DETAIL_COLLECT_WINDOW)
        return
    if case.inject == INJ_ADDR:
        case.expect_code, case.expect_detail = ERR_SHAPE, DETAIL_COLLECT_ADDR
        case.expect_slot = case.elems
        return
    if case.inject == INJ_KBLOCK:
        case.expect_code, case.expect_detail = ERR_SHAPE, DETAIL_COLLECT_KBLOCK
        case.expect_slot = case.blocks
        return
    if case.inject == INJ_DUPLICATE:
        case.expect_code, case.expect_detail = ERR_SHAPE, DETAIL_COLLECT_DUPLICATE
        case.expect_captured = TILE_LANES
        return
    if case.inject == INJ_INCOMPLETE:
        case.expect_code, case.expect_detail = ERR_SHAPE, DETAIL_COLLECT_INCOMPLETE
        case.expect_captured = total - 1
        return
    # clean: every slot, in ascending (lane, element) order
    case.expect_captured = total
    case.expect_vectors = TILE_LANES * case.elems
    case.expect_roots = case.expect_vectors
    for lane in range(TILE_LANES):
        for e in range(case.elems):
            leaves = [case.partials[(b * case.elems + e) * TILE_LANES + lane]
                      for b in range(case.blocks)]
            root, _stages = am.re8_chain(leaves, LEAVES)
            if am.pairwise_tree(leaves) != root:
                raise RuntimeError(f"{case.name}: re8_chain differs from pairwise_tree")
            case.roots.append(root)


def emit(cases: list[Case], out_dir: Path, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    part: list[int] = []
    expect: list[int] = []
    records: list[int] = []
    totals = {"partials": 0, "vectors": 0, "roots": 0, "faults": 0}
    summaries: list[dict[str, Any]] = []
    for case_id, case in enumerate(cases):
        case.case_id = case_id
        evaluate(case, rng)
        case.part_base = len(part)
        part.extend(case.partials)
        case.root_base = len(expect)
        for index, root in enumerate(case.roots):
            expect.append(root)
            expect.append(index)
        totals["partials"] += case.expect_captured
        totals["vectors"] += case.expect_vectors
        totals["roots"] += case.expect_roots
        totals["faults"] += 1 if case.expect_code else 0
        record = [
            case.blocks, case.elems, case.out_base, case.part_base, case.mode,
            case.inject, case.cfg_blocks, case.cfg_elems,
            case.expect_code, case.expect_detail, case.expect_lane, case.expect_slot,
            case.expect_vectors, case.expect_captured, case.expect_roots, case.root_base,
            1, case_id, 0, 0, 0, 0, 0, 0,
        ]
        assert len(record) == CASE_STRIDE
        records.extend(record)
        summaries.append({
            "id": case_id, "name": case.name, "note": case.note,
            "blocks": case.blocks, "elements_per_lane": case.elems, "mode": case.mode,
            "inject": case.inject, "cfg_blocks": case.cfg_blocks,
            "cfg_elems": case.cfg_elems, "out_base": case.out_base,
            "expect_error_code": case.expect_code,
            "expect_error_detail": case.expect_detail,
            "expect_error_detail_name": DETAIL_NAMES.get(case.expect_detail, "none"),
            "expect_vectors": case.expect_vectors,
            "expect_captured": case.expect_captured,
            "expect_roots": case.expect_roots,
        })
    meta = [len(cases), totals["partials"], totals["vectors"], totals["roots"],
            totals["faults"], TILE_LANES, LEAVES, SLOT_ELEMS]
    out_dir.mkdir(parents=True, exist_ok=True)
    # The top declares fixed image sizes; pad so that $readmemh reads a full
    # array and the run log carries no "not enough words" noise.
    def pad(values: list[int], size: int, name: str) -> list[int]:
        if len(values) > size:
            raise RuntimeError(f"{name} needs {len(values)} words, the top declares {size}")
        return values + [0] * (size - len(values))

    files = {
        "pc_part.hex": hex_lines(pad(part, PART_WORDS, "pc_part.hex"), 8),
        "pc_case.hex": hex_lines(pad(records, CASE_WORDS, "pc_case.hex"), 8),
        "pc_expect.hex": hex_lines(pad(expect, EXPECT_WORDS, "pc_expect.hex"), 8),
        "pc_meta.hex": hex_lines(pad(meta, META_WORDS, "pc_meta.hex"), 8),
    }
    digests = {}
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
        digests[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    marker = (f"PASS: ABI3 partial collector cases={len(cases)} "
              f"vectors={totals['vectors']} roots={totals['roots']}")
    manifest = {
        "schema": SCHEMA,
        "seed": seed,
        "geometry": {"tile_lanes": TILE_LANES, "leaves": LEAVES,
                     "slot_elems": SLOT_ELEMS, "case_stride": CASE_STRIDE,
                     "part_words": len(part), "expect_words": len(expect),
                     "case_words": len(records)},
        "totals": totals,
        "required_marker_prefix": marker,
        "reference": {
            "roots": "tools/am_e1_lane_reference.py::re8_chain, asserted equal to "
                     "pairwise_tree (which am_e1_lane_reference asserts against "
                     "runtime/sim/engines/reduction.py::ordered_sum in PAIRWISE_TREE)",
            "leaf_vectors": "checked by each checker directly against pc_part.hex: "
                            "vector v = slot (lane, e) with lane = v / elems and "
                            "e = v mod elems, leaf k = the partial of K-block k",
        },
        "case_record": [
            "blocks", "elements_per_lane", "out_base", "part_base", "mode", "inject",
            "cfg_blocks", "cfg_elems", "expect_error_code", "expect_error_detail",
            "expect_error_lane", "expect_error_slot", "expect_vectors",
            "expect_captured", "expect_roots", "root_expect_base", "flags", "case_id",
            "spare", "spare", "spare", "spare", "spare", "spare",
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
    print(f"collector vectors: {len(manifest['cases'])} cases, "
          f"{manifest['totals']['vectors']} vectors -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
