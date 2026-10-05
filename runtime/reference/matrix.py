"""Exact dense-matrix references for pinned DeepSeek V4 FP8 and BF16 paths.

The FP8 implementation composes scalar and 128-value block contracts into the
complete ``FP8_LINEAR`` operator. The distinct BF16 implementation defines the
indexer's 4,096-to-64 ``F.linear`` path with increasing-reduction-index
binary32 accumulation. No host floating-point arithmetic participates.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from .formats import (
    DENSE_REDUCTION_BLOCK,
    NumericReferenceError,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_ordered_dot,
    decode_bf16,
    fp8_fp8_block_dot,
    quantize_bf16_activation_block,
)


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
DENSE_OUTPUT_SCALE_BLOCK = 128
BF16_LINEAR_INPUT_FEATURES = 4096
BF16_LINEAR_OUTPUT_FEATURES = 64

BF16Matrix: TypeAlias = tuple[tuple[int, ...], ...]
FP8Matrix: TypeAlias = tuple[tuple[int, ...], ...]
E8M0Matrix: TypeAlias = tuple[tuple[int, ...], ...]


class MatrixReferenceError(ValueError):
    """Raised when dense matrix metadata or target arithmetic is invalid."""


@dataclass(frozen=True)
class DenseFP8LinearResult:
    """BF16 result codes and sticky saturation event counts."""

    activation_saturated_block_count: int
    output_saturated_element_count: int
    values: BF16Matrix


@dataclass(frozen=True)
class BF16LinearResult:
    """BF16 matrix result plus the sticky finite-output saturation count."""

    output_saturated_element_count: int
    values: BF16Matrix


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise MatrixReferenceError(f"{label} must be a sequence")
    return value


def _unsigned(value: object, maximum: int, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= maximum
    ):
        raise MatrixReferenceError(f"{label} must be in [0, {maximum}]")
    return value


def _rectangular_codes(
    value: object,
    label: str,
    *,
    maximum: int,
    expected_width: int | None = None,
) -> tuple[tuple[int, ...], ...]:
    raw_rows = _sequence(value, label)
    if not raw_rows:
        raise MatrixReferenceError(f"{label} must contain at least one row")
    width = expected_width
    result: list[tuple[int, ...]] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"{label}[{row_index}]")
        if width is None:
            width = len(row)
            if width == 0:
                raise MatrixReferenceError(
                    f"{label} rows must contain at least one element"
                )
        elif len(row) != width:
            raise MatrixReferenceError(f"{label} must be rectangular with width {width}")
        result.append(
            tuple(
                _unsigned(code, maximum, f"{label}[{row_index}][{column}]")
                for column, code in enumerate(row)
            )
        )
    return tuple(result)


def _finite_bf16_matrix(
    value: object,
    label: str,
    *,
    expected_width: int | None = None,
) -> tuple[tuple[Fraction, ...], ...]:
    codes = _rectangular_codes(
        value,
        label,
        maximum=(1 << 16) - 1,
        expected_width=expected_width,
    )
    result: list[tuple[Fraction, ...]] = []
    for row_index, row in enumerate(codes):
        decoded_row: list[Fraction] = []
        for column, code in enumerate(row):
            decoded = decode_bf16(code)
            if not decoded.finite or decoded.value is None:
                raise MatrixReferenceError(
                    f"{label}[{row_index}][{column}] must be finite BF16"
                )
            decoded_row.append(decoded.value)
        result.append(tuple(decoded_row))
    return tuple(result)


def bf16_linear_bf16(
    input_codes: Sequence[Sequence[int]],
    weight_codes: Sequence[Sequence[int]],
) -> BF16LinearResult:
    """Execute deterministic bias-free ``BF16_LINEAR`` matrix semantics.

    ``input_codes`` has shape ``[M, K]`` and ``weight_codes`` has shape
    ``[N, K]``. Each exact BF16 product is added to a binary32 accumulator in
    increasing logical K order with one RNE rounding per fused product-add. The
    completed accumulator converts once to BF16. This general matrix primitive
    covers the graph-qualified 4,096-to-64 profile without baking batch/sequence
    dimensions into the reference.
    """

    inputs = _finite_bf16_matrix(input_codes, "input_codes")
    reduction = len(inputs[0])
    weights = _finite_bf16_matrix(
        weight_codes,
        "weight_codes",
        expected_width=reduction,
    )

    output: list[tuple[int, ...]] = []
    saturation_count = 0
    for input_index, input_row in enumerate(inputs):
        output_row: list[int] = []
        for output_index, weight_row in enumerate(weights):
            try:
                accumulator = binary32_ordered_dot(input_row, weight_row)
                converted = binary32_bits_to_bf16_rne(accumulator)
            except NumericReferenceError as exc:
                raise MatrixReferenceError(
                    f"BF16 linear arithmetic failed at input row {input_index}, "
                    f"output row {output_index}: {exc}"
                ) from exc
            saturation_count += int(converted.saturated)
            output_row.append(converted.code)
        output.append(tuple(output_row))
    return BF16LinearResult(saturation_count, tuple(output))


def dense_fp8_linear_bf16(
    input_codes: Sequence[Sequence[int]],
    weight_codes: Sequence[Sequence[int]],
    weight_scale_codes: Sequence[Sequence[int]],
) -> DenseFP8LinearResult:
    """Execute target ``FP8_LINEAR`` semantics for a flattened input matrix.

    ``input_codes`` has shape ``[M, K]`` and ``weight_codes`` has shape
    ``[N, K]``. ``weight_scale_codes`` has shape
    ``[ceil(N / 128), K / 128]``. Each BF16 input block is quantized once and
    reused for every output row. Products accumulate in increasing reduction
    order inside each block; block partials reduce through the NUM-6.1 balanced
    tree; the final binary32 value rounds once to BF16.
    """

    raw_weights = _sequence(weight_codes, "weight_codes")
    return _dense_fp8_linear_bf16(
        input_codes,
        raw_weights,
        weight_scale_codes,
        output_row_indices=tuple(range(len(raw_weights))),
        declared_output_count=len(raw_weights),
    )


def dense_fp8_linear_selected_rows_bf16(
    input_codes: Sequence[Sequence[int]],
    selected_weight_codes: Sequence[Sequence[int]],
    weight_scale_codes: Sequence[Sequence[int]],
    *,
    output_row_indices: Sequence[int],
    declared_output_count: int,
) -> DenseFP8LinearResult:
    """Execute exact linear semantics for explicit logical output rows.

    This is an evidence-oriented projection of the complete operator. Weight
    rows are supplied in the same order as the strictly increasing logical
    ``output_row_indices``; scale lookup still uses the original logical output
    tile. ``declared_output_count`` binds the full matrix extent.
    """

    if (
        isinstance(declared_output_count, bool)
        or not isinstance(declared_output_count, int)
        or declared_output_count < 1
    ):
        raise MatrixReferenceError("declared_output_count must be an integer >= 1")
    raw_indices = _sequence(output_row_indices, "output_row_indices")
    indices = tuple(
        _unsigned(
            index,
            declared_output_count - 1,
            f"output_row_indices[{position}]",
        )
        for position, index in enumerate(raw_indices)
    )
    if not indices or indices != tuple(sorted(set(indices))):
        raise MatrixReferenceError(
            "output_row_indices must be non-empty, unique, and strictly increasing"
        )
    raw_weights = _sequence(selected_weight_codes, "selected_weight_codes")
    if len(raw_weights) != len(indices):
        raise MatrixReferenceError(
            "selected weight row count must match output_row_indices"
        )
    return _dense_fp8_linear_bf16(
        input_codes,
        raw_weights,
        weight_scale_codes,
        output_row_indices=indices,
        declared_output_count=declared_output_count,
    )


def _dense_fp8_linear_bf16(
    input_codes: Sequence[Sequence[int]],
    weight_codes: Sequence[Sequence[int]],
    weight_scale_codes: Sequence[Sequence[int]],
    *,
    output_row_indices: tuple[int, ...],
    declared_output_count: int,
) -> DenseFP8LinearResult:
    inputs = _rectangular_codes(input_codes, "input_codes", maximum=(1 << 16) - 1)
    reduction = len(inputs[0])
    if reduction % DENSE_REDUCTION_BLOCK:
        raise MatrixReferenceError(
            f"input reduction width must be divisible by {DENSE_REDUCTION_BLOCK}"
        )
    weights = _rectangular_codes(
        weight_codes,
        "weight_codes",
        maximum=(1 << 8) - 1,
        expected_width=reduction,
    )
    reduction_blocks = reduction // DENSE_REDUCTION_BLOCK
    scale_rows = (declared_output_count + DENSE_OUTPUT_SCALE_BLOCK - 1) // (
        DENSE_OUTPUT_SCALE_BLOCK
    )
    scales = _rectangular_codes(
        weight_scale_codes,
        "weight_scale_codes",
        maximum=(1 << 8) - 1,
        expected_width=reduction_blocks,
    )
    if len(scales) != scale_rows:
        raise MatrixReferenceError(
            "weight_scale_codes row count must equal ceil(output rows / 128)"
        )

    quantized_inputs = []
    activation_saturated_block_count = 0
    try:
        for input_index, input_row in enumerate(inputs):
            blocks = []
            for block_index in range(reduction_blocks):
                start = block_index * DENSE_REDUCTION_BLOCK
                block = quantize_bf16_activation_block(
                    input_row[start : start + DENSE_REDUCTION_BLOCK]
                )
                activation_saturated_block_count += int(block.saturated)
                blocks.append(block)
            quantized_inputs.append(tuple(blocks))
    except NumericReferenceError as exc:
        raise MatrixReferenceError(
            f"activation quantization failed for input row {input_index}: {exc}"
        ) from exc

    output: list[tuple[int, ...]] = []
    output_saturated_element_count = 0
    try:
        for input_index, activation_blocks in enumerate(quantized_inputs):
            output_row: list[int] = []
            for selected_index, weight_row in enumerate(weights):
                output_index = output_row_indices[selected_index]
                scale_row = scales[output_index // DENSE_OUTPUT_SCALE_BLOCK]
                partials = []
                for block_index, activation in enumerate(activation_blocks):
                    start = block_index * DENSE_REDUCTION_BLOCK
                    partials.append(
                        fp8_fp8_block_dot(
                            weight_row[start : start + DENSE_REDUCTION_BLOCK],
                            scale_row[block_index],
                            activation.value_codes,
                            activation.scale_code,
                        )
                    )
                accumulated = binary32_balanced_sum(partials)
                converted = binary32_bits_to_bf16_rne(accumulated)
                output_saturated_element_count += int(converted.saturated)
                output_row.append(converted.code)
            output.append(tuple(output_row))
    except NumericReferenceError as exc:
        raise MatrixReferenceError(
            f"dense FP8 arithmetic failed at input row {input_index}, "
            f"output row {output_index}: {exc}"
        ) from exc
    return DenseFP8LinearResult(
        activation_saturated_block_count,
        output_saturated_element_count,
        tuple(output),
    )


__all__ = [
    "BF16_LINEAR_INPUT_FEATURES",
    "BF16_LINEAR_OUTPUT_FEATURES",
    "BF16LinearResult",
    "DENSE_OUTPUT_SCALE_BLOCK",
    "MODEL_SOURCE_SHA256",
    "BF16Matrix",
    "DenseFP8LinearResult",
    "E8M0Matrix",
    "FP8Matrix",
    "MatrixReferenceError",
    "bf16_linear_bf16",
    "dense_fp8_linear_bf16",
    "dense_fp8_linear_selected_rows_bf16",
]
