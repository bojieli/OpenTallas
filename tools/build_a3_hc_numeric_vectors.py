#!/usr/bin/env python3
"""Build independent exact vectors for the ABI 3.0 HC_PRE numeric RTL.

The oracle in this file is intentionally self-contained.  It decodes finite
binary32 values to ``fractions.Fraction`` objects and performs every required
round-to-nearest, ties-to-even boundary with integer arithmetic.  It imports no
OpenTallas arithmetic implementation and never uses host floating point.

Four Sinkhorn inputs are retained checkpoint-derived stable-softmax matrices
from the first four positions of the authentic ``TA-DS-CTX-200K-1`` PC-14
qualification.  The independent oracle must reproduce the corresponding first
four 4x4 matrices in the already-qualified full-shape output artifact.  The
remaining cases cover directed, random, exceptional, underflow, overflow and
backpressure-relevant values.  This tool builds vectors only; it makes no RTL,
model-token, EOS, timing or TPOT claim.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import struct
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "testdata/rtl/a3_hc_numeric"

EPSILON = 0x358637BD
MAX_FINITE = 0x7F7FFFFF
ERR_NONE = 0
ERR_ARGUMENT = 1
ERR_OVERFLOW = 2
DIVISION_RANDOM_SEED = 0xA3D1_5630
SINKHORN_RANDOM_SEED = 0xA3C2_0020

QUALIFICATION_RESULT = (
    ROOT / "results/abi3/deepseek_hbm_hc_pre_t512_functional_qualification.json"
)
QUALIFICATION_VECTOR = (
    ROOT / "testdata/runtime/deepseek_hbm_hc_pre_t512/qualification_vector.json"
)
QUALIFIED_COMBINATION = (
    ROOT
    / "testdata/runtime/deepseek_hbm_hc_pre_t512/expected_pc14_combination.u32le"
)

VECTOR_FILES = (
    "meta.hex",
    "division.hex",
    "sinkhorn_input.hex",
    "sinkhorn_expected.hex",
    "index.json",
)


# Extracted from the service-side stable_softmax_codes field for the first
# four authentic prompt positions.  The checkpoint/output binding below makes
# accidental or hand-edited drift observable without making the RTL depend on
# a checkpoint-specific lookup table.
CHECKPOINT_STABLE_INPUTS: tuple[tuple[int, ...], ...] = (
    (
        0x3F800008, 0x3586380C, 0x358637BD, 0x358637BD,
        0x35863854, 0x3F408ACA, 0x38AB5998, 0x3E7DC033,
        0x358637FB, 0x3E263DBE, 0x3F5670B1, 0x35906EC1,
        0x3F7E583F, 0x358637BD, 0x358637BD, 0x3BD3F1AC,
    ),
    (
        0x3F800008, 0x3586382C, 0x358637BD, 0x358637BD,
        0x35863869, 0x3F553BF1, 0x3921A24D, 0x3E2AE89F,
        0x35863853, 0x3E538810, 0x3F4B1E0E, 0x36007E8A,
        0x3F7E53FF, 0x358637BD, 0x358637BD, 0x3BD6118B,
    ),
    (
        0x3F800008, 0x35863813, 0x358637BD, 0x358637BD,
        0x35863877, 0x3F43B7F5, 0x391D9A93, 0x3E70F98D,
        0x35863951, 0x3E5C2BA6, 0x3F48F420, 0x3793D734,
        0x3F7CE018, 0x358637BD, 0x358637BD, 0x3C48027F,
    ),
    (
        0x3F800008, 0x358638C0, 0x358637BD, 0x358637BD,
        0x3586381C, 0x3F504A0E, 0x37DA4C5F, 0x3E3ED1C4,
        0x35863816, 0x3E1D7094, 0x3F58A3F9, 0x35A55C63,
        0x3F7EA8D6, 0x358637BD, 0x358637BD, 0x3BABA633,
    ),
)
CHECKPOINT_TOKEN_IDS = (18042, 41514, 6897, 33523)


class OracleError(ValueError):
    """A fail-closed binary32 operation could not produce a finite result."""

    def __init__(self, error: int, message: str) -> None:
        super().__init__(message)
        self.error = error


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pow2(exponent: int) -> Fraction:
    return Fraction(1 << exponent) if exponent >= 0 else Fraction(1, 1 << -exponent)


def decode_finite(code: int) -> Fraction:
    if not 0 <= code < 1 << 32:
        raise OracleError(ERR_ARGUMENT, "binary32 code is outside 32 bits")
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent == 0xFF:
        raise OracleError(ERR_ARGUMENT, "binary32 NaN/infinity is not arithmetic")
    if exponent == 0:
        value = Fraction(fraction) * pow2(-149)
    else:
        value = Fraction((1 << 23) | fraction) * pow2(exponent - 150)
    return -value if code & 0x80000000 else value


def round_integer(value: Fraction) -> int:
    if value < 0:
        raise ValueError("round_integer requires a nonnegative fraction")
    quotient, remainder = divmod(value.numerator, value.denominator)
    twice = remainder * 2
    if twice > value.denominator or (twice == value.denominator and quotient & 1):
        quotient += 1
    return quotient


def floor_log2(value: Fraction) -> int:
    if value <= 0:
        raise ValueError("floor_log2 requires a positive fraction")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < pow2(exponent):
        exponent -= 1
    return exponent


def encode_finite_rne(value: Fraction) -> int:
    """Encode an exact rational to finite binary32 or report overflow."""

    if value == 0:
        return 0
    sign = 0x80000000 if value < 0 else 0
    magnitude = abs(value)
    if magnitude < pow2(-126):
        significand = round_integer(magnitude / pow2(-149))
        if significand == 0:
            return 0
        if significand < 1 << 23:
            return sign | significand
        return sign | (1 << 23)

    exponent = floor_log2(magnitude)
    significand = round_integer(magnitude / pow2(exponent - 23))
    if significand == 1 << 24:
        significand = 1 << 23
        exponent += 1
    if exponent > 127:
        raise OracleError(ERR_OVERFLOW, "finite binary32 result overflow")
    if not (1 << 23) <= significand < (1 << 24):
        raise RuntimeError("normal binary32 significand invariant failed")
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def divide_oracle(numerator: int, denominator: int) -> tuple[int, int]:
    try:
        left = decode_finite(numerator)
        right = decode_finite(denominator)
        if right == 0:
            raise OracleError(ERR_ARGUMENT, "division denominator is zero")
        if left == 0:
            return 0, ERR_NONE
        return encode_finite_rne(left / right), ERR_NONE
    except OracleError as exc:
        return 0, exc.error


def positive_add(left: int, right: int) -> int:
    left_value = decode_finite(left)
    right_value = decode_finite(right)
    if left_value < 0 or right_value < 0:
        raise OracleError(ERR_ARGUMENT, "positive addition received a negative operand")
    return encode_finite_rne(left_value + right_value)


def balanced_sum4(values: Sequence[int]) -> int:
    if len(values) != 4:
        raise ValueError("balanced_sum4 requires exactly four values")
    return positive_add(
        positive_add(values[0], values[1]),
        positive_add(values[2], values[3]),
    )


def sinkhorn_oracle(
    raw_matrix: Sequence[int],
) -> tuple[tuple[int, ...], int, tuple[tuple[int, int], ...]]:
    """Execute the post-softmax 20-column/19-row Sinkhorn tail exactly."""

    if len(raw_matrix) != 16:
        raise ValueError("Sinkhorn matrix must contain exactly 16 values")
    matrix = [int(code) for code in raw_matrix]
    try:
        for code in matrix:
            value = decode_finite(code)
            if value <= 0:
                raise OracleError(ERR_ARGUMENT, "Sinkhorn input is not positive")

        divisions: list[tuple[int, int]] = []
        # Phase zero is a column; odd phases are rows and even phases columns.
        for phase in range(39):
            row_phase = bool(phase & 1)
            for group in range(4):
                indices = (
                    tuple(group * 4 + item for item in range(4))
                    if row_phase
                    else tuple(item * 4 + group for item in range(4))
                )
                denominator = positive_add(
                    balanced_sum4(tuple(matrix[index] for index in indices)),
                    EPSILON,
                )
                replacements: list[int] = []
                for index in indices:
                    numerator = matrix[index]
                    result, error = divide_oracle(numerator, denominator)
                    divisions.append((numerator, denominator))
                    if error != ERR_NONE:
                        raise OracleError(error, "Sinkhorn division failed")
                    replacements.append(result)
                for index, result in zip(indices, replacements, strict=True):
                    matrix[index] = result
        return tuple(matrix), ERR_NONE, tuple(divisions)
    except OracleError as exc:
        return (0,) * 16, exc.error, ()


def write_hex(path: Path, values: Iterable[int]) -> None:
    path.write_text("".join(f"{int(value) & 0xFFFFFFFF:08x}\n" for value in values))


def u32le(values: Iterable[int]) -> bytes:
    return b"".join(struct.pack("<I", int(value)) for value in values)


def matrix_hash(values: Sequence[int]) -> str:
    return sha256_bytes(u32le(values))


def random_finite_code(rng: random.Random, *, signed: bool) -> int:
    while True:
        magnitude = rng.randrange(MAX_FINITE + 1)
        if magnitude == 0 or ((magnitude >> 23) & 0xFF) == 0xFF:
            continue
        return magnitude | (rng.randrange(2) << 31 if signed else 0)


def directed_divisions() -> list[tuple[str, int, int]]:
    cases: list[tuple[str, int, int]] = [
        ("zero_over_one", 0x00000000, 0x3F800000),
        ("negative_zero_over_one", 0x80000000, 0x3F800000),
        ("one_over_one", 0x3F800000, 0x3F800000),
        ("negative_one_over_one", 0xBF800000, 0x3F800000),
        ("one_over_negative_one", 0x3F800000, 0xBF800000),
        ("negative_one_over_negative_one", 0xBF800000, 0xBF800000),
        ("one_over_three", 0x3F800000, 0x40400000),
        ("max_over_one", MAX_FINITE, 0x3F800000),
        ("max_minus_ulp_over_below_one", 0x7F7FFFFE, 0x3F7FFFFF),
        ("max_over_below_one_overflows", MAX_FINITE, 0x3F7FFFFF),
        ("max_over_half_overflows", MAX_FINITE, 0x3F000000),
        ("min_subnormal_over_one", 0x00000001, 0x3F800000),
        ("min_subnormal_underflow_tie_even", 0x00000001, 0x40000000),
        ("min_subnormal_above_half", 0x00000001, 0x3FFFFFFF),
        ("min_subnormal_below_half", 0x00000001, 0x40000001),
        ("three_subnormals_tie_odd_rounds_up", 0x00000003, 0x40000000),
        ("largest_subnormal_over_one", 0x007FFFFF, 0x3F800000),
        ("smallest_normal_over_one", 0x00800000, 0x3F800000),
        ("smallest_normal_over_max", 0x00800000, MAX_FINITE),
        ("max_over_min_subnormal", MAX_FINITE, 0x00000001),
        ("positive_infinity_numerator", 0x7F800000, 0x3F800000),
        ("negative_infinity_numerator", 0xFF800000, 0x3F800000),
        ("quiet_nan_numerator", 0x7FC00001, 0x3F800000),
        ("signaling_nan_numerator", 0x7F800001, 0x3F800000),
        ("positive_infinity_denominator", 0x3F800000, 0x7F800000),
        ("quiet_nan_denominator", 0x3F800000, 0x7FC00001),
        ("positive_zero_denominator", 0x3F800000, 0x00000000),
        ("negative_zero_denominator", 0x3F800000, 0x80000000),
        ("zero_over_zero", 0x00000000, 0x00000000),
    ]
    # Every exact halfway point in the subnormal interval is expressible as
    # an odd binary32 significand divided by two.  Alternate lower-candidate
    # parity to exercise both ties-to-even directions, including boundaries.
    for lower in (0, 1, 2, 3, 7, 8, 0x3FFFFE, 0x3FFFFF, 0x400000, 0x7FFFFE):
        numerator = 2 * lower + 1
        if numerator <= 0xFFFFFF:
            cases.append((f"subnormal_midpoint_lower_{lower:06x}", numerator, 0x40000000))
            cases.append((f"negative_subnormal_midpoint_lower_{lower:06x}", numerator | 0x80000000, 0x40000000))
    return cases


def directed_matrices() -> list[tuple[str, tuple[int, ...], str]]:
    one = 0x3F800000
    return [
        ("all_one", (one,) * 16, "directed"),
        ("all_epsilon", (EPSILON,) * 16, "directed"),
        ("all_min_subnormal", (1,) * 16, "directed"),
        ("all_max_finite_overflow", (MAX_FINITE,) * 16, "directed_overflow"),
        (
            "diagonal_dominant",
            tuple(one if row == column else EPSILON for row in range(4) for column in range(4)),
            "directed",
        ),
        (
            "exponent_ladder",
            tuple(0x28000000 + index * 0x00800000 for index in range(16)),
            "directed",
        ),
        (
            "mixed_extremes",
            tuple(MAX_FINITE if index == 0 else (1 if index & 1 else EPSILON) for index in range(16)),
            "directed",
        ),
        ("zero_input", (0,) + (one,) * 15, "invalid"),
        ("negative_zero_input", (0x80000000,) + (one,) * 15, "invalid"),
        ("negative_input", (0xBF800000,) + (one,) * 15, "invalid"),
        ("infinity_input", (0x7F800000,) + (one,) * 15, "invalid"),
        ("quiet_nan_input", (0x7FC00001,) + (one,) * 15, "invalid"),
        ("negative_nan_input", (0xFFC00001,) + (one,) * 15, "invalid"),
    ]


def build(output: Path) -> dict[str, object]:
    qualification = json.loads(QUALIFICATION_RESULT.read_text())
    qualification_vector = json.loads(QUALIFICATION_VECTOR.read_text())
    if qualification.get("status") != "pass":
        raise ValueError("source HC_PRE functional qualification is not passing")
    if qualification.get("claims", {}).get("model_token_generation") is not False:
        raise ValueError("source qualification claim boundary drift")
    if qualification_vector["first_issue_token_ids"][:4] != list(CHECKPOINT_TOKEN_IDS):
        raise ValueError("checkpoint-derived token identity drift")

    raw_combination = QUALIFIED_COMBINATION.read_bytes()
    if len(raw_combination) != 512 * 16 * 4:
        raise ValueError("qualified combination artifact has wrong extent")
    qualified_first_four = tuple(
        struct.unpack_from("<16I", raw_combination, token * 16 * 4)
        for token in range(4)
    )

    sinkhorn_cases: list[dict[str, object]] = []
    checkpoint_divisions: list[tuple[int, int]] = []

    for index, (token_id, matrix) in enumerate(
        zip(CHECKPOINT_TOKEN_IDS, CHECKPOINT_STABLE_INPUTS, strict=True)
    ):
        expected, error, divisions = sinkhorn_oracle(matrix)
        if error != ERR_NONE or expected != qualified_first_four[index]:
            raise ValueError(f"checkpoint Sinkhorn oracle mismatch at token {index}")
        checkpoint_divisions.extend(divisions)
        sinkhorn_cases.append(
            {
                "label": f"checkpoint_position_{index}_token_{token_id}",
                "category": "checkpoint_derived",
                "input": matrix,
                "expected": expected,
                "error": error,
                "division_count": len(divisions),
            }
        )

    for label, matrix, category in directed_matrices():
        expected, error, _ = sinkhorn_oracle(matrix)
        sinkhorn_cases.append(
            {
                "label": label,
                "category": category,
                "input": matrix,
                "expected": expected,
                "error": error,
                "division_count": 624 if error == ERR_NONE else 0,
            }
        )

    sink_rng = random.Random(SINKHORN_RANDOM_SEED)
    for index in range(48):
        matrix = tuple(
            ((sink_rng.randrange(72, 183) << 23) | sink_rng.randrange(1 << 23))
            for _ in range(16)
        )
        expected, error, _ = sinkhorn_oracle(matrix)
        sinkhorn_cases.append(
            {
                "label": f"moderate_random_{index:03d}",
                "category": "random_moderate",
                "input": matrix,
                "expected": expected,
                "error": error,
                "division_count": 624 if error == ERR_NONE else 0,
            }
        )
    for index in range(16):
        matrix = tuple(random_finite_code(sink_rng, signed=False) for _ in range(16))
        expected, error, _ = sinkhorn_oracle(matrix)
        sinkhorn_cases.append(
            {
                "label": f"wide_random_{index:03d}",
                "category": "random_wide",
                "input": matrix,
                "expected": expected,
                "error": error,
                "division_count": 624 if error == ERR_NONE else 0,
            }
        )

    division_cases: list[dict[str, object]] = []
    for label, numerator, denominator in directed_divisions():
        result, error = divide_oracle(numerator, denominator)
        division_cases.append(
            {
                "label": label,
                "category": "directed",
                "numerator": numerator,
                "denominator": denominator,
                "result": result,
                "error": error,
            }
        )
    for index, (numerator, denominator) in enumerate(checkpoint_divisions):
        result, error = divide_oracle(numerator, denominator)
        if error != ERR_NONE:
            raise ValueError("checkpoint-derived Sinkhorn division is exceptional")
        division_cases.append(
            {
                "label": f"checkpoint_sinkhorn_division_{index:04d}",
                "category": "checkpoint_derived",
                "numerator": numerator,
                "denominator": denominator,
                "result": result,
                "error": error,
            }
        )

    div_rng = random.Random(DIVISION_RANDOM_SEED)
    for index in range(4096):
        numerator = random_finite_code(div_rng, signed=True)
        denominator = random_finite_code(div_rng, signed=True)
        result, error = divide_oracle(numerator, denominator)
        division_cases.append(
            {
                "label": f"random_finite_{index:04d}",
                "category": "random_finite",
                "numerator": numerator,
                "denominator": denominator,
                "result": result,
                "error": error,
            }
        )

    output.mkdir(parents=True, exist_ok=True)
    meta_values = (
        0xA3C20020,
        1,
        len(division_cases),
        len(sinkhorn_cases),
        len(CHECKPOINT_STABLE_INPUTS),
        DIVISION_RANDOM_SEED,
        SINKHORN_RANDOM_SEED,
        EPSILON,
    )
    write_hex(output / "meta.hex", meta_values)
    write_hex(
        output / "division.hex",
        (
            word
            for case in division_cases
            for word in (
                case["numerator"],
                case["denominator"],
                case["result"],
                case["error"],
            )
        ),
    )
    write_hex(
        output / "sinkhorn_input.hex",
        (word for case in sinkhorn_cases for word in case["input"]),
    )
    write_hex(
        output / "sinkhorn_expected.hex",
        (
            word
            for case in sinkhorn_cases
            for word in (*case["expected"], case["error"])
        ),
    )

    division_categories = Counter(str(case["category"]) for case in division_cases)
    division_errors = Counter(int(case["error"]) for case in division_cases)
    sinkhorn_categories = Counter(str(case["category"]) for case in sinkhorn_cases)
    sinkhorn_errors = Counter(int(case["error"]) for case in sinkhorn_cases)
    manifest_without_digest: dict[str, object] = {
        "schema": "opentallas.rtl.a3_hc_numeric_vectors.v1",
        "oracle": {
            "method": "exact Fraction decode, rational arithmetic, integer RNE encode",
            "host_floating_point": False,
            "imports_opentallas_arithmetic": False,
            "division_contract": "finite signed binary32 RNE; canonical positive zero; fail-closed nonfinite/zero-divisor/overflow",
            "sinkhorn_contract": "source-major 4x4; initial column then 19 row/column pairs; balanced four-term positive sums; epsilon 0x358637bd",
        },
        "seeds": {
            "division": DIVISION_RANDOM_SEED,
            "sinkhorn": SINKHORN_RANDOM_SEED,
        },
        "counts": {
            "division_cases": len(division_cases),
            "division_categories": dict(sorted(division_categories.items())),
            "division_errors": {str(key): value for key, value in sorted(division_errors.items())},
            "sinkhorn_cases": len(sinkhorn_cases),
            "sinkhorn_categories": dict(sorted(sinkhorn_categories.items())),
            "sinkhorn_errors": {str(key): value for key, value in sorted(sinkhorn_errors.items())},
            "checkpoint_sinkhorn_divisions": len(checkpoint_divisions),
            "successful_sinkhorn_divisions_per_case": 624,
        },
        "checkpoint_binding": {
            "workload_id": "TA-DS-CTX-200K-1",
            "prompt_token_count": 200000,
            "positions": list(range(4)),
            "token_ids": list(CHECKPOINT_TOKEN_IDS),
            "stable_input_u32le_sha256": matrix_hash(
                tuple(word for matrix in CHECKPOINT_STABLE_INPUTS for word in matrix)
            ),
            "independent_output_u32le_sha256": matrix_hash(
                tuple(word for matrix in qualified_first_four for word in matrix)
            ),
            "qualified_output_prefix_u32le_sha256": sha256_bytes(raw_combination[: 4 * 16 * 4]),
            "qualification_result": str(QUALIFICATION_RESULT.relative_to(ROOT)),
            "qualification_result_sha256": sha256_file(QUALIFICATION_RESULT),
            "qualification_vector": str(QUALIFICATION_VECTOR.relative_to(ROOT)),
            "qualification_vector_sha256": sha256_file(QUALIFICATION_VECTOR),
            "qualified_combination": str(QUALIFIED_COMBINATION.relative_to(ROOT)),
            "qualified_combination_sha256": sha256_file(QUALIFIED_COMBINATION),
            "all_four_outputs_match_qualified_prefix": True,
        },
        "sinkhorn_cases": [
            {
                "index": index,
                "label": case["label"],
                "category": case["category"],
                "input_u32le_sha256": matrix_hash(case["input"]),
                "expected_u32le_sha256": matrix_hash(case["expected"]),
                "error": case["error"],
                "division_count": case["division_count"],
            }
            for index, case in enumerate(sinkhorn_cases)
        ],
        "division_sentinels": [
            {
                "index": index,
                "label": case["label"],
                "numerator": f"{int(case['numerator']):08x}",
                "denominator": f"{int(case['denominator']):08x}",
                "result": f"{int(case['result']):08x}",
                "error": case["error"],
            }
            for index, case in enumerate(division_cases[: len(directed_divisions())])
        ],
        "claim_boundary": {
            "vectors_only": True,
            "full_hc_pre": False,
            "stable_softmax_front_end": False,
            "exponential": False,
            "sigmoid": False,
            "model_token_generation": False,
            "eos": False,
            "architectural_timing": False,
            "tpot": False,
        },
    }
    manifest = dict(manifest_without_digest)
    manifest["manifest_sha256"] = sha256_bytes(canonical(manifest_without_digest))
    (output / "index.json").write_bytes(canonical(manifest) + b"\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    print(
        "PASS HC numeric vectors: "
        f"{manifest['counts']['division_cases']} divisions, "
        f"{manifest['counts']['sinkhorn_cases']} Sinkhorn matrices"
    )


if __name__ == "__main__":
    main()
