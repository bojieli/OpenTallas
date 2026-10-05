"""Independent service arithmetic for DeepSeek V4 ``HC_POST``.

This module implements SPEC-NUM 1.1 NUM-6.7 directly from BF16 and binary32
encodings.  It intentionally does not import the runtime reference lane or any
other service numeric implementation: the binary32 operations, canonical tree,
and BF16 conversion are local so the service result is an independent lane.

The reusable primitive accepts positive rectangular batch, sequence, and hidden
dimensions, with both HC axes equal to the explicit positive ``hc_multiplier``.
The pinned DeepSeek Flash/Pro profile uses ``H = 4`` and ``D = 4096``;
``execute_pinned_hc_post`` below binds those values and the command token bound
before calling the generic primitive.  This module is not itself an unbounded
external service endpoint.

NUM-6.7 does not freeze counter identifiers.  ``logical_counters`` therefore
reports exact, shape-derived service-schedule counts for reconciliation without
claiming an additional architectural counter namespace.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias


HC_POST_PINNED_HC_MULTIPLIER = 4
HC_POST_PINNED_HIDDEN_WIDTH = 4096
HC_POST_MAX_TOKENS_PER_COMMAND = 4

BF16Vector: TypeAlias = tuple[int, ...]
BF16Batch: TypeAlias = tuple[tuple[BF16Vector, ...], ...]
BF16HCBatch: TypeAlias = tuple[tuple[tuple[BF16Vector, ...], ...], ...]
F32Vector: TypeAlias = tuple[int, ...]
F32HCBatch: TypeAlias = tuple[tuple[tuple[F32Vector, ...], ...], ...]
F32HCProductBatch: TypeAlias = tuple[tuple[tuple[tuple[F32Vector, ...], ...], ...], ...]


class HCPostServiceNumericError(ValueError):
    """Raised when an entire HC_POST command must be poisoned."""


@dataclass(frozen=True)
class HCPostServiceResult:
    """Atomic architectural result, exact intermediates, and service counts."""

    output_codes: BF16HCBatch
    output_saturation_count: int
    branch_codes: BF16Batch
    residual_codes: BF16HCBatch
    branch_product_codes: F32HCBatch
    residual_product_codes: F32HCProductBatch
    residual_sum_codes: F32HCBatch
    output_binary32_codes: F32HCBatch
    logical_counters: Mapping[str, int]

    @property
    def semantic_counters(self) -> Mapping[str, int]:
        """Alias emphasizing that these are arithmetic, not physical, counts."""

        return self.logical_counters


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise HCPostServiceNumericError(f"{label} must be a sequence")
    return value


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise HCPostServiceNumericError(f"{label} must be an integer >= 1")
    return value


def _validate_unsigned_code(value: object, bits: int, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < 1 << bits
    ):
        raise HCPostServiceNumericError(
            f"{label} must be an unsigned {bits}-bit encoding"
        )
    return value


def _validate_finite_bf16(value: object, label: str) -> int:
    code = _validate_unsigned_code(value, 16, label)
    if code & 0x7F80 == 0x7F80:
        raise HCPostServiceNumericError(f"{label} must be finite BF16")
    return code


def _validate_finite_binary32(value: object, label: str) -> int:
    code = _validate_unsigned_code(value, 32, label)
    if code & 0x7F800000 == 0x7F800000:
        raise HCPostServiceNumericError(f"{label} must be finite binary32")
    # Signed zero canonicalizes at its first checked arithmetic boundary.
    return 0 if code & 0x7FFFFFFF == 0 else code


def _widen_bf16(code: int) -> int:
    """Widen finite BF16 exactly and canonicalize either zero sign positive."""

    return 0 if code & 0x7FFF == 0 else code << 16


def _validate_branch(value: object) -> BF16Batch:
    label = "branch_bf16_codes"
    raw_batches = _sequence(value, label)
    if not raw_batches:
        raise HCPostServiceNumericError(f"{label} must contain at least one batch")

    sequence_length: int | None = None
    hidden_width: int | None = None
    batches: list[tuple[BF16Vector, ...]] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence_label = f"{label}[{batch_index}]"
        sequence = _sequence(raw_sequence, sequence_label)
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise HCPostServiceNumericError(
                    f"{label} must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise HCPostServiceNumericError(
                f"{label} must be a rectangular rank-3 tensor"
            )

        output_sequence: list[BF16Vector] = []
        for position, raw_vector in enumerate(sequence):
            vector_label = f"{sequence_label}[{position}]"
            vector = _sequence(raw_vector, vector_label)
            if hidden_width is None:
                hidden_width = len(vector)
                if hidden_width == 0:
                    raise HCPostServiceNumericError(
                        f"{label} vectors must contain at least one BF16 value"
                    )
            elif len(vector) != hidden_width:
                raise HCPostServiceNumericError(
                    f"{label} must be a rectangular rank-3 tensor"
                )
            output_sequence.append(
                tuple(
                    _validate_finite_bf16(
                        code,
                        f"{vector_label}[{column}]",
                    )
                    for column, code in enumerate(vector)
                )
            )
        batches.append(tuple(output_sequence))
    return tuple(batches)


def _validate_residual(
    value: object,
    *,
    batch_size: int,
    sequence_length: int,
    hidden_width: int,
    hc_multiplier: int,
) -> BF16HCBatch:
    label = "residual_bf16_codes"
    raw_batches = _sequence(value, label)
    if len(raw_batches) != batch_size:
        raise HCPostServiceNumericError(f"{label} batch dimension must match branch")

    batches: list[tuple[tuple[BF16Vector, ...], ...]] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence_label = f"{label}[{batch_index}]"
        sequence = _sequence(raw_sequence, sequence_label)
        if len(sequence) != sequence_length:
            raise HCPostServiceNumericError(
                f"{label} sequence dimension must match branch"
            )
        output_sequence: list[tuple[BF16Vector, ...]] = []
        for position, raw_sources in enumerate(sequence):
            sources_label = f"{sequence_label}[{position}]"
            sources = _sequence(raw_sources, sources_label)
            if len(sources) != hc_multiplier:
                raise HCPostServiceNumericError(
                    f"{label} source HC dimension must equal hc_multiplier"
                )
            output_sources: list[BF16Vector] = []
            for source, raw_vector in enumerate(sources):
                vector_label = f"{sources_label}[{source}]"
                vector = _sequence(raw_vector, vector_label)
                if len(vector) != hidden_width:
                    raise HCPostServiceNumericError(
                        f"{label} hidden width must match branch"
                    )
                output_sources.append(
                    tuple(
                        _validate_finite_bf16(
                            code,
                            f"{vector_label}[{column}]",
                        )
                        for column, code in enumerate(vector)
                    )
                )
            output_sequence.append(tuple(output_sources))
        batches.append(tuple(output_sequence))
    return tuple(batches)


def _validate_post(
    value: object,
    *,
    batch_size: int,
    sequence_length: int,
    hc_multiplier: int,
) -> tuple[tuple[F32Vector, ...], ...]:
    label = "post_binary32_codes"
    raw_batches = _sequence(value, label)
    if len(raw_batches) != batch_size:
        raise HCPostServiceNumericError(f"{label} batch dimension must match branch")

    batches: list[tuple[F32Vector, ...]] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence_label = f"{label}[{batch_index}]"
        sequence = _sequence(raw_sequence, sequence_label)
        if len(sequence) != sequence_length:
            raise HCPostServiceNumericError(
                f"{label} sequence dimension must match branch"
            )
        output_sequence: list[F32Vector] = []
        for position, raw_vector in enumerate(sequence):
            vector_label = f"{sequence_label}[{position}]"
            vector = _sequence(raw_vector, vector_label)
            if len(vector) != hc_multiplier:
                raise HCPostServiceNumericError(
                    f"{label} destination HC dimension must equal hc_multiplier"
                )
            output_sequence.append(
                tuple(
                    _validate_finite_binary32(
                        code,
                        f"{vector_label}[{destination}]",
                    )
                    for destination, code in enumerate(vector)
                )
            )
        batches.append(tuple(output_sequence))
    return tuple(batches)


def _validate_combination(
    value: object,
    *,
    batch_size: int,
    sequence_length: int,
    hc_multiplier: int,
) -> tuple[tuple[tuple[F32Vector, ...], ...], ...]:
    label = "comb_binary32_codes"
    raw_batches = _sequence(value, label)
    if len(raw_batches) != batch_size:
        raise HCPostServiceNumericError(f"{label} batch dimension must match branch")

    batches: list[tuple[tuple[F32Vector, ...], ...]] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence_label = f"{label}[{batch_index}]"
        sequence = _sequence(raw_sequence, sequence_label)
        if len(sequence) != sequence_length:
            raise HCPostServiceNumericError(
                f"{label} sequence dimension must match branch"
            )
        output_sequence: list[tuple[F32Vector, ...]] = []
        for position, raw_matrix in enumerate(sequence):
            matrix_label = f"{sequence_label}[{position}]"
            matrix = _sequence(raw_matrix, matrix_label)
            if len(matrix) != hc_multiplier:
                raise HCPostServiceNumericError(
                    f"{label} source HC dimension must equal hc_multiplier"
                )
            output_matrix: list[F32Vector] = []
            for source, raw_vector in enumerate(matrix):
                vector_label = f"{matrix_label}[{source}]"
                vector = _sequence(raw_vector, vector_label)
                if len(vector) != hc_multiplier:
                    raise HCPostServiceNumericError(
                        f"{label} destination HC dimension must equal hc_multiplier"
                    )
                output_matrix.append(
                    tuple(
                        _validate_finite_binary32(
                            code,
                            f"{vector_label}[{destination}]",
                        )
                        for destination, code in enumerate(vector)
                    )
                )
            output_sequence.append(tuple(output_matrix))
        batches.append(tuple(output_sequence))
    return tuple(batches)


def _round_integer_right(value: int, shift: int) -> int:
    """Return RNE(value / 2**shift) for nonnegative integer ``value``."""

    if shift <= 0:
        return value << -shift
    quotient, remainder = divmod(value, 1 << shift)
    midpoint = 1 << (shift - 1)
    if remainder > midpoint or (remainder == midpoint and quotient & 1):
        quotient += 1
    return quotient


def _decode_binary32_dyadic(code: int) -> tuple[int, int]:
    """Decode finite binary32 as ``integer * 2**exponent``."""

    exponent_field = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent_field == 0xFF:
        raise HCPostServiceNumericError("binary32 NaN or infinity is not arithmetic")
    if exponent_field == 0:
        significand = fraction
        exponent = -149
    else:
        significand = (1 << 23) | fraction
        exponent = exponent_field - 150
    if code & 0x80000000:
        significand = -significand
    return significand, exponent


def _encode_binary32_dyadic(integer: int, exponent: int) -> int:
    """Round an exact dyadic value to finite binary32, ties to even."""

    if integer == 0:
        return 0
    sign = 0x80000000 if integer < 0 else 0
    magnitude = abs(integer)
    exact_exponent = magnitude.bit_length() - 1 + exponent

    if exact_exponent < -126:
        significand = _round_integer_right(magnitude, -(exponent + 149))
        if significand == 0:
            return 0
        if significand < 1 << 23:
            return sign | significand
        return sign | (1 << 23)

    significand = _round_integer_right(magnitude, magnitude.bit_length() - 24)
    if significand == 1 << 24:
        significand = 1 << 23
        exact_exponent += 1
    if exact_exponent > 127:
        raise HCPostServiceNumericError("finite binary32 arithmetic overflow")
    return sign | ((exact_exponent + 127) << 23) | (significand - (1 << 23))


def _multiply_codes(left_code: int, right_code: int) -> int:
    if left_code & 0x7FFFFFFF == 0 or right_code & 0x7FFFFFFF == 0:
        return 0
    left_integer, left_exponent = _decode_binary32_dyadic(left_code)
    right_integer, right_exponent = _decode_binary32_dyadic(right_code)
    return _encode_binary32_dyadic(
        left_integer * right_integer,
        left_exponent + right_exponent,
    )


def _add_codes(left_code: int, right_code: int) -> int:
    if left_code & 0x7FFFFFFF == 0:
        return right_code if right_code & 0x7FFFFFFF else 0
    if right_code & 0x7FFFFFFF == 0:
        return left_code
    left_integer, left_exponent = _decode_binary32_dyadic(left_code)
    right_integer, right_exponent = _decode_binary32_dyadic(right_code)
    common_exponent = min(left_exponent, right_exponent)
    exact_integer = (left_integer << (left_exponent - common_exponent)) + (
        right_integer << (right_exponent - common_exponent)
    )
    return _encode_binary32_dyadic(exact_integer, common_exponent)


def _balanced_sum_codes(codes: tuple[int, ...]) -> int:
    if not codes:
        raise HCPostServiceNumericError("binary32 balanced reduction is empty")
    level = codes
    while len(level) > 1:
        if len(level) & 1:
            level += (0,)
        level = tuple(
            _add_codes(level[index], level[index + 1])
            for index in range(0, len(level), 2)
        )
    return level[0]


def rn32_multiply(left_code: int, right_code: int) -> int:
    """Apply one finite binary32 RNE multiplication boundary."""

    left = _validate_finite_binary32(left_code, "left_code")
    right = _validate_finite_binary32(right_code, "right_code")
    return _multiply_codes(left, right)


def rn32_add(left_code: int, right_code: int) -> int:
    """Apply one finite binary32 RNE addition boundary."""

    left = _validate_finite_binary32(left_code, "left_code")
    right = _validate_finite_binary32(right_code, "right_code")
    return _add_codes(left, right)


def rn32_balanced_sum(codes: Sequence[int]) -> int:
    """Apply NUM-6.1's ordered balanced tree, padding missing partners by +0."""

    raw = _sequence(codes, "codes")
    if not raw:
        raise HCPostServiceNumericError("codes must contain at least one value")
    validated = tuple(
        _validate_finite_binary32(code, f"codes[{index}]")
        for index, code in enumerate(raw)
    )
    return _balanced_sum_codes(validated)


