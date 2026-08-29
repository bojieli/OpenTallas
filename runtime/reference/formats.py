"""Independent exact scalar semantics for the DeepSeek V4 numeric formats.

This module is deliberately separate from compiler lowering, image generation,
microcode, and RTL.  Values are represented with :class:`fractions.Fraction`
so decoding and tie decisions do not inherit the host's floating-point mode.
The implementation follows ``spec/NUMERICS.md`` and the content-pinned official
DeepSeek V4 checkpoint/conversion sources.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Literal


ValueClass = Literal["zero", "finite", "infinity", "nan"]


class NumericReferenceError(ValueError):
    """Raised when an encoding or architectural numeric input is illegal."""


@dataclass(frozen=True)
class DecodedValue:
    """One exact decoded scalar and its architectural classification."""

    classification: ValueClass
    value: Fraction | None
    negative: bool

    @property
    def finite(self) -> bool:
        return self.classification in {"zero", "finite"}

    @property
    def zero(self) -> bool:
        return self.classification == "zero"

    @property
    def nan(self) -> bool:
        return self.classification == "nan"

    @property
    def infinity(self) -> bool:
        return self.classification == "infinity"


@dataclass(frozen=True)
class QuantizedE2M1:
    """E2M1 result plus the sticky finite-overflow indication."""

    code: int
    saturated: bool


@dataclass(frozen=True)
class QuantizedE4M3FN:
    """E4M3FN result plus the sticky finite-overflow indication."""

    code: int
    saturated: bool


@dataclass(frozen=True)
class QuantizedBF16:
    """BF16 result plus the sticky finite-overflow indication."""

    code: int
    saturated: bool


@dataclass(frozen=True)
class QuantizedActivationBlock:
    """One BF16 activation block converted to E4M3FN plus E8M0 scale."""

    scale_code: int
    value_codes: tuple[int, ...]
    saturated: bool


ROUTED_REDUCTION_BLOCK = 32
DENSE_REDUCTION_BLOCK = 128
_BINARY32_MAX_FINITE = 0x7F7FFFFF
_BF16_MAX_FINITE = 0x7F7F

_E2M1_MAGNITUDES = (
    Fraction(0),
    Fraction(1, 2),
    Fraction(1),
    Fraction(3, 2),
    Fraction(2),
    Fraction(3),
    Fraction(4),
    Fraction(6),
)


def _unsigned(value: int, bits: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise NumericReferenceError(f"{label} must be an unsigned {bits}-bit integer")
    if value < 0 or value >= 1 << bits:
        raise NumericReferenceError(f"{label} is outside {bits} bits")
    return value


def _pow2(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent, 1)
    return Fraction(1, 1 << -exponent)


def _finite(value: Fraction) -> DecodedValue:
    if value == 0:
        return DecodedValue("zero", Fraction(0), False)
    return DecodedValue("finite", value, value < 0)


def decode_e2m1(code: int) -> DecodedValue:
    """Decode one E2M1 nibble, canonicalizing negative zero."""

    code = _unsigned(code, 4, "E2M1 code")
    magnitude = _E2M1_MAGNITUDES[code & 0x7]
    value = -magnitude if code & 0x8 and magnitude else magnitude
    return _finite(value)


def decode_packed_e2m1(byte: int) -> tuple[DecodedValue, DecodedValue]:
    """Decode the official low-nibble-first pair in one checkpoint byte."""

    byte = _unsigned(byte, 8, "packed E2M1 byte")
    return decode_e2m1(byte & 0xF), decode_e2m1(byte >> 4)


def decode_e8m0(code: int) -> DecodedValue:
    """Decode one unsigned E8M0 scale; ``0xff`` is reserved/poison."""

    code = _unsigned(code, 8, "E8M0 code")
    if code == 0xFF:
        return DecodedValue("nan", None, False)
    return _finite(_pow2(code - 127))


def decode_e4m3fn(code: int) -> DecodedValue:
    """Decode OCP/PyTorch finite-only FP8 E4M3FN exactly.

    Codes ``0x7f`` and ``0xff`` are NaNs.  In particular, ``0x7e`` and
    ``0xfe`` are the valid finite endpoints +448 and -448.
    """

    code = _unsigned(code, 8, "E4M3FN code")
    negative = bool(code & 0x80)
    exponent = (code >> 3) & 0xF
    fraction = code & 0x7
    if exponent == 0xF and fraction == 0x7:
        return DecodedValue("nan", None, negative)
    if exponent == 0:
        magnitude = Fraction(fraction) * _pow2(-9)
    else:
        magnitude = Fraction(8 + fraction) * _pow2(exponent - 10)
    value = -magnitude if negative and magnitude else magnitude
    return _finite(value)


def decode_bf16(code: int) -> DecodedValue:
    """Decode one IEEE BF16 value exactly, canonicalizing signed zero."""

    code = _unsigned(code, 16, "BF16 code")
    negative = bool(code & 0x8000)
    exponent = (code >> 7) & 0xFF
    fraction = code & 0x7F
    if exponent == 0xFF:
        if fraction == 0:
            return DecodedValue("infinity", None, negative)
        return DecodedValue("nan", None, negative)
    if exponent == 0:
        magnitude = Fraction(fraction) * _pow2(-133)
    else:
        magnitude = Fraction(128 + fraction) * _pow2(exponent - 134)
    value = -magnitude if negative and magnitude else magnitude
    return _finite(value)


def decode_binary32(code: int) -> DecodedValue:
    """Decode one IEEE binary32 value exactly, canonicalizing signed zero."""

    code = _unsigned(code, 32, "binary32 code")
    negative = bool(code & 0x80000000)
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent == 0xFF:
        if fraction == 0:
            return DecodedValue("infinity", None, negative)
        return DecodedValue("nan", None, negative)
    if exponent == 0:
        magnitude = Fraction(fraction) * _pow2(-149)
    else:
        magnitude = Fraction((1 << 23) + fraction) * _pow2(exponent - 150)
    value = -magnitude if negative and magnitude else magnitude
    return _finite(value)


_E4M3FN_POSITIVE = tuple(
    decode_e4m3fn(code).value for code in range(0x7F)
)
if any(value is None for value in _E4M3FN_POSITIVE):  # pragma: no cover - invariant
    raise RuntimeError("positive E4M3FN table unexpectedly contains NaN")


def _fraction(value: Fraction | int, label: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise NumericReferenceError(f"{label} must be an exact integer or Fraction")
    return Fraction(value)


def _round_ties_to_even_integer(value: Fraction) -> int:
    if value < 0:
        raise NumericReferenceError("unsigned rounding input must be nonnegative")
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = 2 * remainder
    if doubled > value.denominator or (
        doubled == value.denominator and quotient & 1
    ):
        quotient += 1
    return quotient


def _floor_log2(value: Fraction) -> int:
    if value <= 0:
        raise NumericReferenceError("log2 input must be positive")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _pow2(exponent):
        exponent -= 1
    elif value >= _pow2(exponent + 1):  # pragma: no cover - defensive bound
        exponent += 1
    return exponent


def encode_binary32_rne(value: Fraction | int) -> int:
    """Round one exact finite value to IEEE binary32, ties to even.

    Binary32 infinity or NaN is an architectural numeric exception rather than
    a saturating result, so a finite overflow raises ``NumericReferenceError``.
    Output zero is canonicalized to positive zero.
    """

    exact = _fraction(value, "binary32 input")
    if exact == 0:
        return 0
    sign = 0x80000000 if exact < 0 else 0
    magnitude = abs(exact)
    minimum_normal = _pow2(-126)
    if magnitude < minimum_normal:
        significand = _round_ties_to_even_integer(magnitude / _pow2(-149))
        if significand == 0:
            return 0
        if significand < 1 << 23:
            return sign | significand
        # Rounding the largest subnormal upward produces the smallest normal.
        return sign | (1 << 23)

    exponent = _floor_log2(magnitude)
    significand = _round_ties_to_even_integer(
        magnitude / _pow2(exponent - 23)
    )
    if significand == 1 << 24:
        significand = 1 << 23
        exponent += 1
    if exponent > 127:
        raise NumericReferenceError("finite binary32 accumulation overflow")
    if exponent < -126 or not (1 << 23) <= significand < (1 << 24):
        raise RuntimeError("binary32 normal encoding invariant failed")
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def encode_bf16_rne(value: Fraction | int) -> QuantizedBF16:
    """Round one exact finite value directly to BF16, ties to even.

    The conversion is performed from the exact rational input rather than via
    binary32, because an intermediate binary32 rounding can change the BF16
    result at a BF16 midpoint. Finite overflow saturates to the signed maximum
    finite encoding and is reported through the sticky ``saturated`` flag.
    Output zero is canonicalized to positive zero.
    """

    exact = _fraction(value, "BF16 input")
    if exact == 0:
        return QuantizedBF16(0, False)
    sign = 0x8000 if exact < 0 else 0
    magnitude = abs(exact)
    maximum = decode_bf16(_BF16_MAX_FINITE).value
    if maximum is None:  # pragma: no cover - constant-format invariant
        raise RuntimeError("BF16 maximum finite encoding is not finite")
    if magnitude > maximum:
        return QuantizedBF16(sign | _BF16_MAX_FINITE, True)

    minimum_normal = _pow2(-126)
    if magnitude < minimum_normal:
        significand = _round_ties_to_even_integer(magnitude / _pow2(-133))
        if significand == 0:
            return QuantizedBF16(0, False)
        if significand < 1 << 7:
            return QuantizedBF16(sign | significand, False)
        # Rounding the largest subnormal upward produces the smallest normal.
        return QuantizedBF16(sign | (1 << 7), False)

    exponent = _floor_log2(magnitude)
    significand = _round_ties_to_even_integer(
        magnitude / _pow2(exponent - 7)
    )
    if significand == 1 << 8:
        significand = 1 << 7
        exponent += 1
    if exponent > 127:
        return QuantizedBF16(sign | _BF16_MAX_FINITE, True)
    if exponent < -126 or not (1 << 7) <= significand < (1 << 8):
        raise RuntimeError("BF16 normal encoding invariant failed")
    return QuantizedBF16(
        sign | ((exponent + 127) << 7) | (significand - (1 << 7)),
        False,
    )


def _finite_binary32_value(code: int, label: str) -> Fraction:
    decoded = decode_binary32(code)
    if not decoded.finite or decoded.value is None:
        raise NumericReferenceError(f"{label} is binary32 NaN or infinity")
    return decoded.value


def binary32_add(left_code: int, right_code: int) -> int:
    """Add two finite binary32 encodings with one RNE rounding."""

    left = _finite_binary32_value(left_code, "binary32 left addend")
    right = _finite_binary32_value(right_code, "binary32 right addend")
    return encode_binary32_rne(left + right)


def binary32_multiply(left_code: int, right_code: int) -> int:
    """Multiply two finite binary32 encodings with one RNE rounding."""

    left = _finite_binary32_value(left_code, "binary32 left factor")
    right = _finite_binary32_value(right_code, "binary32 right factor")
    return encode_binary32_rne(left * right)


def binary32_divide(numerator_code: int, denominator_code: int) -> int:
    """Divide finite binary32 encodings with one RNE rounding."""

    numerator = _finite_binary32_value(
        numerator_code, "binary32 division numerator"
    )
    denominator = _finite_binary32_value(
        denominator_code, "binary32 division denominator"
    )
    if denominator == 0:
        raise NumericReferenceError("binary32 division denominator is zero")
    return encode_binary32_rne(numerator / denominator)


def binary32_rsqrt(value_code: int) -> int:
    """Return correctly rounded binary32 ``1/sqrt(value)``.

    Candidate selection uses exact rational comparisons, so no host square-root
    implementation or floating-point mode participates. The positive finite
    binary32 code space is monotonic; after locating the adjacent candidates,
    comparing the exact input times their midpoint squared resolves RNE and its
    ties-to-even case without representing the irrational result itself.
    """

    value = _finite_binary32_value(value_code, "binary32 rsqrt input")
    if value <= 0:
        raise NumericReferenceError("binary32 rsqrt input must be positive")

    lower_code = 0
    upper_exclusive = _BINARY32_MAX_FINITE + 1
    while lower_code + 1 < upper_exclusive:
        candidate_code = (lower_code + upper_exclusive) // 2
        candidate = _finite_binary32_value(
            candidate_code, "binary32 rsqrt candidate"
        )
        if candidate * candidate * value <= 1:
            lower_code = candidate_code
        else:
            upper_exclusive = candidate_code

    lower = _finite_binary32_value(lower_code, "binary32 rsqrt lower candidate")
    lower_product = lower * lower * value
    if lower_product == 1:
        return lower_code
    if lower_code == _BINARY32_MAX_FINITE:  # pragma: no cover - finite input bound
        raise NumericReferenceError("binary32 rsqrt overflow")

    upper_code = lower_code + 1
    upper = _finite_binary32_value(upper_code, "binary32 rsqrt upper candidate")
    midpoint = (lower + upper) / 2
    midpoint_product = midpoint * midpoint * value
    if midpoint_product < 1:
        return upper_code
    if midpoint_product > 1:
        return lower_code
    return lower_code if lower_code & 1 == 0 else upper_code


def bf16_rsqrt(value_code: int) -> int:
    """Return correctly rounded BF16 ``1/sqrt(value)``.

    Exact rational comparisons bracket the irrational result between adjacent
    positive finite BF16 values. Comparing the exact input times the square of
    their midpoint then selects round-to-nearest, with the encoding LSB
    resolving an exact tie to even. No host square root or floating-point mode
    participates.
    """

    decoded = decode_bf16(value_code)
    if not decoded.finite or decoded.value is None:
        raise NumericReferenceError("BF16 rsqrt input is NaN or infinity")
    value = decoded.value
    if value <= 0:
        raise NumericReferenceError("BF16 rsqrt input must be positive")

    lower_code = 0
    upper_exclusive = _BF16_MAX_FINITE + 1
    while lower_code + 1 < upper_exclusive:
        candidate_code = (lower_code + upper_exclusive) // 2
        candidate = decode_bf16(candidate_code).value
        if candidate is None:  # pragma: no cover - bounded finite search
            raise RuntimeError("BF16 rsqrt search reached a nonfinite candidate")
        if candidate * candidate * value <= 1:
            lower_code = candidate_code
        else:
            upper_exclusive = candidate_code

    lower = decode_bf16(lower_code).value
    if lower is None:  # pragma: no cover - bounded finite search
        raise RuntimeError("BF16 rsqrt lower candidate is nonfinite")
    lower_product = lower * lower * value
    if lower_product == 1:
        return lower_code
    if lower_code == _BF16_MAX_FINITE:  # pragma: no cover - finite input bound
        raise NumericReferenceError("BF16 rsqrt overflow")

    upper_code = lower_code + 1
    upper = decode_bf16(upper_code).value
    if upper is None:  # pragma: no cover - bounded finite search
        raise RuntimeError("BF16 rsqrt upper candidate is nonfinite")
    midpoint = (lower + upper) / 2
    midpoint_product = midpoint * midpoint * value
    if midpoint_product < 1:
        return upper_code
    if midpoint_product > 1:
        return lower_code
    return lower_code if lower_code & 1 == 0 else upper_code


def binary32_balanced_sum(codes: Iterable[int]) -> int:
    """Reduce finite encodings with the canonical NUM-6.1 balanced tree."""

    level = tuple(codes)
    if not level:
        raise NumericReferenceError("binary32 balanced sum must not be empty")
    for index, code in enumerate(level):
        _finite_binary32_value(code, f"binary32 balanced-sum input {index}")
    while len(level) > 1:
        if len(level) & 1:
            level += (0,)
        level = tuple(
            binary32_add(level[index], level[index + 1])
            for index in range(0, len(level), 2)
        )
    return level[0]


def binary32_product_add(
    accumulator_code: int,
    left: Fraction | int,
    right: Fraction | int,
) -> int:
    """Perform one NUM-4.1 exact-product, single-rounded binary32 add."""

    accumulator = decode_binary32(accumulator_code)
    if not accumulator.finite or accumulator.value is None:
        raise NumericReferenceError("binary32 accumulator is NaN or infinity")
    product = _fraction(left, "product left operand") * _fraction(
        right, "product right operand"
    )
    return encode_binary32_rne(accumulator.value + product)


def binary32_ordered_dot(
    left: Iterable[Fraction | int],
    right: Iterable[Fraction | int],
) -> int:
    """Accumulate a dot product in increasing logical reduction-index order."""

    left_values = tuple(left)
    right_values = tuple(right)
    if not left_values or len(left_values) != len(right_values):
        raise NumericReferenceError("dot operands must have the same nonzero length")
    accumulator = 0
    for lhs, rhs in zip(left_values, right_values, strict=True):
        accumulator = binary32_product_add(accumulator, lhs, rhs)
    return accumulator


def _finite_scale(code: int, label: str) -> Fraction:
    scale = decode_e8m0(code)
    if not scale.finite or scale.value is None:
        raise NumericReferenceError(f"reserved E8M0 scale poisons {label}")
    return scale.value


def _scaled_e4m3fn_values(
    codes: Iterable[int], scale_code: int, label: str
) -> tuple[Fraction, ...]:
    scale = _finite_scale(scale_code, label)
    result: list[Fraction] = []
    for index, code in enumerate(codes):
        decoded = decode_e4m3fn(code)
        if not decoded.finite or decoded.value is None:
            raise NumericReferenceError(f"{label} element {index} is E4M3FN NaN")
        result.append(decoded.value * scale)
    return tuple(result)


def mxfp4_fp8_block_dot(
    packed_weight_bytes: Iterable[int],
    weight_scale_code: int,
    activation_codes: Iterable[int],
    activation_scale_code: int,
) -> int:
    """Execute one official 32-value routed reduction block into binary32."""

    packed = tuple(packed_weight_bytes)
    activations = tuple(activation_codes)
    if len(packed) * 2 != ROUTED_REDUCTION_BLOCK:
        raise NumericReferenceError("MXFP4 routed block must contain 32 weights")
    if len(activations) != ROUTED_REDUCTION_BLOCK:
        raise NumericReferenceError("routed activation block must contain 32 values")
    weights = decode_mxfp4_block(packed, weight_scale_code)
    activation_values = _scaled_e4m3fn_values(
        activations, activation_scale_code, "routed activation block"
    )
    return binary32_ordered_dot(activation_values, weights)


def fp8_fp8_block_dot(
    weight_codes: Iterable[int],
    weight_scale_code: int,
    activation_codes: Iterable[int],
    activation_scale_code: int,
) -> int:
    """Execute one official 128-value dense reduction block into binary32."""

    weights = tuple(weight_codes)
    activations = tuple(activation_codes)
    if len(weights) != DENSE_REDUCTION_BLOCK:
        raise NumericReferenceError("dense FP8 block must contain 128 weights")
    if len(activations) != DENSE_REDUCTION_BLOCK:
        raise NumericReferenceError("dense activation block must contain 128 values")
    weight_values = _scaled_e4m3fn_values(
        weights, weight_scale_code, "dense weight block"
    )
    activation_values = _scaled_e4m3fn_values(
        activations, activation_scale_code, "dense activation block"
    )
    return binary32_ordered_dot(activation_values, weight_values)


def encode_e2m1_rne(value: Fraction | int) -> QuantizedE2M1:
    """Round an exact finite value to E2M1, ties to even, saturating overflow.

    E2M1 has no exceptional encodings. Values outside its finite range saturate
    to signed six. Output zero is canonical positive zero.
    """

    exact = _fraction(value, "E2M1 input")
    if exact == 0:
        return QuantizedE2M1(0, False)
    sign = 0x8 if exact < 0 else 0
    magnitude = abs(exact)
    maximum = _E2M1_MAGNITUDES[-1]
    if magnitude > maximum:
        return QuantizedE2M1(sign | 0x7, True)

    index = bisect_left(_E2M1_MAGNITUDES, magnitude)
    if index < len(_E2M1_MAGNITUDES) and _E2M1_MAGNITUDES[index] == magnitude:
        return QuantizedE2M1(sign | index, False)
    if index == 0 or index >= len(_E2M1_MAGNITUDES):  # pragma: no cover - bounded
        raise RuntimeError("E2M1 rounding search escaped its finite table")
    lower_code = index - 1
    upper_code = index
    lower_distance = magnitude - _E2M1_MAGNITUDES[lower_code]
    upper_distance = _E2M1_MAGNITUDES[upper_code] - magnitude
    if lower_distance < upper_distance:
        selected = lower_code
    elif upper_distance < lower_distance:
        selected = upper_code
    else:
        # The encoding LSB is the retained significand parity for every
        # adjacent E2M1 pair, including the zero/subnormal boundary.
        selected = lower_code if lower_code & 1 == 0 else upper_code
    if selected == 0:
        sign = 0
    return QuantizedE2M1(sign | selected, False)


def encode_e4m3fn_rne(value: Fraction | int) -> QuantizedE4M3FN:
    """Round an exact finite value to E4M3FN, ties to even, saturating overflow."""

    exact = _fraction(value, "E4M3FN input")
    if exact == 0:
        return QuantizedE4M3FN(0, False)
    sign = 0x80 if exact < 0 else 0
    magnitude = abs(exact)
    maximum = Fraction(448)
    if magnitude > maximum:
        return QuantizedE4M3FN(sign | 0x7E, True)

    # Codes 0x00..0x7e are monotonically increasing positive finite values.
    index = bisect_left(_E4M3FN_POSITIVE, magnitude)
    if index < len(_E4M3FN_POSITIVE) and _E4M3FN_POSITIVE[index] == magnitude:
        return QuantizedE4M3FN(sign | index, False)
    if index == 0 or index >= len(_E4M3FN_POSITIVE):  # pragma: no cover - bounded above
        raise RuntimeError("E4M3FN rounding search escaped its finite table")
    lower_code = index - 1
    upper_code = index
    lower_distance = magnitude - _E4M3FN_POSITIVE[lower_code]
    upper_distance = _E4M3FN_POSITIVE[upper_code] - magnitude
    if lower_distance < upper_distance:
        selected = lower_code
    elif upper_distance < lower_distance:
        selected = upper_code
    else:
        # Adjacent encodings have adjacent significands; the encoding LSB is
        # therefore the significand parity used by ties-to-even.
        selected = lower_code if lower_code & 1 == 0 else upper_code
    if selected == 0:
        sign = 0  # architectural zero is canonical positive zero
    return QuantizedE4M3FN(sign | selected, False)


def decode_mxfp4_block(
    packed: Iterable[int], scale_code: int
) -> tuple[Fraction, ...]:
    """Decode one packed MXFP4 block using its exact E8M0 scale."""

    scale = decode_e8m0(scale_code)
    if not scale.finite or scale.value is None:
        raise NumericReferenceError("reserved E8M0 scale poisons the MXFP4 block")
    values: list[Fraction] = []
    for byte in packed:
        low, high = decode_packed_e2m1(byte)
        assert low.value is not None and high.value is not None
        values.extend((low.value * scale.value, high.value * scale.value))
    return tuple(values)


def quantize_bf16_activation_block(
    codes: Iterable[int],
) -> QuantizedActivationBlock:
    """Apply the NUM-3.3 BF16-to-E4M3FN/E8M0 activation rule exactly."""

    decoded: list[Fraction] = []
    for index, code in enumerate(codes):
        value = decode_bf16(code)
        if not value.finite or value.value is None:
            raise NumericReferenceError(
                f"activation BF16 element {index} is NaN or infinity"
            )
        decoded.append(value.value)
    if not decoded:
        raise NumericReferenceError("activation block must contain at least one value")
    maximum = max(abs(value) for value in decoded)
    if maximum == 0:
        return QuantizedActivationBlock(0x7F, tuple(0 for _ in decoded), False)

    scale_code = next(
        (
            code
            for code in range(0xFF)
            if maximum <= Fraction(448) * _pow2(code - 127)
        ),
        None,
    )
    if scale_code is None:
        raise NumericReferenceError("activation requires an unrepresentable E8M0 scale")
    scale = _pow2(scale_code - 127)
    quantized = tuple(encode_e4m3fn_rne(value / scale) for value in decoded)
    return QuantizedActivationBlock(
        scale_code,
        tuple(item.code for item in quantized),
        any(item.saturated for item in quantized),
    )


def binary32_bits_to_bf16_rne(code: int) -> QuantizedBF16:
    """Convert finite IEEE binary32 bits to BF16 under NUM-4.2."""

    code = _unsigned(code, 32, "binary32 code")
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent == 0xFF:
        kind = "infinity" if fraction == 0 else "NaN"
        raise NumericReferenceError(f"binary32 {kind} poisons BF16 conversion")

    upper = code >> 16
    discarded = code & 0xFFFF
    if discarded > 0x8000 or (discarded == 0x8000 and upper & 1):
        upper += 1
    saturated = (upper & 0x7F80) == 0x7F80
    if saturated:
        upper = (upper & 0x8000) | 0x7F7F
    if upper & 0x7FFF == 0:
        upper = 0
    return QuantizedBF16(upper, saturated)
