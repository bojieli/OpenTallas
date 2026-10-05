"""Independent exact BF16 matrix oracle for the tensor accelerator.

This module defines the first real-model tensor numeric contract.  It imports no
compiler, simulator, NumPy, PyTorch, or model implementation.  Every scalar is
represented by its architectural encoding and composed from the exact binary32
reference primitives in :mod:`runtime.reference.formats`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_multiply,
    decode_bf16,
)


NUMERIC_CONTRACT = "bf16_bf16_fp32_sequential_rne_v1"
BF16Matrix: TypeAlias = tuple[tuple[int, ...], ...]


class BF16MatrixReferenceError(ValueError):
    """Raised when a matrix or arithmetic event violates the contract."""


@dataclass(frozen=True)
class BF16LinearResult:
    """Exact output codes and sticky final-conversion saturation count."""

    output_saturated_element_count: int
    values: BF16Matrix


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise BF16MatrixReferenceError(f"{label} must be a sequence")
    return value


def _rectangular_finite_bf16(
    value: object,
    label: str,
    *,
    expected_width: int | None = None,
) -> BF16Matrix:
    raw_rows = _sequence(value, label)
    if not raw_rows:
        raise BF16MatrixReferenceError(f"{label} must contain at least one row")
    width = expected_width
    result: list[tuple[int, ...]] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"{label}[{row_index}]")
        if width is None:
            width = len(row)
            if width == 0:
                raise BF16MatrixReferenceError(
                    f"{label} rows must contain at least one element"
                )
        elif len(row) != width:
            raise BF16MatrixReferenceError(
                f"{label} must be rectangular with width {width}"
            )
        output_row: list[int] = []
        for column, code in enumerate(row):
            item_label = f"{label}[{row_index}][{column}]"
            if (
                isinstance(code, bool)
                or not isinstance(code, int)
                or not 0 <= code < 1 << 16
            ):
                raise BF16MatrixReferenceError(
                    f"{item_label} must be a 16-bit BF16 encoding"
                )
            if not decode_bf16(code).finite:
                raise BF16MatrixReferenceError(f"{item_label} must be finite BF16")
            output_row.append(code)
        result.append(tuple(output_row))
    return tuple(result)


def _selected_indices(
    raw: object,
    *,
    declared_output_count: int,
) -> tuple[int, ...]:
    values = _sequence(raw, "output_row_indices")
    result: list[int] = []
    for position, index in enumerate(values):
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or not 0 <= index < declared_output_count
        ):
            raise BF16MatrixReferenceError(
                f"output_row_indices[{position}] must be in "
                f"[0, {declared_output_count})"
            )
        result.append(index)
    indices = tuple(result)
    if not indices or indices != tuple(sorted(set(indices))):
        raise BF16MatrixReferenceError(
            "output_row_indices must be nonempty, unique, and strictly increasing"
        )
    return indices


def dense_bf16_linear_bf16(
    input_codes: Sequence[Sequence[int]],
    weight_codes: Sequence[Sequence[int]],
) -> BF16LinearResult:
    """Execute the complete ``[M,K] @ [N,K]^T`` target operation."""

    raw_weights = _sequence(weight_codes, "weight_codes")
    return _dense_bf16_linear_bf16(
        input_codes,
        raw_weights,
        output_row_indices=tuple(range(len(raw_weights))),
        declared_output_count=len(raw_weights),
    )


def dense_bf16_linear_selected_rows_bf16(
    input_codes: Sequence[Sequence[int]],
    selected_weight_codes: Sequence[Sequence[int]],
    *,
    output_row_indices: Sequence[int],
    declared_output_count: int,
) -> BF16LinearResult:
    """Execute explicitly selected logical output rows for evidence slices."""

    if (
        isinstance(declared_output_count, bool)
        or not isinstance(declared_output_count, int)
        or declared_output_count < 1
    ):
        raise BF16MatrixReferenceError(
            "declared_output_count must be an integer >= 1"
        )
    indices = _selected_indices(
        output_row_indices,
        declared_output_count=declared_output_count,
    )
    raw_weights = _sequence(selected_weight_codes, "selected_weight_codes")
    if len(raw_weights) != len(indices):
        raise BF16MatrixReferenceError(
            "selected weight row count must match output_row_indices"
        )
    return _dense_bf16_linear_bf16(
        input_codes,
        raw_weights,
        output_row_indices=indices,
        declared_output_count=declared_output_count,
    )


def _dense_bf16_linear_bf16(
    input_codes: object,
    weight_codes: object,
    *,
    output_row_indices: tuple[int, ...],
    declared_output_count: int,
) -> BF16LinearResult:
    inputs = _rectangular_finite_bf16(input_codes, "input_codes")
    reduction = len(inputs[0])
    weights = _rectangular_finite_bf16(
        weight_codes,
        "weight_codes",
        expected_width=reduction,
    )
    if len(weights) != len(output_row_indices) or any(
        index >= declared_output_count for index in output_row_indices
    ):
        raise BF16MatrixReferenceError("logical output-row metadata is inconsistent")

    output: list[tuple[int, ...]] = []
    saturation_count = 0
    try:
        for input_index, input_row in enumerate(inputs):
            output_row: list[int] = []
            for weight_index, weight_row in enumerate(weights):
                accumulator = 0
                for left, right in zip(input_row, weight_row, strict=True):
                    # A BF16 encoding promoted by appending sixteen zero bits is
                    # the exact same value in IEEE binary32.
                    product = binary32_multiply(left << 16, right << 16)
                    accumulator = binary32_add(accumulator, product)
                converted = binary32_bits_to_bf16_rne(accumulator)
                saturation_count += int(converted.saturated)
                output_row.append(converted.code)
            output.append(tuple(output_row))
    except NumericReferenceError as exc:
        raise BF16MatrixReferenceError(
            f"BF16 linear arithmetic failed at input row {input_index}, "
            f"weight row {weight_index}: {exc}"
        ) from exc
    return BF16LinearResult(saturation_count, tuple(output))


__all__ = [
    "BF16LinearResult",
    "BF16Matrix",
    "BF16MatrixReferenceError",
    "NUMERIC_CONTRACT",
    "dense_bf16_linear_bf16",
    "dense_bf16_linear_selected_rows_bf16",
]
