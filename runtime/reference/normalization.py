"""Deterministic weighted RMS normalization for DeepSeek V4.

The pinned source widens BF16 activations to FP32, squares and means the last
axis, applies ``torch.rsqrt(var + 1e-6)``, multiplies the FP32-loaded checkpoint
weight, and converts back to the activation dtype. PyTorch does not freeze one
cross-backend reduction tree, so this target uses the NUM-6.1 balanced tree and
the correctly rounded binary32 reciprocal-square-root primitive.
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
    binary32_rsqrt,
    decode_bf16,
    encode_binary32_rne,
)


MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
RMS_NORM_EPSILON_BINARY32 = 0x358637BD
RMS_NORM_WIDTHS = frozenset({128, 512, 1024, 4096})

BF16RMSMatrix: TypeAlias = tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class RMSNormResult:
    """BF16 outputs and row-level binary32 intermediates retained for checking."""

    inverse_rms_codes: tuple[int, ...]
    mean_square_codes: tuple[int, ...]
    output_codes: BF16RMSMatrix
    output_saturation_count: int


class NormalizationReferenceError(ValueError):
    """Raised when an RMS-normalization request violates the target contract."""


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise NormalizationReferenceError(f"{label} must be a sequence")
    return value


def _finite_bf16_vector(
    value: object,
    *,
    label: str,
    width: int | None = None,
) -> tuple[int, ...]:
    raw = _sequence(value, label)
    if not raw:
        raise NormalizationReferenceError(f"{label} must contain at least one value")
    if width is not None and len(raw) != width:
        raise NormalizationReferenceError(
            f"{label} must contain exactly {width} values"
        )

    result: list[int] = []
    for index, code in enumerate(raw):
        element_label = f"{label}[{index}]"
        if (
            isinstance(code, bool)
            or not isinstance(code, int)
            or not 0 <= code < 1 << 16
        ):
            raise NormalizationReferenceError(
                f"{element_label} must be a 16-bit BF16 encoding"
            )
        decoded = decode_bf16(code)
        if not decoded.finite or decoded.value is None:
            raise NormalizationReferenceError(f"{element_label} must be finite BF16")
        result.append(encode_binary32_rne(decoded.value))
    return tuple(result)


def rms_norm_bf16(
    input_codes: Sequence[Sequence[int]],
    weight_codes: Sequence[int],
    *,
    epsilon_binary32: int = RMS_NORM_EPSILON_BINARY32,
) -> RMSNormResult:
    """Execute qualified weighted RMS normalization over flattened BF16 rows."""

    if (
        isinstance(epsilon_binary32, bool)
        or not isinstance(epsilon_binary32, int)
        or epsilon_binary32 != RMS_NORM_EPSILON_BINARY32
    ):
        raise NormalizationReferenceError(
            "epsilon_binary32 must equal the qualified 1e-6 encoding "
            f"0x{RMS_NORM_EPSILON_BINARY32:08x}"
        )
    weights = _finite_bf16_vector(weight_codes, label="weight_codes")
    width = len(weights)
    if width not in RMS_NORM_WIDTHS:
        raise NormalizationReferenceError(
            f"weight width {width} is outside qualified widths {sorted(RMS_NORM_WIDTHS)}"
        )
    width_code = encode_binary32_rne(width)

    raw_rows = _sequence(input_codes, "input_codes")
    if not raw_rows:
        raise NormalizationReferenceError("input_codes must contain at least one row")

    mean_codes: list[int] = []
    inverse_codes: list[int] = []
    output_rows: list[tuple[int, ...]] = []
    saturation_count = 0
    for row_index, raw_row in enumerate(raw_rows):
        row = _finite_bf16_vector(
            raw_row,
            label=f"input_codes[{row_index}]",
            width=width,
        )
        try:
            squares = tuple(binary32_multiply(value, value) for value in row)
            square_sum = binary32_balanced_sum(squares)
            mean = binary32_divide(square_sum, width_code)
            variance = binary32_add(mean, epsilon_binary32)
            inverse = binary32_rsqrt(variance)

            output: list[int] = []
            for value, weight in zip(row, weights, strict=True):
                normalized = binary32_multiply(value, inverse)
                weighted = binary32_multiply(weight, normalized)
                converted = binary32_bits_to_bf16_rne(weighted)
                saturation_count += int(converted.saturated)
                output.append(converted.code)
        except NumericReferenceError as exc:
            raise NormalizationReferenceError(
                f"input_codes row {row_index} failed: {exc}"
            ) from exc
        mean_codes.append(mean)
        inverse_codes.append(inverse)
        output_rows.append(tuple(output))

    return RMSNormResult(
        inverse_rms_codes=tuple(inverse_codes),
        mean_square_codes=tuple(mean_codes),
        output_codes=tuple(output_rows),
        output_saturation_count=saturation_count,
    )


__all__ = [
    "BF16RMSMatrix",
    "MODEL_SOURCE_SHA256",
    "NormalizationReferenceError",
    "RMS_NORM_EPSILON_BINARY32",
    "RMS_NORM_WIDTHS",
    "RMSNormResult",
    "rms_norm_bf16",
]
