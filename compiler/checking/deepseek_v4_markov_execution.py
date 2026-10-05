"""Independent differential for bounded artifact-driven Markov execution.

This checker imports neither the deployment builder nor service implementation.
It verifies the current artifact table, reruns the independent canonical-row
inverse check, reconstructs the selected BF16 shards, executes the target
reference, and compares the persisted-shaped result and functional counters.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from pathlib import Path
import struct
from typing import Any

from compiler.checking.deepseek_v4_markov_executable import (
    verify_deepseek_v4_markov_executable_roundtrip,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json
from runtime.reference.markov_loop import (
    MarkovLoopReferenceError,
    markov_autoregressive_loop_bf16,
)
from runtime.reference.sampling import (
    ExplicitExponentialEntropy,
    SamplingReferenceError,
)


MODEL_ID = "deepseek-v4-flash-0731"
DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_markov_executable_deployment.v1"
RESOURCE_SCHEMA = "opentallas.deepseek_v4_markov_resources.v1"
REQUEST_SCHEMA = "opentallas.deepseek_v4_markov_executable_request.v1"
RESULT_SCHEMA = "opentallas.deepseek_v4_markov_executable_result.v1"
DIFFERENTIAL_SCHEMA = "opentallas.deepseek_v4_markov_executable_differential.v1"
PROGRAM_SHA256 = "993f099a7fa78937de8eaa93e50cb883884a65fd2e50614b83134d0a30224584"
_VALID_STATUSES = {
    "official_checkpoint_selected_vocabulary_markov_not_full_model",
    "development_fixture_selected_vocabulary_markov_not_release_evidence",
}


class DeepSeekV4MarkovExecutionCheckError(RuntimeError):
    """Raised when artifact execution differs from the independent reference."""


def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        return load_strict_json(path)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4MarkovExecutionCheckError(
            f"cannot load {label}: {exc}"
        ) from exc


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    observed = set(value)
    if observed != expected:
        raise DeepSeekV4MarkovExecutionCheckError(
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
        raise DeepSeekV4MarkovExecutionCheckError(
            f"{label} must be an exact integer in {bound}"
        )
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4MarkovExecutionCheckError(
            f"{label} must be lowercase SHA-256"
        )
    return value


def _selected_ids(value: object, label: str) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise DeepSeekV4MarkovExecutionCheckError(f"{label} must be an array")
    result = tuple(
        _integer(item, f"{label}[{index}]") for index, item in enumerate(value)
    )
    if not result or any(left >= right for left, right in zip(result, result[1:])):
        raise DeepSeekV4MarkovExecutionCheckError(
            f"{label} must be nonempty and strictly increasing"
        )
    return result


def _safe_file(root: Path, value: object, label: str) -> Path:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4MarkovExecutionCheckError(
            f"{label} is not a safe relative path"
        )
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4MarkovExecutionCheckError(
            f"{label} is not a safe relative path"
        )
    if relative.as_posix() != value:
        raise DeepSeekV4MarkovExecutionCheckError(
            f"{label} is not canonical POSIX"
        )
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4MarkovExecutionCheckError(
                f"{label} traverses a symlink"
            )
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise DeepSeekV4MarkovExecutionCheckError(f"{label} escapes its root") from exc
    if not current.is_file():
        raise DeepSeekV4MarkovExecutionCheckError(
            f"{label} is not a regular file"
        )
    return current


def _hash_file(path: Path, label: str) -> tuple[str, int, bytes]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise DeepSeekV4MarkovExecutionCheckError(
            f"cannot read {label}: {exc}"
        ) from exc
    return hashlib.sha256(payload).hexdigest(), len(payload), payload


def _verify_manifest(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], str]:
    path = root / "deployment_manifest.json"
    if path.is_symlink():
        raise DeepSeekV4MarkovExecutionCheckError(
            "deployment manifest must not be a symlink"
        )
    manifest = _load(path, "deployment manifest")
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
    ):
        raise DeepSeekV4MarkovExecutionCheckError("deployment identity differs")
    selected = _selected_ids(
        manifest["selected_global_token_ids"], "selected_global_token_ids"
    )
    compiler = manifest["compiler"]
    if not isinstance(compiler, Mapping):
        raise DeepSeekV4MarkovExecutionCheckError("deployment compiler is absent")
    _exact_keys(compiler, {"name", "version"}, "deployment compiler")
    if (
        compiler["name"] != "opentallas-deepseek-v4-markov-executable-compiler"
        or type(compiler["version"]) is not str
        or not compiler["version"]
    ):
        raise DeepSeekV4MarkovExecutionCheckError("deployment compiler differs")
    abi = manifest["microcode_abi"]
    if abi != {
        "major": 1,
        "minor": 0,
        "name": "deepseek_v4_markov",
        "program_sha256": PROGRAM_SHA256,
    }:
        raise DeepSeekV4MarkovExecutionCheckError("deployment microcode ABI differs")
    raw_artifacts = manifest["artifacts"]
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise DeepSeekV4MarkovExecutionCheckError("deployment artifacts are absent")
    roles: dict[str, dict[str, Any]] = {}
    retained: list[dict[str, Any]] = []
    paths: set[str] = set()
    previous: str | None = None
    for index, record in enumerate(raw_artifacts):
        if not isinstance(record, Mapping):
            raise DeepSeekV4MarkovExecutionCheckError(
                f"artifact record {index} is not an object"
            )
        _exact_keys(
            record,
            {"path", "role", "sha256", "size_bytes"},
            f"artifact record {index}",
        )
        relative = record["path"]
        artifact_path = _safe_file(root, relative, f"artifact {index}.path")
        role = record["role"]
        if type(role) is not str or not role or role in roles or relative in paths:
            raise DeepSeekV4MarkovExecutionCheckError(
                f"artifact record {index} duplicates path or role"
            )
        if previous is not None and relative <= previous:
            raise DeepSeekV4MarkovExecutionCheckError(
                "artifact table is not strictly path-sorted"
            )
        previous = relative
        sha, size, _ = _hash_file(artifact_path, f"artifact {relative}")
        if (
            sha != _digest(record["sha256"], f"artifact {relative} SHA")
            or size != _integer(record["size_bytes"], f"artifact {relative} size")
        ):
            raise DeepSeekV4MarkovExecutionCheckError(
                f"artifact {relative!r} differs from deployment manifest"
            )
        retained_record = dict(record)
        retained.append(retained_record)
        roles[role] = retained_record
        paths.add(relative)
    application_id = _digest(
        manifest["source_application_id"], "source_application_id"
    )
    identity = {
        "artifacts": retained,
        "compiler_version": compiler["version"],
        "microcode_abi": abi,
        "model_id": MODEL_ID,
        "selected_global_token_ids": list(selected),
        "source_application_id": application_id,
    }
    if manifest["build_id"] != hashlib.sha256(
        canonical_json_bytes(identity)
    ).hexdigest():
        raise DeepSeekV4MarkovExecutionCheckError(
            "deployment build_id does not bind artifacts"
        )
    manifest_sha, _, _ = _hash_file(path, "deployment manifest")
    return manifest, roles, manifest_sha


def _resource_shards(
    root: Path,
    resources: Mapping[str, Any],
    roles: Mapping[str, Mapping[str, Any]],
) -> tuple[
    tuple[int, ...],
    tuple[tuple[tuple[int, ...], ...], ...],
    tuple[tuple[tuple[int, ...], ...], ...],
    dict[str, list[str]],
]:
    if resources.get("schema") != RESOURCE_SCHEMA:
        raise DeepSeekV4MarkovExecutionCheckError("resource schema differs")
    selected = _selected_ids(
        resources.get("selected_global_token_ids"), "resource selected IDs"
    )
    markov_rank = _integer(resources.get("markov_rank"), "markov rank", minimum=1)
    model_parallel = _integer(
        resources.get("model_parallel"), "model parallel", minimum=1
    )
    ranks = resources.get("ranks")
    if not isinstance(ranks, list) or len(ranks) != model_parallel:
        raise DeepSeekV4MarkovExecutionCheckError("resource ranks differ")
    w1_shards: list[tuple[tuple[int, ...], ...]] = []
    w2_shards: list[tuple[tuple[int, ...], ...]] = []
    hashes = {"w1": [], "w2": []}
    observed_ids: list[int] = []
    for rank, rank_record in enumerate(ranks):
        if not isinstance(rank_record, Mapping) or rank_record.get("rank") != rank:
            raise DeepSeekV4MarkovExecutionCheckError(
                f"resource rank {rank} differs"
            )
        rank_ids = _selected_ids(
            rank_record.get("global_token_ids"), f"resource rank {rank} IDs"
        )
        observed_ids.extend(rank_ids)
        for key, destination in (("w1", w1_shards), ("w2", w2_shards)):
            resource = rank_record.get(key)
            role = roles.get(f"markov_{key}_rank_{rank:03d}")
            if not isinstance(resource, Mapping) or not isinstance(role, Mapping):
                raise DeepSeekV4MarkovExecutionCheckError(
                    f"resource rank {rank} {key} authority is absent"
                )
            if (
                resource.get("path") != role.get("path")
                or resource.get("sha256") != role.get("sha256")
                or resource.get("size_bytes") != role.get("size_bytes")
            ):
                raise DeepSeekV4MarkovExecutionCheckError(
                    f"resource rank {rank} {key} differs from artifact"
                )
            artifact = _safe_file(
                root, resource["path"], f"resource rank {rank} {key} path"
            )
            _, size, payload = _hash_file(artifact, f"resource rank {rank} {key}")
            expected_size = len(rank_ids) * markov_rank * 2
            if size != expected_size:
                raise DeepSeekV4MarkovExecutionCheckError(
                    f"resource rank {rank} {key} extent differs"
                )
            codes = struct.unpack(f"<{len(rank_ids) * markov_rank}H", payload)
            destination.append(
                tuple(
                    tuple(codes[start : start + markov_rank])
                    for start in range(0, len(codes), markov_rank)
                )
            )
            hashes[key].append(role["sha256"])
    if tuple(observed_ids) != selected:
        raise DeepSeekV4MarkovExecutionCheckError(
            "resource ranks do not reconstruct selected IDs"
        )
    return selected, tuple(w1_shards), tuple(w2_shards), hashes


def _entropy(value: object) -> ExplicitExponentialEntropy | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise DeepSeekV4MarkovExecutionCheckError(
            "request entropy must be an object or null"
        )
    _exact_keys(value, {"binary32_codes", "offset"}, "request entropy")
    codes = value["binary32_codes"]
    if not isinstance(codes, list):
        raise DeepSeekV4MarkovExecutionCheckError(
            "request entropy codes must be an array"
        )
    try:
        return ExplicitExponentialEntropy(
            tuple(codes), _integer(value["offset"], "request entropy offset")
        )
    except SamplingReferenceError as exc:
        raise DeepSeekV4MarkovExecutionCheckError(
            f"request entropy differs: {exc}"
        ) from exc


def _local_inputs(
    request: Mapping[str, Any],
    *,
    selected: tuple[int, ...],
    build_id: str,
) -> tuple[tuple[int, ...], str]:
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
        or request["build_id"] != build_id
        or type(request["require_pytorch_cuda_equivalence"]) is not bool
    ):
        raise DeepSeekV4MarkovExecutionCheckError("execution request identity differs")
    _integer(
        request["temperature_binary32"],
        "temperature_binary32",
        maximum=(1 << 32) - 1,
    )
    tokens = request["input_global_token_ids"]
    if not isinstance(tokens, list) or not tokens:
        raise DeepSeekV4MarkovExecutionCheckError(
            "input_global_token_ids must be a nonempty array"
        )
    mapping = {token: index for index, token in enumerate(selected)}
    local: list[int] = []
    for batch, token in enumerate(tokens):
        if type(token) is not int or token not in mapping:
            raise DeepSeekV4MarkovExecutionCheckError(
                f"input_global_token_ids[{batch}] is outside selected vocabulary"
            )
        local.append(mapping[token])
    return tuple(local), hashlib.sha256(canonical_json_bytes(dict(request))).hexdigest()


def _tensor3(value: tuple[tuple[tuple[int, ...], ...], ...]) -> list:
    return [[list(row) for row in batch] for batch in value]


def _expected_counters(reference: object) -> dict[str, int]:
    counters = reference.counters
    result = {
        name: getattr(counters, name) for name in counters.__dataclass_fields__
    }
    result.update(
        {
            "micro_ops_executed": 21,
            "lookup_micro_ops": 5,
            "projection_micro_ops": 5,
            "bias_add_micro_ops": 5,
            "sampling_micro_ops": 5,
            "complete_micro_ops": 1,
        }
    )
    return result


def _compare_result(
    result: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    manifest_sha256: str,
    request: Mapping[str, Any],
    request_sha256: str,
    selected: tuple[int, ...],
    resource_hashes: Mapping[str, list[str]],
    expected: object,
) -> tuple[str, int]:
    expected_keys = {
        "adjusted_logits_binary32_codes",
        "base_logits_binary32_codes",
        "build_id",
        "deployment_manifest_sha256",
        "entropy_continuation",
        "hashes",
        "input_global_token_ids",
        "logical_counters",
        "markov_bias_binary32_codes",
        "markov_embeddings_bf16_codes",
        "model_id",
        "output_global_token_ids",
        "output_local_token_ids",
        "program_sha256",
        "request_sha256",
        "resource_payload_sha256",
        "result_id",
        "sampling",
        "schema",
        "selected_global_token_ids",
        "source_application_id",
        "status",
    }
    _exact_keys(result, expected_keys, "execution result")
    identity = dict(result)
    observed_result_id = identity.pop("result_id")
    expected_result_id = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    expected_global = [
        [selected[local] for local in row] for row in expected.output_token_ids
    ]
    expected_entropy = (
        None
        if expected.next_entropy is None
        else {
            "binary32_codes": list(expected.next_entropy.binary32_codes),
            "offset": expected.next_entropy.offset,
            "stream_sha256": expected.next_entropy.stream_sha256,
        }
    )
    expected_hashes = {
        "adjusted_logits_binary32_sha256": expected.adjusted_logits_binary32_sha256,
        "base_logits_binary32_sha256": expected.base_logits_binary32_sha256,
        "embedding_weight_bf16_sha256": expected.embedding_weight_bf16_sha256,
        "head_weight_bf16_sha256": expected.head_weight_bf16_sha256,
        "markov_bias_binary32_sha256": expected.markov_bias_binary32_sha256,
        "markov_embeddings_bf16_sha256": expected.markov_embeddings_bf16_sha256,
        "output_local_token_ids_sha256": expected.output_token_ids_sha256,
    }
    expected_sampling = {
        "entropy_offset_after": expected.entropy_offset_after,
        "entropy_offset_before": expected.entropy_offset_before,
        "entropy_stream_sha256": expected.entropy_stream_sha256,
        "mode": expected.sampling_mode,
        "numeric_profile": expected.sampling_numeric_profile,
        "require_pytorch_cuda_equivalence": expected.require_pytorch_cuda_equivalence,
        "source_equivalence": expected.source_equivalence,
        "temperature_binary32": expected.temperature_binary32,
    }
    comparisons = {
        "adjusted_logits_binary32_codes": _tensor3(
            expected.adjusted_logits_binary32_codes
        ),
        "base_logits_binary32_codes": _tensor3(
            expected.base_logits_binary32_codes
        ),
        "build_id": manifest["build_id"],
        "deployment_manifest_sha256": manifest_sha256,
        "entropy_continuation": expected_entropy,
        "hashes": expected_hashes,
        "input_global_token_ids": request["input_global_token_ids"],
        "logical_counters": _expected_counters(expected),
        "markov_bias_binary32_codes": _tensor3(
            expected.markov_bias_binary32_codes
        ),
        "markov_embeddings_bf16_codes": _tensor3(
            expected.markov_embeddings_bf16_codes
        ),
        "model_id": MODEL_ID,
        "output_global_token_ids": expected_global,
        "output_local_token_ids": [list(row) for row in expected.output_token_ids],
        "program_sha256": PROGRAM_SHA256,
        "request_sha256": request_sha256,
        "resource_payload_sha256": dict(resource_hashes),
        "sampling": expected_sampling,
        "schema": RESULT_SCHEMA,
        "selected_global_token_ids": list(selected),
        "source_application_id": manifest["source_application_id"],
        "status": "artifact_authenticated_selected_vocabulary_markov_execution",
    }
    for name, expected_value in comparisons.items():
        if result[name] != expected_value:
            raise DeepSeekV4MarkovExecutionCheckError(
                f"execution result {name} differs from independent reference"
            )
    if observed_result_id != expected_result_id:
        raise DeepSeekV4MarkovExecutionCheckError("execution result_id differs")
    return observed_result_id, len(comparisons)


def verify_deepseek_v4_markov_executable_execution(
    *,
    deployment_root: Path,
    application_root: Path,
    request: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare one artifact result with independent canonical/reference replay."""

    deployment_root = Path(deployment_root).resolve()
    application_root = Path(application_root).resolve()
    manifest, roles, manifest_sha = _verify_manifest(deployment_root)
    current_roundtrip = verify_deepseek_v4_markov_executable_roundtrip(
        deployment_root, application_root
    )
    retained_roundtrip = _load(
        deployment_root / "roundtrip_report.json", "retained roundtrip report"
    )
    if current_roundtrip != retained_roundtrip:
        raise DeepSeekV4MarkovExecutionCheckError(
            "retained roundtrip differs from current independent reconstruction"
        )
    resource_role = roles.get("resource_manifest")
    if resource_role is None:
        raise DeepSeekV4MarkovExecutionCheckError(
            "resource manifest artifact is absent"
        )
    resources = _load(
        _safe_file(
            deployment_root,
            resource_role["path"],
            "resource manifest artifact path",
        ),
        "resource manifest",
    )
    selected, w1, w2, resource_hashes = _resource_shards(
        deployment_root, resources, roles
    )
    if selected != tuple(manifest["selected_global_token_ids"]):
        raise DeepSeekV4MarkovExecutionCheckError(
            "resource and deployment selected vocabularies differ"
        )
    local_inputs, request_sha = _local_inputs(
        request, selected=selected, build_id=manifest["build_id"]
    )
    try:
        expected = markov_autoregressive_loop_bf16(
            request["base_logits_binary32_codes"],
            local_inputs,
            w1,
            w2,
            temperature_binary32=request["temperature_binary32"],
            entropy=_entropy(request["entropy"]),
            tensor_parallel_world_size=len(w1),
            require_pytorch_cuda_equivalence=request[
                "require_pytorch_cuda_equivalence"
            ],
        )
    except (MarkovLoopReferenceError, SamplingReferenceError) as exc:
        raise DeepSeekV4MarkovExecutionCheckError(
            f"independent Markov reference poisoned: {exc}"
        ) from exc
    result_id, comparison_count = _compare_result(
        result,
        manifest=manifest,
        manifest_sha256=manifest_sha,
        request=request,
        request_sha256=request_sha,
        selected=selected,
        resource_hashes=resource_hashes,
        expected=expected,
    )
    body: dict[str, Any] = {
        "application_id": manifest["source_application_id"],
        "build_id": manifest["build_id"],
        "comparison_count": comparison_count,
        "model_id": MODEL_ID,
        "program_sha256": PROGRAM_SHA256,
        "request_sha256": request_sha,
        "result_id": result_id,
        "roundtrip_id": current_roundtrip["roundtrip_id"],
        "schema": DIFFERENTIAL_SCHEMA,
        "selected_global_token_ids": list(selected),
        "status": "exact_artifact_service_reference_match",
    }
    body["differential_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return body


__all__ = [
    "DIFFERENTIAL_SCHEMA",
    "DeepSeekV4MarkovExecutionCheckError",
    "verify_deepseek_v4_markov_executable_execution",
]
