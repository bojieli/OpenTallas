"""Artifact-only execution service for the exact DeepSeek V4 ``HC_PRE`` site.

This module is deliberately independent of the compiler's execution and
reference lanes.  The executable deployment is treated as hostile input: all
paths are opened relative to held directory descriptors, symlinks and special
files are rejected, reads are bounded, canonical JSON is type-sensitive, and
every guarded fingerprint is rechecked before authority is returned.

The only arithmetic entrypoint is :mod:`runtime.service_engine.hc_pre_numeric`.
The packaged 136-byte ABI program is decoded locally and permits exactly one
``HC_PRE`` instruction followed by ``COMPLETE``.  There is no host-side program
assembly, callback, fallback operator, expected-output path, or physical/PPA
claim.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import ExitStack
import ctypes
from dataclasses import dataclass
import errno
import hashlib
import json
import mmap
import os
from pathlib import Path
import secrets
import stat
import struct
from types import MappingProxyType
from typing import Any, NoReturn, overload
import zlib

from runtime.service_engine import hc_pre_numeric
from runtime.service_engine.deepseek_v4_hc_pre import (
    OFFICIAL_CHECKPOINT_LOCK_ID,
    OFFICIAL_REPOSITORY,
    OFFICIAL_REVISION,
    DeepSeekV4HCPreArtifactDeployment,
    load_deepseek_v4_hc_pre_artifact_deployment,
)


MODEL_ID = "deepseek-v4-flash-0731"
EXECUTABLE_DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_hc_pre_executable.v1"
PROGRAM_CONTRACT_SCHEMA = "opentallas.deepseek_v4_hc_pre_program.v1"
LOGICAL_SCHEDULE_SCHEMA = "opentallas.deepseek_v4_hc_pre_logical_schedule.v1"
LOGICAL_CERTIFICATE_SCHEMA = (
    "opentallas.deepseek_v4_hc_pre_logical_schedule_certificate.v1"
)
EXECUTION_REQUEST_SCHEMA = "opentallas.deepseek_v4_hc_pre_execution_request.v1"
EXECUTION_RESULT_SCHEMA = "opentallas.deepseek_v4_hc_pre_execution_result.v1"
EXECUTION_COVERAGE_SCHEMA = "opentallas.deepseek_v4_hc_pre_executable_coverage.v1"

PROGRAM_SHA256 = "7811e26fae1162677a425795294e776caded0e6cd44383986bb34b9bf9c15739"
PROGRAM_CONTRACT_ID = "08446f291c0080b5fdfeffb8165cf5939e09f43c2d6ac77216b65a01a56b5428"
SCHEDULE_ID = "40015466a3736ad3c94d84029e1ad1d65d4a80ad9ad75511a1d81626e573c4f9"
SCHEDULE_CERTIFICATE_ID = (
    "c4c0e29e7caf015bfc4dba54a7ea4e974b1c935f9c3926163ed4a23147bd1e32"
)
PARAMETER_BUILD_ID = "994815427eff455e780f8abf50a299896366dca0a5713778219ec43266aab3e2"
EXECUTABLE_BUILD_ID = "7c2adb319710357ec2faeb941d74c8fed3cfa815ec8986d29e6c190b30ff00ea"
OFFICIAL_APPLICATION_ID = (
    "195f060eafeefbe414eb30525618a42e765c882c39abdcd8885be644882734a1"
)
OFFICIAL_VERIFICATION_ID = (
    "82c453a978017140b2c15fe2b782a7e04698ce55034376d169bfbb54a85dbbb4"
)

BASE_BYTES = 96
PROJECTION_BYTES = 1_572_864
SCALE_BYTES = 12
PROGRAM_BYTES = 136
MAX_TOKEN_COUNT = 4
MIN_TOKEN_COUNT = 1

_DEPLOYMENT_STATUS = "program_packaged_execution_not_yet_evidenced"
_OFFICIAL_APPLICATION_STATUS = (
    "partial_official_transform_application_not_release_evidence"
)
_SITE = {"branch": "attention", "layer": 0, "scope": "main"}
_COMPILER = {
    "name": "opentallas-deepseek-v4-hc-pre-executable-packager",
    "version": "0.1.0",
}
_CLAIM_BOUNDARY = [
    "Packages the exact HC_PRE plus COMPLETE program, deterministic disassembly, hash-bound program contract, independently checked logical schedule and certificate, and all three verified F32 parameter resources.",
    "Program packaged, execution not yet evidenced.",
    "Contains no activation, expected result, callback, fallback arithmetic, runtime execution, or execution-success claim.",
    "The logical schedule establishes instruction order, register causality, and resource identity only; it establishes no cycles, latency, bandwidth, throughput, energy, area, density, routing, or PPA result.",
    "Publication is atomic create-once within a caller-trusted output parent; concurrent mutation by the same filesystem owner is outside the package threat boundary.",
]
_ENTRYPOINT = {
    "execution_coverage": "execution_coverage.json",
    "execution_request_schema": "interfaces/execution_request_v1.schema.json",
    "execution_result_schema": "interfaces/execution_result_v1.schema.json",
    "logical_schedule": "schedule/logical_schedule.json",
    "logical_schedule_certificate": "schedule/logical_schedule_certificate.json",
    "parameter_deployment": "parameters/deployment_manifest.json",
    "program": "program/hc_pre.bin",
    "program_contract": "program/program_contract.json",
    "program_disassembly": "program/hc_pre.disassembly.txt",
}

_FIXED_PATH_BY_ROLE = {
    "execution_coverage": "execution_coverage.json",
    "execution_request_schema": "interfaces/execution_request_v1.schema.json",
    "execution_result_schema": "interfaces/execution_result_v1.schema.json",
    "logical_schedule": "schedule/logical_schedule.json",
    "logical_schedule_certificate": "schedule/logical_schedule_certificate.json",
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
_PARAMETER_ROLE_MAP = {
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
_EXPECTED_ROLES = frozenset(_FIXED_PATH_BY_ROLE) | {
    "hc_base_parameter",
    "hc_projection_parameter",
    "hc_scale_parameter",
}
_EXPECTED_DIRECTORIES = {
    "interfaces",
    "parameters",
    "parameters/payloads",
    "parameters/payloads/sha256",
    "program",
    "schedule",
}
_EXACT_SIZE_BY_ROLE = {
    "hc_base_parameter": BASE_BYTES,
    "hc_projection_parameter": PROJECTION_BYTES,
    "hc_scale_parameter": SCALE_BYTES,
    "logical_schedule": 4_670,
    "logical_schedule_certificate": 1_644,
    "microcode_disassembly": 429,
    "microcode_program": PROGRAM_BYTES,
    "program_contract": 1_363,
}
_PINNED_SHA256_BY_ROLE = {
    "execution_coverage": "34c9f1aa49d7a409d945b10f8f4b0abef4f7c83bb482362624b6db0d2fc327a2",
    "execution_request_schema": "b5b2d9e9b13bcaeae8b51c4b0734d6abda9dcc31d8615192e993794a8a617b4d",
    "execution_result_schema": "0fd6a153e7c80bbdc1667f850d4f02653eee87aee72be090690c505156099770",
    "logical_schedule": "40af4255abdc8ee4d2ae40eb54c4a184b7038d5f21fd1f53d58e1324f089eff0",
    "logical_schedule_certificate": "325a48853587ebcd9f26716a477fcad02e8f0fe167e0b06318711838591d48fb",
    "microcode_disassembly": "c9c2e567c5b8c71da7c5ac238dfeb0ba83de6cf8f24d925b38e18fb9a38affb0",
    "microcode_program": PROGRAM_SHA256,
    "program_contract": "63e4594526b09a0b529a3d65bd97e3e9f07ad1140de11c4e9b54f25e020b4b20",
}

_EXACT_SIZE_BY_ROLE.update(
    {
        "execution_coverage": 641,
        "execution_request_schema": 1_586,
        "execution_result_schema": 12_203,
    }
)

_MAX_JSON_BYTES = 1024 * 1024
_MAX_MANIFEST_BYTES = 256 * 1024
_MAX_REQUEST_JSON_BYTES = 1024 * 1024
_MAX_RESULT_JSON_BYTES = 128 * 1024
_MAX_INPUT_BYTES = MAX_TOKEN_COUNT * 4 * 4096 * 2
_READ_CHUNK_BYTES = 1024 * 1024
_MAX_TREE_DEPTH = 8
_MAX_TREE_ENTRIES = 96

_PROGRAM_HEADER = struct.Struct("<4sBBHII")
_PROGRAM_RECORD = struct.Struct("<BBH14I")
_PROGRAM_MAGIC = b"OTEQ"
_PROGRAM_ABI = (1, 0)
_NO_OPERAND = 0xFFFFFFFF
_OPCODE_HC_PRE = 0x13
_OPCODE_COMPLETE = 0xFF
_REGISTER_HC_HIDDEN = 2
_REGISTER_ATTENTION_INPUT = 3
_REGISTER_ATTENTION_PRE = 4
_REGISTER_ATTENTION_POST = 5
_REGISTER_ATTENTION_COMBINATION = 6
_REGISTER_ATTENTION_RESIDUAL = 7
_RESOURCE_HC_BASE = 4
_RESOURCE_HC_PROJECTION = 5
_RESOURCE_HC_SCALE = 6

_EXPECTED_HC_PRE_OPERANDS = (
    _REGISTER_ATTENTION_INPUT,
    _REGISTER_ATTENTION_PRE,
    _REGISTER_ATTENTION_POST,
    _REGISTER_ATTENTION_COMBINATION,
    _REGISTER_ATTENTION_RESIDUAL,
    _REGISTER_HC_HIDDEN,
    _RESOURCE_HC_BASE,
    _RESOURCE_HC_PROJECTION,
    _RESOURCE_HC_SCALE,
    _NO_OPERAND,
    4,
    20,
    hc_pre_numeric.HC_PRE_NORM_EPSILON_BINARY32,
    hc_pre_numeric.HC_PRE_SINKHORN_EPSILON_BINARY32,
)
_EXPECTED_COMPLETE_OPERANDS = (_NO_OPERAND,) * 10 + (0,) * 4

_RESULT_DEPLOYMENT_STATUS = (
    "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
)
_RESULT_EVIDENCE_SCOPE = "official_checkpoint"
_RESULT_EXECUTION_SCOPE = "exact_hc_pre_site_only"
_RESULT_SOURCE_APPLICATION_STATUS = _OFFICIAL_APPLICATION_STATUS
_RESULT_STATUS = "pass"

_COUNTER_NAMES = frozenset(
    {
        "hc_pre_branch_bf16_conversions",
        "hc_pre_branch_bf16_saturations",
        "hc_pre_branch_coefficient_multiplies",
        "hc_pre_branch_reduction_adds",
        "hc_pre_coefficient_epsilon_adds",
        "hc_pre_exp_evaluations",
        "hc_pre_field_affine_adds",
        "hc_pre_field_affine_multiplies",
        "hc_pre_input_bf16_values",
        "hc_pre_post_factor_multiplies",
        "hc_pre_projection_product_accumulates",
        "hc_pre_projection_rms_multiplies",
        "hc_pre_residual_bf16_values_preserved",
        "hc_pre_rms_divides",
        "hc_pre_rms_epsilon_adds",
        "hc_pre_rms_reduction_adds",
        "hc_pre_rms_square_multiplies",
        "hc_pre_rsqrt_evaluations",
        "hc_pre_sigmoid_evaluations",
        "hc_pre_sinkhorn_column_reduction_adds",
        "hc_pre_sinkhorn_column_stages",
        "hc_pre_sinkhorn_divides",
        "hc_pre_sinkhorn_epsilon_adds",
        "hc_pre_sinkhorn_row_reduction_adds",
        "hc_pre_sinkhorn_row_stages",
        "hc_pre_softmax_max_comparisons",
        "hc_pre_softmax_subtracts",
    }
)


class DeepSeekV4HCPreExecutableServiceError(RuntimeError):
    """Raised when package authority or one execution must be poisoned."""


@dataclass(frozen=True)
class HCPreExecutableArtifactRecord:
    """One immutable artifact identity from the outer deployment table."""

    relative_path: str
    role: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class _StableFile:
    descriptor: int
    fingerprint: tuple[int, ...]
    relative_path: str
    root_descriptor: int
    size_bytes: int


@dataclass(frozen=True)
class _DecodedInstruction:
    opcode: int
    operands: tuple[int, ...]


def _canonical_json_bytes(value: object) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"value is not canonical JSON: {exc}"
        ) from exc
    return (encoded + "\n").encode("ascii")


def _json_equal(left: object, right: object) -> bool:
    """Compare JSON values without Python's bool/integer equality aliases."""

    try:
        return _canonical_json_bytes(left) == _canonical_json_bytes(right)
    except DeepSeekV4HCPreExecutableServiceError:
        return False


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4HCPreExecutableServiceError(
                    f"{label} has duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                DeepSeekV4HCPreExecutableServiceError(
                    f"{label} contains non-finite JSON number {token!r}"
                )
            ),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, DeepSeekV4HCPreExecutableServiceError):
            raise
        raise DeepSeekV4HCPreExecutableServiceError(
            f"cannot decode {label}: {exc}"
        ) from exc
    if type(value) is not dict:
        raise DeepSeekV4HCPreExecutableServiceError(f"{label} is not a JSON object")
    if _canonical_json_bytes(value) != payload:
        raise DeepSeekV4HCPreExecutableServiceError(f"{label} is not canonical JSON")
    return value


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise DeepSeekV4HCPreExecutableServiceError(f"{label} is not an object")
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4HCPreExecutableServiceError(
            f"{label} is not a lowercase SHA-256"
        )
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if (
        type(value) is not int
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        raise DeepSeekV4HCPreExecutableServiceError(
            f"{label} is outside its integer bound"
        )
    return value


def _safe_relative(value: object, label: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4HCPreExecutableServiceError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4HCPreExecutableServiceError(f"{label} is not canonical POSIX")
    return value


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
        raise DeepSeekV4HCPreExecutableServiceError(
            "platform lacks descriptor-relative no-follow bounded operations"
        )


def _open_root(
    stack: ExitStack,
    root: Path,
    label: str,
) -> tuple[int, tuple[int, ...]]:
    _require_secure_file_operations()
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4HCPreExecutableServiceError(f"{label} is not a directory")
    return descriptor, _fingerprint(metadata)


def _open_relative_descriptor(
    root_descriptor: int,
    relative: str,
    label: str,
    *,
    directory: bool = False,
) -> int:
    parts = Path(_safe_relative(relative, label)).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    current = os.dup(root_descriptor)
    try:
        for index, part in enumerate(parts):
            final = index == len(parts) - 1
            flags = directory_flags if not final or directory else file_flags
            next_descriptor = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = next_descriptor
        return current
    except OSError as exc:
        os.close(current)
        raise DeepSeekV4HCPreExecutableServiceError(
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
    descriptor = _open_relative_descriptor(root_descriptor, relative, label)
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise DeepSeekV4HCPreExecutableServiceError(f"{label} is not a regular file")
    if exact_size is not None and metadata.st_size != exact_size:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"{label} has {metadata.st_size} bytes, expected {exact_size}"
        )
    if maximum_size is not None and metadata.st_size > maximum_size:
        raise DeepSeekV4HCPreExecutableServiceError(
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
        raise DeepSeekV4HCPreExecutableServiceError(
            f"{label} changed while it was read"
        )
    current_descriptor = _open_relative_descriptor(
        source.root_descriptor,
        source.relative_path,
        label,
    )
    try:
        current = os.fstat(current_descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or _fingerprint(current) != source.fingerprint
        ):
            raise DeepSeekV4HCPreExecutableServiceError(
                f"{label} was replaced while it was read"
            )
    finally:
        os.close(current_descriptor)


def _read_bytes(source: _StableFile, label: str, maximum: int) -> bytes:
    if source.size_bytes > maximum:
        raise DeepSeekV4HCPreExecutableServiceError(f"{label} exceeds its bounded size")
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
            raise DeepSeekV4HCPreExecutableServiceError(
                f"cannot read {label}: {exc}"
            ) from exc
        if not chunk:
            break
        payload.extend(chunk)
        offset += len(chunk)
    if len(payload) != source.size_bytes:
        raise DeepSeekV4HCPreExecutableServiceError(f"{label} ended while read")
    _verify_stable(source, label)
    return bytes(payload)


def _verify_root_stable(
    root: Path,
    descriptor: int,
    fingerprint: tuple[int, ...],
    label: str,
) -> None:
    if _fingerprint(os.fstat(descriptor)) != fingerprint:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"{label} changed during verification"
        )
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        if _fingerprint(os.fstat(current)) != fingerprint:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"{label} was replaced during verification"
            )
    finally:
        os.close(current)


def _enumerate_tree(root_descriptor: int) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    visited_entries = 0

    def walk(directory_descriptor: int, prefix: str, depth: int) -> None:
        nonlocal visited_entries
        if depth > _MAX_TREE_DEPTH:
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE executable directory depth exceeds its bound"
            )
        before = _fingerprint(os.fstat(directory_descriptor))
        try:
            names = sorted(os.listdir(directory_descriptor))
        except OSError as exc:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"cannot enumerate executable directory {prefix or '.'!r}: {exc}"
            ) from exc
        visited_entries += len(names)
        if visited_entries > _MAX_TREE_ENTRIES:
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE executable entry count exceeds its bound"
            )
        for name in names:
            if name in {"", ".", ".."} or "/" in name or "\x00" in name:
                raise DeepSeekV4HCPreExecutableServiceError(
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
                raise DeepSeekV4HCPreExecutableServiceError(
                    f"cannot inspect executable entry {relative!r}: {exc}"
                ) from exc
            if stat.S_ISREG(metadata.st_mode):
                files.add(relative)
                continue
            if stat.S_ISDIR(metadata.st_mode):
                directories.add(relative)
                flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
                try:
                    child = os.open(name, flags, dir_fd=directory_descriptor)
                except OSError as exc:
                    raise DeepSeekV4HCPreExecutableServiceError(
                        f"cannot open executable directory {relative!r}: {exc}"
                    ) from exc
                try:
                    walk(child, relative, depth + 1)
                finally:
                    os.close(child)
                continue
            raise DeepSeekV4HCPreExecutableServiceError(
                f"executable entry {relative!r} is not a regular file or directory"
            )
        if _fingerprint(os.fstat(directory_descriptor)) != before:
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE executable changed during directory enumeration"
            )

    walk(root_descriptor, "", 0)
    return files, directories


