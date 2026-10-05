"""Independent exact Qwen RMSNorm oracle for the tensor accelerator.

The reference is deliberately scalar and imports no compiler, simulator,
NumPy, PyTorch, or model implementation.  It freezes the target-visible
arithmetic of ``Qwen3RMSNorm.forward``:

* BF16 inputs widen exactly to binary32;
* squares round once to binary32;
* the hidden axis uses the canonical balanced binary32 tree;
* mean, epsilon addition, and reciprocal square root round to binary32;
* the normalized value rounds to BF16 before the BF16 weight multiply; and
* the final product rounds once to BF16.

The reciprocal square root is the correctly rounded binary32 value of the exact
mathematical result, not a host-library approximation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_multiply,
    decode_bf16,
    decode_binary32,
    encode_binary32_rne,
)


NUMERIC_CONTRACT = "qwen3_rmsnorm_fp32_bf16_v1"
EPSILON = Fraction(1, 1_000_000)
EPSILON_CODE = encode_binary32_rne(EPSILON)
BF16Matrix: TypeAlias = tuple[tuple[int, ...], ...]

if EPSILON_CODE != 0x358637BD:  # pragma: no cover - import invariant
    raise RuntimeError("Qwen RMSNorm epsilon encoding differs")


class RMSNormReferenceError(ValueError):
    """Raised when an operand or arithmetic event violates the contract."""


@dataclass(frozen=True)
class RMSNormReferenceResult:
    """Exact output, normalization intermediates, and saturation accounting."""

    inverse_rms_codes: tuple[int, ...]
    mean_square_codes: tuple[int, ...]
    normalized_saturated_element_count: int
    normalized_values: BF16Matrix
    output_saturated_element_count: int
    values: BF16Matrix


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise RMSNormReferenceError(f"{label} must be a sequence")
    return value


def _finite_bf16_code(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < 1 << 16
    ):
        raise RMSNormReferenceError(f"{label} must be a 16-bit BF16 encoding")
    if not decode_bf16(value).finite:
        raise RMSNormReferenceError(f"{label} must be finite BF16")
    return value


def _matrix(value: object, label: str) -> BF16Matrix:
    rows = _sequence(value, label)
    if not rows:
        raise RMSNormReferenceError(f"{label} must contain at least one row")
    width: int | None = None
    result: list[tuple[int, ...]] = []
    for row_index, raw_row in enumerate(rows):
        row = _sequence(raw_row, f"{label}[{row_index}]")
        if width is None:
            width = len(row)
            if width == 0:
                raise RMSNormReferenceError(f"{label} rows must be nonempty")
        elif len(row) != width:
            raise RMSNormReferenceError(
                f"{label} must be rectangular with width {width}"
            )
        result.append(
            tuple(
                _finite_bf16_code(code, f"{label}[{row_index}][{column}]")
                for column, code in enumerate(row)
            )
        )
    return tuple(result)


def _weights(value: object, width: int) -> tuple[int, ...]:
    raw = _sequence(value, "weight_codes")
    if len(raw) != width:
        raise RMSNormReferenceError(
            f"weight_codes must contain exactly {width} elements"
        )
    return tuple(
        _finite_bf16_code(code, f"weight_codes[{index}]")
        for index, code in enumerate(raw)
    )


def _positive_binary32(code: object, label: str) -> tuple[int, Fraction]:
    if (
        isinstance(code, bool)
        or not isinstance(code, int)
        or not 0 <= code < 1 << 32
    ):
        raise RMSNormReferenceError(f"{label} must be a binary32 encoding")
    decoded = decode_binary32(code)
    if not decoded.finite or decoded.value is None or decoded.value <= 0:
        raise RMSNormReferenceError(f"{label} must be positive finite binary32")
    return code, decoded.value


def binary32_rsqrt_rne(code: int) -> int:
    """Return correctly rounded ``1 / sqrt(code)`` for positive binary32."""

    _, argument = _positive_binary32(code, "rsqrt argument")
    low = 0
    high = 0x7F7FFFFF
    lower_code = 0
    while low <= high:
        candidate_code = (low + high) // 2
        candidate = decode_binary32(candidate_code).value
        if candidate is None:  # pragma: no cover - positive finite code range
            raise RuntimeError("rsqrt search reached nonfinite binary32")
        if candidate * candidate * argument <= 1:
            lower_code = candidate_code
            low = candidate_code + 1
        else:
            high = candidate_code - 1
    if lower_code == 0x7F7FFFFF:  # pragma: no cover - binary32 input bound
        return lower_code
    upper_code = lower_code + 1
    lower = decode_binary32(lower_code).value
    upper = decode_binary32(upper_code).value
    if lower is None or upper is None:  # pragma: no cover - search invariant
        raise RuntimeError("rsqrt bracketing value is nonfinite")
    midpoint = (lower + upper) / 2
    comparison = midpoint * midpoint * argument
    if comparison < 1:
        return upper_code
    if comparison > 1:
        return lower_code
    return lower_code if lower_code & 1 == 0 else upper_code


def rms_norm_bf16(
    input_codes: Sequence[Sequence[int]],
    weight_codes: Sequence[int],
    *,
    epsilon_code: int = EPSILON_CODE,
) -> RMSNormReferenceResult:
    """Execute the complete target RMSNorm over one or more hidden rows."""

    inputs = _matrix(input_codes, "input_codes")
    width = len(inputs[0])
    weights = _weights(weight_codes, width)
    epsilon_bits, _ = _positive_binary32(epsilon_code, "epsilon_code")
    try:
        divisor = encode_binary32_rne(width)
        output_rows: list[tuple[int, ...]] = []
        normalized_rows: list[tuple[int, ...]] = []
        mean_codes: list[int] = []
        inverse_codes: list[int] = []
        normalized_saturation_count = 0
        output_saturation_count = 0
        for input_row in inputs:
            squares = tuple(
                binary32_multiply(code << 16, code << 16) for code in input_row
            )
            total = binary32_balanced_sum(squares)
            mean = binary32_divide(total, divisor)
            inverse = binary32_rsqrt_rne(binary32_add(mean, epsilon_bits))
            normalized_row: list[int] = []
            output_row: list[int] = []
            for input_code, weight_code in zip(input_row, weights, strict=True):
                normalized = binary32_bits_to_bf16_rne(
                    binary32_multiply(input_code << 16, inverse)
                )
                weighted = binary32_bits_to_bf16_rne(
                    binary32_multiply(normalized.code << 16, weight_code << 16)
                )
                normalized_saturation_count += int(normalized.saturated)
                output_saturation_count += int(weighted.saturated)
                normalized_row.append(normalized.code)
                output_row.append(weighted.code)
            mean_codes.append(mean)
            inverse_codes.append(inverse)
            normalized_rows.append(tuple(normalized_row))
            output_rows.append(tuple(output_row))
    except NumericReferenceError as exc:
        raise RMSNormReferenceError(f"RMSNorm arithmetic failed: {exc}") from exc
    return RMSNormReferenceResult(
        inverse_rms_codes=tuple(inverse_codes),
        mean_square_codes=tuple(mean_codes),
        normalized_saturated_element_count=normalized_saturation_count,
        normalized_values=tuple(normalized_rows),
        output_saturated_element_count=output_saturation_count,
        values=tuple(output_rows),
    )


__all__ = [
    "EPSILON",
    "EPSILON_CODE",
    "NUMERIC_CONTRACT",
    "RMSNormReferenceError",
    "RMSNormReferenceResult",
    "binary32_rsqrt_rne",
    "rms_norm_bf16",
]
