"""Independent scalar Qwen RoPE oracle for the tensor accelerator.

The coefficient payload is an explicit architectural input.  Its qualification
freezes the pinned Qwen/PyTorch inverse-frequency constants and the BF16 cosine
and sine table separately; this oracle defines the target-visible application
arithmetic without importing NumPy, PyTorch, compiler code, or simulator code.

For each element, both BF16 products round independently to BF16, their sum
rounds once more to BF16, and exact zero is canonical positive zero.  The
half-rotation is ``concat(-x[half:], x[:half])`` from the pinned Qwen source.
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


NUMERIC_CONTRACT = "qwen3_rope_fp32_bf16_v1"
HEAD_DIM = 128
THETA = 1_000_000
BF16Matrix: TypeAlias = tuple[tuple[int, ...], ...]

# Source-derived binary32 constants from the pinned Qwen3 default-RoPE setup:
#   1 / (1_000_000 ** (arange(0, 128, 2, float32) / 128))
# They are part of the numeric profile rather than being recomputed with a host
# pow implementation at deployment time.
INV_FREQ_BINARY32_CODES = (
    0x3F800000,
    0x3F4E4BAD,
    0x3F263DE0,
    0x3F05F6EF,
    0x3ED7E89B,
    0x3EADFCFF,
    0x3E8C3504,
    0x3E61F835,
    0x3E361887,
    0x3E12BD91,
    0x3DEC7FD6,
    0x3DBE94C6,
    0x3D99940D,
    0x3D778513,
    0x3D47763F,
    0x3D20BC1D,
    0x3D0186E3,
    0x3CD0C1A8,
    0x3CA8398B,
    0x3C879008,
    0x3C5A7BF2,
    0x3C301052,
    0x3C0DE12D,
    0x3BE4AA46,
    0x3BB8449C,
    0x3B947DAE,
    0x3B6F520E,
    0x3B40DAC5,
    0x3B1B690D,
    0x3AFA78F0,
    0x3AC9D75C,
    0x3AA2A6F7,
    0x3A83126F,
    0x3A533F28,
    0x3A2A3B44,
    0x3A092E02,
    0x39DD1725,
    0x39B229FB,
    0x398F9272,
    0x39676492,
    0x393A7753,
    0x39164324,
    0x38F22CE2,
    0x38C327B5,
    0x389D43A4,
    0x387D75D4,
    0x384C3FBE,
    0x382497AB,
    0x3804A2B2,
    0x37D5C441,
    0x37AC431D,
    0x378AD0ED,
    0x375FBA4F,
    0x37344A0E,
    0x371148E3,
    0x36EA2732,
    0x36BCB0C1,
    0x36980E02,
    0x36751070,
    0x36457BAB,
    0x361F23E4,
    0x36003DEC,
    0x35CEAF79,
    0x35A68E4C,
)


class RoPEReferenceError(ValueError):
    """Raised when a RoPE operand or arithmetic event is illegal."""


@dataclass(frozen=True)
class RoPEReferenceResult:
    """Exact rotated Q/K values and sticky conversion saturation counts."""

    addition_saturated_element_count: int
    multiplication_saturated_element_count: int
    query_values: BF16Matrix
    key_values: BF16Matrix


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise RoPEReferenceError(f"{label} must be a sequence")
    return value


def _finite_code(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < 1 << 16
    ):
        raise RoPEReferenceError(f"{label} must be a 16-bit BF16 encoding")
    if not decode_bf16(value).finite:
        raise RoPEReferenceError(f"{label} must be finite BF16")
    return value


def _matrix(value: object, label: str) -> BF16Matrix:
    rows = _sequence(value, label)
    if not rows:
        raise RoPEReferenceError(f"{label} must contain at least one head")
    result: list[tuple[int, ...]] = []
    width: int | None = None
    for row_index, raw_row in enumerate(rows):
        row = _sequence(raw_row, f"{label}[{row_index}]")
        if width is None:
            width = len(row)
            if width < 2 or width & 1:
                raise RoPEReferenceError(
                    f"{label} head dimension must be positive even"
                )
        elif len(row) != width:
            raise RoPEReferenceError(f"{label} must be rectangular")
        result.append(
            tuple(
                _finite_code(code, f"{label}[{row_index}][{column}]")
                for column, code in enumerate(row)
            )
        )
    return tuple(result)


def _coefficients(value: object, width: int, label: str) -> tuple[int, ...]:
    raw = _sequence(value, label)
    if len(raw) != width:
        raise RoPEReferenceError(f"{label} must contain exactly {width} values")
    return tuple(
        _finite_code(code, f"{label}[{index}]") for index, code in enumerate(raw)
    )


def _negate(code: int) -> int:
    return 0 if code & 0x7FFF == 0 else code ^ 0x8000


def _rotate(
    rows: BF16Matrix,
    cosine: tuple[int, ...],
    sine: tuple[int, ...],
) -> tuple[BF16Matrix, int, int]:
    width = len(cosine)
    half = width // 2
    products_saturated = 0
    additions_saturated = 0
    output: list[tuple[int, ...]] = []
    try:
        for row in rows:
            result_row: list[int] = []
            for column, code in enumerate(row):
                rotated = (
                    _negate(row[column + half]) if column < half else row[column - half]
                )
                direct_product = binary32_bits_to_bf16_rne(
                    binary32_multiply(code << 16, cosine[column] << 16)
                )
                rotated_product = binary32_bits_to_bf16_rne(
                    binary32_multiply(rotated << 16, sine[column] << 16)
                )
                products_saturated += int(direct_product.saturated)
                products_saturated += int(rotated_product.saturated)
                summed = binary32_bits_to_bf16_rne(
                    binary32_add(
                        direct_product.code << 16,
                        rotated_product.code << 16,
                    )
                )
                additions_saturated += int(summed.saturated)
                result_row.append(summed.code)
            output.append(tuple(result_row))
    except NumericReferenceError as exc:
        raise RoPEReferenceError(f"RoPE arithmetic failed: {exc}") from exc
    return tuple(output), products_saturated, additions_saturated


def rope_bf16(
    query_codes: Sequence[Sequence[int]],
    key_codes: Sequence[Sequence[int]],
    cosine_codes: Sequence[int],
    sine_codes: Sequence[int],
) -> RoPEReferenceResult:
    """Apply one coefficient row to all query and key heads exactly."""

    query = _matrix(query_codes, "query_codes")
    key = _matrix(key_codes, "key_codes")
    width = len(query[0])
    if len(key[0]) != width:
        raise RoPEReferenceError("query and key head dimensions differ")
    cosine = _coefficients(cosine_codes, width, "cosine_codes")
    sine = _coefficients(sine_codes, width, "sine_codes")
    query_output, query_mul_sat, query_add_sat = _rotate(query, cosine, sine)
    key_output, key_mul_sat, key_add_sat = _rotate(key, cosine, sine)
    return RoPEReferenceResult(
        addition_saturated_element_count=query_add_sat + key_add_sat,
        multiplication_saturated_element_count=query_mul_sat + key_mul_sat,
        query_values=query_output,
        key_values=key_output,
    )


__all__ = [
    "HEAD_DIM",
    "INV_FREQ_BINARY32_CODES",
    "NUMERIC_CONTRACT",
    "RoPEReferenceError",
    "RoPEReferenceResult",
    "THETA",
    "rope_bf16",
]
