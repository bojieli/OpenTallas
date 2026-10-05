#!/usr/bin/env python3
"""Certify shipped HBM/SRAM deployments against rebuilt artifacts.

The default case closes the deployment-scoped Qwen W4.6 gate.  It reads the
published neutral graph, capability, and shipped ABI 3.0 bundle; rebuilds the
physical plan and deployment twice; requires both rebuilds and the shipped
bytes to agree; runs the independent HBM/SRAM checker; and proves one-node
capacity and the shared chip's retained inter-chip endpoint.

Additional cases use five arguments::

    --case NAME PRODUCT KERNEL_IR DEPLOYMENT_DIR CAPABILITY_JSON

``PRODUCT`` is currently ``qwen`` or ``deepseek``.  DeepSeek certification
extends the common deployment checks with causal expert-dispatch,
sparse-gather, reduction, activation-transfer, and coordinated-commit
contracts.
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
    Control,
    Feature,
    InstructionFlag,
    Link,
    Major,
    NO_ID,
    Permission,
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

# A certificate is a claim about more than the three backend files that build
# it.  Admission, binary decoding, descriptor interpretation and the neutral IR
# all participate in the result.  Keep this list explicit so a correction in
# any of those layers invalidates an older certificate instead of inheriting
# its former ``pass`` label.
CERTIFICATE_SOURCE_PATHS: Mapping[str, str] = {
    "abi_builder": "runtime/abi3/builder.py",
    "abi_capability": "runtime/abi3/capability.py",
    "abi_constants": "runtime/abi3/constants.py",
    "abi_crc": "runtime/abi3/crc.py",
    "abi_deployment": "runtime/abi3/deployment.py",
    "abi_descriptors": "runtime/abi3/descriptors.py",
    "abi_layout": "runtime/abi3/layout.py",
    "abi_records": "runtime/abi3/records.py",
    "abi_verifier": "runtime/abi3/verifier.py",
    "backend_capability": "compiler/backends/hbm_sram/capability.py",
    "checker": "compiler/backends/hbm_sram/check.py",
    "ir_kernel": "compiler/ir/v3/kernel_ir.py",
    "ir_lowering": "compiler/ir/v3/lowering.py",
    "ir_numeric": "compiler/ir/v3/numeric.py",
    "lowering": "compiler/backends/hbm_sram/lower.py",
    "numeric_contracts": "compiler/backends/numeric_contracts.py",
    "planner": "compiler/backends/hbm_sram/plan.py",
    "campaign_tool": "tools/check_hbm_deployments.py",
}


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
        int(Link.COLLECTIVE),
        int(CollectiveOp.ALL_GATHER),
        frozenset(
            {
                "GATHER",
                "WINDOW_INDEX",
                # Amendment A30.  Absent from this set the draft-window
                # operator does not fail the deployment check -- it
                # silently stops being covered by it.
                "DSPARK_WINDOW_INDEX",
                "INDEX_TOPK",
                "ATTENTION_SPARSE",
            }
        ),
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


def _operator_objects(
    deployment: Deployment, instruction: Any
) -> tuple[set[int], set[int]]:
    """Memory objects read and written by one OPERATOR instruction."""

    descriptor_id = int(instruction.descriptor_id)
    if descriptor_id == NO_ID:
        return set(), set()
    descriptor = deployment.table[descriptor_id]
    if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
        return set(), set()

    def objects(prefix: str, count: int) -> set[int]:
        out: set[int] = set()
        for slot in range(count):
            view_id = int(descriptor.payload[f"{prefix}_view_{slot}"])
            if view_id == NO_ID:
                continue
            view = deployment.table[view_id]
            if view.descriptor_type != ExtendedDescriptorType.TENSOR_VIEW:
                continue
            out.add(int(view.primary_object_id))
        return out

    return objects("input", 4), objects("output", 2)


def _link_records(
    graph: KernelGraph,
    deployment: Deployment,
    instructions: Sequence[Any] | None = None,
) -> list[dict[str, Any]]:
    """Decode LINK sites and prove their received bytes reach an engine input.

    A route-class label is not evidence of communication.  For every LINK
    instruction this reconstructs both sides of the dataflow:

    * an earlier DMA, named by the LINK wait set, must write one of the
      communication's endpoint objects; and
    * the LINK completion must flow through any further LINK publication and a
      DMA unpack into an object read by a later non-DMA engine that waits for
      that unpack.

    Event/object provenance is propagated together.  Merely waiting for an
    event while reading an unrelated arena therefore cannot satisfy the check.
    ``instructions`` is injectable only for mutation tests; governed runs
    always decode the shipped program.
    """

    if instructions is None:
        _header, body = split_program(deployment.program)
        instructions = decode_body(body)
    instructions = list(instructions)
    communications = {
        descriptor_id: deployment.table[descriptor_id]
        for descriptor_id in deployment.table.ids_of_type(
            ExtendedDescriptorType.COMMUNICATION
        )
    }
    kernel_kind = {int(kernel.index): kernel.kind for kernel in graph.kernels}
    producer = {
        int(instruction.signal_event_id): index
        for index, instruction in enumerate(instructions)
        if int(instruction.signal_event_id) != NO_ID
    }
    object_rows = [_operator_objects(deployment, item) for item in instructions]

    records: list[dict[str, Any]] = []
    for index, instruction in enumerate(instructions):
        if int(instruction.major) != int(Major.LINK):
            continue
        communication = communications.get(int(instruction.descriptor_id))
        payload = communication.payload if communication is not None else {}
        local_object = int(payload.get("local_object_id", NO_ID))
        remote_object = int(payload.get("remote_object_id", NO_ID))
        endpoints = {
            value for value in (local_object, remote_object) if value != NO_ID
        }
        waits = _wait_events(deployment, int(instruction.wait_set_id))
        pack_indices = sorted(
            producer[event]
            for event in waits
            if event in producer
            and producer[event] < index
            and int(instructions[producer[event]].major) == int(Major.DMA)
            and bool(object_rows[producer[event]][1] & endpoints)
        )

        signal = int(instruction.signal_event_id)
        provenance: dict[int, set[int]] = (
            {signal: set(endpoints)} if signal != NO_ID and endpoints else {}
        )
        path: list[int] = []
        consumer_index: int | None = None
        consumer_source = NO_ID
        for follower_index in range(index + 1, len(instructions)):
            follower = instructions[follower_index]
            follower_waits = _wait_events(
                deployment, int(follower.wait_set_id)
            )
            carried = set().union(
                *(provenance[event] for event in follower_waits if event in provenance)
            ) if any(event in provenance for event in follower_waits) else set()
            if not carried:
                continue
            inputs, outputs = object_rows[follower_index]
            family = int(follower.major)
            follower_signal = int(follower.signal_event_id)
            if family == int(Major.LINK):
                chained = communications.get(int(follower.descriptor_id))
                if chained is None:
                    continue
                chained_objects = {
                    int(chained.payload[name])
                    for name in ("local_object_id", "remote_object_id")
                    if int(chained.payload[name]) != NO_ID
                }
                if not (carried & chained_objects):
                    continue
                if follower_signal != NO_ID:
                    provenance[follower_signal] = chained_objects
                path.append(follower_index)
                continue
            if family == int(Major.DMA):
                if not (inputs & carried) or not outputs:
                    continue
                if follower_signal != NO_ID:
                    provenance[follower_signal] = set(outputs)
                path.append(follower_index)
                continue
            if inputs & carried:
                consumer_index = follower_index
                consumer_source = int(follower.source_operation_id)
                path.append(follower_index)
                break

        source = int(instruction.source_operation_id)
        records.append(
            {
                "instruction_index": index,
                "subopcode": int(instruction.sub),
                "source_operation_id": source,
                "source_kind": kernel_kind.get(source, ""),
                "signal_event_id": signal,
                "wait_events": sorted(waits),
                "route_class": int(payload.get("route_class", -1)),
                "collective_op": int(payload.get("collective_op", -1)),
                "participant_count": int(payload.get("participant_count", 0)),
                "byte_extent": int(payload.get("byte_extent", 0)),
                "local_object_id": local_object,
                "remote_object_id": remote_object,
                "pack_instruction_indices": pack_indices,
                "consumer_instruction_index": consumer_index,
                "consumer_source_operation_id": consumer_source,
                "consumer_source_kind": kernel_kind.get(consumer_source, ""),
                "binding_path": path,
                "pack_bound": bool(pack_indices),
                "received_data_consumed": consumer_index is not None,
                "causally_bound": bool(pack_indices) and consumer_index is not None,
            }
        )
    return records


def _terminal_cluster_ordering(
    graph: KernelGraph,
    deployment: Deployment,
    instructions: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Reconstruct the fail-stop cluster completion ordering.

    Live model buffers need no STATE transaction.  The one ordering boundary
    that remains is ordinary execution ordering: all cluster work reaches the
    completion barrier, a local FENCE acquires that barrier, and TOKEN_APPEND
    waits for the fence before exposing the selected token.
    """

    if instructions is None:
        _header, body = split_program(deployment.program)
        instructions = decode_body(body)
    instructions = list(instructions)
    links = _link_records(graph, deployment, instructions)
    barriers = [
        record
        for record in links
        if int(record["route_class"])
        == _DEEPSEEK_ROUTE_CONTRACT["coordinated_commit"][0]
    ]
    errors: list[str] = []

    if len(barriers) != 1 or int(barriers[0]["signal_event_id"]) == NO_ID:
        errors.append("expected exactly one completion-signalled cluster barrier")
        barrier_index = -1
        barrier_event = NO_ID
    else:
        barrier_index = int(barriers[0]["instruction_index"])
        barrier_event = int(barriers[0]["signal_event_id"])

    producer_index = {
        int(instruction.signal_event_id): index
        for index, instruction in enumerate(instructions)
        if int(instruction.signal_event_id) != NO_ID
    }
    barrier_waits = (
        set(int(event) for event in barriers[0]["wait_events"])
        if len(barriers) == 1
        else set()
    )
    barrier_waits_for_work = bool(barrier_waits) and all(
        producer_index.get(event, len(instructions)) < barrier_index
        for event in barrier_waits
    )
    if not barrier_waits_for_work:
        errors.append("cluster completion barrier does not wait for prior work")

    fences = [
        (index, instruction)
        for index, instruction in enumerate(instructions)
        if int(instruction.major) == int(Major.CONTROL)
        and int(instruction.sub) == int(Control.FENCE)
        and barrier_event != NO_ID
        and barrier_event
        in _wait_events(deployment, int(instruction.wait_set_id))
    ]
    fence_ordered = (
        len(fences) == 1
        and fences[0][0] > barrier_index
        and int(fences[0][1].signal_event_id) != NO_ID
    )
    if not fence_ordered:
        errors.append("exactly one signalled FENCE must acquire the cluster barrier")
    fence_index = fences[0][0] if fence_ordered else -1
    fence_event = int(fences[0][1].signal_event_id) if fence_ordered else NO_ID

    append_sources = {
        int(kernel.index) for kernel in graph.kernels if kernel.kind == "TOKEN_APPEND"
    }
    appends = [
        (index, instruction)
        for index, instruction in enumerate(instructions)
        if int(instruction.source_operation_id) in append_sources
    ]
    appends_wait_for_fence = bool(append_sources) and {
        int(instruction.source_operation_id) for _index, instruction in appends
    } == append_sources and all(
        index > fence_index
        and fence_event != NO_ID
        and fence_event in _wait_events(deployment, int(instruction.wait_set_id))
        for index, instruction in appends
    )
    if not appends_wait_for_fence:
        errors.append("TOKEN_APPEND does not wait for the post-barrier FENCE")

    no_state_instructions = not any(
        int(instruction.major) == int(Major.STATE) for instruction in instructions
    )
    if not no_state_instructions:
        errors.append("live-buffer execution unexpectedly emits ABI STATE instructions")

    return {
        "ok": not errors,
        "errors": errors,
        "barrier_count": len(barriers),
        "barrier_event": barrier_event,
        "barrier_waits_for_work": barrier_waits_for_work,
        "fence_count": len(fences),
        "fence_event": fence_event,
        "fence_ordered_after_barrier": fence_ordered,
        "token_append_count": len(appends),
        "token_appends_wait_for_fence": appends_wait_for_fence,
        "no_state_instructions": no_state_instructions,
    }


