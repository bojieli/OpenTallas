#!/usr/bin/env python3
"""Build the leaf-vector images and expectations for the RE8 endpoint campaign.

One suite, ``re8``, for ``results/rtl/abi3_re8.json``: every case is a sequence
of leaf vectors presented to ``rtl/abi3/ot_a3_tree_endpoint_fp32.sv`` (LEAVES =
8), with the expected output of every vector computed by the exact K-block
tree reference (``tools/am_e1_lane_reference.py``: ``re8_combine`` for one
endpoint, ``re8_chain`` for the chained shapes, both asserted against
``pairwise_tree``, which is asserted against
``runtime/sim/engines/reduction.py::ordered_sum(PAIRWISE_TREE)``).

The chained shapes are the ones docs/CHIP_ARCHITECTURE_DESIGN.md section 4.4
names: K = 4,096 (32 leaves: stage 1 = four 8-leaf vectors, stage 2 = one
4-leaf vector) and K = 12,288 (96 leaves: twelve, then [8, 4], then [2]).
A stage's vectors carry the previous stage's *expected* outputs as leaves, so
every endpoint in the chain is checked against the reference on its own; the
chain equality itself is the reference's assertion.  Directed vectors cover
subnormal sums, equal-exponent cancellation, ties, the -0.0 leaf
canonicalisation, results just below 2**128, and every fault class at every
level; a rate case streams full vectors back to back.

Images (32-bit words):

``re8_vec.hex``   one vector per VEC_STRIDE words: count, tag, flags (bit 0
                  last, bit 1 an output is expected), leaves 0..7, expected
                  output code
``re8_case.hex``  one record per case (layout in rtl/test/tb_a3_re8.sv)
``re8_meta.hex``  case count and the campaign totals

Images are regenerated deterministically at campaign time from the seed;
``testdata/rtl/abi3_re8/manifest_<profile>_L<L>.json`` pins their digests.
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
from tools.build_abi3_lane_vectors import hex_lines  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_re8_vectors.v1"
LEAVES = 8
VEC_STRIDE = 12
CASE_STRIDE = 16
META_WORDS = 8
FLAG_VEC_LAST = 0x1
FLAG_VEC_EXPECT = 0x2
FLAG_STREAM = 0x1
FLAG_FAULT = 0x2
FLAG_RATE = 0x4
FLAG_SINGLE = 0x8
MANIFEST_DIR = ROOT / "testdata/rtl/abi3_re8"

ERR_NAMES = {am.ERR_NONE: "none", am.ERR_OPERAND_NONFINITE: "operand_nonfinite",
             am.ERR_ACCUMULATE_RANGE: "accumulate_range", am.ERR_SHAPE: "shape"}


@dataclass
class Vector:
    count: int
    leaves: list[int]           # raw codes presented to the RTL (may hold -0.0 or NaN)
    tag: int
    last: bool = False
    expect: int | None = None   # expected output code, None if the vector faults / is dropped
    fault: tuple[int, int] | None = None   # (detail, level) if this vector faults


@dataclass
class Case:
    name: str
    note: str
    vectors: list[Vector]
    stream: bool = True
    rate: bool = False
    mode_name: str | None = None
    leaves_in_chain: int = 0
    shape: str | None = None
    # filled by the builder
    case_id: int = -1
    vec_base: int = 0
    error_code: int = 0
    error_detail: int = 0
    error_level: int = 0
    error_tag: int = 0
    outputs: int = 0
    adds: int = 0
    combines: int = 0
    extras: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Leaf generators
# ---------------------------------------------------------------------------
def f32_code(value: float) -> int:
    return int(np.float32(value).view(np.uint32))


def random_codes(rng: np.random.Generator, count: int, low: int = -140, high: int = 100,
                 zero_rate: float = 0.05) -> list[int]:
    exponents = rng.integers(low, high + 1, size=count)
    mantissas = rng.random(count) + 1.0
    signs = rng.choice([-1.0, 1.0], size=count)
    values = (signs * mantissas * np.exp2(exponents.astype(np.float64))).astype(np.float32)
    zeros = rng.random(count) < zero_rate
    values[zeros] = np.float32(0.0)
    return [int(v) for v in values.view(np.uint32)]


def canonical(code: int) -> int:
    """What the endpoint's unpack does to a leaf: -0.0 -> +0.0."""
    return 0 if (code & 0x7FFFFFFF) == 0 else code