def _verify_directory_binding(root: Path, descriptor: int, label: str) -> None:
    held = os.fstat(descriptor)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        current = os.fstat(current_descriptor)
        if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
            raise DeepSeekV4HCPreExecutableServiceError(
                f"{label} was replaced during result publication"
            )
    finally:
        os.close(current_descriptor)


def _create_private_directory(
    stack: ExitStack,
    *,
    parent: Path,
    parent_descriptor: int,
) -> tuple[Path, str, int]:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    for _ in range(128):
        name = f".hc-pre-result.tmp-{secrets.token_hex(16)}"
        try:
            os.mkdir(name, 0o700, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        except OSError as exc:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"cannot create private HC_PRE result directory: {exc}"
            ) from exc
        try:
            descriptor = os.open(name, flags, dir_fd=parent_descriptor)
        except OSError as exc:
            try:
                os.rmdir(name, dir_fd=parent_descriptor)
            except OSError:
                pass
            raise DeepSeekV4HCPreExecutableServiceError(
                f"cannot open private HC_PRE result directory: {exc}"
            ) from exc
        stack.callback(os.close, descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise DeepSeekV4HCPreExecutableServiceError(
                "private HC_PRE result path is not a directory"
            )
        return parent / name, name, descriptor
    raise DeepSeekV4HCPreExecutableServiceError(
        "cannot reserve a collision-free private HC_PRE result directory"
    )


def _cleanup_private_directory(
    *,
    parent_descriptor: int,
    name: str,
    descriptor: int,
) -> None:
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    held = os.fstat(descriptor)
    try:
        current_descriptor = os.open(name, directory_flags, dir_fd=parent_descriptor)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"cannot safely reopen private HC_PRE result for cleanup: {exc}"
        ) from exc
    current = os.fstat(current_descriptor)
    if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (
        held.st_dev,
        held.st_ino,
    ):
        os.close(current_descriptor)
        raise DeepSeekV4HCPreExecutableServiceError(
            "refusing to clean a replaced private HC_PRE result"
        )
    visited_entries = 0

    def remove_contents(directory_descriptor: int, depth: int) -> None:
        nonlocal visited_entries
        if depth > _MAX_TREE_DEPTH:
            raise DeepSeekV4HCPreExecutableServiceError(
                "private HC_PRE result cleanup exceeds its depth bound"
            )
        try:
            names = os.listdir(directory_descriptor)
        except OSError as exc:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"cannot enumerate private HC_PRE result for cleanup: {exc}"
            ) from exc
        visited_entries += len(names)
        if visited_entries > 32:
            raise DeepSeekV4HCPreExecutableServiceError(
                "private HC_PRE result cleanup exceeds its entry bound"
            )
        for child_name in names:
            if (
                child_name in {"", ".", ".."}
                or "/" in child_name
                or "\x00" in child_name
            ):
                raise DeepSeekV4HCPreExecutableServiceError(
                    "private HC_PRE result contains an unsafe cleanup entry"
                )
            metadata = os.stat(
                child_name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            if stat.S_ISDIR(metadata.st_mode):
                child_descriptor = os.open(
                    child_name,
                    directory_flags,
                    dir_fd=directory_descriptor,
                )
                try:
                    remove_contents(child_descriptor, depth + 1)
                finally:
                    os.close(child_descriptor)
                os.rmdir(child_name, dir_fd=directory_descriptor)
            else:
                os.unlink(child_name, dir_fd=directory_descriptor)

    try:
        remove_contents(current_descriptor, 0)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"cannot clean private HC_PRE result: {exc}"
        ) from exc
    finally:
        os.close(current_descriptor)
    try:
        os.rmdir(name, dir_fd=parent_descriptor)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"cannot remove private HC_PRE result directory: {exc}"
        ) from exc


