#!/usr/bin/env python3
"""Certify shipped HBM/SRAM deployments against rebuilt artifacts.

The default case closes the deployment-scoped Qwen W4.6 gate.  It reads the
published neutral graph, capability, and shipped ABI 3.0 bundle; rebuilds the
physical plan and deployment twice; requires both rebuilds and the shipped
bytes to agree; runs the independent HBM/SRAM checker; and proves one-node
capacity and the shared chip's retained inter-chip endpoint.

Additional cases use five arguments::

    --case NAME PRODUCT KERNEL_IR DEPLOYMENT_DIR CAPABILITY_JSON

``PRODUCT`` is currently ``qwen`` or ``deepseek``.  DeepSeek support records
the same common deployment checks, but its W4.7 semantic requirements remain a
separate acceptance gate until expert/sparse/reduction traffic and capacity are
closed.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from compiler.backends.hbm_sram.check import (  # noqa: E402
    HBM_DEPLOYMENT_CHECK_SCHEMA,
    check_deployment,
)
from compiler.backends.hbm_sram.lower import lower_with_plan  # noqa: E402
from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from runtime.abi3.capability import Capability, canonical_json  # noqa: E402
from runtime.abi3.constants import (  # noqa: E402
    Feature,
    Link,
    Major,
    NO_ID,
    State,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    CollectiveOp,
    ExtendedDescriptorType,
)
from runtime.abi3.records import decode_body, split_program  # noqa: E402

CASE_SCHEMA = "opentallas.hbm_sram.deployment_certificate.v1"
CAMPAIGN_SCHEMA = "opentallas.hbm_sram.deployment_campaign.v1"


@dataclass(frozen=True, slots=True)
class Case:
    name: str
    product: str
    ir: str
    deployment: str
    capability: str


DEFAULT_CASES = (
    Case(
        "qwen3-hbm-single-chip",
        "qwen",
        "build/ir-v3/qwen3-8b/kernel_ir.v3.json",
        "build/abi3/qwen3-8b-hbm-tokens",
        "configs/hardware/abi3_capability/hbm_sram_single_chip.json",
    ),
)

DEFAULT_PEER_CAPABILITY = "configs/hardware/abi3_capability/hbm_sram_cluster_32.json"

_ALLOWED_PROFILE_DIFFERENCES = frozenset(
    {
        "limits.max_nodes",
        "link.bisection_links",
        "link.peers_per_node",
        "link.route_groups",
        "topology_class",
    }
)

_DEEPSEEK_ROUTE_CONTRACT: Mapping[str, tuple[int, int, int, frozenset[str]]] = {
    "expert_dispatch": (
        0,
        int(Link.SCATTER),
        int(CollectiveOp.CONCAT),
        frozenset({"EXPERT_DISPATCH"}),
    ),
    "sparse_gather": (
        1,
        int(Link.GATHER),
        int(CollectiveOp.ALL_GATHER),
        frozenset({"GATHER", "WINDOW_INDEX", "INDEX_TOPK", "ATTENTION_SPARSE"}),
    ),
    "activation_transfer": (
        2,
        int(Link.COLLECTIVE),
        int(CollectiveOp.ALL_GATHER),
        frozenset(),
    ),
    "reduction": (
        3,
        int(Link.COLLECTIVE),
        int(CollectiveOp.SUM),
        frozenset({"EXPERT_REDUCE", "ORDERED_SUM", "PARTITION_SUM"}),
    ),
    "coordinated_commit": (
        4,
        int(Link.BARRIER),
        int(CollectiveOp.SUM),
        frozenset(),
    ),
}


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPOSITORY_ROOT / candidate


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPOSITORY_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def _file_identity(path: Path) -> dict[str, Any]:
    return {
        "path": _relative(path),
        "bytes": path.stat().st_size,
        "sha256": _digest(path),
    }


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {prefix: value}
    out: dict[str, Any] = {}
    for key, member in sorted(value.items()):
        name = f"{prefix}.{key}" if prefix else str(key)
        out.update(_flatten(member, name))
    return out


def _profile_comparison(
    single_chip: Mapping[str, Any], cluster: Mapping[str, Any]
) -> dict[str, Any]:
    left = _flatten(single_chip)
    right = _flatten(cluster)
    differing = {
        key: {"single_chip": left.get(key), "cluster_32": right.get(key)}
        for key in sorted(set(left) | set(right))
        if left.get(key) != right.get(key)
    }
    unexpected = sorted(set(differing) - _ALLOWED_PROFILE_DIFFERENCES)
    return {
        "differing": differing,
        "allowed_differences": sorted(_ALLOWED_PROFILE_DIFFERENCES),
        "unexpected_differences": unexpected,
        "identical_shared_hardware": not unexpected,
    }


def _deployment_equal(left: Deployment, right: Deployment) -> bool:
    return (
        left.program == right.program
        and left.table.encode() == right.table.encode()
        and left.objects == right.objects
        and left.deployment_digest == right.deployment_digest
    )


def _wait_events(deployment: Deployment, wait_set_id: int) -> set[int]:
    if wait_set_id == NO_ID:
        return set()
    descriptor = deployment.table[wait_set_id]
    if descriptor.descriptor_type != ExtendedDescriptorType.EVENT_WAIT_SET:
        return set()
    count = int(descriptor.payload["producer_count"])
    return {int(descriptor.payload[f"producer_{slot}"]) for slot in range(count)}


def _hbm_inventory(deployment: Deployment) -> dict[str, Any]:
    """Inventory the emitted HBM address map, including backed state."""

    intervals: list[tuple[int, int, int, str]] = []
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.MEMORY_OBJECT:
            continue
        storage = StorageClass(int(descriptor.payload["storage_class"]))
        if storage not in {StorageClass.HBM, StorageClass.STATE}:
            continue
        base = int(descriptor.payload["base_address"])
        end = base + int(descriptor.payload["size_bytes"])
        intervals.append((base, end, descriptor.descriptor_id, storage.name))
    intervals.sort()

    overlaps = [
        {
            "left_descriptor": left[2],
            "left_end": left[1],
            "right_descriptor": right[2],
            "right_base": right[0],
        }
        for left, right in zip(intervals, intervals[1:])
        if left[1] > right[0]
    ]
    return {
        "address_map_disjoint": not overlaps,
        "address_span": max((end for _, end, _, _ in intervals), default=0),
        "object_count": len(intervals),
        "overlaps": overlaps,
        "payload_bytes": sum(end - base for base, end, _, _ in intervals),
    }


def run_case(
    case: Case, peer_capability: str = DEFAULT_PEER_CAPABILITY
) -> dict[str, Any]:
    """Rebuild and independently certify one immutable shipped bundle."""

    if case.product not in {"qwen", "deepseek"}:
        raise ValueError(f"unknown HBM product {case.product!r}")

    ir_path = _resolve(case.ir)
    deployment_root = _resolve(case.deployment)
    capability_path = _resolve(case.capability)
    peer_path = _resolve(peer_capability)

    graph = KernelGraph.read(ir_path)
    capability_body = json.loads(capability_path.read_text())
    capability = Capability.from_dict(capability_body)
    shipped = Deployment.read(deployment_root)

    first, first_plan = lower_with_plan(graph, capability)
    second, second_plan = lower_with_plan(graph, capability)
    independent = check_deployment(graph, shipped, capability)
    hbm_inventory = _hbm_inventory(shipped)

    _header, body = split_program(shipped.program)
    instructions = decode_body(body)
    communications = {
        descriptor_id: shipped.table[descriptor_id]
        for descriptor_id in shipped.table.ids_of_type(
            ExtendedDescriptorType.COMMUNICATION
        )
    }
    communication_count = len(communications)
    link_records: list[dict[str, Any]] = []
    for index, instruction in enumerate(instructions):
        if instruction.major != int(Major.LINK):
            continue
        communication = communications.get(int(instruction.descriptor_id))
        payload = communication.payload if communication is not None else {}
        source = int(instruction.source_operation_id)
        source_kind = (
            graph.kernels[source].kind if 0 <= source < len(graph.kernels) else ""
        )
        link_records.append(
            {
                "instruction_index": index,
                "subopcode": int(instruction.sub),
                "source_operation_id": source,
                "source_kind": source_kind,
                "signal_event_id": int(instruction.signal_event_id),
                "wait_events": sorted(
                    _wait_events(shipped, int(instruction.wait_set_id))
                ),
                "route_class": int(payload.get("route_class", -1)),
                "collective_op": int(payload.get("collective_op", -1)),
                "participant_count": int(payload.get("participant_count", 0)),
                "byte_extent": int(payload.get("byte_extent", 0)),
            }
        )
    link_count = len(link_records)

    checks: dict[str, bool] = {}
    errors: list[str] = []

    def require(name: str, ok: bool, message: str) -> None:
        checks[name] = bool(ok)
        if not ok:
            errors.append(message)

    require(
        "model_identity",
        shipped.model_id == graph.model_id,
        "shipped deployment does not name the supplied model",
    )
    require(
        "graph_identity",
        shipped.source_identity.get("graph_id") == graph.graph_id,
        "shipped deployment does not bind the supplied neutral graph",
    )
    require(
        "capability_identity",
        shipped.capability_digest == capability.digest,
        "shipped deployment does not bind the supplied capability",
    )
    require(
        "independent_checker",
        bool(independent["ok"]),
        "independent HBM/SRAM checker rejected the shipped deployment",
    )
    require(
        "abi_verifier",
        bool(independent["verifier"]["admitted"]),
        "frozen ABI 3.0 verifier rejected the shipped deployment",
    )
    require(
        "first_rebuild_matches_shipped",
        _deployment_equal(first, shipped),
        "a clean rebuild does not reproduce the shipped deployment bytes",
    )
    require(
        "second_rebuild_matches_shipped",
        _deployment_equal(second, shipped),
        "a second clean rebuild does not reproduce the shipped deployment bytes",
    )
    require(
        "plan_reproducible",
        first_plan.plan_id == second_plan.plan_id
        and canonical_json(first_plan.to_dict())
        == canonical_json(second_plan.to_dict()),
        "two clean physical-plan builds differ",
    )
    require(
        "plan_bound_to_deployment",
        shipped.source_identity.get("plan_id") == first_plan.plan_id,
        "deployment source identity does not bind the rebuilt physical plan",
    )
    require(
        "zero_copy_weights",
        bool(first_plan.proofs["zero_copy_weights"]),
        "physical plan does not retain zero-copy checkpoint placement",
    )
    require(
        "sram_capacity",
        bool(first_plan.proofs["sram_fits"]),
        "physical plan exceeds node-local SRAM capacity",
    )
    require(
        "hbm_address_map_disjoint",
        bool(hbm_inventory["address_map_disjoint"]),
        "emitted HBM and state objects overlap in the deployed address map",
    )
    plan_hbm_required = int(first_plan.proofs["hbm_bytes_per_node"])
    hbm_available = int(first_plan.proofs["hbm_available_per_node"])
    hbm_required = (
        int(hbm_inventory["address_span"])
        if case.product == "qwen"
        else plan_hbm_required
    )
    rolling_slots = [
        slot for slot in first_plan.arena_slots if slot.rolling_group
    ]
    stream_groups = {
        kernel.stream_group
        for kernel in first_plan.kernels
        if kernel.stream_group
    }
    require(
        "hbm_capacity",
        hbm_required <= hbm_available,
        f"deployment requires {hbm_required} HBM bytes per node, but only "
        f"{hbm_available} are available",
    )

    shared_profile: dict[str, Any] | None = None
    expected_nodes = 1 if case.product == "qwen" else 32
    require(
        "node_count",
        int(first_plan.topology.node_count) == expected_nodes
        and int(independent["actual"]["node_count"]) == expected_nodes,
        f"{case.product} deployment is not exactly {expected_nodes} node(s)",
    )
    if case.product == "qwen":
        peer_body = json.loads(peer_path.read_text())
        shared_profile = _profile_comparison(capability_body, peer_body)
        require(
            "single_chip_topology",
            int(shipped.topology_class) == int(TopologyClass.SINGLE_CHIP),
            "Qwen HBM deployment is not single-chip",
        )
        require(
            "no_cluster_traffic",
            link_count == 0 and communication_count == 0,
            "single-chip Qwen deployment emits cluster traffic",
        )
        features = {int(value) for value in capability_body.get("features", [])}
        link = capability_body.get("link", {})
        require(
            "shared_chip_endpoint",
            int(Feature.INTER_CHIP_ENDPOINT) in features
            and int(Feature.INTEGRITY_RETRY) in features
            and int(link.get("endpoints_per_node", 0)) > 0
            and int(link.get("virtual_channels", 0)) > 0
            and int(link.get("credit_bound", 0)) > 0
            and int(link.get("retry_bound", 0)) > 0,
            "single-chip profile strips the endpoint required by the shared chip",
        )
        require(
            "same_shared_hardware_profile",
            bool(shared_profile["identical_shared_hardware"]),
            "single-chip and cluster profiles differ outside topology/link cardinality",
        )
    else:
        require(
            "cluster_topology",
            int(shipped.topology_class) == int(TopologyClass.CLUSTER_32),
            "DeepSeek HBM deployment is not a conventional-chip cluster",
        )
        require(
            "cluster_traffic_present",
            link_count > 0 and communication_count > 0,
            "DeepSeek 32-node deployment emits no cluster traffic",
        )
        for name, (
            route,
            subopcode,
            collective,
            source_kinds,
        ) in _DEEPSEEK_ROUTE_CONTRACT.items():
            matching = [
                record
                for record in link_records
                if record["route_class"] == route
                and record["subopcode"] == subopcode
                and record["collective_op"] == collective
                and (not source_kinds or record["source_kind"] in source_kinds)
            ]
            require(
                f"{name}_traffic",
                bool(matching),
                f"DeepSeek cluster emits no semantically bound {name} traffic",
            )
        require(
            "all_route_classes",
            {record["route_class"] for record in link_records}
            == set(range(len(_DEEPSEEK_ROUTE_CONTRACT))),
            "DeepSeek cluster does not exercise all five ordered traffic classes",
        )
        replicated = shipped.notes.get("replicated_link_sites", {})
        require(
            "required_traffic_not_replicated",
            not any(
                int(replicated.get(name, 0)) > 0
                for name in ("expert_dispatch", "sparse_gather", "reduction")
            ),
            "expert, sparse, or reduction sites are replicated instead of distributed",
        )

        barrier_records = [
            record
            for record in link_records
            if record["route_class"]
            == _DEEPSEEK_ROUTE_CONTRACT["coordinated_commit"][0]
        ]
        barrier_event = (
            int(barrier_records[0]["signal_event_id"])
            if len(barrier_records) == 1
            else NO_ID
        )
        commit_records = [
            (index, instruction)
            for index, instruction in enumerate(instructions)
            if instruction.major == int(Major.STATE)
            and instruction.sub == int(State.COMMIT)
        ]
        require(
            "one_commit_barrier",
            len(barrier_records) == 1 and barrier_event != NO_ID,
            "DeepSeek cluster does not publish exactly one completion-signalled commit barrier",
        )
        require(
            "commit_barrier_waits_for_work",
            len(barrier_records) == 1 and bool(barrier_records[0]["wait_events"]),
            "coordinated-commit barrier is issued without waiting for prior work",
        )
        require(
            "commits_wait_for_barrier",
            bool(commit_records)
            and barrier_event != NO_ID
            and all(
                index > int(barrier_records[0]["instruction_index"])
                and barrier_event in _wait_events(shipped, int(instruction.wait_set_id))
                for index, instruction in commit_records
            ),
            "node-local STATE.COMMIT operations do not wait for the cluster barrier",
        )

    return {
        "schema": CASE_SCHEMA,
        "case": case.name,
        "product": case.product,
        "status": "pass" if not errors else "fail",
        "ok": not errors,
        "check_count": len(checks),
        "passed_check_count": sum(bool(value) for value in checks.values()),
        "checks": dict(sorted(checks.items())),
        "errors": errors,
        "inputs": {
            "kernel_ir": _file_identity(ir_path),
            "capability": _file_identity(capability_path),
            "peer_capability": (
                _file_identity(peer_path) if case.product == "qwen" else None
            ),
            "deployment": {
                "path": _relative(deployment_root),
                "manifest": _file_identity(deployment_root / "deployment.json"),
                "descriptors": _file_identity(deployment_root / "descriptors.bin"),
                "program": _file_identity(deployment_root / "program.bin"),
            },
        },
        "identity": {
            "model_id": graph.model_id,
            "graph_id": graph.graph_id,
            "plan_id": first_plan.plan_id,
            "deployment_sha256": shipped.deployment_digest.hex(),
            "capability_sha256": capability.digest,
        },
        "actual": {
            **independent["actual"],
            "communications": communication_count,
            "deployed_hbm_address_span": int(hbm_inventory["address_span"]),
            "deployed_hbm_object_count": int(hbm_inventory["object_count"]),
            "deployed_hbm_payload_bytes": int(hbm_inventory["payload_bytes"]),
            "hbm_bytes_per_node": hbm_required,
            "hbm_available_per_node": hbm_available,
            "hbm_headroom_per_node": hbm_available - hbm_required,
            "plan_hbm_bytes_per_node": plan_hbm_required,
            "activation_arena_bytes": int(
                first_plan.proofs["activation_arena_bytes"]
            ),
            "activation_arena_slots": int(
                first_plan.proofs["activation_arena_slots"]
            ),
            "rolling_activation_bytes": sum(
                int(slot.size_bytes) for slot in rolling_slots
            ),
            "rolling_activation_slots": len(rolling_slots),
            "stream_group_count": len(stream_groups),
            "stream_kernel_count": sum(
                bool(kernel.stream_group) for kernel in first_plan.kernels
            ),
            "sram_bytes_per_node": int(first_plan.proofs["sram_bytes"]),
            "sram_available_per_node": int(first_plan.proofs["sram_available"]),
            "weight_segments": int(first_plan.proofs["weight_segments"]),
        },
        "reproducibility": {
            "clean_build_count": 2,
            "first_matches_shipped": _deployment_equal(first, shipped),
            "second_matches_shipped": _deployment_equal(second, shipped),
            "plans_identical": first_plan.plan_id == second_plan.plan_id,
        },
        "shared_hardware_profile": shared_profile,
        "cluster_semantics": (
            {
                "route_contract": {
                    name: {
                        "route_class": contract[0],
                        "subopcode": contract[1],
                        "collective_op": contract[2],
                        "source_kinds": sorted(contract[3]),
                    }
                    for name, contract in _DEEPSEEK_ROUTE_CONTRACT.items()
                },
                "link_records": link_records,
                "replicated_link_sites": dict(
                    sorted(shipped.notes.get("replicated_link_sites", {}).items())
                ),
            }
            if case.product == "deepseek"
            else None
        ),
        "independent_checker": independent,
    }


def _parse_cases(values: Sequence[Sequence[str]] | None) -> tuple[Case, ...]:
    if not values:
        return DEFAULT_CASES
    return tuple(Case(*value) for value in values)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        action="append",
        nargs=5,
        metavar=("NAME", "PRODUCT", "KERNEL_IR", "DEPLOYMENT_DIR", "CAPABILITY"),
        help="deployment case to certify; repeat for independent parallel cases",
    )
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument(
        "--peer-capability",
        default=DEFAULT_PEER_CAPABILITY,
        help="cluster profile compared with the single-chip shared hardware",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "results/abi3/hbm_qwen_deployment_certificate.json",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    cases = _parse_cases(args.case)
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    output = args.output if args.output.is_absolute() else Path.cwd() / args.output
    if output.exists() and not args.force:
        print(f"refusing to overwrite {output}; pass --force", file=sys.stderr)
        return 1

    workers = min(args.jobs, len(cases), os.cpu_count() or 1)
    if workers == 1:
        reports = [run_case(case, args.peer_capability) for case in cases]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            reports = list(
                pool.map(
                    run_case,
                    cases,
                    [args.peer_capability] * len(cases),
                )
            )
    reports.sort(key=lambda report: report["case"])

    source_paths = {
        "checker": REPOSITORY_ROOT / "compiler/backends/hbm_sram/check.py",
        "lowering": REPOSITORY_ROOT / "compiler/backends/hbm_sram/lower.py",
        "planner": REPOSITORY_ROOT / "compiler/backends/hbm_sram/plan.py",
        "campaign_tool": Path(__file__).resolve(),
    }
    campaign = {
        "schema": CAMPAIGN_SCHEMA,
        "status": "pass" if all(report["ok"] for report in reports) else "fail",
        "checker_schema": HBM_DEPLOYMENT_CHECK_SCHEMA,
        "parallel_jobs": workers,
        "case_count": len(reports),
        "source": {
            name: _file_identity(path) for name, path in sorted(source_paths.items())
        },
        "cases": reports,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(campaign))

    if args.json:
        print(json.dumps(campaign, indent=2, sort_keys=True))
    else:
        print(
            f"HBM deployment campaign: {campaign['status']} "
            f"({len(reports)} case(s), {workers} job(s))"
        )
        for report in reports:
            actual = report["actual"]
            print(
                f"  {report['case']:<30} {report['status']:<4} "
                f"{report['passed_check_count']}/{report['check_count']} checks, "
                f"{actual['instructions']} instructions, "
                f"{actual['hbm_bytes_per_node']} HBM B/node"
            )
            for error in report["errors"]:
                print(f"    ERROR: {error}")
        print(f"wrote {_relative(output)}")
    return 0 if campaign["status"] == "pass" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
