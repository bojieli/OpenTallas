"""Bit-preserving structural tensor operations from pinned DeepSeek V4 source."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
BF16_MAX_ENCODING = (1 << 16) - 1

BF16Vector: TypeAlias = tuple[int, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Sequence, ...]
BF16HCSequence: TypeAlias = tuple[tuple[BF16Vector, ...], ...]
BF16HCBatch: TypeAlias = tuple[BF16HCSequence, ...]


class StructuralReferenceError(ValueError):
    """Raised when a structural tensor request is invalid."""


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise StructuralReferenceError(f"{label} must be a sequence")
    return value


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise StructuralReferenceError(f"{label} must be an integer >= 1")
    return value


def _bf16_batch(value: object) -> BF16Batch:
    batches = _sequence(value, "hidden")
    if not batches:
        raise StructuralReferenceError("hidden must contain at least one batch")
    result: list[BF16Sequence] = []
    sequence_length: int | None = None
    hidden_width: int | None = None
    for batch_index, raw_sequence in enumerate(batches):
        sequence = _sequence(raw_sequence, f"hidden[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise StructuralReferenceError(
                    "hidden must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise StructuralReferenceError("hidden must be a rectangular rank-3 tensor")
        output_sequence: list[BF16Vector] = []
        for position, raw_vector in enumerate(sequence):
            vector = _sequence(raw_vector, f"hidden[{batch_index}][{position}]")
            if hidden_width is None:
                hidden_width = len(vector)
                if hidden_width == 0:
                    raise StructuralReferenceError(
                        "hidden vectors must contain at least one BF16 value"
                    )
            elif len(vector) != hidden_width:
                raise StructuralReferenceError(
                    "hidden must be a rectangular rank-3 tensor"
                )
            output_vector: list[int] = []
            for column, code in enumerate(vector):
                if (
                    isinstance(code, bool)
                    or not isinstance(code, int)
                    or not 0 <= code <= BF16_MAX_ENCODING
                ):
                    raise StructuralReferenceError(
                        f"hidden[{batch_index}][{position}][{column}] must be "
                        "a 16-bit BF16 encoding"
                    )
                output_vector.append(code)
            output_sequence.append(tuple(output_vector))
        result.append(tuple(output_sequence))
    return tuple(result)


def hc_expand_bf16(
    hidden: Sequence[Sequence[Sequence[int]]], hc_multiplier: int
) -> BF16HCBatch:
    """Reproduce ``unsqueeze(2).repeat(1, 1, hc_mult, 1)`` exactly.

    The source performs no arithmetic at this boundary; every BF16 payload bit,
    including signed zero, subnormal, infinity, and NaN encodings, is copied.
    """

    hc_multiplier = _positive_integer(hc_multiplier, "hc_multiplier")
    value = _bf16_batch(hidden)
    return tuple(
        tuple(
            tuple(vector for _ in range(hc_multiplier))
            for vector in sequence
        )
        for sequence in value
    )


def dspark_noise_token_block(
    current_token_ids: Sequence[int],
    *,
    block_size: int,
    noise_token_id: int,
    vocabulary_size: int,
) -> tuple[tuple[int, ...], ...]:
    """Construct the token-ID block used before DSpark embedding.

    The current target token occupies column zero and every remaining draft
    position receives the fixed noise token. This is the integer construction in
    ``DSparkBlock.forward_embed`` before its shared embedding lookup and HC copy.
    """

    block_size = _positive_integer(block_size, "block_size")
    vocabulary_size = _positive_integer(vocabulary_size, "vocabulary_size")
    if (
        isinstance(noise_token_id, bool)
        or not isinstance(noise_token_id, int)
        or not 0 <= noise_token_id < vocabulary_size
    ):
        raise StructuralReferenceError(
            "noise_token_id must be a valid vocabulary index"
        )
    raw_tokens = _sequence(current_token_ids, "current_token_ids")
    if not raw_tokens:
        raise StructuralReferenceError(
            "current_token_ids must contain at least one batch token"
        )
    result: list[tuple[int, ...]] = []
    for batch_index, token_id in enumerate(raw_tokens):
        if (
            isinstance(token_id, bool)
            or not isinstance(token_id, int)
            or not 0 <= token_id < vocabulary_size
        ):
            raise StructuralReferenceError(
                f"current_token_ids[{batch_index}] must be a valid vocabulary index"
            )
        result.append((token_id,) + (noise_token_id,) * (block_size - 1))
    return tuple(result)


__all__ = [
    "BF16_MAX_ENCODING",
    "MODEL_SOURCE_SHA256",
    "BF16Batch",
    "BF16HCBatch",
    "BF16HCSequence",
    "BF16Sequence",
    "BF16Vector",
    "StructuralReferenceError",
    "dspark_noise_token_block",
    "hc_expand_bf16",
]