# ---------------------------------------------------------------------------
# Building vectors from the reference
# ---------------------------------------------------------------------------
def single_vector(codes: list[int], tag: int, last: bool = False, count: int | None = None) -> Vector:
    """One endpoint vector; the expectation or the fault comes from re8_combine.

    ``count`` defaults to the number of codes; a smaller count leaves the
    remaining slots holding whatever is given (the endpoint ignores them).
    """
    if count is None:
        count = len(codes)
    try:
        root, _levels, _adds = am.re8_combine([canonical(c) for c in codes[:count]], LEAVES)
        return Vector(count, list(codes), tag, last, root, None)
    except am.TreeFault as fault:
        return Vector(count, list(codes), tag, last, None, (fault.detail, fault.level))


def chain_vectors(codes: list[int], tag0: int) -> tuple[list[Vector], int, list[dict[str, Any]]]:
    """The chained-endpoint vectors of one tree over ``codes`` leaves (no faults)."""
    root, stages = am.re8_chain([canonical(c) for c in codes], LEAVES)
    vectors: list[Vector] = []
    tag = tag0
    if not stages:
        # One leaf: the chain is a single count-1 pass-through.
        vectors.append(single_vector(list(codes), tag, True))
        assert vectors[0].expect == root
        return vectors, root, [{"groups": [1], "adds": [0]}]
    for stage in stages:
        for group, output in zip(stage["inputs"], stage["outputs"]):
            vectors.append(Vector(len(group), list(group), tag, False, output, None))
            tag += 1
    vectors[-1].last = True
    return vectors, root, [{"groups": [len(g) for g in s["inputs"]], "adds": s["adds"]} for s in stages]


