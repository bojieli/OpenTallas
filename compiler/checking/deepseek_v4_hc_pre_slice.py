"""Independent hash and source roundtrip checks for an HC_PRE package.

The checker intentionally duplicates the frozen metadata and tensor contract;
it does not import the compiler builder or either runtime numeric lane.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
from typing import Any

from compiler.checking.deepseek_v4_application import (
    MANIFEST_FILENAME,
    VERIFICATION_FILENAME,
)
from compiler.ir.model import canonical_json_bytes


ROUNDTRIP_SCHEMA = "opentallas.deepseek_v4_hc_pre_roundtrip.v1"
DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_hc_pre_deployment.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_hc_pre_semantic.v1"
TENSOR_SCHEMA = "opentallas.deepseek_v4_hc_pre_tensors.v1"
NUMERIC_PROFILE_SCHEMA = "opentallas.deepseek_v4_hc_pre_numeric_profile.v1"
COUNTER_CONTRACT_SCHEMA = "opentallas.deepseek_v4_hc_pre_counter_contract.v1"
COVERAGE_SCHEMA = "opentallas.deepseek_v4_hc_pre_coverage.v1"
NUMERIC_PROFILE_ID = "opentallas.deepseek_v4_hc_pre_numeric.v1"
MODEL_ID = "deepseek-v4-flash-0731"
OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
OFFICIAL_CANONICAL_PLAN_ID = (
    "7b87ee6168e13cf9be7c5e812a13490b6f264bda78a96ceb2e7c02580c49b3a7"
)
OFFICIAL_CANONICAL_PLAN_SCHEMA = "opentallas.deepseek_v4_canonical_plan.v1"
OFFICIAL_CANONICAL_INPUT_COUNT = 72_317

BASE_NAME = "layers.0.hc_attn_base"
PROJECTION_NAME = "layers.0.hc_attn_fn"
SCALE_NAME = "layers.0.hc_attn_scale"
MODEL_PARALLEL = 4
HIDDEN_SIZE = 4096
FLATTENED_WIDTH = 16384
MIX_FIELD_COUNT = 24
NORM_EPSILON_BINARY32 = 0x358637BD
HC_EPSILON_BINARY32 = 0x358637BD

BASE_SHAPE = [24]
PROJECTION_SHAPE = [24, 16384]
SCALE_SHAPE = [3]
BASE_BYTES = 96
PROJECTION_BYTES = 1_572_864
SCALE_BYTES = 12
TOTAL_PARAMETER_BYTES = 1_572_972

MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
KERNEL_SOURCE_SHA256 = (
    "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
)

_RESOURCES = (
    ("base", BASE_NAME, BASE_SHAPE, BASE_BYTES),
    ("projection", PROJECTION_NAME, PROJECTION_SHAPE, PROJECTION_BYTES),
    ("scale", SCALE_NAME, SCALE_SHAPE, SCALE_BYTES),
)
_EXPECTED_NAMES = frozenset(record[1] for record in _RESOURCES)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_READ_CHUNK_BYTES = 8 * 1024 * 1024
_MAX_JSON_BYTES = 1024 * 1024


class DeepSeekV4HCPreCheckError(RuntimeError):
    """Raised when an HC_PRE package fails identity or byte roundtrip."""


@dataclass(frozen=True)
class _StableFile:
    descriptor: int
    fingerprint: tuple[int, ...]
    relative_path: str
    root_descriptor: int
    size_bytes: int


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DeepSeekV4HCPreCheckError(f"{label} must be an object")
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4HCPreCheckError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise DeepSeekV4HCPreCheckError(f"{label} is not a lowercase SHA-256")
    return value


def _json_equal(left: Any, right: Any) -> bool:
    """Compare strict-JSON values without Python's bool/integer equivalence."""

    return canonical_json_bytes(left) == canonical_json_bytes(right)


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
    ):
        raise DeepSeekV4HCPreCheckError(
            "platform lacks race-resistant bounded checker file operations"
        )


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4HCPreCheckError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4HCPreCheckError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4HCPreCheckError(f"{label} is not canonical POSIX")
    return value


def _open_root(stack: ExitStack, root: Path, label: str) -> tuple[int, tuple[int, ...]]:
    _require_secure_file_operations()
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4HCPreCheckError(f"{label} is not a directory")
    return descriptor, _fingerprint(metadata)


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
        raise DeepSeekV4HCPreCheckError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    finally:
        os.close(directory_descriptor)


