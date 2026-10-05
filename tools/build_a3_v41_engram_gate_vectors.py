#!/usr/bin/env python3
"""Build the VECTOR.ENGRAM_GATE dual-simulator vector set from the reference.

Every expected word comes from ``runtime.reference.engram.engram_gate``, which is
written from the mechanism semantics of the V4.1 plan and the exact binary32
primitives of ``runtime/reference/formats.py``.  Nothing here reads RTL, a
compiler artifact, a cost table or a simulator log.

Three GEOMETRIES are emitted, and the point of emitting three is the acceptance
criterion that no model dimension is frozen into the block:

  g0  VECTOR_WIDTH 256, LANES 4, ACC_EXP_MAX 64    the V4.1-Flash row width
  g1  VECTOR_WIDTH 256, LANES 8, ACC_EXP_MAX 64    same rows, twice the lanes
  g2  VECTOR_WIDTH 272, LANES 4, ACC_EXP_MAX 64    a row LONGER than V4.1's
  g3  VECTOR_WIDTH 272, LANES 4, ACC_EXP_MAX 128   a window wide enough for the
                                                   reduction to round out of
                                                   binary32 range, which is the
                                                   only way sites 4 and 5 are
                                                   reachable at all

The same cases run on all three.  Because the reduction is exact, every computed
code must be byte-identical across g0 and g1; the only field permitted to differ
is the group-aligned count of output words a combine-phase refusal is allowed to
have written, which is a property of the lane grouping and is checked as such.
g2 additionally accepts the 257- and 272-element rows that g0 and g1 refuse with
ERR_SHAPE, which is the direct test that a shape the datapath can compute is not
refused by a constant.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import struct
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.engram import (  # noqa: E402
    ENGRAM_GATE_DEFAULT_ACC_EXP_MAX,
    ENGRAM_GATE_DEFAULT_ACC_EXP_MIN,
    ENGRAM_GATE_EPSILON_BINARY32,
    ENGRAM_GATE_NUMERIC_CONTRACT,
    REFUSAL_NONE,
    engram_gate,
)

DEFAULT_OUTPUT = ROOT / "testdata/rtl/a3_v41_engram_gate"

MAGIC = 0xA341_E9A7
VERSION = 1
SENTINEL = 0xDEADBEEF
#: Words per request record and per expectation record header.
CASE_WORDS = 8
EXPECT_SCALARS = 16
#: Longest row any case issues; also the size of one operand region.
VECTOR_LIMIT = 272
#: Regions: h, key, value, q, k, out.
REGION_COUNT = 6
MEMORY_WORDS = (REGION_COUNT + 1) * VECTOR_LIMIT

GEOMETRIES: tuple[dict[str, int], ...] = (
    {"name": "g0", "vector_width": 256, "lanes": 4, "acc_exp_max": 64},
    {"name": "g1", "vector_width": 256, "lanes": 8, "acc_exp_max": 64},
    {"name": "g2", "vector_width": 272, "lanes": 4, "acc_exp_max": 64},
    #: ACC_EXP_MAX 128 admits a single product that already leaves binary32
    #: finite range, which is what makes the two rounding sites reachable.  The
    #: exact accumulator is then 265 bits, inside the 320-bit summary port.
    {"name": "g3", "vector_width": 272, "lanes": 4, "acc_exp_max": 128},
)


def code(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


NAN = 0x7FC00000
POSITIVE_INFINITY = 0x7F800000
NEGATIVE_INFINITY = 0xFF800000


def _row(generator: random.Random, width: int, scale: float = 1.0) -> list[int]:
    return [code(generator.uniform(-scale, scale)) for _ in range(width)]


def build_cases() -> list[dict[str, Any]]:
    """Assemble the case list.  Each case is one ENGRAM_GATE transaction."""

    generator = random.Random(0xE9A7)
    cases: list[dict[str, Any]] = []

    def add(label: str, width: int, hidden, key, value, query, gate_key) -> None:
        cases.append(
            {
                "label": label,
                "width": width,
                "h": list(hidden),
                "key": list(key),
                "value": list(value),
                "q": list(query),
                "k": list(gate_key),
            }
        )

    # ---- random rows over a wide span of widths, including 1 and the V4.1
    # ---- row width itself, and widths that are not multiples of any LANES.
    for width in (1, 2, 3, 4, 5, 7, 8, 16, 31, 32, 64, 127, 128, 255, 256):
        add(
            f"random_w{width}",
            width,
            _row(generator, width),
            _row(generator, width),
            _row(generator, width),
            _row(generator, width),
            _row(generator, width),
        )

    # ---- directed numeric boundaries -----------------------------------
    #: An all-zero row: both norms are zero, the rounded norm product is zero,
    #: the 1e-6 clamp fires, the normalised dot is +0 and the gate is exactly
    #: 0.5.  This is the clamp's own test and it is not reachable by chance.
    add("all_zero_w4", 4, [0] * 4, [0] * 4, [0] * 4, [0] * 4, [0] * 4)

    #: Norms far below the clamp floor: the clamp fires on a nonzero product.
    tiny = code(2.0**-30)
    add(
        "clamped_tiny_w4",
        4,
        _row(generator, 4),
        _row(generator, 4),
        _row(generator, 4),
        [tiny] * 4,
        [tiny] * 4,
    )

    #: q = -k, so the normalised dot is -1 and the SIGNED square root is
    #: negative.  A plain square root could not produce this gate.
    unit = code(0.5)
    add(
        "antiparallel_w8",
        8,
        _row(generator, 8),
        _row(generator, 8),
        _row(generator, 8),
        [unit] * 8,
        [code(-0.5)] * 8,
    )

    #: q = k, the +1 end of the same axis.
    add(
        "parallel_w8",
        8,
        _row(generator, 8),
        _row(generator, 8),
        _row(generator, 8),
        [unit] * 8,
        [unit] * 8,
    )

    #: Exactly on the exactness-window ceiling: q_i = 2**31 gives a product
    #: exponent of 16 and 16 + 48 = 64 = ACC_EXP_MAX, the last accepted value.
    ceiling = code(2.0**31)
    add(
        "window_ceiling_w4",
        4,
        _row(generator, 4),
        _row(generator, 4),
        _row(generator, 4),
        [ceiling] * 4,
        [ceiling] * 4,
    )

    #: Exactly on the window floor: 2**-40 has integer significand 2**23 and
    #: exponent -63, so the product exponent is -126 = ACC_EXP_MIN, the smallest
    #: accepted value.
    floor_value = code(2.0**-40)
    add(
        "window_floor_w4",
        4,
        _row(generator, 4),
        _row(generator, 4),
        _row(generator, 4),
        [floor_value] * 4,
        [floor_value] * 4,
    )

    #: Reduction sums that leave binary32 finite range.  One product already
    #: exceeds the largest finite binary32, so with the default window these are
    #: window refusals and only the g3 window admits them far enough to reach the
    #: rounding sites.  The second case cancels the dot to EXACTLY zero -- which
    #: an exact reduction does and a rounded one would not -- while both squared
    #: norms still overflow, and that is what separates site 4 from site 5.
    huge = code(float((1 << 24) - 1) * 2.0**40)
    negative_huge = code(-float((1 << 24) - 1) * 2.0**40)
    add(
        "reduce_dot_overflow_w4",
        4,
        _row(generator, 4),
        _row(generator, 4),
        _row(generator, 4),
        [huge] * 4,
        [huge] * 4,
    )
    add(
        "reduce_norm_overflow_w4",
        4,
        _row(generator, 4),
        _row(generator, 4),
        _row(generator, 4),
        [huge, negative_huge, huge, negative_huge],
        [huge, huge, huge, huge],
    )

    #: Rows longer than the V4.1 Engram width.  g2 computes them; g0 and g1
    #: refuse them with ERR_SHAPE.  This pair is the no-frozen-geometry test.
    for width in (257, 272):
        add(
            f"wide_w{width}",
            width,
            _row(generator, width),
            _row(generator, width),
            _row(generator, width),
            _row(generator, width),
            _row(generator, width),
        )

    #: SUBNORMAL operands, in both phases.  A subnormal in q or k always refuses:
    #: its square has product exponent -298, far below the default window floor,
    #: whichever exponent form the decode uses.  A subnormal in key or value is
    #: ordinary arithmetic and must retire, because the combine phase goes
    #: through the qualified binary32 multiply and the reference through exact
    #: rationals, and both represent subnormals exactly.
    smallest = 0x00000001
    largest_subnormal = 0x007FFFFF
    add(
        "reduce_subnormal_q_w4",
        4,
        _row(generator, 4),
        _row(generator, 4),
        _row(generator, 4),
        [smallest] * 4,
        [code(2.0**46)] * 4,
    )
    add(
        "combine_subnormal_key_w4",
        4,
        _row(generator, 4),
        [smallest, largest_subnormal, smallest, largest_subnormal],
        [code(2.0**100)] * 4,
        _row(generator, 4),
        _row(generator, 4),
    )

    # ---- refusals, one per numbered site -------------------------------
    add("shape_zero", 0, [], [], [], [], [])

    for label, position, poison in (
        ("reduce_nan_q_at3", 3, NAN),
        ("reduce_inf_k_at0", 0, POSITIVE_INFINITY),
    ):
        query = _row(generator, 16)
        gate_key = _row(generator, 16)
        if label.endswith("q_at3"):
            query[position] = poison
        else:
            gate_key[position] = poison
        add(
            label,
            16,
            _row(generator, 16),
            _row(generator, 16),
            _row(generator, 16),
            query,
            gate_key,
        )

    #: One binary step below the floor: 2**-41 gives product exponent -128.
    under = code(2.0**-41)
    add(
        "reduce_window_under",
        4,
        _row(generator, 4),
        _row(generator, 4),
        _row(generator, 4),
        [under] * 4,
        [under] * 4,
    )
    #: A product whose magnitude leaves the window ceiling.
    over = code(2.0**40)
    add(
        "reduce_window_over",
        4,
        _row(generator, 4),
        _row(generator, 4),
        _row(generator, 4),
        [over] * 4,
        [over] * 4,
    )

    #: Combine-phase operand refusals at three different element indices, so the
    #: group-aligned written-word count differs between LANES 4 and LANES 8 at
    #: index 5 and agrees at index 0.
    for label, operand, position, poison in (
        ("combine_nan_h_at5", "h", 5, NAN),
        ("combine_inf_key_at9", "key", 9, NEGATIVE_INFINITY),
        ("combine_nan_value_at0", "value", 0, NAN),
    ):
        rows = {
            "h": _row(generator, 16),
            "key": _row(generator, 16),
            "value": _row(generator, 16),
        }
        rows[operand][position] = poison
        add(
            label,
            16,
            rows["h"],
            rows["key"],
            rows["value"],
            _row(generator, 16),
            _row(generator, 16),
        )

    #: key * value leaves binary32 range at element 6.
    key_row = _row(generator, 16)
    value_row = _row(generator, 16)
    key_row[6] = code(2.0**100)
    value_row[6] = code(2.0**100)
    add(
        "combine_product_range_at6",
        16,
        _row(generator, 16),
        key_row,
        value_row,
        _row(generator, 16),
        _row(generator, 16),
    )

    #: h + gate * key * value leaves binary32 range at element 2.
    hidden_row = _row(generator, 16)
    key_row = _row(generator, 16)
    value_row = _row(generator, 16)
    hidden_row[2] = code(3.4e38)
    key_row[2] = code(1.0e19)
    value_row[2] = code(1.0e19)
    add(
        "combine_sum_range_at2",
        16,
        hidden_row,
        key_row,
        value_row,
        _row(generator, 16),
        _row(generator, 16),
    )

    return cases


def _leg_aggregate(
    per_case: list[dict[str, Any]], case_count: int, geometry: dict[str, int]
) -> dict[str, int]:
    """Derive the counters one simulator leg must report for this geometry."""

    written = sum(item["written_words"] for item in per_case)
    retiring = sum(item["retires"] for item in per_case)
    scalar_checks = 15 * case_count
    output_word_checks = written
    sentinel_checks = case_count * VECTOR_LIMIT - written
    return {
        "geometry_width": geometry["vector_width"],
        "geometry_lanes": geometry["lanes"],
        "acc_exp_min": ENGRAM_GATE_DEFAULT_ACC_EXP_MIN,
        "acc_exp_max": geometry["acc_exp_max"],
        "cases": case_count,
        "retiring": retiring,
        "refused": case_count - retiring,
        "clamped": sum(item["clamped"] for item in per_case),
        "scalar_checks": scalar_checks,
        "output_word_checks": output_word_checks,
        "sentinel_checks": sentinel_checks,
        "elements_reduced": sum(item["reduced_words"] for item in per_case),
        "output_words_written": written,
        "write_beats": written,
        "illegal_write_checks": written,
        #: Five initiation-interval checks per RETIRING case: the issue count and
        #: the issue span of each streaming phase, and the span of the write port.
        "initiation_interval_checks": 5 * retiring,
        #: Four post-reset checks, then per case fifteen scalars, one idle check
        #: and one comparison of every word of the output region, and the
        #: initiation-interval checks of the retiring cases.
        "checks": 4 + case_count * (16 + VECTOR_LIMIT) + 5 * retiring,
    }


def region_bases(index: int) -> dict[str, int]:
    """Rotate the operand regions and offset them off every lane boundary.

    A base that is always a multiple of LANES would never test element-granular
    addressing, and a base that never moves would never test that the block
    reads its bases from the request.
    """

    names = ["h", "key", "value", "q", "k", "out"]
    rotation = index % REGION_COUNT
    ordered = names[rotation:] + names[:rotation]
    offset = 3 * (index % 5)
    return {
        name: slot * VECTOR_LIMIT + offset for slot, name in enumerate(ordered)
    }


def evaluate(case: dict[str, Any], geometry: dict[str, int]) -> dict[str, Any]:
    result = engram_gate(
        case["h"],
        case["key"],
        case["value"],
        case["q"],
        case["k"],
        max_width=geometry["vector_width"],
        combine_group=geometry["lanes"],
        acc_exp_max=geometry["acc_exp_max"],
    )
    return {
        "error_code": result.error_code,
        "refusal_stage": result.refusal_stage,
        "written_words": result.written_words,
        "reduced_words": result.reduced_words,
        "dot_code": result.dot_code,
        "norm_q_square_code": result.norm_q_square_code,
        "norm_k_square_code": result.norm_k_square_code,
        "norm_q_code": result.norm_q_code,
        "norm_k_code": result.norm_k_code,
        "denominator_raw_code": result.denominator_raw_code,
        "denominator_code": result.denominator_code,
        "cosine_code": result.cosine_code,
        "signed_sqrt_code": result.signed_sqrt_code,
        "gate_code": result.gate_code,
        "clamped": int(result.clamped),
        "retires": int(result.refusal_stage == REFUSAL_NONE),
        "output_codes": list(result.output_codes),
    }


def expectation_words(evaluated: dict[str, Any]) -> list[int]:
    scalars = [
        evaluated["error_code"],
        evaluated["refusal_stage"],
        evaluated["written_words"],
        evaluated["reduced_words"],
        evaluated["dot_code"],
        evaluated["norm_q_square_code"],
        evaluated["norm_k_square_code"],
        evaluated["norm_q_code"],
        evaluated["norm_k_code"],
        evaluated["denominator_raw_code"],
        evaluated["denominator_code"],
        evaluated["cosine_code"],
        evaluated["signed_sqrt_code"],
        evaluated["gate_code"],
        evaluated["clamped"],
        evaluated["retires"],
    ]
    if len(scalars) != EXPECT_SCALARS:  # pragma: no cover - structural invariant
        raise SystemExit("expectation scalar count drifted")
    row = list(evaluated["output_codes"])
    row += [SENTINEL] * (VECTOR_LIMIT - len(row))
    return scalars + row


def write_hex(path: Path, words: list[int]) -> None:
    path.write_text("".join(f"{word:08x}\n" for word in words))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output: Path = arguments.output
    output.mkdir(parents=True, exist_ok=True)

    cases = build_cases()
    for case in cases:
        if case["width"] > VECTOR_LIMIT:
            raise SystemExit(f"case {case['label']} exceeds the vector limit")

    request_words: list[int] = []
    input_words: list[int] = []
    for index, case in enumerate(cases):
        bases = region_bases(index)
        request_words += [
            case["width"],
            bases["h"],
            bases["key"],
            bases["value"],
            bases["q"],
            bases["k"],
            bases["out"],
            0,
        ]
        for operand in ("h", "key", "value", "q", "k"):
            row = list(case[operand])
            row += [0] * (VECTOR_LIMIT - len(row))
            input_words += row

    evaluated: dict[str, list[dict[str, Any]]] = {}
    expectations: dict[str, list[int]] = {}
    for geometry in GEOMETRIES:
        per_case = [evaluate(case, geometry) for case in cases]
        evaluated[geometry["name"]] = per_case
        words: list[int] = []
        for item in per_case:
            words += expectation_words(item)
        expectations[geometry["name"]] = words

    # The geometry-independence assertion, checked here so a regression is a
    # build failure and not a paragraph in a report.
    differing_fields: set[str] = set()
    for left, right in zip(evaluated["g0"], evaluated["g1"]):
        for field in left:
            if left[field] != right[field]:
                differing_fields.add(field)
        #: The two lane counts may write a different NUMBER of output words when
        #: a combine-phase refusal lands mid-group, but every word both of them
        #: write must be the same word: one row is a prefix of the other.
        shorter, longer = sorted(
            (left["output_codes"], right["output_codes"]), key=len
        )
        if tuple(longer[: len(shorter)]) != tuple(shorter):
            raise SystemExit("LANES changed an output code")
    if differing_fields - {"written_words", "output_codes"}:
        raise SystemExit(
            "LANES changed a computed result: "
            + ", ".join(sorted(differing_fields))
        )
    for index, (left, right) in enumerate(zip(evaluated["g0"], evaluated["g2"])):
        if cases[index]["width"] <= 256 and left != right:
            raise SystemExit(
                f"VECTOR_WIDTH changed case {cases[index]['label']}"
            )

    # No case may mix a nonfinite reduce operand with a window violation: the
    # two sites are reported by sticky flags whose relative priority is fixed,
    # and the reference reports whichever comes first in element order.
    for index, item in enumerate(evaluated["g0"]):
        stage = item["refusal_stage"]
        if stage in (2, 3):
            label = cases[index]["label"]
            if "window" in label and stage != 3:
                raise SystemExit(f"{label} expected a window refusal")
            if ("nan" in label or "inf" in label) and stage != 2:
                raise SystemExit(f"{label} expected an operand refusal")

    write_hex(output / "cases.hex", request_words)
    write_hex(output / "input.hex", input_words)
    for geometry in GEOMETRIES:
        write_hex(
            output / f"expect_{geometry['name']}.hex",
            expectations[geometry["name"]],
        )

    retiring = sum(item["retires"] for item in evaluated["g0"])
    clamping = sum(item["clamped"] for item in evaluated["g0"])
    meta = [
        MAGIC,
        VERSION,
        len(cases),
        VECTOR_LIMIT,
        CASE_WORDS,
        EXPECT_SCALARS,
        MEMORY_WORDS,
        SENTINEL,
    ]
    write_hex(output / "meta.hex", meta)

    index_record: dict[str, Any] = {
        "schema": "opentallas.rtl.a3_v41_engram_gate_vectors.v1",
        "numeric_contract": ENGRAM_GATE_NUMERIC_CONTRACT,
        "epsilon_binary32": f"0x{ENGRAM_GATE_EPSILON_BINARY32:08x}",
        "exactness_window": {
            "acc_exp_min": ENGRAM_GATE_DEFAULT_ACC_EXP_MIN,
            "acc_exp_max": ENGRAM_GATE_DEFAULT_ACC_EXP_MAX,
        },
        "magic": f"0x{MAGIC:08x}",
        "version": VERSION,
        "case_count": len(cases),
        "vector_limit": VECTOR_LIMIT,
        "case_words": CASE_WORDS,
        "expect_scalars": EXPECT_SCALARS,
        "memory_words": MEMORY_WORDS,
        "sentinel": f"0x{SENTINEL:08x}",
        "geometries": [dict(geometry) for geometry in GEOMETRIES],
        "geometry_independence": {
            "computed_codes_identical_across_lanes": True,
            "fields_permitted_to_differ": ["written_words", "output_codes"],
            "output_rows_are_prefixes_of_each_other": True,
            "observed_differing_fields": sorted(differing_fields),
        },
        "aggregate": {
            "retiring_cases": retiring,
            "refused_cases": len(cases) - retiring,
            "clamped_cases": clamping,
            "elements_reduced": sum(
                item["reduced_words"] for item in evaluated["g0"]
            ),
            "output_words_compared_per_geometry": len(cases) * VECTOR_LIMIT,
            "scalar_words_compared_per_geometry": len(cases) * EXPECT_SCALARS,
        },
        #: What each simulator leg must report.  Derived from the reference here
        #: so a case that silently stops being checked fails the campaign; a
        #: constant pinned in the runner would have to be edited instead.
        "per_geometry_aggregate": {
            geometry["name"]: _leg_aggregate(
                evaluated[geometry["name"]], len(cases), geometry
            )
            for geometry in GEOMETRIES
        },
        "refusal_sites_covered": sorted(
            {
                item["refusal_stage"]
                for geometry in GEOMETRIES
                for item in evaluated[geometry["name"]]
            }
        ),
        #: Sites 6 to 10 are STRUCTURALLY UNREACHABLE, not merely uncovered, and
        #: the bound that makes each unreachable is derived from the window
        #: parameters rather than assumed.  Recorded here so the campaign's claim
        #: boundary can state it instead of implying coverage.
        "refusal_sites_unreachable": {
            "6_norm_sqrt": (
                "the square root refuses only a nonfinite or negative argument; "
                "a squared-norm sum is a sum of squares and is neither"
            ),
            "7_denominator": (
                "both norms are at most sqrt(max accepted sum), so their product "
                "cannot leave binary32 range for any window with "
                "ACC_EXP_MAX + clog2(MAX_TERMS) <= 128"
            ),
            "8_divide": (
                "the denominator is clamped at 1e-6 and the numerator is a "
                "finite accepted sum, so the quotient stays finite"
            ),
            "9_signed_sqrt": (
                "the argument is the magnitude of a finite quotient"
            ),
            "10_sigmoid": (
                "Cauchy-Schwarz bounds the unclamped normalised dot by one and "
                "the clamp only shrinks it, so the sigmoid argument stays in a "
                "range the certifying engine rounds without widening"
            ),
        },
        "cases": [
            {
                "index": index,
                "label": case["label"],
                "width": case["width"],
                "bases": region_bases(index),
                "per_geometry": {
                    geometry["name"]: {
                        key: value
                        for key, value in evaluated[geometry["name"]][index].items()
                        if key != "output_codes"
                    }
                    for geometry in GEOMETRIES
                },
            }
            for index, case in enumerate(cases)
        ],
    }
    (output / "index.json").write_text(
        json.dumps(index_record, indent=2, sort_keys=True) + "\n"
    )
    print(
        f"a3_v41_engram_gate vectors: cases={len(cases)} "
        f"retiring={retiring} refused={len(cases) - retiring} "
        f"geometries={len(GEOMETRIES)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
