"""Deterministic DeepSeek V4 128-point Hadamard rotation semantics.

The pinned model calls the unversioned ``fast_hadamard_transform`` dependency
with BF16 input and ``scale=x.size(-1) ** -0.5``. Every graph use has width 128.
The public implementation documents a Sylvester Hadamard matrix and its CUDA
kernel performs seven ascending-stride binary32 butterfly stages, multiplies
once by the binary32-rounded normalization scale, and converts once to BF16.

OpenTallas freezes that arithmetic directly. It preserves binary32 subnormals
and canonicalizes signed zero according to the governed numeric profile rather
than inheriting the development package's ``--use_fast_math`` FTZ behavior.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_multiply,
    decode_bf16,
    encode_binary32_rne,
)


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
REQUIREMENTS_SOURCE_SHA256 = (
    "857e0b8b58e41cabe16e55bf4ab7ff791677c53b25f0f3e104ef85227cd11eab"
)
FHT_DEVELOPMENT_REVISION = "1cc807efbd6cc001df359822d60bf6052dd66859"
HADAMARD_WIDTH = 128
HADAMARD_SCALE_BINARY32 = 0x3DB504F3
HADAMARD_STRIDES = (1, 2, 4, 8, 16, 32, 64)

BF16HadamardMatrix: TypeAlias = tuple[tuple[int, ...], ...]


class HadamardReferenceError(ValueError):
    """Raised when a Hadamard request violates the target contract."""


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise HadamardReferenceError(f"{label} must be a sequence")
    return value


def _negate_binary32(code: int) -> int:
    """Negate a finite code while retaining the target's positive-zero rule."""

    return 0 if code & 0x7FFFFFFF == 0 else code ^ 0x80000000


def _rotate_row(row: Sequence[object], row_index: int) -> tuple[int, ...]:
    if len(row) != HADAMARD_WIDTH:
        raise HadamardReferenceError(
            f"input_codes[{row_index}] must contain exactly {HADAMARD_WIDTH} values"
        )

    values: list[int] = []
    for column, code in enumerate(row):
        label = f"input_codes[{row_index}][{column}]"
        if (
            isinstance(code, bool)
            or not isinstance(code, int)
            or not 0 <= code < 1 << 16
        ):
            raise HadamardReferenceError(f"{label} must be a 16-bit BF16 encoding")
        decoded = decode_bf16(code)
        if not decoded.finite or decoded.value is None:
            raise HadamardReferenceError(f"{label} must be finite BF16")
        values.append(encode_binary32_rne(decoded.value))

    try:
        for stride in HADAMARD_STRIDES:
            for base in range(0, HADAMARD_WIDTH, 2 * stride):
                for offset in range(stride):
                    lower_index = base + offset
                    upper_index = lower_index + stride
                    lower = values[lower_index]
                    upper = values[upper_index]
                    values[lower_index] = binary32_add(lower, upper)
                    values[upper_index] = binary32_add(
                        lower, _negate_binary32(upper)
                    )

        output: list[int] = []
        for value in values:
            scaled = binary32_multiply(value, HADAMARD_SCALE_BINARY32)
            converted = binary32_bits_to_bf16_rne(scaled)
            if converted.saturated:  # pragma: no cover - scale bounds legal rows
                raise NumericReferenceError("Hadamard BF16 output saturated")
            output.append(converted.code)
    except NumericReferenceError as exc:
        raise HadamardReferenceError(
            f"input_codes row {row_index} failed: {exc}"
        ) from exc
    return tuple(output)


def hadamard_rotate_128_bf16(
    input_codes: Sequence[Sequence[int]],
    *,
    width: int = HADAMARD_WIDTH,
) -> BF16HadamardMatrix:
    """Apply the qualified normalized 128-point transform to flattened rows.

    ``input_codes`` is the source-order ``[-1, 128]`` view of either index
    queries or compressed index KV. Every butterfly addition/subtraction has
    one binary32 RNE boundary. The binary32 scale is applied once after all
    seven stages, followed by one BF16 RNE conversion.
    """

    if isinstance(width, bool) or not isinstance(width, int) or width != HADAMARD_WIDTH:
        raise HadamardReferenceError(
            f"width must equal the qualified value {HADAMARD_WIDTH}"
        )
    rows = _sequence(input_codes, "input_codes")
    if not rows:
        raise HadamardReferenceError("input_codes must contain at least one row")
    return tuple(
        _rotate_row(_sequence(row, f"input_codes[{row_index}]"), row_index)
        for row_index, row in enumerate(rows)
    )


__all__ = [
    "BF16HadamardMatrix",
    "FHT_DEVELOPMENT_REVISION",
    "HADAMARD_SCALE_BINARY32",
    "HADAMARD_STRIDES",
    "HADAMARD_WIDTH",
    "HadamardReferenceError",
    "MODEL_SOURCE_SHA256",
    "REQUIREMENTS_SOURCE_SHA256",
    "hadamard_rotate_128_bf16",
]