def _binary32_to_bf16(code: int) -> tuple[int, bool]:
    if code & 0x7F800000 == 0x7F800000:
        raise HCPostServiceNumericError("nonfinite binary32 cannot convert to BF16")
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


def _balanced_add_count(source_count: int) -> int:
    additions = 0
    level_count = source_count
    while level_count > 1:
        level_count = (level_count + 1) // 2
        additions += level_count
    return additions


def _logical_counters(
    *,
    batch_size: int,
    sequence_length: int,
    hidden_width: int,
    hc_multiplier: int,
    saturation_count: int,
) -> Mapping[str, int]:
    tokens = batch_size * sequence_length
    outputs = tokens * hc_multiplier * hidden_width
    counters = {
        "hc_post_branch_bf16_values": tokens * hidden_width,
        "hc_post_residual_bf16_values_preserved": (
            tokens * hc_multiplier * hidden_width
        ),
        "hc_post_post_binary32_values": tokens * hc_multiplier,
        "hc_post_comb_binary32_values": tokens * hc_multiplier * hc_multiplier,
        "hc_post_branch_coefficient_multiplies": outputs,
        "hc_post_residual_coefficient_multiplies": outputs * hc_multiplier,
        "hc_post_residual_reduction_adds": (
            outputs * _balanced_add_count(hc_multiplier)
        ),
        "hc_post_branch_residual_adds": outputs,
        "hc_post_output_bf16_conversions": outputs,
        "hc_post_output_bf16_saturations": saturation_count,
    }
    return MappingProxyType(counters)


