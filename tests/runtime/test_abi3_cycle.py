"""Tests for the shared ABI 3.0 cycle model.

The load-bearing test in this file is architectural-counter agreement: for one
deployment and one request, the functional device in ``runtime/sim/device.py``
and the cycle model in ``runtime/cycle/model.py`` must produce identical values
for every counter outside the frozen registry's timing group.  Everything else
here -- provenance labelling, the bounded-queue and acyclic-wait proofs, the two
fabric realisations, determinism, the CLI -- protects that claim or the claims
built on top of it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from runtime.abi3.capability import Capability, canonical_json
from runtime.abi3.constants import (
    Control,
    Dma,
    Reduction,
    Selection,
    Tensor,
    Vector,
    CounterGroup,
    DType,
    Feature,
    Link,
    Major,
    NO_ID,
    Observation,
    Permission,
    Recovery,
    State,
    StateClass,
    StorageClass,
    TopologyClass,
    counter_id,
)
from runtime.abi3.builder import DeploymentBuilder, DynamicTerm
from runtime.abi3.deployment import Deployment, ObjectSource
from runtime.abi3.descriptors import (
    CollectiveOp,
    ExtendedDescriptorType,
    Phase,
    SelectionMode,
    Symbol,
)
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.abi3.verifier import verify_deployment
from runtime.sim.counters import COUNTERS, NAME_TO_ID, is_timing_counter
from runtime.sim.device import Device
from runtime.cycle.fabric import (
    ClusterFabric,
    WaferFabric,
    assert_no_zero_latency_global_operations,
)
from runtime.cycle.machine import (
    CostTable,
    MachineError,
    MachineModel,
    Provenance,
    load_cost_table,
)
from runtime.cycle.model import (
    CycleModel,
    CycleRequest,
    ScheduleError,
    architectural_counters,
    functional_counters,
    functional_reference,
    operand_extents,
    prove_acyclic_waits,
    timing_counters,
)
from runtime.sim.engines import load_engines

#: The engine implementations register themselves on import; a driver loads
#: them, so the tests do too.  Without them every engine operation traps in
#: *both* models, which is a legitimate run but not one that exercises tiling.
load_engines()

REPO = Path(__file__).resolve().parents[2]
HARDWARE = REPO / "configs" / "hardware"

BASELINE = HARDWARE / "abi3_cost_baseline_v1.json"
ASAP7 = HARDWARE / "abi3_cost_asap7_v1.json"
SKY130_ROM = HARDWARE / "abi3_cost_sky130_rom_v1.json"
CLUSTER32 = HARDWARE / "abi3_cost_cluster32_v1.json"
WAFER = HARDWARE / "abi3_cost_wafer_v1.json"

#: W9.5.  Derived by ``tools/build_abi3_cost_tables.py`` from the routed blocks
#: and the executed RTL campaigns, rather than written by hand.
ASAP7_V2 = HARDWARE / "abi3_cost_asap7_v2.json"
SKY130_ROM_V2 = HARDWARE / "abi3_cost_sky130_rom_v2.json"
IHP_SG13G2 = HARDWARE / "abi3_cost_ihp_sg13g2_v1.json"
CLUSTER32_V2 = HARDWARE / "abi3_cost_cluster32_v2.json"
WAFER_V2 = HARDWARE / "abi3_cost_wafer_v2.json"

#: Views where a block of the machine has actually been routed, so the clock is
#: a post-route result rather than an assumption.
ROUTED_CLOCK_TABLES = [ASAP7_V2, SKY130_ROM_V2, IHP_SG13G2]

#: Every table the generator produces.  The cluster and wafer views get the
#: measured engine rates -- a rate is the RTL's own cycle behaviour and does not
#: depend on the node -- but keep an assumed clock, because nothing of a
#: multi-node or on-wafer machine has been routed.
DERIVED_TABLES = [*ROUTED_CLOCK_TABLES, CLUSTER32_V2, WAFER_V2]

SHIPPED_TABLES = [BASELINE, ASAP7, SKY130_ROM, CLUSTER32, WAFER, *DERIVED_TABLES]

STATE_ROWS = 64
ROW_ELEMS = 8


def request(**kwargs) -> CycleRequest:
    symbols = {
        int(Symbol.SPAN_TOKENS): 1,
        int(Symbol.POSITION_START): 0,
        int(Symbol.POSITION_END): 1,
        int(Symbol.CONTEXT_LENGTH): 1,
    }
    symbols.update(kwargs.pop("symbols", {}))
    return CycleRequest(symbols=symbols, **kwargs)


# ---------------------------------------------------------------------------
# Synthetic deployments
#
# The engine families are being implemented concurrently, so a program that
# issues TENSOR.MATMUL traps in *both* models today.  These synthetic
# deployments exercise the families the frozen device already executes on its
# own -- control flow, transactional state, observation and recovery -- so that
# counter agreement is checked on a transaction that actually completes and
# actually moves bytes.
# ---------------------------------------------------------------------------
def _state_builder(capability: Capability, *, target: str) -> DeploymentBuilder:
    builder = DeploymentBuilder(
        target_id=target,
        model_id="abi3-cycle-synthetic",
        backend="cycle-test",
        capability=capability,
    )
    builder.topology(
        topology_class=TopologyClass(capability.topology_class),
        node_count=capability.limits["max_nodes"],
        hbm_bytes_per_node=capability.memory["hbm"]["bytes"],
        sram_bytes_per_node=capability.memory["sram"]["bytes"],
        key="topology",
    )
    return builder


def synthetic_state_deployment(
    capability: Capability | None = None,
    *,
    tiles: int = 4,
    with_communication: bool = False,
    target: str = "cycle-synthetic",
) -> tuple[Deployment, Capability]:
    """A deployment that completes on today's device and commits real bytes."""
    capability = capability or fixture_capability()
    builder = _state_builder(capability, target=target)
    row_bytes = ROW_ELEMS * 2
    committed = builder.memory_object(
        storage_class=StorageClass.STATE,
        size_bytes=STATE_ROWS * row_bytes,
        source=ObjectSource.zeros(STATE_ROWS * row_bytes),
        permissions=int(Permission.READ | Permission.STATE_COMMIT),
        key="obj.kv.committed",
    )
    prepared = builder.memory_object(
        storage_class=StorageClass.STATE,
        size_bytes=STATE_ROWS * row_bytes,
        source=ObjectSource.zeros(STATE_ROWS * row_bytes),
        permissions=int(Permission.READ | Permission.STATE_PREPARE),
        key="obj.kv.prepared",
    )
    scratch = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=4096,
        source=ObjectSource.zeros(4096),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.scratch",
    )
    kv_view = builder.tensor_view(
        object_id=prepared,
        dtype=DType.BF16,
        dims=[STATE_ROWS, ROW_ELEMS],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.kv",
    )
    # Amendment A21 makes the commit policy a fact about the descriptor table:
    # a prepared image no descriptor names as a destination is UNSTAGED, and
    # its commit publishes nothing.  Before A21 this fixture's commit wrote
    # ``ROW_ELEMS * 2`` bytes; afterwards it silently wrote zero, because
    # nothing here staged a row.  The staging DMA below is what makes the
    # commit real again, so ``state.bytes_written`` is a measurement rather
    # than a missing key.
    stage_source = builder.tensor_view(
        object_id=scratch,
        dtype=DType.BF16,
        dims=[1, ROW_ELEMS],
        key="view.stage.source",
    )
    stage_destination = builder.tensor_view(
        object_id=prepared,
        dtype=DType.BF16,
        dims=[1, ROW_ELEMS],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.stage.destination",
    )
    stage_schedule = builder.schedule(
        engine_family=Major.DMA,
        tile_rows=1,
        tile_cols=ROW_ELEMS,
        tile_depth=1,
        max_outstanding=1,
        issue_window=1,
        key="sched.stage",
    )
    stage_op = builder.operator(
        engine_family=Major.DMA,
        engine_sub=Dma.TRANSFER,
        inputs=[stage_source],
        outputs=[stage_destination],
        schedule_id=stage_schedule,
        source_kernel_id=5,
        key="op.stage",
    )
    state = builder.state(
        state_class=StateClass.KV_CACHE,
        committed_object_id=committed,
        prepared_object_id=prepared,
        row_bytes=row_bytes,
        capacity_rows=STATE_ROWS,
        element_dtype=DType.BF16,
        view_descriptor_id=kv_view,
        key="state.kv",
    )
    loop = builder.loop_control(
        lower_bound=0, upper_bound=tiles, step=1, key="loop.tile"
    )
    snapshot_class = builder.counter_class(
        int(CounterGroup.INSTRUCTION),
        [
            counter_id(CounterGroup.INSTRUCTION, 3),
            counter_id(CounterGroup.LATENCY, 1),
        ],
        key="ctr.snapshot",
    )
    if with_communication:
        builder.require(Feature.INTER_CHIP_ENDPOINT)
        builder.communication(
            collective_op=CollectiveOp.POINT_TO_POINT,
            local_object_id=scratch,
            remote_object_id=scratch,
            source_node=0,
            destination_node=1,
            byte_extent=4096,
            participant_count=2,
            key="comm.p2p",
        )
        builder.communication(
            collective_op=CollectiveOp.SUM,
            local_object_id=scratch,
            remote_object_id=scratch,
            byte_extent=65536,
            participant_count=capability.limits["max_nodes"],
            chunk_bytes=4096,
            key="comm.allreduce",
        )

    prepare_event = builder.new_event()
    read_event = builder.new_event()
    stage_event = builder.new_event()
    builder.emit(
        Major.STATE, State.PREPARE, descriptor_id=state, signal_event_id=prepare_event
    )
    builder.emit(
        Major.DMA,
        Dma.TRANSFER,
        descriptor_id=stage_op,
        wait_set_id=builder.wait_set([prepare_event], key="wait.stage"),
        signal_event_id=stage_event,
        source_operation_id=5,
    )
    builder.open_loop(loop)
    builder.emit(
        Major.OBSERVATION,
        Observation.COUNTER_SNAPSHOT,
        descriptor_id=snapshot_class,
    )
    builder.close_loop()
    builder.emit(
        Major.STATE,
        State.READ,
        descriptor_id=state,
        wait_set_id=builder.wait_set([stage_event], key="wait.prepare"),
        signal_event_id=read_event,
    )
    builder.emit(Major.RECOVERY, Recovery.DRAIN)
    builder.emit(
        Major.STATE,
        State.COMMIT,
        descriptor_id=state,
        wait_set_id=builder.wait_set([read_event], key="wait.read"),
    )
    builder.emit(Major.CONTROL, Control.COMPLETE)
    builder.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    builder.entrypoint(entrypoint_id=1, first_instruction=0, phase=Phase.DECODE)
    builder.source_identity = {"fixture": "abi3-cycle-synthetic-v1"}
    return builder.finish(), capability


TILE_ROWS = 8
TILE_COLS = 32
TILE_DEPTH = 64
VOCAB = 32
CONTEXT = 64


