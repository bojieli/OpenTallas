"""Deterministic DeepSeek V4 learned-index score semantics.

The pinned ratio-four indexer contracts BF16 query heads against BF16
compressed KV entries, applies BF16 ReLU, multiplies each head by a scaled BF16
learned weight, and reduces the 64 logical heads to one BF16 score per candidate.
This reference fixes every otherwise backend-dependent reduction and rounding
boundary without using host floating-point arithmetic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_ordered_dot,
    decode_bf16,
    decode_binary32,
    encode_bf16_rne,
    encode_binary32_rne,
)


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
INDEX_SCORE_HEADS = 64
INDEX_SCORE_HEAD_DIM = 128
INDEX_SCORE_COMPRESSION_RATIO = 4
INDEX_SCORE_SITE_COUNT = 21
INDEX_SCORE_SCALE_BINARY32 = 0x3C3504F3
BF16_MAX_ENCODING = (1 << 16) - 1

BF16Vector: TypeAlias = tuple[int, ...]
BF16Matrix: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Matrix, ...]
BF16ScoreBatch: TypeAlias = tuple[tuple[tuple[int, ...], ...], ...]
BF16ValueVector: TypeAlias = tuple[Fraction, ...]
BF16ValueMatrix: TypeAlias = tuple[BF16ValueVector, ...]
BF16ValueBatch: TypeAlias = tuple[BF16ValueMatrix, ...]
BF16QueryValues: TypeAlias = tuple[
    tuple[tuple[BF16ValueVector, ...], ...], ...
]


class IndexScoreReferenceError(ValueError):
    """Raised when learned-index inputs violate the target contract."""


@dataclass(frozen=True)
class IndexScoreResult:
    """BF16 scores plus sticky finite-overflow event counts."""

    qk_saturated_element_count: int
    scaled_weight_saturated_element_count: int
    weighted_score_saturated_element_count: int
    output_saturated_element_count: int
    values: BF16ScoreBatch


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise IndexScoreReferenceError(f"{label} must be a sequence")
    return value


def _finite_bf16(value: object, label: str) -> Fraction:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= BF16_MAX_ENCODING
    ):
        raise IndexScoreReferenceError(f"{label} must be a 16-bit BF16 encoding")
    decoded = decode_bf16(value)
    if not decoded.finite or decoded.value is None:
        raise IndexScoreReferenceError(f"{label} must be finite BF16")
    return decoded.value


def _finite_query(
    value: object,
) -> tuple[BF16QueryValues, int, int, int]:
    raw_batches = _sequence(value, "query_bf16_codes")
    if not raw_batches:
        raise IndexScoreReferenceError(
            "query_bf16_codes must contain at least one batch"
        )

    result: list[tuple[tuple[BF16ValueVector, ...], ...]] = []
    sequence_length: int | None = None
    head_count: int | None = None
    head_dim: int | None = None
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(
            raw_sequence,
            f"query_bf16_codes[{batch_index}]",
        )
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise IndexScoreReferenceError(
                    "query_bf16_codes must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise IndexScoreReferenceError(
                "query_bf16_codes must be a rectangular rank-4 tensor"
            )

        sequence_values: list[tuple[BF16ValueVector, ...]] = []
        for position, raw_heads in enumerate(sequence):
            heads = _sequence(
                raw_heads,
                f"query_bf16_codes[{batch_index}][{position}]",
            )
            if head_count is None:
                head_count = len(heads)
                if head_count == 0:
                    raise IndexScoreReferenceError(
                        "query_bf16_codes must contain at least one head"
                    )
            elif len(heads) != head_count:
                raise IndexScoreReferenceError(
                    "query_bf16_codes must be a rectangular rank-4 tensor"
                )

            head_values: list[BF16ValueVector] = []
            for head, raw_row in enumerate(heads):
                row = _sequence(
                    raw_row,
                    f"query_bf16_codes[{batch_index}][{position}][{head}]",
                )
                if head_dim is None:
                    head_dim = len(row)
                    if head_dim == 0:
                        raise IndexScoreReferenceError(
                            "query_bf16_codes heads must contain at least one value"
                        )
                elif len(row) != head_dim:
                    raise IndexScoreReferenceError(
                        "query_bf16_codes must be a rectangular rank-4 tensor"
                    )
                head_values.append(
                    tuple(
                        _finite_bf16(
                            code,
                            "query_bf16_codes"
                            f"[{batch_index}][{position}][{head}][{column}]",
                        )
                        for column, code in enumerate(row)
                    )
                )
            sequence_values.append(tuple(head_values))
        result.append(tuple(sequence_values))

    assert sequence_length is not None
    assert head_count is not None
    assert head_dim is not None
    return tuple(result), sequence_length, head_count, head_dim


def _finite_kv(
    value: object,
    *,
    batch_size: int,
    head_dim: int,
) -> BF16ValueBatch:
    raw_batches = _sequence(value, "kv_bf16_codes")
    if len(raw_batches) != batch_size:
        raise IndexScoreReferenceError(
            "kv_bf16_codes batch count must match query_bf16_codes"
        )

    result: list[BF16ValueMatrix] = []
    candidate_count: int | None = None
    for batch_index, raw_candidates in enumerate(raw_batches):
        candidates = _sequence(raw_candidates, f"kv_bf16_codes[{batch_index}]")
        if candidate_count is None:
            candidate_count = len(candidates)
        elif len(candidates) != candidate_count:
            raise IndexScoreReferenceError(
                "kv_bf16_codes must be rectangular on the candidate axis"
            )

        candidate_values: list[BF16ValueVector] = []
        for candidate, raw_row in enumerate(candidates):
            row = _sequence(
                raw_row,
                f"kv_bf16_codes[{batch_index}][{candidate}]",
            )
            if len(row) != head_dim:
                raise IndexScoreReferenceError(
                    f"kv_bf16_codes[{batch_index}][{candidate}] must have "
                    f"head dimension {head_dim}"
                )
            candidate_values.append(
                tuple(
                    _finite_bf16(
                        code,
                        f"kv_bf16_codes[{batch_index}]"
                        f"[{candidate}][{column}]",
                    )
                    for column, code in enumerate(row)
                )
            )
        result.append(tuple(candidate_values))
    return tuple(result)


def _finite_head_weights(
    value: object,
    *,
    batch_size: int,
    sequence_length: int,
    head_count: int,
) -> BF16ValueBatch:
    raw_batches = _sequence(value, "head_weight_bf16_codes")
    if len(raw_batches) != batch_size:
        raise IndexScoreReferenceError(
            "head_weight_bf16_codes batch count must match query_bf16_codes"
        )

    result: list[BF16ValueMatrix] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(
            raw_sequence,
            f"head_weight_bf16_codes[{batch_index}]",
        )
        if len(sequence) != sequence_length:
            raise IndexScoreReferenceError(
                "head_weight_bf16_codes sequence length must match "
                "query_bf16_codes"
            )
        sequence_values: list[BF16ValueVector] = []
        for position, raw_row in enumerate(sequence):
            row = _sequence(
                raw_row,
                f"head_weight_bf16_codes[{batch_index}][{position}]",
            )
            if len(row) != head_count:
                raise IndexScoreReferenceError(
                    f"head_weight_bf16_codes[{batch_index}][{position}] must "
                    f"contain {head_count} heads"
                )
            sequence_values.append(
                tuple(
                    _finite_bf16(
                        code,
                        "head_weight_bf16_codes"
                        f"[{batch_index}][{position}][{head}]",
                    )
                    for head, code in enumerate(row)
                )
            )
        result.append(tuple(sequence_values))
    return tuple(result)


def _positive_binary32(value: object, label: str) -> tuple[int, Fraction]:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < 1 << 32
    ):
        raise IndexScoreReferenceError(f"{label} must be a binary32 encoding")
    decoded = decode_binary32(value)
    if not decoded.finite or decoded.value is None:
        raise IndexScoreReferenceError(f"{label} must be finite binary32")
    if decoded.value <= 0:
        raise IndexScoreReferenceError(f"{label} must be greater than zero")
    return value, decoded.value


def index_score_bf16(
    query_bf16_codes: Sequence[Sequence[Sequence[Sequence[int]]]],
    kv_bf16_codes: Sequence[Sequence[Sequence[int]]],
    head_weight_bf16_codes: Sequence[Sequence[Sequence[int]]],
    *,
    scale_binary32: int = INDEX_SCORE_SCALE_BINARY32,
) -> IndexScoreResult:
    """Produce one deterministic BF16 learned-index score per KV candidate.

    General nonzero head counts and dimensions are accepted for independent
    unit cases.  The graph-qualified profile fixes 64 heads, dimension 128,
    compression ratio four, and scale ``0x3c3504f3``.  A zero-length candidate
    axis is legal and produces empty score rows, matching short prefill spans.
    """

    query_values, sequence_length, head_count, head_dim = _finite_query(
        query_bf16_codes
    )
    kv_values = _finite_kv(
        kv_bf16_codes,
        batch_size=len(query_values),
        head_dim=head_dim,
    )
    head_weight_values = _finite_head_weights(
        head_weight_bf16_codes,
        batch_size=len(query_values),
        sequence_length=sequence_length,
        head_count=head_count,
    )
    _, scale_value = _positive_binary32(scale_binary32, "scale_binary32")

    scaled_weights: list[BF16ValueMatrix] = []
    scaled_weight_saturation = 0
    for sequence in head_weight_values:
        scaled_sequence: list[BF16ValueVector] = []
        for row in sequence:
            scaled_row: list[Fraction] = []
            for weight in row:
                quantized = encode_bf16_rne(weight * scale_value)
                scaled_weight_saturation += int(quantized.saturated)
                decoded = decode_bf16(quantized.code).value
                assert decoded is not None
                scaled_row.append(decoded)
            scaled_sequence.append(tuple(scaled_row))
        scaled_weights.append(tuple(scaled_sequence))

    qk_saturation = 0
    weighted_saturation = 0
    output_saturation = 0
    output_batches: list[tuple[tuple[int, ...], ...]] = []
    for batch_index, (query_sequence, kv_candidates, weight_sequence) in enumerate(
        zip(query_values, kv_values, scaled_weights, strict=True)
    ):
        output_sequence: list[tuple[int, ...]] = []
        for position, (query_heads, scaled_weight_row) in enumerate(
            zip(query_sequence, weight_sequence, strict=True)
        ):
            output_row: list[int] = []
            for candidate, kv_row in enumerate(kv_candidates):
                head_contributions: list[int] = []
                for head, (query_row, scaled_weight) in enumerate(
                    zip(query_heads, scaled_weight_row, strict=True)
                ):
                    try:
                        qk_binary32 = binary32_ordered_dot(query_row, kv_row)
                    except NumericReferenceError as exc:
                        raise IndexScoreReferenceError(
                            "index QK arithmetic failed at batch "
                            f"{batch_index}, position {position}, head {head}, "
                            f"candidate {candidate}: {exc}"
                        ) from exc
                    qk_bf16 = binary32_bits_to_bf16_rne(qk_binary32)
                    qk_saturation += int(qk_bf16.saturated)
                    qk_value = decode_bf16(qk_bf16.code).value
                    assert qk_value is not None
                    relu_value = qk_value if qk_value > 0 else Fraction(0)
                    weighted = encode_bf16_rne(relu_value * scaled_weight)
                    weighted_saturation += int(weighted.saturated)
                    weighted_value = decode_bf16(weighted.code).value
                    assert weighted_value is not None
                    head_contributions.append(encode_binary32_rne(weighted_value))
                try:
                    head_sum = binary32_balanced_sum(head_contributions)
                except NumericReferenceError as exc:
                    raise IndexScoreReferenceError(
                        "index head reduction failed at batch "
                        f"{batch_index}, position {position}, candidate "
                        f"{candidate}: {exc}"
                    ) from exc
                quantized_output = binary32_bits_to_bf16_rne(head_sum)
                output_saturation += int(quantized_output.saturated)
                output_row.append(quantized_output.code)
            output_sequence.append(tuple(output_row))
        output_batches.append(tuple(output_sequence))

    return IndexScoreResult(
        qk_saturated_element_count=qk_saturation,
        scaled_weight_saturated_element_count=scaled_weight_saturation,
        weighted_score_saturated_element_count=weighted_saturation,
        output_saturated_element_count=output_saturation,
        values=tuple(output_batches),
    )


__all__ = [
    "BF16_MAX_ENCODING",
    "INDEX_SCORE_COMPRESSION_RATIO",
    "INDEX_SCORE_HEAD_DIM",
    "INDEX_SCORE_HEADS",
    "INDEX_SCORE_SCALE_BINARY32",
    "INDEX_SCORE_SITE_COUNT",
    "MODEL_SOURCE_SHA256",
    "BF16Batch",
    "BF16Matrix",
    "BF16ScoreBatch",
    "BF16Vector",
    "IndexScoreReferenceError",
    "IndexScoreResult",
    "index_score_bf16",
]
