"""Exact DeepSeek V4 in-place FP4 activation QDQ semantics.

The pinned indexer applies ``fp4_act_quant(..., block_size=32, inplace=True)``
after its Hadamard rotations. The official wrapper makes the last dimension
contiguous and flattens all leading dimensions before launching the kernel.
This reference consumes that flattened BF16 matrix, exposes the otherwise
internal E2M1 and E8M0 encodings for checking, and returns the BF16 QDQ result.

No host floating-point arithmetic participates. Exceptional input and an
intermediate binary32 overflow fail closed instead of silently committing the
official development kernel's incidental NaN/infinity behavior.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_multiply,
    decode_bf16,
    decode_binary32,
    decode_e2m1,
    encode_binary32_rne,
    encode_e2m1_rne,
)


KERNEL_SOURCE_SHA256 = (
    "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
)
FP4_QDQ_BLOCK_SIZE = 32
FP4_MAXIMUM = Fraction(6)
FP4_AMAX_FLOOR = Fraction(6, 1 << 126)
_BINARY32_RECIPROCAL_SIX = encode_binary32_rne(Fraction(1, 6))

BF16Matrix: TypeAlias = tuple[tuple[int, ...], ...]
E2M1Matrix: TypeAlias = tuple[tuple[int, ...], ...]
E8M0Matrix: TypeAlias = tuple[tuple[int, ...], ...]


class QuantizationReferenceError(ValueError):
    """Raised when FP4 QDQ input or arithmetic violates the target contract."""


@dataclass(frozen=True)
class FP4QDQResult:
    """BF16 QDQ output plus internal codes retained for independent checking."""

    e2m1_codes: E2M1Matrix
    scale_codes: E8M0Matrix
    values: BF16Matrix


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise QuantizationReferenceError(f"{label} must be a sequence")
    return value


def _finite_bf16_matrix(value: object) -> tuple[tuple[Fraction, ...], ...]:
    raw_rows = _sequence(value, "input_codes")
    if not raw_rows:
        raise QuantizationReferenceError("input_codes must contain at least one row")

    width: int | None = None
    result: list[tuple[Fraction, ...]] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"input_codes[{row_index}]")
        if width is None:
            width = len(row)
            if width == 0:
                raise QuantizationReferenceError(
                    "input_codes rows must contain at least one element"
                )
        elif len(row) != width:
            raise QuantizationReferenceError(
                f"input_codes must be rectangular with width {width}"
            )

        decoded_row: list[Fraction] = []
        for column, code in enumerate(row):
            label = f"input_codes[{row_index}][{column}]"
            if (
                isinstance(code, bool)
                or not isinstance(code, int)
                or not 0 <= code < 1 << 16
            ):
                raise QuantizationReferenceError(
                    f"{label} must be a 16-bit BF16 encoding"
                )
            decoded = decode_bf16(code)
            if not decoded.finite or decoded.value is None:
                raise QuantizationReferenceError(f"{label} must be finite BF16")
            decoded_row.append(decoded.value)
        result.append(tuple(decoded_row))
    return tuple(result)


def _power_of_two(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent)
    return Fraction(1, 1 << -exponent)


def _ceil_log2(value: Fraction) -> int:
    if value <= 0:
        raise NumericReferenceError("FP4 scale ratio must be positive")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _power_of_two(exponent):
        exponent -= 1
    if value != _power_of_two(exponent):
        exponent += 1
    return exponent


def _block_qdq(
    values: tuple[Fraction, ...],
) -> tuple[int, tuple[int, ...], tuple[int, ...]]:
    maximum = max(max(abs(value) for value in values), FP4_AMAX_FLOOR)

    # Match fast_round_scale: FP32 amax times the rounded FP32 1/6 constant,
    # followed by the bit-level ceil(log2) and exact fast_pow2 construction.
    maximum_code = encode_binary32_rne(maximum)
    ratio_code = binary32_multiply(maximum_code, _BINARY32_RECIPROCAL_SIX)
    ratio = decode_binary32(ratio_code)
    if not ratio.finite or ratio.value is None:  # pragma: no cover - primitive gate
        raise NumericReferenceError("FP4 scale ratio is nonfinite")
    scale_exponent = _ceil_log2(ratio.value)
    scale_code = scale_exponent + 127
    if not 1 <= scale_code <= 253:
        raise NumericReferenceError("FP4 QDQ requires an unrepresentable E8M0 scale")

    scale = _power_of_two(scale_exponent)
    scale_binary32 = encode_binary32_rne(scale)
    fp4_codes: list[int] = []
    output_codes: list[int] = []
    for value in values:
        value_binary32 = encode_binary32_rne(value)
        quotient_code = binary32_divide(value_binary32, scale_binary32)
        quotient = decode_binary32(quotient_code)
        if not quotient.finite or quotient.value is None:  # pragma: no cover
            raise NumericReferenceError("FP4 quotient is nonfinite")
        clamped = max(-FP4_MAXIMUM, min(FP4_MAXIMUM, quotient.value))
        quantized = encode_e2m1_rne(clamped)
        if quantized.saturated:  # pragma: no cover - clamp makes this invariant
            raise RuntimeError("clamped FP4 quotient unexpectedly saturated")
        fp4_codes.append(quantized.code)

        decoded_fp4 = decode_e2m1(quantized.code)
        assert decoded_fp4.value is not None
        fp4_binary32 = encode_binary32_rne(decoded_fp4.value)
        dequantized_code = binary32_multiply(fp4_binary32, scale_binary32)
        output = binary32_bits_to_bf16_rne(dequantized_code)
        if output.saturated:  # pragma: no cover - discrete products skip this range
            raise NumericReferenceError("FP4 QDQ BF16 output saturated")
        output_codes.append(output.code)
    return scale_code, tuple(fp4_codes), tuple(output_codes)


def fp4_qdq_bf16(
    input_codes: Sequence[Sequence[int]],
    *,
    block_size: int = FP4_QDQ_BLOCK_SIZE,
) -> FP4QDQResult:
    """Execute pinned ``FP4_QDQ`` over flattened BF16 rows.

    ``input_codes`` has shape ``[M, N]`` after flattening every original
    leading dimension exactly as the official ``view(-1, N)`` wrapper does.
    The last dimension must be a positive multiple of the only qualified block
    size, 32. Each block selects and records an independent E8M0 scale. The
    returned ``values`` have the same flattened shape; callers restore the
    source leading dimensions without changing element order.
    """

    if (
        isinstance(block_size, bool)
        or not isinstance(block_size, int)
        or block_size != FP4_QDQ_BLOCK_SIZE
    ):
        raise QuantizationReferenceError(
            f"block_size must equal the qualified value {FP4_QDQ_BLOCK_SIZE}"
        )
    values = _finite_bf16_matrix(input_codes)
    width = len(values[0])
    if width % block_size:
        raise QuantizationReferenceError(
            f"input width must be divisible by block_size {block_size}"
        )

    scale_rows: list[tuple[int, ...]] = []
    fp4_rows: list[tuple[int, ...]] = []
    output_rows: list[tuple[int, ...]] = []
    for row_index, row in enumerate(values):
        row_scales: list[int] = []
        row_fp4: list[int] = []
        row_output: list[int] = []
        for block_index, start in enumerate(range(0, width, block_size)):
            try:
                scale, fp4, output = _block_qdq(row[start : start + block_size])
            except NumericReferenceError as exc:
                raise QuantizationReferenceError(
                    f"input_codes row {row_index} block {block_index} failed: {exc}"
                ) from exc
            row_scales.append(scale)
            row_fp4.extend(fp4)
            row_output.extend(output)
        scale_rows.append(tuple(row_scales))
        fp4_rows.append(tuple(row_fp4))
        output_rows.append(tuple(row_output))

    return FP4QDQResult(
        e2m1_codes=tuple(fp4_rows),
        scale_codes=tuple(scale_rows),
        values=tuple(output_rows),
    )
