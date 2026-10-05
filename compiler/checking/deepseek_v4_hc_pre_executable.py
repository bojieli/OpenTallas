"""Independent verifier for the versioned DeepSeek V4 HC_PRE executable package.

The package joins the already verified three-resource parameter deployment to
the exact ``HC_PRE; COMPLETE`` program, its deterministic disassembly, and an
independently checked logical schedule.  Passing this checker proves package
identity and closure only.  It does not prove that the program was executed.

The verifier intentionally does not import the executable package builder or
private helpers from the parameter compiler.  Files are opened relative to
directory descriptors, read with explicit bounds, checked for replacement,
and required to occupy one closed regular-file tree.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import stat
from typing import Any

from compiler.checking.deepseek_v4_hc_pre_schedule import (
    DeepSeekV4HCPreScheduleCheckError,
    verify_deepseek_v4_hc_pre_logical_schedule,
    verify_deepseek_v4_hc_pre_logical_schedule_certificate,
)
from compiler.checking.deepseek_v4_hc_pre_slice import (
    DeepSeekV4HCPreCheckError,
    verify_deepseek_v4_hc_pre_deployment,
)
from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_hc_pre import (
    DeepSeekV4HCPreMicrocodeError,
    assemble,
    build_program_contract,
    decode,
    disassemble,
    encode,
    verify,
    verify_program_contract,
)


EXECUTABLE_DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_hc_pre_executable.v1"
EXECUTABLE_STATUS = "program_packaged_execution_not_yet_evidenced"
MODEL_ID = "deepseek-v4-flash-0731"
COMPILER_NAME = "opentallas-deepseek-v4-hc-pre-executable-packager"
COMPILER_VERSION = "0.1.0"
DEPLOYMENT_MANIFEST = "deployment_manifest.json"

PROGRAM_BYTES = 136
BASE_BYTES = 96
PROJECTION_BYTES = 1_572_864
SCALE_BYTES = 12

CLAIM_BOUNDARY = [
    (
        "Packages the exact HC_PRE plus COMPLETE program, deterministic "
        "disassembly, hash-bound program contract, independently checked "
        "logical schedule and certificate, and all three verified F32 "
        "parameter resources."
    ),
    "Program packaged, execution not yet evidenced.",
    (
        "Contains no activation, expected result, callback, fallback "
        "arithmetic, runtime execution, or execution-success claim."
    ),
    (
        "The logical schedule establishes instruction order, register "
        "causality, and resource identity only; it establishes no cycles, "
        "latency, bandwidth, throughput, energy, area, density, routing, or "
        "PPA result."
    ),
    (
        "Publication is atomic create-once within a caller-trusted output "
        "parent; concurrent mutation by the same filesystem owner is outside "
        "the package threat boundary."
    ),
]

ENTRYPOINT = {
    "execution_coverage": "execution_coverage.json",
    "execution_request_schema": "interfaces/execution_request_v1.schema.json",
    "execution_result_schema": "interfaces/execution_result_v1.schema.json",
    "logical_schedule": "schedule/logical_schedule.json",
    "logical_schedule_certificate": ("schedule/logical_schedule_certificate.json"),
    "parameter_deployment": "parameters/deployment_manifest.json",
    "program": "program/hc_pre.bin",
    "program_contract": "program/program_contract.json",
    "program_disassembly": "program/hc_pre.disassembly.txt",
}

_V1_ROLE_TO_EXECUTABLE_ROLE = {
    "counter_contract": "parameter_counter_contract",
    "hc_base_parameter": "hc_base_parameter",
    "hc_projection_parameter": "hc_projection_parameter",
    "hc_scale_parameter": "hc_scale_parameter",
    "numeric_profile": "parameter_numeric_profile",
    "operator_coverage": "parameter_operator_coverage",
    "roundtrip_report": "parameter_roundtrip_report",
    "semantic_ir": "parameter_semantic_ir",
    "tensor_manifest": "parameter_tensor_manifest",
}

_FIXED_PATH_BY_ROLE = {
    "execution_coverage": "execution_coverage.json",
    "execution_request_schema": "interfaces/execution_request_v1.schema.json",
    "execution_result_schema": "interfaces/execution_result_v1.schema.json",
    "logical_schedule": "schedule/logical_schedule.json",
    "logical_schedule_certificate": ("schedule/logical_schedule_certificate.json"),
    "microcode_disassembly": "program/hc_pre.disassembly.txt",
    "microcode_program": "program/hc_pre.bin",
    "parameter_counter_contract": "parameters/counter_contract.json",
    "parameter_deployment_manifest": "parameters/deployment_manifest.json",
    "parameter_numeric_profile": "parameters/numeric_profile.json",
    "parameter_operator_coverage": "parameters/operator_coverage.json",
    "parameter_roundtrip_report": "parameters/roundtrip_report.json",
    "parameter_semantic_ir": "parameters/model.ir.json",
    "parameter_tensor_manifest": "parameters/tensor_manifest.json",
    "program_contract": "program/program_contract.json",
}

_EXPECTED_ROLES = frozenset(
    {
        *_FIXED_PATH_BY_ROLE,
        "hc_base_parameter",
        "hc_projection_parameter",
        "hc_scale_parameter",
    }
)

_EXACT_SIZE_BY_ROLE = {
    "execution_coverage": 641,
    "execution_request_schema": 1_586,
    "execution_result_schema": 12_203,
    "hc_base_parameter": BASE_BYTES,
    "hc_projection_parameter": PROJECTION_BYTES,
    "hc_scale_parameter": SCALE_BYTES,
    "logical_schedule": 4_670,
    "logical_schedule_certificate": 1_644,
    "microcode_disassembly": 429,
    "microcode_program": PROGRAM_BYTES,
    "program_contract": 1_363,
}

_EXPECTED_SHA256_BY_ROLE = {
    "execution_coverage": (
        "34c9f1aa49d7a409d945b10f8f4b0abef4f7c83bb482362624b6db0d2fc327a2"
    ),
    "execution_request_schema": (
        "b5b2d9e9b13bcaeae8b51c4b0734d6abda9dcc31d8615192e993794a8a617b4d"
    ),
    "execution_result_schema": (
        "0fd6a153e7c80bbdc1667f850d4f02653eee87aee72be090690c505156099770"
    ),
    "logical_schedule": (
        "40af4255abdc8ee4d2ae40eb54c4a184b7038d5f21fd1f53d58e1324f089eff0"
    ),
    "logical_schedule_certificate": (
        "325a48853587ebcd9f26716a477fcad02e8f0fe167e0b06318711838591d48fb"
    ),
    "microcode_disassembly": (
        "c9c2e567c5b8c71da7c5ac238dfeb0ba83de6cf8f24d925b38e18fb9a38affb0"
    ),
    "microcode_program": (
        "7811e26fae1162677a425795294e776caded0e6cd44383986bb34b9bf9c15739"
    ),
    "program_contract": (
        "63e4594526b09a0b529a3d65bd97e3e9f07ad1140de11c4e9b54f25e020b4b20"
    ),
}

_EXPECTED_DIRECTORIES = {
    "interfaces",
    "parameters",
    "parameters/payloads",
    "parameters/payloads/sha256",
    "program",
    "schedule",
}

_READ_CHUNK_BYTES = 8 * 1024 * 1024
_MAX_JSON_BYTES = 1024 * 1024
_MAX_MANIFEST_BYTES = 256 * 1024
_MAX_TREE_ENTRIES = 64
_MAX_TREE_DEPTH = 8


class DeepSeekV4HCPreExecutableCheckError(RuntimeError):
    """Raised when an HC_PRE executable package fails closed verification."""


@dataclass(frozen=True)
class _StableFile:
    descriptor: int
    fingerprint: tuple[int, ...]
    relative_path: str
    root_descriptor: int
    size_bytes: int


@dataclass(frozen=True)
class _StableDirectory:
    descriptor: int
    fingerprint: tuple[int, ...]
    relative_path: str
    root_descriptor: int


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
        or os.stat not in os.supports_dir_fd
    ):
        raise DeepSeekV4HCPreExecutableCheckError(
            "platform lacks race-resistant bounded checker file operations"
        )


def _safe_relative(value: object, label: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4HCPreExecutableCheckError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4HCPreExecutableCheckError(f"{label} is not canonical POSIX")
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4HCPreExecutableCheckError(f"{label} is not a lowercase SHA-256")
    return value


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise DeepSeekV4HCPreExecutableCheckError(f"{label} must be an object")
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


def _canonical_equal(left: object, right: object) -> bool:
    """Compare strict JSON without Python's bool/integer equality aliases."""

    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except (RecursionError, TypeError, ValueError):
        return False