def _scratch_serialization(
    deployment: Deployment,
    capability: Capability,
    instructions: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Prove that the one shared exchange object is reused serially.

    The functional simulator executes instructions synchronously, so a passing
    token run cannot establish this asynchronous scheduling property.  Decode
    the emitted operators, views, communication endpoints, waits, predicates,
    loop bodies and schedules instead.  Every access to the exported exchange
    object must be one complete adjacent pack/LINK/unpack triple, and every
    scratch DMA must use the same dedicated, one-credit physical DMA queue.

    ``instructions`` is injectable for mutation tests only.  Governed
    certificates always decode the shipped program.
    """

    if instructions is None:
        _header, body = split_program(deployment.program)
        instructions = decode_body(body)
    instructions = list(instructions)
    table = deployment.table
    errors: list[str] = []

    object_rows = [_operator_objects(deployment, item) for item in instructions]
    remote_hbm = {
        object_id
        for object_id in table.ids_of_type(ExtendedDescriptorType.MEMORY_OBJECT)
        if int(table[object_id].payload["storage_class"]) == int(StorageClass.HBM)
        and int(table[object_id].permissions) & int(Permission.REMOTE)
    }
    dma_objects = set().union(
        *(
            inputs | outputs
            for item, (inputs, outputs) in zip(instructions, object_rows)
            if int(item.major) == int(Major.DMA)
        )
    ) if instructions else set()
    communication_objects: set[int] = set()
    for descriptor_id in table.ids_of_type(ExtendedDescriptorType.COMMUNICATION):
        payload = table[descriptor_id].payload
        communication_objects.update(
            int(payload[name])
            for name in ("local_object_id", "remote_object_id")
            if int(payload[name]) != NO_ID
        )
    candidates = sorted(remote_hbm & dma_objects & communication_objects)
    if len(candidates) != 1:
        errors.append(
            "expected exactly one REMOTE HBM object shared by DMA and LINK, "
            f"found {candidates}"
        )
        return {
            "ok": False,
            "errors": errors,
            "exchange_object_ids": candidates,
            "triple_count": 0,
            "scratch_dma_count": 0,
            "schedule_ids": [],
            "queue_index": None,
            "issue_window": None,
            "max_outstanding": None,
            "dedicated_queue": False,
        }

    exchange = candidates[0]
    link_indices: list[int] = []
    for index, item in enumerate(instructions):
        if int(item.major) != int(Major.LINK) or int(item.descriptor_id) == NO_ID:
            continue
        descriptor = table[int(item.descriptor_id)]
        if descriptor.descriptor_type != ExtendedDescriptorType.COMMUNICATION:
            continue
        endpoints = {
            int(descriptor.payload[name])
            for name in ("local_object_id", "remote_object_id")
            if int(descriptor.payload[name]) != NO_ID
        }
        if exchange in endpoints:
            link_indices.append(index)

    predicate_mask = int(
        InstructionFlag.PREDICATED | InstructionFlag.PREDICATE_INVERT
    )

    def predicate_signature(item: Any) -> tuple[int, int]:
        return int(item.predicate_id), int(item.flags) & predicate_mask

    scratch_dma_indices = {
        index
        for index, (item, (inputs, outputs)) in enumerate(
            zip(instructions, object_rows)
        )
        if int(item.major) == int(Major.DMA) and exchange in (inputs | outputs)
    }
    triples: list[tuple[int, int, int]] = []
    for link_index in link_indices:
        if link_index == 0 or link_index + 1 >= len(instructions):
            errors.append(f"scratch LINK {link_index} has no adjacent pack/unpack")
            continue
        pack_index = link_index - 1
        unpack_index = link_index + 1
        pack = instructions[pack_index]
        link = instructions[link_index]
        unpack = instructions[unpack_index]
        pack_inputs, pack_outputs = object_rows[pack_index]
        unpack_inputs, unpack_outputs = object_rows[unpack_index]
        if (
            int(pack.major) != int(Major.DMA)
            or exchange not in pack_outputs
            or exchange in pack_inputs
        ):
            errors.append(
                f"scratch LINK {link_index} is not immediately preceded by a "
                "DMA that writes only into the exchange object"
            )
        if (
            int(unpack.major) != int(Major.DMA)
            or exchange not in unpack_inputs
            or exchange in unpack_outputs
        ):
            errors.append(
                f"scratch LINK {link_index} is not immediately followed by a "
                "DMA that reads only from the exchange object"
            )
        pack_event = int(pack.signal_event_id)
        link_event = int(link.signal_event_id)
        if pack_event == NO_ID or pack_event not in _wait_events(
            deployment, int(link.wait_set_id)
        ):
            errors.append(f"scratch LINK {link_index} does not wait for its pack")
        if link_event == NO_ID or link_event not in _wait_events(
            deployment, int(unpack.wait_set_id)
        ):
            errors.append(
                f"scratch unpack {unpack_index} does not wait for LINK {link_index}"
            )
        communication = table[int(link.descriptor_id)]
        if int(communication.payload["completion_event_id"]) != link_event:
            errors.append(
                f"scratch LINK {link_index} descriptor and instruction disagree "
                "on the terminal event"
            )
        if len(
            {
                predicate_signature(pack),
                predicate_signature(link),
                predicate_signature(unpack),
            }
        ) != 1:
            errors.append(
                f"scratch triple at LINK {link_index} does not share one predicate"
            )
        if len(
            {
                int(pack.source_operation_id),
                int(link.source_operation_id),
                int(unpack.source_operation_id),
            }
        ) != 1:
            errors.append(
                f"scratch triple at LINK {link_index} crosses source operations"
            )
        triples.append((pack_index, link_index, unpack_index))

    expected_touches = [index for triple in triples for index in triple]
    actual_touches = sorted(scratch_dma_indices | set(link_indices))
    if expected_touches != actual_touches:
        errors.append(
            "exchange-object accesses are not complete, ordered, non-interleaved "
            "pack/LINK/unpack triples"
        )

    # A loop may repeat complete triples, but it may not back-edge into their
    # middle or leave one half executed in another iteration.
    for descriptor_id in table.ids_of_type(ExtendedDescriptorType.LOOP_CONTROL):
        payload = table[descriptor_id].payload
        start = int(payload["body_start"])
        end = int(payload["body_end"])
        for triple in triples:
            inside = [start <= index < end for index in triple]
            if any(inside) and not all(inside):
                errors.append(
                    f"loop {descriptor_id} splits scratch triple {triple}"
                )

    forbidden_entries = {link for _pack, link, _unpack in triples} | {
        unpack for _pack, _link, unpack in triples
    }
    for index, item in enumerate(instructions):
        if (
            int(item.major) == int(Major.CONTROL)
            and int(item.sub) == int(Control.BRANCH)
            and int(item.control_id) in forbidden_entries
        ):
            errors.append(
                f"branch {index} enters the middle of a scratch exchange at "
                f"{int(item.control_id)}"
            )
    for entrypoint in deployment.entrypoints:
        if int(entrypoint["first_instruction"]) in forbidden_entries:
            errors.append(
                f"entrypoint {entrypoint['entrypoint_id']} enters the middle of "
                "a scratch exchange"
            )

    def schedule_for(index: int) -> tuple[int, Mapping[str, Any]] | None:
        item = instructions[index]
        descriptor = table[int(item.descriptor_id)]
        if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
            errors.append(f"scratch DMA {index} does not name an OPERATOR")
            return None
        schedule_id = int(descriptor.payload["schedule_id"])
        schedule = table[schedule_id]
        if schedule.descriptor_type != ExtendedDescriptorType.SCHEDULE:
            errors.append(
                f"scratch DMA {index} schedule {schedule_id} is not a SCHEDULE"
            )
            return None
        return schedule_id, schedule.payload

    schedules = {
        index: schedule
        for index in sorted(scratch_dma_indices)
        if (schedule := schedule_for(index)) is not None
    }
    schedule_ids = sorted({schedule_id for schedule_id, _payload in schedules.values()})
    queue_indices = {
        int(payload["queue_index"]) for _schedule_id, payload in schedules.values()
    }
    issue_windows = {
        int(payload["issue_window"]) for _schedule_id, payload in schedules.values()
    }
    outstanding = {
        int(payload["max_outstanding"])
        for _schedule_id, payload in schedules.values()
    }
    dma_profile = dict(capability.engines.get("dma", {}))
    dma_queues = int(dma_profile.get("queues", 0))
    queue_index = next(iter(queue_indices)) if len(queue_indices) == 1 else None
    if len(schedules) != len(scratch_dma_indices):
        errors.append("some scratch DMA has no valid schedule")
    if len(queue_indices) != 1 or queue_index is None:
        errors.append("scratch DMAs do not share one physical DMA queue")
    elif not 0 <= queue_index < dma_queues:
        errors.append(
            f"scratch queue {queue_index} is outside {dma_queues} DMA queues"
        )
    elif queue_index != dma_queues - 1:
        errors.append(
            f"scratch queue {queue_index} is not the reserved last DMA queue "
            f"{dma_queues - 1}"
        )
    if outstanding != {1}:
        errors.append(
            f"scratch DMA max_outstanding values are {sorted(outstanding)}, not [1]"
        )
    if issue_windows != {1}:
        errors.append(
            f"scratch DMA issue_window values are {sorted(issue_windows)}, not [1]"
        )

    dedicated = queue_index is not None
    if queue_index is not None:
        for index, item in enumerate(instructions):
            if int(item.major) != int(Major.DMA) or index in scratch_dma_indices:
                continue
            descriptor = table[int(item.descriptor_id)]
            if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
                continue
            schedule = table[int(descriptor.payload["schedule_id"])]
            if (
                schedule.descriptor_type == ExtendedDescriptorType.SCHEDULE
                and int(schedule.payload["queue_index"]) == queue_index
            ):
                dedicated = False
                errors.append(
                    f"non-scratch DMA {index} uses reserved scratch queue "
                    f"{queue_index}"
                )
    return {
        "ok": not errors,
        "errors": errors,
        "exchange_object_ids": candidates,
        "triple_count": len(triples),
        "scratch_dma_count": len(scratch_dma_indices),
        "schedule_ids": schedule_ids,
        "queue_index": queue_index,
        "issue_window": (
            next(iter(issue_windows)) if len(issue_windows) == 1 else None
        ),
        "max_outstanding": (
            next(iter(outstanding)) if len(outstanding) == 1 else None
        ),
        "dedicated_queue": dedicated,
    }


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


def _weight_locality(plan: Any) -> dict[str, Any]:
    """Independently reconstruct logical ownership and physical sources."""
    placements = {item.tensor_id: item for item in plan.weight_placements}
    tensor_modes: dict[str, set[str]] = {}
    role_modes: dict[str, set[str]] = {}
    for kernel in plan.kernels:
        for operand in kernel.operands:
            if operand.residence != "weight":
                continue
            mode = (
                "node_sharded"
                if int(plan.topology.node_count) > 1 and "node" in operand.terms
                else "replicated"
            )
            tensor_modes.setdefault(operand.tensor_id, set()).add(mode)
            role = placements[operand.tensor_id].role_key
            if role:
                role_modes.setdefault(role, set()).add(mode)

    expected: dict[str, str] = {}
    mismatches: list[str] = []
    for placement in plan.weight_placements:
        modes = set(tensor_modes.get(placement.tensor_id, ()))
        if not modes and placement.role_key:
            modes.update(role_modes.get(placement.role_key, ()))
            if placement.role_key.endswith(".scale"):
                modes.update(role_modes.get(placement.role_key[:-6], ()))
        mode = "node_sharded" if modes == {"node_sharded"} else "replicated"
        expected[placement.tensor_id] = mode
        shard_count = (
            int(plan.topology.node_count) if mode == "node_sharded" else 1
        )
        if (
            placement.residency != mode
            or int(placement.shard_count) != shard_count
        ):
            mismatches.append(placement.tensor_id)

    replicated = 0
    node_sharded = 0
    materialized_node_sharded = 0
    fallback_replicated = 0
    local_by_group: dict[str, int] = {}
    group_mismatches: list[str] = []
    materialization_mismatches: list[str] = []
    source_mismatches: list[str] = []
    nodes = int(plan.topology.node_count)

    def identity(segment: Any) -> tuple[str, int, int, str]:
        return (
            str(segment.path),
            int(segment.file_offset),
            int(segment.bytes),
            str(segment.sha256),
        )

    for group in plan.weight_groups:
        tensor_bytes: dict[str, int] = {}
        global_ranges: dict[str, list[tuple[str, int, int, str]]] = {}
        for segment in group.segments:
            tensor_bytes[segment.tensor_id] = (
                tensor_bytes.get(segment.tensor_id, 0) + int(segment.bytes)
            )
            global_ranges.setdefault(segment.tensor_id, []).append(identity(segment))
        modes = {expected.get(tensor_id, "replicated") for tensor_id in tensor_bytes}
        group_mode = next(iter(modes)) if len(modes) == 1 else "mixed"
        if group.residency != group_mode:
            group_mismatches.append(group.group_id)

        physical_modes: set[str] = set()
        node_maps = tuple(getattr(group, "node_segments", ()))
        if node_maps:
            if len(node_maps) != nodes:
                source_mismatches.append(
                    f"{group.group_id}: {len(node_maps)} source maps for {nodes} nodes"
                )
            sizes = [sum(int(segment.bytes) for segment in item) for item in node_maps]
            if not sizes or len(set(sizes)) != 1:
                source_mismatches.append(
                    f"{group.group_id}: node source maps have unequal byte extents"
                )
                local = int(getattr(group, "local_size_bytes", 0))
            else:
                local = sizes[0]
            if local != int(getattr(group, "local_size_bytes", 0)):
                source_mismatches.append(
                    f"{group.group_id}: source maps cover {local}, plan declares "
                    f"{getattr(group, 'local_size_bytes', 0)}"
                )
        else:
            local = int(group.size_bytes)

        for tensor_id, size in tensor_bytes.items():
            if expected.get(tensor_id) == "node_sharded":
                node_sharded += size
            else:
                replicated += size

            physical = "replicated"
            if node_maps and len(node_maps) == nodes:
                per_node = [
                    [identity(segment) for segment in item if segment.tensor_id == tensor_id]
                    for item in node_maps
                ]
                logical = global_ranges[tensor_id]
                if all(item == logical for item in per_node):
                    physical = "replicated"
                elif [entry for item in per_node for entry in item] == logical:
                    byte_extents = [sum(entry[2] for entry in item) for item in per_node]
                    if len(set(byte_extents)) == 1 and byte_extents[0] * nodes == size:
                        physical = "node_sharded"
                    else:
                        source_mismatches.append(
                            f"{group.group_id}/{tensor_id}: shard byte extents are unequal"
                        )
                else:
                    source_mismatches.append(
                        f"{group.group_id}/{tensor_id}: node maps neither replicate "
                        "nor partition the authenticated segment order"
                    )
            declared_physical = getattr(
                placements[tensor_id], "materialization", "replicated"
            )
            if declared_physical != physical:
                materialization_mismatches.append(tensor_id)
            physical_modes.add(physical)
            if physical == "node_sharded":
                materialized_node_sharded += size
            elif expected.get(tensor_id) == "node_sharded":
                fallback_replicated += size

        actual_group_materialization = (
            next(iter(physical_modes))
            if len(physical_modes) == 1
            else "mixed"
        )
        if getattr(group, "materialization", "replicated") != actual_group_materialization:
            materialization_mismatches.append(group.group_id)
        local_by_group[group.group_id] = local
    return {
        "replicated_bytes": replicated,
        "node_sharded_bytes": node_sharded,
        "materialized_node_sharded_bytes": materialized_node_sharded,
        "fallback_replicated_bytes": fallback_replicated,
        "bytes_per_node": sum(local_by_group.values()),
        "local_by_group": local_by_group,
        "placement_mismatches": mismatches,
        "group_mismatches": group_mismatches,
        "materialization_mismatches": materialization_mismatches,
        "source_mismatches": source_mismatches,
    }


def _local_hbm_footprint(
    plan: Any, locality: Mapping[str, Any], communication_scratch: int
) -> dict[str, Any]:
    """Pack the independently reconstructed node-local payload at 4 KiB."""
    resident = 0
    payload = 0
    state_placement_errors: list[str] = []

    def reserve(size: int) -> None:
        nonlocal resident, payload
        if size <= 0:
            return
        resident = ((resident + 4095) // 4096) * 4096 + size
        payload += size

    local_by_group = locality["local_by_group"]
    for group in plan.weight_groups:
        reserve(int(local_by_group[group.group_id]))
    for constant in plan.generated_constants:
        reserve(int(constant.size_bytes))
    for state in plan.states:
        keys = (
            f"state.{state.physical_id}.direct",
            f"state.{state.physical_id}.committed",
            f"state.{state.physical_id}.prepared",
        )
        present = tuple(key for key in keys if key in plan.hbm_map)
        if present not in {(keys[0],), (keys[1], keys[2])}:
            state_placement_errors.append(
                f"{state.physical_id}: expected one direct placement or a "
                f"committed/prepared pair, found {list(present)!r}"
            )
        for key in present:
            placement = plan.hbm_map[key]
            if int(placement.size_bytes) != int(state.size_bytes):
                state_placement_errors.append(
                    f"{key}: placement holds {placement.size_bytes} bytes, "
                    f"state requires {state.size_bytes}"
                )
            reserve(int(placement.size_bytes))
    for arena in plan.arena_slots:
        reserve(int(arena.size_bytes))
    if int(plan.topology.node_count) > 1:
        reserve(64)
    compressor_ratios = {
        int(kernel.aux[1]) if len(kernel.aux) > 1 else 0
        for kernel in plan.kernels
        if kernel.kind == "COMPRESS_STATE_UPDATE"
    }
    for ratio in sorted(compressor_ratios):
        if ratio <= 0:
            state_placement_errors.append(
                f"COMPRESS_STATE_UPDATE declares invalid ratio {ratio}"
            )
            continue
        reserve(4)
    reserve(communication_scratch)
    return {
        "bytes_per_node": resident,
        "payload_bytes_per_node": payload,
        "alignment_bytes_per_node": resident - payload,
        "compressor_boundary_bytes_per_node": 4 * len(compressor_ratios),
        "state_placement_errors": state_placement_errors,
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
    remote_hbm_sizes = [
        int(shipped.table[object_id].payload["size_bytes"])
        for object_id in shipped.table.ids_of_type(
            ExtendedDescriptorType.MEMORY_OBJECT
        )
        if int(shipped.table[object_id].payload["storage_class"])
        == int(StorageClass.HBM)
        and int(shipped.table[object_id].permissions) & int(Permission.REMOTE)
    ]
    communication_scratch = max(remote_hbm_sizes, default=0)
    locality = _weight_locality(first_plan)
    local_hbm = _local_hbm_footprint(
        first_plan, locality, communication_scratch
    )

    _header, body = split_program(shipped.program)
    instructions = decode_body(body)
    communication_count = len(
        shipped.table.ids_of_type(ExtendedDescriptorType.COMMUNICATION)
    )
    link_records = _link_records(graph, shipped, instructions)
    link_count = len(link_records)
    scratch_serialization: dict[str, Any] | None = None
    terminal_ordering: dict[str, Any] | None = None

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
        "weight_residency",
        not locality["placement_mismatches"]
        and not locality["group_mismatches"]
        and not locality["materialization_mismatches"]
        and not locality["source_mismatches"]
        and int(first_plan.proofs["replicated_weight_bytes"])
        == int(locality["replicated_bytes"])
        and int(first_plan.proofs["node_sharded_weight_bytes"])
        == int(locality["node_sharded_bytes"])
        and int(first_plan.proofs["materialized_node_sharded_weight_bytes"])
        == int(locality["materialized_node_sharded_bytes"])
        and int(first_plan.proofs["fallback_replicated_weight_bytes"])
        == int(locality["fallback_replicated_bytes"])
        and int(first_plan.proofs["weight_bytes_per_node"])
        == int(locality["bytes_per_node"]),
        "weight replica/shard declarations or authenticated node sources do "
        "not match the node-selected views",
    )
    generated_constant_bytes = sum(
        int(constant.size_bytes) for constant in first_plan.generated_constants
    )
    require(
        "generated_constants_accounted",
        int(first_plan.proofs["generated_constant_bytes"])
        == generated_constant_bytes,
        "generated HBM constants are omitted from the capacity proof",
    )
    require(
        "node_local_hbm_accounting",
        not local_hbm["state_placement_errors"]
        and int(local_hbm["bytes_per_node"])
        == int(first_plan.proofs["hbm_bytes_per_node"])
        and int(hbm_inventory["address_span"])
        == int(first_plan.proofs["hbm_bytes_per_node"])
        and int(local_hbm["alignment_bytes_per_node"])
        == int(first_plan.proofs["hbm_alignment_bytes"])
        and communication_scratch
        == int(first_plan.proofs["communication_scratch_bytes"]),
        "node-local HBM payload, emitted address span, alignment, or exchange "
        "scratch was miscounted: "
        + "; ".join(local_hbm["state_placement_errors"]),
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
    # Capacity is the actual emitted node-local address map for every product.
    # Substituting a logical residency proof for a larger descriptor span is
    # exactly the mismatch this certificate exists to catch.
    hbm_required = int(hbm_inventory["address_span"])
    rolling_slots = [
        slot for slot in first_plan.arena_slots if slot.rolling_group
    ]
    routed_weight_operands = [
        operand
        for kernel in first_plan.kernels
        for operand in kernel.operands
        if kernel.kind == "ROUTED_MATMUL"
        and operand.direction == "in"
        and operand.slot == 1
        and int(operand.bank) > 0
    ]
    expert_banks = {int(operand.bank) for operand in routed_weight_operands}
    expert_shards = {
        int(operand.bank_shard)
        for operand in routed_weight_operands
        if int(operand.bank_shard) > 0
    }
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
        scratch_serialization = _scratch_serialization(
            shipped, capability, instructions
        )
        terminal_ordering = _terminal_cluster_ordering(
            graph, shipped, instructions
        )
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
            if name not in {"coordinated_commit"}:
                require(
                    f"{name}_received_data_consumed",
                    bool(matching)
                    and all(
                        bool(record["causally_bound"])
                        and int(record["byte_extent"]) > 0
                        for record in matching
                    ),
                    f"DeepSeek {name} traffic is not packed from its producer "
                    "and consumed through the received object by a waiting engine",
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
        data_link_count = sum(
            int(record["route_class"])
            != _DEEPSEEK_ROUTE_CONTRACT["coordinated_commit"][0]
            for record in link_records
        )
        require(
            "communication_scratch_serialized",
            bool(scratch_serialization["ok"])
            and bool(scratch_serialization["dedicated_queue"])
            and int(scratch_serialization["triple_count"]) == data_link_count,
            "DeepSeek shared communication scratch is not one complete "
            "pack/LINK/unpack triple per data-bearing site on a dedicated "
            "one-outstanding DMA queue: "
            + "; ".join(scratch_serialization["errors"]),
        )

        require(
            "one_completion_barrier",
            int(terminal_ordering["barrier_count"]) == 1
            and int(terminal_ordering["barrier_event"]) != NO_ID,
            "DeepSeek cluster does not publish exactly one completion-signalled barrier",
        )
        require(
            "completion_barrier_waits_for_work",
            bool(terminal_ordering["barrier_waits_for_work"]),
            "cluster completion barrier is issued without waiting for prior work",
        )
        require(
            "terminal_fence_waits_for_barrier",
            bool(terminal_ordering["fence_ordered_after_barrier"]),
            "terminal FENCE does not acquire the cluster completion barrier",
        )
        require(
            "token_append_waits_for_terminal_fence",
            bool(terminal_ordering["token_appends_wait_for_fence"]),
            "TOKEN_APPEND does not wait for the post-barrier FENCE",
        )
        require(
            "no_model_state_transactions",
            bool(terminal_ordering["no_state_instructions"]),
            "live-buffer DeepSeek execution unexpectedly emits ABI STATE instructions",
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
            "route_class_counts": {
                str(route): sum(
                    int(record["route_class"]) == route for record in link_records
                )
                for route in sorted(
                    {int(record["route_class"]) for record in link_records}
                )
            },
            "expert_bank_size": (
                next(iter(expert_banks)) if len(expert_banks) == 1 else 0
            ),
            "experts_per_node": (
                next(iter(expert_shards)) if len(expert_shards) == 1 else 0
            ),
            "deployed_hbm_address_span": int(hbm_inventory["address_span"]),
            "deployed_hbm_object_count": int(hbm_inventory["object_count"]),
            "deployed_hbm_payload_bytes": int(hbm_inventory["payload_bytes"]),
            "hbm_bytes_per_node": hbm_required,
            "hbm_available_per_node": hbm_available,
            "hbm_headroom_per_node": hbm_available - hbm_required,
            "plan_hbm_bytes_per_node": plan_hbm_required,
            "replicated_weight_bytes": int(locality["replicated_bytes"]),
            "node_sharded_weight_bytes": int(locality["node_sharded_bytes"]),
            "materialized_node_sharded_weight_bytes": int(
                locality["materialized_node_sharded_bytes"]
            ),
            "fallback_replicated_weight_bytes": int(
                locality["fallback_replicated_bytes"]
            ),
            "node_indexed_weight_objects": sum(
                source.kind == "node_segments"
                for source in shipped.objects.values()
            ),
            "weight_bytes_per_node": int(locality["bytes_per_node"]),
            "weight_replication_overhead_per_node": int(
                first_plan.proofs["weight_replication_overhead_per_node"]
            ),
            "generated_constant_bytes": generated_constant_bytes,
            "communication_scratch_bytes": communication_scratch,
            "communication_scratch_triples": (
                int(scratch_serialization["triple_count"])
                if scratch_serialization is not None
                else 0
            ),
            "communication_scratch_dma_queue": (
                scratch_serialization["queue_index"]
                if scratch_serialization is not None
                else None
            ),
            "communication_scratch_dma_max_outstanding": (
                scratch_serialization["max_outstanding"]
                if scratch_serialization is not None
                else None
            ),
            "hbm_alignment_bytes_per_node": int(
                local_hbm["alignment_bytes_per_node"]
            ),
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
                "scratch_serialization": scratch_serialization,
                "terminal_ordering": terminal_ordering,
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
        name: REPOSITORY_ROOT / relative
        for name, relative in CERTIFICATE_SOURCE_PATHS.items()
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
