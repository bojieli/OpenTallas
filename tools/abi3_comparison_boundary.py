#!/usr/bin/env python3
"""Authoritative, source-revalidated ABI 3.0 comparison boundaries.

The checked-in comparison contract is the pair identity.  It fixes the common
model/workload/execution/scientific policy and the exact target slots: either
the ROM and HBM slots of a storage-class comparison or the two ROM slots
(``rom`` and ``rom_array``) of a packaging comparison.  A target boundary then
binds one slot's deployment, capability, cost table and request.  The ordinary cycle CLI can produce only a
``measurement_slice``; full-workload evidence requires a runner that consumes
and proves the complete governed workload.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from compiler.ir.v3.kernel_ir import IRError, KernelGraph
from runtime.abi3.capability import Capability, canonical_json
from runtime.abi3.constants import Permission, StorageClass, TopologyClass
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import ExtendedDescriptorType, Phase, Symbol
from runtime.driver import DriverError, GenerationDriver
from runtime.cycle.machine import CostTable

REPO = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.abi3.comparison_boundary.v1"
CONTRACT_SCHEMA = "opentallas.abi3.comparison_contract.v1"
BOUNDARY_SCHEMA_PATH = REPO / "schemas/abi3/comparison_boundary_v1.schema.json"
CONTRACT_SCHEMA_PATH = REPO / "schemas/abi3/comparison_contract_v1.schema.json"
CONTRACT_PATHS = {
    "qwen3_rom_single_chip_vs_hbm_single_chip": (
        "configs/abi3/comparison_contracts/"
        "qwen3_rom_single_chip_vs_hbm_single_chip_v1.json"
    ),
    "deepseek_v4_rom_wafer_vs_hbm_cluster_32": (
        "configs/abi3/comparison_contracts/"
        "deepseek_v4_rom_wafer_vs_hbm_cluster_32_v1.json"
    ),
    "deepseek_v4_rom_wafer_vs_rom_array_32": (
        "configs/abi3/comparison_contracts/"
        "deepseek_v4_rom_wafer_vs_rom_array_32_v1.json"
    ),
}
ORACLE_PRODUCER_PATHS = {
    "qwen3_rom_single_chip_vs_hbm_single_chip": (
        "tools/run_qwen3_reference_oracle.py"
    ),
    "deepseek_v4_rom_wafer_vs_hbm_cluster_32": (
        "tools/run_deepseek_v4_reference_oracle.py"
    ),
    "deepseek_v4_rom_wafer_vs_rom_array_32": (
        "tools/run_deepseek_v4_reference_oracle.py"
    ),
}
# The storage class each target role must declare, and the two pair shapes a
# contract's ``targets`` object may take (comparison_contract_v1 ``targets``):
# the ROM/HBM storage-class pair or the ROM/ROM packaging pair.  ``rom_array``
# is a ROM role in every check below; only its slot name differs.
TARGET_ROLE_STORAGE = {"rom": "ROM", "hbm": "HBM", "rom_array": "ROM"}
TARGET_ROLE_PAIRS = (("rom", "hbm"), ("rom", "rom_array"))
REQUEST_TRAJECTORY_SCHEMA = "opentallas.abi3.request_trajectory.v1"
REQUEST_TRAJECTORY_SEMANTIC_SCHEMA = (
    "opentallas.abi3.request_trajectory_semantics.v1"
)
REQUEST_SEMANTIC_SYMBOLS = (
    "SPAN_TOKENS",
    "POSITION_START",
    "POSITION_END",
    "CONTEXT_LENGTH",
    "PHASE",
    "MAX_NEW_TOKENS",
    "BATCH",
    "GENERATION_INDEX",
    "SPAN_LAST_INDEX",
)
_SHA256_LENGTH = 64


class BoundaryError(ValueError):
    """A comparison contract or boundary is malformed or source-inconsistent."""


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_json_loads(payload: str | bytes, *, source: object) -> Any:
    """Parse governed JSON without duplicate-key or non-finite ambiguity."""

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        body: dict[str, Any] = {}
        for key, value in pairs:
            if key in body:
                raise BoundaryError(f"duplicate JSON key {key!r} in {source}")
            body[key] = value
        return body

    def reject_constant(value: str) -> None:
        raise BoundaryError(f"non-finite JSON number {value!r} in {source}")

    try:
        return json.loads(
            payload,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise BoundaryError(f"malformed JSON in {source}: {exc}") from exc


def _strict_json_file(path: Path) -> Any:
    return _strict_json_loads(path.read_bytes(), source=path)


def _read_deployment_strict(root: Path) -> Deployment:
    manifest_path = root / "deployment.json"
    manifest = _strict_json_file(manifest_path)
    if not isinstance(manifest, Mapping):
        raise BoundaryError(f"deployment manifest {manifest_path} is not an object")
    return Deployment.read(root)


def _shown(repo: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _source_path(repo: Path, recorded: object) -> Path:
    """Resolve one canonical repo-relative source path, or refuse it.

    A digest does not make an arbitrary path part of the repository's governed
    source boundary.  In particular, an absolute path or a symlink/``..`` alias
    could otherwise make the same contract mean different bytes on two hosts.
    """

    if not isinstance(recorded, str) or not recorded or "\\" in recorded:
        raise BoundaryError("source path must be a nonempty canonical repo-relative path")
    relative = Path(recorded)
    if (
        relative.is_absolute()
        or relative.as_posix() != recorded
        or "." in relative.parts
        or ".." in relative.parts
    ):
        raise BoundaryError("source path must be canonical and repo-relative")
    root = repo.resolve()
    resolved = (root / relative).resolve()
    try:
        canonical = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise BoundaryError("source path escapes the repository") from exc
    if canonical != recorded:
        raise BoundaryError("source path is an alias rather than its canonical spelling")
    return resolved


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA256_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def contract_target_roles(targets: object) -> tuple[str, str]:
    """Return the ordered role pair a contract's ``targets`` object declares.

    A key set that is neither registered pair falls back to the ROM/HBM pair
    so that every per-role check still reports a named failure (and the
    schema check reports the malformed shape) instead of raising.
    """

    keys = set(_mapping(targets))
    for pair in TARGET_ROLE_PAIRS:
        if keys == set(pair):
            return pair
    return TARGET_ROLE_PAIRS[0]


def _schema_errors(body: object, path: Path) -> list[str]:
    try:
        schema = _strict_json_file(path)
        Draft202012Validator.check_schema(schema)
        return sorted(
            error.message for error in Draft202012Validator(schema).iter_errors(body)
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return [f"cannot validate against {path}: {exc}"]


def legacy_workload_digest(body: Mapping[str, Any]) -> str:
    """Recompute the historical producer digest after validating token count.

    The legacy payload intentionally remains byte-compatible with the workload
    producers.  It is not the complete comparison identity; governed consumers
    must use :func:`comparison_workload_digest` or the full contract digest.
    """

    required = (
        "workload_id",
        "kind",
        "token_ids",
        "prompt_token_count",
        "max_new_tokens",
    )
    missing = [name for name in required if name not in body]
    if missing:
        raise BoundaryError(f"workload is missing identity fields: {missing}")
    token_ids = body["token_ids"]
    if not isinstance(token_ids, list) or any(
        not isinstance(token, int) or isinstance(token, bool) for token in token_ids
    ):
        raise BoundaryError("workload token_ids must be a list of integers")
    prompt_count = body["prompt_token_count"]
    if (
        not isinstance(prompt_count, int)
        or isinstance(prompt_count, bool)
        or prompt_count < 1
        or prompt_count != len(token_ids)
    ):
        raise BoundaryError(
            "workload prompt_token_count must equal its positive token_ids length"
        )
    max_new_tokens = body["max_new_tokens"]
    if (
        not isinstance(max_new_tokens, int)
        or isinstance(max_new_tokens, bool)
        or max_new_tokens < 1
    ):
        raise BoundaryError("workload max_new_tokens must be a positive integer")
    # Preserve the workload producers' established digest payload.  Prompt count
    # is independently checked against len(token_ids), so it cannot drift even
    # though the historical digest format did not duplicate that derivable value.
    payload = {
        "workload_id": body["workload_id"],
        "kind": body["kind"],
        "token_ids": token_ids,
        "max_new_tokens": max_new_tokens,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def comparison_workload_digest(contract: Mapping[str, Any]) -> str:
    """Digest every workload and execution field relevant to comparison."""

    return _digest(
        {
            "schema": "opentallas.abi3.comparison_workload_identity.v1",
            "workload": dict(_mapping(contract.get("workload"))),
            "execution": dict(_mapping(contract.get("execution"))),
        }
    )


def request_trajectory_payload(
    transactions: Sequence[Mapping[str, Any]] | object,
) -> dict[str, Any]:
    """Return the target-neutral semantics shared by both comparison sides.

    Entrypoint and generation-policy descriptor IDs are deployment-local.  The
    governed phase and dynamic symbols are not, so only the latter participate
    in the pair digest.  Admission separately proves every local ID against the
    reopened deployment before this digest is accepted.
    """

    rows = transactions if isinstance(transactions, Sequence) and not isinstance(
        transactions, (str, bytes, bytearray)
    ) else ()
    semantic: list[dict[str, Any]] = []
    for raw in rows:
        row = _mapping(raw)
        request = _mapping(row.get("request"))
        symbols = _mapping(request.get("symbols"))
        semantic.append(
            {
                "transaction_id": row.get("transaction_id"),
                "phase": row.get("phase"),
                "symbols": {
                    name: symbols.get(name) for name in REQUEST_SEMANTIC_SYMBOLS
                },
            }
        )
    return {
        "schema": REQUEST_TRAJECTORY_SEMANTIC_SCHEMA,
        "transactions": semantic,
    }


def request_trajectory_digest(
    transactions: Sequence[Mapping[str, Any]] | object,
) -> str:
    return _digest(request_trajectory_payload(transactions))


def validate_governed_request(
    request: Mapping[str, Any] | object,
    contract: Mapping[str, Any] | object,
    deployment: Deployment | None,
) -> dict[str, bool]:
    """Re-derive one measurement request from contract and deployment sources.

    The deployment-local symbol values and descriptor IDs are deliberately not
    part of the target-neutral trajectory digest.  They are nevertheless part
    of the exact request and must be validated before that digest can be used
    to pair two targets.
    """

    body = _mapping(request)
    execution = _mapping(_mapping(contract).get("execution"))
    workload = _mapping(_mapping(contract).get("workload"))
    generation = _mapping(execution.get("generation"))
    symbols = _mapping(body.get("symbols"))
    prompt_count = workload.get("prompt_token_count")
    max_new_tokens = generation.get("max_new_tokens")
    batch = execution.get("batch")
    phase = symbols.get("PHASE")
    generation_index = symbols.get("GENERATION_INDEX")

    counts_strict = (
        type(prompt_count) is int
        and prompt_count > 0
        and type(max_new_tokens) is int
        and max_new_tokens > 0
        and type(batch) is int
        and batch > 0
    )
    phase_and_index_strict = (
        type(phase) is int
        and phase in {int(Phase.PREFILL), int(Phase.DECODE)}
        and type(generation_index) is int
        and generation_index >= 0
        and (
            (phase == int(Phase.PREFILL) and generation_index == 0)
            or (
                phase == int(Phase.DECODE)
                and type(max_new_tokens) is int
                and 1 <= generation_index < max_new_tokens
            )
        )
    )

    deployment_symbols: dict[str, int] = {}
    deployment_symbols_valid = isinstance(deployment, Deployment)
    if isinstance(deployment, Deployment):
        try:
            _topology, node_count = topology_identity(deployment)
            driver = GenerationDriver(
                SimpleNamespace(deployment=deployment, node_count=node_count)
            )
            deployment_symbols = {
                Symbol(symbol_id).name: value
                for symbol_id, value in driver.deployment_symbols.items()
            }
            deployment_symbols_valid = (
                set(deployment_symbols)
                == {
                    "NODE_ID",
                    "NODE_COUNT",
                    "ACTIVE_EXPERT_COUNT",
                    "SPARSE_INDEX_COUNT",
                    "LAYER_COUNT",
                    "VOCABULARY_PARTITIONS",
                }
                and all(type(value) is int and value >= 0 for value in deployment_symbols.values())
            )
        except (DriverError, KeyError, TypeError, ValueError):
            deployment_symbols_valid = False

    dynamic_symbols: dict[str, Any] = {}
    if counts_strict and phase_and_index_strict:
        if phase == int(Phase.PREFILL):
            span = prompt_count
            position_start = 0
            span_last_index = prompt_count - 1
        else:
            span = 1
            position_start = prompt_count + generation_index - 1
            span_last_index = 0
        dynamic_symbols = {
            "SPAN_TOKENS": span,
            "POSITION_START": position_start,
            "POSITION_END": position_start + span,
            "CONTEXT_LENGTH": position_start + span,
            "PHASE": phase,
            "MAX_NEW_TOKENS": max_new_tokens,
            "BATCH": batch,
            "GENERATION_INDEX": generation_index,
            "SPAN_LAST_INDEX": span_last_index,
        }
    expected_symbols = {**deployment_symbols, **dynamic_symbols}

    matching_entrypoints: list[Mapping[str, Any]] = []
    if isinstance(deployment, Deployment) and type(body.get("entrypoint_id")) is int:
        matching_entrypoints = [
            entry
            for entry in deployment.entrypoints
            if type(entry.get("entrypoint_id")) is int
            and entry.get("entrypoint_id") == body.get("entrypoint_id")
            and type(entry.get("phase")) is int
            and entry.get("phase") == phase
        ]

    return {
        "shape_exact": set(body)
        == {
            "entrypoint_id",
            "generation_policy_id",
            "transactions",
            "label",
            "symbols",
        },
        "scalar_types_strict": (
            type(body.get("entrypoint_id")) is int
            and body.get("entrypoint_id") >= 0
            and type(body.get("generation_policy_id")) is int
            and body.get("generation_policy_id") >= 0
            and type(body.get("transactions")) is int
            and body.get("transactions") == 1
            and body.get("label") == ""
        ),
        "contract_counts_strict": counts_strict,
        "phase_and_generation_index_exact": phase_and_index_strict,
        "entrypoint_exact": len(matching_entrypoints) == 1,
        "generation_policy_exact": (
            len(matching_entrypoints) == 1
            and type(matching_entrypoints[0].get("generation_policy_id")) is int
            and matching_entrypoints[0].get("generation_policy_id") != 0xFFFFFFFF
            and body.get("generation_policy_id")
            == matching_entrypoints[0].get("generation_policy_id")
        ),
        "deployment_symbols_exact": deployment_symbols_valid
        and all(symbols.get(name) == value for name, value in deployment_symbols.items()),
        "dynamic_symbols_exact": bool(dynamic_symbols)
        and all(symbols.get(name) == value for name, value in dynamic_symbols.items()),
        "symbol_set_exact": bool(expected_symbols)
        and set(symbols) == set(expected_symbols)
        and all(type(value) is int and value >= 0 for value in symbols.values()),
    }


def topology_identity(deployment: Deployment) -> tuple[int, int]:
    """Return the manifest topology and descriptor's exact node count."""

    ids = deployment.table.ids_of_type(ExtendedDescriptorType.TOPOLOGY)
    if len(ids) != 1:
        raise BoundaryError(
            "comparison deployment must carry exactly one TOPOLOGY descriptor; "
            f"found {len(ids)}"
        )
    payload = deployment.table[ids[0]].payload
    try:
        raw_topology = payload["topology_class"]
        raw_node_count = payload["node_count"]
        if type(raw_topology) is not int or type(raw_node_count) is not int:
            raise TypeError("TOPOLOGY values are not exact integers")
        topology = int(TopologyClass(raw_topology))
        node_count = raw_node_count
    except (KeyError, TypeError, ValueError) as exc:
        raise BoundaryError("TOPOLOGY has no valid class and node count") from exc
    if topology != int(deployment.topology_class):
        raise BoundaryError("TOPOLOGY class disagrees with deployment class")
    if node_count < 1:
        raise BoundaryError("TOPOLOGY node_count must be positive")
    return topology, node_count


