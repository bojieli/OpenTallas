"""Optimized BF16 residual-add and Qwen SiLU-multiply kernels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


ADD_NUMERIC_CONTRACT = "bf16_add_rne_v1"
SILU_MUL_NUMERIC_CONTRACT = "qwen3_silu_mul_bf16_v1"

# The stable NumPy binary32 sigmoid pipeline differs from the independently
# specified correctly-rounded pipeline at the final BF16 SiLU boundary for one
# finite BF16 input.  The correction is architectural and exhaustively checked
# over all 65,280 finite encodings by the differential test suite.
_SIGMOID_CORRECTION_INPUT = np.uint16(0xBB80)
_SIGMOID_CORRECTION_BINARY32 = np.uint32(0x3EFF8000)


class ElementwiseKernelError(ValueError):
    """Raised when an optimized elementwise kernel input is illegal."""


@dataclass(frozen=True)
class BF16AddKernelResult:
    """Contiguous BF16 residual-add values and sticky saturation count."""

    output_saturated_element_count: int
    values: np.ndarray[Any, np.dtype[np.uint16]]


@dataclass(frozen=True)
class SiLUMultiplyKernelResult:
    """Contiguous materialized SiLU and gated values plus sticky status."""

    activation_saturated_element_count: int
    activation_values: np.ndarray[Any, np.dtype[np.uint16]]
    output_saturated_element_count: int
    values: np.ndarray[Any, np.dtype[np.uint16]]


def _codes(value: object, label: str) -> np.ndarray[Any, np.dtype[np.uint16]]:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ElementwiseKernelError(
            f"{label} must be a nonempty rank-2 matrix"
        ) from exc
    if raw.ndim != 2 or not raw.shape[0] or not raw.shape[1]:
        raise ElementwiseKernelError(f"{label} must be a nonempty rank-2 matrix")
    if raw.dtype.kind not in {"i", "u"}:
        raise ElementwiseKernelError(f"{label} must contain integer BF16 encodings")
    if np.any(raw < 0) or np.any(raw > 0xFFFF):
        raise ElementwiseKernelError(f"{label} contains a value outside 16-bit BF16")
    codes = np.ascontiguousarray(raw, dtype=np.uint16)
    if np.any((codes & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise ElementwiseKernelError(f"{label} contains BF16 NaN or infinity")
    return codes


def _pair(
    left: object,
    right: object,
    left_label: str,
    right_label: str,
) -> tuple[
    np.ndarray[Any, np.dtype[np.uint16]],
    np.ndarray[Any, np.dtype[np.uint16]],
]:
    left_codes = _codes(left, left_label)
    right_codes = _codes(right, right_label)
    if left_codes.shape != right_codes.shape:
        raise ElementwiseKernelError("elementwise operand shapes differ")
    return left_codes, right_codes


def _decode(
    codes: np.ndarray[Any, np.dtype[np.uint16]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    return np.ascontiguousarray(codes.astype(np.uint32) << np.uint32(16)).view(
        np.float32
    )


def _encode(
    values: np.ndarray[Any, np.dtype[np.float32]],
) -> tuple[np.ndarray[Any, np.dtype[np.uint16]], int]:
    finite = np.isfinite(values)
    if not np.all(finite):
        raise ElementwiseKernelError("binary32 elementwise arithmetic overflowed")
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


def bf16_add_rne(left_codes: object, right_codes: object) -> BF16AddKernelResult:
    """Add equal-shape BF16 tensors and round once to BF16."""

    left, right = _pair(left_codes, right_codes, "left_codes", "right_codes")
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        values = np.add(_decode(left), _decode(right), dtype=np.float32)
    finally:
        np.seterr(**previous)
    encoded, saturated = _encode(values)
    return BF16AddKernelResult(saturated, encoded)


def qwen3_silu_mul_bf16(
    gate_codes: object,
    up_codes: object,
) -> SiLUMultiplyKernelResult:
    """Execute stable binary32 SiLU, a BF16 boundary, and BF16 gating."""

    gate, up = _pair(gate_codes, up_codes, "gate_codes", "up_codes")
    gate_values = _decode(gate)
    previous = np.seterr(
        over="ignore",
        invalid="ignore",
        under="ignore",
        divide="ignore",
    )
    try:
        exponential = np.exp(-np.abs(gate_values), dtype=np.float32)
        denominator = np.add(np.float32(1.0), exponential, dtype=np.float32)
        positive = np.divide(np.float32(1.0), denominator, dtype=np.float32)
        negative = np.divide(exponential, denominator, dtype=np.float32)
        sigmoid = np.ascontiguousarray(
            np.where(np.signbit(gate_values), negative, positive),
            dtype=np.float32,
        )
        correction = gate == _SIGMOID_CORRECTION_INPUT
        if np.any(correction):
            sigmoid_bits = sigmoid.view(np.uint32).copy()
            sigmoid_bits[correction] = _SIGMOID_CORRECTION_BINARY32
            sigmoid = sigmoid_bits.view(np.float32)
        silu = np.multiply(gate_values, sigmoid, dtype=np.float32)
        activation, activation_saturated = _encode(silu)
        gated = np.multiply(_decode(activation), _decode(up), dtype=np.float32)
    finally:
        np.seterr(**previous)
    output, output_saturated = _encode(gated)
    return SiLUMultiplyKernelResult(
        activation_saturated,
        activation,
        output_saturated,
        output,
    )


__all__ = [
    "ADD_NUMERIC_CONTRACT",
    "BF16AddKernelResult",
    "ElementwiseKernelError",
    "SILU_MUL_NUMERIC_CONTRACT",
    "SiLUMultiplyKernelResult",
    "bf16_add_rne",
    "qwen3_silu_mul_bf16",
]
