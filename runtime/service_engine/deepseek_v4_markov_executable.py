"""Artifact-only execution of a bounded DeepSeek V4 Markov deployment.

The loader verifies the complete deployment artifact table, build identity,
semantic/resource manifests, selected-row inverse report, fixed wire program,
and BF16 payloads before execution.  It imports neither compiler code nor the
target reference.  Global token IDs are mapped to the deployment's explicit
selected-vocabulary indices only at the service boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from .deepseek_v4_markov import (
    DeepSeekV4MarkovServiceError,
    MarkovServiceEntropy,
    MarkovServiceResult,
    execute_deepseek_v4_markov_program,
)


MODEL_ID = "deepseek-v4-flash-0731"
DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_markov_executable_deployment.v1"
RESOURCE_SCHEMA = "opentallas.deepseek_v4_markov_resources.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_markov_executable_slice.v1"
ROUNDTRIP_SCHEMA = "opentallas.deepseek_v4_markov_executable_roundtrip.v1"
REQUEST_SCHEMA = "opentallas.deepseek_v4_markov_executable_request.v1"
RESULT_SCHEMA = "opentallas.deepseek_v4_markov_executable_result.v1"
PROGRAM_SCHEMA = "opentallas.deepseek_v4_markov_program.v1"
PROGRAM_SHA256 = "993f099a7fa78937de8eaa93e50cb883884a65fd2e50614b83134d0a30224584"
W1_NAME = "mtp.2.markov_head.markov_w1.weight"
W2_NAME = "mtp.2.markov_head.markov_w2.weight"
CLAIM_BOUNDARY = [
    "Executes the five-step Markov program over an authenticated selected-vocabulary view.",
    "Preserves selected global token identities and original tensor-parallel row ownership.",
    "Does not execute the complete 129280-row vocabulary, checkpoint-derived base logits, or a transformer block.",
    "Functional counters are not physical traffic, cycles, schedules, RTL, PPA, or performance evidence.",
]
_MAGIC = b"OTMKV1\0\0"
_HEADER = struct.Struct("<8sHHII32s")
_RECORD = struct.Struct("<HHHHHHHH")
_NO = 0xFFFF
_FIXED_ROLES = {
    "microcode",
    "microcode_disassembly",
    "program_contract",
    "resource_manifest",
    "roundtrip_report",
    "semantic_ir",
}
_VALID_STATUSES = {
    "official_checkpoint_selected_vocabulary_markov_not_full_model",
    "development_fixture_selected_vocabulary_markov_not_release_evidence",
}


class DeepSeekV4MarkovExecutableServiceError(RuntimeError):
    """Raised when deployment authentication or bounded execution fails."""


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"value is not canonical JSON: {exc}"
        ) from exc
    return (text + "\n").encode("ascii")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DeepSeekV4MarkovExecutableServiceError(
                f"duplicate JSON key {key!r}"
            )
        result[key] = value
    return result


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                DeepSeekV4MarkovExecutableServiceError(
                    f"nonfinite JSON number {token!r}"
                )
            ),
        )
    except DeepSeekV4MarkovExecutableServiceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"cannot load {label}: {exc}"
        ) from exc
    if type(value) is not dict:
        raise DeepSeekV4MarkovExecutableServiceError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} fields differ: missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )


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
        bound = f"[{minimum}, {maximum}]" if maximum is not None else f">={minimum}"
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} must be an exact integer in {bound}"
        )
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} must be lowercase SHA-256"
        )
    return value


def _selected_ids(value: object, label: str) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise DeepSeekV4MarkovExecutableServiceError(f"{label} must be an array")
    result = tuple(
        _integer(item, f"{label}[{index}]") for index, item in enumerate(value)
    )
    if not result or any(left >= right for left, right in zip(result, result[1:])):
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} must be nonempty and strictly increasing"
        )
    return result


def _safe_file(root: Path, value: object, label: str) -> tuple[str, Path]:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} is not canonical POSIX"
        )
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4MarkovExecutableServiceError(
                f"{label} traverses a symlink"
            )
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} escapes its deployment"
        ) from exc
    if not current.is_file():
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} is not a regular file"
        )
    return relative.as_posix(), current


def _read_file(path: Path, label: str, *, maximum: int | None = None) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"cannot read {label}: {exc}"
        ) from exc
    if maximum is not None and len(payload) > maximum:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} exceeds maximum size {maximum}"
        )
    return payload


@dataclass(frozen=True, slots=True)
class _Artifact:
    relative_path: str
    role: str
    sha256: str
    size_bytes: int
    path: Path


@dataclass(frozen=True, slots=True)
class DeepSeekV4MarkovExecutableDeployment:
    """Fully authenticated selected-vocabulary deployment held for execution."""

    root: Path
    manifest: dict[str, Any]
    manifest_sha256: str
    semantic: dict[str, Any]
    program_payload: bytes
    selected_global_token_ids: tuple[int, ...]
    embedding_weight_shards_bf16_codes: tuple[tuple[tuple[int, ...], ...], ...]
    head_weight_shards_bf16_codes: tuple[tuple[tuple[int, ...], ...], ...]
    resource_payload_sha256: dict[str, tuple[str, ...]]


def _verify_artifacts(
    root: Path, manifest: Mapping[str, Any]
) -> tuple[dict[str, _Artifact], list[dict[str, Any]]]:
    raw_records = manifest.get("artifacts")
    if not isinstance(raw_records, list) or not raw_records:
        raise DeepSeekV4MarkovExecutableServiceError(
            "deployment artifact table is absent"
        )
    paths: set[str] = set()
    roles: set[str] = set()
    by_role: dict[str, _Artifact] = {}
    retained: list[dict[str, Any]] = []
    previous: str | None = None
    for index, raw in enumerate(raw_records):
        if not isinstance(raw, Mapping):
            raise DeepSeekV4MarkovExecutableServiceError(
                f"artifact record {index} is not an object"
            )
        _exact_keys(
            raw,
            {"path", "role", "sha256", "size_bytes"},
            f"artifact record {index}",
        )
        relative, path = _safe_file(root, raw["path"], f"artifact {index}.path")
        role = raw["role"]
        if type(role) is not str or not role:
            raise DeepSeekV4MarkovExecutableServiceError(
                f"artifact record {index}.role must be nonempty"
            )
        if relative in paths or role in roles:
            raise DeepSeekV4MarkovExecutableServiceError(
                f"artifact record {index} duplicates a path or role"
            )
        if previous is not None and relative <= previous:
            raise DeepSeekV4MarkovExecutableServiceError(
                "artifact table must be strictly path-sorted"
            )
        previous = relative
        expected_sha = _digest(raw["sha256"], f"artifact {relative} SHA")
        expected_size = _integer(raw["size_bytes"], f"artifact {relative} size")
        payload = _read_file(path, f"artifact {relative}")
        if len(payload) != expected_size or hashlib.sha256(payload).hexdigest() != expected_sha:
            raise DeepSeekV4MarkovExecutableServiceError(
                f"artifact {relative!r} differs from deployment manifest"
            )
        artifact = _Artifact(relative, role, expected_sha, expected_size, path)
        by_role[role] = artifact
        retained.append(dict(raw))
        paths.add(relative)
        roles.add(role)
    return by_role, retained


def _verify_manifest(
    manifest: Mapping[str, Any], artifacts: list[dict[str, Any]]
) -> tuple[tuple[int, ...], str]:
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
            "selected_global_token_ids",
            "source_application_id",
            "status",
        },
        "deployment manifest",
    )
    if (
        manifest["schema"] != DEPLOYMENT_SCHEMA
        or manifest["model_id"] != MODEL_ID
        or manifest["status"] not in _VALID_STATUSES
        or manifest["claim_boundary"] != CLAIM_BOUNDARY
    ):
        raise DeepSeekV4MarkovExecutableServiceError(
            "deployment schema, status, or claim boundary differs"
        )
    compiler = manifest["compiler"]
    if not isinstance(compiler, Mapping):
        raise DeepSeekV4MarkovExecutableServiceError("compiler identity is absent")
    _exact_keys(compiler, {"name", "version"}, "compiler identity")
    if (
        compiler["name"] != "opentallas-deepseek-v4-markov-executable-compiler"
        or type(compiler["version"]) is not str
        or not compiler["version"]
    ):
        raise DeepSeekV4MarkovExecutableServiceError("compiler identity differs")
    abi = manifest["microcode_abi"]
    expected_abi = {
        "major": 1,
        "minor": 0,
        "name": "deepseek_v4_markov",
        "program_sha256": PROGRAM_SHA256,
    }
    if abi != expected_abi:
        raise DeepSeekV4MarkovExecutableServiceError("microcode ABI differs")
    selected = _selected_ids(
        manifest["selected_global_token_ids"], "selected_global_token_ids"
    )
    application_id = _digest(
        manifest["source_application_id"], "source_application_id"
    )
    identity = {
        "artifacts": artifacts,
        "compiler_version": compiler["version"],
        "microcode_abi": expected_abi,
        "model_id": MODEL_ID,
        "selected_global_token_ids": list(selected),
        "source_application_id": application_id,
    }
    expected_build_id = hashlib.sha256(_canonical_json_bytes(identity)).hexdigest()
    if manifest["build_id"] != expected_build_id:
        raise DeepSeekV4MarkovExecutableServiceError(
            "deployment build_id does not bind its artifact table"
        )
    return selected, application_id


def _expected_program_records() -> tuple[tuple[int, ...], ...]:
    records: list[tuple[int, ...]] = []
    for step in range(5):
        records.extend(
            (
                (1, step, 5, 1 if step == 0 else 4, _NO, _NO, 0, 0),
                (2, step, 6, 5, _NO, _NO, 1, 0),
                (3, step, 7, 0, 6, _NO, _NO, 0),
                (4, step, 4, 7, 2, 3 if step == 0 else 8, _NO, 0),
            )
        )
    records.append((0xFFFF, 5, 4, 7, 5, 8, _NO, 0))
    return tuple(records)


def _verify_program(payload: bytes) -> None:
    if len(payload) != _HEADER.size + 21 * _RECORD.size:
        raise DeepSeekV4MarkovExecutableServiceError("microcode extent differs")
    magic, major, minor, count, record_size, body_sha = _HEADER.unpack_from(payload)
    body = payload[_HEADER.size :]
    if (
        magic != _MAGIC
        or (major, minor) != (1, 0)
        or count != 21
        or record_size != _RECORD.size
        or hashlib.sha256(body).digest() != body_sha
        or hashlib.sha256(payload).hexdigest() != PROGRAM_SHA256
    ):
        raise DeepSeekV4MarkovExecutableServiceError("microcode identity differs")
    records = tuple(
        _RECORD.unpack_from(body, offset)
        for offset in range(0, len(body), _RECORD.size)
    )
    if records != _expected_program_records():
        raise DeepSeekV4MarkovExecutableServiceError("microcode causal records differ")


def _verify_contract(value: Mapping[str, Any]) -> None:
    required = {
        "abi",
        "causal_contract",
        "instruction_count",
        "micro_ops",
        "model_id",
        "numeric_contract",
        "numeric_profile",
        "outputs",
        "program_sha256",
        "registers",
        "resources",
        "schema",
        "source",
        "status",
        "timing_claim",
        "unsupported_claims",
    }
    _exact_keys(value, required, "program contract")
    if (
        value["schema"] != PROGRAM_SCHEMA
        or value["model_id"] != MODEL_ID
        or value["program_sha256"] != PROGRAM_SHA256
        or value["instruction_count"] != 21
        or value["abi"] != {"major": 1, "minor": 0}
        or value["timing_claim"] is not None
        or value["status"]
        != "compiler_contract_verified_execution_separately_required"
    ):
        raise DeepSeekV4MarkovExecutableServiceError("program contract identity differs")
    resources = value["resources"]
    if (
        not isinstance(resources, list)
        or len(resources) != 2
        or [resource.get("name") for resource in resources if isinstance(resource, Mapping)]
        != [W1_NAME, W2_NAME]
    ):
        raise DeepSeekV4MarkovExecutableServiceError(
            "program resource contract differs"
        )
    operations = value["micro_ops"]
    expected_operations = [
        {"opcode": opcode, "step": step}
        for step in range(5)
        for opcode in (
            "TOKEN_LOOKUP",
            "VOCABULARY_PROJECT",
            "BINARY32_BIAS_ADD",
            "SAMPLE_AND_CARRY",
        )
    ] + [{"opcode": "COMPLETE", "step": 5}]
    if operations != expected_operations:
        raise DeepSeekV4MarkovExecutableServiceError(
            "program operation contract differs"
        )


def _verify_semantic(
    value: Mapping[str, Any],
    *,
    selected: tuple[int, ...],
    application_id: str,
) -> dict[str, int]:
    _exact_keys(
        value,
        {
            "claim_boundary",
            "dimensions",
            "global_token_mapping",
            "model_id",
            "numeric_profile",
            "operations",
            "outputs",
            "schema",
            "source",
        },
        "semantic IR",
    )
    if (
        value["schema"] != SEMANTIC_SCHEMA
        or value["model_id"] != MODEL_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["numeric_profile"]
        != "opentallas.deepseek_v4_markov_loop_binary32.v1"
        or value["operations"]
        != [
            "TOKEN_LOOKUP",
            "VOCABULARY_PROJECT",
            "BINARY32_BIAS_ADD",
            "SAMPLE_AND_CARRY",
            "COMPLETE",
        ]
    ):
        raise DeepSeekV4MarkovExecutableServiceError("semantic contract differs")
    dimensions = value["dimensions"]
    expected_dimension_keys = {
        "block_size",
        "full_vocabulary_size",
        "markov_rank",
        "model_parallel",
        "selected_rows_per_rank",
        "selected_vocabulary_size",
    }
    if not isinstance(dimensions, Mapping):
        raise DeepSeekV4MarkovExecutableServiceError("semantic dimensions are absent")
    _exact_keys(dimensions, expected_dimension_keys, "semantic dimensions")
    parsed = {
        key: _integer(dimensions[key], f"dimensions.{key}", minimum=1)
        for key in expected_dimension_keys
    }
    if (
        parsed["block_size"] != 5
        or parsed["selected_vocabulary_size"] != len(selected)
        or parsed["selected_vocabulary_size"]
        != parsed["model_parallel"] * parsed["selected_rows_per_rank"]
        or selected[-1] >= parsed["full_vocabulary_size"]
    ):
        raise DeepSeekV4MarkovExecutableServiceError("semantic dimensions differ")
    expected_mapping = [
        {"global_token_id": token, "local_index": index}
        for index, token in enumerate(selected)
    ]
    if value["global_token_mapping"] != expected_mapping:
        raise DeepSeekV4MarkovExecutableServiceError(
            "semantic global-token mapping differs"
        )
    source = value["source"]
    if not isinstance(source, Mapping):
        raise DeepSeekV4MarkovExecutableServiceError("semantic source is absent")
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
    if source["application_id"] != application_id:
        raise DeepSeekV4MarkovExecutableServiceError(
            "semantic source application differs"
        )
    for key in ("checkpoint_lock_id", "verification_id"):
        _digest(source[key], f"semantic source {key}")
    return parsed


def _artifact_for(
    by_role: Mapping[str, _Artifact], role: str, path: object
) -> _Artifact:
    artifact = by_role.get(role)
    if artifact is None or artifact.relative_path != path:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"resource path differs from artifact role {role!r}"
        )
    return artifact


def _decode_bf16_rows(
    artifact: _Artifact,
    *,
    row_count: int,
    markov_rank: int,
    label: str,
) -> tuple[tuple[int, ...], ...]:
    payload = _read_file(artifact.path, label)
    expected_size = row_count * markov_rank * 2
    if len(payload) != expected_size:
        raise DeepSeekV4MarkovExecutableServiceError(f"{label} extent differs")
    codes = struct.unpack(f"<{row_count * markov_rank}H", payload)
    for index, code in enumerate(codes):
        if code & 0x7F80 == 0x7F80:
            raise DeepSeekV4MarkovExecutableServiceError(
                f"{label} contains nonfinite BF16 at element {index}"
            )
    return tuple(
        tuple(codes[start : start + markov_rank])
        for start in range(0, len(codes), markov_rank)
    )


def _verify_resource_record(
    value: Mapping[str, Any],
    *,
    artifact: _Artifact,
    label: str,
) -> None:
    _exact_keys(
        value,
        {
            "path",
            "sha256",
            "size_bytes",
            "source_assignment_path",
            "source_assignment_sha256",
            "source_assignment_size_bytes",
        },
        label,
    )
    if (
        value["path"] != artifact.relative_path
        or value["sha256"] != artifact.sha256
        or value["size_bytes"] != artifact.size_bytes
    ):
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} differs from authenticated artifact"
        )
    _digest(value["source_assignment_sha256"], f"{label} source SHA")
    _integer(value["source_assignment_size_bytes"], f"{label} source size", minimum=1)
    if type(value["source_assignment_path"]) is not str:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"{label} source path differs"
        )


def _verify_resources(
    value: Mapping[str, Any],
    *,
    dimensions: Mapping[str, int],
    selected: tuple[int, ...],
    application_id: str,
    by_role: Mapping[str, _Artifact],
) -> tuple[
    tuple[tuple[tuple[int, ...], ...], ...],
    tuple[tuple[tuple[int, ...], ...], ...],
    dict[str, tuple[str, ...]],
]:
    _exact_keys(
        value,
        {
            "application_id",
            "full_vocabulary_size",
            "markov_rank",
            "model_parallel",
            "ranks",
            "schema",
            "selected_global_token_ids",
            "selected_vocabulary_size",
            "source_tensor_payload_sha256",
        },
        "resource manifest",
    )
    if (
        value["schema"] != RESOURCE_SCHEMA
        or value["application_id"] != application_id
        or value["selected_global_token_ids"] != list(selected)
        or value["selected_vocabulary_size"]
        != dimensions["selected_vocabulary_size"]
        or value["full_vocabulary_size"] != dimensions["full_vocabulary_size"]
        or value["markov_rank"] != dimensions["markov_rank"]
        or value["model_parallel"] != dimensions["model_parallel"]
    ):
        raise DeepSeekV4MarkovExecutableServiceError(
            "resource manifest dimensions or identity differ"
        )
    full_hashes = value["source_tensor_payload_sha256"]
    if not isinstance(full_hashes, Mapping) or set(full_hashes) != {W1_NAME, W2_NAME}:
        raise DeepSeekV4MarkovExecutableServiceError(
            "resource source-tensor authority differs"
        )
    for name, digest in full_hashes.items():
        _digest(digest, f"resource source {name} SHA")
    ranks = value["ranks"]
    if not isinstance(ranks, list) or len(ranks) != dimensions["model_parallel"]:
        raise DeepSeekV4MarkovExecutableServiceError("resource rank count differs")
    w1_shards: list[tuple[tuple[int, ...], ...]] = []
    w2_shards: list[tuple[tuple[int, ...], ...]] = []
    w1_hashes: list[str] = []
    w2_hashes: list[str] = []
    observed_ids: list[int] = []
    for expected_rank, rank_value in enumerate(ranks):
        if not isinstance(rank_value, Mapping):
            raise DeepSeekV4MarkovExecutableServiceError(
                f"resource rank {expected_rank} is not an object"
            )
        _exact_keys(
            rank_value,
            {"global_token_ids", "rank", "row_start", "row_stop", "w1", "w2"},
            f"resource rank {expected_rank}",
        )
        rank_ids = _selected_ids(
            rank_value["global_token_ids"], f"resource rank {expected_rank} IDs"
        )
        row_start = _integer(rank_value["row_start"], "resource row_start")
        row_stop = _integer(rank_value["row_stop"], "resource row_stop", minimum=1)
        if (
            rank_value["rank"] != expected_rank
            or len(rank_ids) != dimensions["selected_rows_per_rank"]
            or row_start >= row_stop
            or any(token < row_start or token >= row_stop for token in rank_ids)
        ):
            raise DeepSeekV4MarkovExecutableServiceError(
                f"resource rank {expected_rank} ownership differs"
            )
        observed_ids.extend(rank_ids)
        raw_w1 = rank_value["w1"]
        raw_w2 = rank_value["w2"]
        if not isinstance(raw_w1, Mapping) or not isinstance(raw_w2, Mapping):
            raise DeepSeekV4MarkovExecutableServiceError(
                f"resource rank {expected_rank} tensor records differ"
            )
        w1_role = f"markov_w1_rank_{expected_rank:03d}"
        w2_role = f"markov_w2_rank_{expected_rank:03d}"
        w1_artifact = _artifact_for(by_role, w1_role, raw_w1.get("path"))
        w2_artifact = _artifact_for(by_role, w2_role, raw_w2.get("path"))
        _verify_resource_record(
            raw_w1, artifact=w1_artifact, label=f"resource rank {expected_rank} W1"
        )
        _verify_resource_record(
            raw_w2, artifact=w2_artifact, label=f"resource rank {expected_rank} W2"
        )
        w1_shards.append(
            _decode_bf16_rows(
                w1_artifact,
                row_count=len(rank_ids),
                markov_rank=dimensions["markov_rank"],
                label=f"resource rank {expected_rank} W1",
            )
        )
        w2_shards.append(
            _decode_bf16_rows(
                w2_artifact,
                row_count=len(rank_ids),
                markov_rank=dimensions["markov_rank"],
                label=f"resource rank {expected_rank} W2",
            )
        )
        w1_hashes.append(w1_artifact.sha256)
        w2_hashes.append(w2_artifact.sha256)
    if tuple(observed_ids) != selected:
        raise DeepSeekV4MarkovExecutableServiceError(
            "resource rank IDs do not reconstruct selected vocabulary"
        )
    expected_roles = _FIXED_ROLES | {
        f"markov_{weight}_rank_{rank:03d}"
        for rank in range(dimensions["model_parallel"])
        for weight in ("w1", "w2")
    }
    if set(by_role) != expected_roles:
        raise DeepSeekV4MarkovExecutableServiceError(
            "deployment artifact roles differ from resource topology"
        )
    return (
        tuple(w1_shards),
        tuple(w2_shards),
        {"w1": tuple(w1_hashes), "w2": tuple(w2_hashes)},
    )


def _verify_roundtrip(
    value: Mapping[str, Any],
    *,
    selected: tuple[int, ...],
    application_id: str,
    by_role: Mapping[str, _Artifact],
    model_parallel: int,
) -> None:
    required = {
        "application_id",
        "checked_deployment_payload_bytes",
        "checked_deployment_payload_count",
        "checked_source_assignment_bytes",
        "checked_source_assignment_count",
        "model_id",
        "program_sha256",
        "reconstructed",
        "roundtrip_id",
        "schema",
        "selected_global_token_ids",
        "status",
    }
    _exact_keys(value, required, "roundtrip report")
    identity = dict(value)
    observed_id = identity.pop("roundtrip_id")
    expected_id = hashlib.sha256(_canonical_json_bytes(identity)).hexdigest()
    reconstructed = value["reconstructed"]
    if not isinstance(reconstructed, list):
        raise DeepSeekV4MarkovExecutableServiceError(
            "roundtrip reconstructed rows are absent"
        )
    selected_paths = {
        artifact.relative_path: artifact
        for role, artifact in by_role.items()
        if role.startswith("markov_w1_rank_") or role.startswith("markov_w2_rank_")
    }
    seen: set[str] = set()
    selected_bytes = 0
    source_bytes = 0
    for index, record in enumerate(reconstructed):
        if not isinstance(record, Mapping):
            raise DeepSeekV4MarkovExecutableServiceError(
                f"roundtrip record {index} is not an object"
            )
        _exact_keys(
            record,
            {
                "deployment_path",
                "global_token_ids",
                "rank",
                "selected_payload_sha256",
                "selected_payload_size_bytes",
                "source_assignment_path",
                "source_assignment_sha256",
                "source_assignment_size_bytes",
                "tensor_name",
            },
            f"roundtrip record {index}",
        )
        artifact = selected_paths.get(record["deployment_path"])
        if (
            artifact is None
            or artifact.relative_path in seen
            or record["selected_payload_sha256"] != artifact.sha256
            or record["selected_payload_size_bytes"] != artifact.size_bytes
        ):
            raise DeepSeekV4MarkovExecutableServiceError(
                f"roundtrip record {index} differs from authenticated payload"
            )
        seen.add(artifact.relative_path)
        selected_bytes += artifact.size_bytes
        source_bytes += _integer(
            record["source_assignment_size_bytes"],
            f"roundtrip record {index} source bytes",
            minimum=1,
        )
        _digest(record["source_assignment_sha256"], "roundtrip source SHA")
    if (
        value["schema"] != ROUNDTRIP_SCHEMA
        or value["application_id"] != application_id
        or value["model_id"] != MODEL_ID
        or value["program_sha256"] != PROGRAM_SHA256
        or value["selected_global_token_ids"] != list(selected)
        or value["status"]
        != "all_selected_rows_match_verified_canonical_assignments"
        or value["checked_deployment_payload_count"] != 2 * model_parallel
        or value["checked_source_assignment_count"] != 2 * model_parallel
        or value["checked_deployment_payload_bytes"] != selected_bytes
        or value["checked_source_assignment_bytes"] != source_bytes
        or seen != set(selected_paths)
        or observed_id != expected_id
    ):
        raise DeepSeekV4MarkovExecutableServiceError(
            "roundtrip report identity or accounting differs"
        )


def load_deepseek_v4_markov_executable_deployment(
    deployment_dir: Path,
) -> DeepSeekV4MarkovExecutableDeployment:
    """Load and fully authenticate one bounded Markov deployment."""

    root = Path(deployment_dir).resolve()
    if not root.is_dir():
        raise DeepSeekV4MarkovExecutableServiceError(
            f"Markov deployment is not a directory: {root}"
        )
    manifest_path = root / "deployment_manifest.json"
    if manifest_path.is_symlink():
        raise DeepSeekV4MarkovExecutableServiceError(
            "deployment manifest must not be a symlink"
        )
    manifest_payload = _read_file(
        manifest_path, "deployment manifest", maximum=1024 * 1024
    )
    manifest = _load_json(manifest_path, "deployment manifest")
    by_role, artifact_records = _verify_artifacts(root, manifest)
    selected, application_id = _verify_manifest(manifest, artifact_records)
    missing = _FIXED_ROLES - set(by_role)
    if missing:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"deployment lacks fixed artifact roles {sorted(missing)}"
        )
    entrypoint = manifest["entrypoint"]
    if not isinstance(entrypoint, Mapping):
        raise DeepSeekV4MarkovExecutableServiceError("deployment entrypoint is absent")
    expected_entrypoint = {
        "microcode": by_role["microcode"].relative_path,
        "program_contract": by_role["program_contract"].relative_path,
        "resource_manifest": by_role["resource_manifest"].relative_path,
        "semantic_ir": by_role["semantic_ir"].relative_path,
    }
    if dict(entrypoint) != expected_entrypoint:
        raise DeepSeekV4MarkovExecutableServiceError(
            "deployment entrypoint differs from artifact roles"
        )
    program = _read_file(by_role["microcode"].path, "microcode", maximum=4096)
    _verify_program(program)
    contract = _load_json(by_role["program_contract"].path, "program contract")
    _verify_contract(contract)
    semantic = _load_json(by_role["semantic_ir"].path, "semantic IR")
    dimensions = _verify_semantic(
        semantic, selected=selected, application_id=application_id
    )
    resources = _load_json(by_role["resource_manifest"].path, "resource manifest")
    w1, w2, resource_hashes = _verify_resources(
        resources,
        dimensions=dimensions,
        selected=selected,
        application_id=application_id,
        by_role=by_role,
    )
    roundtrip = _load_json(by_role["roundtrip_report"].path, "roundtrip report")
    _verify_roundtrip(
        roundtrip,
        selected=selected,
        application_id=application_id,
        by_role=by_role,
        model_parallel=dimensions["model_parallel"],
    )
    disassembly = _read_file(
        by_role["microcode_disassembly"].path,
        "microcode disassembly",
        maximum=64 * 1024,
    )
    try:
        disassembly_text = disassembly.decode("ascii")
    except UnicodeDecodeError as exc:
        raise DeepSeekV4MarkovExecutableServiceError(
            "microcode disassembly is not ASCII"
        ) from exc
    if (
        not disassembly_text.startswith("# OpenTallas DeepSeek V4 Markov ABI 1.0\n")
        or disassembly_text.count("TOKEN_LOOKUP") != 5
        or disassembly_text.count("VOCABULARY_PROJECT") != 5
        or disassembly_text.count("BINARY32_BIAS_ADD") != 5
        or disassembly_text.count("SAMPLE_AND_CARRY") != 5
        or disassembly_text.count("COMPLETE") != 1
    ):
        raise DeepSeekV4MarkovExecutableServiceError(
            "microcode disassembly differs from fixed program"
        )
    return DeepSeekV4MarkovExecutableDeployment(
        root=root,
        manifest=manifest,
        manifest_sha256=hashlib.sha256(manifest_payload).hexdigest(),
        semantic=semantic,
        program_payload=program,
        selected_global_token_ids=selected,
        embedding_weight_shards_bf16_codes=w1,
        head_weight_shards_bf16_codes=w2,
        resource_payload_sha256=resource_hashes,
    )


def _request_entropy(value: object) -> MarkovServiceEntropy | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise DeepSeekV4MarkovExecutableServiceError(
            "request entropy must be an object or null"
        )
    _exact_keys(value, {"binary32_codes", "offset"}, "request entropy")
    codes = value["binary32_codes"]
    if not isinstance(codes, list):
        raise DeepSeekV4MarkovExecutableServiceError(
            "request entropy binary32_codes must be an array"
        )
    try:
        return MarkovServiceEntropy(
            tuple(codes),
            _integer(value["offset"], "request entropy offset"),
        )
    except DeepSeekV4MarkovServiceError as exc:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"request entropy differs: {exc}"
        ) from exc


def _parse_request(
    deployment: DeepSeekV4MarkovExecutableDeployment,
    request: object,
) -> tuple[dict[str, Any], tuple[int, ...], MarkovServiceEntropy | None, str]:
    if type(request) is not dict:
        raise DeepSeekV4MarkovExecutableServiceError("request must be an exact object")
    _exact_keys(
        request,
        {
            "base_logits_binary32_codes",
            "build_id",
            "entropy",
            "input_global_token_ids",
            "model_id",
            "require_pytorch_cuda_equivalence",
            "schema",
            "temperature_binary32",
        },
        "execution request",
    )
    if (
        request["schema"] != REQUEST_SCHEMA
        or request["model_id"] != MODEL_ID
        or request["build_id"] != deployment.manifest["build_id"]
    ):
        raise DeepSeekV4MarkovExecutableServiceError("request identity differs")
    raw_tokens = request["input_global_token_ids"]
    if not isinstance(raw_tokens, list) or not raw_tokens:
        raise DeepSeekV4MarkovExecutableServiceError(
            "input_global_token_ids must be a nonempty array"
        )
    mapping = {
        token: index
        for index, token in enumerate(deployment.selected_global_token_ids)
    }
    local: list[int] = []
    for batch, token in enumerate(raw_tokens):
        if type(token) is not int or token not in mapping:
            raise DeepSeekV4MarkovExecutableServiceError(
                f"input_global_token_ids[{batch}] is outside selected vocabulary"
            )
        local.append(mapping[token])
    if type(request["require_pytorch_cuda_equivalence"]) is not bool:
        raise DeepSeekV4MarkovExecutableServiceError(
            "require_pytorch_cuda_equivalence must be an exact bool"
        )
    _integer(
        request["temperature_binary32"],
        "temperature_binary32",
        maximum=(1 << 32) - 1,
    )
    normalized = dict(request)
    request_sha = hashlib.sha256(_canonical_json_bytes(normalized)).hexdigest()
    return normalized, tuple(local), _request_entropy(request["entropy"]), request_sha


def _json_tensor3(value: tuple[tuple[tuple[int, ...], ...], ...]) -> list:
    return [[list(row) for row in batch] for batch in value]


def _json_result(
    deployment: DeepSeekV4MarkovExecutableDeployment,
    request: Mapping[str, Any],
    request_sha256: str,
    result: MarkovServiceResult,
) -> dict[str, Any]:
    selected = deployment.selected_global_token_ids
    global_outputs = tuple(
        tuple(selected[local] for local in row) for row in result.output_token_ids
    )
    next_entropy = result.next_entropy
    body: dict[str, Any] = {
        "base_logits_binary32_codes": _json_tensor3(
            result.base_logits_binary32_codes
        ),
        "build_id": deployment.manifest["build_id"],
        "deployment_manifest_sha256": deployment.manifest_sha256,
        "entropy_continuation": (
            None
            if next_entropy is None
            else {
                "binary32_codes": list(next_entropy.binary32_codes),
                "offset": next_entropy.offset,
                "stream_sha256": next_entropy.stream_sha256,
            }
        ),
        "hashes": {
            "adjusted_logits_binary32_sha256": result.adjusted_logits_binary32_sha256,
            "base_logits_binary32_sha256": result.base_logits_binary32_sha256,
            "embedding_weight_bf16_sha256": result.embedding_weight_bf16_sha256,
            "head_weight_bf16_sha256": result.head_weight_bf16_sha256,
            "markov_bias_binary32_sha256": result.markov_bias_binary32_sha256,
            "markov_embeddings_bf16_sha256": result.markov_embeddings_bf16_sha256,
            "output_local_token_ids_sha256": result.output_token_ids_sha256,
        },
        "input_global_token_ids": list(request["input_global_token_ids"]),
        "logical_counters": dict(result.logical_counters),
        "markov_bias_binary32_codes": _json_tensor3(
            result.markov_bias_binary32_codes
        ),
        "markov_embeddings_bf16_codes": _json_tensor3(
            result.markov_embeddings_bf16_codes
        ),
        "model_id": MODEL_ID,
        "output_global_token_ids": [list(row) for row in global_outputs],
        "output_local_token_ids": [list(row) for row in result.output_token_ids],
        "program_sha256": result.program_sha256,
        "request_sha256": request_sha256,
        "resource_payload_sha256": {
            key: list(value)
            for key, value in deployment.resource_payload_sha256.items()
        },
        "sampling": {
            "entropy_offset_after": result.entropy_offset_after,
            "entropy_offset_before": result.entropy_offset_before,
            "entropy_stream_sha256": result.entropy_stream_sha256,
            "mode": result.sampling_mode,
            "numeric_profile": result.sampling_numeric_profile,
            "require_pytorch_cuda_equivalence": result.require_pytorch_cuda_equivalence,
            "source_equivalence": result.source_equivalence,
            "temperature_binary32": result.temperature_binary32,
        },
        "schema": RESULT_SCHEMA,
        "selected_global_token_ids": list(selected),
        "source_application_id": deployment.manifest["source_application_id"],
        "status": "artifact_authenticated_selected_vocabulary_markov_execution",
        "adjusted_logits_binary32_codes": _json_tensor3(
            result.adjusted_logits_binary32_codes
        ),
    }
    body["result_id"] = hashlib.sha256(_canonical_json_bytes(body)).hexdigest()
    return body


def execute_deepseek_v4_markov_executable_deployment(
    deployment_dir: Path,
    request: object,
) -> dict[str, Any]:
    """Authenticate artifacts and execute one global-token Markov request."""

    deployment = load_deepseek_v4_markov_executable_deployment(deployment_dir)
    normalized, local_tokens, entropy, request_sha = _parse_request(
        deployment, request
    )
    try:
        result = execute_deepseek_v4_markov_program(
            deployment.program_payload,
            normalized["base_logits_binary32_codes"],
            local_tokens,
            deployment.embedding_weight_shards_bf16_codes,
            deployment.head_weight_shards_bf16_codes,
            temperature_binary32=normalized["temperature_binary32"],
            entropy=entropy,
            tensor_parallel_world_size=len(
                deployment.embedding_weight_shards_bf16_codes
            ),
            require_pytorch_cuda_equivalence=normalized[
                "require_pytorch_cuda_equivalence"
            ],
        )
    except DeepSeekV4MarkovServiceError as exc:
        raise DeepSeekV4MarkovExecutableServiceError(
            f"bounded Markov execution poisoned: {exc}"
        ) from exc
    return _json_result(deployment, normalized, request_sha, result)


__all__ = [
    "DEPLOYMENT_SCHEMA",
    "DeepSeekV4MarkovExecutableDeployment",
    "DeepSeekV4MarkovExecutableServiceError",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "execute_deepseek_v4_markov_executable_deployment",
    "load_deepseek_v4_markov_executable_deployment",
]
