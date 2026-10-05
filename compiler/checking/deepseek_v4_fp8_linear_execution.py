"""Independent locked-checkpoint differential for DeepSeek V4 FP8 linear.

The checker never imports the FP8 service engine.  It validates and hashes the
persisted deployment, streams the original locked weight tensor while retaining
the required logical rows, reads the small scale table from the original
checkpoint, executes an independent target-precision reference, and compares the
persisted service result exactly.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
from typing import Any

from compiler.frontend.checkpoint import (
    LockedCheckpointReader,
    validate_checkpoint_lock,
)
from compiler.frontend.deepseek_v4 import (
    MODEL_ID,
    REPOSITORY,
    REVISION,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_fp8_linear import decode, disassemble, verify
from runtime.reference.matrix import (
    MatrixReferenceError,
    dense_fp8_linear_bf16,
    dense_fp8_linear_selected_rows_bf16,
)


DIFFERENTIAL_SCHEMA = "opentallas.deepseek_v4_fp8_linear_differential.v1"
DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_fp8_linear_deployment.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_fp8_linear_slice.v1"
TENSOR_SCHEMA = "opentallas.deepseek_v4_fp8_linear_tensors.v1"
REQUEST_SCHEMA = "opentallas.deepseek_v4_fp8_linear_request.v1"
RESULT_SCHEMA = "opentallas.deepseek_v4_fp8_linear_result.v1"
EXPECTATION_SCHEMA = "opentallas.deepseek_v4_fp8_linear_expectations.v1"
COVERAGE_SCHEMA = "opentallas.deepseek_v4_fp8_linear_coverage.v1"
ROUNDTRIP_SCHEMA = "opentallas.deepseek_v4_fp8_linear_roundtrip.v1"
FULL_DIFFERENTIAL_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_differential.v1"
FULL_DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_deployment.v1"
FULL_SEMANTIC_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full.v1"
FULL_TENSOR_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_tensors.v1"
FULL_RESULT_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_result.v1"
FULL_COVERAGE_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_coverage.v1"
WEIGHT_NAME = "layers.0.attn.wq_a.weight"
SCALE_NAME = "layers.0.attn.wq_a.scale"
BLOCK_SIZE = 128
MAX_INPUT_ROWS = 4
MAX_SELECTED_ROWS = 64
MAX_FEATURE_EXTENT = 65_536
MAX_WEIGHT_PAYLOAD_BYTES = 8 * 1024 * 1024
MAX_FULL_PRODUCTS_PER_INPUT_ROW = 8 * 1024 * 1024
MAX_PRODUCTS_PER_REQUEST = 16 * 1024 * 1024
JSON_FIXED_OVERHEAD_BYTES = 64 * 1024

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROLES = frozenset(
    {
        "execution_expectations",
        "microcode",
        "microcode_disassembly",
        "operator_coverage",
        "output_selection",
        "roundtrip_report",
        "scale_table",
        "semantic_ir",
        "tensor_manifest",
        "weight_matrix",
    }
)
_SEMANTIC_CLAIM = (
    "Selected logical output rows of layer-0 query-A FP8_LINEAR only; "
    "not complete query projection, attention, or a transformer block."
)
_DEPLOYMENT_CLAIMS = [
    "Executes selected logical output rows of one FP8_LINEAR operator.",
    "Does not execute all query-A rows, attention, a transformer block, logits, or decode state.",
    "Functional counters are not hardware cycles, PPA, or NVIDIA comparison evidence.",
]
_FULL_SEMANTIC_CLAIM = (
    "Complete layer-0 query-A FP8_LINEAR outputs for supplied BF16 rows; "
    "not input normalization, attention, or a transformer block."
)
_FULL_DEPLOYMENT_CLAIMS = [
    "Executes every logical output row of one FP8_LINEAR operator.",
    "Does not execute input normalization, attention, a transformer block, logits, or decode state.",
    "Functional counters are not hardware cycles, PPA, or NVIDIA comparison evidence.",
]


class DeepSeekV4FP8LinearDifferentialError(RuntimeError):
    """Raised when persisted execution differs from locked source semantics."""


@dataclass(frozen=True)
class _Artifact:
    path: Path
    relative_path: str
    role: str
    sha256: str
    size_bytes: int
    descriptor: int
    fingerprint: tuple[int, ...]


def _strict_json_payload(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4FP8LinearDifferentialError(
                    f"{label} has duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                DeepSeekV4FP8LinearDifferentialError(
                    f"{label} has non-finite JSON number {token!r}"
                )
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"cannot decode {label}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} is not a JSON object"
        )
    if canonical_json_bytes(value) != payload:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} is not canonical JSON"
        )
    return value


def _small_bytes(path: Path, label: str, maximum: int = 1024 * 1024) -> bytes:
    """Read one stable, bounded regular file without following its final symlink."""

    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_NONBLOCK")
        or not hasattr(os, "O_CLOEXEC")
        or not hasattr(os, "pread")
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "platform lacks race-resistant bounded file operations"
        )
    path = Path(path)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK

    def open_descriptor(stack: ExitStack, context: str) -> int:
        try:
            descriptor = os.open(path, flags)
        except OSError as exc:
            raise DeepSeekV4FP8LinearDifferentialError(
                f"cannot {context} {label} without following symlinks: {exc}"
            ) from exc
        stack.callback(os.close, descriptor)
        return descriptor

    try:
        with ExitStack() as stack:
            descriptor = open_descriptor(stack, "open")
            payload, fingerprint = _descriptor_bytes(
                descriptor,
                label,
                maximum=maximum,
            )
            current_descriptor = open_descriptor(stack, "reopen")
            current = os.fstat(current_descriptor)
            if (
                not stat.S_ISREG(current.st_mode)
                or _fingerprint(current) != fingerprint
            ):
                raise DeepSeekV4FP8LinearDifferentialError(
                    f"{label} was replaced while the checker read it"
                )
            return payload
    except DeepSeekV4FP8LinearDifferentialError:
        raise
    except OSError as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"cannot read {label}: {exc}"
        ) from exc


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


def _open_root(stack: ExitStack, root: Path) -> tuple[int, tuple[int, ...]]:
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "pread")
        or os.open not in os.supports_dir_fd
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "platform lacks race-resistant checker file operations"
        )
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptor = os.open(root, flags)
    except OSError as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"cannot open deployment root descriptor: {exc}"
        ) from exc
    stack.callback(os.close, descriptor)
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        raise DeepSeekV4FP8LinearDifferentialError(
            "deployment root descriptor is not a directory"
        )
    return descriptor, _fingerprint(metadata)


def _open_relative(
    stack: ExitStack, root_descriptor: int, relative: str, label: str
) -> int:
    parts = Path(relative).parts
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
        descriptor = os.open(
            parts[-1], file_flags, dir_fd=directory_descriptor
        )
    except OSError as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"cannot open {label} without following symlinks: {exc}"
        ) from exc
    finally:
        os.close(directory_descriptor)
    stack.callback(os.close, descriptor)
    return descriptor


def _descriptor_bytes(
    descriptor: int,
    label: str,
    *,
    maximum: int,
    expected_fingerprint: tuple[int, ...] | None = None,
) -> tuple[bytes, tuple[int, ...]]:
    before = os.fstat(descriptor)
    before_fingerprint = _fingerprint(before)
    if not stat.S_ISREG(before.st_mode):
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} descriptor is not a regular file"
        )
    if before.st_size > maximum:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} exceeds its {maximum}-byte checker bound"
        )
    payload = bytearray()
    offset = 0
    while offset < before.st_size:
        chunk = os.pread(
            descriptor,
            min(8 * 1024 * 1024, before.st_size - offset),
            offset,
        )
        if not chunk:
            break
        payload.extend(chunk)
        offset += len(chunk)
    after_fingerprint = _fingerprint(os.fstat(descriptor))
    if after_fingerprint != before_fingerprint or len(payload) != before.st_size:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} changed while the checker read it"
        )
    if (
        expected_fingerprint is not None
        and before_fingerprint != expected_fingerprint
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} descriptor identity changed"
        )
    return bytes(payload), before_fingerprint


def _descriptor_hash(
    descriptor: int,
    label: str,
    *,
    expected_fingerprint: tuple[int, ...] | None = None,
) -> tuple[str, int, tuple[int, ...]]:
    before = os.fstat(descriptor)
    before_fingerprint = _fingerprint(before)
    if not stat.S_ISREG(before.st_mode):
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} descriptor is not a regular file"
        )
    digest = hashlib.sha256()
    size = 0
    while True:
        chunk = os.pread(descriptor, 8 * 1024 * 1024, size)
        if not chunk:
            break
        digest.update(chunk)
        size += len(chunk)
    after_fingerprint = _fingerprint(os.fstat(descriptor))
    if after_fingerprint != before_fingerprint or size != before.st_size:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} changed while the checker hashed it"
        )
    if (
        expected_fingerprint is not None
        and before_fingerprint != expected_fingerprint
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} descriptor identity changed"
        )
    return digest.hexdigest(), size, before_fingerprint


def _verified_small_bytes(
    artifact: _Artifact, label: str, maximum: int = 1024 * 1024
) -> bytes:
    payload, _ = _descriptor_bytes(
        artifact.descriptor,
        label,
        maximum=maximum,
        expected_fingerprint=artifact.fingerprint,
    )
    if (hashlib.sha256(payload).hexdigest(), len(payload)) != (
        artifact.sha256,
        artifact.size_bytes,
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} differs from its deployment artifact record"
        )
    return payload


def _verified_json(artifact: _Artifact, label: str) -> dict[str, Any]:
    return _strict_json_payload(_verified_small_bytes(artifact, label), label)


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


def _integer(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        bound = f"[{minimum}, {maximum}]" if maximum is not None else f">= {minimum}"
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} must be an integer in {bound}"
        )
    return value


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} must be a lowercase SHA-256"
        )
    return value


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _safe_file(root: Path, value: Any, label: str) -> tuple[str, Path]:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} is not canonical POSIX"
        )
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4FP8LinearDifferentialError(f"{label} traverses a symlink")
    try:
        current.resolve().relative_to(root)
    except ValueError as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} escapes deployment"
        ) from exc
    if not current.is_file():
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} is not a regular file"
        )
    return value, current


def _deployment_artifacts(
    root: Path,
    manifest: Mapping[str, Any],
    *,
    stack: ExitStack,
    root_descriptor: int,
) -> tuple[dict[str, _Artifact], bool]:
    _exact_keys(
        manifest,
        {
            "artifacts",
            "build_id",
            "claim_boundary",
            "compiler",
            "entrypoint",
            "microcode_abi",
            "model_id",
            "schema",
            "source_application_id",
            "status",
        },
        "FP8 linear deployment manifest",
    )
    schema = manifest["schema"]
    if schema not in {DEPLOYMENT_SCHEMA, FULL_DEPLOYMENT_SCHEMA}:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear deployment schema is unsupported"
        )
    full_operator = schema == FULL_DEPLOYMENT_SCHEMA
    if manifest["model_id"] != MODEL_ID:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear deployment identity differs"
        )
    expected_claims = (
        _FULL_DEPLOYMENT_CLAIMS if full_operator else _DEPLOYMENT_CLAIMS
    )
    if manifest["claim_boundary"] != expected_claims:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear deployment claim boundary differs"
        )
    expected_statuses = (
        {
            "development_fixture_complete_fp8_linear_operator_not_release_evidence",
            "real_checkpoint_complete_fp8_linear_operator",
        }
        if full_operator
        else {
            "development_fixture_selected_fp8_linear_rows_not_release_evidence",
            "real_checkpoint_selected_fp8_linear_rows_not_full_operator",
        }
    )
    if manifest["status"] not in expected_statuses:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear deployment status is unsupported"
        )
    raw = manifest["artifacts"]
    if not isinstance(raw, list) or not raw:
        raise DeepSeekV4FP8LinearDifferentialError("deployment artifacts are absent")
    by_role: dict[str, _Artifact] = {}
    retained: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    previous: str | None = None
    for index, record in enumerate(raw):
        if not isinstance(record, Mapping):
            raise DeepSeekV4FP8LinearDifferentialError(
                f"deployment artifact {index} is not an object"
            )
        _exact_keys(
            record,
            {"path", "role", "sha256", "size_bytes"},
            f"deployment artifact {index}",
        )
        relative, path = _safe_file(root, record["path"], f"artifact {index}.path")
        role = record["role"]
        if (
            not isinstance(role, str)
            or not role
            or role in by_role
            or relative in seen_paths
            or (previous is not None and relative <= previous)
        ):
            raise DeepSeekV4FP8LinearDifferentialError(
                "deployment artifacts have duplicate or noncanonical identities"
            )
        digest = _hash(record["sha256"], f"artifact {relative}.sha256")
        size = _integer(record["size_bytes"], f"artifact {relative}.size_bytes")
        descriptor = _open_relative(
            stack,
            root_descriptor,
            relative,
            f"deployment artifact {relative!r}",
        )
        observed_digest, observed_size, fingerprint = _descriptor_hash(
            descriptor, f"deployment artifact {relative!r}"
        )
        if (observed_digest, observed_size) != (digest, size):
            raise DeepSeekV4FP8LinearDifferentialError(
                f"deployment artifact {relative!r} differs from its manifest"
            )
        artifact = _Artifact(
            path,
            relative,
            role,
            digest,
            size,
            descriptor,
            fingerprint,
        )
        by_role[role] = artifact
        retained.append(dict(record))
        seen_paths.add(relative)
        previous = relative
    if set(by_role) != _ROLES:
        raise DeepSeekV4FP8LinearDifferentialError(
            "deployment artifact roles differ from the fixed FP8 slice"
        )
    expected_entrypoint = {
        "execution_expectations": by_role["execution_expectations"].relative_path,
        "microcode": by_role["microcode"].relative_path,
        "semantic_ir": by_role["semantic_ir"].relative_path,
        "tensor_manifest": by_role["tensor_manifest"].relative_path,
    }
    if (
        not isinstance(manifest["entrypoint"], Mapping)
        or dict(manifest["entrypoint"]) != expected_entrypoint
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear deployment entrypoint differs from artifact roles"
        )
    compiler = manifest["compiler"]
    if not isinstance(compiler, Mapping):
        raise DeepSeekV4FP8LinearDifferentialError("compiler identity is absent")
    _exact_keys(compiler, {"name", "version"}, "compiler identity")
    expected_compiler = (
        "opentallas-deepseek-v4-fp8-linear-compiler"
        if full_operator
        else "opentallas-deepseek-v4-fp8-linear-slice-compiler"
    )
    if (
        compiler["name"] != expected_compiler
        or not isinstance(compiler["version"], str)
        or not compiler["version"]
    ):
        raise DeepSeekV4FP8LinearDifferentialError("compiler identity differs")
    abi = manifest["microcode_abi"]
    if abi != {"major": 1, "minor": 0, "name": "deepseek_v4_fp8_linear"}:
        raise DeepSeekV4FP8LinearDifferentialError("FP8 microcode ABI differs")
    application_id = _hash(
        manifest["source_application_id"], "source_application_id"
    )
    identity = {
        "artifacts": retained,
        "compiler_version": compiler["version"],
        "microcode_abi": abi,
        "model_id": MODEL_ID,
        "source_application_id": application_id,
    }
    if manifest["build_id"] != _sha256_json(identity):
        raise DeepSeekV4FP8LinearDifferentialError(
            "deployment build_id does not bind verified artifacts"
        )
    return by_role, full_operator


def _dimensions_and_source(
    semantic: Mapping[str, Any],
    manifest: Mapping[str, Any],
    lock: Mapping[str, Any],
    *,
    full_operator: bool,
) -> tuple[int, int, tuple[int, ...], Mapping[str, Any]]:
    _exact_keys(
        semantic,
        {
            "claim_boundary",
            "dimensions",
            "model_id",
            "numeric_profile",
            "operation",
            "schema",
            "source",
        },
        "FP8 linear semantic IR",
    )
    expected_schema = FULL_SEMANTIC_SCHEMA if full_operator else SEMANTIC_SCHEMA
    expected_claim = _FULL_SEMANTIC_CLAIM if full_operator else _SEMANTIC_CLAIM
    expected_numeric_profile = (
        "deepseek_v4_dense_fp8_full_v1"
        if full_operator
        else "deepseek_v4_dense_fp8_selected_rows_v1"
    )
    expected_operation = {
        "input": "input_bf16_codes",
        "kind": "FP8_LINEAR" if full_operator else "FP8_LINEAR_SELECTED_ROWS",
        "output": "output_bf16_codes",
        "scale_resource": SCALE_NAME,
        "weight_resource": WEIGHT_NAME,
    }
    if (
        semantic["schema"] != expected_schema
        or semantic["model_id"] != MODEL_ID
        or semantic["claim_boundary"] != expected_claim
        or semantic["numeric_profile"] != expected_numeric_profile
        or semantic["operation"] != expected_operation
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear semantic identity differs"
        )
    dimensions = semantic["dimensions"]
    if not isinstance(dimensions, Mapping):
        raise DeepSeekV4FP8LinearDifferentialError("semantic dimensions are absent")
    dimension_keys = {"block_size", "input_features", "output_features"}
    if not full_operator:
        dimension_keys.add("selected_output_rows")
    _exact_keys(dimensions, dimension_keys, "FP8 linear dimensions")
    input_features = _integer(
        dimensions["input_features"],
        "dimensions.input_features",
        minimum=BLOCK_SIZE,
        maximum=MAX_FEATURE_EXTENT,
    )
    output_features = _integer(
        dimensions["output_features"],
        "dimensions.output_features",
        minimum=1,
        maximum=MAX_FEATURE_EXTENT,
    )
    if dimensions["block_size"] != BLOCK_SIZE or input_features % BLOCK_SIZE:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear dimensions violate the 128-value block contract"
        )
    weight_bytes = input_features * output_features
    if weight_bytes > MAX_WEIGHT_PAYLOAD_BYTES:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 weight extent exceeds the checker memory budget"
        )
    if full_operator and weight_bytes > MAX_FULL_PRODUCTS_PER_INPUT_ROW:
        raise DeepSeekV4FP8LinearDifferentialError(
            "complete FP8 operator exceeds the checker work budget"
        )
    if full_operator:
        rows = tuple(range(output_features))
    else:
        raw_rows = dimensions["selected_output_rows"]
        if not isinstance(raw_rows, list):
            raise DeepSeekV4FP8LinearDifferentialError(
                "selected output rows are absent"
            )
        rows = tuple(
            _integer(
                row,
                f"selected_output_rows[{index}]",
                maximum=output_features - 1,
            )
            for index, row in enumerate(raw_rows)
        )
        if (
            not rows
            or len(rows) > MAX_SELECTED_ROWS
            or rows != tuple(sorted(set(rows)))
        ):
            raise DeepSeekV4FP8LinearDifferentialError(
                "selected output rows are not unique strictly increasing indices"
            )
    source = semantic["source"]
    if not isinstance(source, Mapping):
        raise DeepSeekV4FP8LinearDifferentialError("semantic source is absent")
    _exact_keys(
        source,
        {
            "application_id",
            "application_status",
            "checkpoint_lock_id",
            "evidence_scope",
            "repository",
            "revision",
            "verification_id",
        },
        "FP8 linear semantic source",
    )
    for key in ("application_id", "checkpoint_lock_id", "verification_id"):
        _hash(source[key], f"semantic source {key}")
    lock_source = lock["source"]
    if (
        source["application_id"] != manifest["source_application_id"]
        or source["checkpoint_lock_id"] != lock["lock_id"]
        or source["repository"] != lock_source["repository"]
        or source["revision"] != lock_source["revision"]
        or source["evidence_scope"]
        not in {"development_fixture", "official_checkpoint"}
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "semantic source differs from deployment or checkpoint lock"
        )
    evidence_scope = source["evidence_scope"]
    allowed_application_statuses = {
        "official_checkpoint": {
            "complete_official_transform_application",
            "partial_official_transform_application_not_release_evidence",
        },
        "development_fixture": {
            "development_fixture_application_not_release_evidence"
        },
    }[evidence_scope]
    if source["application_status"] not in allowed_application_statuses:
        raise DeepSeekV4FP8LinearDifferentialError(
            "semantic application status differs from evidence scope"
        )
    expected_deployment_status = (
        "real_checkpoint_complete_fp8_linear_operator"
        if full_operator and evidence_scope == "official_checkpoint"
        else (
            "development_fixture_complete_fp8_linear_operator_not_release_evidence"
            if full_operator
            else (
                "real_checkpoint_selected_fp8_linear_rows_not_full_operator"
                if evidence_scope == "official_checkpoint"
                else "development_fixture_selected_fp8_linear_rows_not_release_evidence"
            )
        )
    )
    if manifest["status"] != expected_deployment_status:
        raise DeepSeekV4FP8LinearDifferentialError(
            "deployment status overstates or understates its evidence scope"
        )
    if evidence_scope == "official_checkpoint" and (
        source["repository"],
        source["revision"],
        input_features,
        output_features,
    ) != (REPOSITORY, REVISION, 4096, 1024):
        raise DeepSeekV4FP8LinearDifferentialError(
            "official FP8 source identity or dimensions differ"
        )
    return input_features, output_features, rows, source


def _artifact_matches(
    artifact: _Artifact, record: Mapping[str, Any], label: str
) -> None:
    if (
        record.get("path") != artifact.relative_path
        or record.get("sha256") != artifact.sha256
        or record.get("size_bytes") != artifact.size_bytes
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} does not bind its deployment artifact"
        )


def _tensor_resources(
    tensors: Mapping[str, Any],
    artifacts: Mapping[str, _Artifact],
    *,
    input_features: int,
    output_features: int,
    selected_rows: tuple[int, ...],
    evidence_scope: str,
    full_operator: bool,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    _exact_keys(
        tensors, {"output_selection", "scale", "schema", "weight"}, "tensor manifest"
    )
    expected_schema = FULL_TENSOR_SCHEMA if full_operator else TENSOR_SCHEMA
    if tensors["schema"] != expected_schema:
        raise DeepSeekV4FP8LinearDifferentialError("tensor manifest schema differs")
    weight = tensors["weight"]
    scale = tensors["scale"]
    selection = tensors["output_selection"]
    if not all(isinstance(item, Mapping) for item in (weight, scale, selection)):
        raise DeepSeekV4FP8LinearDifferentialError("tensor resources are malformed")
    _exact_keys(
        weight,
        {
            "dtype",
            "path",
            "replicated_ranks",
            "sha256",
            "shape",
            "size_bytes",
            "source_assignment_path",
        },
        "weight resource",
    )
    _exact_keys(
        scale,
        {
            "dtype",
            "path",
            "replicated_ranks",
            "sha256",
            "shape",
            "size_bytes",
            "source_assignment_path",
        },
        "scale resource",
    )
    _exact_keys(
        selection,
        {"dtype", "path", "rows", "sha256", "size_bytes"},
        "selection resource",
    )
    _artifact_matches(artifacts["weight_matrix"], weight, "weight resource")
    _artifact_matches(artifacts["scale_table"], scale, "scale resource")
    _artifact_matches(artifacts["output_selection"], selection, "selection resource")
    blocks = input_features // BLOCK_SIZE
    scale_rows = (output_features + BLOCK_SIZE - 1) // BLOCK_SIZE
    ranks = weight["replicated_ranks"]
    if (
        weight["dtype"] != "F8_E4M3"
        or weight["shape"] != [output_features, input_features]
        or weight["size_bytes"] != output_features * input_features
        or scale["dtype"] != "F8_E8M0"
        or scale["shape"] != [scale_rows, blocks]
        or scale["size_bytes"] != scale_rows * blocks
        or ranks != scale["replicated_ranks"]
        or not isinstance(ranks, list)
        or not ranks
        or ranks != list(range(len(ranks)))
        or not isinstance(weight["source_assignment_path"], str)
        or not isinstance(scale["source_assignment_path"], str)
        or (evidence_scope == "official_checkpoint" and ranks != [0, 1, 2, 3])
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "weight or scale resource metadata differs"
        )
    selection_payload = _verified_small_bytes(
        artifacts["output_selection"],
        "output selection",
        maximum=(output_features if full_operator else MAX_SELECTED_ROWS) * 4,
    )
    if (
        selection["dtype"] != "U32"
        or selection["rows"] != list(selected_rows)
        or len(selection_payload) != len(selected_rows) * 4
        or struct.unpack(f"<{len(selected_rows)}I", selection_payload) != selected_rows
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "output selection metadata or bytes differ"
        )
    return weight, scale


def _expected_coefficients(
    input_features: int, selected_count: int
) -> dict[str, int]:
    blocks = input_features // BLOCK_SIZE
    return {
        "activation_blocks_quantized": blocks,
        "activation_values_quantized": input_features,
        "bf16_outputs_written": selected_count,
        "binary32_block_reduction_adds": selected_count * (blocks - 1),
        "binary32_product_accumulates": selected_count * input_features,
        "logical_input_bytes_read": input_features * 2,
        "logical_output_bytes_written": selected_count * 2,
        "logical_rom_bytes_read": selected_count * (input_features + blocks),
        "matrix_block_dots": selected_count * blocks,
    }


def _scan_artifact_codes(
    artifact: _Artifact, forbidden: frozenset[int], label: str
) -> None:
    digest = hashlib.sha256()
    size = 0
    before_fingerprint = _fingerprint(os.fstat(artifact.descriptor))
    if before_fingerprint != artifact.fingerprint:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} descriptor identity changed before scanning"
        )
    offset = 0
    while True:
        chunk = os.pread(artifact.descriptor, 8 * 1024 * 1024, offset)
        if not chunk:
            break
        digest.update(chunk)
        size += len(chunk)
        for index, code in enumerate(chunk):
            if code in forbidden:
                raise DeepSeekV4FP8LinearDifferentialError(
                    f"{label} contains reserved code 0x{code:02x} at "
                    f"byte {offset + index}"
                )
        offset += len(chunk)
    if _fingerprint(os.fstat(artifact.descriptor)) != before_fingerprint:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} changed while the checker scanned it"
        )
    if (digest.hexdigest(), size) != (artifact.sha256, artifact.size_bytes):
        raise DeepSeekV4FP8LinearDifferentialError(
            f"{label} changed while the checker scanned it"
        )


def _verify_contract_artifacts(
    artifacts: Mapping[str, _Artifact],
    manifest: Mapping[str, Any],
    *,
    input_features: int,
    selected_count: int,
    weight_resource: Mapping[str, Any],
    scale_resource: Mapping[str, Any],
    full_operator: bool,
) -> None:
    expectations = _verified_json(
        artifacts["execution_expectations"], "execution expectations"
    )
    _exact_keys(
        expectations,
        {
            "counter_coefficients_per_input_row",
            "fixed_counters",
            "hardware_accounting",
            "schema",
        },
        "execution expectations",
    )
    if (
        expectations["schema"] != EXPECTATION_SCHEMA
        or expectations["counter_coefficients_per_input_row"]
        != _expected_coefficients(input_features, selected_count)
        or expectations["fixed_counters"]
        != {
            "completion_events": 1,
            "micro_ops_executed": 2,
            "semantic_operations_executed": 1,
        }
        or expectations["hardware_accounting"]
        != {
            "cycles": None,
            "hbm_transactions": None,
            "stalls": None,
            "status": "not modeled by the functional FP8 linear slice",
        }
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "execution expectation contract differs"
        )

    coverage = _verified_json(artifacts["operator_coverage"], "coverage ledger")
    expected_coverage = {
        "implemented_operator_kind": (
            "FP8_LINEAR" if full_operator else "FP8_LINEAR_SELECTED_ROWS"
        ),
        "model_id": MODEL_ID,
        "schema": FULL_COVERAGE_SCHEMA if full_operator else COVERAGE_SCHEMA,
        "status": (
            "complete_operator_arithmetic_only"
            if full_operator
            else "selected_output_rows_arithmetic_slice_only"
        ),
        "underlying_graph_operator_kind": "FP8_LINEAR",
    }
    if coverage != expected_coverage:
        raise DeepSeekV4FP8LinearDifferentialError("coverage ledger differs")

    roundtrip = _verified_json(artifacts["roundtrip_report"], "roundtrip report")
    _exact_keys(
        roundtrip,
        {
            "application_id",
            "checked_artifact_count",
            "checked_payload_bytes",
            "model_id",
            "reconstructed",
            "roundtrip_id",
            "schema",
            "status",
        },
        "roundtrip report",
    )
    raw_reconstructed = roundtrip["reconstructed"]
    if not isinstance(raw_reconstructed, list) or len(raw_reconstructed) != 2:
        raise DeepSeekV4FP8LinearDifferentialError(
            "roundtrip reconstruction records differ"
        )
    expected_reconstructed = {
        artifacts["weight_matrix"].relative_path: (
            artifacts["weight_matrix"],
            weight_resource,
            WEIGHT_NAME,
        ),
        artifacts["scale_table"].relative_path: (
            artifacts["scale_table"],
            scale_resource,
            SCALE_NAME,
        ),
    }
    seen: set[str] = set()
    for index, record in enumerate(raw_reconstructed):
        if not isinstance(record, Mapping):
            raise DeepSeekV4FP8LinearDifferentialError(
                f"roundtrip record {index} is malformed"
            )
        _exact_keys(
            record,
            {
                "deployment_path",
                "sha256",
                "size_bytes",
                "source_assignment_path",
                "tensor_name",
            },
            f"roundtrip record {index}",
        )
        expected = expected_reconstructed.get(record["deployment_path"])
        if expected is None or record["deployment_path"] in seen:
            raise DeepSeekV4FP8LinearDifferentialError(
                f"roundtrip record {index} has an unknown or duplicate path"
            )
        artifact, resource, tensor_name = expected
        if record != {
            "deployment_path": artifact.relative_path,
            "sha256": artifact.sha256,
            "size_bytes": artifact.size_bytes,
            "source_assignment_path": resource["source_assignment_path"],
            "tensor_name": tensor_name,
        }:
            raise DeepSeekV4FP8LinearDifferentialError(
                f"roundtrip record {index} differs from tensor resources"
            )
        seen.add(record["deployment_path"])
    roundtrip_identity = dict(roundtrip)
    observed_roundtrip_id = roundtrip_identity.pop("roundtrip_id")
    if (
        roundtrip["schema"] != ROUNDTRIP_SCHEMA
        or roundtrip["application_id"] != manifest["source_application_id"]
        or roundtrip["model_id"] != MODEL_ID
        or roundtrip["status"] != "full_selected_payload_match"
        or roundtrip["checked_artifact_count"] != 2
        or roundtrip["checked_payload_bytes"]
        != sum(value[0].size_bytes for value in expected_reconstructed.values())
        or seen != set(expected_reconstructed)
        or observed_roundtrip_id != _sha256_json(roundtrip_identity)
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "roundtrip identity or accounting differs"
        )

    try:
        instructions = decode(
            _verified_small_bytes(
                artifacts["microcode"], "microcode", maximum=64 * 1024
            )
        )
        verify(instructions)
    except ValueError as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"FP8 linear microcode differs: {exc}"
        ) from exc
    try:
        observed_disassembly = _verified_small_bytes(
            artifacts["microcode_disassembly"],
            "microcode disassembly",
            maximum=256 * 1024,
        ).decode("ascii")
    except UnicodeDecodeError as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            "microcode disassembly is not ASCII"
        ) from exc
    if observed_disassembly != disassemble(instructions):
        raise DeepSeekV4FP8LinearDifferentialError(
            "microcode disassembly differs from the decoded program"
        )

    _scan_artifact_codes(
        artifacts["weight_matrix"], frozenset({0x7F, 0xFF}), "FP8 weight payload"
    )
    _scan_artifact_codes(
        artifacts["scale_table"], frozenset({0xFF}), "E8M0 scale payload"
    )


def _parse_request(
    request: Mapping[str, Any],
    *,
    build_id: str,
    input_features: int,
) -> tuple[tuple[tuple[int, ...], ...], str]:
    _exact_keys(
        request,
        {"build_id", "input_bf16_codes", "model_id", "schema"},
        "FP8 linear request",
    )
    if (
        request["schema"] != REQUEST_SCHEMA
        or request["model_id"] != MODEL_ID
        or request["build_id"] != build_id
    ):
        raise DeepSeekV4FP8LinearDifferentialError("request identity differs")
    raw_rows = request["input_bf16_codes"]
    if (
        not isinstance(raw_rows, list)
        or not 1 <= len(raw_rows) <= MAX_INPUT_ROWS
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            f"request must contain 1 through {MAX_INPUT_ROWS} input rows"
        )
    rows = []
    for row_index, raw_row in enumerate(raw_rows):
        if not isinstance(raw_row, list) or len(raw_row) != input_features:
            raise DeepSeekV4FP8LinearDifferentialError(
                f"input_bf16_codes[{row_index}] width differs"
            )
        rows.append(
            tuple(
                _integer(
                    code,
                    f"input_bf16_codes[{row_index}][{column}]",
                    maximum=0xFFFF,
                )
                for column, code in enumerate(raw_row)
            )
        )
    return tuple(rows), _sha256_json(dict(request))


def _expected_counters(
    *, input_features: int, selected_count: int, input_row_count: int
) -> dict[str, int]:
    result = {
        "completion_events": 1,
        "micro_ops_executed": 2,
        "semantic_operations_executed": 1,
    }
    result.update(
        {
            key: value * input_row_count
            for key, value in _expected_coefficients(
                input_features, selected_count
            ).items()
        }
    )
    return dict(sorted(result.items()))


def _parse_result(
    result: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    source: Mapping[str, Any],
    request_sha256: str,
    input_row_count: int,
    selected_rows: tuple[int, ...],
    expected_counters: Mapping[str, int],
    full_operator: bool,
) -> tuple[tuple[tuple[int, ...], ...], Mapping[str, Any]]:
    _exact_keys(
        result,
        {
            "build_id",
            "counter_reconciliation",
            "counters",
            "deployment_status",
            "evidence_scope",
            "execution_scope",
            "model_id",
            "numeric_status",
            "outputs",
            "request_sha256",
            "schema",
            "source_application_status",
            "status",
        },
        "FP8 linear result",
    )
    expected_schema = FULL_RESULT_SCHEMA if full_operator else RESULT_SCHEMA
    expected_scope = (
        "complete_fp8_linear_operator"
        if full_operator
        else "selected_output_rows_arithmetic_slice_only"
    )
    if (
        result["schema"] != expected_schema
        or result["model_id"] != MODEL_ID
        or result["build_id"] != manifest["build_id"]
        or result["request_sha256"] != request_sha256
        or result["deployment_status"] != manifest["status"]
        or result["evidence_scope"] != source["evidence_scope"]
        or result["source_application_status"] != source["application_status"]
        or result["execution_scope"] != expected_scope
        or result["counter_reconciliation"] != "exact"
        or result["status"] != "pass"
        or result["counters"] != expected_counters
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear result identity or counters differ"
        )
    numeric = result["numeric_status"]
    if not isinstance(numeric, Mapping):
        raise DeepSeekV4FP8LinearDifferentialError("numeric status is absent")
    _exact_keys(
        numeric,
        {
            "activation_saturated_block_count",
            "output_saturated_element_count",
            "poison",
        },
        "numeric status",
    )
    activation_saturations = _integer(
        numeric["activation_saturated_block_count"],
        "activation_saturated_block_count",
    )
    output_saturations = _integer(
        numeric["output_saturated_element_count"],
        "output_saturated_element_count",
    )
    if (
        numeric["poison"] is not False
        or activation_saturations
        > input_row_count * (expected_counters["activation_blocks_quantized"] // input_row_count)
        or output_saturations > input_row_count * len(selected_rows)
    ):
        raise DeepSeekV4FP8LinearDifferentialError("numeric status is impossible")
    outputs = result["outputs"]
    if not isinstance(outputs, list) or len(outputs) != 1:
        raise DeepSeekV4FP8LinearDifferentialError("FP8 linear output list differs")
    output = outputs[0]
    if not isinstance(output, Mapping):
        raise DeepSeekV4FP8LinearDifferentialError("FP8 linear output is malformed")
    _exact_keys(
        output,
        {"dtype", "id", "logical_output_rows", "shape", "values"},
        "FP8 linear output",
    )
    if (
        output["dtype"] != "BF16_BITS"
        or output["id"] != "output_bf16_codes"
        or output["logical_output_rows"] != list(selected_rows)
        or output["shape"] != [input_row_count, len(selected_rows)]
    ):
        raise DeepSeekV4FP8LinearDifferentialError("FP8 output metadata differs")
    raw_values = output["values"]
    if not isinstance(raw_values, list) or len(raw_values) != input_row_count:
        raise DeepSeekV4FP8LinearDifferentialError("FP8 output row extent differs")
    values = []
    for row_index, raw_row in enumerate(raw_values):
        if not isinstance(raw_row, list) or len(raw_row) != len(selected_rows):
            raise DeepSeekV4FP8LinearDifferentialError(
                f"FP8 output row {row_index} width differs"
            )
        values.append(
            tuple(
                _integer(
                    code,
                    f"outputs[0].values[{row_index}][{column}]",
                    maximum=0xFFFF,
                )
                for column, code in enumerate(raw_row)
            )
        )
    return tuple(values), numeric


class _RowCollector:
    """Retain selected fixed-width rows while hashing the full locked tensor."""

    def __init__(self, row_indices: Sequence[int], row_bytes: int):
        self._row_bytes = row_bytes
        self._rows = tuple(sorted(set(row_indices)))
        self._buffers = {row: bytearray(row_bytes) for row in self._rows}
        self._filled = {row: 0 for row in self._rows}
        self._offset = 0

    def consume(self, chunk: bytes) -> None:
        chunk_start = self._offset
        chunk_stop = chunk_start + len(chunk)
        for row in self._rows:
            row_start = row * self._row_bytes
            row_stop = row_start + self._row_bytes
            overlap_start = max(chunk_start, row_start)
            overlap_stop = min(chunk_stop, row_stop)
            if overlap_start >= overlap_stop:
                continue
            source_start = overlap_start - chunk_start
            destination_start = overlap_start - row_start
            length = overlap_stop - overlap_start
            self._buffers[row][destination_start : destination_start + length] = chunk[
                source_start : source_start + length
            ]
            self._filled[row] += length
        self._offset = chunk_stop

    def finish(self, expected_bytes: int) -> dict[int, bytes]:
        if self._offset != expected_bytes:
            raise DeepSeekV4FP8LinearDifferentialError(
                "locked weight stream length differs from metadata"
            )
        incomplete = [
            row for row, filled in self._filled.items() if filled != self._row_bytes
        ]
        if incomplete:
            raise DeepSeekV4FP8LinearDifferentialError(
                f"locked weight stream omitted selected rows {incomplete}"
            )
        return {row: bytes(value) for row, value in self._buffers.items()}


class _BoundedCollector:
    def __init__(self, maximum_bytes: int):
        self._maximum_bytes = maximum_bytes
        self._payload = bytearray()

    def consume(self, chunk: bytes) -> None:
        if len(self._payload) + len(chunk) > self._maximum_bytes:
            raise DeepSeekV4FP8LinearDifferentialError(
                "locked scale table exceeds the independent checker bound"
            )
        self._payload.extend(chunk)

    def finish(self, expected_bytes: int) -> bytes:
        if len(self._payload) != expected_bytes:
            raise DeepSeekV4FP8LinearDifferentialError(
                "locked scale stream length differs from metadata"
            )
        return bytes(self._payload)


def _verify_deepseek_v4_fp8_linear_execution(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    deployment_root: Path,
    request_path: Path,
    result_path: Path,
    stack: ExitStack,
) -> dict[str, Any]:
    """Compare persisted FP8 execution to the original locked tensors."""

    validate_checkpoint_lock(lock)
    root = Path(deployment_root).resolve()
    if not root.is_dir():
        raise DeepSeekV4FP8LinearDifferentialError(
            f"FP8 linear deployment is not a directory: {root}"
        )
    root_descriptor, root_fingerprint = _open_root(stack, root)
    manifest_path = root / "deployment_manifest.json"
    if manifest_path.is_symlink():
        raise DeepSeekV4FP8LinearDifferentialError(
            "deployment manifest must not be a symlink"
        )
    manifest_descriptor = _open_relative(
        stack,
        root_descriptor,
        "deployment_manifest.json",
        "deployment manifest",
    )
    manifest_payload, manifest_fingerprint = _descriptor_bytes(
        manifest_descriptor,
        "deployment manifest",
        maximum=1024 * 1024,
    )
    manifest = _strict_json_payload(manifest_payload, "deployment manifest")
    artifacts, full_operator = _deployment_artifacts(
        root,
        manifest,
        stack=stack,
        root_descriptor=root_descriptor,
    )
    semantic = _verified_json(artifacts["semantic_ir"], "semantic IR")
    input_features, output_features, selected_rows, source = _dimensions_and_source(
        semantic, manifest, lock, full_operator=full_operator
    )
    if source["evidence_scope"] == "official_checkpoint":
        validate_official_checkpoint_lock(lock, load_official_config())
    tensors = _verified_json(artifacts["tensor_manifest"], "tensor manifest")
    weight_resource, scale_resource = _tensor_resources(
        tensors,
        artifacts,
        input_features=input_features,
        output_features=output_features,
        selected_rows=selected_rows,
        evidence_scope=source["evidence_scope"],
        full_operator=full_operator,
    )
    _verify_contract_artifacts(
        artifacts,
        manifest,
        input_features=input_features,
        selected_count=len(selected_rows),
        weight_resource=weight_resource,
        scale_resource=scale_resource,
        full_operator=full_operator,
    )
    request = _strict_json_payload(
        _small_bytes(
            Path(request_path),
            "execution request",
            maximum=(
                JSON_FIXED_OVERHEAD_BYTES
                + MAX_INPUT_ROWS * input_features * 6
            ),
        ),
        "execution request",
    )
    inputs, request_sha256 = _parse_request(
        request,
        build_id=manifest["build_id"],
        input_features=input_features,
    )
    expected_counters = _expected_counters(
        input_features=input_features,
        selected_count=len(selected_rows),
        input_row_count=len(inputs),
    )
    product_accumulates = len(inputs) * len(selected_rows) * input_features
    if product_accumulates > MAX_PRODUCTS_PER_REQUEST:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear request exceeds the checker work budget"
        )
    result = _strict_json_payload(
        _small_bytes(
            Path(result_path),
            "execution result",
            maximum=(
                JSON_FIXED_OVERHEAD_BYTES
                + len(inputs) * len(selected_rows) * 6
            ),
        ),
        "execution result",
    )
    observed, observed_numeric = _parse_result(
        result,
        manifest=manifest,
        source=source,
        request_sha256=request_sha256,
        input_row_count=len(inputs),
        selected_rows=selected_rows,
        expected_counters=expected_counters,
        full_operator=full_operator,
    )

    blocks = input_features // BLOCK_SIZE
    scale_rows = (output_features + BLOCK_SIZE - 1) // BLOCK_SIZE
    weight_collector = _RowCollector(selected_rows, input_features)
    scale_collector = _BoundedCollector(scale_rows * blocks)
    with LockedCheckpointReader(snapshot, lock) as reader:
        weight_record = reader.consume_tensor_payload(
            WEIGHT_NAME, weight_collector.consume
        )
        scale_record = reader.consume_tensor_payload(SCALE_NAME, scale_collector.consume)
    if (
        weight_record["dtype"] != "F8_E4M3"
        or weight_record["shape"] != [output_features, input_features]
        or weight_record["size_bytes"] != output_features * input_features
        or scale_record["dtype"] != "F8_E8M0"
        or scale_record["shape"] != [scale_rows, blocks]
        or scale_record["size_bytes"] != scale_rows * blocks
        or weight_resource["sha256"] != weight_record["payload_sha256"]
        or weight_resource["size_bytes"] != weight_record["size_bytes"]
        or scale_resource["sha256"] != scale_record["payload_sha256"]
        or scale_resource["size_bytes"] != scale_record["size_bytes"]
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "deployment tensors differ from original locked tensor identities"
        )
    selected_weight_rows = weight_collector.finish(weight_record["size_bytes"])
    scale_payload = scale_collector.finish(scale_record["size_bytes"])
    scales = tuple(
        tuple(scale_payload[start : start + blocks])
        for start in range(0, len(scale_payload), blocks)
    )
    try:
        ordered_weight_rows = tuple(
            tuple(selected_weight_rows[row]) for row in selected_rows
        )
        if full_operator:
            expected = dense_fp8_linear_bf16(inputs, ordered_weight_rows, scales)
        else:
            expected = dense_fp8_linear_selected_rows_bf16(
                inputs,
                ordered_weight_rows,
                scales,
                output_row_indices=selected_rows,
                declared_output_count=output_features,
            )
    except MatrixReferenceError as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"independent FP8 reference rejected locked execution: {exc}"
        ) from exc
    expected_numeric = {
        "activation_saturated_block_count": (
            expected.activation_saturated_block_count
        ),
        "output_saturated_element_count": expected.output_saturated_element_count,
        "poison": False,
    }
    if observed != expected.values:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 output differs from locked checkpoint semantics"
        )
    if dict(observed_numeric) != expected_numeric:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 saturation status differs from independent semantics"
        )

    current_manifest_payload, _ = _descriptor_bytes(
        manifest_descriptor,
        "deployment manifest",
        maximum=1024 * 1024,
        expected_fingerprint=manifest_fingerprint,
    )
    if current_manifest_payload != manifest_payload:
        raise DeepSeekV4FP8LinearDifferentialError(
            "deployment manifest changed during independent checking"
        )
    for artifact in artifacts.values():
        digest, size, _ = _descriptor_hash(
            artifact.descriptor,
            f"deployment artifact {artifact.relative_path!r}",
            expected_fingerprint=artifact.fingerprint,
        )
        if (digest, size) != (artifact.sha256, artifact.size_bytes):
            raise DeepSeekV4FP8LinearDifferentialError(
                f"deployment artifact {artifact.relative_path!r} changed during checking"
            )
    with ExitStack() as current_stack:
        current_root_descriptor, current_root_fingerprint = _open_root(
            current_stack, root
        )
        if current_root_fingerprint != root_fingerprint:
            raise DeepSeekV4FP8LinearDifferentialError(
                "deployment root changed during independent checking"
            )
        current_manifest_descriptor = _open_relative(
            current_stack,
            current_root_descriptor,
            "deployment_manifest.json",
            "current deployment manifest",
        )
        current_payload, current_fingerprint = _descriptor_bytes(
            current_manifest_descriptor,
            "current deployment manifest",
            maximum=1024 * 1024,
        )
        if (
            current_payload != manifest_payload
            or current_fingerprint != manifest_fingerprint
        ):
            raise DeepSeekV4FP8LinearDifferentialError(
                "deployment manifest was replaced during independent checking"
            )
        for artifact in artifacts.values():
            current_descriptor = _open_relative(
                current_stack,
                current_root_descriptor,
                artifact.relative_path,
                f"current deployment artifact {artifact.relative_path!r}",
            )
            digest, size, current_fingerprint = _descriptor_hash(
                current_descriptor,
                f"current deployment artifact {artifact.relative_path!r}",
            )
            if (
                (digest, size) != (artifact.sha256, artifact.size_bytes)
                or current_fingerprint != artifact.fingerprint
            ):
                raise DeepSeekV4FP8LinearDifferentialError(
                    f"deployment artifact {artifact.relative_path!r} was replaced "
                    "during independent checking"
                )
    shape = [len(inputs), len(selected_rows)]
    comparison = {
        "element_count": math.prod(shape),
        "expected_sha256": _sha256_json(expected.values),
        "observed_sha256": _sha256_json(observed),
        "output": "output_bf16_codes",
        "shape": shape,
        "status": "exact",
    }
    source_tensors = [
        {
            "deployment_sha256": resource["sha256"],
            "dtype": record["dtype"],
            "name": record["name"],
            "payload_sha256": record["payload_sha256"],
            "shape": record["shape"],
            "size_bytes": record["size_bytes"],
        }
        for resource, record in (
            (weight_resource, weight_record),
            (scale_resource, scale_record),
        )
    ]
    common_body: dict[str, Any] = {
        "build_id": manifest["build_id"],
        "checkpoint_lock_id": lock["lock_id"],
        "comparison": comparison,
        "counters": expected_counters,
        "input_row_count": len(inputs),
        "model_id": MODEL_ID,
        "numeric_status": expected_numeric,
        "request_sha256": request_sha256,
        "source_application_id": source["application_id"],
        "source_tensors": source_tensors,
    }
    if full_operator:
        body = {
            **common_body,
            "claim_boundary": (
                "Exact complete-output layer-0 query-A FP8 linear differential "
                "for supplied BF16 rows only; not input normalization, attention, "
                "a transformer block, or full model."
            ),
            "output_row_count": output_features,
            "schema": FULL_DIFFERENTIAL_SCHEMA,
            "status": "exact_locked_checkpoint_complete_fp8_linear_differential",
        }
    else:
        body = {
            **common_body,
            "claim_boundary": (
                "Exact selected-row layer-0 query-A FP8 linear differential only; "
                "not the complete projection, attention, a transformer block, or full model."
            ),
            "schema": DIFFERENTIAL_SCHEMA,
            "selected_output_rows": list(selected_rows),
            "status": "exact_locked_checkpoint_selected_row_differential",
        }
    body["differential_id"] = _sha256_json(body)
    return body


def verify_deepseek_v4_fp8_linear_execution(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    deployment_root: Path,
    request_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    """Independently verify one stable artifact tree against locked tensors."""

    with ExitStack() as stack:
        return _verify_deepseek_v4_fp8_linear_execution(
            snapshot=snapshot,
            lock=lock,
            deployment_root=deployment_root,
            request_path=request_path,
            result_path=result_path,
            stack=stack,
        )


__all__ = [
    "DIFFERENTIAL_SCHEMA",
    "FULL_DIFFERENTIAL_SCHEMA",
    "DeepSeekV4FP8LinearDifferentialError",
    "verify_deepseek_v4_fp8_linear_execution",
]
