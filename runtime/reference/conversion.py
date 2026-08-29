"""Atomic finite-binary32 to BF16 tensor conversion semantics.

This is the tensor-level NUM-4.2 boundary used by the pinned DeepSeek V4
compressor's ``kv.to(dtype)`` immediately after FP32 pooling and before
RMSNorm.  It exists as a separate graph operation so the FP32 pool output is
not silently consumed by a BF16-only normalization reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from .formats import binary32_bits_to_bf16_rne, decode_binary32


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
BINARY32_TO_BF16_PROFILE = "opentallas.binary32_tensor_to_bf16_rne_sat.v1"
BINARY32_BYTES = 4
BF16_BYTES = 2
BINARY32_MAX_ENCODING = (1 << 32) - 1


Binary32Vector: TypeAlias = tuple[int, ...]
Binary32Sequence: TypeAlias = tuple[Binary32Vector, ...]
Binary32Tensor: TypeAlias = tuple[Binary32Sequence, ...]
BF16Vector: TypeAlias = tuple[int, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Tensor: TypeAlias = tuple[BF16Sequence, ...]


class ConversionReferenceError(ValueError):
    """Raised when a tensor conversion is malformed or poisoned."""


@dataclass(frozen=True)
class Binary32ToBF16Counters:
    """Exact logical tensor traffic and visible conversion status."""

    batch_count: int
    sequence_length: int
    width: int
    input_binary32_values: int
    logical_input_read_bytes: int
    output_bf16_values: int
    logical_output_write_bytes: int
    finite_saturation_count: int
    transaction_commits: int


@dataclass(frozen=True)
class Binary32ToBF16Result:
    """Converted immutable tensor and exact logical counters."""

    bf16_codes: BF16Tensor
    counters: Binary32ToBF16Counters


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise ConversionReferenceError(f"{label} must be an exact list or tuple")
    return value


def binary32_tensor_to_bf16_rne(value: object) -> Binary32ToBF16Result:
    """Convert one rectangular finite rank-three tensor under NUM-4.2.

    Every encoding validates before conversion begins, and the result is built
    off to the side before its single immutable commit.  The graph invokes this
    only when compressor pooling produced at least one complete row.
    """

    raw_batches = _sequence(value, "binary32_codes")
    if not raw_batches:
        raise ConversionReferenceError("binary32_codes must contain at least one batch")
    sequence_length: int | None = None
    width: int | None = None
    frozen: list[Binary32Sequence] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"binary32_codes[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length < 1:
                raise ConversionReferenceError(
                    "binary32_codes must contain at least one row per batch"
                )
        elif len(sequence) != sequence_length:
            raise ConversionReferenceError(
                "binary32_codes must be rectangular on the sequence axis"
            )
        rows: list[Binary32Vector] = []
        for row_index, raw_row in enumerate(sequence):
            row = _sequence(
                raw_row,
                f"binary32_codes[{batch_index}][{row_index}]",
            )
            if width is None:
                width = len(row)
                if width < 1:
                    raise ConversionReferenceError(
                        "binary32_codes rows must contain at least one value"
                    )
            elif len(row) != width:
                raise ConversionReferenceError(
                    "binary32_codes must be rectangular on the value axis"
                )
            frozen_row: list[int] = []
            for column, code in enumerate(row):
                label = f"binary32_codes[{batch_index}][{row_index}][{column}]"
                if type(code) is not int or not 0 <= code <= BINARY32_MAX_ENCODING:
                    raise ConversionReferenceError(
                        f"{label} must be a 32-bit binary32 encoding"
                    )
                decoded = decode_binary32(code)
                if not decoded.finite or decoded.value is None:
                    raise ConversionReferenceError(f"{label} must be finite binary32")
                frozen_row.append(code)
            rows.append(tuple(frozen_row))
        frozen.append(tuple(rows))
    assert sequence_length is not None
    assert width is not None

    saturation_count = 0
    output: list[BF16Sequence] = []
    for sequence in frozen:
        converted_rows: list[BF16Vector] = []
        for row in sequence:
            converted_row: list[int] = []
            for code in row:
                converted = binary32_bits_to_bf16_rne(code)
                saturation_count += int(converted.saturated)
                converted_row.append(converted.code)
            converted_rows.append(tuple(converted_row))
        output.append(tuple(converted_rows))

    value_count = len(frozen) * sequence_length * width
    return Binary32ToBF16Result(
        bf16_codes=tuple(output),
        counters=Binary32ToBF16Counters(
            batch_count=len(frozen),
            sequence_length=sequence_length,
            width=width,
            input_binary32_values=value_count,
            logical_input_read_bytes=value_count * BINARY32_BYTES,
            output_bf16_values=value_count,
            logical_output_write_bytes=value_count * BF16_BYTES,
            finite_saturation_count=saturation_count,
            transaction_commits=1,
        ),
    )


__all__ = [
    "BF16_BYTES",
    "BINARY32_BYTES",
    "BINARY32_MAX_ENCODING",
    "BINARY32_TO_BF16_PROFILE",
    "MODEL_SOURCE_SHA256",
    "Binary32ToBF16Counters",
    "Binary32ToBF16Result",
    "ConversionReferenceError",
    "binary32_tensor_to_bf16_rne",
]
