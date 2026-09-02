"""Independent legality report for an HBM/SRAM ABI 3.0 deployment.

TA-HBM-3.0 section 4.4: *the checker must not import allocator, scheduler,
lowering, or expected-result code*.  This module therefore imports only the
frozen contracts -- the neutral IR schema, the frozen kernel-to-engine table and
the ABI 3.0 record decoders -- and reconstructs, from the graph alone, what the
deployment ought to contain.  It never imports :mod:`.lower` or :mod:`.plan`;
the weight grouping, the layer banding and the program shape are re-derived here
by a second implementation, and a disagreement between the two is reported
rather than reconciled.

What it proves
--------------
1. every neutral kernel reaches an engine operation, with the family and
   subopcode the frozen table assigns and no other;
2. weights are zero-copy: every declared checkpoint range appears exactly once,
   in an immutable object, with its digest intact, and no byte is duplicated,
   dropped or relaid out;
3. per-layer weight roles are one object each with a constant stride, which is
   the precondition for the layer loop;
4. the program is loop-compressed: the layer count does not appear in the
   instruction count, and the reconstructed loop nest matches the descriptors;
5. exactly one topology descriptor, agreeing with the capability, with cluster
   traffic present if and only if there is more than one node;
6. every state resource the graph declares is bound to a state descriptor whose
   prepare/commit pairs close; and
7. the deployment passes the frozen ABI 3.0 verifier.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from compiler.ir.v3.kernel_ir import (
    CheckpointBinding,
    Kernel,
    KernelGraph,
    Symbolic,
    Tensor,
)
from compiler.ir.v3.lowering import ABSENT_OPERANDS, abi_input_slots, engine_for
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Control,
    Dma,
    Major,
    NO_ID,
    Permission,
    Route,
    Selection,
    State,
    StorageClass,
    Tensor as TensorOp,
    TopologyClass,
    Vector,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import ExtendedDescriptorType, SelectorKind, Symbol
from runtime.abi3.records import decode_body, split_program
from runtime.abi3.verifier import verify_deployment

HBM_DEPLOYMENT_CHECK_SCHEMA = "opentallas.hbm_sram.deployment_check.v1"

#: Independent copy of the neutral-dtype table.  Duplicated on purpose: a
#: checker that shares the backend's tables cannot catch the backend's table
#: being wrong.
_DTYPE_BITS: Mapping[str, int] = {
    "bf16": 16,
    "fp16": 16,
    "fp32": 32,
    "fp8_e4m3fn": 8,
    "fp8_e5m2": 8,
    "mxfp4_e2m1": 4,
    "e8m0": 8,
    "i8": 8,
    "u8": 8,
    "bool": 8,
    "i32": 32,
    "u32": 32,
    "i64": 64,
    "u64": 64,
}

#: Same slack the placement rule uses when merging file-adjacent ranges.
_MERGE_SLACK = 4096

#: Kernel kinds the backend is allowed to fold into the hoisted state
#: transaction rather than emitting as an engine operator.
_TRANSACTION_KINDS = frozenset({"STATE_PREPARE", "STATE_COMMIT", "STATE_READ"})


def _wait_events(table: Any, wait_set_id: int) -> set[int]:
    if wait_set_id == NO_ID or not 0 <= wait_set_id < len(table):
        return set()
    descriptor = table[wait_set_id]
    if descriptor.descriptor_type != ExtendedDescriptorType.EVENT_WAIT_SET:
        return set()
    count = int(descriptor.payload["producer_count"])
    return {
        int(descriptor.payload[f"producer_{slot}"]) for slot in range(count)
    }


def _operator_io_objects(table: Any, instruction: Any) -> tuple[set[int], set[int]]:
    descriptor_id = int(instruction.descriptor_id)
    if descriptor_id == NO_ID or not 0 <= descriptor_id < len(table):
        return set(), set()
    operator = table[descriptor_id]
    if operator.descriptor_type != ExtendedDescriptorType.OPERATOR:
        return set(), set()

    def collect(prefix: str, count: int) -> set[int]:
        objects: set[int] = set()
        for slot in range(count):
            view_id = int(operator.payload[f"{prefix}_view_{slot}"])
            if view_id == NO_ID or not 0 <= view_id < len(table):
                continue
            view = table[view_id]
            if view.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW:
                objects.add(int(view.primary_object_id))
        return objects

    return collect("input", 4), collect("output", 2)


def _check_shared_exchange_schedule(
    deployment: Deployment,
    capability: Capability,
    instructions: Sequence[Any],
) -> dict[str, Any]:
    """Independently prove the one-buffer cluster exchange is serialized.

    The physical plan reserves only the largest communication array.  That is
    sound only when every pack/LINK/unpack use of the exported HBM object is a
    complete causal triple on one dedicated DMA queue with one outstanding
    request.  Reconstruct the invariant from emitted records rather than
    trusting the planner or the deployment-certificate tool.
    """

    table = deployment.table
    errors: list[str] = []
    object_rows = [_operator_io_objects(table, item) for item in instructions]
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
            "expected one REMOTE HBM exchange object shared by DMA and LINK, "
            f"found {candidates}"
        )
        return {"ok": False, "errors": errors, "exchange_object_ids": candidates}

    exchange = candidates[0]
    scratch_dmas = {
        index
        for index, (item, (inputs, outputs)) in enumerate(
            zip(instructions, object_rows)
        )
        if int(item.major) == int(Major.DMA) and exchange in (inputs | outputs)
    }
    links: list[int] = []
    for index, item in enumerate(instructions):
        if int(item.major) != int(Major.LINK):
            continue
        descriptor_id = int(item.descriptor_id)
        if descriptor_id == NO_ID or not 0 <= descriptor_id < len(table):
            continue
        descriptor = table[descriptor_id]
        if descriptor.descriptor_type != ExtendedDescriptorType.COMMUNICATION:
            continue
        endpoints = {
            int(descriptor.payload[name])
            for name in ("local_object_id", "remote_object_id")
            if int(descriptor.payload[name]) != NO_ID
        }
        if exchange in endpoints:
            links.append(index)

    expected_touches: set[int] = set()
    for link_index in links:
        if link_index == 0 or link_index + 1 >= len(instructions):
            errors.append(f"exchange LINK {link_index} has no adjacent pack/unpack")
            continue
        pack_index, unpack_index = link_index - 1, link_index + 1
        pack, link, unpack = (
            instructions[pack_index],
            instructions[link_index],
            instructions[unpack_index],
        )
        pack_inputs, pack_outputs = object_rows[pack_index]
        unpack_inputs, unpack_outputs = object_rows[unpack_index]
        if (
            int(pack.major) != int(Major.DMA)
            or exchange not in pack_outputs
            or exchange in pack_inputs
        ):
            errors.append(f"exchange LINK {link_index} has no adjacent DMA pack")
        if (
            int(unpack.major) != int(Major.DMA)
            or exchange not in unpack_inputs
            or exchange in unpack_outputs
        ):
            errors.append(f"exchange LINK {link_index} has no adjacent DMA unpack")
        pack_event = int(pack.signal_event_id)
        link_event = int(link.signal_event_id)
        if pack_event == NO_ID or pack_event not in _wait_events(
            table, int(link.wait_set_id)
        ):
            errors.append(f"exchange LINK {link_index} does not wait for its pack")
        if link_event == NO_ID or link_event not in _wait_events(
            table, int(unpack.wait_set_id)
        ):
            errors.append(f"exchange unpack {unpack_index} does not wait for LINK")
        expected_touches.update((pack_index, unpack_index))

    if scratch_dmas != expected_touches:
        errors.append(
            "exchange-object DMA accesses are not complete adjacent "
            "pack/LINK/unpack triples"
        )

    schedules: dict[int, Mapping[str, Any]] = {}
    for index in sorted(scratch_dmas):
        operator_id = int(instructions[index].descriptor_id)
        if not 0 <= operator_id < len(table):
            errors.append(f"exchange DMA {index} names no operator")
            continue
        operator = table[operator_id]
        if operator.descriptor_type != ExtendedDescriptorType.OPERATOR:
            errors.append(f"exchange DMA {index} names no OPERATOR")
            continue
        schedule_id = int(operator.payload["schedule_id"])
        if not 0 <= schedule_id < len(table):
            errors.append(f"exchange DMA {index} names no schedule")
            continue
        schedule = table[schedule_id]
        if schedule.descriptor_type != ExtendedDescriptorType.SCHEDULE:
            errors.append(f"exchange DMA {index} names no SCHEDULE")
            continue
        schedules[index] = schedule.payload

    queue_indices = {int(p["queue_index"]) for p in schedules.values()}
    issue_windows = {int(p["issue_window"]) for p in schedules.values()}
    outstanding = {int(p["max_outstanding"]) for p in schedules.values()}
    dma_queues = int(capability.engines.get("dma", {}).get("queues", 0))
    queue_index = next(iter(queue_indices)) if len(queue_indices) == 1 else None
    if len(schedules) != len(scratch_dmas):
        errors.append("some exchange DMA has no valid schedule")
    if queue_index is None or queue_index != dma_queues - 1:
        errors.append(
            f"exchange DMAs use queues {sorted(queue_indices)}, expected the "
            f"dedicated last DMA queue {dma_queues - 1}"
        )
    if issue_windows != {1}:
        errors.append(f"exchange DMA issue_window values are {sorted(issue_windows)}")
    if outstanding != {1}:
        errors.append(
            f"exchange DMA max_outstanding values are {sorted(outstanding)}"
        )
    if queue_index is not None:
        for index, item in enumerate(instructions):
            if int(item.major) != int(Major.DMA) or index in scratch_dmas:
                continue
            operator_id = int(item.descriptor_id)
            if not 0 <= operator_id < len(table):
                continue
            operator = table[operator_id]
            if operator.descriptor_type != ExtendedDescriptorType.OPERATOR:
                continue
            schedule = table[int(operator.payload["schedule_id"])]
            if (
                schedule.descriptor_type == ExtendedDescriptorType.SCHEDULE
                and int(schedule.payload["queue_index"]) == queue_index
            ):
                errors.append(
                    f"non-exchange DMA {index} uses reserved queue {queue_index}"
                )
    return {
        "ok": not errors,
        "errors": errors,
        "exchange_object_ids": candidates,
        "link_count": len(links),
        "scratch_dma_count": len(scratch_dmas),
        "queue_index": queue_index,
        "issue_window": next(iter(issue_windows)) if len(issue_windows) == 1 else None,
        "max_outstanding": next(iter(outstanding)) if len(outstanding) == 1 else None,
    }


def check_deployment(
    graph: KernelGraph, deployment: Deployment, capability: Capability
) -> dict[str, Any]:
    """Return the lane's independent legality report for one deployment."""
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, ok: bool, message: str) -> bool:
        checks[name] = checks.get(name, True) and bool(ok)
        if not ok:
            errors.append(message)
        return bool(ok)

    table = deployment.table
    header, body = split_program(deployment.program)
    instructions = decode_body(body)

    descriptors_of = {
        kind: [table[i] for i in table.ids_of_type(kind)]
        for kind in ExtendedDescriptorType
    }
    operators = descriptors_of[ExtendedDescriptorType.OPERATOR]
    objects = descriptors_of[ExtendedDescriptorType.MEMORY_OBJECT]
    loops = descriptors_of[ExtendedDescriptorType.LOOP_CONTROL]
    views = descriptors_of[ExtendedDescriptorType.TENSOR_VIEW]
    states = descriptors_of[ExtendedDescriptorType.STATE]
    topologies = descriptors_of[ExtendedDescriptorType.TOPOLOGY]
    communications = descriptors_of[ExtendedDescriptorType.COMMUNICATION]

    tensors = {t.tensor_id: t for t in graph.tensors}
    bands = _reconstruct_bands(graph, tensors)
    expected_groups, expected_extents, expected_members = _reconstruct_weight_groups(
        graph, tensors, bands
    )
    first_iteration = {
        b["layers"][offset] for b in bands for offset in range(b["period"])
    }
    representative = {
        k.index for k in graph.kernels if k.layer is None or k.layer in first_iteration
    }
    emitted_kernels = {
        k for k in representative if graph.kernels[k].kind not in _TRANSACTION_KINDS
    }

    # -- 1. engine mapping ------------------------------------------------
    # Only an operator named by an instruction can witness a graph kernel's
    # lowering.  Descriptor tables may legitimately contain unreferenced
    # records, and accepting one of those here lets a digest-consistent decoy
    # hide a malformed view on the operator the program actually executes.
    # Bind both provenance fields and the executed opcode before admitting the
    # descriptor to the witness set; the generic verifier checks the same wire
    # structure, while this check gives the independent semantic lane a
    # fail-closed association with the neutral graph.
    by_kernel: dict[int, list[Any]] = {}
    reachable_ids: set[int] = set()
    graph_kernel_ids = {kernel.index for kernel in graph.kernels}
    for instruction_index, instruction in enumerate(instructions):
        descriptor_id = int(instruction.descriptor_id)
        if descriptor_id == NO_ID or not 0 <= descriptor_id < len(table):
            continue
        descriptor = table[descriptor_id]
        if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
            continue
        instruction_source = int(instruction.source_operation_id)
        descriptor_source = int(descriptor.payload["source_kernel_id"])
        source_ok = (
            instruction_source in graph_kernel_ids
            and instruction_source == descriptor_source
        )
        require(
            "reachable_operator_source_binding",
            source_ok,
            f"instruction {instruction_index} executes operator {descriptor_id} "
            f"with source operation {instruction_source}, but the descriptor "
            f"names source kernel {descriptor_source}",
        )
        engine_ok = (
            int(instruction.major) == int(descriptor.payload["engine_family"])
            and int(instruction.sub) == int(descriptor.payload["engine_sub"])
        )
        require(
            "reachable_operator_engine_binding",
            engine_ok,
            f"instruction {instruction_index} executes "
            f"{int(instruction.major):#x}.{int(instruction.sub):#x}, but operator "
            f"{descriptor_id} declares "
            f"{int(descriptor.payload['engine_family']):#x}."
            f"{int(descriptor.payload['engine_sub']):#x}",
        )
        if not source_ok or not engine_ok or descriptor_id in reachable_ids:
            continue
        reachable_ids.add(descriptor_id)
        by_kernel.setdefault(instruction_source, []).append(descriptor)
    for index in sorted(emitted_kernels):
        kernel = graph.kernels[index]
        engine = engine_for(kernel.kind)
        found = by_kernel.get(index, [])
        if not require(
            "kernel_coverage",
            bool(found),
            f"kernel {index} ({kernel.kernel_id}) reaches no engine operator",
        ):
            continue
        families = {
            (d.payload["engine_family"], d.payload["engine_sub"]) for d in found
        }
        require(
            "engine_mapping",
            (int(engine.family), int(engine.sub)) in families,
            f"kernel {index} ({kernel.kind}) must lower to "
            f"{Major(engine.family).name}.{int(engine.sub)}, found {sorted(families)}",
        )
    for index in sorted(representative - emitted_kernels):
        kernel = graph.kernels[index]
        engine = engine_for(kernel.kind)
        require(
            "state_kernel_coverage",
            any(
                i.major == int(engine.family) and i.sub == int(engine.sub)
                for i in instructions
            ),
            f"state kernel {index} ({kernel.kind}) has no matching instruction",
        )

    # -- 2/3. zero-copy weights and role stacks ---------------------------
    immutable = [
        d
        for d in objects
        if d.permissions & Permission.IMMUTABLE
        and d.payload["storage_class"] == int(StorageClass.HBM)
    ]
    generated = [
        d
        for d in immutable
        if (deployment.objects.get(d.descriptor_id) or _NO_SOURCE).kind == "generated"
    ]
    _check_generated_constants(
        graph, deployment, generated, require, errors, capability
    )
    immutable = [d for d in immutable if d not in generated]
    actual_groups: list[list[tuple[str, int, int, str | None]]] = []
    actual_group_ids: list[int] = []
    seen_ranges: dict[tuple[str, int, int], int] = {}
    for descriptor in immutable:
        source = deployment.objects.get(descriptor.descriptor_id)
        if source is None or source.kind not in {"segments", "node_segments"}:
            errors.append(
                f"object {descriptor.descriptor_id} holds weights but is not a "
                "zero-copy shared or node-indexed segments source"
            )
            checks["zero_copy_weights"] = False
            continue
        maps = (
            source.node_segments
            if source.kind == "node_segments"
            else (source.segments,)
        )
        if source.kind == "node_segments" and len(topologies) == 1:
            require(
                "node_source_count",
                len(maps) == int(topologies[0].payload["node_count"]),
                f"object {descriptor.descriptor_id} declares {len(maps)} node "
                f"source maps for a {topologies[0].payload['node_count']}-node "
                "topology",
            )
        group_ranges: dict[tuple[str, int, int], str | None] = {}
        for node_id, segments in enumerate(maps):
            require(
                "object_size_matches_segments",
                sum(segment.bytes for segment in segments)
                == descriptor.payload["size_bytes"],
                f"object {descriptor.descriptor_id} node {node_id} declares "
                f"{descriptor.payload['size_bytes']} bytes but its segments "
                f"cover {sum(segment.bytes for segment in segments)}",
            )
            node_seen: set[tuple[str, int, int]] = set()
            for segment in segments:
                key = (segment.path, segment.offset, segment.bytes)
                if key in node_seen:
                    errors.append(
                        f"checkpoint range {key} occurs twice in object "
                        f"{descriptor.descriptor_id}'s node {node_id} map"
                    )
                    checks["zero_copy_weights"] = False
                node_seen.add(key)
                prior_digest = group_ranges.get(key)
                if prior_digest is not None and prior_digest != segment.sha256:
                    errors.append(
                        f"checkpoint range {key} has inconsistent digests in "
                        f"object {descriptor.descriptor_id}'s node maps"
                    )
                    checks["zero_copy_weights"] = False
                group_ranges[key] = segment.sha256
        group = [(*key, digest) for key, digest in group_ranges.items()]
        for path, offset, size, _digest in group:
            key = (path, offset, size)
            if key in seen_ranges:
                errors.append(
                    f"checkpoint range {key} is materialised twice (objects "
                    f"{seen_ranges[key]} and {descriptor.descriptor_id}); a "
                    "zero-copy placement never duplicates a byte"
                )
                checks["zero_copy_weights"] = False
            seen_ranges[key] = descriptor.descriptor_id
        actual_groups.append(group)
        actual_group_ids.append(descriptor.descriptor_id)
    checks.setdefault("zero_copy_weights", True)

    declared = {
        rng
        for t in graph.tensors
        if t.binding is not None
        for rng in _binding_ranges(t.binding)
    }
    materialised = {tuple(seg) for group in actual_groups for seg in group}
    missing = declared - materialised
    extra = materialised - declared
    require(
        "every_weight_placed",
        not missing,
        f"{len(missing)} declared checkpoint ranges are not placed in any object",
    )
    require(
        "no_invented_weights",
        not extra,
        f"{len(extra)} object segments do not correspond to a declared binding",
    )

    expected_sets = sorted(
        sorted(tuple(s) for s in group) for group in expected_groups.values()
    )
    actual_sets = sorted(sorted(tuple(s) for s in group) for group in actual_groups)
    require(
        "weight_grouping_agrees",
        expected_sets == actual_sets,
        f"weight grouping disagrees: the checker reconstructs "
        f"{len(expected_sets)} objects, the deployment declares {len(actual_sets)}",
    )

    # Match a reconstructed logical group to its descriptor by the complete
    # authenticated inventory.  The inventory is only the join key: source
    # order and view addresses are checked below from the graph, never inferred
    # from the deployment's ordering or offsets.
    object_for_group: dict[str, int] = {}
    for group_key, expected in expected_groups.items():
        matches = [
            object_id
            for object_id, actual in zip(actual_group_ids, actual_groups)
            if sorted(tuple(item) for item in actual)
            == sorted(tuple(item) for item in expected)
        ]
        require(
            "weight_group_identity",
            len(matches) == 1,
            f"weight group {group_key} matches {len(matches)} immutable objects, "
            "expected exactly one",
        )
        if len(matches) == 1:
            object_for_group[group_key] = matches[0]

    node_count_for_weights = (
        int(topologies[0].payload["node_count"]) if len(topologies) == 1 else 1
    )
    expected_layout = _reconstruct_weight_layout(
        graph,
        tensors,
        expected_groups,
        expected_members,
        node_count_for_weights,
    )
    _check_weight_sources(
        deployment,
        table,
        expected_layout,
        object_for_group,
        require,
    )
    _check_weight_views(
        graph,
        tensors,
        table,
        by_kernel,
        expected_layout,
        object_for_group,
        emitted_kernels,
        node_count_for_weights,
        require,
    )

    for role_key, extents in expected_extents.items():
        if len(extents) < 2:
            continue
        # The per-*layer* extent, not the per-segment one: a role whose payload
        # arrives as many authenticated ranges still has to give the layer loop
        # one constant stride, and comparing segment sizes would find every
        # expert the same size and say nothing about the layer.
        require(
            "uniform_layer_stride",
            len(set(extents)) == 1,
            f"role {role_key} has {len(set(extents))} distinct per-layer extents, "
            "so the layer loop cannot carry a constant stride",
        )

    # -- 4. loop compression ----------------------------------------------
    band_loops = [
        d
        for d in loops
        if d.payload["bound_selector_kind"] == int(SelectorKind.CONSTANT)
        and d.payload["max_iterations"] in {b["layer_count"] for b in bands}
        and d.payload["max_iterations"] > 1
    ]
    multi_layer_bands = [b for b in bands if b["layer_count"] > 1]
    require(
        "layer_loop_present",
        len(band_loops) >= len(multi_layer_bands),
        f"{len(multi_layer_bands)} multi-layer bands but only {len(band_loops)} "
        "layer loops; the program is unrolled over layers",
    )
    body_kernels = sum(len(b["body"]) for b in bands)
    prologue = sum(1 for k in graph.kernels if k.layer is None)
    # One engine instruction per kernel, wrapped where the token count is a
    # runtime symbol: at most three instructions per kernel plus loop framing.
    ceiling = 6 * (body_kernels + prologue) + 64
    require(
        "loop_compressed",
        len(instructions) <= ceiling,
        f"program has {len(instructions)} instructions for {body_kernels} body "
        f"kernels and {prologue} prologue kernels; the compact-control-flow "
        f"bound is {ceiling}",
    )
    total_layers = sum(b["layer_count"] * b["period"] for b in bands)
    require(
        "instructions_independent_of_depth",
        len(instructions) <= ceiling,
        "instruction count scales with layer count",
    )

    for descriptor in loops:
        payload = descriptor.payload
        require(
            "loop_bounded",
            payload["max_iterations"] > 0
            and payload["max_iterations"] <= capability.limits["max_loop_trip"],
            f"loop {descriptor.descriptor_id} declares "
            f"{payload['max_iterations']} iterations",
        )
        if payload["bound_selector_kind"] == int(SelectorKind.RUNTIME_SYMBOL):
            require(
                "symbol_registry",
                payload["bound_symbol_id"] in {int(s) for s in Symbol},
                f"loop {descriptor.descriptor_id} names symbol "
                f"{payload['bound_symbol_id']}, which is not in the frozen registry",
            )

    # -- 5. topology and cluster traffic ----------------------------------
    require(
        "one_topology_descriptor",
        len(topologies) == 1,
        f"deployment declares {len(topologies)} topology descriptors, expected 1",
    )
    node_count = 1
    if topologies:
        payload = topologies[0].payload
        node_count = payload["node_count"]
        require(
            "topology_matches_capability",
            payload["topology_class"] == capability.topology_class,
            "topology descriptor disagrees with the capability's topology class",
        )
        expected_nodes = (
            capability.limits["max_nodes"]
            if capability.topology_class != int(TopologyClass.SINGLE_CHIP)
            else 1
        )
        require(
            "node_count_matches_capability",
            node_count == expected_nodes,
            f"topology declares {node_count} nodes, capability admits {expected_nodes}",
        )
    link_instructions = [i for i in instructions if i.major == int(Major.LINK)]
    require(
        "link_traffic_matches_topology",
        bool(link_instructions) == (node_count > 1),
        "cluster deployments must move data between chips and single-chip "
        "deployments must not",
    )
    for instruction in link_instructions:
        descriptor = table[instruction.descriptor_id]
        require(
            "link_descriptor_type",
            descriptor.descriptor_type == ExtendedDescriptorType.COMMUNICATION,
            f"LINK instruction names descriptor {instruction.descriptor_id}, "
            "which is not a communication descriptor",
        )
        require(
            "link_participants",
            descriptor.payload["participant_count"] == node_count,
            "a collective must name every participating node",
        )
    scratch_schedule: dict[str, Any] | None = None
    if node_count > 1:
        classes = {d.payload["route_class"] for d in communications}
        require(
            "traffic_classes",
            len(classes) >= 2,
            "a cluster deployment must separate its traffic classes",
        )
        sharded_views = [
            d
            for d in views
            if any(
                d.payload[f"term{s}_kind"] == int(SelectorKind.RUNTIME_SYMBOL)
                and d.payload[f"term{s}_index"] == int(Symbol.NODE_ID)
                for s in range(d.payload["dynamic_term_count"])
            )
        ]
        require(
            "work_is_sharded",
            bool(sharded_views),
            "a 32-node deployment must shard work by node",
        )
        scratch_schedule = _check_shared_exchange_schedule(
            deployment, capability, instructions
        )
        require(
            "communication_scratch_serialized",
            bool(scratch_schedule["ok"]),
            "shared communication scratch is not serialized on one dedicated "
            "one-outstanding DMA queue: "
            + "; ".join(scratch_schedule["errors"]),
        )

    # -- 6. states ---------------------------------------------------------
    resources = {s.state_id for s in graph.states}
    if resources:
        require(
            "states_bound",
            bool(states),
            f"{len(resources)} declared state resources but no state descriptor",
        )
        require(
            "states_merged_not_multiplied",
            len(states) <= len(resources),
            "physical state resources outnumber the declared ones",
        )
        capacity = sum(
            d.payload["capacity_rows"] * d.payload["row_bytes"] for d in states
        )
        declared_capacity = sum(
            _extent(s.capacity_rows) * s.row_elements * _bits(s.dtype) // 8
            for s in graph.states
        )
        require(
            "state_capacity",
            capacity >= declared_capacity,
            f"state descriptors hold {capacity} bytes, the graph declares "
            f"{declared_capacity}",
        )
    prepared: dict[int, int] = {}
    committed: set[int] = set()
    for index, instruction in enumerate(instructions):
        if instruction.major != int(Major.STATE):
            continue
        if instruction.sub == int(State.PREPARE):
            prepared[instruction.descriptor_id] = index
        elif instruction.sub in (int(State.COMMIT), int(State.DISCARD)):
            committed.add(instruction.descriptor_id)
            prepared.pop(instruction.descriptor_id, None)
    require(
        "state_transactions_close",
        not prepared,
        f"{len(prepared)} state resources are prepared without a commit",
    )
    require(
        "every_state_committed",
        committed >= {d.descriptor_id for d in states},
        "some state resource is never committed",
    )

    # -- 7. the frozen verifier -------------------------------------------
    verifier = verify_deployment(deployment, capability)
    require(
        "abi_verifier",
        verifier.admitted,
        "the frozen ABI 3.0 verifier rejected the deployment",
    )
    errors.extend(f"verifier: {message}" for message in verifier.errors)

    # -- summary -----------------------------------------------------------
    completes = [
        i
        for i in instructions
        if i.major == int(Major.CONTROL) and i.sub == int(Control.COMPLETE)
    ]
    require(
        "single_completion",
        len(completes) == 1,
        f"{len(completes)} COMPLETE instructions, expected exactly one",
    )

    return {
        "schema": HBM_DEPLOYMENT_CHECK_SCHEMA,
        "status": "pass" if not errors else "fail",
        "ok": not errors,
        "errors": errors,
        "generated_constants": len(generated),
        "warnings": warnings,
        "check_count": len(checks),
        "passed_check_count": sum(bool(value) for value in checks.values()),
        "checks": dict(sorted(checks.items())),
        "expected": {
            "weight_objects": len(expected_groups),
            "weight_bytes": sum(
                seg[2] for group in expected_groups.values() for seg in group
            ),
            "bands": len(bands),
            "layers": total_layers,
            "body_kernels": body_kernels,
            "instruction_ceiling": ceiling,
            "kernels": len(graph.kernels),
        },
        "actual": {
            "instructions": len(instructions),
            "descriptors": len(table),
            "weight_objects": len(immutable),
            "weight_bytes": sum(seg[2] for group in actual_groups for seg in group),
            "operators": len(operators),
            "views": len(views),
            "loops": len(loops),
            "states": len(states),
            "link_instructions": len(link_instructions),
            "node_count": node_count,
            "declared_retired_work": header.max_retired_work,
        },
        "communication_scratch": scratch_schedule,
        "verifier": verifier.to_dict(),
    }


