"""Independent legality checker for immutable-ROM ABI 3.0 schedules.

The ROM schedule generator lives in :mod:`compiler.backends.rom.common.program`.
This module deliberately does not import it, either ROM product, or the ROM
image planner.  It consumes only the neutral graph, the emitted deployment, the
advertised capability, and frozen ABI contracts.  Layer runs, dependencies,
resource masks, topology participation, queue pressure, state ordering, and
worst-case work are reconstructed here by a second implementation.

That separation is load-bearing.  The generic ABI verifier proves that records
are well formed and safe to execute; it cannot prove that a legal-looking bank
mask, queue, route class, or wait set is the one the source graph and ROM plan
require.  This checker supplies that semantic proof and then invokes the frozen
verifier as a final, independent admission gate.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import ceil, prod
from typing import Any, Callable, Mapping, Sequence

from compiler.ir.v3.kernel_ir import Kernel, KernelGraph, Symbolic, Tensor
from compiler.ir.v3.lowering import engine_for
from runtime.abi3.capability import Capability, canonical_json
from runtime.abi3.constants import (
    Control,
    DTYPE_BITS,
    DType,
    InstructionFlag,
    Link,
    Major,
    NO_ID,
    ParticipantScope,
    Permission,
    State,
    StorageClass,
    Tensor as TensorOp,
    TopologyClass,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import (
    CollectiveOp,
    ExtendedDescriptorType,
    SelectorKind,
)
from runtime.abi3.records import Instruction, decode_body, split_program
from runtime.abi3.verifier import verify_deployment

SCHEDULE_CHECK_SCHEMA = "opentallas.rom.schedule_check.v1"

# These are wire values, intentionally repeated instead of imported from the
# producer.  They are the meanings written into SCHEDULE.resource_bound.
_ROM_READ = 1
_TENSOR_LANES = 2
_MEMORY_PORT = 3
_STATE_TRANSACTION = 4
_LINK = 5
_SELECTION = 6

_ENGINE_KEY: Mapping[int, str] = {
    int(Major.DMA): "dma",
    int(Major.TENSOR): "tensor",
    int(Major.VECTOR): "vector",
    int(Major.ATTENTION): "attention",
    int(Major.ROUTE): "route",
    int(Major.REDUCTION): "reduction",
    int(Major.SELECTION): "selection",
    int(Major.STATE): "state",
    int(Major.LINK): "link",
}

_WEIGHT_ROLES = frozenset({"weight", "constant"})
_TRANSACTION_KINDS = frozenset({"STATE_PREPARE", "STATE_COMMIT"})
_DIRECT_STATE_KIND = "STATE_READ"
_MAX_LAYER_PERIOD = 8

# The generator may materialise the dispatch rows before issuing the frozen
# ROUTE.EXPERT_DISPATCH operation.  Both instructions retain the source kernel
# ID, so the checker permits precisely this extra operation and no generic
# backend-private opcode.
_AUXILIARY_ENGINE_OPS: Mapping[str, frozenset[tuple[int, int]]] = {
    "EXPERT_DISPATCH": frozenset({(int(Major.DMA), 0)}),  # DMA.TRANSFER
}


@dataclass(frozen=True, slots=True)
class _Band:
    """One independently reconstructed periodic layer span."""

    first_layer: int
    layers: tuple[int, ...]
    period: int
    iterations: int
    body: tuple[Kernel, ...]


def check_rom_schedule(
    graph: KernelGraph, deployment: Deployment, capability: Capability
) -> dict[str, Any]:
    """Return an independent semantic schedule report.

    The function never raises for a semantic mismatch.  Wire decoding still
    fails closed before this function can reason about records; callers that
    campaign corrupt bytes should catch those decoder exceptions separately.
    """

    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}

    def require(name: str, ok: bool, message: str) -> bool:
        checks[name] = checks.get(name, True) and bool(ok)
        if not ok:
            errors.append(message)
        return bool(ok)

    header, body = split_program(deployment.program)
    instructions = decode_body(body)
    table = deployment.table
    by_type = {
        kind: [table[index] for index in table.ids_of_type(kind)]
        for kind in ExtendedDescriptorType
    }
    objects = {
        d.descriptor_id: d for d in by_type[ExtendedDescriptorType.MEMORY_OBJECT]
    }
    views = {d.descriptor_id: d for d in by_type[ExtendedDescriptorType.TENSOR_VIEW]}
    schedules = {d.descriptor_id: d for d in by_type[ExtendedDescriptorType.SCHEDULE]}
    numeric_ids = {d.descriptor_id for d in by_type[ExtendedDescriptorType.NUMERIC]}
    operators = {d.descriptor_id: d for d in by_type[ExtendedDescriptorType.OPERATOR]}
    waits = {d.descriptor_id: d for d in by_type[ExtendedDescriptorType.EVENT_WAIT_SET]}
    loops = {d.descriptor_id: d for d in by_type[ExtendedDescriptorType.LOOP_CONTROL]}
    states = {d.descriptor_id: d for d in by_type[ExtendedDescriptorType.STATE]}
    communications = {
        d.descriptor_id: d for d in by_type[ExtendedDescriptorType.COMMUNICATION]
    }
    counter_classes = {
        d.descriptor_id: d for d in by_type[ExtendedDescriptorType.COUNTER_CLASS]
    }
    topologies = by_type[ExtendedDescriptorType.TOPOLOGY]

    # -- artifact identity -------------------------------------------------
    require(
        "model_identity",
        deployment.model_id == graph.model_id,
        f"deployment model {deployment.model_id!r} is not graph model "
        f"{graph.model_id!r}",
    )
    require(
        "graph_identity",
        deployment.source_identity.get("graph_id") == graph.graph_id,
        "deployment source_identity does not bind the supplied neutral graph",
    )
    require(
        "capability_identity",
        deployment.capability_digest == capability.digest,
        "deployment capability digest does not bind the supplied capability",
    )
    require(
        "rom_backend",
        deployment.backend.startswith("rom."),
        f"backend {deployment.backend!r} is not an immutable-ROM backend",
    )
    require(
        "rom_weights",
        deployment.source_identity.get("weight_storage_class") == "ROM",
        "schedule proof requires the ROM storage-class deployment",
    )

    require(
        "one_topology",
        len(topologies) == 1,
        f"deployment has {len(topologies)} topology descriptors, expected one",
    )
    topology: Mapping[str, Any] = topologies[0].payload if topologies else {}
    topology_class = int(topology.get("topology_class", capability.topology_class))
    if topology:
        require(
            "topology_identity",
            int(topology["topology_class"])
            == int(deployment.topology_class)
            == int(capability.topology_class),
            "deployment, topology descriptor, and capability disagree on topology",
        )

    # -- independent layer reconstruction ---------------------------------
    bands, canonical, representatives = _reconstruct_bands(graph)
    expected_order = _representative_order(graph, bands)
    order_position = {
        kernel.index: position for position, kernel in enumerate(expected_order)
    }
    representative_ids = {kernel.index for kernel in representatives}

    require(
        "layered_graph",
        bool(bands),
        "the graph has no reconstructable layered span",
    )
    constant_setups: list[tuple[int, Any]] = []
    for index, instruction in enumerate(instructions):
        if instruction.major != int(Major.CONTROL) or instruction.sub != int(
            Control.LOOP_SETUP
        ):
            continue
        descriptor = loops.get(instruction.control_id)
        if descriptor is None:
            continue
        if descriptor.payload["bound_selector_kind"] == int(SelectorKind.CONSTANT):
            constant_setups.append((index, descriptor))
    require(
        "layer_loop_count",
        len(constant_setups) == len(bands),
        f"checker reconstructs {len(bands)} layer bands but deployment has "
        f"{len(constant_setups)} constant layer loops",
    )
    unmatched = list(constant_setups)
    matched_band_loops: list[tuple[_Band, Any]] = []
    for band in bands:
        match = _match_band_loop(band, unmatched, instructions, operators)
        if require(
            "layer_loop_body",
            match is not None,
            f"no constant loop contains the reconstructed body beginning at "
            f"layer {band.first_layer} with period {band.period}",
        ):
            _, descriptor = match
            unmatched.remove(match)
            matched_band_loops.append((band, descriptor))
            require(
                "layer_loop_trip",
                int(descriptor.payload["max_iterations"]) == band.iterations,
                f"layer {band.first_layer} loop declares "
                f"{descriptor.payload['max_iterations']} trips; checker derives "
                f"{band.iterations}",
            )

    # -- program/operator correspondence ----------------------------------
    instruction_operators: list[tuple[int, Instruction, Any]] = []
    by_source: dict[int, list[tuple[int, Instruction, Any]]] = {}
    scheduled_families = {
        int(Major.DMA),
        int(Major.TENSOR),
        int(Major.VECTOR),
        int(Major.ATTENTION),
        int(Major.ROUTE),
        int(Major.REDUCTION),
        int(Major.SELECTION),
    }
    for index, instruction in enumerate(instructions):
        if instruction.major not in scheduled_families:
            continue
        operator = operators.get(instruction.descriptor_id)
        if not require(
            "operator_descriptor_type",
            operator is not None,
            f"instruction {index} {instruction.mnemonic} does not name an "
            "OPERATOR descriptor",
        ):
            continue
        instruction_operators.append((index, instruction, operator))
        source = int(operator.payload["source_kernel_id"])
        by_source.setdefault(source, []).append((index, instruction, operator))
        require(
            "instruction_operator_agreement",
            int(operator.payload["engine_family"]) == instruction.major
            and int(operator.payload["engine_sub"]) == instruction.sub
            and int(instruction.source_operation_id) == source,
            f"instruction {index} and operator {operator.descriptor_id} disagree "
            "on engine or source kernel",
        )
        require(
            "representative_source",
            source in representative_ids,
            f"operator {operator.descriptor_id} names non-representative source "
            f"kernel {source}",
        )

    for kernel in expected_order:
        if kernel.kind in _TRANSACTION_KINDS:
            continue
        if kernel.kind == _DIRECT_STATE_KIND:
            expected = _expected_engine(kernel)
            found = [
                instruction
                for instruction in instructions
                if instruction.source_operation_id == kernel.index
                and (instruction.major, instruction.sub) == expected
            ]
            require(
                "state_read_coverage",
                bool(found),
                f"STATE_READ kernel {kernel.index} has no direct STATE.READ "
                "instruction",
            )
            continue
        expected = _expected_engine(kernel)
        emitted = by_source.get(kernel.index, [])
        pairs = {(item[1].major, item[1].sub) for item in emitted}
        require(
            "kernel_coverage",
            expected in pairs,
            f"kernel {kernel.index} ({kernel.kind}) requires "
            f"{_mnemonic(expected)}, found "
            f"{sorted(_mnemonic(pair) for pair in pairs)}",
        )
        permitted = {expected} | set(_AUXILIARY_ENGINE_OPS.get(kernel.kind, ()))
        require(
            "no_private_engine_ops",
            pairs <= permitted,
            f"kernel {kernel.index} ({kernel.kind}) emits private/unexplained "
            f"engine operations {sorted(_mnemonic(pair) for pair in pairs - permitted)}",
        )

    # -- control-flow work and instruction multiplicity -------------------
    multipliers = [0] * len(instructions)
    work = _expanded_work(
        instructions, loops, multipliers, require, 0, len(instructions), 1
    )
    require(
        "exact_retired_work_bound",
        work == int(header.max_retired_work),
        f"independent loop expansion derives {work} retired instructions; "
        f"header declares {header.max_retired_work}",
    )
    require(
        "retired_work_capability",
        work <= int(capability.limits["max_retired_work"]),
        f"expanded work {work} exceeds capability bound "
        f"{capability.limits['max_retired_work']}",
    )

    # -- schedules, banks, ports, routes, and queue occupancy --------------
    plan = deployment.notes.get("rom_plan")
    plan_regions = _plan_regions(plan)
    plan_objects = {int(region["object_id"]): region for region in plan_regions}
    require(
        "rom_plan_present",
        isinstance(plan, Mapping) and bool(plan_regions),
        "deployment publishes no parseable ROM plan for schedule reconstruction",
    )
    resource_intervals: dict[tuple[int, int, int, int], list[tuple[int, int, int]]] = {}
    resource_bytes = int(
        plan.get("layout", {}).get("resource_bytes", 0)
        if isinstance(plan, Mapping)
        else 0
    )
    for region in plan_regions:
        shards = region.get("shards", [])
        payload_bytes = int(region.get("payload_bytes", 0))
        allocated_bytes = payload_bytes + int(region.get("pad_bytes", 0))
        parsed = [
            tuple(int(value) for value in shard[:7])
            for shard in shards
            if isinstance(shard, (list, tuple)) and len(shard) >= 7
        ]
        require(
            "rom_shard_records",
            len(parsed) == len(shards) and bool(parsed),
            f"ROM region {region.get('region_id')} has a malformed or empty shard list",
        )
        cursor = 0
        for shard in sorted(parsed, key=lambda item: item[4]):
            node, reticle, tile, bank, region_offset, extent, resource_offset = shard
            require(
                "rom_shard_coverage",
                region_offset == cursor and extent > 0,
                f"ROM region {region.get('region_id')} shard coverage jumps from "
                f"{cursor} to {region_offset} or has zero extent",
            )
            cursor = max(cursor, region_offset + extent)
            require(
                "rom_shard_resource_capacity",
                resource_bytes > 0 and resource_offset + extent <= resource_bytes,
                f"ROM region {region.get('region_id')} shard at resource offset "
                f"{resource_offset} does not fit {resource_bytes} bytes",
            )
            reticle_count = max(int(topology.get("reticle_count", 0)), 1)
            tiles_per_reticle = max(int(topology.get("tiles_per_reticle", 0)), 1)
            require(
                "rom_shard_topology",
                node == int(topology.get("local_node_id", 0))
                and 0 <= reticle < reticle_count
                and 0 <= tile < reticle_count * tiles_per_reticle
                and (
                    topology_class == int(TopologyClass.SINGLE_CHIP)
                    or tile // tiles_per_reticle == reticle
                ),
                f"ROM region {region.get('region_id')} shard coordinate "
                f"{(node, reticle, tile, bank)} is outside the admitted topology",
            )
            key = (node, reticle, tile, bank)
            resource_intervals.setdefault(key, []).append(
                (
                    resource_offset,
                    resource_offset + extent,
                    int(region.get("region_id", -1)),
                )
            )
        require(
            "rom_region_fully_sharded",
            cursor == allocated_bytes,
            f"ROM region {region.get('region_id')} shards cover {cursor} bytes, "
            f"payload plus padding declares {allocated_bytes}",
        )
    for key, intervals in resource_intervals.items():
        ordered = sorted(intervals)
        for left, right in zip(ordered, ordered[1:]):
            require(
                "rom_resource_conflict_free",
                left[1] <= right[0],
                f"ROM resource {key} regions {left[2]} and {right[2]} overlap "
                f"at byte intervals {left[:2]} and {right[:2]}",
            )
    if topology_class == int(TopologyClass.WAFER_LOGICAL_DEVICE):
        expected_route_digest = _wafer_route_digest(plan_regions)
        require(
            "wafer_route_table_digest",
            bytes(topology.get("route_table_digest", bytes(32)))
            == expected_route_digest,
            "topology route-table digest does not bind the emitted per-tile "
            "shard coordinate table",
        )
    used_schedules: set[int] = set()
    queue_dispatch_bound: dict[str, int] = {}
    graph_tensors = {tensor.tensor_id: tensor for tensor in graph.tensors}
    resource_issues: list[tuple[int, int, int, int, int, set[int], int]] = []
    queue_pressure_slots = 0
    memory_read_bound = {name: 0 for name in ("rom", "sram", "hbm", "state", "host")}
    memory_write_bound = {name: 0 for name in ("rom", "sram", "hbm", "state", "host")}

    for index, instruction, operator in instruction_operators:
        schedule_id = int(operator.payload["schedule_id"])
        schedule = schedules.get(schedule_id)
        if not require(
            "schedule_present",
            schedule is not None,
            f"operator {operator.descriptor_id} names missing schedule {schedule_id}",
        ):
            continue
        used_schedules.add(schedule_id)
        payload = schedule.payload
        family = int(operator.payload["engine_family"])
        engine_spec = capability.engines.get(_ENGINE_KEY.get(family, ""), {})
        queues = max(int(engine_spec.get("queues", 0)), 0)
        require(
            "engine_advertised",
            queues > 0,
            f"operator {operator.descriptor_id} uses {_mnemonic((family, instruction.sub))} "
            "but the capability advertises no queue for that engine",
        )
        require(
            "schedule_family",
            int(payload["engine_family"]) == family,
            f"schedule {schedule_id} family {payload['engine_family']} does not "
            f"match operator family {family}",
        )
        require(
            "queue_index",
            0 <= int(payload["queue_index"]) < max(queues, 1),
            f"schedule {schedule_id} queue {payload['queue_index']} is outside "
            f"the {queues} advertised {_ENGINE_KEY.get(family, 'unknown')} queues",
        )
        max_outstanding = int(payload["max_outstanding"])
        issue_window = int(payload["issue_window"])
        require(
            "queue_occupancy",
            1
            <= issue_window
            <= max_outstanding
            <= int(capability.limits["max_outstanding_per_queue"]),
            f"schedule {schedule_id} issue/max-outstanding "
            f"{issue_window}/{max_outstanding} exceeds queue bounds",
        )
        rows = int(payload["tile_rows"])
        cols = int(payload["tile_cols"])
        depth = int(payload["tile_depth"])
        lanes = max(int(engine_spec.get("lanes", 0)) or 64, 1)
        require(
            "tile_geometry",
            rows > 0 and cols > 0 and depth > 0 and cols <= lanes,
            f"schedule {schedule_id} tile {rows}x{cols}x{depth} is not positive "
            f"or exceeds {lanes} {_ENGINE_KEY.get(family, 'engine')} lanes",
        )

        input_views = _operator_views(operator, "input_view_", 4, views, require)
        output_views = _operator_views(operator, "output_view_", 2, views, require)
        expected_bank = _bank_mask(input_views, objects, plan_objects)
        expected_port = _port_mask((*input_views, *output_views), objects)
        allocated_ports = _allocated_port_mask(objects)
        expected_route = _route_class(input_views, objects, plan_objects)
        expected_bound = _resource_bound(family, input_views, objects)
        require(
            "rom_bank_mask",
            int(payload["bank_mask"]) == expected_bank,
            f"schedule {schedule_id} bank mask {payload['bank_mask']:#x}; "
            f"ROM operands reconstruct to {expected_bank:#x}",
        )
        actual_port = int(payload["port_mask"])
        require(
            "memory_port_coverage",
            actual_port & expected_port == expected_port,
            f"schedule {schedule_id} port mask {actual_port:#x} omits visible "
            f"operand ports {expected_port:#x}",
        )
        require(
            "memory_ports_allocated",
            actual_port & ~allocated_ports == 0,
            f"schedule {schedule_id} names a port with no emitted mutable "
            f"object: mask {actual_port:#x}, allocated {allocated_ports:#x}",
        )
        require(
            "operator_route_class",
            int(payload["noc_route_class"]) == expected_route,
            f"schedule {schedule_id} route class {payload['noc_route_class']}; "
            f"ROM shards reconstruct to {expected_route}",
        )
        require(
            "resource_bound",
            int(payload["resource_bound"]) == expected_bound,
            f"schedule {schedule_id} resource bound {payload['resource_bound']}; "
            f"operands and engine reconstruct to {expected_bound}",
        )

        rom_banks = max(int(capability.memory.get("rom", {}).get("banks", 0)), 1)
        sram_banks = max(int(capability.memory.get("sram", {}).get("banks", 0)), 1)
        require(
            "bank_mask_capacity",
            int(payload["bank_mask"]) & ~((1 << min(rom_banks, 32)) - 1) == 0,
            f"schedule {schedule_id} names a ROM bank outside the capability",
        )
        require(
            "port_mask_capacity",
            int(payload["port_mask"]) & ~((1 << min(sram_banks, 32)) - 1) == 0,
            f"schedule {schedule_id} names a mutable-memory port outside the "
            "capability",
        )
        link_classes = int(topology.get("link_class_count", 0))
        require(
            "route_class_capacity",
            int(payload["noc_route_class"]) == 0
            if link_classes == 0
            else int(payload["noc_route_class"]) < link_classes,
            f"schedule {schedule_id} route class {payload['noc_route_class']} is "
            f"outside {link_classes} topology classes",
        )

        source_kernel = graph.kernels[int(operator.payload["source_kernel_id"])]
        tiles = max(
            _tile_count_bound(rows, cols, depth, input_views, output_views),
            _graph_tile_count_bound(source_kernel, graph_tensors, rows, cols, depth),
        )
        require(
            "outstanding_has_work",
            max_outstanding <= max(tiles, 1),
            f"schedule {schedule_id} admits {max_outstanding} outstanding tiles "
            f"but its views contain at most {tiles}",
        )
        dynamic = max(multipliers[index], 1)
        resource_issues.append(
            (
                index,
                actual_port,
                family,
                int(payload["queue_index"]),
                int(instruction.signal_event_id),
                _wait_events(instruction, waits, require),
                dynamic,
            )
        )
        queue_pressure_slots += dynamic * max(max_outstanding - issue_window, 0)
        queue_key = f"{_ENGINE_KEY.get(family, str(family))}:{payload['queue_index']}"
        queue_dispatch_bound[queue_key] = (
            queue_dispatch_bound.get(queue_key, 0) + dynamic
        )
        _accumulate_view_bytes(
            input_views, objects, dynamic, memory_read_bound, require
        )
        _accumulate_view_bytes(
            output_views, objects, dynamic, memory_write_bound, require
        )

    require(
        "no_orphan_schedules",
        used_schedules == set(schedules),
        f"{len(set(schedules) - used_schedules)} schedule descriptors are never "
        "referenced by an operator",
    )
    potential_port_conflicts = 0
    for left, right in zip(resource_issues, resource_issues[1:]):
        (_li, left_ports, left_family, left_queue, left_event, _lw, left_dynamic) = left
        (
            _ri,
            right_ports,
            right_family,
            right_queue,
            _re,
            right_wait,
            right_dynamic,
        ) = right
        if not left_ports & right_ports:
            continue
        if (left_family, left_queue) == (right_family, right_queue):
            continue  # one hardware queue serialises the shared port
        if left_event != NO_ID and left_event in right_wait:
            continue  # the explicit dependency serialises the shared port
        potential_port_conflicts += min(left_dynamic, right_dynamic)

    # -- graph dependencies, events, and deadlock freedom -----------------
    signals_by_source: dict[int, set[int]] = {}
    signal_index: dict[int, int] = {}
    for index, instruction in enumerate(instructions):
        event = int(instruction.signal_event_id)
        if event == NO_ID:
            continue
        signal_index[event] = index
        source = int(instruction.source_operation_id)
        if source != NO_ID:
            signals_by_source.setdefault(source, set()).add(event)

    producer = {
        tensor: kernel.index for kernel in graph.kernels for tensor in kernel.outputs
    }
    dependency_edges = 0
    for index, instruction, operator in instruction_operators:
        source = int(operator.payload["source_kernel_id"])
        kernel = graph.kernels[source]
        actual_wait = _wait_events(instruction, waits, require)
        dependencies = list(kernel.inputs)
        if kernel.predicate:
            dependencies.append(kernel.predicate)
        conditional_inputs = {
            int(slot)
            for slot in dict(kernel.attributes.get("operand_present_predicate", {}))
        }
        expected_sources: set[int] = set()
        for dependency_slot, tensor_id in enumerate(dependencies):
            if dependency_slot in conditional_inputs and instruction.flags & int(
                InstructionFlag.PREDICATE_INVERT
            ):
                # This is the explicitly declared operand-absent path.  It
                # must not wait for a producer predicated off under the same
                # condition; the sibling present path is checked separately.
                continue
            original = producer.get(tensor_id)
            if original is None:
                continue
            expected = canonical.get(original, original)
            # The producer is in a later iteration of a compressed run.  It
            # has no instruction or event of its own; LOOP_NEXT completes the
            # final iteration before control leaves the run, which is the
            # dependency certificate for the following band or epilogue.
            if original != expected:
                continue
            if expected == source:
                continue
            # A canonical producer later in the same compressed body is a
            # loop-carried value.  Program order, not a first-iteration event,
            # carries that dependency.
            if order_position.get(expected, -1) >= order_position.get(source, 1 << 30):
                continue
            if graph.kernels[expected].kind == _DIRECT_STATE_KIND:
                continue
            expected_sources.add(expected)
        for expected in expected_sources:
            events = signals_by_source.get(expected, set())
            dependency_edges += 1
            require(
                "producer_signals",
                bool(events),
                f"producer kernel {expected} has no completion event for "
                f"consumer kernel {source}",
            )
            require(
                "producer_consumer_wait",
                bool(events & actual_wait),
                f"kernel {source} does not wait for direct producer kernel "
                f"{expected}; expected one of events {sorted(events)}, found "
                f"{sorted(actual_wait)}",
            )
        for event in actual_wait:
            require(
                "wait_has_earlier_producer",
                event in signal_index and signal_index[event] < index,
                f"instruction {index} waits on event {event} without an earlier "
                "producer",
            )

    for wait in waits.values():
        count = int(wait.payload["producer_count"])
        named = [int(wait.payload[f"producer_{slot}"]) for slot in range(count)]
        require(
            "wait_set_unique",
            len(named) == len(set(named)) and NO_ID not in named,
            f"wait set {wait.descriptor_id} contains duplicate or absent producers",
        )
        require(
            "wait_set_all",
            int(wait.payload["required_count"]) == count,
            f"wait set {wait.descriptor_id} requires "
            f"{wait.payload['required_count']} of {count}; graph dependencies are "
            "conjunctive",
        )

    # -- runtime route/sparse-index bounds --------------------------------
    for kernel in representatives:
        if kernel.kind in {"TOPK", "BIASED_TOPK", "EXPERT_DISPATCH", "ROUTED_MATMUL"}:
            top_k = _first_int(kernel.attributes, "top_k", "k", default=1)
            experts = _first_int(
                kernel.attributes, "expert_count", "experts", default=1
            )
            require(
                "expert_topk_bound",
                1 <= top_k <= int(capability.limits["max_topk"]),
                f"kernel {kernel.index} selects top_k={top_k}, capability admits "
                f"{capability.limits['max_topk']}",
            )
            require(
                "expert_id_bound",
                1 <= experts <= int(capability.limits["max_expert_ids"]),
                f"kernel {kernel.index} addresses {experts} experts, capability "
                f"admits {capability.limits['max_expert_ids']}",
            )
        if kernel.kind in {"INDEX_TOPK", "WINDOW_INDEX", "ATTENTION_SPARSE"}:
            candidates = _first_int(
                kernel.attributes,
                "k",
                "top_k",
                "window_size",
                default=_domain_int(kernel, "candidates", 1),
            )
            require(
                "sparse_index_bound",
                1 <= candidates <= int(capability.limits["max_context_positions"]),
                f"kernel {kernel.index} sparse/index extent {candidates} exceeds "
                "the context-position capability",
            )

    # -- local/on-wafer paths, collectives, credits, and retry buffers -----
    link_instructions = [
        (index, instruction)
        for index, instruction in enumerate(instructions)
        if instruction.major == int(Major.LINK)
    ]
    if topology_class == int(TopologyClass.SINGLE_CHIP):
        require(
            "single_chip_has_no_links",
            not link_instructions and not communications,
            "single-chip ROM deployment emits on-wafer LINK traffic",
        )
    else:
        require(
            "wafer_has_links",
            bool(link_instructions) and bool(communications),
            "wafer ROM deployment has no fabric schedule",
        )

    used_communications: set[int] = set()
    link_bytes_bound = 0
    link_flits_bound = 0
    link_stall_events_bound = 0
    route_classes: set[int] = set()
    layer_loop_ranges = [
        (int(descriptor.payload["body_start"]), int(descriptor.payload["body_end"]))
        for _, descriptor in constant_setups
    ]
    for index, instruction in link_instructions:
        communication = communications.get(instruction.descriptor_id)
        if not require(
            "communication_descriptor",
            communication is not None,
            f"LINK instruction {index} does not name a COMMUNICATION descriptor",
        ):
            continue
        used_communications.add(communication.descriptor_id)
        payload = communication.payload
        route_classes.add(int(payload["route_class"]))
        require(
            "link_in_layer_schedule",
            any(start <= index <= end for start, end in layer_loop_ranges),
            f"wafer LINK instruction {index} is outside every layer schedule",
        )
        require(
            "link_completion_event",
            int(instruction.signal_event_id) != NO_ID,
            f"LINK instruction {index} publishes no completion event",
        )
        require(
            "link_flow_control",
            int(payload["credit_bound"]) > 0
            and int(payload["retry_bound"]) > 0
            and int(payload["timeout_class"]) > 0,
            f"communication {communication.descriptor_id} has zero credit, retry, "
            "or timeout bound",
        )
        extent = int(payload["byte_extent"])
        chunk = int(payload["chunk_bytes"])
        require(
            "link_chunk",
            chunk > 0,
            f"communication {communication.descriptor_id} has zero chunk size",
        )
        expected_collectives = _collectives_for_link(instruction.sub)
        require(
            "link_collective_kind",
            int(payload["collective_op"]) in expected_collectives,
            f"{instruction.mnemonic} names collective operation "
            f"{payload['collective_op']}",
        )
        route_contract = _link_route_contract(instruction.sub)
        if route_contract is not None:
            require(
                "link_route_and_virtual_channel",
                (int(payload["route_class"]), int(payload["virtual_channel"]))
                == route_contract,
                f"{instruction.mnemonic} uses route/VC "
                f"{(payload['route_class'], payload['virtual_channel'])}; "
                f"traffic semantics derive {route_contract}",
            )
        if int(payload["collective_op"]) in {
            int(CollectiveOp.SUM),
            int(CollectiveOp.MAX),
            int(CollectiveOp.MIN),
        }:
            require(
                "collective_numeric_contract",
                int(payload["reduction_numeric_id"]) in numeric_ids,
                f"arithmetic collective {communication.descriptor_id} names no "
                "NUMERIC descriptor",
            )
        require(
            "link_extent",
            extent > 0 or instruction.sub == int(Link.BARRIER),
            f"{instruction.mnemonic} communication {communication.descriptor_id} "
            "has no payload",
        )
        participants = int(payload["participant_count"])
        expected_participants = _participant_count(instruction.sub, payload, topology)
        require(
            "link_participants",
            participants == expected_participants,
            f"communication {communication.descriptor_id} declares {participants} "
            f"participants; topology and scope derive {expected_participants}",
        )
        local = objects.get(int(payload["local_object_id"]))
        remote = objects.get(int(payload["remote_object_id"]))
        required_bytes = max(participants * extent, 64)
        require(
            "link_local_capacity",
            local is not None
            and int(payload["local_offset"]) + required_bytes
            <= int(local.payload["size_bytes"]),
            f"communication {communication.descriptor_id} local participant array "
            "does not fit",
        )
        require(
            "link_remote_capacity",
            remote is not None
            and int(payload["remote_offset"]) + required_bytes
            <= int(remote.payload["size_bytes"])
            and bool(remote.permissions & int(Permission.REMOTE)),
            f"communication {communication.descriptor_id} remote participant array "
            "does not fit or is not exported REMOTE",
        )
        counter_id = int(payload["counter_class_id"])
        require(
            "communication_counter_class",
            counter_id in counter_classes,
            f"communication {communication.descriptor_id} names no counter class",
        )
        dynamic = max(multipliers[index], 1)
        traffic_factor = max(participants, 1)
        link_bytes_bound += dynamic * extent * traffic_factor
        if extent:
            link_flits_bound += dynamic * ceil(extent / max(chunk, 1)) * traffic_factor
        link_stall_events_bound += dynamic * int(payload["retry_bound"])

    require(
        "no_orphan_communications",
        used_communications == set(communications),
        f"{len(set(communications) - used_communications)} communication "
        "descriptors are not issued",
    )
    if link_instructions:
        expected_classes = set(range(int(topology.get("link_class_count", 0))))
        require(
            "fabric_route_classes",
            route_classes == expected_classes,
            f"fabric schedule uses route classes {sorted(route_classes)}, topology "
            f"declares {sorted(expected_classes)}",
        )
        for band, descriptor in matched_band_loops:
            start = int(descriptor.payload["body_start"])
            end = int(descriptor.payload["body_end"])
            actual_subs = [
                instruction.sub
                for instruction in instructions[start:end]
                if instruction.major == int(Major.LINK)
            ]
            expected_subs = [int(Link.MULTICAST), int(Link.GATHER)]
            if any(kernel.kind == "EXPERT_DISPATCH" for kernel in band.body):
                expected_subs.append(int(Link.SCATTER))
            expected_subs.extend(
                [int(Link.COLLECTIVE), int(Link.SEND), int(Link.BARRIER)]
            )
            require(
                "wafer_band_path",
                actual_subs == expected_subs,
                f"layer band beginning {band.first_layer} fabric path is "
                f"{actual_subs}; graph anchors derive {expected_subs}",
            )

    # -- state transaction order ------------------------------------------
    prepared: dict[int, int] = {}
    closed: dict[int, int] = {}
    first_non_state = next(
        (
            index
            for index, instruction in enumerate(instructions)
            if instruction.major not in {int(Major.STATE), int(Major.CONTROL)}
        ),
        len(instructions),
    )
    complete_indices = [
        index
        for index, instruction in enumerate(instructions)
        if instruction.major == int(Major.CONTROL)
        and instruction.sub == int(Control.COMPLETE)
    ]
    for index, instruction in enumerate(instructions):
        if instruction.major != int(Major.STATE):
            continue
        descriptor_id = int(instruction.descriptor_id)
        if instruction.sub == int(State.PREPARE):
            require(
                "state_prepare_once",
                descriptor_id not in prepared and descriptor_id not in closed,
                f"state {descriptor_id} is prepared more than once or after closure",
            )
            prepared[descriptor_id] = index
            require(
                "state_prepare_before_work",
                index < first_non_state,
                f"state {descriptor_id} is prepared after engine work starts",
            )
        elif instruction.sub in {int(State.COMMIT), int(State.DISCARD)}:
            require(
                "state_close_after_prepare",
                descriptor_id in prepared and descriptor_id not in closed,
                f"state {descriptor_id} closes without one open prepare",
            )
            closed[descriptor_id] = index
    require(
        "all_states_transactional",
        set(prepared) == set(states) == set(closed),
        f"state transaction sets differ: descriptors={sorted(states)}, "
        f"prepare={sorted(prepared)}, close={sorted(closed)}",
    )
    if complete_indices:
        terminal = complete_indices[0]
        require(
            "state_close_before_completion",
            all(index < terminal for index in closed.values()),
            "a state transaction closes after COMPLETE",
        )
    require(
        "single_completion",
        len(complete_indices) == 1 and complete_indices[0] == len(instructions) - 1,
        f"program has COMPLETE at {complete_indices}, expected one final instruction",
    )

    # -- counter certificate structure ------------------------------------
    for descriptor in counter_classes.values():
        count = int(descriptor.payload["event_count"])
        counters = [int(descriptor.payload[f"counter_{slot}"]) for slot in range(count)]
        group = int(descriptor.payload["group"])
        require(
            "counter_class_nonempty",
            count > 0 and NO_ID not in counters and len(counters) == len(set(counters)),
            f"counter class {descriptor.descriptor_id} is empty or duplicated",
        )
        require(
            "counter_group_namespace",
            all((counter >> 24) == group for counter in counters),
            f"counter class {descriptor.descriptor_id} contains an event outside "
            f"group {group}",
        )
    for operator in operators.values():
        counter_id = int(operator.payload["counter_class_id"])
        require(
            "operator_counter_class",
            counter_id in counter_classes,
            f"operator {operator.descriptor_id} names no counter class",
        )

    # -- memory capacity and immutable placement ---------------------------
    footprint = {name: 0 for name in ("rom", "sram", "hbm", "state", "host")}
    for descriptor in objects.values():
        storage = StorageClass(int(descriptor.payload["storage_class"])).name.lower()
        footprint[storage] = footprint.get(storage, 0) + int(
            descriptor.payload["size_bytes"]
        )
    for storage in ("rom", "sram"):
        limit = int(capability.memory.get(storage, {}).get("bytes", 0))
        require(
            "memory_capacity",
            footprint.get(storage, 0) <= limit,
            f"{storage} objects occupy {footprint.get(storage, 0)} bytes, "
            f"capability declares {limit}",
        )
    hbm_session = footprint.get("hbm", 0) + footprint.get("state", 0)
    hbm_limit = int(capability.memory.get("hbm", {}).get("bytes", 0))
    require(
        "memory_capacity",
        hbm_session <= hbm_limit,
        f"HBM plus state objects occupy {hbm_session} bytes, capability declares "
        f"{hbm_limit}",
    )

    # -- frozen ABI verifier -----------------------------------------------
    verifier = verify_deployment(deployment, capability)
    require(
        "abi_verifier",
        verifier.admitted,
        "the frozen ABI 3.0 verifier rejected the deployment",
    )
    errors.extend(f"verifier: {message}" for message in verifier.errors)

    return {
        "schema": SCHEDULE_CHECK_SCHEMA,
        "status": "pass" if not errors else "fail",
        "ok": not errors,
        "target_id": deployment.target_id,
        "model_id": graph.model_id,
        "backend": deployment.backend,
        "graph_id": graph.graph_id,
        "deployment_sha256": deployment.deployment_digest.hex(),
        "capability_sha256": capability.digest,
        "check_count": len(checks),
        "passed_check_count": sum(bool(value) for value in checks.values()),
        "checks": dict(sorted(checks.items())),
        "errors": errors,
        "warnings": warnings,
        "expected": {
            "bands": [
                {
                    "first_layer": band.first_layer,
                    "layers_covered": len(band.layers),
                    "period": band.period,
                    "loop_trip": band.iterations,
                    "body_kernels": len(band.body),
                }
                for band in bands
            ],
            "dependency_edges": dependency_edges,
            "representative_kernels": len(representatives),
            "retired_work": work,
        },
        "actual": {
            "instructions": len(instructions),
            "descriptors": len(table),
            "operators": len(operators),
            "schedules": len(schedules),
            "wait_sets": len(waits),
            "communications": len(communications),
            "states": len(states),
            "link_instructions": len(link_instructions),
        },
        "counter_bounds": {
            "memory_read_bytes": dict(sorted(memory_read_bound.items())),
            "memory_write_bytes": dict(sorted(memory_write_bound.items())),
            "link_payload_bytes": link_bytes_bound,
            "link_flits": link_flits_bound,
            "link_retry_or_stall_events": link_stall_events_bound,
            "potential_mutable_port_conflicts": potential_port_conflicts,
            "queue_pressure_slots": queue_pressure_slots,
            "queue_dispatches": dict(sorted(queue_dispatch_bound.items())),
            "retired_work": work,
        },
        "memory_footprint": dict(sorted(footprint.items())),
        "verifier": verifier.to_dict(),
    }


def _extent(value: Any) -> int:
    if isinstance(value, Symbolic):
        return max(int(value.maximum or value.multiplier or 1), 1)
    return max(int(value), 1)


def _layer_signature(
    kernels: Sequence[Kernel], tensors: Mapping[str, Tensor]
) -> tuple[Any, ...]:
    """Structural layer identity, including constant weight stride facts."""

    rows = []
    for kernel in kernels:
        weight_extents = []
        for name in kernel.inputs:
            tensor = tensors[name]
            weight_extents.append(
                int(tensor.binding.bytes)
                if tensor.role in _WEIGHT_ROLES and tensor.binding is not None
                else -1
            )
        rows.append(
            (
                kernel.kind,
                kernel.numeric_contract,
                tuple(tensors[name].role for name in kernel.inputs),
                tuple(tensors[name].dtype for name in kernel.inputs),
                tuple(tensors[name].role for name in kernel.outputs),
                tuple(tensors[name].dtype for name in kernel.outputs),
                tuple(weight_extents),
                len(kernel.state_reads),
                len(kernel.state_writes),
                tuple(kernel.phases),
            )
        )
    return tuple(rows)


def _reconstruct_bands(
    graph: KernelGraph,
) -> tuple[list[_Band], dict[int, int], tuple[Kernel, ...]]:
    """Factor the layer signature stream without calling the compressor.

    The search grows a candidate repeated prefix and chooses the span that
    removes the most layers.  The producer uses a different helper and data
    structure; agreement is therefore evidence rather than shared state.
    """

    tensors = {tensor.tensor_id: tensor for tensor in graph.tensors}
    by_layer: dict[int, list[Kernel]] = {}
    layered_positions = []
    for position, kernel in enumerate(graph.kernels):
        if kernel.layer is not None:
            by_layer.setdefault(int(kernel.layer), []).append(kernel)
            layered_positions.append(position)
    if not by_layer:
        return (
            [],
            {kernel.index: kernel.index for kernel in graph.kernels},
            tuple(graph.kernels),
        )
    layers = sorted(by_layer)
    signatures = [_layer_signature(by_layer[layer], tensors) for layer in layers]
    bands: list[_Band] = []
    cursor = 0
    while cursor < len(layers):
        best_period = 1
        best_iterations = 1
        best_eliminated = 0
        for period in range(1, min(_MAX_LAYER_PERIOD, len(layers) - cursor) + 1):
            iterations = 1
            while cursor + (iterations + 1) * period <= len(layers):
                candidate = cursor + iterations * period
                if (
                    signatures[candidate : candidate + period]
                    != signatures[cursor : cursor + period]
                ):
                    break
                if any(
                    layers[candidate + offset]
                    != layers[cursor + offset] + iterations * period
                    for offset in range(period)
                ):
                    break
                iterations += 1
            eliminated = (iterations - 1) * period
            if eliminated > best_eliminated or (
                eliminated == best_eliminated and period < best_period
            ):
                best_eliminated = eliminated
                best_period = period
                best_iterations = iterations
        covered = tuple(layers[cursor : cursor + best_period * best_iterations])
        body = tuple(
            kernel for layer in covered[:best_period] for kernel in by_layer[layer]
        )
        bands.append(
            _Band(
                first_layer=covered[0],
                layers=covered,
                period=best_period,
                iterations=best_iterations,
                body=body,
            )
        )
        cursor += best_period * best_iterations

    canonical = {kernel.index: kernel.index for kernel in graph.kernels}
    reps: list[Kernel] = []
    for band in bands:
        blocks = []
        for iteration in range(band.iterations):
            block = tuple(
                kernel
                for layer in band.layers[
                    iteration * band.period : (iteration + 1) * band.period
                ]
                for kernel in by_layer[layer]
            )
            blocks.append(block)
        for block in blocks:
            if len(block) != len(band.body):
                continue
            for representative, peer in zip(band.body, block):
                canonical[peer.index] = representative.index
        reps.extend(band.body)
    first = min(layered_positions)
    last = max(layered_positions)
    representatives = (
        tuple(graph.kernels[:first]) + tuple(reps) + tuple(graph.kernels[last + 1 :])
    )
    return bands, canonical, representatives


def _representative_order(
    graph: KernelGraph, bands: Sequence[_Band]
) -> tuple[Kernel, ...]:
    layered = [
        index for index, kernel in enumerate(graph.kernels) if kernel.layer is not None
    ]
    if not layered:
        return tuple(graph.kernels)
    return (
        tuple(graph.kernels[: layered[0]])
        + tuple(kernel for band in bands for kernel in band.body)
        + tuple(graph.kernels[layered[-1] + 1 :])
    )


def _match_band_loop(
    band: _Band,
    candidates: Sequence[tuple[int, Any]],
    instructions: Sequence[Instruction],
    operators: Mapping[int, Any],
) -> tuple[int, Any] | None:
    expected = [
        kernel.index for kernel in band.body if kernel.kind not in _TRANSACTION_KINDS
    ]
    for setup, descriptor in candidates:
        start = int(descriptor.payload["body_start"])
        end = int(descriptor.payload["body_end"])
        if not (start == setup + 1 and start <= end < len(instructions)):
            continue
        found: list[int] = []
        for instruction in instructions[start:end]:
            source = int(instruction.source_operation_id)
            if source == NO_ID:
                continue
            if found and found[-1] == source:
                continue
            if source not in found:
                found.append(source)
        if all(source in found for source in expected):
            positions = [found.index(source) for source in expected]
            if positions == sorted(positions):
                return setup, descriptor
    return None


def _expected_engine(kernel: Kernel) -> tuple[int, int]:
    # These are semantic reconciliations visible in the neutral graph itself,
    # not imports from the ROM producer.
    if kernel.kind == "HASH_ROUTE":
        return int(Major.TENSOR), int(TensorOp.EMBED_LOOKUP)
    if kernel.kind == "COMPRESS_PROJECT" and len(kernel.inputs) == 2:
        return int(Major.TENSOR), int(TensorOp.MATMUL)
    engine = engine_for(kernel.kind)
    return int(engine.family), int(engine.sub)


def _mnemonic(pair: tuple[int, int]) -> str:
    try:
        family = Major(pair[0])
        from runtime.abi3.constants import SUBOPCODES

        return f"{family.name}.{SUBOPCODES[family](pair[1]).name}"
    except (KeyError, ValueError):
        return f"{pair[0]:#x}.{pair[1]:#x}"


def _expanded_work(
    instructions: Sequence[Instruction],
    loops: Mapping[int, Any],
    multipliers: list[int],
    require: Callable[[str, bool, str], bool],
    start: int,
    end: int,
    factor: int,
) -> int:
    """Recursively expand loop intervals and record dynamic issue counts."""

    work = 0
    index = start
    while index < end:
        instruction = instructions[index]
        if instruction.major == int(Major.CONTROL) and instruction.sub == int(
            Control.LOOP_SETUP
        ):
            descriptor = loops.get(instruction.control_id)
            if descriptor is None:
                multipliers[index] += factor
                work += factor
                index += 1
                continue
            body_start = int(descriptor.payload["body_start"])
            body_end = int(descriptor.payload["body_end"])
            trip = max(int(descriptor.payload["max_iterations"]), 1)
            valid = (
                body_start == index + 1
                and body_start <= body_end < end
                and instructions[body_end].major == int(Major.CONTROL)
                and instructions[body_end].sub == int(Control.LOOP_NEXT)
                and instructions[body_end].control_id == instruction.control_id
            )
            require(
                "loop_structure",
                valid,
                f"loop setup {index} and descriptor {instruction.control_id} do "
                "not delimit one nested body",
            )
            if not valid:
                multipliers[index] += factor
                work += factor
                index += 1
                continue
            multipliers[index] += factor
            work += factor
            work += _expanded_work(
                instructions,
                loops,
                multipliers,
                require,
                body_start,
                body_end,
                factor * trip,
            )
            multipliers[body_end] += factor * trip
            work += factor * trip
            index = body_end + 1
            continue
        multipliers[index] += factor
        work += factor
        index += 1
    return work


def _plan_regions(plan: Any) -> list[Mapping[str, Any]]:
    if not isinstance(plan, Mapping):
        return []
    regions = plan.get("regions", [])
    if not isinstance(regions, list):
        return []
    return [region for region in regions if isinstance(region, Mapping)]


def _wafer_route_digest(regions: Sequence[Mapping[str, Any]]) -> bytes:
    """Rebuild the route-table digest from the published shard coordinates."""

    body = {
        "schema": "opentallas.rom.wafer_route_table.v1",
        "shards": [
            [int(region["region_id"]), *[int(value) for value in shard]]
            for region in regions
            for shard in region.get("shards", [])
        ],
    }
    return hashlib.sha256(canonical_json(body)).digest()


def _operator_views(
    operator: Any,
    prefix: str,
    count: int,
    views: Mapping[int, Any],
    require: Callable[[str, bool, str], bool],
) -> tuple[Any, ...]:
    out = []
    for slot in range(count):
        descriptor_id = int(operator.payload[f"{prefix}{slot}"])
        if descriptor_id == NO_ID:
            continue
        view = views.get(descriptor_id)
        require(
            "operator_view_type",
            view is not None,
            f"operator {operator.descriptor_id} {prefix}{slot} names non-view "
            f"descriptor {descriptor_id}",
        )
        if view is not None:
            out.append(view)
    return tuple(out)


def _bank_mask(
    input_views: Sequence[Any],
    objects: Mapping[int, Any],
    plan_objects: Mapping[int, Mapping[str, Any]],
) -> int:
    mask = 0
    for view in input_views:
        object_id = int(view.primary_object_id)
        obj = objects.get(object_id)
        if obj is None or int(obj.payload["storage_class"]) != int(StorageClass.ROM):
            continue
        region = plan_objects.get(object_id)
        if region is None:
            continue  # mask-programmed generated constant, not a planned bank
        for shard in region.get("shards", []):
            if not isinstance(shard, (list, tuple)) or len(shard) < 4:
                continue
            tile = int(shard[2])
            bank = int(shard[3])
            index = tile or bank
            mask |= 1 << (index % 32)
    return mask


def _port_mask(views: Sequence[Any], objects: Mapping[int, Any]) -> int:
    mask = 0
    for view in views:
        obj = objects.get(int(view.primary_object_id))
        if obj is None or int(obj.payload["storage_class"]) == int(StorageClass.ROM):
            continue
        port = int(obj.payload["bank_or_tile"])
        if 0 <= port < 32:
            mask |= 1 << port
    return mask


def _allocated_port_mask(objects: Mapping[int, Any]) -> int:
    """Mutable logical ports that have a concrete object behind them.

    A substituted host input and a few ABI auxiliary operands reserve a port in
    the source schedule while their OPERATOR row names no ordinary tensor view.
    Those hidden uses cannot be reconstructed as an exact per-operator mask
    from the wire records.  They can still be proved to name a real allocated
    port, while every visible operand must appear explicitly.
    """

    mask = 0
    for obj in objects.values():
        if int(obj.payload["storage_class"]) == int(StorageClass.ROM):
            continue
        port = int(obj.payload["bank_or_tile"])
        if 0 <= port < 32:
            mask |= 1 << port
    return mask


def _route_class(
    input_views: Sequence[Any],
    objects: Mapping[int, Any],
    plan_objects: Mapping[int, Mapping[str, Any]],
) -> int:
    reticles: set[int] = set()
    tiles: set[int] = set()
    for view in input_views:
        object_id = int(view.primary_object_id)
        obj = objects.get(object_id)
        if obj is None or int(obj.payload["storage_class"]) != int(StorageClass.ROM):
            continue
        region = plan_objects.get(object_id)
        if region is None:
            continue
        for shard in region.get("shards", []):
            if isinstance(shard, (list, tuple)) and len(shard) >= 3:
                reticles.add(int(shard[1]))
                tiles.add(int(shard[2]))
    if len(reticles) > 1:
        return 2
    if len(tiles) > 1:
        return 1
    return 0


def _resource_bound(
    family: int, input_views: Sequence[Any], objects: Mapping[int, Any]
) -> int:
    has_rom = any(
        (obj := objects.get(int(view.primary_object_id))) is not None
        and int(obj.payload["storage_class"]) == int(StorageClass.ROM)
        for view in input_views
    )
    bound = _ROM_READ if has_rom and family == int(Major.TENSOR) else _MEMORY_PORT
    if family == int(Major.ROUTE):
        return _TENSOR_LANES
    if family == int(Major.SELECTION):
        return _SELECTION
    if family == int(Major.STATE):
        return _STATE_TRANSACTION
    return bound


def _view_elements(view: Any) -> int:
    rank = int(view.payload["rank"])
    return prod(max(int(view.payload[f"dim{axis}"]), 1) for axis in range(rank))


def _view_bytes(view: Any) -> int:
    """Physical byte span of a strided view, not its logical element count.

    Broadcast operands intentionally have a zero stride.  Multiplying their
    dimensions would claim they overrun the one plane they repeatedly read;
    the highest addressed element is the actual storage proof.
    """

    bits = int(DTYPE_BITS[DType(int(view.payload["dtype"]))])
    rank = int(view.payload["rank"])
    highest = int(view.payload["element_offset"])
    for axis in range(rank):
        highest += max(int(view.payload[f"dim{axis}"]) - 1, 0) * int(
            view.payload[f"stride{axis}"]
        )
    return ceil((highest + 1) * bits / 8)


def _tile_count_bound(
    rows: int,
    cols: int,
    depth: int,
    input_views: Sequence[Any],
    output_views: Sequence[Any],
) -> int:
    views = list(output_views) or list(input_views)
    if not views:
        return 1
    principal = views[0]
    rank = int(principal.payload["rank"])
    logical_rows = max(int(principal.payload["dim0"]), 1)
    logical_cols = max(int(principal.payload[f"dim{rank - 1}"]), 1)
    reduction = 1
    if input_views:
        candidate = input_views[-1]
        in_rank = int(candidate.payload["rank"])
        reduction = max(int(candidate.payload[f"dim{in_rank - 1}"]), 1)
    return (
        ceil(logical_rows / rows) * ceil(logical_cols / cols) * ceil(reduction / depth)
    )


def _graph_tile_count_bound(
    kernel: Kernel,
    tensors: Mapping[str, Tensor],
    tile_rows: int,
    tile_cols: int,
    tile_depth: int,
) -> int:
    """Conservative work tiles from the neutral iteration domain.

    An ABI operator may expose only one feature group or one phase-specific
    view even though its schedule prices the complete neutral operation.  The
    source graph is therefore the authority for the upper work envelope; using
    only that narrowed view would incorrectly call legitimate queue depth idle.
    """

    weights = [
        tensors[name]
        for name in kernel.inputs
        if name in tensors and tensors[name].role in _WEIGHT_ROLES
    ]
    outputs = [tensors[name] for name in kernel.outputs if name in tensors]
    rows = _domain_int(kernel, "tokens", 0)
    if rows <= 0:
        rows = _domain_int(kernel, "rows", 0)
    if rows <= 0 and outputs:
        rows = _extent(outputs[0].shape[0])
    rows = max(rows, 1)
    if weights:
        dims = tuple(_extent(dim) for dim in weights[0].shape)
        width = max(dims[0], 1)
        reduction = max(dims[-1], 1)
    elif outputs:
        dims = tuple(_extent(dim) for dim in outputs[0].shape)
        width = max(dims[-1], 1)
        reduction = 1
    else:
        width = reduction = 1
    return (
        ceil(rows / tile_rows) * ceil(width / tile_cols) * ceil(reduction / tile_depth)
    )


def _storage_name(obj: Any) -> str:
    return StorageClass(int(obj.payload["storage_class"])).name.lower()


def _accumulate_view_bytes(
    views: Sequence[Any],
    objects: Mapping[int, Any],
    multiplier: int,
    totals: dict[str, int],
    require: Callable[[str, bool, str], bool],
) -> None:
    for view in views:
        obj = objects.get(int(view.primary_object_id))
        if obj is None:
            continue
        size = _view_bytes(view)
        require(
            "view_object_capacity",
            size <= int(obj.payload["size_bytes"]),
            f"view {view.descriptor_id} spans {size} bytes, object "
            f"{obj.descriptor_id} holds {obj.payload['size_bytes']}",
        )
        totals[_storage_name(obj)] = (
            totals.get(_storage_name(obj), 0) + size * multiplier
        )


def _wait_events(
    instruction: Instruction,
    waits: Mapping[int, Any],
    require: Callable[[str, bool, str], bool],
) -> set[int]:
    if instruction.wait_set_id == NO_ID:
        return set()
    descriptor = waits.get(int(instruction.wait_set_id))
    if not require(
        "wait_descriptor_type",
        descriptor is not None,
        f"instruction names non-wait descriptor {instruction.wait_set_id}",
    ):
        return set()
    count = int(descriptor.payload["producer_count"])
    return {int(descriptor.payload[f"producer_{slot}"]) for slot in range(count)}


def _first_int(values: Mapping[str, Any], *names: str, default: int) -> int:
    for name in names:
        value = values.get(name)
        if isinstance(value, int) and not isinstance(value, bool):
            return int(value)
    return int(default)


def _domain_int(kernel: Kernel, name: str, default: int) -> int:
    value = kernel.iteration_domain.get(name)
    return _extent(value) if value is not None else int(default)


def _collectives_for_link(sub: int) -> set[int]:
    point = int(CollectiveOp.POINT_TO_POINT)
    if sub in {
        int(Link.SEND),
        int(Link.RECEIVE),
        int(Link.REMOTE_DMA),
        int(Link.BARRIER),
    }:
        return {point}
    if sub == int(Link.MULTICAST):
        return {int(CollectiveOp.BROADCAST)}
    if sub == int(Link.GATHER):
        return {int(CollectiveOp.ALL_GATHER)}
    if sub == int(Link.SCATTER):
        return {int(CollectiveOp.CONCAT), int(CollectiveOp.REDUCE_SCATTER)}
    if sub == int(Link.COLLECTIVE):
        return {
            int(CollectiveOp.SUM),
            int(CollectiveOp.MAX),
            int(CollectiveOp.MIN),
            int(CollectiveOp.REDUCE_SCATTER),
        }
    return set()


def _link_route_contract(sub: int) -> tuple[int, int] | None:
    """Route class and virtual channel assigned to each semantic traffic kind."""

    return {
        int(Link.MULTICAST): (0, 0),
        int(Link.GATHER): (1, 1),
        int(Link.SCATTER): (2, 2),
        int(Link.COLLECTIVE): (2, 2),
        int(Link.SEND): (0, 3),
        int(Link.BARRIER): (1, 3),
    }.get(int(sub))


def _participant_count(
    link_sub: int, payload: Mapping[str, Any], topology: Mapping[str, Any]
) -> int:
    if link_sub in {int(Link.SEND), int(Link.RECEIVE), int(Link.REMOTE_DMA)}:
        return 2
    scope = ParticipantScope(int(payload["participant_scope"]))
    if scope is ParticipantScope.NODE:
        count = int(topology.get("node_count", 0))
    elif scope is ParticipantScope.RETICLE:
        count = int(topology.get("reticle_count", 0))
    else:
        count = int(topology.get("reticle_count", 0)) * int(
            topology.get("tiles_per_reticle", 0)
        )
    groups = int(topology.get("route_group_count", 0))
    if int(payload["group_id"]) != NO_ID and groups > 1 and count % groups == 0:
        count //= groups
    return count


__all__ = ["SCHEDULE_CHECK_SCHEMA", "check_rom_schedule"]