def _write_exclusive_bytes(
    root_descriptor: int,
    relative: str,
    payload: bytes,
) -> None:
    if type(payload) is not bytes:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"result artifact {relative!r} is not exact bytes"
        )
    parts = Path(_safe_relative(relative, "result artifact path")).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    current = os.dup(root_descriptor)
    descriptor: int | None = None
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = next_descriptor
        descriptor = os.open(
            parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
            dir_fd=current,
        )
        offset = 0
        while offset < len(payload):
            count = os.write(descriptor, payload[offset:])
            if count <= 0:
                raise DeepSeekV4HCPreExecutableServiceError(
                    f"result artifact {relative!r} ended while written"
                )
            offset += count
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(payload):
            raise DeepSeekV4HCPreExecutableServiceError(
                f"result artifact {relative!r} is not a complete regular file"
            )
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"cannot write result artifact {relative!r}: {exc}"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(current)


def _publish_create_once(
    *,
    parent_descriptor: int,
    temporary_name: str,
    output_name: str,
    output: Path,
) -> None:
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
            raise DeepSeekV4HCPreExecutableServiceError(
                f"result output already exists: {output}"
            )
        if error not in {errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP}:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"cannot atomically publish HC_PRE result: {os.strerror(error)}"
            )
    raise DeepSeekV4HCPreExecutableServiceError(
        "platform lacks atomic rename-without-replacement result publication"
    )


def _open_optional_child_directory(
    parent_descriptor: int,
    name: str,
    label: str,
) -> int | None:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        return os.open(name, flags, dir_fd=parent_descriptor)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise DeepSeekV4HCPreExecutableServiceError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc


def _require_child_directory_identity(
    *,
    parent_descriptor: int,
    name: str,
    held_descriptor: int,
    label: str,
) -> None:
    current_descriptor = _open_optional_child_directory(
        parent_descriptor,
        name,
        label,
    )
    if current_descriptor is None:
        raise DeepSeekV4HCPreExecutableServiceError(f"{label} is absent")
    try:
        current = os.fstat(current_descriptor)
        held = os.fstat(held_descriptor)
        if (
            not stat.S_ISDIR(current.st_mode)
            or not stat.S_ISDIR(held.st_mode)
            or (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino)
        ):
            raise DeepSeekV4HCPreExecutableServiceError(
                f"{label} does not name the verified result directory"
            )
    finally:
        os.close(current_descriptor)


def _restore_staging_after_failed_publication(
    *,
    parent_descriptor: int,
    temporary_name: str,
    output_name: str,
    temporary_descriptor: int,
    output: Path,
) -> None:
    """Restore our inode to its private name without touching a competitor."""

    temporary_current = _open_optional_child_directory(
        parent_descriptor,
        temporary_name,
        "private HC_PRE result rollback path",
    )
    if temporary_current is not None:
        try:
            current = os.fstat(temporary_current)
            held = os.fstat(temporary_descriptor)
            if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
                raise DeepSeekV4HCPreExecutableServiceError(
                    "private HC_PRE result rollback path was replaced"
                )
            return
        finally:
            os.close(temporary_current)

    _require_child_directory_identity(
        parent_descriptor=parent_descriptor,
        name=output_name,
        held_descriptor=temporary_descriptor,
        label="published HC_PRE result rollback path",
    )
    _publish_create_once(
        parent_descriptor=parent_descriptor,
        temporary_name=output_name,
        output_name=temporary_name,
        output=output,
    )
    _require_child_directory_identity(
        parent_descriptor=parent_descriptor,
        name=temporary_name,
        held_descriptor=temporary_descriptor,
        label="restored private HC_PRE result rollback path",
    )


def _decode_exact_program(payload: bytes) -> tuple[_DecodedInstruction, ...]:
    """Decode and require the sole legal ``HC_PRE; COMPLETE`` wire program."""

    if type(payload) is not bytes or len(payload) != PROGRAM_BYTES:
        raise DeepSeekV4HCPreExecutableServiceError(
            "packaged HC_PRE program must be exact 136-byte ABI bytes"
        )
    if hashlib.sha256(payload).hexdigest() != PROGRAM_SHA256:
        raise DeepSeekV4HCPreExecutableServiceError(
            "packaged HC_PRE program SHA-256 differs"
        )
    magic, major, minor, record_bytes, count, expected_crc = (
        _PROGRAM_HEADER.unpack_from(payload)
    )
    if (
        magic != _PROGRAM_MAGIC
        or (major, minor) != _PROGRAM_ABI
        or record_bytes != _PROGRAM_RECORD.size
        or count != 2
    ):
        raise DeepSeekV4HCPreExecutableServiceError(
            "packaged HC_PRE program ABI header differs"
        )
    body = payload[_PROGRAM_HEADER.size :]
    if len(body) != count * _PROGRAM_RECORD.size:
        raise DeepSeekV4HCPreExecutableServiceError(
            "packaged HC_PRE program body length differs"
        )
    if zlib.crc32(body) & 0xFFFFFFFF != expected_crc:
        raise DeepSeekV4HCPreExecutableServiceError(
            "packaged HC_PRE program CRC32 differs"
        )
    decoded: list[_DecodedInstruction] = []
    for index in range(count):
        raw = _PROGRAM_RECORD.unpack_from(body, index * _PROGRAM_RECORD.size)
        opcode, flags, reserved = raw[:3]
        if flags != 0 or reserved != 0:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"packaged instruction {index} has unsupported control bits"
            )
        decoded.append(_DecodedInstruction(opcode, tuple(raw[3:])))
    expected = (
        _DecodedInstruction(_OPCODE_HC_PRE, _EXPECTED_HC_PRE_OPERANDS),
        _DecodedInstruction(_OPCODE_COMPLETE, _EXPECTED_COMPLETE_OPERANDS),
    )
    if tuple(decoded) != expected:
        raise DeepSeekV4HCPreExecutableServiceError(
            "packaged program is not exact HC_PRE followed by COMPLETE"
        )
    return expected


class _MappedF32Payload:
    """Read-only stable-descriptor-backed little-endian binary32 payload."""

    __slots__ = (
        "_descriptor",
        "_fingerprint",
        "_mapping",
        "_sha256",
        "_size_bytes",
        "label",
    )

    def __init__(self, source: _StableFile, sha256: str, label: str):
        self.label = label
        self._descriptor = os.dup(source.descriptor)
        self._fingerprint = _fingerprint(os.fstat(self._descriptor))
        self._size_bytes = source.size_bytes
        self._sha256 = sha256
        try:
            self._mapping = mmap.mmap(
                self._descriptor,
                self._size_bytes,
                access=mmap.ACCESS_READ,
            )
            self.verify()
            for index, (code,) in enumerate(struct.iter_unpack("<I", self._mapping)):
                if code & 0x7F800000 == 0x7F800000:
                    raise DeepSeekV4HCPreExecutableServiceError(
                        f"{label} contains nonfinite binary32 at element {index}"
                    )
        except Exception:
            mapping = getattr(self, "_mapping", None)
            if mapping is not None:
                mapping.close()
            os.close(self._descriptor)
            self._descriptor = -1
            raise

    @property
    def element_count(self) -> int:
        return self._size_bytes // 4

    def code(self, index: int) -> int:
        if not 0 <= index < self.element_count:
            raise IndexError(index)
        try:
            return struct.unpack_from("<I", self._mapping, index * 4)[0]
        except (ValueError, BufferError) as exc:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"{self.label} mapping is unavailable"
            ) from exc

    def verify(self) -> None:
        if self._descriptor < 0:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"{self.label} mapping is closed"
            )
        if _fingerprint(os.fstat(self._descriptor)) != self._fingerprint:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"{self.label} changed after deployment verification"
            )
        digest = hashlib.sha256(self._mapping).hexdigest()
        if digest != self._sha256:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"{self.label} bytes changed after deployment verification"
            )

    def close(self) -> None:
        if self._descriptor < 0:
            return
        self._mapping.close()
        os.close(self._descriptor)
        self._descriptor = -1

    def __del__(self) -> None:  # pragma: no cover - best-effort process cleanup
        try:
            self.close()
        except (BufferError, OSError):
            pass