class _NoSource:
    kind = "missing"


_NO_SOURCE = _NoSource()


def _position_inputs(graph: KernelGraph) -> tuple[str, ...]:
    """Declared inputs whose content is the request's position range.

    Rank one, an index storage type, consumed by something other than the
    embedding lookup: that is a position range, whether the exporter declared it
    over the whole span or as the single base element the consumer adds its row
    to.  Both are ``POSITION_START`` plus an offset, and neither is host data,
    because ADR-003 carries the position in the submission rather than in a
    window.
    """
    consumers: dict[str, list[str]] = {}
    for kernel in graph.kernels:
        for name in kernel.inputs:
            consumers.setdefault(name, []).append(kernel.kind)
    out = []
    for tensor in graph.tensors:
        if tensor.role != "input" or tensor.dtype not in {"u32", "i32"}:
            continue
        if len(tensor.shape) != 1:
            continue
        leading = tensor.shape[0]
        if not isinstance(leading, Symbolic) and int(leading) != 1:
            continue
        kinds = consumers.get(tensor.tensor_id, [])
        if not kinds or "EMBEDDING_LOOKUP" in kinds:
            continue
        out.append(tensor.tensor_id)
    return tuple(sorted(out))


def _ring_moduli(graph: KernelGraph) -> set[int]:
    """Every ring capacity the graph's cache writes address.

    Re-derived from the kernel attributes rather than from the planner: a
    destination-row map of ``absolute_position_mod_window`` says the write
    wraps, and ``window_size`` says at what.  Any other map -- including one
    this checker does not recognise -- implies no ring, so a table that claims
    a modulus the graph never asks for is reported rather than accepted.
    """
    moduli: set[int] = set()
    for kernel in graph.kernels:
        if (
            str(kernel.attributes.get("cache_row", ""))
            != "absolute_position_mod_window"
        ):
            continue
        window = int(kernel.attributes.get("window_size", 0) or 0)
        if window > 0:
            moduli.add(window)
    return moduli