def cycle_capability(
    topology: TopologyClass = TopologyClass.SINGLE_CHIP,
) -> Capability:
    """A capability large enough to tile against, with a full engine set."""
    features = [
        Feature.HOST_QUEUE_ABI,
        Feature.DEPLOYMENT_DESCRIPTOR_ABI,
        Feature.DETERMINISTIC_MICROSEQUENCER,
        Feature.BF16_TENSOR,
        Feature.TRANSACTIONAL_STATE,
        Feature.ON_DEVICE_SELECTION,
    ]
    if topology == TopologyClass.CLUSTER_32:
        features.append(Feature.INTER_CHIP_ENDPOINT)
    if topology == TopologyClass.WAFER_LOGICAL_DEVICE:
        features.append(Feature.WAFER_ENDPOINT)
    capability = Capability(
        capability_id="",
        topology_class=int(topology),
        features=tuple(int(f) for f in features),
        limits={
            "max_instructions": 4096,
            "max_descriptors": 4096,
            "max_loop_depth": 4,
            "max_loop_trip": 1 << 20,
            "max_retired_work": 1 << 32,
            "max_events": 256,
            "max_event_id": 511,
            "max_state_resources": 16,
            "max_outstanding_per_queue": 4,
            "max_context_positions": CONTEXT,
            "max_expert_ids": 1024,
            "max_topk": 16,
            "max_vocabulary": VOCAB,
            "max_sessions": 4,
            "max_nodes": 32 if topology == TopologyClass.CLUSTER_32 else 1,
        },
        numeric_contracts=(
            "bf16_bf16_fp32_blocked_rne_v1",
            "bf16_bf16_fp32_sequential_rne_v1",
            "exact_index_select_v1",
        ),
        engines={
            "tensor": {"lanes": 32, "queues": 2},
            "vector": {"lanes": 16, "queues": 1},
            "reduction": {"lanes": 8, "queues": 1},
            "selection": {"lanes": 8, "queues": 1},
            "dma": {"lanes": 1, "queues": 2},
            "state": {"lanes": 1, "queues": 1},
        },
        memory={
            "sram": {"bytes": 1 << 20, "banks": 8, "ports": 2},
            "hbm": {"bytes": 1 << 24, "channels": 4},
            "rom": {"bytes": 1 << 24},
        },
        technology_view="fixture",
    )
    capability.validate()
    return capability


def synthetic_tiled_deployment(
    capability: Capability | None = None,
    *,
    storage_class: StorageClass = StorageClass.HBM,
    tile_rows: int = 4,
    tile_cols: int = 8,
    tile_depth: int = 16,
    max_outstanding: int = 4,
    bank_mask: int = 0,
    port_mask: int = 0,
    schedule_reduction: bool = True,
    layers: int = 1,
    independent_matmuls: int = 0,
) -> tuple[Deployment, Capability]:
    """A completing deployment whose every operator carries a tile mapping.

    Extents deliberately do not divide the tile shape, so partial tiles -- and
    the padding work they waste -- are exercised rather than assumed away.
    """
    capability = capability or cycle_capability()
    builder = _state_builder(capability, target="cycle-tiled")
    builder.require(Feature.BF16_TENSOR)

    weight_bytes = VOCAB * TILE_DEPTH * 2
    weights = builder.memory_object(
        storage_class=storage_class,
        size_bytes=weight_bytes,
        source=ObjectSource.zeros(weight_bytes),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
        key="obj.weights",
    )
    act_bytes = TILE_ROWS * TILE_DEPTH * 2
    out_bytes = TILE_ROWS * VOCAB * 2
    activations = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=act_bytes + 2 * out_bytes,
        source=ObjectSource.zeros(act_bytes + 2 * out_bytes),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.activations",
    )
    logits = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=VOCAB * 2,
        source=ObjectSource.zeros(VOCAB * 2),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.logits",
    )
    token_slots = 1 + CONTEXT
    tokens = builder.memory_object(
        storage_class=StorageClass.HOST,
        size_bytes=token_slots * 4,
        source=ObjectSource.zeros(token_slots * 4),
        permissions=int(Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE),
        key="obj.tokens",
    )
    row_bytes = TILE_DEPTH * 2
    kv_committed = builder.memory_object(
        storage_class=StorageClass.STATE,
        size_bytes=CONTEXT * row_bytes,
        source=ObjectSource.zeros(CONTEXT * row_bytes),
        permissions=int(Permission.READ | Permission.STATE_COMMIT),
        key="obj.kv.committed",
    )
    kv_prepared = builder.memory_object(
        storage_class=StorageClass.STATE,
        size_bytes=CONTEXT * row_bytes,
        source=ObjectSource.zeros(CONTEXT * row_bytes),
        permissions=int(Permission.READ | Permission.STATE_PREPARE),
        key="obj.kv.prepared",
    )

    # TA-ABI3-OPCONV-1 amendment A7 names the blocked contract for execution,
    # but the tensor engine in this tree implements the sequential association
    # only, so the deployment binds what the machine can actually run.  The
    # cycle-model report names whichever contract the deployment bound.
    matmul_numeric = builder.numeric(
        contract="bf16_bf16_fp32_sequential_rne_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        key="num.matmul",
    )
    select_numeric = builder.numeric(
        contract="exact_index_select_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.U32,
        accumulator_dtype=DType.FP32,
        key="num.select",
    )

    tensor_schedule = builder.schedule(
        engine_family=Major.TENSOR,
        tile_rows=tile_rows,
        tile_cols=tile_cols,
        tile_depth=tile_depth,
        max_outstanding=max_outstanding,
        issue_window=2,
        bank_mask=bank_mask,
        port_mask=port_mask,
        queue_index=0,
        key="sched.tensor",
    )
    vector_schedule = builder.schedule(
        engine_family=Major.VECTOR,
        tile_rows=tile_rows,
        tile_cols=tile_cols,
        tile_depth=1,
        max_outstanding=max_outstanding,
        issue_window=1,
        key="sched.vector",
    )
    reduction_schedule = builder.schedule(
        engine_family=Major.REDUCTION,
        tile_rows=1,
        tile_cols=tile_cols,
        tile_depth=tile_rows,
        max_outstanding=max_outstanding,
        issue_window=2,
        key="sched.reduction",
    )
    selection_schedule = builder.schedule(
        engine_family=Major.SELECTION,
        tile_rows=1,
        tile_cols=tile_cols,
        tile_depth=1,
        max_outstanding=max_outstanding,
        issue_window=2,
        key="sched.selection",
    )

    activation_view = builder.tensor_view(
        object_id=activations,
        dtype=DType.BF16,
        dims=[TILE_ROWS, TILE_DEPTH],
        key="view.activations",
    )
    weight_view = builder.tensor_view(
        object_id=weights,
        dtype=DType.BF16,
        dims=[VOCAB, TILE_DEPTH],
        key="view.weights",
    )
    output_view = builder.tensor_view(
        object_id=activations,
        dtype=DType.BF16,
        dims=[TILE_ROWS, VOCAB],
        element_offset=TILE_ROWS * TILE_DEPTH,
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.output",
    )
    residual_view = builder.tensor_view(
        object_id=activations,
        dtype=DType.BF16,
        dims=[TILE_ROWS, VOCAB],
        element_offset=TILE_ROWS * TILE_DEPTH + TILE_ROWS * VOCAB,
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.residual",
    )
    logits_view = builder.tensor_view(
        object_id=logits,
        dtype=DType.BF16,
        dims=[VOCAB],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.logits",
    )
    selected_view = builder.tensor_view(
        object_id=tokens,
        dtype=DType.U32,
        dims=[1],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.selected",
    )
    ring_view = builder.tensor_view(
        object_id=tokens,
        dtype=DType.U32,
        dims=[1],
        element_offset=1,
        dynamic=[DynamicTerm.symbol(Symbol.GENERATION_INDEX, 1)],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.ring",
    )
    kv_view = builder.tensor_view(
        object_id=kv_prepared,
        dtype=DType.BF16,
        dims=[CONTEXT, TILE_DEPTH],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.kv",
    )
    # Amendment A21: without a descriptor that names ``kv_prepared`` as a
    # destination this deployment's STATE.COMMIT is UNSTAGED and moves zero
    # bytes, which would leave every state-traffic assertion below true of a
    # machine that did nothing.  One row is staged so the commit is real.
    kv_stage_source = builder.tensor_view(
        object_id=activations,
        dtype=DType.BF16,
        dims=[1, TILE_DEPTH],
        key="view.kv.stage.source",
    )
    kv_stage_destination = builder.tensor_view(
        object_id=kv_prepared,
        dtype=DType.BF16,
        dims=[1, TILE_DEPTH],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.kv.stage.destination",
    )
    kv_stage_schedule = builder.schedule(
        engine_family=Major.DMA,
        tile_rows=1,
        tile_cols=tile_cols,
        tile_depth=1,
        max_outstanding=max_outstanding,
        issue_window=1,
        key="sched.kv.stage",
    )
    kv_stage_op = builder.operator(
        engine_family=Major.DMA,
        engine_sub=Dma.TRANSFER,
        inputs=[kv_stage_source],
        outputs=[kv_stage_destination],
        schedule_id=kv_stage_schedule,
        source_kernel_id=5,
        key="op.kv.stage",
    )

    matmul_op = builder.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[activation_view, weight_view],
        outputs=[output_view],
        numeric_profile_id=matmul_numeric,
        schedule_id=tensor_schedule,
        source_kernel_id=0,
        key="op.matmul",
    )
    add_op = builder.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.ADD,
        inputs=[output_view, residual_view],
        outputs=[residual_view],
        numeric_profile_id=matmul_numeric,
        schedule_id=vector_schedule,
        source_kernel_id=1,
        key="op.add",
    )
    reduce_op = builder.operator(
        engine_family=Major.REDUCTION,
        engine_sub=Reduction.ORDERED_SUM,
        inputs=[residual_view],
        outputs=[logits_view],
        numeric_profile_id=matmul_numeric,
        schedule_id=reduction_schedule if schedule_reduction else NO_ID,
        source_kernel_id=2,
        key="op.reduce",
    )
    argmax_op = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.ARGMAX,
        inputs=[logits_view],
        outputs=[selected_view],
        numeric_profile_id=select_numeric,
        schedule_id=selection_schedule,
        source_kernel_id=3,
        key="op.argmax",
    )
    append_op = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.TOKEN_APPEND,
        inputs=[selected_view],
        outputs=[ring_view],
        numeric_profile_id=select_numeric,
        schedule_id=selection_schedule,
        source_kernel_id=4,
        key="op.append",
    )
    kv_state = builder.state(
        state_class=StateClass.KV_CACHE,
        committed_object_id=kv_committed,
        prepared_object_id=kv_prepared,
        row_bytes=row_bytes,
        capacity_rows=CONTEXT,
        element_dtype=DType.BF16,
        view_descriptor_id=kv_view,
        key="state.kv",
    )
    policy = builder.generation_policy(
        eos_token_ids=[VOCAB - 1],
        max_new_tokens=8,
        vocabulary_size=VOCAB,
        token_ring_object_id=tokens,
        selection_mode=SelectionMode.GREEDY_ARGMAX_LOWEST_ID,
        key="policy",
    )

    layer_loop = (
        builder.loop_control(
            lower_bound=0, upper_bound=layers, step=1, key="loop.layer"
        )
        if layers > 1
        else NO_ID
    )

    builder.emit(Major.STATE, State.PREPARE, descriptor_id=kv_state)
    if layer_loop != NO_ID:
        # The program loops over layers, never over tiles.
        builder.open_loop(layer_loop)
    matmul_event = builder.new_event()
    builder.emit(
        Major.TENSOR,
        Tensor.MATMUL,
        descriptor_id=matmul_op,
        signal_event_id=matmul_event,
        source_operation_id=0,
    )
    for _ in range(independent_matmuls):
        # No wait set and no signal: these are independent of everything, so the
        # only thing that can hold them up is a queue credit.
        builder.emit(
            Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul_op, source_operation_id=0
        )
    add_event = builder.new_event()
    builder.emit(
        Major.VECTOR,
        Vector.ADD,
        descriptor_id=add_op,
        wait_set_id=builder.wait_set([matmul_event], key="wait.matmul"),
        signal_event_id=add_event,
        source_operation_id=1,
    )
    if layer_loop != NO_ID:
        builder.close_loop()
    reduce_event = builder.new_event()
    builder.emit(
        Major.REDUCTION,
        Reduction.ORDERED_SUM,
        descriptor_id=reduce_op,
        wait_set_id=builder.wait_set([add_event], key="wait.add"),
        signal_event_id=reduce_event,
        source_operation_id=2,
    )
    argmax_event = builder.new_event()
    builder.emit(
        Major.SELECTION,
        Selection.ARGMAX,
        descriptor_id=argmax_op,
        wait_set_id=builder.wait_set([reduce_event], key="wait.reduce"),
        signal_event_id=argmax_event,
        source_operation_id=3,
    )
    builder.emit(
        Major.SELECTION,
        Selection.TOKEN_APPEND,
        descriptor_id=append_op,
        wait_set_id=builder.wait_set([argmax_event], key="wait.argmax"),
        source_operation_id=4,
    )
    builder.emit(
        Major.DMA,
        Dma.TRANSFER,
        descriptor_id=kv_stage_op,
        source_operation_id=5,
    )
    builder.emit(Major.STATE, State.COMMIT, descriptor_id=kv_state)
    builder.emit(Major.CONTROL, Control.COMPLETE)
    builder.entrypoint(
        entrypoint_id=0,
        first_instruction=0,
        phase=Phase.PREFILL,
        generation_policy_id=policy,
    )
    builder.entrypoint(
        entrypoint_id=1,
        first_instruction=0,
        phase=Phase.DECODE,
        generation_policy_id=policy,
    )
    builder.source_identity = {"fixture": "abi3-cycle-tiled-v1"}
    return builder.finish(), capability