def _open_root(stack: ExitStack, root: Path, label: str) -> tuple[int, tuple[int, ...]]:
    _require_secure_file_operations()
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4HCPreExecutableCheckError(f"{label} is not a directory")
    return descriptor, _fingerprint(metadata)


def _open_relative_descriptor(
    root_descriptor: int,
    relative: str,
    label: str,
    *,
    directory: bool,
) -> int:
    parts = Path(_safe_relative(relative, label)).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    current_descriptor = os.dup(root_descriptor)
    try:
        for index, part in enumerate(parts):
            final = index == len(parts) - 1
            flags = directory_flags if not final or directory else file_flags
            next_descriptor = os.open(
                part,
                flags,
                dir_fd=current_descriptor,
            )
            os.close(current_descriptor)
            current_descriptor = next_descriptor
        return current_descriptor
    except OSError as exc:
        os.close(current_descriptor)
        raise DeepSeekV4HCPreExecutableCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc


def _safe_file(
    stack: ExitStack,
    root_descriptor: int,
    value: object,
    label: str,
    *,
    exact_size: int | None = None,
    maximum_size: int | None = None,
) -> _StableFile:
    relative = _safe_relative(value, label)
    descriptor = _open_relative_descriptor(
        root_descriptor,
        relative,
        label,
        directory=False,
    )
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise DeepSeekV4HCPreExecutableCheckError(f"{label} is not a regular file")
    if exact_size is not None and metadata.st_size != exact_size:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"{label} has {metadata.st_size} bytes, expected {exact_size}"
        )
    if maximum_size is not None and metadata.st_size > maximum_size:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"{label} exceeds its {maximum_size}-byte bound"
        )
    return _StableFile(
        descriptor=descriptor,
        fingerprint=_fingerprint(metadata),
        relative_path=relative,
        root_descriptor=root_descriptor,
        size_bytes=metadata.st_size,
    )


