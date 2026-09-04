"""Focused correctness-bound timing tests for shared ABI 3.0 batches."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from runtime.abi3.builder import DeploymentBuilder, DynamicTerm
from runtime.abi3.constants import (
    Control,
    DType,
    Dma,
    Feature,
    HostOpcode,
    Link,
    Major,
    ParticipantScope,
    Permission,
    Selection,
    StorageClass,
    SubmissionFlag,
    TopologyClass,
    Vector,
)
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import CollectiveOp, Phase, SelectionMode, Symbol
from runtime.abi3.fixture import fixture_capability
from runtime.abi3.records import EosReason, Submission
from runtime.abi3.request import RequestSymbolDescriptor
from runtime.cycle.batch import CycleBatchScheduler, TimingBindingError
from runtime.cycle.machine import load_cost_table
from runtime.cycle.model import CycleModel
from runtime.sim.batch import BatchError, BatchLaneSubmission
from runtime.sim.engines import load_engines


REPO = Path(__file__).resolve().parents[2]
BASELINE = REPO / "configs" / "hardware" / "abi3_cost_baseline_v1.json"
CLUSTER = REPO / "configs" / "hardware" / "abi3_cost_cluster32_v1.json"
VOCABULARY = 4
VECTOR_ELEMENTS = 4096


def _deployment(
    *,
    topology: TopologyClass = TopologyClass.SINGLE_CHIP,
    max_sessions: int = 8,
    with_link: bool = False,
):
    capability = fixture_capability(topology)
    capability.limits = {**capability.limits, "max_sessions": max_sessions}
    if with_link:
        capability.features = tuple(
            sorted({*capability.features, int(Feature.INTEGRITY_RETRY)})
        )
    capability.validate()
    builder = DeploymentBuilder(
        target_id="abi3-cycle-batch-fixture",
        model_id="abi3-cycle-batch-fixture",
        backend="cycle-batch-test",
        capability=capability,
    )
    builder.topology(
        topology_class=topology,
        node_count=capability.limits["max_nodes"],
        hbm_bytes_per_node=capability.memory["hbm"]["bytes"],
        sram_bytes_per_node=capability.memory["sram"]["bytes"],
        key="topology",
    )

    hbm_a = builder.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=VECTOR_ELEMENTS * 2,
        source=ObjectSource.zeros(VECTOR_ELEMENTS * 2),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
        key="obj.hbm.a",
    )
    hbm_b = builder.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=VECTOR_ELEMENTS * 2,
        source=ObjectSource.zeros(VECTOR_ELEMENTS * 2),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
        key="obj.hbm.b",
    )
    dma_output = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=VECTOR_ELEMENTS * 2,
        source=ObjectSource.zeros(VECTOR_ELEMENTS * 2),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.sram.dma",
    )
    vector_output = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=VECTOR_ELEMENTS * 2,
        source=ObjectSource.zeros(VECTOR_ELEMENTS * 2),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.sram.vector",
    )
    logits = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=VOCABULARY * 4,
        source=ObjectSource.zeros(VOCABULARY * 4),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.logits",
    )
    tokens = builder.memory_object(
        storage_class=StorageClass.HOST,
        size_bytes=(1 + capability.limits["max_context_positions"]) * 4,
        source=ObjectSource.zeros(
            (1 + capability.limits["max_context_positions"]) * 4
        ),
        permissions=int(Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE),
        key="obj.tokens",
    )

    a_view = builder.tensor_view(
        object_id=hbm_a, dtype=DType.BF16, dims=[VECTOR_ELEMENTS], key="view.a"
    )
    b_view = builder.tensor_view(
        object_id=hbm_b, dtype=DType.BF16, dims=[VECTOR_ELEMENTS], key="view.b"
    )
    dma_view = builder.tensor_view(
        object_id=dma_output,
        dtype=DType.BF16,
        dims=[VECTOR_ELEMENTS],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.dma",
    )
    vector_view = builder.tensor_view(
        object_id=vector_output,
        dtype=DType.BF16,
        dims=[VECTOR_ELEMENTS],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.vector",
    )
    logits_view = builder.tensor_view(
        object_id=logits,
        dtype=DType.FP32,
        dims=[VOCABULARY],
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

    vector_numeric = builder.numeric(
        contract="bf16_add_rne_v1",
        input_dtype=DType.BF16,
        second_input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        accumulator_dtype=DType.FP32,
        key="numeric.vector",
    )
    selection_numeric = builder.numeric(
        contract="exact_index_select_v1",
        input_dtype=DType.FP32,
        output_dtype=DType.U32,
        accumulator_dtype=DType.FP32,
        key="numeric.selection",
    )
    dma_schedule = builder.schedule(
        engine_family=Major.DMA,
        tile_rows=1,
        tile_cols=VECTOR_ELEMENTS,
        tile_depth=1,
        max_outstanding=1,
        issue_window=2,
        bank_mask=1,
        port_mask=1,
        key="schedule.dma",
    )
    vector_schedule = builder.schedule(
        engine_family=Major.VECTOR,
        tile_rows=1,
        tile_cols=VECTOR_ELEMENTS,
        tile_depth=1,
        max_outstanding=1,
        issue_window=2,
        bank_mask=1,
        port_mask=1,
        key="schedule.vector",
    )
    selection_schedule = builder.schedule(
        engine_family=Major.SELECTION,
        tile_rows=1,
        tile_cols=VOCABULARY,
        tile_depth=1,
        max_outstanding=1,
        issue_window=2,
        bank_mask=1,
        port_mask=1,
        key="schedule.selection",
    )
    dma = builder.operator(
        engine_family=Major.DMA,
        engine_sub=Dma.TRANSFER,
        inputs=[a_view],
        outputs=[dma_view],
        schedule_id=dma_schedule,
        source_kernel_id=0,
        key="op.dma",
    )
    add = builder.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.ADD,
        inputs=[a_view, b_view],
        outputs=[vector_view],
        numeric_profile_id=vector_numeric,
        schedule_id=vector_schedule,
        source_kernel_id=1,
        key="op.add",
    )
    argmax = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.ARGMAX,
        inputs=[logits_view],
        outputs=[selected_view],
        numeric_profile_id=selection_numeric,
        schedule_id=selection_schedule,
        source_kernel_id=2,
        key="op.argmax",
    )
    append = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.TOKEN_APPEND,
        inputs=[selected_view],
        outputs=[ring_view],
        numeric_profile_id=selection_numeric,
        schedule_id=selection_schedule,
        source_kernel_id=3,
        key="op.append",
    )
    policy = builder.generation_policy(
        eos_token_ids=[VOCABULARY - 1],
        max_new_tokens=8,
        vocabulary_size=VOCABULARY,
        token_ring_object_id=tokens,
        selection_mode=SelectionMode.GREEDY_ARGMAX_LOWEST_ID,
        key="policy",
    )

    ragged = builder.loop_control(
        lower_bound=0,
        upper_bound=0,
        step=1,
        max_iterations=8,
        bound_symbol=Symbol.SPAN_TOKENS,
        key="loop.ragged",
    )
    builder.open_loop(ragged)
    builder.emit(Major.CONTROL, Control.NOP)
    builder.close_loop()
    builder.emit(Major.DMA, Dma.TRANSFER, descriptor_id=dma)
    builder.emit(Major.VECTOR, Vector.ADD, descriptor_id=add)

    if with_link:
        builder.require(Feature.INTER_CHIP_ENDPOINT)
        exchange = builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=capability.limits["max_nodes"] * 64,
            source=ObjectSource.zeros(capability.limits["max_nodes"] * 64),
            permissions=int(Permission.READ | Permission.WRITE | Permission.REMOTE),
            key="obj.exchange",
        )
        communication = builder.communication(
            collective_op=CollectiveOp.SUM,
            local_object_id=exchange,
            remote_object_id=exchange,
            byte_extent=0,
            participant_count=capability.limits["max_nodes"],
            participant_scope=ParticipantScope.NODE,
            key="comm.barrier",
        )
        builder.emit(Major.LINK, Link.BARRIER, descriptor_id=communication)

    builder.emit(Major.SELECTION, Selection.ARGMAX, descriptor_id=argmax)
    builder.emit(Major.SELECTION, Selection.TOKEN_APPEND, descriptor_id=append)
    builder.emit(Major.CONTROL, Control.COMPLETE)
    builder.entrypoint(
        entrypoint_id=0,
        first_instruction=0,
        phase=Phase.DECODE,
        generation_policy_id=policy,
    )
    builder.source_identity = {"fixture": "abi3-cycle-batch-v1"}
    return builder.finish(), capability, logits, policy


def _lane(
    scheduler: CycleBatchScheduler,
    lane_index: int,
    transaction_id: int,
    policy_id: int,
    *,
    span: int,
) -> BatchLaneSubmission:
    session = scheduler.sessions[lane_index]
    descriptor_id = scheduler.device.next_request_descriptor_id
    position_start = session.position
    symbols = {
        int(Symbol.SPAN_TOKENS): span,
        int(Symbol.POSITION_START): position_start,
        int(Symbol.POSITION_END): position_start + span,
        int(Symbol.CONTEXT_LENGTH): position_start + span,
        int(Symbol.PHASE): int(Phase.DECODE),
        int(Symbol.GENERATION_INDEX): len(session.generated),
        int(Symbol.MAX_NEW_TOKENS): 8,
        int(Symbol.BATCH): scheduler.batch_size,
        int(Symbol.NODE_ID): 0,
        int(Symbol.NODE_COUNT): scheduler.device.node_count,
        int(Symbol.ACTIVE_EXPERT_COUNT): 0,
        int(Symbol.SPARSE_INDEX_COUNT): 0,
        int(Symbol.LAYER_COUNT): 0,
        int(Symbol.VOCABULARY_PARTITIONS): 1,
        int(Symbol.SPAN_LAST_INDEX): span - 1,
    }
    descriptor = RequestSymbolDescriptor.from_symbols(
        request_descriptor_id=descriptor_id,
        deployment_id=scheduler.device.deployment.deployment_id,
        deployment_generation=scheduler.device.deployment.generation,
        session_id=session.session_id,
        session_generation=session.generation,
        transaction_id=transaction_id,
        symbols=symbols,
    )
    scheduler.device.register_request_descriptor(descriptor.encode())
    submission = Submission(
        host_opcode=int(HostOpcode.GENERATE),
        deployment_id=scheduler.device.deployment.deployment_id,
        deployment_generation=scheduler.device.deployment.generation,
        session_id=session.session_id,
        session_generation=session.generation,
        request_descriptor_id=descriptor_id,
        transaction_id=transaction_id,
        idempotency_key=hashlib.sha256(
            f"{session.session_id}:{session.generation}:{transaction_id}".encode()
        ).digest()[:16],
        entrypoint_id=0,
        generation_policy_id=policy_id,
        flags=int(SubmissionFlag.DECODE_PHASE),
    )
    return BatchLaneSubmission(lane_index=lane_index, record=submission.encode())


def _stage_token(
    scheduler: CycleBatchScheduler, logits: int, lane: int, token: int
) -> None:
    values = np.zeros(VOCABULARY, dtype=np.float32)
    values[token] = 9.0
    scheduler.stage_host_bytes(lane, logits, 0, values.tobytes())


def _scheduler(batch_size: int, *, cluster: bool = False):
    topology = TopologyClass.CLUSTER_32 if cluster else TopologyClass.SINGLE_CHIP
    deployment, capability, logits, policy = _deployment(
        topology=topology,
        max_sessions=max(batch_size, 2),
        with_link=cluster,
    )
    table = load_cost_table(CLUSTER if cluster else BASELINE)
    model = CycleModel(deployment, capability, table)
    return CycleBatchScheduler(model, batch_size), logits, policy


@pytest.mark.parametrize("batch_size", [1, 2, 4, 8])
def test_genuine_batch_sizes_preserve_exact_tokens_and_block_fixture_tpot(
    batch_size: int,
) -> None:
    load_engines()
    scheduler, logits, policy = _scheduler(batch_size)
    for lane in range(batch_size):
        _stage_token(scheduler, logits, lane, VOCABULARY - 1)
    wave = scheduler.submit_wave(
        [
            _lane(scheduler, lane, 100 + lane, policy, span=lane + 1)
            for lane in range(batch_size)
        ]
    )

    assert [lane.result.produced_tokens for lane in wave.lanes] == [
        (VOCABULARY - 1,)
    ] * batch_size
    assert all(
        lane.completion.completion_timestamp > lane.result.retired
        for lane in wave.lanes
    )
    evidence = scheduler.evidence(
        [[VOCABULARY - 1]] * batch_size,
        expected_eos_reasons=[EosReason.OFFICIAL_EOS] * batch_size,
        full_model_execution=False,
    )
    assert evidence["physical_batch_size"] == batch_size
    assert evidence["claim_boundary"]["engine_coissue_implemented"] is True
    assert evidence["claim_boundary"]["shared_resource_cycle_timing_implemented"] is True
    assert evidence["claim_boundary"]["functional_tokens_changed_by_timing_replay"] is False
    assert evidence["acceptance_gates"]["gate1_correctness"]["exact_token_equality"]
    assert evidence["acceptance_gates"]["gate1_correctness"]["exact_eos_equality"]
    assert evidence["acceptance_gates"]["gate1_correctness"]["status"] == (
        "not_qualified"
    )
    assert evidence["claim_boundary"]["eligible_for_full_model_token_correctness_gate"] is False
    assert evidence["claim_boundary"]["eligible_for_target_tpot"] is False
    assert len(evidence["timing"]["records"]) == batch_size
    if batch_size == 1:
        assert scheduler.batch_execution_id is None
    else:
        assert scheduler.batch_execution_id is not None


def test_ragged_lanes_share_engines_memory_and_monotonic_token_commits() -> None:
    load_engines()
    scheduler, logits, policy = _scheduler(2)
    for lane, token in enumerate((1, 2)):
        _stage_token(scheduler, logits, lane, token)
    first = scheduler.submit_wave(
        [
            _lane(scheduler, 0, 10, policy, span=1),
            _lane(scheduler, 1, 11, policy, span=4),
        ]
    )
    assert [len(trace.steps) for trace in scheduler.device.transaction_traces] == [
        8,
        14,
    ]
    for lane in range(2):
        _stage_token(scheduler, logits, lane, VOCABULARY - 1)
    second = scheduler.submit_wave(
        [
            _lane(scheduler, 0, 12, policy, span=2),
            _lane(scheduler, 1, 13, policy, span=5),
        ]
    )

    assert [lane.result.produced_tokens for lane in first.lanes] == [(1,), (2,)]
    assert [lane.result.produced_tokens for lane in second.lanes] == [(3,), (3,)]
    evidence = scheduler.evidence(
        [[1, 3], [2, 3]],
        expected_eos_reasons=[EosReason.OFFICIAL_EOS] * 2,
    )
    node = evidence["timing"]["shared_resources"]["nodes"][0]
    assert node["scheduler"]["cross_lane_transitions"] > 0
    assert node["scheduler"]["cross_lane_overlap_events"] > 0
    assert node["queues"]["selection.0"]["credit_stall_cycles"] > 0
    assert node["memory"]["hbm"]["conflict_cycles"] > 0
    assert node["memory"]["sram"]["conflict_cycles"] > 0
    assert evidence["timing"]["performance"]["distribution"]["sample_count"] == 2
    assert [
        sequence["generated_token_count"]
        for sequence in evidence["timing"]["performance"]["sequences"]
    ] == [2, 2]
    for sequence in evidence["sequences"]:
        assert sequence["no_post_eos_transaction"]
        assert sequence["token_commit_ticks"][1] > sequence["token_commit_ticks"][0]
    with pytest.raises(BatchError, match="all batch lanes are retired"):
        scheduler.submit_wave([])


def test_heterogeneous_batch_retires_eos_lane_without_stalling_live_lane() -> None:
    load_engines()
    scheduler, logits, policy = _scheduler(2)
    _stage_token(scheduler, logits, 0, VOCABULARY - 1)
    _stage_token(scheduler, logits, 1, 1)
    first = scheduler.submit_wave(
        [
            _lane(scheduler, 0, 40, policy, span=1),
            _lane(scheduler, 1, 41, policy, span=4),
        ]
    )
    assert first.active_mask_after == (False, True)

    _stage_token(scheduler, logits, 1, VOCABULARY - 1)
    second = scheduler.submit_wave(
        [_lane(scheduler, 1, 42, policy, span=2)]
    )
    assert second.active_mask_before == (False, True)
    assert second.active_mask_after == (False, False)

    evidence = scheduler.evidence(
        [[VOCABULARY - 1], [1, VOCABULARY - 1]],
        expected_eos_reasons=[EosReason.OFFICIAL_EOS] * 2,
    )
    timelines = evidence["timing"]["performance"]["sequences"]
    assert [row["token_commit_ticks"] for row in timelines] == [
        [first.lanes[0].completion.completion_timestamp],
        [
            first.lanes[1].completion.completion_timestamp,
            second.lanes[0].completion.completion_timestamp,
        ],
    ]
    assert all(row["request_start_tick"] is not None for row in timelines)
    assert all(sequence["no_post_eos_transaction"] for sequence in evidence["sequences"])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda record: replace(record, session_id=record.session_id + 1),
        lambda record: replace(record, transaction_id=record.transaction_id + 1),
        lambda record: replace(record, lane_index=record.lane_index + 1),
        lambda record: replace(record, produced_token_id=0),
        lambda record: replace(record, eos_reason=EosReason.NONE),
        lambda record: replace(record, submission_digest="0" * 64),
        lambda record: replace(record, token_commit_tick=record.token_commit_tick + 1),
    ],
)
def test_any_timing_binding_mutation_is_rejected(mutation) -> None:
    load_engines()
    scheduler, logits, policy = _scheduler(1)
    _stage_token(scheduler, logits, 0, VOCABULARY - 1)
    scheduler.submit_wave([_lane(scheduler, 0, 20, policy, span=1)])
    record = scheduler.timing_records[0]
    scheduler.verify_timing_record(record)
    with pytest.raises(TimingBindingError):
        scheduler.verify_timing_record(mutation(record))


def test_cluster_lanes_contend_on_one_physical_fabric() -> None:
    load_engines()
    scheduler, logits, policy = _scheduler(2, cluster=True)
    for lane in range(2):
        _stage_token(scheduler, logits, lane, VOCABULARY - 1)
    scheduler.submit_wave(
        [
            _lane(scheduler, 0, 30, policy, span=1),
            _lane(scheduler, 1, 31, policy, span=2),
        ]
    )
    evidence = scheduler.evidence(
        [[3], [3]],
        expected_eos_reasons=[EosReason.OFFICIAL_EOS] * 2,
    )
    fabric = evidence["timing"]["shared_resources"]["fabric"]
    assert fabric["kind"] == "cluster"
    assert fabric["ports"]["total_busy_cycles"] > 0
    assert fabric["ports"]["total_contention_cycles"] > 0
    assert evidence["timing"]["shared_resources"]["node_count"] == 32