def _check_generated_constants(
    graph: KernelGraph,
    deployment: Deployment,
    generated: Sequence[Any],
    require: Any,
    errors: list[str],
    capability: Capability,
) -> None:
    """Prove every derived constant is declared, reproducible and digest-bound.

    A generated object is the one place a deployment carries bytes no
    checkpoint authenticated, so it gets the strictest independent check in
    this module: the graph must declare that generator on a ``constant``, the
    parameters must be exactly the graph's, and re-running the registered
    generator here must reproduce the bound digest.  That catches a backend
    that fabricates a table, one that binds a stale digest, and a generator
    that has drifted since the deployment was built.
    """
    # Declared as (generator, parameters) *pairs*, not as a map from generator
    # name to parameters.  One generator name legitimately serves several
    # constants -- DeepSeek states its rotary table twice, once unscaled and
    # once with YaRN, both through ``deepseek_rope_coefficients_v1`` -- and
    # keying by name kept whichever came last, so the correctly built table was
    # reported as declaring the other one's parameters.
    declared = [
        (tensor.generator, dict(tensor.generator_parameters))
        for tensor in graph.tensors
        if getattr(tensor, "generator", "")
    ]
    declared_names = {name for name, _ in declared}
    # Two generators are legitimately *implied* by the graph rather than
    # declared on a tensor.  Each rule is re-derived here from the graph so
    # that a backend cannot pass off any other fabricated table as one of them.
    #
    #  * a rank-one index input over the token axis holds the request's
    #    position range, which ADR-003 binds as a symbol; and
    #  * a cache write whose destination-row map is
    #    ``absolute_position_mod_window`` addresses a ring of ``window_size``
    #    rows, and a view can offset an index vector by a symbol but cannot
    #    reduce one, so the reduction has to be tabulated.
    positions = _position_inputs(graph)
    moduli = _ring_moduli(graph)
    reach = int(capability.limits["max_context_positions"])
    for descriptor in generated:
        source = deployment.objects[descriptor.descriptor_id]
        oid = descriptor.descriptor_id
        parameters = dict(source.parameters)
        if source.generator == "arange_u32_v1" and positions:
            # Its only parameter is a count, and it must reach at least one
            # context beyond the last admissible start.
            require(
                "generated_position_extent",
                int(parameters.get("count", 0)) > reach,
                f"object {oid} holds {parameters.get('count')} positions; "
                "a window starting at the last admissible position runs past it",
            )
        elif source.generator == "ring_indices_v1" and moduli:
            require(
                "generated_ring_modulus",
                int(parameters.get("modulus", 0)) in moduli,
                f"object {oid} tabulates a ring of "
                f"{parameters.get('modulus')} rows; the graph's window caches "
                f"ring at {sorted(moduli)}",
            )
            require(
                "generated_position_extent",
                int(parameters.get("count", 0)) > reach,
                f"object {oid} holds {parameters.get('count')} ring rows; "
                "a window starting at the last admissible position runs past it",
            )
        else:
            if not require(
                "generated_is_declared",
                source.generator in declared_names,
                f"object {oid} names generator {source.generator!r}, which no "
                "constant in the graph declares",
            ):
                continue
            require(
                "generated_parameters_match",
                (source.generator, parameters) in declared,
                f"object {oid} declares parameters {parameters}; no constant in "
                f"the graph declares {source.generator!r} with them -- it "
                f"declares "
                f"{[p for name, p in declared if name == source.generator]}",
            )
        try:
            from runtime.sim.generators import digest_of as _generator_digest

            recomputed = _generator_digest(source.generator, source.parameters)
        except Exception as exc:  # unknown or misparameterised generator
            errors.append(f"object {oid}: generator failed to reproduce: {exc}")
            continue
        require(
            "generated_digest_reproduces",
            recomputed == source.digest,
            f"object {oid} binds digest {source.digest[:16]} but "
            f"{source.generator} reproduces {recomputed[:16]}",
        )
        require(
            "generated_content_digest_bound",
            descriptor.payload["content_digest"].hex() == source.digest,
            f"object {oid} descriptor does not bind its generated result",
        )
        require(
            "generated_is_immutable",
            not descriptor.permissions & Permission.WRITE,
            f"object {oid} is a derived constant but declares a write path",
        )


