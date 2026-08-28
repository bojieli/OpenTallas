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
    magnitudes = (
        Fraction(0),
        Fraction(1, 2),
        Fraction(1),
        Fraction(3, 2),
        Fraction(2),
        Fraction(3),
        Fraction(4),
        Fraction(6),
    )
    magnitude = magnitudes[code & 0x7]
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


_E4M3FN_POSITIVE = tuple(
    decode_e4m3fn(code).value for code in range(0x7F)
)
if any(value is None for value in _E4M3FN_POSITIVE):  # pragma: no cover - invariant
    raise RuntimeError("positive E4M3FN table unexpectedly contains NaN")


def _fraction(value: Fraction | int, label: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise NumericReferenceError(f"{label} must be an exact integer or Fraction")
    return Fraction(value)


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