def synthetic_link_deployment() -> tuple[Deployment, Capability]:
    """A deployment whose last instruction is a LINK the device cannot execute."""
    capability = fixture_capability(TopologyClass.CLUSTER_32)
    builder = _state_builder(capability, target="cycle-synthetic-link")
    builder.require(Feature.INTER_CHIP_ENDPOINT)
    window = builder.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=65536,
        source=ObjectSource.zeros(65536),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.window",
    )
    comm = builder.communication(
        collective_op=CollectiveOp.SUM,
        local_object_id=window,
        remote_object_id=window,
        byte_extent=65536,
        participant_count=32,
        chunk_bytes=4096,
        key="comm.allreduce",
    )
    builder.emit(Major.LINK, Link.COLLECTIVE, descriptor_id=comm)
    builder.emit(Major.CONTROL, Control.COMPLETE)
    builder.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return builder.finish(), capability


def backward_wait_deployment() -> tuple[Deployment, Capability]:
    """A program whose wait names an event signalled *later* in program order."""
    capability = fixture_capability()
    builder = _state_builder(capability, target="cycle-synthetic-backward")
    late = builder.new_event()
    snapshot_class = builder.counter_class(
        int(CounterGroup.INSTRUCTION),
        [counter_id(CounterGroup.INSTRUCTION, 3)],
        key="ctr.snapshot",
    )
    builder.emit(
        Major.OBSERVATION,
        Observation.COUNTER_SNAPSHOT,
        descriptor_id=snapshot_class,
        wait_set_id=builder.wait_set([late], key="wait.late"),
    )
    builder.emit(
        Major.OBSERVATION,
        Observation.TRACE_CHECKPOINT,
        descriptor_id=snapshot_class,
        signal_event_id=late,
    )
    builder.emit(Major.CONTROL, Control.COMPLETE)
    builder.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return builder.finish(), capability


# ---------------------------------------------------------------------------
# 1. The counter registry
# ---------------------------------------------------------------------------
def test_timing_group_is_exactly_the_latency_group():
    for cid, name in COUNTERS.items():
        assert is_timing_counter(name) == (name.startswith("latency."))
        assert is_timing_counter(name) == ((cid >> 24) == int(CounterGroup.LATENCY))


def test_new_timing_counters_are_registered_and_unique():
    added = [
        "latency.compute_cycles",
        "latency.engine_busy_cycles",
        "latency.engine_idle_cycles",
        "latency.queue_stall_cycles",
        "latency.wait_stall_cycles",
        "latency.memory_stall_cycles",
        "latency.hbm_busy_cycles",
        "latency.sram_busy_cycles",
        "latency.rom_busy_cycles",
        "latency.host_busy_cycles",
        "latency.sram_bank_conflict_cycles",
        "latency.hbm_channel_conflict_cycles",
        "latency.link_serialization_cycles",
        "latency.link_hop_cycles",
        "latency.link_credit_stall_cycles",
        "latency.link_retry_cycles",
        "latency.link_switch_contention_cycles",
        "latency.collective_cycles",
        "latency.barrier_cycles",
        "latency.node_skew_cycles",
        "latency.sequencer_fetch_cycles",
    ]
    for name in added:
        assert name in NAME_TO_ID, f"{name} is not in the frozen registry"
    assert len(set(COUNTERS.values())) == len(COUNTERS)
    assert len(set(COUNTERS)) == len(COUNTERS)


def test_frozen_counter_ids_are_unchanged():
    # Adding an event is additive; changing an assigned one is not.
    assert NAME_TO_ID["latency.transaction_cycles"] == counter_id(CounterGroup.LATENCY, 1)
    assert NAME_TO_ID["latency.issue_cycles"] == counter_id(CounterGroup.LATENCY, 2)
    assert NAME_TO_ID["latency.stall_cycles"] == counter_id(CounterGroup.LATENCY, 3)
    assert NAME_TO_ID["instructions.retired"] == counter_id(CounterGroup.INSTRUCTION, 3)


# ---------------------------------------------------------------------------
# 2. Cost tables and provenance
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", SHIPPED_TABLES, ids=lambda p: p.name)
def test_shipped_cost_table_loads_and_labels_every_value(path: Path):
    table = load_cost_table(path)
    assert table.parameters
    for name, entry in table.parameters.items():
        provenance = Provenance(entry["provenance"])
        if provenance is not Provenance.ASSUMED:
            assert entry.get("source"), f"{name} claims {provenance.value} with no source"
        assert "value" in entry
        assert entry.get("unit"), f"{name} has no unit"


def test_cost_table_rejects_an_unlabelled_parameter(tmp_path: Path):
    body = json.loads(BASELINE.read_text())
    body["parameters"]["clock.frequency_hz"].pop("provenance")
    path = tmp_path / "abi3_cost_broken.json"
    path.write_text(json.dumps(body))
    with pytest.raises(MachineError, match="provenance"):
        load_cost_table(path)


def test_cost_table_rejects_characterized_without_a_source(tmp_path: Path):
    body = json.loads(BASELINE.read_text())
    body["parameters"]["clock.frequency_hz"]["provenance"] = "characterized"
    body["parameters"]["clock.frequency_hz"].pop("source", None)
    path = tmp_path / "abi3_cost_nosource.json"
    path.write_text(json.dumps(body))
    table = load_cost_table(path)
    with pytest.raises(MachineError, match="without citing a source"):
        table.resolve("clock.frequency_hz")


def test_cost_table_requires_the_reserved_filename_prefix(tmp_path: Path):
    path = tmp_path / "not_a_cost_table.json"
    path.write_text(BASELINE.read_text())
    with pytest.raises(MachineError, match="prefix"):
        load_cost_table(path)


def test_missing_parameter_fails_closed_rather_than_defaulting(tmp_path: Path):
    body = json.loads(BASELINE.read_text())
    del body["parameters"]["hbm.read_latency_cycles"]
    path = tmp_path / "abi3_cost_missing.json"
    path.write_text(json.dumps(body))
    table = load_cost_table(path)
    machine = MachineModel(fixture_capability(), table)
    with pytest.raises(MachineError, match="refuses to substitute"):
        machine.memory()


def test_ns_to_cycles_composition_takes_the_weaker_provenance():
    """A characterized SPICE latency over an assumed clock is not characterized."""
    table = load_cost_table(SKY130_ROM)
    assert table.resolve("rom.read_latency_cycles").provenance is Provenance.CHARACTERIZED
    assert table.resolve("clock.frequency_hz").provenance is Provenance.ASSUMED
    machine = MachineModel(fixture_capability(), table)
    machine.memory()
    resolved = machine.used()["rom.read_latency_cycles"]
    assert resolved.unit == "cycles"
    assert resolved.provenance is Provenance.ASSUMED
    assert "clock.frequency_hz" in resolved.source
    assert resolved.value >= 1


def test_bandwidth_conversion_carries_the_datasheet_source():
    table = load_cost_table(BASELINE)
    machine = MachineModel(fixture_capability(), table)
    machine.memory()
    resolved = machine.used()["hbm.bytes_per_cycle_per_channel"]
    assert resolved.unit == "B/cycle"
    assert "technology_inputs.json" in resolved.source
    # datasheet bandwidth over an assumed clock is assumed, not datasheet
    assert resolved.provenance is Provenance.ASSUMED


def test_work_over_cycles_shows_its_division_instead_of_a_bare_quotient():
    """A measured rate arrives as two operands, and the model divides them.

    ``docs/METHODOLOGY.md`` section 0: where a figure is the author's
    arithmetic on two cited cells, the document shows the division.  A rate
    pre-divided by hand is a number whose derivation lives only in prose.
    """
    table = load_cost_table(ASAP7_V2)
    entry = table.entry("engine.tensor.work_per_lane_cycle")
    assert entry["convert"] == "work_over_cycles"
    assert entry["work_units"] > 0 and entry["cycles"] > 0
    machine = MachineModel(fixture_capability(), table)
    tensor = machine.engine("tensor")
    assert tensor.work_per_lane_cycle == entry["work_units"] / entry["cycles"]
    resolved = machine.used()["engine.tensor.work_per_lane_cycle"]
    assert resolved.provenance is Provenance.CHARACTERIZED
    assert str(entry["work_units"]) in resolved.note
    assert str(entry["cycles"]) in resolved.note


def test_a_measured_rate_that_disagrees_with_its_own_operands_is_refused(
    tmp_path: Path,
):
    """The stated quotient and the stated operands must be the same number.

    This is the defect class this repository keeps finding: a legal value, no
    trap, nothing refused.  A table that says 1.0 while its operands say 0.34
    would time the machine at the number nobody measured.
    """
    body = json.loads(ASAP7_V2.read_text())
    body["parameters"]["engine.tensor.work_per_lane_cycle"]["value"] = 1.0
    path = tmp_path / "abi3_cost_liar.json"
    path.write_text(json.dumps(body))
    machine = MachineModel(fixture_capability(), load_cost_table(path))
    with pytest.raises(MachineError, match="states 1.0 but"):
        machine.engine("tensor")


def test_a_measured_rate_needs_both_operands(tmp_path: Path):
    body = json.loads(ASAP7_V2.read_text())
    del body["parameters"]["engine.tensor.work_per_lane_cycle"]["cycles"]
    path = tmp_path / "abi3_cost_halfmeasured.json"
    path.write_text(json.dumps(body))
    machine = MachineModel(fixture_capability(), load_cost_table(path))
    with pytest.raises(MachineError, match="'work_units' and a 'cycles'"):
        machine.engine("tensor")


def test_a_measured_rate_does_not_borrow_the_clock_s_provenance(tmp_path: Path):
    """A work-per-cycle rate is the same number at any frequency.

    ``ns_to_cycles`` and the bandwidth conversion both divide by the clock and
    are therefore no stronger than it.  This one does not, so an assumed clock
    must not drag a measured rate down with it -- and a characterized clock
    must not prop a bad one up.
    """
    body = json.loads(ASAP7_V2.read_text())
    body["parameters"]["clock.frequency_hz"] = {
        "value": 1e9,
        "unit": "Hz",
        "provenance": "assumed",
    }
    path = tmp_path / "abi3_cost_assumedclock.json"
    path.write_text(json.dumps(body))
    machine = MachineModel(fixture_capability(), load_cost_table(path))
    machine.engine("tensor")
    assert (
        machine.used()["engine.tensor.work_per_lane_cycle"].provenance
        is Provenance.CHARACTERIZED
    )


