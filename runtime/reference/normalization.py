"""Deterministic weighted and per-head RMS normalization for DeepSeek V4.

The learned-weight path widens BF16 activations to FP32 before its arithmetic.
The distinct query-head path receives BF16 from ``fp8_gemm`` and keeps the
source-visible square, mean, epsilon, reciprocal-square-root, and pointwise
multiply boundaries in BF16. PyTorch does not freeze a cross-backend reduction
tree or reciprocal-square-root approximation, so both paths use deterministic
NUM-6 target adaptations at those otherwise backend-dependent boundaries.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    bf16_rsqrt,
    binary32_add,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    binary32_divide,
    binary32_multiply,
    binary32_rsqrt,
    decode_bf16,
    encode_binary32_rne,
    encode_bf16_rne,
)


MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
RMS_NORM_EPSILON_BINARY32 = 0x358637BD
RMS_NORM_WIDTHS = frozenset({128, 512, 1024, 4096})
HEAD_RMS_NORM_EPSILON_BF16 = 0x3586
HEAD_RMS_NORM_WIDTH = 512

BF16RMSMatrix: TypeAlias = tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class RMSNormResult:
    """BF16 outputs and row-level binary32 intermediates retained for checking."""

    inverse_rms_codes: tuple[int, ...]
    mean_square_codes: tuple[int, ...]
    output_codes: BF16RMSMatrix
    output_saturation_count: int


@dataclass(frozen=True)
class HeadRMSNormResult:
    """BF16 outputs and BF16 row intermediates retained for checking."""

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


def _finite_bf16_codes(
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
        result.append(code)
    return tuple(result)


def _finite_bf16_vector(
    value: object,
    *,
    label: str,
    width: int | None = None,
) -> tuple[int, ...]:
    result: list[int] = []
    for code in _finite_bf16_codes(value, label=label, width=width):
        decoded = decode_bf16(code)
        if decoded.value is None:  # pragma: no cover - validated by helper
            raise RuntimeError("validated BF16 value became nonfinite")
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


def head_rms_norm_bf16(
    input_codes: Sequence[Sequence[int]],
    *,
    epsilon_bf16: int = HEAD_RMS_NORM_EPSILON_BF16,
) -> HeadRMSNormResult:
    """Execute the qualified unweighted BF16 query-head normalization."""

    if (
        isinstance(epsilon_bf16, bool)
        or not isinstance(epsilon_bf16, int)
        or epsilon_bf16 != HEAD_RMS_NORM_EPSILON_BF16
    ):
        raise NormalizationReferenceError(
            "epsilon_bf16 must equal the qualified 1e-6 encoding "
            f"0x{HEAD_RMS_NORM_EPSILON_BF16:04x}"
        )
    raw_rows = _sequence(input_codes, "input_codes")
    if not raw_rows:
        raise NormalizationReferenceError("input_codes must contain at least one row")

    epsilon = decode_bf16(epsilon_bf16).value
    if epsilon is None:  # pragma: no cover - qualified constant invariant
        raise RuntimeError("HEAD_RMS_NORM epsilon is not finite BF16")
    width_code = encode_binary32_rne(HEAD_RMS_NORM_WIDTH)
    mean_codes: list[int] = []
    inverse_codes: list[int] = []
    output_rows: list[tuple[int, ...]] = []
    saturation_count = 0
    for row_index, raw_row in enumerate(raw_rows):
        row = _finite_bf16_codes(
            raw_row,
            label=f"input_codes[{row_index}]",
            width=HEAD_RMS_NORM_WIDTH,
        )
        try:
            values = []
            for code in row:
                decoded = decode_bf16(code)
                if decoded.value is None:  # pragma: no cover - validated by helper
                    raise RuntimeError("validated HEAD_RMS_NORM row became nonfinite")
                values.append(decoded.value)

            square_codes: list[int] = []
            for value in values:
                square = encode_bf16_rne(value * value)
                if square.saturated:
                    raise NumericReferenceError("finite BF16 square overflow")
                square_codes.append(square.code)
            widened_squares = []
            for code in square_codes:
                decoded = decode_bf16(code)
                if decoded.value is None:  # pragma: no cover - finite encoder invariant
                    raise RuntimeError("HEAD_RMS_NORM square became nonfinite")
                widened_squares.append(encode_binary32_rne(decoded.value))
            square_sum = binary32_balanced_sum(widened_squares)
            mean_binary32 = binary32_divide(square_sum, width_code)
            mean = binary32_bits_to_bf16_rne(mean_binary32)
            if mean.saturated:
                raise NumericReferenceError("finite BF16 mean-square overflow")
            mean_value = decode_bf16(mean.code).value
            if mean_value is None:  # pragma: no cover - finite conversion invariant
                raise RuntimeError("HEAD_RMS_NORM mean-square became nonfinite")
            biased = encode_bf16_rne(mean_value + epsilon)
            if biased.saturated:
                raise NumericReferenceError("finite BF16 epsilon add overflow")
            inverse = bf16_rsqrt(biased.code)
            inverse_value = decode_bf16(inverse).value
            if inverse_value is None:  # pragma: no cover - finite rsqrt invariant
                raise RuntimeError("HEAD_RMS_NORM inverse RMS became nonfinite")

            output: list[int] = []
            for value in values:
                converted = encode_bf16_rne(value * inverse_value)
                saturation_count += int(converted.saturated)
                output.append(converted.code)
        except NumericReferenceError as exc:
            raise NormalizationReferenceError(
                f"input_codes row {row_index} failed: {exc}"
            ) from exc
        mean_codes.append(mean.code)
        inverse_codes.append(inverse)
        output_rows.append(tuple(output))

    return HeadRMSNormResult(
        inverse_rms_codes=tuple(inverse_codes),
        mean_square_codes=tuple(mean_codes),
        output_codes=tuple(output_rows),
        output_saturation_count=saturation_count,
    )


__all__ = [
    "BF16RMSMatrix",
    "HEAD_RMS_NORM_EPSILON_BF16",
    "HEAD_RMS_NORM_WIDTH",
    "HeadRMSNormResult",
    "MODEL_SOURCE_SHA256",
    "NormalizationReferenceError",
    "RMS_NORM_EPSILON_BINARY32",
    "RMS_NORM_WIDTHS",
    "RMSNormResult",
    "head_rms_norm_bf16",
    "rms_norm_bf16",
]
