"""Artifact-only service engine for DeepSeek V4 FP8 linear deployments."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import stat
import struct
from typing import Any, Iterator

from compiler.frontend.deepseek_v4 import (
    MODEL_ID,
    OFFICIAL_CHECKPOINT_LOCK_ID,
    REPOSITORY,
    REVISION,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json
from compiler.microcode.deepseek_v4_fp8_linear import (
    ABI_MAJOR,
    ABI_MINOR,
    DENSE_BLOCK_SIZE,
    INPUT_BF16,
    OUTPUT_BF16,
    Instruction,
    Opcode,
    decode,
    disassemble,
    verify,
)
from runtime.service_engine.fp8_numeric import (
    FP8ServiceNumericError,
    execute_selected_rows,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_fp8_linear_deployment.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_fp8_linear_slice.v1"
TENSOR_SCHEMA = "opentallas.deepseek_v4_fp8_linear_tensors.v1"
EXPECTATION_SCHEMA = "opentallas.deepseek_v4_fp8_linear_expectations.v1"
COVERAGE_SCHEMA = "opentallas.deepseek_v4_fp8_linear_coverage.v1"
ROUNDTRIP_SCHEMA = "opentallas.deepseek_v4_fp8_linear_roundtrip.v1"
REQUEST_SCHEMA = "opentallas.deepseek_v4_fp8_linear_request.v1"
RESULT_SCHEMA = "opentallas.deepseek_v4_fp8_linear_result.v1"
NUMERIC_PROFILE = "deepseek_v4_dense_fp8_selected_rows_v1"
FULL_DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_deployment.v1"
FULL_SEMANTIC_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full.v1"
FULL_TENSOR_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_tensors.v1"
FULL_COVERAGE_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_coverage.v1"
FULL_RESULT_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_result.v1"
FULL_NUMERIC_PROFILE = "deepseek_v4_dense_fp8_full_v1"
MAX_INPUT_ROWS = 4
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
_COUNTER_KEYS = frozenset(
    {
        "activation_blocks_quantized",
        "activation_values_quantized",
        "bf16_outputs_written",
        "binary32_block_reduction_adds",
        "binary32_product_accumulates",
        "completion_events",
        "logical_input_bytes_read",
        "logical_output_bytes_written",
        "logical_rom_bytes_read",
        "matrix_block_dots",
        "micro_ops_executed",
        "semantic_operations_executed",
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


class DeepSeekV4FP8LinearServiceEngineError(RuntimeError):
    """Raised when FP8 artifacts, execution, numerics, or counters differ."""


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4FP8LinearServiceEngineError(
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
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"{label} must be an integer in {bound}"
        )
    return value


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"{label} must be a lowercase SHA-256"
        )
    return value


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"cannot hash FP8 linear artifact {path.name!r}: {exc}"
        ) from exc
    return digest.hexdigest(), size


def _safe_file(root: Path, value: Any, label: str) -> tuple[str, Path]:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"{label} is not canonical POSIX"
        )
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4FP8LinearServiceEngineError(f"{label} traverses a symlink")
    try:
        current.resolve().relative_to(root)
    except ValueError as exc:
        raise DeepSeekV4FP8LinearServiceEngineError(f"{label} escapes deployment") from exc
    if not current.is_file():
        raise DeepSeekV4FP8LinearServiceEngineError(f"{label} is not a regular file")
    return value, current


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return load_strict_json(path)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"cannot load {label}: {exc}"
        ) from exc


def _file_fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _small_bytes(path: Path, label: str, maximum: int = 1024 * 1024) -> bytes:
    """Read one stable, bounded regular file without following its final symlink."""

    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_NONBLOCK")
        or not hasattr(os, "O_CLOEXEC")
        or not hasattr(os, "pread")
    ):
        raise DeepSeekV4FP8LinearServiceEngineError(
            "platform lacks race-resistant bounded file operations"
        )
    path = Path(path)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK

    def open_descriptor(context: str) -> int:
        try:
            return os.open(path, flags)
        except OSError as exc:
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"cannot {context} {label} without following symlinks: {exc}"
            ) from exc

    try:
        descriptor = open_descriptor("open")
        try:
            before = os.fstat(descriptor)
            before_fingerprint = _file_fingerprint(before)
            if not stat.S_ISREG(before.st_mode):
                raise DeepSeekV4FP8LinearServiceEngineError(
                    f"{label} is not a regular file"
                )
            if before.st_size > maximum:
                raise DeepSeekV4FP8LinearServiceEngineError(
                    f"{label} exceeds its {maximum}-byte runtime bound"
                )
            payload = bytearray()
            offset = 0
            while offset < before.st_size:
                chunk = os.pread(
                    descriptor,
                    min(1024 * 1024, before.st_size - offset),
                    offset,
                )
                if not chunk:
                    break
                payload.extend(chunk)
                offset += len(chunk)
            if (
                len(payload) != before.st_size
                or _file_fingerprint(os.fstat(descriptor)) != before_fingerprint
            ):
                raise DeepSeekV4FP8LinearServiceEngineError(
                    f"{label} changed while the runtime read it"
                )
        finally:
            os.close(descriptor)

        current_descriptor = open_descriptor("reopen")
        try:
            current = os.fstat(current_descriptor)
            if (
                not stat.S_ISREG(current.st_mode)
                or _file_fingerprint(current) != before_fingerprint
            ):
                raise DeepSeekV4FP8LinearServiceEngineError(
                    f"{label} was replaced while the runtime read it"
                )
        finally:
            os.close(current_descriptor)
        return bytes(payload)
    except DeepSeekV4FP8LinearServiceEngineError:
        raise
    except OSError as exc:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"cannot read {label}: {exc}"
        ) from exc


@dataclass(frozen=True)
class _Artifact:
    relative_path: str
    role: str
    sha256: str
    size_bytes: int
    path: Path


@dataclass(frozen=True)
class DeepSeekV4FP8LinearDeployment:
    root: Path
    manifest: dict[str, Any]
    semantic: dict[str, Any]
    expectations: dict[str, Any]
    instructions: tuple[Instruction, ...]
    weight_path: Path
    scale_path: Path
    selected_rows: tuple[int, ...]
    input_features: int
    output_features: int
    evidence_scope: str
    full_operator: bool
    manifest_artifact: _Artifact
    artifacts: tuple[_Artifact, ...]


def _strict_json_payload(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekV4FP8LinearServiceEngineError(
                    f"{label} has duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                DeepSeekV4FP8LinearServiceEngineError(
                    f"{label} has non-finite JSON number {token!r}"
                )
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"cannot decode {label}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise DeepSeekV4FP8LinearServiceEngineError(f"{label} is not a JSON object")
    if canonical_json_bytes(value) != payload:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"{label} is not canonical JSON"
        )
    return value


def _verified_small_bytes(
    artifact: _Artifact, label: str, maximum: int = 1024 * 1024
) -> bytes:
    payload = _small_bytes(artifact.path, label, maximum)
    if (hashlib.sha256(payload).hexdigest(), len(payload)) != (
        artifact.sha256,
        artifact.size_bytes,
    ):
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"{label} differs from its deployment artifact record"
        )
    return payload


def _verified_json(artifact: _Artifact, label: str) -> dict[str, Any]:
    return _strict_json_payload(_verified_small_bytes(artifact, label), label)


def _verify_artifacts(
    root: Path, manifest: Mapping[str, Any]
) -> tuple[dict[str, _Artifact], list[dict[str, Any]]]:
    raw = manifest.get("artifacts")
    if not isinstance(raw, list) or not raw:
        raise DeepSeekV4FP8LinearServiceEngineError("artifact table is absent")
    by_role: dict[str, _Artifact] = {}
    seen_paths: set[str] = set()
    retained = []
    previous_path: str | None = None
    for index, record in enumerate(raw):
        if not isinstance(record, Mapping):
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"artifact record {index} is not an object"
            )
        _exact_keys(
            record,
            {"path", "role", "sha256", "size_bytes"},
            f"artifact record {index}",
        )
        relative, path = _safe_file(root, record["path"], f"artifact {index}.path")
        role = record["role"]
        if not isinstance(role, str) or not role or role in by_role:
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"artifact record {index} has duplicate or invalid role"
            )
        if relative in seen_paths:
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"artifact record {index} duplicates a path"
            )
        if previous_path is not None and relative <= previous_path:
            raise DeepSeekV4FP8LinearServiceEngineError(
                "artifact table must be strictly path-sorted"
            )
        previous_path = relative
        seen_paths.add(relative)
        digest = _hash(record["sha256"], f"artifact {relative}.sha256")
        size = _integer(record["size_bytes"], f"artifact {relative}.size_bytes")
        if _sha256_file(path) != (digest, size):
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"artifact {relative!r} differs from deployment manifest"
            )
        by_role[role] = _Artifact(relative, role, digest, size, path)
        retained.append(dict(record))
    if set(by_role) != _ROLES:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"artifact roles differ: missing={sorted(_ROLES - by_role.keys())}, "
            f"extra={sorted(by_role.keys() - _ROLES)}"
        )
    return by_role, retained


def _verify_manifest(
    manifest: dict[str, Any], artifacts: list[dict[str, Any]], *, full_operator: bool
) -> None:
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
        "deployment manifest",
    )
    expected_schema = FULL_DEPLOYMENT_SCHEMA if full_operator else DEPLOYMENT_SCHEMA
    if manifest["schema"] != expected_schema or manifest["model_id"] != MODEL_ID:
        raise DeepSeekV4FP8LinearServiceEngineError(
            "deployment schema or model identity differs"
        )
    compiler = manifest["compiler"]
    if not isinstance(compiler, Mapping):
        raise DeepSeekV4FP8LinearServiceEngineError("compiler identity is absent")
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
        raise DeepSeekV4FP8LinearServiceEngineError("compiler identity differs")
    abi = manifest["microcode_abi"]
    if abi != {
        "major": ABI_MAJOR,
        "minor": ABI_MINOR,
        "name": "deepseek_v4_fp8_linear",
    }:
        raise DeepSeekV4FP8LinearServiceEngineError("microcode ABI differs")
    application_id = _hash(
        manifest["source_application_id"], "source_application_id"
    )
    identity = {
        "artifacts": artifacts,
        "compiler_version": compiler["version"],
        "microcode_abi": abi,
        "model_id": MODEL_ID,
        "source_application_id": application_id,
    }
    if manifest["build_id"] != hashlib.sha256(
        canonical_json_bytes(identity)
    ).hexdigest():
        raise DeepSeekV4FP8LinearServiceEngineError(
            "deployment build_id does not bind its artifacts"
        )
    expected_claims = (
        _FULL_DEPLOYMENT_CLAIMS if full_operator else _DEPLOYMENT_CLAIMS
    )
    if manifest["claim_boundary"] != expected_claims:
        raise DeepSeekV4FP8LinearServiceEngineError("deployment claim boundary differs")
    allowed_statuses = (
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
    if manifest["status"] not in allowed_statuses:
        raise DeepSeekV4FP8LinearServiceEngineError("deployment status is unsupported")


def _verify_semantic(
    semantic: dict[str, Any], manifest: Mapping[str, Any], *, full_operator: bool
) -> tuple[int, int, tuple[int, ...], str]:
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
    expected_numeric = FULL_NUMERIC_PROFILE if full_operator else NUMERIC_PROFILE
    expected_claim = _FULL_SEMANTIC_CLAIM if full_operator else _SEMANTIC_CLAIM
    expected_operation = {
        "input": "input_bf16_codes",
        "kind": "FP8_LINEAR" if full_operator else "FP8_LINEAR_SELECTED_ROWS",
        "output": "output_bf16_codes",
        "scale_resource": "layers.0.attn.wq_a.scale",
        "weight_resource": "layers.0.attn.wq_a.weight",
    }
    if (
        semantic["schema"] != expected_schema
        or semantic["model_id"] != MODEL_ID
        or semantic["numeric_profile"] != expected_numeric
        or semantic["claim_boundary"] != expected_claim
        or semantic["operation"] != expected_operation
    ):
        raise DeepSeekV4FP8LinearServiceEngineError("FP8 linear semantics differ")
    dimensions = semantic["dimensions"]
    if not isinstance(dimensions, Mapping):
        raise DeepSeekV4FP8LinearServiceEngineError("semantic dimensions are absent")
    dimension_keys = {"block_size", "input_features", "output_features"}
    if not full_operator:
        dimension_keys.add("selected_output_rows")
    _exact_keys(dimensions, dimension_keys, "semantic dimensions")
    input_features = _integer(
        dimensions["input_features"],
        "dimensions.input_features",
        minimum=1,
        maximum=MAX_FEATURE_EXTENT,
    )
    output_features = _integer(
        dimensions["output_features"],
        "dimensions.output_features",
        minimum=1,
        maximum=MAX_FEATURE_EXTENT,
    )
    if dimensions["block_size"] != DENSE_BLOCK_SIZE or input_features % DENSE_BLOCK_SIZE:
        raise DeepSeekV4FP8LinearServiceEngineError(
            "semantic block size or reduction extent differs"
        )
    weight_bytes = input_features * output_features
    if weight_bytes > MAX_WEIGHT_PAYLOAD_BYTES:
        raise DeepSeekV4FP8LinearServiceEngineError(
            "FP8 weight extent exceeds the runtime memory budget"
        )
    if full_operator and weight_bytes > MAX_FULL_PRODUCTS_PER_INPUT_ROW:
        raise DeepSeekV4FP8LinearServiceEngineError(
            "complete FP8 operator exceeds the runtime work budget"
        )
    if full_operator:
        rows = tuple(range(output_features))
    else:
        raw_rows = dimensions["selected_output_rows"]
        if not isinstance(raw_rows, list):
            raise DeepSeekV4FP8LinearServiceEngineError(
                "selected output rows are absent"
            )
        rows = tuple(
            _integer(row, f"selected_output_rows[{index}]")
            for index, row in enumerate(raw_rows)
        )
        if (
            not rows
            or rows != tuple(sorted(set(rows)))
            or rows[-1] >= output_features
            or len(rows) > 64
        ):
            raise DeepSeekV4FP8LinearServiceEngineError(
                "selected output rows are not legal logical indices"
            )
    source = semantic["source"]
    if not isinstance(source, Mapping):
        raise DeepSeekV4FP8LinearServiceEngineError("semantic source is absent")
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
        "semantic source",
    )
    if source["application_id"] != manifest["source_application_id"]:
        raise DeepSeekV4FP8LinearServiceEngineError("application identity differs")
    for key in ("application_id", "checkpoint_lock_id", "verification_id"):
        _hash(source[key], f"semantic source {key}")
    evidence_scope = source["evidence_scope"]
    if evidence_scope not in {"development_fixture", "official_checkpoint"}:
        raise DeepSeekV4FP8LinearServiceEngineError("evidence scope is unsupported")
    expected_status = (
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
    if manifest["status"] != expected_status:
        raise DeepSeekV4FP8LinearServiceEngineError(
            "deployment status overstates evidence scope"
        )
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
        raise DeepSeekV4FP8LinearServiceEngineError(
            "application status differs from evidence scope"
        )
    if evidence_scope == "official_checkpoint":
        if (
            source["repository"],
            source["revision"],
            source["checkpoint_lock_id"],
            input_features,
            output_features,
        ) != (
            REPOSITORY,
            REVISION,
            OFFICIAL_CHECKPOINT_LOCK_ID,
            4096,
            1024,
        ):
            raise DeepSeekV4FP8LinearServiceEngineError(
                "official FP8 linear source or dimensions differ"
            )
    return input_features, output_features, rows, evidence_scope


def _artifact_path(
    artifacts: Mapping[str, _Artifact], record: Mapping[str, Any], role: str
) -> _Artifact:
    artifact = artifacts[role]
    if (
        record.get("path") != artifact.relative_path
        or record.get("sha256") != artifact.sha256
        or record.get("size_bytes") != artifact.size_bytes
    ):
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"tensor resource differs from artifact role {role!r}"
        )
    return artifact


def _verify_tensors(
    tensors: dict[str, Any],
    artifacts: Mapping[str, _Artifact],
    input_features: int,
    output_features: int,
    selected_rows: tuple[int, ...],
    *,
    full_operator: bool,
) -> tuple[_Artifact, _Artifact]:
    _exact_keys(
        tensors, {"output_selection", "scale", "schema", "weight"}, "tensor manifest"
    )
    expected_schema = FULL_TENSOR_SCHEMA if full_operator else TENSOR_SCHEMA
    if tensors["schema"] != expected_schema:
        raise DeepSeekV4FP8LinearServiceEngineError("tensor schema differs")
    weight = tensors["weight"]
    scale = tensors["scale"]
    selection = tensors["output_selection"]
    if not all(isinstance(record, Mapping) for record in (weight, scale, selection)):
        raise DeepSeekV4FP8LinearServiceEngineError("tensor resources are malformed")
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
    weight_artifact = _artifact_path(artifacts, weight, "weight_matrix")
    scale_artifact = _artifact_path(artifacts, scale, "scale_table")
    selection_artifact = _artifact_path(artifacts, selection, "output_selection")
    scale_shape = [
        (output_features + DENSE_BLOCK_SIZE - 1) // DENSE_BLOCK_SIZE,
        input_features // DENSE_BLOCK_SIZE,
    ]
    if (
        weight["dtype"] != "F8_E4M3"
        or weight["shape"] != [output_features, input_features]
        or weight_artifact.size_bytes != output_features * input_features
        or scale["dtype"] != "F8_E8M0"
        or scale["shape"] != scale_shape
        or scale_artifact.size_bytes != scale_shape[0] * scale_shape[1]
        or weight["replicated_ranks"] != scale["replicated_ranks"]
        or not isinstance(weight["replicated_ranks"], list)
        or not weight["replicated_ranks"]
        or weight["replicated_ranks"]
        != list(range(len(weight["replicated_ranks"])))
        or not isinstance(weight["source_assignment_path"], str)
        or not isinstance(scale["source_assignment_path"], str)
    ):
        raise DeepSeekV4FP8LinearServiceEngineError("weight or scale metadata differs")
    selection_payload = _verified_small_bytes(
        selection_artifact,
        "output selection",
        maximum=(output_features if full_operator else 64) * 4,
    )
    if (
        selection["dtype"] != "U32"
        or selection["rows"] != list(selected_rows)
        or selection_artifact.size_bytes != len(selected_rows) * 4
        or struct.unpack(f"<{len(selected_rows)}I", selection_payload) != selected_rows
    ):
        raise DeepSeekV4FP8LinearServiceEngineError("output selection bytes differ")
    return weight_artifact, scale_artifact


def _scan_codes(
    artifact: _Artifact, forbidden: frozenset[int], label: str
) -> None:
    digest = hashlib.sha256()
    size = 0
    try:
        with artifact.path.open("rb") as handle:
            offset = 0
            while chunk := handle.read(8 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                for index, code in enumerate(chunk):
                    if code in forbidden:
                        raise DeepSeekV4FP8LinearServiceEngineError(
                            f"{label} contains reserved code 0x{code:02x} at "
                            f"byte {offset + index}"
                        )
                offset += len(chunk)
    except OSError as exc:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"cannot validate {label}: {exc}"
        ) from exc
    if (digest.hexdigest(), size) != (artifact.sha256, artifact.size_bytes):
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"{label} changed between artifact verification and code scan"
        )


def _expected_coefficients(
    input_features: int, selected_count: int
) -> dict[str, int]:
    blocks = input_features // DENSE_BLOCK_SIZE
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


def _verify_expectations(
    value: dict[str, Any], input_features: int, selected_count: int
) -> None:
    _exact_keys(
        value,
        {
            "counter_coefficients_per_input_row",
            "fixed_counters",
            "hardware_accounting",
            "schema",
        },
        "execution expectations",
    )
    if value["schema"] != EXPECTATION_SCHEMA:
        raise DeepSeekV4FP8LinearServiceEngineError("expectation schema differs")
    if value["counter_coefficients_per_input_row"] != _expected_coefficients(
        input_features, selected_count
    ) or value["fixed_counters"] != {
        "completion_events": 1,
        "micro_ops_executed": 2,
        "semantic_operations_executed": 1,
    }:
        raise DeepSeekV4FP8LinearServiceEngineError("counter contract differs")
    hardware = value["hardware_accounting"]
    if (
        not isinstance(hardware, Mapping)
        or set(hardware) != {"cycles", "hbm_transactions", "stalls", "status"}
        or hardware["status"]
        != "not modeled by the functional FP8 linear slice"
        or any(hardware[key] is not None for key in ("cycles", "hbm_transactions", "stalls"))
    ):
        raise DeepSeekV4FP8LinearServiceEngineError(
            "functional slice contains speculative hardware accounting"
        )


def _verify_auxiliary(
    coverage: dict[str, Any],
    roundtrip: dict[str, Any],
    manifest: Mapping[str, Any],
    artifacts: Mapping[str, _Artifact],
    *,
    full_operator: bool,
) -> None:
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
        raise DeepSeekV4FP8LinearServiceEngineError("coverage ledger differs")
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
    reconstructed = roundtrip["reconstructed"]
    expected_payloads = {
        artifacts["weight_matrix"].relative_path: artifacts["weight_matrix"],
        artifacts["scale_table"].relative_path: artifacts["scale_table"],
    }
    if not isinstance(reconstructed, list) or len(reconstructed) != 2:
        raise DeepSeekV4FP8LinearServiceEngineError("roundtrip records differ")
    seen = set()
    for index, record in enumerate(reconstructed):
        if not isinstance(record, Mapping):
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"roundtrip record {index} is malformed"
            )
        artifact = expected_payloads.get(record.get("deployment_path"))
        if (
            artifact is None
            or artifact.relative_path in seen
            or record.get("sha256") != artifact.sha256
            or record.get("size_bytes") != artifact.size_bytes
        ):
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"roundtrip record {index} differs"
            )
        seen.add(artifact.relative_path)
    identity = dict(roundtrip)
    observed_id = identity.pop("roundtrip_id")
    if (
        roundtrip["schema"] != ROUNDTRIP_SCHEMA
        or roundtrip["model_id"] != MODEL_ID
        or roundtrip["application_id"] != manifest["source_application_id"]
        or roundtrip["status"] != "full_selected_payload_match"
        or roundtrip["checked_artifact_count"] != 2
        or roundtrip["checked_payload_bytes"]
        != sum(artifact.size_bytes for artifact in expected_payloads.values())
        or seen != set(expected_payloads)
        or observed_id != hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    ):
        raise DeepSeekV4FP8LinearServiceEngineError("roundtrip evidence differs")


def load_deepseek_v4_fp8_linear_deployment(
    deployment_dir: Path,
) -> DeepSeekV4FP8LinearDeployment:
    root = Path(deployment_dir).resolve()
    if not root.is_dir():
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"FP8 linear deployment is not a directory: {root}"
        )
    manifest_path = root / "deployment_manifest.json"
    if manifest_path.is_symlink():
        raise DeepSeekV4FP8LinearServiceEngineError(
            "deployment manifest must not be a symlink"
        )
    manifest_payload = _small_bytes(
        manifest_path, "deployment manifest", maximum=1024 * 1024
    )
    manifest = _strict_json_payload(manifest_payload, "deployment manifest")
    manifest_artifact = _Artifact(
        "deployment_manifest.json",
        "deployment_manifest",
        hashlib.sha256(manifest_payload).hexdigest(),
        len(manifest_payload),
        manifest_path,
    )
    manifest_schema = manifest.get("schema")
    if manifest_schema not in {DEPLOYMENT_SCHEMA, FULL_DEPLOYMENT_SCHEMA}:
        raise DeepSeekV4FP8LinearServiceEngineError(
            "deployment schema is not a supported FP8 linear profile"
        )
    full_operator = manifest_schema == FULL_DEPLOYMENT_SCHEMA
    artifacts, retained = _verify_artifacts(root, manifest)
    _verify_manifest(manifest, retained, full_operator=full_operator)
    entrypoint = manifest["entrypoint"]
    expected_entrypoint = {
        "execution_expectations": artifacts["execution_expectations"].relative_path,
        "microcode": artifacts["microcode"].relative_path,
        "semantic_ir": artifacts["semantic_ir"].relative_path,
        "tensor_manifest": artifacts["tensor_manifest"].relative_path,
    }
    if not isinstance(entrypoint, Mapping) or dict(entrypoint) != expected_entrypoint:
        raise DeepSeekV4FP8LinearServiceEngineError(
            "entrypoint differs from verified artifact roles"
        )
    semantic = _verified_json(artifacts["semantic_ir"], "semantic IR")
    input_features, output_features, rows, evidence_scope = _verify_semantic(
        semantic, manifest, full_operator=full_operator
    )
    tensors = _verified_json(artifacts["tensor_manifest"], "tensor manifest")
    weight_artifact, scale_artifact = _verify_tensors(
        tensors,
        artifacts,
        input_features,
        output_features,
        rows,
        full_operator=full_operator,
    )
    _scan_codes(
        weight_artifact, frozenset({0x7F, 0xFF}), "FP8 weight payload"
    )
    _scan_codes(scale_artifact, frozenset({0xFF}), "E8M0 scale payload")
    expectations = _verified_json(
        artifacts["execution_expectations"], "execution expectations"
    )
    _verify_expectations(expectations, input_features, len(rows))
    _verify_auxiliary(
        _verified_json(artifacts["operator_coverage"], "coverage ledger"),
        _verified_json(artifacts["roundtrip_report"], "roundtrip report"),
        manifest,
        artifacts,
        full_operator=full_operator,
    )
    try:
        instructions = decode(
            _verified_small_bytes(
                artifacts["microcode"], "microcode", maximum=64 * 1024
            )
        )
        verify(instructions)
    except ValueError as exc:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"FP8 linear microcode is invalid: {exc}"
        ) from exc
    try:
        observed_disassembly = _verified_small_bytes(
            artifacts["microcode_disassembly"],
            "microcode disassembly",
            maximum=256 * 1024,
        ).decode("ascii")
    except UnicodeDecodeError as exc:
        raise DeepSeekV4FP8LinearServiceEngineError(
            "microcode disassembly is not ASCII"
        ) from exc
    if observed_disassembly != disassemble(instructions):
        raise DeepSeekV4FP8LinearServiceEngineError(
            "microcode disassembly differs from decoded program"
        )
    return DeepSeekV4FP8LinearDeployment(
        root=root,
        manifest=manifest,
        semantic=semantic,
        expectations=expectations,
        instructions=instructions,
        weight_path=weight_artifact.path,
        scale_path=scale_artifact.path,
        selected_rows=rows,
        input_features=input_features,
        output_features=output_features,
        evidence_scope=evidence_scope,
        full_operator=full_operator,
        manifest_artifact=manifest_artifact,
        artifacts=tuple(
            sorted(artifacts.values(), key=lambda artifact: artifact.relative_path)
        ),
    )


def _load_request(
    deployment: DeepSeekV4FP8LinearDeployment, request_path: Path
) -> tuple[tuple[tuple[int, ...], ...], str]:
    maximum = (
        JSON_FIXED_OVERHEAD_BYTES
        + MAX_INPUT_ROWS * deployment.input_features * 6
    )
    request = _strict_json_payload(
        _small_bytes(
            Path(request_path),
            "FP8 linear execution request",
            maximum=maximum,
        ),
        "FP8 linear execution request",
    )
    _exact_keys(
        request,
        {"build_id", "input_bf16_codes", "model_id", "schema"},
        "FP8 linear execution request",
    )
    if (
        request["schema"] != REQUEST_SCHEMA
        or request["model_id"] != MODEL_ID
        or request["build_id"] != deployment.manifest["build_id"]
    ):
        raise DeepSeekV4FP8LinearServiceEngineError(
            "execution request identity differs from deployment"
        )
    raw_rows = request["input_bf16_codes"]
    if (
        isinstance(raw_rows, (str, bytes, bytearray))
        or not isinstance(raw_rows, Sequence)
        or not 1 <= len(raw_rows) <= MAX_INPUT_ROWS
    ):
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"input_bf16_codes must contain 1 through {MAX_INPUT_ROWS} rows"
        )
    rows = []
    for row_index, raw_row in enumerate(raw_rows):
        if (
            isinstance(raw_row, (str, bytes, bytearray))
            or not isinstance(raw_row, Sequence)
            or len(raw_row) != deployment.input_features
        ):
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"input_bf16_codes[{row_index}] must contain "
                f"{deployment.input_features} elements"
            )
        row = []
        for column, code in enumerate(raw_row):
            if (
                isinstance(code, bool)
                or not isinstance(code, int)
                or not 0 <= code <= 0xFFFF
            ):
                raise DeepSeekV4FP8LinearServiceEngineError(
                    f"input_bf16_codes[{row_index}][{column}] is not uint16"
                )
            row.append(code)
        rows.append(tuple(row))
    product_accumulates = (
        len(rows) * len(deployment.selected_rows) * deployment.input_features
    )
    if product_accumulates > MAX_PRODUCTS_PER_REQUEST:
        raise DeepSeekV4FP8LinearServiceEngineError(
            "FP8 linear request exceeds the exact-arithmetic work budget"
        )
    return tuple(rows), hashlib.sha256(canonical_json_bytes(request)).hexdigest()


@contextmanager
def _mapped_resources(
    deployment: DeepSeekV4FP8LinearDeployment,
) -> Iterator[tuple[mmap.mmap, mmap.mmap]]:
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "pread")
        or os.open not in os.supports_dir_fd
    ):
        raise DeepSeekV4FP8LinearServiceEngineError(
            "platform lacks race-resistant deployment file operations"
        )

    directory_flags = (
        os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
    )
    file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK

    def fingerprint(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_nlink,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

    def open_root(stack: ExitStack) -> tuple[int, tuple[int, ...]]:
        root_fd = os.open(deployment.root, directory_flags)
        stack.callback(os.close, root_fd)
        root_stat = os.fstat(root_fd)
        if not stat.S_ISDIR(root_stat.st_mode):
            raise DeepSeekV4FP8LinearServiceEngineError(
                "deployment root descriptor is not a directory"
            )
        return root_fd, fingerprint(root_stat)

    def open_relative(stack: ExitStack, root_fd: int, relative: str) -> int:
        parts = Path(relative).parts
        directory_fd = os.dup(root_fd)
        try:
            for part in parts[:-1]:
                next_fd = os.open(part, directory_flags, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = next_fd
            file_fd = os.open(parts[-1], file_flags, dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
        stack.callback(os.close, file_fd)
        return file_fd

    def verify_descriptor(
        descriptor: int, artifact: _Artifact
    ) -> tuple[int, ...]:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"runtime artifact {artifact.relative_path!r} is not a regular file"
            )
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.pread(descriptor, 8 * 1024 * 1024, size)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(descriptor)
        before_fingerprint = fingerprint(before)
        if fingerprint(after) != before_fingerprint:
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"runtime artifact {artifact.relative_path!r} changed while hashing"
            )
        if (digest.hexdigest(), size) != (artifact.sha256, artifact.size_bytes):
            raise DeepSeekV4FP8LinearServiceEngineError(
                f"runtime artifact {artifact.relative_path!r} differs from deployment"
            )
        return before_fingerprint

    records = (deployment.manifest_artifact, *deployment.artifacts)

    def open_and_verify_tree(
        stack: ExitStack,
    ) -> tuple[int, tuple[int, ...], dict[str, int], dict[str, tuple[int, ...]]]:
        root_fd, root_fingerprint = open_root(stack)
        descriptors: dict[str, int] = {}
        fingerprints: dict[str, tuple[int, ...]] = {}
        for artifact in records:
            descriptor = open_relative(stack, root_fd, artifact.relative_path)
            descriptors[artifact.role] = descriptor
            fingerprints[artifact.role] = verify_descriptor(descriptor, artifact)
        return root_fd, root_fingerprint, descriptors, fingerprints

    try:
        with ExitStack() as stack:
            (
                _,
                root_fingerprint,
                descriptors,
                fingerprints,
            ) = open_and_verify_tree(stack)
            weight = mmap.mmap(
                descriptors["weight_matrix"], 0, access=mmap.ACCESS_READ
            )
            scale = mmap.mmap(descriptors["scale_table"], 0, access=mmap.ACCESS_READ)
            stack.callback(weight.close)
            stack.callback(scale.close)
            try:
                yield weight, scale
            finally:
                for artifact in records:
                    observed = verify_descriptor(
                        descriptors[artifact.role], artifact
                    )
                    if observed != fingerprints[artifact.role]:
                        raise DeepSeekV4FP8LinearServiceEngineError(
                            f"runtime artifact {artifact.relative_path!r} changed "
                            "during execution"
                        )
                with ExitStack() as current_stack:
                    (
                        _,
                        current_root_fingerprint,
                        _,
                        current_fingerprints,
                    ) = open_and_verify_tree(current_stack)
                    if current_root_fingerprint != root_fingerprint:
                        raise DeepSeekV4FP8LinearServiceEngineError(
                            "deployment root changed during execution"
                        )
                    for artifact in records:
                        if (
                            current_fingerprints[artifact.role]
                            != fingerprints[artifact.role]
                        ):
                            raise DeepSeekV4FP8LinearServiceEngineError(
                                f"runtime artifact {artifact.relative_path!r} was "
                                "replaced during execution"
                            )
    except (OSError, ValueError) as exc:
        raise DeepSeekV4FP8LinearServiceEngineError(
            f"cannot memory-map FP8 linear resources: {exc}"
        ) from exc


def _expected_counters(
    deployment: DeepSeekV4FP8LinearDeployment, input_row_count: int
) -> dict[str, int]:
    result = {key: 0 for key in sorted(_COUNTER_KEYS)}
    for key, value in deployment.expectations[
        "counter_coefficients_per_input_row"
    ].items():
        result[key] = value * input_row_count
    for key, value in deployment.expectations["fixed_counters"].items():
        result[key] = value
    return result


class DeepSeekV4FP8LinearServiceEngine:
    """Verified interpreter for one bounded or complete FP8 linear program."""

    def __init__(self, deployment: DeepSeekV4FP8LinearDeployment):
        self.deployment = deployment

    @classmethod
    def load(cls, deployment_dir: Path) -> "DeepSeekV4FP8LinearServiceEngine":
        return cls(load_deepseek_v4_fp8_linear_deployment(deployment_dir))

    def execute(self, request_path: Path) -> dict[str, Any]:
        inputs, request_sha256 = _load_request(self.deployment, request_path)
        state: dict[int, Any] = {INPUT_BF16: inputs}
        completed = False
        activation_saturations = 0
        output_saturations = 0
        with _mapped_resources(self.deployment) as (weights, scales):
            blocks = self.deployment.input_features // DENSE_BLOCK_SIZE

            def weight_row(row: int) -> bytes:
                start = row * self.deployment.input_features
                return weights[start : start + self.deployment.input_features]

            def scale_code(row: int, block: int) -> int:
                return scales[(row // DENSE_BLOCK_SIZE) * blocks + block]

            for pc, instruction in enumerate(self.deployment.instructions):
                if instruction.opcode == Opcode.COMPLETE:
                    if (
                        pc != len(self.deployment.instructions) - 1
                        or completed
                        or OUTPUT_BF16 not in state
                    ):
                        raise DeepSeekV4FP8LinearServiceEngineError(
                            "illegal COMPLETE control flow"
                        )
                    completed = True
                    continue
                if instruction.source not in state:
                    raise DeepSeekV4FP8LinearServiceEngineError(
                        f"pc {pc} reads unavailable state slot {instruction.source}"
                    )
                if instruction.opcode != Opcode.FP8_LINEAR_SELECTED_ROWS:
                    raise DeepSeekV4FP8LinearServiceEngineError(
                        f"pc {pc} has unsupported opcode"
                    )
                try:
                    (
                        state[instruction.destination],
                        activation_saturations,
                        output_saturations,
                    ) = execute_selected_rows(
                        state[instruction.source],
                        selected_rows=self.deployment.selected_rows,
                        input_features=self.deployment.input_features,
                        weight_row=weight_row,
                        scale_code=scale_code,
                    )
                except FP8ServiceNumericError as exc:
                    raise DeepSeekV4FP8LinearServiceEngineError(
                        f"FP8 linear numeric poison: {exc}"
                    ) from exc
        if not completed:
            raise DeepSeekV4FP8LinearServiceEngineError(
                "microcode terminated without COMPLETE"
            )
        counters = _expected_counters(self.deployment, len(inputs))
        if set(counters) != _COUNTER_KEYS:
            raise DeepSeekV4FP8LinearServiceEngineError(
                "execution counters do not cover their strict contract"
            )
        values = state[OUTPUT_BF16]
        execution_scope = (
            "complete_fp8_linear_operator"
            if self.deployment.full_operator
            else "selected_output_rows_arithmetic_slice_only"
        )
        result_schema = (
            FULL_RESULT_SCHEMA if self.deployment.full_operator else RESULT_SCHEMA
        )
        return {
            "build_id": self.deployment.manifest["build_id"],
            "counter_reconciliation": "exact",
            "counters": counters,
            "deployment_status": self.deployment.manifest["status"],
            "evidence_scope": self.deployment.evidence_scope,
            "execution_scope": execution_scope,
            "model_id": MODEL_ID,
            "numeric_status": {
                "activation_saturated_block_count": activation_saturations,
                "output_saturated_element_count": output_saturations,
                "poison": False,
            },
            "outputs": [
                {
                    "dtype": "BF16_BITS",
                    "id": "output_bf16_codes",
                    "logical_output_rows": list(self.deployment.selected_rows),
                    "shape": [len(inputs), len(self.deployment.selected_rows)],
                    "values": [list(row) for row in values],
                }
            ],
            "request_sha256": request_sha256,
            "schema": result_schema,
            "source_application_status": self.deployment.semantic["source"][
                "application_status"
            ],
            "status": "pass",
        }


def execute_deepseek_v4_fp8_linear_deployment(
    deployment_dir: Path, request_path: Path
) -> dict[str, Any]:
    return DeepSeekV4FP8LinearServiceEngine.load(deployment_dir).execute(request_path)


__all__ = [
    "DEPLOYMENT_SCHEMA",
    "FULL_DEPLOYMENT_SCHEMA",
    "FULL_RESULT_SCHEMA",
    "DeepSeekV4FP8LinearDeployment",
    "DeepSeekV4FP8LinearServiceEngine",
    "DeepSeekV4FP8LinearServiceEngineError",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "execute_deepseek_v4_fp8_linear_deployment",
    "load_deepseek_v4_fp8_linear_deployment",
]