# ---------------------------------------------------------------------------
# Independent reconstruction
# ---------------------------------------------------------------------------
def _bits(dtype: str) -> int:
    try:
        return _DTYPE_BITS[dtype]
    except KeyError:
        raise ValueError(f"unknown neutral dtype {dtype!r}") from None


def _extent(value: Any, fallback: int = 1) -> int:
    if isinstance(value, Symbolic):
        return value.maximum if value.maximum > 0 else fallback
    return int(value)


def _signature(
    kernels: Sequence[Kernel],
    tensors: Mapping[str, Tensor],
    produced: Mapping[str, int],
) -> str:
    parts = []
    for kernel in kernels:
        classes = []
        for name in kernel.inputs:
            tensor = tensors[name]
            if tensor.role in {"weight", "constant"}:
                classes.append("w")
            elif tensor.role == "input":
                classes.append("i")
            elif tensor.role == "output":
                classes.append("o")
            elif name in produced:
                classes.append("a")
            else:
                classes.append("x")
        parts.append(
            "|".join(
                (
                    kernel.kind,
                    kernel.numeric_contract,
                    ",".join(classes),
                    str(len(kernel.outputs)),
                    ",".join(sorted(kernel.phases)),
                    str(len(kernel.state_reads)),
                    str(len(kernel.state_writes)),
                )
            )
        )
    return ";".join(parts)


