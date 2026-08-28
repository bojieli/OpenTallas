"""Deterministic DeepSeek V4 vector-boundary reference operations.

The pinned model captures selected main-model hidden states with
``h.mean(dim=2)``. The source fixes the HC source axis but does not freeze one
cross-backend reduction tree. OpenTallas therefore widens finite BF16 payloads
exactly to binary32, applies the NUM-6.1 canonical balanced tree, divides once
in binary32, and converts the result to BF16 with round-to-nearest ties-to-even.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    decode_bf16,
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


def _finite_bf16_hc_batch(value: object) -> BF16HCBatch:
    batches = _sequence(value, "hidden_bf16_codes")
    if not batches:
        raise VectorReferenceError(
            "hidden_bf16_codes must contain at least one batch"
        )

    result: list[BF16HCSequence] = []
    sequence_length: int | None = None
    hc_count: int | None = None
    hidden_width: int | None = None
    for batch_index, raw_sequence in enumerate(batches):
        sequence = _sequence(
            raw_sequence, f"hidden_bf16_codes[{batch_index}]"
        )
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise VectorReferenceError(
                    "hidden_bf16_codes must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise VectorReferenceError(
                "hidden_bf16_codes must be a rectangular rank-4 tensor"
            )

        output_sequence: list[tuple[BF16Vector, ...]] = []
        for position, raw_hc_vectors in enumerate(sequence):
            hc_vectors = _sequence(
                raw_hc_vectors,
                f"hidden_bf16_codes[{batch_index}][{position}]",
            )
            if hc_count is None:
                hc_count = len(hc_vectors)
                if hc_count == 0:
                    raise VectorReferenceError(
                        "hidden_bf16_codes must contain at least one HC stream"
                    )
            elif len(hc_vectors) != hc_count:
                raise VectorReferenceError(
                    "hidden_bf16_codes must be a rectangular rank-4 tensor"
                )

            output_hc_vectors: list[BF16Vector] = []
            for hc_index, raw_vector in enumerate(hc_vectors):
                vector = _sequence(
                    raw_vector,
                    f"hidden_bf16_codes[{batch_index}][{position}][{hc_index}]",
                )
                if hidden_width is None:
                    hidden_width = len(vector)
                    if hidden_width == 0:
                        raise VectorReferenceError(
                            "hidden_bf16_codes vectors must contain at least one "
                            "BF16 value"
                        )
                elif len(vector) != hidden_width:
                    raise VectorReferenceError(
                        "hidden_bf16_codes must be a rectangular rank-4 tensor"
                    )

                output_vector: list[int] = []
                for column, code in enumerate(vector):
                    label = (
                        f"hidden_bf16_codes[{batch_index}][{position}]"
                        f"[{hc_index}][{column}]"
                    )
                    if (
                        isinstance(code, bool)
                        or not isinstance(code, int)
                        or not 0 <= code <= BF16_MAX_ENCODING
                    ):
                        raise VectorReferenceError(
                            f"{label} must be a 16-bit BF16 encoding"
                        )
                    decoded = decode_bf16(code)
                    if not decoded.finite:
                        raise VectorReferenceError(f"{label} must be finite BF16")
                    output_vector.append(code)
                output_hc_vectors.append(tuple(output_vector))
            output_sequence.append(tuple(output_hc_vectors))
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


__all__ = [
    "BF16_MAX_ENCODING",
    "MODEL_SOURCE_SHA256",
    "BF16Batch",
    "BF16HCBatch",
    "BF16HCSequence",
    "BF16Sequence",
    "BF16Vector",
    "VectorReferenceError",
    "target_hidden_capture_bf16",
]
