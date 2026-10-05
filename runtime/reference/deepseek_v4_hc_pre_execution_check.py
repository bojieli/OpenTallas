"""Independent locked-checkpoint differential for executable ``HC_PRE``.

This checker is intentionally outside the service-engine dependency graph.  It
opens the original official checkpoint, decodes the three learned F32 tensors,
and calls only :func:`runtime.reference.hyper_connection.hc_pre_bf16`.  The
executable deployment, source application, request, and result are treated as
hostile artifact trees: JSON must be canonical, paths are descriptor-relative,
symlinks and special files are rejected, reads are bounded, and every held
identity is rechecked after the reference transaction.

Passing this checker proves exact agreement for one persisted layer-0
attention ``HC_PRE`` transaction.  It does not prove a complete attention
operator, transformer block, model execution, physical schedule, RTL, PPA, or
comparison with another accelerator.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass, fields
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import stat
import struct
from typing import Any

from compiler.checking.deepseek_v4_hc_pre_executable import (
    DeepSeekV4HCPreExecutableCheckError,
    verify_deepseek_v4_hc_pre_executable_deployment,
)
from compiler.frontend.checkpoint import (
    CheckpointError,
    LockedCheckpointReader,
)
from compiler.frontend.deepseek_v4 import (
    DeepSeekV4AdapterError,
    OFFICIAL_CHECKPOINT_LOCK_ID,
    REPOSITORY,
    REVISION,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.ir.model import IRValidationError, canonical_json_bytes
from runtime.reference.hyper_connection import (
    HCPreReferenceError,
    hc_pre_bf16,
)


MODEL_ID = "deepseek-v4-flash-0731"
DIFFERENTIAL_SCHEMA = "opentallas.deepseek_v4_hc_pre_execution_differential.v1"
EXECUTABLE_DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_hc_pre_executable.v1"
REQUEST_SCHEMA = "opentallas.deepseek_v4_hc_pre_execution_request.v1"
RESULT_SCHEMA = "opentallas.deepseek_v4_hc_pre_execution_result.v1"
PROGRAM_SHA256 = "7811e26fae1162677a425795294e776caded0e6cd44383986bb34b9bf9c15739"
PARAMETER_BUILD_ID = "994815427eff455e780f8abf50a299896366dca0a5713778219ec43266aab3e2"
APPLICATION_ID = "195f060eafeefbe414eb30525618a42e765c882c39abdcd8885be644882734a1"
VERIFICATION_ID = "82c453a978017140b2c15fe2b782a7e04698ce55034376d169bfbb54a85dbbb4"

APPLICATION_MANIFEST = "canonical_application.json"
APPLICATION_VERIFICATION = "canonical_verification.json"
DEPLOYMENT_MANIFEST = "deployment_manifest.json"
REQUEST_MANIFEST = "request_manifest.json"
RESULT_MANIFEST = "result_manifest.json"

BASE_NAME = "layers.0.hc_attn_base"
PROJECTION_NAME = "layers.0.hc_attn_fn"
SCALE_NAME = "layers.0.hc_attn_scale"

_OFFICIAL_TENSORS: dict[str, tuple[str, tuple[int, ...], int, str]] = {
    BASE_NAME: (
        "F32",
        (24,),
        96,
        "edaa695cf5de59f919415f6e71dcb35be5ad817a06fa7222ee3021d9f388adda",
    ),
    PROJECTION_NAME: (
        "F32",
        (24, 16_384),
        1_572_864,
        "f5c1ffdfb92df2c04ac17e9a31e38701f2b7a5cac0cd427a2df2aa3e239987fc",
    ),
    SCALE_NAME: (
        "F32",
        (3,),
        12,
        "0b0e327d2f4d1a104c53d6e0a9172cf532028383e82cdf6d70537cb83092c63f",
    ),
}

_COUNTERS = frozenset(
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

_EXPECTED_DEPLOYMENT_ROLES = frozenset(
    {
        "execution_coverage",
        "execution_request_schema",
        "execution_result_schema",
        "hc_base_parameter",
        "hc_projection_parameter",
        "hc_scale_parameter",
        "logical_schedule",
        "logical_schedule_certificate",
        "microcode_disassembly",
        "microcode_program",
        "parameter_counter_contract",
        "parameter_deployment_manifest",
        "parameter_numeric_profile",
        "parameter_operator_coverage",
        "parameter_roundtrip_report",
        "parameter_semantic_ir",
        "parameter_tensor_manifest",
        "program_contract",
    }
)

_MAX_JSON_BYTES = 1024 * 1024
_MAX_MANIFEST_BYTES = 256 * 1024
_MAX_RESULT_PAYLOAD_BYTES = 4 * 4 * 4096 * 2
_MAX_TREE_ENTRIES = 96
_MAX_TREE_DEPTH = 8
_READ_CHUNK_BYTES = 1024 * 1024


class DeepSeekV4HCPreExecutionCheckError(RuntimeError):
    """Raised when a persisted HC_PRE result lacks exact source agreement."""


@dataclass(frozen=True)
class _StableFile:
    descriptor: int
    fingerprint: tuple[int, ...]
    relative_path: str
    root_descriptor: int
    size_bytes: int


@dataclass(frozen=True)
class _GuardedRoot:
    path: Path
    descriptor: int
    fingerprint: tuple[int, ...]
    label: str


@dataclass(frozen=True)
class _Deployment:
    root: _GuardedRoot
    manifest: _StableFile
    artifacts: tuple[_StableFile, ...]
    build_id: str
    parameter_build_id: str
    application_id: str
    verification_id: str


@dataclass(frozen=True)
class _Application:
    root: _GuardedRoot
    manifest: _StableFile
    verification: _StableFile
    assignments: tuple[_StableFile, ...]
    input_records: Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True)
class _Request:
    root: _GuardedRoot
    manifest_file: _StableFile
    input_file: _StableFile
    manifest_sha256: str
    input_sha256: str
    batch_size: int
    sequence_length: int
    token_count: int
    flat_input_codes: tuple[tuple[tuple[int, ...], ...], ...]


@dataclass(frozen=True)
class _PayloadSpec:
    identifier: str
    path: str
    dtype: str
    encoding: str
    shape_suffix: tuple[int, ...]
    bytes_per_token: int
    bits: int
    register: str | None


@dataclass(frozen=True)
class _ObservedPayload:
    spec: _PayloadSpec
    descriptor: Mapping[str, Any]
    file: _StableFile
    payload: bytes
    codes: tuple[int, ...]


@dataclass(frozen=True)
class _Result:
    root: _GuardedRoot
    manifest_file: _StableFile
    manifest_sha256: str
    payloads: Mapping[str, _ObservedPayload]
    logical_counters: Mapping[str, int]
    branch_saturation_count: int


_PAYLOAD_SPECS = (
    _PayloadSpec(
        "attention_input",
        "outputs/attention_input.bf16le",
        "BF16",
        "bfloat16_little_endian",
        (4096,),
        4096 * 2,
        16,
        "ATTENTION_INPUT",
    ),
    _PayloadSpec(
        "attention_pre",
        "outputs/attention_pre.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4,),
        4 * 4,
        32,
        "ATTENTION_PRE",
    ),
    _PayloadSpec(
        "attention_post",
        "outputs/attention_post.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4,),
        4 * 4,
        32,
        "ATTENTION_POST",
    ),
    _PayloadSpec(
        "attention_combination",
        "outputs/attention_combination.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4, 4),
        4 * 4 * 4,
        32,
        "ATTENTION_COMBINATION",
    ),
    _PayloadSpec(
        "attention_residual",
        "outputs/attention_residual.bf16le",
        "BF16",
        "bfloat16_little_endian",
        (4, 4096),
        4 * 4096 * 2,
        16,
        "ATTENTION_RESIDUAL",
    ),
    _PayloadSpec(
        "rms_mean_codes",
        "diagnostics/rms_mean.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (),
        4,
        32,
        None,
    ),
    _PayloadSpec(
        "rms_inverse_codes",
        "diagnostics/rms_inverse.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (),
        4,
        32,
        None,
    ),
    _PayloadSpec(
        "projection_codes",
        "diagnostics/projection.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (24,),
        24 * 4,
        32,
        None,
    ),
    _PayloadSpec(
        "mix_codes",
        "diagnostics/mix.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (24,),
        24 * 4,
        32,
        None,
    ),
    _PayloadSpec(
        "stable_softmax_codes",
        "diagnostics/stable_softmax.f32le",
        "F32",
        "ieee754_binary32_little_endian",
        (4, 4),
        4 * 4 * 4,
        32,
        None,
    ),
)
_SPECS_BY_ID = {spec.identifier: spec for spec in _PAYLOAD_SPECS}


def _canonical(value: object) -> bytes:
    try:
        return canonical_json_bytes(value)
    except (IRValidationError, TypeError, ValueError) as exc:
        raise DeepSeekV4HCPreExecutionCheckError(
            f"value is not canonical JSON: {exc}"
        ) from exc


def _json_equal(left: object, right: object) -> bool:
    try:
        return _canonical(left) == _canonical(right)
    except DeepSeekV4HCPreExecutionCheckError:
        return False


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise DeepSeekV4HCPreExecutionCheckError(
                    f"{label} has duplicate JSON key {key!r}"
                )
            value[key] = item
        return value

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                DeepSeekV4HCPreExecutionCheckError(
                    f"{label} has non-finite JSON number {token!r}"
                )
            ),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, DeepSeekV4HCPreExecutionCheckError):
            raise
        raise DeepSeekV4HCPreExecutionCheckError(
            f"cannot decode {label}: {exc}"
        ) from exc
    if type(value) is not dict:
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not a JSON object")
    if _canonical(value) != payload:
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not canonical JSON")
    return value


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not an object")
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4HCPreExecutionCheckError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
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
        raise DeepSeekV4HCPreExecutionCheckError(
            f"{label} is outside its exact integer bound"
        )
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not a lowercase SHA-256")
    return value


def _safe_relative(value: object, label: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not canonical POSIX")
    return value


def _fingerprint(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _require_secure_operations() -> None:
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_NONBLOCK")
        or not hasattr(os, "O_CLOEXEC")
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "pread")
        or os.open not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
        or os.unlink not in os.supports_dir_fd
        or os.link not in os.supports_dir_fd
    ):
        raise DeepSeekV4HCPreExecutionCheckError(
            "platform lacks descriptor-relative no-follow checker operations"
        )


def _open_root(stack: ExitStack, root: Path, label: str) -> _GuardedRoot:
    _require_secure_operations()
    path = Path(root).absolute()
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutionCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not a directory")
    return _GuardedRoot(path, descriptor, _fingerprint(metadata), label)


def _open_relative(root_descriptor: int, relative: str, label: str) -> int:
    parts = Path(_safe_relative(relative, label)).parts
    directory_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    current = os.dup(root_descriptor)
    try:
        for index, part in enumerate(parts):
            flags = file_flags if index == len(parts) - 1 else directory_flags
            following = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = following
        return current
    except OSError as exc:
        os.close(current)
        raise DeepSeekV4HCPreExecutionCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc


def _safe_file(
    stack: ExitStack,
    root: _GuardedRoot,
    relative: object,
    label: str,
    *,
    exact_size: int | None = None,
    maximum_size: int | None = None,
) -> _StableFile:
    path = _safe_relative(relative, label)
    descriptor = _open_relative(root.descriptor, path, label)
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not a regular file")
    if exact_size is not None and metadata.st_size != exact_size:
        raise DeepSeekV4HCPreExecutionCheckError(
            f"{label} has {metadata.st_size} bytes, expected {exact_size}"
        )
    if maximum_size is not None and metadata.st_size > maximum_size:
        raise DeepSeekV4HCPreExecutionCheckError(
            f"{label} exceeds its {maximum_size}-byte bound"
        )
    return _StableFile(
        descriptor,
        _fingerprint(metadata),
        path,
        root.descriptor,
        metadata.st_size,
    )


def _verify_file(source: _StableFile, label: str) -> None:
    if _fingerprint(os.fstat(source.descriptor)) != source.fingerprint:
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} changed while held")
    current = _open_relative(source.root_descriptor, source.relative_path, label)
    try:
        metadata = os.fstat(current)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or _fingerprint(metadata) != source.fingerprint
        ):
            raise DeepSeekV4HCPreExecutionCheckError(f"{label} was replaced")
    finally:
        os.close(current)


def _verify_root(root: _GuardedRoot) -> None:
    if _fingerprint(os.fstat(root.descriptor)) != root.fingerprint:
        raise DeepSeekV4HCPreExecutionCheckError(f"{root.label} changed while held")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current = os.open(root.path, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutionCheckError(
            f"cannot reopen {root.label}: {exc}"
        ) from exc
    try:
        if _fingerprint(os.fstat(current)) != root.fingerprint:
            raise DeepSeekV4HCPreExecutionCheckError(f"{root.label} was replaced")
    finally:
        os.close(current)


def _verify_root_binding(root: _GuardedRoot) -> None:
    """Verify path-to-descriptor identity while allowing intentional writes.

    Publication necessarily changes the parent directory's mtime, ctime, size,
    and sometimes link count.  Those fields remain appropriate for read-only
    artifact roots, but a mutable publication parent must be compared by its
    held device/inode/type identity instead.
    """

    held = os.fstat(root.descriptor)
    if not stat.S_ISDIR(held.st_mode):
        raise DeepSeekV4HCPreExecutionCheckError(
            f"held {root.label} is no longer a directory"
        )
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root.path, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreExecutionCheckError(
            f"cannot reopen {root.label} without following symlinks: {exc}"
        ) from exc
    try:
        current = os.fstat(current_descriptor)
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (
            held.st_dev,
            held.st_ino,
        ):
            raise DeepSeekV4HCPreExecutionCheckError(
                f"{root.label} was replaced during publication"
            )
    finally:
        os.close(current_descriptor)


def _read_bytes(source: _StableFile, label: str, maximum: int) -> bytes:
    if source.size_bytes > maximum:
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} exceeds its read bound")
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
            raise DeepSeekV4HCPreExecutionCheckError(
                f"cannot read {label}: {exc}"
            ) from exc
        if not chunk:
            break
        payload.extend(chunk)
        offset += len(chunk)
    if len(payload) != source.size_bytes:
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} ended during read")
    _verify_file(source, label)
    return bytes(payload)


def _hash_file(source: _StableFile, label: str) -> str:
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
            raise DeepSeekV4HCPreExecutionCheckError(
                f"cannot hash {label}: {exc}"
            ) from exc
        if not chunk:
            break
        digest.update(chunk)
        offset += len(chunk)
    if offset != source.size_bytes:
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} ended during hash")
    _verify_file(source, label)
    return digest.hexdigest()


def _json_file(
    stack: ExitStack,
    root: _GuardedRoot,
    relative: str,
    label: str,
    *,
    maximum: int = _MAX_JSON_BYTES,
) -> tuple[dict[str, Any], bytes, _StableFile]:
    source = _safe_file(
        stack,
        root,
        relative,
        label,
        maximum_size=maximum,
    )
    payload = _read_bytes(source, label, maximum)
    return _strict_json(payload, label), payload, source


def _enumerate_tree(root: _GuardedRoot) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    count = 0

    def walk(descriptor: int, prefix: str, depth: int) -> None:
        nonlocal count
        if depth > _MAX_TREE_DEPTH:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"{root.label} exceeds its tree-depth bound"
            )
        before = _fingerprint(os.fstat(descriptor))
        try:
            names = sorted(os.listdir(descriptor))
        except OSError as exc:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"cannot enumerate {root.label}: {exc}"
            ) from exc
        count += len(names)
        if count > _MAX_TREE_ENTRIES:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"{root.label} exceeds its tree-entry bound"
            )
        for name in names:
            if name in {"", ".", ".."} or "/" in name or "\x00" in name:
                raise DeepSeekV4HCPreExecutionCheckError(
                    f"{root.label} contains an unsafe entry"
                )
            relative = f"{prefix}/{name}" if prefix else name
            try:
                metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            except OSError as exc:
                raise DeepSeekV4HCPreExecutionCheckError(
                    f"cannot inspect {root.label} entry {relative!r}: {exc}"
                ) from exc
            if stat.S_ISREG(metadata.st_mode):
                files.add(relative)
            elif stat.S_ISDIR(metadata.st_mode):
                directories.add(relative)
                flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
                try:
                    child = os.open(name, flags, dir_fd=descriptor)
                except OSError as exc:
                    raise DeepSeekV4HCPreExecutionCheckError(
                        f"cannot open {root.label} directory {relative!r}: {exc}"
                    ) from exc
                try:
                    walk(child, relative, depth + 1)
                finally:
                    os.close(child)
            else:
                raise DeepSeekV4HCPreExecutionCheckError(
                    f"{root.label} entry {relative!r} is not regular"
                )
        if _fingerprint(os.fstat(descriptor)) != before:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"{root.label} changed during tree enumeration"
            )

    walk(root.descriptor, "", 0)
    return files, directories


def _directory_closure(paths: Sequence[str]) -> set[str]:
    directories: set[str] = set()
    for path in paths:
        parts = Path(path).parts[:-1]
        for length in range(1, len(parts) + 1):
            directories.add(Path(*parts[:length]).as_posix())
    return directories


def _load_deployment(
    stack: ExitStack,
    deployment_root: Path,
    application_root: Path,
) -> _Deployment:
    root = _open_root(stack, deployment_root, "HC_PRE executable deployment root")
    try:
        independent = verify_deepseek_v4_hc_pre_executable_deployment(
            root.path, Path(application_root).absolute()
        )
    except (DeepSeekV4HCPreExecutableCheckError, OSError, ValueError) as exc:
        raise DeepSeekV4HCPreExecutionCheckError(
            f"executable package identity verification failed: {exc}"
        ) from exc
    manifest, payload, manifest_file = _json_file(
        stack,
        root,
        DEPLOYMENT_MANIFEST,
        "HC_PRE executable deployment manifest",
        maximum=_MAX_MANIFEST_BYTES,
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
    build_id = _digest(manifest["build_id"], "deployment.build_id")
    body = {key: manifest[key] for key in manifest if key != "build_id"}
    if _sha256_json(body) != build_id:
        raise DeepSeekV4HCPreExecutionCheckError(
            "executable deployment build_id does not bind its body"
        )
    source = _exact_keys(
        manifest["source"],
        {
            "application_id",
            "application_status",
            "checkpoint_lock_id",
            "evidence_scope",
            "repository",
            "revision",
            "verification_id",
        },
        "deployment.source",
    )
    expected_identity = {
        "model_id": MODEL_ID,
        "parameter_build_id": PARAMETER_BUILD_ID,
        "program_sha256": PROGRAM_SHA256,
        "schema": EXECUTABLE_DEPLOYMENT_SCHEMA,
        "status": "program_packaged_execution_not_yet_evidenced",
    }
    if not _json_equal(
        {key: manifest[key] for key in expected_identity}, expected_identity
    ):
        raise DeepSeekV4HCPreExecutionCheckError(
            "executable deployment identity differs from the HC_PRE contract"
        )
    expected_source = {
        "application_id": APPLICATION_ID,
        "application_status": (
            "partial_official_transform_application_not_release_evidence"
        ),
        "checkpoint_lock_id": OFFICIAL_CHECKPOINT_LOCK_ID,
        "evidence_scope": "official_checkpoint",
        "repository": REPOSITORY,
        "revision": REVISION,
        "verification_id": VERIFICATION_ID,
    }
    if not _json_equal(source, expected_source):
        raise DeepSeekV4HCPreExecutionCheckError(
            "executable deployment source is not the pinned official application"
        )
    raw_artifacts = manifest["artifacts"]
    if type(raw_artifacts) is not list or len(raw_artifacts) != 18:
        raise DeepSeekV4HCPreExecutionCheckError(
            "executable deployment does not enumerate exactly 18 artifacts"
        )
    paths: list[str] = []
    roles: set[str] = set()
    guarded: list[_StableFile] = []
    for index, raw in enumerate(raw_artifacts):
        record = _exact_keys(
            raw,
            {"path", "role", "sha256", "size_bytes"},
            f"deployment.artifacts[{index}]",
        )
        path = _safe_relative(record["path"], f"deployment.artifacts[{index}].path")
        role = record["role"]
        if type(role) is not str or role not in _EXPECTED_DEPLOYMENT_ROLES:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"deployment artifact role {role!r} is outside the closed set"
            )
        if path in paths or role in roles:
            raise DeepSeekV4HCPreExecutionCheckError(
                "deployment artifact paths and roles must be unique"
            )
        paths.append(path)
        roles.add(role)
        digest = _digest(record["sha256"], f"deployment.artifacts[{index}].sha256")
        size = _integer(
            record["size_bytes"],
            f"deployment.artifacts[{index}].size_bytes",
            minimum=1,
            maximum=2 * 1024 * 1024,
        )
        source_file = _safe_file(
            stack,
            root,
            path,
            f"deployment artifact {path!r}",
            exact_size=size,
            maximum_size=2 * 1024 * 1024,
        )
        if _hash_file(source_file, f"deployment artifact {path!r}") != digest:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"deployment artifact {path!r} differs from its digest"
            )
        if role == "microcode_program" and digest != PROGRAM_SHA256:
            raise DeepSeekV4HCPreExecutionCheckError(
                "deployment microcode differs from the exact HC_PRE program"
            )
        guarded.append(source_file)
    if paths != sorted(paths) or roles != _EXPECTED_DEPLOYMENT_ROLES:
        raise DeepSeekV4HCPreExecutionCheckError(
            "deployment artifact ordering or role closure differs"
        )
    actual_files, actual_directories = _enumerate_tree(root)
    expected_files = set(paths) | {DEPLOYMENT_MANIFEST}
    if actual_files != expected_files or actual_directories != _directory_closure(
        tuple(expected_files)
    ):
        raise DeepSeekV4HCPreExecutionCheckError(
            "executable deployment tree closure differs"
        )
    if independent.get("build_id") != build_id:
        raise DeepSeekV4HCPreExecutionCheckError(
            "independent package checker returned a different build identity"
        )
    return _Deployment(
        root,
        manifest_file,
        tuple(guarded),
        build_id,
        PARAMETER_BUILD_ID,
        APPLICATION_ID,
        VERIFICATION_ID,
    )


def _load_application(
    stack: ExitStack,
    application_root: Path,
) -> _Application:
    root = _open_root(stack, application_root, "HC_PRE source application root")
    application, _, manifest_file = _json_file(
        stack, root, APPLICATION_MANIFEST, "HC_PRE canonical application"
    )
    verification, _, verification_file = _json_file(
        stack, root, APPLICATION_VERIFICATION, "HC_PRE canonical verification"
    )
    _exact_keys(
        application,
        {
            "application_id",
            "assignments",
            "coverage",
            "evidence_scope",
            "inputs",
            "plan",
            "schema",
            "selection",
            "source",
            "status",
        },
        "HC_PRE canonical application",
    )
    application_id = _digest(application["application_id"], "application_id")
    application_body = {
        key: application[key] for key in application if key != "application_id"
    }
    if (
        application_id != APPLICATION_ID
        or _sha256_json(application_body) != APPLICATION_ID
    ):
        raise DeepSeekV4HCPreExecutionCheckError(
            "canonical application identity differs"
        )
    source = _exact_keys(
        application["source"],
        {"checkpoint_lock_id", "repository", "revision"},
        "canonical application source",
    )
    expected_application_metadata = {
        "evidence_scope": "official_checkpoint",
        "schema": "opentallas.canonical_application.v1",
        "status": "partial_official_transform_application_not_release_evidence",
    }
    if not _json_equal(
        {key: application[key] for key in expected_application_metadata},
        expected_application_metadata,
    ) or not _json_equal(
        source,
        {
            "checkpoint_lock_id": OFFICIAL_CHECKPOINT_LOCK_ID,
            "repository": REPOSITORY,
            "revision": REVISION,
        },
    ):
        raise DeepSeekV4HCPreExecutionCheckError(
            "canonical application is not the pinned official source selection"
        )
    raw_inputs = application["inputs"]
    if type(raw_inputs) is not list or len(raw_inputs) != 3:
        raise DeepSeekV4HCPreExecutionCheckError(
            "canonical application must select exactly three HC_PRE tensors"
        )
    inputs: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(raw_inputs):
        record = _exact_keys(
            raw,
            {
                "action",
                "logical_dtype",
                "name",
                "payload_sha256",
                "shape",
                "size_bytes",
                "storage_dtype",
            },
            f"canonical inputs[{index}]",
        )
        name = record["name"]
        if type(name) is not str or name not in _OFFICIAL_TENSORS or name in inputs:
            raise DeepSeekV4HCPreExecutionCheckError(
                "canonical application input names differ"
            )
        dtype, shape, size, digest = _OFFICIAL_TENSORS[name]
        expected = {
            "action": "replicate_identity",
            "logical_dtype": "FP32",
            "name": name,
            "payload_sha256": digest,
            "shape": list(shape),
            "size_bytes": size,
            "storage_dtype": dtype,
        }
        if not _json_equal(record, expected):
            raise DeepSeekV4HCPreExecutionCheckError(
                f"canonical input {name!r} differs from official identity"
            )
        inputs[name] = record
    if set(inputs) != set(_OFFICIAL_TENSORS):
        raise DeepSeekV4HCPreExecutionCheckError(
            "canonical application input closure differs"
        )
    raw_assignments = application["assignments"]
    if type(raw_assignments) is not list or len(raw_assignments) != 12:
        raise DeepSeekV4HCPreExecutionCheckError(
            "canonical application must contain twelve rank assignments"
        )
    assignment_files: list[_StableFile] = []
    assignment_paths: list[str] = []
    for index, raw in enumerate(raw_assignments):
        assignment = _exact_keys(
            raw,
            {
                "logical_dtype",
                "name",
                "path",
                "payload_bytes",
                "rank",
                "scale_source",
                "sha256",
                "shape",
                "source",
                "storage_dtype",
                "transform",
            },
            f"canonical assignments[{index}]",
        )
        name = assignment["name"]
        if type(name) is not str or name not in _OFFICIAL_TENSORS:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"canonical assignment {index} tensor differs"
            )
        _, shape, size, digest = _OFFICIAL_TENSORS[name]
        rank = _integer(
            assignment["rank"], f"canonical assignments[{index}].rank", maximum=3
        )
        expected_path = f"ranks/rank-{rank:03d}/{name}.bin"
        if (
            assignment["path"] != expected_path
            or assignment["sha256"] != digest
            or assignment["payload_bytes"] != size
            or assignment["shape"] != list(shape)
            or assignment["storage_dtype"] != "F32"
            or assignment["logical_dtype"] != "FP32"
            or assignment["transform"] != "identity"
            or assignment["scale_source"] is not None
        ):
            raise DeepSeekV4HCPreExecutionCheckError(
                f"canonical assignment {index} metadata differs"
            )
        source_record = _exact_keys(
            assignment["source"],
            {"name", "payload_sha256", "shape", "slice", "storage_dtype"},
            f"canonical assignments[{index}].source",
        )
        if not _json_equal(
            source_record,
            {
                "name": name,
                "payload_sha256": digest,
                "shape": list(shape),
                "slice": None,
                "storage_dtype": "F32",
            },
        ):
            raise DeepSeekV4HCPreExecutionCheckError(
                f"canonical assignment {index} source differs"
            )
        source_file = _safe_file(
            stack,
            root,
            expected_path,
            f"canonical assignment payload {expected_path!r}",
            exact_size=size,
            maximum_size=1_572_864,
        )
        if _hash_file(source_file, f"canonical assignment {expected_path!r}") != digest:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"canonical assignment payload {expected_path!r} differs"
            )
        assignment_files.append(source_file)
        assignment_paths.append(expected_path)
    if len(set(assignment_paths)) != 12:
        raise DeepSeekV4HCPreExecutionCheckError(
            "canonical assignment path closure differs"
        )
    _exact_keys(
        verification,
        {
            "application_id",
            "checkpoint_lock_id",
            "checks",
            "coverage",
            "schema",
            "status",
            "verification_id",
        },
        "HC_PRE canonical verification",
    )
    verification_id = _digest(verification["verification_id"], "verification_id")
    verification_body = {
        key: verification[key] for key in verification if key != "verification_id"
    }
    if (
        verification_id != VERIFICATION_ID
        or _sha256_json(verification_body) != VERIFICATION_ID
        or verification["application_id"] != APPLICATION_ID
        or verification["checkpoint_lock_id"] != OFFICIAL_CHECKPOINT_LOCK_ID
        or verification["schema"] != "opentallas.canonical_application_check.v1"
        or verification["status"] != "full_assignment_match"
    ):
        raise DeepSeekV4HCPreExecutionCheckError(
            "canonical verification identity differs"
        )
    expected_files = {
        APPLICATION_MANIFEST,
        APPLICATION_VERIFICATION,
        *assignment_paths,
    }
    files_observed, directories_observed = _enumerate_tree(root)
    if files_observed != expected_files or directories_observed != _directory_closure(
        tuple(expected_files)
    ):
        raise DeepSeekV4HCPreExecutionCheckError(
            "canonical application tree closure differs"
        )
    return _Application(
        root,
        manifest_file,
        verification_file,
        tuple(assignment_files),
        inputs,
    )


class _BoundedCollector:
    def __init__(self, exact_size: int, label: str):
        self._exact_size = exact_size
        self._label = label
        self._payload = bytearray()

    def consume(self, chunk: bytes) -> None:
        if len(self._payload) + len(chunk) > self._exact_size:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"{self._label} exceeds its locked size"
            )
        self._payload.extend(chunk)

    def finish(self) -> bytes:
        if len(self._payload) != self._exact_size:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"{self._label} ended before its locked size"
            )
        return bytes(self._payload)


def _decode_f32(payload: bytes, expected_count: int, label: str) -> tuple[int, ...]:
    if type(payload) is not bytes or len(payload) != expected_count * 4:
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} byte count differs")
    codes = tuple(code for (code,) in struct.iter_unpack("<I", payload))
    for index, code in enumerate(codes):
        if code & 0x7F800000 == 0x7F800000:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"{label} contains non-finite F32 at element {index}"
            )
    return codes


def _load_checkpoint_parameters(
    snapshot: Path,
    lock: dict[str, Any],
    application: _Application,
) -> tuple[
    tuple[tuple[int, ...], ...],
    tuple[int, ...],
    tuple[int, ...],
    list[dict[str, Any]],
]:
    try:
        validate_official_checkpoint_lock(lock, load_official_config())
    except (CheckpointError, DeepSeekV4AdapterError, OSError, ValueError) as exc:
        raise DeepSeekV4HCPreExecutionCheckError(
            f"checkpoint lock is not the pinned official release: {exc}"
        ) from exc
    collectors = {
        name: _BoundedCollector(spec[2], f"locked tensor {name!r}")
        for name, spec in _OFFICIAL_TENSORS.items()
    }
    records: dict[str, dict[str, Any]] = {}
    try:
        with LockedCheckpointReader(snapshot, lock) as reader:
            for name in (BASE_NAME, PROJECTION_NAME, SCALE_NAME):
                records[name] = reader.consume_tensor_payload(
                    name, collectors[name].consume, chunk_bytes=_READ_CHUNK_BYTES
                )
    except (CheckpointError, OSError, ValueError) as exc:
        raise DeepSeekV4HCPreExecutionCheckError(
            f"cannot read original locked HC_PRE tensors: {exc}"
        ) from exc
    payloads: dict[str, bytes] = {}
    source_records: list[dict[str, Any]] = []
    for name in (BASE_NAME, PROJECTION_NAME, SCALE_NAME):
        dtype, shape, size, digest = _OFFICIAL_TENSORS[name]
        record = records[name]
        expected_record = {
            "dtype": dtype,
            "name": name,
            "payload_sha256": digest,
            "shape": list(shape),
            "shard": "model-00002-of-00048.safetensors",
            "size_bytes": size,
        }
        if not _json_equal(record, expected_record):
            raise DeepSeekV4HCPreExecutionCheckError(
                f"locked tensor identity differs for {name!r}"
            )
        application_record = application.input_records[name]
        if (
            application_record["payload_sha256"] != record["payload_sha256"]
            or application_record["shape"] != record["shape"]
            or application_record["size_bytes"] != record["size_bytes"]
            or application_record["storage_dtype"] != record["dtype"]
        ):
            raise DeepSeekV4HCPreExecutionCheckError(
                f"source application and locked tensor differ for {name!r}"
            )
        payload = collectors[name].finish()
        if hashlib.sha256(payload).hexdigest() != digest:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"locked tensor bytes differ for {name!r}"
            )
        payloads[name] = payload
        source_records.append(
            {
                "dtype": dtype,
                "name": name,
                "payload_sha256": digest,
                "shape": list(shape),
                "size_bytes": size,
            }
        )
    base = _decode_f32(payloads[BASE_NAME], 24, "locked HC_PRE base")
    flat_projection = _decode_f32(
        payloads[PROJECTION_NAME], 24 * 16_384, "locked HC_PRE projection"
    )
    projection = tuple(
        flat_projection[row * 16_384 : (row + 1) * 16_384] for row in range(24)
    )
    scale = _decode_f32(payloads[SCALE_NAME], 3, "locked HC_PRE scale")
    return projection, scale, base, source_records


def _decode_codes(payload: bytes, bits: int, label: str) -> tuple[int, ...]:
    if bits == 16:
        if len(payload) % 2:
            raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not BF16 aligned")
        codes = tuple(code for (code,) in struct.iter_unpack("<H", payload))
        mask = 0x7F80
    elif bits == 32:
        if len(payload) % 4:
            raise DeepSeekV4HCPreExecutionCheckError(f"{label} is not F32 aligned")
        codes = tuple(code for (code,) in struct.iter_unpack("<I", payload))
        mask = 0x7F800000
    else:  # pragma: no cover - frozen internal table
        raise RuntimeError("unsupported code width")
    for index, code in enumerate(codes):
        if code & mask == mask:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"{label} contains non-finite data at element {index}"
            )
    return codes


def _reshape_input(
    flat: tuple[int, ...], batch_size: int, sequence_length: int
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    tokens: list[tuple[tuple[int, ...], ...]] = []
    offset = 0
    for _ in range(batch_size * sequence_length):
        streams: list[tuple[int, ...]] = []
        for _ in range(4):
            streams.append(tuple(flat[offset : offset + 4096]))
            offset += 4096
        tokens.append(tuple(streams))
    if offset != len(flat):  # pragma: no cover - exact size invariant
        raise DeepSeekV4HCPreExecutionCheckError(
            "request input decoder did not consume its payload"
        )
    return tuple(tokens)


def _load_request(
    stack: ExitStack,
    request_root: Path,
    build_id: str,
) -> _Request:
    root = _open_root(stack, request_root, "HC_PRE request root")
    request, payload, manifest_file = _json_file(
        stack, root, REQUEST_MANIFEST, "HC_PRE request manifest"
    )
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
        raise DeepSeekV4HCPreExecutionCheckError(
            "request batch_size*sequence_length differs from token_count"
        )
    expected_identity = {
        "build_id": build_id,
        "model_id": MODEL_ID,
        "program_sha256": PROGRAM_SHA256,
        "schema": REQUEST_SCHEMA,
    }
    if not _json_equal(
        {key: request[key] for key in expected_identity}, expected_identity
    ):
        raise DeepSeekV4HCPreExecutionCheckError(
            "request build, model, program, or schema identity differs"
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
        "request input descriptor",
    )
    size_bytes = token_count * 4 * 4096 * 2
    input_sha256 = _digest(descriptor["sha256"], "request.input.sha256")
    expected_descriptor = {
        "dtype": "BF16",
        "encoding": "bfloat16_little_endian",
        "id": "hc_hidden",
        "path": "input/hc_hidden.bf16le",
        "register": "HC_HIDDEN",
        "sha256": input_sha256,
        "shape": [batch_size, sequence_length, 4, 4096],
        "size_bytes": size_bytes,
    }
    if not _json_equal(descriptor, expected_descriptor):
        raise DeepSeekV4HCPreExecutionCheckError("request input descriptor differs")
    input_file = _safe_file(
        stack,
        root,
        descriptor["path"],
        "HC_PRE request input",
        exact_size=size_bytes,
        maximum_size=_MAX_RESULT_PAYLOAD_BYTES,
    )
    input_payload = _read_bytes(
        input_file, "HC_PRE request input", _MAX_RESULT_PAYLOAD_BYTES
    )
    if hashlib.sha256(input_payload).hexdigest() != input_sha256:
        raise DeepSeekV4HCPreExecutionCheckError(
            "request input payload differs from its hash"
        )
    flat = _decode_codes(input_payload, 16, "HC_PRE request input")
    actual_files, actual_directories = _enumerate_tree(root)
    expected_files = {REQUEST_MANIFEST, "input/hc_hidden.bf16le"}
    if actual_files != expected_files or actual_directories != _directory_closure(
        tuple(expected_files)
    ):
        raise DeepSeekV4HCPreExecutionCheckError("request tree closure differs")
    return _Request(
        root,
        manifest_file,
        input_file,
        hashlib.sha256(payload).hexdigest(),
        input_sha256,
        batch_size,
        sequence_length,
        token_count,
        _reshape_input(flat, batch_size, sequence_length),
    )


def _payload_descriptor(
    value: object,
    spec: _PayloadSpec,
    *,
    batch_size: int,
    sequence_length: int,
    label: str,
) -> dict[str, Any]:
    expected_keys = {"dtype", "encoding", "id", "path", "sha256", "shape", "size_bytes"}
    if spec.register is not None:
        expected_keys.add("register")
    descriptor = _exact_keys(value, expected_keys, label)
    digest = _digest(descriptor["sha256"], f"{label}.sha256")
    expected: dict[str, Any] = {
        "dtype": spec.dtype,
        "encoding": spec.encoding,
        "id": spec.identifier,
        "path": spec.path,
        "sha256": digest,
        "shape": [batch_size, sequence_length, *spec.shape_suffix],
        "size_bytes": batch_size * sequence_length * spec.bytes_per_token,
    }
    if spec.register is not None:
        expected["register"] = spec.register
    if not _json_equal(descriptor, expected):
        raise DeepSeekV4HCPreExecutionCheckError(f"{label} metadata differs")
    return descriptor


def _load_result(
    stack: ExitStack,
    result_root: Path,
    deployment: _Deployment,
    request: _Request,
) -> _Result:
    root = _open_root(stack, result_root, "HC_PRE result root")
    result, manifest_payload, manifest_file = _json_file(
        stack, root, RESULT_MANIFEST, "HC_PRE result manifest"
    )
    _exact_keys(
        result,
        {
            "batch_size",
            "build_id",
            "counter_reconciliation",
            "deployment_status",
            "diagnostics",
            "evidence_scope",
            "execution_scope",
            "logical_counters",
            "model_id",
            "numeric_status",
            "outputs",
            "program_sha256",
            "request_sha256",
            "schema",
            "sequence_length",
            "source_application_status",
            "status",
            "token_count",
        },
        "HC_PRE result manifest",
    )
    expected_identity = {
        "batch_size": request.batch_size,
        "build_id": deployment.build_id,
        "counter_reconciliation": "exact",
        "deployment_status": (
            "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
        ),
        "evidence_scope": "official_checkpoint",
        "execution_scope": "exact_hc_pre_site_only",
        "model_id": MODEL_ID,
        "program_sha256": PROGRAM_SHA256,
        "request_sha256": request.manifest_sha256,
        "schema": RESULT_SCHEMA,
        "sequence_length": request.sequence_length,
        "source_application_status": (
            "partial_official_transform_application_not_release_evidence"
        ),
        "status": "pass",
        "token_count": request.token_count,
    }
    if not _json_equal(
        {key: result[key] for key in expected_identity}, expected_identity
    ):
        raise DeepSeekV4HCPreExecutionCheckError(
            "result transaction, source, build, or program identity differs"
        )
    raw_outputs = result["outputs"]
    output_specs = _PAYLOAD_SPECS[:5]
    if type(raw_outputs) is not list or len(raw_outputs) != len(output_specs):
        raise DeepSeekV4HCPreExecutionCheckError(
            "result must contain exactly five ordered outputs"
        )
    diagnostics = _exact_keys(
        result["diagnostics"],
        {
            "mix_codes",
            "projection_codes",
            "rms_inverse_codes",
            "rms_mean_codes",
            "stable_softmax_codes",
        },
        "result diagnostics",
    )
    descriptor_values = list(zip(output_specs, raw_outputs, strict=True))
    descriptor_values.extend(
        (spec, diagnostics[spec.identifier]) for spec in _PAYLOAD_SPECS[5:]
    )
    observed: dict[str, _ObservedPayload] = {}
    for spec, raw_descriptor in descriptor_values:
        descriptor = _payload_descriptor(
            raw_descriptor,
            spec,
            batch_size=request.batch_size,
            sequence_length=request.sequence_length,
            label=f"result payload {spec.identifier!r}",
        )
        source = _safe_file(
            stack,
            root,
            spec.path,
            f"result payload {spec.identifier!r}",
            exact_size=descriptor["size_bytes"],
            maximum_size=_MAX_RESULT_PAYLOAD_BYTES,
        )
        payload = _read_bytes(
            source,
            f"result payload {spec.identifier!r}",
            _MAX_RESULT_PAYLOAD_BYTES,
        )
        if hashlib.sha256(payload).hexdigest() != descriptor["sha256"]:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"result payload {spec.identifier!r} differs from its hash"
            )
        codes = _decode_codes(payload, spec.bits, f"result payload {spec.identifier!r}")
        expected_elements = math.prod(descriptor["shape"])
        if len(codes) != expected_elements:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"result payload {spec.identifier!r} element count differs"
            )
        observed[spec.identifier] = _ObservedPayload(
            spec, descriptor, source, payload, codes
        )
    numeric = _exact_keys(
        result["numeric_status"],
        {"branch_saturation_count", "poison"},
        "result numeric_status",
    )
    saturation = _integer(
        numeric["branch_saturation_count"],
        "result.numeric_status.branch_saturation_count",
        maximum=request.token_count * 4096,
    )
    if type(numeric["poison"]) is not bool or numeric["poison"] is not False:
        raise DeepSeekV4HCPreExecutionCheckError(
            "committed result numeric_status.poison must be exactly false"
        )
    raw_counters = _exact_keys(
        result["logical_counters"], set(_COUNTERS), "result logical_counters"
    )
    counters = {
        name: _integer(raw_counters[name], f"result.logical_counters.{name}")
        for name in sorted(_COUNTERS)
    }
    expected_files = {RESULT_MANIFEST, *(spec.path for spec in _PAYLOAD_SPECS)}
    actual_files, actual_directories = _enumerate_tree(root)
    if actual_files != expected_files or actual_directories != _directory_closure(
        tuple(expected_files)
    ):
        raise DeepSeekV4HCPreExecutionCheckError("result tree closure differs")
    return _Result(
        root,
        manifest_file,
        hashlib.sha256(manifest_payload).hexdigest(),
        observed,
        counters,
        saturation,
    )


def _flatten_codes(value: object, label: str) -> tuple[int, ...]:
    flattened: list[int] = []

    def visit(item: object) -> None:
        if type(item) is int:
            flattened.append(item)
            return
        if isinstance(item, (str, bytes, bytearray)) or not isinstance(item, Sequence):
            raise DeepSeekV4HCPreExecutionCheckError(
                f"independent reference {label} is malformed"
            )
        for child in item:
            visit(child)

    visit(value)
    return tuple(flattened)


def _encode_codes(codes: tuple[int, ...], bits: int, label: str) -> bytes:
    maximum = (1 << bits) - 1
    if any(type(code) is not int or not 0 <= code <= maximum for code in codes):
        raise DeepSeekV4HCPreExecutionCheckError(
            f"independent reference {label} contains an invalid code"
        )
    if bits == 16:
        encoder = struct.Struct("<H")
    elif bits == 32:
        encoder = struct.Struct("<I")
    else:  # pragma: no cover - frozen internal table
        raise RuntimeError("unsupported code width")
    return b"".join(encoder.pack(code) for code in codes)


def _expected_payloads(reference: object) -> dict[str, object]:
    # Attribute names are deliberately spelled out: a future reference result
    # extension cannot silently enter the persisted differential contract.
    return {
        "attention_input": reference.branch_bf16_codes,
        "attention_pre": reference.pre_binary32_codes,
        "attention_post": reference.post_binary32_codes,
        "attention_combination": reference.comb_binary32_codes,
        "attention_residual": reference.residual_bf16_codes,
        "rms_mean_codes": reference.diagnostics.mean_square_codes,
        "rms_inverse_codes": reference.diagnostics.inverse_rms_codes,
        "projection_codes": reference.diagnostics.projection_codes,
        "mix_codes": reference.diagnostics.normalized_projection_codes,
        "stable_softmax_codes": reference.diagnostics.split.softmax_codes,
    }


def _verify_guarded_inputs(
    deployment: _Deployment,
    application: _Application,
    request: _Request,
    result: _Result,
) -> None:
    for label, source in (
        ("deployment manifest", deployment.manifest),
        *(("deployment artifact", item) for item in deployment.artifacts),
        ("application manifest", application.manifest),
        ("application verification", application.verification),
        *(("application assignment", item) for item in application.assignments),
        ("request manifest", request.manifest_file),
        ("request input", request.input_file),
        ("result manifest", result.manifest_file),
        *(("result payload", item.file) for item in result.payloads.values()),
    ):
        _verify_file(source, f"guarded {label} {source.relative_path!r}")
    expected_trees = {
        deployment.root.path: (
            {
                DEPLOYMENT_MANIFEST,
                *(item.relative_path for item in deployment.artifacts),
            },
            _directory_closure(
                tuple(
                    {
                        DEPLOYMENT_MANIFEST,
                        *(item.relative_path for item in deployment.artifacts),
                    }
                )
            ),
        ),
        application.root.path: (
            {
                APPLICATION_MANIFEST,
                APPLICATION_VERIFICATION,
                *(item.relative_path for item in application.assignments),
            },
            _directory_closure(
                tuple(
                    {
                        APPLICATION_MANIFEST,
                        APPLICATION_VERIFICATION,
                        *(item.relative_path for item in application.assignments),
                    }
                )
            ),
        ),
        request.root.path: (
            {REQUEST_MANIFEST, request.input_file.relative_path},
            _directory_closure((REQUEST_MANIFEST, request.input_file.relative_path)),
        ),
        result.root.path: (
            {
                RESULT_MANIFEST,
                *(item.file.relative_path for item in result.payloads.values()),
            },
            _directory_closure(
                tuple(
                    {
                        RESULT_MANIFEST,
                        *(item.file.relative_path for item in result.payloads.values()),
                    }
                )
            ),
        ),
    }
    for root in (deployment.root, application.root, request.root, result.root):
        _verify_root(root)
        # A second closed-tree walk catches nested directory insertion or
        # replacement even when the root directory entry itself is unchanged.
        if _enumerate_tree(root) != expected_trees[root.path]:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"{root.label} tree changed during independent execution checking"
            )


def _unlink_report_name_if_owned(
    parent_descriptor: int,
    name: str,
    expected_identity: tuple[int, int],
) -> bool:
    """Remove one report name only while it still names our regular file.

    The report parent is caller-trusted, but late publication failures must not
    blindly delete a path another actor replaced.  Descriptor-relative,
    no-follow inspection narrows cleanup to the inode created by this call.
    """

    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    except FileNotFoundError:
        return False
    metadata = os.fstat(descriptor)
    os.close(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or (
            metadata.st_dev,
            metadata.st_ino,
        )
        != expected_identity
    ):
        return False
    try:
        os.unlink(name, dir_fd=parent_descriptor)
    except FileNotFoundError:
        return False
    return True


def _publish_report(report_path: Path, payload: bytes) -> None:
    if type(payload) is not bytes:
        raise DeepSeekV4HCPreExecutionCheckError("report payload is not exact bytes")
    raw = Path(report_path)
    if not raw.name or raw.name in {".", ".."} or "/" in raw.name or "\x00" in raw.name:
        raise DeepSeekV4HCPreExecutionCheckError(
            "report_path must name one specific file"
        )
    path = raw.absolute()
    with ExitStack() as stack:
        parent = _open_root(stack, path.parent, "HC_PRE differential report parent")
        if os.path.lexists(path):
            raise DeepSeekV4HCPreExecutionCheckError(
                f"differential report already exists: {path}"
            )
        descriptor: int | None = None
        temporary_name: str | None = None
        private_identity: tuple[int, int] | None = None
        linked = False
        committed = False
        try:
            for _ in range(128):
                candidate = f".hc-pre-differential.tmp-{secrets.token_hex(16)}"
                try:
                    descriptor = os.open(
                        candidate,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | os.O_CLOEXEC
                        | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=parent.descriptor,
                    )
                    temporary_name = candidate
                    break
                except FileExistsError:
                    continue
                except OSError as exc:
                    raise DeepSeekV4HCPreExecutionCheckError(
                        f"cannot create private differential report: {exc}"
                    ) from exc
            if descriptor is None or temporary_name is None:
                raise DeepSeekV4HCPreExecutionCheckError(
                    "cannot reserve private differential report"
                )
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                if written <= 0:
                    raise DeepSeekV4HCPreExecutionCheckError(
                        "short write while publishing differential report"
                    )
                offset += written
            os.fsync(descriptor)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != len(payload):
                raise DeepSeekV4HCPreExecutionCheckError(
                    "private differential report identity differs"
                )
            private_identity = (metadata.st_dev, metadata.st_ino)
            _verify_root_binding(parent)
            try:
                os.link(
                    temporary_name,
                    path.name,
                    src_dir_fd=parent.descriptor,
                    dst_dir_fd=parent.descriptor,
                    follow_symlinks=False,
                )
            except FileExistsError as exc:
                raise DeepSeekV4HCPreExecutionCheckError(
                    f"differential report already exists: {path}"
                ) from exc
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    raise DeepSeekV4HCPreExecutionCheckError(
                        f"differential report already exists: {path}"
                    ) from exc
                raise DeepSeekV4HCPreExecutionCheckError(
                    f"cannot atomically publish differential report: {exc}"
                ) from exc
            linked = True
            os.fsync(parent.descriptor)
            published = _open_relative(parent.descriptor, path.name, "published report")
            try:
                published_metadata = os.fstat(published)
                if not stat.S_ISREG(published_metadata.st_mode) or (
                    published_metadata.st_dev,
                    published_metadata.st_ino,
                ) != (metadata.st_dev, metadata.st_ino):
                    raise DeepSeekV4HCPreExecutionCheckError(
                        "published differential report was replaced"
                    )
            finally:
                os.close(published)
            _verify_root_binding(parent)
            committed = True
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if linked and not committed:
                try:
                    if private_identity is not None and _unlink_report_name_if_owned(
                        parent.descriptor,
                        path.name,
                        private_identity,
                    ):
                        os.fsync(parent.descriptor)
                except OSError:
                    # The caller-trusted parent has already violated its
                    # publication boundary. Preserve the original failure.
                    pass
            if temporary_name is not None:
                try:
                    if private_identity is not None and _unlink_report_name_if_owned(
                        parent.descriptor,
                        temporary_name,
                        private_identity,
                    ):
                        os.fsync(parent.descriptor)
                except OSError as exc:
                    if not linked:
                        raise DeepSeekV4HCPreExecutionCheckError(
                            f"cannot remove private differential report: {exc}"
                        ) from exc


def verify_deepseek_v4_hc_pre_execution(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    deployment_root: Path,
    request_root: Path,
    result_root: Path,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Verify and optionally create-once publish one exact HC_PRE differential."""

    with ExitStack() as stack:
        deployment = _load_deployment(stack, deployment_root, application_root)
        application = _load_application(stack, application_root)
        if (
            deployment.application_id != APPLICATION_ID
            or deployment.verification_id != VERIFICATION_ID
        ):
            raise DeepSeekV4HCPreExecutionCheckError(
                "deployment and source application identities differ"
            )
        request = _load_request(stack, request_root, deployment.build_id)
        result = _load_result(stack, result_root, deployment, request)
        projection, scale, base, source_tensors = _load_checkpoint_parameters(
            snapshot, lock, application
        )
        try:
            reference = hc_pre_bf16(
                request.flat_input_codes,
                projection,
                scale,
                base,
            )
        except HCPreReferenceError as exc:
            raise DeepSeekV4HCPreExecutionCheckError(
                f"independent HC_PRE reference rejected the transaction: {exc}"
            ) from exc

        reference_counter_fields = {
            field.name: getattr(reference.counters, field.name)
            for field in fields(reference.counters)
        }
        reference_token_count = reference_counter_fields.pop("hc_pre_token_count", None)
        if (
            type(reference_token_count) is not int
            or reference_token_count != request.token_count
            or reference_token_count != request.batch_size * request.sequence_length
            or reference_token_count
            != _integer(
                request.token_count,
                "request token_count reconciliation",
                minimum=1,
                maximum=4,
            )
        ):
            raise DeepSeekV4HCPreExecutionCheckError(
                "reference hc_pre_token_count does not reconcile with B*S and root token_count"
            )
        if set(reference_counter_fields) != _COUNTERS:
            raise DeepSeekV4HCPreExecutionCheckError(
                "independent reference counter contract differs from the 27 persisted counters"
            )
        if not _json_equal(reference_counter_fields, result.logical_counters):
            raise DeepSeekV4HCPreExecutionCheckError(
                "result logical counters differ from independent accounting"
            )
        if (
            reference.branch_output_saturation_count != result.branch_saturation_count
            or reference_counter_fields["hc_pre_branch_bf16_saturations"]
            != result.branch_saturation_count
        ):
            raise DeepSeekV4HCPreExecutionCheckError(
                "result branch saturation count differs from independent arithmetic"
            )

        expected_values = _expected_payloads(reference)
        comparisons: list[dict[str, Any]] = []
        for spec in _PAYLOAD_SPECS:
            expected_codes = _flatten_codes(
                expected_values[spec.identifier], spec.identifier
            )
            observed = result.payloads[spec.identifier]
            if expected_codes != observed.codes:
                raise DeepSeekV4HCPreExecutionCheckError(
                    f"result payload {spec.identifier!r} differs from locked-checkpoint semantics"
                )
            expected_payload = _encode_codes(expected_codes, spec.bits, spec.identifier)
            if expected_payload != observed.payload:
                raise DeepSeekV4HCPreExecutionCheckError(
                    f"result payload {spec.identifier!r} byte encoding differs"
                )
            expected_sha256 = hashlib.sha256(expected_payload).hexdigest()
            if expected_sha256 != observed.descriptor["sha256"]:
                raise DeepSeekV4HCPreExecutionCheckError(
                    f"result payload {spec.identifier!r} descriptor hash differs"
                )
            comparisons.append(
                {
                    "element_count": len(expected_codes),
                    "expected_sha256": expected_sha256,
                    "observed_sha256": hashlib.sha256(observed.payload).hexdigest(),
                    "payload": spec.identifier,
                    "shape": observed.descriptor["shape"],
                    "status": "exact",
                }
            )

        _verify_guarded_inputs(deployment, application, request, result)
        report: dict[str, Any] = {
            "application_id": APPLICATION_ID,
            "batch_size": request.batch_size,
            "branch_saturation_count": result.branch_saturation_count,
            "build_id": deployment.build_id,
            "checkpoint_lock_id": OFFICIAL_CHECKPOINT_LOCK_ID,
            "claim_boundary": (
                "Exact locked-checkpoint differential for one layer-0 attention HC_PRE "
                "transaction only; not complete attention, a transformer block, full-model "
                "execution, RTL, physical timing, PPA, or accelerator comparison."
            ),
            "comparisons": comparisons,
            "input_sha256": request.input_sha256,
            "logical_counters": dict(sorted(result.logical_counters.items())),
            "model_id": MODEL_ID,
            "parameter_build_id": deployment.parameter_build_id,
            "program_sha256": PROGRAM_SHA256,
            "request_sha256": request.manifest_sha256,
            "result_manifest_sha256": result.manifest_sha256,
            "schema": DIFFERENTIAL_SCHEMA,
            "sequence_length": request.sequence_length,
            "source_tensors": source_tensors,
            "status": "exact_locked_checkpoint_hc_pre_differential",
            "token_count": request.token_count,
            "verification_id": VERIFICATION_ID,
        }
        report["differential_id"] = _sha256_json(report)
        if report_path is not None:
            _publish_report(Path(report_path), _canonical(report))
        return report


__all__ = [
    "DIFFERENTIAL_SCHEMA",
    "PROGRAM_SHA256",
    "DeepSeekV4HCPreExecutionCheckError",
    "verify_deepseek_v4_hc_pre_execution",
]
