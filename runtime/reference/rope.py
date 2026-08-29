"""Deterministic DeepSeek V4 Flash rotary-embedding semantics.

The pinned source forms adjacent binary32 complex pairs from the final 64
channels, multiplies them by a position-dependent unit phasor, and copies the
result back to BF16.  It uses the phasor conjugate for ``ROPE_INVERSE``.  Pure
sliding-window layers select base RoPE with theta 10,000; compressed layers
select theta 160,000 plus the committed YaRN interpolation.

Ordinary query, KV, and attention-output calls consume consecutive phasor
positions.  Compressor prefill instead slices the same table with its released
ratio-four or ratio-128 stride; compressor decode supplies the absolute
``start_pos + 1 - ratio`` row.  This module exposes those table-application
semantics, but does not claim that a compiler or graph caller selected the
right schedule.

The development implementation computes powers and ``torch.polar`` on the
active backend, so their final bits and complex contraction are not portable.
This reference freezes those otherwise moving choices: mathematical powers
are correctly rounded to binary32 before the source-ordered reciprocal and
YaRN operations; sine and cosine are correctly rounded from exact rational
intervals; complex products use separate binary32 RNE multiply and add/sub
boundaries; subnormals are preserved; arithmetic zero is canonical positive;
and an exceptional or overflowing transaction fails without a partial result.
Logical counters reconcile only the application transaction; the source's
one-time phasor-table construction is outside them.

This is functional evidence for the two rotary operators only.  It is not a
Torch/CUDA-equivalence, checkpoint or service execution, graph-position
binding, cycle, latency, bandwidth, energy, area, routing, or PPA claim.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
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
GENERATE_SOURCE_SHA256 = (
    "775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812"
)
ROPE_NUMERIC_PROFILE = "opentallas.deepseek_v4_rope_numeric.v2"

ROPE_DIMENSION = 64
ROPE_COMPLEX_PAIRS = ROPE_DIMENSION // 2
MAX_BATCH_SIZE = 4
MAX_HEAD_COUNT = 64
BASE_ROPE_THETA = 10_000
COMPRESSED_ROPE_THETA = 160_000
YARN_ORIGINAL_SEQUENCE_LENGTH = 65_536
YARN_FACTOR = 16
YARN_BETA_FAST = 32
YARN_BETA_SLOW = 1
YARN_CORRECTION_LOW = 15
YARN_CORRECTION_HIGH = 25
MAX_SEQUENCE_LENGTH = YARN_ORIGINAL_SEQUENCE_LENGTH
MAX_POSITION = MAX_SEQUENCE_LENGTH - 1
SUPPORTED_HEAD_WIDTHS = frozenset({64, 128, 512})
SUPPORTED_POSITION_STRIDES = frozenset({1, 4, 128})

BASE_ROPE_PROFILE = "base"
COMPRESSED_YARN_ROPE_PROFILE = "compressed_yarn"
RopeProfile: TypeAlias = Literal["base", "compressed_yarn"]
BF16Vector: TypeAlias = tuple[int, ...]
BF16Rank3: TypeAlias = tuple[tuple[BF16Vector, ...], ...]
BF16Rank4: TypeAlias = tuple[tuple[tuple[BF16Vector, ...], ...], ...]
BF16RotaryTensor: TypeAlias = BF16Rank3 | BF16Rank4

EXCLUDED_CLAIMS = (
    "active_backend_torch_polar_bit_equivalence",
    "cuda_or_accelerator_kernel_equivalence",
    "checkpoint_execution",
    "service_engine_execution",
    "compiler_or_graph_position_binding",
    "cycles_latency_throughput_bandwidth_energy_area_density_routing_ppa",
    "end_to_end_model_execution",
)

_BINARY32_ONE = 0x3F800000
_BINARY32_YARN_FACTOR = 0x41800000
_BINARY32_MAX_FINITE = 0x7F7FFFFF
_INITIAL_TRANSCENDENTAL_PRECISION = 96


class RopeReferenceError(ValueError):
    """Raised when a complete rotary transaction must be rejected."""


@dataclass(frozen=True)
class RopeCounters:
    """Exact logical work for one committed rotary tensor transaction."""

    tensor_rank: int
    batch_count: int
    sequence_length: int
    head_count: int
    head_width: int
    rope_dimension: int
    complex_pairs_per_vector: int
    position_stride: int
    rotated_vector_count: int
    input_bf16_values: int
    prefix_bf16_values_preserved: int
    rotated_input_bf16_values: int
    logical_phasor_binary32_values_read: int
    bf16_to_binary32_exact_widenings: int
    binary32_multiplications: int
    binary32_additions_or_subtractions: int
    conjugated_sine_binary32_values: int
    binary32_to_bf16_conversions: int
    output_bf16_values: int
    transaction_commits: int

    def __post_init__(self) -> None:
        """Reject forged reconciliation records at the public constructor."""

        _validate_rope_counters(self)


@dataclass(frozen=True)
class RopeResult:
    """Immutable output and logical reconciliation data for one direction."""

    numeric_profile: str
    profile: RopeProfile
    inverse: bool
    start_position: int
    last_position: int
    position_stride: int
    output_bf16_codes: BF16RotaryTensor
    counters: RopeCounters

    def __post_init__(self) -> None:
        """Require a complete immutable result that reconciles to its counters."""

        _validate_rope_result(self)


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise RopeReferenceError(f"{label} must be an exact list or tuple")
    return value


def _finite_bf16(code: object, label: str) -> int:
    if type(code) is not int or not 0 <= code < 1 << 16:
        raise RopeReferenceError(f"{label} must be a 16-bit BF16 encoding")
    decoded = decode_bf16(code)
    if not decoded.finite or decoded.value is None:
        raise RopeReferenceError(f"{label} must be finite BF16")
    return code


def _counter_integer(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise RopeReferenceError(f"{label} must be a nonnegative exact integer")
    return value


def _validate_rope_counters(counters: RopeCounters) -> None:
    """Validate every scalar and formula in a public counter record."""

    if type(counters) is not RopeCounters:
        raise RopeReferenceError("counter record must be an exact RopeCounters")
    names = (
        "tensor_rank",
        "batch_count",
        "sequence_length",
        "head_count",
        "head_width",
        "rope_dimension",
        "complex_pairs_per_vector",
        "position_stride",
        "rotated_vector_count",
        "input_bf16_values",
        "prefix_bf16_values_preserved",
        "rotated_input_bf16_values",
        "logical_phasor_binary32_values_read",
        "bf16_to_binary32_exact_widenings",
        "binary32_multiplications",
        "binary32_additions_or_subtractions",
        "conjugated_sine_binary32_values",
        "binary32_to_bf16_conversions",
        "output_bf16_values",
        "transaction_commits",
    )
    values = {
        name: _counter_integer(getattr(counters, name), f"counters.{name}")
        for name in names
    }
    rank = values["tensor_rank"]
    batch_count = values["batch_count"]
    sequence_length = values["sequence_length"]
    head_count = values["head_count"]
    head_width = values["head_width"]
    stride = values["position_stride"]
    if rank not in {3, 4}:
        raise RopeReferenceError("counters.tensor_rank must be exactly 3 or 4")
    if not 1 <= batch_count <= MAX_BATCH_SIZE:
        raise RopeReferenceError(
            f"counters.batch_count must be in [1, {MAX_BATCH_SIZE}]"
        )
    if not 1 <= sequence_length <= MAX_SEQUENCE_LENGTH:
        raise RopeReferenceError(
            "counters.sequence_length must be in the pinned table bounds"
        )
    if rank == 3 and head_count != 1:
        raise RopeReferenceError("rank-3 counters must have head_count equal to 1")
    if rank == 4 and not 1 <= head_count <= MAX_HEAD_COUNT:
        raise RopeReferenceError(
            f"rank-4 counters.head_count must be in [1, {MAX_HEAD_COUNT}]"
        )
    if head_width not in SUPPORTED_HEAD_WIDTHS:
        raise RopeReferenceError(
            "counters.head_width must be an official RoPE call-site width"
        )
    if values["rope_dimension"] != ROPE_DIMENSION:
        raise RopeReferenceError(f"counters.rope_dimension must equal {ROPE_DIMENSION}")
    if values["complex_pairs_per_vector"] != ROPE_COMPLEX_PAIRS:
        raise RopeReferenceError(
            f"counters.complex_pairs_per_vector must equal {ROPE_COMPLEX_PAIRS}"
        )
    if stride not in SUPPORTED_POSITION_STRIDES:
        raise RopeReferenceError(
            "counters.position_stride must be exactly 1, 4, or 128"
        )

    vector_count = batch_count * sequence_length * head_count
    total_values = vector_count * head_width
    rotated_values = vector_count * ROPE_DIMENSION
    pair_count = vector_count * ROPE_COMPLEX_PAIRS
    expected = {
        "rotated_vector_count": vector_count,
        "input_bf16_values": total_values,
        "prefix_bf16_values_preserved": (head_width - ROPE_DIMENSION) * vector_count,
        "rotated_input_bf16_values": rotated_values,
        "logical_phasor_binary32_values_read": pair_count * 2,
        "bf16_to_binary32_exact_widenings": rotated_values,
        "binary32_multiplications": pair_count * 4,
        "binary32_additions_or_subtractions": pair_count * 2,
        "binary32_to_bf16_conversions": rotated_values,
        "output_bf16_values": total_values,
        "transaction_commits": 1,
    }
    for name, expected_value in expected.items():
        if values[name] != expected_value:
            raise RopeReferenceError(
                f"counters.{name} does not reconcile to the tensor dimensions"
            )
    allowed_conjugations = {0, sequence_length * ROPE_COMPLEX_PAIRS}
    if values["conjugated_sine_binary32_values"] not in allowed_conjugations:
        raise RopeReferenceError(
            "counters.conjugated_sine_binary32_values does not reconcile to "
            "a forward or inverse transaction"
        )


def _immutable_result_shape(value: object) -> tuple[int, ...]:
    """Validate and shape an exact-tuple BF16 tensor without accepting aliases."""

    if type(value) is not tuple:
        raise RopeReferenceError(
            "output_bf16_codes must be a deeply immutable exact-tuple tensor"
        )

    def visit(current: object, label: str, depth: int) -> tuple[int, ...]:
        if type(current) is not tuple:
            if isinstance(current, Sequence) and not isinstance(
                current,
                (str, bytes),
            ):
                raise RopeReferenceError(
                    "output_bf16_codes must be deeply immutable exact tuples"
                )
            _finite_bf16(current, label)
            return ()
        if depth >= 4:
            raise RopeReferenceError(
                "output_bf16_codes must be a rank-3 or rank-4 tensor"
            )
        if not current:
            raise RopeReferenceError(f"{label} must not be empty")
        child_shape: tuple[int, ...] | None = None
        for index, child in enumerate(current):
            shape = visit(child, f"{label}[{index}]", depth + 1)
            if child_shape is None:
                child_shape = shape
            elif shape != child_shape:
                raise RopeReferenceError(
                    "output_bf16_codes must be a rectangular tensor"
                )
        assert child_shape is not None
        return (len(current), *child_shape)

    shape = visit(value, "output_bf16_codes", 0)
    if len(shape) not in {3, 4}:
        raise RopeReferenceError("output_bf16_codes must be a rank-3 or rank-4 tensor")
    return shape


def _validate_rope_result(result: RopeResult) -> None:
    """Validate public result authority independently of the evaluator path."""

    if type(result) is not RopeResult:
        raise RopeReferenceError("result record must be an exact RopeResult")
    if type(result.numeric_profile) is not str or (
        result.numeric_profile != ROPE_NUMERIC_PROFILE
    ):
        raise RopeReferenceError(f"numeric_profile must equal {ROPE_NUMERIC_PROFILE!r}")
    profile = _profile_name(result.profile)
    if type(result.inverse) is not bool:
        raise RopeReferenceError("inverse must be an exact boolean")
    start = _position(result.start_position, "start_position")
    last = _position(result.last_position, "last_position")
    stride = _position_stride(result.position_stride)
    if stride != 1 and (profile != COMPRESSED_YARN_ROPE_PROFILE or result.inverse):
        raise RopeReferenceError(
            "nonunit result position_stride is admitted only for forward "
            "compressed_yarn compressor-prefill rotation"
        )
    if type(result.counters) is not RopeCounters:
        raise RopeReferenceError("counters must be an exact RopeCounters record")
    _validate_rope_counters(result.counters)
    shape = _immutable_result_shape(result.output_bf16_codes)
    batch_count, sequence_length = shape[:2]
    if batch_count > MAX_BATCH_SIZE:
        raise RopeReferenceError(f"output batch size must not exceed {MAX_BATCH_SIZE}")
    if sequence_length > MAX_SEQUENCE_LENGTH:
        raise RopeReferenceError(
            "output sequence length exceeds the pinned position table"
        )
    head_count = 1 if len(shape) == 3 else shape[2]
    if len(shape) == 4 and head_count > MAX_HEAD_COUNT:
        raise RopeReferenceError(f"output head count must not exceed {MAX_HEAD_COUNT}")
    head_width = shape[-1]
    if head_width not in SUPPORTED_HEAD_WIDTHS:
        raise RopeReferenceError(
            "output head width must be one of the official RoPE call-site widths"
        )
    expected_last = start + (sequence_length - 1) * stride
    if expected_last > MAX_POSITION or last != expected_last:
        raise RopeReferenceError(
            "last_position does not reconcile to start, sequence, and stride"
        )
    counters = result.counters
    dimensions = (
        counters.tensor_rank,
        counters.batch_count,
        counters.sequence_length,
        counters.head_count,
        counters.head_width,
        counters.position_stride,
    )
    expected_dimensions = (
        len(shape),
        batch_count,
        sequence_length,
        head_count,
        head_width,
        stride,
    )
    if dimensions != expected_dimensions:
        raise RopeReferenceError(
            "counters dimensions do not reconcile to output_bf16_codes"
        )
    expected_conjugations = (
        sequence_length * ROPE_COMPLEX_PAIRS if result.inverse else 0
    )
    if counters.conjugated_sine_binary32_values != expected_conjugations:
        raise RopeReferenceError(
            "inverse direction does not reconcile to the conjugation counter"
        )


def _materialize_tensor(
    value: object,
) -> tuple[BF16RotaryTensor, tuple[int, ...]]:
    if type(value) not in {list, tuple}:
        raise RopeReferenceError(
            "input_bf16_codes must be a rank-3 or rank-4 exact list or tuple"
        )

    def visit(
        current: object,
        label: str,
        depth: int,
    ) -> tuple[object, tuple[int, ...]]:
        if type(current) not in {list, tuple}:
            if isinstance(current, Sequence) and not isinstance(
                current,
                (str, bytes, bytearray),
            ):
                raise RopeReferenceError(f"{label} must be an exact list or tuple")
            return _finite_bf16(current, label), ()
        if depth >= 4:
            raise RopeReferenceError(
                "input_bf16_codes must be a rank-3 or rank-4 tensor"
            )
        raw = _sequence(current, label)
        if not raw:
            raise RopeReferenceError(f"{label} must not be empty")
        if depth == 0 and len(raw) > MAX_BATCH_SIZE:
            raise RopeReferenceError(
                f"batch size must not exceed the pinned maximum {MAX_BATCH_SIZE}"
            )
        if depth == 1 and len(raw) > MAX_SEQUENCE_LENGTH:
            raise RopeReferenceError(
                "sequence length exceeds the pinned 65,536-position table"
            )
        if depth in {2, 3} and len(raw) > max(SUPPORTED_HEAD_WIDTHS):
            raise RopeReferenceError(
                "input_bf16_codes has an axis larger than the pinned head width"
            )
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
    return materialized, shape  # type: ignore[return-value]


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


def _position_stride(value: object) -> int:
    if type(value) is not int or value not in SUPPORTED_POSITION_STRIDES:
        raise RopeReferenceError("position_stride must be exactly 1, 4, or 128")
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
    base = BASE_ROPE_THETA if profile == BASE_ROPE_PROFILE else COMPRESSED_ROPE_THETA
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
        # for the constants above.  Preserve the subsequent source operation
        # order after that host-side range selection.
        result: list[int] = []
        for index, frequency in enumerate(frequencies):
            ramp = encode_binary32_rne(
                max(
                    Fraction(0),
                    min(
                        Fraction(1),
                        Fraction(
                            index - YARN_CORRECTION_LOW,
                            YARN_CORRECTION_HIGH - YARN_CORRECTION_LOW,
                        ),
                    ),
                )
            )
            smooth = binary32_add(_BINARY32_ONE, _negate_binary32(ramp))
            one_minus_smooth = binary32_add(
                _BINARY32_ONE,
                _negate_binary32(smooth),
            )
            interpolated = binary32_multiply(
                binary32_divide(frequency, _BINARY32_YARN_FACTOR),
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


def apply_rotary_bf16_result(
    input_bf16_codes: object,
    start_position: int,
    *,
    profile: RopeProfile = BASE_ROPE_PROFILE,
    inverse: bool = False,
    rope_dimension: int = ROPE_DIMENSION,
    position_stride: int = 1,
) -> RopeResult:
    """Evaluate one exact, atomic suffix-rotation transaction.

    Accepted layouts are ``[batch, sequence, width]`` and
    ``[batch, sequence, heads, width]``.  Width is one of the three official
    call-site widths 64, 128, or 512; only its final 64 channels rotate.
    ``start_position`` names sequence element zero.  A stride of one covers
    ordinary query/KV/output calls; strides four and 128 cover the official
    compressor-prefill frequency slices.  Compressor decode must supply its
    already adjusted absolute position.  Every sampled position must remain
    within the pinned 65,536-position interactive table.

    Counters cover tensor application only.  The source constructs its phasor
    table once at model initialization, so coefficient generation is not
    charged to each application transaction.
    """

    if type(inverse) is not bool:
        raise RopeReferenceError("inverse must be an exact boolean")
    if type(rope_dimension) is not int or rope_dimension != ROPE_DIMENSION:
        raise RopeReferenceError(
            f"rope_dimension must equal the pinned value {ROPE_DIMENSION}"
        )
    selected_profile = _profile_name(profile)
    start = _position(start_position, "start_position")
    stride = _position_stride(position_stride)
    if stride != 1 and (selected_profile != COMPRESSED_YARN_ROPE_PROFILE or inverse):
        raise RopeReferenceError(
            "nonunit position_stride is admitted only for forward "
            "compressed_yarn compressor-prefill rotation"
        )
    tensor, shape = _materialize_tensor(input_bf16_codes)
    batch_size, sequence_length = shape[:2]
    if batch_size > MAX_BATCH_SIZE:
        raise RopeReferenceError(
            f"batch size must not exceed the pinned maximum {MAX_BATCH_SIZE}"
        )
    last_position = start + (sequence_length - 1) * stride
    if last_position > MAX_POSITION:
        raise RopeReferenceError(
            "sampled rotary positions exceed the pinned 65,536-position table"
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
        output: BF16RotaryTensor = tuple(
            tuple(
                _rotate_vector(
                    row,  # type: ignore[arg-type]
                    _phasors(start + sequence_index * stride, selected_profile),
                    inverse=inverse,
                )
                for sequence_index, row in enumerate(batch)  # type: ignore[union-attr]
            )
            for batch in tensor
        )
        head_count = 1
    else:
        output = tuple(
            tuple(
                tuple(
                    _rotate_vector(
                        row,  # type: ignore[arg-type]
                        _phasors(
                            start + sequence_index * stride,
                            selected_profile,
                        ),
                        inverse=inverse,
                    )
                    for row in heads  # type: ignore[union-attr]
                )
                for sequence_index, heads in enumerate(batch)  # type: ignore[union-attr]
            )
            for batch in tensor
        )
        head_count = shape[2]

    vector_count = batch_size * sequence_length * head_count
    total_values = vector_count * width
    rotated_values = vector_count * ROPE_DIMENSION
    pair_count = vector_count * ROPE_COMPLEX_PAIRS
    counters = RopeCounters(
        tensor_rank=len(shape),
        batch_count=batch_size,
        sequence_length=sequence_length,
        head_count=head_count,
        head_width=width,
        rope_dimension=ROPE_DIMENSION,
        complex_pairs_per_vector=ROPE_COMPLEX_PAIRS,
        position_stride=stride,
        rotated_vector_count=vector_count,
        input_bf16_values=total_values,
        prefix_bf16_values_preserved=(width - ROPE_DIMENSION) * vector_count,
        rotated_input_bf16_values=rotated_values,
        logical_phasor_binary32_values_read=pair_count * 2,
        bf16_to_binary32_exact_widenings=rotated_values,
        binary32_multiplications=pair_count * 4,
        binary32_additions_or_subtractions=pair_count * 2,
        conjugated_sine_binary32_values=(
            sequence_length * ROPE_COMPLEX_PAIRS if inverse else 0
        ),
        binary32_to_bf16_conversions=rotated_values,
        output_bf16_values=total_values,
        transaction_commits=1,
    )
    return RopeResult(
        numeric_profile=ROPE_NUMERIC_PROFILE,
        profile=selected_profile,
        inverse=inverse,
        start_position=start,
        last_position=last_position,
        position_stride=stride,
        output_bf16_codes=output,
        counters=counters,
    )


def apply_rotary_bf16(
    input_bf16_codes: object,
    start_position: int,
    *,
    profile: RopeProfile = BASE_ROPE_PROFILE,
    inverse: bool = False,
    rope_dimension: int = ROPE_DIMENSION,
    position_stride: int = 1,
) -> BF16RotaryTensor:
    """Return only the tensor output of :func:`apply_rotary_bf16_result`."""

    return apply_rotary_bf16_result(
        input_bf16_codes,
        start_position,
        profile=profile,
        inverse=inverse,
        rope_dimension=rope_dimension,
        position_stride=position_stride,
    ).output_bf16_codes


def rope_apply_bf16(
    input_bf16_codes: object,
    start_position: int,
    *,
    profile: RopeProfile = BASE_ROPE_PROFILE,
    rope_dimension: int = ROPE_DIMENSION,
    position_stride: int = 1,
) -> BF16RotaryTensor:
    """Execute pinned ``ROPE_APPLY``."""

    return apply_rotary_bf16(
        input_bf16_codes,
        start_position,
        profile=profile,
        inverse=False,
        rope_dimension=rope_dimension,
        position_stride=position_stride,
    )


def rope_inverse_bf16(
    input_bf16_codes: object,
    start_position: int,
    *,
    profile: RopeProfile = BASE_ROPE_PROFILE,
    rope_dimension: int = ROPE_DIMENSION,
    position_stride: int = 1,
) -> BF16RotaryTensor:
    """Execute pinned ``ROPE_INVERSE`` with conjugate phasors."""

    return apply_rotary_bf16(
        input_bf16_codes,
        start_position,
        profile=profile,
        inverse=True,
        rope_dimension=rope_dimension,
        position_stride=position_stride,
    )


# Assert the content-pinned profile remains closed at import time without
# evaluating any position-dependent transcendental values.
_BASE_FREQUENCIES: Final = _frequency_codes(BASE_ROPE_PROFILE)
_COMPRESSED_FREQUENCIES: Final = _frequency_codes(COMPRESSED_YARN_ROPE_PROFILE)
if (
    len(_BASE_FREQUENCIES) != ROPE_COMPLEX_PAIRS
    or len(_COMPRESSED_FREQUENCIES) != ROPE_COMPLEX_PAIRS
    or _BINARY32_YARN_FACTOR != encode_binary32_rne(YARN_FACTOR)
):  # pragma: no cover - committed-module invariant
    raise RuntimeError("committed DeepSeek V4 RoPE frequency closure differs")


__all__ = [
    "BASE_ROPE_PROFILE",
    "BASE_ROPE_THETA",
    "BF16Rank3",
    "BF16Rank4",
    "BF16RotaryTensor",
    "BF16Vector",
    "COMPRESSED_YARN_ROPE_PROFILE",
    "COMPRESSED_ROPE_THETA",
    "EXCLUDED_CLAIMS",
    "GENERATE_SOURCE_SHA256",
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
    "RopeCounters",
    "RopeProfile",
    "RopeReferenceError",
    "RopeResult",
    "SUPPORTED_HEAD_WIDTHS",
    "SUPPORTED_POSITION_STRIDES",
    "YARN_BETA_FAST",
    "YARN_BETA_SLOW",
    "YARN_CORRECTION_HIGH",
    "YARN_CORRECTION_LOW",
    "YARN_FACTOR",
    "YARN_ORIGINAL_SEQUENCE_LENGTH",
    "apply_rotary_bf16",
    "apply_rotary_bf16_result",
    "rope_apply_bf16",
    "rope_frequency_binary32_codes",
    "rope_inverse_bf16",
    "rope_phasor_binary32_codes",
]
