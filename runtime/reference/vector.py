"""Deterministic DeepSeek V4 vector-boundary reference operations.

The pinned model captures selected main-model hidden states with
``h.mean(dim=2)``. The source fixes the HC source axis but does not freeze one
cross-backend reduction tree. OpenTallas therefore widens finite BF16 payloads
exactly to binary32, applies the NUM-6.1 canonical balanced tree, divides once
in binary32, and converts the result to BF16 with round-to-nearest ties-to-even.

The same numeric primitives define ``HC_POST``: a branch contribution and four
residual-stream contributions are multiplied in binary32, residuals reduce by
the canonical source-stream tree, and the result converts once to BF16.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_multiply,
    decode_bf16,
    decode_binary32,
    encode_binary32_rne,
)


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
BF16_MAX_ENCODING = (1 << 16) - 1

BF16Vector: TypeAlias = tuple[int, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Sequence, ...]
BF16HCSequence: TypeAlias = tuple[tuple[BF16Vector, ...], ...]
BF16HCBatch: TypeAlias = tuple[BF16HCSequence, ...]


@dataclass(frozen=True)
class HCPostResult:
    """BF16 HC output and its sticky finite-saturation count."""

    output_codes: BF16HCBatch
    output_saturation_count: int


class VectorReferenceError(ValueError):
    """Raised when a vector request violates the target numeric contract."""


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise VectorReferenceError(f"{label} must be a sequence")
    return value


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise VectorReferenceError(f"{label} must be an integer >= 1")
    return value


def _finite_bf16_batch(value: object, label: str) -> BF16Batch:
    batches = _sequence(value, label)
    if not batches:
        raise VectorReferenceError(f"{label} must contain at least one batch")

    result: list[BF16Sequence] = []
    sequence_length: int | None = None
    hidden_width: int | None = None
    for batch_index, raw_sequence in enumerate(batches):
        sequence = _sequence(raw_sequence, f"{label}[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise VectorReferenceError(
                    f"{label} must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise VectorReferenceError(f"{label} must be a rectangular rank-3 tensor")

        output_sequence: list[BF16Vector] = []
        for position, raw_vector in enumerate(sequence):
            vector = _sequence(raw_vector, f"{label}[{batch_index}][{position}]")
            if hidden_width is None:
                hidden_width = len(vector)
                if hidden_width == 0:
                    raise VectorReferenceError(
                        f"{label} vectors must contain at least one BF16 value"
                    )
            elif len(vector) != hidden_width:
                raise VectorReferenceError(
                    f"{label} must be a rectangular rank-3 tensor"
                )
            output_vector: list[int] = []
            for column, code in enumerate(vector):
                element_label = f"{label}[{batch_index}][{position}][{column}]"
                if (
                    isinstance(code, bool)
                    or not isinstance(code, int)
                    or not 0 <= code <= BF16_MAX_ENCODING
                ):
                    raise VectorReferenceError(
                        f"{element_label} must be a 16-bit BF16 encoding"
                    )
                decoded = decode_bf16(code)
                if not decoded.finite:
                    raise VectorReferenceError(
                        f"{element_label} must be finite BF16"
                    )
                output_vector.append(code)
            output_sequence.append(tuple(output_vector))
        result.append(tuple(output_sequence))
    return tuple(result)


def _finite_bf16_hc_batch(
    value: object, label: str = "hidden_bf16_codes"
) -> BF16HCBatch:
    batches = _sequence(value, label)
    if not batches:
        raise VectorReferenceError(f"{label} must contain at least one batch")

    result: list[BF16HCSequence] = []
    sequence_length: int | None = None
    hc_count: int | None = None
    hidden_width: int | None = None
    for batch_index, raw_sequence in enumerate(batches):
        sequence = _sequence(raw_sequence, f"{label}[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise VectorReferenceError(
                    f"{label} must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise VectorReferenceError(
                f"{label} must be a rectangular rank-4 tensor"
            )

        output_sequence: list[tuple[BF16Vector, ...]] = []
        for position, raw_hc_vectors in enumerate(sequence):
            hc_vectors = _sequence(
                raw_hc_vectors,
                f"{label}[{batch_index}][{position}]",
            )
            if hc_count is None:
                hc_count = len(hc_vectors)
                if hc_count == 0:
                    raise VectorReferenceError(
                        f"{label} must contain at least one HC stream"
                    )
            elif len(hc_vectors) != hc_count:
                raise VectorReferenceError(
                    f"{label} must be a rectangular rank-4 tensor"
                )

            output_hc_vectors: list[BF16Vector] = []
            for hc_index, raw_vector in enumerate(hc_vectors):
                vector = _sequence(
                    raw_vector,
                    f"{label}[{batch_index}][{position}][{hc_index}]",
                )
                if hidden_width is None:
                    hidden_width = len(vector)
                    if hidden_width == 0:
                        raise VectorReferenceError(
                            f"{label} vectors must contain at least one BF16 value"
                        )
                elif len(vector) != hidden_width:
                    raise VectorReferenceError(
                        f"{label} must be a rectangular rank-4 tensor"
                    )

                output_vector: list[int] = []
                for column, code in enumerate(vector):
                    element_label = (
                        f"{label}[{batch_index}][{position}][{hc_index}][{column}]"
                    )
                    if (
                        isinstance(code, bool)
                        or not isinstance(code, int)
                        or not 0 <= code <= BF16_MAX_ENCODING
                    ):
                        raise VectorReferenceError(
                            f"{element_label} must be a 16-bit BF16 encoding"
                        )
                    decoded = decode_bf16(code)
                    if not decoded.finite:
                        raise VectorReferenceError(
                            f"{element_label} must be finite BF16"
                        )
                    output_vector.append(code)
                output_hc_vectors.append(tuple(output_vector))
            output_sequence.append(tuple(output_hc_vectors))
        result.append(tuple(output_sequence))
    return tuple(result)


def _finite_binary32_code(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VectorReferenceError(f"{label} must be a binary32 encoding")
    try:
        decoded = decode_binary32(value)
    except ValueError as exc:
        raise VectorReferenceError(f"{label} must be a binary32 encoding") from exc
    if not decoded.finite:
        raise VectorReferenceError(f"{label} must be finite binary32")
    return value


def _finite_binary32_post(
    value: object,
    *,
    batch_size: int,
    sequence_length: int,
    hc_multiplier: int,
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    label = "post_binary32_codes"
    batches = _sequence(value, label)
    if len(batches) != batch_size:
        raise VectorReferenceError(f"{label} batch dimension must match branch")
    result: list[tuple[tuple[int, ...], ...]] = []
    for batch_index, raw_sequence in enumerate(batches):
        sequence = _sequence(raw_sequence, f"{label}[{batch_index}]")
        if len(sequence) != sequence_length:
            raise VectorReferenceError(
                f"{label} sequence dimension must match branch"
            )
        output_sequence: list[tuple[int, ...]] = []
        for position, raw_vector in enumerate(sequence):
            vector = _sequence(raw_vector, f"{label}[{batch_index}][{position}]")
            if len(vector) != hc_multiplier:
                raise VectorReferenceError(
                    f"{label} HC dimension must equal hc_multiplier"
                )
            output_sequence.append(
                tuple(
                    _finite_binary32_code(
                        code, f"{label}[{batch_index}][{position}][{destination}]"
                    )
                    for destination, code in enumerate(vector)
                )
            )
        result.append(tuple(output_sequence))
    return tuple(result)


def _finite_binary32_comb(
    value: object,
    *,
    batch_size: int,
    sequence_length: int,
    hc_multiplier: int,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    label = "comb_binary32_codes"
    batches = _sequence(value, label)
    if len(batches) != batch_size:
        raise VectorReferenceError(f"{label} batch dimension must match branch")
    result: list[tuple[tuple[tuple[int, ...], ...], ...]] = []
    for batch_index, raw_sequence in enumerate(batches):
        sequence = _sequence(raw_sequence, f"{label}[{batch_index}]")
        if len(sequence) != sequence_length:
            raise VectorReferenceError(
                f"{label} sequence dimension must match branch"
            )
        output_sequence: list[tuple[tuple[int, ...], ...]] = []
        for position, raw_matrix in enumerate(sequence):
            matrix = _sequence(raw_matrix, f"{label}[{batch_index}][{position}]")
            if len(matrix) != hc_multiplier:
                raise VectorReferenceError(
                    f"{label} source HC dimension must equal hc_multiplier"
                )
            output_matrix: list[tuple[int, ...]] = []
            for source, raw_vector in enumerate(matrix):
                vector = _sequence(
                    raw_vector,
                    f"{label}[{batch_index}][{position}][{source}]",
                )
                if len(vector) != hc_multiplier:
                    raise VectorReferenceError(
                        f"{label} destination HC dimension must equal hc_multiplier"
                    )
                output_matrix.append(
                    tuple(
                        _finite_binary32_code(
                            code,
                            f"{label}[{batch_index}][{position}]"
                            f"[{source}][{destination}]",
                        )
                        for destination, code in enumerate(vector)
                    )
                )
            output_sequence.append(tuple(output_matrix))
        result.append(tuple(output_sequence))
    return tuple(result)


def target_hidden_capture_bf16(
    hidden_bf16_codes: Sequence[Sequence[Sequence[Sequence[int]]]],
    *,
    hc_multiplier: int,
) -> BF16Batch:
    """Mean the HC source axis with canonical binary32/BF16 semantics.

    Input shape is ``[batch, sequence, hc_multiplier, width]`` and output shape
    is ``[batch, sequence, width]``. Every finite BF16 input widens exactly by
    appending sixteen zero bits. Intermediate binary32 overflow and nonfinite
    input fail closed instead of inheriting backend-specific behavior.
    """

    hc_multiplier = _positive_integer(hc_multiplier, "hc_multiplier")
    hidden = _finite_bf16_hc_batch(hidden_bf16_codes)
    observed_hc_count = len(hidden[0][0])
    if observed_hc_count != hc_multiplier:
        raise VectorReferenceError(
            "hidden_bf16_codes HC dimension must equal hc_multiplier "
            f"({observed_hc_count} != {hc_multiplier})"
        )

    try:
        divisor_code = encode_binary32_rne(hc_multiplier)
    except NumericReferenceError as exc:  # pragma: no cover - impractical shape
        raise VectorReferenceError(
            f"hc_multiplier cannot be represented for binary32 division: {exc}"
        ) from exc

    output: list[BF16Sequence] = []
    for batch_index, sequence in enumerate(hidden):
        output_sequence: list[BF16Vector] = []
        for position, hc_vectors in enumerate(sequence):
            output_vector: list[int] = []
            for column in range(len(hc_vectors[0])):
                # BF16 is the upper half of binary32, so this widening is exact
                # for finite values, including subnormals and signed zero.
                source_codes = tuple(vector[column] << 16 for vector in hc_vectors)
                try:
                    total_code = binary32_balanced_sum(source_codes)
                    mean_code = binary32_divide(total_code, divisor_code)
                    output_code = binary32_bits_to_bf16_rne(mean_code).code
                except NumericReferenceError as exc:
                    raise VectorReferenceError(
                        "target-hidden arithmetic failed at "
                        f"[{batch_index}][{position}][{column}]: {exc}"
                    ) from exc
                output_vector.append(output_code)
            output_sequence.append(tuple(output_vector))
        output.append(tuple(output_sequence))
    return tuple(output)


def hc_post_bf16(
    branch_bf16_codes: Sequence[Sequence[Sequence[int]]],
    residual_bf16_codes: Sequence[Sequence[Sequence[Sequence[int]]]],
    post_binary32_codes: Sequence[Sequence[Sequence[int]]],
    comb_binary32_codes: Sequence[Sequence[Sequence[Sequence[int]]]],
    *,
    hc_multiplier: int,
) -> HCPostResult:
    """Apply the pinned HC post-mix with deterministic target arithmetic.

    ``comb[source][destination]`` follows the broadcast and reduction axes in
    ``Block.hc_post``. Every BF16 operand widens exactly. Multiplications round
    once to binary32, residual source streams use the NUM-6.1 balanced tree,
    the branch contribution is added once, and the result converts once to
    BF16. Intermediate nonfinite values poison; finite BF16 saturation is
    returned as a sticky count.
    """

    hc_multiplier = _positive_integer(hc_multiplier, "hc_multiplier")
    branch = _finite_bf16_batch(branch_bf16_codes, "branch_bf16_codes")
    residual = _finite_bf16_hc_batch(
        residual_bf16_codes, "residual_bf16_codes"
    )
    batch_size = len(branch)
    sequence_length = len(branch[0])
    hidden_width = len(branch[0][0])
    if len(residual) != batch_size or len(residual[0]) != sequence_length:
        raise VectorReferenceError(
            "residual_bf16_codes batch and sequence dimensions must match branch"
        )
    observed_hc_count = len(residual[0][0])
    if observed_hc_count != hc_multiplier:
        raise VectorReferenceError(
            "residual_bf16_codes HC dimension must equal hc_multiplier "
            f"({observed_hc_count} != {hc_multiplier})"
        )
    if len(residual[0][0][0]) != hidden_width:
        raise VectorReferenceError(
            "residual_bf16_codes hidden width must match branch"
        )

    post = _finite_binary32_post(
        post_binary32_codes,
        batch_size=batch_size,
        sequence_length=sequence_length,
        hc_multiplier=hc_multiplier,
    )
    comb = _finite_binary32_comb(
        comb_binary32_codes,
        batch_size=batch_size,
        sequence_length=sequence_length,
        hc_multiplier=hc_multiplier,
    )

    saturation_count = 0
    output: list[BF16HCSequence] = []
    for batch_index in range(batch_size):
        output_sequence: list[tuple[BF16Vector, ...]] = []
        for position in range(sequence_length):
            output_destinations: list[BF16Vector] = []
            for destination in range(hc_multiplier):
                output_vector: list[int] = []
                for column in range(hidden_width):
                    try:
                        branch_product = binary32_multiply(
                            post[batch_index][position][destination],
                            branch[batch_index][position][column] << 16,
                        )
                        residual_products = tuple(
                            binary32_multiply(
                                comb[batch_index][position][source][destination],
                                residual[batch_index][position][source][column] << 16,
                            )
                            for source in range(hc_multiplier)
                        )
                        residual_sum = binary32_balanced_sum(residual_products)
                        output_code = binary32_add(branch_product, residual_sum)
                        converted = binary32_bits_to_bf16_rne(output_code)
                    except NumericReferenceError as exc:
                        raise VectorReferenceError(
                            "HC-post arithmetic failed at "
                            f"[{batch_index}][{position}]"
                            f"[{destination}][{column}]: {exc}"
                        ) from exc
                    output_vector.append(converted.code)
                    saturation_count += int(converted.saturated)
                output_destinations.append(tuple(output_vector))
            output_sequence.append(tuple(output_destinations))
        output.append(tuple(output_sequence))
    return HCPostResult(tuple(output), saturation_count)


__all__ = [
    "BF16_MAX_ENCODING",
    "MODEL_SOURCE_SHA256",
    "BF16Batch",
    "BF16HCBatch",
    "BF16HCSequence",
    "BF16Sequence",
    "BF16Vector",
    "HCPostResult",
    "VectorReferenceError",
    "hc_post_bf16",
    "target_hidden_capture_bf16",
]
