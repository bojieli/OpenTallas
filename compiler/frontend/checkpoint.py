"""Strict, streaming safetensors checkpoint locking and payload access.

This module reads every byte of each declared shard exactly once while building
the lock. It verifies header structure, shape/dtype sizes, contiguous and
non-overlapping data intervals, index-to-shard assignment, complete tensor
coverage, required auxiliary files, whole-file hashes, and per-tensor payload
hashes. Canonical output contains no timestamps, hostnames, or local paths.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
from typing import Any, BinaryIO

from compiler.ir.model import IRValidationError, canonical_json_bytes, load_strict_json


CHECKPOINT_SOURCE_SCHEMA = "opentallas.checkpoint_source.v1"
CHECKPOINT_LOCK_SCHEMA = "opentallas.checkpoint_lock.v1"
MAX_HEADER_BYTES = 512 * 1024 * 1024
MAX_TENSOR_RANK = 16
MAX_TENSOR_ELEMENTS = (1 << 63) - 1
CHUNK_BYTES = 8 * 1024 * 1024
REVISION = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

# Safetensors names used by the pinned DeepSeek inventories plus the ordinary
# byte-aligned scalar formats. DeepSeek's packed FP4 payload is represented as
# I8 by the released checkpoint; this reader does not invent a nibble format.
DTYPE_BITS = {
    "BOOL": 8,
    "U8": 8,
    "I8": 8,
    "F8_E4M3": 8,
    "F8_E5M2": 8,
    "F8_E8M0": 8,
    "U16": 16,
    "I16": 16,
    "F16": 16,
    "BF16": 16,
    "U32": 32,
    "I32": 32,
    "F32": 32,
    "U64": 64,
    "I64": 64,
    "F64": 64,
}


class CheckpointError(RuntimeError):
    """Raised when checkpoint identity, structure, or content fails closed."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(CHUNK_BYTES):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise CheckpointError(f"cannot hash required file {path.name!r}: {exc}") from exc
    return digest.hexdigest(), size


def _strict_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CheckpointError(f"duplicate JSON key {key!r} in {label}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CheckpointError(f"non-finite JSON number {token!r} in {label}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"invalid JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise CheckpointError(f"expected a JSON object in {label}")
    return value


def _exact_keys(
    value: dict[str, Any], required: set[str], optional: set[str], label: str
) -> None:
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - required - optional)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing {missing}")
        if unknown:
            details.append(f"unknown {unknown}")
        raise CheckpointError(f"{label} has " + "; ".join(details))