class _F32Vector(Sequence[int]):
    """Immutable sequence view over a stable mapped binary32 payload."""

    __slots__ = ("_length", "_payload", "_start")

    def __init__(self, payload: _MappedF32Payload, start: int, length: int):
        if start < 0 or length < 0 or start + length > payload.element_count:
            raise DeepSeekV4HCPreExecutableServiceError(
                "mapped F32 vector lies outside its payload"
            )
        self._payload = payload
        self._start = start
        self._length = length

    def __len__(self) -> int:
        return self._length

    @overload
    def __getitem__(self, index: int) -> int: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[int, ...]: ...

    def __getitem__(self, index: int | slice) -> int | tuple[int, ...]:
        if isinstance(index, slice):
            start, stop, step = index.indices(self._length)
            return tuple(self[position] for position in range(start, stop, step))
        if index < 0:
            index += self._length
        if not 0 <= index < self._length:
            raise IndexError(index)
        return self._payload.code(self._start + index)

    def __iter__(self) -> Iterator[int]:
        for index in range(self._length):
            yield self._payload.code(self._start + index)


@dataclass(frozen=True)
class DeepSeekV4HCPreExecutableDeployment:
    """Exact official executable package and stable mapped F32 resources."""

    root: Path
    build_id: str
    parameter_build_id: str
    application_id: str
    verification_id: str
    artifacts: tuple[HCPreExecutableArtifactRecord, ...]
    instructions: tuple[_DecodedInstruction, ...]
    parameter_deployment: DeepSeekV4HCPreArtifactDeployment
    base_codes: Sequence[int]
    projection_codes: tuple[Sequence[int], ...]
    scale_codes: Sequence[int]
    execution_coverage_sha256: str
    request_schema_sha256: str
    result_schema_sha256: str
    _mapped_payloads: tuple[_MappedF32Payload, ...]
    _root_fingerprint: tuple[int, ...]
    _file_fingerprints: tuple[tuple[str, tuple[int, ...]], ...]

    @property
    def executable(self) -> bool:
        """This package carries exact HC_PRE program execution authority."""

        return True

    def _verify_resources(self) -> None:
        for payload in self._mapped_payloads:
            payload.verify()

    def close(self) -> None:
        """Close all owned mappings; repeated calls are harmless."""

        for payload in self._mapped_payloads:
            payload.close()

    def __enter__(self) -> DeepSeekV4HCPreExecutableDeployment:
        self._verify_resources()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

    def _verify_snapshot(self) -> None:
        """Revalidate the exact files whose identities granted authority."""

        with ExitStack() as stack:
            root_descriptor, root_fingerprint = _open_root(
                stack, self.root, "HC_PRE executable deployment root"
            )
            if root_fingerprint != self._root_fingerprint:
                raise DeepSeekV4HCPreExecutableServiceError(
                    "HC_PRE executable deployment root changed after loading"
                )
            for relative, expected in self._file_fingerprints:
                source = _safe_file(
                    stack,
                    root_descriptor,
                    relative,
                    f"guarded executable file {relative!r}",
                    maximum_size=2 * 1024 * 1024,
                )
                if source.fingerprint != expected:
                    raise DeepSeekV4HCPreExecutableServiceError(
                        f"guarded executable file {relative!r} was replaced"
                    )
                _verify_stable(source, f"guarded executable file {relative!r}")
            _verify_root_stable(
                self.root,
                root_descriptor,
                root_fingerprint,
                "HC_PRE executable deployment root",
            )
        self._verify_resources()


def _expected_source() -> dict[str, str]:
    return {
        "application_id": OFFICIAL_APPLICATION_ID,
        "application_status": _OFFICIAL_APPLICATION_STATUS,
        "checkpoint_lock_id": OFFICIAL_CHECKPOINT_LOCK_ID,
        "evidence_scope": "official_checkpoint",
        "repository": OFFICIAL_REPOSITORY,
        "revision": OFFICIAL_REVISION,
        "verification_id": OFFICIAL_VERIFICATION_ID,
    }


def _expected_execution_coverage() -> dict[str, Any]:
    return {
        "execution_evidence": "none",
        "model_id": MODEL_ID,
        "parameter_coverage": "all_three_verified_f32_resources",
        "program_execution_authority": "complete",
        "program_scope": "exact_hc_pre_plus_complete_for_one_layer_0_attention_site",
        "request_schema": EXECUTION_REQUEST_SCHEMA,
        "result_schema": EXECUTION_RESULT_SCHEMA,
        "schedule_coverage": (
            "exact_two_slot_logical_schedule_with_independent_certificate"
        ),
        "schema": EXECUTION_COVERAGE_SCHEMA,
        "site": dict(_SITE),
        "status": "program_authority_complete_execution_evidence_none",
    }


def _verify_interface_schema(
    value: dict[str, Any],
    *,
    schema_name: str,
    file_name: str,
    label: str,
) -> None:
    if (
        value.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
        or value.get("$id")
        != (
            "https://opentallas.org/schemas/compiler/"
            f"deepseek_v4_hc_pre_executable/{file_name}"
        )
        or value.get("type") != "object"
        or value.get("additionalProperties") is not False
    ):
        raise DeepSeekV4HCPreExecutableServiceError(
            f"{label} outer schema identity differs"
        )
    properties = value.get("properties")
    if type(properties) is not dict:
        raise DeepSeekV4HCPreExecutableServiceError(f"{label} properties are absent")
    instance_schema = properties.get("schema")
    if not _json_equal(instance_schema, {"const": schema_name}):
        raise DeepSeekV4HCPreExecutableServiceError(
            f"{label} instance schema identity differs"
        )


def _verify_contract_documents(payloads: Mapping[str, bytes]) -> None:
    for role, expected_digest in _PINNED_SHA256_BY_ROLE.items():
        if hashlib.sha256(payloads[role]).hexdigest() != expected_digest:
            raise DeepSeekV4HCPreExecutableServiceError(
                f"executable role {role!r} differs from its pinned contract"
            )

    coverage = _strict_json(payloads["execution_coverage"], "execution coverage")
    if not _json_equal(coverage, _expected_execution_coverage()):
        raise DeepSeekV4HCPreExecutableServiceError(
            "executable coverage differs from its exact authority boundary"
        )

    program_contract = _strict_json(
        payloads["program_contract"], "HC_PRE program contract"
    )
    if (
        program_contract.get("schema") != PROGRAM_CONTRACT_SCHEMA
        or program_contract.get("contract_id") != PROGRAM_CONTRACT_ID
        or program_contract.get("program_sha256") != PROGRAM_SHA256
        or not _json_equal(
            program_contract.get("operator_sequence"), ["HC_PRE", "COMPLETE"]
        )
    ):
        raise DeepSeekV4HCPreExecutableServiceError(
            "HC_PRE program contract identity differs"
        )

    schedule = _strict_json(payloads["logical_schedule"], "logical schedule")
    identity = schedule.get("identity")
    if (
        schedule.get("schema") != LOGICAL_SCHEDULE_SCHEMA
        or schedule.get("schedule_id") != SCHEDULE_ID
        or type(identity) is not dict
        or identity.get("program_sha256") != PROGRAM_SHA256
        or identity.get("program_contract_id") != PROGRAM_CONTRACT_ID
    ):
        raise DeepSeekV4HCPreExecutableServiceError(
            "HC_PRE logical schedule identity differs"
        )
    slots = schedule.get("slots")
    if type(slots) is not list or not _json_equal(
        [
            {
                "instruction_index": slot.get("instruction_index"),
                "opcode": slot.get("opcode"),
                "slot": slot.get("slot"),
                "terminal": slot.get("terminal"),
            }
            for slot in slots
            if type(slot) is dict
        ],
        [
            {
                "instruction_index": 0,
                "opcode": "HC_PRE",
                "slot": 0,
                "terminal": False,
            },
            {
                "instruction_index": 1,
                "opcode": "COMPLETE",
                "slot": 1,
                "terminal": True,
            },
        ],
    ):
        raise DeepSeekV4HCPreExecutableServiceError(
            "HC_PRE logical schedule is not exact HC_PRE then COMPLETE"
        )

    certificate = _strict_json(
        payloads["logical_schedule_certificate"],
        "logical schedule certificate",
    )
    if (
        certificate.get("schema") != LOGICAL_CERTIFICATE_SCHEMA
        or certificate.get("certificate_id") != SCHEDULE_CERTIFICATE_ID
        or certificate.get("schedule_id") != SCHEDULE_ID
        or certificate.get("program_sha256") != PROGRAM_SHA256
        or certificate.get("program_contract_id") != PROGRAM_CONTRACT_ID
    ):
        raise DeepSeekV4HCPreExecutableServiceError(
            "HC_PRE logical schedule certificate identity differs"
        )

    request_schema = _strict_json(
        payloads["execution_request_schema"], "execution request schema"
    )
    _verify_interface_schema(
        request_schema,
        schema_name=EXECUTION_REQUEST_SCHEMA,
        file_name="execution_request_v1.schema.json",
        label="execution request schema",
    )
    result_schema = _strict_json(
        payloads["execution_result_schema"], "execution result schema"
    )
    _verify_interface_schema(
        result_schema,
        schema_name=EXECUTION_RESULT_SCHEMA,
        file_name="execution_result_v1.schema.json",
        label="execution result schema",
    )


def _reconcile_parameter_deployment(
    deployment: DeepSeekV4HCPreArtifactDeployment,
    outer_records: Mapping[str, HCPreExecutableArtifactRecord],
    parameter_manifest_payload: bytes,
) -> None:
    if deployment.build_id != PARAMETER_BUILD_ID:
        raise DeepSeekV4HCPreExecutableServiceError(
            "nested parameter deployment is not the pinned official build"
        )
    manifest_record = outer_records["parameter_deployment_manifest"]
    if manifest_record.sha256 != hashlib.sha256(
        parameter_manifest_payload
    ).hexdigest() or manifest_record.size_bytes != len(parameter_manifest_payload):
        raise DeepSeekV4HCPreExecutableServiceError(
            "nested parameter manifest differs from the outer artifact table"
        )
    for inner in deployment.artifacts:
        outer_role = _PARAMETER_ROLE_MAP[inner.role]
        outer = outer_records[outer_role]
        if (
            outer.relative_path != f"parameters/{inner.relative_path}"
            or outer.sha256 != inner.sha256
            or outer.size_bytes != inner.size_bytes
        ):
            raise DeepSeekV4HCPreExecutableServiceError(
                f"outer executable record differs for parameter role {inner.role!r}"
            )


