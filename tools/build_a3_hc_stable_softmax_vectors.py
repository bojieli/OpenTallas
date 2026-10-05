#!/usr/bin/env python3
"""Build independent exact vectors for the HC stable-softmax RTL.

The retained checkpoint binary contains only source-major 4x4 combination
logits.  This tool computes expected results with exact rational binary32
decode/arithmetic/RNE and the independent exact-interval exponential reference;
it imports neither the service arithmetic lane nor any RTL implementation.

The corpus covers every matrix from the first and final prefill blocks of the
governed 200,000-token workload, a one-token shape witness, directed ordering
and underflow boundaries, and fail-closed exceptional inputs.  These vectors
are arithmetic dependency evidence, not generated model tokens or TPOT.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.hyper_connection import (  # noqa: E402
    HCPreReferenceError,
    binary32_exp_rne,
)
from tools import build_a3_hc_numeric_vectors as numeric_vectors  # noqa: E402


DEFAULT_CHECKPOINT = ROOT / "testdata/rtl/a3_hc_stable_softmax"
DEFAULT_OUTPUT = DEFAULT_CHECKPOINT
CHECKPOINT_MANIFEST = "checkpoint_logits.json"
CHECKPOINT_BINARY = "checkpoint_logits.u32le"
VECTOR_FILES = ("meta.hex", "matrix_input.hex", "matrix_expected.hex", "index.json")

SCHEMA = "opentallas.rtl.a3_hc_stable_softmax_vectors.v1"
MAGIC = 0xA3C5_0F7A
EPSILON = 0x358637BD
MAX_FINITE = 0x7F7FFFFF
ERR_NONE = 0
ERR_ARGUMENT = 1
ERR_OVERFLOW = 2


class OracleError(ValueError):
    """One fail-closed arithmetic operation could not produce a finite code."""

    def __init__(self, error: int, message: str) -> None:
        super().__init__(message)
        self.error = error


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pow2(exponent: int) -> Fraction:
    return Fraction(1 << exponent) if exponent >= 0 else Fraction(1, 1 << -exponent)


def canonical_zero(code: int) -> int:
    return 0 if code & 0x7FFFFFFF == 0 else code


def decode_finite(code: int) -> Fraction:
    if isinstance(code, bool) or not isinstance(code, int) or not 0 <= code < 1 << 32:
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
    """Encode an exact rational to finite binary32, or report overflow."""

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
    if not (1 << 23) <= significand < 1 << 24:
        raise RuntimeError("normal binary32 significand invariant failed")
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def add_rne(left: int, right: int) -> int:
    return encode_finite_rne(decode_finite(left) + decode_finite(right))


def positive_add_rne(left: int, right: int) -> int:
    left_value = decode_finite(left)
    right_value = decode_finite(right)
    if left_value < 0 or right_value < 0:
        raise OracleError(ERR_ARGUMENT, "positive addition received a negative operand")
    return encode_finite_rne(left_value + right_value)


def divide_rne(numerator: int, denominator: int) -> int:
    left = decode_finite(numerator)
    right = decode_finite(denominator)
    if right == 0:
        raise OracleError(ERR_ARGUMENT, "division denominator is zero")
    return encode_finite_rne(left / right)


def maximum_code(row: Sequence[int]) -> tuple[int, int]:
    if len(row) != 4:
        raise ValueError("stable-softmax row must contain four values")
    selected = canonical_zero(int(row[0]))
    selected_value = decode_finite(selected)
    selected_column = 0
    for column, raw in enumerate(row[1:], start=1):
        candidate = canonical_zero(int(raw))
        candidate_value = decode_finite(candidate)
        if candidate_value > selected_value:
            selected = candidate
            selected_value = candidate_value
            selected_column = column
    return selected, selected_column


def stable_softmax_oracle(
    raw_matrix: Sequence[int],
) -> tuple[tuple[int, ...], int, dict[str, Any]]:
    """Execute the frozen 4x4 stable-softmax sequence exactly."""

    if len(raw_matrix) != 16:
        raise ValueError("one stable-softmax matrix requires sixteen values")
    matrix = [canonical_zero(int(code)) for code in raw_matrix]
    diagnostics: dict[str, Any] = {
        "exp_zero_count": 0,
        "maximum_columns": [],
        "shifted_codes": [],
    }
    try:
        for code in matrix:
            decode_finite(code)
        output: list[int] = []
        for row_start in range(0, 16, 4):
            row = matrix[row_start : row_start + 4]
            maximum, maximum_column = maximum_code(row)
            diagnostics["maximum_columns"].append(maximum_column)
            negative_maximum = (
                0 if maximum & 0x7FFFFFFF == 0 else maximum ^ 0x80000000
            )
            shifted = [add_rne(code, negative_maximum) for code in row]
            if any(decode_finite(code) > 0 for code in shifted):
                raise OracleError(ERR_ARGUMENT, "max subtraction became positive")
            diagnostics["shifted_codes"].extend(shifted)
            try:
                exponentials = [binary32_exp_rne(code) for code in shifted]
            except HCPreReferenceError as exc:
                raise OracleError(ERR_ARGUMENT, str(exc)) from exc
            diagnostics["exp_zero_count"] += sum(code == 0 for code in exponentials)
            denominator = positive_add_rne(
                positive_add_rne(exponentials[0], exponentials[1]),
                positive_add_rne(exponentials[2], exponentials[3]),
            )
            if denominator == 0:
                raise OracleError(ERR_ARGUMENT, "stable-softmax denominator is zero")
            output.extend(
                positive_add_rne(divide_rne(code, denominator), EPSILON)
                for code in exponentials
            )
        return tuple(output), ERR_NONE, diagnostics
    except OracleError as exc:
        return (0,) * 16, exc.error, diagnostics


def u32le(values: Iterable[int]) -> bytes:
    return b"".join(struct.pack("<I", int(value)) for value in values)


def write_hex(path: Path, values: Iterable[int]) -> None:
    path.write_text(
        "".join(f"{int(value) & 0xFFFFFFFF:08x}\n" for value in values),
        encoding="ascii",
    )


def load_checkpoint_inputs(checkpoint: Path) -> tuple[list[tuple[int, ...]], dict[str, Any]]:
    manifest_path = checkpoint / CHECKPOINT_MANIFEST
    binary_path = checkpoint / CHECKPOINT_BINARY
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    if manifest.get("schema") != "opentallas.rtl.a3_hc_stable_softmax_checkpoint_inputs.v1":
        raise ValueError("checkpoint stable-softmax manifest schema drift")
    if manifest.get("status") != "checkpoint_derived_input_vectors":
        raise ValueError("checkpoint stable-softmax manifest is not an input record")
    expected_record = manifest.get("record_sha256")
    record_body = dict(manifest)
    record_body.pop("record_sha256", None)
    if expected_record != sha256_bytes(canonical(record_body)):
        raise ValueError("checkpoint stable-softmax manifest record hash drift")
    for relative, expected in manifest.get("source_sha256", {}).items():
        source = ROOT / relative
        if not source.is_file() or sha256_file(source) != expected:
            raise ValueError(f"checkpoint extraction source hash drift: {relative}")

    payload = binary_path.read_bytes()
    if sha256_bytes(payload) != manifest.get("binary_sha256"):
        raise ValueError("checkpoint stable-softmax binary hash drift")
    count = int(manifest.get("matrix_count", -1))
    if len(payload) != count * 16 * 4:
        raise ValueError("checkpoint stable-softmax binary size drift")
    words = tuple(value[0] for value in struct.iter_unpack("<I", payload))
    matrices = [tuple(words[index : index + 16]) for index in range(0, len(words), 16)]
    if len(matrices) != count:
        raise RuntimeError("checkpoint stable-softmax matrix decode invariant failed")
    return matrices, manifest


def directed_matrices() -> list[tuple[str, str, tuple[int, ...]]]:
    zero = 0x00000000
    one = 0x3F800000
    neg_one = 0xBF800000
    ordered = (0xC0400000, 0xC0000000, neg_one, zero)
    reversed_ordered = tuple(reversed(ordered))
    underflow = (zero, 0xC2C80000, 0xC2D00000, 0xC3800000)
    near_one = (0x3F7FFFFF, one, 0x3F800001, 0x3F800002)
    near_negative_one = (0xBF800002, 0xBF800001, neg_one, 0xBF7FFFFF)
    subnormal = (0x00000000, 0x00000001, 0x00000002, 0x007FFFFF)
    negative_subnormal = (0x807FFFFF, 0x80000002, 0x80000001, 0x80000000)
    max_each_column = tuple(
        value
        for shift in range(4)
        for value in ordered[shift:] + ordered[:shift]
    )
    valid = [
        ("all_positive_zero", "directed_ordering", (zero,) * 16),
        ("all_one", "directed_ordering", (one,) * 16),
        (
            "signed_zero_ties",
            "directed_ordering",
            (0x80000000, zero, 0x80000000, zero) * 4,
        ),
        ("maximum_each_column", "directed_ordering", max_each_column),
        ("ascending_rows", "directed_ordering", ordered * 4),
        ("descending_rows", "directed_ordering", reversed_ordered * 4),
        ("near_equal_positive", "directed_rounding", near_one * 4),
        ("near_equal_negative", "directed_rounding", near_negative_one * 4),
        ("positive_subnormal_ladder", "directed_rounding", subnormal * 4),
        (
            "negative_subnormal_ladder",
            "directed_rounding",
            negative_subnormal * 4,
        ),
        ("exponential_underflow", "directed_underflow", underflow * 4),
        (
            "negative_maximum_underflow",
            "directed_underflow",
            (zero, 0xFF7FFFFF, 0xC3800000, 0xC2D00000) * 4,
        ),
        ("all_max_finite", "directed_extreme", (MAX_FINITE,) * 16),
        ("all_negative_max_finite", "directed_extreme", (0xFF7FFFFF,) * 16),
        (
            "mixed_rows",
            "directed_ordering",
            ordered + near_one + underflow + negative_subnormal,
        ),
    ]

    overflow = (MAX_FINITE, 0xFF7FFFFF, zero, one) + (zero,) * 12
    invalids = [
        ("subtraction_overflow", "directed_overflow", overflow),
        (
            "positive_infinity",
            "nonfinite_refusal",
            (0x7F800000,) + (one,) * 15,
        ),
        (
            "negative_infinity",
            "nonfinite_refusal",
            (one,) * 5 + (0xFF800000,) + (one,) * 10,
        ),
        (
            "quiet_nan",
            "nonfinite_refusal",
            (one,) * 15 + (0x7FC00001,),
        ),
        (
            "signaling_nan",
            "nonfinite_refusal",
            (one,) * 7 + (0x7F800001,) + (one,) * 8,
        ),
        (
            "negative_nan",
            "nonfinite_refusal",
            (0xFFC00001,) + (one,) * 15,
        ),
    ]
    return valid + invalids


def build(
    output: Path = DEFAULT_OUTPUT,
    checkpoint: Path = DEFAULT_CHECKPOINT,
) -> dict[str, Any]:
    checkpoint_matrices, checkpoint_manifest = load_checkpoint_inputs(checkpoint)
    cases: list[tuple[str, str, tuple[int, ...]]] = []
    for index, matrix in enumerate(checkpoint_matrices):
        segment = "checkpoint_first_t512" if index < 512 else "checkpoint_final_t320"
        cases.append((f"{segment}_{index if index < 512 else index - 512}", segment, matrix))
    cases.extend(directed_matrices())

    expected: list[tuple[int, ...]] = []
    errors: list[int] = []
    error_counts: Counter[int] = Counter()
    category_counts: Counter[str] = Counter()
    maximum_columns: Counter[int] = Counter()
    exp_zero_count = 0
    shifted_zero_count = 0
    shifted_subnormal_count = 0
    checkpoint_expected: list[int] = []

    for _, category, matrix in cases:
        result, error, diagnostics = stable_softmax_oracle(matrix)
        expected.append(result)
        errors.append(error)
        error_counts[error] += 1
        category_counts[category] += 1
        exp_zero_count += int(diagnostics["exp_zero_count"])
        maximum_columns.update(int(value) for value in diagnostics["maximum_columns"])
        for code in diagnostics["shifted_codes"]:
            shifted_zero_count += int(code & 0x7FFFFFFF == 0)
            shifted_subnormal_count += int(
                code & 0x7FFFFFFF != 0 and (code >> 23) & 0xFF == 0
            )
        if category.startswith("checkpoint_"):
            checkpoint_expected.extend(result)

    first_four = tuple(expected[:4])
    if first_four != numeric_vectors.CHECKPOINT_STABLE_INPUTS:
        raise ValueError("independent first-four stable-softmax checkpoint sentinel drift")
    if any(errors[: len(checkpoint_matrices)]):
        raise ValueError("a checkpoint-derived stable-softmax matrix failed the oracle")

    output.mkdir(parents=True, exist_ok=True)
    input_words = [code for _, _, matrix in cases for code in matrix]
    expected_words = [
        word
        for result, error in zip(expected, errors, strict=True)
        for word in (*result, error)
    ]
    meta_words = (
        MAGIC,
        1,
        len(cases),
        len(checkpoint_matrices),
        len(cases) - len(checkpoint_matrices),
        error_counts[ERR_NONE],
        len(cases) - error_counts[ERR_NONE],
        0,  # Case zero is the explicit T=1 checkpoint shape witness.
    )
    write_hex(output / "meta.hex", meta_words)
    write_hex(output / "matrix_input.hex", input_words)
    write_hex(output / "matrix_expected.hex", expected_words)

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "independent_exact_vectors",
        "matrix_input_words": 16,
        "matrix_expected_words": 17,
        "counts": {
            "cases": len(cases),
            "checkpoint_cases": len(checkpoint_matrices),
            "directed_cases": len(cases) - len(checkpoint_matrices),
            "successful_cases": error_counts[ERR_NONE],
            "refused_cases": len(cases) - error_counts[ERR_NONE],
            "errors": {str(key): value for key, value in sorted(error_counts.items())},
            "categories": dict(sorted(category_counts.items())),
        },
        "coverage": {
            "maximum_column_counts": {
                str(key): value for key, value in sorted(maximum_columns.items())
            },
            "exponential_zero_results": exp_zero_count,
            "shifted_zero_codes": shifted_zero_count,
            "shifted_subnormal_codes": shifted_subnormal_count,
            "nonfinite_refusal_kinds": 5,
            "subtraction_overflow_cases": error_counts[ERR_OVERFLOW],
        },
        "checkpoint_binding": {
            "workload_id": checkpoint_manifest["workload"]["workload_id"],
            "workload_digest": checkpoint_manifest["workload"]["workload_digest"],
            "prompt_token_count": checkpoint_manifest["workload"]["prompt_token_count"],
            "checkpoint_revision": checkpoint_manifest["checkpoint"]["revision"],
            "input_binary_sha256": checkpoint_manifest["binary_sha256"],
            "segments": checkpoint_manifest["segments"],
            "independent_expected_u32le_sha256": sha256_bytes(
                u32le(checkpoint_expected)
            ),
            "first_four_match_retained_service_sentinels": True,
            "t1_shape_witness": {
                "case_index": 0,
                "position": 0,
                "token_id": numeric_vectors.CHECKPOINT_TOKEN_IDS[0],
                "input_u32le_sha256": sha256_bytes(u32le(cases[0][2])),
                "expected_u32le_sha256": sha256_bytes(u32le(expected[0])),
            },
        },
        "oracle": {
            "binary32_arithmetic": "self-contained exact Fraction decode/rational arithmetic/integer RNE encode",
            "exponential": "runtime.reference.hyper_connection exact-rational adaptive interval",
            "host_floating_point": False,
            "service_arithmetic_imported": False,
            "rtl_implementation_imported": False,
            "operation_order": "source-major max; RN32 subtract; CR32 exp; balanced RN32 sum; RN32 divide; RN32 epsilon add",
        },
        "files": {
            "meta.hex": sha256_file(output / "meta.hex"),
            "matrix_input.hex": sha256_file(output / "matrix_input.hex"),
            "matrix_expected.hex": sha256_file(output / "matrix_expected.hex"),
        },
        "claim_boundary": {
            "vectors_only": True,
            "checkpoint_first_and_final_prefill_blocks_covered": True,
            "full_200k_checkpoint_domain": False,
            "full_hc_pre": False,
            "model_token_generation": False,
            "eos": False,
            "architectural_timing": False,
            "tpot": False,
        },
    }
    body["vector_set_id"] = sha256_bytes(canonical(body))
    (output / "index.json").write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build(args.output, args.checkpoint)
    print(
        "built HC stable-softmax vectors: "
        f"{result['counts']['cases']} cases, "
        f"{result['counts']['checkpoint_cases']} checkpoint-derived, "
        f"{result['counts']['refused_cases']} refused"
    )


if __name__ == "__main__":
    main()