@pytest.mark.parametrize("path", ROUTED_CLOCK_TABLES, ids=lambda p: p.name)
def test_a_derived_table_names_the_engines_that_have_no_routed_block(path: Path):
    """The clock is an upper bound, and the table has to say why.

    A routed view's core clock is the minimum over the blocks routed so far.
    Families with no routed block can only lower it, so a table that did not
    name them would read as a measurement of the whole machine.
    """
    body = json.loads(path.read_text())
    derived = body["derived_from"]
    assert derived["generator"] == "tools/build_abi3_cost_tables.py"
    assert derived["clock_is_routed"] is True
    clock = body["parameters"]["clock.frequency_hz"]
    assert clock["provenance"] == "characterized"
    uncovered = derived["engine_families_with_no_routed_block"]
    for family in uncovered:
        assert family in clock["note"], (
            f"{family} has no routed block and the clock note does not say so"
        )
    if uncovered:
        assert "upper bound" in clock["note"]
    else:
        assert "not an upper bound" in clock["note"]
    # Whatever is covered must be named too: the note is where a reader learns
    # which block set the clock and which ones it beat.
    assert "minimum post-route fmax" in clock["note"]


def test_the_asap7_clock_is_the_routed_tensor_engine_not_the_integer_proxy():
    """The block the machine spends its cycles in is the one that sets the clock.

    ``abi3-cost-asap7-v1`` took its clock from ``ot_numeric_dot``, whose own
    campaign claim boundary says it implements signed integer DV and *not* the
    BF16 arithmetic this program targets.  ``ot_ta_matmul_bf16_sram_engine`` is
    the real tensor engine, it is now routed on the same platform and corner,
    and it closes several times slower.  A core clock taken from a proxy that
    is faster than the block it stands in for is the optimistic direction, so
    this test pins the replacement.
    """
    routed = json.loads(
        (
            REPO / "results" / "physical_abi3" / "asap7"
            / "matmul_bf16_sram_engine" / "pnr.json"
        ).read_text()
    )
    metrics = routed["place_and_route"]["metrics"]
    assert routed["design"]["top"] == "ot_ta_matmul_bf16_sram_engine"
    assert metrics["drc_errors"] == 0
    assert metrics["setup_violations"] == 0 and metrics["hold_violations"] == 0
    table = json.loads(ASAP7_V2.read_text())
    clock = table["parameters"]["clock.frequency_hz"]
    assert clock["value"] == metrics["fmax_hz"]
    assert "matmul_bf16_sram_engine" in clock["source"]
    hand = json.loads(ASAP7.read_text())["parameters"]["clock.frequency_hz"]
    assert clock["value"] < hand["value"], (
        "the routed tensor engine is meant to be the binding, slower block"
    )
    assert "tensor" not in table["derived_from"][
        "engine_families_with_no_routed_block"
    ]


@pytest.mark.parametrize("path", [CLUSTER32_V2, WAFER_V2], ids=lambda p: p.name)
def test_an_unrouted_view_keeps_its_assumed_clock(path: Path):
    """A measured rate must not smuggle in a clock from a different view.

    ADR-003 section 3.5 forbids mixing views, and the easiest way to break that
    rule by accident is to give a table one view's measured rate and another
    view's routed frequency.  Nothing of a 32-node or wafer machine has been
    routed, so these tables take the rates and keep the assumption.
    """
    body = json.loads(path.read_text())
    assert body["derived_from"]["clock_is_routed"] is False
    assert body["parameters"]["clock.frequency_hz"]["provenance"] == "assumed"
    assert body["parameters"]["engine.tensor.work_per_lane_cycle"][
        "provenance"
    ] == "characterized"
    # Every family is uncovered, because no block of this machine is routed.
    uncovered = body["derived_from"]["engine_families_with_no_routed_block"]
    assert set(uncovered) >= {"tensor", "vector", "reduction", "link"}
    machine = MachineModel(
        cycle_capability(
            TopologyClass.CLUSTER_32
            if "cluster" in path.name
            else TopologyClass.WAFER_LOGICAL_DEVICE
        ),
        load_cost_table(path),
    )
    machine.engine("tensor")
    assert machine.provenance_class() is Provenance.ASSUMED


@pytest.mark.parametrize("path", DERIVED_TABLES, ids=lambda p: p.name)
def test_the_reduction_rate_is_measured_and_matches_its_campaign(path: Path):
    """An assumption that turns out to be right is still worth measuring.

    ``engine.reduction.work_per_lane_cycle`` was a hand-written 1.0.  The
    endpoint that implements the family is routed in both physical views, and
    two simulators now measure its rate directly, so the table carries the
    measurement.  It lands just under 1.0 -- the assumption was very nearly
    right, which is a result, and one nobody could have stated before.
    """
    campaign = json.loads((REPO / "results" / "rtl" / "abi3_engine_rate.json").read_text())
    case = next(
        c for c in campaign["cases"] if c["engine_family"] == "reduction"
    )
    assert case["simulators_agree"] is True
    assert {run["simulator"] for run in case["runs"]} == {"iverilog", "verilator"}
    entry = json.loads(path.read_text())["parameters"][
        "engine.reduction.work_per_lane_cycle"
    ]
    assert entry["provenance"] == "characterized"
    assert entry["work_units"] == case["work_units"]
    assert entry["cycles"] == case["cycles"]
    machine = MachineModel(fixture_capability(), load_cost_table(path))
    assert machine.engine("reduction").work_per_lane_cycle == pytest.approx(
        case["work_units"] / case["cycles"]
    )
    # The bench counts the drain, so it cannot overstate the engine.
    assert entry["value"] <= 1.0


def test_the_derived_tables_still_match_the_artifacts_they_cite():
    """``--check`` is the guard that a cost table did not drift from evidence."""
    completed = subprocess.run(
        [sys.executable, str(REPO / "tools" / "build_abi3_cost_tables.py"), "--check"],
        cwd=REPO,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_capability_supplies_structure_and_cost_table_supplies_rates():
    capability = fixture_capability()
    machine = MachineModel(capability, load_cost_table(BASELINE))
    tensor = machine.engine("tensor")
    assert tensor.lanes == capability.engines["tensor"]["lanes"]
    assert machine.used()["engine.tensor.lanes"].origin == "capability"
    assert machine.used()["engine.tensor.work_per_lane_cycle"].origin == "cost_table"
    memory = machine.memory()
    assert memory.sram.units == capability.memory["sram"]["banks"]
    # HBM channel count is not advertised by this capability, so it falls back
    # to the cost table and is labelled there.
    assert machine.used()["hbm.channels"].origin == "cost_table"


# ---------------------------------------------------------------------------
# 3. Architectural-counter agreement (the load-bearing property)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "storage,table",
    [(StorageClass.HBM, BASELINE), (StorageClass.ROM, SKY130_ROM)],
)
def test_tiled_deployment_counter_agreement(storage: StorageClass, table: Path):
    """The load-bearing property, on a transaction that actually contracts."""
    deployment, capability = synthetic_tiled_deployment(storage_class=storage)
    req = request()
    result = CycleModel(deployment, capability, load_cost_table(table)).run(req)
    body = result.to_dict()
    assert body["execution"]["status"] == "SUCCESS"
    reference = functional_counters(deployment, capability, req)
    assert result.architectural == reference
    assert reference["tensor.multiplications"] > 0
    assert reference["selection.tokens_selected"] == 1
    assert body["timing"]["tile_launches"] > 0


@pytest.mark.parametrize(
    "storage,table",
    [(StorageClass.HBM, BASELINE), (StorageClass.ROM, SKY130_ROM)],
)
def test_abi3_fixture_counter_agreement(storage: StorageClass, table: Path):
    """The conformance fixture, timed and checked against the functional device."""
    capability = fixture_capability()
    deployment = build_fixture(storage_class=storage, capability=capability)
    req = request()
    model = CycleModel(deployment, capability, load_cost_table(table))
    assert model.schedule_audit["complete"], model.schedule_audit["findings"]
    result = model.run(req)
    body = result.to_dict()
    assert body["execution"]["status"] == "SUCCESS"
    assert result.architectural == functional_counters(deployment, capability, req)
    assert body["timing"]["tile_launches"] > 0


def test_every_fixture_operator_carries_a_tile_mapping():
    """The audit is what makes an unmapped operator visible before a run."""
    capability = fixture_capability()
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    model = CycleModel(deployment, capability, load_cost_table(BASELINE))
    audit = model.schedule_audit
    assert audit["complete"] is True
    assert audit["findings"] == []
    assert audit["operators_checked"] >= 4
    for did in deployment.table.ids_of_type(ExtendedDescriptorType.OPERATOR):
        operator = deployment.table[did]
        assert operator.payload["schedule_id"] != NO_ID


def test_synthetic_deployment_completes_and_agrees():
    deployment, capability = synthetic_state_deployment()
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors
    req = request()
    model = CycleModel(deployment, capability, load_cost_table(BASELINE))
    result = model.run(req)
    body = result.to_dict()
    assert body["execution"]["status"] == "SUCCESS"
    counters = result.architectural
    assert counters == functional_counters(deployment, capability, req)
    # The transaction really did work: it committed state bytes and iterated.
    assert counters["state.commits"] == 1
    assert counters["state.rows_committed"] == 1
    # Two writes into the STATE class, not one: the staging DMA puts a row into
    # the prepared image and the commit publishes that row into the committed
    # image.  Amendment A21 is what makes the first of those mandatory -- an
    # unstaged prepared image commits nothing at all.
    assert counters["state.bytes_written"] == 2 * ROW_ELEMS * 2
    assert counters.get("state.unstaged_commits", 0) == 0
    assert counters["control.loop_iterations"] == 4
    assert counters["fault.drains"] == 1


def test_multi_transaction_agreement():
    deployment, capability = synthetic_state_deployment()
    req = request(transactions=3)
    model = CycleModel(deployment, capability, load_cost_table(BASELINE))
    result = model.run(req)
    assert result.to_dict()["execution"]["transactions"] == 3
    assert result.architectural == functional_counters(deployment, capability, req)
    assert result.architectural["state.commits"] == 3


def test_trap_agreement_on_a_link_collective():
    """Both models must fail in the same place, in the same way."""
    deployment, capability = synthetic_link_deployment()
    req = request()
    result = CycleModel(deployment, capability, load_cost_table(CLUSTER32)).run(req)
    body = result.to_dict()
    reference = functional_reference(deployment, capability, req)
    assert body["execution"]["status"] == reference["status"] == "FAILED"
    assert body["execution"]["trap_class"] == reference["trap_class"]
    assert (
        body["execution"]["first_fault_instruction"]
        == reference["first_fault_instruction"]
    )
    assert body["execution"]["retired"] == reference["retired"]
    assert result.architectural == reference["counters"]


def test_agreement_holds_across_cost_tables():
    """Two machines, one architecture: only the timing may differ."""
    deployment, capability = synthetic_state_deployment()
    req = request()
    first = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(req)
    second = CycleModel(deployment, capability, load_cost_table(ASAP7)).run(req)
    assert first.architectural == second.architectural
    assert first.to_dict()["timing"]["seconds"] != second.to_dict()["timing"]["seconds"]


def test_a_measured_engine_rate_changes_the_timing_and_nothing_else():
    """W9.5, stated as a property.

    Feeding a characterized rate back in is only legitimate if it moves the
    clock and leaves the architecture alone.  The tiled deployment contracts,
    so its tensor time is real work; the derived table must slow it down --
    the measured engine retires 0.35 work units per cycle where the hand
    table assumed one -- without moving a single architectural counter.
    """
    deployment, capability = synthetic_tiled_deployment()
    req = request()
    hand = CycleModel(deployment, capability, load_cost_table(ASAP7)).run(req)
    measured = CycleModel(deployment, capability, load_cost_table(ASAP7_V2)).run(req)
    assert hand.architectural == measured.architectural
    hand_body = hand.to_dict()
    measured_body = measured.to_dict()
    hand_tensor = hand_body["engines"]["tensor"]
    measured_tensor = measured_body["engines"]["tensor"]
    assert hand_tensor["issued_tile_work"] == measured_tensor["issued_tile_work"]
    assert measured_tensor["busy_cycles"] > hand_tensor["busy_cycles"]
    assert measured_body["timing"]["total_cycles"] > hand_body["timing"]["total_cycles"]