def load_deepseek_v4_hc_pre_executable_deployment(
    deployment_dir: Path,
) -> DeepSeekV4HCPreExecutableDeployment:
    """Verify and map the complete pinned official executable package."""

    if not EXECUTABLE_BUILD_ID:
        raise DeepSeekV4HCPreExecutableServiceError(
            "final executable deployment identity has not been frozen"
        )
    root = Path(deployment_dir).absolute()
    mapped_payloads: list[_MappedF32Payload] = []
    try:
        with ExitStack() as stack:
            root_descriptor, root_fingerprint = _open_root(
                stack, root, "HC_PRE executable deployment root"
            )
            manifest_file = _safe_file(
                stack,
                root_descriptor,
                "deployment_manifest.json",
                "HC_PRE executable deployment manifest",
                maximum_size=_MAX_MANIFEST_BYTES,
            )
            manifest_payload = _read_bytes(
                manifest_file,
                "HC_PRE executable deployment manifest",
                _MAX_MANIFEST_BYTES,
            )
            manifest = _strict_json(
                manifest_payload, "HC_PRE executable deployment manifest"
            )
            _exact_keys(
                manifest,
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
            expected_metadata = {
                "claim_boundary": _CLAIM_BOUNDARY,
                "compiler": _COMPILER,
                "entrypoint": _ENTRYPOINT,
                "model_id": MODEL_ID,
                "parameter_build_id": PARAMETER_BUILD_ID,
                "program_contract_id": PROGRAM_CONTRACT_ID,
                "program_sha256": PROGRAM_SHA256,
                "schedule_certificate_id": SCHEDULE_CERTIFICATE_ID,
                "schedule_id": SCHEDULE_ID,
                "schema": EXECUTABLE_DEPLOYMENT_SCHEMA,
                "site": _SITE,
                "source": _expected_source(),
                "status": _DEPLOYMENT_STATUS,
            }
            observed_metadata = {key: manifest[key] for key in expected_metadata}
            if not _json_equal(observed_metadata, expected_metadata):
                raise DeepSeekV4HCPreExecutableServiceError(
                    "HC_PRE executable metadata or official source identity differs"
                )

            raw_artifacts = manifest["artifacts"]
            if type(raw_artifacts) is not list or len(raw_artifacts) != 18:
                raise DeepSeekV4HCPreExecutableServiceError(
                    "HC_PRE executable must enumerate exactly 18 artifacts"
                )
            records: list[HCPreExecutableArtifactRecord] = []
            records_by_role: dict[str, HCPreExecutableArtifactRecord] = {}
            files_by_role: dict[str, _StableFile] = {}
            payloads_by_role: dict[str, bytes] = {}
            observed_records: list[dict[str, Any]] = []
            paths: set[str] = set()
            previous_path: str | None = None
            for index, raw_record in enumerate(raw_artifacts):
                record = _exact_keys(
                    raw_record,
                    {"path", "role", "sha256", "size_bytes"},
                    f"artifacts[{index}]",
                )
                relative = _safe_relative(record["path"], f"artifacts[{index}].path")
                role = record["role"]
                if type(role) is not str or role not in _EXPECTED_ROLES:
                    raise DeepSeekV4HCPreExecutableServiceError(
                        f"artifacts[{index}].role is outside the closed role set"
                    )
                if role in records_by_role or relative in paths:
                    raise DeepSeekV4HCPreExecutableServiceError(
                        "HC_PRE executable artifact roles and paths must be unique"
                    )
                if previous_path is not None and relative <= previous_path:
                    raise DeepSeekV4HCPreExecutableServiceError(
                        "HC_PRE executable artifact table is not path-sorted"
                    )
                previous_path = relative
                paths.add(relative)
                digest = _digest(record["sha256"], f"artifacts[{index}].sha256")
                exact_size = _EXACT_SIZE_BY_ROLE.get(role)
                size = _integer(
                    record["size_bytes"],
                    f"artifacts[{index}].size_bytes",
                    minimum=1,
                    maximum=2 * 1024 * 1024,
                )
                if exact_size is not None and size != exact_size:
                    raise DeepSeekV4HCPreExecutableServiceError(
                        f"artifact role {role!r} has a noncanonical size"
                    )
                source_file = _safe_file(
                    stack,
                    root_descriptor,
                    relative,
                    f"executable artifact {relative!r}",
                    exact_size=size,
                    maximum_size=2 * 1024 * 1024,
                )
                payload = _read_bytes(
                    source_file,
                    f"executable artifact {relative!r}",
                    2 * 1024 * 1024,
                )
                if hashlib.sha256(payload).hexdigest() != digest:
                    raise DeepSeekV4HCPreExecutableServiceError(
                        f"executable artifact {relative!r} differs from its hash"
                    )
                immutable = HCPreExecutableArtifactRecord(relative, role, digest, size)
                records.append(immutable)
                records_by_role[role] = immutable
                files_by_role[role] = source_file
                payloads_by_role[role] = payload
                observed_records.append(dict(record))

            if set(records_by_role) != _EXPECTED_ROLES:
                raise DeepSeekV4HCPreExecutableServiceError(
                    "HC_PRE executable artifact role closure differs"
                )
            for role, expected_path in _FIXED_PATH_BY_ROLE.items():
                if records_by_role[role].relative_path != expected_path:
                    raise DeepSeekV4HCPreExecutableServiceError(
                        f"HC_PRE executable role {role!r} has a noncanonical path"
                    )

            body = {key: manifest[key] for key in manifest if key != "build_id"}
            build_id = _digest(manifest["build_id"], "executable build_id")
            if hashlib.sha256(_canonical_json_bytes(body)).hexdigest() != build_id:
                raise DeepSeekV4HCPreExecutableServiceError(
                    "HC_PRE executable build_id does not bind its full body"
                )
            if build_id != EXECUTABLE_BUILD_ID:
                raise DeepSeekV4HCPreExecutableServiceError(
                    "HC_PRE executable is not the pinned official package build"
                )

            _verify_contract_documents(payloads_by_role)
            instructions = _decode_exact_program(payloads_by_role["microcode_program"])

            parameter_deployment = load_deepseek_v4_hc_pre_artifact_deployment(
                root / "parameters"
            )
            _reconcile_parameter_deployment(
                parameter_deployment,
                records_by_role,
                payloads_by_role["parameter_deployment_manifest"],
            )

            actual_files, actual_directories = _enumerate_tree(root_descriptor)
            if (
                actual_files != paths | {"deployment_manifest.json"}
                or actual_directories != _EXPECTED_DIRECTORIES
            ):
                raise DeepSeekV4HCPreExecutableServiceError(
                    "HC_PRE executable contains an unlisted or missing tree entry"
                )
            for source_file in (manifest_file, *files_by_role.values()):
                _verify_stable(
                    source_file,
                    f"guarded executable file {source_file.relative_path!r}",
                )
            _verify_root_stable(
                root,
                root_descriptor,
                root_fingerprint,
                "HC_PRE executable deployment root",
            )

            base_map = _MappedF32Payload(
                files_by_role["hc_base_parameter"],
                records_by_role["hc_base_parameter"].sha256,
                "HC_PRE base parameter",
            )
            mapped_payloads.append(base_map)
            projection_map = _MappedF32Payload(
                files_by_role["hc_projection_parameter"],
                records_by_role["hc_projection_parameter"].sha256,
                "HC_PRE projection parameter",
            )
            mapped_payloads.append(projection_map)
            scale_map = _MappedF32Payload(
                files_by_role["hc_scale_parameter"],
                records_by_role["hc_scale_parameter"].sha256,
                "HC_PRE scale parameter",
            )
            mapped_payloads.append(scale_map)
            base_codes = _F32Vector(base_map, 0, 24)
            projection_codes = tuple(
                _F32Vector(projection_map, row * 16_384, 16_384) for row in range(24)
            )
            scale_codes = _F32Vector(scale_map, 0, 3)
            for payload in mapped_payloads:
                payload.verify()
            for source_file in (manifest_file, *files_by_role.values()):
                _verify_stable(
                    source_file,
                    f"guarded executable file {source_file.relative_path!r}",
                )
            _verify_root_stable(
                root,
                root_descriptor,
                root_fingerprint,
                "HC_PRE executable deployment root",
            )

            result = DeepSeekV4HCPreExecutableDeployment(
                root=root,
                build_id=build_id,
                parameter_build_id=PARAMETER_BUILD_ID,
                application_id=OFFICIAL_APPLICATION_ID,
                verification_id=OFFICIAL_VERIFICATION_ID,
                artifacts=tuple(records),
                instructions=instructions,
                parameter_deployment=parameter_deployment,
                base_codes=base_codes,
                projection_codes=projection_codes,
                scale_codes=scale_codes,
                execution_coverage_sha256=records_by_role["execution_coverage"].sha256,
                request_schema_sha256=records_by_role[
                    "execution_request_schema"
                ].sha256,
                result_schema_sha256=records_by_role["execution_result_schema"].sha256,
                _mapped_payloads=tuple(mapped_payloads),
                _root_fingerprint=root_fingerprint,
                _file_fingerprints=tuple(
                    sorted(
                        (
                            source.relative_path,
                            source.fingerprint,
                        )
                        for source in (manifest_file, *files_by_role.values())
                    )
                ),
            )
            mapped_payloads = []
            return result
    finally:
        for payload in mapped_payloads:
            payload.close()


@dataclass(frozen=True)
class HCPreExecutableRequest:
    """Fully verified canonical command and bit-preserving BF16 input."""

    request_sha256: str
    build_id: str
    model_id: str
    program_sha256: str
    batch_size: int
    sequence_length: int
    token_count: int
    input_codes: tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]
    _root: Path
    _root_fingerprint: tuple[int, ...]
    _file_fingerprints: tuple[tuple[str, tuple[int, ...]], ...]

    def _verify_snapshot(self) -> None:
        with ExitStack() as stack:
            root_descriptor, root_fingerprint = _open_root(
                stack, self._root, "HC_PRE request root"
            )
            if root_fingerprint != self._root_fingerprint:
                raise DeepSeekV4HCPreExecutableServiceError(
                    "HC_PRE request root changed after loading"
                )
            for relative, expected in self._file_fingerprints:
                source = _safe_file(
                    stack,
                    root_descriptor,
                    relative,
                    f"guarded request file {relative!r}",
                    maximum_size=_MAX_REQUEST_JSON_BYTES,
                )
                if source.fingerprint != expected:
                    raise DeepSeekV4HCPreExecutableServiceError(
                        f"guarded request file {relative!r} was replaced"
                    )
                _verify_stable(source, f"guarded request file {relative!r}")
            _verify_root_stable(
                self._root,
                root_descriptor,
                root_fingerprint,
                "HC_PRE request root",
            )


