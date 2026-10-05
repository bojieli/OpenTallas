#!/usr/bin/env python3
"""Build the images and expectations for the two-tile dependent-chain campaign.

The chain of section 13 item 13, as five design modules:

    ot_a3_tile64 -> ot_a3_partial_collector -> ot_a3_tree_endpoint_fp32
                 -> ot_a3_operand_receiver  -> ot_a3_tile64

The producer is (rows 1, cols 64, K = 128 B) at BF16 g = 1 with op_kblock 128,
so it emits one binary32 partial per lane per K-block.  The collector gathers
each lane's B partials into one leaf vector, the endpoint reduces it to a root,
the receiver rounds the root once to BF16 and writes it into the consumer's
activation FIFO, and the consumer is (rows 1, cols 64, K = 64) with
op_kblock = K -- its K is the producer's N, which is what makes the two
operations dependent rather than merely consecutive.

Every expectation is the exact AM-E1 reference already used by
``results/rtl/abi3_tile64.json`` and ``results/rtl/abi3_re8.json``:
``tools/build_abi3_tile64_vectors.py``'s ``evaluate_case`` for each tile's
partials, ``am.re8_chain`` for the roots, and ``rtl/ot_fp32_rne_pkg.sv``'s
binary32 -> BF16 round-to-nearest-even for the activation the receiver
delivers.  Nothing in the chain is modelled twice: the consumer's own case is
built FROM the roots the producer's case produced, so the campaign checks the
composition and not just the pieces.
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
import tools.build_abi3_tile64_vectors as t64  # noqa: E402
from tools.build_abi3_lane_vectors import BF16, bf16_window, hex_lines, pack_words  # noqa: E402
from tools.build_abi3_receiver_vectors import bf16_rne  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_boundary_chain_vectors.v1"
TILE_LANES = 64
LEAVES = 8
KBLOCK = 128
CASE_STRIDE = 32
META_WORDS = 8
# rtl/test/a3_boundary_chain_top.sv declares these image sizes
PSTREAM_WORDS = 4096
CSTREAM_WORDS = 512
PACT_WORDS = 4096
CASE_WORDS = 1024
EXPECT_WORDS = 8192
STREAM_CHUNKS = 32


class ChainCase:
    def __init__(self, name: str, note: str, blocks: int) -> None:
        self.name = name
        self.note = note
        self.blocks = blocks               # B: the producer's K-blocks
        self.case_id = -1
        self.producer: t64.TileCase | None = None
        self.consumer: t64.TileCase | None = None
        self.roots: list[int] = []          # 64, one per output column
        self.act_words: list[int] = []      # 64, the words the receiver must deliver
        self.cons_partials: list[int] = []  # 64, one per consumer lane
        self.p_stream: list[int] = []
        self.c_stream: list[int] = []
        self.p_act: list[int] = []
        self.p_w_base = 0
        self.c_w_base = 0
        self.p_act_base = 0
        self.expect_base = 0


def make_tile_case(name: str, depth: int, kblock: int, a_codes: np.ndarray,
                   b_codes: np.ndarray) -> t64.TileCase:
    return t64.TileCase(
        name=name, note="", rows=1, cols=64, depth=depth,
        dtype_a=BF16, dtype_b=BF16, group=1,
        a_codes=a_codes, b_codes=b_codes, kblock=kblock, out_fp32=True,
    )


def build_cases(blocks_list: list[int]) -> list[ChainCase]:
    return [ChainCase(f"b{b}", f"the producer runs {b} K-block(s) of 128, so every "
                      f"output column is a {b}-leaf reduction", b)
            for b in blocks_list]


def evaluate(case: ChainCase, rng: np.random.Generator, adder_stages: int) -> None:
    depth = case.blocks * KBLOCK
    p_a = bf16_window(rng, (1, depth), 118, 137)
    p_b = bf16_window(rng, (64, depth), 118, 137)
    producer = make_tile_case(f"chain_{case.name}_producer", depth, KBLOCK, p_a, p_b)
    t64.evaluate_case(producer, adder_stages)
    t64.check_expectation(producer)
    if not producer.tree_checked:
        raise RuntimeError(f"{case.name}: the producer refused its own descriptor")
    case.producer = producer
    case.roots = list(producer.roots)
    if len(case.roots) != TILE_LANES:
        raise RuntimeError(f"{case.name}: {len(case.roots)} roots, expected {TILE_LANES}")

    # what the receiver must deliver: one BF16 element per 64-bit word at g = 1
    codes = []
    for root in case.roots:
        error, _saturated, bf = bf16_rne(root)
        if error:
            raise RuntimeError(f"{case.name}: a root is not finite")
        codes.append(bf)
    case.act_words = list(codes)

    # the consumer: its K is the producer's N, its activations are those roots
    c_a = np.array(codes, dtype=np.uint16).reshape(1, TILE_LANES)
    c_b = bf16_window(rng, (64, TILE_LANES), 118, 137)
    consumer = make_tile_case(f"chain_{case.name}_consumer", TILE_LANES, TILE_LANES, c_a, c_b)
    t64.evaluate_case(consumer, adder_stages)
    t64.check_expectation(consumer)
    if not consumer.tree_checked:
        raise RuntimeError(f"{case.name}: the consumer refused its own descriptor")
    case.consumer = consumer
    # op_kblock = K, so B = 1 and the single partial IS the column's value
    case.cons_partials = [consumer.partials[0][lane][0] for lane in range(TILE_LANES)]

    # the activation image the producer's own H-tree broadcasts (outside the span)
    case.p_act = []
    for b in range(case.blocks):
        sub = t64.lane_block_case(producer, b, 0, 0)
        words = pack_words(sub.a_codes, BF16, 1)
        if len(words) != KBLOCK:
            raise RuntimeError(f"{case.name}: activation slice is {len(words)} words")
        case.p_act.extend(words)

    case.p_stream = []
    for b in range(case.blocks):
        case.p_stream.extend(t64.stream_words(producer, b, adder_stages))
    case.c_stream = list(t64.stream_words(consumer, 0, adder_stages))


def emit(cases: list[ChainCase], out_dir: Path, seed: int,
         adder_stages: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    pstream: list[int] = []
    cstream: list[int] = []
    pact: list[int] = []
    expect: list[int] = []
    records: list[int] = []
    summaries: list[dict[str, Any]] = []
    for case_id, case in enumerate(cases):
        case.case_id = case_id
        evaluate(case, rng, adder_stages)
        case.p_w_base = len(pstream)
        pstream.extend(case.p_stream)
        case.c_w_base = len(cstream)
        cstream.extend(case.c_stream)
        case.p_act_base = len(pact)
        pact.extend(case.p_act)
        case.expect_base = len(expect)
        expect.extend(case.roots)                                  # 64 roots
        expect.extend(case.act_words)                              # 64 activation words
        expect.extend(case.cons_partials)                          # 64 consumer partials
        # The field offsets are rtl/test/a3_boundary_chain_top.sv's, verbatim.
        record = [
            1, 64, case.blocks * KBLOCK, KBLOCK, case.blocks,        # 0..4
            0, KBLOCK, case.p_w_base, len(case.p_stream), 0, 1,      # 5..10
            case.p_act_base, KBLOCK,                                 # 11, 12
            1, 64, TILE_LANES, TILE_LANES, 1,                        # 13..17
            0, TILE_LANES, case.c_w_base, len(case.c_stream), 0, 1,  # 18..23
            0, 0, case.expect_base, case_id, adder_stages, 0, 0, 0,  # 24..31
        ]
        assert len(record) == CASE_STRIDE, len(record)
        records.extend(record)
        summaries.append({
            "id": case_id, "name": case.name, "note": case.note,
            "producer": {
                "rows": 1, "cols": 64, "depth": case.blocks * KBLOCK,
                "kblock": KBLOCK, "kblocks": case.blocks,
                "stream_words": len(case.p_stream),
                "lane_ops": case.producer.mac_count,
                "partials": case.blocks * TILE_LANES,
            },
            "consumer": {
                "rows": 1, "cols": 64, "depth": TILE_LANES, "kblock": TILE_LANES,
                "kblocks": 1, "stream_words": len(case.c_stream),
                "lane_ops": case.consumer.mac_count,
            },
            "leaves_per_output_element": case.blocks,
            "root_0": f"0x{case.roots[0]:08x}",
            "activation_word_0": f"0x{case.act_words[0]:04x}",
            "consumer_partial_0": f"0x{case.cons_partials[0]:08x}",
        })

    def pad(values: list[int], size: int, name: str) -> list[int]:
        if len(values) > size:
            raise RuntimeError(f"{name} needs {len(values)} words, the top declares {size}")
        return values + [0] * (size - len(values))

    meta = [len(cases), sum(len(c.p_stream) for c in cases),
            sum(len(c.c_stream) for c in cases), TILE_LANES, adder_stages,
            CASE_STRIDE, LEAVES, KBLOCK]
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "ch_pstream.hex": hex_lines(
            pad(t64.chunks32(pstream, 1024), STREAM_CHUNKS * PSTREAM_WORDS,
                "ch_pstream.hex"), 8),
        "ch_cstream.hex": hex_lines(
            pad(t64.chunks32(cstream, 1024), STREAM_CHUNKS * CSTREAM_WORDS,
                "ch_cstream.hex"), 8),
        "ch_pact.hex": hex_lines(
            pad(t64.chunks32(pact, 64), 2 * PACT_WORDS, "ch_pact.hex"), 8),
        "ch_case.hex": hex_lines(pad(records, CASE_WORDS, "ch_case.hex"), 8),
        "ch_expect.hex": hex_lines(pad(expect, EXPECT_WORDS, "ch_expect.hex"), 8),
        "ch_meta.hex": hex_lines(pad(meta, META_WORDS, "ch_meta.hex"), 8),
    }
    digests = {}
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
        digests[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    marker = f"PASS: ABI3 two-tile dependent chain cases={len(cases)}"
    manifest = {
        "schema": SCHEMA,
        "seed": seed,
        "adder_stages": adder_stages,
        "geometry": {
            "tile_lanes": TILE_LANES, "leaves": LEAVES, "kblock": KBLOCK,
            "case_stride": CASE_STRIDE,
            "producer_stream_words": len(pstream),
            "consumer_stream_words": len(cstream),
            "producer_activation_words": len(pact),
            "expect_words": len(expect), "case_words": len(records),
        },
        "required_marker_prefix": marker,
        "reference": {
            "partials": "tools/build_abi3_tile64_vectors.py::evaluate_case "
                        "(tools/am_e1_lane_reference.py element_chain per lane per "
                        "K-block), the same reference results/rtl/abi3_tile64.json "
                        "is checked against",
            "roots": "tools/am_e1_lane_reference.py::re8_chain over those partials, "
                     "asserted equal to pairwise_tree",
            "activation": "binary32 -> BF16 round-to-nearest-even, the contract of "
                          "rtl/ot_fp32_rne_pkg.sv::fp32_to_bf16_rne",
            "composition": "the consumer's case is built FROM the producer's roots, "
                           "so its expected partials are only reachable if every "
                           "stage of the chain delivered the right value",
        },
        "case_record": [
            "p_rows", "p_cols", "p_depth", "p_kblock", "p_blocks", "p_a_base",
            "p_a_stride", "p_w_base", "p_w_words", "p_out_base", "p_out_stride",
            "p_act_img_base", "p_act_slice_words",
            "c_rows", "c_cols", "c_depth", "c_kblock", "c_blocks", "c_a_base",
            "c_a_stride", "c_w_base", "c_w_words", "c_out_base", "c_out_stride",
            "spare", "spare", "expect_base", "case_id", "adder_stages",
            "spare", "spare", "spare",
        ],
        "expect_layout": (
            "per case at expect_base: 64 binary32 roots, then 64 BF16 activation "
            "words (in the low 16 bits), then 64 binary32 consumer partials"),
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
    parser.add_argument("--adder-stages", type=int, default=3)
    parser.add_argument("--blocks", type=int, nargs="+", default=[1, 2, 3, 5, 8])
    args = parser.parse_args(argv)
    manifest = emit(build_cases(args.blocks), args.out_dir, args.seed, args.adder_stages)
    print(f"chain vectors: {len(manifest['cases'])} cases, L={args.adder_stages} "
          f"-> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