def build_cases(rng: np.random.Generator, profile: str) -> list[Case]:
    cases: list[Case] = []
    tag = 1

    def add(name, note, vectors, *, stream=True, rate=False, mode_name=None, leaves=0, shape=None):
        cases.append(Case(name, note, vectors, stream, rate, mode_name, leaves, shape))

    # -- the worked example of section 4.3 / 4.4 (K = 4,096, one column) -------------
    worked = [0x4B800000] + [0x3F800000] * 31
    vectors, root, stages = chain_vectors(worked, tag)
    tag += len(vectors)
    assert root == 0x4B80000F, f"{root:#010x}"
    assert [v.expect for v in vectors[:4]] == [0x4B800003, 0x41000000, 0x41000000, 0x41000000]
    add("worked_example_k4096", "P_0 = 2**24, P_1..P_31 = 1.0: stage 1 [8,8,8,8] -> stage 2 [4] = 0x4B80000F "
        "(the flat 32-leaf recurrence; sequential ascending would give 0x4B800000, the exact sum 16,777,247)",
        vectors, leaves=32, shape="K=4096")
    cases[-1].extras = {"stages": stages, "root": f"{root:#010x}", "sequential_ascending": "0x4b800000",
                        "exact_sum": 16777247}

    # -- the two chained shapes, random leaves ---------------------------------------------
    chains = 6 if profile == "full" else 2
    for index in range(chains):
        codes = random_codes(rng, 32, -60, 60)
        vectors, root, stages = chain_vectors(codes, tag)
        tag += len(vectors)
        add(f"chain_k4096_{index}", "32 random leaves through 4 + 1 endpoints", vectors, leaves=32, shape="K=4096")
        cases[-1].extras = {"stages": stages, "root": f"{root:#010x}"}
    for index in range(chains):
        codes = random_codes(rng, 96, -60, 60)
        vectors, root, stages = chain_vectors(codes, tag)
        tag += len(vectors)
        add(f"chain_k12288_{index}", "96 random leaves through 12 + 2 + 1 endpoints", vectors, leaves=96,
            shape="K=12288")
        cases[-1].extras = {"stages": stages, "root": f"{root:#010x}"}
    # every leaf count 1..64 once (every tail shape of every stage)
    for count in range(1, 65):
        codes = random_codes(rng, count, -30, 30)
        vectors, root, stages = chain_vectors(codes, tag)
        tag += len(vectors)
        add(f"chain_n{count}", f"{count} leaves: every endpoint count and carry pattern the chain produces",
            vectors, leaves=count)
        cases[-1].extras = {"stages": stages}

    # -- single vectors, every count, random and directed -------------------------------------
    for count in range(1, LEAVES + 1):
        vectors = [single_vector(random_codes(rng, count, -100, 100), tag + k, k == 3) for k in range(4)]
        tag += 4
        add(f"count_{count}", f"{count} valid leaves, 4 random vectors", vectors)
    # invalid leaf slots hold anything, including NaN, and are ignored
    codes = [0x3F800000, 0x40000000, 0x40400000] + [0x7FC00000] * 5
    add("invalid_slots_ignored", "count 3 with NaN in the five invalid slots: no fault, 1 + 2 + 3 = 6",
        [single_vector(codes, tag, count=3)])
    assert cases[-1].vectors[0].expect == 0x40C00000
    tag += 1
    # signed zero canonicalisation
    add("negative_zero_leaves", "-0.0 leaves and a count-1 pass-through: every result is +0.0",
        [single_vector([0x80000000] * 8, tag), single_vector([0x80000000], tag + 1),
         single_vector([0x80000000, 0x00000000, 0x80000000], tag + 2)])
    tag += 3
    assert all(v.expect == 0 for v in cases[-1].vectors)
    # subnormals
    add("subnormal_sums", "sums inside and across the binary32 subnormal range, ties to even on the grid",
        [single_vector([0x00000001] * 8, tag),
         single_vector([0x00000001, 0x00000002, 0x00000004, 0x00000008, 0x00000010, 0x00000020, 0x00000040,
                        0x00000080], tag + 1),
         single_vector([0x007FFFFF, 0x00000001, 0x00000000, 0x00000000], tag + 2),
         single_vector([0x00800000, 0x80000001] + [0] * 6, tag + 3),
         single_vector(random_codes(rng, 8, -149, -120), tag + 4),
         single_vector(random_codes(rng, 8, -140, -126), tag + 5)])
    tag += 6
    # cancellation and ties
    add("cancellation_and_ties", "x + (-x) at every level, equal exponents, half-ulp ties rounding to even",
        [single_vector([0x40400000, 0xC0400000] * 4, tag),
         single_vector([0x40400000, 0x40400000, 0xC0400000, 0xC0400000, 0x3F800000, 0xBF800000, 0x00000000,
                        0x00000000], tag + 1),
         single_vector([0x4B800000, 0x3F800000, 0x4B800000, 0x3F800000, 0x4B800001, 0x3F800000, 0x4B800001,
                        0x3F800000], tag + 2),
         single_vector([0x3F800000, 0x33800000, 0x3F800000, 0x33800001, 0x3F800001, 0x33800000, 0x00000000,
                        0x00000000], tag + 3),
         single_vector([0x4B000000, 0xCAFFFFFF, 0x3F800000, 0x00000000], tag + 4)])
    tag += 5
    # the top of the range, no fault
    add("near_overflow", "results just below 2**128 without a fault",
        [single_vector([0x7F7FFFFF, 0x00000001] + [0] * 6, tag),
         single_vector([0x7F000000, 0x7EFFFFFE, 0x00000000, 0x00000000], tag + 1),   # exactly the max
         single_vector([0x7F7FFFFF, 0x72FFFFFF] + [0] * 6, tag + 2),
         single_vector([0x7F7FFFFF, 0xFF7FFFFF, 0x7F7FFFFF, 0x00000000], tag + 3)])
    tag += 4
    assert cases[-1].vectors[2].expect == 0x7F7FFFFF     # just under half an ulp: rounds down to the max
    add("mixed_magnitudes", "random vectors over 2**-140 .. 2**100 with mixed signs and zeros",
        [single_vector(random_codes(rng, LEAVES, -140, 100), tag + k, k == 15) for k in range(16)])
    tag += 16

    # -- faults, one per class and level ---------------------------------------------------------
    def fault_case(name, note, vectors, mode_name):
        add(name, note, vectors, mode_name=mode_name)

    big = 0x7F7FFFFF
    fault_case("fault_add_range_level1", "2**128 reached at level 1 (leaves 0 + 1)",
               [single_vector(random_codes(rng, 8, -10, 10), tag), single_vector([big, big] + [0] * 6, tag + 1),
                single_vector(random_codes(rng, 8, -10, 10), tag + 2)], "add_range_level1")
    tag += 3
    fault_case("fault_add_range_tie", "the largest finite plus exactly half an ulp: the tie rounds to even, "
               "which is 2**128 (round_pack refuses it)",
               [single_vector([0x7F7FFFFF, 0x73000000] + [0] * 6, tag)], "add_range_tie_level1")
    tag += 1
    fault_case("fault_add_range_level2", "finite level-1 sums whose level-2 sum reaches 2**128",
               [single_vector([0x7F000000, 0x7F000000, 0x7F000000, 0x7F000000] + [0] * 4, tag)],
               "add_range_level2")
    tag += 1
    fault_case("fault_add_range_level3", "finite level-2 sums whose level-3 sum reaches 2**128",
               [single_vector([0x7E800000] * 8, tag)], "add_range_level3")
    tag += 1
    fault_case("fault_leaf_nan", "a NaN leaf in a valid slot",
               [single_vector(random_codes(rng, 8, -10, 10), tag),
                single_vector([0x3F800000, 0x7FC00000, 0x3F800000], tag + 1)], "leaf_nonfinite_nan")
    tag += 2
    fault_case("fault_leaf_infinity", "an infinity leaf in the last valid slot",
               [single_vector([0x3F800000] * 7 + [0xFF800000], tag)], "leaf_nonfinite_infinity")
    tag += 1
    fault_case("fault_leaf_count_zero", "count 0 is refused",
               [Vector(0, [0x3F800000] * 8, tag, False, None, (am.DETAIL_TREE_LEAF_COUNT, 0))],
               "leaf_count_zero")
    tag += 1
    fault_case("fault_leaf_count_over", "count 9 exceeds LEAVES",
               [Vector(9, [0x3F800000] * 8, tag, False, None, (am.DETAIL_TREE_LEAF_COUNT, 0))],
               "leaf_count_over")
    tag += 1
    # a fault inside a stream: everything before it is emitted, nothing after
    vectors = [single_vector(random_codes(rng, 8, -20, 20), tag + k) for k in range(6)]
    vectors[3] = single_vector([0x3F800000, 0x3F800000, 0x7F800000, 0x3F800000], tag + 3)
    tag += 6
    fault_case("fault_mid_stream", "vector 3 of 6 holds an infinity: vectors 0..2 emitted, 3..5 dropped",
               vectors, "fault_mid_stream")
    # the same fault presented one vector at a time
    vectors = [single_vector(random_codes(rng, 8, -20, 20), tag + k) for k in range(3)]
    vectors[1] = single_vector([big, big, 0, 0], tag + 1)
    tag += 3
    add("fault_single_step", "the endpoint stops after the fault and ignores the next vector until clear",
        vectors, stream=False, mode_name="fault_single_step")

    # -- rate: full vectors back to back --------------------------------------------------------------
    count = 512 if profile == "full" else 64
    vectors = [single_vector(random_codes(rng, LEAVES, -40, 40), tag + k, k == count - 1) for k in range(count)]
    tag += count
    add("rate_stream", f"{count} full vectors back to back: one combine per cycle, latency measured",
        vectors, rate=True)
    return cases