def _immutable_storage_classes(deployment: Deployment) -> set[str]:
    classes: set[str] = set()
    for object_id in deployment.objects:
        descriptor = deployment.table[object_id]
        if not descriptor.permissions & int(Permission.IMMUTABLE):
            continue
        try:
            classes.add(StorageClass(int(descriptor.payload["storage_class"])).name)
        except (KeyError, TypeError, ValueError):
            continue
    return classes


def _policy_identity(contract: Mapping[str, Any], role: str) -> dict[str, Any]:
    policy = _mapping(contract.get("policy"))
    target = _mapping(_mapping(contract.get("targets")).get(role))
    cost_policy = _mapping(target.get("cost_policy"))
    return {
        "schema": "opentallas.abi3.comparison_cost_policy.v1",
        "comparison_id": contract.get("comparison_id"),
        "target_role": role,
        "policy_id": cost_policy.get("policy_id"),
        "technology_view": policy.get("technology_view"),
        "pvt": policy.get("pvt"),
        "clock": policy.get("clock"),
        "evidence_class": policy.get("evidence_class"),
        "latency_boundary": policy.get("latency_boundary"),
        "state_boundary": policy.get("state_boundary"),
        "external_memory_policy": policy.get("external_memory_policy"),
        "external_fabric_policy": policy.get("external_fabric_policy"),
    }