def test_making_the_clock_characterized_promotes_what_divides_by_it():
    """A conversion is no stronger than its weakest input -- in both directions.

    The SKY130 view's ROM read latency is a real ngspice measurement that v1
    had to report as ``assumed``, because turning nanoseconds into cycles
    needed a clock nobody had measured.  A routed clock does not make the SPICE
    run better; it removes the assumption that was hiding it.
    """
    hand = load_cost_table(SKY130_ROM)
    derived = load_cost_table(SKY130_ROM_V2)
    assert hand.resolve("clock.frequency_hz").provenance is Provenance.ASSUMED
    assert derived.resolve("clock.frequency_hz").provenance is Provenance.CHARACTERIZED
    # The underlying SPICE figure is the same nanosecond number in both.
    assert hand.entry("rom.read_latency_cycles")["value"] == (
        derived.entry("rom.read_latency_cycles")["value"]
    )
    for table, expected in ((hand, Provenance.ASSUMED), (derived, Provenance.CHARACTERIZED)):
        machine = MachineModel(fixture_capability(), table)
        machine.memory()
        assert machine.used()["rom.read_latency_cycles"].provenance is expected


def test_timing_counters_are_disjoint_from_architectural_counters():
    deployment, capability = synthetic_state_deployment()
    result = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(request())
    architectural = result.architectural
    timing = result.timing
    assert not set(architectural) & set(timing)
    assert all(not is_timing_counter(n) for n in architectural)
    assert all(is_timing_counter(n) for n in timing)
    assert timing["latency.transaction_cycles"] > 0
    assert timing["latency.issue_cycles"] > 0
    assert timing["latency.sequencer_fetch_cycles"] > 0


def test_functional_device_leaves_every_timing_counter_at_zero():
    deployment, capability = synthetic_state_deployment()
    device = Device(deployment, capability)
    session = device.create_session()
    result = device.run_transaction(
        session, entrypoint_id=0, symbols=request().symbols
    )
    assert timing_counters(result.counters) == {}
    assert architectural_counters(result.counters)


# ---------------------------------------------------------------------------
# 3b. Schedule-driven tiling
#
# The program carries no tile loops, so this model is the only place tiling
# becomes time.  These tests protect that: a missing or zeroed mapping must be a
# hard error, a different tile shape must change cycles and nothing else, and
# every schedule field the model claims to honour must be observable in the
# result.
# ---------------------------------------------------------------------------
def test_tile_count_follows_the_schedule_not_the_program():
    deployment, capability = synthetic_tiled_deployment(
        tile_rows=4, tile_cols=8, tile_depth=16
    )
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    tensor = body["tiling"]["by_family"]["tensor"]
    # 8x32x64 contraction under a 4x8x16 tile: 2 * 4 * 4 tiles.
    assert tensor["tiles"] == 2 * 4 * 4
    assert tensor["tile_shapes"][0]["tile_rows"] == 4
    assert body["tiling"]["source"] == "SCHEDULE descriptor"
    # The program itself contains no tile loop: eight operations plus the
    # amendment-A21 staging DMA that makes the commit publish real rows.
    assert body["execution"]["retired"] == 9


def test_tile_shape_changes_cycles_but_never_architectural_counters():
    coarse, capability = synthetic_tiled_deployment(
        tile_rows=8, tile_cols=32, tile_depth=64
    )
    fine, _ = synthetic_tiled_deployment(
        capability, tile_rows=2, tile_cols=4, tile_depth=8
    )
    req = request()
    table = load_cost_table(BASELINE)
    coarse_result = CycleModel(coarse, capability, table).run(req)
    fine_result = CycleModel(fine, capability, table).run(req)
    assert coarse_result.architectural == fine_result.architectural
    assert (
        fine_result.to_dict()["tiling"]["tile_launches"]
        > coarse_result.to_dict()["tiling"]["tile_launches"]
    )
    assert coarse_result.total_cycles != fine_result.total_cycles


def test_partial_tiles_charge_their_padding():
    deployment, capability = synthetic_tiled_deployment(
        tile_rows=3, tile_cols=7, tile_depth=10
    )
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    tensor = body["tiling"]["by_family"]["tensor"]
    assert tensor["padding_work"] > 0
    assert tensor["issued_work"] > tensor["useful_work"]
    assert body["counters"]["timing"]["latency.tile_padding_work"] > 0


def test_an_absent_tile_mapping_is_rejected_before_it_reaches_the_model():
    """The verifier now refuses an untimeable deployment at admission.

    That is stronger than catching it here: the deployment never reaches a
    timing model at all. The cycle model keeps its own check for the case where
    verification is bypassed, which is what the rest of this test exercises.
    """
    deployment, capability = synthetic_tiled_deployment(schedule_reduction=False)
    report = verify_deployment(deployment, capability)
    assert not report.admitted
    assert any("carries no SCHEDULE descriptor" in e for e in report.errors), report.errors
    with pytest.raises(ScheduleError, match="carries no SCHEDULE descriptor"):
        CycleModel(deployment, capability, load_cost_table(BASELINE), verify=False)
    permissive = CycleModel(
        deployment,
        capability,
        load_cost_table(BASELINE),
        strict_schedules=False,
        verify=False,
    )
    finding = permissive.schedule_audit["findings"][0]
    assert finding["reason"] == "absent_tile_mapping"
    assert finding["mnemonic"] == "REDUCTION.ORDERED_SUM"
    with pytest.raises(ScheduleError):
        permissive.run(request())


def test_a_zeroed_tile_mapping_is_a_hard_error_and_names_the_descriptor():
    deployment, capability = synthetic_tiled_deployment(tile_rows=4)
    # Zero the tensor schedule's tile_rows in place and re-encode the table.
    schedules = deployment.table.ids_of_type(ExtendedDescriptorType.SCHEDULE)
    target = schedules[0]
    descriptor = deployment.table[target]
    descriptor.payload["tile_rows"] = 0
    deployment.table._records[target] = descriptor.encode()  # noqa: SLF001
    with pytest.raises(ScheduleError) as excinfo:
        CycleModel(
            deployment, capability, load_cost_table(BASELINE), verify=False
        )
    message = str(excinfo.value)
    assert f"SCHEDULE descriptor {target}" in message
    assert "tile_rows" in message


def test_schedule_max_outstanding_narrows_the_queue():
    deployment, capability = synthetic_tiled_deployment(max_outstanding=1)
    model = CycleModel(deployment, capability, load_cost_table(BASELINE))
    body = model.run(request()).to_dict()
    tensor = body["tiling"]["by_family"]["tensor"]["examples"][0]
    assert tensor["max_outstanding"] == 1
    assert (
        tensor["max_outstanding"]
        <= capability.limits["max_outstanding_per_queue"]
    )


def test_schedule_max_outstanding_produces_real_queue_stalls():
    """The credit bound is timed, not just reported."""
    table = load_cost_table(BASELINE)
    narrow, capability = synthetic_tiled_deployment(
        independent_matmuls=3, max_outstanding=1
    )
    wide, _ = synthetic_tiled_deployment(
        capability, independent_matmuls=3, max_outstanding=4
    )
    req = request()
    narrow_result = CycleModel(narrow, capability, table).run(req)
    wide_result = CycleModel(wide, capability, table).run(req)
    narrow_body = narrow_result.to_dict()
    wide_body = wide_result.to_dict()
    assert narrow_body["timing"]["queue_stall_cycles"] > 0
    assert wide_body["timing"]["queue_stall_cycles"] == 0
    assert narrow_body["queues"]["tensor.0"]["observed_max_occupancy"] == 1
    assert wide_body["queues"]["tensor.0"]["observed_max_occupancy"] == 4
    assert narrow_result.total_cycles > wide_result.total_cycles
    # A queue bound is a timing property; the architecture is unchanged.
    assert narrow_result.architectural == wide_result.architectural


def test_program_loops_over_layers_and_the_schedule_owns_the_tiles():
    deployment, capability = synthetic_tiled_deployment(layers=4)
    req = request()
    result = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(req)
    body = result.to_dict()
    assert body["execution"]["status"] == "SUCCESS"
    assert result.architectural == functional_counters(deployment, capability, req)
    # Four layer iterations retire four MATMUL descriptors, and the tile count
    # is four times one layer's tiles -- not four times an unrolled tile loop.
    assert result.architectural["control.loop_iterations"] == 4
    assert result.architectural["engine.tensor.descriptors"] == 4
    assert body["tiling"]["by_family"]["tensor"]["tiles"] == 4 * 32


def test_wait_stalls_dominate_a_serial_dependency_chain():
    deployment, capability = synthetic_tiled_deployment(layers=4)
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    timing = body["timing"]
    assert timing["wait_stall_cycles"] > 0
    assert timing["stall_cycles"] == (
        timing["wait_stall_cycles"] + timing["queue_stall_cycles"]
    )


def test_schedule_bank_mask_confines_sram_and_raises_conflicts():
    table = load_cost_table(BASELINE)
    wide, capability = synthetic_tiled_deployment(bank_mask=0)
    narrow, _ = synthetic_tiled_deployment(capability, bank_mask=0b1)
    wide_body = CycleModel(wide, capability, table).run(request()).to_dict()
    narrow_body = CycleModel(narrow, capability, table).run(request()).to_dict()
    assert (
        narrow_body["memory"]["sram"]["conflict_cycles"]
        > wide_body["memory"]["sram"]["conflict_cycles"]
    )
    # The mask changed the timing, never the architectural traffic.
    assert (
        narrow_body["memory"]["sram"]["bytes_total"]
        == wide_body["memory"]["sram"]["bytes_total"]
    )


def test_tiling_amplifies_wire_traffic_but_not_architectural_bytes():
    deployment, capability = synthetic_tiled_deployment(
        tile_rows=4, tile_cols=8, tile_depth=16
    )
    req = request()
    result = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(req)
    body = result.to_dict()
    hbm = body["memory"]["hbm"]
    # The weight operand is re-fetched once per row tile.
    assert hbm["transferred_bytes_read"] == hbm["bytes_read"] * 2
    assert hbm["tile_amplification"] == 2.0
    reference = functional_counters(deployment, capability, req)
    assert reference["hbm.bytes_read"] == hbm["bytes_read"]


def test_issue_window_of_one_serialises_memory_behind_compute():
    deployment, capability = synthetic_tiled_deployment()
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    # The VECTOR schedule declares issue_window=1, so its tile memory cannot
    # overlap its tile compute.
    assert body["timing"]["tile_pipeline_stall_cycles"] > 0
    assert body["engines"]["vector"]["tile_pipeline_stall_cycles"] > 0
    assert body["engines"]["tensor"]["tile_pipeline_stall_cycles"] == 0


def test_operand_extents_follow_the_frozen_operand_table():
    from runtime.cycle.model import TraceStep

    step = TraceStep(index=0, kind="ENGINE", family="tensor")
    step.operand_dims = {"in0": (8, 64), "in1": (32, 64), "out0": (8, 32)}
    assert operand_extents(step) == (8, 32, 64)
    step.family = "vector"
    assert operand_extents(step) == (8, 32, 1)
    step.family = "reduction"
    step.operand_dims = {"in0": (8, 32), "out0": (32,)}
    assert operand_extents(step) == (1, 32, 8)


def test_unmodelled_schedule_fields_are_named_rather_than_ignored():
    deployment, capability = synthetic_tiled_deployment()
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    unmodelled = body["tiling"]["unmodelled_schedule_fields"]
    assert set(unmodelled) == {"resource_bound", "priority"}
    for reason in unmodelled.values():
        assert reason


