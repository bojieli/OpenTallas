#!/usr/bin/env python3
"""Build the fail-closed readiness record for checklist gate TA-CMP-7-ASAP7.

This is a preflight, not a performance-report generator.  It inventories the
evidence needed to compare the Qwen ROM/HBM targets, the DeepSeek wafer/32
node HBM targets and the DeepSeek wafer/32 node ROM array targets in one
predictive ASAP7 view.  Each registered contract names its own pair of target
roles (ROM/HBM or ROM/ROM); the pairing below follows the contract rather
than assuming one side is HBM.  An input from another technology view is
reported as excluded and is never used to satisfy the gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import Capability, canonical_json  # noqa: E402
from runtime.abi3.constants import TopologyClass  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import Phase  # noqa: E402
from runtime.cycle.machine import (  # noqa: E402
    ENGINE_FAMILY_NAMES,
    CostTable,
    MachineError,
    MachineModel,
)
from tools.abi3_comparison_boundary import (  # noqa: E402
    BoundaryError,
    CONTRACT_PATHS,
    ORACLE_PRODUCER_PATHS,
    REQUEST_TRAJECTORY_SCHEMA,
    TARGET_ROLE_STORAGE,
    comparison_workload_digest,
    contract_target_roles,
    load_comparison_contract,
    request_trajectory_digest,
    validate_boundary,
    validate_comparison_contract,
    validate_governed_request,
)


SCHEMA = "opentallas.abi3.asap7_comparison_readiness.v1"
GATE_ID = "TA-CMP-7-ASAP7"
REQUIRED_VIEW = "asap7"
FUNCTIONAL_SCHEMAS = frozenset(
    {
        "opentallas.abi3.accelerator_tokens.v1",
        "opentallas.abi3.campaign.v1",
    }
)
CYCLE_SCHEMA = "opentallas.abi3.cycle_result.v1"
CYCLE_PRODUCER = "tools/run_abi3_cycle.py"
CYCLE_PRODUCER_SCHEMA = "opentallas.abi3.cycle_producer.v1"
CYCLE_PRODUCER_EVIDENCE_CLASS = "cycle_model_measurement"
ENGINE_FAMILIES = tuple(sorted(set(ENGINE_FAMILY_NAMES.values())))
FUNCTIONAL_PRODUCER = "tools/run_accelerator_tokens.py"
FUNCTIONAL_COMMON_SOURCES = frozenset(
    {
        FUNCTIONAL_PRODUCER,
        "compiler/backends/numeric_contracts.py",
        "compiler/ir/v3/kernel_ir.py",
        "compiler/ir/v3/lowering.py",
        "compiler/ir/v3/numeric.py",
        "runtime/abi3/builder.py",
        "runtime/abi3/capability.py",
        "runtime/abi3/constants.py",
        "runtime/abi3/crc.py",
        "runtime/abi3/deployment.py",
        "runtime/driver.py",
        "runtime/abi3/descriptors.py",
        "runtime/abi3/layout.py",
        "runtime/abi3/records.py",
        "runtime/abi3/verifier.py",
        "runtime/evidence.py",
        "runtime/reference/compression_pool.py",
        "runtime/reference/formats.py",
        "runtime/reference/hadamard.py",
        "runtime/reference/hyper_connection.py",
        "runtime/reference/normalization.py",
        "runtime/reference/quantization.py",
        "runtime/reference/sparse_attention.py",
        "runtime/reference/sqrt_softplus.py",
        "runtime/reference/swiglu.py",
        "runtime/reference/transcendental.py",
        "runtime/sim/backend.py",
        "runtime/sim/counters.py",
        "runtime/sim/device.py",
        "runtime/sim/engine.py",
        "runtime/sim/formats.py",
        "runtime/sim/generators.py",
        "runtime/sim/memory.py",
        "runtime/sim/performance.py",
        "runtime/sim/weight_cache.py",
        "runtime/tensor_accelerator/attention.py",
        "runtime/tensor_accelerator/bf16.py",
        "runtime/tensor_accelerator/elementwise.py",
        "runtime/tensor_accelerator/rmsnorm.py",
        "runtime/tensor_accelerator/rope.py",
        "runtime/tensor_accelerator/sparse_attention.py",
    }
)
# ``compiler/backends/schedule_rule.py`` is AM-E9's one SCHEDULE emission rule,
# a functional source of every backend (tools/run_accelerator_tokens.py
# BACKEND_FUNCTIONAL_SOURCE_PATHS), so every boundary below carries it.
FUNCTIONAL_BACKEND_SOURCES = {
    ("qwen3_rom_single_chip_vs_hbm_single_chip", "rom"): frozenset(
        {
            "compiler/backends/rom/qwen3.py",
            "compiler/backends/rom/common/image.py",
            "compiler/backends/rom/common/program.py",
            "compiler/backends/schedule_rule.py",
        }
    ),
    ("qwen3_rom_single_chip_vs_hbm_single_chip", "hbm"): frozenset(
        {
            "compiler/backends/hbm_sram/lower.py",
            "compiler/backends/hbm_sram/plan.py",
            "compiler/backends/schedule_rule.py",
        }
    ),
    ("deepseek_v4_rom_wafer_vs_hbm_cluster_32", "rom"): frozenset(
        {
            "compiler/backends/rom/deepseek_v4.py",
            "compiler/backends/rom/common/image.py",
            "compiler/backends/rom/common/program.py",
            "compiler/backends/schedule_rule.py",
        }
    ),
    ("deepseek_v4_rom_wafer_vs_hbm_cluster_32", "hbm"): frozenset(
        {
            "compiler/backends/hbm_sram/lower.py",
            "compiler/backends/hbm_sram/plan.py",
            "compiler/backends/schedule_rule.py",
        }
    ),
    ("deepseek_v4_rom_wafer_vs_rom_array_32", "rom"): frozenset(
        {
            "compiler/backends/rom/deepseek_v4.py",
            "compiler/backends/rom/common/image.py",
            "compiler/backends/rom/common/program.py",
            "compiler/backends/schedule_rule.py",
        }
    ),
    # The array backend is the producer's ``rom_deepseek_v4_array`` boundary:
    # it lowers through the wafer backend's module as well as its own.
    ("deepseek_v4_rom_wafer_vs_rom_array_32", "rom_array"): frozenset(
        {
            "compiler/backends/rom/deepseek_v4_array.py",
            "compiler/backends/rom/deepseek_v4.py",
            "compiler/backends/rom/common/image.py",
            "compiler/backends/rom/common/program.py",
            "compiler/backends/schedule_rule.py",
        }
    ),
}

CAPABILITY_PATHS = (
    "configs/hardware/abi3_capability/rom_qwen3.json",
    "configs/hardware/abi3_capability/hbm_sram_single_chip.json",
    "configs/hardware/abi3_capability/rom_deepseek_v4.json",
    "configs/hardware/abi3_capability/hbm_sram_cluster_32.json",
)

#: The comparisons THIS gate requires.  TA-CMP-7-ASAP7 is the governed
#: comparison of the four-target release, and its required set is the three
#: contracts of that release.  ``CONTRACT_PATHS`` is the registry of every
#: contract the boundary tool knows, which since WP-N of
#: docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md also holds the three
#: DeepSeek-V4.1 pairs.  Those belong to gate DS41-CMP11 and are deliberately
#: NOT pulled in here: a later target may not enlarge this gate's required set,
#: turn its source-valid verdict false, or otherwise change what closing it
#: means.  A new contract joins this tuple only when the board adds it to this
#: gate.
REQUIRED_COMPARISON_IDS = (
    "qwen3_rom_single_chip_vs_hbm_single_chip",
    "deepseek_v4_rom_wafer_vs_hbm_cluster_32",
    "deepseek_v4_rom_wafer_vs_rom_array_32",
)
REQUIRED_CONTRACT_PATHS = {
    comparison_id: CONTRACT_PATHS[comparison_id]
    for comparison_id in REQUIRED_COMPARISON_IDS
}

SOURCE_PATHS = (
    "Makefile",
    "tools/audit_abi3_asap7_comparison_readiness.py",
    "tools/abi3_comparison_boundary.py",
    "tools/run_abi3_cycle.py",
    "tools/build_abi3_cost_tables.py",
    "runtime/cycle/machine.py",
    "runtime/abi3/capability.py",
    "configs/pdk/asap7_physical_lock.json",
    "schemas/abi3/comparison_boundary_v1.schema.json",
    "schemas/abi3/comparison_contract_v1.schema.json",
    *REQUIRED_CONTRACT_PATHS.values(),
    "docs/FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md",
    "docs/TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md",
)

CLUSTER_FABRIC_PARAMETERS = (
    "fabric.cluster.link_bytes_per_cycle",
    "fabric.cluster.link_hop_latency_cycles",
    "fabric.cluster.switch_latency_cycles",
    "fabric.cluster.switch_levels",
    "fabric.cluster.switch_radix",
    "fabric.cluster.packet_bytes",
    "fabric.cluster.packet_header_bytes",
    "fabric.cluster.credits",
    "fabric.cluster.credit_return_cycles",
    "fabric.cluster.retry_interval_packets",
    "fabric.cluster.retry_cycles",
    "fabric.cluster.barrier_round_cycles",
    "fabric.cluster.endpoint_latency_cycles",
)

WAFER_FABRIC_PARAMETERS = (
    "fabric.wafer.reticle_rows",
    "fabric.wafer.reticle_cols",
    "fabric.wafer.tile_rows_per_reticle",
    "fabric.wafer.tile_cols_per_reticle",
    "fabric.wafer.tile_link_bytes_per_cycle",
    "fabric.wafer.tile_hop_cycles",
    "fabric.wafer.router_latency_cycles",
    "fabric.wafer.stitch_bytes_per_cycle",
    "fabric.wafer.stitch_hop_cycles",
    "fabric.wafer.packet_bytes",
    "fabric.wafer.packet_header_bytes",
    "fabric.wafer.credits",
    "fabric.wafer.credit_return_cycles",
    "fabric.wafer.virtual_channels",
    "fabric.wafer.barrier_level_cycles",
    "fabric.wafer.endpoint_latency_cycles",
)


def _strict_json_loads(payload: str | bytes, *, source: object) -> Any:
    """Reject duplicate object keys and JSON's non-finite extensions."""

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        body: dict[str, Any] = {}
        for key, value in pairs:
            if key in body:
                raise ValueError(f"duplicate JSON key {key!r} in {source}")
            body[key] = value
        return body

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number {value!r} in {source}")

    return json.loads(
        payload,
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )


