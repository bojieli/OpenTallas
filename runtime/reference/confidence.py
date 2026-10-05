"""Deterministic DeepSeek V4 DSpark confidence-score semantics.

The pinned final DSpark stage concatenates its BF16 hidden row with the BF16
Markov embedding, widens both and the checkpoint BF16 projection weight to
binary32, and executes one bias-free ``F.linear`` output.  This reference fixes
an increasing-reduction-index binary32 accumulation without using host
floating-point arithmetic.
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_ordered_dot,
    decode_bf16,
)


MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
CONFIDENCE_HIDDEN_WIDTH = 4096
CONFIDENCE_MARKOV_WIDTH = 256
CONFIDENCE_INPUT_WIDTH = CONFIDENCE_HIDDEN_WIDTH + CONFIDENCE_MARKOV_WIDTH
CONFIDENCE_OUTPUTS = 1
CONFIDENCE_BLOCK_SIZE = 5
BF16_MAX_ENCODING = (1 << 16) - 1

BF16Vector: TypeAlias = tuple[int, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Sequence, ...]
BF16ValueBatch: TypeAlias = tuple[tuple[tuple[Fraction, ...], ...], ...]
Binary32Sequence: TypeAlias = tuple[int, ...]
Binary32Batch: TypeAlias = tuple[Binary32Sequence, ...]


class ConfidenceReferenceError(ValueError):
    """Raised when confidence-score inputs violate the target contract."""


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ConfidenceReferenceError(f"{label} must be a sequence")
    return value


def _finite_bf16_batch(
    value: object,
    label: str,
) -> BF16ValueBatch:
    raw_batches = _sequence(value, label)
    if not raw_batches:
        raise ConfidenceReferenceError(f"{label} must contain at least one batch")
    batch_values: list[tuple[tuple[Fraction, ...], ...]] = []
    sequence_length: int | None = None
    width: int | None = None
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"{label}[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise ConfidenceReferenceError(
                    f"{label} must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise ConfidenceReferenceError(
                f"{label} must be a rectangular rank-3 tensor"
            )

        sequence_values: list[tuple[Fraction, ...]] = []
        for position, raw_row in enumerate(sequence):
            row = _sequence(raw_row, f"{label}[{batch_index}][{position}]")
            if width is None:
                width = len(row)
                if width == 0:
                    raise ConfidenceReferenceError(
                        f"{label} rows must contain at least one BF16 value"
                    )
            elif len(row) != width:
                raise ConfidenceReferenceError(
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
                    raise ConfidenceReferenceError(
                        f"{element_label} must be a 16-bit BF16 encoding"
                    )
                decoded = decode_bf16(code)
                if not decoded.finite or decoded.value is None:
                    raise ConfidenceReferenceError(
                        f"{element_label} must be finite BF16"
                    )
                row_values.append(decoded.value)
            sequence_values.append(tuple(row_values))
        batch_values.append(tuple(sequence_values))
    return tuple(batch_values)


def _finite_bf16_weight(
    value: object,
    *,
    expected_width: int,
) -> tuple[Fraction, ...]:
    raw_rows = _sequence(value, "weight_bf16_codes")
    if len(raw_rows) != CONFIDENCE_OUTPUTS:
        raise ConfidenceReferenceError(
            "weight_bf16_codes must contain exactly one confidence output row"
        )
    row = _sequence(raw_rows[0], "weight_bf16_codes[0]")
    if len(row) != expected_width:
        raise ConfidenceReferenceError(
            f"weight_bf16_codes[0] must have concatenated width {expected_width}"
        )
    result: list[Fraction] = []
    for column, code in enumerate(row):
        label = f"weight_bf16_codes[0][{column}]"
        if (
            isinstance(code, bool)
            or not isinstance(code, int)
            or not 0 <= code <= BF16_MAX_ENCODING
        ):
            raise ConfidenceReferenceError(f"{label} must be a 16-bit BF16 encoding")
        decoded = decode_bf16(code)
        if not decoded.finite or decoded.value is None:
            raise ConfidenceReferenceError(f"{label} must be finite BF16")
        result.append(decoded.value)
    return tuple(result)


def confidence_score_bf16(
    hidden_bf16_codes: Sequence[Sequence[Sequence[int]]],
    markov_bf16_codes: Sequence[Sequence[Sequence[int]]],
    weight_bf16_codes: Sequence[Sequence[int]],
) -> Binary32Batch:
    """Concatenate BF16 rows and project one architectural binary32 score.

    The public reference accepts general nonzero hidden and Markov widths so
    small independent cases remain practical.  The graph-qualified profile is
    fixed separately at 4,096 plus 256 inputs and five draft positions.
    """

    hidden_values = _finite_bf16_batch(
        hidden_bf16_codes,
        "hidden_bf16_codes",
    )
    markov_values = _finite_bf16_batch(
        markov_bf16_codes,
        "markov_bf16_codes",
    )
    if len(markov_values) != len(hidden_values) or len(markov_values[0]) != len(
        hidden_values[0]
    ):
        raise ConfidenceReferenceError(
            "markov_bf16_codes batch and sequence shape must match hidden_bf16_codes"
        )

    concatenated_width = len(hidden_values[0][0]) + len(markov_values[0][0])
    weight_values = _finite_bf16_weight(
        weight_bf16_codes,
        expected_width=concatenated_width,
    )
    output: list[Binary32Sequence] = []
    for batch_index, (hidden_sequence, markov_sequence) in enumerate(
        zip(hidden_values, markov_values, strict=True)
    ):
        output_sequence: list[int] = []
        for position, (hidden_row, markov_row) in enumerate(
            zip(hidden_sequence, markov_sequence, strict=True)
        ):
            try:
                output_sequence.append(
                    binary32_ordered_dot(hidden_row + markov_row, weight_values)
                )
            except NumericReferenceError as exc:
                raise ConfidenceReferenceError(
                    f"confidence-score arithmetic failed at batch {batch_index}, "
                    f"position {position}: {exc}"
                ) from exc
        output.append(tuple(output_sequence))
    return tuple(output)


__all__ = [
    "BF16_MAX_ENCODING",
    "CONFIDENCE_BLOCK_SIZE",
    "CONFIDENCE_HIDDEN_WIDTH",
    "CONFIDENCE_INPUT_WIDTH",
    "CONFIDENCE_MARKOV_WIDTH",
    "CONFIDENCE_OUTPUTS",
    "MODEL_SOURCE_SHA256",
    "BF16Batch",
    "BF16Sequence",
    "BF16Vector",
    "Binary32Batch",
    "Binary32Sequence",
    "ConfidenceReferenceError",
    "confidence_score_bf16",
]