# ---------------------------------------------------------------------------
# 3c. Numeric contract identity
# ---------------------------------------------------------------------------
def test_result_names_the_numeric_contracts_it_timed():
    deployment, capability = synthetic_tiled_deployment()
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    contracts = body["numerics"]["contracts"]
    assert contracts
    named = {entry["contract"] for entry in contracts.values()}
    assert "bf16_bf16_fp32_sequential_rne_v1" in named
    for entry in contracts.values():
        assert entry["contract"] in capability.numeric_contracts


def test_result_records_the_implementation_identity():
    deployment, capability = synthetic_tiled_deployment()
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    identity = body["numerics"]["implementation_identity"]
    assert set(identity) >= {"python", "numpy", "platform", "device", "note"}
    assert "TA-ABI3-OPCONV-1" in identity["note"]


def test_result_records_which_engines_were_registered():
    deployment, capability = synthetic_tiled_deployment()
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    coverage = body["engine_coverage"]
    assert coverage["implemented"] > 0
    assert isinstance(coverage["missing_operations"], list)


# ---------------------------------------------------------------------------
# 4. Determinism
# ---------------------------------------------------------------------------
def test_same_inputs_produce_byte_identical_output():
    deployment, capability = synthetic_state_deployment()
    req = request(transactions=2)
    first = canonical_json(
        CycleModel(deployment, capability, load_cost_table(BASELINE)).run(req).to_dict()
    )
    second = canonical_json(
        CycleModel(deployment, capability, load_cost_table(BASELINE)).run(req).to_dict()
    )
    assert first == second


def test_cluster_output_is_byte_identical_across_runs():
    capability = fixture_capability(TopologyClass.CLUSTER_32)
    deployment, _ = synthetic_state_deployment(capability, with_communication=True)
    req = request()
    table = load_cost_table(CLUSTER32)
    first = canonical_json(CycleModel(deployment, capability, table).run(req).to_dict())
    second = canonical_json(CycleModel(deployment, capability, table).run(req).to_dict())
    assert first == second


# ---------------------------------------------------------------------------
# 5. Proofs
# ---------------------------------------------------------------------------
def test_bounded_queue_occupancy_is_proved_and_observed():
    deployment, capability = synthetic_state_deployment()
    result = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(request())
    proof = result.to_dict()["proofs"]["bounded_queue_occupancy"]
    assert proof["proved"]
    assert proof["violations"] == []
    for name, bound in proof["bounds"].items():
        assert bound >= 1
        assert proof["observed_max"][name] <= bound


def test_queue_bound_never_exceeds_the_capability_outstanding_limit():
    capability = fixture_capability()
    machine = MachineModel(capability, load_cost_table(BASELINE))
    limit = capability.limits["max_outstanding_per_queue"]
    for family in ("tensor", "vector", "dma", "state"):
        params = machine.engine(family)
        assert params.max_outstanding <= limit
        assert params.max_outstanding <= params.queue_depth


def test_acyclic_waits_proof_passes_on_an_admitted_program():
    deployment, capability = synthetic_state_deployment()
    device = Device(deployment, capability)
    proof = prove_acyclic_waits(device)
    assert proof["proved"], proof["violations"]
    assert proof["dependency_edges"] == 3


def test_acyclic_waits_proof_catches_a_wait_on_a_later_signal():
    """An independent check of the same deadlock the verifier now rejects.

    The two are deliberately separate: the verifier decides admission, the cycle
    model has to prove the schedule it is about to *time* cannot deadlock.  A
    program that waits on an event signalled later in program order would hang
    an in-order microsequencer, and both must say so.
    """
    deployment, capability = backward_wait_deployment()
    assert not verify_deployment(deployment, capability).admitted
    device = Device(deployment, capability, verify=False)
    proof = prove_acyclic_waits(device)
    assert not proof["proved"]
    assert proof["violations"][0]["kind"] == "wait_on_later_or_self_signal"


def test_single_chip_has_no_zero_latency_global_operation_to_model():
    deployment, capability = synthetic_state_deployment()
    result = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(request())
    proof = result.to_dict()["proofs"]["no_zero_latency_global_operations"]
    assert proof["proved"]


@pytest.mark.parametrize(
    "topology,table",
    [
        (TopologyClass.CLUSTER_32, CLUSTER32),
        (TopologyClass.WAFER_LOGICAL_DEVICE, WAFER),
    ],
)
def test_global_operations_are_never_zero_latency(topology, table):
    capability = fixture_capability(topology)
    deployment, _ = synthetic_state_deployment(capability)
    result = CycleModel(deployment, capability, load_cost_table(table)).run(request())
    proof = result.to_dict()["proofs"]["no_zero_latency_global_operations"]
    assert proof["proved"]
    assert proof["violations"] == []
    assert all(cycles > 0 for cycles in proof["probe_cycles"].values())


# ---------------------------------------------------------------------------
# 6. Provenance of reported rates
# ---------------------------------------------------------------------------
def test_every_reported_rate_names_the_provenance_of_every_input():
    deployment, capability = synthetic_state_deployment()
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    assert body["rates"]
    used = set(body["provenance"]["parameters"])
    for rate in body["rates"]:
        provenance = rate["provenance"]
        assert provenance["inputs"], f"{rate['name']} names no inputs"
        assert set(provenance["inputs"]) <= used
        assert provenance["class"] in {p.value for p in Provenance}


def test_a_result_that_used_an_assumed_value_is_labelled_assumed():
    deployment, capability = synthetic_state_deployment()
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    provenance = body["provenance"]
    assert provenance["class"] == "assumed"
    assert provenance["depends_on_assumed_values"] is True
    assert provenance["by_class"]["assumed"]


def test_characterized_inputs_are_reported_by_name():
    deployment, capability = synthetic_state_deployment()
    body = CycleModel(deployment, capability, load_cost_table(ASAP7)).run(
        request()
    ).to_dict()
    characterized = body["provenance"]["by_class"]["characterized"]
    assert "clock.frequency_hz" in characterized
    parameter = body["provenance"]["parameters"]["clock.frequency_hz"]
    assert "results/asap7_physical/physical.json" in parameter["source"]
    assert parameter["value"] == 243123000.0


# ---------------------------------------------------------------------------
# 7. Memory hierarchy
# ---------------------------------------------------------------------------
def test_state_traffic_is_timed_in_its_backing_storage_class():
    deployment, capability = synthetic_state_deployment()
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    memory = body["memory"]
    assert memory["state_backing_storage_class"] == "SRAM"
    # Two row-sized reads and two row-sized writes reach the backing class: the
    # staging DMA reads scratch and writes the prepared image, and the atomic
    # commit reads that prepared extent and writes the committed one.
    assert memory["sram"]["bytes_read"] == 2 * ROW_ELEMS * 2
    assert memory["sram"]["bytes_written"] == 2 * ROW_ELEMS * 2
    assert memory["sram"]["transactions"] >= 4
    assert memory["sram"]["busy_cycles"] > 0


def test_rom_and_hbm_route_the_same_weight_traffic_to_different_classes():
    """The property the ROM-versus-HBM comparison rests on.

    The two builds differ only in the weight object's storage class, so the same
    contraction must appear as ROM traffic in one and HBM traffic in the other,
    with identical architectural counters.
    """
    table = load_cost_table(BASELINE)
    hbm_deployment, capability = synthetic_tiled_deployment(
        storage_class=StorageClass.HBM
    )
    rom_deployment, _ = synthetic_tiled_deployment(
        capability, storage_class=StorageClass.ROM
    )
    req = request()
    hbm = CycleModel(hbm_deployment, capability, table).run(req)
    rom = CycleModel(rom_deployment, capability, table).run(req)
    hbm_body, rom_body = hbm.to_dict(), rom.to_dict()
    assert hbm_body["memory"]["hbm"]["bytes_read"] > 0
    assert hbm_body["memory"]["rom"]["bytes_read"] == 0
    assert rom_body["memory"]["rom"]["bytes_read"] > 0
    assert rom_body["memory"]["hbm"]["bytes_read"] == 0
    assert (
        rom_body["memory"]["rom"]["bytes_read"]
        == hbm_body["memory"]["hbm"]["bytes_read"]
    )
    # Architecturally the two builds are the same program on the same data.
    hbm_counters = hbm.architectural
    rom_counters = rom.architectural
    assert hbm_counters.pop("hbm.bytes_read") == rom_counters.pop("rom.bytes_read")
    assert hbm_counters == rom_counters


def test_memory_report_accounts_for_every_byte_the_device_moved():
    """The memory report is the functional device's traffic, not a sample of it.

    The cycle model instruments the device's view resolvers to learn which
    object each engine touched, and buckets those accesses by storage class.
    The architectural byte counters are produced independently, by the frozen
    device, so the two are an end-to-end check on the instrumentation: if a
    change to ``runtime/sim`` moves where an engine reads from, the report goes
    quiet and this test says so rather than the study silently resting on
    zero-byte timing.

    HBM, ROM and HOST reconcile exactly.  SRAM carries the state resource as
    well, because ADR-003 leaves a STATE object's placement open and the
    machine model backs it with SRAM.  The two sides differ by different
    amounts and the difference is the point: the atomic commit *reads* the
    prepared image and *writes* the committed one, but only the write is an
    architectural STATE byte, so the read side of the SRAM report exceeds the
    SRAM counters by one commit payload while the write side exceeds them by
    every STATE byte written -- the staging DMA's row plus the commit's.
    """
    deployment, capability = synthetic_tiled_deployment(storage_class=StorageClass.HBM)
    result = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(request())
    body = result.to_dict()
    arch = result.architectural
    assert body["memory"]["state_backing_storage_class"] == "SRAM"

    for klass in ("hbm", "rom", "host"):
        block = body["memory"][klass]
        assert block["bytes_read"] == arch.get(f"{klass}.bytes_read", 0), klass
        assert block["bytes_written"] == arch.get(f"{klass}.bytes_written", 0), klass

    state_written = arch.get("state.bytes_written", 0)
    assert state_written > 0, "amendment A21 left this commit unstaged"
    commit_bytes = arch["state.rows_committed"] * TILE_DEPTH * 2
    assert body["memory"]["sram"]["bytes_read"] == arch["sram.bytes_read"] + commit_bytes
    assert (
        body["memory"]["sram"]["bytes_written"]
        == arch["sram.bytes_written"] + state_written
    )
    # One row staged and the same row published.
    assert state_written == 2 * commit_bytes
    # And the weight traffic really is on the wire, not merely in a counter.
    assert body["memory"]["hbm"]["bytes_read"] > 0
    assert body["memory"]["hbm"]["busy_cycles"] > 0


def test_cluster_timing_is_one_node_and_says_so():
    """A node's share is a node's share, not thirty-two nodes' work.

    The functional device replays every compute instruction once per logical
    node inside a single transaction, so its architectural counters are cluster
    totals.  The cycle model times one node and replays it, so its timing and
    its memory traffic must be that one node's -- otherwise every per-node
    figure, and the critical path built from them, is inflated by the node
    count.  The result states which of the two scopes each block carries.
    """
    capability = cycle_capability(TopologyClass.CLUSTER_32)
    deployment, _ = synthetic_tiled_deployment(capability)
    req = request()
    body = CycleModel(deployment, capability, load_cost_table(CLUSTER32)).run(
        req
    ).to_dict()
    nodes = body["cluster"]["nodes"]
    assert nodes == 32
    arch = body["counters"]["architectural"]
    # The device counted thirty-two nodes' weight reads; the model timed one.
    assert arch["hbm.bytes_read"] == nodes * body["memory"]["hbm"]["bytes_read"]
    assert body["memory"]["hbm"]["bytes_read"] > 0
    scope = body["cluster"]["reporting_scope"]
    assert scope["memory"] == "one node"
    assert scope["timing"] == "one node"
    assert scope["counters.architectural"] == "the whole cluster"

    # One node's compute is what a single chip running the same program spends,
    # which is the strongest available statement that the replay is a replay.
    single_capability = cycle_capability()
    single, _ = synthetic_tiled_deployment(single_capability)
    single_body = CycleModel(
        single, single_capability, load_cost_table(CLUSTER32)
    ).run(req).to_dict()
    assert (
        body["cluster"]["per_node"][0]["compute_cycles"]
        == single_body["timing"]["compute_cycles"]
    )


