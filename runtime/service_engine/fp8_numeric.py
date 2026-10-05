"""Service-engine implementation of the frozen dense FP8 arithmetic contract.

This module is intentionally independent of ``runtime.reference``.  It carries
raw architectural encodings and uses exact rational arithmetic to make every
rounding point explicit.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction


DENSE_BLOCK_SIZE = 128


class FP8ServiceNumericError(ValueError):
    """Raised when service-engine numeric input poisons the transaction."""


@dataclass(frozen=True)
class QuantizedBlock:
    scale_code: int
    value_codes: tuple[int, ...]
    saturated: bool


@dataclass(frozen=True)
class BF16Result:
    code: int
    saturated: bool


def _unsigned(value: int, bits: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 1 << bits:
        raise FP8ServiceNumericError(f"{label} is outside unsigned {bits} bits")
    return value


def _pow2(exponent: int) -> Fraction:
    return Fraction(1 << exponent, 1) if exponent >= 0 else Fraction(1, 1 << -exponent)


def _round_even(value: Fraction) -> int:
    if value < 0:
        raise FP8ServiceNumericError("unsigned rounding input is negative")
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = remainder * 2
    if doubled > value.denominator or (
        doubled == value.denominator and quotient & 1
    ):
        quotient += 1
    return quotient


def _floor_log2(value: Fraction) -> int:
    if value <= 0:
        raise FP8ServiceNumericError("log2 input is not positive")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _pow2(exponent):
        exponent -= 1
    elif value >= _pow2(exponent + 1):
        exponent += 1
    return exponent


def decode_bf16_finite(code: int) -> Fraction:
    code = _unsigned(code, 16, "BF16 code")
    negative = bool(code & 0x8000)
    exponent = (code >> 7) & 0xFF
    fraction = code & 0x7F
    if exponent == 0xFF:
        raise FP8ServiceNumericError("BF16 NaN or infinity poisons activation input")
    if exponent == 0:
        magnitude = Fraction(fraction) * _pow2(-133)
    else:
        magnitude = Fraction(128 + fraction) * _pow2(exponent - 134)
    return -magnitude if negative and magnitude else magnitude


def decode_e4m3fn_finite(code: int) -> Fraction:
    code = _unsigned(code, 8, "E4M3FN code")
    negative = bool(code & 0x80)
    exponent = (code >> 3) & 0xF
    fraction = code & 0x7
    if exponent == 0xF and fraction == 0x7:
        raise FP8ServiceNumericError("E4M3FN NaN poisons weight or activation")
    if exponent == 0:
        magnitude = Fraction(fraction) * _pow2(-9)
    else:
        magnitude = Fraction(8 + fraction) * _pow2(exponent - 10)
    return -magnitude if negative and magnitude else magnitude


def decode_e8m0_finite(code: int) -> Fraction:
    code = _unsigned(code, 8, "E8M0 code")
    if code == 0xFF:
        raise FP8ServiceNumericError("reserved E8M0 scale poisons transaction")
    return _pow2(code - 127)


_POSITIVE_E4M3 = tuple(decode_e4m3fn_finite(code) for code in range(0x7F))


def _encode_e4m3fn(value: Fraction) -> tuple[int, bool]:
    if value == 0:
        return 0, False
    sign = 0x80 if value < 0 else 0
    magnitude = abs(value)
    if magnitude > 448:
        return sign | 0x7E, True
    lower = 0
    upper = len(_POSITIVE_E4M3)
    while lower < upper:
        middle = (lower + upper) // 2
        if _POSITIVE_E4M3[middle] < magnitude:
            lower = middle + 1
        else:
            upper = middle
    index = lower
    if index < len(_POSITIVE_E4M3) and _POSITIVE_E4M3[index] == magnitude:
        return sign | index, False
    if index == 0 or index >= len(_POSITIVE_E4M3):
        raise FP8ServiceNumericError("E4M3FN rounding search escaped finite table")
    below = index - 1
    below_distance = magnitude - _POSITIVE_E4M3[below]
    above_distance = _POSITIVE_E4M3[index] - magnitude
    if below_distance < above_distance:
        selected = below
    elif above_distance < below_distance:
        selected = index
    else:
        selected = below if below & 1 == 0 else index
    return (0 if selected == 0 else sign) | selected, False


def quantize_bf16_block(codes: tuple[int, ...]) -> QuantizedBlock:
    if len(codes) != DENSE_BLOCK_SIZE:
        raise FP8ServiceNumericError(
            f"activation block must contain {DENSE_BLOCK_SIZE} BF16 values"
        )
    values = tuple(decode_bf16_finite(code) for code in codes)
    maximum = max(abs(value) for value in values)
    if maximum == 0:
        return QuantizedBlock(0x7F, (0,) * DENSE_BLOCK_SIZE, False)
    scale_code = next(
        (
            code
            for code in range(0xFF)
            if maximum <= Fraction(448) * _pow2(code - 127)
        ),
        None,
    )
    if scale_code is None:
        raise FP8ServiceNumericError("activation requires unrepresentable E8M0 scale")
    scale = _pow2(scale_code - 127)
    quantized = tuple(_encode_e4m3fn(value / scale) for value in values)
    return QuantizedBlock(
        scale_code,
        tuple(record[0] for record in quantized),
        any(record[1] for record in quantized),
    )


def _decode_binary32_finite(code: int) -> Fraction:
    code = _unsigned(code, 32, "binary32 code")
    negative = bool(code & 0x80000000)
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent == 0xFF:
        raise FP8ServiceNumericError("binary32 NaN or infinity poisons accumulation")
    if exponent == 0:
        magnitude = Fraction(fraction) * _pow2(-149)
    else:
        magnitude = Fraction((1 << 23) + fraction) * _pow2(exponent - 150)
    return -magnitude if negative and magnitude else magnitude


def _encode_binary32(value: Fraction) -> int:
    if value == 0:
        return 0
    sign = 0x80000000 if value < 0 else 0
    magnitude = abs(value)
    if magnitude < _pow2(-126):
        significand = _round_even(magnitude / _pow2(-149))
        if significand == 0:
            return 0
        if significand < 1 << 23:
            return sign | significand
        return sign | (1 << 23)
    exponent = _floor_log2(magnitude)
    significand = _round_even(magnitude / _pow2(exponent - 23))
    if significand == 1 << 24:
        significand = 1 << 23
        exponent += 1
    if exponent > 127:
        raise FP8ServiceNumericError("finite binary32 accumulation overflow")
    if exponent < -126 or not (1 << 23) <= significand < 1 << 24:
        raise FP8ServiceNumericError("binary32 encoding invariant failed")
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def _binary32_add(left: int, right: int) -> int:
    return _encode_binary32(
        _decode_binary32_finite(left) + _decode_binary32_finite(right)
    )


def _balanced_sum(codes: tuple[int, ...]) -> int:
    if not codes:
        raise FP8ServiceNumericError("binary32 reduction is empty")
    level = codes
    while len(level) > 1:
        if len(level) & 1:
            level += (0,)
        level = tuple(
            _binary32_add(level[index], level[index + 1])
            for index in range(0, len(level), 2)
        )
    return level[0]


def _block_dot(
    activation: QuantizedBlock,
    weight_codes: bytes,
    weight_scale_code: int,
) -> int:
    if len(weight_codes) != DENSE_BLOCK_SIZE:
        raise FP8ServiceNumericError(
            f"weight block must contain {DENSE_BLOCK_SIZE} FP8 values"
        )
    activation_scale = decode_e8m0_finite(activation.scale_code)
    weight_scale = decode_e8m0_finite(weight_scale_code)
    accumulator = 0
    for activation_code, weight_code in zip(
        activation.value_codes, weight_codes, strict=True
    ):
        product = (
            decode_e4m3fn_finite(activation_code)
            * activation_scale
            * decode_e4m3fn_finite(weight_code)
            * weight_scale
        )
        accumulator = _encode_binary32(
            _decode_binary32_finite(accumulator) + product
        )
    return accumulator


def _binary32_to_bf16(code: int) -> BF16Result:
    code = _unsigned(code, 32, "binary32 output")
    exponent = (code >> 23) & 0xFF
    if exponent == 0xFF:
        raise FP8ServiceNumericError("binary32 NaN or infinity poisons BF16 output")
    upper = code >> 16
    discarded = code & 0xFFFF
    if discarded > 0x8000 or (discarded == 0x8000 and upper & 1):
        upper += 1
    saturated = (upper & 0x7F80) == 0x7F80
    if saturated:
        upper = (upper & 0x8000) | 0x7F7F
    if upper & 0x7FFF == 0:
        upper = 0
    return BF16Result(upper, saturated)


def execute_selected_rows(
    input_rows: tuple[tuple[int, ...], ...],
    *,
    selected_rows: tuple[int, ...],
    input_features: int,
    weight_row: Callable[[int], bytes],
    scale_code: Callable[[int, int], int],
) -> tuple[tuple[tuple[int, ...], ...], int, int]:
    """Execute selected output rows through injected artifact accessors."""

    if input_features % DENSE_BLOCK_SIZE:
        raise FP8ServiceNumericError("input_features is not divisible by block size")
    block_count = input_features // DENSE_BLOCK_SIZE
    quantized_rows = []
    activation_saturations = 0
    for row in input_rows:
        if len(row) != input_features:
            raise FP8ServiceNumericError("input row width differs from input_features")
        blocks = []
        for block_index in range(block_count):
            start = block_index * DENSE_BLOCK_SIZE
            block = quantize_bf16_block(row[start : start + DENSE_BLOCK_SIZE])
            activation_saturations += int(block.saturated)
            blocks.append(block)
        quantized_rows.append(tuple(blocks))
    output = []
    output_saturations = 0
    for activation_blocks in quantized_rows:
        output_row = []
        for logical_row in selected_rows:
            weights = weight_row(logical_row)
            if len(weights) != input_features:
                raise FP8ServiceNumericError("weight accessor returned wrong row width")
            partials = []
            for block_index, activation in enumerate(activation_blocks):
                start = block_index * DENSE_BLOCK_SIZE
                partials.append(
                    _block_dot(
                        activation,
                        weights[start : start + DENSE_BLOCK_SIZE],
                        scale_code(logical_row, block_index),
                    )
                )
            converted = _binary32_to_bf16(_balanced_sum(tuple(partials)))
            output_saturations += int(converted.saturated)
            output_row.append(converted.code)
        output.append(tuple(output_row))
    return tuple(output), activation_saturations, output_saturations


__all__ = [
    "DENSE_BLOCK_SIZE",
    "FP8ServiceNumericError",
    "execute_selected_rows",
]
