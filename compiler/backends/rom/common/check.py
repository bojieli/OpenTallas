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
from compiler.backends.schedule_rule import (
    COLUMN_LANE_FAMILIES,
    E9_TILE_COLS,
    operator_shape as _e9_operator_shape,
    sram_banks as _e9_sram_banks,
    sram_ports as _e9_sram_ports,
    staging_bank_mask as _e9_staging_bank_mask,
)
from runtime.abi3.capability import Capability, canonical_json
from runtime.abi3.constants import (
    Control,
    DTYPE_BITS,
    DType,
    Dma,
    InstructionFlag,
    Link,
    Major,
    NO_ID,
    NO_NODE,
    ParticipantScope,
    Permission,
    Reduction,
    RoundingMode,
    State,
    StorageClass,
    Tensor as TensorOp,
    TopologyClass,
    Vector,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import (
    CollectiveOp,
    Comparison,
    ExtendedDescriptorType,
    Phase,
    PredicateKind,
    SelectorKind,
    Symbol,
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

#: Topology classes that place ROM by ``(node, bank)`` rather than by
#: ``(reticle, tile)``: every node is its own placement target and the
#: reticle/tile axes are unused.  ``CLUSTER_32`` is the 32-node array;
#: ``CLUSTER_N`` (amendment AM-R1) is the same machine shape at a node count
#: the capability declares, which is what the DeepSeek-V4.1 ROM array is.  A
#: class missing from this set is checked as a single placed device, which for
#: a multi-node ROM array refuses every shard on a node other than zero --
#: found while lowering ``deepseek_v41_array`` onto ``CLUSTER_N``.
_NODE_PLACED_TOPOLOGY_CLASSES = frozenset(
    {int(TopologyClass.CLUSTER_32), int(TopologyClass.CLUSTER_N)}
)

_WEIGHT_ROLES = frozenset({"weight", "constant"})
_TRANSACTION_KINDS = frozenset({"STATE_PREPARE", "STATE_COMMIT"})
_DIRECT_STATE_KIND = "STATE_READ"
_DIRECT_BUFFER_STATE_CLASSES = frozenset(
    {"compressed_kv", "compressor_window", "kv_cache", "kv_window"}
)
_MAX_LAYER_PERIOD = 8

# The generator may materialise the dispatch rows before issuing the frozen
# ROUTE.EXPERT_DISPATCH operation.  Both instructions retain the source kernel
# ID, so the checker permits precisely this extra operation and no generic
# backend-private opcode.
_AUXILIARY_ENGINE_OPS: Mapping[str, frozenset[tuple[int, int]]] = {
    "EXPERT_DISPATCH": frozenset({(int(Major.DMA), 0)}),  # DMA.TRANSFER
    # The released rolling compressor is expanded into ordinary frozen ABI
    # 3.0 dataflow.  This allow-list admits only those existing operations;
    # ``_check_rolling_compressor`` below independently proves their exact
    # views, predicates, constants, generators, dependencies, and counts.
    "COMPRESS_STATE_UPDATE": frozenset(
        {
            (int(Major.DMA), int(Dma.TRANSFER)),
            (int(Major.DMA), int(Dma.FILL)),
            (int(Major.DMA), int(Dma.GATHER)),
            (int(Major.DMA), int(Dma.SCATTER)),
            (int(Major.REDUCTION), int(Reduction.ORDERED_SUM)),
        }
    ),
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
    numerics = {
        d.descriptor_id: d for d in by_type[ExtendedDescriptorType.NUMERIC]
    }
    numeric_ids = set(numerics)
    operators = {d.descriptor_id: d for d in by_type[ExtendedDescriptorType.OPERATOR]}
    predicates = {
        d.descriptor_id: d for d in by_type[ExtendedDescriptorType.PREDICATE]
    }
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
    direct_state_ids = frozenset(
        state.state_id
        for state in graph.states
        if state.state_class in _DIRECT_BUFFER_STATE_CLASSES
    )
    transactional_state_ids = frozenset(
        state.state_id
        for state in graph.states
        if state.state_id not in direct_state_ids
    )
    # Qwen's append result tensors and attention-history tensors have distinct
    # names, so tensor producer edges alone cannot prove the DMA-to-attention
    # hazard.  Reconstruct the preceding writers from the neutral state
    # effects, independently of the producer's resource-event bookkeeping.
    kv_cache_ids = frozenset(
        state.state_id for state in graph.states if state.state_class == "kv_cache"
    )
    kv_writers: dict[str, set[int]] = {}
    kv_dependencies: dict[int, set[int]] = {}
    for kernel in expected_order:
        dependencies: set[int] = set()
        if kernel.kind not in _TRANSACTION_KINDS:
            for state_id in kernel.state_reads:
                if state_id in kv_cache_ids:
                    dependencies.update(kv_writers.get(state_id, ()))
        if dependencies:
            kv_dependencies[kernel.index] = dependencies
        if kernel.kind not in _TRANSACTION_KINDS:
            for state_id in kernel.state_writes:
                if state_id in kv_cache_ids:
                    kv_writers.setdefault(state_id, set()).add(kernel.index)
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
        match = _match_band_loop(
            band,
            unmatched,
            instructions,
            operators,
            direct_state_ids,
        )
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
            if _uses_only_direct_state(kernel, direct_state_ids):
                # In the fail-stop ABI 3.0 profile the ordinary HBM object is
                # already the execution image.  STATE_READ therefore carries
                # an IR dependency/view alias and intentionally emits no
                # STATE-family instruction.
                continue
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
        if kernel.kind == "ROUTED_MATMUL" and int(topology.get("node_count", 1)) > 1:
            # On a multi-node topology a routed contraction's owner-partial
            # rows are cleared, packed, all-reduced and unpacked by a
            # data-bearing reduction.  Those three DMA operations are admitted
            # here only because ``data_bearing_expert_reduction`` below proves
            # the whole chain -- its shape, its waits, its buffers and that the
            # fill covers the participant slot's declared maximum with positive
            # zero -- for every such kernel; an unproven move still fails there.
            permitted = permitted | {
                (int(Major.DMA), int(Dma.TRANSFER)),
                (int(Major.DMA), int(Dma.FILL)),
            }
        require(
            "no_private_engine_ops",
            pairs <= permitted,
            f"kernel {kernel.index} ({kernel.kind}) emits private/unexplained "
            f"engine operations {sorted(_mnemonic(pair) for pair in pairs - permitted)}",
        )

    rolling_predicates = _check_rolling_compressor(
        graph=graph,
        deployment=deployment,
        expected_order=expected_order,
        instructions=instructions,
        by_source=by_source,
        objects=objects,
        views=views,
        numerics=numerics,
        predicates=predicates,
        waits=waits,
        states=states,
        require=require,
    )

    # A dynamic tensor-view term can add POSITION_START but cannot divide it.
    # Independently prove that every compressed-cache scatter reads the
    # generated quotient table with the exact divisor and addressing geometry
    # stated by the graph.  Merely reproducing a generated object's own digest
    # would not prove that it is the right generated object for this operand.
    for kernel in expected_order:
        if (
            str(kernel.attributes.get("cache_row", ""))
            != "completed_absolute_position_floor_div_ratio"
        ):
            continue
        divisor = int(kernel.attributes.get("ratio", 0) or 0)
        require(
            "floor_divisor_positive",
            divisor > 0,
            f"kernel {kernel.index} declares compressed row divisor {divisor}",
        )
        emitted = [
            item
            for item in by_source.get(kernel.index, ())
            if (item[1].major, item[1].sub)
            == (int(Major.DMA), int(Dma.SCATTER))
        ]
        expected_scatter_count = (
            2
            if str(kernel.attributes.get("execution_predicate", ""))
            in rolling_predicates
            else 1
        )
        if not require(
            "floor_div_scatter_present",
            len(emitted) == expected_scatter_count,
            f"kernel {kernel.index} has {len(emitted)} compressed-row scatters, "
            f"expected {expected_scatter_count}",
        ):
            continue
        for _index, _instruction, operator in emitted:
            index_view = views.get(int(operator.payload["input_view_0"]))
            if not require(
                "floor_div_index_view_present",
                index_view is not None,
                f"kernel {kernel.index} compressed-row scatter has no index view",
            ):
                continue
            source = deployment.objects.get(int(index_view.primary_object_id))
            parameters = dict(source.parameters) if source is not None else {}
            require(
                "floor_div_generator_exact",
                source is not None
                and source.kind == "generated"
                and source.generator == "floor_div_indices_v1"
                and int(parameters.get("divisor", 0)) == divisor,
                f"kernel {kernel.index} compressed-row index is not generated as "
                f"position // {divisor}",
            )
            require(
                "floor_div_generator_extent",
                int(parameters.get("count", 0))
                > int(capability.limits["max_context_positions"]),
                f"kernel {kernel.index} quotient table does not extend beyond the "
                "maximum admissible position",
            )
            payload = index_view.payload
            terms = _view_terms(index_view)
            require(
                "floor_div_index_geometry",
                int(payload["stride0"]) == divisor
                and (
                    int(SelectorKind.RUNTIME_SYMBOL),
                    int(Symbol.POSITION_START),
                    1,
                )
                in terms,
                f"kernel {kernel.index} quotient view does not use storage stride "
                f"{divisor} with POSITION_START coefficient one",
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
            if topology_class in _NODE_PLACED_TOPOLOGY_CLASSES:
                # A conventional-chip cluster places by (node, bank): every
                # node is a placement target and the reticle/tile axes are
                # unused.  Node identity is what the array's expert ownership
                # rests on, so a shard on a node the topology does not declare
                # is refused outright.
                node_count = max(int(topology.get("node_count", 0)), 1)
                inside = 0 <= node < node_count and reticle == 0 and tile == 0
            else:
                # A wafer places by (node, reticle, tile).  The reticle and tile
                # axes are *per device*, so the bound is one wafer's grid
                # whatever the machine's node count is; the node axis is every
                # wafer the topology declares.  A one-wafer machine declares one
                # node and its ``local_node_id`` is zero, so this is the rule
                # that was here, restated for a machine that has a second
                # wafer: the V4.1 pipeline puts the encoder on node 0 and the
                # decoder on node 1, and ``node == local_node_id`` would have
                # refused every region of the second stage.
                node_count = max(int(topology.get("node_count", 0)), 1)
                inside = (
                    0 <= node < node_count
                    and 0 <= reticle < reticle_count
                    and 0 <= tile < reticle_count * tiles_per_reticle
                    and (
                        topology_class == int(TopologyClass.SINGLE_CHIP)
                        or tile // tiles_per_reticle == reticle
                    )
                )
            require(
                "rom_shard_topology",
                inside,
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
    # AM-C4 / [T2.1-20]: scratchpad ports per bank -- ``memory.sram.ports``
    # when the capability publishes it, two otherwise (the same reading the
    # emission rule takes, so the checker and the compiler cannot disagree).
    ports = _e9_sram_ports(capability)
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
        # AM-E9: a tile is at most 64 columns wide ([T2.1-3]).  A column-lane
        # engine (tensor, vector, attention, reduction) that advertises fewer
        # lanes bounds the tile at its lane count; the ``lanes`` the DMA,
        # selection, state and link engines publish are movers and units and
        # the route engine's are key lanes ([T2.1-12], design section 3.8),
        # not a column bound.
        if family in COLUMN_LANE_FAMILIES:
            lanes = max(int(engine_spec.get("lanes", 0)) or E9_TILE_COLS, 1)
        else:
            lanes = E9_TILE_COLS
        require(
            "tile_geometry",
            rows > 0 and cols > 0 and depth > 0 and cols <= lanes,
            f"schedule {schedule_id} tile {rows}x{cols}x{depth} is not positive "
            f"or exceeds {lanes} {_ENGINE_KEY.get(family, 'engine')} lanes",
        )

        input_views = _operator_views(operator, "input_view_", 4, views, require)
        output_views = _operator_views(operator, "output_view_", 2, views, require)
        rom_shards = _bank_mask(input_views, objects, plan_objects)
        expected_port = _port_mask((*input_views, *output_views), objects, ports)
        allocated_ports = _allocated_port_mask(ports)
        expected_route = _route_class(input_views, objects, plan_objects)
        expected_bound = _resource_bound(family, input_views, objects)
        # AM-E9 v2: bank_mask is the shared activation placement -- the
        # scratchpad banks of the staging regions this engine family streams
        # through -- and no longer the operator's mask-ROM shard set.  The
        # cycle model applies the field to the SRAM class alone
        # (``runtime/cycle/model.py`` ``MemorySystem.schedule``), so a ROM-bank
        # set here was spent as a scratchpad-bank set and a weight-free
        # operator's zero was read as UNRESTRICTED.  The shard reconstruction
        # is still checked, against the plan objects, below.
        expected_bank = _e9_staging_bank_mask(family, capability)
        require(
            "staging_bank_mask",
            int(payload["bank_mask"]) == expected_bank,
            f"schedule {schedule_id} bank mask {payload['bank_mask']:#x}; the "
            f"shared activation placement for this family is {expected_bank:#x}",
        )
        actual_port = int(payload["port_mask"])
        # AM-C4: port_mask bit p is scratchpad port p, and AM-E9 grants every
        # operator every port.  An operator with a mutable (non-ROM) operand
        # must therefore name all of them; a bit above the port count names a
        # port the capability does not have.
        require(
            "memory_port_coverage",
            actual_port & expected_port == expected_port,
            f"schedule {schedule_id} port mask {actual_port:#x} omits scratchpad "
            f"ports {expected_port:#x} its mutable operands are served on",
        )
        require(
            "memory_ports_allocated",
            actual_port & ~allocated_ports == 0,
            f"schedule {schedule_id} names a scratchpad port the capability "
            f"does not publish: mask {actual_port:#x}, ports {allocated_ports:#x}",
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
        sram_bank_count = _e9_sram_banks(capability)
        require(
            "bank_mask_capacity",
            int(payload["bank_mask"]) & ~((1 << min(sram_bank_count, 32)) - 1) == 0,
            f"schedule {schedule_id} names a scratchpad bank outside the "
            f"capability's {sram_bank_count}",
        )
        # The ROM-shard reconstruction the SCHEDULE field used to carry, moved
        # to the store it is true of: the operator's ROM operands must occupy
        # mask-ROM banks the capability publishes.  ``memory.rom.banks`` bounds
        # the plan, not the scratchpad descriptor.
        require(
            "rom_shard_banks",
            rom_shards & ~((1 << min(rom_banks, 32)) - 1) == 0,
            f"schedule {schedule_id} reads ROM shards in banks "
            f"{rom_shards:#x}, outside the capability's {rom_banks}",
        )
        require(
            "port_mask_capacity",
            int(payload["port_mask"]) & ~((1 << min(ports, 32)) - 1) == 0,
            f"schedule {schedule_id} names a scratchpad port outside the "
            f"capability's {ports}",
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
            _graph_tile_count_bound(
                source_kernel, graph_tensors, family, int(instruction.sub),
                capability, rows, cols, depth,
            ),
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
    # -- data-bearing expert reductions (multi-node ROM) --------------------
    # For every ROUTED_MATMUL on a multi-node topology, the chain
    #   pack (DMA.TRANSFER, source K) -> LINK.COLLECTIVE SUM over all the
    #   nodes -> unpack (DMA.TRANSFER, source K)
    # must exist exactly once per body position, each link waiting on the one
    # before, the pack reading the tensor the unpack writes, and the pack
    # writing a REMOTE participant array.  Its consumers then have to wait on
    # the unpack: a wait on the contraction's own event would read the
    # owner-partial rows before the other 31 owners' contributions arrived.
    # Which routed contractions *need* one.  A multi-node machine is not by
    # itself a reason: the reduction exists because an expert bank is split by
    # owner (A28 ``node_segments``), so each node computes only its own
    # experts' rows.  A layer-pipelined machine -- the V4.1 two-wafer target,
    # whose wafers hold whole layers with all their experts -- shards no bank,
    # has no owner-partial rows, and must not be required to sum any.  The
    # distinction is read off the emitted object's own source kind, which is the
    # thing that decides whether a node's image is the whole bank or a slice of
    # it.
    node_sharded_objects = {
        object_id
        for object_id, source in getattr(deployment, "objects", {}).items()
        if getattr(source, "kind", "") == "node_segments"
    }
    node_sharded_routed: set[int] = set()
    if node_sharded_objects:
        for kernel in graph.kernels:
            if kernel.kind != "ROUTED_MATMUL":
                continue
            for _index, _instruction, operator in by_source.get(kernel.index, []):
                for view in _operator_views(
                    operator, "input_view_", 4, views, require
                ):
                    if int(view.primary_object_id) in node_sharded_objects:
                        node_sharded_routed.add(kernel.index)
    reductions = _data_bearing_reductions(
        graph=graph,
        instructions=instructions,
        operators=operators,
        communications=communications,
        views=views,
        objects=objects,
        waits=waits,
        topology=topology,
        representative_ids=representative_ids,
        node_sharded_routed=frozenset(node_sharded_routed),
        require=require,
    )
    reduction_moves: set[int] = set()
    for source_kernel, (unpack_events, explained) in reductions.items():
        signals_by_source[source_kernel] = set(unpack_events)
        reduction_moves.update(explained)
    # -- phase-selected joins (TA-ABI3-OPCONV-1 phase layouts) --------------
    # A CONCAT that declares ``phase_inputs`` reads a different operand subset
    # in prefill and in decode.  Its lowering is one operator per phase behind
    # a PHASE_IS branch, each waiting on the producers of *its* subset only,
    # and the block converges on a CONTROL.FENCE (or, when an optional operand
    # splits the phase further, on a CONTROL.WAIT under the operator's own
    # guard) before control leaves it.  The conventions state the certificate:
    # control converges only after the selected producer is complete, so
    # program order carries the result into the consumer.  The checker derives
    # both halves from the graph and the program rather than trusting either:
    # every phase's producer set must be waited by one of the join's
    # instructions, every instruction must wait a whole phase, every operator
    # must be followed by its fence or guarded wait before another kernel
    # issues, and every consumer must sit after the converged block.
    phase_layouts: dict[int, dict[str, tuple[int, ...]]] = {}
    for kernel in graph.kernels:
        declared = kernel.attributes.get("phase_inputs")
        if isinstance(declared, Mapping) and declared:
            phase_layouts[kernel.index] = {
                str(phase): tuple(int(slot) for slot in row)
                for phase, row in declared.items()
                if isinstance(row, (list, tuple))
            }
    converged: dict[int, int] = {}
    for source, rows in by_source.items():
        if source not in phase_layouts:
            continue
        settled = True
        last_index = -1
        for index, instruction, _operator in rows:
            last_index = max(last_index, index)
            own_event = int(instruction.signal_event_id)
            guard = (
                int(instruction.predicate_id),
                bool(instruction.flags & int(InstructionFlag.PREDICATE_INVERT)),
            )
            certified = False
            for later in instructions[index + 1 :]:
                if later.major in scheduled_families:
                    later_operator = operators.get(later.descriptor_id)
                    if later_operator is None or int(
                        later_operator.payload["source_kernel_id"]
                    ) != source:
                        break
                    continue
                if later.major != int(Major.CONTROL):
                    break
                if later.sub in (int(Control.LOOP_NEXT), int(Control.BRANCH)):
                    # Control leaves the phase block here; a fence in the
                    # sibling block certifies the sibling, not this operator.
                    break
                if int(later.source_operation_id) != source:
                    continue
                later_guard = (
                    int(later.predicate_id),
                    bool(later.flags & int(InstructionFlag.PREDICATE_INVERT)),
                )
                if later.sub == int(Control.FENCE) and later.predicate_id == NO_ID:
                    certified = True
                    break
                if (
                    later.sub == int(Control.WAIT)
                    and own_event != NO_ID
                    and own_event in _wait_events(later, waits, require)
                    and (later.predicate_id == NO_ID or later_guard == guard)
                ):
                    certified = True
                    break
            settled = require(
                "phase_layout_convergence",
                certified,
                f"phase-layout kernel {source} instruction {index} is not "
                "followed by its fence or guarded wait before control leaves "
                "the phase block",
            ) and settled
        if settled and last_index >= 0:
            converged[source] = last_index
    phase_coverage: dict[int, set[str]] = {
        source: set() for source in by_source if source in phase_layouts
    }

    dependency_edges = 0
    for index, instruction, operator in instruction_operators:
        if index in reduction_moves:
            # The pack and the unpack wait on the contraction and on the
            # all-reduce respectively; ``_data_bearing_reductions`` proved that
            # chain.  Their producers are not the kernel's IR inputs.
            continue
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

        def expected_for(slots: set[int] | None) -> set[int]:
            found: set[int] = set()
            for dependency_slot, tensor_id in enumerate(dependencies):
                if slots is not None and dependency_slot not in slots:
                    continue
                if dependency_slot in conditional_inputs and instruction.flags & int(
                    InstructionFlag.PREDICATE_INVERT
                ):
                    # This is the explicitly declared operand-absent path.  It
                    # must not wait for a producer predicated off under the
                    # same condition; the sibling present path is checked
                    # separately.
                    continue
                original = producer.get(tensor_id)
                if original is None:
                    continue
                expected = canonical.get(original, original)
                # The producer is in a later iteration of a compressed run.  It
                # has no instruction or event of its own; LOOP_NEXT completes
                # the final iteration before control leaves the run, which is
                # the dependency certificate for the following band or
                # epilogue.
                if original != expected:
                    continue
                if expected == source:
                    continue
                # A canonical producer later in the same compressed body is a
                # loop-carried value.  Program order, not a first-iteration
                # event, carries that dependency.
                if order_position.get(expected, -1) >= order_position.get(
                    source, 1 << 30
                ):
                    continue
                if graph.kernels[expected].kind == _DIRECT_STATE_KIND:
                    continue
                found.add(expected)
            return found

        def waited(expected: int) -> bool:
            if expected in converged:
                return converged[expected] < index
            return bool(signals_by_source.get(expected, set()) & actual_wait)

        if source in phase_layouts:
            # The instruction must acquire one whole phase's producers.  Which
            # phase is not written on the instruction; it is whichever subset
            # the waits cover, and the coverage rule below insists that every
            # phase is taken by some instruction of the join.
            matched = [
                phase
                for phase, slots in phase_layouts[source].items()
                if all(waited(expected) for expected in expected_for(set(slots)))
            ]
            require(
                "phase_layout_wait",
                bool(matched),
                f"phase-layout kernel {source} instruction {index} waits "
                f"{sorted(actual_wait)}, which acquires no declared phase's "
                "producers",
            )
            phase_coverage.setdefault(source, set()).update(matched)
            expected_sources = (
                expected_for(set(phase_layouts[source][matched[0]]))
                if matched
                else expected_for(None)
            )
        else:
            expected_sources = expected_for(None)
        expected_sources.update(kv_dependencies.get(source, ()))
        for expected in expected_sources:
            dependency_edges += 1
            if expected in converged:
                require(
                    "phase_layout_program_order",
                    converged[expected] < index,
                    f"kernel {source} instruction {index} reads phase-layout "
                    f"kernel {expected} before its block converges at "
                    f"instruction {converged[expected]}",
                )
                continue
            events = signals_by_source.get(expected, set())
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
    for source, phases in phase_coverage.items():
        declared = set(phase_layouts[source])
        require(
            "phase_layout_coverage",
            phases == declared,
            f"phase-layout kernel {source} acquires phases {sorted(phases)}; "
            f"the graph declares {sorted(declared)}",
        )

    # -- no wait may require two mutually exclusive producers ---------------
    # An unconditional forward CONTROL.BRANCH that jumps past a later
    # instruction proves the two sides are mutually exclusive: whichever side
    # control enters, the other never runs and never signals.  A wait set that
    # names an event from each side therefore blocks forever on the side not
    # taken.  This is a property of the program alone, and it is checked over
    # every wait set rather than only the ones a phase layout produces, because
    # an instruction's predicate is only part of its reachability condition and
    # any construct that branches can make two same-guard producers exclusive.
    skips = [
        (index, int(instruction.control_id))
        for index, instruction in enumerate(instructions)
        if instruction.major == int(Major.CONTROL)
        and instruction.sub == int(Control.BRANCH)
        and instruction.predicate_id == NO_ID
        and int(instruction.control_id) > index
    ]
    require("branch_exclusive_wait", True, "")
    for index, instruction in enumerate(instructions):
        if instruction.wait_set_id == NO_ID:
            continue
        producers = sorted(
            {
                signal_index[event]
                for event in _wait_events(instruction, waits, require)
                if event in signal_index
            }
        )
        if len(producers) < 2:
            continue
        for branch, target in skips:
            before = [position for position in producers if position < branch]
            after = [position for position in producers if branch < position < target]
            if before and after:
                require(
                    "branch_exclusive_wait",
                    False,
                    f"instruction {index} waits on events signalled at "
                    f"{before[-1]} and {after[0]}, which the unconditional "
                    f"branch at {branch} to {target} makes mutually exclusive",
                )
                break

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
        if kernel.kind in {
            "INDEX_TOPK",
            "WINDOW_INDEX",
            "DSPARK_WINDOW_INDEX",
            "ATTENTION_SPARSE",
        }:
            candidates = _first_int(
                kernel.attributes,
                "k",
                "top_k",
                "window_size",
                default=_domain_int(kernel, "candidates", 1),
            )
            if kernel.kind == "DSPARK_WINDOW_INDEX":
                # Amendment A30.  This operator's bounded extent is the width
                # of the row it writes, and that row is the window followed by
                # the draft block: bounding it by ``window_size`` alone
                # under-bounds the operator's own output by the block, which is
                # precisely the segment the window operator cannot address.
                candidates += _first_int(
                    kernel.attributes, "draft_block_size", default=0
                )
            require(
                "sparse_index_bound",
                1 <= candidates <= int(capability.limits["max_context_positions"]),
                f"kernel {kernel.index} sparse/index extent {candidates} exceeds "
                "the context-position capability",
            )

    # -- two-wafer pipeline placement, reconstructed from the descriptors --
    # A V4.1-class ROM machine is two wafer-scale logical devices carrying one
    # program (plan sections 6.1 and 6.2).  Every rule below reads the node a
    # MEMORY_OBJECT declares -- the field the device and the frozen verifier
    # act on -- and never the producer's own placement notes, so agreement is
    # evidence.  On a one-node product every band maps to node 0 and the rules
    # are satisfied without saying anything, which is correct: there is no
    # second wafer for a reader to be stranded on.
    def _rom_object_nodes(operator: Any) -> set[int]:
        """Nodes of the immutable ROM operands one operator addresses."""
        nodes: set[int] = set()
        for prefix, count in (("input_view_", 4), ("output_view_", 2)):
            for view in _operator_views(operator, prefix, count, views, require):
                obj = objects.get(int(view.primary_object_id))
                if obj is None:
                    continue
                if int(obj.payload["storage_class"]) != int(StorageClass.ROM):
                    continue
                node = int(obj.payload["node_id"])
                if node != NO_NODE:
                    nodes.add(node)
        return nodes

    node_of_kernel: dict[int, int] = {}
    for source, emitted in by_source.items():
        nodes: set[int] = set()
        for _index, _instruction, operator in emitted:
            nodes |= _rom_object_nodes(operator)
        if len(nodes) == 1:
            node_of_kernel[source] = next(iter(nodes))
        elif len(nodes) > 1:
            require(
                "one_node_per_kernel",
                False,
                f"kernel {source} reads immutable ROM on nodes {sorted(nodes)}; "
                "one operator cannot address two devices' mask ROM",
            )
    require("one_node_per_kernel", True, "")

    def _own_node(kernel_index: int) -> int | None:
        """The node of ``kernel_index``'s own mask ROM, via its representative."""
        representative = canonical.get(kernel_index, kernel_index)
        node = node_of_kernel.get(representative)
        return node if node is not None else node_of_kernel.get(kernel_index)

    band_node: dict[int, int | None] = {}
    node_of_layer: dict[int, int] = {}
    for position, band in enumerate(bands):
        nodes = {
            node
            for kernel in band.body
            if (node := _own_node(kernel.index)) is not None
        }
        require(
            "one_node_per_band",
            len(nodes) <= 1,
            f"layer band beginning {band.first_layer} reads mask ROM on nodes "
            f"{sorted(nodes)}; a pipeline stage is a span of layers on one wafer",
        )
        band_node[position] = next(iter(nodes)) if len(nodes) == 1 else None
        if band_node[position] is not None:
            for layer in band.layers:
                node_of_layer[int(layer)] = band_node[position]
    require("one_node_per_band", True, "")

    def _node_of(kernel_index: int) -> int | None:
        """The device that executes ``kernel_index``.

        A kernel with a weight operand says where it runs itself.  One without
        -- a sparse attention reading only activations and a cache, which is
        exactly the reader a shared-cache rule is about -- runs where its
        *layer* runs, and the layer's device is the one its band's mask ROM
        declares.  Without that step the rule would be blind to the only kernels
        it exists to constrain.
        """
        own = _own_node(kernel_index)
        if own is not None:
            return own
        kernel = graph.kernels[kernel_index]
        if kernel.layer is None:
            return None
        return node_of_layer.get(int(kernel.layer))

    # ``shared_state_locality`` (plan section 6.3).  A global KV cache written
    # by one layer and read by later ones is a placement constraint the wafer
    # backend never had before: the reader cannot reach a cache that lives in
    # another device's memory.  The rule is stated over the graph's own state
    # effects and the emitted node of every kernel that touches them, so a
    # partition that stranded a reader fails here rather than at run time.
    state_writer_nodes: dict[str, set[int]] = {}
    state_reader_nodes: dict[str, set[int]] = {}
    for kernel in graph.kernels:
        if kernel.kind in _TRANSACTION_KINDS:
            continue
        node = _node_of(kernel.index)
        if node is None:
            continue
        for state_id in kernel.state_writes:
            state_writer_nodes.setdefault(state_id, set()).add(node)
        for state_id in kernel.state_reads:
            state_reader_nodes.setdefault(state_id, set()).add(node)
    for state_id in sorted(set(state_writer_nodes) | set(state_reader_nodes)):
        writers = state_writer_nodes.get(state_id, set())
        readers = state_reader_nodes.get(state_id, set())
        require(
            "shared_state_locality",
            len(writers | readers) <= 1,
            f"state resource {state_id!r} is written on node(s) {sorted(writers)} "
            f"and read on node(s) {sorted(readers)}; every reader of a shared "
            "cache must sit on the device that owns it",
        )
    require("shared_state_locality", True, "")

    # ``resident_hbm_region`` (plan section 6.3).  A table a layer reads every
    # token and nothing ever writes -- the Engram row table and its compressed
    # id map -- is a load-once region.  The rule is what "load once" means on
    # the wire: the objects behind it are immutable, no STATE descriptor holds
    # them, and no DMA.SCATTER writes into them.  A layered embedding lookup is
    # the structural signature; the prologue's token embedding has no layer and
    # is an ordinary model weight.
    resident_tensors = {
        name
        for kernel in graph.kernels
        if kernel.kind == "EMBEDDING_LOOKUP" and kernel.layer is not None
        for name in kernel.inputs
        if name in graph_tensors and graph_tensors[name].role in _WEIGHT_ROLES
    }
    resident_objects: set[int] = set()
    for kernel in graph.kernels:
        if kernel.kind != "EMBEDDING_LOOKUP" or kernel.layer is None:
            continue
        for _index, _instruction, operator in by_source.get(
            canonical.get(kernel.index, kernel.index), []
        ):
            for view in _operator_views(operator, "input_view_", 4, views, require):
                obj = objects.get(int(view.primary_object_id))
                if obj is None:
                    continue
                if int(obj.permissions) == int(Permission.READ | Permission.IMMUTABLE):
                    resident_objects.add(obj.descriptor_id)
    if resident_tensors:
        require(
            "resident_hbm_region",
            bool(resident_objects),
            f"{len(resident_tensors)} layered lookup table(s) are declared and no "
            "immutable object backs them",
        )
        state_bound = {
            int(descriptor.payload[field])
            for descriptor in states.values()
            for field in ("committed_object_id", "prepared_object_id")
        }
        require(
            "resident_hbm_region",
            not (resident_objects & state_bound),
            "a load-once resident table is bound to a STATE descriptor, so it is "
            "committed rather than resident",
        )
        for index, instruction, operator in instruction_operators:
            if (instruction.major, instruction.sub) != (
                int(Major.DMA),
                int(Dma.SCATTER),
            ):
                continue
            written = {
                int(view.primary_object_id)
                for view in _operator_views(
                    operator, "output_view_", 2, views, require
                )
            }
            require(
                "resident_hbm_region",
                not (written & resident_objects),
                f"DMA.SCATTER at instruction {index} writes into the load-once "
                "resident table region",
            )
    require("resident_hbm_region", True, "")

    # ``candidate_pool_bound`` (plan section 6.3).  CSA2's block selection
    # publishes a candidate pool, and every index top-k after it scans that
    # pool and not the whole context.  The bound is read off the capability --
    # ``max_candidate_positions`` -- because a literal here would be the model
    # constant mirrored into a checker that this plan forbids; a capability that
    # declares no pool is a machine with no candidate stage and the rule is
    # vacuous.
    candidate_bound = int(capability.limits.get("max_candidate_positions", 0))
    candidate_sources = [
        kernel for kernel in graph.kernels if kernel.kind == "CANDIDATE_MASK"
    ]
    if candidate_sources:
        require(
            "candidate_pool_bound",
            candidate_bound > 0,
            "the graph publishes a candidate pool and the capability declares no "
            "max_candidate_positions to bound it",
        )
        mask_tensors: dict[str, int] = {}
        for kernel in candidate_sources:
            for name in kernel.outputs:
                tensor = graph_tensors.get(name)
                if tensor is None:
                    continue
                population = 1
                for dim in tensor.shape:
                    population *= 1 if isinstance(dim, Symbolic) else max(int(dim), 1)
                mask_tensors[name] = population
                require(
                    "candidate_pool_bound",
                    population <= candidate_bound,
                    f"candidate mask {name!r} declares a population of "
                    f"{population}, over the capability's {candidate_bound}",
                )
        mask_states = {
            state_id
            for kernel in candidate_sources
            for state_id in kernel.state_writes
        }
        first_source = min(kernel.index for kernel in candidate_sources)
        mask_views = set(mask_tensors)
        for kernel in graph.kernels:
            if kernel.kind == "STATE_READ" and (
                set(kernel.state_reads) & mask_states
            ):
                mask_views.update(kernel.outputs)
        for kernel in graph.kernels:
            if kernel.kind != "INDEX_TOPK" or kernel.index <= first_source:
                continue
            carried = [name for name in kernel.inputs if name in mask_views]
            require(
                "candidate_pool_bound",
                bool(carried),
                f"INDEX_TOPK kernel {kernel.index} runs after the candidate "
                f"source and carries no candidate mask (reads {list(kernel.inputs)})",
            )
    require("candidate_pool_bound", True, "")

    # ``expert_capacity`` (plan section 6.3).  V4.1 routes among 384 experts and
    # selects six; V4's record admits 256 and eight.  Every routed operator
    # states the population it selects among and the width it selects, and both
    # are checked against the capability the deployment is admitted on.
    expert_limit = int(capability.limits["max_expert_ids"])
    topk_limit = int(capability.limits["max_topk"])
    for kernel in graph.kernels:
        declared = _first_int(
            kernel.attributes, "expert_count", default=_domain_int(kernel, "expert_count", 0)
        )
        if declared:
            require(
                "expert_capacity",
                declared <= expert_limit,
                f"kernel {kernel.index} ({kernel.kind}) routes among {declared} "
                f"experts; the capability admits {expert_limit}",
            )
        # The selection width is the trailing extent of the routing operator's
        # *index* output: a biased top-k and an expert dispatch both publish one
        # integer expert id per selected expert per token, so that extent is the
        # top-k and nothing else in the graph has to say so.
        if kernel.kind not in {"BIASED_TOPK", "EXPERT_DISPATCH"}:
            continue
        for name in kernel.outputs:
            tensor = graph_tensors.get(name)
            if tensor is None or tensor.dtype not in {"u32", "i32"}:
                continue
            dims = [dim for dim in tensor.shape if not isinstance(dim, Symbolic)]
            if not dims:
                continue
            width = int(dims[-1])
            if width <= 0:
                continue
            require(
                "expert_capacity",
                width <= topk_limit,
                f"kernel {kernel.index} ({kernel.kind}) selects {width} experts "
                f"per token in {name!r}; the capability admits max_topk "
                f"{topk_limit}",
            )
    require("expert_capacity", True, "")

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
        band_position = {id(band): index for index, band in enumerate(bands)}
        previous_node: int | None = None
        for band, descriptor in matched_band_loops:
            start = int(descriptor.payload["body_start"])
            end = int(descriptor.payload["body_end"])
            actual_subs = [
                instruction.sub
                for instruction in instructions[start:end]
                if instruction.major == int(Major.LINK)
            ]
            expected_subs: list[int] = []
            # A band that opens a new device is a pipeline stage boundary, and
            # the residual it consumes has to cross the package: exactly one
            # endpoint-initiated remote transfer, ahead of the band's own
            # on-wafer traffic.  The boundary is derived from the node the
            # band's mask ROM declares, so a program that claimed a two-wafer
            # partition and moved nothing between the wafers fails here.
            this_node = band_node.get(band_position.get(id(band), -1))
            crosses = (
                this_node is not None
                and previous_node is not None
                and this_node != previous_node
            )
            if crosses:
                expected_subs.append(int(Link.REMOTE_DMA))
            if this_node is not None:
                previous_node = this_node
            expected_subs.extend([int(Link.MULTICAST), int(Link.GATHER)])
            if any(kernel.kind == "EXPERT_DISPATCH" for kernel in band.body):
                expected_subs.append(int(Link.SCATTER))
            collectives = 1
            if topology_class in _NODE_PLACED_TOPOLOGY_CLASSES:
                # A multi-node ROM sums owner partials once per routed group:
                # every EXPERT_REDUCE fed by a routed contraction is one
                # data-bearing collective, and a band with none keeps the
                # wafer's single traffic-modelling collective.
                fed = 0
                pending = False
                for kernel in band.body:
                    if kernel.kind == "ROUTED_MATMUL":
                        pending = True
                    elif kernel.kind == "EXPERT_REDUCE":
                        fed += 1 if pending else 0
                        pending = False
                collectives = max(fed, 1)
            expected_subs.extend([int(Link.COLLECTIVE)] * collectives)
            expected_subs.extend([int(Link.SEND), int(Link.BARRIER)])
            require(
                "wafer_band_path",
                actual_subs == expected_subs,
                f"layer band beginning {band.first_layer} fabric path is "
                f"{actual_subs}; graph anchors derive {expected_subs}",
            )

    # -- state transaction order ------------------------------------------
    if direct_state_ids and not transactional_state_ids:
        require(
            "direct_state_has_no_state_descriptors",
            not states,
            "a graph containing only direct HBM state emitted STATE descriptors",
        )
        require(
            "direct_state_has_no_state_instructions",
            not any(
                instruction.major == int(Major.STATE)
                for instruction in instructions
            ),
            "a graph containing only direct HBM state emitted STATE instructions",
        )
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


def _view_dims(view: Any | None) -> tuple[int, ...]:
    if view is None:
        return ()
    payload = view.payload
    return tuple(
        int(payload[f"dim{axis}"]) for axis in range(int(payload["rank"]))
    )


def _view_strides(view: Any | None) -> tuple[int, ...]:
    if view is None:
        return ()
    payload = view.payload
    return tuple(
        int(payload[f"stride{axis}"]) for axis in range(int(payload["rank"]))
    )


def _view_terms(view: Any | None) -> tuple[tuple[int, int, int], ...]:
    if view is None:
        return ()
    payload = view.payload
    return tuple(
        (
            int(payload[f"term{slot}_kind"]),
            int(payload[f"term{slot}_index"]),
            int(payload[f"term{slot}_stride"]),
        )
        for slot in range(int(payload["dynamic_term_count"]))
    )


def _operator_view(
    operator: Any, views: Mapping[int, Any], field: str
) -> Any | None:
    descriptor_id = int(operator.payload[field])
    if descriptor_id == NO_ID:
        return None
    return views.get(descriptor_id)


def _generated_view_source(deployment: Deployment, view: Any) -> Any | None:
    if view is None:
        return None
    source = deployment.objects.get(int(view.primary_object_id))
    if source is None or source.kind != "generated":
        return None
    return source


def _phase_predicate(
    predicates: Mapping[int, Any], descriptor_id: int, phase: Phase
) -> bool:
    predicate = predicates.get(int(descriptor_id))
    if predicate is None:
        return False
    payload = predicate.payload
    return (
        int(payload["predicate_kind"]) == int(PredicateKind.PHASE_IS)
        and int(payload["comparison"]) == int(Comparison.EQ)
        and int(payload["selector_kind"]) == int(SelectorKind.RUNTIME_SYMBOL)
        and int(payload["selector_index"]) == int(Symbol.PHASE)
        and int(payload["immediate"]) == int(phase)
    )


def _prefill_group_predicate(
    predicates: Mapping[int, Any], descriptor_id: int, ratio: int
) -> bool:
    predicate = predicates.get(int(descriptor_id))
    if predicate is None:
        return False
    payload = predicate.payload
    return (
        int(payload["predicate_kind"]) == int(PredicateKind.COMPARE_SYMBOL)
        and int(payload["comparison"]) == int(Comparison.GE)
        and int(payload["selector_kind"]) == int(SelectorKind.RUNTIME_SYMBOL)
        and int(payload["selector_index"]) == int(Symbol.SPAN_TOKENS)
        and int(payload["immediate"]) == int(ratio)
    )


def _check_rolling_compressor(
    *,
    graph: KernelGraph,
    deployment: Deployment,
    expected_order: Sequence[Kernel],
    instructions: Sequence[Instruction],
    by_source: Mapping[int, Sequence[tuple[int, Instruction, Any]]],
    objects: Mapping[int, Any],
    views: Mapping[int, Any],
    numerics: Mapping[int, Any],
    predicates: Mapping[int, Any],
    waits: Mapping[int, Any],
    states: Mapping[int, Any],
    require: Callable[[str, bool, str], bool],
) -> dict[str, int]:
    """Independently prove the released ABI-3.0 rolling transition.

    The neutral state-update kernel is deliberately expanded, but only into
    frozen DMA, REDUCTION and VECTOR rows.  This proof reconstructs the two raw
    HBM rings, APE addition, boundary flag, no-copy gather, dual downstream
    paths, compressed RoPE position, and final history fence from descriptors;
    producer-side helper names and metadata are never imported.
    """

    updates = [kernel for kernel in expected_order if kernel.kind == "COMPRESS_STATE_UPDATE"]
    if not updates:
        return {}

    tensor_by_id = {tensor.tensor_id: tensor for tensor in graph.tensors}
    state_by_id = {state.state_id: state for state in graph.states}
    rolling_predicates: dict[str, int] = {}
    update_rows: dict[int, dict[str, Any]] = {}
    boundary_by_ratio: dict[int, int] = {}
    raw_history_events: set[int] = set()

    signal_instruction = {
        int(instruction.signal_event_id): (index, instruction)
        for index, instruction in enumerate(instructions)
        if int(instruction.signal_event_id) != NO_ID
    }

    def emitted(
        kernel: Kernel, family: Major, sub: int
    ) -> list[tuple[int, Instruction, Any]]:
        return [
            item
            for item in by_source.get(kernel.index, ())
            if (int(item[1].major), int(item[1].sub)) == (int(family), int(sub))
        ]

    def storage(view: Any | None) -> int:
        if view is None:
            return -1
        descriptor = objects.get(int(view.primary_object_id))
        return -1 if descriptor is None else int(descriptor.payload["storage_class"])

    def generated(
        view: Any | None, name: str, parameter: str, value: int
    ) -> bool:
        source = _generated_view_source(deployment, view)
        return (
            source is not None
            and source.generator == name
            and int(dict(source.parameters).get(parameter, -1)) == int(value)
        )

    def generated_as(view: Any | None, name: str) -> bool:
        source = _generated_view_source(deployment, view)
        return source is not None and source.generator == name

    def runtime_term(view: Any | None, symbol: Symbol) -> bool:
        return view is not None and (
            int(SelectorKind.RUNTIME_SYMBOL), int(symbol), 1
        ) in _view_terms(view)

    note = dict(deployment.notes.get("rom_predicates", {})).get(
        "rolling_compressor"
    )
    expected_ratios = sorted(
        {int(kernel.attributes.get("ratio", 0) or 0) for kernel in updates}
    )
    require(
        "rolling_abi3_metadata",
        note
        == {
            "abi": "3.0",
            "boundary": "ring_indices_v1(POSITION_END) == 0",
            "history": "ordinary_hbm_circular_absolute_position",
            "ratios": expected_ratios,
            "roll_copy": False,
        },
        "rolling compressor metadata is not the frozen direct-HBM ABI 3.0 profile",
    )
    require(
        "rolling_no_state_descriptors",
        not states
        and not any(instruction.major == int(Major.STATE) for instruction in instructions),
        "rolling compressor emitted ABI STATE records instead of ordinary HBM",
    )

    for kernel in updates:
        ratio = int(kernel.attributes.get("ratio", 0) or 0)
        predicate_name = str(kernel.attributes.get("predicate_output", ""))
        conditions = kernel.attributes.get("predicate_condition", {})
        conditions = dict(conditions) if isinstance(conditions, Mapping) else {}
        require(
            "rolling_ratio",
            ratio in {4, 128},
            f"compressor kernel {kernel.index} uses unpinned ratio {ratio}",
        )
        require(
            "rolling_predicate_contract",
            bool(predicate_name)
            and conditions.get("decode") == f"context_length % {ratio} == 0"
            and conditions.get("prefill") == f"span_groups_ratio{ratio} > 0",
            f"compressor kernel {kernel.index} does not declare the exact two-phase boundary",
        )
        previous = rolling_predicates.setdefault(predicate_name, ratio)
        require(
            "rolling_predicate_ratio_unique",
            previous == ratio,
            f"rolling predicate {predicate_name!r} names conflicting ratios",
        )

        packed = tensor_by_id[kernel.inputs[0]]
        packed_dims = tuple(_extent(value) for value in packed.shape)
        width = packed_dims[-1] if len(packed_dims) == 3 else 0
        slots = ratio * (2 if ratio == 4 else 1)
        head_dim = width // (2 if ratio == 4 else 1) if width else 0
        named_states = [state_by_id.get(name) for name in kernel.state_reads]
        require(
            "rolling_state_pair",
            len(named_states) == 2
            and None not in named_states
            and set(kernel.state_reads) == set(kernel.state_writes),
            f"compressor kernel {kernel.index} does not read/write one raw state pair",
        )
        require(
            "rolling_state_geometry",
            bool(width)
            and packed_dims[1:2] == (2,)
            and all(
                state is not None
                and state.state_class == "compressor_window"
                and state.dtype == "fp32"
                and _extent(state.capacity_rows) == slots
                and int(state.row_elements) == width
                for state in named_states
            )
            and {state.initialization for state in named_states if state is not None}
            == {"zero", "negative_infinity"},
            f"compressor kernel {kernel.index} raw state is not FP32 {slots}x{width}",
        )

        fills = emitted(kernel, Major.DMA, int(Dma.FILL))
        reset_rows: dict[int, tuple[int, Instruction, Any, Any]] = {}
        for item in fills:
            output = _operator_view(item[2], views, "output_view_0")
            if output is None or _view_dims(output) != (slots, width):
                continue
            code = int(item[2].payload["aux_id_0"])
            reset_rows[code] = (*item, output)
        require(
            "rolling_history_resets",
            set(reset_rows) == {0, 0xFF800000}
            and len(reset_rows) == 2
            and all(
                int(row[1].predicate_id) != NO_ID
                and _phase_predicate(predicates, row[1].predicate_id, Phase.PREFILL)
                and not row[1].flags & int(InstructionFlag.PREDICATE_INVERT)
                and int(row[3].payload["dtype"]) == int(DType.FP32)
                and _view_strides(row[3]) == (width, 1)
                and storage(row[3]) == int(StorageClass.HBM)
                for row in reset_rows.values()
            ),
            f"compressor kernel {kernel.index} lacks exact zero/-infinity HBM resets",
        )
        if set(reset_rows) != {0, 0xFF800000}:
            continue
        kv_reset = reset_rows[0]
        score_reset = reset_rows[0xFF800000]
        kv_history = kv_reset[3]
        score_history = score_reset[3]
        history_objects = {
            int(kv_history.primary_object_id),
            int(score_history.primary_object_id),
        }
        require(
            "rolling_history_objects_distinct",
            len(history_objects) == 2
            and all(
                int(view.permissions) & int(Permission.READ | Permission.WRITE)
                == int(Permission.READ | Permission.WRITE)
                for view in (kv_history, score_history)
            ),
            f"compressor kernel {kernel.index} does not bind two writable HBM histories",
        )

        gathers = emitted(kernel, Major.DMA, int(Dma.GATHER))
        ape_rows = [
            item
            for item in gathers
            if item[1].predicate_id == NO_ID
            and storage(_operator_view(item[2], views, "input_view_1"))
            == int(StorageClass.ROM)
        ]
        require(
            "rolling_ape_gather_count",
            len(ape_rows) == 1,
            f"compressor kernel {kernel.index} has {len(ape_rows)} APE gathers",
        )
        sums = emitted(kernel, Major.REDUCTION, int(Reduction.ORDERED_SUM))
        scatters = emitted(kernel, Major.DMA, int(Dma.SCATTER))
        pools = emitted(kernel, Major.VECTOR, int(Vector.COMPRESS))
        require(
            "rolling_primitive_counts",
            len(sums) == 1 and len(scatters) == 2 and len(pools) == 1,
            f"compressor kernel {kernel.index} does not emit one sum, two scatters and one pool",
        )
        if len(ape_rows) != 1 or len(sums) != 1 or len(scatters) != 2 or len(pools) != 1:
            continue

        ape_at, ape_instruction, ape_operator = ape_rows[0]
        ape_index = _operator_view(ape_operator, views, "input_view_0")
        ape_source = _operator_view(ape_operator, views, "input_view_1")
        ape_output = _operator_view(ape_operator, views, "output_view_0")
        require(
            "rolling_ape_geometry",
            generated(ape_index, "ring_indices_v1", "modulus", ratio)
            and runtime_term(ape_index, Symbol.POSITION_START)
            and _view_dims(ape_source) == (ratio, width)
            and _view_strides(ape_source) == (width, 1)
            and int(ape_source.payload["dtype"]) == int(DType.FP32)
            and _view_dims(ape_output)[-1:] == (width,)
            and _view_strides(ape_output)[-1:] == (1,)
            and int(ape_output.payload["dtype"]) == int(DType.FP32),
            f"compressor kernel {kernel.index} APE gather is not the ratio-{ratio} ring",
        )

        sum_at, sum_instruction, sum_operator = sums[0]
        score_terms = _operator_view(sum_operator, views, "input_view_0")
        score_scratch = _operator_view(sum_operator, views, "input_view_1")
        sum_output = _operator_view(sum_operator, views, "output_view_0")
        numeric = numerics.get(int(sum_operator.payload["numeric_profile_id"]))
        numeric_payload = numeric.payload if numeric is not None else {}
        require(
            "rolling_score_add_fp32_rne",
            score_scratch is not None
            and sum_output is not None
            and score_scratch.descriptor_id == sum_output.descriptor_id
            and score_terms is not None
            and int(score_terms.payload["dtype"]) == int(DType.FP32)
            and int(score_scratch.payload["dtype"]) == int(DType.FP32)
            and numeric is not None
            and all(
                int(numeric_payload.get(field, -1)) == int(DType.FP32)
                for field in (
                    "input_dtype",
                    "second_input_dtype",
                    "accumulator_dtype",
                    "output_dtype",
                )
            )
            and int(numeric_payload.get("rounding_mode", -1))
            == int(RoundingMode.NEAREST_EVEN)
            and ape_instruction.signal_event_id
            in _wait_events(sum_instruction, waits, require),
            f"compressor kernel {kernel.index} score plus APE is not binary32 RNE",
        )

        scatter_by_object = {
            int(_operator_view(item[2], views, "output_view_0").primary_object_id): item
            for item in scatters
            if _operator_view(item[2], views, "output_view_0") is not None
        }
        require(
            "rolling_history_scatter_targets",
            set(scatter_by_object) == history_objects
            and all(item[1].predicate_id == NO_ID for item in scatters),
            f"compressor kernel {kernel.index} does not append both histories unconditionally",
        )
        if set(scatter_by_object) != history_objects:
            continue
        kv_scatter = scatter_by_object[int(kv_history.primary_object_id)]
        score_scatter = scatter_by_object[int(score_history.primary_object_id)]
        kv_index = _operator_view(kv_scatter[2], views, "input_view_0")
        score_index = _operator_view(score_scatter[2], views, "input_view_0")
        kv_values = _operator_view(kv_scatter[2], views, "input_view_1")
        score_values = _operator_view(score_scatter[2], views, "input_view_1")
        require(
            "rolling_history_ring_append",
            kv_index is not None
            and score_index is not None
            and kv_index.descriptor_id == score_index.descriptor_id
            and generated(kv_index, "ring_indices_v1", "modulus", slots)
            and runtime_term(kv_index, Symbol.POSITION_START)
            and _view_strides(kv_index) == (1,)
            and kv_values is not None
            and _view_dims(kv_values)[-1:] == (width,)
            and _view_strides(kv_values)[-2:] == (2 * width, 1)
            and score_values is not None
            and score_scratch is not None
            and score_values.descriptor_id == score_scratch.descriptor_id,
            f"compressor kernel {kernel.index} history append is not the {slots}-row absolute ring",
        )
        require(
            "rolling_packed_split",
            kv_values is not None
            and score_terms is not None
            and int(kv_values.primary_object_id) == int(score_terms.primary_object_id)
            and len(_view_dims(score_terms)) == 3
            and _view_dims(score_terms)[0] == 1
            and _view_dims(score_terms)[-1] == width
            and _view_strides(score_terms)[-2:] == (2 * width, 1)
            and int(score_terms.payload["element_offset"])
            == int(kv_values.payload["element_offset"]) + width,
            f"compressor kernel {kernel.index} does not split packed [S,2,W] exactly",
        )
        score_waits = _wait_events(score_scatter[1], waits, require)
        require(
            "rolling_history_write_order",
            int(kv_scatter[1].signal_event_id) in score_waits
            and int(sum_instruction.signal_event_id) in score_waits,
            f"compressor kernel {kernel.index} score history does not follow KV and APE writes",
        )
        raw_history_events.update(
            {
                int(kv_scatter[1].signal_event_id),
                int(score_scatter[1].signal_event_id),
            }
        )

        common_reset_waits = set(_wait_events(kv_scatter[1], waits, require)) & set(
            _wait_events(score_scatter[1], waits, require)
        )
        reset_join = next(
            (
                event
                for event in common_reset_waits
                if event in signal_instruction
                and signal_instruction[event][1].major == int(Major.CONTROL)
                and signal_instruction[event][1].sub == int(Control.NOP)
                and signal_instruction[event][1].predicate_id == NO_ID
            ),
            None,
        )
        reset_events = {
            int(kv_reset[1].signal_event_id),
            int(score_reset[1].signal_event_id),
        }
        guarded_reset_waits: set[int] = set()
        if reset_join is not None:
            join_at = signal_instruction[reset_join][0]
            for candidate in instructions[:join_at]:
                if (
                    candidate.major == int(Major.CONTROL)
                    and candidate.sub == int(Control.WAIT)
                    and _phase_predicate(
                        predicates, candidate.predicate_id, Phase.PREFILL
                    )
                ):
                    guarded_reset_waits.update(
                        _wait_events(candidate, waits, require) & reset_events
                    )
        require(
            "rolling_reset_convergence",
            reset_join is not None and guarded_reset_waits == reset_events,
            f"compressor kernel {kernel.index} does not converge guarded resets before append",
        )

        pool_at, pool_instruction, pool_operator = pools[0]
        require(
            "rolling_prefill_pool",
            _prefill_group_predicate(predicates, pool_instruction.predicate_id, ratio)
            and not pool_instruction.flags & int(InstructionFlag.PREDICATE_INVERT)
            and int(pool_operator.payload["aux_id_0"]) == 2
            and int(pool_operator.payload["aux_id_1"]) == ratio
            and int(pool_operator.payload["aux_id_2"]) == int(Symbol.POSITION_START)
            and int(score_scatter[1].signal_event_id)
            in _wait_events(pool_instruction, waits, require),
            f"compressor kernel {kernel.index} prefill pool is not exact VECTOR.COMPRESS subcase 2",
        )

        boundary_rows = [
            item
            for item in gathers
            if item[1].predicate_id != NO_ID
            and item[1].flags & int(InstructionFlag.PREDICATE_INVERT)
            and storage(_operator_view(item[2], views, "input_view_1"))
            == int(StorageClass.HBM)
        ]
        expected_boundary_rows = 4 if ratio == 4 else 2
        boundary_ids = {int(item[1].predicate_id) for item in boundary_rows}
        require(
            "rolling_boundary_gather_count",
            len(boundary_rows) == expected_boundary_rows and len(boundary_ids) == 1,
            f"compressor kernel {kernel.index} has {len(boundary_rows)} ratio-{ratio} boundary gathers",
        )
        if len(boundary_rows) != expected_boundary_rows or len(boundary_ids) != 1:
            continue
        boundary_id = next(iter(boundary_ids))
        previous_boundary = boundary_by_ratio.setdefault(ratio, boundary_id)
        require(
            "rolling_boundary_predicate_shared",
            previous_boundary == boundary_id,
            f"ratio-{ratio} compressor kernels do not share one boundary predicate",
        )
        boundary_predicate = predicates.get(boundary_id)
        require(
            "rolling_boundary_boolean",
            boundary_predicate is not None
            and int(boundary_predicate.payload["predicate_kind"])
            == int(PredicateKind.BOOLEAN_OBJECT)
            and int(boundary_predicate.payload["comparison"]) == int(Comparison.EQ),
            f"ratio-{ratio} boundary is not an inverted BOOLEAN_OBJECT zero test",
        )

        pool_output_objects = {
            int(view.primary_object_id)
            for field in ("output_view_0", "output_view_1")
            if (view := _operator_view(pool_operator, views, field)) is not None
        }
        boundary_output_objects = {
            int(view.primary_object_id)
            for item in boundary_rows
            if (view := _operator_view(item[2], views, "output_view_0")) is not None
        }
        require(
            "rolling_boundary_pool_alias",
            boundary_output_objects <= pool_output_objects,
            f"compressor kernel {kernel.index} decode gather does not feed the prefill pool buffers",
        )

        by_history: dict[int, list[tuple[int, Instruction, Any]]] = {}
        for item in boundary_rows:
            source_view = _operator_view(item[2], views, "input_view_1")
            if source_view is not None:
                by_history.setdefault(int(source_view.primary_object_id), []).append(item)
        require(
            "rolling_boundary_history_pair",
            set(by_history) == history_objects,
            f"compressor kernel {kernel.index} boundary gather misses a history plane",
        )
        for object_id, rows in by_history.items():
            base_view = (
                kv_history
                if object_id == int(kv_history.primary_object_id)
                else score_history
            )
            base = int(base_view.payload["element_offset"])
            rows.sort(key=lambda item: int(_operator_view(item[2], views, "input_view_0").payload["element_offset"]))
            if ratio == 4:
                geometry_ok = len(rows) == 2
                if len(rows) == 2:
                    left_index = _operator_view(rows[0][2], views, "input_view_0")
                    right_index = _operator_view(rows[1][2], views, "input_view_0")
                    left_source = _operator_view(rows[0][2], views, "input_view_1")
                    right_source = _operator_view(rows[1][2], views, "input_view_1")
                    left_output = _operator_view(rows[0][2], views, "output_view_0")
                    right_output = _operator_view(rows[1][2], views, "output_view_0")
                    geometry_ok = geometry_ok and (
                        generated(left_index, "ring_indices_v1", "modulus", slots)
                        and generated(right_index, "ring_indices_v1", "modulus", slots)
                        and runtime_term(left_index, Symbol.POSITION_END)
                        and runtime_term(right_index, Symbol.POSITION_END)
                        and _view_dims(left_index) == (ratio,)
                        and _view_dims(right_index) == (ratio,)
                        and int(left_index.payload["element_offset"]) == 0
                        and int(right_index.payload["element_offset"]) == ratio
                        and _view_dims(left_source) == (slots, head_dim)
                        and _view_dims(right_source) == (slots, head_dim)
                        and _view_strides(left_source) == (width, 1)
                        and _view_strides(right_source) == (width, 1)
                        and int(left_source.payload["element_offset"]) == base
                        and int(right_source.payload["element_offset"]) == base + head_dim
                        and _view_dims(left_output) == (ratio, head_dim)
                        and _view_dims(right_output) == (ratio, head_dim)
                        and _view_strides(left_output) == (head_dim, 1)
                        and _view_strides(right_output) == (head_dim, 1)
                        and int(right_output.payload["element_offset"])
                        - int(left_output.payload["element_offset"])
                        == ratio * head_dim
                    )
            else:
                geometry_ok = len(rows) == 1
                if len(rows) == 1:
                    index_view = _operator_view(rows[0][2], views, "input_view_0")
                    source_view = _operator_view(rows[0][2], views, "input_view_1")
                    output_view = _operator_view(rows[0][2], views, "output_view_0")
                    geometry_ok = geometry_ok and (
                        generated(index_view, "ring_indices_v1", "modulus", slots)
                        and runtime_term(index_view, Symbol.POSITION_END)
                        and _view_dims(index_view) == (slots,)
                        and int(index_view.payload["element_offset"]) == 0
                        and _view_dims(source_view) == (slots, width)
                        and _view_strides(source_view) == (width, 1)
                        and int(source_view.payload["element_offset"]) == base
                        and _view_dims(output_view) == (slots, width)
                        and _view_strides(output_view) == (width, 1)
                    )
            require(
                "rolling_boundary_geometry",
                geometry_ok,
                f"compressor kernel {kernel.index} has incorrect ratio-{ratio} history ordering",
            )

        ordered_boundary = sorted(boundary_rows, key=lambda item: item[0])
        boundary_chain_ok = bool(ordered_boundary)
        predecessor = int(score_scatter[1].signal_event_id)
        for item in ordered_boundary:
            boundary_chain_ok = boundary_chain_ok and predecessor in _wait_events(
                item[1], waits, require
            )
            predecessor = int(item[1].signal_event_id)
        require(
            "rolling_boundary_write_order",
            boundary_chain_ok,
            f"compressor kernel {kernel.index} boundary gather races its history append",
        )

        transfers = emitted(kernel, Major.DMA, int(Dma.TRANSFER))
        require(
            "rolling_no_history_roll_copy",
            all(
                (view := _operator_view(item[2], views, "output_view_0")) is not None
                and _view_dims(view) == (1,)
                and int(view.payload["dtype"]) == int(DType.U32)
                for item in transfers
            ),
            f"compressor kernel {kernel.index} emits a physical history roll copy",
        )
        update_rows[kernel.index] = {
            "ratio": ratio,
            "boundary": boundary_id,
            "history_objects": history_objects,
        }

    # One ordinary four-byte HBM flag and one pair of phase-selected writers
    # serve every representative compressor of a ratio.
    all_update_ops = [item for kernel in updates for item in by_source.get(kernel.index, ())]
    boundary_objects: set[int] = set()
    for ratio, predicate_id in sorted(boundary_by_ratio.items()):
        predicate = predicates.get(predicate_id)
        object_id = (
            int(predicate.payload["object_id"])
            if predicate is not None
            else NO_ID
        )
        boundary_objects.add(object_id)
        descriptor = objects.get(object_id)
        transfers = []
        fills = []
        for item in all_update_ops:
            output = _operator_view(item[2], views, "output_view_0")
            if output is None or int(output.primary_object_id) != object_id:
                continue
            if (item[1].major, item[1].sub) == (int(Major.DMA), int(Dma.TRANSFER)):
                transfers.append(item)
            if (item[1].major, item[1].sub) == (int(Major.DMA), int(Dma.FILL)):
                fills.append(item)
        require(
            "rolling_boundary_flag_object",
            descriptor is not None
            and int(descriptor.payload["storage_class"]) == int(StorageClass.HBM)
            and int(descriptor.payload["size_bytes"]) == 4
            and len(transfers) == 1
            and len(fills) == 1,
            f"ratio-{ratio} does not have one shared four-byte HBM boundary flag",
        )
        if len(transfers) != 1 or len(fills) != 1:
            continue
        transfer = transfers[0]
        fill = fills[0]
        ring_word = _operator_view(transfer[2], views, "input_view_0")
        flag_view = _operator_view(transfer[2], views, "output_view_0")
        require(
            "rolling_boundary_flag_writers",
            generated(ring_word, "ring_indices_v1", "modulus", ratio)
            and runtime_term(ring_word, Symbol.POSITION_END)
            and _view_dims(ring_word) == (1,)
            and flag_view is not None
            and int(flag_view.permissions)
            & int(Permission.READ | Permission.WRITE)
            == int(Permission.READ | Permission.WRITE)
            and int(fill[2].payload["aux_id_0"]) == 1
            and _phase_predicate(predicates, transfer[1].predicate_id, Phase.DECODE)
            and _phase_predicate(predicates, fill[1].predicate_id, Phase.PREFILL),
            f"ratio-{ratio} boundary flag is not POSITION_END modulo ratio with prefill suppression",
        )
        first_use = min(
            (
                index
                for index, instruction in enumerate(instructions)
                if int(instruction.predicate_id) == predicate_id
            ),
            default=len(instructions),
        )
        guarded = set()
        for writer in (transfer, fill):
            for index, instruction in enumerate(instructions):
                if not writer[0] < index < first_use:
                    continue
                if (
                    instruction.major == int(Major.CONTROL)
                    and instruction.sub == int(Control.WAIT)
                    and instruction.predicate_id == writer[1].predicate_id
                    and writer[1].signal_event_id
                    in _wait_events(instruction, waits, require)
                ):
                    guarded.add(int(writer[1].signal_event_id))
        uses = [
            instruction
            for instruction in instructions
            if int(instruction.predicate_id) == predicate_id
        ]
        require(
            "rolling_boundary_flag_acquire",
            guarded
            == {
                int(transfer[1].signal_event_id),
                int(fill[1].signal_event_id),
            }
            and uses
            and all(
                instruction.flags & int(InstructionFlag.PREDICATE_INVERT)
                for instruction in uses
            ),
            f"ratio-{ratio} boundary object is read before its guarded write completes",
        )
    require(
        "rolling_boundary_objects_distinct",
        len(boundary_objects) == len(boundary_by_ratio),
        "different compression ratios alias one boundary flag",
    )

    # Every should-compress consumer has a many-row prefill path and a static
    # one-row decode path.  The decode path is gated by the same inverted
    # BOOLEAN_OBJECT as its state transition.
    for kernel in expected_order:
        predicate_name = str(kernel.attributes.get("execution_predicate", ""))
        if predicate_name not in rolling_predicates:
            continue
        ratio = rolling_predicates[predicate_name]
        pair = _expected_engine(kernel)
        issued = [
            item
            for item in by_source.get(kernel.index, ())
            if (item[1].major, item[1].sub) == pair
        ]
        boundary_id = boundary_by_ratio.get(ratio, NO_ID)
        prefill = [
            item
            for item in issued
            if _prefill_group_predicate(predicates, item[1].predicate_id, ratio)
            and not item[1].flags & int(InstructionFlag.PREDICATE_INVERT)
        ]
        decode = [
            item
            for item in issued
            if int(item[1].predicate_id) == boundary_id
            and item[1].flags & int(InstructionFlag.PREDICATE_INVERT)
        ]
        require(
            "rolling_dual_path",
            len(issued) == 2 and len(prefill) == 1 and len(decode) == 1,
            f"rolling consumer {kernel.index} does not have exact prefill/decode paths",
        )
        if len(prefill) != 1 or len(decode) != 1:
            continue
        decode_item = decode[0]
        static_ok = True
        for field in (
            "input_view_0",
            "input_view_1",
            "input_view_2",
            "input_view_3",
            "output_view_0",
            "output_view_1",
        ):
            view = _operator_view(decode_item[2], views, field)
            if view is None or storage(view) == int(StorageClass.ROM):
                continue
            if kernel.kind == "KV_APPEND" and field.startswith("output_"):
                continue
            dims = _view_dims(view)
            static_ok = static_ok and bool(dims) and dims[0] == 1
            static_ok = static_ok and not _view_terms(view)
            if kernel.kind == "COMPRESS_POOL":
                static_ok = static_ok and len(dims) > 1 and dims[1] == 1
        require(
            "rolling_decode_static_extent",
            static_ok,
            f"rolling consumer {kernel.index} decode path is not a static one-group view",
        )

        if kernel.kind == "GATHER" and bool(kernel.attributes.get("compressed", False)):
            prefill_index = _operator_view(prefill[0][2], views, "input_view_0")
            decode_index = _operator_view(decode_item[2], views, "input_view_0")
            coefficient = _operator_view(decode_item[2], views, "input_view_1")
            tensor = tensor_by_id[kernel.inputs[1]]
            tensor_dims = tuple(_extent(value) for value in tensor.shape)
            coefficient_width = tensor_dims[-1]
            require(
                "rolling_rope_group_start",
                generated(decode_index, "floor_div_indices_v1", "divisor", ratio)
                and runtime_term(decode_index, Symbol.POSITION_START)
                and _view_dims(decode_index) == (1,)
                and _view_strides(decode_index) == (ratio,)
                and generated_as(prefill_index, "arange_u32_v1")
                and runtime_term(prefill_index, Symbol.POSITION_START)
                and _view_strides(prefill_index) == (ratio,)
                and coefficient is not None
                and _view_dims(coefficient)
                == ((tensor_dims[0] + ratio - 1) // ratio, coefficient_width)
                and _view_strides(coefficient) == (ratio * coefficient_width, 1),
                f"compressed RoPE kernel {kernel.index} does not select p+1-ratio at decode boundary",
            )

        if kernel.kind == "KV_APPEND":
            tail = max(prefill[0][0], decode_item[0])
            convergence = list(instructions[tail + 1 : tail + 4])
            expected_events = {
                int(prefill[0][1].signal_event_id),
                int(decode_item[1].signal_event_id),
            }
            waited_events: set[int] = set()
            guarded_ok = len(convergence) == 3
            for instruction in convergence[:2]:
                guarded_ok = guarded_ok and (
                    instruction.major == int(Major.CONTROL)
                    and instruction.sub == int(Control.WAIT)
                )
                waited_events.update(_wait_events(instruction, waits, require))
            joined = convergence[2] if len(convergence) == 3 else None
            guarded_ok = guarded_ok and (
                waited_events == expected_events
                and joined is not None
                and joined.major == int(Major.CONTROL)
                and joined.sub == int(Control.NOP)
                and joined.predicate_id == NO_ID
                and joined.signal_event_id != NO_ID
            )
            require(
                "rolling_append_convergence",
                guarded_ok,
                f"compressed append {kernel.index} does not publish a non-boundary-safe ready event",
            )

    # The terminal FENCE must acquire both raw history writes.  Following the
    # unconditional event DAG proves this without relying on instruction order
    # or the producer's internal frontier algorithm.
    # A phase-layout join converges on a fence of its own (it carries the
    # join's source_operation_id); the terminal token fence is the one that
    # belongs to no kernel.
    fences = [
        instruction
        for instruction in instructions
        if instruction.major == int(Major.CONTROL)
        and instruction.sub == int(Control.FENCE)
        and int(instruction.source_operation_id) == NO_ID
    ]
    ancestors: set[int] = set()
    if len(fences) == 1:
        pending = list(_wait_events(fences[0], waits, require))
        while pending:
            event = int(pending.pop())
            if event in ancestors:
                continue
            ancestors.add(event)
            signaller = signal_instruction.get(event)
            if signaller is not None:
                pending.extend(_wait_events(signaller[1], waits, require))
    require(
        "rolling_history_terminal_fence",
        len(fences) == 1 and raw_history_events <= ancestors,
        "terminal token fence does not acquire every raw compressor history write",
    )

    return rolling_predicates


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
    direct_state_ids: frozenset[str],
) -> tuple[int, Any] | None:
    expected = [
        kernel.index
        for kernel in band.body
        if kernel.kind not in _TRANSACTION_KINDS
        and not (
            kernel.kind == _DIRECT_STATE_KIND
            and _uses_only_direct_state(kernel, direct_state_ids)
        )
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


def _uses_only_direct_state(
    kernel: Kernel, direct_state_ids: frozenset[str]
) -> bool:
    """Whether every state effect on ``kernel`` names a direct HBM resource."""

    named = (*kernel.state_reads, *kernel.state_writes)
    return bool(named) and all(state_id in direct_state_ids for state_id in named)


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
    """The mask-ROM shards this operator's ROM operands occupy.

    This was the expected value of the SCHEDULE ``bank_mask``.  Since AM-E9 v2
    that field is the shared activation placement over the scratchpad -- the
    store the cycle model actually charges it to -- and this reconstruction is
    checked against the ROM plan instead (``rom_shard_banks``), which is where
    AM-C4's own last clause already puts per-tile ROM placement.
    """

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


def _port_mask(views: Sequence[Any], objects: Mapping[int, Any], ports: int) -> int:
    """The scratchpad ports an operator's mutable operands are served on.

    AM-C4 (design section 3.8, 10.1): ``port_mask`` bit p is scratchpad port
    p -- the reading ``runtime.cycle.model.MemorySystem._allowed`` takes, bits
    over ``ports_per_unit`` -- and AM-E9 grants every operator every port, so
    an operator with any non-ROM operand must name all ``ports`` of them.  The
    previous reading (bit b = the SRAM *bank* of each activation object) was a
    bank set in a port field, and the shipped ROM program carried it while the
    HBM program carried ports; the two could never agree.
    """
    for view in views:
        obj = objects.get(int(view.primary_object_id))
        if obj is None or int(obj.payload["storage_class"]) == int(StorageClass.ROM):
            continue
        return (1 << min(max(int(ports), 1), 32)) - 1
    return 0


def _allocated_port_mask(ports: int) -> int:
    """Every scratchpad port the capability publishes (AM-C4)."""

    return (1 << min(max(int(ports), 1), 32)) - 1


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
    family: int,
    sub: int,
    capability: Capability,
    tile_rows: int,
    tile_cols: int,
    tile_depth: int,
) -> int:
    """Conservative work tiles from the neutral iteration domain.

    An ABI operator may expose only one feature group or one phase-specific
    view even though its schedule prices the complete neutral operation.  The
    source graph is therefore the authority for the upper work envelope; using
    only that narrowed view would incorrectly call legitimate queue depth idle.

    The envelope is the graph's own extents read the way AM-E9 reads them
    (``compiler.backends.schedule_rule.operator_shape``): the output width, the
    contracted extent -- a weight's K, or the context positions an attention
    operator walks (AM-E2 v2: 128 per block) -- and the rows the iteration
    domain names, which bound every dispatch the compiler can state.
    """

    outputs = [tensors[name] for name in kernel.outputs if name in tensors]
    rows = _domain_int(kernel, "tokens", 0)
    if rows <= 0:
        rows = _domain_int(kernel, "rows", 0)
    if rows <= 0 and outputs:
        rows = _extent(outputs[0].shape[0])
    rows = max(rows, 1)
    shape = _e9_operator_shape(
        kernel, tensors, family, sub, rows=rows, capability=capability
    )
    return (
        ceil(shape.rows / tile_rows)
        * ceil(shape.cols / tile_cols)
        * ceil(shape.reduction / tile_depth)
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


def _data_bearing_reductions(
    *,
    graph: KernelGraph,
    instructions: Sequence[Any],
    operators: Mapping[int, Any],
    communications: Mapping[int, Any],
    views: Mapping[int, Any],
    objects: Mapping[int, Any],
    waits: Mapping[int, Any],
    topology: Mapping[str, Any],
    representative_ids: Any,
    node_sharded_routed: Any,
    require: Callable[..., bool],
) -> dict[int, tuple[set[int], set[int]]]:
    """Reconstruct every data-bearing expert reduction and prove its chain.

    Returns ``{routed kernel index: ({unpack signal events}, {instruction
    indices the chain explains})}``.  On a one-node topology there are none and
    nothing is required, and the same is true of a multi-node topology that
    shards no expert bank by owner: ``node_sharded_routed`` is the set of routed
    contractions whose bank is split, and only those have partial rows to sum.
    """
    node_count = int(topology.get("node_count", 1))
    if node_count <= 1 or not node_sharded_routed:
        return {}
    # Only representative kernels have instructions; a compressed run's later
    # layers ride the representative's body and its reduction.
    routed = {
        kernel.index
        for kernel in graph.kernels
        if kernel.kind == "ROUTED_MATMUL" and kernel.index in representative_ids
    }
    if not routed:
        return {}
    signal_of: dict[int, int] = {}
    for index, instruction in enumerate(instructions):
        event = int(instruction.signal_event_id)
        if event != NO_ID:
            signal_of[index] = event
    found: dict[int, tuple[set[int], set[int]]] = {}
    # walk the program: every DMA.TRANSFER attributed to a routed kernel must
    # be the pack or the unpack of one chain
    pending: dict[int, tuple[int, int]] = {}  # kernel -> (pack index, pack event)
    for index, instruction in enumerate(instructions):
        if instruction.major == int(Major.DMA) and instruction.sub == int(Dma.TRANSFER):
            operator = operators.get(instruction.descriptor_id)
            if operator is None:
                continue
            source = int(operator.payload["source_kernel_id"])
            if source not in routed:
                continue
            if source not in pending:
                # the pack: it must wait on the contraction's own event and
                # write a REMOTE participant array
                own = {
                    signal_of[i]
                    for i, ins in enumerate(instructions)
                    if i < index
                    and ins.source_operation_id == source
                    and i in signal_of
                    and ins.major == int(Major.TENSOR)
                }
                actual = _wait_events(instruction, waits, require)
                require(
                    "reduction_pack_waits_for_contraction",
                    bool(own & actual),
                    f"reduction pack at {index} for kernel {source} does not wait "
                    f"for the contraction's events {sorted(own)}; waits {sorted(actual)}",
                )
                out_view = views.get(int(operator.payload["output_view_0"]))
                pack_target = (
                    int(out_view.primary_object_id) if out_view is not None else NO_ID
                )
                # The collective reduces a descriptor constant's worth of bytes
                # from every participant, while the pack writes only the rows
                # this step produced.  So the slot has to be cleared first, over
                # its declared maximum and with positive zero, or the tail of a
                # short step is summed as data.  The staging objects are shared
                # by byte size across the program, so that tail is another
                # step's bytes read under this step's dtype.
                clear_index = NO_ID
                for i in range(index - 1, -1, -1):
                    candidate = instructions[i]
                    if candidate.major != int(Major.DMA):
                        continue
                    if candidate.sub != int(Dma.FILL):
                        break
                    fill_op = operators.get(candidate.descriptor_id)
                    if fill_op is None or int(
                        fill_op.payload["source_kernel_id"]
                    ) != source:
                        break
                    fill_view = views.get(int(fill_op.payload["output_view_0"]))
                    fill_target = (
                        int(fill_view.primary_object_id)
                        if fill_view is not None
                        else NO_ID
                    )
                    require(
                        "reduction_clear_covers_the_slot",
                        fill_target == pack_target
                        and fill_view is not None
                        and int(fill_view.payload["edge_mask_id"]) == NO_ID
                        and int(fill_view.payload["extent_unit"]) == 0,
                        f"kernel {source}: the fill at {i} does not cover the "
                        "participant slot's declared maximum unconditionally",
                    )
                    require(
                        "reduction_clear_is_positive_zero",
                        int(fill_op.payload["aux_id_0"]) == 0,
                        f"kernel {source}: the fill at {i} writes code "
                        f"{fill_op.payload['aux_id_0']}, not positive zero",
                    )
                    clear_index = i
                    break
                require(
                    "reduction_clears_the_slot",
                    clear_index != NO_ID,
                    f"kernel {source}: the pack at {index} is not preceded by a "
                    "fill of its participant slot, so the collective would sum "
                    "whatever the previous step left in the tail",
                )
                if clear_index != NO_ID:
                    require(
                        "reduction_pack_waits_for_the_clear",
                        signal_of.get(clear_index, NO_ID)
                        in _wait_events(instruction, waits, require),
                        f"kernel {source}: the pack at {index} does not wait for "
                        f"the fill at {clear_index}",
                    )
                pending[source] = (
                    index,
                    signal_of.get(index, NO_ID),
                    pack_target,
                    clear_index,
                )
                continue
            pack_index, pack_event, pack_target, clear_index = pending.pop(source)
            # between the pack and this unpack: exactly one LINK.COLLECTIVE SUM
            # at route class 3 over all the nodes, waiting on the pack
            links = [
                (i, ins)
                for i, ins in enumerate(instructions)
                if pack_index < i < index and ins.major == int(Major.LINK)
            ]
            summing = []
            for i, ins in links:
                comm = communications.get(ins.descriptor_id)
                if comm is None:
                    continue
                payload = comm.payload
                if (
                    int(payload["collective_op"]) == int(CollectiveOp.SUM)
                    and int(payload["participant_scope"]) == int(ParticipantScope.NODE)
                    and int(payload["participant_count"]) == node_count
                ):
                    summing.append((i, ins))
            require(
                "reduction_collective_present",
                len(summing) == 1,
                f"kernel {source}: {len(summing)} node-scoped SUM collectives "
                f"over {node_count} nodes between pack {pack_index} and unpack "
                f"{index}; expected exactly one",
            )
            if len(summing) != 1:
                continue
            link_index, link = summing[0]
            endpoints = communications[link.descriptor_id].payload
            unpack_in = views.get(int(operator.payload["input_view_0"]))
            unpack_source = (
                int(unpack_in.primary_object_id) if unpack_in is not None else NO_ID
            )
            # The pack writes the collective's participant array and the
            # unpack reads its local buffer: the moves are bound to the very
            # endpoints the collective names, not to any staging object.
            require(
                "reduction_pack_targets_participant_array",
                pack_target != NO_ID
                and pack_target == int(endpoints["remote_object_id"]),
                f"kernel {source}: the pack writes object {pack_target}, the "
                f"all-reduce's participant array is {endpoints['remote_object_id']}",
            )
            require(
                "reduction_unpack_reads_reduced_buffer",
                unpack_source != NO_ID
                and unpack_source == int(endpoints["local_object_id"]),
                f"kernel {source}: the unpack reads object {unpack_source}, the "
                f"all-reduce's local buffer is {endpoints['local_object_id']}",
            )
            link_wait = _wait_events(link, waits, require)
            require(
                "reduction_collective_waits_for_pack",
                pack_event != NO_ID and pack_event in link_wait,
                f"kernel {source}: the all-reduce at {link_index} does not wait "
                f"for pack event {pack_event}; waits {sorted(link_wait)}",
            )
            link_event = signal_of.get(link_index, NO_ID)
            unpack_wait = _wait_events(instruction, waits, require)
            require(
                "reduction_unpack_waits_for_collective",
                link_event != NO_ID and link_event in unpack_wait,
                f"kernel {source}: the unpack at {index} does not wait for the "
                f"all-reduce event {link_event}; waits {sorted(unpack_wait)}",
            )
            pack_op = operators.get(instructions[pack_index].descriptor_id)
            pack_in = views.get(int(pack_op.payload["input_view_0"])) if pack_op else None
            unpack_out = views.get(int(operator.payload["output_view_0"]))
            same_buffer = (
                pack_in is not None
                and unpack_out is not None
                and int(pack_in.primary_object_id) == int(unpack_out.primary_object_id)
            )
            require(
                "reduction_round_trips_the_tensor",
                same_buffer,
                f"kernel {source}: the pack reads and the unpack writes different "
                "objects; the reduced rows must land where the partial rows were",
            )
            events, explained = found.setdefault(source, (set(), set()))
            events.add(signal_of.get(index, NO_ID))
            explained.update((pack_index, index))
            if clear_index != NO_ID:
                explained.add(clear_index)
    for source, (pack_index, _event, _target, _clear) in pending.items():
        require(
            "reduction_unpack_present",
            False,
            f"kernel {source}: pack at {pack_index} has no unpack",
        )
    # Which routed contractions must be reduced: the one whose output leaves
    # the expert chain.  A DeepSeek expert is gate, up and down contractions
    # with a per-expert SwiGLU between them; the gate and up outputs feed only
    # per-expert elementwise work and the down contraction on the same node,
    # so they stay owner-local, and it is the down output -- the last routed
    # contraction before EXPERT_REDUCE -- whose partial rows every node needs.
    required: set[int] = set()
    last_routed: int | None = None
    for kernel in graph.kernels:
        if kernel.index not in representative_ids:
            continue
        if kernel.kind == "ROUTED_MATMUL":
            last_routed = kernel.index if kernel.index in node_sharded_routed else None
        elif kernel.kind == "EXPERT_REDUCE" and last_routed is not None:
            required.add(last_routed)
            last_routed = None
    for source in sorted(required):
        require(
            "data_bearing_expert_reduction",
            source in found,
            f"ROUTED_MATMUL kernel {source} feeds EXPERT_REDUCE on a {node_count}-node "
            "topology and has no data-bearing expert reduction; its owner-partial "
            "rows would never be summed",
        )
    for source in sorted(set(found) - required):
        require(
            "reduction_only_where_rows_leave_the_expert_chain",
            False,
            f"ROUTED_MATMUL kernel {source} is reduced although its output stays "
            "inside the expert chain; a needless all-reduce is fabric traffic the "
            "wafer does not pay",
        )
    return found


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