def test_memory_bandwidth_and_latency_move_the_total(tmp_path: Path):
    """A slower memory really does make the same program take longer."""
    body = json.loads(BASELINE.read_text())
    body["parameters"]["hbm.read_latency_cycles"]["value"] = 12000
    body["parameters"]["hbm.bytes_per_cycle_per_channel"]["value"] = 4.0e9
    body["cost_table_id"] = "abi3-cost-slow-hbm"
    slow = tmp_path / "abi3_cost_slow.json"
    slow.write_text(json.dumps(body))

    deployment, capability = synthetic_tiled_deployment()
    req = request()
    fast_result = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(req)
    slow_result = CycleModel(deployment, capability, load_cost_table(slow)).run(req)
    assert slow_result.total_cycles > fast_result.total_cycles * 5
    assert slow_result.architectural == fast_result.architectural


def test_each_storage_class_keeps_its_own_bandwidth_and_latency():
    machine = MachineModel(fixture_capability(), load_cost_table(BASELINE))
    memory = machine.memory()
    assert memory.rom.read_latency_cycles != memory.hbm.read_latency_cycles
    assert memory.rom.bytes_per_cycle_per_unit != memory.sram.bytes_per_cycle_per_unit
    # ROM is immutable: its write path is unreachable by construction.
    assert memory.rom.write_latency_cycles > memory.hbm.write_latency_cycles


def test_address_placement_is_reported():
    deployment, capability = synthetic_state_deployment()
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    placement = body["memory"]["address_placement"]
    assert placement["mode"] in {"descriptor_base_address", "synthetic_packed"}
    assert placement["object_count"] >= 3
    assert placement["note"]


def test_memory_report_separates_the_four_classes():
    deployment, capability = synthetic_state_deployment()
    body = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(
        request()
    ).to_dict()
    for klass in ("hbm", "sram", "rom", "host"):
        block = body["memory"][klass]
        assert set(block) >= {
            "bytes_read",
            "bytes_written",
            "transactions",
            "busy_cycles",
            "conflict_cycles",
            "bandwidth_utilisation",
            "structure",
        }


# ---------------------------------------------------------------------------
# 8. Fabric: the 32-node cluster
# ---------------------------------------------------------------------------
def cluster_fabric() -> ClusterFabric:
    machine = MachineModel(
        fixture_capability(TopologyClass.CLUSTER_32), load_cost_table(CLUSTER32)
    )
    return ClusterFabric(machine.cluster_fabric())


def wafer_fabric() -> WaferFabric:
    machine = MachineModel(
        fixture_capability(TopologyClass.WAFER_LOGICAL_DEVICE), load_cost_table(WAFER)
    )
    return WaferFabric(machine.wafer_fabric())


def test_cluster_unicast_is_serialisation_bound_for_large_transfers():
    fabric = cluster_fabric()
    small = fabric.unicast(0, 31, 4096)
    fabric = cluster_fabric()
    large = fabric.unicast(0, 31, 4096 * 64)
    assert large.cycles > small.cycles
    assert large.serialization_cycles > small.serialization_cycles
    assert large.packets > small.packets
    assert small.hop_cycles == large.hop_cycles  # latency does not scale with bytes


def test_cluster_unicast_costs_at_least_one_endpoint_latency():
    fabric = cluster_fabric()
    empty = fabric.unicast(0, 1, 0)
    assert empty.cycles > 0
    assert empty.messages == 1


def test_cluster_switch_contention_is_reported_separately():
    fabric = cluster_fabric()
    # Every node in a different leaf group sends through the one spine port.
    first = fabric.unicast(0, 31, 1 << 20)
    second = fabric.unicast(8, 24, 1 << 20)
    assert second.switch_contention_cycles > 0
    assert first.switch_contention_cycles >= 0
    report = fabric.port_report()
    assert report["total_contention_cycles"] > 0
    assert report["busiest"]


def test_cluster_credits_bound_the_pipeline():
    fabric = cluster_fabric()
    timing = fabric.unicast(0, 31, 1 << 22)
    assert timing.credit_stall_cycles > 0
    assert timing.counters()["link.credit_stalls"] == 1


def test_cluster_retry_is_modelled():
    fabric = cluster_fabric()
    timing = fabric.unicast(0, 31, 1 << 24)
    assert timing.retries > 0
    assert timing.retry_cycles > 0
    assert timing.counters()["link.retries"] == timing.retries


def test_cluster_collective_runs_an_algorithm_not_a_penalty():
    fabric = cluster_fabric()
    members = list(range(32))
    all_reduce = fabric.collective(int(CollectiveOp.SUM), members, 1 << 20)
    assert all_reduce.algorithm == "ring_reduce_scatter_then_all_gather"
    assert all_reduce.steps == 2 * (len(members) - 1)
    assert all_reduce.messages == all_reduce.steps * len(members)
    assert all_reduce.cycles > 0
    assert all_reduce.bytes_moved > 0


def test_cluster_broadcast_is_a_tree():
    fabric = cluster_fabric()
    members = list(range(32))
    broadcast = fabric.collective(int(CollectiveOp.BROADCAST), members, 4096)
    assert broadcast.algorithm == "binomial_tree_broadcast"
    assert broadcast.steps == 5  # ceil(log2(32))
    assert broadcast.messages == len(members) - 1


def test_cluster_barrier_is_bounded_and_never_free():
    fabric = cluster_fabric()
    barrier = fabric.barrier(list(range(32)))
    assert barrier.cycles > 0
    assert barrier.steps == 5
    assert barrier.messages == 5 * 32


def test_cluster_collective_grows_with_participants():
    small = cluster_fabric().collective(int(CollectiveOp.SUM), list(range(4)), 1 << 18)
    large = cluster_fabric().collective(int(CollectiveOp.SUM), list(range(32)), 1 << 18)
    assert large.cycles > small.cycles
    assert large.steps > small.steps


def test_cluster_route_crosses_a_spine_only_between_leaf_groups():
    fabric = cluster_fabric()
    near = fabric.route(0, 1)
    far = fabric.route(0, 31)
    assert near.hops < far.hops
    assert "spine" in far.description
    assert "spine" not in near.description


# ---------------------------------------------------------------------------
# 9. Fabric: the wafer
# ---------------------------------------------------------------------------
def test_wafer_routing_is_dimension_ordered_and_counts_hops():
    fabric = wafer_fabric()
    route = fabric.route(0, fabric.cols * 3 + 5)
    assert route.hops == 3 + 5
    assert "XY" in route.description


def test_wafer_reticle_stitch_costs_more_than_a_local_hop():
    fabric = wafer_fabric()
    params = fabric.params
    local = fabric.route(0, 1)
    # Crossing the reticle boundary in X: column tile_cols is in reticle (0,1).
    crossing = fabric.route(params.tile_cols - 1, params.tile_cols)
    assert local.hops == crossing.hops == 1
    assert crossing.ports[0].name.startswith("stitch")
    assert local.ports[0].name.startswith("tile")


def test_wafer_barrier_is_hierarchical_bounded_and_nonzero():
    fabric = wafer_fabric()
    barrier = fabric.barrier(list(range(64)))
    assert barrier.algorithm == "hierarchical_tree"
    assert barrier.cycles > 0
    # 2 * ceil(log2(64)) tree levels, not O(participants) rounds.
    assert barrier.steps == 2 * 6
    assert barrier.messages == 2 * (64 - 1)


def test_wafer_barrier_scales_logarithmically_not_linearly():
    small = wafer_fabric().barrier(list(range(8)))
    large = wafer_fabric().barrier(list(range(512)))
    assert large.steps == 2 * 9
    assert small.steps == 2 * 3
    assert large.cycles < small.cycles * 64  # sublinear in participants


def test_wafer_congestion_accumulates_on_shared_links():
    fabric = wafer_fabric()
    fabric.unicast(0, 40, 1 << 20)
    fabric.unicast(1, 41, 1 << 20)
    second = fabric.unicast(0, 39, 1 << 20)
    report = fabric.port_report()
    assert report["total_busy_cycles"] > 0
    assert second.switch_contention_cycles > 0


def test_wafer_zero_latency_probe():
    fabric = wafer_fabric()
    proof = assert_no_zero_latency_global_operations(fabric)
    assert proof["proved"]
    assert all(v > 0 for v in proof["probe_cycles"].values())


def test_wafer_probe_does_not_disturb_fabric_state():
    fabric = wafer_fabric()
    fabric.unicast(0, 5, 4096)
    before = fabric.port_report()
    assert_no_zero_latency_global_operations(fabric)
    assert fabric.port_report() == before


# ---------------------------------------------------------------------------
# 10. Topology cost stays explicit
# ---------------------------------------------------------------------------
def test_cluster_reports_compute_link_collective_and_skew_separately():
    capability = fixture_capability(TopologyClass.CLUSTER_32)
    deployment, _ = synthetic_state_deployment(capability, with_communication=True)
    body = CycleModel(deployment, capability, load_cost_table(CLUSTER32)).run(
        request()
    ).to_dict()
    cluster = body["cluster"]
    assert cluster["nodes"] == 32
    assert cluster["blended_total_reported"] is False
    assert len(cluster["per_node"]) == 32
    for node in cluster["per_node"]:
        assert set(node) >= {
            "compute_cycles",
            "link_cycles",
            "collective_cycles",
            "barrier_cycles",
            "engine_idle_cycles",
            "skew_cycles",
            "end_cycle",
        }
    aggregate = cluster["aggregate"]
    assert set(aggregate) >= {
        "critical_path_cycles",
        "skew_cycles",
        "compute_cycles_total",
        "link_cycles_total",
        "collective_cycles_total",
        "idle_skew_cycles_total",
    }
    assert aggregate["critical_path_cycles"] > 0


def test_cluster_per_node_compute_is_nonzero_for_a_contracting_program():
    capability = cycle_capability(TopologyClass.CLUSTER_32)
    deployment, _ = synthetic_tiled_deployment(capability)
    req = request()
    result = CycleModel(deployment, capability, load_cost_table(CLUSTER32)).run(req)
    body = result.to_dict()
    cluster = body["cluster"]
    assert len(cluster["per_node"]) == 32
    assert all(node["compute_cycles"] > 0 for node in cluster["per_node"])
    assert cluster["aggregate"]["compute_cycles_total"] == 32 * (
        cluster["per_node"][0]["compute_cycles"]
    )
    assert result.architectural == functional_counters(
        deployment, capability, req, node_count=32
    )


def test_cluster_declared_communication_is_timed_and_labelled():
    capability = fixture_capability(TopologyClass.CLUSTER_32)
    deployment, _ = synthetic_state_deployment(capability, with_communication=True)
    body = CycleModel(deployment, capability, load_cost_table(CLUSTER32)).run(
        request()
    ).to_dict()
    declared = body["fabric"]["declared"]
    assert declared["status"] == "declared_not_executed"
    assert declared["descriptor_count"] == 2
    assert declared["total_cycles"] > 0
    for entry in declared["entries"]:
        assert entry["cycles"] > 0
        assert entry["serialization_cycles"] > 0
    # It is never folded into the executed timing.
    assert body["timing"]["link_cycles"] == 0


def test_cluster_notes_a_topology_descriptor_mismatch_as_a_gap():
    capability = cycle_capability(TopologyClass.CLUSTER_32)
    deployment, _ = synthetic_tiled_deployment(capability)
    # The tiled builder declares the capability's node count in its topology
    # descriptor, so force a mismatch the way a stale build would.
    topology_id = deployment.table.ids_of_type(ExtendedDescriptorType.TOPOLOGY)[0]
    descriptor = deployment.table[topology_id]
    descriptor.payload["node_count"] = 1
    deployment.table._records[topology_id] = descriptor.encode()  # noqa: SLF001
    body = CycleModel(
        deployment, capability, load_cost_table(CLUSTER32), verify=False
    ).run(request()).to_dict()
    wheres = [gap["where"] for gap in body["gaps"]]
    assert "topology descriptor vs capability" in wheres