def comparison_payload(boundary: Mapping[str, Any]) -> dict[str, Any]:
    """Return the shared pair identity, which is solely the contract lock."""

    contract = _mapping(boundary.get("comparison_contract"))
    return {
        "schema": "opentallas.abi3.comparison_scope.v2",
        "comparison_id": boundary.get("comparison_id"),
        "contract_sha256": contract.get("sha256"),
    }


def boundary_digest(boundary: Mapping[str, Any]) -> str:
    payload = dict(boundary)
    payload.pop("boundary_sha256", None)
    return _digest(payload)


def validate_comparison_contract(
    contract: Mapping[str, Any] | object,
    *,
    repo: Path = REPO,
    source_path: Path | None = None,
) -> dict[str, Any]:
    """Validate schema, shared sources, policies, and target source locks."""

    body = _mapping(contract)
    model = _mapping(body.get("model"))
    workload = _mapping(body.get("workload"))
    execution = _mapping(body.get("execution"))
    generation = _mapping(execution.get("generation"))
    targets = _mapping(body.get("targets"))
    roles = contract_target_roles(targets)
    schema_errors = _schema_errors(body, CONTRACT_SCHEMA_PATH)
    shared: dict[str, bool] = {
        "schema_valid": not schema_errors,
        "registered_path_exact": (
            source_path is not None
            and body.get("comparison_id") in CONTRACT_PATHS
            and _shown(repo, source_path)
            == CONTRACT_PATHS.get(str(body.get("comparison_id")))
        ),
        "contract_integer_fields_strict": (
            type(execution.get("batch")) is int
            and execution.get("batch", 0) > 0
            and type(execution.get("concurrency")) is int
            and execution.get("concurrency", 0) > 0
            and type(execution.get("context_tokens")) is int
            and execution.get("context_tokens", 0) > 0
            and type(generation.get("max_new_tokens")) is int
            and generation.get("max_new_tokens", 0) > 0
            and type(generation.get("vocabulary_size")) is int
            and generation.get("vocabulary_size", 0) > 0
            and isinstance(generation.get("eos_token_ids"), list)
            and bool(generation.get("eos_token_ids"))
            and all(type(token) is int and token >= 0 for token in generation.get("eos_token_ids", []))
            and type(workload.get("prompt_token_count")) is int
            and workload.get("prompt_token_count", 0) > 0
            and type(workload.get("max_new_tokens")) is int
            and workload.get("max_new_tokens", 0) > 0
            and all(
                type(_mapping(targets.get(role)).get("topology_class")) is int
                and 0 <= _mapping(targets.get(role)).get("topology_class", -1) <= 2
                and type(_mapping(targets.get(role)).get("node_count")) is int
                and _mapping(targets.get(role)).get("node_count", 0) > 0
                for role in roles
            )
        ),
    }

    graph: KernelGraph | None = None
    try:
        graph_path = _source_path(repo, model.get("kernel_ir_path"))
        graph_source = _strict_json_file(graph_path)
        if not isinstance(graph_source, Mapping):
            raise BoundaryError("Kernel IR source is not an object")
        graph = KernelGraph.from_dict(graph_source)
        shared.update(
            kernel_ir_source_sha256_exact=(
                _file_sha256(graph_path) == model.get("kernel_ir_source_sha256")
            ),
            graph_id_source_exact=graph.graph_id == model.get("graph_id"),
            model_id_source_exact=graph.model_id == model.get("model_id"),
            numeric_profile_source_exact=(
                graph.numeric_profile == model.get("numeric_profile")
            ),
        )
    except (IRError, OSError, TypeError, ValueError, json.JSONDecodeError):
        shared.update(
            kernel_ir_source_sha256_exact=False,
            graph_id_source_exact=False,
            model_id_source_exact=False,
            numeric_profile_source_exact=False,
        )

    workload_source: Mapping[str, Any] = {}
    try:
        workload_path = _source_path(repo, workload.get("path"))
        payload = workload_path.read_bytes()
        parsed = _strict_json_loads(payload, source=workload_path)
        if not isinstance(parsed, Mapping):
            raise BoundaryError("workload source is not an object")
        workload_source = parsed
        computed = legacy_workload_digest(workload_source)
        rendered = workload_source.get("rendered_text")
        if not isinstance(rendered, str):
            raise BoundaryError("workload rendered_text is not a string")
        rendered_digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        shared.update(
            workload_source_sha256_exact=(
                hashlib.sha256(payload).hexdigest() == workload.get("source_sha256")
            ),
            workload_digest_self_consistent=(
                workload_source.get("digest") == computed
            ),
            workload_digest_source_exact=computed == workload.get("digest"),
            workload_id_source_exact=(
                workload_source.get("workload_id") == workload.get("workload_id")
            ),
            workload_kind_source_exact=(
                workload_source.get("kind") == workload.get("kind")
            ),
            prompt_token_count_source_exact=(
                workload_source.get("prompt_token_count")
                == workload.get("prompt_token_count")
            ),
            max_new_tokens_source_exact=(
                workload_source.get("max_new_tokens")
                == workload.get("max_new_tokens")
            ),
            rendered_text_digest_self_consistent=(
                workload_source.get("rendered_text_sha256") == rendered_digest
            ),
            rendered_text_source_exact=(
                rendered_digest == workload.get("rendered_text_sha256")
            ),
        )
    except (BoundaryError, OSError, TypeError, ValueError, json.JSONDecodeError):
        shared.update(
            workload_source_sha256_exact=False,
            workload_digest_self_consistent=False,
            workload_digest_source_exact=False,
            workload_id_source_exact=False,
            workload_kind_source_exact=False,
            prompt_token_count_source_exact=False,
            max_new_tokens_source_exact=False,
            rendered_text_digest_self_consistent=False,
            rendered_text_source_exact=False,
        )

    try:
        index_path = _source_path(repo, workload.get("index_path"))
        payload = index_path.read_bytes()
        index = _strict_json_loads(payload, source=index_path)
        if not isinstance(index, Mapping):
            raise BoundaryError("workload index source is not an object")
        entry = _mapping(_mapping(index.get("workloads")).get(workload.get("workload_id")))
        shared.update(
            workload_index_source_sha256_exact=(
                hashlib.sha256(payload).hexdigest()
                == workload.get("index_source_sha256")
            ),
            workload_index_schema_exact=index.get("schema") == workload.get("index_schema"),
            workload_index_model_exact=index.get("model_id") == model.get("model_id"),
            tokenizer_identity_exact=(
                index.get("tokenizer_sha256") == workload.get("tokenizer_sha256")
            ),
            workload_index_entry_exact=(
                entry.get("digest") == workload.get("digest")
                and entry.get("kind") == workload.get("kind")
                and type(entry.get("prompt_token_count")) is int
                and entry.get("prompt_token_count")
                == workload.get("prompt_token_count")
                and type(entry.get("max_new_tokens")) is int
                and entry.get("max_new_tokens") == workload.get("max_new_tokens")
                and entry.get("path")
                == Path(str(workload.get("path"))).name
            ),
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        shared.update(
            workload_index_source_sha256_exact=False,
            workload_index_schema_exact=False,
            workload_index_model_exact=False,
            tokenizer_identity_exact=False,
            workload_index_entry_exact=False,
        )

    template = _mapping(workload.get("template"))
    if template.get("mode") == "none_plain_text":
        shared["template_identity_exact"] = (
            template.get("template_id") == "none_plain_text"
            and template.get("path") is None
            and template.get("source_sha256") is None
        )
    else:
        try:
            template_path = _source_path(repo, template.get("path"))
            shared["template_identity_exact"] = (
                _file_sha256(template_path) == template.get("source_sha256")
            )
        except (OSError, TypeError, ValueError):
            shared["template_identity_exact"] = False

    graph_generation = _mapping(graph.generation_policy) if graph is not None else {}
    graph_generation_limit = graph_generation.get("maximum_new_tokens")
    contract_generation_limit = generation.get("max_new_tokens")
    shared.update(
        execution_context_exact=(
            execution.get("context_tokens") == workload.get("prompt_token_count")
        ),
        execution_generation_bound_exact=(
            generation.get("max_new_tokens") == workload.get("max_new_tokens")
        ),
        graph_generation_semantics_exact=(
            graph_generation.get("selection_mode") == generation.get("selection_mode")
            and graph_generation.get("tie_rule") == generation.get("tie_rule")
            and graph_generation.get("eos_token_ids") == generation.get("eos_token_ids")
            and graph_generation.get("include_eos_in_output")
            == generation.get("include_eos_in_output")
            and graph_generation.get("stop_condition")
            == generation.get("stop_condition")
            and graph_generation.get("vocabulary_size")
            == generation.get("vocabulary_size")
            and isinstance(graph_generation_limit, int)
            and not isinstance(graph_generation_limit, bool)
            and isinstance(contract_generation_limit, int)
            and not isinstance(contract_generation_limit, bool)
            and graph_generation_limit >= contract_generation_limit
        ),
    )

    oracle_lock = _mapping(body.get("external_oracle"))
    oracle_producer = _mapping(oracle_lock.get("producer"))
    oracle_status = oracle_lock.get("status")
    expected_oracle_tool = ORACLE_PRODUCER_PATHS.get(
        str(body.get("comparison_id"))
    )
    pending_oracle = (
        oracle_status == "pending"
        and oracle_lock.get("source_sha256") is None
        and oracle_producer.get("source_sha256") is None
    )
    locked_oracle = (
        oracle_status == "locked"
        and _is_sha256(oracle_lock.get("source_sha256"))
        and _is_sha256(oracle_producer.get("source_sha256"))
    )
    try:
        _source_path(repo, oracle_lock.get("path"))
        _source_path(repo, oracle_producer.get("tool"))
        oracle_paths_canonical = True
    except (BoundaryError, OSError, TypeError, ValueError):
        oracle_paths_canonical = False
    shared["external_oracle_contract_well_formed"] = (
        (pending_oracle or locked_oracle)
        and oracle_paths_canonical
        and oracle_lock.get("schema")
        == "opentallas.abi3.reference_oracle.v1"
        and oracle_lock.get("evidence_class")
        == "external_reference_comparator"
        and oracle_producer.get("tool") == expected_oracle_tool
    )

    oracle_source_exact = False
    oracle_producer_exact = False
    oracle_identity_exact = False
    oracle_terminal_exact = False
    if locked_oracle:
        try:
            oracle_path = _source_path(repo, oracle_lock.get("path")).resolve()
            oracle_path.relative_to(repo.resolve())
            oracle_payload = oracle_path.read_bytes()
            oracle = _strict_json_loads(oracle_payload, source=oracle_path)
            if not isinstance(oracle, Mapping):
                raise BoundaryError("external oracle source is not an object")
            producer_path = _source_path(repo, expected_oracle_tool).resolve()
            producer_path.relative_to(repo.resolve())
            oracle_result = _mapping(
                _mapping(oracle.get("results")).get(workload.get("workload_id"))
            )
            generated = oracle_result.get("generated_token_ids")
            vocabulary_size = generation.get("vocabulary_size")
            cap = generation.get("max_new_tokens")
            generated_valid = (
                isinstance(generated, list)
                and bool(generated)
                and type(vocabulary_size) is int
                and type(cap) is int
                and 0 < len(generated) <= cap
                and all(
                    type(token) is int
                    and 0 <= token < vocabulary_size
                    for token in generated
                )
            )
            eos_ids = generation.get("eos_token_ids")
            eos = set(eos_ids) if isinstance(eos_ids, list) else set()
            stop_reason = oracle_result.get("stop_reason")
            eos_terminal = (
                generated_valid
                and stop_reason == "eos"
                and generated[-1] in eos
                and not any(token in eos for token in generated[:-1])
            )
            cap_terminal = (
                generated_valid
                and stop_reason == "max_new_tokens"
                and isinstance(cap, int)
                and not isinstance(cap, bool)
                and len(generated) == cap
                and not any(token in eos for token in generated)
            )
            oracle_source_exact = (
                _shown(repo, oracle_path) == oracle_lock.get("path")
                and hashlib.sha256(oracle_payload).hexdigest()
                == oracle_lock.get("source_sha256")
            )
            oracle_producer_exact = (
                _shown(repo, producer_path) == expected_oracle_tool
                and _file_sha256(producer_path)
                == oracle_producer.get("source_sha256")
            )
            oracle_identity_exact = (
                generated_valid
                and oracle.get("schema") == oracle_lock.get("schema")
                and oracle.get("evidence_class")
                == oracle_lock.get("evidence_class")
                and oracle.get("model_id") == model.get("model_id")
                and oracle.get("tokenizer_sha256")
                == workload.get("tokenizer_sha256")
                and oracle_result.get("workload_digest")
                == workload.get("digest")
                and type(oracle_result.get("prompt_token_count")) is int
                and oracle_result.get("prompt_token_count")
                == workload.get("prompt_token_count")
                and type(oracle_result.get("generated_token_count")) is int
                and oracle_result.get("generated_token_count")
                == len(generated)
            )
            oracle_terminal_exact = eos_terminal or cap_terminal
        except (
            BoundaryError,
            OSError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            pass
    shared.update(
        external_oracle_source_exact_if_locked=(
            pending_oracle or oracle_source_exact
        ),
        external_oracle_producer_exact_if_locked=(
            pending_oracle or oracle_producer_exact
        ),
        external_oracle_identity_exact_if_locked=(
            pending_oracle or oracle_identity_exact
        ),
        external_oracle_terminal_exact_if_locked=(
            pending_oracle or oracle_terminal_exact
        ),
    )
    oracle_ready = (
        locked_oracle
        and shared["external_oracle_contract_well_formed"]
        and oracle_source_exact
        and oracle_producer_exact
        and oracle_identity_exact
        and oracle_terminal_exact
    )
    oracle_checks = {"external_oracle_locked": oracle_ready}

    target_checks: dict[str, bool] = {}
    target_ready: dict[str, bool] = {}
    for role in roles:
        target = _mapping(targets.get(role))
        expected_storage = TARGET_ROLE_STORAGE[role]
        try:
            _source_path(repo, _mapping(target.get("deployment")).get("path"))
            _source_path(repo, _mapping(target.get("capability")).get("path"))
            _source_path(
                repo,
                _mapping(_mapping(target.get("cost_policy")).get("lock")).get(
                    "path"
                ),
            )
            target_paths_canonical = True
        except (BoundaryError, OSError, TypeError, ValueError):
            target_paths_canonical = False
        target_identity_well_formed = (
            target.get("role") == role
            and target.get("storage_class") == expected_storage
            and type(target.get("topology_class")) is int
            and 0 <= target.get("topology_class", -1) <= 2
            and type(target.get("node_count")) is int
            and target.get("node_count", 0) > 0
            and target_paths_canonical
        )
        shared[f"target_{role}_identity_well_formed"] = target_identity_well_formed
        target_checks[f"target_{role}_identity_well_formed"] = (
            target_identity_well_formed
        )
        locks_ready = True
        for label in ("deployment", "capability"):
            lock = _mapping(target.get(label))
            locked = (
                lock.get("status") == "locked"
                and _is_sha256(lock.get("digest"))
                and _is_sha256(lock.get("source_sha256"))
            )
            target_checks[f"target_{role}_{label}_locked"] = locked
            locks_ready = locks_ready and locked
        cost_policy = _mapping(target.get("cost_policy"))
        cost_lock = _mapping(cost_policy.get("lock"))
        cost_locked = (
            cost_lock.get("status") == "locked"
            and _is_sha256(cost_lock.get("digest"))
            and _is_sha256(cost_lock.get("source_sha256"))
        )
        target_checks[f"target_{role}_cost_policy_locked"] = cost_locked
        locks_ready = locks_ready and cost_locked
        clock = _mapping(_mapping(body.get("policy")).get("clock"))
        frequency_ready = (
            isinstance(clock.get("comparison_frequency_hz"), int)
            and not isinstance(clock.get("comparison_frequency_hz"), bool)
            and clock.get("comparison_frequency_hz", 0) > 0
        )
        target_checks[f"target_{role}_clock_locked"] = frequency_ready
        locks_ready = locks_ready and frequency_ready

        if locks_ready:
            try:
                deployment_lock = _mapping(target.get("deployment"))
                deployment_root = _source_path(repo, deployment_lock.get("path"))
                deployment = _read_deployment_strict(deployment_root)
                topology, nodes = topology_identity(deployment)
                storage = _immutable_storage_classes(deployment)
                capability_lock = _mapping(target.get("capability"))
                capability_path = _source_path(repo, capability_lock.get("path"))
                capability_payload = capability_path.read_bytes()
                capability_body = _strict_json_loads(
                    capability_payload, source=capability_path
                )
                if not isinstance(capability_body, Mapping):
                    raise BoundaryError("capability source is not an object")
                capability = Capability.from_dict(capability_body)
                cost_path = _source_path(repo, cost_lock.get("path"))
                cost_payload = cost_path.read_bytes()
                cost_body = _strict_json_loads(cost_payload, source=cost_path)
                if not isinstance(cost_body, Mapping):
                    raise BoundaryError("cost-table source is not an object")
                cost = CostTable.from_dict(cost_body, path=cost_path)
                clock_entry = _mapping(_mapping(cost_body.get("parameters")).get("clock.frequency_hz"))
                clock_value = clock_entry.get("value")
                target_checks.update(
                    {
                        f"target_{role}_deployment_source_exact": (
                            deployment.deployment_digest.hex()
                            == deployment_lock.get("digest")
                            and _file_sha256(deployment_root / "deployment.json")
                            == deployment_lock.get("source_sha256")
                            and deployment.backend == target.get("backend")
                            and deployment.target_id == target.get("target_id")
                            and deployment.model_id == model.get("model_id")
                            and _mapping(deployment.source_identity).get("graph_id")
                            == model.get("graph_id")
                            and topology == target.get("topology_class")
                            and nodes == target.get("node_count")
                            and expected_storage in storage
                            and ({"ROM", "HBM"} - {expected_storage}).isdisjoint(storage)
                        ),
                        f"target_{role}_capability_source_exact": (
                            hashlib.sha256(capability_payload).hexdigest()
                            == capability_lock.get("source_sha256")
                            and capability.digest == capability_lock.get("digest")
                            and type(capability_body.get("topology_class")) is int
                            and type(
                                _mapping(capability_body.get("limits")).get(
                                    "max_nodes"
                                )
                            )
                            is int
                            and capability.technology_view
                            == _mapping(body.get("policy")).get("technology_view")
                            and int(capability.topology_class)
                            == target.get("topology_class")
                            and capability.limits.get("max_nodes", 0)
                            >= target.get("node_count", 1)
                            and deployment.capability_digest == capability.digest
                        ),
                        f"target_{role}_cost_source_exact": (
                            hashlib.sha256(cost_payload).hexdigest()
                            == cost_lock.get("source_sha256")
                            and cost.digest == cost_lock.get("digest")
                            and cost.cost_table_id == cost_policy.get("cost_table_id")
                            and cost.technology_view
                            == _mapping(body.get("policy")).get("technology_view")
                            and cost_body.get("comparison_policy")
                            == _policy_identity(body, role)
                            and isinstance(clock_value, (int, float))
                            and not isinstance(clock_value, bool)
                            and clock_value == clock.get("comparison_frequency_hz")
                        ),
                    }
                )
            except (
                AttributeError,
                BoundaryError,
                IRError,
                KeyError,
                OSError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                target_checks[f"target_{role}_deployment_source_exact"] = False
                target_checks[f"target_{role}_capability_source_exact"] = False
                target_checks[f"target_{role}_cost_source_exact"] = False
        target_ready[role] = locks_ready and all(
            passed
            for name, passed in target_checks.items()
            if name.startswith(f"target_{role}_")
        )

    first_target, second_target = (_mapping(targets.get(role)) for role in roles)
    shared.update(
        target_ids_distinct=(
            bool(first_target.get("target_id"))
            and bool(second_target.get("target_id"))
            and first_target.get("target_id") != second_target.get("target_id")
        ),
        target_deployments_distinct=(
            bool(_mapping(first_target.get("deployment")).get("path"))
            and bool(_mapping(second_target.get("deployment")).get("path"))
            and _mapping(first_target.get("deployment")).get("path")
            != _mapping(second_target.get("deployment")).get("path")
        ),
    )

    checks = {**shared, **oracle_checks, **target_checks}
    failed = [name for name, passed in checks.items() if not passed]
    shared_failed = [name for name, passed in shared.items() if not passed]
    return {
        "valid": not shared_failed,
        "ready": not failed,
        "external_oracle_source_ready": oracle_ready,
        "target_sources_ready": target_ready,
        "contract_sha256": _digest(body) if body else None,
        "source_sha256": _file_sha256(source_path) if source_path and source_path.is_file() else None,
        "checks": checks,
        "schema_errors": schema_errors,
        "failed_checks": failed,
    }


def load_comparison_contract(
    comparison_id: str,
    *,
    repo: Path = REPO,
    path: Path | None = None,
    require_ready: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    """Load the registered contract, optionally requiring all target locks."""

    registered = CONTRACT_PATHS.get(comparison_id)
    if registered is None:
        raise BoundaryError(f"unknown governed comparison_id {comparison_id!r}")
    source_path = path if path is not None else repo / registered
    try:
        body = _strict_json_file(source_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise BoundaryError(f"cannot read comparison contract {source_path}: {exc}") from exc
    if not isinstance(body, dict) or body.get("comparison_id") != comparison_id:
        raise BoundaryError("comparison contract does not name the requested comparison")
    validation = validate_comparison_contract(body, repo=repo, source_path=source_path)
    if not validation["valid"]:
        raise BoundaryError(
            "comparison contract shared sources are invalid: "
            + ", ".join(validation["failed_checks"])
        )
    if require_ready and not validation["ready"]:
        raise BoundaryError(
            "comparison contract target sources are not locked: "
            + ", ".join(validation["failed_checks"])
        )
    return body, validation, source_path


def _target_role(
    contract: Mapping[str, Any], deployment: Deployment
) -> tuple[str, Mapping[str, Any]]:
    topology, nodes = topology_identity(deployment)
    storage = _immutable_storage_classes(deployment)
    matches: list[tuple[str, Mapping[str, Any]]] = []
    targets = _mapping(contract.get("targets"))
    for role in contract_target_roles(targets):
        target = _mapping(targets.get(role))
        expected_storage = target.get("storage_class")
        if (
            target.get("role") == role
            and deployment.backend == target.get("backend")
            and deployment.target_id == target.get("target_id")
            and topology == target.get("topology_class")
            and nodes == target.get("node_count")
            and expected_storage in storage
            and ({"ROM", "HBM"} - {str(expected_storage)}).isdisjoint(storage)
        ):
            matches.append((role, target))
    if len(matches) != 1:
        raise BoundaryError(
            "deployment does not match exactly one contract-defined target side"
        )
    return matches[0]


def build_boundary(
    *,
    comparison_id: str,
    deployment: Deployment,
    deployment_path: Path,
    capability: Capability,
    capability_path: Path,
    cost_table: CostTable,
    cost_table_path: Path,
    workload_path: Path,
    request: Mapping[str, Any],
    repo: Path = REPO,
    comparison_contract_path: Path | None = None,
    execution_scope: str = "measurement_slice",
) -> dict[str, Any]:
    """Build one target boundary; this runner cannot claim full-workload scope."""

    if execution_scope != "measurement_slice":
        raise BoundaryError(
            "build_boundary only supports measurement_slice; full_workload requires "
            "a runner that proves complete token consumption and terminal generation"
        )
    contract, contract_validation, contract_path = load_comparison_contract(
        comparison_id,
        repo=repo,
        path=comparison_contract_path,
        require_ready=True,
    )
    model = _mapping(contract["model"])
    governed_workload = _mapping(contract["workload"])
    if _shown(repo, workload_path) != governed_workload.get("path"):
        raise BoundaryError("workload path is not the contract-governed source")
    if deployment.model_id != model.get("model_id"):
        raise BoundaryError("deployment model_id disagrees with the contract")
    if _mapping(deployment.source_identity).get("graph_id") != model.get("graph_id"):
        raise BoundaryError("deployment graph_id disagrees with authoritative Kernel IR")
    if deployment.capability_digest != capability.digest:
        raise BoundaryError("deployment capability digest disagrees with capability")
    role, target = _target_role(contract, deployment)
    request_checks = validate_governed_request(request, contract, deployment)
    failed_request_checks = [
        name for name, passed in request_checks.items() if not passed
    ]
    if failed_request_checks:
        raise BoundaryError(
            "governed request is invalid: " + ", ".join(failed_request_checks)
        )

    deployment_lock = _mapping(target.get("deployment"))
    capability_lock = _mapping(target.get("capability"))
    cost_policy = _mapping(target.get("cost_policy"))
    cost_lock = _mapping(cost_policy.get("lock"))
    exact_locks = {
        "deployment path": _shown(repo, deployment_path) == deployment_lock.get("path"),
        "deployment digest": (
            deployment.deployment_digest.hex() == deployment_lock.get("digest")
        ),
        "deployment source": (
            _file_sha256(deployment_path / "deployment.json")
            == deployment_lock.get("source_sha256")
        ),
        "capability path": _shown(repo, capability_path) == capability_lock.get("path"),
        "capability digest": capability.digest == capability_lock.get("digest"),
        "capability source": _file_sha256(capability_path)
        == capability_lock.get("source_sha256"),
        "cost path": _shown(repo, cost_table_path) == cost_lock.get("path"),
        "cost digest": cost_table.digest == cost_lock.get("digest"),
        "cost source": _file_sha256(cost_table_path) == cost_lock.get("source_sha256"),
        "cost id": cost_table.cost_table_id == cost_policy.get("cost_table_id"),
    }
    failed_locks = [name for name, passed in exact_locks.items() if not passed]
    if failed_locks:
        raise BoundaryError("target source lock mismatch: " + ", ".join(failed_locks))

    workload_body = _strict_json_file(workload_path)
    computed_workload_digest = legacy_workload_digest(workload_body)
    if computed_workload_digest != governed_workload.get("digest"):
        raise BoundaryError("workload digest disagrees with comparison contract")
    topology, node_count = topology_identity(deployment)
    cost_source = _strict_json_file(cost_table_path)
    boundary: dict[str, Any] = {
        "schema": SCHEMA,
        "comparison_id": comparison_id,
        "comparison_contract": {
            "path": _shown(repo, contract_path),
            "source_sha256": contract_validation["source_sha256"],
            "sha256": contract_validation["contract_sha256"],
            "schema": CONTRACT_SCHEMA,
        },
        "execution_scope": execution_scope,
        "model_id": model["model_id"],
        "model_digest": model["graph_id"],
        "numeric_profile": model["numeric_profile"],
        "comparison_workload_sha256": comparison_workload_digest(contract),
        "workload": {
            "path": governed_workload["path"],
            "sha256": governed_workload["source_sha256"],
            "workload_id": governed_workload["workload_id"],
            "workload_digest": governed_workload["digest"],
            "kind": governed_workload["kind"],
            "prompt_token_count": governed_workload["prompt_token_count"],
            "max_new_tokens": governed_workload["max_new_tokens"],
            "index_path": governed_workload["index_path"],
            "index_source_sha256": governed_workload["index_source_sha256"],
            "tokenizer_sha256": governed_workload["tokenizer_sha256"],
            "rendered_text_sha256": governed_workload["rendered_text_sha256"],
            "template": governed_workload["template"],
        },
        "target": {
            "role": role,
            "backend": deployment.backend,
            "target_id": deployment.target_id,
            "storage_class": target["storage_class"],
            "topology_class": topology,
            "node_count": node_count,
        },
        "deployment": {
            "path": _shown(repo, deployment_path),
            "sha256": deployment.deployment_digest.hex(),
            "manifest_sha256": _file_sha256(deployment_path / "deployment.json"),
        },
        "capability": {
            "path": _shown(repo, capability_path),
            "sha256": capability.digest,
            "source_sha256": _file_sha256(capability_path),
            "technology_view": capability.technology_view,
        },
        "cost_table": {
            "path": _shown(repo, cost_table_path),
            "sha256": cost_table.digest,
            "source_sha256": _file_sha256(cost_table_path),
            "schema": cost_source.get("schema"),
            "cost_table_id": cost_table.cost_table_id,
            "technology_view": cost_table.technology_view,
            "policy_id": cost_policy["policy_id"],
        },
        "request_sha256": _digest(request),
        "comparison_sha256": contract_validation["contract_sha256"],
    }
    boundary["boundary_sha256"] = boundary_digest(boundary)
    validation = validate_boundary(
        boundary,
        repo=repo,
        expected_contract=contract,
        expected_contract_path=contract_path,
    )
    if not validation["valid"]:
        raise BoundaryError(
            "constructed boundary failed validation: "
            + ", ".join(validation["failed_checks"])
        )
    return boundary


def _normalise_topology(value: object) -> int | None:
    try:
        if type(value) is str:
            return int(TopologyClass[value])
        if type(value) is int:
            return int(TopologyClass(value))
        return None
    except (KeyError, TypeError, ValueError):
        return None


def validate_boundary(
    boundary: Mapping[str, Any] | object,
    *,
    repo: Path = REPO,
    cycle_inputs: Mapping[str, Any] | None = None,
    expected_contract: Mapping[str, Any] | None = None,
    expected_contract_path: Path | None = None,
) -> dict[str, Any]:
    """Re-read the authoritative contract and every target source."""

    body = _mapping(boundary)
    contract_record = _mapping(body.get("comparison_contract"))
    target = _mapping(body.get("target"))
    workload = _mapping(body.get("workload"))
    deployment_record = _mapping(body.get("deployment"))
    capability_record = _mapping(body.get("capability"))
    cost_record = _mapping(body.get("cost_table"))
    schema_errors = _schema_errors(body, BOUNDARY_SCHEMA_PATH)
    checks: dict[str, bool] = {
        "schema_valid": not schema_errors,
        "boundary_digest_exact": body.get("boundary_sha256") == boundary_digest(body),
        "execution_scope_known": body.get("execution_scope")
        in {"measurement_slice", "full_workload"},
    }

    contract: Mapping[str, Any] = {}
    contract_validation: Mapping[str, Any] = {}
    try:
        contract_path = _source_path(repo, contract_record.get("path"))
        loaded = _strict_json_file(contract_path)
        if not isinstance(loaded, Mapping):
            raise BoundaryError("comparison contract is not an object")
        contract = loaded
        contract_validation = validate_comparison_contract(
            contract, repo=repo, source_path=contract_path
        )
        expected = expected_contract if expected_contract is not None else contract
        expected_path = (
            expected_contract_path
            if expected_contract_path is not None
            else repo / CONTRACT_PATHS[str(body.get("comparison_id"))]
        )
        checks.update(
            contract_schema_valid=contract_validation.get("valid") is True,
            contract_target_sources_ready=contract_validation.get("ready") is True,
            contract_path_exact=_shown(repo, contract_path) == _shown(repo, expected_path),
            contract_source_sha256_exact=(
                _file_sha256(contract_path) == contract_record.get("source_sha256")
            ),
            contract_digest_exact=(
                _digest(contract) == contract_record.get("sha256") == _digest(expected)
            ),
            comparison_id_contract_exact=(
                body.get("comparison_id") == contract.get("comparison_id")
            ),
            comparison_digest_exact=(
                body.get("comparison_sha256") == contract_record.get("sha256")
            ),
        )
    except (AttributeError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        checks.update(
            contract_schema_valid=False,
            contract_target_sources_ready=False,
            contract_path_exact=False,
            contract_source_sha256_exact=False,
            contract_digest_exact=False,
            comparison_id_contract_exact=False,
            comparison_digest_exact=False,
        )

    model = _mapping(contract.get("model"))
    governed_workload = _mapping(contract.get("workload"))
    targets = _mapping(contract.get("targets"))
    role = target.get("role")
    expected_target = _mapping(targets.get(role))
    checks.update(
        model_identity_contract_exact=(
            body.get("model_id") == model.get("model_id")
            and body.get("model_digest") == model.get("graph_id")
            and body.get("numeric_profile") == model.get("numeric_profile")
        ),
        comparison_workload_digest_exact=(
            body.get("comparison_workload_sha256")
            == comparison_workload_digest(contract)
        ),
        workload_contract_exact=(
            type(workload.get("prompt_token_count")) is int
            and type(workload.get("max_new_tokens")) is int
            and workload.get("path") == governed_workload.get("path")
            and workload.get("sha256") == governed_workload.get("source_sha256")
            and workload.get("workload_id") == governed_workload.get("workload_id")
            and workload.get("workload_digest") == governed_workload.get("digest")
            and workload.get("kind") == governed_workload.get("kind")
            and workload.get("prompt_token_count")
            == governed_workload.get("prompt_token_count")
            and workload.get("max_new_tokens")
            == governed_workload.get("max_new_tokens")
            and workload.get("index_path") == governed_workload.get("index_path")
            and workload.get("index_source_sha256")
            == governed_workload.get("index_source_sha256")
            and workload.get("tokenizer_sha256")
            == governed_workload.get("tokenizer_sha256")
            and workload.get("rendered_text_sha256")
            == governed_workload.get("rendered_text_sha256")
            and workload.get("template") == governed_workload.get("template")
        ),
        target_role_exact=role in TARGET_ROLE_STORAGE
        and expected_target.get("role") == role,
        target_identity_contract_exact=(
            type(target.get("topology_class")) is int
            and type(target.get("node_count")) is int
            and target.get("backend") == expected_target.get("backend")
            and target.get("target_id") == expected_target.get("target_id")
            and target.get("storage_class") == expected_target.get("storage_class")
            and target.get("topology_class")
            == expected_target.get("topology_class")
            and target.get("node_count") == expected_target.get("node_count")
        ),
    )

    try:
        root = _source_path(repo, deployment_record.get("path"))
        deployment = _read_deployment_strict(root)
        topology, nodes = topology_identity(deployment)
        storage = _immutable_storage_classes(deployment)
        lock = _mapping(expected_target.get("deployment"))
        checks.update(
            deployment_source_exact=(
                deployment.deployment_digest.hex() == deployment_record.get("sha256")
                == lock.get("digest")
                and _file_sha256(root / "deployment.json")
                == deployment_record.get("manifest_sha256")
                == lock.get("source_sha256")
                and _shown(repo, root) == lock.get("path")
            ),
            deployment_model_exact=(
                deployment.model_id == body.get("model_id")
                and _mapping(deployment.source_identity).get("graph_id")
                == body.get("model_digest")
            ),
            deployment_target_exact=(
                deployment.backend == target.get("backend")
                and deployment.target_id == target.get("target_id")
                and topology == target.get("topology_class")
                and nodes == target.get("node_count")
                and target.get("storage_class") in storage
                and ({"ROM", "HBM"} - {str(target.get("storage_class"))}).isdisjoint(storage)
            ),
        )
    except (
        AttributeError,
        BoundaryError,
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        deployment = None
        checks.update(
            deployment_source_exact=False,
            deployment_model_exact=False,
            deployment_target_exact=False,
        )

    try:
        path = _source_path(repo, capability_record.get("path"))
        payload = path.read_bytes()
        capability_body = _strict_json_loads(payload, source=path)
        if not isinstance(capability_body, Mapping):
            raise BoundaryError("capability source is not an object")
        capability = Capability.from_dict(capability_body)
        lock = _mapping(expected_target.get("capability"))
        policy = _mapping(contract.get("policy"))
        checks["capability_source_exact"] = (
            hashlib.sha256(payload).hexdigest()
            == capability_record.get("source_sha256")
            == lock.get("source_sha256")
            and capability.digest == capability_record.get("sha256") == lock.get("digest")
            and type(capability_body.get("topology_class")) is int
            and type(_mapping(capability_body.get("limits")).get("max_nodes")) is int
            and _shown(repo, path) == lock.get("path")
            and capability.technology_view
            == capability_record.get("technology_view")
            == policy.get("technology_view")
            and isinstance(deployment, Deployment)
            and deployment.capability_digest == capability.digest
        )
    except (AttributeError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        checks["capability_source_exact"] = False

    try:
        path = _source_path(repo, cost_record.get("path"))
        payload = path.read_bytes()
        cost_body = _strict_json_loads(payload, source=path)
        if not isinstance(cost_body, Mapping):
            raise BoundaryError("cost-table source is not an object")
        cost = CostTable.from_dict(cost_body, path=path)
        cost_policy = _mapping(expected_target.get("cost_policy"))
        lock = _mapping(cost_policy.get("lock"))
        checks["cost_source_exact"] = (
            hashlib.sha256(payload).hexdigest()
            == cost_record.get("source_sha256")
            == lock.get("source_sha256")
            and cost.digest == cost_record.get("sha256") == lock.get("digest")
            and _shown(repo, path) == lock.get("path")
            and cost.cost_table_id == cost_record.get("cost_table_id")
            == cost_policy.get("cost_table_id")
            and cost.technology_view == cost_record.get("technology_view")
            == _mapping(contract.get("policy")).get("technology_view")
            and cost_record.get("policy_id") == cost_policy.get("policy_id")
            and cost_body.get("comparison_policy") == _policy_identity(contract, str(role))
        )
    except (AttributeError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        checks["cost_source_exact"] = False

    if cycle_inputs is not None:
        inputs = _mapping(cycle_inputs)
        request_checks = validate_governed_request(
            inputs.get("request"), contract, deployment
        )
        checks.update(
            cycle_boundary_digest_exact=(
                inputs.get("comparison_boundary_digest") == body.get("boundary_sha256")
            ),
            cycle_comparison_digest_exact=(
                inputs.get("comparison_digest") == body.get("comparison_sha256")
            ),
            cycle_contract_digest_exact=(
                inputs.get("comparison_contract_digest")
                == contract_record.get("sha256")
            ),
            cycle_execution_scope_exact=(
                inputs.get("comparison_execution_scope")
                == body.get("execution_scope")
            ),
            cycle_model_exact=(
                inputs.get("model_id") == body.get("model_id")
                and inputs.get("model_digest") == body.get("model_digest")
            ),
            cycle_workload_exact=inputs.get("workload") == workload,
            cycle_comparison_workload_digest_exact=(
                inputs.get("comparison_workload_sha256")
                == body.get("comparison_workload_sha256")
            ),
            cycle_target_exact=(
                inputs.get("backend") == target.get("backend")
                and inputs.get("target_id") == target.get("target_id")
                and _normalise_topology(inputs.get("topology_class"))
                == target.get("topology_class")
                and type(inputs.get("node_count")) is int
                and inputs.get("node_count") == target.get("node_count")
            ),
            cycle_deployment_digest_exact=(
                inputs.get("deployment_digest") == deployment_record.get("sha256")
            ),
            cycle_capability_exact=(
                inputs.get("capability_digest") == capability_record.get("sha256")
                and inputs.get("capability_technology_view")
                == capability_record.get("technology_view")
            ),
            cycle_cost_table_exact=(
                _mapping(inputs.get("cost_table")).get("sha256")
                == cost_record.get("sha256")
                and _mapping(inputs.get("cost_table")).get("cost_table_id")
                == cost_record.get("cost_table_id")
                and _mapping(inputs.get("cost_table")).get("technology_view")
                == cost_record.get("technology_view")
            ),
            cycle_request_binding_exact=(
                (
                    body.get("execution_scope") == "measurement_slice"
                    and isinstance(inputs.get("request"), Mapping)
                    and inputs.get("request_trajectory_sha256") is None
                    and all(request_checks.values())
                    and _digest(_mapping(inputs.get("request")))
                    == body.get("request_sha256")
                    and body.get("request_trajectory_sha256") is None
                )
                or (
                    body.get("execution_scope") == "full_workload"
                    and inputs.get("request") is None
                    and inputs.get("request_trajectory_sha256")
                    == body.get("request_trajectory_sha256")
                    and body.get("request_sha256") is None
                )
            ),
        )

    failed = [name for name, passed in checks.items() if not passed]
    return {
        "valid": not failed,
        "checks": checks,
        "schema_errors": schema_errors,
        "contract_validation": contract_validation,
        "failed_checks": failed,
    }
