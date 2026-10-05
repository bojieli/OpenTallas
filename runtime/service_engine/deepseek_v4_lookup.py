"""Artifact-only service engine for the DeepSeek V4 real-payload lookup slice.

The engine accepts only deployments emitted by
``build_deepseek_v4_lookup_deployment``.  It stream-verifies every manifested
artifact, memory-maps the large ROM payloads, interprets the dedicated OTV4
microcode, and carries BF16 values as raw 16-bit encodings.  It deliberately
does not import source checkpoint payloads or reference-operator results.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import hashlib
import mmap
from pathlib import Path
import re
import struct
from typing import Any

from compiler.frontend.deepseek_v4 import MODEL_ID, REPOSITORY, REVISION
from compiler.ir.model import canonical_json_bytes, load_strict_json
from compiler.microcode.deepseek_v4_lookup import (
    ABI_MAJOR,
    ABI_MINOR,
    EMBEDDING,
    HASH_ROUTES,
    HC_HIDDEN,
    TOKENS,
    Instruction,
    Opcode,
    decode,
    disassemble,
    verify,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_lookup_deployment.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_lookup_slice.v1"
TENSOR_SCHEMA = "opentallas.deepseek_v4_lookup_tensors.v1"
EXPECTATION_SCHEMA = "opentallas.deepseek_v4_lookup_expectations.v1"
COVERAGE_SCHEMA = "opentallas.deepseek_v4_lookup_coverage.v1"
ROUNDTRIP_SCHEMA = "opentallas.deepseek_v4_lookup_roundtrip.v1"
REQUEST_SCHEMA = "opentallas.deepseek_v4_lookup_request.v1"
RESULT_SCHEMA = "opentallas.deepseek_v4_lookup_result.v1"
NUMERIC_PROFILE = "deepseek_v4_flash_lookup_bits_v1"
MAX_REQUEST_TOKENS = 256

_SEMANTIC_CLAIM_BOUNDARY = (
    "Three real-payload pure operators only; not a transformer block, "
    "complete decode, hardware timing, or full-model execution."
)
_DEPLOYMENT_CLAIM_BOUNDARY = [
    "Executes TOKEN_EMBED, HC_EXPAND, and HASH_ROUTE only.",
    "Does not execute a transformer block, attention, MoE arithmetic, logits, or decode state.",
    "Functional counters are not hardware cycles, PPA, or NVIDIA comparison evidence.",
]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FIXED_ROLES = frozenset(
    {
        "execution_expectations",
        "hash_route_table",
        "microcode",
        "microcode_disassembly",
        "operator_coverage",
        "roundtrip_report",
        "semantic_ir",
        "tensor_manifest",
    }
)
_COUNTER_KEYS = frozenset(
    {
        "bf16_codes_copied",
        "completion_events",
        "logical_activation_bytes_read",
        "logical_activation_bytes_written",
        "logical_input_bytes_read",
        "logical_rom_bytes_read",
        "micro_ops_executed",
        "rom_lookup_rows",
        "semantic_operations_executed",
    }
)


class DeepSeekV4LookupServiceEngineError(RuntimeError):
    """Raised when lookup artifacts, requests, execution, or counters differ."""


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4LookupServiceEngineError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DeepSeekV4LookupServiceEngineError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _hash_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise DeepSeekV4LookupServiceEngineError(
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
        raise DeepSeekV4LookupServiceEngineError(
            f"cannot hash deployment artifact {path.name!r}: {exc}"
        ) from exc
    return digest.hexdigest(), size


def _safe_file(root: Path, value: Any, label: str) -> tuple[str, Path]:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
    ):
        raise DeepSeekV4LookupServiceEngineError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4LookupServiceEngineError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4LookupServiceEngineError(
            f"{label} is not canonical POSIX"
        )
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4LookupServiceEngineError(f"{label} traverses a symlink")
    try:
        current.resolve().relative_to(root)
    except ValueError as exc:
        raise DeepSeekV4LookupServiceEngineError(f"{label} escapes deployment") from exc
    if not current.is_file():
        raise DeepSeekV4LookupServiceEngineError(
            f"{label} is not a regular file"
        )
    return value, current


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return load_strict_json(path)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4LookupServiceEngineError(
            f"cannot load {label}: {exc}"
        ) from exc


def _read_small(path: Path, label: str, *, maximum: int) -> bytes:
    try:
        size = path.stat().st_size
        if size > maximum:
            raise DeepSeekV4LookupServiceEngineError(
                f"{label} exceeds its {maximum}-byte runtime bound"
            )
        return path.read_bytes()
    except OSError as exc:
        raise DeepSeekV4LookupServiceEngineError(f"cannot read {label}: {exc}") from exc


@dataclass(frozen=True)
class _Artifact:
    relative_path: str
    role: str
    sha256: str
    size_bytes: int
    path: Path


@dataclass(frozen=True)
class _EmbeddingRank:
    path: Path
    rank: int
    row_start: int
    row_stop: int
    size_bytes: int


@dataclass(frozen=True)
class DeepSeekV4LookupDeployment:
    root: Path
    manifest: dict[str, Any]
    semantic: dict[str, Any]
    expectations: dict[str, Any]
    instructions: tuple[Instruction, ...]
    embedding_ranks: tuple[_EmbeddingRank, ...]
    hash_route_path: Path
    dimensions: dict[str, int]
    evidence_scope: str


def _verify_artifacts(
    root: Path, manifest: Mapping[str, Any]
) -> tuple[dict[str, _Artifact], list[dict[str, Any]]]:
    records = manifest.get("artifacts")
    if not isinstance(records, list) or not records:
        raise DeepSeekV4LookupServiceEngineError("deployment artifact table is absent")
    paths: set[str] = set()
    roles: set[str] = set()
    by_role: dict[str, _Artifact] = {}
    retained: list[dict[str, Any]] = []
    previous_path: str | None = None
    for index, raw in enumerate(records):
        if not isinstance(raw, Mapping):
            raise DeepSeekV4LookupServiceEngineError(
                f"artifact record {index} is not an object"
            )
        _exact_keys(
            raw,
            {"path", "role", "sha256", "size_bytes"},
            f"artifact record {index}",
        )
        relative, path = _safe_file(root, raw["path"], f"artifact {index}.path")
        role = raw["role"]
        if not isinstance(role, str) or not role:
            raise DeepSeekV4LookupServiceEngineError(
                f"artifact record {index}.role must be non-empty"
            )
        if relative in paths or role in roles:
            raise DeepSeekV4LookupServiceEngineError(
                f"artifact record {index} duplicates a path or role"
            )
        if previous_path is not None and relative <= previous_path:
            raise DeepSeekV4LookupServiceEngineError(
                "deployment artifact table must be strictly path-sorted"
            )
        previous_path = relative
        paths.add(relative)
        roles.add(role)
        expected_hash = _hash_text(raw["sha256"], f"artifact {relative}.sha256")
        expected_size = _integer(raw["size_bytes"], f"artifact {relative}.size_bytes")
        observed_hash, observed_size = _sha256_file(path)
        if (observed_hash, observed_size) != (expected_hash, expected_size):
            raise DeepSeekV4LookupServiceEngineError(
                f"artifact {relative!r} differs from its deployment manifest"
            )
        artifact = _Artifact(relative, role, expected_hash, expected_size, path)
        by_role[role] = artifact
        retained.append(dict(raw))
    return by_role, retained


def _verify_manifest_identity(
    manifest: dict[str, Any], artifacts: list[dict[str, Any]]
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
    if manifest["schema"] != DEPLOYMENT_SCHEMA or manifest["model_id"] != MODEL_ID:
        raise DeepSeekV4LookupServiceEngineError(
            "deployment schema or model identity differs"
        )
    compiler = manifest["compiler"]
    if not isinstance(compiler, Mapping):
        raise DeepSeekV4LookupServiceEngineError("compiler identity is absent")
    _exact_keys(compiler, {"name", "version"}, "compiler identity")
    if compiler["name"] != "opentallas-deepseek-v4-lookup-slice-compiler":
        raise DeepSeekV4LookupServiceEngineError("compiler name differs")
    if not isinstance(compiler["version"], str) or not compiler["version"]:
        raise DeepSeekV4LookupServiceEngineError("compiler version is invalid")
    abi = manifest["microcode_abi"]
    if abi != {
        "major": ABI_MAJOR,
        "minor": ABI_MINOR,
        "name": "deepseek_v4_lookup",
    }:
        raise DeepSeekV4LookupServiceEngineError("microcode ABI identity differs")
    application_id = _hash_text(
        manifest["source_application_id"], "source_application_id"
    )
    identity = {
        "artifacts": artifacts,
        "compiler_version": compiler["version"],
        "microcode_abi": abi,
        "model_id": MODEL_ID,
        "source_application_id": application_id,
    }
    expected_build_id = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    if manifest["build_id"] != expected_build_id:
        raise DeepSeekV4LookupServiceEngineError(
            "deployment build_id does not bind its artifact table"
        )
    if manifest["status"] not in {
        "development_fixture_lookup_slice_not_release_evidence",
        "real_checkpoint_lookup_slice_not_full_model",
    }:
        raise DeepSeekV4LookupServiceEngineError("deployment status is unsupported")
    if manifest["claim_boundary"] != _DEPLOYMENT_CLAIM_BOUNDARY:
        raise DeepSeekV4LookupServiceEngineError("deployment claim boundary differs")


def _dimensions(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise DeepSeekV4LookupServiceEngineError("semantic dimensions are absent")
    expected = {
        "expert_count",
        "hc_multiplier",
        "hidden_size",
        "model_parallel",
        "route_top_k",
        "vocabulary_size",
    }
    _exact_keys(value, expected, "semantic dimensions")
    return {key: _integer(value[key], f"dimensions.{key}", minimum=1) for key in expected}


def _verify_semantic(
    value: dict[str, Any], manifest: Mapping[str, Any]
) -> tuple[dict[str, int], str]:
    _exact_keys(
        value,
        {
            "claim_boundary",
            "dimensions",
            "model_id",
            "numeric_profile",
            "operations",
            "outputs",
            "schema",
            "source",
        },
        "lookup semantic IR",
    )
    if (
        value["schema"] != SEMANTIC_SCHEMA
        or value["model_id"] != MODEL_ID
        or value["numeric_profile"] != NUMERIC_PROFILE
        or value["claim_boundary"] != _SEMANTIC_CLAIM_BOUNDARY
    ):
        raise DeepSeekV4LookupServiceEngineError("lookup semantic identity differs")
    expected_operations = [
        {
            "id": "token_embed",
            "input": "token_ids",
            "kind": "TOKEN_EMBED",
            "output": "embedding_bf16_codes",
            "resource": "embed.weight",
        },
        {
            "id": "hc_expand",
            "input": "embedding_bf16_codes",
            "kind": "HC_EXPAND",
            "output": "hc_hidden_bf16_codes",
            "resource": None,
        },
        {
            "id": "hash_route",
            "input": "token_ids",
            "kind": "HASH_ROUTE",
            "output": "expert_ids",
            "resource": "layers.0.ffn.gate.tid2eid",
        },
    ]
    if value["operations"] != expected_operations or value["outputs"] != [
        "embedding_bf16_codes",
        "hc_hidden_bf16_codes",
        "expert_ids",
    ]:
        raise DeepSeekV4LookupServiceEngineError("lookup semantic program differs")
    source = value["source"]
    if not isinstance(source, Mapping):
        raise DeepSeekV4LookupServiceEngineError("lookup semantic source is absent")
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
        "lookup semantic source",
    )
    if source["application_id"] != manifest["source_application_id"]:
        raise DeepSeekV4LookupServiceEngineError(
            "semantic source application differs from deployment"
        )
    for key in ("checkpoint_lock_id", "verification_id"):
        _hash_text(source[key], f"semantic source {key}")
    for key in ("application_status", "repository", "revision"):
        if not isinstance(source[key], str) or not source[key]:
            raise DeepSeekV4LookupServiceEngineError(
                f"semantic source {key} must be non-empty"
            )
    evidence_scope = source["evidence_scope"]
    if evidence_scope not in {"development_fixture", "official_checkpoint"}:
        raise DeepSeekV4LookupServiceEngineError("semantic evidence scope is unsupported")
    expected_status = (
        "real_checkpoint_lookup_slice_not_full_model"
        if evidence_scope == "official_checkpoint"
        else "development_fixture_lookup_slice_not_release_evidence"
    )
    if manifest["status"] != expected_status:
        raise DeepSeekV4LookupServiceEngineError(
            "deployment status overstates its semantic evidence scope"
        )
    expected_application_statuses = {
        "official_checkpoint": {
            "complete_official_transform_application",
            "partial_official_transform_application_not_release_evidence",
        },
        "development_fixture": {
            "development_fixture_application_not_release_evidence"
        },
    }[evidence_scope]
    if source["application_status"] not in expected_application_statuses:
        raise DeepSeekV4LookupServiceEngineError(
            "canonical application status differs from its evidence scope"
        )
    dimensions = _dimensions(value["dimensions"])
    if evidence_scope == "official_checkpoint":
        if (source["repository"], source["revision"]) != (REPOSITORY, REVISION):
            raise DeepSeekV4LookupServiceEngineError(
                "official semantic source is not the pinned V4 release"
            )
        if dimensions != {
            "expert_count": 256,
            "hc_multiplier": 4,
            "hidden_size": 4096,
            "model_parallel": 4,
            "route_top_k": 6,
            "vocabulary_size": 129280,
        }:
            raise DeepSeekV4LookupServiceEngineError(
                "official lookup dimensions differ from the pinned release"
            )
    return dimensions, evidence_scope


def _artifact_for_path(
    by_role: Mapping[str, _Artifact], path: str, role: str
) -> _Artifact:
    artifact = by_role.get(role)
    if artifact is None or artifact.relative_path != path:
        raise DeepSeekV4LookupServiceEngineError(
            f"tensor resource {path!r} differs from artifact role {role!r}"
        )
    return artifact


def _verify_tensor_manifest(
    value: dict[str, Any],
    dimensions: Mapping[str, int],
    by_role: Mapping[str, _Artifact],
) -> tuple[tuple[_EmbeddingRank, ...], Path]:
    _exact_keys(value, {"embedding", "hash_route", "schema"}, "tensor manifest")
    if value["schema"] != TENSOR_SCHEMA:
        raise DeepSeekV4LookupServiceEngineError("tensor manifest schema differs")
    embedding = value["embedding"]
    if not isinstance(embedding, Mapping):
        raise DeepSeekV4LookupServiceEngineError("embedding manifest is absent")
    _exact_keys(
        embedding,
        {"dtype", "hidden_size", "ranks", "vocabulary_size"},
        "embedding manifest",
    )
    if (
        embedding["dtype"] != "BF16"
        or embedding["hidden_size"] != dimensions["hidden_size"]
        or embedding["vocabulary_size"] != dimensions["vocabulary_size"]
    ):
        raise DeepSeekV4LookupServiceEngineError("embedding metadata differs")
    records = embedding["ranks"]
    if not isinstance(records, list) or len(records) != dimensions["model_parallel"]:
        raise DeepSeekV4LookupServiceEngineError("embedding rank coverage differs")
    ranks: list[_EmbeddingRank] = []
    expected_start = 0
    expected_roles: set[str] = set(_FIXED_ROLES)
    for rank, raw in enumerate(records):
        if not isinstance(raw, Mapping):
            raise DeepSeekV4LookupServiceEngineError(
                f"embedding rank {rank} is not an object"
            )
        _exact_keys(
            raw,
            {
                "path",
                "rank",
                "row_start",
                "row_stop",
                "sha256",
                "size_bytes",
                "source_assignment_path",
            },
            f"embedding rank {rank}",
        )
        stop = _integer(raw["row_stop"], f"embedding rank {rank}.row_stop", minimum=1)
        role = f"embedding_rank_{rank:03d}"
        artifact = _artifact_for_path(by_role, raw["path"], role)
        expected_roles.add(role)
        expected_size = (stop - expected_start) * dimensions["hidden_size"] * 2
        if (
            raw["rank"] != rank
            or raw["row_start"] != expected_start
            or stop <= expected_start
            or raw["sha256"] != artifact.sha256
            or raw["size_bytes"] != artifact.size_bytes
            or artifact.size_bytes != expected_size
            or not isinstance(raw["source_assignment_path"], str)
            or not raw["source_assignment_path"]
        ):
            raise DeepSeekV4LookupServiceEngineError(
                f"embedding rank {rank} metadata differs"
            )
        ranks.append(
            _EmbeddingRank(
                artifact.path,
                rank,
                expected_start,
                stop,
                artifact.size_bytes,
            )
        )
        expected_start = stop
    if expected_start != dimensions["vocabulary_size"]:
        raise DeepSeekV4LookupServiceEngineError(
            "embedding ranks do not cover the vocabulary"
        )

    route = value["hash_route"]
    if not isinstance(route, Mapping):
        raise DeepSeekV4LookupServiceEngineError("hash-route manifest is absent")
    _exact_keys(
        route,
        {
            "dtype",
            "expert_count",
            "path",
            "route_top_k",
            "sha256",
            "size_bytes",
            "source_assignment_path",
            "source_rank",
            "verified_replica_ranks",
            "vocabulary_size",
        },
        "hash-route manifest",
    )
    route_artifact = _artifact_for_path(
        by_role, route["path"], "hash_route_table"
    )
    expected_route_size = (
        dimensions["vocabulary_size"] * dimensions["route_top_k"] * 8
    )
    if (
        route["dtype"] != "I64"
        or route["expert_count"] != dimensions["expert_count"]
        or route["route_top_k"] != dimensions["route_top_k"]
        or route["vocabulary_size"] != dimensions["vocabulary_size"]
        or route["sha256"] != route_artifact.sha256
        or route["size_bytes"] != route_artifact.size_bytes
        or route_artifact.size_bytes != expected_route_size
        or route["verified_replica_ranks"]
        != list(range(dimensions["model_parallel"]))
        or not isinstance(route["source_rank"], int)
        or route["source_rank"] not in range(dimensions["model_parallel"])
        or not isinstance(route["source_assignment_path"], str)
        or not route["source_assignment_path"]
    ):
        raise DeepSeekV4LookupServiceEngineError("hash-route metadata differs")
    if set(by_role) != expected_roles:
        raise DeepSeekV4LookupServiceEngineError(
            f"deployment roles differ: missing={sorted(expected_roles - by_role.keys())}, "
            f"extra={sorted(by_role.keys() - expected_roles)}"
        )
    return tuple(ranks), route_artifact.path


def _verify_expectations(
    value: dict[str, Any], dimensions: Mapping[str, int]
) -> None:
    _exact_keys(
        value,
        {
            "counter_coefficients_per_token",
            "fixed_counters",
            "hardware_accounting",
            "schema",
        },
        "execution expectations",
    )
    if value["schema"] != EXPECTATION_SCHEMA:
        raise DeepSeekV4LookupServiceEngineError("expectation schema differs")
    coefficients = value["counter_coefficients_per_token"]
    fixed = value["fixed_counters"]
    if not isinstance(coefficients, Mapping) or not isinstance(fixed, Mapping):
        raise DeepSeekV4LookupServiceEngineError("counter expectations are absent")
    expected_coefficients = {
        "bf16_codes_copied": dimensions["hc_multiplier"]
        * dimensions["hidden_size"],
        "logical_activation_bytes_read": dimensions["hidden_size"] * 2,
        "logical_activation_bytes_written": (
            dimensions["hidden_size"] * 2
            + dimensions["hc_multiplier"] * dimensions["hidden_size"] * 2
            + dimensions["route_top_k"] * 8
        ),
        "logical_input_bytes_read": 16,
        "logical_rom_bytes_read": dimensions["hidden_size"] * 2
        + dimensions["route_top_k"] * 8,
        "rom_lookup_rows": 2,
    }
    expected_fixed = {
        "completion_events": 1,
        "micro_ops_executed": 4,
        "semantic_operations_executed": 3,
    }
    if dict(coefficients) != expected_coefficients or dict(fixed) != expected_fixed:
        raise DeepSeekV4LookupServiceEngineError(
            "execution counter contract differs from lookup semantics"
        )
    hardware = value["hardware_accounting"]
    if (
        not isinstance(hardware, Mapping)
        or set(hardware) != {"cycles", "hbm_transactions", "stalls", "status"}
        or hardware["status"] != "not modeled by the functional lookup slice"
        or any(hardware[key] is not None for key in ("cycles", "hbm_transactions", "stalls"))
    ):
        raise DeepSeekV4LookupServiceEngineError(
            "lookup slice must not contain speculative hardware accounting"
        )


def _verify_auxiliary_evidence(
    coverage: dict[str, Any],
    roundtrip: dict[str, Any],
    manifest: Mapping[str, Any],
    by_role: Mapping[str, _Artifact],
) -> None:
    if coverage != {
        "implemented_operator_kinds": ["HASH_ROUTE", "HC_EXPAND", "TOKEN_EMBED"],
        "model_id": MODEL_ID,
        "schema": COVERAGE_SCHEMA,
        "status": "three_operator_real_payload_slice_only",
        "unimplemented_graph_operator_kind_count": 40,
    }:
        raise DeepSeekV4LookupServiceEngineError("operator coverage ledger differs")
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
    if not isinstance(reconstructed, list):
        raise DeepSeekV4LookupServiceEngineError(
            "roundtrip reconstructed artifacts are absent"
        )
    payload_artifacts = {
        artifact.relative_path: artifact
        for role, artifact in by_role.items()
        if role == "hash_route_table" or role.startswith("embedding_rank_")
    }
    seen: set[str] = set()
    total = 0
    for index, raw in enumerate(reconstructed):
        if not isinstance(raw, Mapping):
            raise DeepSeekV4LookupServiceEngineError(
                f"roundtrip record {index} is not an object"
            )
        _exact_keys(
            raw,
            {
                "deployment_path",
                "rank",
                "sha256",
                "size_bytes",
                "source_assignment_path",
                "tensor_name",
            },
            f"roundtrip record {index}",
        )
        artifact = payload_artifacts.get(raw["deployment_path"])
        if (
            artifact is None
            or artifact.relative_path in seen
            or raw["sha256"] != artifact.sha256
            or raw["size_bytes"] != artifact.size_bytes
        ):
            raise DeepSeekV4LookupServiceEngineError(
                f"roundtrip record {index} differs from deployed payload"
            )
        seen.add(artifact.relative_path)
        total += artifact.size_bytes
    identity = dict(roundtrip)
    observed_roundtrip_id = identity.pop("roundtrip_id")
    expected_roundtrip_id = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    if (
        roundtrip["schema"] != ROUNDTRIP_SCHEMA
        or roundtrip["model_id"] != MODEL_ID
        or roundtrip["application_id"] != manifest["source_application_id"]
        or roundtrip["status"] != "full_selected_payload_match"
        or roundtrip["checked_artifact_count"] != len(payload_artifacts)
        or roundtrip["checked_payload_bytes"] != total
        or seen != set(payload_artifacts)
        or observed_roundtrip_id != expected_roundtrip_id
    ):
        raise DeepSeekV4LookupServiceEngineError("roundtrip evidence differs")


def load_deepseek_v4_lookup_deployment(
    deployment_dir: Path,
) -> DeepSeekV4LookupDeployment:
    """Stream-verify and load one immutable lookup deployment descriptor."""

    root = Path(deployment_dir).resolve()
    if not root.is_dir():
        raise DeepSeekV4LookupServiceEngineError(
            f"lookup deployment is not a directory: {root}"
        )
    manifest_path = root / "deployment_manifest.json"
    if manifest_path.is_symlink():
        raise DeepSeekV4LookupServiceEngineError(
            "deployment manifest must not be a symlink"
        )
    manifest = _load_json(manifest_path, "lookup deployment manifest")
    by_role, retained_artifacts = _verify_artifacts(root, manifest)
    _verify_manifest_identity(manifest, retained_artifacts)
    missing_fixed_roles = _FIXED_ROLES - by_role.keys()
    if missing_fixed_roles:
        raise DeepSeekV4LookupServiceEngineError(
            f"deployment lacks fixed artifact roles {sorted(missing_fixed_roles)}"
        )
    entrypoint = manifest["entrypoint"]
    if not isinstance(entrypoint, Mapping):
        raise DeepSeekV4LookupServiceEngineError("lookup entrypoint is absent")
    expected_entrypoint = {
        "execution_expectations": by_role["execution_expectations"].relative_path,
        "microcode": by_role["microcode"].relative_path,
        "semantic_ir": by_role["semantic_ir"].relative_path,
        "tensor_manifest": by_role["tensor_manifest"].relative_path,
    }
    if dict(entrypoint) != expected_entrypoint:
        raise DeepSeekV4LookupServiceEngineError(
            "lookup entrypoint differs from verified artifact roles"
        )
    semantic = _load_json(by_role["semantic_ir"].path, "lookup semantic IR")
    dimensions, evidence_scope = _verify_semantic(semantic, manifest)
    tensors = _load_json(by_role["tensor_manifest"].path, "lookup tensor manifest")
    embedding_ranks, hash_route_path = _verify_tensor_manifest(
        tensors, dimensions, by_role
    )
    expectations = _load_json(
        by_role["execution_expectations"].path, "lookup execution expectations"
    )
    _verify_expectations(expectations, dimensions)
    coverage = _load_json(by_role["operator_coverage"].path, "operator coverage")
    roundtrip = _load_json(by_role["roundtrip_report"].path, "roundtrip report")
    _verify_auxiliary_evidence(coverage, roundtrip, manifest, by_role)
    microcode_payload = _read_small(
        by_role["microcode"].path, "lookup microcode", maximum=64 * 1024
    )
    try:
        instructions = decode(microcode_payload)
        verify(instructions, dimensions["hc_multiplier"])
    except ValueError as exc:
        raise DeepSeekV4LookupServiceEngineError(
            f"lookup microcode is invalid: {exc}"
        ) from exc
    disassembly = _read_small(
        by_role["microcode_disassembly"].path,
        "lookup microcode disassembly",
        maximum=256 * 1024,
    )
    try:
        observed_disassembly = disassembly.decode("ascii")
    except UnicodeDecodeError as exc:
        raise DeepSeekV4LookupServiceEngineError(
            "lookup microcode disassembly is not ASCII"
        ) from exc
    if observed_disassembly != disassemble(instructions):
        raise DeepSeekV4LookupServiceEngineError(
            "microcode disassembly differs from decoded instructions"
        )
    return DeepSeekV4LookupDeployment(
        root,
        manifest,
        semantic,
        expectations,
        instructions,
        embedding_ranks,
        hash_route_path,
        dimensions,
        evidence_scope,
    )


def _load_request(
    deployment: DeepSeekV4LookupDeployment, request_path: Path
) -> tuple[tuple[tuple[int, ...], ...], str]:
    request = _load_json(Path(request_path), "lookup execution request")
    _exact_keys(
        request,
        {"build_id", "model_id", "schema", "token_ids"},
        "lookup execution request",
    )
    if (
        request["schema"] != REQUEST_SCHEMA
        or request["model_id"] != MODEL_ID
        or request["build_id"] != deployment.manifest["build_id"]
    ):
        raise DeepSeekV4LookupServiceEngineError(
            "lookup execution request identity differs from deployment"
        )
    raw_batches = request["token_ids"]
    if (
        isinstance(raw_batches, (str, bytes, bytearray))
        or not isinstance(raw_batches, Sequence)
        or not raw_batches
    ):
        raise DeepSeekV4LookupServiceEngineError(
            "token_ids must be a non-empty rank-2 array"
        )
    batches: list[tuple[int, ...]] = []
    sequence_length: int | None = None
    token_count = 0
    for batch_index, raw_row in enumerate(raw_batches):
        if (
            isinstance(raw_row, (str, bytes, bytearray))
            or not isinstance(raw_row, Sequence)
        ):
            raise DeepSeekV4LookupServiceEngineError(
                f"token_ids[{batch_index}] must be an array"
            )
        if sequence_length is None:
            sequence_length = len(raw_row)
            if sequence_length == 0:
                raise DeepSeekV4LookupServiceEngineError(
                    "token_ids rows must be non-empty"
                )
        elif len(raw_row) != sequence_length:
            raise DeepSeekV4LookupServiceEngineError(
                "token_ids must be a rectangular rank-2 array"
            )
        row: list[int] = []
        for position, token_id in enumerate(raw_row):
            if (
                isinstance(token_id, bool)
                or not isinstance(token_id, int)
                or not 0 <= token_id < deployment.dimensions["vocabulary_size"]
            ):
                raise DeepSeekV4LookupServiceEngineError(
                    f"token_ids[{batch_index}][{position}] is outside vocabulary"
                )
            row.append(token_id)
        token_count += len(row)
        if token_count > MAX_REQUEST_TOKENS:
            raise DeepSeekV4LookupServiceEngineError(
                f"lookup request exceeds the {MAX_REQUEST_TOKENS}-token v1 bound"
            )
        batches.append(tuple(row))
    return tuple(batches), hashlib.sha256(canonical_json_bytes(request)).hexdigest()


@contextmanager
def _mapped_resources(
    deployment: DeepSeekV4LookupDeployment,
) -> Iterator[tuple[tuple[mmap.mmap, ...], mmap.mmap]]:
    try:
        with ExitStack() as stack:
            embedding_maps: list[mmap.mmap] = []
            for rank in deployment.embedding_ranks:
                handle = stack.enter_context(rank.path.open("rb"))
                mapped = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
                stack.callback(mapped.close)
                embedding_maps.append(mapped)
            route_handle = stack.enter_context(deployment.hash_route_path.open("rb"))
            route_map = mmap.mmap(route_handle.fileno(), 0, access=mmap.ACCESS_READ)
            stack.callback(route_map.close)
            yield tuple(embedding_maps), route_map
    except (OSError, ValueError) as exc:
        raise DeepSeekV4LookupServiceEngineError(
            f"cannot memory-map lookup resources: {exc}"
        ) from exc


def _empty_counters() -> dict[str, int]:
    return {key: 0 for key in sorted(_COUNTER_KEYS)}


def _token_count(tokens: tuple[tuple[int, ...], ...]) -> int:
    return sum(len(row) for row in tokens)


def _gather_embedding(
    tokens: tuple[tuple[int, ...], ...],
    deployment: DeepSeekV4LookupDeployment,
    tables: tuple[mmap.mmap, ...],
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    row_stops = tuple(rank.row_stop for rank in deployment.embedding_ranks)
    row_decoder = struct.Struct(f"<{deployment.dimensions['hidden_size']}H")
    batches: list[tuple[tuple[int, ...], ...]] = []
    for batch in tokens:
        rows: list[tuple[int, ...]] = []
        for token_id in batch:
            rank_index = bisect_right(row_stops, token_id)
            rank = deployment.embedding_ranks[rank_index]
            offset = (token_id - rank.row_start) * row_decoder.size
            rows.append(row_decoder.unpack_from(tables[rank_index], offset))
        batches.append(tuple(rows))
    return tuple(batches)


def _expand_hc(
    hidden: tuple[tuple[tuple[int, ...], ...], ...], multiplier: int
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    return tuple(
        tuple(tuple(vector for _ in range(multiplier)) for vector in batch)
        for batch in hidden
    )


def _gather_routes(
    tokens: tuple[tuple[int, ...], ...],
    route_table: mmap.mmap,
    route_top_k: int,
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    row_decoder = struct.Struct(f"<{route_top_k}q")
    return tuple(
        tuple(
            row_decoder.unpack_from(route_table, token_id * row_decoder.size)
            for token_id in batch
        )
        for batch in tokens
    )


def _expected_counters(
    deployment: DeepSeekV4LookupDeployment, token_count: int
) -> dict[str, int]:
    coefficients = deployment.expectations["counter_coefficients_per_token"]
    fixed = deployment.expectations["fixed_counters"]
    result = _empty_counters()
    for key, value in coefficients.items():
        result[key] = value * token_count
    for key, value in fixed.items():
        result[key] = value
    return result


def _json_embedding(
    value: tuple[tuple[tuple[int, ...], ...], ...],
) -> list[list[list[int]]]:
    return [[list(vector) for vector in batch] for batch in value]


def _json_hc(
    value: tuple[tuple[tuple[tuple[int, ...], ...], ...], ...],
) -> list[list[list[list[int]]]]:
    return [
        [[list(vector) for vector in copies] for copies in batch]
        for batch in value
    ]


class DeepSeekV4LookupServiceEngine:
    """Verified interpreter for the fixed three-operation lookup program."""

    def __init__(self, deployment: DeepSeekV4LookupDeployment):
        self.deployment = deployment

    @classmethod
    def load(cls, deployment_dir: Path) -> "DeepSeekV4LookupServiceEngine":
        return cls(load_deepseek_v4_lookup_deployment(deployment_dir))

    def execute(self, request_path: Path) -> dict[str, Any]:
        tokens, request_sha256 = _load_request(self.deployment, request_path)
        count = _token_count(tokens)
        counters = _empty_counters()
        state: dict[int, Any] = {TOKENS: tokens}
        completed = False
        dimensions = self.deployment.dimensions
        with _mapped_resources(self.deployment) as (embedding_tables, route_table):
            for pc, instruction in enumerate(self.deployment.instructions):
                counters["micro_ops_executed"] += 1
                if instruction.opcode == Opcode.COMPLETE:
                    if pc != len(self.deployment.instructions) - 1 or completed:
                        raise DeepSeekV4LookupServiceEngineError(
                            "lookup microcode has illegal COMPLETE control flow"
                        )
                    if not {EMBEDDING, HC_HIDDEN, HASH_ROUTES} <= state.keys():
                        raise DeepSeekV4LookupServiceEngineError(
                            "COMPLETE observed before all lookup outputs"
                        )
                    completed = True
                    counters["completion_events"] += 1
                    continue
                counters["semantic_operations_executed"] += 1
                if instruction.source not in state:
                    raise DeepSeekV4LookupServiceEngineError(
                        f"pc {pc} reads unavailable state slot {instruction.source}"
                    )
                if instruction.opcode == Opcode.TOKEN_EMBED:
                    state[instruction.destination] = _gather_embedding(
                        state[instruction.source], self.deployment, embedding_tables
                    )
                    counters["logical_input_bytes_read"] += count * 8
                    counters["logical_rom_bytes_read"] += (
                        count * dimensions["hidden_size"] * 2
                    )
                    counters["logical_activation_bytes_written"] += (
                        count * dimensions["hidden_size"] * 2
                    )
                    counters["rom_lookup_rows"] += count
                elif instruction.opcode == Opcode.HC_EXPAND:
                    state[instruction.destination] = _expand_hc(
                        state[instruction.source], instruction.immediate
                    )
                    counters["logical_activation_bytes_read"] += (
                        count * dimensions["hidden_size"] * 2
                    )
                    counters["logical_activation_bytes_written"] += (
                        count
                        * instruction.immediate
                        * dimensions["hidden_size"]
                        * 2
                    )
                    counters["bf16_codes_copied"] += (
                        count * instruction.immediate * dimensions["hidden_size"]
                    )
                elif instruction.opcode == Opcode.HASH_ROUTE:
                    state[instruction.destination] = _gather_routes(
                        state[instruction.source],
                        route_table,
                        dimensions["route_top_k"],
                    )
                    counters["logical_input_bytes_read"] += count * 8
                    counters["logical_rom_bytes_read"] += (
                        count * dimensions["route_top_k"] * 8
                    )
                    counters["logical_activation_bytes_written"] += (
                        count * dimensions["route_top_k"] * 8
                    )
                    counters["rom_lookup_rows"] += count
                else:  # Static verification makes this unreachable.
                    raise DeepSeekV4LookupServiceEngineError(
                        f"pc {pc} has an unsupported lookup opcode"
                    )
        if not completed:
            raise DeepSeekV4LookupServiceEngineError(
                "lookup microcode terminated without COMPLETE"
            )
        expected = _expected_counters(self.deployment, count)
        if counters != expected:
            differences = {
                key: {"actual": counters[key], "expected": expected[key]}
                for key in sorted(_COUNTER_KEYS)
                if counters[key] != expected[key]
            }
            raise DeepSeekV4LookupServiceEngineError(
                f"lookup execution counters do not reconcile: {differences}"
            )
        batch_size = len(tokens)
        sequence_length = len(tokens[0])
        hidden_size = dimensions["hidden_size"]
        multiplier = dimensions["hc_multiplier"]
        route_top_k = dimensions["route_top_k"]
        return {
            "build_id": self.deployment.manifest["build_id"],
            "counter_reconciliation": "exact",
            "counters": counters,
            "deployment_status": self.deployment.manifest["status"],
            "evidence_scope": self.deployment.evidence_scope,
            "execution_scope": "three_operator_real_payload_slice_only",
            "model_id": MODEL_ID,
            "outputs": [
                {
                    "dtype": "BF16_BITS",
                    "id": "embedding_bf16_codes",
                    "shape": [batch_size, sequence_length, hidden_size],
                    "values": _json_embedding(state[EMBEDDING]),
                },
                {
                    "dtype": "BF16_BITS",
                    "id": "hc_hidden_bf16_codes",
                    "shape": [
                        batch_size,
                        sequence_length,
                        multiplier,
                        hidden_size,
                    ],
                    "values": _json_hc(state[HC_HIDDEN]),
                },
                {
                    "dtype": "I64",
                    "id": "expert_ids",
                    "shape": [batch_size, sequence_length, route_top_k],
                    "values": _json_embedding(state[HASH_ROUTES]),
                },
            ],
            "request_sha256": request_sha256,
            "schema": RESULT_SCHEMA,
            "source_application_status": self.deployment.semantic["source"][
                "application_status"
            ],
            "status": "pass",
        }


def execute_deepseek_v4_lookup_deployment(
    deployment_dir: Path, request_path: Path
) -> dict[str, Any]:
    return DeepSeekV4LookupServiceEngine.load(deployment_dir).execute(request_path)


__all__ = [
    "DEPLOYMENT_SCHEMA",
    "DeepSeekV4LookupDeployment",
    "DeepSeekV4LookupServiceEngine",
    "DeepSeekV4LookupServiceEngineError",
    "MAX_REQUEST_TOKENS",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "execute_deepseek_v4_lookup_deployment",
    "load_deepseek_v4_lookup_deployment",
]