def _safe_directory(
    stack: ExitStack,
    root_descriptor: int,
    relative: str,
    label: str,
) -> _StableDirectory:
    descriptor = _open_relative_descriptor(
        root_descriptor,
        relative,
        label,
        directory=True,
    )
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4HCPreExecutableCheckError(f"{label} is not a directory")
    return _StableDirectory(
        descriptor=descriptor,
        fingerprint=_fingerprint(metadata),
        relative_path=relative,
        root_descriptor=root_descriptor,
    )


def _verify_stable(source: _StableFile, label: str) -> None:
    if _fingerprint(os.fstat(source.descriptor)) != source.fingerprint:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"{label} changed while the checker read it"
        )
    current_descriptor = _open_relative_descriptor(
        source.root_descriptor,
        source.relative_path,
        label,
        directory=False,
    )
    try:
        current = os.fstat(current_descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or _fingerprint(current) != source.fingerprint
        ):
            raise DeepSeekV4HCPreExecutableCheckError(
                f"{label} was replaced while the checker read it"
            )
    finally:
        os.close(current_descriptor)


def _verify_directory_stable(source: _StableDirectory, label: str) -> None:
    if _fingerprint(os.fstat(source.descriptor)) != source.fingerprint:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"{label} changed during verification"
        )
    current_descriptor = _open_relative_descriptor(
        source.root_descriptor,
        source.relative_path,
        label,
        directory=True,
    )
    try:
        current = os.fstat(current_descriptor)
        if (
            not stat.S_ISDIR(current.st_mode)
            or _fingerprint(current) != source.fingerprint
        ):
            raise DeepSeekV4HCPreExecutableCheckError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current_descriptor)


def _verify_root_stable(
    root: Path,
    descriptor: int,
    fingerprint: tuple[int, ...],
    label: str,
) -> None:
    if _fingerprint(os.fstat(descriptor)) != fingerprint:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"{label} changed during verification"
        )
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        if _fingerprint(os.fstat(current_descriptor)) != fingerprint:
            raise DeepSeekV4HCPreExecutableCheckError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current_descriptor)


def _descriptor_bytes(source: _StableFile, label: str, maximum: int) -> bytes:
    if source.size_bytes > maximum:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"{label} exceeds its {maximum}-byte bound"
        )
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
            raise DeepSeekV4HCPreExecutableCheckError(
                f"cannot read {label}: {exc}"
            ) from exc
        if not chunk:
            break
        payload.extend(chunk)
        offset += len(chunk)
    if len(payload) != source.size_bytes:
        raise DeepSeekV4HCPreExecutableCheckError(f"{label} ended while it was read")
    _verify_stable(source, label)
    return bytes(payload)


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
            raise DeepSeekV4HCPreExecutableCheckError(
                f"cannot hash {label}: {exc}"
            ) from exc
        if not chunk:
            break
        digest.update(chunk)
        offset += len(chunk)
    if offset != source.size_bytes:
        raise DeepSeekV4HCPreExecutableCheckError(f"{label} ended while it was hashed")
    _verify_stable(source, label)
    return digest.hexdigest(), offset