def _reconstruct_bands(
    graph: KernelGraph, tensors: Mapping[str, Tensor]
) -> list[dict[str, Any]]:
    """Independently recompute the layer bands from kernel structure.

    A band is a repeating block of ``period`` layers.  The search here is
    written the other way round from the planner's -- it grows the period until
    the signature sequence repeats, rather than testing candidate periods -- so
    that agreement between the two is evidence rather than a shared bug.
    """
    produced = {n: k.index for k in graph.kernels for n in k.outputs}
    by_layer: dict[int, list[Kernel]] = {}
    for kernel in graph.kernels:
        if kernel.layer is not None:
            by_layer.setdefault(kernel.layer, []).append(kernel)
    if not by_layer:
        return []
    layers = sorted(by_layer)
    signatures = [_signature(by_layer[layer], tensors, produced) for layer in layers]

    bands: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(layers):
        best_period, best_iterations = 1, 1
        for period in range(1, min(_MAX_PERIOD, len(layers) - cursor) + 1):
            iterations = 1
            while True:
                start = cursor + iterations * period
                if start + period > len(layers):
                    break
                if any(
                    signatures[start + offset] != signatures[cursor + offset]
                    or layers[start + offset]
                    != layers[cursor + offset] + iterations * period
                    for offset in range(period)
                ):
                    break
                iterations += 1
            while iterations >= 2 and not _uniform(
                by_layer, layers, cursor, period, iterations, tensors
            ):
                iterations -= 1
            if iterations >= 2 and period * iterations > best_period * best_iterations:
                best_period, best_iterations = period, iterations
        if best_iterations < 2:
            bands.append(
                {
                    "first_layer": layers[cursor],
                    "layer_count": 1,
                    "period": 1,
                    "layers": [layers[cursor]],
                    "body": list(by_layer[layers[cursor]]),
                }
            )
            cursor += 1
            continue
        covered = layers[cursor : cursor + best_period * best_iterations]
        body: list[Kernel] = []
        for layer in covered[:best_period]:
            body.extend(by_layer[layer])
        bands.append(
            {
                "first_layer": covered[0],
                "layer_count": best_iterations,
                "period": best_period,
                "layers": covered,
                "body": body,
            }
        )
        cursor += best_period * best_iterations
    return bands


#: Must match the planner's bound; a disagreement here is itself a finding.
_MAX_PERIOD = 8


def _uniform(
    by_layer: Mapping[int, Sequence[Kernel]],
    layers: Sequence[int],
    cursor: int,
    period: int,
    iterations: int,
    tensors: Mapping[str, Tensor],
) -> bool:
    blocks = []
    for iteration in range(iterations):
        block: list[Kernel] = []
        for offset in range(period):
            block.extend(by_layer[layers[cursor + iteration * period + offset]])
        blocks.append(block)
    body = blocks[0]
    if any(len(block) != len(body) for block in blocks):
        return False
    for position, kernel in enumerate(body):
        for slot, name in enumerate(kernel.inputs):
            if tensors[name].role not in {"weight", "constant"}:
                continue
            names = []
            for block in blocks:
                peer = block[position]
                if slot >= len(peer.inputs):
                    return False
                names.append(peer.inputs[slot])
            if len(set(names)) == 1:
                # One tensor for the whole run reads from one address in every
                # iteration, so it carries no per-layer stride and needs no
                # checkpoint binding to state one.  A generated constant -- the
                # rope coefficient table -- has no binding and never will.
                continue
            if len(set(names)) != iterations:
                return False
            extents = set()
            for member_id in names:
                member = tensors[member_id]
                if member.binding is None:
                    return False
                extents.add((member.binding.bytes, member.dtype))
            if len(extents) != 1:
                return False
    return True


#: One authenticated checkpoint range: path, file offset, extent, digest.
_Range = tuple[str, int, int, str]


def _binding_ranges(binding: CheckpointBinding) -> list[_Range]:
    """The authenticated checkpoint ranges one binding names.

    A segmented binding names one range per segment -- DeepSeek's 256 routed
    experts per layer -- and the flat ``(path, offset, bytes)`` triple it also
    carries is the *total*, not a range anything may read: the experts are
    interleaved in the shard.  Reading the totals would let a placement that
    covers the wrong bytes reconcile against this checker exactly.
    """
    if binding.segments:
        return [(s.path, s.offset, s.bytes, s.sha256) for s in binding.segments]
    return [(binding.path, binding.offset, binding.bytes, binding.sha256)]


def _elements_in_bytes(size: int, dtype: str) -> int:
    bits = _bits(dtype)
    if int(size) * 8 % bits:
        raise ValueError(f"{size} bytes do not hold a whole number of {dtype} elements")
    return int(size) * 8 // bits


def _matrix_shape(tensor: Tensor) -> tuple[int, int]:
    """Independently flatten one neutral tensor to its matrix presentation."""
    if not tensor.shape:
        return 1, 1
    if isinstance(tensor.shape[0], Symbolic):
        rows = _extent(tensor.shape[0])
        cols = 1
        for axis in tensor.shape[1:]:
            cols *= max(_extent(axis), 1)
        return max(rows, 1), max(cols, 1)
    rows = 1
    for axis in tensor.shape[:-1]:
        rows *= max(_extent(axis), 1)
    return max(rows, 1), max(_extent(tensor.shape[-1]), 1)


