#!/usr/bin/env python3
"""Build the fail-closed readiness record for checklist gate TA-CMP-7-ASAP7.

This is a preflight, not a performance-report generator.  It inventories the
evidence needed to compare the Qwen ROM/HBM targets and the DeepSeek wafer/32
node targets in one predictive ASAP7 view.  An input from another technology
view is reported as excluded and is never used to satisfy the gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import Capability, canonical_json  # noqa: E402
from runtime.abi3.constants import TopologyClass  # noqa: E402
from runtime.cycle.machine import (  # noqa: E402
    ENGINE_FAMILY_NAMES,
    CostTable,
    MachineError,
    MachineModel,
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
ENGINE_FAMILIES = tuple(sorted(set(ENGINE_FAMILY_NAMES.values())))

COMPARISON_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "comparison_id": "qwen3_rom_single_chip_vs_hbm_single_chip",
        "model_id": "qwen3-8b",
        "workload_id": "TA-QW-8K-1",
        "workload_path": "build/workloads/qwen3-8b/TA-QW-8K-1.json",
        "workload_index_path": "build/workloads/qwen3-8b/index.json",
        "prompt_token_count": 8_000,
        "max_new_tokens": 256,
        "targets": {
            "rom": {"topology_class": 0, "node_count": 1},
            "hbm": {"topology_class": 0, "node_count": 1},
        },
    },
    {
        "comparison_id": "deepseek_v4_rom_wafer_vs_hbm_cluster_32",
        "model_id": "deepseek-v4-flash-0731",
        "workload_id": "TA-DS-CTX-200K-1",
        "workload_path": (
            "build/workloads/deepseek-v4-flash-0731/TA-DS-CTX-200K-1.json"
        ),
        "workload_index_path": "build/workloads/deepseek-v4-flash-0731/index.json",
        "prompt_token_count": 200_000,
        "max_new_tokens": 256,
        "targets": {
            "rom": {"topology_class": 2, "node_count": 1},
            "hbm": {"topology_class": 1, "node_count": 32},
        },
    },
)

CAPABILITY_PATHS = (
    "configs/hardware/abi3_capability/rom_qwen3.json",
    "configs/hardware/abi3_capability/hbm_sram_single_chip.json",
    "configs/hardware/abi3_capability/rom_deepseek_v4.json",
    "configs/hardware/abi3_capability/hbm_sram_cluster_32.json",
)

SOURCE_PATHS = (
    "Makefile",
    "tools/audit_abi3_asap7_comparison_readiness.py",
    "tools/run_abi3_cycle.py",
    "tools/build_abi3_cost_tables.py",
    "runtime/cycle/machine.py",
    "runtime/abi3/capability.py",
    "configs/pdk/asap7_physical_lock.json",
    "docs/FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md",
    "docs/TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md",
    "docs/UNIFIED_EXECUTION_CHECKLIST.md",
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


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def _identity(repo: Path, path: Path) -> dict[str, Any]:
    return {
        "path": _relative(repo, path),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }


def _role(backend: Any, target_id: Any = "") -> str | None:
    text = f"{backend} {target_id}".lower()
    if "rom" in text:
        return "rom"
    if "hbm" in text:
        return "hbm"
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


def _completion_closed(payload: Mapping[str, Any], expected_tokens: int) -> bool:
    stop_reason = str(payload.get("stop_reason", "")).lower()
    if "eos" in stop_reason:
        return True
    return (
        stop_reason == "max_new_tokens"
        and payload.get("generated_token_count") == expected_tokens
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

    target_role = _role(target.get("backend"), target.get("target_id"))
    expected_target = contract["targets"].get(target_role or "", {})
    token_ids = payload.get("generated_token_ids")
    token_ids = token_ids if isinstance(token_ids, list) else []
    status = body.get("status")
    checks = {
        "status_pass": status == "pass",
        "no_failure": payload.get("failure") in (None, ""),
        "model_id_exact": workload.get("model_id", contract["model_id"])
        == contract["model_id"],
        "workload_digest_exact": bool(contract.get("workload_digest"))
        and workload.get("workload_digest") == contract.get("workload_digest"),
        "prompt_token_count_exact": workload.get("prompt_token_count")
        == contract["prompt_token_count"],
        "declared_run_max_new_tokens_exact": workload.get("max_new_tokens")
        == contract["max_new_tokens"],
        "tokenizer_identity_exact": bool(contract.get("tokenizer_sha256"))
        and workload.get("tokenizer_sha256") == contract.get("tokenizer_sha256"),
        "target_role_known": target_role in {"rom", "hbm"},
        "topology_exact": target.get("topology_class")
        == expected_target.get("topology_class"),
        "node_count_exact": target.get("node_count")
        == expected_target.get("node_count"),
        "token_count_consistent": payload.get("generated_token_count")
        == len(token_ids),
        "mandatory_completion_closed": _completion_closed(
            payload, int(contract["max_new_tokens"])
        ),
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


def _workload_contract(repo: Path, base: Mapping[str, Any]) -> dict[str, Any]:
    contract = dict(base)
    workload_path = repo / str(base["workload_path"])
    index_path = repo / str(base["workload_index_path"])
    workload = _load_json(workload_path) if workload_path.is_file() else {}
    index = _load_json(index_path) if index_path.is_file() else {}
    entry = index.get("workloads", {}).get(base["workload_id"], {})
    contract["workload_digest"] = workload.get("digest") or entry.get("digest")
    contract["tokenizer_sha256"] = index.get("tokenizer_sha256")
    contract["source_checks"] = {
        "workload_present": workload_path.is_file(),
        "index_present": index_path.is_file(),
        "workload_id_exact": workload.get("workload_id") == base["workload_id"],
        "digest_agrees_with_index": bool(workload.get("digest"))
        and workload.get("digest") == entry.get("digest"),
        "prompt_token_count_exact": workload.get("prompt_token_count")
        == base["prompt_token_count"],
        "max_new_tokens_exact": workload.get("max_new_tokens")
        == base["max_new_tokens"],
        "tokenizer_identity_present": bool(index.get("tokenizer_sha256")),
    }
    contract["source_valid"] = all(contract["source_checks"].values())
    return contract


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
        except (OSError, json.JSONDecodeError):
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
        admitted = {
            role: [item for item in candidates if item["role"] == role and item["admissible"]]
            for role in ("rom", "hbm")
        }
        matching_pair = None
        for left in admitted["rom"]:
            for right in admitted["hbm"]:
                if left["generated_token_ids"] == right["generated_token_ids"]:
                    matching_pair = {"rom": left["path"], "hbm": right["path"]}
                    break
            if matching_pair:
                break
        for item in candidates:
            item.pop("generated_token_ids", None)
        pair_ready = bool(matching_pair)
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
            "matching_pair": matching_pair,
            "ready": pair_ready and bool(contract["source_valid"]),
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
    topology = int(capability_body.get("topology_class", -1))
    parameters = cost_body.get("parameters")
    parameters = parameters if isinstance(parameters, Mapping) else {}
    missing_fabric = sorted(
        name for name in _required_fabric_parameters(topology) if name not in parameters
    )

    try:
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


def assess_cycle_document(
    body: Mapping[str, Any],
    path: str,
    *,
    sha256: str = "",
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return the strict W11.2 admission decision for one cycle result."""
    if body.get("schema") != CYCLE_SCHEMA:
        return None
    inputs = body.get("inputs")
    inputs = inputs if isinstance(inputs, Mapping) else {}
    cost = inputs.get("cost_table")
    cost = cost if isinstance(cost, Mapping) else {}
    workload = inputs.get("workload")
    workload = workload if isinstance(workload, Mapping) else {}
    agreement = body.get("functional_agreement")
    agreement = agreement if isinstance(agreement, Mapping) else {}
    execution = body.get("execution")
    execution = execution if isinstance(execution, Mapping) else {}
    schedule = body.get("schedule_audit")
    schedule = schedule if isinstance(schedule, Mapping) else {}
    gaps = body.get("gaps")
    request = inputs.get("request")
    request = request if isinstance(request, Mapping) else {}
    target_role = _role(inputs.get("backend"), inputs.get("target_id"))
    raw_topology = inputs.get("topology_class")
    try:
        topology = (
            int(TopologyClass[raw_topology])
            if isinstance(raw_topology, str)
            else int(raw_topology)
        )
    except (KeyError, TypeError, ValueError):
        topology = None
    expected_target = (
        contract.get("targets", {}).get(target_role or "", {})
        if contract is not None
        else {}
    )
    expected_topology = expected_target.get("topology_class")
    expected_nodes = expected_target.get("node_count")
    checks = {
        "cost_table_view_exact": cost.get("technology_view") == REQUIRED_VIEW,
        "capability_view_exact": inputs.get("capability_technology_view")
        == REQUIRED_VIEW,
        "workload_id_present": bool(workload.get("workload_id")),
        "workload_digest_present": bool(workload.get("workload_digest")),
        "comparison_boundary_digest_present": bool(
            inputs.get("comparison_boundary_digest")
        ),
        "target_role_known": target_role in {"rom", "hbm"},
        "topology_class_exact": topology == expected_topology
        if contract is not None
        else topology is not None,
        "node_count_exact": inputs.get("node_count") == expected_nodes
        if contract is not None
        else isinstance(inputs.get("node_count"), int)
        and not isinstance(inputs.get("node_count"), bool)
        and inputs.get("node_count", 0) > 0,
        "execution_status_success": execution.get("status") == "SUCCESS",
        "execution_trap_none": execution.get("trap_class") == "NONE",
        "execution_transactions_complete": isinstance(
            request.get("transactions"), int
        )
        and not isinstance(request.get("transactions"), bool)
        and request.get("transactions", 0) > 0
        and execution.get("transactions") == request.get("transactions"),
        "schedule_audit_complete": schedule.get("complete") is True
        and schedule.get("findings") == [],
        "contract_gaps_empty": isinstance(gaps, list) and not gaps,
        "functional_counter_agreement": agreement.get("checked") is True
        and agreement.get("agrees") is True,
    }
    failed = [name for name, value in checks.items() if not value]
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
        "comparison_boundary_digest": inputs.get("comparison_boundary_digest"),
        "request": request,
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
    contracts_by_workload = {
        str(item["workload_id"]): item for item in contracts
    }
    for path in sorted(root.rglob("*.json")) if root.exists() else []:
        try:
            body = _load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(body, Mapping):
            continue
        inputs = body.get("inputs")
        inputs = inputs if isinstance(inputs, Mapping) else {}
        workload = inputs.get("workload")
        workload = workload if isinstance(workload, Mapping) else {}
        contract = contracts_by_workload.get(str(workload.get("workload_id", "")))
        assessed = assess_cycle_document(
            body,
            _relative(repo, path),
            sha256=_sha256(path),
            contract=contract,
        )
        if assessed is not None:
            candidates.append(assessed)
            inspected.add(path)
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
            and item["workload_id"] == contract["workload_id"]
            and item["workload_digest"] == contract.get("workload_digest")
        ]
        matched = None
        for rom in (item for item in exact if item["role"] == "rom"):
            for hbm in (item for item in exact if item["role"] == "hbm"):
                same_boundary = (
                    rom["comparison_boundary_digest"]
                    == hbm["comparison_boundary_digest"]
                )
                same_request = rom["request"] == hbm["request"]
                if same_boundary and same_request:
                    matched = {"rom": rom["path"], "hbm": hbm["path"]}
                    break
            if matched:
                break
        pair_results[str(contract["comparison_id"])] = {
            "workload_id": contract["workload_id"],
            "admissible_candidate_count": len(exact),
            "matched_pair": matched,
            "ready": bool(matched),
        }

    return (
        {
            "admission_rule": {
                "required_cost_table_view": REQUIRED_VIEW,
                "required_capability_view": REQUIRED_VIEW,
                "required_bindings": [
                    "inputs.workload.workload_id",
                    "inputs.workload.workload_digest",
                    "inputs.comparison_boundary_digest",
                    "inputs.request",
                    "inputs.topology_class",
                    "inputs.node_count",
                    "execution.status=SUCCESS",
                    "execution.trap_class=NONE",
                    "execution.transactions=inputs.request.transactions",
                    "schedule_audit.complete=true with no findings",
                    "gaps=[]",
                    "functional_agreement.checked",
                    "functional_agreement.agrees",
                ],
                "note": (
                    "The boundary digest must cover PVT, clock, workload, numeric "
                    "profile, batch/concurrency, generation, latency, and evidence "
                    "boundaries. Matching filenames or symbols alone are not proof."
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

    qwen = functional["qwen3_rom_single_chip_vs_hbm_single_chip"]
    deepseek = functional["deepseek_v4_rom_wafer_vs_hbm_cluster_32"]
    if not qwen["ready"]:
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
    if not deepseek["ready"]:
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
                    "identical governed comparison-boundary digest."
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
                    "capability/cost inputs and one identical governed boundary."
                ),
            }
        )
    if cycles["admissible_cycle_result_count"] == 0:
        blockers.append(
            {
                "code": "cycle_workload_identity_missing",
                "scope": "cycle/provenance",
                "required_action": (
                    "Bind workload id/digest and comparison-boundary digest into cycle "
                    "results; request symbols and filenames are insufficient."
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
    contracts = [_workload_contract(repo, base) for base in COMPARISON_CONTRACTS]
    functional, external_oracles, functional_inputs = _functional_inventory(
        repo, contracts
    )
    machine, machine_inputs = _capability_cost_inventory(repo)
    cycles, cycle_inputs = _cycle_inventory(repo, contracts)
    physical, physical_inputs = _physical_inventory(repo)
    blockers = _blockers(functional, machine, cycles, physical)

    cycle_ready = all(item["ready"] for item in cycles["comparisons"].values())
    correctness_ready = all(item["ready"] for item in functional.values())
    capability_ready = machine["all_required_capabilities_same_view"] and all(
        item["same_view_admissible"]
        for item in machine["topology_support"].values()
    )
    dimensions = {
        "correctness": {
            "ready": correctness_ready,
            "evidence": "mandatory functional target pairs",
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
        for key in ("workload_path", "workload_index_path"):
            path = repo / str(contract[key])
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
