"""Build a byte-exact parameter package for one DeepSeek V4 ``HC_PRE`` site.

This compiler lane packages the three learned tensors and the frozen
SPEC-NUM 1.1 NUM-6.10 contract for the layer-0 attention pre-mix.  It does not
emit microcode, activations, result vectors, or an execution claim.

Publication is descriptor-anchored and create-once inside a caller-trusted
output parent.  A process with the same filesystem identity must not mutate
that parent concurrently.  Existing output-path symlinks are resolved before
the resolved parent is opened and adopted as this trust boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import ExitStack
import ctypes
from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import struct
from typing import Any

from compiler.checking.deepseek_v4_application import (
    DeepSeekV4ApplicationCheckError,
    MANIFEST_FILENAME,
    VERIFICATION_FILENAME,
    verify_canonical_application,
)
from compiler.checking.deepseek_v4_hc_pre_slice import (
    verify_deepseek_v4_hc_pre_deployment,
    verify_deepseek_v4_hc_pre_roundtrip,
)
from compiler.frontend.checkpoint import validate_checkpoint_lock
from compiler.frontend.deepseek_v4 import (
    MODEL_ID,
    REPOSITORY,
    REVISION,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.ir.model import (
    canonical_json_bytes,
    write_canonical_json,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_hc_pre_deployment.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_hc_pre_semantic.v1"
TENSOR_SCHEMA = "opentallas.deepseek_v4_hc_pre_tensors.v1"
NUMERIC_PROFILE_SCHEMA = "opentallas.deepseek_v4_hc_pre_numeric_profile.v1"
COUNTER_CONTRACT_SCHEMA = "opentallas.deepseek_v4_hc_pre_counter_contract.v1"
COVERAGE_SCHEMA = "opentallas.deepseek_v4_hc_pre_coverage.v1"
NUMERIC_PROFILE_ID = "opentallas.deepseek_v4_hc_pre_numeric.v1"
COMPILER_VERSION = "0.1.0"

BASE_NAME = "layers.0.hc_attn_base"
PROJECTION_NAME = "layers.0.hc_attn_fn"
SCALE_NAME = "layers.0.hc_attn_scale"

HC_MULTIPLIER = 4
HIDDEN_SIZE = 4096
FLATTENED_WIDTH = HC_MULTIPLIER * HIDDEN_SIZE
MIX_FIELD_COUNT = (2 + HC_MULTIPLIER) * HC_MULTIPLIER
SINKHORN_ITERATIONS = 20
NORM_EPSILON_BINARY32 = 0x358637BD
HC_EPSILON_BINARY32 = 0x358637BD
MODEL_PARALLEL = 4

BASE_SHAPE = [MIX_FIELD_COUNT]
PROJECTION_SHAPE = [MIX_FIELD_COUNT, FLATTENED_WIDTH]
SCALE_SHAPE = [3]
BASE_BYTES = MIX_FIELD_COUNT * 4
PROJECTION_BYTES = MIX_FIELD_COUNT * FLATTENED_WIDTH * 4
SCALE_BYTES = 3 * 4
TOTAL_PARAMETER_BYTES = BASE_BYTES + PROJECTION_BYTES + SCALE_BYTES

# This is the deterministic four-rank official plan identity produced by
# compiler.canonical.plan for the pinned release.  Checking it here avoids
# rebuilding the 72,317-record plan during a three-tensor package build.
OFFICIAL_CANONICAL_PLAN_ID = (
    "7b87ee6168e13cf9be7c5e812a13490b6f264bda78a96ceb2e7c02580c49b3a7"
)
OFFICIAL_CANONICAL_PLAN_SCHEMA = "opentallas.deepseek_v4_canonical_plan.v1"
OFFICIAL_CANONICAL_INPUT_COUNT = 72_317

MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
KERNEL_SOURCE_SHA256 = (
    "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
)

_EXPECTED_RESOURCES = {
    BASE_NAME: (BASE_SHAPE, BASE_BYTES, "base"),
    PROJECTION_NAME: (PROJECTION_SHAPE, PROJECTION_BYTES, "projection"),
    SCALE_NAME: (SCALE_SHAPE, SCALE_BYTES, "scale"),
}
_EXPECTED_NAMES = frozenset(_EXPECTED_RESOURCES)
_READ_CHUNK_BYTES = 8 * 1024 * 1024
_MAX_APPLICATION_JSON_BYTES = 1024 * 1024


class DeepSeekV4HCPreBuildError(RuntimeError):
    """Raised when canonical tensors cannot form the fixed HC_PRE package."""


@dataclass(frozen=True)
class _StableFile:
    descriptor: int
    fingerprint: tuple[int, ...]
    relative_path: str
    root_descriptor: int
    size_bytes: int


def _fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _require_secure_file_operations() -> None:
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_NONBLOCK")
        or not hasattr(os, "O_CLOEXEC")
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "pread")
        or os.open not in os.supports_dir_fd
        or os.mkdir not in os.supports_dir_fd
        or os.rmdir not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
        or os.unlink not in os.supports_dir_fd
    ):
        raise DeepSeekV4HCPreBuildError(
            "platform lacks race-resistant bounded file operations"
        )


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4HCPreBuildError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4HCPreBuildError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4HCPreBuildError(f"{label} is not canonical POSIX")
    return value


def _open_root(stack: ExitStack, root: Path, label: str) -> tuple[int, tuple[int, ...]]:
    _require_secure_file_operations()
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreBuildError(
            f"cannot open {label} descriptor without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4HCPreBuildError(f"{label} is not a directory")
    return descriptor, _fingerprint(metadata)


def _verify_root_binding(root: Path, descriptor: int, label: str) -> None:
    """Require the current path to resolve to the already-open directory."""

    _verify_root_stable(root, descriptor, _fingerprint(os.fstat(descriptor)), label)


def _create_private_directory(
    stack: ExitStack,
    *,
    parent: Path,
    parent_descriptor: int,
    prefix: str,
) -> tuple[Path, str, int]:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    for _ in range(128):
        name = f".{prefix}.tmp-{secrets.token_hex(16)}"
        try:
            os.mkdir(name, 0o700, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        except OSError as exc:
            raise DeepSeekV4HCPreBuildError(
                f"cannot create private HC_PRE directory: {exc}"
            ) from exc
        try:
            descriptor = os.open(name, flags, dir_fd=parent_descriptor)
        except OSError as exc:
            try:
                os.rmdir(name, dir_fd=parent_descriptor)
            except OSError:
                pass
            raise DeepSeekV4HCPreBuildError(
                f"cannot open private HC_PRE directory: {exc}"
            ) from exc
        stack.callback(os.close, descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise DeepSeekV4HCPreBuildError("private HC_PRE path is not a directory")
        return parent / name, name, descriptor
    raise DeepSeekV4HCPreBuildError(
        "cannot reserve a collision-free private HC_PRE directory"
    )


def _cleanup_private_directory(
    *,
    parent_descriptor: int,
    name: str,
    descriptor: int,
    label: str,
) -> None:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    held = os.fstat(descriptor)
    try:
        current_descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    except OSError as exc:
        raise DeepSeekV4HCPreBuildError(
            f"cannot safely reopen {label} for cleanup: {exc}"
        ) from exc
    current = os.fstat(current_descriptor)
    if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (
        held.st_dev,
        held.st_ino,
    ):
        os.close(current_descriptor)
        raise DeepSeekV4HCPreBuildError(f"refusing to clean a replaced {label}")

    visited_entries = 0

    def remove_contents(directory_descriptor: int, depth: int) -> None:
        nonlocal visited_entries
        if depth > 8:
            raise DeepSeekV4HCPreBuildError(f"{label} cleanup depth exceeds its bound")
        try:
            names = os.listdir(directory_descriptor)
        except OSError as exc:
            raise DeepSeekV4HCPreBuildError(
                f"cannot enumerate {label} for cleanup: {exc}"
            ) from exc
        visited_entries += len(names)
        if visited_entries > 128:
            raise DeepSeekV4HCPreBuildError(
                f"{label} cleanup entry count exceeds its bound"
            )
        for child_name in names:
            if (
                child_name in {"", ".", ".."}
                or "/" in child_name
                or "\x00" in child_name
            ):
                raise DeepSeekV4HCPreBuildError(
                    f"{label} contains an unsafe cleanup entry"
                )
            try:
                metadata = os.stat(
                    child_name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
                if stat.S_ISDIR(metadata.st_mode):
                    child_descriptor = os.open(
                        child_name,
                        flags,
                        dir_fd=directory_descriptor,
                    )
                    try:
                        remove_contents(child_descriptor, depth + 1)
                    finally:
                        os.close(child_descriptor)
                    os.rmdir(child_name, dir_fd=directory_descriptor)
                else:
                    os.unlink(child_name, dir_fd=directory_descriptor)
            except OSError as exc:
                raise DeepSeekV4HCPreBuildError(
                    f"cannot safely remove {label} entry {child_name!r}: {exc}"
                ) from exc

    try:
        remove_contents(current_descriptor, 0)
    finally:
        os.close(current_descriptor)
    try:
        os.rmdir(name, dir_fd=parent_descriptor)
    except OSError as exc:
        raise DeepSeekV4HCPreBuildError(f"cannot safely clean {label}: {exc}") from exc


def _open_relative_descriptor(root_descriptor: int, relative: str, label: str) -> int:
    parts = Path(_safe_relative(relative, label)).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    directory_descriptor = os.dup(root_descriptor)
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(
                part,
                directory_flags,
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        return os.open(parts[-1], file_flags, dir_fd=directory_descriptor)
    except OSError as exc:
        raise DeepSeekV4HCPreBuildError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    finally:
        os.close(directory_descriptor)


def _safe_source(
    stack: ExitStack,
    root_descriptor: int,
    value: Any,
    label: str,
    *,
    exact_size: int | None = None,
    maximum_size: int | None = None,
) -> _StableFile:
    relative = _safe_relative(value, label)
    descriptor = _open_relative_descriptor(root_descriptor, relative, label)
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise DeepSeekV4HCPreBuildError(f"{label} is not a regular file")
    if exact_size is not None and metadata.st_size != exact_size:
        raise DeepSeekV4HCPreBuildError(
            f"{label} has {metadata.st_size} bytes, expected {exact_size}"
        )
    if maximum_size is not None and metadata.st_size > maximum_size:
        raise DeepSeekV4HCPreBuildError(
            f"{label} exceeds its {maximum_size}-byte bound"
        )
    return _StableFile(
        descriptor=descriptor,
        fingerprint=_fingerprint(metadata),
        relative_path=relative,
        root_descriptor=root_descriptor,
        size_bytes=metadata.st_size,
    )


def _verify_stable(source: _StableFile, label: str) -> None:
    if _fingerprint(os.fstat(source.descriptor)) != source.fingerprint:
        raise DeepSeekV4HCPreBuildError(f"{label} changed while it was in use")
    current_descriptor = _open_relative_descriptor(
        source.root_descriptor, source.relative_path, label
    )
    try:
        current = os.fstat(current_descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or _fingerprint(current) != source.fingerprint
        ):
            raise DeepSeekV4HCPreBuildError(f"{label} was replaced while it was in use")
    finally:
        os.close(current_descriptor)


def _verify_root_stable(
    root: Path,
    descriptor: int,
    fingerprint: tuple[int, ...],
    label: str,
) -> None:
    if _fingerprint(os.fstat(descriptor)) != fingerprint:
        raise DeepSeekV4HCPreBuildError(f"{label} changed while it was in use")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreBuildError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        if _fingerprint(os.fstat(current_descriptor)) != fingerprint:
            raise DeepSeekV4HCPreBuildError(f"{label} was replaced while it was in use")
    finally:
        os.close(current_descriptor)


def _descriptor_bytes(source: _StableFile, label: str, *, maximum: int) -> bytes:
    if source.size_bytes > maximum:
        raise DeepSeekV4HCPreBuildError(f"{label} exceeds its {maximum}-byte bound")
    payload = bytearray()
    offset = 0
    while offset < source.size_bytes:
        try:
            chunk = os.pread(
                source.descriptor,
                min(_READ_CHUNK_BYTES, source.size_bytes - offset),
                offset,
            )
        except OSError as exc:
            raise DeepSeekV4HCPreBuildError(f"cannot read {label}: {exc}") from exc
        if not chunk:
            break
        payload.extend(chunk)
        offset += len(chunk)
    if len(payload) != source.size_bytes:
        raise DeepSeekV4HCPreBuildError(f"{label} ended before its declared size")
    _verify_stable(source, label)
    return bytes(payload)


def _strict_json_payload(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4HCPreBuildError(
                    f"{label} has duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                DeepSeekV4HCPreBuildError(
                    f"{label} has non-finite JSON number {token!r}"
                )
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DeepSeekV4HCPreBuildError(f"cannot decode {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise DeepSeekV4HCPreBuildError(f"{label} is not a JSON object")
    if canonical_json_bytes(value) != payload:
        raise DeepSeekV4HCPreBuildError(f"{label} is not canonical JSON")
    return value


def _sha256_file(source: _StableFile, label: str) -> tuple[str, int]:
    digest = hashlib.sha256()
    offset = 0
    while offset < source.size_bytes:
        try:
            chunk = os.pread(
                source.descriptor,
                min(_READ_CHUNK_BYTES, source.size_bytes - offset),
                offset,
            )
        except OSError as exc:
            raise DeepSeekV4HCPreBuildError(f"cannot hash {label}: {exc}") from exc
        if not chunk:
            break
        digest.update(chunk)
        offset += len(chunk)
    if offset != source.size_bytes:
        raise DeepSeekV4HCPreBuildError(f"{label} ended while it was hashed")
    _verify_stable(source, label)
    return digest.hexdigest(), offset


def _copy_locked(
    source: _StableFile,
    destination: Path,
    *,
    expected_sha256: str,
    expected_size: int,
) -> tuple[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    output_descriptor = -1
    try:
        output_descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
        while size < source.size_bytes:
            chunk = os.pread(
                source.descriptor,
                min(_READ_CHUNK_BYTES, source.size_bytes - size),
                size,
            )
            if not chunk:
                break
            digest.update(chunk)
            written = 0
            while written < len(chunk):
                count = os.write(output_descriptor, chunk[written:])
                if count <= 0:
                    raise OSError("short write while copying HC_PRE tensor")
                written += count
            size += len(chunk)
        os.fsync(output_descriptor)
    except OSError as exc:
        raise DeepSeekV4HCPreBuildError(
            f"cannot copy canonical HC_PRE tensor {source.relative_path!r}: {exc}"
        ) from exc
    finally:
        if output_descriptor >= 0:
            os.close(output_descriptor)
    _verify_stable(source, f"canonical HC_PRE tensor {source.relative_path!r}")
    observed = digest.hexdigest()
    if (observed, size) != (expected_sha256, expected_size):
        raise DeepSeekV4HCPreBuildError(
            f"canonical HC_PRE tensor {source.relative_path!r} changed during compilation"
        )
    return observed, size


def _validate_finite_f32(
    source: _StableFile, *, expected_elements: int, label: str
) -> None:
    observed_elements = 0
    offset = 0
    while offset < source.size_bytes:
        try:
            chunk = os.pread(
                source.descriptor,
                min(_READ_CHUNK_BYTES, source.size_bytes - offset),
                offset,
            )
        except OSError as exc:
            raise DeepSeekV4HCPreBuildError(f"cannot validate {label}: {exc}") from exc
        if not chunk:
            break
        if len(chunk) % 4:
            raise DeepSeekV4HCPreBuildError(
                f"{label} payload is not aligned to binary32"
            )
        for (code,) in struct.iter_unpack("<I", chunk):
            if code & 0x7F800000 == 0x7F800000:
                raise DeepSeekV4HCPreBuildError(
                    f"{label} contains nonfinite binary32 code at element "
                    f"{observed_elements}"
                )
            observed_elements += 1
        offset += len(chunk)
    _verify_stable(source, label)
    if observed_elements != expected_elements:
        raise DeepSeekV4HCPreBuildError(
            f"{label} element count differs from its reserved shape"
        )


def _assignments_by_name(
    application: Mapping[str, Any],
) -> dict[str, list[Mapping[str, Any]]]:
    raw = application.get("assignments")
    if not isinstance(raw, list) or any(not isinstance(item, Mapping) for item in raw):
        raise DeepSeekV4HCPreBuildError("canonical assignments are malformed")
    result: dict[str, list[Mapping[str, Any]]] = {}
    seen: set[tuple[int, str]] = set()
    for index, record in enumerate(raw):
        name = record.get("name")
        rank = record.get("rank")
        if (
            not isinstance(name, str)
            or isinstance(rank, bool)
            or not isinstance(rank, int)
            or rank < 0
            or (rank, name) in seen
        ):
            raise DeepSeekV4HCPreBuildError(
                f"canonical assignment {index} has an invalid identity"
            )
        seen.add((rank, name))
        result.setdefault(name, []).append(record)
    for records in result.values():
        records.sort(key=lambda item: item["rank"])
    return result


def _validate_application_selection(application: Mapping[str, Any]) -> None:
    inputs = application.get("inputs")
    if not isinstance(inputs, list) or any(
        not isinstance(item, Mapping) for item in inputs
    ):
        raise DeepSeekV4HCPreBuildError("canonical inputs are malformed")
    input_names = [item.get("name") for item in inputs]
    if set(input_names) != _EXPECTED_NAMES or len(input_names) != len(_EXPECTED_NAMES):
        raise DeepSeekV4HCPreBuildError(
            "HC_PRE application must consume exactly layer-0 attention base, "
            "projection, and scale tensors"
        )
    selection = application.get("selection")
    if not isinstance(selection, Mapping) or (
        selection.get("requested_input_names") != sorted(_EXPECTED_NAMES)
        or selection.get("dependency_input_names") != []
    ):
        raise DeepSeekV4HCPreBuildError(
            "HC_PRE canonical selection does not name exactly its three source tensors"
        )


def _validate_resources(
    application: Mapping[str, Any],
) -> dict[str, list[Mapping[str, Any]]]:
    _validate_application_selection(application)
    by_name = _assignments_by_name(application)
    if set(by_name) != _EXPECTED_NAMES:
        raise DeepSeekV4HCPreBuildError(
            "HC_PRE application contains assignments outside its three learned resources"
        )

    for name, (shape, payload_bytes, _) in _EXPECTED_RESOURCES.items():
        records = by_name[name]
        if [record.get("rank") for record in records] != list(range(MODEL_PARALLEL)):
            raise DeepSeekV4HCPreBuildError(
                f"{name!r} must be replicated on exactly ranks 0..3"
            )
        first = records[0]
        identity_fields = (
            "logical_dtype",
            "payload_bytes",
            "sha256",
            "shape",
            "storage_dtype",
            "transform",
        )
        identity = {field: first.get(field) for field in identity_fields}
        source_identity = first.get("source")
        if (
            identity
            != {
                "logical_dtype": "FP32",
                "payload_bytes": payload_bytes,
                "sha256": first.get("sha256"),
                "shape": shape,
                "storage_dtype": "F32",
                "transform": "identity",
            }
            or not isinstance(first.get("sha256"), str)
            or len(first["sha256"]) != 64
            or not isinstance(source_identity, Mapping)
            or source_identity.get("name") != name
            or source_identity.get("shape") != shape
            or source_identity.get("storage_dtype") != "F32"
            or source_identity.get("slice") is not None
            or source_identity.get("payload_sha256") != first.get("sha256")
            or first.get("scale_source") is not None
        ):
            raise DeepSeekV4HCPreBuildError(
                f"{name!r} rank 0 violates the reserved F32 tensor contract"
            )
        for record in records[1:]:
            if (
                {field: record.get(field) for field in identity_fields} != identity
                or record.get("source") != source_identity
                or record.get("scale_source") is not None
            ):
                raise DeepSeekV4HCPreBuildError(
                    f"{name!r} model-parallel replicas are not byte-identical identities"
                )
    return by_name


def _validate_official_application(application: Mapping[str, Any]) -> None:
    if application.get("evidence_scope") != "official_checkpoint":
        return
    if application.get("plan") != {
        "expected_input_count": OFFICIAL_CANONICAL_INPUT_COUNT,
        "plan_id": OFFICIAL_CANONICAL_PLAN_ID,
        "schema": OFFICIAL_CANONICAL_PLAN_SCHEMA,
    }:
        raise DeepSeekV4HCPreBuildError(
            "official HC_PRE application is not derived from the pinned MP=4 canonical plan"
        )
    if application.get("status") != (
        "partial_official_transform_application_not_release_evidence"
    ):
        raise DeepSeekV4HCPreBuildError(
            "official HC_PRE selection must retain its partial-application boundary"
        )


def _artifact_record(
    stack: ExitStack,
    root_descriptor: int,
    relative: str,
    role: str,
) -> dict[str, Any]:
    source = _safe_source(
        stack,
        root_descriptor,
        relative,
        f"emitted HC_PRE artifact {relative!r}",
        maximum_size=TOTAL_PARAMETER_BYTES,
    )
    digest, size = _sha256_file(source, f"emitted HC_PRE artifact {relative!r}")
    return {
        "path": relative,
        "role": role,
        "sha256": digest,
        "size_bytes": size,
    }


def _copy_stable_file(source: _StableFile, destination: Path, label: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor = -1
    offset = 0
    try:
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
        while offset < source.size_bytes:
            chunk = os.pread(
                source.descriptor,
                min(_READ_CHUNK_BYTES, source.size_bytes - offset),
                offset,
            )
            if not chunk:
                break
            written = 0
            while written < len(chunk):
                count = os.write(descriptor, chunk[written:])
                if count <= 0:
                    raise OSError("short write while snapshotting canonical evidence")
                written += count
            offset += len(chunk)
        os.fsync(descriptor)
    except OSError as exc:
        raise DeepSeekV4HCPreBuildError(f"cannot snapshot {label}: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if offset != source.size_bytes:
        raise DeepSeekV4HCPreBuildError(f"{label} ended during secure snapshot")
    _verify_stable(source, label)


def _replay_private_application(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application: Mapping[str, Any],
    retained: Mapping[str, Any],
    sources: Mapping[tuple[int, str], _StableFile],
    parent: Path,
    parent_descriptor: int,
) -> dict[str, Any]:
    with ExitStack() as replay_stack:
        replay_root, replay_name, replay_descriptor = _create_private_directory(
            replay_stack,
            parent=parent,
            parent_descriptor=parent_descriptor,
            prefix="hc-pre-replay",
        )
        try:
            write_canonical_json(replay_root / MANIFEST_FILENAME, application)
            write_canonical_json(replay_root / VERIFICATION_FILENAME, retained)
            assignments = application.get("assignments")
            if not isinstance(assignments, list):
                raise DeepSeekV4HCPreBuildError("canonical assignments are malformed")
            for assignment in assignments:
                if not isinstance(assignment, Mapping):
                    raise DeepSeekV4HCPreBuildError("canonical assignment is malformed")
                key = (assignment.get("rank"), assignment.get("name"))
                source = sources.get(key)
                if source is None:
                    raise DeepSeekV4HCPreBuildError(
                        f"canonical assignment {key!r} lacks a stable descriptor"
                    )
                relative = _safe_relative(
                    assignment.get("path"), f"canonical assignment {key!r}.path"
                )
                _copy_stable_file(
                    source,
                    replay_root / relative,
                    f"canonical assignment {key!r}",
                )
            try:
                verification = verify_canonical_application(replay_root, snapshot, lock)
            except DeepSeekV4ApplicationCheckError as exc:
                raise DeepSeekV4HCPreBuildError(
                    f"independent canonical application replay failed: {exc}"
                ) from exc
            if canonical_json_bytes(retained) != canonical_json_bytes(verification):
                raise DeepSeekV4HCPreBuildError(
                    "retained canonical verification differs from independent replay"
                )
            return verification
        finally:
            _cleanup_private_directory(
                parent_descriptor=parent_descriptor,
                name=replay_name,
                descriptor=replay_descriptor,
                label="private canonical replay",
            )


def _numeric_profile() -> dict[str, Any]:
    return {
        "arithmetic_order": {
            "branch_reduction": "balanced_(p0_plus_p1)_plus_(p2_plus_p3)",
            "field_affine": "separate_binary32_multiply_then_add",
            "nonlinear": "correctly_rounded_binary32_sigmoid_and_exp",
            "projection": "increasing_k_exact_product_single_rne_product_add",
            "rms_reduction": "balanced_14_level_binary32_rne",
            "sinkhorn": "stable_softmax_column_then_19_row_column_pairs",
        },
        "constants": {
            "hc_epsilon_binary32": HC_EPSILON_BINARY32,
            "norm_epsilon_binary32": NORM_EPSILON_BINARY32,
        },
        "dimensions": {
            "combination_destinations": HC_MULTIPLIER,
            "combination_sources": HC_MULTIPLIER,
            "flattened_width": FLATTENED_WIDTH,
            "hc_multiplier": HC_MULTIPLIER,
            "hidden_size": HIDDEN_SIZE,
            "mix_fields": MIX_FIELD_COUNT,
            "post_fields": HC_MULTIPLIER,
            "pre_fields": HC_MULTIPLIER,
            "sinkhorn_iterations": SINKHORN_ITERATIONS,
        },
        "encodings": {
            "branch_and_residual": "BF16",
            "byte_order": "little",
            "coefficients_and_parameters": "F32",
            "input": "BF16",
        },
        "exception_policy": {
            "command_commit": "atomic_across_all_batch_times_sequence_tokens",
            "finite_branch_saturation": "final_bf16_conversion_only_and_counted",
            "nonfinite_or_boundary_overflow": "poison_without_partial_commit",
            "subnormals": "preserved_no_ftz_or_daz",
        },
        "profile_id": NUMERIC_PROFILE_ID,
        "runtime_axes": {
            "batch": "positive_dynamic",
            "sequence": "positive_dynamic",
            "token_count": "batch_times_sequence",
        },
        "schema": NUMERIC_PROFILE_SCHEMA,
        "source_boundary": {
            "backend_bit_equivalence": "not_claimed",
            "kernel_source_sha256": KERNEL_SOURCE_SHA256,
            "model_source_sha256": MODEL_SOURCE_SHA256,
        },
        "specification": {
            "document": "SPEC-NUM",
            "requirement": "NUM-6.10",
            "version": "1.1",
        },
    }


def _counter_contract() -> dict[str, Any]:
    return {
        "command_scaling": {
            "fixed_counters": "per_token_coefficient_times_batch_times_sequence",
            "poisoned_command": "no_success_counter_commit",
            "saturation_counter": "exact_observed_final_bf16_clamp_count",
        },
        "data_dependent": {
            "hc_pre_branch_bf16_saturations": {
                "maximum_per_token": HIDDEN_SIZE,
                "minimum_per_token": 0,
            }
        },
        "evidence_boundary": (
            "Semantic reconciliation coefficients only; not instruction, traffic, "
            "cycle, throughput, energy, area, or PPA evidence."
        ),
        "numeric_profile_id": NUMERIC_PROFILE_ID,
        "per_successfully_committed_token": {
            "hc_pre_branch_bf16_conversions": 4096,
            "hc_pre_branch_coefficient_multiplies": 16384,
            "hc_pre_branch_reduction_adds": 12288,
            "hc_pre_coefficient_epsilon_adds": 4,
            "hc_pre_exp_evaluations": 16,
            "hc_pre_field_affine_adds": 24,
            "hc_pre_field_affine_multiplies": 24,
            "hc_pre_input_bf16_values": 16384,
            "hc_pre_post_factor_multiplies": 4,
            "hc_pre_projection_product_accumulates": 393216,
            "hc_pre_projection_rms_multiplies": 24,
            "hc_pre_residual_bf16_values_preserved": 16384,
            "hc_pre_rms_divides": 1,
            "hc_pre_rms_epsilon_adds": 1,
            "hc_pre_rms_reduction_adds": 16383,
            "hc_pre_rms_square_multiplies": 16384,
            "hc_pre_rsqrt_evaluations": 1,
            "hc_pre_sigmoid_evaluations": 8,
            "hc_pre_sinkhorn_column_reduction_adds": 240,
            "hc_pre_sinkhorn_column_stages": 20,
            "hc_pre_sinkhorn_divides": 640,
            "hc_pre_sinkhorn_epsilon_adds": 172,
            "hc_pre_sinkhorn_row_reduction_adds": 240,
            "hc_pre_sinkhorn_row_stages": 20,
            "hc_pre_softmax_max_comparisons": 12,
            "hc_pre_softmax_subtracts": 16,
        },
        "schema": COUNTER_CONTRACT_SCHEMA,
        "specification": "SPEC-NUM 1.1 NUM-6.10.6",
    }


def _source_record(
    application: Mapping[str, Any], verification: Mapping[str, Any]
) -> dict[str, Any]:
    source = application["source"]
    return {
        "application_id": application["application_id"],
        "application_status": application["status"],
        "checkpoint_lock_id": source["checkpoint_lock_id"],
        "evidence_scope": application["evidence_scope"],
        "repository": source["repository"],
        "revision": source["revision"],
        "verification_id": verification["verification_id"],
    }


def _build_into(
    *,
    application_root: Path,
    application: Mapping[str, Any],
    verification: Mapping[str, Any],
    root: Path,
    sources: Mapping[tuple[int, str], _StableFile],
) -> dict[str, Any]:
    resources = _validate_resources(application)
    _validate_official_application(application)
    free_bytes = shutil.disk_usage(root.parent).free
    reserve = 1024 * 1024
    if free_bytes < TOTAL_PARAMETER_BYTES + reserve:
        raise DeepSeekV4HCPreBuildError(
            "HC_PRE package lacks bounded free-space reserve"
        )

    tensor_records: dict[str, dict[str, Any]] = {}
    payload_roles: dict[str, str] = {}
    for name, (shape, expected_size, resource) in _EXPECTED_RESOURCES.items():
        assignments = resources[name]
        source = sources.get((0, name))
        if source is None:
            raise DeepSeekV4HCPreBuildError(
                f"{resource} rank-0 source lacks a stable descriptor"
            )
        expected_digest = assignments[0]["sha256"]
        relative = f"payloads/sha256/{expected_digest}.f32le"
        destination = root / relative
        _validate_finite_f32(
            source,
            expected_elements=expected_size // 4,
            label=f"HC_PRE {resource}",
        )
        digest, size = _copy_locked(
            source,
            destination,
            expected_sha256=expected_digest,
            expected_size=expected_size,
        )
        tensor_records[resource] = {
            "content_address": f"sha256:{digest}",
            "dtype": "F32",
            "encoding": "ieee754_binary32_little_endian",
            "layout": "c_contiguous_row_major",
            "memory_map": {
                "length_bytes": size,
                "offset_bytes": 0,
            },
            "name": name,
            "path": relative,
            "replicated_ranks": list(range(MODEL_PARALLEL)),
            "sha256": digest,
            "shape": shape,
            "size_bytes": size,
            "source_assignment_paths": [record["path"] for record in assignments],
        }
        payload_roles[relative] = f"hc_{resource}_parameter"

    tensor_manifest = {
        "base": tensor_records["base"],
        "model_parallel": MODEL_PARALLEL,
        "projection": tensor_records["projection"],
        "scale": tensor_records["scale"],
        "schema": TENSOR_SCHEMA,
        "total_unique_payload_bytes": TOTAL_PARAMETER_BYTES,
    }
    write_canonical_json(root / "tensor_manifest.json", tensor_manifest)

    source = _source_record(application, verification)
    semantic = {
        "architectural_outputs": {
            "branch": {"dtype": "BF16", "shape": "[batch,sequence,4096]"},
            "comb": {"dtype": "F32", "shape": "[batch,sequence,4,4]"},
            "post": {"dtype": "F32", "shape": "[batch,sequence,4]"},
            "residual": {
                "dtype": "BF16",
                "shape": "[batch,sequence,4,4096]",
            },
        },
        "claim_boundary": (
            "Complete learned-parameter and numeric-contract package for one "
            "layer-0 attention HC_PRE site; contains no activation, result, or "
            "execution evidence."
        ),
        "model_id": MODEL_ID,
        "numeric_profile_id": NUMERIC_PROFILE_ID,
        "operation": {
            "base_resource": BASE_NAME,
            "input": "x_bf16[batch,sequence,4,4096]",
            "kind": "HC_PRE",
            "projection_resource": PROJECTION_NAME,
            "scale_resource": SCALE_NAME,
        },
        "schema": SEMANTIC_SCHEMA,
        "site": {"branch": "attention", "layer": 0, "scope": "main"},
        "source": source,
    }
    write_canonical_json(root / "model.ir.json", semantic)
    write_canonical_json(root / "numeric_profile.json", _numeric_profile())
    write_canonical_json(root / "counter_contract.json", _counter_contract())
    coverage = {
        "execution_coverage": "none",
        "model_id": MODEL_ID,
        "numeric_contract_coverage": "SPEC-NUM 1.1 NUM-6.10",
        "packaged_operator_kind": "HC_PRE",
        "parameter_coverage": "all_three_learned_resources_for_one_site",
        "schema": COVERAGE_SCHEMA,
        "site": {"branch": "attention", "layer": 0, "scope": "main"},
        "status": "complete_operator_artifact_contract_not_execution_evidence",
    }
    write_canonical_json(root / "operator_coverage.json", coverage)
    roundtrip = verify_deepseek_v4_hc_pre_roundtrip(root, application_root)
    write_canonical_json(root / "roundtrip_report.json", roundtrip)

    roles = {
        "counter_contract.json": "counter_contract",
        "model.ir.json": "semantic_ir",
        "numeric_profile.json": "numeric_profile",
        "operator_coverage.json": "operator_coverage",
        "roundtrip_report.json": "roundtrip_report",
        "tensor_manifest.json": "tensor_manifest",
        **payload_roles,
    }
    with ExitStack() as artifact_stack:
        root_descriptor, _ = _open_root(
            artifact_stack, root, "HC_PRE temporary deployment root"
        )
        artifacts = [
            _artifact_record(
                artifact_stack,
                root_descriptor,
                relative,
                roles[relative],
            )
            for relative in sorted(roles)
        ]
    identity = {
        "artifacts": artifacts,
        "compiler": {
            "name": "opentallas-deepseek-v4-hc-pre-artifact-compiler",
            "version": COMPILER_VERSION,
        },
        "model_id": MODEL_ID,
        "numeric_profile_id": NUMERIC_PROFILE_ID,
        "site": {"branch": "attention", "layer": 0, "scope": "main"},
        "source": source,
    }
    build_id = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    official = application.get("evidence_scope") == "official_checkpoint"
    deployment = {
        **identity,
        "build_id": build_id,
        "claim_boundary": [
            "Packages all learned parameters and the frozen numeric contract for one complete HC_PRE site.",
            "Contains no input activation or expected result and establishes no execution, transformer, model-completion, or CUDA-equivalence claim.",
            "Semantic counter coefficients are contract metadata only and establish no cycles, throughput, energy, area, or PPA result.",
            "Publication is atomic create-once within a caller-trusted output parent; concurrent mutation by the same filesystem owner is outside the package threat boundary.",
        ],
        "entrypoint": {
            "counter_contract": "counter_contract.json",
            "numeric_profile": "numeric_profile.json",
            "semantic_ir": "model.ir.json",
            "tensor_manifest": "tensor_manifest.json",
        },
        "schema": DEPLOYMENT_SCHEMA,
        "status": (
            "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
            if official
            else "development_fixture_complete_hc_pre_parameters_not_release_evidence"
        ),
    }
    write_canonical_json(root / "deployment_manifest.json", deployment)
    verify_deepseek_v4_hc_pre_deployment(root, application_root)
    return deployment


def _publish_create_once(
    *,
    parent_descriptor: int,
    temporary_name: str,
    output_name: str,
    output: Path,
) -> None:
    """Atomically rename a completed directory without replacing a peer."""

    renameat2 = getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None)
    if renameat2 is not None:
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            parent_descriptor,
            os.fsencode(temporary_name),
            parent_descriptor,
            os.fsencode(output_name),
            1,
        )
        if result == 0:
            return
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise DeepSeekV4HCPreBuildError(f"output already exists: {output}")
        if error not in {errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP}:
            raise DeepSeekV4HCPreBuildError(
                f"cannot publish HC_PRE package atomically: {os.strerror(error)}"
            )

    raise DeepSeekV4HCPreBuildError(
        "platform lacks atomic rename-without-replacement support"
    )


def build_deepseek_v4_hc_pre_deployment(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    output: Path,
) -> dict[str, Any]:
    """Verify and publish one package inside a caller-trusted output parent."""

    validate_checkpoint_lock(lock)
    _require_secure_file_operations()
    application_root = Path(application_root).absolute()
    raw_output = Path(output)
    if not raw_output.name or raw_output.name in {".", ".."}:
        raise DeepSeekV4HCPreBuildError("output must name a specific directory")
    if os.path.lexists(raw_output):
        raise DeepSeekV4HCPreBuildError(f"output already exists: {raw_output}")
    output = raw_output.resolve()
    if output == Path(output.anchor):
        raise DeepSeekV4HCPreBuildError("output must not be a filesystem root")
    output.parent.mkdir(parents=True, exist_ok=True)
    required_free_bytes = TOTAL_PARAMETER_BYTES * (MODEL_PARALLEL + 1) + 2 * 1024 * 1024
    if shutil.disk_usage(output.parent).free < required_free_bytes:
        raise DeepSeekV4HCPreBuildError(
            "HC_PRE verification and package snapshots lack bounded free-space reserve"
        )

    with ExitStack() as source_stack:
        output_parent_descriptor, _ = _open_root(
            source_stack, output.parent, "HC_PRE output parent"
        )
        _verify_root_binding(
            output.parent,
            output_parent_descriptor,
            "HC_PRE output parent",
        )
        application_descriptor, application_fingerprint = _open_root(
            source_stack, application_root, "canonical application root"
        )
        manifest_file = _safe_source(
            source_stack,
            application_descriptor,
            MANIFEST_FILENAME,
            "canonical application manifest",
            maximum_size=_MAX_APPLICATION_JSON_BYTES,
        )
        verification_file = _safe_source(
            source_stack,
            application_descriptor,
            VERIFICATION_FILENAME,
            "canonical application verification",
            maximum_size=_MAX_APPLICATION_JSON_BYTES,
        )
        application = _strict_json_payload(
            _descriptor_bytes(
                manifest_file,
                "canonical application manifest",
                maximum=_MAX_APPLICATION_JSON_BYTES,
            ),
            "canonical application manifest",
        )
        retained = _strict_json_payload(
            _descriptor_bytes(
                verification_file,
                "canonical application verification",
                maximum=_MAX_APPLICATION_JSON_BYTES,
            ),
            "canonical application verification",
        )
        resources = _validate_resources(application)
        _validate_official_application(application)
        stable_sources: dict[tuple[int, str], _StableFile] = {}
        for name, (shape, payload_bytes, resource) in _EXPECTED_RESOURCES.items():
            del shape
            for assignment in resources[name]:
                rank = assignment["rank"]
                stable_sources[(rank, name)] = _safe_source(
                    source_stack,
                    application_descriptor,
                    assignment["path"],
                    f"canonical HC_PRE {resource} rank {rank}",
                    exact_size=payload_bytes,
                )

        verification = _replay_private_application(
            snapshot=snapshot,
            lock=lock,
            application=application,
            retained=retained,
            sources=stable_sources,
            parent=output.parent,
            parent_descriptor=output_parent_descriptor,
        )
        _verify_root_binding(
            output.parent,
            output_parent_descriptor,
            "HC_PRE output parent",
        )
        application_source = application.get("source")
        lock_source = lock["source"]
        expected_application_source = {
            "checkpoint_lock_id": lock["lock_id"],
            "repository": lock_source["repository"],
            "revision": lock_source["revision"],
        }
        if application_source != expected_application_source:
            raise DeepSeekV4HCPreBuildError(
                "canonical HC_PRE application source differs from its checkpoint lock"
            )
        if application.get("evidence_scope") == "official_checkpoint":
            validate_official_checkpoint_lock(lock, load_official_config())
            if (
                application_source["repository"],
                application_source["revision"],
            ) != (REPOSITORY, REVISION):
                raise DeepSeekV4HCPreBuildError(
                    "official HC_PRE application is not the pinned V4 Flash release"
                )

        guarded_files = [manifest_file, verification_file, *stable_sources.values()]
        for guarded in guarded_files:
            _verify_stable(guarded, f"canonical source {guarded.relative_path!r}")
        _verify_root_stable(
            application_root,
            application_descriptor,
            application_fingerprint,
            "canonical application root",
        )

        temporary, temporary_name, temporary_descriptor = _create_private_directory(
            source_stack,
            parent=output.parent,
            parent_descriptor=output_parent_descriptor,
            prefix="hc-pre-package",
        )
        published = False
        try:
            _verify_root_binding(
                output.parent,
                output_parent_descriptor,
                "HC_PRE output parent",
            )
            _verify_root_binding(
                temporary,
                temporary_descriptor,
                "HC_PRE temporary deployment root",
            )
            deployment = _build_into(
                application_root=application_root,
                application=application,
                verification=verification,
                root=temporary,
                sources=stable_sources,
            )
            for guarded in guarded_files:
                _verify_stable(guarded, f"canonical source {guarded.relative_path!r}")
            _verify_root_stable(
                application_root,
                application_descriptor,
                application_fingerprint,
                "canonical application root",
            )
            _verify_root_binding(
                temporary,
                temporary_descriptor,
                "HC_PRE temporary deployment root",
            )
            _verify_root_binding(
                output.parent,
                output_parent_descriptor,
                "HC_PRE output parent",
            )
            _publish_create_once(
                parent_descriptor=output_parent_descriptor,
                temporary_name=temporary_name,
                output_name=output.name,
                output=output,
            )
            published = True
            _verify_root_binding(
                output.parent,
                output_parent_descriptor,
                "HC_PRE output parent",
            )
            _verify_root_binding(
                output,
                temporary_descriptor,
                "published HC_PRE deployment root",
            )
            return deployment
        except Exception:
            if not published:
                _cleanup_private_directory(
                    parent_descriptor=output_parent_descriptor,
                    name=temporary_name,
                    descriptor=temporary_descriptor,
                    label="temporary HC_PRE deployment",
                )
            raise


__all__ = [
    "BASE_NAME",
    "DeepSeekV4HCPreBuildError",
    "NUMERIC_PROFILE_ID",
    "PROJECTION_NAME",
    "SCALE_NAME",
    "build_deepseek_v4_hc_pre_deployment",
]
