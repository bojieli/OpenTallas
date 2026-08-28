"""Independent inverse reconstruction of source ROM tensors from an image.

This checker deliberately does not call the image packer's encoding function.
It reconstructs the source values with a separate implementation, verifies every
interval and hash, and requires every non-payload image byte to be zero.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import struct
from typing import Any

from compiler.ir.model import load_strict_json


ROUNDTRIP_SCHEMA = "opentallas.rom_roundtrip_report.v1"


class InverseCheckError(ValueError):
    """Raised when a physical image cannot reconstruct its source tensors."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise InverseCheckError(f"{label} must be an integer >= {minimum}")
    return value


def _independent_encode(raw: dict[str, Any]) -> bytes:
    tensor_id = raw.get("id")
    dtype = raw.get("dtype")
    shape = raw.get("shape")
    values = raw.get("values")
    if not isinstance(tensor_id, str) or not isinstance(shape, list) or not shape:
        raise InverseCheckError("source ROM tensor metadata is malformed")
    count = 1
    for extent in shape:
        count *= _require_int(extent, f"tensor {tensor_id} extent", minimum=1)
    if not isinstance(values, list) or len(values) != count:
        raise InverseCheckError(f"source ROM tensor {tensor_id!r} payload is incomplete")
    for index, item in enumerate(values):
        if isinstance(item, bool) or not isinstance(item, int):
            raise InverseCheckError(
                f"source ROM tensor {tensor_id!r} value {index} is not integral"
            )
    try:
        if dtype == "i8":
            return struct.pack(f"<{count}b", *values)
        if dtype == "i32":
            return struct.pack(f"<{count}i", *values)
    except struct.error as exc:
        raise InverseCheckError(
            f"source ROM tensor {tensor_id!r} cannot be encoded: {exc}"
        ) from exc
    raise InverseCheckError(f"source ROM tensor {tensor_id!r} has unknown dtype")


def check_rom_image(source_ir: Path, deployment_dir: Path) -> dict[str, Any]:
    source = load_strict_json(source_ir)
    manifest = load_strict_json(deployment_dir / "tensor_manifest.json")
    try:
        image_path = deployment_dir / manifest["image"]["path"]
        image = image_path.read_bytes()
    except (KeyError, OSError, TypeError) as exc:
        raise InverseCheckError(f"cannot load governed ROM image: {exc}") from exc
    image_record = manifest.get("image")
    if not isinstance(image_record, dict):
        raise InverseCheckError("tensor manifest image record is missing")
    if _require_int(image_record.get("size_bytes"), "image size") != len(image):
        raise InverseCheckError("ROM image size differs from its manifest")
    if image_record.get("sha256") != _sha256(image):
        raise InverseCheckError("ROM image hash differs from its manifest")

    source_tensors = source.get("tensors")
    manifest_tensors = manifest.get("tensors")
    if not isinstance(source_tensors, list) or not isinstance(manifest_tensors, list):
        raise InverseCheckError("source or manifest tensor table is missing")
    if len(source_tensors) != len(manifest_tensors):
        raise InverseCheckError("source and manifest tensor counts differ")

    occupied = bytearray(len(image))
    reconstructed: list[dict[str, Any]] = []
    payload_bytes = 0
    for index, (raw_source, raw_manifest) in enumerate(
        zip(source_tensors, manifest_tensors, strict=True)
    ):
        if not isinstance(raw_source, dict) or not isinstance(raw_manifest, dict):
            raise InverseCheckError(f"tensor record {index} is malformed")
        identity = (
            raw_source.get("id"),
            raw_source.get("dtype"),
            raw_source.get("shape"),
            raw_source.get("storage"),
        )
        manifest_identity = (
            raw_manifest.get("tensor_id"),
            raw_manifest.get("dtype"),
            raw_manifest.get("shape"),
            raw_manifest.get("storage"),
        )
        if identity != manifest_identity or raw_manifest.get("tensor_index") != index:
            raise InverseCheckError(f"tensor record {index} identity mismatch")
        image_slice = raw_manifest.get("image")
        if raw_source.get("storage") != "rom":
            if image_slice is not None:
                raise InverseCheckError(f"non-ROM tensor {identity[0]!r} owns image bytes")
            continue
        if not isinstance(image_slice, dict):
            raise InverseCheckError(f"ROM tensor {identity[0]!r} lacks an image interval")
        expected = _independent_encode(raw_source)
        offset = _require_int(image_slice.get("offset_bytes"), "image offset")
        length = _require_int(image_slice.get("length_bytes"), "image length", minimum=1)
        if offset % _require_int(manifest.get("alignment_bytes"), "alignment", minimum=1):
            raise InverseCheckError(f"ROM tensor {identity[0]!r} is misaligned")
        end = offset + length
        if length != len(expected) or end > len(image):
            raise InverseCheckError(f"ROM tensor {identity[0]!r} interval is invalid")
        if any(occupied[offset:end]):
            raise InverseCheckError(f"ROM tensor {identity[0]!r} overlaps another tensor")
        occupied[offset:end] = bytes([1]) * length
        actual = image[offset:end]
        if image_slice.get("sha256") != _sha256(actual):
            raise InverseCheckError(f"ROM tensor {identity[0]!r} slice hash mismatch")
        if actual != expected:
            raise InverseCheckError(f"ROM tensor {identity[0]!r} inverse mismatch")
        payload_bytes += length
        reconstructed.append(
            {
                "length_bytes": length,
                "offset_bytes": offset,
                "sha256": _sha256(actual),
                "tensor_id": identity[0],
            }
        )

    padding_indices = [index for index, used in enumerate(occupied) if not used]
    if any(image[index] != 0 for index in padding_indices):
        raise InverseCheckError("ROM image contains nonzero padding data")
    canonical_content = b"".join(
        record["tensor_id"].encode("utf-8")
        + b"\0"
        + bytes.fromhex(record["sha256"])
        for record in reconstructed
    )
    return {
        "image_sha256": _sha256(image),
        "image_size_bytes": len(image),
        "model_id": source.get("model_id"),
        "padding_bytes": len(image) - payload_bytes,
        "payload_bytes": payload_bytes,
        "reconstructed_content_sha256": _sha256(canonical_content),
        "reconstructed_tensors": reconstructed,
        "schema": ROUNDTRIP_SCHEMA,
        "status": "pass",
    }
