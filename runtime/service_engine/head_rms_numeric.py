"""Independent service arithmetic for DeepSeek V4 ``HEAD_RMS_NORM``.

This module implements the frozen NUM-6.9 profile without calling compiler or
reference-model numeric helpers.  Raw BF16/binary32 encodings and exact
rational arithmetic make every declared BF16 boundary, balanced reduction,
and reciprocal-square-root tie decision explicit.

The operation is atomic at the Python interface: every row and profile field
is validated before arithmetic begins, and no result object is returned if any
row poisons.  Input containers are never mutated.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias


HEAD_RMS_NORM_EPSILON_BF16 = 0x3586
HEAD_RMS_NORM_WIDTH = 512
HEAD_RMS_NORM_MAX_ROWS = 4

BF16Matrix: TypeAlias = tuple[tuple[int, ...], ...]

_BF16_MAX_FINITE = 0x7F7F
_BINARY32_WIDTH_512 = 0x44000000


class HeadRMSServiceNumericError(ValueError):
    """Raised when a HEAD_RMS_NORM service transaction must be poisoned."""


@dataclass(frozen=True)
class HeadRMSServiceResult:
    """Architectural outputs and row diagnostics from one atomic transaction."""

    mean_square_codes: tuple[int, ...]
    inverse_rms_codes: tuple[int, ...]
    output_codes: BF16Matrix
    output_saturation_count: int


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise HeadRMSServiceNumericError(f"{label} must be a sequence")
    return value


def _pow2(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent)
    return Fraction(1, 1 << -exponent)


def _round_ties_to_even_integer(value: Fraction) -> int:
    if value < 0:  # pragma: no cover - callers pass magnitudes
        raise HeadRMSServiceNumericError("unsigned rounding input is negative")
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = remainder * 2
    if doubled > value.denominator or (doubled == value.denominator and quotient & 1):
        quotient += 1
    return quotient


def _floor_log2(value: Fraction) -> int:
    if value <= 0:  # pragma: no cover - guarded by encoders
        raise HeadRMSServiceNumericError("log2 input is not positive")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _pow2(exponent):
        exponent -= 1
    elif value >= _pow2(exponent + 1):  # pragma: no cover - defensive bound
        exponent += 1
    return exponent


def _decode_bf16_finite(code: int) -> Fraction:
    if isinstance(code, bool) or not isinstance(code, int) or not 0 <= code < 1 << 16:
        raise HeadRMSServiceNumericError("BF16 code is outside unsigned 16 bits")
    negative = bool(code & 0x8000)
    exponent = (code >> 7) & 0xFF
    fraction = code & 0x7F
    if exponent == 0xFF:
        raise HeadRMSServiceNumericError("BF16 NaN or infinity poisons HEAD_RMS_NORM")
    if exponent == 0:
        magnitude = Fraction(fraction) * _pow2(-133)
    else:
        magnitude = Fraction(128 + fraction) * _pow2(exponent - 134)
    return -magnitude if negative and magnitude else magnitude


def _finite_bf16_row(value: object, label: str) -> tuple[int, ...]:
    raw = _sequence(value, label)
    if len(raw) != HEAD_RMS_NORM_WIDTH:
        raise HeadRMSServiceNumericError(
            f"{label} must contain exactly {HEAD_RMS_NORM_WIDTH} values"
        )
    result: list[int] = []
    for index, code in enumerate(raw):
        element_label = f"{label}[{index}]"
        if (
            isinstance(code, bool)
            or not isinstance(code, int)
            or not 0 <= code < 1 << 16
        ):
            raise HeadRMSServiceNumericError(
                f"{element_label} must be a 16-bit BF16 encoding"
            )
        if code & 0x7F80 == 0x7F80:
            raise HeadRMSServiceNumericError(f"{element_label} must be finite BF16")
        result.append(code)
    return tuple(result)


def _encode_bf16(value: Fraction) -> tuple[int, bool]:
    """Directly round an exact finite value to BF16, saturating overflow."""

    if value == 0:
        return 0, False
    sign = 0x8000 if value < 0 else 0
    magnitude = abs(value)
    maximum = _decode_bf16_finite(_BF16_MAX_FINITE)
    if magnitude > maximum:
        return sign | _BF16_MAX_FINITE, True

    if magnitude < _pow2(-126):
        significand = _round_ties_to_even_integer(magnitude / _pow2(-133))
        if significand == 0:
            return 0, False
        if significand < 1 << 7:
            return sign | significand, False
        return sign | (1 << 7), False

    exponent = _floor_log2(magnitude)
    significand = _round_ties_to_even_integer(magnitude / _pow2(exponent - 7))
    if significand == 1 << 8:
        significand = 1 << 7
        exponent += 1
    if exponent > 127:
        return sign | _BF16_MAX_FINITE, True
    if exponent < -126 or not 1 << 7 <= significand < 1 << 8:
        raise HeadRMSServiceNumericError("BF16 encoding invariant failed")
    return (
        sign | ((exponent + 127) << 7) | (significand - (1 << 7)),
        False,
    )


def _decode_binary32_finite(code: int) -> Fraction:
    if isinstance(code, bool) or not isinstance(code, int) or not 0 <= code < 1 << 32:
        raise HeadRMSServiceNumericError("binary32 code is outside unsigned 32 bits")
    negative = bool(code & 0x80000000)
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent == 0xFF:
        raise HeadRMSServiceNumericError(
            "binary32 NaN or infinity poisons HEAD_RMS_NORM"
        )
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
    if magnitude < _pow2(-126):
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
        raise HeadRMSServiceNumericError("finite binary32 reduction overflow")
    if exponent < -126 or not 1 << 23 <= significand < 1 << 24:
        raise HeadRMSServiceNumericError("binary32 encoding invariant failed")
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def _binary32_add(left_code: int, right_code: int) -> int:
    return _encode_binary32(
        _decode_binary32_finite(left_code) + _decode_binary32_finite(right_code)
    )


def _binary32_divide(numerator_code: int, denominator_code: int) -> int:
    denominator = _decode_binary32_finite(denominator_code)
    if denominator == 0:  # pragma: no cover - fixed width is positive
        raise HeadRMSServiceNumericError("binary32 division denominator is zero")
    return _encode_binary32(_decode_binary32_finite(numerator_code) / denominator)


def _binary32_balanced_sum(codes: tuple[int, ...]) -> int:
    if not codes:  # pragma: no cover - qualified width is nonzero
        raise HeadRMSServiceNumericError("binary32 balanced reduction is empty")
    level = codes
    while len(level) > 1:
        if len(level) & 1:
            level += (0,)
        level = tuple(
            _binary32_add(level[index], level[index + 1])
            for index in range(0, len(level), 2)
        )
    return level[0]


def _binary32_to_bf16(code: int) -> tuple[int, bool]:
    """Round an already-rounded finite binary32 encoding once to BF16."""

    _decode_binary32_finite(code)
    upper = code >> 16
    discarded = code & 0xFFFF
    if discarded > 0x8000 or (discarded == 0x8000 and upper & 1):
        upper += 1
    saturated = upper & 0x7F80 == 0x7F80
    if saturated:
        upper = (upper & 0x8000) | _BF16_MAX_FINITE
    if upper & 0x7FFF == 0:
        upper = 0
    return upper, saturated


def cr_bf16_rsqrt(value_code: int) -> int:
    """Correctly round ``1/sqrt(value)`` directly to BF16."""

    value = _decode_bf16_finite(value_code)
    if value <= 0:
        raise HeadRMSServiceNumericError(
            "BF16 reciprocal-square-root input is not positive"
        )

    lower_code = 0
    upper_exclusive = _BF16_MAX_FINITE + 1
    while lower_code + 1 < upper_exclusive:
        candidate_code = (lower_code + upper_exclusive) // 2
        candidate = _decode_bf16_finite(candidate_code)
        if candidate * candidate * value <= 1:
            lower_code = candidate_code
        else:
            upper_exclusive = candidate_code

    lower = _decode_bf16_finite(lower_code)
    lower_product = lower * lower * value
    if lower_product == 1:
        return lower_code
    if lower_code == _BF16_MAX_FINITE:
        raise HeadRMSServiceNumericError("finite BF16 reciprocal square root overflow")

    upper_code = lower_code + 1
    upper = _decode_bf16_finite(upper_code)
    midpoint_product = ((lower + upper) / 2) ** 2 * value
    if midpoint_product < 1:
        return upper_code
    if midpoint_product > 1:
        return lower_code
    return lower_code if lower_code & 1 == 0 else upper_code


def execute_head_rms_norm(
    input_codes: Sequence[Sequence[int]],
    *,
    epsilon_bf16: int = HEAD_RMS_NORM_EPSILON_BF16,
) -> HeadRMSServiceResult:
    """Execute one atomic NUM-6.9 unweighted query-head normalization."""

    if (
        isinstance(epsilon_bf16, bool)
        or not isinstance(epsilon_bf16, int)
        or epsilon_bf16 != HEAD_RMS_NORM_EPSILON_BF16
    ):
        raise HeadRMSServiceNumericError(
            "epsilon_bf16 must equal the qualified 1e-6 encoding "
            f"0x{HEAD_RMS_NORM_EPSILON_BF16:04x}"
        )

    raw_rows = _sequence(input_codes, "input_codes")
    if not raw_rows:
        raise HeadRMSServiceNumericError("input_codes must contain at least one row")
    # Diagnose a rank-1 payload as a shape/type error before applying the outer
    # command bound.  Inspecting one element is constant work and does not
    # materialize an attacker-controlled request.
    _sequence(raw_rows[0], "input_codes[0]")
    if len(raw_rows) > HEAD_RMS_NORM_MAX_ROWS:
        raise HeadRMSServiceNumericError(
            "input_codes row count exceeds the qualified command maximum "
            f"of {HEAD_RMS_NORM_MAX_ROWS}"
        )
    # Validate every row before any calculation so malformed later rows cannot
    # yield an observable partial transaction.
    rows = tuple(
        _finite_bf16_row(row, f"input_codes[{row_index}]")
        for row_index, row in enumerate(raw_rows)
    )
    epsilon = _decode_bf16_finite(HEAD_RMS_NORM_EPSILON_BF16)

    means: list[int] = []
    inverses: list[int] = []
    outputs: list[tuple[int, ...]] = []
    saturation_count = 0
    for row_index, row in enumerate(rows):
        try:
            values = tuple(_decode_bf16_finite(code) for code in row)

            square_codes: list[int] = []
            for value in values:
                square_code, square_saturated = _encode_bf16(value * value)
                if square_saturated:
                    raise HeadRMSServiceNumericError("finite BF16 square overflow")
                square_codes.append(square_code)

            widened_squares = tuple(
                0 if code & 0x7FFF == 0 else code << 16 for code in square_codes
            )
            square_sum = _binary32_balanced_sum(widened_squares)
            mean_binary32 = _binary32_divide(square_sum, _BINARY32_WIDTH_512)
            mean, mean_saturated = _binary32_to_bf16(mean_binary32)
            if mean_saturated:
                raise HeadRMSServiceNumericError("finite BF16 mean-square overflow")

            biased_mean, biased_saturated = _encode_bf16(
                _decode_bf16_finite(mean) + epsilon
            )
            if biased_saturated:
                raise HeadRMSServiceNumericError("finite BF16 epsilon add overflow")
            inverse = cr_bf16_rsqrt(biased_mean)
            inverse_value = _decode_bf16_finite(inverse)

            output_row: list[int] = []
            for value in values:
                output, saturated = _encode_bf16(value * inverse_value)
                output_row.append(output)
                saturation_count += int(saturated)
        except HeadRMSServiceNumericError as exc:
            raise HeadRMSServiceNumericError(
                f"input_codes row {row_index} failed: {exc}"
            ) from exc

        means.append(mean)
        inverses.append(inverse)
        outputs.append(tuple(output_row))

    return HeadRMSServiceResult(
        mean_square_codes=tuple(means),
        inverse_rms_codes=tuple(inverses),
        output_codes=tuple(outputs),
        output_saturation_count=saturation_count,
    )


__all__ = [
    "HEAD_RMS_NORM_EPSILON_BF16",
    "HEAD_RMS_NORM_MAX_ROWS",
    "HEAD_RMS_NORM_WIDTH",
    "HeadRMSServiceNumericError",
    "HeadRMSServiceResult",
    "cr_bf16_rsqrt",
    "execute_head_rms_norm",
]
