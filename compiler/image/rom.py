"""Canonical little-endian ROM packing for compiler fixture tensors."""

from __future__ import annotations

import hashlib
import struct
from typing import Any

from compiler.ir.model import Model, Tensor


IMAGE_ALIGNMENT = 16
IMAGE_SCHEMA = "opentallas.tensor_manifest.v1"


class RomImageError(ValueError):
    """Raised when a tensor cannot be represented by the fixture image ABI."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _align(value: int, alignment: int = IMAGE_ALIGNMENT) -> int:
    return (value + alignment - 1) // alignment * alignment


def encode_tensor(tensor: Tensor) -> bytes:
    if tensor.values is None:
        raise RomImageError(f"ROM tensor {tensor.tensor_id!r} has no values")
    try:
        if tensor.dtype == "i8":
            return struct.pack(f"<{len(tensor.values)}b", *tensor.values)
        if tensor.dtype == "i32":
            return struct.pack(f"<{len(tensor.values)}i", *tensor.values)
    except struct.error as exc:
        raise RomImageError(f"cannot encode tensor {tensor.tensor_id!r}: {exc}") from exc
    raise RomImageError(f"unsupported image dtype {tensor.dtype!r}")


def decode_tensor_bytes(dtype: str, payload: bytes) -> tuple[int, ...]:
    if dtype == "i8":
        return tuple(struct.unpack(f"<{len(payload)}b", payload))
    if dtype == "i32":
        if len(payload) % 4:
            raise RomImageError("i32 payload length is not divisible by four")
        return tuple(struct.unpack(f"<{len(payload) // 4}i", payload))
    raise RomImageError(f"unsupported image dtype {dtype!r}")


def build_rom_image(model: Model) -> tuple[bytes, dict[str, Any]]:
    """Pack every ROM tensor once, with zero-filled alignment gaps."""

    image = bytearray()
    records: list[dict[str, Any]] = []
    for tensor in model.tensors:
        record: dict[str, Any] = {
            "dtype": tensor.dtype,
            "shape": list(tensor.shape),
            "size_bytes": tensor.size_bytes,
            "storage": tensor.storage,
            "tensor_id": tensor.tensor_id,
            "tensor_index": tensor.index,
        }
        if tensor.storage == "rom":
            offset = _align(len(image))
            if offset > len(image):
                image.extend(bytes(offset - len(image)))
            payload = encode_tensor(tensor)
            if len(payload) != tensor.size_bytes:
                raise RomImageError(
                    f"encoded tensor {tensor.tensor_id!r} has the wrong size"
                )
            image.extend(payload)
            record["image"] = {
                "length_bytes": len(payload),
                "offset_bytes": offset,
                "sha256": _sha256(payload),
            }
        else:
            record["image"] = None
        records.append(record)
    final_size = _align(len(image))
    if final_size > len(image):
        image.extend(bytes(final_size - len(image)))
    payload = bytes(image)
    manifest = {
        "alignment_bytes": IMAGE_ALIGNMENT,
        "byte_order": "little",
        "image": {
            "path": "rom_stage00_image.bin",
            "sha256": _sha256(payload),
            "size_bytes": len(payload),
        },
        "schema": IMAGE_SCHEMA,
        "tensors": records,
    }
    return payload, manifest
