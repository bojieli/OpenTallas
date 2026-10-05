"""Data-bearing implementation of the Qwen RMSNorm target contract.

This implementation is separate from the exact scalar oracle.  NumPy performs
the bounded vector work and explicit binary32 balanced reduction.  A local
integer algorithm computes correctly rounded reciprocal square root without a
host libm dependency.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np


NUMERIC_CONTRACT = "qwen3_rmsnorm_fp32_bf16_v1"
EPSILON_CODE = 0x358637BD


class RMSNormKernelError(ValueError):
    """Raised when data or arithmetic violates the target contract."""


@dataclass(frozen=True)
class RMSNormKernelResult:
    """Target values and architectural diagnostic encodings."""

    inverse_rms_codes: np.ndarray[Any, np.dtype[np.uint32]]
    mean_square_codes: np.ndarray[Any, np.dtype[np.uint32]]
    normalized_saturated_element_count: int
    normalized_values: np.ndarray[Any, np.dtype[np.uint16]]
    output_saturated_element_count: int
    values: np.ndarray[Any, np.dtype[np.uint16]]


def _input_codes(value: object) -> np.ndarray[Any, np.dtype[np.uint16]]:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise RMSNormKernelError("input_codes must be a nonempty rank-2 matrix") from exc
    if raw.ndim != 2 or not raw.shape[0] or not raw.shape[1]:
        raise RMSNormKernelError("input_codes must be a nonempty rank-2 matrix")
    if raw.dtype.kind not in {"i", "u"}:
        raise RMSNormKernelError("input_codes must contain integer BF16 encodings")
    if np.any(raw < 0) or np.any(raw > 0xFFFF):
        raise RMSNormKernelError("input_codes contains a value outside 16-bit BF16")
    result = np.ascontiguousarray(raw, dtype=np.uint16)
    if np.any((result & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise RMSNormKernelError("input_codes contains BF16 NaN or infinity")
    return result


def _weight_codes(value: object, width: int) -> np.ndarray[Any, np.dtype[np.uint16]]:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise RMSNormKernelError(
            f"weight_codes must be an integer vector of width {width}"
        ) from exc
    if raw.ndim != 1 or raw.shape[0] != width or raw.dtype.kind not in {"i", "u"}:
        raise RMSNormKernelError(
            f"weight_codes must be an integer vector of width {width}"
        )
    if np.any(raw < 0) or np.any(raw > 0xFFFF):
        raise RMSNormKernelError("weight_codes contains a value outside 16-bit BF16")
    result = np.ascontiguousarray(raw, dtype=np.uint16)
    if np.any((result & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise RMSNormKernelError("weight_codes contains BF16 NaN or infinity")
    return result


def _decode_bf16(
    codes: np.ndarray[Any, np.dtype[np.uint16]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    return np.ascontiguousarray(codes.astype(np.uint32) << np.uint32(16)).view(
        np.float32
    )


def _encode_bf16_rne(
    values: np.ndarray[Any, np.dtype[np.float32]],
) -> tuple[np.ndarray[Any, np.dtype[np.uint16]], int]:
    if not np.all(np.isfinite(values)):
        raise RMSNormKernelError("binary32 value is NaN or infinity")
    bits = np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)
    upper = bits >> np.uint32(16)
    discarded = bits & np.uint32(0xFFFF)
    increment = (discarded > np.uint32(0x8000)) | (
        (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
    )
    rounded = upper + increment.astype(np.uint32)
    saturated = (rounded & np.uint32(0x7F80)) == np.uint32(0x7F80)
    saturation_count = int(np.count_nonzero(saturated))
    signs = rounded & np.uint32(0x8000)
    rounded = np.where(saturated, signs | np.uint32(0x7F7F), rounded)
    rounded = np.where((rounded & np.uint32(0x7FFF)) == 0, 0, rounded)
    return np.ascontiguousarray(rounded, dtype=np.uint16), saturation_count


def _binary32_components(code: int) -> tuple[int, int]:
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent == 0:
        return fraction, -149
    return (1 << 23) | fraction, exponent - 150


def _compare_square_product_to_one(
    significand: int,
    exponent: int,
    argument_significand: int,
    argument_exponent: int,
) -> int:
    product = significand * significand * argument_significand
    power = 2 * exponent + argument_exponent
    if power >= 0:
        left = product << power
        right = 1
    else:
        left = product
        right = 1 << -power
    return (left > right) - (left < right)


def _binary32_rsqrt_rne(code: int) -> int:
    exponent = (code >> 23) & 0xFF
    if code <= 0 or code & 0x80000000 or exponent == 0xFF:
        raise RMSNormKernelError("rsqrt argument must be positive finite binary32")
    argument_significand, argument_exponent = _binary32_components(code)
    low = 0
    high = 0x7F7FFFFF
    lower_code = 0
    while low <= high:
        candidate_code = (low + high) // 2
        candidate_significand, candidate_exponent = _binary32_components(
            candidate_code
        )
        comparison = _compare_square_product_to_one(
            candidate_significand,
            candidate_exponent,
            argument_significand,
            argument_exponent,
        )
        if comparison <= 0:
            lower_code = candidate_code
            low = candidate_code + 1
        else:
            high = candidate_code - 1
    if lower_code == 0x7F7FFFFF:  # pragma: no cover - binary32 input bound
        return lower_code
    upper_code = lower_code + 1
    lower_significand, lower_exponent = _binary32_components(lower_code)
    upper_significand, upper_exponent = _binary32_components(upper_code)
    common_exponent = min(lower_exponent, upper_exponent)
    midpoint_significand = (
        (lower_significand << (lower_exponent - common_exponent))
        + (upper_significand << (upper_exponent - common_exponent))
    )
    comparison = _compare_square_product_to_one(
        midpoint_significand,
        common_exponent - 1,
        argument_significand,
        argument_exponent,
    )
    if comparison < 0:
        return upper_code
    if comparison > 0:
        return lower_code
    return lower_code if lower_code & 1 == 0 else upper_code


def _epsilon_value(code: object) -> np.float32:
    if (
        isinstance(code, bool)
        or not isinstance(code, int)
        or not 0 < code < 1 << 31
        or code & 0x7F800000 == 0x7F800000
    ):
        raise RMSNormKernelError("epsilon_code must be positive finite binary32")
    return np.asarray([code], dtype=np.uint32).view(np.float32)[0]


def _balanced_sum(
    values: np.ndarray[Any, np.dtype[np.float32]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    level = np.ascontiguousarray(values, dtype=np.float32)
    while level.shape[1] > 1:
        if level.shape[1] & 1:
            level = np.concatenate(
                (level, np.zeros((level.shape[0], 1), dtype=np.float32)), axis=1
            )
        level = np.add(level[:, 0::2], level[:, 1::2], dtype=np.float32)
    return np.ascontiguousarray(level[:, 0], dtype=np.float32)


def rms_norm_bf16(
    input_codes: Sequence[Sequence[int]] | np.ndarray[Any, Any],
    weight_codes: Sequence[int] | np.ndarray[Any, Any],
    *,
    epsilon_code: int = EPSILON_CODE,
) -> RMSNormKernelResult:
    """Execute bounded data-bearing RMSNorm with target-visible arithmetic."""

    inputs = _input_codes(input_codes)
    weights = _weight_codes(weight_codes, inputs.shape[1])
    epsilon = _epsilon_value(epsilon_code)
    input_values = _decode_bf16(inputs)
    weight_values = _decode_bf16(weights)
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        squares = np.multiply(input_values, input_values, dtype=np.float32)
        if not np.all(np.isfinite(squares)):
            raise RMSNormKernelError("BF16 square overflowed binary32")
        totals = _balanced_sum(squares)
        means = np.divide(totals, np.float32(inputs.shape[1]), dtype=np.float32)
        arguments = np.add(means, epsilon, dtype=np.float32)
        if not np.all(np.isfinite(arguments)) or np.any(arguments <= 0):
            raise RMSNormKernelError("RMSNorm variance argument is not positive finite")
        argument_codes = np.ascontiguousarray(arguments).view(np.uint32)
        inverse_codes = np.asarray(
            [_binary32_rsqrt_rne(int(code)) for code in argument_codes],
            dtype=np.uint32,
        )
        inverse_values = inverse_codes.view(np.float32)
        normalized_fp32 = np.multiply(
            input_values,
            inverse_values[:, None],
            dtype=np.float32,
        )
        normalized, normalized_saturation_count = _encode_bf16_rne(
            normalized_fp32
        )
        output_fp32 = np.multiply(
            _decode_bf16(normalized),
            weight_values[None, :],
            dtype=np.float32,
        )
        output, output_saturation_count = _encode_bf16_rne(output_fp32)
    finally:
        np.seterr(**previous)
    return RMSNormKernelResult(
        inverse_rms_codes=np.ascontiguousarray(inverse_codes),
        mean_square_codes=np.ascontiguousarray(means).view(np.uint32),
        normalized_saturated_element_count=normalized_saturation_count,
        normalized_values=normalized,
        output_saturated_element_count=output_saturation_count,
        values=output,
    )


__all__ = [
    "EPSILON_CODE",
    "NUMERIC_CONTRACT",
    "RMSNormKernelError",
    "RMSNormKernelResult",
    "rms_norm_bf16",
]