def _load_json(path: Path) -> Any:
    return _strict_json_loads(path.read_bytes(), source=path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _semantic_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def _identity(repo: Path, path: Path) -> dict[str, Any]:
    return {
        "path": _relative(repo, path),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _strict_int(value: object, *, minimum: int | None = None) -> bool:
    return type(value) is int and (minimum is None or value >= minimum)


def _contract_summary(
    body: Mapping[str, Any],
    validation: Mapping[str, Any],
    path: Path,
    repo: Path,
) -> dict[str, Any]:
    """Expose the authoritative document without copying its identity by hand."""

    model = _mapping(body.get("model"))
    workload = _mapping(body.get("workload"))
    execution = _mapping(body.get("execution"))
    external_oracle = _mapping(body.get("external_oracle"))
    targets = _mapping(body.get("targets"))
    target_sources_ready = _mapping(validation.get("target_sources_ready"))
    target_lock_status: dict[str, Any] = {}
    for role in contract_target_roles(targets):
        target = _mapping(targets.get(role))
        cost_policy = _mapping(target.get("cost_policy"))
        target_lock_status[role] = {
            "deployment": _mapping(target.get("deployment")).get("status"),
            "capability": _mapping(target.get("capability")).get("status"),
            "cost_policy": _mapping(cost_policy.get("lock")).get("status"),
            "source_ready": target_sources_ready.get(role) is True,
        }
    source_valid = validation.get("valid") is True
    ready = source_valid and validation.get("ready") is True
    return {
        "comparison_id": body.get("comparison_id"),
        "contract_path": _relative(repo, path),
        "contract_source_sha256": _sha256(path) if path.is_file() else None,
        "contract_sha256": validation.get("contract_sha256"),
        "contract_source_valid": source_valid,
        "contract_ready": ready,
        "external_oracle_source_ready": validation.get(
            "external_oracle_source_ready"
        )
        is True,
        "external_oracle_lock_status": external_oracle.get("status"),
        "external_oracle": dict(external_oracle),
        "target_sources_ready": dict(target_sources_ready),
        "target_lock_status": target_lock_status,
        "source_validation": dict(validation),
        "document": dict(body),
        # Compatibility fields used by the focused audit helpers and historical
        # readiness artifact consumers.  Every value is derived from the same
        # checked-in document above; none is a second contract definition.
        "schema": body.get("schema"),
        "version": body.get("version"),
        "model": dict(model),
        "model_id": model.get("model_id"),
        "model_digest": model.get("graph_id"),
        "numeric_profile": model.get("numeric_profile"),
        "workload": dict(workload),
        "workload_id": workload.get("workload_id"),
        "workload_path": workload.get("path"),
        "workload_index_path": workload.get("index_path"),
        "workload_digest": workload.get("digest"),
        "comparison_workload_sha256": comparison_workload_digest(body),
        "workload_source_sha256": workload.get("source_sha256"),
        "tokenizer_sha256": workload.get("tokenizer_sha256"),
        "prompt_token_count": workload.get("prompt_token_count"),
        "max_new_tokens": workload.get("max_new_tokens"),
        "execution": dict(execution),
        "policy": dict(_mapping(body.get("policy"))),
        "targets": {key: dict(_mapping(value)) for key, value in targets.items()},
        "source_checks": dict(_mapping(validation.get("checks"))),
        "source_valid": source_valid,
    }


def _load_authoritative_contracts(repo: Path) -> tuple[dict[str, Any], ...]:
    contracts: list[dict[str, Any]] = []
    for comparison_id, relative in REQUIRED_CONTRACT_PATHS.items():
        path = repo / relative
        try:
            body, validation, path = load_comparison_contract(
                comparison_id,
                repo=repo,
                path=path,
            )
        except BoundaryError:
            try:
                loaded = _load_json(path)
                body = loaded if isinstance(loaded, Mapping) else {}
            except (OSError, ValueError, json.JSONDecodeError):
                body = {}
            validation = validate_comparison_contract(
                body,
                repo=repo,
                source_path=path,
            )
        summary = _contract_summary(body, validation, path, repo)
        # A missing or malformed document must still occupy its registered slot
        # in the readiness report, never silently remove a mandatory comparison.
        if summary["comparison_id"] != comparison_id:
            summary["comparison_id"] = comparison_id
            summary["contract_source_valid"] = False
            summary["contract_ready"] = False
            summary["source_valid"] = False
        contracts.append(summary)
    return tuple(contracts)


COMPARISON_CONTRACTS: tuple[dict[str, Any], ...] = _load_authoritative_contracts(REPO)


def _target_role(
    target: Mapping[str, Any], contract: Mapping[str, Any]
) -> str | None:
    """Resolve a role only by an exact authoritative target identity."""

    targets = _mapping(contract.get("targets"))
    for role in contract_target_roles(targets):
        expected = _mapping(targets.get(role))
        if (
            _strict_int(target.get("topology_class"), minimum=0)
            and _strict_int(target.get("node_count"), minimum=1)
            and target.get("backend") == expected.get("backend")
            and target.get("target_id") == expected.get("target_id")
            and target.get("topology_class") == expected.get("topology_class")
            and target.get("node_count") == expected.get("node_count")
        ):
            return role
    return None


def _functional_payload(body: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if body.get("schema") not in FUNCTIONAL_SCHEMAS:
        return None
    if body.get("schema") == "opentallas.abi3.campaign.v1":
        record = body.get("record")
        return record if isinstance(record, Mapping) else None
    return body


def _reference_agreement(
    body: Mapping[str, Any], payload: Mapping[str, Any]
) -> bool:
    oracle = body.get("oracle")
    if isinstance(oracle, Mapping) and oracle.get("agreement") is True:
        return True
    notes = payload.get("notes")
    return isinstance(notes, Mapping) and notes.get("reference_agreement") is True


def _completion_closed(
    payload: Mapping[str, Any], generation: Mapping[str, Any]
) -> bool:
    token_ids = payload.get("generated_token_ids")
    if not isinstance(token_ids, list) or not token_ids:
        return False
    if any(not isinstance(token, int) or isinstance(token, bool) for token in token_ids):
        return False
    stop_reason = payload.get("stop_reason")
    raw_eos = generation.get("eos_token_ids")
    eos = {
        token
        for token in raw_eos
        if isinstance(token, int) and not isinstance(token, bool)
    } if isinstance(raw_eos, list) else set()
    cap = generation.get("max_new_tokens")
    if stop_reason == "eos":
        return token_ids[-1] in eos and not any(token in eos for token in token_ids[:-1])
    return (
        stop_reason == "max_new_tokens"
        and isinstance(cap, int)
        and not isinstance(cap, bool)
        and len(token_ids) == cap
        and not any(token in eos for token in token_ids)
    )


def assess_functional_document(
    body: Mapping[str, Any],
    path: str,
    contract: Mapping[str, Any],
    *,
    sha256: str = "",
) -> dict[str, Any] | None:
    """Assess one functional artifact against one mandatory workload."""
    payload = _functional_payload(body)
    if payload is None:
        return None
    workload = payload.get("workload")
    target = payload.get("target")
    if not isinstance(workload, Mapping) or not isinstance(target, Mapping):
        return None
    if workload.get("workload_id") != contract["workload_id"]:
        return None

    target_role = _target_role(target, contract)
    expected_target = _mapping(_mapping(contract.get("targets")).get(target_role))
    generation = _mapping(_mapping(contract.get("execution")).get("generation"))
    token_ids = payload.get("generated_token_ids")
    token_ids = token_ids if isinstance(token_ids, list) else []
    status = body.get("status")
    checks = {
        "acceptance_contract_source_valid": contract.get("source_valid") is True,
        "status_pass": status == "pass",
        "no_failure": payload.get("failure") in (None, ""),
        "model_id_exact": workload.get("model_id", contract["model_id"])
        == contract["model_id"],
        "model_digest_exact": workload.get("graph_id") == contract["model_digest"],
        "numeric_profile_exact": workload.get("numeric_profile")
        == contract["numeric_profile"],
        "workload_digest_exact": bool(contract.get("workload_digest"))
        and workload.get("workload_digest") == contract.get("workload_digest"),
        "prompt_token_count_exact": _strict_int(
            workload.get("prompt_token_count"), minimum=1
        )
        and workload.get("prompt_token_count") == contract["prompt_token_count"],
        "declared_run_max_new_tokens_exact": _strict_int(
            workload.get("max_new_tokens"), minimum=1
        )
        and workload.get("max_new_tokens") == contract["max_new_tokens"],
        "tokenizer_identity_exact": bool(contract.get("tokenizer_sha256"))
        and workload.get("tokenizer_sha256") == contract.get("tokenizer_sha256"),
        "target_role_known": target_role in TARGET_ROLE_STORAGE,
        "target_backend_exact": target.get("backend")
        == expected_target.get("backend"),
        "target_id_exact": target.get("target_id")
        == expected_target.get("target_id"),
        "topology_exact": _strict_int(target.get("topology_class"), minimum=0)
        and target.get("topology_class") == expected_target.get("topology_class"),
        "node_count_exact": _strict_int(target.get("node_count"), minimum=1)
        and target.get("node_count") == expected_target.get("node_count"),
        "token_count_consistent": _strict_int(
            payload.get("generated_token_count"), minimum=1
        )
        and payload.get("generated_token_count") == len(token_ids),
        "mandatory_completion_closed": _completion_closed(payload, generation),
        "external_reference_agreement": _reference_agreement(body, payload),
    }
    failed = [name for name, value in checks.items() if not value]
    return {
        "path": path,
        "sha256": sha256,
        "schema": body.get("schema"),
        "status": status,
        "role": target_role,
        "backend": target.get("backend"),
        "target_id": target.get("target_id"),
        "technology_view": target.get("technology_view"),
        "topology_class": target.get("topology_class"),
        "node_count": target.get("node_count"),
        "workload_digest": workload.get("workload_digest"),
        "prompt_token_count": workload.get("prompt_token_count"),
        "declared_run_max_new_tokens": workload.get("max_new_tokens"),
        "generated_token_count": payload.get("generated_token_count"),
        "stop_reason": payload.get("stop_reason"),
        "failure": payload.get("failure"),
        "reference_agreement": _reference_agreement(body, payload),
        "first_divergence_index": (
            payload.get("notes", {}).get("first_divergence_index")
            if isinstance(payload.get("notes"), Mapping)
            else None
        ),
        "checks": checks,
        "failed_checks": failed,
        "admissible": not failed,
        "generated_token_ids": token_ids,
    }


def _functional_inventory(
    repo: Path, contracts: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]], set[Path]]:
    results: dict[str, Any] = {}
    inspected: set[Path] = set()
    external_oracles: list[dict[str, Any]] = []
    result_root = repo / "results" / "abi3"

    documents: list[tuple[Path, Mapping[str, Any]]] = []
    for path in sorted(result_root.rglob("*.json")) if result_root.exists() else []:
        try:
            body = _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(body, Mapping):
            continue
        documents.append((path, body))

    for contract in contracts:
        candidates: list[dict[str, Any]] = []
        workload_id = str(contract["workload_id"])
        for path, body in documents:
            assessed = assess_functional_document(
                body,
                _relative(repo, path),
                contract,
                sha256=_sha256(path),
            )
            if assessed is not None:
                candidates.append(assessed)
                inspected.add(path)
            oracle_results = body.get("results")
            if isinstance(oracle_results, Mapping) and workload_id in oracle_results:
                row = oracle_results[workload_id]
                if isinstance(row, Mapping):
                    external_oracles.append(
                        {
                            "path": _relative(repo, path),
                            "sha256": _sha256(path),
                            "workload_id": workload_id,
                            "workload_digest": row.get("workload_digest"),
                            "generated_token_count": row.get("generated_token_count"),
                            "stop_reason": row.get("stop_reason"),
                            "accelerator_execution": False,
                        }
                    )
                    inspected.add(path)

        candidates.sort(key=lambda item: item["path"])
        first_role, second_role = contract_target_roles(contract.get("targets"))
        admitted = {
            role: [item for item in candidates if item["role"] == role and item["admissible"]]
            for role in (first_role, second_role)
        }
        matching_pair = None
        for left in admitted[first_role]:
            for right in admitted[second_role]:
                if left["generated_token_ids"] == right["generated_token_ids"]:
                    matching_pair = {
                        first_role: left["path"],
                        second_role: right["path"],
                    }
                    break
            if matching_pair:
                break
        for item in candidates:
            item.pop("generated_token_ids", None)
        results[str(contract["comparison_id"])] = {
            "workload_id": workload_id,
            "mandatory_prompt_token_count": contract["prompt_token_count"],
            "mandatory_max_new_tokens": contract["max_new_tokens"],
            "workload_source_valid": contract["source_valid"],
            "candidate_count": len(candidates),
            "candidates": candidates,
            "admissible_candidate_counts": {
                role: len(items) for role, items in admitted.items()
            },
            "legacy_matching_pair": matching_pair,
            "matching_pair": matching_pair,
            "diagnostic_only": True,
            "ready": False,
            "note": (
                "Legacy functional records remain visible for diagnosis, but their "
                "self-reported oracle verdicts cannot close W11.2 correctness."
            ),
        }
    return results, sorted(external_oracles, key=lambda item: item["path"]), inspected


def _required_fabric_parameters(topology_class: int) -> tuple[str, ...]:
    if topology_class == int(TopologyClass.CLUSTER_32):
        return CLUSTER_FABRIC_PARAMETERS
    if topology_class == int(TopologyClass.WAFER_LOGICAL_DEVICE):
        return WAFER_FABRIC_PARAMETERS
    return ()


def assess_machine_documents(
    capability_body: Mapping[str, Any],
    cost_body: Mapping[str, Any],
    *,
    capability_path: str,
    cost_path: str,
) -> dict[str, Any]:
    """Apply the production resolver to one capability/cost-table pair."""
    errors: list[dict[str, str]] = []
    checks: dict[str, bool] = {}
    topology = _normalise_topology(capability_body.get("topology_class"))
    parameters = cost_body.get("parameters")
    parameters = parameters if isinstance(parameters, Mapping) else {}
    missing_fabric = sorted(
        name
        for name in _required_fabric_parameters(topology if topology is not None else -1)
        if name not in parameters
    )

    try:
        if topology is None:
            raise ValueError("topology_class must be an exact enum integer or name")
        capability = Capability.from_dict(capability_body)
        table = CostTable.from_dict(cost_body, path=Path(cost_path))
        machine = MachineModel(capability, table)
    except (KeyError, TypeError, ValueError, MachineError) as exc:
        return {
            "capability_path": capability_path,
            "cost_table_path": cost_path,
            "capability_technology_view": capability_body.get("technology_view"),
            "cost_table_technology_view": cost_body.get("technology_view"),
            "topology_class": topology,
            "same_view": False,
            "model_complete": False,
            "admissible": False,
            "missing_fabric_parameters": missing_fabric,
            "checks": {"documents_valid": False},
            "errors": [{"stage": "documents", "message": str(exc)}],
        }

    same_view = (
        capability.technology_view == REQUIRED_VIEW
        and table.technology_view == REQUIRED_VIEW
    )
    checks["documents_valid"] = True
    checks["technology_view_exact"] = same_view

    stages = [
        ("clock", lambda: machine.clock_hz),
        ("sequencer", machine.sequencer),
        ("memory", machine.memory),
        *[(f"engine.{family}", lambda family=family: machine.engine(family)) for family in ENGINE_FAMILIES],
    ]
    if topology == int(TopologyClass.CLUSTER_32):
        stages.append(("fabric.cluster", machine.cluster_fabric))
    elif topology == int(TopologyClass.WAFER_LOGICAL_DEVICE):
        stages.append(("fabric.wafer", machine.wafer_fabric))

    for name, operation in stages:
        try:
            operation()
            checks[name] = True
        except (KeyError, TypeError, ValueError, MachineError) as exc:
            checks[name] = False
            errors.append({"stage": name, "message": str(exc)})
    model_complete = all(value for name, value in checks.items() if name != "technology_view_exact")
    return {
        "capability_path": capability_path,
        "cost_table_path": cost_path,
        "capability_technology_view": capability.technology_view,
        "cost_table_technology_view": table.technology_view,
        "topology_class": topology,
        "same_view": same_view,
        "model_complete": model_complete,
        "admissible": same_view and model_complete,
        "missing_fabric_parameters": missing_fabric,
        "checks": checks,
        "errors": errors,
    }


def _capability_cost_inventory(repo: Path) -> tuple[dict[str, Any], set[Path]]:
    inspected: set[Path] = set()
    capabilities: list[dict[str, Any]] = []
    capability_docs: list[tuple[Path, Mapping[str, Any]]] = []
    for relative in CAPABILITY_PATHS:
        path = repo / relative
        if not path.is_file():
            capabilities.append({"path": relative, "present": False})
            continue
        body = _load_json(path)
        inspected.add(path)
        capability_docs.append((path, body))
        capabilities.append(
            {
                **_identity(repo, path),
                "present": True,
                "technology_view": body.get("technology_view"),
                "topology_class": body.get("topology_class"),
                "max_nodes": body.get("limits", {}).get("max_nodes"),
                "same_view": body.get("technology_view") == REQUIRED_VIEW,
            }
        )

    asap7_tables: list[tuple[Path, Mapping[str, Any]]] = []
    excluded_tables: list[dict[str, Any]] = []
    hardware = repo / "configs" / "hardware"
    for path in sorted(hardware.glob("abi3_cost_*.json")) if hardware.exists() else []:
        body = _load_json(path)
        row = {
            **_identity(repo, path),
            "cost_table_id": body.get("cost_table_id"),
            "technology_view": body.get("technology_view"),
            "parameter_count": len(body.get("parameters", {})),
        }
        if body.get("technology_view") == REQUIRED_VIEW:
            asap7_tables.append((path, body))
            inspected.add(path)
        else:
            excluded_tables.append(row)

    compatibility = [
        assess_machine_documents(
            capability_body,
            cost_body,
            capability_path=_relative(repo, capability_path),
            cost_path=_relative(repo, cost_path),
        )
        for capability_path, capability_body in capability_docs
        for cost_path, cost_body in asap7_tables
    ]
    for item in compatibility:
        item["capability_sha256"] = next(
            row["sha256"]
            for row in capabilities
            if row.get("path") == item["capability_path"]
        )
        item["cost_table_sha256"] = _sha256(repo / item["cost_table_path"])

    topology_support: dict[str, Any] = {}
    for topology, name in ((0, "single_chip"), (1, "cluster_32"), (2, "wafer")):
        rows = [item for item in compatibility if item["topology_class"] == topology]
        topology_support[name] = {
            "topology_class": topology,
            "model_complete_with_an_asap7_table": any(
                item["model_complete"] for item in rows
            ),
            "same_view_admissible": any(item["admissible"] for item in rows),
            "missing_fabric_parameters": sorted(
                {name for item in rows for name in item["missing_fabric_parameters"]}
            ),
        }

    return (
        {
            "capabilities": capabilities,
            "asap7_cost_tables": [
                {
                    **_identity(repo, path),
                    "cost_table_id": body.get("cost_table_id"),
                    "version": body.get("version"),
                    "parameter_count": len(body.get("parameters", {})),
                    "derived_from": body.get("derived_from", {}),
                }
                for path, body in asap7_tables
            ],
            "excluded_other_view_cost_tables": excluded_tables,
            "compatibility_matrix": compatibility,
            "topology_support": topology_support,
            "all_required_capabilities_same_view": bool(capabilities)
            and all(item.get("same_view") for item in capabilities),
        },
        inspected,
    )


def _normalise_topology(value: object) -> int | None:
    try:
        if type(value) is str:
            return int(TopologyClass[value])
        if type(value) is int:
            return int(TopologyClass(value))
        return None
    except (KeyError, TypeError, ValueError):
        return None


def _contract_document(contract: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if contract is None:
        return {}
    document = contract.get("document")
    return document if isinstance(document, Mapping) else contract


def _read_evidence_source(
    repo: Path, record: Mapping[str, Any]
) -> tuple[Mapping[str, Any], Path | None, str | None]:
    """Reopen a repo-contained JSON source and return its raw digest."""

    try:
        recorded = record.get("path")
        if (
            not isinstance(recorded, str)
            or not recorded
            or "\\" in recorded
            or Path(recorded).is_absolute()
            or Path(recorded).as_posix() != recorded
            or "." in Path(recorded).parts
            or ".." in Path(recorded).parts
        ):
            return {}, None, None
        path = (repo / recorded).resolve()
        path.relative_to(repo.resolve())
        if path.relative_to(repo.resolve()).as_posix() != recorded:
            return {}, None, None
        payload = path.read_bytes()
        body = _strict_json_loads(payload, source=path)
        if not isinstance(body, Mapping):
            return {}, path, hashlib.sha256(payload).hexdigest()
        return body, path, hashlib.sha256(payload).hexdigest()
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {}, None, None


def _integer_tokens(value: object, vocabulary_size: object) -> list[int] | None:
    if (
        not isinstance(value, list)
        or not isinstance(vocabulary_size, int)
        or isinstance(vocabulary_size, bool)
        or vocabulary_size < 1
        or any(
            not isinstance(token, int)
            or isinstance(token, bool)
            or token < 0
            or token >= vocabulary_size
            for token in value
        )
    ):
        return None
    return value


def _required_functional_sources(
    repo: Path, comparison_id: object, role: object
) -> frozenset[str]:
    backend_sources = FUNCTIONAL_BACKEND_SOURCES.get(
        (str(comparison_id), str(role))
    )
    if backend_sources is None:
        return frozenset()
    engine_root = repo / "runtime/sim/engines"
    engine_sources = frozenset(
        path.relative_to(repo).as_posix()
        for path in engine_root.glob("*.py")
        if path.is_file()
    )
    return FUNCTIONAL_COMMON_SOURCES | backend_sources | engine_sources


def _validate_source_map(
    repo: Path,
    value: object,
    required: frozenset[str],
) -> tuple[dict[str, bool], list[str]]:
    """Rehash every canonical repo-contained path in a producer source map."""

    source_map = value if isinstance(value, Mapping) else {}
    nonempty = bool(source_map)
    well_formed = nonempty
    exact = nonempty
    inspected: list[str] = []
    for recorded, expected_sha in source_map.items():
        if (
            not isinstance(recorded, str)
            or not recorded
            or "\\" in recorded
            or Path(recorded).is_absolute()
            or Path(recorded).as_posix() != recorded
            or "." in Path(recorded).parts
            or ".." in Path(recorded).parts
            or not isinstance(expected_sha, str)
            or len(expected_sha) != 64
            or any(character not in "0123456789abcdef" for character in expected_sha)
        ):
            well_formed = False
            exact = False
            continue
        try:
            path = (repo / recorded).resolve()
            path.relative_to(repo.resolve())
            if path.relative_to(repo.resolve()).as_posix() != recorded or not path.is_file():
                raise OSError(recorded)
            inspected.append(recorded)
            if _sha256(path) != expected_sha:
                exact = False
        except (OSError, ValueError):
            exact = False
    return (
        {
            "nonempty": nonempty,
            "well_formed": well_formed,
            "required": bool(required) and set(source_map) == set(required),
            "exact": exact and well_formed,
        },
        sorted(set(inspected)),
    )


def _finite_nonnegative(value: object, *, positive: bool = False) -> bool:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        return False
    return value > 0 if positive else value >= 0


def _numeric_leaves_nonnegative(value: object) -> bool:
    if isinstance(value, Mapping):
        return all(_numeric_leaves_nonnegative(item) for item in value.values())
    if isinstance(value, list):
        return all(_numeric_leaves_nonnegative(item) for item in value)
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return _finite_nonnegative(value)
    return True


def _measurement_document_checks(
    source: Mapping[str, Any],
    reference: Mapping[str, Any],
    request: Mapping[str, Any],
    functional_step: Mapping[str, Any],
    aggregate_inputs: Mapping[str, Any],
    contract: Mapping[str, Any],
    *,
    repo: Path,
    source_sha256: str | None,
) -> dict[str, bool]:
    """Validate one source-reopened transaction timing result."""

    source_inputs = _mapping(source.get("inputs"))
    execution = _mapping(source.get("execution"))
    timing = _mapping(source.get("timing"))
    counters = _mapping(source.get("counters"))
    architectural = _mapping(counters.get("architectural"))
    timing_counters = _mapping(counters.get("timing"))
    memory = _mapping(source.get("memory"))
    engines = _mapping(source.get("engines"))
    provenance = _mapping(source.get("provenance"))
    producer = _mapping(source.get("producer"))
    rates = source.get("rates")
    rates = rates if isinstance(rates, list) else []
    rate_rows = {
        row.get("name"): row
        for row in rates
        if isinstance(row, Mapping) and isinstance(row.get("name"), str)
    }

    total_cycles = timing.get("total_cycles")
    frequency = timing.get("clock_frequency_hz")
    seconds = timing.get("seconds")
    timing_values_valid = bool(timing) and all(
        _finite_nonnegative(value) for value in timing.values()
    )
    timing_cycle_counts_valid = all(
        _strict_int(value, minimum=0)
        for name, value in timing.items()
        if str(name).endswith("_cycles")
    )
    timing_valid = (
        timing_values_valid
        and timing_cycle_counts_valid
        and _strict_int(total_cycles, minimum=1)
        and _finite_nonnegative(frequency, positive=True)
        and _finite_nonnegative(seconds, positive=True)
        and timing.get("transaction_cycles") == total_cycles
        and math.isclose(
            float(seconds),
            float(total_cycles) / float(frequency),
            rel_tol=1e-9,
            abs_tol=1e-15,
        )
    )

    required_rates = {
        "transactions_per_second": "1/s",
        "tokens_per_second": "tokens/s",
    }
    throughput_valid = bool(rates) and len(rate_rows) == len(rates)
    for name, unit in required_rates.items():
        row = _mapping(rate_rows.get(name))
        rate_provenance = _mapping(row.get("provenance"))
        throughput_valid = throughput_valid and (
            row.get("unit") == unit
            and _finite_nonnegative(row.get("value"))
            and isinstance(rate_provenance.get("class"), str)
            and bool(_mapping(rate_provenance.get("inputs")))
        )
    throughput_valid = throughput_valid and all(
        _finite_nonnegative(_mapping(row).get("value")) for row in rates
    )

    counters_valid = (
        bool(architectural)
        and bool(timing_counters)
        and set(architectural).isdisjoint(timing_counters)
        and all(not str(name).startswith("latency.") for name in architectural)
        and all(str(name).startswith("latency.") for name in timing_counters)
        and all(_strict_int(value, minimum=0) for value in architectural.values())
        and all(_strict_int(value, minimum=0) for value in timing_counters.values())
        and timing_counters.get("latency.transaction_cycles") == total_cycles
    )

    memory_valid = bool(memory) and _numeric_leaves_nonnegative(memory)
    memory_activity = False
    for storage_class in ("hbm", "sram", "rom", "host"):
        row = _mapping(memory.get(storage_class))
        core = (
            "accesses",
            "bytes_read",
            "bytes_written",
            "bytes_total",
            "busy_cycles",
            "bandwidth_utilisation",
        )
        integer_counts = core[:-1]
        memory_valid = memory_valid and bool(row) and all(
            _strict_int(row.get(name), minimum=0) for name in integer_counts
        )
        memory_valid = memory_valid and (
            _finite_nonnegative(row.get("bandwidth_utilisation"))
            and row.get("bandwidth_utilisation", 0) <= 1
            and row.get("bytes_total")
            == row.get("bytes_read", 0) + row.get("bytes_written", 0)
        )
        memory_activity = memory_activity or any(
            _mapping(row).get(name, 0) > 0
            for name in ("accesses", "bytes_total", "busy_cycles")
            if _finite_nonnegative(_mapping(row).get(name, 0))
        )
    memory_valid = memory_valid and memory_activity

    utilisation_valid = bool(engines) and _numeric_leaves_nonnegative(engines)
    engine_activity = False
    for row_value in engines.values():
        row = _mapping(row_value)
        utilisation_valid = utilisation_valid and all(
            _strict_int(row.get(name), minimum=0)
            for name in ("operations", "busy_cycles", "idle_cycles")
        )
        utilisation_valid = utilisation_valid and (
            _finite_nonnegative(row.get("utilisation"))
            and row.get("utilisation", 0) <= 1
            and _strict_int(total_cycles, minimum=1)
            and row.get("busy_cycles", 0) <= total_cycles
            and row.get("busy_cycles", 0) + row.get("idle_cycles", 0)
            == total_cycles
            and math.isclose(
                float(row.get("utilisation", -1)),
                float(row.get("busy_cycles", 0)) / float(total_cycles),
                rel_tol=1e-6,
                abs_tol=1e-6,
            )
        )
        engine_activity = engine_activity or (
            _finite_nonnegative(row.get("operations"))
            and _finite_nonnegative(row.get("busy_cycles"))
            and (row.get("operations", 0) > 0 or row.get("busy_cycles", 0) > 0)
        )
    utilisation_valid = utilisation_valid and engine_activity

    stall_names = (
        "stall_cycles",
        "queue_stall_cycles",
        "wait_stall_cycles",
        "memory_stall_cycles",
        "tile_pipeline_stall_cycles",
    )
    stalls_valid = all(
        name in timing and _strict_int(timing.get(name), minimum=0)
        for name in stall_names
    ) and all(
        timing_counters.get(f"latency.{name}", 0) == timing.get(name)
        for name in stall_names
    )
    stalls_valid = stalls_valid and timing.get("stall_cycles") == (
        timing.get("queue_stall_cycles", 0) + timing.get("wait_stall_cycles", 0)
    )

    boundary = _mapping(source.get("comparison_boundary"))
    registered_contract_path = CONTRACT_PATHS.get(str(contract.get("comparison_id")))
    contract_path = (
        repo / registered_contract_path if registered_contract_path is not None else None
    )
    try:
        source_boundary_validation = validate_boundary(
            boundary,
            repo=repo,
            cycle_inputs=source_inputs,
            expected_contract=_contract_document(contract),
            expected_contract_path=contract_path,
        )
        boundary_valid = source_boundary_validation.get("valid") is True
    except (BoundaryError, OSError, TypeError, ValueError, json.JSONDecodeError):
        boundary_valid = False

    cost = _mapping(source_inputs.get("cost_table"))
    aggregate_cost = _mapping(aggregate_inputs.get("cost_table"))
    identity_valid = (
        source_inputs.get("model_id") == aggregate_inputs.get("model_id")
        and source_inputs.get("model_digest") == aggregate_inputs.get("model_digest")
        and source_inputs.get("backend") == aggregate_inputs.get("backend")
        and source_inputs.get("target_id") == aggregate_inputs.get("target_id")
        and _normalise_topology(source_inputs.get("topology_class"))
        == _normalise_topology(aggregate_inputs.get("topology_class"))
        and _strict_int(source_inputs.get("node_count"), minimum=1)
        and source_inputs.get("node_count") == aggregate_inputs.get("node_count")
        and source_inputs.get("deployment_digest")
        == aggregate_inputs.get("deployment_digest")
        and source_inputs.get("capability_digest")
        == aggregate_inputs.get("capability_digest")
        and source_inputs.get("capability_technology_view")
        == aggregate_inputs.get("capability_technology_view")
        and source_inputs.get("workload") == aggregate_inputs.get("workload")
        and cost.get("sha256") == aggregate_cost.get("sha256")
        and cost.get("cost_table_id") == aggregate_cost.get("cost_table_id")
        and cost.get("technology_view") == aggregate_cost.get("technology_view")
    )
    counts = _mapping(provenance.get("counts"))
    source_provenance_valid = (
        provenance.get("class") in {"characterized", "datasheet", "assumed"}
        and bool(counts)
        and all(_strict_int(value, minimum=0) for value in counts.values())
        and bool(_mapping(provenance.get("parameters")))
    )
    producer_source_valid = False
    try:
        producer_path = (repo / CYCLE_PRODUCER).resolve()
        producer_source_valid = (
            set(producer)
            == {"schema", "tool", "source_sha256", "evidence_class"}
            and producer.get("schema") == CYCLE_PRODUCER_SCHEMA
            and producer.get("tool") == CYCLE_PRODUCER
            and producer.get("evidence_class") == CYCLE_PRODUCER_EVIDENCE_CLASS
            and producer_path.relative_to(repo.resolve()).as_posix()
            == CYCLE_PRODUCER
            and producer_path.is_file()
            and _sha256(producer_path) == producer.get("source_sha256")
        )
    except (OSError, TypeError, ValueError):
        producer_source_valid = False
    source_execution_valid = (
        execution.get("status") == "SUCCESS"
        and execution.get("trap_class") == "NONE"
        and _strict_int(execution.get("transactions"), minimum=1)
        and execution.get("transactions") == 1
        and execution.get("produced_tokens") == functional_step.get("produced_tokens")
        and _mapping(source.get("schedule_audit")).get("complete") is True
        and _mapping(source.get("schedule_audit")).get("findings") == []
        and source.get("gaps") == []
        and _mapping(source.get("functional_agreement")).get("checked") is True
        and _mapping(source.get("functional_agreement")).get("agrees") is True
    )
    return {
        "reference_complete": set(reference) == {"path", "sha256", "schema"}
        and reference.get("schema") == CYCLE_SCHEMA,
        "source_exact": bool(source)
        and source.get("schema") == CYCLE_SCHEMA
        and source_sha256 == reference.get("sha256"),
        "boundary_source_valid": boundary_valid,
        "target_inputs_exact": identity_valid,
        "request_exact": source_inputs.get("request") == request,
        "execution_exact": source_execution_valid,
        "producer_source_valid": producer_source_valid,
        "provenance_source_valid": source_provenance_valid,
        "timing_valid": timing_valid,
        "throughput_valid": throughput_valid,
        "counters_valid": counters_valid,
        "memory_valid": memory_valid,
        "utilisation_valid": utilisation_valid,
        "stalls_valid": stalls_valid,
    }


def _request_trajectory_checks(
    evidence: Mapping[str, Any],
    contract: Mapping[str, Any],
    boundary: Mapping[str, Any],
    aggregate_inputs: Mapping[str, Any],
    per_step: Sequence[Mapping[str, Any]],
    generated_count: object,
    *,
    repo: Path,
) -> tuple[dict[str, bool], dict[str, Any]]:
    """Re-derive every governed request and reopen its timing measurement."""

    trajectory = _mapping(evidence.get("request_trajectory"))
    rows_value = trajectory.get("transactions")
    rows = rows_value if isinstance(rows_value, list) else []
    execution = _mapping(contract.get("execution"))
    workload = _mapping(contract.get("workload"))
    prompt_count = workload.get("prompt_token_count")
    generation = _mapping(execution.get("generation"))
    max_new_tokens = generation.get("max_new_tokens")
    batch = execution.get("batch")

    try:
        deployment_path = boundary.get("deployment", {}).get("path")
        if not isinstance(deployment_path, str) or Path(deployment_path).is_absolute():
            raise ValueError("noncanonical deployment path")
        deployment_root = (repo / deployment_path).resolve()
        if deployment_root.relative_to(repo.resolve()).as_posix() != deployment_path:
            raise ValueError("aliased deployment path")
        deployment = Deployment.read(deployment_root)
        deployment_loaded = True
    except (AttributeError, OSError, TypeError, ValueError, json.JSONDecodeError):
        deployment = None
        deployment_loaded = False

    shape_valid = (
        set(trajectory) == {"schema", "sha256", "transactions"}
        and trajectory.get("schema") == REQUEST_TRAJECTORY_SCHEMA
        and bool(rows)
        and _strict_int(generated_count, minimum=1)
        and len(rows) == generated_count == len(per_step)
    )
    row_shape_valid = shape_valid
    transaction_phase_exact = shape_valid
    request_shape_valid = shape_valid
    entrypoints_exact = shape_valid and deployment_loaded
    generation_policies_exact = shape_valid and deployment_loaded
    dynamic_symbols_exact = shape_valid
    governed_counts_valid = (
        _strict_int(prompt_count, minimum=1)
        and _strict_int(max_new_tokens, minimum=1)
        and _strict_int(batch, minimum=1)
    )
    safe_prompt_count = prompt_count if _strict_int(prompt_count, minimum=1) else 0
    measurement_checks: list[dict[str, bool]] = []
    measurement_paths: list[str] = []

    for index, row_value in enumerate(rows):
        row = _mapping(row_value)
        step = _mapping(per_step[index]) if index < len(per_step) else {}
        request = _mapping(row.get("request"))
        symbols = _mapping(request.get("symbols"))
        phase = "prefill" if index == 0 else "decode"
        phase_value = int(Phase.PREFILL if index == 0 else Phase.DECODE)
        expected_symbols = {
            "SPAN_TOKENS": safe_prompt_count if index == 0 else 1,
            "POSITION_START": 0 if index == 0 else safe_prompt_count + index - 1,
            "POSITION_END": safe_prompt_count if index == 0 else safe_prompt_count + index,
            "CONTEXT_LENGTH": safe_prompt_count if index == 0 else safe_prompt_count + index,
            "PHASE": phase_value,
            "MAX_NEW_TOKENS": max_new_tokens,
            "BATCH": batch,
            "GENERATION_INDEX": index,
            "SPAN_LAST_INDEX": safe_prompt_count - 1 if index == 0 else 0,
        }
        row_shape_valid = row_shape_valid and set(row) == {
            "transaction_id",
            "phase",
            "request",
            "measurement",
        }
        transaction_phase_exact = transaction_phase_exact and (
            _strict_int(row.get("transaction_id"), minimum=1)
            and row.get("transaction_id") == index + 1
            and _strict_int(step.get("transaction_id"), minimum=1)
            and row.get("transaction_id") == step.get("transaction_id")
            and row.get("phase") == phase == step.get("phase")
        )
        request_checks = validate_governed_request(
            request,
            contract,
            deployment if isinstance(deployment, Deployment) else None,
        )
        request_shape_valid = request_shape_valid and all(
            request_checks.get(name) is True
            for name in ("shape_exact", "scalar_types_strict", "symbol_set_exact")
        )
        dynamic_symbols_exact = dynamic_symbols_exact and governed_counts_valid and (
            request_checks.get("contract_counts_strict") is True
            and request_checks.get("phase_and_generation_index_exact") is True
            and request_checks.get("deployment_symbols_exact") is True
            and request_checks.get("dynamic_symbols_exact") is True
            and all(
                symbols.get(name) == value
                and _strict_int(symbols.get(name), minimum=0)
                for name, value in expected_symbols.items()
            )
        )
        entrypoints_exact = (
            entrypoints_exact and request_checks.get("entrypoint_exact") is True
        )
        generation_policies_exact = (
            generation_policies_exact
            and request_checks.get("generation_policy_exact") is True
        )

        measurement_ref = _mapping(row.get("measurement"))
        measurement, measurement_path, measurement_sha = _read_evidence_source(
            repo, measurement_ref
        )
        measurement_checks.append(
            _measurement_document_checks(
                measurement,
                measurement_ref,
                request,
                step,
                aggregate_inputs,
                contract,
                repo=repo,
                source_sha256=measurement_sha,
            )
        )
        if measurement_path is not None:
            measurement_paths.append(_relative(repo, measurement_path))

    digest = request_trajectory_digest(rows)
    checks = {
        "request_trajectory_schema_and_count_exact": shape_valid,
        "request_trajectory_rows_exact": row_shape_valid,
        "request_trajectory_transactions_and_phases_exact": transaction_phase_exact,
        "request_trajectory_request_shape_exact": request_shape_valid,
        "request_trajectory_entrypoints_exact": entrypoints_exact,
        "request_trajectory_generation_policies_exact": generation_policies_exact,
        "request_trajectory_dynamic_symbols_exact": dynamic_symbols_exact,
        "request_trajectory_digest_exact": (
            trajectory.get("sha256")
            == boundary.get("request_trajectory_sha256")
            == aggregate_inputs.get("request_trajectory_sha256")
            == digest
        ),
        "cycle_measurement_count_exact": bool(rows)
        and len(measurement_checks) == len(rows)
        and len(set(measurement_paths)) == len(rows),
    }
    for name in (
        "reference_complete",
        "source_exact",
        "boundary_source_valid",
        "target_inputs_exact",
        "request_exact",
        "execution_exact",
        "producer_source_valid",
        "provenance_source_valid",
        "timing_valid",
        "throughput_valid",
        "counters_valid",
        "memory_valid",
        "utilisation_valid",
        "stalls_valid",
    ):
        checks[f"cycle_measurement_{name}"] = bool(measurement_checks) and all(
            result.get(name) is True for result in measurement_checks
        )
    return checks, {
        "request_trajectory_sha256": digest,
        "request_transaction_count": len(rows),
        "cycle_measurement_paths": measurement_paths,
    }


def _full_workload_checks(
    evidence: Mapping[str, Any],
    contract: Mapping[str, Any],
    boundary: Mapping[str, Any],
    cycle_inputs: Mapping[str, Any],
    *,
    repo: Path,
) -> tuple[dict[str, bool], dict[str, Any]]:
    """Reopen the accelerator and oracle artifacts; never trust result claims."""

    workload = _mapping(contract.get("workload"))
    model = _mapping(contract.get("model"))
    execution = _mapping(contract.get("execution"))
    generation = _mapping(execution.get("generation"))
    target = _mapping(boundary.get("target"))
    expected_target = _mapping(_mapping(contract.get("targets")).get(target.get("role")))
    functional_ref = _mapping(evidence.get("functional_artifact"))
    oracle_ref = _mapping(evidence.get("external_oracle"))
    functional, functional_path, functional_sha = _read_evidence_source(
        repo, functional_ref
    )
    oracle, oracle_path, oracle_sha = _read_evidence_source(repo, oracle_ref)

    expected_functional_schema = "opentallas.abi3.accelerator_tokens.v1"
    expected_functional_class = "functional_artifact_only"
    expected_oracle_schema = "opentallas.abi3.reference_oracle.v1"
    expected_oracle_class = "external_reference_comparator"
    functional_model = _mapping(functional.get("model"))
    functional_target = _mapping(functional.get("target"))
    functional_workload = _mapping(functional.get("workload"))
    functional_template = _mapping(functional_workload.get("template"))
    functional_execution = _mapping(functional.get("comparison_execution"))
    functional_oracle = _mapping(functional.get("oracle"))
    verification = _mapping(functional.get("verification"))
    required_functional_sources = _required_functional_sources(
        repo, contract.get("comparison_id"), target.get("role")
    )
    functional_source_checks, functional_source_paths = _validate_source_map(
        repo,
        functional.get("source_sha256"),
        required_functional_sources,
    )
    oracle_lock = _mapping(contract.get("external_oracle"))
    oracle_producer = _mapping(oracle_lock.get("producer"))
    oracle_producer_exact = False
    try:
        oracle_producer_path = (repo / str(oracle_producer.get("tool"))).resolve()
        oracle_producer_path.relative_to(repo.resolve())
        oracle_producer_exact = (
            oracle_producer.get("tool")
            == ORACLE_PRODUCER_PATHS.get(str(contract.get("comparison_id")))
            and oracle_producer_path.is_file()
            and _sha256(oracle_producer_path)
            == oracle_producer.get("source_sha256")
        )
    except (OSError, TypeError, ValueError):
        pass

    try:
        workload_path = repo / str(workload.get("path"))
        source_workload = _load_json(workload_path)
        source_workload = _mapping(source_workload)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        source_workload = {}
    vocabulary_size = generation.get("vocabulary_size")
    prompt_tokens = _integer_tokens(source_workload.get("token_ids"), vocabulary_size)
    generated = _integer_tokens(functional.get("generated_token_ids"), vocabulary_size)
    oracle_results = _mapping(oracle.get("results"))
    oracle_result = _mapping(oracle_results.get(workload.get("workload_id")))
    oracle_tokens = _integer_tokens(
        oracle_result.get("generated_token_ids"), vocabulary_size
    )
    per_step = functional.get("per_step")
    per_step = per_step if isinstance(per_step, list) else []
    generated_count = functional.get("generated_token_count")
    cap = generation.get("max_new_tokens")
    raw_eos = generation.get("eos_token_ids")
    eos = {
        token
        for token in raw_eos
        if isinstance(token, int) and not isinstance(token, bool)
    } if isinstance(raw_eos, list) else set()
    stop_reason = functional.get("stop_reason")
    comparison_workload_sha256 = comparison_workload_digest(contract)
    eos_terminal = (
        stop_reason == "eos"
        and bool(generated)
        and generated[-1] in eos
        and not any(token in eos for token in generated[:-1])
    )
    cap_terminal = (
        stop_reason == "max_new_tokens"
        and isinstance(cap, int)
        and not isinstance(cap, bool)
        and generated_count == cap
        and bool(generated)
        and not any(token in eos for token in generated)
    )
    prompt_digest = (
        _semantic_digest(prompt_tokens) if prompt_tokens is not None else None
    )
    generated_digest = (
        _semantic_digest(generated) if generated is not None else None
    )
    step_tokens_exact = generated is not None and len(per_step) == len(generated) and all(
        isinstance(step, Mapping)
        and _strict_int(step.get("step"), minimum=0)
        and step.get("step") == index
        and isinstance(step.get("produced_tokens"), list)
        and len(step.get("produced_tokens")) == 1
        and _strict_int(step.get("produced_tokens")[0], minimum=0)
        and step.get("produced_tokens") == [generated[index]]
        and _strict_int(step.get("final_token_id"), minimum=0)
        and step.get("final_token_id") == generated[index]
        for index, step in enumerate(per_step)
    )
    step_success = bool(per_step) and all(
        isinstance(step, Mapping)
        and step.get("status") == "SUCCESS"
        and step.get("trap") == "NONE"
        for step in per_step
    )
    step_phases = [
        step.get("phase") if isinstance(step, Mapping) else None for step in per_step
    ]
    phases_exact = (
        bool(step_phases)
        and step_phases[0] == "prefill"
        and all(phase == "decode" for phase in step_phases[1:])
        and execution.get("phases") == ["prefill", "decode"]
    )
    transaction_ids = [
        step.get("transaction_id") if isinstance(step, Mapping) else None
        for step in per_step
    ]
    transactions_exact = (
        bool(transaction_ids)
        and all(_strict_int(value, minimum=1) for value in transaction_ids)
        and transaction_ids == list(range(1, len(transaction_ids) + 1))
    )
    expected_oracle_path = (
        _relative(repo, oracle_path) if oracle_path is not None else None
    )
    checks = {
        "full_workload_scope": evidence.get("scope") == "full_workload",
        "functional_artifact_reference_complete": (
            functional_ref.get("path") is not None
            and functional_ref.get("sha256") is not None
            and functional_ref.get("schema") == expected_functional_schema
            and functional_ref.get("evidence_class") == expected_functional_class
        ),
        "functional_artifact_source_exact": bool(functional)
        and functional_sha == functional_ref.get("sha256"),
        "functional_artifact_schema_exact": functional.get("schema")
        == functional_ref.get("schema")
        == expected_functional_schema,
        "functional_artifact_evidence_class_exact": functional.get("evidence_class")
        == functional_ref.get("evidence_class")
        == expected_functional_class,
        "functional_producer_exact": functional.get("tool")
        == FUNCTIONAL_PRODUCER,
        "functional_backend_exact": functional_target.get("backend")
        == expected_target.get("backend"),
        "functional_source_map_nonempty": functional_source_checks["nonempty"],
        "functional_source_map_well_formed": functional_source_checks[
            "well_formed"
        ],
        "functional_source_map_required": functional_source_checks["required"],
        "functional_source_map_exact": functional_source_checks["exact"],
        "functional_artifact_status_pass": functional.get("status") == "pass"
        and functional.get("failure") in (None, "")
        and verification.get("admitted") is True
        and functional.get("token_legitimacy_problems") == [],
        "functional_model_identity_exact": (
            functional_model.get("model_id") == model.get("model_id")
            and functional_model.get("graph_id") == model.get("graph_id")
            and functional_model.get("numeric_profile") == model.get("numeric_profile")
        ),
        "functional_target_identity_exact": (
            functional_target.get("role") == target.get("role")
            and functional_target.get("backend") == target.get("backend")
            == expected_target.get("backend")
            and functional_target.get("target_id") == target.get("target_id")
            == expected_target.get("target_id")
            and functional_target.get("storage_class") == target.get("storage_class")
            == expected_target.get("storage_class")
            and _strict_int(functional_target.get("topology_class"), minimum=0)
            and functional_target.get("topology_class")
            == target.get("topology_class")
            == expected_target.get("topology_class")
            and _strict_int(functional_target.get("node_count"), minimum=1)
            and functional_target.get("node_count") == target.get("node_count")
            == expected_target.get("node_count")
            and functional_target.get("technology_view")
            == _mapping(contract.get("policy")).get("technology_view")
        ),
        "functional_target_sources_exact": (
            functional_target.get("deployment_digest")
            == _mapping(expected_target.get("deployment")).get("digest")
            == _mapping(boundary.get("deployment")).get("sha256")
            and functional_target.get("capability_digest")
            == _mapping(expected_target.get("capability")).get("digest")
            == _mapping(boundary.get("capability")).get("sha256")
        ),
        "functional_workload_identity_exact": (
            functional.get("comparison_workload_sha256")
            == comparison_workload_sha256
            and functional_workload.get("workload_id")
            == workload.get("workload_id")
            and functional_workload.get("path") == workload.get("path")
            and functional_workload.get("source_sha256")
            == workload.get("source_sha256")
            and functional_workload.get("workload_digest") == workload.get("digest")
            and _strict_int(
                functional_workload.get("prompt_token_count"), minimum=1
            )
            and functional_workload.get("prompt_token_count")
            == workload.get("prompt_token_count")
            and _strict_int(
                functional_workload.get("max_new_tokens"), minimum=1
            )
            and functional_workload.get("max_new_tokens")
            == workload.get("max_new_tokens")
            and functional_workload.get("index_path") == workload.get("index_path")
            and functional_workload.get("index_source_sha256")
            == workload.get("index_source_sha256")
            and functional_workload.get("tokenizer_sha256")
            == workload.get("tokenizer_sha256")
            and functional_workload.get("rendered_text_sha256")
            == workload.get("rendered_text_sha256")
            and functional_template == _mapping(workload.get("template"))
        ),
        "functional_input_tokens_exact": (
            prompt_tokens is not None
            and functional_workload.get("prompt_token_ids") == prompt_tokens
            and functional_workload.get("prompt_token_ids_sha256") == prompt_digest
            and len(prompt_tokens) == workload.get("prompt_token_count")
        ),
        "functional_execution_contract_exact": functional_execution
        == {
            "scope": "full_workload",
            "phases": execution.get("phases"),
            "batch": execution.get("batch"),
            "concurrency": execution.get("concurrency"),
        }
        and _strict_int(functional_execution.get("batch"), minimum=1)
        and _strict_int(functional_execution.get("concurrency"), minimum=1),
        "generated_token_ids_valid": generated is not None and bool(generated),
        "generated_token_count_exact": (
            generated is not None
            and _strict_int(generated_count, minimum=1)
            and generated_count == len(generated)
        ),
        "generated_token_count_within_cap": (
            _strict_int(generated_count, minimum=1)
            and _strict_int(cap, minimum=1)
            and 0 < generated_count <= cap
        ),
        "per_step_tokens_exact": step_tokens_exact,
        "per_step_success": step_success,
        "per_step_phases_exact": phases_exact,
        "per_step_transactions_strict": transactions_exact,
        "terminal_reason_exact": eos_terminal or cap_terminal,
        "no_post_eos_transactions": generated is not None
        and not any(token in eos for token in generated[:-1]),
        "external_oracle_reference_complete": (
            oracle_ref.get("path") is not None
            and oracle_ref.get("sha256") is not None
            and oracle_ref.get("schema") == expected_oracle_schema
            and oracle_ref.get("evidence_class") == expected_oracle_class
        ),
        "external_oracle_contract_locked": (
            oracle_lock.get("status") == "locked"
            and isinstance(oracle_lock.get("source_sha256"), str)
            and isinstance(oracle_producer.get("source_sha256"), str)
        ),
        "external_oracle_reference_contract_exact": (
            oracle_ref.get("path") == oracle_lock.get("path")
            and oracle_ref.get("sha256") == oracle_lock.get("source_sha256")
            and oracle_ref.get("schema") == oracle_lock.get("schema")
            and oracle_ref.get("evidence_class")
            == oracle_lock.get("evidence_class")
        ),
        "external_oracle_producer_source_exact": oracle_producer_exact,
        "external_oracle_source_exact": bool(oracle)
        and oracle_sha
        == oracle_ref.get("sha256")
        == oracle_lock.get("source_sha256"),
        "external_oracle_schema_exact": oracle.get("schema")
        == oracle_ref.get("schema")
        == oracle_lock.get("schema")
        == expected_oracle_schema,
        "external_oracle_evidence_class_exact": oracle.get("evidence_class")
        == oracle_ref.get("evidence_class")
        == oracle_lock.get("evidence_class")
        == expected_oracle_class,
        "external_oracle_model_identity_exact": (
            oracle.get("model_id") == model.get("model_id")
            and oracle.get("tokenizer_sha256") == workload.get("tokenizer_sha256")
        ),
        "external_oracle_workload_identity_exact": (
            oracle_result.get("workload_digest") == workload.get("digest")
            and _strict_int(oracle_result.get("prompt_token_count"), minimum=1)
            and oracle_result.get("prompt_token_count")
            == workload.get("prompt_token_count")
        ),
        "external_oracle_tokens_exact": (
            generated is not None
            and oracle_tokens is not None
            and oracle_tokens == generated
            and _strict_int(
                oracle_result.get("generated_token_count"), minimum=1
            )
            and oracle_result.get("generated_token_count") == len(generated)
            and oracle_result.get("stop_reason") == stop_reason
        ),
        "functional_oracle_link_exact": (
            functional_oracle.get("artifact")
            == expected_oracle_path
            == oracle_lock.get("path")
            and functional_oracle.get("artifact_sha256") == oracle_sha
            == oracle_ref.get("sha256")
            == oracle_lock.get("source_sha256")
            and functional_oracle.get("evidence_class") == expected_oracle_class
        ),
        "functional_oracle_agreement_complete": (
            generated is not None
            and functional_oracle.get("agreement") is True
            and _strict_int(functional_oracle.get("compared_tokens"), minimum=1)
            and functional_oracle.get("compared_tokens") == len(generated)
            and _strict_int(functional_oracle.get("oracle_token_count"), minimum=1)
            and functional_oracle.get("oracle_token_count") == len(generated)
            and functional_oracle.get("first_divergence_index") is None
            and functional_oracle.get("generated_token_ids") == generated
        ),
    }
    trajectory_checks, trajectory_evidence = _request_trajectory_checks(
        evidence,
        contract,
        boundary,
        cycle_inputs,
        per_step,
        generated_count,
        repo=repo,
    )
    checks.update(trajectory_checks)
    # Correctness is cycle-linked: a functional artifact cannot close the
    # comparison if any referenced transaction measurement is missing,
    # malformed, or produced by an unbound tool/source revision.
    functional_evidence_valid = all(checks.values())
    return checks, {
        "functional_artifact_path": (
            _relative(repo, functional_path) if functional_path is not None else None
        ),
        "functional_artifact_sha256": functional_sha,
        "functional_source_paths": functional_source_paths,
        "external_oracle_path": expected_oracle_path,
        "external_oracle_producer_path": oracle_producer.get("tool"),
        "external_oracle_sha256": oracle_sha,
        "generated_token_count": generated_count,
        "generated_token_sequence_sha256": generated_digest,
        "functional_evidence_valid": functional_evidence_valid,
        **trajectory_evidence,
    }


def assess_cycle_document(
    body: Mapping[str, Any],
    path: str,
    *,
    sha256: str = "",
    contract: Mapping[str, Any] | None = None,
    repo: Path = REPO,
    required_view: str = REQUIRED_VIEW,
) -> dict[str, Any] | None:
    """Return the strict W11.2 admission decision for one cycle result."""
    if body.get("schema") != CYCLE_SCHEMA:
        return None
    inputs = _mapping(body.get("inputs"))
    cost = _mapping(inputs.get("cost_table"))
    workload = _mapping(inputs.get("workload"))
    agreement = _mapping(body.get("functional_agreement"))
    execution = _mapping(body.get("execution"))
    schedule = _mapping(body.get("schedule_audit"))
    gaps = body.get("gaps")
    boundary = _mapping(body.get("comparison_boundary"))
    boundary_target = _mapping(boundary.get("target"))
    boundary_workload = _mapping(boundary.get("workload"))
    contract_document = _contract_document(contract)
    contract_path = (
        repo / str(contract.get("contract_path"))
        if contract is not None and contract.get("contract_path")
        else None
    )
    boundary_validation = validate_boundary(
        boundary,
        repo=repo,
        cycle_inputs=inputs,
        expected_contract=contract_document if contract is not None else None,
        expected_contract_path=contract_path,
    )
    workload_execution = _mapping(body.get("workload_execution"))
    target_role = boundary_target.get("role")
    raw_topology = inputs.get("topology_class")
    topology = _normalise_topology(raw_topology)
    expected_target = _mapping(
        _mapping(contract_document.get("targets")).get(target_role)
    )
    expected_topology = expected_target.get("topology_class")
    expected_nodes = expected_target.get("node_count")
    contract_digest = contract.get("contract_sha256") if contract is not None else None
    policy = _mapping(contract_document.get("policy"))
    contract_known = (
        contract is not None
        and contract_document.get("comparison_id") == contract.get("comparison_id")
    )
    source_valid = contract is not None and (
        contract.get("contract_source_valid", contract.get("source_valid")) is True
    )
    target_sources_ready = contract is not None and (
        contract.get("contract_ready") is True
    )
    workload_checks, workload_evidence = _full_workload_checks(
        workload_execution,
        contract_document,
        boundary,
        inputs,
        repo=repo,
    )
    checks = {
        "acceptance_contract_known": contract_known,
        "acceptance_contract_source_valid": source_valid,
        "acceptance_contract_target_sources_ready": target_sources_ready,
        "comparison_boundary_source_valid": boundary_validation["valid"],
        "comparison_id_exact": contract_known
        and boundary.get("comparison_id") == contract_document.get("comparison_id"),
        "comparison_contract_digest_exact": (
            bool(contract_digest)
            and _mapping(boundary.get("comparison_contract")).get("sha256")
            == contract_digest
            and boundary.get("comparison_sha256") == contract_digest
            and inputs.get("comparison_contract_digest") == contract_digest
            and inputs.get("comparison_digest") == contract_digest
        ),
        "comparison_execution_scope_exact": (
            boundary.get("execution_scope") == "full_workload"
            and inputs.get("comparison_execution_scope") == "full_workload"
        ),
        "comparison_workload_digest_exact": (
            boundary.get("comparison_workload_sha256")
            == inputs.get("comparison_workload_sha256")
            == comparison_workload_digest(contract_document)
        ),
        "model_identity_exact": (
            boundary.get("model_id")
            == inputs.get("model_id")
            == _mapping(contract_document.get("model")).get("model_id")
            and boundary.get("model_digest")
            == inputs.get("model_digest")
            == _mapping(contract_document.get("model")).get("graph_id")
            and boundary.get("numeric_profile")
            == _mapping(contract_document.get("model")).get("numeric_profile")
        ),
        "workload_id_exact": boundary_workload.get("workload_id")
        == _mapping(contract_document.get("workload")).get("workload_id"),
        "workload_digest_exact": (
            boundary_workload.get("workload_digest")
            == _mapping(contract_document.get("workload")).get("digest")
            == workload.get("workload_digest")
        ),
        "workload_source_exact": (
            boundary_workload.get("path")
            == _mapping(contract_document.get("workload")).get("path")
            and boundary_workload.get("sha256")
            == _mapping(contract_document.get("workload")).get("source_sha256")
        ),
        "cost_table_view_exact": cost.get("technology_view")
        == policy.get("technology_view")
        == required_view,
        "capability_view_exact": inputs.get("capability_technology_view")
        == policy.get("technology_view")
        == required_view,
        "target_role_exact": target_role in TARGET_ROLE_STORAGE
        and expected_target.get("role") == target_role
        and _target_role(boundary_target, contract_document) == target_role,
        "target_backend_exact": inputs.get("backend")
        == boundary_target.get("backend")
        == expected_target.get("backend"),
        "target_id_exact": inputs.get("target_id")
        == boundary_target.get("target_id")
        == expected_target.get("target_id"),
        "target_storage_class_exact": boundary_target.get("storage_class")
        == expected_target.get("storage_class"),
        "topology_class_exact": topology is not None
        and _strict_int(boundary_target.get("topology_class"), minimum=0)
        and topology == expected_topology == boundary_target.get("topology_class"),
        "node_count_exact": (
            _strict_int(inputs.get("node_count"), minimum=1)
            and inputs.get("node_count") == expected_nodes
            == boundary_target.get("node_count")
        ),
        "execution_status_success": execution.get("status") == "SUCCESS",
        "execution_trap_none": execution.get("trap_class") == "NONE",
        "execution_transactions_complete": _strict_int(
            workload_evidence.get("request_transaction_count"), minimum=1
        )
        and _strict_int(execution.get("transactions"), minimum=1)
        and execution.get("transactions")
        == workload_evidence.get("request_transaction_count"),
        "execution_transactions_match_full_workload": (
            _strict_int(execution.get("transactions"), minimum=1)
            and execution.get("transactions")
            == workload_evidence.get("generated_token_count")
        ),
        "schedule_audit_complete": schedule.get("complete") is True
        and schedule.get("findings") == [],
        "contract_gaps_empty": isinstance(gaps, list) and not gaps,
        "functional_counter_agreement": agreement.get("checked") is True
        and agreement.get("agrees") is True,
        **workload_checks,
    }
    failed = [name for name, value in checks.items() if not value]
    functional_binding_checks = (
        "acceptance_contract_known",
        "acceptance_contract_source_valid",
        "acceptance_contract_target_sources_ready",
        "comparison_boundary_source_valid",
        "comparison_id_exact",
        "comparison_contract_digest_exact",
        "comparison_execution_scope_exact",
        "comparison_workload_digest_exact",
        "model_identity_exact",
        "workload_id_exact",
        "workload_digest_exact",
        "workload_source_exact",
        "target_role_exact",
        "target_backend_exact",
        "target_id_exact",
        "target_storage_class_exact",
        "topology_class_exact",
        "node_count_exact",
    )
    functional_evidence_admissible = (
        workload_evidence.get("functional_evidence_valid") is True
        and all(checks[name] for name in functional_binding_checks)
    )
    return {
        "path": path,
        "sha256": sha256,
        "backend": inputs.get("backend"),
        "target_id": inputs.get("target_id"),
        "role": target_role,
        "topology_class": topology,
        "topology_class_raw": raw_topology,
        "node_count": inputs.get("node_count"),
        "cost_table_id": cost.get("cost_table_id"),
        "cost_table_technology_view": cost.get("technology_view"),
        "capability_technology_view": inputs.get("capability_technology_view"),
        "workload_id": workload.get("workload_id"),
        "workload_digest": workload.get("workload_digest"),
        "comparison_id": boundary.get("comparison_id"),
        "model_digest": boundary.get("model_digest"),
        "comparison_digest": boundary.get("comparison_sha256"),
        "comparison_contract_digest": inputs.get("comparison_contract_digest"),
        "comparison_workload_sha256": inputs.get("comparison_workload_sha256"),
        "comparison_execution_scope": inputs.get("comparison_execution_scope"),
        "comparison_boundary_digest": inputs.get("comparison_boundary_digest"),
        "deployment_digest": inputs.get("deployment_digest"),
        "generated_token_sequence_sha256": workload_evidence.get(
            "generated_token_sequence_sha256"
        ),
        "external_oracle_sha256": workload_evidence.get("external_oracle_sha256"),
        "functional_artifact_path": workload_evidence.get("functional_artifact_path"),
        "functional_artifact_sha256": workload_evidence.get(
            "functional_artifact_sha256"
        ),
        "functional_source_paths": workload_evidence.get(
            "functional_source_paths", []
        ),
        "external_oracle_path": workload_evidence.get("external_oracle_path"),
        "external_oracle_producer_path": workload_evidence.get(
            "external_oracle_producer_path"
        ),
        "request_trajectory_sha256": workload_evidence.get(
            "request_trajectory_sha256"
        ),
        "cycle_measurement_paths": workload_evidence.get(
            "cycle_measurement_paths", []
        ),
        "functional_evidence_admissible": functional_evidence_admissible,
        "boundary_source_validation": boundary_validation,
        "workload_execution": dict(workload_execution),
        "execution_status": execution.get("status"),
        "trap_class": execution.get("trap_class"),
        "schedule_audit_complete": schedule.get("complete"),
        "contract_gap_count": len(gaps) if isinstance(gaps, list) else None,
        "provenance_class": body.get("provenance", {}).get("class"),
        "checks": checks,
        "failed_checks": failed,
        "admissible": not failed,
    }


def _cycle_inventory(
    repo: Path, contracts: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], set[Path]]:
    inspected: set[Path] = set()
    candidates: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    root = repo / "results" / "abi3"
    contracts_by_id = {str(item["comparison_id"]): item for item in contracts}
    for path in sorted(root.rglob("*.json")) if root.exists() else []:
        try:
            body = _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(body, Mapping):
            continue
        boundary = _mapping(body.get("comparison_boundary"))
        contract = contracts_by_id.get(str(boundary.get("comparison_id", "")))
        assessed = assess_cycle_document(
            body,
            _relative(repo, path),
            sha256=_sha256(path),
            contract=contract,
            repo=repo,
        )
        if assessed is not None:
            candidates.append(assessed)
            inspected.add(path)
            for source_key in ("functional_artifact_path", "external_oracle_path"):
                source = assessed.get(source_key)
                if isinstance(source, str) and source:
                    source_path = repo / source
                    if source_path.is_file():
                        inspected.add(source_path)
            for source in assessed.get("functional_source_paths", []):
                source_path = repo / str(source)
                if source_path.is_file():
                    inspected.add(source_path)
            for source in assessed.get("cycle_measurement_paths", []):
                source_path = repo / str(source)
                if source_path.is_file():
                    inspected.add(source_path)
            oracle_producer = assessed.get("external_oracle_producer_path")
            if isinstance(oracle_producer, str) and oracle_producer:
                source_path = repo / oracle_producer
                if source_path.is_file():
                    inspected.add(source_path)
        elif body.get("schema") == "opentallas.abi3.cycle_sweep.v1":
            diagnostics.append(
                {
                    **_identity(repo, path),
                    "schema": body.get("schema"),
                    "admitted": False,
                    "reason": "diagnostic multi-table sweep is not a target pair",
                }
            )
            inspected.add(path)

    pair_results: dict[str, Any] = {}
    for contract in contracts:
        exact = [
            item
            for item in candidates
            if item["admissible"]
            and item["comparison_id"] == contract["comparison_id"]
            and item["comparison_contract_digest"]
            == contract.get("contract_sha256")
        ]
        matched = None
        first_role, second_role = contract_target_roles(contract.get("targets"))
        sides = {
            role: [item for item in exact if item["role"] == role]
            for role in (first_role, second_role)
        }
        if len(sides[first_role]) == 1 and len(sides[second_role]) == 1:
            left = sides[first_role][0]
            right = sides[second_role][0]
            if (
                left["comparison_digest"] == right["comparison_digest"]
                == contract.get("contract_sha256")
                and left["model_digest"] == right["model_digest"]
                and left["comparison_workload_sha256"]
                == right["comparison_workload_sha256"]
                == contract.get("comparison_workload_sha256")
                and left["target_id"] != right["target_id"]
                and left["deployment_digest"] != right["deployment_digest"]
                and left["comparison_boundary_digest"]
                != right["comparison_boundary_digest"]
                and left["generated_token_sequence_sha256"]
                == right["generated_token_sequence_sha256"]
                and left["external_oracle_sha256"]
                == right["external_oracle_sha256"]
                and bool(left["request_trajectory_sha256"])
                and left["request_trajectory_sha256"]
                == right["request_trajectory_sha256"]
            ):
                matched = {first_role: left["path"], second_role: right["path"]}

        functional_exact = [
            item
            for item in candidates
            if item["functional_evidence_admissible"]
            and item["comparison_id"] == contract["comparison_id"]
            and item["comparison_contract_digest"] == contract.get("contract_sha256")
            and item["checks"].get("request_trajectory_schema_and_count_exact") is True
            and item["checks"].get("request_trajectory_rows_exact") is True
            and item["checks"].get(
                "request_trajectory_transactions_and_phases_exact"
            )
            is True
            and item["checks"].get("request_trajectory_request_shape_exact") is True
            and item["checks"].get("request_trajectory_entrypoints_exact") is True
            and item["checks"].get(
                "request_trajectory_generation_policies_exact"
            )
            is True
            and item["checks"].get("request_trajectory_dynamic_symbols_exact") is True
            and item["checks"].get("request_trajectory_digest_exact") is True
        ]
        functional_sides = {
            role: [item for item in functional_exact if item["role"] == role]
            for role in (first_role, second_role)
        }
        functional_matched = None
        if (
            len(functional_sides[first_role]) == 1
            and len(functional_sides[second_role]) == 1
        ):
            left = functional_sides[first_role][0]
            right = functional_sides[second_role][0]
            if (
                left["comparison_digest"] == right["comparison_digest"]
                == contract.get("contract_sha256")
                and left["model_digest"] == right["model_digest"]
                and left["comparison_workload_sha256"]
                == right["comparison_workload_sha256"]
                == contract.get("comparison_workload_sha256")
                and left["target_id"] != right["target_id"]
                and left["deployment_digest"] != right["deployment_digest"]
                and left["generated_token_sequence_sha256"]
                == right["generated_token_sequence_sha256"]
                and left["external_oracle_sha256"]
                == right["external_oracle_sha256"]
                and bool(left["request_trajectory_sha256"])
                and left["request_trajectory_sha256"]
                == right["request_trajectory_sha256"]
            ):
                functional_matched = {
                    first_role: left["path"],
                    second_role: right["path"],
                }
        pair_results[str(contract["comparison_id"])] = {
            "workload_id": contract["workload_id"],
            "comparison_contract_digest": contract.get("contract_sha256"),
            "admissible_candidate_count": len(exact),
            "admissible_candidate_counts": {
                role: len(items) for role, items in sides.items()
            },
            "matched_pair": matched,
            "ready": bool(matched),
            "strict_functional_candidate_count": len(functional_exact),
            "strict_functional_candidate_counts": {
                role: len(items) for role, items in functional_sides.items()
            },
            "strict_functional_matched_pair": functional_matched,
            "functional_ready": bool(functional_matched),
        }

    return (
        {
            "admission_rule": {
                "required_cost_table_view": REQUIRED_VIEW,
                "required_capability_view": REQUIRED_VIEW,
                "required_bindings": [
                    "inputs.workload.workload_id",
                    "inputs.workload.workload_digest",
                    "inputs.model_digest (authoritative Kernel IR graph identity)",
                    "comparison_boundary (source-revalidated v1 object)",
                    "inputs.comparison_contract_digest (shared pair identity)",
                    "inputs.comparison_execution_scope=full_workload",
                    "inputs.comparison_boundary_digest",
                    "inputs.topology_class",
                    "inputs.node_count",
                    "workload_execution full input digest/count and phases",
                    "tools/run_accelerator_tokens.py functional producer identity",
                    "complete rehashed runtime/backend functional source map",
                    "contract-locked external reference-oracle path and SHA",
                    "contract-locked external oracle producer source SHA",
                    "artifact-derived exact batch/concurrency and per-step phases",
                    "artifact-derived terminal EOS-or-cap and no post-EOS proof",
                    "matching generated-token and oracle digests on both "
                    "sides of the contract's target pair",
                    "execution.status=SUCCESS",
                    "execution.trap_class=NONE",
                    "execution.transactions=inputs.request.transactions",
                    "schedule_audit.complete=true with no findings",
                    "gaps=[]",
                    "functional_agreement.checked",
                    "functional_agreement.agrees",
                ],
                "note": (
                    "Each target-specific boundary binds the governed workload, "
                    "deployment, capability, topology/node count, and exact target cost "
                    "policy. The authoritative contract digest is the complete shared "
                    "pair identity. Full workload consumption and terminal generation "
                    "are rechecked independently; request transaction counts alone are "
                    "never workload proof."
                ),
            },
            "cycle_results": candidates,
            "admissible_cycle_result_count": sum(
                1 for item in candidates if item["admissible"]
            ),
            "excluded_cycle_result_count": sum(
                1 for item in candidates if not item["admissible"]
            ),
            "diagnostic_artifacts": diagnostics,
            "comparisons": pair_results,
        },
        inspected,
    )


def _physical_inventory(repo: Path) -> tuple[dict[str, Any], set[Path]]:
    inspected: set[Path] = set()
    lock_path = repo / "configs" / "pdk" / "asap7_physical_lock.json"
    lock = _load_json(lock_path) if lock_path.is_file() else {}
    if lock_path.is_file():
        inspected.add(lock_path)
    blocks: list[dict[str, Any]] = []
    root = repo / "results" / "physical_abi3" / "asap7"
    family_map = {
        "add_bf16_sram_engine": "vector",
        "ot_ta_matmul_bf16_sram_engine": "tensor",
        "reduction_s8_g2": "reduction",
    }
    covered: set[str] = set()
    for path in sorted(root.glob("*/pnr.json")) if root.exists() else []:
        body = _load_json(path)
        inspected.add(path)
        design = body.get("design", {})
        corner = body.get("corner", {})
        pnr = body.get("place_and_route", {})
        metrics = pnr.get("metrics", {}) if isinstance(pnr, Mapping) else {}
        block = design.get("block")
        family = family_map.get(str(block))
        if family and body.get("status") == "pass":
            covered.add(family)
        blocks.append(
            {
                **_identity(repo, path),
                "block": block,
                "engine_family": family,
                "status": body.get("status"),
                "view": body.get("view"),
                "flow_completed": body.get("flow_completed"),
                "corner": corner.get("name"),
                "voltage_v": corner.get("voltage_v"),
                "temperature_c": corner.get("temperature_c"),
                "macro_count": metrics.get("macro_count"),
                "standard_cell_area_um2": metrics.get("standard_cell_area_um2"),
                "power_total_w": metrics.get("power_total_w"),
                "fmax_hz": metrics.get("fmax_hz"),
            }
        )

    missing = sorted(set(ENGINE_FAMILIES) - covered)
    claim_boundary = lock.get("claim_boundary", [])
    return (
        {
            "physical_lock": {
                **(_identity(repo, lock_path) if lock_path.is_file() else {}),
                "present": lock_path.is_file(),
                "campaign_id": lock.get("campaign_id"),
                "evidence_class": lock.get("evidence_class"),
                "asap7_version": lock.get("toolchain", {})
                .get("asap7", {})
                .get("version"),
                "claim_boundary": claim_boundary,
            },
            "routed_blocks": blocks,
            "engine_families_covered": sorted(covered),
            "engine_families_missing": missing,
            "engine_family_covered_count": len(covered),
            "engine_family_missing_count": len(missing),
            "control_plane_routed": False,
            "rom_macro_characterized": False,
            "sram_macro_characterized": False,
            "cluster_fabric_routed": False,
            "wafer_fabric_routed": False,
            "full_qwen_targets_characterized": False,
            "full_deepseek_targets_characterized": False,
            "target_area_available": False,
            "target_energy_available": False,
            "calibrated_uncertainty_interval_available": False,
        },
        inspected,
    )


def _blockers(
    functional: Mapping[str, Any],
    machine: Mapping[str, Any],
    cycles: Mapping[str, Any],
    physical: Mapping[str, Any],
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []

    qwen = cycles["comparisons"]["qwen3_rom_single_chip_vs_hbm_single_chip"]
    deepseek = cycles["comparisons"][
        "deepseek_v4_rom_wafer_vs_hbm_cluster_32"
    ]
    wafer_array = cycles["comparisons"]["deepseek_v4_rom_wafer_vs_rom_array_32"]
    if not qwen["functional_ready"]:
        blockers.append(
            {
                "code": "qwen_mandatory_correctness_not_closed",
                "scope": "correctness/qwen",
                "required_action": (
                    "Produce ROM and HBM accelerator records for all 8,000 prompt "
                    "tokens through EOS or the governed 256-token bound, each in "
                    "agreement with the external reference, with identical output."
                ),
            }
        )
    if not deepseek["functional_ready"]:
        blockers.append(
            {
                "code": "deepseek_mandatory_accelerator_pair_missing",
                "scope": "correctness/deepseek",
                "required_action": (
                    "Execute both the ROM wafer and HBM 32-node accelerator targets "
                    "for TA-DS-CTX-200K-1; the external oracle alone is not an "
                    "accelerator pair."
                ),
            }
        )
    if not wafer_array["functional_ready"]:
        blockers.append(
            {
                "code": "deepseek_wafer_array_mandatory_accelerator_pair_missing",
                "scope": "correctness/deepseek_wafer_array",
                "required_action": (
                    "Execute both the ROM wafer and the 32-node ROM array "
                    "accelerator targets for TA-DS-CTX-200K-1 with identical "
                    "output; the packaging comparison has no HBM side and the "
                    "external oracle alone is not an accelerator pair."
                ),
            }
        )

    if not machine["all_required_capabilities_same_view"]:
        blockers.append(
            {
                "code": "asap7_capability_records_missing",
                "scope": "capability",
                "required_action": (
                    "Publish separately versioned ASAP7 characterization capabilities "
                    "for all four targets without erasing their distinct memory "
                    "technology or topology identities."
                ),
            }
        )
    support = machine["topology_support"]
    if not support["cluster_32"]["model_complete_with_an_asap7_table"]:
        blockers.append(
            {
                "code": "asap7_cluster_cost_model_missing",
                "scope": "cost_model/cluster_32",
                "required_action": (
                    "Characterize or explicitly source every cluster fabric parameter "
                    "inside an ASAP7 table; the cluster32 view cannot be borrowed."
                ),
            }
        )
    if not support["wafer"]["model_complete_with_an_asap7_table"]:
        blockers.append(
            {
                "code": "asap7_wafer_cost_model_missing",
                "scope": "cost_model/wafer",
                "required_action": (
                    "Characterize or explicitly source every wafer fabric parameter "
                    "inside an ASAP7 table; the wafer view cannot be borrowed."
                ),
            }
        )

    cycle_pairs = cycles["comparisons"]
    if not cycle_pairs["qwen3_rom_single_chip_vs_hbm_single_chip"]["ready"]:
        blockers.append(
            {
                "code": "qwen_same_view_cycle_pair_missing",
                "scope": "cycle/qwen",
                "required_action": (
                    "Run both Qwen targets with ASAP7 capability/cost inputs and one "
                    "matching shared comparison digest, using distinct source-valid "
                    "target boundaries."
                ),
            }
        )
    if not cycle_pairs["deepseek_v4_rom_wafer_vs_hbm_cluster_32"]["ready"]:
        blockers.append(
            {
                "code": "deepseek_same_view_cycle_pair_missing",
                "scope": "cycle/deepseek",
                "required_action": (
                    "Run the complete DeepSeek wafer and 32-node targets with ASAP7 "
                    "capability/cost inputs, a matching shared comparison digest, and "
                    "distinct source-valid target boundaries."
                ),
            }
        )
    if not cycle_pairs["deepseek_v4_rom_wafer_vs_rom_array_32"]["ready"]:
        blockers.append(
            {
                "code": "deepseek_wafer_array_same_view_cycle_pair_missing",
                "scope": "cycle/deepseek_wafer_array",
                "required_action": (
                    "Run the complete DeepSeek ROM wafer and 32-node ROM array "
                    "targets with ASAP7 capability/cost inputs, a matching shared "
                    "comparison digest, and distinct source-valid target boundaries."
                ),
            }
        )
    if cycles["admissible_cycle_result_count"] == 0:
        blockers.append(
            {
                "code": "cycle_workload_identity_missing",
                "scope": "cycle/provenance",
                "required_action": (
                    "Bind the deployment graph digest, workload id/digest, shared "
                    "comparison digest, and target boundary digest into cycle results; "
                    "request symbols and filenames are insufficient."
                ),
            }
        )

    missing_families = physical["engine_families_missing"]
    if missing_families:
        blockers.append(
            {
                "code": "asap7_engine_coverage_incomplete",
                "scope": "physical/engines",
                "required_action": "Route missing engine families: "
                + ", ".join(missing_families)
                + ".",
            }
        )
    for field, code, scope, action in (
        (
            "control_plane_routed",
            "asap7_control_plane_missing",
            "physical/control",
            "Route and characterize the ABI3 control/sequencer plane in ASAP7.",
        ),
        (
            "rom_macro_characterized",
            "asap7_rom_macro_missing",
            "physical/memory",
            "Provide an admissible ASAP7 ROM macro view; bundled FakeRAM is forbidden.",
        ),
        (
            "sram_macro_characterized",
            "asap7_sram_macro_missing",
            "physical/memory",
            "Provide an admissible ASAP7 SRAM macro view; bundled FakeRAM is forbidden.",
        ),
        (
            "cluster_fabric_routed",
            "asap7_cluster_fabric_missing",
            "physical/cluster",
            "Characterize the cluster link/switch/endpoint path in the same view.",
        ),
        (
            "wafer_fabric_routed",
            "asap7_wafer_fabric_missing",
            "physical/wafer",
            "Characterize tile, stitch, router, and endpoint paths in the same view.",
        ),
    ):
        if not physical[field]:
            blockers.append(
                {"code": code, "scope": scope, "required_action": action}
            )
    if not (
        physical["target_area_available"]
        and physical["target_energy_available"]
        and physical["calibrated_uncertainty_interval_available"]
    ):
        blockers.append(
            {
                "code": "target_area_energy_uncertainty_missing",
                "scope": "reporting",
                "required_action": (
                    "Report full-target area and energy plus a visibly bounded "
                    "uncertainty treatment; routed block metrics are not target totals."
                ),
            }
        )
    return blockers


def build_report(repo: Path = REPO) -> dict[str, Any]:
    repo = repo.resolve()
    contracts = list(_load_authoritative_contracts(repo))
    functional, external_oracles, functional_inputs = _functional_inventory(
        repo, contracts
    )
    machine, machine_inputs = _capability_cost_inventory(repo)
    cycles, cycle_inputs = _cycle_inventory(repo, contracts)
    physical, physical_inputs = _physical_inventory(repo)
    blockers = _blockers(functional, machine, cycles, physical)

    cycle_ready = all(item["ready"] for item in cycles["comparisons"].values())
    correctness_ready = all(
        item["functional_ready"] for item in cycles["comparisons"].values()
    )
    capability_ready = machine["all_required_capabilities_same_view"] and all(
        item["same_view_admissible"]
        for item in machine["topology_support"].values()
    )
    dimensions = {
        "correctness": {
            "ready": correctness_ready,
            "evidence": (
                "source-reopened functional artifacts bound to governed cycle "
                "request trajectories"
            ),
        },
        "latency": {"ready": cycle_ready, "evidence": "same-view cycle pairs"},
        "throughput": {
            "ready": cycle_ready,
            "evidence": "same-view cycle pairs",
        },
        "energy": {
            "ready": physical["target_energy_available"],
            "evidence": "full-target same-view physical accounting",
        },
        "area": {
            "ready": physical["target_area_available"],
            "evidence": "full-target same-view physical accounting",
        },
        "memory": {"ready": cycle_ready, "evidence": "same-view cycle pairs"},
        "utilization": {
            "ready": cycle_ready,
            "evidence": "same-view cycle pairs",
        },
        "stalls": {"ready": cycle_ready, "evidence": "same-view cycle pairs"},
        "capacity": {
            "ready": capability_ready,
            "evidence": "same-view exact capability limits",
        },
        "uncertainty": {
            "ready": physical["calibrated_uncertainty_interval_available"],
            "evidence": "predictive-view uncertainty boundary",
        },
    }

    inspected = functional_inputs | machine_inputs | cycle_inputs | physical_inputs
    for contract in contracts:
        source_paths = [
            contract.get("contract_path"),
            contract.get("workload_path"),
            contract.get("workload_index_path"),
            _mapping(contract.get("model")).get("kernel_ir_path"),
        ]
        external_oracle = _mapping(contract.get("external_oracle"))
        external_oracle_producer = _mapping(external_oracle.get("producer"))
        if external_oracle.get("status") == "locked":
            source_paths.extend(
                [
                    external_oracle.get("path"),
                    external_oracle_producer.get("tool"),
                ]
            )
        template = _mapping(_mapping(contract.get("workload")).get("template"))
        if template.get("path") is not None:
            source_paths.append(template.get("path"))
        for relative in source_paths:
            if not relative:
                continue
            path = repo / str(relative)
            if path.is_file():
                inspected.add(path)
    source_sha256 = {
        relative: _sha256(repo / relative)
        for relative in SOURCE_PATHS
        if (repo / relative).is_file()
    }

    return {
        "schema": SCHEMA,
        "gate_id": GATE_ID,
        "status": "blocked" if blockers else "ready",
        "ready": not blockers,
        "acceptance_contract": {
            "technology_view": REQUIRED_VIEW,
            "technology_claim": (
                "predictive ASAP7 research view only; not a foundry, "
                "manufacturability, or N4 claim"
            ),
            "strict_no_cross_view_mixing": True,
            "comparison_contracts_source_valid": all(
                contract["contract_source_valid"] for contract in contracts
            ),
            "comparison_contracts_target_sources_ready": all(
                contract["contract_ready"] for contract in contracts
            ),
            "comparison_contracts_external_oracles_ready": all(
                contract["external_oracle_source_ready"] for contract in contracts
            ),
            "required_comparisons": contracts,
            "required_reporting_dimensions": list(dimensions),
            "external_components": [
                "HBM stacks and PHY",
                "cluster switches and package links",
                "wafer process, stitch, package, power delivery, yield, and thermal",
            ],
            "external_component_policy": (
                "Retain explicit datasheet/assumed provenance inside the ASAP7 "
                "comparison boundary; never relabel external numbers as routed."
            ),
        },
        "functional_correctness": functional,
        "external_reference_only_evidence": external_oracles,
        "capability_and_cost_model": machine,
        "cycle_evidence": cycles,
        "physical_evidence": physical,
        "reporting_dimensions": dimensions,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "claim_boundary": {
            "gate_closed": not blockers,
            "performance_comparison_admissible": not blockers,
            "cross_view_inputs_admitted": False,
            "short_functional_pairs_close_gate": False,
            "routed_blocks_are_full_target_evidence": False,
            "note": (
                "This artifact records readiness only. No latency, throughput, "
                "energy, area, or capacity winner may be claimed while status is "
                "blocked."
            ),
        },
        "provenance": {
            "source_sha256": source_sha256,
            "inspected_artifacts": [
                _identity(repo, path) for path in sorted(inspected)
            ],
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "results" / "abi3" / "asap7_comparison_readiness.json",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="refuse if the committed artifact is absent or differs",
    )
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="return 2 while any W11.2 prerequisite is missing",
    )
    args = parser.parse_args(argv)

    report = build_report(REPO)
    payload = canonical_json(report)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != payload:
            print(f"STALE {args.output}: regenerate the W11.2 readiness artifact")
            return 3
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)

    print(
        f"{GATE_ID}: {report['status']} "
        f"({report['blocker_count']} blockers, "
        f"{report['cycle_evidence']['admissible_cycle_result_count']} "
        "admissible cycle results)"
    )
    if args.require_ready and not report["ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
