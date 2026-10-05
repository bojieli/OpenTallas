#!/usr/bin/env python3
"""Build exact vectors for the V4.1 FP4 main-KV dequantize RTL block.

Every expected word comes from ``runtime/reference/fp4_kv.py``, an independent
exact-rational oracle for ``fp4_e2m1_s16_e4m3_to_fp8_v1``.  Nothing here is
transcribed from ``rtl/abi3/ot_a3_vector_fp4kv_dequant.sv``.

The case list is built to make three claims checkable rather than asserted:

* **exhaustive numerics** -- cases ``exhaustive_low`` and ``exhaustive_high``
  together cover ALL 16 E2M1 codes against ALL 254 finite E4M3FN scale codes,
  which is the complete input space of one element of this contract;
* **no frozen geometry** -- extents 8 .. 2048, scale groups 8, 12, 16, 20, 32,
  64 and 512 (including groups that are not powers of two and a group equal to
  the whole extent), the group taken from the operand field and from the
  parameter default, and a shape whose legality DIFFERS between lane counts;
* **fail-closed atomicity** -- poisoned (NaN) scales inside the extent refuse
  with an untouched destination, while a NaN scale byte OUTSIDE the extent is
  correctly ignored.

This builder does not execute RTL, produce a model token or establish timing.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.fp4_kv import (  # noqa: E402
    CONTRACT,
    DEFAULT_SCALE_GROUP,
    V41_LATENT_ELEMENTS,
    dequantize_to_fp8,
    finite_scale_codes,
    quantize_to_fp4,
    scale_code_is_nonfinite,
)

OUTPUT_ROOT = ROOT / "testdata/rtl/a3_v41_fp4kv"
VECTOR_FILES = (
    "meta.hex",
    "cases.hex",
    "code.hex",
    "scale.hex",
    "pass.hex",
    "expected.hex",
    "index.json",
)

#: Mirrors the elaboration defaults of ot_a3_vector_fp4kv_dequant.  The
#: testbench instantiates the same three lane counts.
RTL_MAX_ELEMENTS = 2048
RTL_SCALE_GROUP_DEFAULT = DEFAULT_SCALE_GROUP
LANE_SET = (1, 4, 8)
WORD_BITS = 32
CODE_BITS = 4
SCALE_BITS = 8
RESULT_BITS = 8
CODES_PER_WORD = WORD_BITS // CODE_BITS
SCALES_PER_WORD = WORD_BITS // SCALE_BITS
RESULTS_PER_WORD = WORD_BITS // RESULT_BITS

ERR_NONE = 0
ERR_OPERAND_NONFINITE = 1
ERR_SHAPE = 7

META_MAGIC = 0xA341F4D0
META_VERSION = 1
META_WORDS = 12
CASE_WORDS = 16
REGION_ALIGN = 8
SENTINEL = 0xDEADBEEF

RANDOM_SEED = 0xA3_41_0F_04


class VectorError(RuntimeError):
    """Raised when a requested case is internally inconsistent."""


def codes_per_port(lanes: int) -> int:
    """E2M1 codes delivered by one code-operand port read at ``lanes``."""

    return max(WORD_BITS, lanes * CODE_BITS) // CODE_BITS


def results_per_port(lanes: int) -> int:
    """FP8 elements carried by one result/passthrough port beat at ``lanes``."""

    return max(WORD_BITS, lanes * RESULT_BITS) // RESULT_BITS


def shape_error(
    *, count: int, group_field: int, passthrough: int, lanes: int
) -> int:
    """The error a legal-shape predicate must report, per lane count.

    This mirrors, in one place, the predicate documented in the RTL header:
    every bound is derived from a parameter (``lanes``, ``MAX_ELEMENTS``, the
    word and format widths) or from an operand field (``group_field``), and no
    model dimension appears.  It is a *prediction* compared against the RTL by
    the campaign, which is the point of having it.
    """

    group = group_field if group_field else RTL_SCALE_GROUP_DEFAULT
    dequantized = count - passthrough
    if count == 0 or count > RTL_MAX_ELEMENTS:
        return ERR_SHAPE
    if passthrough > count:
        return ERR_SHAPE
    if group_field > RTL_MAX_ELEMENTS:
        return ERR_SHAPE
    if group == 0 or group % lanes:
        return ERR_SHAPE
    if dequantized % codes_per_port(lanes):
        return ERR_SHAPE
    if passthrough % results_per_port(lanes):
        return ERR_SHAPE
    if count % results_per_port(lanes):
        return ERR_SHAPE
    return ERR_NONE


def pack(values: list[int], per_word: int, bits: int) -> list[int]:
    """Pack elements low-element-first into 32-bit words."""

    if len(values) % per_word:
        raise VectorError("packed region is not a whole number of words")
    words: list[int] = []
    for start in range(0, len(values), per_word):
        word = 0
        for offset, value in enumerate(values[start : start + per_word]):
            if value < 0 or value >= 1 << bits:
                raise VectorError(f"element {value} does not fit {bits} bits")
            word |= value << (bits * offset)
        words.append(word)
    return words


def align(position: int) -> int:
    return ((position + REGION_ALIGN - 1) // REGION_ALIGN) * REGION_ALIGN


def latent_values(count: int, seed: int) -> list[Fraction]:
    """A deterministic pseudo-random post-RoPE latent, as exact rationals."""

    rng = random.Random(seed)
    values: list[Fraction] = []
    for index in range(count):
        # A spread of magnitudes across seven binades, plus exact zeros and a
        # few near-tie values, so the quantizer emits a realistic scale mix.
        if index % 37 == 0:
            values.append(Fraction(0))
            continue
        exponent = rng.randint(-6, 3)
        mantissa = Fraction(rng.randint(1, 255), 128)
        sign = -1 if rng.random() < 0.5 else 1
        values.append(sign * mantissa * Fraction(2) ** exponent)
    return values


def exhaustive_case(scale_codes: tuple[int, ...]) -> tuple[list[int], list[int]]:
    """One group of all 16 E2M1 codes per supplied scale, in code order."""

    codes: list[int] = []
    for _ in scale_codes:
        codes.extend(range(16))
    return codes, list(scale_codes)


def build_cases() -> list[dict[str, Any]]:
    finite = finite_scale_codes()
    if len(finite) != 254:
        raise VectorError("E4M3FN must have exactly 254 finite codes")
    low, high = finite[:127], finite[127:]

    cases: list[dict[str, Any]] = []

    def add(
        name: str,
        *,
        count: int,
        group_field: int,
        codes: list[int],
        scales: list[int],
        passthrough: list[int] | None = None,
        note: str,
        poison: bool = False,
    ) -> None:
        cases.append(
            {
                "name": name,
                "count": count,
                "group_field": group_field,
                "codes": codes,
                "scales": scales,
                "passthrough": list(passthrough or []),
                "note": note,
                "declared_poison": poison,
            }
        )

    exhaustive_low_codes, exhaustive_low_scales = exhaustive_case(low)
    add(
        "exhaustive_low",
        count=len(exhaustive_low_codes),
        group_field=16,
        codes=exhaustive_low_codes,
        scales=exhaustive_low_scales,
        note="all 16 E2M1 codes against finite E4M3FN scales 0x00..0x7e",
    )
    exhaustive_high_codes, exhaustive_high_scales = exhaustive_case(high)
    add(
        "exhaustive_high",
        count=len(exhaustive_high_codes),
        group_field=16,
        codes=exhaustive_high_codes,
        scales=exhaustive_high_scales,
        note="all 16 E2M1 codes against finite E4M3FN scales 0x80..0xfe",
    )

    quantized = quantize_to_fp4(
        latent_values(V41_LATENT_ELEMENTS, RANDOM_SEED), group=DEFAULT_SCALE_GROUP
    )
    add(
        "v41_latent_group16",
        count=V41_LATENT_ELEMENTS,
        group_field=16,
        codes=list(quantized.e2m1_codes),
        scales=list(quantized.e4m3_scale_codes),
        note="the V4.1 main-latent shape: 512 elements, one E4M3 scale per 16",
    )
    add(
        "v41_latent_group_from_default",
        count=V41_LATENT_ELEMENTS,
        group_field=0,
        codes=list(quantized.e2m1_codes),
        scales=list(quantized.e4m3_scale_codes),
        note="identical request with the group taken from the parameter default",
    )

    for group in (8, 32, 64, 512):
        variant = quantize_to_fp4(
            latent_values(V41_LATENT_ELEMENTS, RANDOM_SEED + group), group=group
        )
        add(
            f"group_{group}",
            count=V41_LATENT_ELEMENTS,
            group_field=group,
            codes=list(variant.e2m1_codes),
            scales=list(variant.e4m3_scale_codes),
            note=f"same extent with a {group}-element scale group",
        )

    for group, count in ((12, 48), (20, 80)):
        variant = quantize_to_fp4(
            latent_values(count, RANDOM_SEED + 100 + group), group=group
        )
        add(
            f"group_{group}_not_power_of_two",
            count=count,
            group_field=group,
            codes=list(variant.e2m1_codes),
            scales=list(variant.e4m3_scale_codes),
            note=(
                f"group {group} is not a power of two: legal wherever "
                f"{group} % LANES == 0 and refused elsewhere"
            ),
        )

    for count in (8, 64, RTL_MAX_ELEMENTS):
        variant = quantize_to_fp4(
            latent_values(count, RANDOM_SEED + 200 + count),
            group=8 if count == 8 else 16,
        )
        add(
            f"extent_{count}",
            count=count,
            group_field=8 if count == 8 else 16,
            codes=list(variant.e2m1_codes),
            scales=list(variant.e4m3_scale_codes),
            note=f"extent {count}, the smallest and largest admitted here",
        )

    add(
        "saturating_scales",
        count=32,
        group_field=16,
        codes=list(range(16)) * 2,
        scales=[0x7E, 0x7D],
        note="scale 448 drives products past the finite FP8 range: saturation",
    )
    add(
        "negative_scales",
        count=32,
        group_field=16,
        codes=list(range(16)) * 2,
        scales=[0xBC, 0xFE],
        note="a signed scale: the result sign is the XOR of both operand signs",
    )
    add(
        "zero_scale",
        count=16,
        group_field=16,
        codes=list(range(16)),
        scales=[0x00],
        note="a zero scale yields canonical positive zero for every element",
    )
    add(
        "subnormal_scales",
        count=64,
        group_field=16,
        codes=list(range(16)) * 4,
        scales=[0x01, 0x02, 0x03, 0x07],
        note="subnormal E4M3FN scales exercise the ties-to-even underflow edge",
    )
    add(
        "smallest_scales_tie_to_zero",
        count=16,
        group_field=16,
        codes=[1, 1, 1, 1, 3, 3, 3, 3, 2, 2, 2, 2, 5, 5, 5, 5],
        scales=[0x01],
        note="products at exactly half the smallest FP8 subnormal: tie to even",
    )

    passthrough_quantized = quantize_to_fp4(
        latent_values(448, RANDOM_SEED + 300), group=16
    )
    add(
        "passthrough_trailing_64",
        count=512,
        group_field=16,
        codes=list(passthrough_quantized.e2m1_codes),
        scales=list(passthrough_quantized.e4m3_scale_codes),
        passthrough=[(index * 7 + 3) & 0xFF for index in range(64)],
        note=(
            "the IR's third DEQUANTIZE operand: 64 trailing FP8 elements copied "
            "verbatim, as the vendor's partial QDQ leaves unquantized channels"
        ),
    )
    add(
        "passthrough_only",
        count=64,
        group_field=16,
        codes=[],
        scales=[],
        passthrough=[(index * 13 + 1) & 0xFF for index in range(64)],
        note="a pure passthrough needs no scale operand at all",
    )
    add(
        "passthrough_keeps_nan_bytes",
        count=32,
        group_field=16,
        codes=[],
        scales=[],
        passthrough=[0x7F, 0xFF] * 16,
        note=(
            "a passthrough element is a byte copy, NaN payload included: the "
            "block must not interpret operand three"
        ),
    )

    # ---- fail-closed poison ------------------------------------------------
    poison_variant = quantize_to_fp4(latent_values(64, RANDOM_SEED + 400), group=16)
    poison_scales = list(poison_variant.e4m3_scale_codes)
    poison_scales[2] = 0x7F
    add(
        "poison_scale_inside_extent",
        count=64,
        group_field=16,
        codes=list(poison_variant.e2m1_codes),
        scales=poison_scales,
        note="a NaN scale inside the extent refuses with an untouched destination",
        poison=True,
    )
    poison_negative = list(poison_variant.e4m3_scale_codes)
    poison_negative[1] = 0xFF
    add(
        "poison_scale_negative_nan",
        count=64,
        group_field=16,
        codes=list(poison_variant.e2m1_codes),
        scales=poison_negative,
        note="the second E4M3FN NaN encoding poisons its group as well",
        poison=True,
    )
    outside = quantize_to_fp4(latent_values(32, RANDOM_SEED + 500), group=16)
    add(
        "nan_scale_outside_extent_is_ignored",
        count=32,
        group_field=16,
        codes=list(outside.e2m1_codes),
        scales=[*outside.e4m3_scale_codes, 0x7F, 0xFF],
        note=(
            "the scale operand's last word carries NaN bytes beyond the two "
            "groups this extent uses; they must not refuse the request"
        ),
    )

    # ---- refusals ----------------------------------------------------------
    refusal_source = quantize_to_fp4(latent_values(64, RANDOM_SEED + 600), group=16)
    add(
        "refuse_zero_extent",
        count=0,
        group_field=16,
        codes=list(refusal_source.e2m1_codes),
        scales=list(refusal_source.e4m3_scale_codes),
        note="an empty request is a shape error, not a silent no-op",
    )
    add(
        "refuse_over_capacity",
        count=RTL_MAX_ELEMENTS + 8,
        group_field=16,
        codes=list(refusal_source.e2m1_codes),
        scales=list(refusal_source.e4m3_scale_codes),
        note="past MAX_ELEMENTS: a capacity bound, not a model dimension",
    )
    add(
        "refuse_partial_group",
        count=24,
        group_field=16,
        codes=list(refusal_source.e2m1_codes[:24]),
        scales=list(refusal_source.e4m3_scale_codes[:2]),
        note=(
            "24 elements is not a whole number of 16-element groups; the scan "
            "accumulator witnesses it without a divider"
        ),
    )
    add(
        "refuse_group_larger_than_extent",
        count=16,
        group_field=32,
        codes=list(refusal_source.e2m1_codes[:16]),
        scales=list(refusal_source.e4m3_scale_codes[:1]),
        note="a group wider than the extent has no complete scale",
    )
    add(
        "refuse_unaligned_extent",
        count=18,
        group_field=16,
        codes=list(refusal_source.e2m1_codes[:16]),
        scales=list(refusal_source.e4m3_scale_codes[:1]),
        note="an extent that is not a whole number of result words",
    )
    add(
        "refuse_unaligned_passthrough",
        count=32,
        group_field=16,
        codes=list(refusal_source.e2m1_codes[:30]),
        scales=list(refusal_source.e4m3_scale_codes[:2]),
        passthrough=[0x11, 0x22],
        note="a passthrough region that is not a whole number of port beats",
    )
    add(
        "refuse_zero_group_field_is_impossible",
        count=32,
        group_field=RTL_MAX_ELEMENTS + 16,
        codes=list(refusal_source.e2m1_codes[:32]),
        scales=list(refusal_source.e4m3_scale_codes[:2]),
        note="a group field past the extent bound is refused, never truncated",
    )
    return cases


def expected_for(case: dict[str, Any]) -> dict[str, Any]:
    """Reference outputs for one case, or the reason there are none."""

    count = int(case["count"])
    group_field = int(case["group_field"])
    group = group_field if group_field else RTL_SCALE_GROUP_DEFAULT
    passthrough = list(case["passthrough"])
    dequantized = count - len(passthrough)
    errors = {
        lanes: shape_error(
            count=count,
            group_field=group_field,
            passthrough=len(passthrough),
            lanes=lanes,
        )
        for lanes in LANE_SET
    }
    used_scales = 0
    poisoned = False
    if dequantized > 0 and dequantized % group == 0:
        used_scales = dequantized // group
        poisoned = any(
            scale_code_is_nonfinite(code)
            for code in case["scales"][:used_scales]
        )
    for lanes in LANE_SET:
        if errors[lanes] != ERR_NONE:
            continue
        if poisoned:
            errors[lanes] = ERR_OPERAND_NONFINITE
        elif dequantized > 0 and dequantized % group:
            errors[lanes] = ERR_SHAPE

    if any(error == ERR_NONE for error in errors.values()):
        result = dequantize_to_fp8(
            case["codes"][:dequantized],
            case["scales"][:used_scales],
            group=group,
            passthrough=passthrough,
        )
        if len(result.fp8_codes) != count:
            raise VectorError(f"{case['name']}: oracle produced {len(result.fp8_codes)}")
        words = pack(list(result.fp8_codes), RESULTS_PER_WORD, RESULT_BITS)
        saturation = result.saturation_count
    else:
        words = []
        saturation = 0
    return {
        "errors": errors,
        "words": words,
        "saturation": saturation,
        "dequantized": dequantized,
        "group": group,
        "used_scales": used_scales,
        "poisoned": poisoned,
    }


def build(output: Path) -> dict[str, Any]:
    cases = build_cases()
    code_memory: list[int] = []
    scale_memory: list[int] = []
    pass_memory: list[int] = []
    expected_memory: list[int] = []
    out_words_total = 0
    records: list[dict[str, Any]] = []
    case_rows: list[list[int]] = []

    for case in cases:
        derived = expected_for(case)
        codes = list(case["codes"][: derived["dequantized"]])
        if len(codes) % CODES_PER_WORD:
            codes = codes + [0] * (CODES_PER_WORD - len(codes) % CODES_PER_WORD)
        scales = list(case["scales"])
        if not scales:
            scales = [0]
        while len(scales) % SCALES_PER_WORD:
            scales.append(0)
        passthrough = list(case["passthrough"])
        if not passthrough:
            passthrough = [0] * RESULTS_PER_WORD
        while len(passthrough) % RESULTS_PER_WORD:
            passthrough.append(0)

        code_base = align(len(code_memory))
        code_memory.extend([0] * (code_base - len(code_memory)))
        code_memory.extend(pack(codes, CODES_PER_WORD, CODE_BITS))
        scale_base = align(len(scale_memory))
        scale_memory.extend([0] * (scale_base - len(scale_memory)))
        scale_memory.extend(pack(scales, SCALES_PER_WORD, SCALE_BITS))
        pass_base = align(len(pass_memory))
        pass_memory.extend([0] * (pass_base - len(pass_memory)))
        pass_memory.extend(pack(passthrough, RESULTS_PER_WORD, RESULT_BITS))

        out_base = align(out_words_total)
        out_words = len(derived["words"])
        # Every case keeps at least REGION_ALIGN guard words after its
        # region so the testbench can prove a refusal -- and an over-run --
        # left the destination untouched.
        out_words_total = out_base + max(out_words, REGION_ALIGN) + REGION_ALIGN
        expected_offset = len(expected_memory)
        expected_memory.extend(derived["words"])

        errors = derived["errors"]
        row = [
            int(case["count"]),
            int(case["group_field"]),
            len(case["passthrough"]),
            code_base,
            scale_base,
            pass_base,
            out_base,
            expected_offset,
            out_words,
            derived["saturation"],
            errors[LANE_SET[0]],
            errors[LANE_SET[1]],
            errors[LANE_SET[2]],
            int(case["count"]) // LANE_SET[0] if errors[LANE_SET[0]] == ERR_NONE else 0,
            int(case["count"]) // LANE_SET[1] if errors[LANE_SET[1]] == ERR_NONE else 0,
            int(case["count"]) // LANE_SET[2] if errors[LANE_SET[2]] == ERR_NONE else 0,
        ]
        if len(row) != CASE_WORDS:
            raise VectorError("case descriptor width changed")
        case_rows.append(row)
        records.append(
            {
                "name": case["name"],
                "note": case["note"],
                "count": int(case["count"]),
                "group_field": int(case["group_field"]),
                "effective_group": derived["group"],
                "passthrough": len(case["passthrough"]),
                "dequantized_elements": derived["dequantized"],
                "scales_used": derived["used_scales"],
                "expected_output_words": out_words,
                "expected_saturations": derived["saturation"],
                "expected_error": {str(k): v for k, v in errors.items()},
                "expected_issue_beats": {
                    str(lanes): (
                        int(case["count"]) // lanes
                        if errors[lanes] == ERR_NONE
                        else 0
                    )
                    for lanes in LANE_SET
                },
                "poisoned_scale_in_extent": derived["poisoned"],
                "code_base": code_base,
                "scale_base": scale_base,
                "pass_base": pass_base,
                "out_base": out_base,
            }
        )

    # Element-level check budget, per simulator and per lane count.
    element_checks = {
        str(lanes): sum(
            record["count"]
            for record in records
            if record["expected_error"][str(lanes)] == ERR_NONE
        )
        for lanes in LANE_SET
    }
    word_checks = {
        str(lanes): sum(
            record["expected_output_words"]
            for record in records
            if record["expected_error"][str(lanes)] == ERR_NONE
        )
        for lanes in LANE_SET
    }
    exhaustive = sum(
        record["count"]
        for record in records
        if record["name"].startswith("exhaustive_")
    )

    meta = [
        META_MAGIC,
        META_VERSION,
        len(cases),
        CASE_WORDS,
        len(code_memory),
        len(scale_memory),
        len(pass_memory),
        len(expected_memory),
        out_words_total,
        RTL_MAX_ELEMENTS,
        RTL_SCALE_GROUP_DEFAULT,
        SENTINEL,
    ]
    if len(meta) != META_WORDS:
        raise VectorError("meta width changed")

    manifest = {
        "schema": "opentallas.rtl.a3_v41_fp4kv_vectors.v1",
        "contract": CONTRACT,
        "reference": "runtime/reference/fp4_kv.py",
        "source": "SRC-DSV41-FLASH-MODEL",
        "rtl_parameters": {
            "MAX_ELEMENTS": RTL_MAX_ELEMENTS,
            "SCALE_GROUP_DEFAULT": RTL_SCALE_GROUP_DEFAULT,
            "lane_counts_instantiated": list(LANE_SET),
        },
        "memory": {
            "code_words": len(code_memory),
            "scale_words": len(scale_memory),
            "pass_words": len(pass_memory),
            "expected_words": len(expected_memory),
            "out_words": out_words_total,
            "sentinel": SENTINEL,
        },
        "coverage": {
            "e2m1_codes_covered": 16,
            "finite_e4m3fn_scale_codes_covered": 254,
            "exhaustive_pair_elements": exhaustive,
            "distinct_scale_groups_admitted": sorted(
                {
                    record["effective_group"]
                    for record in records
                    if ERR_NONE in record["expected_error"].values()
                }
            ),
            "extents_requested": sorted({record["count"] for record in records}),
            "extents_admitted": sorted(
                {
                    record["count"]
                    for record in records
                    if ERR_NONE in record["expected_error"].values()
                }
            ),
            "element_checks_per_lane_count": element_checks,
            "output_word_checks_per_lane_count": word_checks,
        },
        "claim_boundary": {
            "establishes_e2m1_e4m3_to_fp8_bit_exactness": True,
            "establishes_vendor_forward_quantizer_scale_rule": False,
            "establishes_frequency_or_area": False,
            "establishes_token_correctness_or_tpot": False,
            "executes_the_shipped_engine_array_or_a_descriptor": False,
            "implements_dequantize_operand_slot_three_passthrough": True,
            "reads_the_pinned_vendor_model_py": False,
        },
        "cases": records,
        "expected_pass": {
            "cases": len(cases),
            "lane_counts": len(LANE_SET),
            "element_checks": sum(element_checks.values()),
            "word_checks": sum(word_checks.values()),
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    write_hex(output / "meta.hex", meta)
    write_hex(output / "cases.hex", [word for row in case_rows for word in row])
    write_hex(output / "code.hex", code_memory)
    write_hex(output / "scale.hex", scale_memory)
    write_hex(output / "pass.hex", pass_memory)
    write_hex(output / "expected.hex", expected_memory)
    (output / "index.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def write_hex(path: Path, words: list[int]) -> None:
    if not words:
        words = [0]
    path.write_text("".join(f"{word & 0xFFFFFFFF:08x}\n" for word in words))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    return result


def main() -> int:
    args = parser().parse_args()
    manifest = build(args.output)
    digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True).encode()
    ).hexdigest()
    print(
        f"a3_v41_fp4kv vectors cases={manifest['expected_pass']['cases']} "
        f"element_checks={manifest['expected_pass']['element_checks']} "
        f"exhaustive={manifest['coverage']['exhaustive_pair_elements']} "
        f"manifest_sha256={digest[:16]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