def _load_execution_request(
    deployment: DeepSeekV4HCPreExecutableDeployment,
    request_manifest: Path,
) -> HCPreExecutableRequest:
    path = Path(request_manifest).absolute()
    if path.name != "request_manifest.json":
        raise DeepSeekV4HCPreExecutableServiceError(
            "HC_PRE request must be named request_manifest.json"
        )
    root = path.parent
    with ExitStack() as stack:
        root_descriptor, root_fingerprint = _open_root(
            stack, root, "HC_PRE request root"
        )
        manifest_file = _safe_file(
            stack,
            root_descriptor,
            "request_manifest.json",
            "HC_PRE request manifest",
            maximum_size=_MAX_REQUEST_JSON_BYTES,
        )
        manifest_payload = _read_bytes(
            manifest_file,
            "HC_PRE request manifest",
            _MAX_REQUEST_JSON_BYTES,
        )
        request = _strict_json(manifest_payload, "HC_PRE request manifest")
        _exact_keys(
            request,
            {
                "batch_size",
                "build_id",
                "input",
                "model_id",
                "program_sha256",
                "schema",
                "sequence_length",
                "token_count",
            },
            "HC_PRE request manifest",
        )
        batch_size = _integer(
            request["batch_size"], "request.batch_size", minimum=1, maximum=4
        )
        sequence_length = _integer(
            request["sequence_length"],
            "request.sequence_length",
            minimum=1,
            maximum=4,
        )
        token_count = _integer(
            request["token_count"], "request.token_count", minimum=1, maximum=4
        )
        if batch_size * sequence_length != token_count:
            raise DeepSeekV4HCPreExecutableServiceError(
                "request batch_size*sequence_length must equal token_count"
            )
        expected_identity = {
            "build_id": deployment.build_id,
            "model_id": MODEL_ID,
            "program_sha256": PROGRAM_SHA256,
            "schema": EXECUTION_REQUEST_SCHEMA,
        }
        observed_identity = {key: request[key] for key in expected_identity}
        if not _json_equal(observed_identity, expected_identity):
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE request identity differs from its deployment"
            )

        descriptor = _exact_keys(
            request["input"],
            {
                "dtype",
                "encoding",
                "id",
                "path",
                "register",
                "sha256",
                "shape",
                "size_bytes",
            },
            "HC_PRE request input descriptor",
        )
        size_bytes = token_count * 4 * 4096 * 2
        expected_descriptor = {
            "dtype": "BF16",
            "encoding": "bfloat16_little_endian",
            "id": "hc_hidden",
            "path": "input/hc_hidden.bf16le",
            "register": "HC_HIDDEN",
            "sha256": descriptor.get("sha256"),
            "shape": [batch_size, sequence_length, 4, 4096],
            "size_bytes": size_bytes,
        }
        input_sha256 = _digest(descriptor.get("sha256"), "request.input.sha256")
        if not _json_equal(descriptor, expected_descriptor):
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE request input descriptor differs"
            )
        input_file = _safe_file(
            stack,
            root_descriptor,
            descriptor["path"],
            "HC_PRE request BF16 input",
            exact_size=size_bytes,
            maximum_size=_MAX_INPUT_BYTES,
        )
        input_payload = _read_bytes(
            input_file, "HC_PRE request BF16 input", _MAX_INPUT_BYTES
        )
        if hashlib.sha256(input_payload).hexdigest() != input_sha256:
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE request BF16 input differs from its SHA-256"
            )
        flat = tuple(code for (code,) in struct.iter_unpack("<H", input_payload))
        for index, code in enumerate(flat):
            if code & 0x7F80 == 0x7F80:
                raise DeepSeekV4HCPreExecutableServiceError(
                    f"HC_PRE request input contains nonfinite BF16 at element {index}"
                )
        batches: list[tuple[tuple[tuple[int, ...], ...], ...]] = []
        offset = 0
        for _ in range(batch_size):
            sequences: list[tuple[tuple[int, ...], ...]] = []
            for _ in range(sequence_length):
                streams: list[tuple[int, ...]] = []
                for _ in range(4):
                    streams.append(tuple(flat[offset : offset + 4096]))
                    offset += 4096
                sequences.append(tuple(streams))
            batches.append(tuple(sequences))
        if offset != len(flat):  # pragma: no cover - exact size invariant
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE request decoding did not consume its complete payload"
            )

        actual_files, actual_directories = _enumerate_tree(root_descriptor)
        if actual_files != {
            "request_manifest.json",
            "input/hc_hidden.bf16le",
        } or actual_directories != {"input"}:
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE request contains an unlisted or missing tree entry"
            )
        _verify_stable(manifest_file, "HC_PRE request manifest")
        _verify_stable(input_file, "HC_PRE request BF16 input")
        _verify_root_stable(
            root,
            root_descriptor,
            root_fingerprint,
            "HC_PRE request root",
        )
        return HCPreExecutableRequest(
            request_sha256=hashlib.sha256(manifest_payload).hexdigest(),
            build_id=deployment.build_id,
            model_id=MODEL_ID,
            program_sha256=PROGRAM_SHA256,
            batch_size=batch_size,
            sequence_length=sequence_length,
            token_count=token_count,
            input_codes=tuple(batches),
            _root=root,
            _root_fingerprint=root_fingerprint,
            _file_fingerprints=tuple(
                sorted(
                    (
                        source.relative_path,
                        source.fingerprint,
                    )
                    for source in (manifest_file, input_file)
                )
            ),
        )


@dataclass(frozen=True)
class HCPreExecutableResult:
    """One complete immutable HC_PRE execution result with all observables."""

    build_id: str
    model_id: str
    program_sha256: str
    request_sha256: str
    batch_size: int
    sequence_length: int
    token_count: int
    deployment_status: str
    evidence_scope: str
    source_application_status: str
    status: str
    execution_scope: str
    counter_reconciliation: str
    numeric_status: Mapping[str, int | bool]
    attention_input_codes: hc_pre_numeric.BF16Tensor3
    attention_pre_codes: hc_pre_numeric.F32Tensor3
    attention_post_codes: hc_pre_numeric.F32Tensor3
    attention_combination_codes: hc_pre_numeric.F32Tensor4
    attention_residual_codes: hc_pre_numeric.BF16Tensor4
    rms_mean_codes: tuple[tuple[int, ...], ...]
    rms_inverse_codes: tuple[tuple[int, ...], ...]
    projection_codes: hc_pre_numeric.F32Tensor3
    mix_codes: hc_pre_numeric.F32Tensor3
    stable_softmax_codes: hc_pre_numeric.F32Tensor4
    branch_saturation_count: int
    logical_counters: Mapping[str, int]
    manifest: Mapping[str, Any]

    @property
    def architectural_outputs(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "ATTENTION_INPUT": self.attention_input_codes,
                "ATTENTION_PRE": self.attention_pre_codes,
                "ATTENTION_POST": self.attention_post_codes,
                "ATTENTION_COMBINATION": self.attention_combination_codes,
                "ATTENTION_RESIDUAL": self.attention_residual_codes,
            }
        )


def _poison(message: str, cause: BaseException | None = None) -> NoReturn:
    error = DeepSeekV4HCPreExecutableServiceError(message)
    if cause is None:
        raise error
    raise error from cause


def _encode_tensor(
    value: object,
    shape: tuple[int, ...],
    *,
    bits: int,
    label: str,
) -> bytes:
    """Serialize one exact nested tuple without host-float conversion."""

    payload = bytearray()
    decoder = struct.Struct("<H" if bits == 16 else "<I")
    exponent_mask = 0x7F80 if bits == 16 else 0x7F800000

    def visit(current: object, dimensions: tuple[int, ...], path: str) -> None:
        if not dimensions:
            if type(current) is not int or current < 0 or current >= 1 << bits:
                _poison(f"{path} is not an unsigned {bits}-bit encoding")
            if current & exponent_mask == exponent_mask:
                _poison(f"{path} is not a finite encoded value")
            payload.extend(decoder.pack(current))
            return
        if type(current) is not tuple or len(current) != dimensions[0]:
            _poison(f"{path} must be an exact tuple with extent {dimensions[0]}")
        for index, child in enumerate(current):
            visit(child, dimensions[1:], f"{path}[{index}]")

    visit(value, shape, label)
    expected_size = decoder.size
    for extent in shape:
        expected_size *= extent
    if len(payload) != expected_size:  # pragma: no cover - recursive invariant
        _poison(f"{label} serialization size differs")
    return bytes(payload)


def _result_descriptor(
    *,
    identifier: str,
    dtype: str,
    encoding: str,
    path: str,
    payload: bytes,
    shape: tuple[int, ...],
    register: str | None,
) -> dict[str, Any]:
    descriptor: dict[str, Any] = {
        "dtype": dtype,
        "encoding": encoding,
        "id": identifier,
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "shape": list(shape),
        "size_bytes": len(payload),
    }
    if register is not None:
        descriptor["register"] = register
    return descriptor


