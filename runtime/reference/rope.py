"""Deterministic DeepSeek V4 Flash rotary-embedding semantics.

The pinned source forms adjacent binary32 complex pairs from the final 64
channels, multiplies them by a position-dependent unit phasor, and copies the
result back to BF16.  It uses the phasor conjugate for ``ROPE_INVERSE``.  Pure
sliding-window layers select base RoPE with theta 10,000; compressed layers
select theta 160,000 plus the committed YaRN interpolation.

The development implementation computes powers and ``torch.polar`` on the
active backend, so their final bits and complex contraction are not portable.
This reference freezes those otherwise moving choices: mathematical powers
are correctly rounded to binary32 before the source-ordered reciprocal and
YaRN operations; sine and cosine are correctly rounded from exact rational
intervals; complex products use separate binary32 RNE multiply and add/sub
boundaries; subnormals are preserved; arithmetic zero is canonical positive;
and an exceptional or overflowing transaction fails without a partial result.

This is functional evidence for the two rotary operators only.  It is not a
CUDA-equivalence, checkpoint-output, cycle, latency, or PPA claim.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from fractions import Fraction
from typing import Final, Literal, TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_multiply,
    decode_bf16,
    decode_binary32,
    encode_binary32_rne,
)


OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
ROPE_NUMERIC_PROFILE = "opentallas.deepseek_v4_rope_numeric.v1"

ROPE_DIMENSION = 64
ROPE_COMPLEX_PAIRS = ROPE_DIMENSION // 2
MAX_BATCH_SIZE = 4
MAX_HEAD_COUNT = 64
MAX_SEQUENCE_LENGTH = 65_536
MAX_POSITION = MAX_SEQUENCE_LENGTH - 1
SUPPORTED_HEAD_WIDTHS = frozenset({64, 128, 512})

BASE_ROPE_PROFILE = "base"
COMPRESSED_YARN_ROPE_PROFILE = "compressed_yarn"
RopeProfile: TypeAlias = Literal["base", "compressed_yarn"]

_BINARY32_ONE = 0x3F800000
_BINARY32_SIXTEEN = 0x41800000
_BINARY32_MAX_FINITE = 0x7F7FFFFF
_INITIAL_TRANSCENDENTAL_PRECISION = 96


class RopeReferenceError(ValueError):
    """Raised when a complete rotary transaction must be rejected."""


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise RopeReferenceError(f"{label} must be a sequence")
    return value


def _finite_bf16(code: object, label: str) -> int:
    if type(code) is not int or not 0 <= code < 1 << 16:
        raise RopeReferenceError(f"{label} must be a 16-bit BF16 encoding")
    decoded = decode_bf16(code)
    if not decoded.finite or decoded.value is None:
        raise RopeReferenceError(f"{label} must be finite BF16")
    return code


def _materialize_tensor(
    value: object,
) -> tuple[tuple[object, ...], tuple[int, ...]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise RopeReferenceError("input_bf16_codes must be a rank-3 or rank-4 sequence")

    def visit(
        current: object,
        label: str,
        depth: int,
    ) -> tuple[object, tuple[int, ...]]:
        if not isinstance(current, Sequence) or isinstance(
            current, (str, bytes, bytearray)
        ):
            return _finite_bf16(current, label), ()
        if depth >= 4:
            raise RopeReferenceError(
                "input_bf16_codes must be a rank-3 or rank-4 tensor"
            )
        raw = tuple(_sequence(current, label))
        if not raw:
            raise RopeReferenceError(f"{label} must not be empty")
        children: list[object] = []
        child_shape: tuple[int, ...] | None = None
        for index, child in enumerate(raw):
            materialized, shape = visit(child, f"{label}[{index}]", depth + 1)
            if child_shape is None:
                child_shape = shape
            elif shape != child_shape:
                raise RopeReferenceError(
                    "input_bf16_codes must be a rectangular tensor"
                )
            children.append(materialized)
        assert child_shape is not None
        return tuple(children), (len(children), *child_shape)

    materialized, shape = visit(value, "input_bf16_codes", 0)
    if type(materialized) is not tuple or len(shape) not in {3, 4}:
        raise RopeReferenceError("input_bf16_codes must be a rank-3 or rank-4 tensor")
    return materialized, shape


def _profile_name(value: object) -> RopeProfile:
    if type(value) is not str or value not in {
        BASE_ROPE_PROFILE,
        COMPRESSED_YARN_ROPE_PROFILE,
    }:
        raise RopeReferenceError("profile must be 'base' or 'compressed_yarn'")
    return value


def _position(value: object, label: str = "position") -> int:
    if type(value) is not int or not 0 <= value <= MAX_POSITION:
        raise RopeReferenceError(f"{label} must be an integer in [0, {MAX_POSITION}]")
    return value


def _negate_binary32(code: int) -> int:
    return 0 if code & 0x7FFFFFFF == 0 else code ^ 0x80000000


def _binary32_value(code: int) -> Fraction:
    decoded = decode_binary32(code)
    if not decoded.finite or decoded.value is None:  # pragma: no cover - internal
        raise RuntimeError("internal binary32 code unexpectedly became nonfinite")
    return decoded.value


@lru_cache(maxsize=64)
def _correctly_rounded_root_power(base: int, index: int) -> int:
    """Return CR32(``base ** (index / 32)``) without host ``pow``."""

    if index == 0:
        return _BINARY32_ONE
    target = base**index
    lower_code = 0
    upper_exclusive = _BINARY32_MAX_FINITE + 1
    while lower_code + 1 < upper_exclusive:
        candidate_code = (lower_code + upper_exclusive) // 2
        candidate = _binary32_value(candidate_code)
        if candidate**32 <= target:
            lower_code = candidate_code
        else:
            upper_exclusive = candidate_code

    lower = _binary32_value(lower_code)
    if lower**32 == target:
        return lower_code
    upper_code = lower_code + 1
    upper = _binary32_value(upper_code)
    midpoint = (lower + upper) / 2
    midpoint_power = midpoint**32
    if midpoint_power < target:
        return upper_code
    if midpoint_power > target:
        return lower_code
    return lower_code if lower_code & 1 == 0 else upper_code


@lru_cache(maxsize=2)
def _frequency_codes(profile: RopeProfile) -> tuple[int, ...]:
    base = 10_000 if profile == BASE_ROPE_PROFILE else 160_000
    try:
        frequencies = tuple(
            binary32_divide(
                _BINARY32_ONE,
                _correctly_rounded_root_power(base, index),
            )
            for index in range(ROPE_COMPLEX_PAIRS)
        )
        if profile == BASE_ROPE_PROFILE:
            return frequencies

        # The pinned Python correction calculation yields low=15 and high=25
        # for dim=64, theta=160000, original_seq_len=65536, beta_fast=32,
        # and beta_slow=1.  Preserve the subsequent source operation order.
        result: list[int] = []
        for index, frequency in enumerate(frequencies):
            ramp = encode_binary32_rne(
                max(Fraction(0), min(Fraction(1), Fraction(index - 15, 10)))
            )
            smooth = binary32_add(_BINARY32_ONE, _negate_binary32(ramp))
            one_minus_smooth = binary32_add(
                _BINARY32_ONE,
                _negate_binary32(smooth),
            )
            interpolated = binary32_multiply(
                binary32_divide(frequency, _BINARY32_SIXTEEN),
                one_minus_smooth,
            )
            original = binary32_multiply(frequency, smooth)
            result.append(binary32_add(interpolated, original))
        return tuple(result)
    except NumericReferenceError as exc:  # pragma: no cover - fixed constants
        raise RuntimeError("committed RoPE frequency profile is invalid") from exc


def rope_frequency_binary32_codes(
    *,
    profile: RopeProfile = BASE_ROPE_PROFILE,
) -> tuple[int, ...]:
    """Return the 32 frozen source-ordered binary32 angular frequencies."""

    return _frequency_codes(_profile_name(profile))


def _atan_reciprocal_interval(
    reciprocal: int,
    precision: int,
) -> tuple[Fraction, Fraction]:
    """Enclose ``atan(1/reciprocal)`` with consecutive exact partial sums."""

    threshold = Fraction(1, 1 << (precision + 16))
    square = reciprocal * reciprocal
    term = Fraction(1, reciprocal)
    partial = Fraction(0)
    index = 0
    while True:
        partial = partial + term if index & 1 == 0 else partial - term
        next_term = term * Fraction(2 * index + 1, (2 * index + 3) * square)
        next_partial = partial - next_term if index & 1 == 0 else partial + next_term
        if next_term <= threshold:
            return min(partial, next_partial), max(partial, next_partial)
        term = next_term
        index += 1


@lru_cache(maxsize=16)
def _pi_interval(precision: int) -> tuple[Fraction, Fraction]:
    """Machin-formula enclosure of mathematical pi."""

    five_lower, five_upper = _atan_reciprocal_interval(5, precision)
    two39_lower, two39_upper = _atan_reciprocal_interval(239, precision)
    return (
        16 * five_lower - 4 * two39_upper,
        16 * five_upper - 4 * two39_lower,
    )


def _sin_point_interval(
    value: Fraction,
    precision: int,
) -> tuple[Fraction, Fraction]:
    if value == 0:
        return Fraction(0), Fraction(0)
    threshold = Fraction(1, 1 << (precision + 16))
    square = value * value
    term = value
    partial = Fraction(0)
    index = 0
    while True:
        partial = partial + term if index & 1 == 0 else partial - term
        next_term = term * square / ((2 * index + 2) * (2 * index + 3))
        next_partial = partial - next_term if index & 1 == 0 else partial + next_term
        if next_term <= threshold:
            return min(partial, next_partial), max(partial, next_partial)
        term = next_term
        index += 1


def _cos_point_interval(
    value: Fraction,
    precision: int,
) -> tuple[Fraction, Fraction]:
    if value == 0:
        return Fraction(1), Fraction(1)
    threshold = Fraction(1, 1 << (precision + 16))
    square = value * value
    term = Fraction(1)
    partial = Fraction(0)
    index = 0
    while True:
        partial = partial + term if index & 1 == 0 else partial - term
        next_term = term * square / ((2 * index + 1) * (2 * index + 2))
        next_partial = partial - next_term if index & 1 == 0 else partial + next_term
        if next_term <= threshold:
            return min(partial, next_partial), max(partial, next_partial)
        term = next_term
        index += 1


def _signed_interval(
    interval: tuple[Fraction, Fraction],
    negative: bool,
) -> tuple[Fraction, Fraction]:
    if not negative:
        return interval
    lower, upper = interval
    return -upper, -lower


def _rounded_interval(interval: tuple[Fraction, Fraction]) -> int | None:
    lower, upper = interval
    lower_code = encode_binary32_rne(lower)
    upper_code = encode_binary32_rne(upper)
    return lower_code if lower_code == upper_code else None


@lru_cache(maxsize=65_536)
def _binary32_sin_cos_rne(angle_code: int) -> tuple[int, int]:
    angle = _binary32_value(angle_code)
    if angle < 0:  # pragma: no cover - position/frequency construction is positive
        raise RuntimeError("internal RoPE angle is negative")
    if angle == 0:
        return _BINARY32_ONE, 0

    precision = _INITIAL_TRANSCENDENTAL_PRECISION
    while True:
        pi_lower, pi_upper = _pi_interval(precision)
        half_lower = pi_lower / 2
        half_upper = pi_upper / 2
        quotient_lower = angle // half_upper
        quotient_upper = angle // half_lower
        if quotient_lower != quotient_upper:
            precision *= 2
            continue
        quadrant_count = int(quotient_lower)
        reduced_lower = angle - quadrant_count * half_upper
        reduced_upper = angle - quadrant_count * half_lower
        if reduced_lower < 0 or reduced_upper > half_upper:
            precision *= 2
            continue

        sin_lower, _ = _sin_point_interval(reduced_lower, precision)
        _, sin_upper = _sin_point_interval(reduced_upper, precision)
        cos_lower, _ = _cos_point_interval(reduced_upper, precision)
        _, cos_upper = _cos_point_interval(reduced_lower, precision)
        sine = (sin_lower, sin_upper)
        cosine = (cos_lower, cos_upper)
        quadrant = quadrant_count & 3
        if quadrant == 0:
            sine_interval = sine
            cosine_interval = cosine
        elif quadrant == 1:
            sine_interval = cosine
            cosine_interval = _signed_interval(sine, True)
        elif quadrant == 2:
            sine_interval = _signed_interval(sine, True)
            cosine_interval = _signed_interval(cosine, True)
        else:
            sine_interval = _signed_interval(cosine, True)
            cosine_interval = sine

        sine_code = _rounded_interval(sine_interval)
        cosine_code = _rounded_interval(cosine_interval)
        if sine_code is not None and cosine_code is not None:
            return cosine_code, sine_code
        precision *= 2


@lru_cache(maxsize=131_072)
def _phasors(position: int, profile: RopeProfile) -> tuple[tuple[int, int], ...]:
    if position == 0:
        return ((_BINARY32_ONE, 0),) * ROPE_COMPLEX_PAIRS
    position_code = encode_binary32_rne(position)
    result: list[tuple[int, int]] = []
    for frequency in _frequency_codes(profile):
        angle = binary32_multiply(position_code, frequency)
        result.append(_binary32_sin_cos_rne(angle))
    return tuple(result)


def rope_phasor_binary32_codes(
    position: int,
    *,
    profile: RopeProfile = BASE_ROPE_PROFILE,
) -> tuple[tuple[int, int], ...]:
    """Return source-ordered ``(cos, sin)`` binary32 pairs for one position."""

    return _phasors(_position(position), _profile_name(profile))


def _rotate_vector(
    vector: tuple[int, ...],
    phasors: tuple[tuple[int, int], ...],
    *,
    inverse: bool,
) -> tuple[int, ...]:
    prefix = vector[:-ROPE_DIMENSION]
    suffix = vector[-ROPE_DIMENSION:]
    output: list[int] = []
    try:
        for pair_index, (cosine, forward_sine) in enumerate(phasors):
            sine = _negate_binary32(forward_sine) if inverse else forward_sine
            real = suffix[2 * pair_index] << 16
            imaginary = suffix[2 * pair_index + 1] << 16
            real_output = binary32_add(
                binary32_multiply(real, cosine),
                _negate_binary32(binary32_multiply(imaginary, sine)),
            )
            imaginary_output = binary32_add(
                binary32_multiply(real, sine),
                binary32_multiply(imaginary, cosine),
            )
            for code in (real_output, imaginary_output):
                converted = binary32_bits_to_bf16_rne(code)
                if converted.saturated:
                    raise NumericReferenceError("rotary BF16 conversion overflowed")
                output.append(converted.code)
    except NumericReferenceError as exc:
        raise RopeReferenceError(f"rotary pair arithmetic failed: {exc}") from exc
    return prefix + tuple(output)


def apply_rotary_bf16(
    input_bf16_codes: object,
    start_position: int,
    *,
    profile: RopeProfile = BASE_ROPE_PROFILE,
    inverse: bool = False,
    rope_dimension: int = ROPE_DIMENSION,
) -> tuple[object, ...]:
    """Apply the exact pinned suffix rotation to a rank-3 or rank-4 tensor.

    Accepted layouts are ``[batch, sequence, width]`` and
    ``[batch, sequence, heads, width]``.  Width is one of the three official
    call-site widths 64, 128, or 512; only its final 64 channels rotate.
    ``start_position`` names sequence element zero, and positions must remain
    within the official 65,536-token reference window.
    """

    if type(inverse) is not bool:
        raise RopeReferenceError("inverse must be an exact boolean")
    if type(rope_dimension) is not int or rope_dimension != ROPE_DIMENSION:
        raise RopeReferenceError(
            f"rope_dimension must equal the pinned value {ROPE_DIMENSION}"
        )
    selected_profile = _profile_name(profile)
    start = _position(start_position, "start_position")
    tensor, shape = _materialize_tensor(input_bf16_codes)
    batch_size, sequence_length = shape[:2]
    if batch_size > MAX_BATCH_SIZE:
        raise RopeReferenceError(
            f"batch size must not exceed the pinned maximum {MAX_BATCH_SIZE}"
        )
    if start + sequence_length > MAX_SEQUENCE_LENGTH:
        raise RopeReferenceError(
            "start_position plus sequence length exceeds the official window"
        )
    if len(shape) == 4 and shape[2] > MAX_HEAD_COUNT:
        raise RopeReferenceError(
            f"head count must not exceed the pinned maximum {MAX_HEAD_COUNT}"
        )
    width = shape[-1]
    if width not in SUPPORTED_HEAD_WIDTHS:
        raise RopeReferenceError(
            "head width must be one of the pinned call-site widths "
            f"{sorted(SUPPORTED_HEAD_WIDTHS)}"
        )

    if len(shape) == 3:
        return tuple(
            tuple(
                _rotate_vector(
                    row,  # type: ignore[arg-type]
                    _phasors(start + sequence_index, selected_profile),
                    inverse=inverse,
                )
                for sequence_index, row in enumerate(batch)  # type: ignore[union-attr]
            )
            for batch in tensor
        )
    return tuple(
        tuple(
            tuple(
                _rotate_vector(
                    row,  # type: ignore[arg-type]
                    _phasors(start + sequence_index, selected_profile),
                    inverse=inverse,
                )
                for row in heads  # type: ignore[union-attr]
            )
            for sequence_index, heads in enumerate(batch)  # type: ignore[union-attr]
        )
        for batch in tensor
    )


def rope_apply_bf16(
    input_bf16_codes: object,
    start_position: int,
    *,
    profile: RopeProfile = BASE_ROPE_PROFILE,
    rope_dimension: int = ROPE_DIMENSION,
) -> tuple[object, ...]:
    """Execute pinned ``ROPE_APPLY``."""

    return apply_rotary_bf16(
        input_bf16_codes,
        start_position,
        profile=profile,
        inverse=False,
        rope_dimension=rope_dimension,
    )


def rope_inverse_bf16(
    input_bf16_codes: object,
    start_position: int,
    *,
    profile: RopeProfile = BASE_ROPE_PROFILE,
    rope_dimension: int = ROPE_DIMENSION,
) -> tuple[object, ...]:
    """Execute pinned ``ROPE_INVERSE`` with conjugate phasors."""

    return apply_rotary_bf16(
        input_bf16_codes,
        start_position,
        profile=profile,
        inverse=True,
        rope_dimension=rope_dimension,
    )


# Assert the content-pinned profile remains closed at import time without
# evaluating any position-dependent transcendental values.
_BASE_FREQUENCIES: Final = _frequency_codes(BASE_ROPE_PROFILE)
_COMPRESSED_FREQUENCIES: Final = _frequency_codes(COMPRESSED_YARN_ROPE_PROFILE)
if (
    len(_BASE_FREQUENCIES) != ROPE_COMPLEX_PAIRS
    or len(_COMPRESSED_FREQUENCIES) != ROPE_COMPLEX_PAIRS
):  # pragma: no cover - committed-module invariant
    raise RuntimeError("committed DeepSeek V4 RoPE frequency closure differs")


__all__ = [
    "BASE_ROPE_PROFILE",
    "COMPRESSED_YARN_ROPE_PROFILE",
    "INFERENCE_CONFIG_SHA256",
    "MAX_BATCH_SIZE",
    "MAX_HEAD_COUNT",
    "MAX_POSITION",
    "MAX_SEQUENCE_LENGTH",
    "MODEL_SOURCE_SHA256",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "ROPE_COMPLEX_PAIRS",
    "ROPE_DIMENSION",
    "ROPE_NUMERIC_PROFILE",
    "RopeProfile",
    "RopeReferenceError",
    "SUPPORTED_HEAD_WIDTHS",
    "apply_rotary_bf16",
    "rope_apply_bf16",
    "rope_frequency_binary32_codes",
    "rope_inverse_bf16",
    "rope_phasor_binary32_codes",
]