def _safe_file(
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
        raise DeepSeekV4HCPreCheckError(f"{label} is not a regular file")
    if exact_size is not None and metadata.st_size != exact_size:
        raise DeepSeekV4HCPreCheckError(
            f"{label} has {metadata.st_size} bytes, expected {exact_size}"
        )
    if maximum_size is not None and metadata.st_size > maximum_size:
        raise DeepSeekV4HCPreCheckError(
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
        raise DeepSeekV4HCPreCheckError(f"{label} changed while the checker read it")
    current_descriptor = _open_relative_descriptor(
        source.root_descriptor, source.relative_path, label
    )
    try:
        current = os.fstat(current_descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or _fingerprint(current) != source.fingerprint
        ):
            raise DeepSeekV4HCPreCheckError(
                f"{label} was replaced while the checker read it"
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
        raise DeepSeekV4HCPreCheckError(f"{label} changed during verification")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreCheckError(
            f"cannot reopen {label} without following symlinks: {exc}"
        ) from exc
    try:
        if _fingerprint(os.fstat(current_descriptor)) != fingerprint:
            raise DeepSeekV4HCPreCheckError(f"{label} was replaced during verification")
    finally:
        os.close(current_descriptor)


def _descriptor_bytes(source: _StableFile, label: str, maximum: int) -> bytes:
    if source.size_bytes > maximum:
        raise DeepSeekV4HCPreCheckError(f"{label} exceeds its bounded size")
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
            raise DeepSeekV4HCPreCheckError(f"cannot read {label}: {exc}") from exc
        if not chunk:
            break
        payload.extend(chunk)
        offset += len(chunk)
    if len(payload) != source.size_bytes:
        raise DeepSeekV4HCPreCheckError(f"{label} ended while it was read")
    _verify_stable(source, label)
    return bytes(payload)


def _strict_json_payload(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4HCPreCheckError(
                    f"{label} has duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                DeepSeekV4HCPreCheckError(
                    f"{label} has non-finite JSON number {token!r}"
                )
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DeepSeekV4HCPreCheckError(f"cannot decode {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise DeepSeekV4HCPreCheckError(f"{label} is not a JSON object")
    if canonical_json_bytes(value) != payload:
        raise DeepSeekV4HCPreCheckError(f"{label} is not canonical JSON")
    return value


def _load_json(
    stack: ExitStack,
    root_descriptor: int,
    relative: str,
    label: str,
    *,
    maximum: int = _MAX_JSON_BYTES,
) -> tuple[dict[str, Any], _StableFile]:
    source = _safe_file(
        stack,
        root_descriptor,
        relative,
        label,
        maximum_size=maximum,
    )
    return _strict_json_payload(
        _descriptor_bytes(source, label, maximum), label
    ), source


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
            raise DeepSeekV4HCPreCheckError(f"cannot hash {label}: {exc}") from exc
        if not chunk:
            break
        digest.update(chunk)
        offset += len(chunk)
    if offset != source.size_bytes:
        raise DeepSeekV4HCPreCheckError(f"{label} ended while it was hashed")
    _verify_stable(source, label)
    return digest.hexdigest(), offset


def _compare_files(left: _StableFile, right: _StableFile, *, label: str) -> None:
    if left.size_bytes != right.size_bytes:
        raise DeepSeekV4HCPreCheckError(f"{label} sizes differ")
    offset = 0
    while offset < left.size_bytes:
        length = min(_READ_CHUNK_BYTES, left.size_bytes - offset)
        try:
            left_chunk = os.pread(left.descriptor, length, offset)
            right_chunk = os.pread(right.descriptor, length, offset)
        except OSError as exc:
            raise DeepSeekV4HCPreCheckError(f"cannot compare {label}: {exc}") from exc
        if left_chunk != right_chunk or not left_chunk:
            raise DeepSeekV4HCPreCheckError(
                f"{label} differs at or after byte {offset}"
            )
        offset += len(left_chunk)
    _verify_stable(left, f"{label} left file")
    _verify_stable(right, f"{label} right file")


def _validate_finite_f32(
    source: _StableFile, *, expected_elements: int, label: str
) -> None:
    count = 0
    offset = 0
    while offset < source.size_bytes:
        try:
            chunk = os.pread(
                source.descriptor,
                min(_READ_CHUNK_BYTES, source.size_bytes - offset),
                offset,
            )
        except OSError as exc:
            raise DeepSeekV4HCPreCheckError(f"cannot inspect {label}: {exc}") from exc
        if not chunk:
            break
        if len(chunk) % 4:
            raise DeepSeekV4HCPreCheckError(f"{label} is not binary32 aligned")
        for (code,) in struct.iter_unpack("<I", chunk):
            if code & 0x7F800000 == 0x7F800000:
                raise DeepSeekV4HCPreCheckError(
                    f"{label} contains nonfinite binary32 at element {count}"
                )
            count += 1
        offset += len(chunk)
    _verify_stable(source, label)
    if count != expected_elements:
        raise DeepSeekV4HCPreCheckError(
            f"{label} has {count} elements, expected {expected_elements}"
        )


def _load_inputs(
    stack: ExitStack,
    deployment_descriptor: int,
    application_descriptor: int,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[_StableFile],
]:
    semantic, semantic_file = _load_json(
        stack, deployment_descriptor, "model.ir.json", "HC_PRE semantic IR"
    )
    tensors, tensor_file = _load_json(
        stack,
        deployment_descriptor,
        "tensor_manifest.json",
        "HC_PRE tensor manifest",
    )
    application, application_file = _load_json(
        stack,
        application_descriptor,
        MANIFEST_FILENAME,
        "canonical application manifest",
    )
    verification, verification_file = _load_json(
        stack,
        application_descriptor,
        VERIFICATION_FILENAME,
        "canonical application verification",
    )
    return (
        semantic,
        tensors,
        application,
        verification,
        [semantic_file, tensor_file, application_file, verification_file],
    )


def _application_evidence(
    application: Mapping[str, Any], verification: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, list[Mapping[str, Any]]]]:
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
        "canonical application",
    )
    application_id = _digest(application["application_id"], "application_id")
    application_body = dict(application)
    application_body.pop("application_id")
    if (
        hashlib.sha256(canonical_json_bytes(application_body)).hexdigest()
        != application_id
    ):
        raise DeepSeekV4HCPreCheckError("canonical application ID differs")
    if application.get("schema") != "opentallas.canonical_application.v1":
        raise DeepSeekV4HCPreCheckError("canonical application schema differs")
    source = _exact_keys(
        application.get("source"),
        {"checkpoint_lock_id", "repository", "revision"},
        "canonical application source",
    )
    checkpoint_lock_id = _digest(
        source["checkpoint_lock_id"], "source.checkpoint_lock_id"
    )
    if not isinstance(source["repository"], str) or not source["repository"]:
        raise DeepSeekV4HCPreCheckError("source.repository is invalid")
    if (
        not isinstance(source["revision"], str)
        or _REVISION.fullmatch(source["revision"]) is None
    ):
        raise DeepSeekV4HCPreCheckError("source.revision is not a commit identity")
    plan = _exact_keys(
        application.get("plan"),
        {"expected_input_count", "plan_id", "schema"},
        "canonical application plan",
    )
    expected_input_count = plan.get("expected_input_count")
    if (
        isinstance(expected_input_count, bool)
        or not isinstance(expected_input_count, int)
        or expected_input_count < 1
    ):
        raise DeepSeekV4HCPreCheckError(
            "canonical application expected input count is invalid"
        )
    _digest(plan.get("plan_id"), "plan.plan_id")
    if not isinstance(plan.get("schema"), str) or not plan["schema"]:
        raise DeepSeekV4HCPreCheckError("canonical application plan schema is invalid")

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
        "canonical verification",
    )
    verification_id = _digest(
        verification["verification_id"], "verification.verification_id"
    )
    verification_body = dict(verification)
    verification_body.pop("verification_id")
    if (
        hashlib.sha256(canonical_json_bytes(verification_body)).hexdigest()
        != verification_id
        or verification.get("application_id") != application_id
        or verification.get("checkpoint_lock_id") != checkpoint_lock_id
        or verification.get("schema") != "opentallas.canonical_application_check.v1"
        or verification.get("status") != "full_assignment_match"
    ):
        raise DeepSeekV4HCPreCheckError("canonical verification identity differs")

    inputs = application.get("inputs")
    if not isinstance(inputs, list) or len(inputs) != len(_RESOURCES):
        raise DeepSeekV4HCPreCheckError(
            "canonical application does not select exactly three HC_PRE tensors"
        )
    inputs_by_name: dict[str, Mapping[str, Any]] = {}
    for index, (_, name, shape, size_bytes) in enumerate(_RESOURCES):
        record = _exact_keys(
            inputs[index],
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
        payload_sha256 = _digest(
            record.get("payload_sha256"), f"inputs[{index}].payload_sha256"
        )
        expected_record = {
            "action": "replicate_identity",
            "logical_dtype": "FP32",
            "name": name,
            "payload_sha256": payload_sha256,
            "shape": shape,
            "size_bytes": size_bytes,
            "storage_dtype": "F32",
        }
        if not _json_equal(record, expected_record):
            raise DeepSeekV4HCPreCheckError(
                f"canonical input {name!r} differs from its HC_PRE contract"
            )
        inputs_by_name[name] = record

    selection = _exact_keys(
        application.get("selection"),
        {"complete_plan", "dependency_input_names", "requested_input_names"},
        "canonical application selection",
    )
    if (
        not isinstance(selection.get("complete_plan"), bool)
        or selection.get("dependency_input_names") != []
        or selection.get("requested_input_names") != sorted(_EXPECTED_NAMES)
    ):
        raise DeepSeekV4HCPreCheckError(
            "canonical application selection differs from the HC_PRE package"
        )
    evidence_scope = application.get("evidence_scope")
    if evidence_scope == "official_checkpoint":
        if (
            selection.get("complete_plan") is not False
            or application.get("status")
            != "partial_official_transform_application_not_release_evidence"
            or application.get("plan")
            != {
                "expected_input_count": OFFICIAL_CANONICAL_INPUT_COUNT,
                "plan_id": OFFICIAL_CANONICAL_PLAN_ID,
                "schema": OFFICIAL_CANONICAL_PLAN_SCHEMA,
            }
            or (source.get("repository"), source.get("revision"))
            != (OFFICIAL_REPOSITORY, OFFICIAL_REVISION)
        ):
            raise DeepSeekV4HCPreCheckError(
                "official HC_PRE application is not the pinned MP=4 release selection"
            )
    elif evidence_scope == "development_fixture":
        if (
            selection.get("complete_plan") is not True
            or expected_input_count != len(_RESOURCES)
            or application.get("status")
            != "development_fixture_application_not_release_evidence"
        ):
            raise DeepSeekV4HCPreCheckError(
                "development HC_PRE application status or completeness differs"
            )
    else:
        raise DeepSeekV4HCPreCheckError("canonical application evidence scope differs")

    raw_assignments = application.get("assignments")
    if not isinstance(raw_assignments, list) or len(raw_assignments) != (
        len(_RESOURCES) * MODEL_PARALLEL
    ):
        raise DeepSeekV4HCPreCheckError(
            "canonical application must contain exactly twelve HC_PRE assignments"
        )
    assignments_by_name: dict[str, list[Mapping[str, Any]]] = {
        name: [] for _, name, _, _ in _RESOURCES
    }
    assignment_index = 0
    for _, name, shape, size_bytes in _RESOURCES:
        input_record = inputs_by_name[name]
        digest = input_record["payload_sha256"]
        for rank in range(MODEL_PARALLEL):
            record = _exact_keys(
                raw_assignments[assignment_index],
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
                f"canonical assignments[{assignment_index}]",
            )
            _exact_keys(
                record.get("source"),
                {"name", "payload_sha256", "shape", "slice", "storage_dtype"},
                f"canonical assignments[{assignment_index}].source",
            )
            expected_assignment = {
                "logical_dtype": "FP32",
                "name": name,
                "path": f"ranks/rank-{rank:03d}/{name}.bin",
                "payload_bytes": size_bytes,
                "rank": rank,
                "scale_source": None,
                "sha256": digest,
                "shape": shape,
                "source": {
                    "name": name,
                    "payload_sha256": digest,
                    "shape": shape,
                    "slice": None,
                    "storage_dtype": "F32",
                },
                "storage_dtype": "F32",
                "transform": "identity",
            }
            if not _json_equal(record, expected_assignment):
                raise DeepSeekV4HCPreCheckError(
                    f"canonical HC_PRE {name!r} rank {rank} assignment differs"
                )
            assignments_by_name[name].append(record)
            assignment_index += 1

    expected_coverage = {
        "consumed_input_count": len(_RESOURCES),
        "consumed_input_payload_bytes": TOTAL_PARAMETER_BYTES,
        "output_assignment_count": len(_RESOURCES) * MODEL_PARALLEL,
        "output_payload_bytes": TOTAL_PARAMETER_BYTES * MODEL_PARALLEL,
    }
    coverage = _exact_keys(
        application.get("coverage"),
        set(expected_coverage),
        "canonical application coverage",
    )
    if not _json_equal(coverage, expected_coverage):
        raise DeepSeekV4HCPreCheckError("canonical application coverage differs")

    checks = verification.get("checks")
    if not isinstance(checks, list) or len(checks) != len(raw_assignments):
        raise DeepSeekV4HCPreCheckError(
            "canonical verification must contain exactly twelve HC_PRE checks"
        )
    for index, assignment in enumerate(raw_assignments):
        check = _exact_keys(
            checks[index],
            {
                "assignment_path",
                "check_id",
                "checked_output_bytes",
                "detail_check_id",
                "method",
                "output_sha256",
                "rank",
                "source_name",
                "status",
                "transform",
            },
            f"canonical verification checks[{index}]",
        )
        check_body = {
            "assignment_path": assignment["path"],
            "checked_output_bytes": assignment["payload_bytes"],
            "detail_check_id": None,
            "method": "streamed_identity_or_slice",
            "output_sha256": assignment["sha256"],
            "rank": assignment["rank"],
            "source_name": assignment["source"]["name"],
            "status": "full_payload_match",
            "transform": "identity",
        }
        expected_check = {
            **check_body,
            "check_id": hashlib.sha256(canonical_json_bytes(check_body)).hexdigest(),
        }
        if not _json_equal(check, expected_check):
            raise DeepSeekV4HCPreCheckError(
                f"canonical verification check {index} differs"
            )
    expected_verification_coverage = {
        "checked_assignment_count": len(raw_assignments),
        "checked_input_count": len(_RESOURCES),
        "checked_output_bytes": TOTAL_PARAMETER_BYTES * MODEL_PARALLEL,
    }
    verification_coverage = _exact_keys(
        verification.get("coverage"),
        set(expected_verification_coverage),
        "canonical verification coverage",
    )
    if not _json_equal(verification_coverage, expected_verification_coverage):
        raise DeepSeekV4HCPreCheckError("canonical verification coverage differs")

    source_identity = {
        "application_id": application_id,
        "application_status": application["status"],
        "checkpoint_lock_id": checkpoint_lock_id,
        "evidence_scope": application["evidence_scope"],
        "repository": source["repository"],
        "revision": source["revision"],
        "verification_id": verification_id,
    }
    return source_identity, assignments_by_name


def _expected_semantic(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
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
        "source": dict(source),
    }


def _expected_numeric_profile() -> dict[str, Any]:
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
            "combination_destinations": 4,
            "combination_sources": 4,
            "flattened_width": FLATTENED_WIDTH,
            "hc_multiplier": 4,
            "hidden_size": HIDDEN_SIZE,
            "mix_fields": MIX_FIELD_COUNT,
            "post_fields": 4,
            "pre_fields": 4,
            "sinkhorn_iterations": 20,
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


def _expected_counter_contract() -> dict[str, Any]:
    return {
        "command_scaling": {
            "fixed_counters": "per_token_coefficient_times_batch_times_sequence",
            "poisoned_command": "no_success_counter_commit",
            "saturation_counter": "exact_observed_final_bf16_clamp_count",
        },
        "data_dependent": {
            "hc_pre_branch_bf16_saturations": {
                "maximum_per_token": 4096,
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


def _expected_coverage() -> dict[str, Any]:
    return {
        "execution_coverage": "none",
        "model_id": MODEL_ID,
        "numeric_contract_coverage": "SPEC-NUM 1.1 NUM-6.10",
        "packaged_operator_kind": "HC_PRE",
        "parameter_coverage": "all_three_learned_resources_for_one_site",
        "schema": COVERAGE_SCHEMA,
        "site": {"branch": "attention", "layer": 0, "scope": "main"},
        "status": "complete_operator_artifact_contract_not_execution_evidence",
    }


def _roundtrip_core(
    stack: ExitStack,
    deployment_descriptor: int,
    application_descriptor: int,
) -> tuple[dict[str, Any], list[_StableFile]]:
    semantic, tensors, application, verification, guarded_files = _load_inputs(
        stack, deployment_descriptor, application_descriptor
    )
    source_identity, assignments_by_name = _application_evidence(
        application, verification
    )
    if not _json_equal(semantic, _expected_semantic(source_identity)):
        raise DeepSeekV4HCPreCheckError(
            "HC_PRE semantic contract or source identity differs"
        )
    _exact_keys(
        tensors,
        {
            "base",
            "model_parallel",
            "projection",
            "scale",
            "schema",
            "total_unique_payload_bytes",
        },
        "HC_PRE tensor manifest",
    )
    tensor_header = {
        "model_parallel": tensors.get("model_parallel"),
        "schema": tensors.get("schema"),
        "total_unique_payload_bytes": tensors.get("total_unique_payload_bytes"),
    }
    if not _json_equal(
        tensor_header,
        {
            "model_parallel": MODEL_PARALLEL,
            "schema": TENSOR_SCHEMA,
            "total_unique_payload_bytes": TOTAL_PARAMETER_BYTES,
        },
    ):
        raise DeepSeekV4HCPreCheckError("HC_PRE tensor manifest header differs")

    reconstructed: list[dict[str, Any]] = []
    for resource, name, shape, size_bytes in _RESOURCES:
        record = _exact_keys(
            tensors.get(resource),
            {
                "content_address",
                "dtype",
                "encoding",
                "layout",
                "memory_map",
                "name",
                "path",
                "replicated_ranks",
                "sha256",
                "shape",
                "size_bytes",
                "source_assignment_paths",
            },
            f"HC_PRE tensor_manifest.{resource}",
        )
        assignments = assignments_by_name[name]
        source_paths = [item.get("path") for item in assignments]
        first = assignments[0]
        digest = _digest(first.get("sha256"), f"canonical {resource}.sha256")
        expected_path = f"payloads/sha256/{digest}.f32le"
        expected_record = {
            "content_address": f"sha256:{digest}",
            "dtype": "F32",
            "encoding": "ieee754_binary32_little_endian",
            "layout": "c_contiguous_row_major",
            "memory_map": {"length_bytes": size_bytes, "offset_bytes": 0},
            "name": name,
            "path": expected_path,
            "replicated_ranks": [0, 1, 2, 3],
            "sha256": digest,
            "shape": shape,
            "size_bytes": size_bytes,
            "source_assignment_paths": source_paths,
        }
        if not _json_equal(record, expected_record):
            raise DeepSeekV4HCPreCheckError(
                f"HC_PRE {resource} manifest differs from its fixed contract"
            )

        deployment_file = _safe_file(
            stack,
            deployment_descriptor,
            expected_path,
            f"HC_PRE {resource}.path",
            exact_size=size_bytes,
        )
        guarded_files.append(deployment_file)
        observed_digest, observed_size = _sha256_file(
            deployment_file, f"HC_PRE {resource}.path"
        )
        if (observed_digest, observed_size) != (digest, size_bytes):
            raise DeepSeekV4HCPreCheckError(
                f"HC_PRE {resource} differs from its content address"
            )
        _validate_finite_f32(
            deployment_file,
            expected_elements=size_bytes // 4,
            label=f"HC_PRE {resource}",
        )

        for rank, assignment in enumerate(assignments):
            canonical_file = _safe_file(
                stack,
                application_descriptor,
                assignment.get("path"),
                f"canonical {resource} rank {rank}.path",
                exact_size=size_bytes,
            )
            guarded_files.append(canonical_file)
            canonical_digest, canonical_size = _sha256_file(
                canonical_file, f"canonical {resource} rank {rank}.path"
            )
            if (canonical_digest, canonical_size) != (digest, size_bytes):
                raise DeepSeekV4HCPreCheckError(
                    f"canonical HC_PRE {resource} rank {rank} payload differs"
                )
            _compare_files(
                deployment_file,
                canonical_file,
                label=f"HC_PRE {resource} and canonical rank {rank}",
            )
        reconstructed.append(
            {
                "deployment_path": expected_path,
                "dtype": "F32",
                "replicated_ranks": [0, 1, 2, 3],
                "sha256": digest,
                "shape": shape,
                "size_bytes": size_bytes,
                "source_assignment_paths": source_paths,
                "tensor_name": name,
            }
        )

    body: dict[str, Any] = {
        "application_id": source_identity["application_id"],
        "checked_artifact_count": 3,
        "checked_payload_bytes": TOTAL_PARAMETER_BYTES,
        "checked_replica_count": 12,
        "checked_replica_payload_bytes": TOTAL_PARAMETER_BYTES * MODEL_PARALLEL,
        "checkpoint_lock_id": source_identity["checkpoint_lock_id"],
        "model_id": MODEL_ID,
        "reconstructed": reconstructed,
        "schema": ROUNDTRIP_SCHEMA,
        "status": "byte_exact_full_parameter_roundtrip",
    }
    body["roundtrip_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return body, guarded_files


def verify_deepseek_v4_hc_pre_roundtrip(
    deployment_root: Path,
    application_root: Path,
) -> dict[str, Any]:
    """Independently match all emitted bytes to every canonical MP=4 replica."""

    deployment_root = Path(deployment_root).absolute()
    application_root = Path(application_root).absolute()
    with ExitStack() as stack:
        deployment_descriptor, deployment_fingerprint = _open_root(
            stack, deployment_root, "HC_PRE deployment root"
        )
        application_descriptor, application_fingerprint = _open_root(
            stack, application_root, "canonical application root"
        )
        body, guarded_files = _roundtrip_core(
            stack, deployment_descriptor, application_descriptor
        )
        for guarded in guarded_files:
            _verify_stable(guarded, f"guarded file {guarded.relative_path!r}")
        _verify_root_stable(
            deployment_root,
            deployment_descriptor,
            deployment_fingerprint,
            "HC_PRE deployment root",
        )
        _verify_root_stable(
            application_root,
            application_descriptor,
            application_fingerprint,
            "canonical application root",
        )
        return body


def _load_exact_json(
    stack: ExitStack,
    root_descriptor: int,
    relative: str,
    expected: Mapping[str, Any],
    label: str,
) -> _StableFile:
    observed, source = _load_json(stack, root_descriptor, relative, label)
    if not _json_equal(observed, expected):
        raise DeepSeekV4HCPreCheckError(f"{label} differs from its frozen contract")
    return source


def _enumerate_tree(root_descriptor: int) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    visited_entries = 0

    def walk(directory_descriptor: int, prefix: str, depth: int) -> None:
        nonlocal visited_entries
        if depth > 8:
            raise DeepSeekV4HCPreCheckError(
                "HC_PRE deployment directory depth exceeds its bound"
            )
        before = _fingerprint(os.fstat(directory_descriptor))
        try:
            names = sorted(os.listdir(directory_descriptor))
        except OSError as exc:
            raise DeepSeekV4HCPreCheckError(
                f"cannot enumerate HC_PRE deployment: {exc}"
            ) from exc
        visited_entries += len(names)
        if visited_entries > 64:
            raise DeepSeekV4HCPreCheckError(
                "HC_PRE deployment entry count exceeds its bound"
            )
        for name in names:
            if name in {"", ".", ".."} or "/" in name or "\x00" in name:
                raise DeepSeekV4HCPreCheckError(
                    "HC_PRE deployment contains an unsafe directory entry"
                )
            relative = f"{prefix}/{name}" if prefix else name
            try:
                metadata = os.stat(
                    name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            except OSError as exc:
                raise DeepSeekV4HCPreCheckError(
                    f"cannot inspect deployment entry {relative!r}: {exc}"
                ) from exc
            if stat.S_ISREG(metadata.st_mode):
                files.add(relative)
                continue
            if stat.S_ISDIR(metadata.st_mode):
                directories.add(relative)
                flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
                try:
                    child_descriptor = os.open(name, flags, dir_fd=directory_descriptor)
                except OSError as exc:
                    raise DeepSeekV4HCPreCheckError(
                        f"cannot open deployment directory {relative!r}: {exc}"
                    ) from exc
                try:
                    walk(child_descriptor, relative, depth + 1)
                finally:
                    os.close(child_descriptor)
                continue
            raise DeepSeekV4HCPreCheckError(
                f"HC_PRE deployment entry {relative!r} is not a regular file or directory"
            )
        if _fingerprint(os.fstat(directory_descriptor)) != before:
            raise DeepSeekV4HCPreCheckError(
                "HC_PRE deployment changed during directory enumeration"
            )

    walk(root_descriptor, "", 0)
    return files, directories


def verify_deepseek_v4_hc_pre_deployment(
    deployment_root: Path,
    application_root: Path,
) -> dict[str, Any]:
    """Verify package closure, every artifact hash, build ID, and source bytes."""

    deployment_root = Path(deployment_root).absolute()
    application_root = Path(application_root).absolute()
    with ExitStack() as stack:
        deployment_descriptor, deployment_fingerprint = _open_root(
            stack, deployment_root, "HC_PRE deployment root"
        )
        application_descriptor, application_fingerprint = _open_root(
            stack, application_root, "canonical application root"
        )
        deployment, deployment_file = _load_json(
            stack,
            deployment_descriptor,
            "deployment_manifest.json",
            "HC_PRE deployment manifest",
        )
        application, application_file = _load_json(
            stack,
            application_descriptor,
            MANIFEST_FILENAME,
            "canonical application manifest",
        )
        verification, verification_file = _load_json(
            stack,
            application_descriptor,
            VERIFICATION_FILENAME,
            "canonical application verification",
        )
        guarded_files = [deployment_file, application_file, verification_file]
        source_identity, _ = _application_evidence(application, verification)
        _exact_keys(
            deployment,
            {
                "artifacts",
                "build_id",
                "claim_boundary",
                "compiler",
                "entrypoint",
                "model_id",
                "numeric_profile_id",
                "schema",
                "site",
                "source",
                "status",
            },
            "HC_PRE deployment manifest",
        )
        expected_status = (
            "official_checkpoint_complete_hc_pre_parameters_not_execution_evidence"
            if source_identity["evidence_scope"] == "official_checkpoint"
            else "development_fixture_complete_hc_pre_parameters_not_release_evidence"
        )
        deployment_metadata = {
            key: deployment[key]
            for key in (
                "claim_boundary",
                "compiler",
                "entrypoint",
                "model_id",
                "numeric_profile_id",
                "schema",
                "site",
                "source",
                "status",
            )
        }
        expected_deployment_metadata = {
            "claim_boundary": [
                "Packages all learned parameters and the frozen numeric contract for one complete HC_PRE site.",
                "Contains no input activation or expected result and establishes no execution, transformer, model-completion, or CUDA-equivalence claim.",
                "Semantic counter coefficients are contract metadata only and establish no cycles, throughput, energy, area, or PPA result.",
                "Publication is atomic create-once within a caller-trusted output parent; concurrent mutation by the same filesystem owner is outside the package threat boundary.",
            ],
            "compiler": {
                "name": "opentallas-deepseek-v4-hc-pre-artifact-compiler",
                "version": "0.1.0",
            },
            "entrypoint": {
                "counter_contract": "counter_contract.json",
                "numeric_profile": "numeric_profile.json",
                "semantic_ir": "model.ir.json",
                "tensor_manifest": "tensor_manifest.json",
            },
            "model_id": MODEL_ID,
            "numeric_profile_id": NUMERIC_PROFILE_ID,
            "schema": DEPLOYMENT_SCHEMA,
            "site": {"branch": "attention", "layer": 0, "scope": "main"},
            "source": source_identity,
            "status": expected_status,
        }
        if not _json_equal(deployment_metadata, expected_deployment_metadata):
            raise DeepSeekV4HCPreCheckError(
                "HC_PRE deployment metadata or claim boundary differs"
            )

        artifacts = deployment.get("artifacts")
        if not isinstance(artifacts, list) or len(artifacts) != 9:
            raise DeepSeekV4HCPreCheckError(
                "HC_PRE deployment must enumerate exactly nine artifacts"
            )
        paths: set[str] = set()
        roles: set[str] = set()
        role_by_path: dict[str, str] = {}
        artifact_bytes = 0
        ordered_paths: list[str] = []
        for index, value in enumerate(artifacts):
            record = _exact_keys(
                value,
                {"path", "role", "sha256", "size_bytes"},
                f"HC_PRE artifacts[{index}]",
            )
            path_value = record.get("path")
            role = record.get("role")
            size_value = record.get("size_bytes")
            if (
                not isinstance(path_value, str)
                or path_value in paths
                or not isinstance(role, str)
                or role in roles
                or isinstance(size_value, bool)
                or not isinstance(size_value, int)
                or not 1 <= size_value <= PROJECTION_BYTES
            ):
                raise DeepSeekV4HCPreCheckError(
                    "HC_PRE artifact paths, roles, or bounded sizes are invalid"
                )
            paths.add(path_value)
            roles.add(role)
            role_by_path[path_value] = role
            ordered_paths.append(path_value)
            artifact_file = _safe_file(
                stack,
                deployment_descriptor,
                path_value,
                f"artifact {index}.path",
                exact_size=size_value,
            )
            guarded_files.append(artifact_file)
            digest, size = _sha256_file(
                artifact_file, f"HC_PRE artifact {path_value!r}"
            )
            if digest != _digest(record.get("sha256"), f"artifacts[{index}].sha256"):
                raise DeepSeekV4HCPreCheckError(
                    f"HC_PRE artifact {path_value!r} differs from its manifest"
                )
            artifact_bytes += size
        if ordered_paths != sorted(ordered_paths):
            raise DeepSeekV4HCPreCheckError(
                "HC_PRE artifact records are not in canonical path order"
            )
        expected_roles = {
            "counter_contract",
            "hc_base_parameter",
            "hc_projection_parameter",
            "hc_scale_parameter",
            "numeric_profile",
            "operator_coverage",
            "roundtrip_report",
            "semantic_ir",
            "tensor_manifest",
        }
        if roles != expected_roles:
            raise DeepSeekV4HCPreCheckError("HC_PRE artifact role closure differs")

        actual_files, actual_directories = _enumerate_tree(deployment_descriptor)
        if actual_files != paths | {
            "deployment_manifest.json"
        } or actual_directories != {"payloads", "payloads/sha256"}:
            raise DeepSeekV4HCPreCheckError(
                "HC_PRE deployment contains an unlisted or missing artifact or directory"
            )

        identity = {
            "artifacts": artifacts,
            "compiler": deployment["compiler"],
            "model_id": deployment["model_id"],
            "numeric_profile_id": deployment["numeric_profile_id"],
            "site": deployment["site"],
            "source": deployment["source"],
        }
        build_id = _digest(deployment.get("build_id"), "deployment.build_id")
        if hashlib.sha256(canonical_json_bytes(identity)).hexdigest() != build_id:
            raise DeepSeekV4HCPreCheckError("HC_PRE deployment build ID differs")

        guarded_files.append(
            _load_exact_json(
                stack,
                deployment_descriptor,
                "model.ir.json",
                _expected_semantic(source_identity),
                "HC_PRE semantic IR",
            )
        )
        guarded_files.append(
            _load_exact_json(
                stack,
                deployment_descriptor,
                "numeric_profile.json",
                _expected_numeric_profile(),
                "HC_PRE numeric profile",
            )
        )
        guarded_files.append(
            _load_exact_json(
                stack,
                deployment_descriptor,
                "counter_contract.json",
                _expected_counter_contract(),
                "HC_PRE counter contract",
            )
        )
        guarded_files.append(
            _load_exact_json(
                stack,
                deployment_descriptor,
                "operator_coverage.json",
                _expected_coverage(),
                "HC_PRE operator coverage",
            )
        )
        roundtrip, roundtrip_guards = _roundtrip_core(
            stack, deployment_descriptor, application_descriptor
        )
        guarded_files.extend(roundtrip_guards)
        guarded_files.append(
            _load_exact_json(
                stack,
                deployment_descriptor,
                "roundtrip_report.json",
                roundtrip,
                "HC_PRE roundtrip report",
            )
        )
        reconstructed_paths = {
            item["tensor_name"]: item["deployment_path"]
            for item in roundtrip["reconstructed"]
        }
        expected_role_by_path = {
            "counter_contract.json": "counter_contract",
            "model.ir.json": "semantic_ir",
            "numeric_profile.json": "numeric_profile",
            "operator_coverage.json": "operator_coverage",
            "roundtrip_report.json": "roundtrip_report",
            "tensor_manifest.json": "tensor_manifest",
            reconstructed_paths[BASE_NAME]: "hc_base_parameter",
            reconstructed_paths[PROJECTION_NAME]: "hc_projection_parameter",
            reconstructed_paths[SCALE_NAME]: "hc_scale_parameter",
        }
        if role_by_path != expected_role_by_path:
            raise DeepSeekV4HCPreCheckError(
                "HC_PRE artifact path-to-role mapping differs"
            )

        for guarded in guarded_files:
            _verify_stable(guarded, f"guarded file {guarded.relative_path!r}")
        _verify_root_stable(
            deployment_root,
            deployment_descriptor,
            deployment_fingerprint,
            "HC_PRE deployment root",
        )
        _verify_root_stable(
            application_root,
            application_descriptor,
            application_fingerprint,
            "canonical application root",
        )
        return {
            "application_id": source_identity["application_id"],
            "artifact_bytes": artifact_bytes,
            "build_id": build_id,
            "checked_artifact_count": len(artifacts),
            "roundtrip_id": roundtrip["roundtrip_id"],
            "status": "artifact_hashes_and_source_roundtrip_verified",
        }


__all__ = [
    "DeepSeekV4HCPreCheckError",
    "ROUNDTRIP_SCHEMA",
    "verify_deepseek_v4_hc_pre_deployment",
    "verify_deepseek_v4_hc_pre_roundtrip",
]