def execute_hc_post(
    branch_bf16_codes: Sequence[Sequence[Sequence[int]]],
    residual_bf16_codes: Sequence[Sequence[Sequence[Sequence[int]]]],
    post_binary32_codes: Sequence[Sequence[Sequence[int]]],
    comb_binary32_codes: Sequence[Sequence[Sequence[Sequence[int]]]],
    *,
    hc_multiplier: int,
) -> HCPostServiceResult:
    """Execute one homogeneous NUM-6.7 command and return only on full success."""

    multiplier = _positive_integer(hc_multiplier, "hc_multiplier")
    branch = _validate_branch(branch_bf16_codes)
    batch_size = len(branch)
    sequence_length = len(branch[0])
    hidden_width = len(branch[0][0])

    # Materialize and validate every input before arithmetic starts.  The local
    # immutable snapshots also prevent caller mutation from changing a command
    # in flight.  No result object or counter escapes if a later operation fails.
    residual = _validate_residual(
        residual_bf16_codes,
        batch_size=batch_size,
        sequence_length=sequence_length,
        hidden_width=hidden_width,
        hc_multiplier=multiplier,
    )
    post = _validate_post(
        post_binary32_codes,
        batch_size=batch_size,
        sequence_length=sequence_length,
        hc_multiplier=multiplier,
    )
    combination = _validate_combination(
        comb_binary32_codes,
        batch_size=batch_size,
        sequence_length=sequence_length,
        hc_multiplier=multiplier,
    )

    output_batches: list[tuple[tuple[BF16Vector, ...], ...]] = []
    branch_product_batches: list[tuple[tuple[F32Vector, ...], ...]] = []
    residual_product_batches: list[tuple[tuple[tuple[F32Vector, ...], ...], ...]] = []
    residual_sum_batches: list[tuple[tuple[F32Vector, ...], ...]] = []
    output_binary32_batches: list[tuple[tuple[F32Vector, ...], ...]] = []
    saturation_count = 0

    for batch_index in range(batch_size):
        output_sequence: list[tuple[BF16Vector, ...]] = []
        branch_product_sequence: list[tuple[F32Vector, ...]] = []
        residual_product_sequence: list[tuple[tuple[F32Vector, ...], ...]] = []
        residual_sum_sequence: list[tuple[F32Vector, ...]] = []
        output_binary32_sequence: list[tuple[F32Vector, ...]] = []
        for position in range(sequence_length):
            output_destinations: list[BF16Vector] = []
            branch_product_destinations: list[F32Vector] = []
            destination_residual_products: list[tuple[F32Vector, ...]] = []
            residual_sum_destinations: list[F32Vector] = []
            output_binary32_destinations: list[F32Vector] = []
            for destination in range(multiplier):
                output_vector: list[int] = []
                branch_product_vector: list[int] = []
                residual_product_vectors: list[list[int]] = [
                    [] for _ in range(multiplier)
                ]
                residual_sum_vector: list[int] = []
                output_binary32_vector: list[int] = []
                for column in range(hidden_width):
                    try:
                        branch_value = branch[batch_index][position][column]
                        branch_widened = _widen_bf16(branch_value)
                        branch_product = _multiply_codes(
                            post[batch_index][position][destination],
                            branch_widened,
                        )
                        residual_products = tuple(
                            _multiply_codes(
                                combination[batch_index][position][source][destination],
                                _widen_bf16(
                                    residual[batch_index][position][source][column]
                                ),
                            )
                            for source in range(multiplier)
                        )
                        residual_sum = _balanced_sum_codes(residual_products)
                        output_binary32 = _add_codes(
                            branch_product,
                            residual_sum,
                        )
                        output_code, saturated = _binary32_to_bf16(output_binary32)
                    except HCPostServiceNumericError as exc:
                        raise HCPostServiceNumericError(
                            "HC_POST arithmetic failed at "
                            f"[{batch_index}][{position}]"
                            f"[{destination}][{column}]: {exc}"
                        ) from exc

                    output_vector.append(output_code)
                    branch_product_vector.append(branch_product)
                    for source, product in enumerate(residual_products):
                        residual_product_vectors[source].append(product)
                    residual_sum_vector.append(residual_sum)
                    output_binary32_vector.append(output_binary32)
                    saturation_count += int(saturated)

                output_destinations.append(tuple(output_vector))
                branch_product_destinations.append(tuple(branch_product_vector))
                destination_residual_products.append(
                    tuple(tuple(vector) for vector in residual_product_vectors)
                )
                residual_sum_destinations.append(tuple(residual_sum_vector))
                output_binary32_destinations.append(tuple(output_binary32_vector))

            # Diagnostic orientation is [source][destination][hidden], matching
            # the architectural combination tensor rather than loop nesting.
            residual_products_by_source = tuple(
                tuple(
                    destination_residual_products[destination][source]
                    for destination in range(multiplier)
                )
                for source in range(multiplier)
            )
            output_sequence.append(tuple(output_destinations))
            branch_product_sequence.append(tuple(branch_product_destinations))
            residual_product_sequence.append(residual_products_by_source)
            residual_sum_sequence.append(tuple(residual_sum_destinations))
            output_binary32_sequence.append(tuple(output_binary32_destinations))

        output_batches.append(tuple(output_sequence))
        branch_product_batches.append(tuple(branch_product_sequence))
        residual_product_batches.append(tuple(residual_product_sequence))
        residual_sum_batches.append(tuple(residual_sum_sequence))
        output_binary32_batches.append(tuple(output_binary32_sequence))

    return HCPostServiceResult(
        output_codes=tuple(output_batches),
        output_saturation_count=saturation_count,
        branch_codes=branch,
        residual_codes=residual,
        branch_product_codes=tuple(branch_product_batches),
        residual_product_codes=tuple(residual_product_batches),
        residual_sum_codes=tuple(residual_sum_batches),
        output_binary32_codes=tuple(output_binary32_batches),
        logical_counters=_logical_counters(
            batch_size=batch_size,
            sequence_length=sequence_length,
            hidden_width=hidden_width,
            hc_multiplier=multiplier,
            saturation_count=saturation_count,
        ),
    )