def _strict_json_payload(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4HCPreExecutableCheckError(
                    f"{label} has duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(token: str) -> object:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"{label} has non-finite JSON number {token!r}"
        )

    def bounded_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value):
            raise DeepSeekV4HCPreExecutableCheckError(
                f"{label} has non-finite JSON number {token!r}"
            )
        return value

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
            parse_float=bounded_float,
        )
    except DeepSeekV4HCPreExecutableCheckError:
        raise
    except (
        UnicodeError,
        json.JSONDecodeError,
        OverflowError,
        RecursionError,
        ValueError,
    ) as exc:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"cannot decode {label}: {exc}"
        ) from exc
    if type(value) is not dict:
        raise DeepSeekV4HCPreExecutableCheckError(f"{label} is not a JSON object")
    try:
        canonical = canonical_json_bytes(value)
    except (RecursionError, TypeError, ValueError) as exc:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"cannot canonicalize {label}: {exc}"
        ) from exc
    if canonical != payload:
        raise DeepSeekV4HCPreExecutableCheckError(f"{label} is not canonical JSON")
    return value


def _json_from_file(
    source: _StableFile,
    label: str,
    *,
    maximum: int = _MAX_JSON_BYTES,
) -> dict[str, Any]:
    return _strict_json_payload(
        _descriptor_bytes(source, label, maximum),
        label,
    )


def _enumerate_tree(root_descriptor: int) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    visited_entries = 0

    def walk(directory_descriptor: int, prefix: str, depth: int) -> None:
        nonlocal visited_entries
        if depth > _MAX_TREE_DEPTH:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable directory depth exceeds its bound"
            )
        before = _fingerprint(os.fstat(directory_descriptor))
        try:
            names = sorted(os.listdir(directory_descriptor))
        except OSError as exc:
            raise DeepSeekV4HCPreExecutableCheckError(
                f"cannot enumerate HC_PRE executable package: {exc}"
            ) from exc
        visited_entries += len(names)
        if visited_entries > _MAX_TREE_ENTRIES:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable entry count exceeds its bound"
            )
        for name in names:
            if name in {"", ".", ".."} or "/" in name or "\x00" in name:
                raise DeepSeekV4HCPreExecutableCheckError(
                    "HC_PRE executable contains an unsafe directory entry"
                )
            relative = f"{prefix}/{name}" if prefix else name
            try:
                metadata = os.stat(
                    name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            except OSError as exc:
                raise DeepSeekV4HCPreExecutableCheckError(
                    f"cannot inspect executable entry {relative!r}: {exc}"
                ) from exc
            if stat.S_ISREG(metadata.st_mode):
                files.add(relative)
                continue
            if stat.S_ISDIR(metadata.st_mode):
                directories.add(relative)
                flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
                try:
                    child_descriptor = os.open(
                        name,
                        flags,
                        dir_fd=directory_descriptor,
                    )
                except OSError as exc:
                    raise DeepSeekV4HCPreExecutableCheckError(
                        f"cannot open executable directory {relative!r}: {exc}"
                    ) from exc
                try:
                    walk(child_descriptor, relative, depth + 1)
                finally:
                    os.close(child_descriptor)
                continue
            raise DeepSeekV4HCPreExecutableCheckError(
                f"HC_PRE executable entry {relative!r} is not a regular file "
                "or directory"
            )
        if _fingerprint(os.fstat(directory_descriptor)) != before:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable changed during directory enumeration"
            )

    walk(root_descriptor, "", 0)
    return files, directories


def _is_parameter_payload_path(value: str) -> bool:
    prefix = "parameters/payloads/sha256/"
    suffix = ".f32le"
    if not value.startswith(prefix) or not value.endswith(suffix):
        return False
    digest = value[len(prefix) : -len(suffix)]
    return len(digest) == 64 and all(
        character in "0123456789abcdef" for character in digest
    )


def _artifact_bound(role: str) -> tuple[int | None, int | None]:
    exact = _EXACT_SIZE_BY_ROLE.get(role)
    if exact is not None:
        return exact, None
    return None, _MAX_JSON_BYTES


