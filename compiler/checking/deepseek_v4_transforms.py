"""Independent full-byte checks for DeepSeek V4 canonical transformations.

This checker does not call compiler.canonical transformation routines. Expected
values come through the separately implemented exact numeric reference, then a
full payload comparison binds every emitted byte.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import math
from typing import Any, Sequence

from compiler.ir.model import canonical_json_bytes
from runtime.reference.formats import (
    NumericReferenceError,
    binary32_bits_to_bf16_rne,
    decode_e4m3fn,
    decode_e8m0,
    encode_binary32_rne,
)


class DeepSeekV4TransformCheckError(RuntimeError):
    """Raised when a canonical payload differs from the independent reference."""


def _shape(value: Any, label: str) -> tuple[int, int]:
    if (
        isinstance(value, (str, bytes))
        or not isinstance(value, Sequence)
        or len(value) != 2
        or any(
            isinstance(extent, bool)
            or not isinstance(extent, int)
            or extent <= 0
            for extent in value
        )
    ):
        raise DeepSeekV4TransformCheckError(
            f"{label} must contain two positive integer extents"
        )
    return int(value[0]), int(value[1])


def _expected_bf16_code(weight_code: int, scale_code: int) -> int:
    weight = decode_e4m3fn(weight_code)
    scale = decode_e8m0(scale_code)
    if (
        not weight.finite
        or weight.value is None
        or not scale.finite
        or scale.value is None
    ):
        raise DeepSeekV4TransformCheckError(
            "source contains E4M3FN NaN or reserved E8M0"
        )
    try:
        binary32 = encode_binary32_rne(weight.value * scale.value)
        bf16 = binary32_bits_to_bf16_rne(binary32)
    except NumericReferenceError as exc:
        raise DeepSeekV4TransformCheckError(
            f"source product is not finite BF16: {exc}"
        ) from exc
    if bf16.saturated:
        raise DeepSeekV4TransformCheckError(
            "source product overflows finite BF16"
        )
    code = bf16.code
    if code == 0 and weight_code & 0x80:
        code = 0x8000
    return code


@lru_cache(maxsize=1)
def _reference_table() -> tuple[Any, Any]:
    try:
        import numpy as np
    except ImportError as exc:
        raise DeepSeekV4TransformCheckError(
            "NumPy is required for transform checking"
        ) from exc
    values = np.zeros((256, 256), dtype="<u2")
    valid = np.zeros((256, 256), dtype=np.bool_)
    for scale_code in range(0x100):
        for weight_code in range(0x100):
            try:
                values[scale_code, weight_code] = _expected_bf16_code(
                    weight_code, scale_code
                )
            except DeepSeekV4TransformCheckError:
                continue
            valid[scale_code, weight_code] = True
    return values, valid


def verify_dequantized_fp8_e8m0_bf16(
    weight_payload: bytes | bytearray | memoryview,
    scale_payload: bytes | bytearray | memoryview,
    output_payload: bytes | bytearray | memoryview,
    weight_shape: Sequence[int],
    scale_shape: Sequence[int],
) -> dict[str, Any]:
    """Compare every BF16 output element against the numeric reference."""

    try:
        import numpy as np
    except ImportError as exc:
        raise DeepSeekV4TransformCheckError(
            "NumPy is required for transform checking"
        ) from exc
    rows, columns = _shape(weight_shape, "weight_shape")
    scale_rows, scale_columns = _shape(scale_shape, "scale_shape")
    if rows % 128 or columns % 128:
        raise DeepSeekV4TransformCheckError(
            "weight dimensions must be multiples of 128"
        )
    if (scale_rows, scale_columns) != (rows // 128, columns // 128):
        raise DeepSeekV4TransformCheckError(
            "scale shape does not cover 128 by 128 blocks"
        )
    weight_bytes = memoryview(weight_payload).cast("B")
    scale_bytes = memoryview(scale_payload).cast("B")
    output_bytes = memoryview(output_payload).cast("B")
    if len(weight_bytes) != rows * columns:
        raise DeepSeekV4TransformCheckError("weight byte count differs from shape")
    if len(scale_bytes) != scale_rows * scale_columns:
        raise DeepSeekV4TransformCheckError("scale byte count differs from shape")
    if len(output_bytes) != rows * columns * 2:
        raise DeepSeekV4TransformCheckError("BF16 byte count differs from shape")
    weights = np.frombuffer(weight_bytes, dtype=np.uint8).reshape(rows, columns)
    scales = np.frombuffer(scale_bytes, dtype=np.uint8).reshape(
        scale_rows, scale_columns
    )
    observed = np.frombuffer(output_bytes, dtype="<u2").reshape(rows, columns)
    table, valid = _reference_table()
    checked = 0
    for block_row, row_start in enumerate(range(0, rows, 128)):
        scale_by_column = np.repeat(scales[block_row], 128)
        weight_block = weights[row_start : row_start + 128]
        validity = valid[scale_by_column[None, :], weight_block]
        if not bool(np.all(validity)):
            row, column = (int(index) for index in np.argwhere(~validity)[0])
            raise DeepSeekV4TransformCheckError(
                f"invalid source at element ({row_start + row}, {column})"
            )
        expected = table[scale_by_column[None, :], weight_block]
        difference = observed[row_start : row_start + 128] != expected
        if bool(np.any(difference)):
            row, column = (int(index) for index in np.argwhere(difference)[0])
            absolute_row = row_start + row
            raise DeepSeekV4TransformCheckError(
                f"BF16 mismatch at element ({absolute_row}, {column}): "
                f"0x{int(observed[absolute_row, column]):04x} versus "
                f"0x{int(expected[row, column]):04x}"
            )
        checked += weight_block.size
    report: dict[str, Any] = {
        "checked_element_count": checked,
        "output_sha256": hashlib.sha256(output_bytes).hexdigest(),
        "scale_sha256": hashlib.sha256(scale_bytes).hexdigest(),
        "schema": "opentallas.deepseek_v4_transform_check.v1",
        "status": "full_payload_match",
        "transform": "dequantize_fp8_e8m0_to_bf16_rne",
        "weight_sha256": hashlib.sha256(weight_bytes).hexdigest(),
    }
    report["check_id"] = hashlib.sha256(canonical_json_bytes(report)).hexdigest()
    return report


def verify_native_mxfp4_identity(
    source_weight: bytes | bytearray | memoryview,
    source_scale: bytes | bytearray | memoryview,
    output_weight: bytes | bytearray | memoryview,
    output_scale: bytes | bytearray | memoryview,
    weight_shape: Sequence[int],
    scale_shape: Sequence[int],
) -> dict[str, Any]:
    """Prove the native MXFP4 profile retains every packed and scale byte."""

    rows, packed_columns = _shape(weight_shape, "weight_shape")
    scale_rows, scale_columns = _shape(scale_shape, "scale_shape")
    if packed_columns % 16 or (scale_rows, scale_columns) != (
        rows,
        packed_columns // 16,
    ):
        raise DeepSeekV4TransformCheckError("MXFP4 weight/scale shapes disagree")
    expected_weight_bytes = math.prod((rows, packed_columns))
    expected_scale_bytes = math.prod((scale_rows, scale_columns))
    source_weight_view = memoryview(source_weight).cast("B")
    source_scale_view = memoryview(source_scale).cast("B")
    output_weight_view = memoryview(output_weight).cast("B")
    output_scale_view = memoryview(output_scale).cast("B")
    if len(source_weight_view) != expected_weight_bytes:
        raise DeepSeekV4TransformCheckError("source MXFP4 byte count differs")
    if len(source_scale_view) != expected_scale_bytes:
        raise DeepSeekV4TransformCheckError("source scale byte count differs")
    if bytes(source_weight_view) != bytes(output_weight_view):
        raise DeepSeekV4TransformCheckError(
            "native MXFP4 output differs from source packed bytes"
        )
    if bytes(source_scale_view) != bytes(output_scale_view):
        raise DeepSeekV4TransformCheckError(
            "native MXFP4 output differs from source E8M0 bytes"
        )
    reserved = bytes(source_scale_view).find(b"\xff")
    if reserved >= 0:
        raise DeepSeekV4TransformCheckError(
            f"source E8M0 element {reserved} is reserved"
        )
    report: dict[str, Any] = {
        "checked_scale_byte_count": expected_scale_bytes,
        "checked_weight_byte_count": expected_weight_bytes,
        "scale_sha256": hashlib.sha256(source_scale_view).hexdigest(),
        "schema": "opentallas.deepseek_v4_transform_check.v1",
        "status": "full_payload_match",
        "transform": "native_mxfp4_byte_identity",
        "weight_sha256": hashlib.sha256(source_weight_view).hexdigest(),
    }
    report["check_id"] = hashlib.sha256(canonical_json_bytes(report)).hexdigest()
    return report


__all__ = [
    "DeepSeekV4TransformCheckError",
    "verify_dequantized_fp8_e8m0_bf16",
    "verify_native_mxfp4_identity",
]