def execute_pinned_hc_post(
    branch_bf16_codes: Sequence[Sequence[Sequence[int]]],
    residual_bf16_codes: Sequence[Sequence[Sequence[Sequence[int]]]],
    post_binary32_codes: Sequence[Sequence[Sequence[int]]],
    comb_binary32_codes: Sequence[Sequence[Sequence[Sequence[int]]]],
) -> HCPostServiceResult:
    """Execute the bounded Flash/Pro HC_POST command profile.

    This is the production-facing numeric entrypoint for the current compiler
    schedule.  It rejects oversized token extents and non-pinned hidden widths
    before the generic primitive allocates its quadratic-H diagnostics.
    """

    label = "branch_bf16_codes"
    raw_batches = _sequence(branch_bf16_codes, label)
    if not raw_batches:
        raise HCPostServiceNumericError(f"{label} must contain at least one batch")
    if len(raw_batches) > HC_POST_MAX_TOKENS_PER_COMMAND:
        raise HCPostServiceNumericError(
            f"{label} batch extent exceeds the pinned command token bound"
        )
    sequence_length: int | None = None
    token_count = 0
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"{label}[{batch_index}]")
        if not sequence:
            raise HCPostServiceNumericError(
                f"{label} must contain at least one position per batch"
            )
        if sequence_length is None:
            sequence_length = len(sequence)
        elif len(sequence) != sequence_length:
            raise HCPostServiceNumericError(
                f"{label} must be a rectangular rank-3 tensor"
            )
        token_count += len(sequence)
        if token_count > HC_POST_MAX_TOKENS_PER_COMMAND:
            raise HCPostServiceNumericError(
                f"{label} batch*sequence exceeds the pinned command token bound"
            )
        for position, raw_vector in enumerate(sequence):
            vector = _sequence(raw_vector, f"{label}[{batch_index}][{position}]")
            if len(vector) != HC_POST_PINNED_HIDDEN_WIDTH:
                raise HCPostServiceNumericError(
                    f"{label} hidden width must equal the pinned value "
                    f"{HC_POST_PINNED_HIDDEN_WIDTH}"
                )

    return execute_hc_post(
        branch_bf16_codes,
        residual_bf16_codes,
        post_binary32_codes,
        comb_binary32_codes,
        hc_multiplier=HC_POST_PINNED_HC_MULTIPLIER,
    )


__all__ = [
    "HC_POST_MAX_TOKENS_PER_COMMAND",
    "HC_POST_PINNED_HC_MULTIPLIER",
    "HC_POST_PINNED_HIDDEN_WIDTH",
    "HCPostServiceNumericError",
    "HCPostServiceResult",
    "execute_hc_post",
    "execute_pinned_hc_post",
    "rn32_add",
    "rn32_balanced_sum",
    "rn32_multiply",
]