def _expected_execution_coverage() -> dict[str, Any]:
    return {
        "execution_evidence": "none",
        "model_id": MODEL_ID,
        "parameter_coverage": "all_three_verified_f32_resources",
        "program_execution_authority": "complete",
        "program_scope": ("exact_hc_pre_plus_complete_for_one_layer_0_attention_site"),
        "request_schema": ("opentallas.deepseek_v4_hc_pre_execution_request.v1"),
        "result_schema": "opentallas.deepseek_v4_hc_pre_execution_result.v1",
        "schedule_coverage": (
            "exact_two_slot_logical_schedule_with_independent_certificate"
        ),
        "schema": "opentallas.deepseek_v4_hc_pre_executable_coverage.v1",
        "site": {"branch": "attention", "layer": 0, "scope": "main"},
        "status": "program_authority_complete_execution_evidence_none",
    }


def _verify_frozen_json_document(value: object, role: str) -> None:
    """Compare one parsed document to an independent exact byte identity."""

    expected_size = _EXACT_SIZE_BY_ROLE[role]
    expected_digest = _EXPECTED_SHA256_BY_ROLE[role]
    try:
        payload = canonical_json_bytes(value)
    except (RecursionError, TypeError, ValueError) as exc:
        raise DeepSeekV4HCPreExecutableCheckError(
            f"HC_PRE executable role {role!r} is not canonical JSON: {exc}"
        ) from exc
    if (
        len(payload) != expected_size
        or hashlib.sha256(payload).hexdigest() != expected_digest
    ):
        raise DeepSeekV4HCPreExecutableCheckError(
            f"HC_PRE executable role {role!r} differs from its independently "
            "frozen exact JSON document"
        )


def _artifact_record(
    path: str,
    role: str,
    source: _StableFile,
) -> dict[str, Any]:
    digest, size = _sha256_file(source, f"executable artifact {path!r}")
    return {
        "path": path,
        "role": role,
        "sha256": digest,
        "size_bytes": size,
    }


def _parameter_expected_artifacts(
    parameter_manifest: dict[str, Any],
    parameter_manifest_file: _StableFile,
) -> list[dict[str, Any]]:
    raw_artifacts = parameter_manifest.get("artifacts")
    if type(raw_artifacts) is not list or len(raw_artifacts) != 9:
        raise DeepSeekV4HCPreExecutableCheckError(
            "verified parameter deployment does not expose nine artifacts"
        )
    expected = [
        _artifact_record(
            "parameters/deployment_manifest.json",
            "parameter_deployment_manifest",
            parameter_manifest_file,
        )
    ]
    for index, raw_record in enumerate(raw_artifacts):
        record = _exact_keys(
            raw_record,
            {"path", "role", "sha256", "size_bytes"},
            f"parameter artifacts[{index}]",
        )
        parameter_path = _safe_relative(
            record.get("path"),
            f"parameter artifacts[{index}].path",
        )
        role = record.get("role")
        if type(role) is not str or role not in _V1_ROLE_TO_EXECUTABLE_ROLE:
            raise DeepSeekV4HCPreExecutableCheckError(
                "verified parameter deployment role closure differs"
            )
        size = record.get("size_bytes")
        if type(size) is not int or size < 1 or size > PROJECTION_BYTES:
            raise DeepSeekV4HCPreExecutableCheckError(
                "verified parameter deployment artifact size is invalid"
            )
        expected.append(
            {
                "path": f"parameters/{parameter_path}",
                "role": _V1_ROLE_TO_EXECUTABLE_ROLE[role],
                "sha256": _digest(
                    record.get("sha256"),
                    f"parameter artifacts[{index}].sha256",
                ),
                "size_bytes": size,
            }
        )
    return expected


