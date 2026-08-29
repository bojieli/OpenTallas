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
from runtime.abi3.descriptors import CollectiveOp, Phase, SelectionMode, Symbol
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

SHIPPED_TABLES = [BASELINE, ASAP7, SKY130_ROM, CLUSTER32, WAFER]

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
    builder.emit(
        Major.STATE, State.PREPARE, descriptor_id=state, signal_event_id=prepare_event
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
        wait_set_id=builder.wait_set([prepare_event], key="wait.prepare"),
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

    matmul_numeric = builder.numeric(
        contract="bf16_bf16_fp32_blocked_rne_v1",
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

    builder.emit(Major.STATE, State.PREPARE, descriptor_id=kv_state)
    matmul_event = builder.new_event()
    builder.emit(
        Major.TENSOR,
        Tensor.MATMUL,
        descriptor_id=matmul_op,
        signal_event_id=matmul_event,
        source_operation_id=0,
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
@pytest.mark.parametrize("storage", [StorageClass.HBM, StorageClass.ROM])
def test_fixture_counter_agreement(storage: StorageClass):
    capability = fixture_capability()
    deployment = build_fixture(storage_class=storage, capability=capability)
    req = request()
    model = CycleModel(deployment, capability, load_cost_table(BASELINE))
    result = model.run(req)
    reference = functional_counters(deployment, capability, req)
    assert result.architectural == reference
    assert reference, "the fixture must produce at least one architectural counter"


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
    assert counters["state.bytes_written"] == ROW_ELEMS * 2
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


def test_link_trap_agreement():
    """Both models must fail the same way on an unimplemented engine."""
    deployment, capability = synthetic_link_deployment()
    req = request()
    model = CycleModel(deployment, capability, load_cost_table(CLUSTER32))
    result = model.run(req)
    body = result.to_dict()
    assert body["execution"]["status"] == "FAILED"
    assert body["execution"]["trap_class"] == "CAPABILITY_OR_RESOURCE"
    assert result.architectural == functional_counters(deployment, capability, req)


def test_agreement_holds_across_cost_tables():
    """Two machines, one architecture: only the timing may differ."""
    deployment, capability = synthetic_state_deployment()
    req = request()
    first = CycleModel(deployment, capability, load_cost_table(BASELINE)).run(req)
    second = CycleModel(deployment, capability, load_cost_table(ASAP7)).run(req)
    assert first.architectural == second.architectural
    assert first.to_dict()["timing"]["seconds"] != second.to_dict()["timing"]["seconds"]


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
    assert proof["dependency_edges"] == 2


def test_acyclic_waits_proof_catches_a_wait_on_a_later_signal():
    """The verifier admits this program; the cycle model's proof rejects it.

    ``runtime/abi3/verifier.py`` only checks that *some* instruction signals the
    event.  On an in-order microsequencer that is not enough: waiting on an
    event signalled later is a deadlock, and the cycle model must say so.
    """
    deployment, capability = backward_wait_deployment()
    assert verify_deployment(deployment, capability).admitted
    device = Device(deployment, capability)
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
    # The atomic commit reads the prepared extent and writes the committed one.
    assert memory["sram"]["bytes_read"] == ROW_ELEMS * 2
    assert memory["sram"]["bytes_written"] == ROW_ELEMS * 2
    assert memory["sram"]["transactions"] >= 2
    assert memory["sram"]["busy_cycles"] > 0


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
            "idle_cycles",
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
    capability = fixture_capability(TopologyClass.CLUSTER_32)
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    body = CycleModel(deployment, capability, load_cost_table(CLUSTER32)).run(
        request()
    ).to_dict()
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


def test_cli_writes_canonical_json(tmp_path: Path):
    out = tmp_path / "result.json"
    proc = run_cli(
        "--fixture", "hbm",
        "--cost-table", str(BASELINE),
        "--symbol", "SPAN_TOKENS=1",
        "--symbol", "POSITION_END=1",
        "--out", str(out),
        "--check-functional-agreement",
    )
    assert proc.returncode == 0, proc.stderr
    raw = out.read_bytes()
    body = json.loads(raw)
    assert raw == canonical_json(body), "output is not canonical JSON"
    assert body["schema"] == "opentallas.abi3.cycle_result.v1"
    assert body["functional_agreement"]["agrees"] is True
    assert body["provenance"]["class"] == "assumed"


def test_cli_refuses_to_overwrite_without_force(tmp_path: Path):
    out = tmp_path / "result.json"
    out.write_text("{}")
    proc = run_cli(
        "--fixture", "hbm", "--cost-table", str(BASELINE), "--out", str(out)
    )
    assert proc.returncode != 0
    assert "already exists" in proc.stderr
    assert out.read_text() == "{}"


def test_cli_force_overwrites(tmp_path: Path):
    out = tmp_path / "result.json"
    out.write_text("{}")
    proc = run_cli(
        "--fixture", "rom",
        "--cost-table", str(SKY130_ROM),
        "--out", str(out),
        "--force",
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(out.read_text())["inputs"]["target_id"] == "fixture-rom"


def test_cli_output_is_reproducible(tmp_path: Path):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    for out in (first, second):
        proc = run_cli(
            "--fixture", "hbm",
            "--cost-table", str(ASAP7),
            "--symbol", "SPAN_TOKENS=1",
            "--out", str(out),
        )
        assert proc.returncode == 0, proc.stderr
    assert first.read_bytes() == second.read_bytes()


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


@pytest.mark.skipif(
    not REAL_DEPLOYMENTS, reason="no ABI 3.0 deployment exists under build/ or results/"
)
@pytest.mark.parametrize("root", REAL_DEPLOYMENTS, ids=lambda p: p.name)
def test_real_deployment_counter_agreement(root: Path):
    deployment = Deployment.read(root)
    capability_path = root / "capability.json"
    if not capability_path.exists():
        pytest.skip(f"{root} carries no capability.json")
    capability = Capability.from_dict(json.loads(capability_path.read_text()))
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
