"""Independent locked-checkpoint differential for selected DeepSeek V4 FP8 rows.

The checker never imports the FP8 service engine.  It validates and hashes the
persisted deployment, streams the original locked weight tensor while retaining
only selected logical rows, reads the small scale table from the original
checkpoint, executes the independent target-precision reference, and compares
the persisted service result exactly.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from typing import Any

from compiler.frontend.checkpoint import (
    LockedCheckpointReader,
    validate_checkpoint_lock,
)
from compiler.frontend.deepseek_v4 import MODEL_ID, REPOSITORY, REVISION
from compiler.ir.model import canonical_json_bytes, load_strict_json
from compiler.microcode.deepseek_v4_fp8_linear import decode, disassemble, verify
from runtime.reference.matrix import (
    MatrixReferenceError,
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
WEIGHT_NAME = "layers.0.attn.wq_a.weight"
SCALE_NAME = "layers.0.attn.wq_a.scale"
BLOCK_SIZE = 128
MAX_INPUT_ROWS = 4
MAX_SELECTED_ROWS = 64
MAX_FEATURE_EXTENT = 65_536

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


class DeepSeekV4FP8LinearDifferentialError(RuntimeError):
    """Raised when persisted execution differs from locked source semantics."""


@dataclass(frozen=True)
class _Artifact:
    path: Path
    relative_path: str
    role: str
    sha256: str
    size_bytes: int


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return load_strict_json(path)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"cannot load {label}: {exc}"
        ) from exc


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
    try:
        if path.stat().st_size > maximum:
            raise DeepSeekV4FP8LinearDifferentialError(
                f"{label} exceeds its {maximum}-byte checker bound"
            )
        return path.read_bytes()
    except OSError as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"cannot read {label}: {exc}"
        ) from exc


def _verified_small_bytes(
    artifact: _Artifact, label: str, maximum: int = 1024 * 1024
) -> bytes:
    payload = _small_bytes(artifact.path, label, maximum)
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


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"cannot hash deployment artifact {path.name!r}: {exc}"
        ) from exc
    return digest.hexdigest(), size


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
    root: Path, manifest: Mapping[str, Any]
) -> dict[str, _Artifact]:
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
    if manifest["schema"] != DEPLOYMENT_SCHEMA or manifest["model_id"] != MODEL_ID:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear deployment identity differs"
        )
    if manifest["claim_boundary"] != _DEPLOYMENT_CLAIMS:
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear deployment claim boundary differs"
        )
    if manifest["status"] not in {
        "development_fixture_selected_fp8_linear_rows_not_release_evidence",
        "real_checkpoint_selected_fp8_linear_rows_not_full_operator",
    }:
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
        if _sha256_file(path) != (digest, size):
            raise DeepSeekV4FP8LinearDifferentialError(
                f"deployment artifact {relative!r} differs from its manifest"
            )
        artifact = _Artifact(path, relative, role, digest, size)
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
    if (
        compiler["name"] != "opentallas-deepseek-v4-fp8-linear-slice-compiler"
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
    return by_role


def _dimensions_and_source(
    semantic: Mapping[str, Any],
    manifest: Mapping[str, Any],
    lock: Mapping[str, Any],
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
    if (
        semantic["schema"] != SEMANTIC_SCHEMA
        or semantic["model_id"] != MODEL_ID
        or semantic["claim_boundary"] != _SEMANTIC_CLAIM
        or semantic["numeric_profile"]
        != "deepseek_v4_dense_fp8_selected_rows_v1"
        or semantic["operation"]
        != {
            "input": "input_bf16_codes",
            "kind": "FP8_LINEAR_SELECTED_ROWS",
            "output": "output_bf16_codes",
            "scale_resource": SCALE_NAME,
            "weight_resource": WEIGHT_NAME,
        }
    ):
        raise DeepSeekV4FP8LinearDifferentialError(
            "FP8 linear semantic identity differs"
        )
    dimensions = semantic["dimensions"]
    if not isinstance(dimensions, Mapping):
        raise DeepSeekV4FP8LinearDifferentialError("semantic dimensions are absent")
    _exact_keys(
        dimensions,
        {"block_size", "input_features", "output_features", "selected_output_rows"},
        "FP8 linear dimensions",
    )
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
    raw_rows = dimensions["selected_output_rows"]
    if not isinstance(raw_rows, list):
        raise DeepSeekV4FP8LinearDifferentialError("selected output rows are absent")
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
        "real_checkpoint_selected_fp8_linear_rows_not_full_operator"
        if evidence_scope == "official_checkpoint"
        else "development_fixture_selected_fp8_linear_rows_not_release_evidence"
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
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    _exact_keys(
        tensors, {"output_selection", "scale", "schema", "weight"}, "tensor manifest"
    )
    if tensors["schema"] != TENSOR_SCHEMA:
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
        artifacts["output_selection"], "output selection", maximum=64 * 4
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
    try:
        with artifact.path.open("rb") as handle:
            offset = 0
            while chunk := handle.read(8 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                for index, code in enumerate(chunk):
                    if code in forbidden:
                        raise DeepSeekV4FP8LinearDifferentialError(
                            f"{label} contains reserved code 0x{code:02x} at "
                            f"byte {offset + index}"
                        )
                offset += len(chunk)
    except OSError as exc:
        raise DeepSeekV4FP8LinearDifferentialError(
            f"cannot scan {label}: {exc}"
        ) from exc
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
    if coverage != {
        "implemented_operator_kind": "FP8_LINEAR_SELECTED_ROWS",
        "model_id": MODEL_ID,
        "schema": COVERAGE_SCHEMA,
        "status": "selected_output_rows_arithmetic_slice_only",
        "underlying_graph_operator_kind": "FP8_LINEAR",
    }:
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
    if (
        result["schema"] != RESULT_SCHEMA
        or result["model_id"] != MODEL_ID
        or result["build_id"] != manifest["build_id"]
        or result["request_sha256"] != request_sha256
        or result["deployment_status"] != manifest["status"]
        or result["evidence_scope"] != source["evidence_scope"]
        or result["source_application_status"] != source["application_status"]
        or result["execution_scope"]
        != "selected_output_rows_arithmetic_slice_only"
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


def verify_deepseek_v4_fp8_linear_execution(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    deployment_root: Path,
    request_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    """Compare persisted selected-row execution to the original locked tensors."""

    validate_checkpoint_lock(lock)
    root = Path(deployment_root).resolve()
    if not root.is_dir():
        raise DeepSeekV4FP8LinearDifferentialError(
            f"FP8 linear deployment is not a directory: {root}"
        )
    manifest_path = root / "deployment_manifest.json"
    if manifest_path.is_symlink():
        raise DeepSeekV4FP8LinearDifferentialError(
            "deployment manifest must not be a symlink"
        )
    manifest_payload = _small_bytes(
        manifest_path, "deployment manifest", maximum=1024 * 1024
    )
    manifest = _strict_json_payload(manifest_payload, "deployment manifest")
    artifacts = _deployment_artifacts(root, manifest)
    semantic = _verified_json(artifacts["semantic_ir"], "semantic IR")
    input_features, output_features, selected_rows, source = _dimensions_and_source(
        semantic, manifest, lock
    )
    tensors = _verified_json(artifacts["tensor_manifest"], "tensor manifest")
    weight_resource, scale_resource = _tensor_resources(
        tensors,
        artifacts,
        input_features=input_features,
        output_features=output_features,
        selected_rows=selected_rows,
        evidence_scope=source["evidence_scope"],
    )
    _verify_contract_artifacts(
        artifacts,
        manifest,
        input_features=input_features,
        selected_count=len(selected_rows),
        weight_resource=weight_resource,
        scale_resource=scale_resource,
    )
    request = _load_json(Path(request_path), "execution request")
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
    result = _load_json(Path(result_path), "execution result")
    observed, observed_numeric = _parse_result(
        result,
        manifest=manifest,
        source=source,
        request_sha256=request_sha256,
        input_row_count=len(inputs),
        selected_rows=selected_rows,
        expected_counters=expected_counters,
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
        expected = dense_fp8_linear_selected_rows_bf16(
            inputs,
            tuple(tuple(selected_weight_rows[row]) for row in selected_rows),
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

    if _small_bytes(
        manifest_path, "deployment manifest", maximum=1024 * 1024
    ) != manifest_payload:
        raise DeepSeekV4FP8LinearDifferentialError(
            "deployment manifest changed during independent checking"
        )
    for artifact in artifacts.values():
        relative, current_path = _safe_file(
            root, artifact.relative_path, f"rechecked artifact {artifact.role}.path"
        )
        if relative != artifact.relative_path or _sha256_file(current_path) != (
            artifact.sha256,
            artifact.size_bytes,
        ):
            raise DeepSeekV4FP8LinearDifferentialError(
                f"deployment artifact {artifact.relative_path!r} changed during checking"
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
    body: dict[str, Any] = {
        "build_id": manifest["build_id"],
        "checkpoint_lock_id": lock["lock_id"],
        "claim_boundary": (
            "Exact selected-row layer-0 query-A FP8 linear differential only; "
            "not the complete projection, attention, a transformer block, or full model."
        ),
        "comparison": comparison,
        "counters": expected_counters,
        "input_row_count": len(inputs),
        "model_id": MODEL_ID,
        "numeric_status": expected_numeric,
        "request_sha256": request_sha256,
        "schema": DIFFERENTIAL_SCHEMA,
        "selected_output_rows": list(selected_rows),
        "source_application_id": source["application_id"],
        "source_tensors": source_tensors,
        "status": "exact_locked_checkpoint_selected_row_differential",
    }
    body["differential_id"] = _sha256_json(body)
    return body


__all__ = [
    "DIFFERENTIAL_SCHEMA",
    "DeepSeekV4FP8LinearDifferentialError",
    "verify_deepseek_v4_fp8_linear_execution",
]