def _safe_relative_path(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\x00" in value
        or "\\" in value
    ):
        raise CheckpointError(f"{label} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CheckpointError(f"{label} is not a safe relative path: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise CheckpointError(f"{label} is not in canonical POSIX form: {value!r}")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise CheckpointError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CheckpointError(f"{label} must be an integer >= {minimum}")
    return value


def _expected_file(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CheckpointError(f"{label} must be an object")
    _exact_keys(value, {"path", "sha256", "size_bytes"}, set(), label)
    return {
        "path": _safe_relative_path(value["path"], f"{label}.path"),
        "sha256": _sha256(value["sha256"], f"{label}.sha256"),
        "size_bytes": _integer(value["size_bytes"], f"{label}.size_bytes"),
    }


def _snapshot_file(snapshot: Path, relative: str) -> Path:
    # Hugging Face snapshots intentionally use symlinks to content-addressed
    # blobs, so the resolved target need not remain beneath the snapshot. The
    # logical path itself is traversal-safe and the bytes are cryptographically
    # bound in the generated lock.
    path = snapshot / relative
    if not path.is_file():
        raise CheckpointError(f"checkpoint snapshot is missing {relative!r}")
    return path


def validate_checkpoint_source(value: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a checkpoint-source declaration."""

    if not isinstance(value, dict):
        raise CheckpointError("checkpoint source must be an object")
    _exact_keys(
        value,
        {
            "checkpoint_index",
            "expected_files",
            "remote_code_policy",
            "repository",
            "required_files",
            "revision",
            "schema",
        },
        set(),
        "checkpoint source",
    )
    if value["schema"] != CHECKPOINT_SOURCE_SCHEMA:
        raise CheckpointError(
            f"unsupported checkpoint source schema {value['schema']!r}"
        )
    repository = value["repository"]
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise CheckpointError("repository must be one immutable owner/name identity")
    repository_parts = repository.split("/")
    if any(REPOSITORY_COMPONENT.fullmatch(part) is None for part in repository_parts):
        raise CheckpointError("repository must be one immutable owner/name identity")
    revision = value["revision"]
    if not isinstance(revision, str) or REVISION.fullmatch(revision) is None:
        raise CheckpointError("revision must be a 40-character lowercase commit hash")
    if value["remote_code_policy"] not in {"disabled", "reviewed_and_pinned"}:
        raise CheckpointError("remote_code_policy must be disabled or reviewed_and_pinned")
    checkpoint_index = _safe_relative_path(
        value["checkpoint_index"], "checkpoint_index"
    )
    raw_required = value["required_files"]
    if not isinstance(raw_required, list):
        raise CheckpointError("required_files must be an array")
    required = [
        _safe_relative_path(item, f"required_files[{index}]")
        for index, item in enumerate(raw_required)
    ]
    if required != sorted(required) or len(set(required)) != len(required):
        raise CheckpointError("required_files must be unique and lexicographically sorted")
    if checkpoint_index in required:
        raise CheckpointError("checkpoint_index is implicit and must not be duplicated")
    raw_expected = value["expected_files"]
    if not isinstance(raw_expected, list) or not raw_expected:
        raise CheckpointError("expected_files must be a non-empty array")
    expected = [
        _expected_file(item, f"expected_files[{index}]")
        for index, item in enumerate(raw_expected)
    ]
    expected_paths = [item["path"] for item in expected]
    if expected_paths != sorted(expected_paths) or len(set(expected_paths)) != len(
        expected_paths
    ):
        raise CheckpointError(
            "expected_files must have unique, lexicographically sorted paths"
        )
    missing_expectations = sorted(
        {checkpoint_index, *required} - set(expected_paths)
    )
    if missing_expectations:
        raise CheckpointError(
            "expected_files lacks checkpoint or required files: "
            f"{missing_expectations}"
        )
    return {
        "checkpoint_index": checkpoint_index,
        "expected_files": expected,
        "remote_code_policy": value["remote_code_policy"],
        "repository": repository,
        "required_files": required,
        "revision": revision,
        "schema": CHECKPOINT_SOURCE_SCHEMA,
    }


def load_checkpoint_source(path: Path) -> dict[str, Any]:
    try:
        value = load_strict_json(path)
    except (OSError, ValueError) as exc:
        raise CheckpointError(f"cannot load checkpoint source {path}: {exc}") from exc
    return validate_checkpoint_source(value)


def _shape(value: Any, tensor_name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) > MAX_TENSOR_RANK:
        raise CheckpointError(
            f"tensor {tensor_name!r} shape must be an array of rank <= {MAX_TENSOR_RANK}"
        )
    result: list[int] = []
    elements = 1
    for index, extent in enumerate(value):
        if isinstance(extent, bool) or not isinstance(extent, int) or extent < 0:
            raise CheckpointError(
                f"tensor {tensor_name!r} extent {index} must be a nonnegative integer"
            )
        elements *= extent
        if elements > MAX_TENSOR_ELEMENTS:
            raise CheckpointError(f"tensor {tensor_name!r} element count overflows")
        result.append(extent)
    return tuple(result)


def _offsets(value: Any, tensor_name: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
        or value[0] < 0
        or value[1] < value[0]
    ):
        raise CheckpointError(f"tensor {tensor_name!r} has invalid data_offsets")
    return value[0], value[1]


@dataclass(frozen=True)
class TensorInterval:
    name: str
    dtype: str
    shape: tuple[int, ...]
    start: int
    end: int

    @property
    def size_bytes(self) -> int:
        return self.end - self.start


def _parse_header(
    header: dict[str, Any], shard_name: str
) -> tuple[dict[str, Any] | None, tuple[TensorInterval, ...]]:
    raw_metadata = header.get("__metadata__")
    if raw_metadata is not None:
        if not isinstance(raw_metadata, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in raw_metadata.items()
        ):
            raise CheckpointError(
                f"safetensors __metadata__ in {shard_name!r} must map strings to strings"
            )
        metadata: dict[str, Any] | None = dict(sorted(raw_metadata.items()))
    else:
        metadata = None

    intervals: list[TensorInterval] = []
    for tensor_name, raw in header.items():
        if tensor_name == "__metadata__":
            continue
        if (
            not isinstance(tensor_name, str)
            or not tensor_name
            or "\x00" in tensor_name
            or len(tensor_name) > 4096
        ):
            raise CheckpointError(f"invalid tensor name in shard {shard_name!r}")
        if not isinstance(raw, dict):
            raise CheckpointError(f"tensor {tensor_name!r} metadata must be an object")
        _exact_keys(
            raw,
            {"data_offsets", "dtype", "shape"},
            set(),
            f"tensor {tensor_name!r}",
        )
        dtype = raw["dtype"]
        if dtype not in DTYPE_BITS:
            raise CheckpointError(
                f"tensor {tensor_name!r} uses unsupported dtype {dtype!r}"
            )
        shape = _shape(raw["shape"], tensor_name)
        start, end = _offsets(raw["data_offsets"], tensor_name)
        elements = math.prod(shape)
        expected_bits = elements * DTYPE_BITS[dtype]
        if expected_bits % 8 or end - start != expected_bits // 8:
            raise CheckpointError(
                f"tensor {tensor_name!r} storage differs from shape/dtype: "
                f"{end - start} bytes versus {expected_bits / 8:g}"
            )
        intervals.append(TensorInterval(tensor_name, dtype, shape, start, end))

    if not intervals:
        raise CheckpointError(f"safetensors shard {shard_name!r} has no tensors")
    ordered = tuple(sorted(intervals, key=lambda item: (item.start, item.end, item.name)))
    cursor = 0
    for interval in ordered:
        if interval.start != cursor:
            relation = "overlap" if interval.start < cursor else "gap"
            raise CheckpointError(
                f"safetensors shard {shard_name!r} has a data {relation} before "
                f"tensor {interval.name!r}: expected offset {cursor}, got {interval.start}"
            )
        cursor = interval.end
    return metadata, ordered


def _read_exact(handle: BinaryIO, size: int, label: str) -> bytes:
    payload = handle.read(size)
    if len(payload) != size:
        raise CheckpointError(f"short read while reading {label}")
    return payload


def _inspect_shard(path: Path, logical_path: str) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            prefix = _read_exact(handle, 8, f"{logical_path} prefix")
            header_length = struct.unpack("<Q", prefix)[0]
            if not 1 < header_length <= MAX_HEADER_BYTES:
                raise CheckpointError(
                    f"implausible safetensors header length {header_length} in {logical_path!r}"
                )
            raw_header = _read_exact(
                handle, header_length, f"{logical_path} header"
            )
            if b"\x00" in raw_header:
                raise CheckpointError(
                    f"safetensors header in {logical_path!r} contains NUL padding"
                )
            header = _strict_json_bytes(raw_header, f"{logical_path} header")
            metadata, intervals = _parse_header(header, logical_path)

            file_digest = hashlib.sha256(prefix + raw_header)
            tensor_records: list[dict[str, Any]] = []
            for interval in intervals:
                tensor_digest = hashlib.sha256()
                remaining = interval.size_bytes
                while remaining:
                    chunk = handle.read(min(remaining, CHUNK_BYTES))
                    if not chunk:
                        raise CheckpointError(
                            f"short payload for tensor {interval.name!r} in {logical_path!r}"
                        )
                    tensor_digest.update(chunk)
                    file_digest.update(chunk)
                    remaining -= len(chunk)
                tensor_records.append(
                    {
                        "data_offsets": [interval.start, interval.end],
                        "dtype": interval.dtype,
                        "name": interval.name,
                        "payload_sha256": tensor_digest.hexdigest(),
                        "shape": list(interval.shape),
                        "size_bytes": interval.size_bytes,
                    }
                )
            if handle.read(1):
                raise CheckpointError(
                    f"safetensors shard {logical_path!r} contains trailing payload bytes"
                )
    except OSError as exc:
        raise CheckpointError(f"cannot inspect shard {logical_path!r}: {exc}") from exc

    data_size = intervals[-1].end
    file_size = 8 + header_length + data_size
    return {
        "data_size_bytes": data_size,
        "file_sha256": file_digest.hexdigest(),
        "file_size_bytes": file_size,
        "header_length_bytes": header_length,
        "header_sha256": _sha256_bytes(raw_header),
        "metadata": metadata,
        "path": logical_path,
        "tensor_count": len(tensor_records),
        "tensors": tensor_records,
    }


def _parse_index(index: dict[str, Any], logical_path: str) -> tuple[int, dict[str, str]]:
    _exact_keys(index, {"metadata", "weight_map"}, set(), "checkpoint index")
    metadata = index["metadata"]
    weight_map = index["weight_map"]
    if not isinstance(metadata, dict):
        raise CheckpointError("checkpoint index metadata must be an object")
    total_size = metadata.get("total_size")
    if (
        isinstance(total_size, bool)
        or not isinstance(total_size, int)
        or total_size < 0
    ):
        raise CheckpointError("checkpoint index metadata.total_size is required")
    if not isinstance(weight_map, dict) or not weight_map:
        raise CheckpointError("checkpoint index weight_map must be non-empty")
    normalized: dict[str, str] = {}
    for tensor_name, shard_name in weight_map.items():
        if (
            not isinstance(tensor_name, str)
            or not tensor_name
            or "\x00" in tensor_name
            or tensor_name == "__metadata__"
        ):
            raise CheckpointError(f"invalid tensor name in {logical_path!r}")
        normalized[tensor_name] = _safe_relative_path(
            shard_name, f"weight_map[{tensor_name!r}]"
        )
    return total_size, normalized


def _required_file_manifest(snapshot: Path, relative: str) -> dict[str, Any]:
    digest, size = _sha256_file(_snapshot_file(snapshot, relative))
    return {"path": relative, "sha256": digest, "size_bytes": size}


def _require_expected_file(
    observed: dict[str, Any], expected: dict[str, Any], label: str
) -> None:
    if observed != expected:
        raise CheckpointError(
            f"{label} {observed.get('path')!r} differs from its immutable source "
            f"expectation: observed sha256={observed.get('sha256')}, "
            f"size={observed.get('size_bytes')}; expected "
            f"sha256={expected.get('sha256')}, size={expected.get('size_bytes')}"
        )


def _lock_without_id(
    source: dict[str, Any],
    files: list[dict[str, Any]],
    shards: list[dict[str, Any]],
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    return {
        "checkpoint": checkpoint,
        "files": files,
        "schema": CHECKPOINT_LOCK_SCHEMA,
        "shards": shards,
        "source": source,
    }


def build_checkpoint_lock(snapshot: Path, source: dict[str, Any]) -> dict[str, Any]:
    """Read and bind every declared checkpoint and auxiliary-file byte."""

    source = validate_checkpoint_source(source)
    snapshot = snapshot.resolve()
    if not snapshot.is_dir():
        raise CheckpointError(f"checkpoint snapshot is not a directory: {snapshot}")
    expected_files = {item["path"]: item for item in source["expected_files"]}
    index_path = _snapshot_file(snapshot, source["checkpoint_index"])
    try:
        index_raw = index_path.read_bytes()
    except OSError as exc:
        raise CheckpointError(f"cannot read checkpoint index: {exc}") from exc
    index_manifest = {
        "path": source["checkpoint_index"],
        "sha256": _sha256_bytes(index_raw),
        "size_bytes": len(index_raw),
    }
    _require_expected_file(
        index_manifest,
        expected_files[source["checkpoint_index"]],
        "checkpoint index",
    )
    index = _strict_json_bytes(index_raw, source["checkpoint_index"])
    expected_total_size, weight_map = _parse_index(
        index, source["checkpoint_index"]
    )

    required_paths = sorted(
        [source["checkpoint_index"], *source["required_files"]]
    )
    files: list[dict[str, Any]] = []
    for relative in required_paths:
        manifest = (
            index_manifest
            if relative == source["checkpoint_index"]
            else _required_file_manifest(snapshot, relative)
        )
        _require_expected_file(
            manifest, expected_files[relative], "required checkpoint file"
        )
        files.append(manifest)

    shard_names = sorted(set(weight_map.values()))
    declared_paths = set(required_paths) | set(shard_names)
    missing_expectations = sorted(declared_paths - expected_files.keys())
    extra_expectations = sorted(expected_files.keys() - declared_paths)
    if missing_expectations or extra_expectations:
        raise CheckpointError(
            "source expectations differ from index-derived checkpoint files: "
            f"missing={missing_expectations[:8]}, extra={extra_expectations[:8]}"
        )
    shards: list[dict[str, Any]] = []
    for name in shard_names:
        path = _snapshot_file(snapshot, name)
        try:
            observed_size = path.stat().st_size
        except OSError as exc:
            raise CheckpointError(f"cannot stat shard {name!r}: {exc}") from exc
        expected = expected_files[name]
        if observed_size != expected["size_bytes"]:
            raise CheckpointError(
                f"checkpoint shard {name!r} has {observed_size} bytes but its "
                f"immutable source expectation declares {expected['size_bytes']}"
            )
        shard = _inspect_shard(path, name)
        _require_expected_file(
            {
                "path": shard["path"],
                "sha256": shard["file_sha256"],
                "size_bytes": shard["file_size_bytes"],
            },
            expected,
            "checkpoint shard",
        )
        shards.append(shard)
    observed: dict[str, str] = {}
    all_tensor_records: list[dict[str, Any]] = []
    payload_bytes = 0
    for shard in shards:
        for tensor in shard["tensors"]:
            tensor_name = tensor["name"]
            if tensor_name in observed:
                raise CheckpointError(
                    f"tensor {tensor_name!r} appears in multiple checkpoint shards"
                )
            observed[tensor_name] = shard["path"]
            payload_bytes += tensor["size_bytes"]
            all_tensor_records.append(
                {
                    "dtype": tensor["dtype"],
                    "name": tensor_name,
                    "payload_sha256": tensor["payload_sha256"],
                    "shape": tensor["shape"],
                    "shard": shard["path"],
                    "size_bytes": tensor["size_bytes"],
                }
            )
    missing = sorted(weight_map.keys() - observed.keys())
    extra = sorted(observed.keys() - weight_map.keys())
    wrong_shard = sorted(
        tensor_name
        for tensor_name in weight_map.keys() & observed.keys()
        if weight_map[tensor_name] != observed[tensor_name]
    )
    if missing or extra or wrong_shard:
        raise CheckpointError(
            "checkpoint index/header coverage differs: "
            f"missing={missing[:8]}, extra={extra[:8]}, wrong_shard={wrong_shard[:8]}"
        )
    if payload_bytes != expected_total_size:
        raise CheckpointError(
            f"checkpoint payload is {payload_bytes} bytes but index declares "
            f"{expected_total_size}"
        )
    all_tensor_records.sort(key=lambda item: item["name"])
    tensor_content_sha256 = _sha256_bytes(
        canonical_json_bytes(all_tensor_records)
    )
    checkpoint = {
        "payload_bytes": payload_bytes,
        "shard_count": len(shards),
        "tensor_content_sha256": tensor_content_sha256,
        "tensor_count": len(observed),
    }
    body = _lock_without_id(source, files, shards, checkpoint)
    return {**body, "lock_id": _sha256_bytes(canonical_json_bytes(body))}


def _validate_lock_structure(lock: dict[str, Any]) -> None:
    if not isinstance(lock, dict):
        raise CheckpointError("checkpoint lock must be an object")
    _exact_keys(
        lock,
        {"checkpoint", "files", "lock_id", "schema", "shards", "source"},
        set(),
        "checkpoint lock",
    )
    if lock["schema"] != CHECKPOINT_LOCK_SCHEMA:
        raise CheckpointError(f"unsupported checkpoint lock schema {lock['schema']!r}")
    _sha256(lock["lock_id"], "checkpoint lock_id")
    source = validate_checkpoint_source(lock["source"])
    expected_by_path = {item["path"]: item for item in source["expected_files"]}

    if not isinstance(lock["files"], list) or not lock["files"]:
        raise CheckpointError("checkpoint files must be a non-empty array")
    files = [
        _expected_file(item, f"checkpoint files[{index}]")
        for index, item in enumerate(lock["files"])
    ]
    file_paths = [item["path"] for item in files]
    expected_auxiliary_paths = sorted(
        [source["checkpoint_index"], *source["required_files"]]
    )
    if file_paths != expected_auxiliary_paths:
        raise CheckpointError(
            "checkpoint lock file table must exactly cover the index and required files"
        )
    for item in files:
        if item != expected_by_path.get(item["path"]):
            raise CheckpointError(
                f"checkpoint lock file {item['path']!r} differs from its source expectation"
            )

    if not isinstance(lock["shards"], list) or not lock["shards"]:
        raise CheckpointError("checkpoint shards must be a non-empty array")
    shard_paths: list[str] = []
    tensor_names: set[str] = set()
    all_tensor_records: list[dict[str, Any]] = []
    payload_bytes = 0
    for shard_index, shard in enumerate(lock["shards"]):
        label = f"checkpoint shards[{shard_index}]"
        if not isinstance(shard, dict):
            raise CheckpointError(f"{label} must be an object")
        _exact_keys(
            shard,
            {
                "data_size_bytes",
                "file_sha256",
                "file_size_bytes",
                "header_length_bytes",
                "header_sha256",
                "metadata",
                "path",
                "tensor_count",
                "tensors",
            },
            set(),
            label,
        )
        path = _safe_relative_path(shard["path"], f"{label}.path")
        shard_paths.append(path)
        file_sha256 = _sha256(shard["file_sha256"], f"{label}.file_sha256")
        _sha256(shard["header_sha256"], f"{label}.header_sha256")
        header_length = _integer(
            shard["header_length_bytes"],
            f"{label}.header_length_bytes",
            minimum=2,
        )
        if header_length > MAX_HEADER_BYTES:
            raise CheckpointError(f"{label}.header_length_bytes exceeds the limit")
        data_size = _integer(
            shard["data_size_bytes"], f"{label}.data_size_bytes"
        )
        file_size = _integer(
            shard["file_size_bytes"], f"{label}.file_size_bytes", minimum=10
        )
        if file_size != 8 + header_length + data_size:
            raise CheckpointError(f"{label} has inconsistent file/header/data sizes")
        metadata = shard["metadata"]
        if metadata is not None and (
            not isinstance(metadata, dict)
            or any(
                not isinstance(key, str) or not isinstance(value, str)
                for key, value in metadata.items()
            )
        ):
            raise CheckpointError(f"{label}.metadata must be null or string pairs")
        tensor_count = _integer(
            shard["tensor_count"], f"{label}.tensor_count", minimum=1
        )
        tensors = shard["tensors"]
        if not isinstance(tensors, list) or len(tensors) != tensor_count:
            raise CheckpointError(f"{label}.tensors differs from tensor_count")
        cursor = 0
        sort_keys: list[tuple[int, int, str]] = []
        for tensor_index, tensor in enumerate(tensors):
            tensor_label = f"{label}.tensors[{tensor_index}]"
            if not isinstance(tensor, dict):
                raise CheckpointError(f"{tensor_label} must be an object")
            _exact_keys(
                tensor,
                {
                    "data_offsets",
                    "dtype",
                    "name",
                    "payload_sha256",
                    "shape",
                    "size_bytes",
                },
                set(),
                tensor_label,
            )
            name = tensor["name"]
            if (
                not isinstance(name, str)
                or not name
                or "\x00" in name
                or len(name) > 4096
                or name == "__metadata__"
            ):
                raise CheckpointError(f"{tensor_label}.name is invalid")
            if name in tensor_names:
                raise CheckpointError(f"duplicate locked tensor name {name!r}")
            tensor_names.add(name)
            dtype = tensor["dtype"]
            if dtype not in DTYPE_BITS:
                raise CheckpointError(f"{tensor_label}.dtype is unsupported")
            shape = _shape(tensor["shape"], name)
            start, end = _offsets(tensor["data_offsets"], name)
            size = _integer(tensor["size_bytes"], f"{tensor_label}.size_bytes")
            if start != cursor:
                relation = "overlap" if start < cursor else "gap"
                raise CheckpointError(f"{label} has a tensor data {relation}")
            if end - start != size:
                raise CheckpointError(f"{tensor_label} has inconsistent offsets and size")
            expected_bits = math.prod(shape) * DTYPE_BITS[dtype]
            if expected_bits % 8 or size != expected_bits // 8:
                raise CheckpointError(
                    f"{tensor_label} storage differs from shape/dtype"
                )
            payload_sha256 = _sha256(
                tensor["payload_sha256"], f"{tensor_label}.payload_sha256"
            )
            cursor = end
            payload_bytes += size
            sort_keys.append((start, end, name))
            all_tensor_records.append(
                {
                    "dtype": dtype,
                    "name": name,
                    "payload_sha256": payload_sha256,
                    "shape": list(shape),
                    "shard": path,
                    "size_bytes": size,
                }
            )
        if sort_keys != sorted(sort_keys):
            raise CheckpointError(f"{label}.tensors are not in canonical interval order")
        if cursor != data_size:
            raise CheckpointError(f"{label} tensor intervals do not cover all shard data")
        expected_shard = expected_by_path.get(path)
        if expected_shard != {
            "path": path,
            "sha256": file_sha256,
            "size_bytes": file_size,
        }:
            raise CheckpointError(
                f"checkpoint shard {path!r} differs from its source expectation"
            )
    if shard_paths != sorted(shard_paths) or len(set(shard_paths)) != len(shard_paths):
        raise CheckpointError("checkpoint shard paths must be unique and sorted")
    if set(file_paths) & set(shard_paths):
        raise CheckpointError("checkpoint shards overlap required file paths")
    if set(file_paths) | set(shard_paths) != set(expected_by_path):
        raise CheckpointError(
            "checkpoint lock does not exactly cover every source-expected file"
        )

    checkpoint = lock["checkpoint"]
    if not isinstance(checkpoint, dict):
        raise CheckpointError("checkpoint summary must be an object")
    _exact_keys(
        checkpoint,
        {
            "payload_bytes",
            "shard_count",
            "tensor_content_sha256",
            "tensor_count",
        },
        set(),
        "checkpoint summary",
    )
    summary_payload_bytes = _integer(
        checkpoint["payload_bytes"], "checkpoint payload_bytes"
    )
    summary_shards = _integer(
        checkpoint["shard_count"], "checkpoint shard_count", minimum=1
    )
    summary_tensors = _integer(
        checkpoint["tensor_count"], "checkpoint tensor_count", minimum=1
    )
    summary_content_sha256 = _sha256(
        checkpoint["tensor_content_sha256"], "checkpoint tensor_content_sha256"
    )
    all_tensor_records.sort(key=lambda item: item["name"])
    observed_content_sha256 = _sha256_bytes(
        canonical_json_bytes(all_tensor_records)
    )
    if (
        summary_payload_bytes != payload_bytes
        or summary_shards != len(shard_paths)
        or summary_tensors != len(tensor_names)
        or summary_content_sha256 != observed_content_sha256
    ):
        raise CheckpointError("checkpoint summary differs from its shard/tensor tables")

    body = {
        "checkpoint": checkpoint,
        "files": files,
        "schema": CHECKPOINT_LOCK_SCHEMA,
        "shards": lock["shards"],
        "source": source,
    }
    try:
        observed_lock_id = _sha256_bytes(canonical_json_bytes(body))
    except IRValidationError as exc:
        raise CheckpointError(f"checkpoint lock is not canonical JSON: {exc}") from exc
    if lock["lock_id"] != observed_lock_id:
        raise CheckpointError("checkpoint lock_id does not bind the lock contents")


def load_checkpoint_lock(path: Path) -> dict[str, Any]:
    try:
        lock = load_strict_json(path)
    except (OSError, ValueError) as exc:
        raise CheckpointError(f"cannot load checkpoint lock {path}: {exc}") from exc
    _validate_lock_structure(lock)
    return lock


def validate_checkpoint_lock(lock: dict[str, Any]) -> dict[str, Any]:
    """Validate an in-memory lock before another compiler front end consumes it."""

    _validate_lock_structure(lock)
    return lock


def verify_checkpoint_lock(snapshot: Path, lock: dict[str, Any]) -> dict[str, Any]:
    """Rebuild a lock from local bytes and require canonical equality."""

    _validate_lock_structure(lock)
    rebuilt = build_checkpoint_lock(snapshot, lock["source"])
    if rebuilt != lock:
        raise CheckpointError(
            "checkpoint bytes or metadata differ from the governed checkpoint lock"
        )
    return rebuilt


class LockedCheckpointReader:
    """Reuse verified shard handles while consuming hash-locked tensor bytes.

    The reader validates the complete lock once, verifies each accessed shard
    header once, hashes every consumed tensor payload, and rejects a snapshot
    file whose device, inode, size, modification time, or metadata-change time
    changes while the reader is active. Both the open descriptor and its live
    snapshot path are checked so atomic path replacement cannot evade the guard.
    It is intentionally single-threaded; callbacks are completed before another
    tensor may be consumed.
    """

    def __init__(self, snapshot: Path, lock: dict[str, Any]):
        _validate_lock_structure(lock)
        try:
            resolved_snapshot = Path(snapshot).resolve()
        except TypeError as exc:
            raise CheckpointError("checkpoint snapshot must be a filesystem path") from exc
        if not resolved_snapshot.is_dir():
            raise CheckpointError(
                f"checkpoint snapshot is not a directory: {resolved_snapshot}"
            )
        self._snapshot = resolved_snapshot
        self._lock_id = lock["lock_id"]
        self._shards: dict[str, dict[str, Any]] = {}
        self._tensors: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
        for shard in lock["shards"]:
            logical_path = shard["path"]
            self._shards[logical_path] = shard
            for tensor in shard["tensors"]:
                self._tensors[tensor["name"]] = (shard, tensor)
        self._handles: dict[
            str, tuple[BinaryIO, tuple[int, int, int, int, int]]
        ] = {}
        self._accessed_tensors: set[str] = set()
        self._closed = False

    @property
    def lock_id(self) -> str:
        return self._lock_id

    @property
    def accessed_tensor_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._accessed_tensors))

    @property
    def accessed_shard_paths(self) -> tuple[str, ...]:
        return tuple(sorted(self._handles))

    def __enter__(self) -> LockedCheckpointReader:
        self._require_open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close(verify_unchanged=exc_type is None)

    def _require_open(self) -> None:
        if self._closed:
            raise CheckpointError("locked checkpoint reader is closed")

    @staticmethod
    def _fingerprint(
        stat_result: os.stat_result,
    ) -> tuple[int, int, int, int, int]:
        return (
            stat_result.st_dev,
            stat_result.st_ino,
            stat_result.st_size,
            stat_result.st_mtime_ns,
            stat_result.st_ctime_ns,
        )

    def _open_shard(self, shard: dict[str, Any]) -> BinaryIO:
        self._require_open()
        logical_path = _safe_relative_path(shard["path"], "locked shard path")
        cached = self._handles.get(logical_path)
        if cached is not None:
            return cached[0]
        shard_path = _snapshot_file(self._snapshot, logical_path)
        try:
            handle = shard_path.open("rb")
            stat_result = os.fstat(handle.fileno())
            if stat_result.st_size != shard["file_size_bytes"]:
                raise CheckpointError(
                    f"locked shard {logical_path!r} has a different file size"
                )
            prefix = _read_exact(handle, 8, f"{logical_path} prefix")
            header_length = struct.unpack("<Q", prefix)[0]
            if header_length != shard["header_length_bytes"]:
                raise CheckpointError(
                    f"locked shard {logical_path!r} has a different header length"
                )
            raw_header = _read_exact(handle, header_length, f"{logical_path} header")
            if _sha256_bytes(raw_header) != shard["header_sha256"]:
                raise CheckpointError(
                    f"locked shard {logical_path!r} has a different header"
                )
        except Exception:
            if "handle" in locals():
                handle.close()
            raise
        self._handles[logical_path] = (handle, self._fingerprint(stat_result))
        return handle

    def _tensor_entry(
        self, tensor_name: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        self._require_open()
        if not isinstance(tensor_name, str) or not tensor_name:
            raise CheckpointError("tensor_name must be a non-empty string")
        entry = self._tensors.get(tensor_name)
        if entry is None:
            raise CheckpointError(
                f"checkpoint lock contains 0 records for tensor {tensor_name!r}"
            )
        return entry

    def tensor_record(self, tensor_name: str) -> dict[str, Any]:
        """Return immutable identity metadata for one locked tensor."""

        shard, tensor = self._tensor_entry(tensor_name)
        return {
            "dtype": tensor["dtype"],
            "name": tensor["name"],
            "payload_sha256": tensor["payload_sha256"],
            "shape": list(tensor["shape"]),
            "shard": shard["path"],
            "size_bytes": tensor["size_bytes"],
        }

    def consume_tensor_payload(
        self,
        tensor_name: str,
        consumer: Callable[[bytes], None],
        *,
        chunk_bytes: int = CHUNK_BYTES,
    ) -> dict[str, Any]:
        """Feed every locked payload byte to ``consumer`` and verify its hash."""

        if not callable(consumer):
            raise CheckpointError("tensor payload consumer must be callable")
        chunk_bytes = _integer(chunk_bytes, "chunk_bytes", minimum=1)
        if chunk_bytes > 256 * 1024 * 1024:
            raise CheckpointError("chunk_bytes exceeds the 256-MiB reader bound")
        shard, tensor = self._tensor_entry(tensor_name)
        handle = self._open_shard(shard)
        start, end = tensor["data_offsets"]
        remaining = end - start
        digest = hashlib.sha256()
        try:
            handle.seek(8 + shard["header_length_bytes"] + start)
            while remaining:
                chunk = handle.read(min(remaining, chunk_bytes))
                if not chunk:
                    raise CheckpointError(
                        f"short read while reading tensor {tensor_name!r}"
                    )
                digest.update(chunk)
                consumer(chunk)
                remaining -= len(chunk)
        except OSError as exc:
            raise CheckpointError(
                f"cannot read tensor {tensor_name!r}: {exc}"
            ) from exc
        if digest.hexdigest() != tensor["payload_sha256"]:
            raise CheckpointError(
                f"tensor {tensor_name!r} payload differs from its lock"
            )
        self._accessed_tensors.add(tensor_name)
        return self.tensor_record(tensor_name)

    def close(self, *, verify_unchanged: bool = True) -> None:
        """Close all shard handles, optionally rejecting concurrent mutation."""

        if self._closed:
            return
        first_error: CheckpointError | None = None
        if verify_unchanged:
            for logical_path, (handle, fingerprint) in self._handles.items():
                try:
                    observed_handle = self._fingerprint(os.fstat(handle.fileno()))
                    observed_path = self._fingerprint(
                        (self._snapshot / logical_path).stat()
                    )
                except OSError as exc:
                    if first_error is None:
                        first_error = CheckpointError(
                            f"locked shard {logical_path!r} changed while reader was "
                            f"active: cannot restat descriptor and snapshot path: {exc}"
                        )
                    continue
                if (
                    observed_handle != fingerprint
                    or observed_path != fingerprint
                ) and first_error is None:
                    first_error = CheckpointError(
                        f"locked shard {logical_path!r} changed while reader was active"
                    )
        for handle, _ in self._handles.values():
            handle.close()
        self._handles.clear()
        self._closed = True
        if first_error is not None:
            raise first_error


def read_tensor_payload(
    snapshot: Path, lock: dict[str, Any], tensor_name: str
) -> bytes:
    """Read one tensor by locked interval and verify its exact payload hash."""

    chunks: list[bytes] = []
    with LockedCheckpointReader(snapshot, lock) as reader:
        reader.consume_tensor_payload(tensor_name, chunks.append)
    return b"".join(chunks)