def _scale_row_block(tensor: Tensor, tensors: Mapping[str, Tensor]) -> int:
    """Leading-axis rows represented by one block-scale code."""
    scale = tensors.get(tensor.scale_tensor_id or "")
    if scale is None or int(tensor.scale_block_elements or 0) <= 0:
        return 1
    rows = 1
    for axis in tensor.shape[:-1]:
        rows *= max(_extent(axis), 1)
    scale_rows = 1
    for axis in scale.shape[:-1]:
        scale_rows *= max(_extent(axis), 1)
    if scale_rows <= 0 or rows % scale_rows:
        return 1
    return max(rows // scale_rows, 1)


def _domain_extent(kernel: Kernel, graph: KernelGraph) -> int:
    symbols = {symbol.name: symbol.maximum for symbol in graph.symbols}
    for key in ("reduction_width", "reduction", "depth"):
        value = kernel.iteration_domain.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            return int(symbols.get(value, 0))
        return _extent(value, 0)
    return 0


def _logical_weight_use(
    graph: KernelGraph,
    kernel: Kernel,
    tensor_id: str,
    tensors: Mapping[str, Tensor],
    node_count: int,
) -> tuple[bool, bool, int]:
    """Return ``(node selected, physically contiguous, node stride)``.

    This is reconstructed from the neutral contraction geometry.  In
    particular it does not inspect a tensor-view term: that term is one of the
    claims this checker is meant to verify.  Routed banks are owned in
    consecutive expert runs; ordinary contractions own output-column runs.
    """
    if node_count <= 1 or len(kernel.inputs) < 2 or kernel.inputs[1] != tensor_id:
        return False, True, 0
    engine = engine_for(kernel.kind)
    if int(engine.family) != int(Major.TENSOR) or int(engine.sub) not in {
        int(TensorOp.MATMUL),
        int(TensorOp.GROUPED_MATMUL),
        int(TensorOp.ROUTED_MATMUL),
    }:
        return False, True, 0
    if not kernel.outputs:
        return False, True, 0

    weight = tensors[tensor_id]
    weight_rows, weight_cols = _matrix_shape(weight)
    _out_rows, output_cols = _matrix_shape(tensors[kernel.outputs[0]])
    _activation_rows, activation_cols = _matrix_shape(tensors[kernel.inputs[0]])

    declared_experts = int(kernel.attributes.get("expert_count", 0) or 0)
    bank = 0
    if (
        declared_experts > 1
        and len(weight.shape) == 3
        and _extent(weight.shape[0]) == declared_experts
    ):
        bank = declared_experts
        weight_rows //= bank
    bank_shard = (
        bank // node_count
        if bank >= node_count and bank % node_count == 0
        else 0
    )

    depth = _domain_extent(kernel, graph) or activation_cols
    if weight_cols == depth:
        transposed = False
    elif weight_rows == depth:
        transposed = True
    elif depth and weight_cols % depth == 0:
        transposed = False
    elif depth and weight_rows % depth == 0:
        transposed = True
    else:
        return False, True, 0

    if bank_shard:
        expert_stride = weight_rows * weight_cols
        return True, True, bank_shard * expert_stride

    row_block = _scale_row_block(weight, tensors)
    if (
        output_cols <= node_count
        or output_cols % node_count
        or (output_cols // node_count) % row_block
    ):
        return False, True, 0
    shard_columns = output_cols // node_count
    node_stride = shard_columns if transposed else shard_columns * weight_cols
    return True, not transposed, node_stride


def _partition_ranges(
    ranges: Sequence[_Range],
    size_bytes: int,
    dtype: str,
    node_count: int,
) -> tuple[tuple[_Range, ...], ...] | None:
    """Split complete authenticated ranges into equal consecutive node runs."""
    if node_count <= 1 or size_bytes <= 0 or size_bytes % node_count:
        return None
    elements = _elements_in_bytes(size_bytes, dtype)
    if elements % node_count:
        return None
    per_node = size_bytes // node_count
    out: list[tuple[_Range, ...]] = []
    current: list[_Range] = []
    current_bytes = 0
    for item in ranges:
        extent = int(item[2])
        if extent <= 0 or current_bytes + extent > per_node:
            return None
        current.append(item)
        current_bytes += extent
        if current_bytes == per_node:
            out.append(tuple(current))
            current = []
            current_bytes = 0
    if current or len(out) != node_count:
        return None
    return tuple(out)


def _reconstruct_weight_layout(
    graph: KernelGraph,
    tensors: Mapping[str, Tensor],
    groups: Mapping[str, Sequence[_Range]],
    members_by_group: Mapping[str, Sequence[str]],
    node_count: int,
) -> dict[str, Any]:
    """Rebuild node sources, tensor origins and induction strides from the IR."""
    group_of = {
        tensor_id: group_key
        for group_key, members in members_by_group.items()
        for tensor_id in members
    }
    ranges_by_tensor = {
        tensor_id: tuple(_binding_ranges(tensors[tensor_id].binding))
        for tensor_id in group_of
        if tensors[tensor_id].binding is not None
    }

    modes: dict[str, set[bool]] = {}
    contiguous: dict[str, bool] = {}
    for kernel in graph.kernels:
        for tensor_id in kernel.inputs:
            if tensor_id not in group_of:
                continue
            selected, safe, _stride = _logical_weight_use(
                graph, kernel, tensor_id, tensors, node_count
            )
            modes.setdefault(tensor_id, set()).add(selected)
            if selected:
                contiguous[tensor_id] = contiguous.get(tensor_id, True) and safe

    logical = {tensor_id: values == {True} for tensor_id, values in modes.items()}
    # A folded role has one placement decision.  Members outside the emitted
    # first iteration inherit the decision reconstructed from all peers.
    for group_key, members in members_by_group.items():
        if not group_key.startswith("role:") or group_key.endswith(".scale"):
            continue
        role_modes = {
            mode for tensor_id in members for mode in modes.get(tensor_id, ())
        }
        selected = role_modes == {True}
        for tensor_id in members:
            logical[tensor_id] = selected
    # Scale tensors have no explicit operator slot.  Their ownership is the
    # weight's ownership because the weight view is their sole address.
    for tensor in tensors.values():
        scale_id = tensor.scale_tensor_id
        if tensor.tensor_id in group_of and scale_id in group_of:
            logical[scale_id] = logical.get(tensor.tensor_id, False)
            contiguous[scale_id] = contiguous.get(tensor.tensor_id, True)

    partitions: dict[str, tuple[tuple[_Range, ...], ...]] = {}
    eligible: dict[str, bool] = {}
    for tensor_id in group_of:
        tensor = tensors[tensor_id]
        binding = tensor.binding
        assert binding is not None
        pieces = (
            _partition_ranges(
                ranges_by_tensor[tensor_id], binding.bytes, tensor.dtype, node_count
            )
            if logical.get(tensor_id, False)
            and contiguous.get(tensor_id, True)
            else None
        )
        eligible[tensor_id] = pieces is not None
        if pieces is not None:
            partitions[tensor_id] = pieces

    role_groups = [
        tuple(members)
        for group_key, members in members_by_group.items()
        if group_key.startswith("role:")
    ]
    changed = True
    while changed:
        changed = False
        for members in role_groups:
            shared = all(eligible.get(tensor_id, False) for tensor_id in members)
            for tensor_id in members:
                if eligible.get(tensor_id, False) != shared:
                    eligible[tensor_id] = shared
                    changed = True
        for tensor in tensors.values():
            scale_id = tensor.scale_tensor_id
            if tensor.tensor_id not in eligible or scale_id not in eligible:
                continue
            shared = eligible[tensor.tensor_id] and eligible[scale_id]
            if eligible[tensor.tensor_id] != shared:
                eligible[tensor.tensor_id] = shared
                changed = True
            if eligible[scale_id] != shared:
                eligible[scale_id] = shared
                changed = True

    expected_groups: dict[str, dict[str, Any]] = {}
    placements: dict[str, dict[str, Any]] = {}
    for group_key, members in members_by_group.items():
        node_indexed = any(eligible.get(tensor_id, False) for tensor_id in members)
        node_maps: list[list[_Range]] = [[] for _ in range(node_count)]
        cursor_bytes = 0
        for tensor_id in members:
            tensor = tensors[tensor_id]
            binding = tensor.binding
            assert binding is not None
            if node_indexed:
                maps = (
                    partitions[tensor_id]
                    if eligible.get(tensor_id, False)
                    else tuple(ranges_by_tensor[tensor_id] for _ in range(node_count))
                )
                local_bytes = sum(item[2] for item in maps[0])
                for node_id, source_ranges in enumerate(maps):
                    node_maps[node_id].extend(source_ranges)
            else:
                local_bytes = binding.bytes
            placements[tensor_id] = {
                "group_key": group_key,
                "element_offset": _elements_in_bytes(cursor_bytes, tensor.dtype),
                "layer_stride_elements": 0,
                "logical_node_sharded": logical.get(tensor_id, False),
                "materialization": (
                    "node_sharded" if eligible.get(tensor_id, False) else "replicated"
                ),
            }
            cursor_bytes += local_bytes

        expected_groups[group_key] = {
            "kind": "node_segments" if node_indexed else "segments",
            "size_bytes": cursor_bytes,
            "ranges": tuple(groups[group_key]),
            "node_maps": tuple(tuple(items) for items in node_maps),
            "members": tuple(members),
        }

    for group_key, members in members_by_group.items():
        if not group_key.startswith("role:") or len(members) < 2:
            continue
        offsets = [placements[tensor_id]["element_offset"] for tensor_id in members]
        deltas = {right - left for left, right in zip(offsets, offsets[1:])}
        stride = next(iter(deltas)) if len(deltas) == 1 else -1
        for tensor_id in members:
            placements[tensor_id]["layer_stride_elements"] = stride

    return {"groups": expected_groups, "placements": placements}


def _source_ranges(source: Any) -> tuple[_Range, ...]:
    return tuple(
        (segment.path, segment.offset, segment.bytes, segment.sha256)
        for segment in source
    )


def _check_weight_sources(
    deployment: Deployment,
    table: Any,
    layout: Mapping[str, Any],
    object_for_group: Mapping[str, int],
    require: Any,
) -> None:
    """Verify exact authenticated byte order for every reconstructed source."""
    for group_key, expected in layout["groups"].items():
        object_id = object_for_group.get(group_key)
        if object_id is None:
            continue
        source = deployment.objects.get(object_id)
        if not require(
            "authenticated_segment_order",
            source is not None and source.kind == expected["kind"],
            f"weight group {group_key} object {object_id} must use an exact "
            f"{expected['kind']} source",
        ):
            continue
        descriptor = table[object_id]
        require(
            "weight_object_local_extent",
            int(descriptor.payload["size_bytes"]) == int(expected["size_bytes"]),
            f"weight group {group_key} object {object_id} has local extent "
            f"{descriptor.payload['size_bytes']}, expected {expected['size_bytes']}",
        )
        if source.kind == "segments":
            actual = _source_ranges(source.segments)
            wanted = expected["ranges"]
        else:
            actual = tuple(_source_ranges(items) for items in source.node_segments)
            wanted = expected["node_maps"]
        require(
            "authenticated_segment_order",
            actual == wanted,
            f"weight group {group_key} object {object_id} does not preserve the "
            "graph's exact per-node authenticated segment order",
        )


def _view_terms(view: Any, kind: SelectorKind) -> list[tuple[int, int]]:
    return [
        (
            int(view.payload[f"term{index}_index"]),
            int(view.payload[f"term{index}_stride"]),
        )
        for index in range(int(view.payload["dynamic_term_count"]))
        if int(view.payload[f"term{index}_kind"]) == int(kind)
    ]


def _presented_element_factor(kernel: Kernel, tensor_id: str, tensor: Tensor) -> int:
    """Element-address multiplier for an explicitly declared narrow reading."""
    if (
        len(kernel.inputs) > 1
        and kernel.inputs[1] == tensor_id
        and tensor.dtype == "i64"
        and str(kernel.attributes.get("table_element_reading", "") or "")
        == "low_u32_of_i64"
    ):
        return 2
    return 1


def _checker_input_slots(
    kernel: Kernel, tensors: Mapping[str, Tensor]
) -> list[str | None]:
    """Reconstruct TA-ABI3 operand slots without consulting backend plans.

    The neutral lowering module owns declared holes.  The few frozen operand
    conventions layered on top are re-stated here so a view is checked in the
    slot that gives it meaning, rather than merely matched to some view of the
    same memory object.
    """
    names = list(kernel.inputs)
    permutation = {
        "HYPER_CONNECT_PRE": (0, 1, 3, 2),
        "HYPER_CONNECT_HEAD": (0, 1, 3, 2),
    }.get(kernel.kind)
    if permutation is not None and len(names) == len(permutation):
        names = [names[index] for index in permutation]

    engine = engine_for(kernel.kind)
    index_first = (int(engine.family), int(engine.sub)) in {
        (int(Major.TENSOR), int(TensorOp.EMBED_LOOKUP)),
        (int(Major.DMA), int(Dma.GATHER)),
        (int(Major.DMA), int(Dma.SCATTER)),
        (int(Major.ROUTE), int(Route.EXPERT_DISPATCH)),
    }
    if index_first and len(names) >= 2:
        integer = {"u32", "i32", "u64", "i64"}
        if tensors[names[0]].dtype not in integer:
            for position, name in enumerate(names):
                if tensors[name].dtype in integer:
                    names.insert(0, names.pop(position))
                    break

    if kernel.kind == "EXPERT_REDUCE" and "base_operand_index" in kernel.attributes:
        base = int(kernel.attributes["base_operand_index"])
        return [kernel.inputs[0], None, kernel.inputs[base]]

    limit = {
        (int(Major.VECTOR), int(Vector.SILU_MUL)): 2,
        (int(Major.SELECTION), int(Selection.ARGMAX)): 1,
        (int(Major.SELECTION), int(Selection.TOKEN_APPEND)): 1,
    }.get((int(engine.family), int(engine.sub)), 4)
    names = names[:limit]
    attributes = kernel.attributes
    if kernel.kind == "COMPRESS_STATE_UPDATE" and ABSENT_OPERANDS not in attributes:
        attributes = {**attributes, ABSENT_OPERANDS: [1]}
    return abi_input_slots(kernel.kind, names, attributes)


def _check_weight_views(
    graph: KernelGraph,
    tensors: Mapping[str, Tensor],
    table: Any,
    by_kernel: Mapping[int, Sequence[Any]],
    layout: Mapping[str, Any],
    object_for_group: Mapping[str, int],
    emitted_kernels: set[int],
    node_count: int,
    require: Any,
) -> None:
    """Bind every reachable weight slot to one exact reconstructed local view.

    The unit of proof is an executed operator slot, not the set of views that
    happen to claim the same ``source_kernel_id``.  Requiring each property on
    each slot both excludes unreachable decoys and prevents two reachable views
    from splitting the proof (one with the right stride, another with the right
    node selector).
    """
    placements = layout["placements"]
    for kernel_index in sorted(emitted_kernels):
        kernel = graph.kernels[kernel_index]
        input_slots = _checker_input_slots(kernel, tensors)
        engine = engine_for(kernel.kind)
        kernel_operators = [
            operator
            for operator in by_kernel.get(kernel_index, ())
            if int(operator.payload["engine_family"]) == int(engine.family)
            and int(operator.payload["engine_sub"]) == int(engine.sub)
        ]
        for slot, tensor_id in enumerate(input_slots[:4]):
            if tensor_id is None:
                continue
            expected = placements.get(tensor_id)
            if expected is None:
                continue
            object_id = object_for_group.get(expected["group_key"])
            if object_id is None:
                continue
            factor = _presented_element_factor(
                kernel, tensor_id, tensors[tensor_id]
            )
            expected_offset = int(expected["element_offset"]) * factor
            expected_stride = int(expected["layer_stride_elements"]) * factor
            selected, _safe, expected_node_stride = _logical_weight_use(
                graph, kernel, tensor_id, tensors, node_count
            )
            expected_node_stride *= factor
            tensor = tensors[tensor_id]
            scale_id = tensor.scale_tensor_id
            scale_placement = placements.get(scale_id or "")
            scale_object_id = (
                object_for_group.get(scale_placement["group_key"])
                if scale_placement is not None
                else None
            )
            block = int(tensor.scale_block_elements or 0)
            row_block = _scale_row_block(tensor, tensors)
            cols = _matrix_shape(tensor)[1]

            def scale_code(elements: int) -> int:
                return (int(elements) // cols // row_block) * (cols // block)

            companion_layout_ok = True
            if scale_placement is not None:
                physical_offset = int(expected["element_offset"])
                physical_stride = int(expected["layer_stride_elements"])
                companion_layout_ok = (
                    block > 0
                    and cols % block == 0
                    and int(scale_placement["element_offset"])
                    == scale_code(physical_offset)
                    and int(scale_placement["layer_stride_elements"])
                    == scale_code(physical_stride)
                )
                require(
                    "weight_scale_companion_layout",
                    companion_layout_ok,
                    f"weight {tensor_id} and scale {scale_id} do not have the "
                    "independently derived block-code origin and layer stride",
                )

            for operator in kernel_operators:
                view_id = int(operator.payload[f"input_view_{slot}"])
                view = (
                    table[view_id]
                    if view_id != NO_ID and 0 <= view_id < len(table)
                    else None
                )
                bound_ok = bool(
                    view is not None
                    and view.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
                    and int(view.primary_object_id) == object_id
                )
                require(
                    "weight_view_bound",
                    bound_ok,
                    f"reachable operator {operator.descriptor_id} for kernel "
                    f"{kernel.kernel_id} slot {slot} has no tensor view over "
                    f"object {object_id} for weight {tensor_id}",
                )
                if not bound_ok or view is None:
                    continue

                offset_ok = int(view.payload["element_offset"]) == expected_offset
                require(
                    "weight_view_offsets",
                    offset_ok,
                    f"reachable operator {operator.descriptor_id} kernel "
                    f"{kernel.kernel_id} weight {tensor_id} must start at element "
                    f"{expected_offset} in object {object_id}",
                )

                loop_terms = _view_terms(view, SelectorKind.LOOP_INDUCTION)
                stride_ok = (
                    len(loop_terms) == 1
                    and loop_terms[0][1] == expected_stride
                    if expected_stride > 0
                    else not loop_terms
                )
                require(
                    "weight_view_layer_strides",
                    stride_ok,
                    f"reachable operator {operator.descriptor_id} kernel "
                    f"{kernel.kernel_id} weight {tensor_id} must carry layer "
                    f"stride {expected_stride} from element {expected_offset}",
                )

                node_terms = [
                    term
                    for term in _view_terms(view, SelectorKind.RUNTIME_SYMBOL)
                    if term[0] == int(Symbol.NODE_ID)
                ]
                physically_sharded = expected["materialization"] == "node_sharded"
                node_ok = (
                    len(node_terms) == 1
                    and node_terms[0][1] == expected_node_stride
                    if selected and not physically_sharded
                    else not node_terms
                )
                require(
                    "weight_view_node_selection",
                    node_ok,
                    f"reachable operator {operator.descriptor_id} kernel "
                    f"{kernel.kernel_id} weight {tensor_id} has the wrong NODE_ID "
                    "selection for its reconstructed physical materialization",
                )

                if scale_placement is None:
                    scale_ok = int(view.payload["scale_object_id"]) == NO_ID
                    scale_message = (
                        f"reachable operator {operator.descriptor_id} kernel "
                        f"{kernel.kernel_id} weight {tensor_id} names an undeclared "
                        "block-scale companion"
                    )
                else:
                    scale_ok = bool(
                        scale_object_id is not None
                        and int(view.payload["scale_object_id"]) == scale_object_id
                        and int(view.payload["scale_block_elements"]) == block
                        and max(int(view.payload["scale_block_rows"]), 1)
                        == row_block
                    )
                    scale_message = (
                        f"reachable operator {operator.descriptor_id} kernel "
                        f"{kernel.kernel_id} weight {tensor_id} does not bind scale "
                        f"{scale_id} with its declared block geometry"
                    )
                require("weight_scale_view_binding", scale_ok, scale_message)
                require(
                    "weight_view_exact",
                    offset_ok
                    and stride_ok
                    and node_ok
                    and companion_layout_ok
                    and scale_ok,
                    f"reachable operator {operator.descriptor_id} kernel "
                    f"{kernel.kernel_id} slot {slot} is not the exact independently "
                    f"reconstructed view for weight {tensor_id}",
                )


def _reconstruct_weight_groups(
    graph: KernelGraph,
    tensors: Mapping[str, Tensor],
    bands: Sequence[Mapping[str, Any]],
) -> tuple[
    dict[str, list[_Range]],
    dict[str, list[int]],
    dict[str, tuple[str, ...]],
]:
    """Independently recompute the expected weight objects.

    Rule one: one object per weight role, segments in layer order.  When every
    member of that role names a distinct block-scale tensor, the scale tensors
    form a companion object in the same member order: the frozen block-scale
    address is the weight element offset divided by its block geometry, so a
    file-adjacent scale layout would not preserve the layer stride.  Rule two:
    everything left over is grouped by adjacency inside one checkpoint file.

    Returns the ranges each object holds and, for the role objects, the
    per-layer byte extent of each member -- which is what the layer stride is
    made of and is not recoverable from the ranges once a segmented binding has
    been expanded.
    """
    by_layer: dict[int, list[Kernel]] = {}
    for kernel in graph.kernels:
        if kernel.layer is not None:
            by_layer.setdefault(kernel.layer, []).append(kernel)

    groups: dict[str, list[_Range]] = {}
    extents: dict[str, list[int]] = {}
    members_by_group: dict[str, tuple[str, ...]] = {}
    claimed: set[str] = set()
    for band in bands:
        period = band["period"]
        blocks = []
        for iteration in range(band["layer_count"]):
            block: list[Kernel] = []
            for offset in range(period):
                block.extend(by_layer[band["layers"][iteration * period + offset]])
            blocks.append(block)
        for position, kernel in enumerate(band["body"]):
            for slot, name in enumerate(kernel.inputs):
                tensor = tensors[name]
                if tensor.role not in {"weight", "constant"} or tensor.binding is None:
                    continue
                members: list[str] = []
                for block in blocks:
                    if position >= len(block):
                        members = []
                        break
                    peer = block[position]
                    if slot >= len(peer.inputs):
                        members = []
                        break
                    member = peer.inputs[slot]
                    if (
                        member in claimed
                        or member in members
                        or tensors[member].binding is None
                    ):
                        members = []
                        break
                    members.append(member)
                if not members:
                    continue
                claimed.update(members)
                role_key = f"role:{band['first_layer']}.{position}.{slot}"
                groups[role_key] = [
                    rng for m in members for rng in _binding_ranges(tensors[m].binding)
                ]
                extents[role_key] = [tensors[m].binding.bytes for m in members]
                members_by_group[role_key] = tuple(members)

                scale_members: list[str] = []
                for member in members:
                    scale_id = tensors[member].scale_tensor_id
                    scale = tensors.get(scale_id) if scale_id else None
                    if (
                        scale is None
                        or scale.binding is None
                        or scale.tensor_id in claimed
                        or scale.tensor_id in scale_members
                    ):
                        scale_members = []
                        break
                    scale_members.append(scale.tensor_id)
                if len(scale_members) == len(members):
                    claimed.update(scale_members)
                    scale_key = f"{role_key}.scale"
                    groups[scale_key] = [
                        rng
                        for member in scale_members
                        for rng in _binding_ranges(tensors[member].binding)
                    ]
                    extents[scale_key] = [
                        tensors[member].binding.bytes for member in scale_members
                    ]
                    members_by_group[scale_key] = tuple(scale_members)

    leftovers = sorted(
        (
            t
            for t in graph.tensors
            if t.role in {"weight", "constant"}
            and t.binding is not None
            and t.tensor_id not in claimed
        ),
        key=lambda t: (t.binding.path, t.binding.offset, t.tensor_id),
    )
    run_index = 0
    end = -1
    path = None
    for tensor in leftovers:
        binding = tensor.binding
        assert binding is not None
        if path != binding.path or not 0 <= binding.offset - end <= _MERGE_SLACK:
            run_index += 1
            path = binding.path
        group_key = f"file:{run_index}"
        groups.setdefault(group_key, []).extend(_binding_ranges(binding))
        members_by_group[group_key] = (
            *members_by_group.get(group_key, ()),
            tensor.tensor_id,
        )
        end = binding.offset + binding.bytes
    return groups, extents, members_by_group


__all__ = ["HBM_DEPLOYMENT_CHECK_SCHEMA", "check_deployment"]
