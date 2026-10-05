"""Exact reference for the DeepSeek-V4.1-Flash main-KV FP4 latent contract.

Contract name: ``fp4_e2m1_s16_e4m3_to_fp8_v1``.

The mechanism, per docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md section 5
row 1 and section 7, is **E2M1 elements carrying one E4M3FN scale per 16
elements**.  It is deliberately *not* ``mxfp4_e2m1``, whose scale is E8M0 and
whose group is 32: the pinned V4.1 attention compressor quantizes the main
latent after RoPE with ``fp4_act_quant(latent, 16, True,
scale_dtype=float8_e4m3fn)`` (docs/SOURCES.md, SRC-DSV41-FLASH-MODEL), while
the *indexer* key keeps the MXFP4 shape.  Sharing one dtype name would let a
deployment hand a table quantized one way to an engine expecting the other.

WHAT IS EXACT AND WHY IT IS UNAMBIGUOUS.  A dequantized element is

    value = decode_e2m1(code) * decode_e4m3fn(scale_code)

An E2M1 magnitude is ``M * 2**-1`` with ``M`` in {0,1,2,3,4,6,8,12}; an E4M3FN
magnitude is ``S * 2**E`` with ``S`` in 0..15 and ``E`` in [-9, 5].  The
product significand is therefore ``M * S <= 180``, at most eight significant
bits, and the product exponent lies in [-10, 4].  Every such product is
*exactly* representable in IEEE binary32, so rounding the exact rational
product once to E4M3FN and rounding a binary32 product to E4M3FN give the same
code for every one of the 256 x 16 input pairs -- there is no double-rounding
freedom in the contract and no intermediate width to declare.
:func:`prove_binary32_intermediate_is_exact` checks that claim over the whole
input space rather than asserting it.

The output format is E4M3FN with saturating round-to-nearest-even, the same
rule ``runtime.reference.formats.encode_e4m3fn_rne`` applies everywhere else in
this repository.  Saturation is *counted*, not an error: the architectural
destination format is finite-only FP8 and the vendor path likewise clamps.

WHAT THIS MODULE DOES NOT PIN.  The vendor's *forward* quantizer chooses the
per-group E4M3 scale; the pinned ``inference/model.py`` is not present in this
checkout (docs/SOURCES.md pins only its SHA-256), so
:func:`quantize_group_to_fp4` implements the documented ``amax / 6`` rule as a
*representative* generator of authentic-shaped code/scale pairs and is not an
evidence claim about vendor bit-exactness.  Nothing downstream of the
dequantize direction depends on it: the dequantize contract is fixed by the two
format definitions alone.

No host floating-point arithmetic participates.  Values are
:class:`fractions.Fraction`, so no tie decision inherits the host's rounding
mode.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction

from .formats import (
    NumericReferenceError,
    decode_e2m1,
    decode_e4m3fn,
    encode_e2m1_rne,
    encode_e4m3fn_rne,
)


#: The numeric contract this module defines, as published by the V4.1
#: capability (plan section 6.4).
CONTRACT = "fp4_e2m1_s16_e4m3_to_fp8_v1"

#: The V4.1 main-KV scale group.  A *default*, never a frozen bound: every
#: entry point takes ``group`` and the RTL takes it as an operand field.
DEFAULT_SCALE_GROUP = 16

#: ``head_dim`` of the pinned V4.1 text config, i.e. the element count of one
#: owned global KV latent.  Recorded for orientation only; no function here
#: rejects another extent.
V41_LATENT_ELEMENTS = 512

#: Largest finite E4M3FN magnitude; both NaN codes are 0x7f / 0xff.
E4M3FN_MAX = Fraction(448)

#: Largest finite E2M1 magnitude.
E2M1_MAX = Fraction(6)


class FP4KVReferenceError(ValueError):
    """Raised when an input code, scale, extent or group is illegal."""


@dataclass(frozen=True)
class DequantizedVector:
    """One dequantized vector plus everything an audit needs to re-derive it."""

    #: E4M3FN result codes, one per input element, in element order.
    fp8_codes: tuple[int, ...]
    #: Exact rational value of each *product*, before the E4M3FN rounding.
    exact_products: tuple[Fraction, ...]
    #: Exact rational value each result code decodes back to.
    fp8_values: tuple[Fraction, ...]
    #: Count of elements whose product exceeded the finite E4M3FN range.
    saturation_count: int
    #: Elements copied verbatim from the passthrough operand (trailing).
    passthrough_count: int
    #: The scale group actually applied.
    group: int


@dataclass(frozen=True)
class QuantizedVector:
    """Representative forward quantization, used to synthesize vectors."""

    e2m1_codes: tuple[int, ...]
    e4m3_scale_codes: tuple[int, ...]
    group: int


def _code(value: object, bits: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FP4KVReferenceError(f"{label} must be an unsigned {bits}-bit integer")
    if value < 0 or value >= 1 << bits:
        raise FP4KVReferenceError(f"{label} {value} is outside {bits} bits")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise FP4KVReferenceError(f"{label} must be a positive integer")
    return value


def scale_code_is_nonfinite(scale_code: int) -> bool:
    """True for the two E4M3FN NaN encodings, which poison a group."""

    _code(scale_code, 8, "E4M3FN scale code")
    return (scale_code & 0x7F) == 0x7F


def scale_value(scale_code: int) -> Fraction:
    """Exact value of one E4M3FN scale, rejecting the NaN encodings."""

    decoded = decode_e4m3fn(_code(scale_code, 8, "E4M3FN scale code"))
    if not decoded.finite or decoded.value is None:
        raise FP4KVReferenceError(
            f"E4M3FN scale code 0x{scale_code:02x} is NaN and poisons its group"
        )
    return decoded.value


def element_value(code: int) -> Fraction:
    """Exact value of one E2M1 element.  E2M1 has no exceptional encodings."""

    decoded = decode_e2m1(_code(code, 4, "E2M1 code"))
    if decoded.value is None:  # pragma: no cover - E2M1 is finite by construction
        raise FP4KVReferenceError("E2M1 decode produced no value")
    return decoded.value


def dequantize_element_to_fp8(code: int, scale_code: int) -> tuple[int, bool]:
    """Dequantize one element.  Returns its E4M3FN code and its saturation."""

    product = element_value(code) * scale_value(scale_code)
    quantized = encode_e4m3fn_rne(product)
    return quantized.code, quantized.saturated


def dequantize_group_to_fp8(
    codes: Sequence[int], scale_code: int
) -> tuple[tuple[int, ...], int]:
    """Dequantize one complete scale group.  Returns codes and saturations."""

    if not codes:
        raise FP4KVReferenceError("a scale group must contain at least one element")
    results: list[int] = []
    saturations = 0
    for code in codes:
        result, saturated = dequantize_element_to_fp8(code, scale_code)
        results.append(result)
        saturations += int(saturated)
    return tuple(results), saturations


def dequantize_to_fp8(
    codes: Sequence[int],
    scale_codes: Sequence[int],
    *,
    group: int = DEFAULT_SCALE_GROUP,
    passthrough: Sequence[int] = (),
) -> DequantizedVector:
    """Dequantize a whole latent under ``fp4_e2m1_s16_e4m3_to_fp8_v1``.

    ``codes`` are the E2M1 elements of the quantized region in element order.
    ``scale_codes`` carries one E4M3FN code per ``group`` of them.
    ``passthrough`` is the optional trailing region the IR's third DEQUANTIZE
    operand supplies already in FP8; it is copied verbatim, which is what the
    vendor's *partial* QDQ does to channels it does not quantize.

    The quantized region must be a whole number of groups: a partial group has
    no scale and the contract does not define one.
    """

    group = _positive(group, "group")
    quantized_count = len(codes)
    if quantized_count % group:
        raise FP4KVReferenceError(
            f"quantized extent {quantized_count} is not a whole number of "
            f"{group}-element groups"
        )
    expected_scales = quantized_count // group
    if len(scale_codes) != expected_scales:
        raise FP4KVReferenceError(
            f"{len(scale_codes)} scales supplied for {expected_scales} groups"
        )
    if quantized_count == 0 and not passthrough:
        raise FP4KVReferenceError("a dequantize must produce at least one element")

    products: list[Fraction] = []
    results: list[int] = []
    saturations = 0
    for index, code in enumerate(codes):
        scale = scale_codes[index // group]
        product = element_value(code) * scale_value(scale)
        quantized = encode_e4m3fn_rne(product)
        products.append(product)
        results.append(quantized.code)
        saturations += int(quantized.saturated)

    for index, code in enumerate(passthrough):
        _code(code, 8, f"passthrough FP8 code [{index}]")
        decoded = decode_e4m3fn(code)
        # A passthrough element is a byte copy, NaN payload included: the
        # vendor does not touch the channels it did not quantize, so neither
        # does this contract.  Its "product" is only defined when finite.
        products.append(decoded.value if decoded.value is not None else Fraction(0))
        results.append(code)

    values: list[Fraction] = []
    for code in results:
        decoded = decode_e4m3fn(code)
        values.append(decoded.value if decoded.value is not None else Fraction(0))

    return DequantizedVector(
        fp8_codes=tuple(results),
        exact_products=tuple(products),
        fp8_values=tuple(values),
        saturation_count=saturations,
        passthrough_count=len(passthrough),
        group=group,
    )


def dequantize_to_bf16_values(
    codes: Sequence[int],
    scale_codes: Sequence[int],
    *,
    group: int = DEFAULT_SCALE_GROUP,
) -> tuple[Fraction, ...]:
    """The exact products, i.e. what a BF16 reconstruction would round.

    The vendor reconstructs in BF16 in place; OpenTallas keeps the dequantized
    main KV in FP8 because that is what its attention datapath consumes.  Both
    round the *same* exact product, so this function exists to make the
    difference between the two destination formats auditable rather than
    implied: BF16 has eight significand bits and therefore represents every
    product exactly, so BF16 reconstruction loses nothing and the FP8 contract
    is the only lossy step.
    """

    group = _positive(group, "group")
    if len(codes) % group:
        raise FP4KVReferenceError("quantized extent is not a whole number of groups")
    if len(scale_codes) != len(codes) // group:
        raise FP4KVReferenceError("scale count does not match the group count")
    return tuple(
        element_value(code) * scale_value(scale_codes[index // group])
        for index, code in enumerate(codes)
    )


def quantize_group_to_fp4(values: Sequence[Fraction]) -> tuple[int, tuple[int, ...]]:
    """Representative forward quantization of one group.  NOT vendor-pinned.

    ``scale = amax / 6`` rounded to E4M3FN, then ``clamp(x / scale, +-6)``
    rounded to E2M1.  This follows the rule docs/SOURCES.md records for the
    V4.1 compressor, but the pinned ``model.py`` is absent from this checkout,
    so the exact scale-selection path (floor constant, reciprocal rounding) is
    *not* established here.  It is used only to generate code/scale pairs whose
    distribution resembles a real latent.
    """

    if not values:
        raise FP4KVReferenceError("a scale group must contain at least one value")
    amax = max(abs(Fraction(value)) for value in values)
    if amax == 0:
        return 0, tuple(0 for _ in values)
    scale_quantized = encode_e4m3fn_rne(amax / E2M1_MAX)
    scale = scale_value(scale_quantized.code)
    if scale == 0:
        # An underflowed scale cannot represent the group at all; fail closed
        # rather than emit codes that decode to zero.
        raise FP4KVReferenceError("group amax underflows every E4M3FN scale")
    codes: list[int] = []
    for value in values:
        quotient = Fraction(value) / scale
        clamped = max(-E2M1_MAX, min(E2M1_MAX, quotient))
        codes.append(encode_e2m1_rne(clamped).code)
    return scale_quantized.code, tuple(codes)


def quantize_to_fp4(
    values: Sequence[Fraction], *, group: int = DEFAULT_SCALE_GROUP
) -> QuantizedVector:
    """Representative forward quantization of a whole latent.  NOT vendor-pinned."""

    group = _positive(group, "group")
    if len(values) == 0 or len(values) % group:
        raise FP4KVReferenceError("extent is not a whole number of groups")
    codes: list[int] = []
    scales: list[int] = []
    for start in range(0, len(values), group):
        scale_code, group_codes = quantize_group_to_fp4(values[start : start + group])
        scales.append(scale_code)
        codes.extend(group_codes)
    return QuantizedVector(tuple(codes), tuple(scales), group)


def finite_scale_codes() -> tuple[int, ...]:
    """Every E4M3FN code that is a legal scale, in ascending code order."""

    return tuple(code for code in range(256) if not scale_code_is_nonfinite(code))


def prove_binary32_intermediate_is_exact() -> int:
    """Check the module docstring's exactness claim over the whole input space.

    Returns the number of (element, scale) pairs checked.  Every product is
    compared against its own binary32 round-trip: if any product needed more
    than 24 significand bits, the contract would have an intermediate-width
    degree of freedom and this would raise.
    """

    from .formats import decode_binary32, encode_binary32_rne

    checked = 0
    for code in range(16):
        element = element_value(code)
        for scale in finite_scale_codes():
            product = element * scale_value(scale)
            round_trip = decode_binary32(encode_binary32_rne(product))
            if round_trip.value != product:
                raise NumericReferenceError(
                    f"E2M1 0x{code:x} times E4M3FN 0x{scale:02x} is not exact "
                    "in binary32; the contract would be ambiguous"
                )
            checked += 1
    return checked


def contract_digest_inputs() -> Iterable[str]:
    """The identifiers an evidence record should bind this contract to."""

    return (
        CONTRACT,
        "SRC-DSV41-FLASH-MODEL",
        f"scale_group_default={DEFAULT_SCALE_GROUP}",
        "element_format=e2m1",
        "scale_format=e4m3fn",
        "result_format=e4m3fn",
        "rounding=round_to_nearest_even_saturating",
    )
