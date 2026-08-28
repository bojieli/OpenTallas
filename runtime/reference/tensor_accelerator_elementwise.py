"""Independent scalar BF16 elementwise contracts for Qwen decoder layers.

The module imports no compiler, simulator, array package, framework, or model
implementation.  Inputs and outputs are architectural BF16 encodings.  It
defines the exact residual-add boundary and the materialized-BF16 SiLU/gating
boundary used by the pinned Qwen3 decoder source.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_exp_nonpositive,
    binary32_multiply,
    decode_bf16,
)


ADD_NUMERIC_CONTRACT = "bf16_add_rne_v1"
SILU_MUL_NUMERIC_CONTRACT = "qwen3_silu_mul_bf16_v1"
BF16Matrix: TypeAlias = tuple[tuple[int, ...], ...]


class ElementwiseReferenceError(ValueError):
    """Raised when an elementwise input or arithmetic event is illegal."""


@dataclass(frozen=True)
class BF16AddReferenceResult:
    """Exact BF16 residual-add values and sticky saturation count."""

    output_saturated_element_count: int
    values: BF16Matrix


@dataclass(frozen=True)
class SiLUMultiplyReferenceResult:
    """Exact materialized SiLU and gated BF16 values plus sticky status."""

    activation_saturated_element_count: int
    activation_values: BF16Matrix
    output_saturated_element_count: int
    values: BF16Matrix


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ElementwiseReferenceError(f"{label} must be a sequence")
    return value


def _matrix(value: object, label: str) -> BF16Matrix:
    rows = _sequence(value, label)
    if not rows:
        raise ElementwiseReferenceError(f"{label} must contain at least one row")
    width: int | None = None
    result: list[tuple[int, ...]] = []
    for row_index, raw_row in enumerate(rows):
        row = _sequence(raw_row, f"{label}[{row_index}]")
        if width is None:
            width = len(row)
            if width == 0:
                raise ElementwiseReferenceError(
                    f"{label} rows must contain at least one element"
                )
        elif len(row) != width:
            raise ElementwiseReferenceError(f"{label} must be rectangular")
        parsed: list[int] = []
        for column, code in enumerate(row):
            item_label = f"{label}[{row_index}][{column}]"
            if (
                isinstance(code, bool)
                or not isinstance(code, int)
                or not 0 <= code <= 0xFFFF
            ):
                raise ElementwiseReferenceError(
                    f"{item_label} must be a 16-bit BF16 encoding"
                )
            if not decode_bf16(code).finite:
                raise ElementwiseReferenceError(f"{item_label} must be finite BF16")
            parsed.append(code)
        result.append(tuple(parsed))
    return tuple(result)


def _same_shape(left: BF16Matrix, right: BF16Matrix, label: str) -> None:
    if len(left) != len(right) or any(
        len(left_row) != len(right_row)
        for left_row, right_row in zip(left, right, strict=False)
    ):
        raise ElementwiseReferenceError(f"{label} shapes differ")


def bf16_add_rne(
    left_codes: Sequence[Sequence[int]],
    right_codes: Sequence[Sequence[int]],
) -> BF16AddReferenceResult:
    """Add equal-shape BF16 tensors through one binary32 RNE boundary."""

    left = _matrix(left_codes, "left_codes")
    right = _matrix(right_codes, "right_codes")
    _same_shape(left, right, "add operand")
    rows: list[tuple[int, ...]] = []
    saturated = 0
    try:
        for row_index, (left_row, right_row) in enumerate(
            zip(left, right, strict=True)
        ):
            output: list[int] = []
            for column, (left_code, right_code) in enumerate(
                zip(left_row, right_row, strict=True)
            ):
                summed = binary32_add(left_code << 16, right_code << 16)
                converted = binary32_bits_to_bf16_rne(summed)
                saturated += int(converted.saturated)
                output.append(converted.code)
            rows.append(tuple(output))
    except NumericReferenceError as exc:
        raise ElementwiseReferenceError(
            f"BF16 add arithmetic failed at [{row_index}][{column}]: {exc}"
        ) from exc
    return BF16AddReferenceResult(saturated, tuple(rows))


def _sigmoid_binary32_from_bf16(code: int) -> int:
    """Execute the stable, explicitly rounded sigmoid subgraph."""

    value = code << 16
    if code & 0x8000:
        exponential = binary32_exp_nonpositive(value)
        denominator = binary32_add(0x3F800000, exponential)
        return binary32_divide(exponential, denominator)
    negated = 0 if value & 0x7FFFFFFF == 0 else value ^ 0x80000000
    exponential = binary32_exp_nonpositive(negated)
    denominator = binary32_add(0x3F800000, exponential)
    return binary32_divide(0x3F800000, denominator)


def qwen3_silu_mul_bf16(
    gate_codes: Sequence[Sequence[int]],
    up_codes: Sequence[Sequence[int]],
) -> SiLUMultiplyReferenceResult:
    """Apply Qwen SiLU, materialize BF16, and multiply the BF16 up path.

    For each gate value, sigmoid uses the stable sign-selected form with one
    correctly rounded binary32 exponential, one binary32 denominator addition,
    and one binary32 division.  The gate/sigmoid product converts once to BF16.
    That materialized BF16 activation is then multiplied by the BF16 up value
    and converted once more to BF16.
    """

    gate = _matrix(gate_codes, "gate_codes")
    up = _matrix(up_codes, "up_codes")
    _same_shape(gate, up, "SiLU-multiply operand")
    activation_rows: list[tuple[int, ...]] = []
    output_rows: list[tuple[int, ...]] = []
    activation_saturated = 0
    output_saturated = 0
    try:
        for row_index, (gate_row, up_row) in enumerate(zip(gate, up, strict=True)):
            activations: list[int] = []
            outputs: list[int] = []
            for column, (gate_code, up_code) in enumerate(
                zip(gate_row, up_row, strict=True)
            ):
                sigmoid = _sigmoid_binary32_from_bf16(gate_code)
                silu_binary32 = binary32_multiply(gate_code << 16, sigmoid)
                activation = binary32_bits_to_bf16_rne(silu_binary32)
                activation_saturated += int(activation.saturated)
                gated_binary32 = binary32_multiply(
                    activation.code << 16,
                    up_code << 16,
                )
                output = binary32_bits_to_bf16_rne(gated_binary32)
                output_saturated += int(output.saturated)
                activations.append(activation.code)
                outputs.append(output.code)
            activation_rows.append(tuple(activations))
            output_rows.append(tuple(outputs))
    except NumericReferenceError as exc:
        raise ElementwiseReferenceError(
            f"Qwen SiLU-multiply arithmetic failed at [{row_index}][{column}]: {exc}"
        ) from exc
    return SiLUMultiplyReferenceResult(
        activation_saturated,
        tuple(activation_rows),
        output_saturated,
        tuple(output_rows),
    )


__all__ = [
    "ADD_NUMERIC_CONTRACT",
    "BF16AddReferenceResult",
    "BF16Matrix",
    "ElementwiseReferenceError",
    "SILU_MUL_NUMERIC_CONTRACT",
    "SiLUMultiplyReferenceResult",
    "bf16_add_rne",
    "qwen3_silu_mul_bf16",
]
