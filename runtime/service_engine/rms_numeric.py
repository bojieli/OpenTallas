"""Independent service arithmetic for weighted DeepSeek V4 RMS normalization.

The implementation follows ``spec/NUMERICS.md`` NUM-6.8 without depending on
the compiler or reference-model numeric helpers.  Raw encodings and exact
rational arithmetic keep every required binary32 rounding boundary explicit.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias


RMS_NORM_EPSILON_BINARY32 = 0x358637BD
RMS_NORM_WIDTHS = frozenset({128, 512, 1024, 4096})

BF16Matrix: TypeAlias = tuple[tuple[int, ...], ...]

_BINARY32_MAX_FINITE = 0x7F7FFFFF


class RMSServiceNumericError(ValueError):
    """Raised when a weighted RMS service transaction must be poisoned."""


@dataclass(frozen=True)
class RMSServiceResult:
    """Architectural output plus row intermediates used by evidence checks."""

    mean_square_codes: tuple[int, ...]
    inverse_rms_codes: tuple[int, ...]
    output_codes: BF16Matrix
    output_saturation_count: int


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise RMSServiceNumericError(f"{label} must be a sequence")
    return value


def _widen_finite_bf16_vector(
    value: object,
    *,
    label: str,
    width: int | None = None,
) -> tuple[int, ...]:
    raw = _sequence(value, label)
    if not raw:
        raise RMSServiceNumericError(f"{label} must contain at least one value")
    if width is not None and len(raw) != width:
        raise RMSServiceNumericError(f"{label} must contain exactly {width} values")

    widened: list[int] = []
    for index, code in enumerate(raw):
        element_label = f"{label}[{index}]"
        if (
            isinstance(code, bool)
            or not isinstance(code, int)
            or not 0 <= code < 1 << 16
        ):
            raise RMSServiceNumericError(
                f"{element_label} must be a 16-bit BF16 encoding"
            )
        if code & 0x7F80 == 0x7F80:
            raise RMSServiceNumericError(f"{element_label} must be finite BF16")
        # Every finite BF16 value widens exactly by appending sixteen zero bits.
        # Canonicalize either signed-zero encoding at this arithmetic boundary.
        widened.append(0 if code & 0x7FFF == 0 else code << 16)
    return tuple(widened)


def _pow2(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent, 1)
    return Fraction(1, 1 << -exponent)


def _round_ties_to_even_integer(value: Fraction) -> int:
    if value < 0:  # pragma: no cover - all callers pass magnitudes
        raise RMSServiceNumericError("unsigned rounding input is negative")
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = remainder * 2
    if doubled > value.denominator or (doubled == value.denominator and quotient & 1):
        quotient += 1
    return quotient


def _floor_log2(value: Fraction) -> int:
    if value <= 0:  # pragma: no cover - guarded by callers
        raise RMSServiceNumericError("log2 input is not positive")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _pow2(exponent):
        exponent -= 1
    elif value >= _pow2(exponent + 1):  # pragma: no cover - defensive bound
        exponent += 1
    return exponent


def _decode_binary32_finite(code: int) -> Fraction:
    if isinstance(code, bool) or not isinstance(code, int) or not 0 <= code < 1 << 32:
        raise RMSServiceNumericError("binary32 code is outside unsigned 32 bits")
    negative = bool(code & 0x80000000)
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent == 0xFF:
        raise RMSServiceNumericError("binary32 NaN or infinity poisons RMS service")
    if exponent == 0:
        magnitude = Fraction(fraction) * _pow2(-149)
    else:
        magnitude = Fraction((1 << 23) + fraction) * _pow2(exponent - 150)
    return -magnitude if negative and magnitude else magnitude


def _encode_binary32(value: Fraction) -> int:
    """Round an exact finite value to binary32 with RNE and gradual underflow."""

    if value == 0:
        return 0
    sign = 0x80000000 if value < 0 else 0
    magnitude = abs(value)
    minimum_normal = _pow2(-126)
    if magnitude < minimum_normal:
        significand = _round_ties_to_even_integer(magnitude / _pow2(-149))
        if significand == 0:
            return 0
        if significand < 1 << 23:
            return sign | significand
        return sign | (1 << 23)

    exponent = _floor_log2(magnitude)
    significand = _round_ties_to_even_integer(magnitude / _pow2(exponent - 23))
    if significand == 1 << 24:
        significand = 1 << 23
        exponent += 1
    if exponent > 127:
        raise RMSServiceNumericError("finite binary32 arithmetic overflow")
    if exponent < -126 or not (1 << 23) <= significand < 1 << 24:
        raise RMSServiceNumericError("binary32 encoding invariant failed")
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def _binary32_add(left_code: int, right_code: int) -> int:
    return _encode_binary32(
        _decode_binary32_finite(left_code) + _decode_binary32_finite(right_code)
    )


def _binary32_multiply(left_code: int, right_code: int) -> int:
    return _encode_binary32(
        _decode_binary32_finite(left_code) * _decode_binary32_finite(right_code)
    )


def _binary32_divide(numerator_code: int, denominator_code: int) -> int:
    denominator = _decode_binary32_finite(denominator_code)
    if denominator == 0:  # pragma: no cover - every qualified width is positive
        raise RMSServiceNumericError("binary32 division denominator is zero")
    return _encode_binary32(_decode_binary32_finite(numerator_code) / denominator)


def _binary32_balanced_sum(codes: tuple[int, ...]) -> int:
    if not codes:  # pragma: no cover - qualified rows are nonempty
        raise RMSServiceNumericError("binary32 RMS reduction is empty")
    level = codes
    while len(level) > 1:
        if len(level) & 1:
            level += (0,)
        level = tuple(
            _binary32_add(level[index], level[index + 1])
            for index in range(0, len(level), 2)
        )
    return level[0]


def _binary32_rsqrt(value_code: int) -> int:
    """Correctly round ``1/sqrt(value)`` to binary32, ties to even."""

    value = _decode_binary32_finite(value_code)
    if value <= 0:
        raise RMSServiceNumericError(
            "binary32 reciprocal-square-root input is not positive"
        )

    # Positive finite binary32 encodings are monotonic.  Find the adjacent
    # representable results around the exact reciprocal square root, then use
    # an exact midpoint comparison so host floating point never participates.
    lower_code = 0
    upper_exclusive = _BINARY32_MAX_FINITE + 1
    while lower_code + 1 < upper_exclusive:
        candidate_code = (lower_code + upper_exclusive) // 2
        candidate = _decode_binary32_finite(candidate_code)
        if candidate * candidate * value <= 1:
            lower_code = candidate_code
        else:
            upper_exclusive = candidate_code

    lower = _decode_binary32_finite(lower_code)
    lower_product = lower * lower * value
    if lower_product == 1:
        return lower_code
    if lower_code == _BINARY32_MAX_FINITE:
        raise RMSServiceNumericError("finite binary32 reciprocal square root overflow")

    upper_code = lower_code + 1
    upper = _decode_binary32_finite(upper_code)
    midpoint_product = ((lower + upper) / 2) ** 2 * value
    if midpoint_product < 1:
        return upper_code
    if midpoint_product > 1:
        return lower_code
    return lower_code if lower_code & 1 == 0 else upper_code


def _binary32_to_bf16(code: int) -> tuple[int, bool]:
    if isinstance(code, bool) or not isinstance(code, int) or not 0 <= code < 1 << 32:
        raise RMSServiceNumericError("binary32 output is outside unsigned 32 bits")
    if code & 0x7F800000 == 0x7F800000:
        raise RMSServiceNumericError("binary32 NaN or infinity poisons BF16 output")

    upper = code >> 16
    discarded = code & 0xFFFF
    if discarded > 0x8000 or (discarded == 0x8000 and upper & 1):
        upper += 1
    saturated = upper & 0x7F80 == 0x7F80
    if saturated:
        upper = (upper & 0x8000) | 0x7F7F
    if upper & 0x7FFF == 0:
        upper = 0
    return upper, saturated


def execute_weighted_rms_norm(
    input_codes: Sequence[Sequence[int]],
    weight_codes: Sequence[int],
    *,
    epsilon_binary32: int = RMS_NORM_EPSILON_BINARY32,
) -> RMSServiceResult:
    """Execute qualified NUM-6.8 weighted RMS normalization over BF16 rows."""

    if (
        isinstance(epsilon_binary32, bool)
        or not isinstance(epsilon_binary32, int)
        or epsilon_binary32 != RMS_NORM_EPSILON_BINARY32
    ):
        raise RMSServiceNumericError(
            "epsilon_binary32 must equal the qualified 1e-6 encoding "
            f"0x{RMS_NORM_EPSILON_BINARY32:08x}"
        )

    weights = _widen_finite_bf16_vector(weight_codes, label="weight_codes")
    width = len(weights)
    if width not in RMS_NORM_WIDTHS:
        raise RMSServiceNumericError(
            f"weight width {width} is outside qualified widths {sorted(RMS_NORM_WIDTHS)}"
        )
    width_code = _encode_binary32(Fraction(width))

    raw_rows = _sequence(input_codes, "input_codes")
    if not raw_rows:
        raise RMSServiceNumericError("input_codes must contain at least one row")

    means: list[int] = []
    inverses: list[int] = []
    outputs: list[tuple[int, ...]] = []
    saturation_count = 0
    for row_index, raw_row in enumerate(raw_rows):
        row = _widen_finite_bf16_vector(
            raw_row,
            label=f"input_codes[{row_index}]",
            width=width,
        )
        try:
            squares = tuple(_binary32_multiply(value, value) for value in row)
            square_sum = _binary32_balanced_sum(squares)
            mean = _binary32_divide(square_sum, width_code)
            biased_mean = _binary32_add(mean, epsilon_binary32)
            inverse = _binary32_rsqrt(biased_mean)

            output_row: list[int] = []
            for value, weight in zip(row, weights, strict=True):
                normalized = _binary32_multiply(value, inverse)
                weighted = _binary32_multiply(normalized, weight)
                converted, saturated = _binary32_to_bf16(weighted)
                saturation_count += int(saturated)
                output_row.append(converted)
        except RMSServiceNumericError as exc:
            raise RMSServiceNumericError(
                f"input_codes row {row_index} failed: {exc}"
            ) from exc

        means.append(mean)
        inverses.append(inverse)
        outputs.append(tuple(output_row))

    return RMSServiceResult(
        mean_square_codes=tuple(means),
        inverse_rms_codes=tuple(inverses),
        output_codes=tuple(outputs),
        output_saturation_count=saturation_count,
    )


__all__ = [
    "RMS_NORM_EPSILON_BINARY32",
    "RMS_NORM_WIDTHS",
    "RMSServiceNumericError",
    "RMSServiceResult",
    "execute_weighted_rms_norm",
]
