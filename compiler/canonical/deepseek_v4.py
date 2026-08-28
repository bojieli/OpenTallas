"""Canonical byte transforms for the pinned DeepSeek V4 Flash checkpoint.

The release's local converter applies name normalization, tensor-parallel
sharding, packed-MXFP4 reinterpretation, and a block-scaled FP8 to BF16
conversion for the output-A projection. This module specifies those byte
operations without importing checkpoint Python.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from functools import lru_cache
import math
import re
from typing import Any

from compiler.frontend.checkpoint import DTYPE_BITS


CANONICAL_PLAN_SCHEMA = "opentallas.deepseek_v4_canonical_plan.v1"
CONVERT_SOURCE_SHA256 = (
    "6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe"
)
FP8_BLOCK = 128
MXFP4_BLOCK = 32

_MAPPING: dict[str, tuple[str, int]] = {
    "embed": ("embed", 0),
    "wq_b": ("wq_b", 0),
    "wo_a": ("wo_a", 0),
    "wo_b": ("wo_b", 1),
    "head": ("head", 0),
    "attn_sink": ("attn_sink", 0),
    "weights_proj": ("weights_proj", 0),
    "markov_w1": ("markov_w1", 0),
    "markov_w2": ("markov_w2", 0),
}
_SPECIAL_KEY_FRAGMENTS = ("hc", "attn_sink", "tie2eid", "ape")
_EXPERT_RE = re.compile(r"(?:^|\.)ffn\.experts\.([0-9]+)\.")


class CanonicalTransformError(RuntimeError):
    """Raised when an official tensor cannot be transformed exactly."""


def _integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise CanonicalTransformError(
            f"{label} must be an integer in {minimum}..{maximum}"
        )
    return value


def _shape(value: Any, label: str) -> tuple[int, ...]:
    if (
        isinstance(value, (str, bytes))
        or not isinstance(value, Sequence)
        or not value
    ):
        raise CanonicalTransformError(f"{label} must be a nonempty shape")
    return tuple(
        _integer(
            extent,
            f"{label}[{index}]",
            minimum=1,
            maximum=(1 << 63) - 1,
        )
        for index, extent in enumerate(value)
    )


def _owner_key(name: str) -> str:
    parts = name.split(".")
    if any(fragment in name for fragment in _SPECIAL_KEY_FRAGMENTS):
        return parts[-1]
    if len(parts) < 2:
        raise CanonicalTransformError(
            f"tensor name {name!r} has no parameter owner component"
        )
    return parts[-2]


def canonicalize_source_name(name: str) -> str | None:
    """Apply the exact name and duplicate-omission rules in convert.py."""

    if not isinstance(name, str) or not name or "\x00" in name:
        raise CanonicalTransformError("tensor name must be a nonempty safe string")
    if name.startswith("model."):
        name = name[len("model.") :]
    if name.startswith("mtp.") and ("emb" in name or name.endswith("head.weight")):
        return None
    name = name.replace("self_attn", "attn")
    name = name.replace("mlp", "ffn")
    name = name.replace("weight_scale_inv", "scale")
    name = name.replace("e_score_correction_bias", "bias")
    key = _owner_key(name)
    new_key, _ = _MAPPING.get(key, (key, -1))
    return name.replace(key, new_key)


def partition_axis(name: str) -> int | None:
    """Return the exact tensor-parallel axis selected by convert.py."""

    record = _MAPPING.get(_owner_key(name))
    return record[1] if record is not None else None


def routed_expert_id(name: str) -> int | None:
    """Return the globally numbered routed expert encoded in a tensor name."""

    match = _EXPERT_RE.search(name)
    return int(match.group(1)) if match else None


def dtype_bytes(dtype: str) -> int:
    bits = DTYPE_BITS.get(dtype)
    if bits is None or bits % 8:
        raise CanonicalTransformError(f"dtype {dtype!r} is not byte aligned")
    return bits // 8


def slice_row_major_payload(
    payload: bytes | bytearray | memoryview,
    shape: Sequence[int],
    dtype: str,
    axis: int,
    start: int,
    stop: int,
) -> tuple[bytes, tuple[int, ...]]:
    """Extract one exact logical slice from row-major tensor bytes."""

    tensor_shape = _shape(shape, "shape")
    axis = _integer(axis, "axis", 0, len(tensor_shape) - 1)
    start = _integer(start, "start", 0, tensor_shape[axis])
    stop = _integer(stop, "stop", 0, tensor_shape[axis])
    if stop <= start:
        raise CanonicalTransformError("slice stop must be greater than start")
    item_bytes = dtype_bytes(dtype)
    expected_bytes = math.prod(tensor_shape) * item_bytes
    view = memoryview(payload).cast("B")
    if len(view) != expected_bytes:
        raise CanonicalTransformError(
            f"payload has {len(view)} bytes, expected {expected_bytes}"
        )
    outer = math.prod(tensor_shape[:axis])
    inner = math.prod(tensor_shape[axis + 1 :])
    extent = tensor_shape[axis]
    selected = stop - start
    chunk_bytes = selected * inner * item_bytes
    output = bytearray(outer * chunk_bytes)
    destination = 0
    for outer_index in range(outer):
        source = (outer_index * extent + start) * inner * item_bytes
        output[destination : destination + chunk_bytes] = view[
            source : source + chunk_bytes
        ]
        destination += chunk_bytes
    output_shape = list(tensor_shape)
    output_shape[axis] = selected
    return bytes(output), tuple(output_shape)


def _round_unsigned_ratio_to_even(numerator: int, denominator: int) -> int:
    quotient, remainder = divmod(numerator, denominator)
    doubled = remainder * 2
    if doubled > denominator or (doubled == denominator and quotient & 1):
        quotient += 1
    return quotient


def fp8_e8m0_to_bf16_code(weight_code: int, scale_code: int) -> int:
    """Convert E4M3FN times E8M0 to the BF16 bits produced by convert.py.

    The conversion is exact in BF16's normal range because E4M3FN has fewer
    significand bits. BF16 subnormal underflow is rounded to nearest, ties even.
    Negative zero is retained like PyTorch. NaN, reserved scale, and finite
    overflow fail closed.
    """

    weight_code = _integer(weight_code, "weight_code", 0, 0xFF)
    scale_code = _integer(scale_code, "scale_code", 0, 0xFF)
    if scale_code == 0xFF:
        raise CanonicalTransformError("reserved E8M0 scale code 0xff")
    sign = (weight_code & 0x80) << 8
    magnitude_code = weight_code & 0x7F
    exponent = (magnitude_code >> 3) & 0xF
    fraction = magnitude_code & 0x7
    if exponent == 0xF and fraction == 0x7:
        raise CanonicalTransformError(
            f"E4M3FN weight code 0x{weight_code:02x} is NaN"
        )
    if magnitude_code == 0:
        return sign
    if exponent == 0:
        significand = fraction
        power = scale_code - 136
    else:
        significand = 8 + fraction
        power = exponent + scale_code - 137
    leading_power = significand.bit_length() - 1 + power
    if leading_power >= -126:
        if leading_power > 127:
            raise CanonicalTransformError(
                "scaled E4M3FN value overflows finite BF16"
            )
        precision = significand.bit_length()
        bf16_significand = significand << (8 - precision)
        exponent_field = leading_power + 127
        return sign | (exponent_field << 7) | (bf16_significand - 128)

    shift = power + 133
    if shift >= 0:
        subnormal = significand << shift
    else:
        subnormal = _round_unsigned_ratio_to_even(
            significand, 1 << (-shift)
        )
    if subnormal > 128:
        raise RuntimeError("BF16 subnormal rounding invariant failed")
    if subnormal == 128:
        return sign | 0x0080
    return sign | subnormal


@lru_cache(maxsize=1)
def _fp8_scale_to_bf16_tables() -> tuple[Any, Any]:
    try:
        import numpy as np
    except ImportError as exc:
        raise CanonicalTransformError("NumPy is required for matrix conversion") from exc
    values = np.zeros((256, 256), dtype="<u2")
    valid = np.zeros((256, 256), dtype=np.bool_)
    for scale_code in range(0xFF):
        for weight_code in range(0x100):
            try:
                values[scale_code, weight_code] = fp8_e8m0_to_bf16_code(
                    weight_code, scale_code
                )
            except CanonicalTransformError:
                continue
            valid[scale_code, weight_code] = True
    return values, valid


def _dequantized_bf16_chunks(
    weight_payload: bytes | bytearray | memoryview,
    scale_payload: bytes | bytearray | memoryview,
    weight_shape: Sequence[int],
    scale_shape: Sequence[int],
) -> Iterable[bytes]:
    try:
        import numpy as np
    except ImportError as exc:
        raise CanonicalTransformError("NumPy is required for matrix conversion") from exc
    rows, columns = _shape(weight_shape, "weight_shape")
    scale_rows, scale_columns = _shape(scale_shape, "scale_shape")
    if rows % FP8_BLOCK or columns % FP8_BLOCK:
        raise CanonicalTransformError(
            "wo_a weight dimensions must both be multiples of 128"
        )
    expected_scale_shape = (rows // FP8_BLOCK, columns // FP8_BLOCK)
    if (scale_rows, scale_columns) != expected_scale_shape:
        raise CanonicalTransformError(
            f"scale_shape {(scale_rows, scale_columns)!r} differs from "
            f"{expected_scale_shape!r}"
        )
    weight_view = memoryview(weight_payload).cast("B")
    scale_view = memoryview(scale_payload).cast("B")
    if len(weight_view) != rows * columns:
        raise CanonicalTransformError(
            f"weight payload has {len(weight_view)} bytes, expected {rows * columns}"
        )
    if len(scale_view) != scale_rows * scale_columns:
        raise CanonicalTransformError(
            f"scale payload has {len(scale_view)} bytes, expected "
            f"{scale_rows * scale_columns}"
        )
    weights = np.frombuffer(weight_view, dtype=np.uint8).reshape(rows, columns)
    scales = np.frombuffer(scale_view, dtype=np.uint8).reshape(
        scale_rows, scale_columns
    )
    if np.any(scales == 0xFF):
        location = tuple(int(index) for index in np.argwhere(scales == 0xFF)[0])
        raise CanonicalTransformError(
            f"wo_a scale at block {location!r} uses reserved E8M0 code 0xff"
        )
    table, valid = _fp8_scale_to_bf16_tables()
    for row_start in range(0, rows, FP8_BLOCK):
        block_row = row_start // FP8_BLOCK
        scale_by_column = np.repeat(scales[block_row], FP8_BLOCK)
        weight_block = weights[row_start : row_start + FP8_BLOCK]
        validity = valid[scale_by_column[None, :], weight_block]
        if not bool(np.all(validity)):
            row, column = (int(index) for index in np.argwhere(~validity)[0])
            raise CanonicalTransformError(
                "wo_a conversion encountered NaN or BF16 overflow at "
                f"element ({row_start + row}, {column})"
            )
        output = table[scale_by_column[None, :], weight_block]
        yield output.astype("<u2", copy=False).tobytes(order="C")


def dequantize_fp8_e8m0_matrix_to_bf16(
    weight_payload: bytes | bytearray | memoryview,
    scale_payload: bytes | bytearray | memoryview,
    weight_shape: Sequence[int],
    scale_shape: Sequence[int],
) -> bytes:
    """Dequantize a row-major block-scaled FP8 matrix to BF16 bytes."""

    return b"".join(
        _dequantized_bf16_chunks(
            weight_payload, scale_payload, weight_shape, scale_shape
        )
    )


def validate_native_mxfp4_pair(
    weight_payload: bytes | bytearray | memoryview,
    scale_payload: bytes | bytearray | memoryview,
    weight_shape: Sequence[int],
    scale_shape: Sequence[int],
) -> None:
    """Validate packed MXFP4/E8M0 retained byte-for-byte for mask ROM."""

    rows, packed_columns = _shape(weight_shape, "weight_shape")
    scale_rows, scale_columns = _shape(scale_shape, "scale_shape")
    if packed_columns % (MXFP4_BLOCK // 2):
        raise CanonicalTransformError(
            "packed MXFP4 columns must contain complete 32-value blocks"
        )
    expected_scale_shape = (rows, packed_columns // (MXFP4_BLOCK // 2))
    if (scale_rows, scale_columns) != expected_scale_shape:
        raise CanonicalTransformError(
            f"MXFP4 scale shape {(scale_rows, scale_columns)!r} differs from "
            f"{expected_scale_shape!r}"
        )
    weights = memoryview(weight_payload).cast("B")
    scales = memoryview(scale_payload).cast("B")
    if len(weights) != rows * packed_columns:
        raise CanonicalTransformError("packed MXFP4 weight byte count differs")
    if len(scales) != scale_rows * scale_columns:
        raise CanonicalTransformError("MXFP4 scale byte count differs")
    reserved = bytes(scales).find(b"\xff")
    if reserved >= 0:
        raise CanonicalTransformError(
            f"MXFP4 scale element {reserved} uses reserved E8M0 code 0xff"
        )


__all__ = [
    "CANONICAL_PLAN_SCHEMA",
    "CONVERT_SOURCE_SHA256",
    "CanonicalTransformError",
    "canonicalize_source_name",
    "dequantize_fp8_e8m0_matrix_to_bf16",
    "dtype_bytes",
    "fp8_e8m0_to_bf16_code",
    "partition_axis",
    "routed_expert_id",
    "slice_row_major_payload",
    "validate_native_mxfp4_pair",
]