def _reconcile_counters(
    deployment: DeepSeekV4HCPreExecutableDeployment,
    numeric: hc_pre_numeric.HCPreServiceResult,
    token_count: int,
) -> Mapping[str, int]:
    coefficients = dict(deployment.parameter_deployment.counter_coefficients)
    fixed_names = _COUNTER_NAMES - {"hc_pre_branch_bf16_saturations"}
    if set(coefficients) != fixed_names or any(
        type(value) is not int or value < 0 for value in coefficients.values()
    ):
        _poison("verified HC_PRE parameter counter contract differs at execution")
    saturation_count = numeric.branch_saturation_count
    if (
        type(saturation_count) is not int
        or not 0 <= saturation_count <= token_count * 4096
    ):
        _poison("HC_PRE numeric branch saturation count is outside its bound")
    expected = {
        name: coefficient * token_count for name, coefficient in coefficients.items()
    }
    expected["hc_pre_branch_bf16_saturations"] = saturation_count
    observed = numeric.logical_counters
    if not isinstance(observed, Mapping) or set(observed) != _COUNTER_NAMES:
        _poison("HC_PRE numeric logical counter closure differs")
    for name, value in observed.items():
        if type(name) is not str or type(value) is not int or value < 0:
            _poison("HC_PRE numeric logical counter types differ")
    if dict(observed) != expected:
        _poison("HC_PRE numeric logical counters do not reconcile exactly")
    if observed["hc_pre_branch_bf16_saturations"] != numeric.branch_saturation_count:
        _poison("HC_PRE numeric saturation counter does not reconcile")
    return MappingProxyType(dict(sorted(expected.items())))


def _build_result(
    deployment: DeepSeekV4HCPreExecutableDeployment,
    request: HCPreExecutableRequest,
    numeric: hc_pre_numeric.HCPreServiceResult,
) -> tuple[HCPreExecutableResult, dict[str, bytes], dict[str, Any]]:
    if type(numeric) is not hc_pre_numeric.HCPreServiceResult:
        _poison("HC_PRE numeric engine returned an invalid result object")
    batch = request.batch_size
    sequence = request.sequence_length
    axes = (batch, sequence)
    if numeric.residual_codes != request.input_codes:
        _poison("HC_PRE numeric residual does not preserve the exact request input")

    tensor_specs = (
        (
            "attention_input",
            numeric.branch_codes,
            axes + (4096,),
            16,
            "BF16",
            "bfloat16_little_endian",
            "outputs/attention_input.bf16le",
            "ATTENTION_INPUT",
        ),
        (
            "attention_pre",
            numeric.pre_codes,
            axes + (4,),
            32,
            "F32",
            "ieee754_binary32_little_endian",
            "outputs/attention_pre.f32le",
            "ATTENTION_PRE",
        ),
        (
            "attention_post",
            numeric.post_codes,
            axes + (4,),
            32,
            "F32",
            "ieee754_binary32_little_endian",
            "outputs/attention_post.f32le",
            "ATTENTION_POST",
        ),
        (
            "attention_combination",
            numeric.combination_codes,
            axes + (4, 4),
            32,
            "F32",
            "ieee754_binary32_little_endian",
            "outputs/attention_combination.f32le",
            "ATTENTION_COMBINATION",
        ),
        (
            "attention_residual",
            numeric.residual_codes,
            axes + (4, 4096),
            16,
            "BF16",
            "bfloat16_little_endian",
            "outputs/attention_residual.bf16le",
            "ATTENTION_RESIDUAL",
        ),
        (
            "rms_mean_codes",
            numeric.rms_mean_codes,
            axes,
            32,
            "F32",
            "ieee754_binary32_little_endian",
            "diagnostics/rms_mean.f32le",
            None,
        ),
        (
            "rms_inverse_codes",
            numeric.rms_inverse_codes,
            axes,
            32,
            "F32",
            "ieee754_binary32_little_endian",
            "diagnostics/rms_inverse.f32le",
            None,
        ),
        (
            "projection_codes",
            numeric.projection_codes,
            axes + (24,),
            32,
            "F32",
            "ieee754_binary32_little_endian",
            "diagnostics/projection.f32le",
            None,
        ),
        (
            "mix_codes",
            numeric.mix_codes,
            axes + (24,),
            32,
            "F32",
            "ieee754_binary32_little_endian",
            "diagnostics/mix.f32le",
            None,
        ),
        (
            "stable_softmax_codes",
            numeric.stable_softmax_codes,
            axes + (4, 4),
            32,
            "F32",
            "ieee754_binary32_little_endian",
            "diagnostics/stable_softmax.f32le",
            None,
        ),
    )
    payloads: dict[str, bytes] = {}
    descriptors: dict[str, dict[str, Any]] = {}
    for identifier, value, shape, bits, dtype, encoding, path, register in tensor_specs:
        payload = _encode_tensor(value, shape, bits=bits, label=identifier)
        payloads[path] = payload
        descriptors[identifier] = _result_descriptor(
            identifier=identifier,
            dtype=dtype,
            encoding=encoding,
            path=path,
            payload=payload,
            shape=shape,
            register=register,
        )
    if len(payloads) != 10:
        _poison("HC_PRE result payload closure differs")

    counters = _reconcile_counters(deployment, numeric, request.token_count)
    manifest: dict[str, Any] = {
        "batch_size": batch,
        "build_id": deployment.build_id,
        "counter_reconciliation": "exact",
        "deployment_status": _RESULT_DEPLOYMENT_STATUS,
        "diagnostics": {
            "mix_codes": descriptors["mix_codes"],
            "projection_codes": descriptors["projection_codes"],
            "rms_inverse_codes": descriptors["rms_inverse_codes"],
            "rms_mean_codes": descriptors["rms_mean_codes"],
            "stable_softmax_codes": descriptors["stable_softmax_codes"],
        },
        "evidence_scope": _RESULT_EVIDENCE_SCOPE,
        "execution_scope": _RESULT_EXECUTION_SCOPE,
        "logical_counters": dict(counters),
        "model_id": MODEL_ID,
        "numeric_status": {
            "branch_saturation_count": numeric.branch_saturation_count,
            "poison": False,
        },
        "outputs": [
            descriptors["attention_input"],
            descriptors["attention_pre"],
            descriptors["attention_post"],
            descriptors["attention_combination"],
            descriptors["attention_residual"],
        ],
        "program_sha256": PROGRAM_SHA256,
        "request_sha256": request.request_sha256,
        "schema": EXECUTION_RESULT_SCHEMA,
        "sequence_length": sequence,
        "source_application_status": _RESULT_SOURCE_APPLICATION_STATUS,
        "status": _RESULT_STATUS,
        "token_count": request.token_count,
    }
    result = HCPreExecutableResult(
        build_id=deployment.build_id,
        model_id=MODEL_ID,
        program_sha256=PROGRAM_SHA256,
        request_sha256=request.request_sha256,
        batch_size=batch,
        sequence_length=sequence,
        token_count=request.token_count,
        deployment_status=_RESULT_DEPLOYMENT_STATUS,
        evidence_scope=_RESULT_EVIDENCE_SCOPE,
        source_application_status=_RESULT_SOURCE_APPLICATION_STATUS,
        status=_RESULT_STATUS,
        execution_scope=_RESULT_EXECUTION_SCOPE,
        counter_reconciliation="exact",
        numeric_status=MappingProxyType(
            {
                "branch_saturation_count": numeric.branch_saturation_count,
                "poison": False,
            }
        ),
        attention_input_codes=numeric.branch_codes,
        attention_pre_codes=numeric.pre_codes,
        attention_post_codes=numeric.post_codes,
        attention_combination_codes=numeric.combination_codes,
        attention_residual_codes=numeric.residual_codes,
        rms_mean_codes=numeric.rms_mean_codes,
        rms_inverse_codes=numeric.rms_inverse_codes,
        projection_codes=numeric.projection_codes,
        mix_codes=numeric.mix_codes,
        stable_softmax_codes=numeric.stable_softmax_codes,
        branch_saturation_count=numeric.branch_saturation_count,
        logical_counters=counters,
        manifest=_freeze_json(manifest),
    )
    return result, payloads, manifest


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_json(child) for key, child in value.items()}
        )
    if type(value) is list:
        return tuple(_freeze_json(child) for child in value)
    return value


