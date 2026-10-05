"""Deterministic DeepSeek V4 compressor-projection semantics.

The pinned compressor widens each BF16 hidden row to binary32 and applies two
independent bias-free projections: one produces KV candidates and one produces
learned pooling scores.  Both runtime parameters are exact binary32 widenings
of BF16 checkpoint tensors.  This reference fixes increasing-reduction-index
binary32 accumulation without using host floating-point arithmetic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from .formats import NumericReferenceError, binary32_ordered_dot, decode_bf16


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
COMPRESS_INPUT_FEATURES = 4096
MAIN_RATIO4_OUTPUT_FEATURES = 1024
MAIN_RATIO128_OUTPUT_FEATURES = 512
INDEX_RATIO4_OUTPUT_FEATURES = 256
COMPRESS_OUTPUT_FEATURE_PROFILES = (
    INDEX_RATIO4_OUTPUT_FEATURES,
    MAIN_RATIO128_OUTPUT_FEATURES,
    MAIN_RATIO4_OUTPUT_FEATURES,
)
BF16_MAX_ENCODING = (1 << 16) - 1

BF16Vector: TypeAlias = tuple[int, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Sequence, ...]
BF16ValueBatch: TypeAlias = tuple[tuple[tuple[Fraction, ...], ...], ...]
BF16ValueMatrix: TypeAlias = tuple[tuple[Fraction, ...], ...]
Binary32Vector: TypeAlias = tuple[int, ...]
Binary32Sequence: TypeAlias = tuple[Binary32Vector, ...]
Binary32Batch: TypeAlias = tuple[Binary32Sequence, ...]


class CompressionReferenceError(ValueError):
    """Raised when compressor-projection inputs violate the target contract."""


@dataclass(frozen=True)
class CompressProjectResult:
    """Binary32 KV candidates and learned pooling-score tensors."""

    kv: Binary32Batch
    scores: Binary32Batch


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise CompressionReferenceError(f"{label} must be a sequence")
    return value


def _finite_bf16_batch(value: object, label: str) -> BF16ValueBatch:
    raw_batches = _sequence(value, label)
    if not raw_batches:
        raise CompressionReferenceError(f"{label} must contain at least one batch")

    batch_values: list[tuple[tuple[Fraction, ...], ...]] = []
    sequence_length: int | None = None
    width: int | None = None
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"{label}[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise CompressionReferenceError(
                    f"{label} must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise CompressionReferenceError(
                f"{label} must be a rectangular rank-3 tensor"
            )

        sequence_values: list[tuple[Fraction, ...]] = []
        for position, raw_row in enumerate(sequence):
            row = _sequence(raw_row, f"{label}[{batch_index}][{position}]")
            if width is None:
                width = len(row)
                if width == 0:
                    raise CompressionReferenceError(
                        f"{label} rows must contain at least one BF16 value"
                    )
            elif len(row) != width:
                raise CompressionReferenceError(
                    f"{label} must be a rectangular rank-3 tensor"
                )

            row_values: list[Fraction] = []
            for column, code in enumerate(row):
                element_label = f"{label}[{batch_index}][{position}][{column}]"
                if (
                    isinstance(code, bool)
                    or not isinstance(code, int)
                    or not 0 <= code <= BF16_MAX_ENCODING
                ):
                    raise CompressionReferenceError(
                        f"{element_label} must be a 16-bit BF16 encoding"
                    )
                decoded = decode_bf16(code)
                if not decoded.finite or decoded.value is None:
                    raise CompressionReferenceError(
                        f"{element_label} must be finite BF16"
                    )
                row_values.append(decoded.value)
            sequence_values.append(tuple(row_values))
        batch_values.append(tuple(sequence_values))
    return tuple(batch_values)


def _finite_bf16_weight(
    value: object,
    label: str,
    *,
    expected_width: int,
) -> BF16ValueMatrix:
    raw_rows = _sequence(value, label)
    if not raw_rows:
        raise CompressionReferenceError(
            f"{label} must contain at least one output row"
        )

    result: list[tuple[Fraction, ...]] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"{label}[{row_index}]")
        if len(row) != expected_width:
            raise CompressionReferenceError(
                f"{label}[{row_index}] must have input width {expected_width}"
            )
        row_values: list[Fraction] = []
        for column, code in enumerate(row):
            element_label = f"{label}[{row_index}][{column}]"
            if (
                isinstance(code, bool)
                or not isinstance(code, int)
                or not 0 <= code <= BF16_MAX_ENCODING
            ):
                raise CompressionReferenceError(
                    f"{element_label} must be a 16-bit BF16 encoding"
                )
            decoded = decode_bf16(code)
            if not decoded.finite or decoded.value is None:
                raise CompressionReferenceError(
                    f"{element_label} must be finite BF16"
                )
            row_values.append(decoded.value)
        result.append(tuple(row_values))
    return tuple(result)


def _project_row(
    input_values: tuple[Fraction, ...],
    weight_values: BF16ValueMatrix,
    *,
    batch_index: int,
    position: int,
    projection: str,
) -> Binary32Vector:
    output: list[int] = []
    for output_index, weight_row in enumerate(weight_values):
        try:
            output.append(binary32_ordered_dot(input_values, weight_row))
        except NumericReferenceError as exc:
            raise CompressionReferenceError(
                f"compressor {projection} arithmetic failed at batch "
                f"{batch_index}, position {position}, output {output_index}: {exc}"
            ) from exc
    return tuple(output)


def compress_project_bf16(
    hidden_bf16_codes: Sequence[Sequence[Sequence[int]]],
    kv_weight_bf16_codes: Sequence[Sequence[int]],
    gate_weight_bf16_codes: Sequence[Sequence[int]],
) -> CompressProjectResult:
    """Apply independent BF16-checkpoint KV and gate projections to BF16 rows.

    The public reference accepts general nonzero rectangular shapes so small
    independent cases remain practical.  The graph-qualified profiles use
    4,096 input columns and 256, 512, or 1,024 output columns for each of the
    two projections.
    """

    hidden_values = _finite_bf16_batch(hidden_bf16_codes, "hidden_bf16_codes")
    input_width = len(hidden_values[0][0])
    kv_weight_values = _finite_bf16_weight(
        kv_weight_bf16_codes,
        "kv_weight_bf16_codes",
        expected_width=input_width,
    )
    gate_weight_values = _finite_bf16_weight(
        gate_weight_bf16_codes,
        "gate_weight_bf16_codes",
        expected_width=input_width,
    )
    if len(gate_weight_values) != len(kv_weight_values):
        raise CompressionReferenceError(
            "gate_weight_bf16_codes output count must match "
            "kv_weight_bf16_codes"
        )

    kv_batches: list[Binary32Sequence] = []
    score_batches: list[Binary32Sequence] = []
    for batch_index, sequence in enumerate(hidden_values):
        kv_sequence: list[Binary32Vector] = []
        score_sequence: list[Binary32Vector] = []
        for position, hidden_row in enumerate(sequence):
            kv_sequence.append(
                _project_row(
                    hidden_row,
                    kv_weight_values,
                    batch_index=batch_index,
                    position=position,
                    projection="KV",
                )
            )
            score_sequence.append(
                _project_row(
                    hidden_row,
                    gate_weight_values,
                    batch_index=batch_index,
                    position=position,
                    projection="gate",
                )
            )
        kv_batches.append(tuple(kv_sequence))
        score_batches.append(tuple(score_sequence))
    return CompressProjectResult(
        kv=tuple(kv_batches),
        scores=tuple(score_batches),
    )


__all__ = [
    "BF16_MAX_ENCODING",
    "COMPRESS_INPUT_FEATURES",
    "COMPRESS_OUTPUT_FEATURE_PROFILES",
    "INDEX_RATIO4_OUTPUT_FEATURES",
    "MAIN_RATIO4_OUTPUT_FEATURES",
    "MAIN_RATIO128_OUTPUT_FEATURES",
    "MODEL_SOURCE_SHA256",
    "BF16Batch",
    "BF16Sequence",
    "BF16Vector",
    "Binary32Batch",
    "Binary32Sequence",
    "Binary32Vector",
    "CompressProjectResult",
    "CompressionReferenceError",
    "compress_project_bf16",
]