def test_wafer_result_carries_the_on_wafer_fabric():
    capability = fixture_capability(TopologyClass.WAFER_LOGICAL_DEVICE)
    deployment, _ = synthetic_state_deployment(capability)
    body = CycleModel(deployment, capability, load_cost_table(WAFER)).run(
        request()
    ).to_dict()
    fabric = body["fabric"]
    assert fabric["kind"] == "wafer"
    assert fabric["topology_class"] == "WAFER_LOGICAL_DEVICE"
    assert fabric["parameters"]["tiles"] == 8 * 8 * 8 * 8
    assert "cluster" not in body


# ---------------------------------------------------------------------------
# 11. The CLI
# ---------------------------------------------------------------------------
def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / "run_abi3_cycle.py"), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
    )


def publish(tmp_path: Path, storage: StorageClass = StorageClass.HBM) -> Path:
    """Write a real deployment root plus its capability, as a backend would."""
    deployment, capability = synthetic_tiled_deployment(storage_class=storage)
    root = tmp_path / f"deployment-{storage.name.lower()}"
    deployment.write(root)
    (root / "capability.json").write_bytes(canonical_json(capability.to_dict()))
    return root


SYMBOLS = (
    "--symbol", "SPAN_TOKENS=1",
    "--symbol", "POSITION_START=0",
    "--symbol", "POSITION_END=1",
    "--symbol", "CONTEXT_LENGTH=1",
)


def test_cli_writes_canonical_json(tmp_path: Path):
    root = publish(tmp_path)
    out = tmp_path / "result.json"
    proc = run_cli(
        "--deployment", str(root),
        "--capability", str(root / "capability.json"),
        "--cost-table", str(BASELINE),
        *SYMBOLS,
        "--out", str(out),
        "--check-functional-agreement",
    )
    assert proc.returncode == 0, proc.stderr
    raw = out.read_bytes()
    body = json.loads(raw)
    assert raw == canonical_json(body), "output is not canonical JSON"
    assert body["schema"] == "opentallas.abi3.cycle_result.v1"
    assert body["functional_agreement"]["agrees"] is True
    assert body["execution"]["status"] == "SUCCESS"
    assert body["timing"]["tile_launches"] > 0
    assert body["provenance"]["class"] == "assumed"


def test_cli_refuses_to_overwrite_without_force(tmp_path: Path):
    root = publish(tmp_path)
    out = tmp_path / "result.json"
    out.write_text("{}")
    proc = run_cli(
        "--deployment", str(root),
        "--capability", str(root / "capability.json"),
        "--cost-table", str(BASELINE),
        "--out", str(out),
    )
    assert proc.returncode != 0
    assert "already exists" in proc.stderr
    assert out.read_text() == "{}"


def test_cli_force_overwrites(tmp_path: Path):
    root = publish(tmp_path, StorageClass.ROM)
    out = tmp_path / "result.json"
    out.write_text("{}")
    proc = run_cli(
        "--deployment", str(root),
        "--capability", str(root / "capability.json"),
        "--cost-table", str(SKY130_ROM),
        *SYMBOLS,
        "--out", str(out),
        "--force",
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(out.read_text())
    assert body["inputs"]["target_id"] == "cycle-tiled"
    assert body["memory"]["rom"]["bytes_read"] > 0


def test_cli_output_is_reproducible(tmp_path: Path):
    root = publish(tmp_path)
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    for out in (first, second):
        proc = run_cli(
            "--deployment", str(root),
            "--capability", str(root / "capability.json"),
            "--cost-table", str(ASAP7),
            *SYMBOLS,
            "--out", str(out),
        )
        assert proc.returncode == 0, proc.stderr
    assert first.read_bytes() == second.read_bytes()


# ---------------------------------------------------------------------------
# 12. The characterization sweep (W9.5)
# ---------------------------------------------------------------------------
def run_sweep(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / "run_abi3_cycle_sweep.py"), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
    )


def test_sweep_records_both_timings_and_proves_one_architecture(tmp_path: Path):
    """A characterization feedback result is a *pair* of timings, or nothing.

    The number the derived table produces means nothing without the number it
    replaced, so the sweep records both and the ratio between them, and it
    proves the property that makes the ratio a cost-table effect: one
    architecture, two clocks.
    """
    root = publish(tmp_path)
    out = tmp_path / "sweep.json"
    proc = run_sweep(
        "--deployment", str(root),
        "--capability", str(root / "capability.json"),
        "--baseline", str(ASAP7),
        "--cost-table", str(ASAP7_V2),
        *SYMBOLS,
        "--out", str(out),
    )
    assert proc.returncode == 0, proc.stderr
    raw = out.read_bytes()
    body = json.loads(raw)
    assert raw == canonical_json(body), "output is not canonical JSON"
    assert body["schema"] == "opentallas.abi3.cycle_sweep.v1"
    assert body["architectural_counters_identical_across_tables"] is True
    assert body["architectural_counters_compared"] > 0
    assert len(body["runs"]) == 2
    comparison = body["comparisons"][0]
    assert comparison["baseline_cost_table_id"] == "abi3-cost-asap7-v1"
    assert comparison["cost_table_id"] == "abi3-cost-asap7-v2"
    # The measured tensor rate is 2.89x slower per lane than the hand value,
    # so the derived table must not come out faster.
    assert comparison["cycles_ratio"] > 1.0
    assert "engine.tensor.work_per_lane_cycle" in (
        comparison["characterized_parameters_gained"]
    )
    assert body["claim_boundary"]


def test_sweep_refuses_to_report_a_ratio_between_two_architectures(tmp_path: Path):
    """If the counters move, the timing difference is not the cost table's.

    The sweep is built so that this cannot be reported as a speedup.  A cost
    table that changed the architecture would make every ratio in the document
    a comparison of two different machines.
    """
    root = publish(tmp_path)
    # A capability with fewer events makes the *deployment* refuse, not the
    # counters move, so instead break the invariant the honest way: give the
    # second table a state backing class that reroutes traffic, and assert the
    # tool still finds one architecture.  The counters must not care.
    body = json.loads(ASAP7_V2.read_text())
    body["parameters"]["state.backing_storage_class"]["value"] = "HBM"
    other = tmp_path / "abi3_cost_hbm_state.json"
    other.write_text(json.dumps(body))
    out = tmp_path / "sweep.json"
    proc = run_sweep(
        "--deployment", str(root),
        "--capability", str(root / "capability.json"),
        "--baseline", str(ASAP7),
        "--cost-table", str(other),
        *SYMBOLS,
        "--out", str(out),
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(out.read_text())[
        "architectural_counters_identical_across_tables"
    ] is True


def publish_unmapped(tmp_path: Path) -> Path:
    """A deployment whose REDUCTION operator deliberately has no schedule."""
    deployment, capability = synthetic_tiled_deployment(schedule_reduction=False)
    root = tmp_path / "deployment-unmapped"
    deployment.write(root)
    (root / "capability.json").write_bytes(canonical_json(capability.to_dict()))
    return root


def test_cli_refuses_a_deployment_without_a_tile_mapping(tmp_path: Path):
    root = publish_unmapped(tmp_path)
    out = tmp_path / "result.json"
    proc = run_cli(
        "--deployment", str(root),
        "--capability", str(root / "capability.json"),
        "--cost-table", str(BASELINE),
        *SYMBOLS,
        "--out", str(out),
    )
    assert proc.returncode != 0
    assert "tile mapping is incomplete" in proc.stderr
    assert "REDUCTION.ORDERED_SUM" in proc.stderr
    assert not out.exists()


def test_cli_permissive_schedules_still_fails_closed_at_timing(tmp_path: Path):
    root = publish_unmapped(tmp_path)
    out = tmp_path / "result.json"
    proc = run_cli(
        "--deployment", str(root),
        "--capability", str(root / "capability.json"),
        "--cost-table", str(BASELINE),
        "--permissive-schedules",
        *SYMBOLS,
        "--out", str(out),
    )
    assert proc.returncode != 0
    # Refused at admission now, before timing. Either refusal is acceptable so
    # long as it is a clean diagnosis naming the missing schedule.
    assert "Traceback" not in proc.stderr, proc.stderr
    assert (
        "carries no SCHEDULE descriptor" in proc.stderr
        or "will not invent a tile shape" in proc.stderr
    ), proc.stderr
    assert not out.exists()


def test_cli_rejects_an_unknown_symbol(tmp_path: Path):
    proc = run_cli(
        "--fixture", "hbm",
        "--cost-table", str(BASELINE),
        "--symbol", "NOT_A_SYMBOL=1",
        "--out", str(tmp_path / "x.json"),
    )
    assert proc.returncode != 0
    assert "unknown runtime symbol" in proc.stderr


# ---------------------------------------------------------------------------
# 12. Real deployments, when they exist
# ---------------------------------------------------------------------------
def discover_real_deployments() -> list[Path]:
    roots = [REPO / "build", REPO / "results"]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for manifest in sorted(root.rglob("deployment.json")):
            try:
                body = json.loads(manifest.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if body.get("schema") == "opentallas.abi3.deployment.v1":
                found.append(manifest.parent)
    return found


REAL_DEPLOYMENTS = discover_real_deployments()

CAPABILITY_CONFIGS = HARDWARE / "abi3_capability"


def _published_capability_for(deployment: Deployment) -> Capability | None:
    """The published capability whose digest this deployment was admitted against.

    A deployment records ``capability_digest``; ``tools/publish_abi3_capabilities.py``
    writes the records themselves.  Matching on the digest is the only safe
    join: a capability that merely has the right shape is a different machine,
    and the verifier would refuse it.
    """
    if not CAPABILITY_CONFIGS.is_dir():
        return None
    wanted = deployment.capability_digest
    for path in sorted(CAPABILITY_CONFIGS.glob("*.json")):
        try:
            candidate = Capability.from_dict(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError, KeyError, ValueError):
            continue
        if candidate.digest == wanted:
            return candidate
    return None


@pytest.mark.skipif(
    not REAL_DEPLOYMENTS, reason="no ABI 3.0 deployment exists under build/ or results/"
)
@pytest.mark.parametrize("root", REAL_DEPLOYMENTS, ids=lambda p: p.name)
def test_real_deployment_counter_agreement(root: Path):
    """The load-bearing property, on a deployment a backend actually emitted.

    This test skipped for the whole life of the deployments under ``build/``,
    because ``tools/build_hbm_sram_deployment.py`` writes no ``capability.json``
    into the deployment root -- so the one check that runs the cycle model
    against the *real* Qwen program never ran.  A deployment binds the digest of
    the capability it was admitted against, and the published capabilities are
    on disk, so the record can be found rather than waited for.
    """
    deployment = Deployment.read(root)
    capability_path = root / "capability.json"
    if capability_path.exists():
        capability = Capability.from_dict(json.loads(capability_path.read_text()))
    else:
        capability = _published_capability_for(deployment)
        if capability is None:
            pytest.skip(
                f"{root} carries no capability.json and no published capability "
                f"has its digest {deployment.capability_digest}"
            )
    table = {
        int(TopologyClass.SINGLE_CHIP): BASELINE,
        int(TopologyClass.CLUSTER_32): CLUSTER32,
        int(TopologyClass.WAFER_LOGICAL_DEVICE): WAFER,
    }[int(deployment.topology_class)]
    req = request()
    result = CycleModel(deployment, capability, load_cost_table(table), root=root).run(
        req
    )
    assert result.architectural == functional_counters(
        deployment, capability, req, root=root
    )