# ---------------------------------------------------------------------------
# Expectations and emission
# ---------------------------------------------------------------------------
def evaluate(cases: list[Case]) -> None:
    for case in cases:
        outputs = 0
        adds = 0
        fault: Vector | None = None
        for vector in case.vectors:
            if fault is not None:
                vector.expect = None          # dropped after the fault
                continue
            if vector.fault is not None:
                fault = vector
                continue
            assert vector.expect is not None
            outputs += 1
            adds += vector.count - 1
        case.outputs = outputs
        case.adds = adds
        case.combines = outputs
        if fault is not None:
            detail, level = fault.fault
            case.error_code = am.tree_error_code_of_detail(detail)
            case.error_detail = detail
            case.error_level = level
            case.error_tag = fault.tag
        if case.mode_name and fault is None:
            raise RuntimeError(f"{case.name}: fault case without a fault")
        if not case.mode_name and fault is not None:
            raise RuntimeError(f"{case.name}: unexpected fault {fault.fault}")


def emit(cases: list[Case], out_dir: Path, adder_stages: int, profile: str, seed: int) -> dict[str, Any]:
    vec_words: list[int] = []
    case_words: list[int] = []
    totals = {"vectors": 0, "outputs": 0, "faults": 0, "adds": 0, "combines": 0}
    summaries: list[dict[str, Any]] = []
    for case_id, case in enumerate(cases):
        case.case_id = case_id
        case.vec_base = len(vec_words) // VEC_STRIDE
        for vector in case.vectors:
            leaves = list(vector.leaves) + [0] * (LEAVES - len(vector.leaves))
            flags = (FLAG_VEC_LAST if vector.last else 0) | (FLAG_VEC_EXPECT if vector.expect is not None else 0)
            record = [vector.count, vector.tag, flags, *leaves[:LEAVES],
                      vector.expect if vector.expect is not None else 0]
            assert len(record) == VEC_STRIDE
            vec_words.extend(record)
        flags = ((FLAG_STREAM if case.stream else FLAG_SINGLE) | (FLAG_FAULT if case.error_code else 0)
                 | (FLAG_RATE if case.rate else 0))
        record = [case_id, case.vec_base, len(case.vectors), flags, case.error_code, case.error_detail,
                  case.error_level, case.error_tag, case.outputs, case.adds, case.combines, case.leaves_in_chain,
                  0, 0, 0, 0]
        assert len(record) == CASE_STRIDE
        case_words.extend(record)
        totals["vectors"] += len(case.vectors)
        totals["outputs"] += case.outputs
        totals["faults"] += 1 if case.error_code else 0
        totals["adds"] += case.adds
        totals["combines"] += case.combines
        summaries.append({
            "id": case_id, "name": case.name, "note": case.note, "vectors": len(case.vectors),
            "stream": case.stream, "rate": case.rate, "mode_name": case.mode_name,
            "leaves_in_chain": case.leaves_in_chain, "shape": case.shape,
            "expected": {"error_code": case.error_code, "error_detail": case.error_detail,
                         "error_level": case.error_level, "error_tag": case.error_tag,
                         "outputs": case.outputs, "adds": case.adds, "combines": case.combines},
            "extras": case.extras,
        })
    meta = [len(cases), totals["vectors"], totals["outputs"], totals["faults"], totals["adds"],
            totals["combines"], CASE_STRIDE, VEC_STRIDE]
    assert len(meta) == META_WORDS
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "re8_vec.hex": hex_lines(vec_words, 8),
        "re8_case.hex": hex_lines(case_words, 8),
        "re8_meta.hex": hex_lines(meta, 8),
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
                "error_detail": case.error_detail, "error_level": case.error_level,
                "error_tag": case.error_tag, "detail_name": am.DETAIL_NAMES.get(case.error_detail, "?"),
                "class_name": ERR_NAMES.get(case.error_code, "?"),
            }
    marker = (f"PASS: ABI3 re8 cases={len(cases)} vectors={totals['vectors']} outputs={totals['outputs']} "
              f"faults={totals['faults']} adds={totals['adds']} combines={totals['combines']}")
    manifest = {
        "schema": SCHEMA, "suite": "re8", "profile": profile, "seed": seed, "leaves": LEAVES,
        "adder_stages": adder_stages, "case_stride": CASE_STRIDE, "vec_stride": VEC_STRIDE,
        "totals": totals, "required_marker_prefix": marker,
        "rate_cases": [{"case": c.case_id, "vectors": len(c.vectors)} for c in cases if c.rate],
        "failure_modes": modes, "image_sha256": digests, "cases": summaries,
        "reference": {
            "model": "tools/am_e1_lane_reference.py (re8_combine, re8_chain, pairwise_tree)",
            "source_of_truth": "runtime/sim/engines/reduction.py::ordered_sum, ReductionOrder.PAIRWISE_TREE",
            "numeric_authority": "runtime/reference/formats.py (fractions.Fraction, encode_binary32_rne), pinned to np.add float32",
            "chained_shapes": "K = 4,096: [8,8,8,8] then [4]; K = 12,288: 12 x [8] then [8,4] then [2]",
            "signed_zero": "a -0.0 leaf is canonicalised to +0.0 by the endpoint; the reference is given the canonical leaf",
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--adder-stages", type=int, default=3)
    parser.add_argument("--profile", choices=("quick", "full"), default="full")
    parser.add_argument("--seed", type=int, default=20260905)
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args(argv)
    rng = np.random.default_rng(args.seed)
    cases = build_cases(rng, args.profile)
    evaluate(cases)
    manifest = emit(cases, args.out_dir, args.adder_stages, args.profile, args.seed)
    if args.write_manifest:
        target = MANIFEST_DIR / f"manifest_{args.profile}_L{args.adder_stages}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"manifest -> {target}")
    print(f"re8: {len(cases)} cases, {manifest['totals']['vectors']} vectors, "
          f"{manifest['totals']['adds']} adds -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