def verify_deepseek_v4_hc_pre_executable_deployment(
    deployment_root: Path,
    application_root: Path,
) -> dict[str, Any]:
    """Verify the closed executable package without making an execution claim."""

    deployment_root = Path(deployment_root).absolute()
    application_root = Path(application_root).absolute()
    with ExitStack() as stack:
        root_descriptor, root_fingerprint = _open_root(
            stack,
            deployment_root,
            "HC_PRE executable deployment root",
        )
        manifest_file = _safe_file(
            stack,
            root_descriptor,
            DEPLOYMENT_MANIFEST,
            "HC_PRE executable deployment manifest",
            maximum_size=_MAX_MANIFEST_BYTES,
        )
        deployment = _json_from_file(
            manifest_file,
            "HC_PRE executable deployment manifest",
            maximum=_MAX_MANIFEST_BYTES,
        )
        _exact_keys(
            deployment,
            {
                "artifacts",
                "build_id",
                "claim_boundary",
                "compiler",
                "entrypoint",
                "model_id",
                "parameter_build_id",
                "program_contract_id",
                "program_sha256",
                "schedule_certificate_id",
                "schedule_id",
                "schema",
                "site",
                "source",
                "status",
            },
            "HC_PRE executable deployment manifest",
        )

        artifacts = deployment.get("artifacts")
        if type(artifacts) is not list or len(artifacts) != 18:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable must enumerate exactly eighteen artifacts"
            )
        paths: set[str] = set()
        roles: set[str] = set()
        ordered_paths: list[str] = []
        files_by_path: dict[str, _StableFile] = {}
        observed_records: list[dict[str, Any]] = []
        artifact_bytes = 0
        guarded_files = [manifest_file]

        for index, raw_record in enumerate(artifacts):
            record = _exact_keys(
                raw_record,
                {"path", "role", "sha256", "size_bytes"},
                f"executable artifacts[{index}]",
            )
            path = _safe_relative(
                record.get("path"),
                f"executable artifacts[{index}].path",
            )
            role = record.get("role")
            size = record.get("size_bytes")
            if (
                path in paths
                or type(role) is not str
                or role in roles
                or role not in _EXPECTED_ROLES
                or type(size) is not int
                or size < 1
            ):
                raise DeepSeekV4HCPreExecutableCheckError(
                    "HC_PRE executable artifact paths, roles, or sizes are invalid"
                )
            fixed_path = _FIXED_PATH_BY_ROLE.get(role)
            if fixed_path is not None and path != fixed_path:
                raise DeepSeekV4HCPreExecutableCheckError(
                    f"HC_PRE executable role {role!r} has the wrong path"
                )
            if role in {
                "hc_base_parameter",
                "hc_projection_parameter",
                "hc_scale_parameter",
            } and not _is_parameter_payload_path(path):
                raise DeepSeekV4HCPreExecutableCheckError(
                    f"HC_PRE executable role {role!r} has an invalid payload path"
                )
            exact_size, maximum_size = _artifact_bound(role)
            if exact_size is not None and size != exact_size:
                raise DeepSeekV4HCPreExecutableCheckError(
                    f"HC_PRE executable role {role!r} has an invalid size"
                )
            if maximum_size is not None and size > maximum_size:
                raise DeepSeekV4HCPreExecutableCheckError(
                    f"HC_PRE executable role {role!r} exceeds its size bound"
                )

            artifact_file = _safe_file(
                stack,
                root_descriptor,
                path,
                f"executable artifacts[{index}].path",
                exact_size=size,
                maximum_size=maximum_size,
            )
            digest, observed_size = _sha256_file(
                artifact_file,
                f"HC_PRE executable artifact {path!r}",
            )
            if digest != _digest(
                record.get("sha256"),
                f"executable artifacts[{index}].sha256",
            ):
                raise DeepSeekV4HCPreExecutableCheckError(
                    f"HC_PRE executable artifact {path!r} differs from its manifest"
                )
            expected_digest = _EXPECTED_SHA256_BY_ROLE.get(role)
            if expected_digest is not None and digest != expected_digest:
                raise DeepSeekV4HCPreExecutableCheckError(
                    f"HC_PRE executable role {role!r} differs from its frozen "
                    "exact document"
                )
            paths.add(path)
            roles.add(role)
            ordered_paths.append(path)
            files_by_path[path] = artifact_file
            guarded_files.append(artifact_file)
            artifact_bytes += observed_size
            observed_records.append(dict(record))

        if roles != _EXPECTED_ROLES:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable artifact role closure differs"
            )
        if ordered_paths != sorted(ordered_paths):
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable artifact records are not in canonical path order"
            )

        parameter_directory = _safe_directory(
            stack,
            root_descriptor,
            "parameters",
            "HC_PRE parameter deployment directory",
        )
        parameter_manifest_file = files_by_path["parameters/deployment_manifest.json"]
        parameter_manifest = _json_from_file(
            parameter_manifest_file,
            "HC_PRE parameter deployment manifest",
        )
        _verify_directory_stable(
            parameter_directory,
            "HC_PRE parameter deployment directory",
        )
        try:
            parameter_report = verify_deepseek_v4_hc_pre_deployment(
                deployment_root / "parameters",
                application_root,
            )
        except DeepSeekV4HCPreCheckError as exc:
            raise DeepSeekV4HCPreExecutableCheckError(
                f"nested HC_PRE parameter deployment differs: {exc}"
            ) from exc
        _verify_directory_stable(
            parameter_directory,
            "HC_PRE parameter deployment directory",
        )
        parameter_build_id = _digest(
            parameter_manifest.get("build_id"),
            "parameter deployment build_id",
        )
        if parameter_report.get("build_id") != parameter_build_id:
            raise DeepSeekV4HCPreExecutableCheckError(
                "nested HC_PRE parameter checker build identity differs"
            )

        execution_coverage = _json_from_file(
            files_by_path["execution_coverage.json"],
            "HC_PRE executable coverage",
        )
        _verify_frozen_json_document(execution_coverage, "execution_coverage")
        if not _canonical_equal(
            execution_coverage,
            _expected_execution_coverage(),
        ):
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable coverage or evidence boundary differs"
            )
        request_schema = _json_from_file(
            files_by_path["interfaces/execution_request_v1.schema.json"],
            "HC_PRE execution request schema",
        )
        _verify_frozen_json_document(
            request_schema,
            "execution_request_schema",
        )
        result_schema = _json_from_file(
            files_by_path["interfaces/execution_result_v1.schema.json"],
            "HC_PRE execution result schema",
        )
        _verify_frozen_json_document(
            result_schema,
            "execution_result_schema",
        )

        program_file = files_by_path["program/hc_pre.bin"]
        program_payload = _descriptor_bytes(
            program_file,
            "HC_PRE executable program",
            PROGRAM_BYTES,
        )
        try:
            decoded_program = decode(program_payload)
            verify(decoded_program)
            expected_program = encode(assemble())
        except DeepSeekV4HCPreMicrocodeError as exc:
            raise DeepSeekV4HCPreExecutableCheckError(
                f"HC_PRE executable program differs: {exc}"
            ) from exc
        if len(program_payload) != PROGRAM_BYTES or program_payload != expected_program:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable program is not the exact 136-byte fragment"
            )
        program_sha256 = hashlib.sha256(program_payload).hexdigest()

        disassembly_payload = _descriptor_bytes(
            files_by_path["program/hc_pre.disassembly.txt"],
            "HC_PRE deterministic disassembly",
            _EXACT_SIZE_BY_ROLE["microcode_disassembly"],
        )
        expected_disassembly = disassemble(decoded_program).encode("utf-8")
        if disassembly_payload != expected_disassembly:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE deterministic disassembly differs from the program"
            )

        program_contract = _json_from_file(
            files_by_path["program/program_contract.json"],
            "HC_PRE program contract",
        )
        try:
            verify_program_contract(program_contract)
            expected_program_contract = build_program_contract()
        except DeepSeekV4HCPreMicrocodeError as exc:
            raise DeepSeekV4HCPreExecutableCheckError(
                f"HC_PRE program contract differs: {exc}"
            ) from exc
        if not _canonical_equal(program_contract, expected_program_contract):
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE program contract differs from its frozen definition"
            )
        if program_contract.get("program_sha256") != program_sha256:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE program contract does not bind the packaged program"
            )
        program_contract_id = _digest(
            program_contract.get("contract_id"),
            "program contract_id",
        )

        logical_schedule = _json_from_file(
            files_by_path["schedule/logical_schedule.json"],
            "HC_PRE logical schedule",
        )
        logical_certificate = _json_from_file(
            files_by_path["schedule/logical_schedule_certificate.json"],
            "HC_PRE logical schedule certificate",
        )
        try:
            expected_certificate = verify_deepseek_v4_hc_pre_logical_schedule(
                logical_schedule
            )
            verify_deepseek_v4_hc_pre_logical_schedule_certificate(
                logical_certificate,
                logical_schedule,
            )
        except DeepSeekV4HCPreScheduleCheckError as exc:
            raise DeepSeekV4HCPreExecutableCheckError(
                f"HC_PRE logical schedule or certificate differs: {exc}"
            ) from exc
        if not _canonical_equal(logical_certificate, expected_certificate):
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE logical certificate differs from independent verification"
            )
        schedule_id = _digest(
            logical_schedule.get("schedule_id"),
            "logical schedule_id",
        )
        schedule_certificate_id = _digest(
            logical_certificate.get("certificate_id"),
            "logical schedule certificate_id",
        )
        schedule_identity = logical_schedule.get("identity")
        if type(schedule_identity) is not dict or not _canonical_equal(
            {
                "program_contract_id": schedule_identity.get("program_contract_id"),
                "program_sha256": schedule_identity.get("program_sha256"),
            },
            {
                "program_contract_id": program_contract_id,
                "program_sha256": program_sha256,
            },
        ):
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE logical schedule does not bind the packaged program"
            )

        expected_metadata = {
            "claim_boundary": CLAIM_BOUNDARY,
            "compiler": {
                "name": COMPILER_NAME,
                "version": COMPILER_VERSION,
            },
            "entrypoint": ENTRYPOINT,
            "model_id": MODEL_ID,
            "parameter_build_id": parameter_build_id,
            "program_contract_id": program_contract_id,
            "program_sha256": program_sha256,
            "schedule_certificate_id": schedule_certificate_id,
            "schedule_id": schedule_id,
            "schema": EXECUTABLE_DEPLOYMENT_SCHEMA,
            "site": {"branch": "attention", "layer": 0, "scope": "main"},
            "source": parameter_manifest.get("source"),
            "status": EXECUTABLE_STATUS,
        }
        observed_metadata = {key: deployment.get(key) for key in expected_metadata}
        if not _canonical_equal(observed_metadata, expected_metadata):
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable metadata, entrypoints, or claim boundary differs"
            )

        expected_artifacts = _parameter_expected_artifacts(
            parameter_manifest,
            parameter_manifest_file,
        )
        for path, role in (
            ("execution_coverage.json", "execution_coverage"),
            (
                "interfaces/execution_request_v1.schema.json",
                "execution_request_schema",
            ),
            (
                "interfaces/execution_result_v1.schema.json",
                "execution_result_schema",
            ),
            ("program/hc_pre.bin", "microcode_program"),
            ("program/hc_pre.disassembly.txt", "microcode_disassembly"),
            ("program/program_contract.json", "program_contract"),
            ("schedule/logical_schedule.json", "logical_schedule"),
            (
                "schedule/logical_schedule_certificate.json",
                "logical_schedule_certificate",
            ),
        ):
            expected_artifacts.append(_artifact_record(path, role, files_by_path[path]))
        expected_artifacts.sort(key=lambda record: record["path"])
        if not _canonical_equal(observed_records, expected_artifacts):
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable artifact path-to-role or nested hash binding differs"
            )

        build_id = _digest(deployment.get("build_id"), "deployment build_id")
        identity_body = {
            key: deployment[key] for key in deployment if key != "build_id"
        }
        if hashlib.sha256(canonical_json_bytes(identity_body)).hexdigest() != build_id:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable full-body build identity differs"
            )

        actual_files, actual_directories = _enumerate_tree(root_descriptor)
        if actual_files != paths | {DEPLOYMENT_MANIFEST}:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable contains an unlisted or missing file"
            )
        if actual_directories != _EXPECTED_DIRECTORIES:
            raise DeepSeekV4HCPreExecutableCheckError(
                "HC_PRE executable directory closure differs"
            )

        for guarded in guarded_files:
            _verify_stable(
                guarded,
                f"guarded executable file {guarded.relative_path!r}",
            )
        _verify_directory_stable(
            parameter_directory,
            "HC_PRE parameter deployment directory",
        )
        _verify_root_stable(
            deployment_root,
            root_descriptor,
            root_fingerprint,
            "HC_PRE executable deployment root",
        )
        return {
            "application_id": parameter_report["application_id"],
            "artifact_bytes": artifact_bytes,
            "build_id": build_id,
            "checked_artifact_count": len(artifacts),
            "parameter_build_id": parameter_build_id,
            "program_contract_id": program_contract_id,
            "program_sha256": program_sha256,
            "schedule_certificate_id": schedule_certificate_id,
            "schedule_id": schedule_id,
            "status": "package_identity_verified_execution_not_evidenced",
        }


__all__ = [
    "CLAIM_BOUNDARY",
    "COMPILER_NAME",
    "COMPILER_VERSION",
    "DEPLOYMENT_MANIFEST",
    "ENTRYPOINT",
    "EXECUTABLE_DEPLOYMENT_SCHEMA",
    "EXECUTABLE_STATUS",
    "DeepSeekV4HCPreExecutableCheckError",
    "verify_deepseek_v4_hc_pre_executable_deployment",
]