def _descriptor_paths(manifest: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    outputs = manifest.get("outputs")
    diagnostics = manifest.get("diagnostics")
    if type(outputs) is not list or len(outputs) != 5 or type(diagnostics) is not dict:
        _poison("staged HC_PRE result descriptor closure differs")
    expected_diagnostic_names = {
        "mix_codes",
        "projection_codes",
        "rms_inverse_codes",
        "rms_mean_codes",
        "stable_softmax_codes",
    }
    if set(diagnostics) != expected_diagnostic_names:
        _poison("staged HC_PRE diagnostic descriptor closure differs")
    descriptors = [*outputs]
    descriptors.extend(diagnostics[name] for name in sorted(diagnostics))
    if any(type(descriptor) is not dict for descriptor in descriptors):
        _poison("staged HC_PRE result contains a non-object descriptor")
    return tuple(descriptors)


def _verify_staged_result(
    root: Path,
    root_descriptor: int,
    expected_manifest: dict[str, Any],
    expected_payloads: Mapping[str, bytes],
) -> None:
    root_fingerprint = _fingerprint(os.fstat(root_descriptor))
    with ExitStack() as stack:
        manifest_file = _safe_file(
            stack,
            root_descriptor,
            "result_manifest.json",
            "staged HC_PRE result manifest",
            maximum_size=_MAX_RESULT_JSON_BYTES,
        )
        manifest_payload = _read_bytes(
            manifest_file,
            "staged HC_PRE result manifest",
            _MAX_RESULT_JSON_BYTES,
        )
        manifest = _strict_json(manifest_payload, "staged HC_PRE result manifest")
        if not _json_equal(manifest, expected_manifest):
            _poison("staged HC_PRE result manifest differs before publication")
        descriptors = _descriptor_paths(manifest)
        observed_paths: set[str] = set()
        guarded: list[_StableFile] = [manifest_file]
        for index, descriptor in enumerate(descriptors):
            path = _safe_relative(
                descriptor.get("path"), f"result descriptor {index}.path"
            )
            if path in observed_paths or path not in expected_payloads:
                _poison("staged HC_PRE result descriptor path closure differs")
            observed_paths.add(path)
            size = _integer(
                descriptor.get("size_bytes"),
                f"result descriptor {index}.size_bytes",
                minimum=1,
                maximum=_MAX_INPUT_BYTES,
            )
            digest = _digest(
                descriptor.get("sha256"), f"result descriptor {index}.sha256"
            )
            source = _safe_file(
                stack,
                root_descriptor,
                path,
                f"staged HC_PRE result artifact {path!r}",
                exact_size=size,
                maximum_size=_MAX_INPUT_BYTES,
            )
            guarded.append(source)
            payload = _read_bytes(
                source,
                f"staged HC_PRE result artifact {path!r}",
                _MAX_INPUT_BYTES,
            )
            if (
                payload != expected_payloads[path]
                or hashlib.sha256(payload).hexdigest() != digest
            ):
                _poison(f"staged HC_PRE result artifact {path!r} differs")
        if observed_paths != set(expected_payloads):
            _poison("staged HC_PRE result payload closure differs")
        actual_files, actual_directories = _enumerate_tree(root_descriptor)
        if actual_files != observed_paths | {"result_manifest.json"} or (
            actual_directories != {"diagnostics", "outputs"}
        ):
            _poison("staged HC_PRE result tree is not exactly closed")
        for source in guarded:
            _verify_stable(source, f"guarded staged result {source.relative_path!r}")
        _verify_root_stable(
            root,
            root_descriptor,
            root_fingerprint,
            "staged HC_PRE result root",
        )


def _fsync_directory(root_descriptor: int, relative: str) -> None:
    descriptor = _open_relative_descriptor(
        root_descriptor,
        relative,
        f"HC_PRE result directory {relative!r}",
        directory=True,
    )
    try:
        os.fsync(descriptor)
    except OSError as exc:
        _poison(f"cannot synchronize HC_PRE result directory {relative!r}", exc)
    finally:
        os.close(descriptor)


def _require_result_absent(parent_descriptor: int, name: str, output: Path) -> None:
    if name in {"", ".", ".."} or "/" in name or "\\" in name or "\x00" in name:
        _poison("HC_PRE result root must be one safe child of its parent")
    try:
        os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as exc:
        _poison(f"cannot inspect HC_PRE result output {output}: {exc}", exc)
    _poison(f"result output already exists: {output}")


def _publish_result(
    *,
    output: Path,
    parent: Path,
    parent_descriptor: int,
    output_name: str,
    payloads: Mapping[str, bytes],
    manifest: dict[str, Any],
) -> None:
    with ExitStack() as stack:
        temporary_root, temporary_name, temporary_descriptor = (
            _create_private_directory(
                stack,
                parent=parent,
                parent_descriptor=parent_descriptor,
            )
        )
        published = False
        namespace_committed = False
        try:
            try:
                os.mkdir("outputs", 0o700, dir_fd=temporary_descriptor)
                os.mkdir("diagnostics", 0o700, dir_fd=temporary_descriptor)
            except OSError as exc:
                _poison("cannot create HC_PRE result artifact directories", exc)
            for relative in sorted(payloads):
                _write_exclusive_bytes(
                    temporary_descriptor,
                    relative,
                    payloads[relative],
                )
            _write_exclusive_bytes(
                temporary_descriptor,
                "result_manifest.json",
                _canonical_json_bytes(manifest),
            )
            _fsync_directory(temporary_descriptor, "diagnostics")
            _fsync_directory(temporary_descriptor, "outputs")
            try:
                os.fsync(temporary_descriptor)
            except OSError as exc:
                _poison("cannot synchronize staged HC_PRE result root", exc)
            _verify_staged_result(
                temporary_root,
                temporary_descriptor,
                manifest,
                payloads,
            )
            _verify_directory_binding(
                parent,
                parent_descriptor,
                "HC_PRE result parent",
            )
            _publish_create_once(
                parent_descriptor=parent_descriptor,
                temporary_name=temporary_name,
                output_name=output_name,
                output=output,
            )
            namespace_committed = True
            _verify_directory_binding(
                parent,
                parent_descriptor,
                "HC_PRE result parent",
            )
            _require_child_directory_identity(
                parent_descriptor=parent_descriptor,
                name=output_name,
                held_descriptor=temporary_descriptor,
                label="published HC_PRE result root",
            )
            try:
                os.fsync(parent_descriptor)
            except OSError as exc:
                _poison("cannot synchronize published HC_PRE result parent", exc)
            _verify_directory_binding(
                parent,
                parent_descriptor,
                "HC_PRE result parent",
            )
            _require_child_directory_identity(
                parent_descriptor=parent_descriptor,
                name=output_name,
                held_descriptor=temporary_descriptor,
                label="published HC_PRE result root",
            )
            published = True
        finally:
            if not published:
                if namespace_committed:
                    _restore_staging_after_failed_publication(
                        parent_descriptor=parent_descriptor,
                        temporary_name=temporary_name,
                        output_name=output_name,
                        temporary_descriptor=temporary_descriptor,
                        output=output,
                    )
                _cleanup_private_directory(
                    parent_descriptor=parent_descriptor,
                    name=temporary_name,
                    descriptor=temporary_descriptor,
                )


def _execute_packaged_program(
    deployment: DeepSeekV4HCPreExecutableDeployment,
    request: HCPreExecutableRequest,
) -> hc_pre_numeric.HCPreServiceResult:
    numeric: hc_pre_numeric.HCPreServiceResult | None = None
    completed = False
    for program_counter, instruction in enumerate(deployment.instructions):
        if instruction.opcode == _OPCODE_HC_PRE:
            if program_counter != 0 or numeric is not None or completed:
                _poison("packaged HC_PRE program has illegal operator control flow")
            try:
                numeric = hc_pre_numeric.execute_hc_pre(
                    request.input_codes,
                    deployment.projection_codes,
                    deployment.scale_codes,
                    deployment.base_codes,
                    norm_epsilon_binary32=(hc_pre_numeric.HC_PRE_NORM_EPSILON_BINARY32),
                    hc_epsilon_binary32=(
                        hc_pre_numeric.HC_PRE_SINKHORN_EPSILON_BINARY32
                    ),
                )
            except Exception as exc:
                _poison("packaged HC_PRE numeric execution poisoned", exc)
            continue
        if instruction.opcode == _OPCODE_COMPLETE:
            if (
                program_counter != len(deployment.instructions) - 1
                or numeric is None
                or completed
            ):
                _poison("packaged HC_PRE program has illegal COMPLETE control flow")
            completed = True
            continue
        _poison(f"packaged HC_PRE program has unsupported opcode {instruction.opcode}")
    if not completed or numeric is None:
        _poison("packaged HC_PRE program did not commit COMPLETE")
    return numeric


class DeepSeekV4HCPreExecutableServiceEngine:
    """Artifact-only interpreter for the pinned executable HC_PRE package."""

    def __init__(self, deployment: DeepSeekV4HCPreExecutableDeployment):
        if type(deployment) is not DeepSeekV4HCPreExecutableDeployment:
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE executable deployment snapshot is invalid"
            )
        self.deployment = deployment
        self._closed = False

    @classmethod
    def load(cls, deployment_dir: Path) -> DeepSeekV4HCPreExecutableServiceEngine:
        return cls(load_deepseek_v4_hc_pre_executable_deployment(deployment_dir))

    def execute(
        self,
        request_manifest: Path,
        result_dir: Path,
    ) -> HCPreExecutableResult:
        """Execute the packaged program and atomically publish all observables."""

        if self._closed:
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE executable service engine is closed"
            )

        output = Path(result_dir).absolute()
        parent = output.parent
        output_name = output.name
        with ExitStack() as stack:
            parent_descriptor, _ = _open_root(stack, parent, "HC_PRE result parent")
            _require_result_absent(parent_descriptor, output_name, output)
            deployment = self.deployment
            deployment._verify_snapshot()
            request = _load_execution_request(deployment, request_manifest)
            request._verify_snapshot()
            numeric = _execute_packaged_program(deployment, request)
            deployment._verify_snapshot()
            request._verify_snapshot()
            result, payloads, manifest = _build_result(
                deployment,
                request,
                numeric,
            )
            _verify_directory_binding(
                parent,
                parent_descriptor,
                "HC_PRE result parent",
            )
            _require_result_absent(parent_descriptor, output_name, output)
            _publish_result(
                output=output,
                parent=parent,
                parent_descriptor=parent_descriptor,
                output_name=output_name,
                payloads=payloads,
                manifest=manifest,
            )
            return result

    def close(self) -> None:
        """Deterministically release all deployment mappings."""

        if self._closed:
            return
        self.deployment.close()
        self._closed = True

    def __enter__(self) -> DeepSeekV4HCPreExecutableServiceEngine:
        if self._closed:
            raise DeepSeekV4HCPreExecutableServiceError(
                "HC_PRE executable service engine is closed"
            )
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()


def execute_deepseek_v4_hc_pre_executable_deployment(
    deployment_dir: Path,
    request_manifest: Path,
    result_dir: Path,
) -> HCPreExecutableResult:
    """Load the exact deployment, execute its program, and publish one result."""

    with DeepSeekV4HCPreExecutableServiceEngine.load(deployment_dir) as engine:
        return engine.execute(request_manifest, result_dir)


__all__ = [
    "EXECUTABLE_BUILD_ID",
    "EXECUTABLE_DEPLOYMENT_SCHEMA",
    "EXECUTION_REQUEST_SCHEMA",
    "EXECUTION_RESULT_SCHEMA",
    "HCPreExecutableArtifactRecord",
    "HCPreExecutableRequest",
    "HCPreExecutableResult",
    "MODEL_ID",
    "PROGRAM_CONTRACT_ID",
    "PROGRAM_SHA256",
    "SCHEDULE_CERTIFICATE_ID",
    "SCHEDULE_ID",
    "DeepSeekV4HCPreExecutableServiceError",
    "DeepSeekV4HCPreExecutableDeployment",
    "DeepSeekV4HCPreExecutableServiceEngine",
    "execute_deepseek_v4_hc_pre_executable_deployment",
    "load_deepseek_v4_hc_pre_executable_deployment",
]
