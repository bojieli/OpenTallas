"""Focused correctness-bound timing tests for shared ABI 3.0 batches."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from runtime.abi3.builder import DeploymentBuilder, DynamicTerm
from runtime.abi3.capability import digest_of
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
from runtime.cycle.governed import (
    GovernedTimingExportError,
    RELEASE_FILE_DIGEST_FIELD,
    RELEASE_SEMANTIC_DIGEST_FIELD,
    publish_governed_target_timing_trace,
)
from runtime.cycle.machine import load_cost_table
from runtime.cycle.model import CycleModel
from runtime.driver import BatchGenerationDriver, BatchGenerationRequest
from runtime.sim.batch import BatchError, BatchLaneSubmission
from runtime.sim.engines import load_engines
from abi3_comparison_contract_support import (
    make_locked_repository,
    policy_identity,
    sha256_file,
    write_json,
)
from tools.abi3_comparison_boundary import validate_comparison_contract
from tools.freeze_abi3_execution_release import build_release_lock


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
    max_context_positions: int = 64,
    max_new_tokens: int = 8,
    target_id: str = "abi3-cycle-batch-fixture",
    model_id: str = "abi3-cycle-batch-fixture",
    backend: str = "cycle-batch-test",
    graph_id: str | None = None,
    with_prefill: bool = False,
    vocabulary: int = VOCABULARY,
    technology_view: str = "fixture",
):
    capability = fixture_capability(topology)
    capability.technology_view = technology_view
    capability.limits = {
        **capability.limits,
        "max_sessions": max_sessions,
        "max_context_positions": max_context_positions,
    }
    if with_link:
        capability.features = tuple(
            sorted({*capability.features, int(Feature.INTEGRITY_RETRY)})
        )
    capability.validate()
    builder = DeploymentBuilder(
        target_id=target_id,
        model_id=model_id,
        backend=backend,
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
        size_bytes=vocabulary * 4,
        source=ObjectSource.zeros(vocabulary * 4),
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
        dims=[vocabulary],
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
        tile_cols=vocabulary,
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
        eos_token_ids=[vocabulary - 1],
        max_new_tokens=max_new_tokens,
        vocabulary_size=vocabulary,
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
    if with_prefill:
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
    else:
        builder.entrypoint(
            entrypoint_id=0,
            first_instruction=0,
            phase=Phase.DECODE,
            generation_policy_id=policy,
        )
    builder.source_identity = (
        {"fixture": "abi3-cycle-batch-v1"}
        if graph_id is None
        else {"graph_id": graph_id}
    )
    return builder.finish(), capability, logits, policy


def _lane(
    scheduler: CycleBatchScheduler,
    lane_index: int,
    transaction_id: int,
    policy_id: int,
    *,
    span: int,
    phase: Phase = Phase.DECODE,
    entrypoint_id: int = 0,
    max_new_tokens: int = 8,
) -> BatchLaneSubmission:
    session = scheduler.sessions[lane_index]
    descriptor_id = scheduler.device.next_request_descriptor_id
    position_start = session.position
    symbols = {
        int(Symbol.SPAN_TOKENS): span,
        int(Symbol.POSITION_START): position_start,
        int(Symbol.POSITION_END): position_start + span,
        int(Symbol.CONTEXT_LENGTH): position_start + span,
        int(Symbol.PHASE): int(phase),
        int(Symbol.GENERATION_INDEX): len(session.generated),
        int(Symbol.MAX_NEW_TOKENS): max_new_tokens,
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
        entrypoint_id=entrypoint_id,
        generation_policy_id=policy_id,
        flags=int(
            SubmissionFlag.PREFILL_PHASE
            if phase is Phase.PREFILL
            else SubmissionFlag.DECODE_PHASE
        ),
    )
    return BatchLaneSubmission(lane_index=lane_index, record=submission.encode())


def _stage_token(
    scheduler: CycleBatchScheduler,
    logits: int,
    lane: int,
    token: int,
    *,
    vocabulary: int = VOCABULARY,
) -> None:
    values = np.zeros(vocabulary, dtype=np.float32)
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


def test_generation_driver_retains_modeled_ticks_from_the_same_token_execution() -> None:
    """Driver records must carry the cycle scheduler's bound completion ticks."""

    load_engines()
    deployment, capability, logits, _policy = _deployment(
        max_sessions=2,
        max_new_tokens=3,
        with_prefill=True,
    )
    model = CycleModel(deployment, capability, load_cost_table(BASELINE))
    scheduler = CycleBatchScheduler(model, 2)
    _stage_token(scheduler, logits, 0, 1)
    _stage_token(scheduler, logits, 1, 2)

    result = BatchGenerationDriver(scheduler).generate_batch(
        (
            BatchGenerationRequest("one-token", (1,), 1),
            BatchGenerationRequest("two-tokens", (2, 0, 1), 2),
        )
    )

    assert [row.generation.generated_token_ids for row in result.sequences] == [
        (1,),
        (2, 2),
    ]
    assert [row.generation.stop_reason for row in result.sequences] == [
        "max_new_tokens",
        "max_new_tokens",
    ]
    assert len(scheduler.timing_records) == 3
    for lane, sequence in enumerate(result.sequences):
        step_ticks = [
            step["completion_timestamp"] for step in sequence.generation.per_step
        ]
        assert step_ticks == scheduler.history[lane].commit_ticks
        assert sequence.generation.request_start_tick == result.scheduler_evidence[
            "sequences"
        ][lane]["request_start_ticks"][0]
    assert result.scheduler_evidence["scheduler"] == "shared_resource_cycle_v1"
    assert result.scheduler_evidence["acceptance_gates"]["gate1_correctness"][
        "status"
    ] == "not_evaluable"
    assert result.scheduler_evidence["acceptance_gates"]["gate2_tpot"][
        "status"
    ] == "blocked"


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


def test_transaction_ids_are_session_scoped_in_a_physical_batch() -> None:
    load_engines()
    scheduler, logits, policy = _scheduler(2)
    for lane in range(2):
        _stage_token(scheduler, logits, lane, VOCABULARY - 1)
    wave = scheduler.submit_wave(
        [
            _lane(scheduler, 0, 1, policy, span=1),
            _lane(scheduler, 1, 1, policy, span=1),
        ]
    )

    assert [lane.completion.transaction_id for lane in wave.lanes] == [1, 1]
    assert len({lane.completion.session_id for lane in wave.lanes}) == 2
    assert {
        (record.session_id, record.transaction_id)
        for record in scheduler.timing_records
    } == {
        (wave.lanes[0].session_id, 1),
        (wave.lanes[1].session_id, 1),
    }


@pytest.mark.parametrize(
    "mutation",
    [
        lambda record: replace(record, session_id=record.session_id + 1),
        lambda record: replace(record, transaction_id=record.transaction_id + 1),
        lambda record: replace(record, lane_index=record.lane_index + 1),
        lambda record: replace(record, produced_token_id=0),
        lambda record: replace(record, eos_reason=EosReason.NONE),
        lambda record: replace(record, submission_digest="0" * 64),
        lambda record: replace(record, request_symbols_digest="0" * 64),
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


def _run(repo: Path, *command: str) -> None:
    subprocess.run(command, cwd=repo, check=True, capture_output=True, text=True)


def _governed_budget() -> dict:
    return {
        "schema": "opentallas.abi3.tpot_acceptance_budget.v1",
        "metric": "per_sequence_steady_state_decode_step_latency_seconds",
        "batch_size": 1,
        "steady_state_start_decode_step": 0,
        "roles": {
            role: {
                "maximum_seconds": 1.0,
                "statistic": "p95",
                "eligible_measurement_classes": ["abi3_cycle_model_execution"],
                "assumption_dependent_evidence_allowed": False,
            }
            for role in ("rom", "hbm")
        },
    }


def _governed_export_fixture(tmp_path: Path, *, characterized: bool = True):
    bundle = make_locked_repository(
        tmp_path,
        namespace="cycle-governed",
        max_new_tokens=256,
        oracle_generated_token_ids=[1, 7],
        oracle_stop_reason="eos",
    )
    contract = bundle["contract"]
    contract["execution"]["tpot_acceptance"] = _governed_budget()
    target = contract["targets"]["hbm"]
    deployment, capability, logits, generation_policy = _deployment(
        max_sessions=2,
        max_context_positions=512,
        max_new_tokens=256,
        target_id=target["target_id"],
        model_id=contract["model"]["model_id"],
        backend=target["backend"],
        graph_id=contract["model"]["graph_id"],
        with_prefill=True,
        vocabulary=8,
        technology_view="asap7",
    )
    capability_path = tmp_path / target["capability"]["path"]
    write_json(capability_path, capability.to_dict())
    deployment_root = tmp_path / target["deployment"]["path"]
    deployment.write(deployment_root)
    target["capability"].update(
        status="locked",
        digest=capability.digest,
        source_sha256=sha256_file(capability_path),
    )
    target["deployment"].update(
        status="locked",
        digest=deployment.deployment_digest.hex(),
        source_sha256=sha256_file(deployment_root / "deployment.json"),
    )

    cost_path = tmp_path / target["cost_policy"]["lock"]["path"]
    cost = json.loads(cost_path.read_text(encoding="utf-8"))
    characterization = tmp_path / "results/characterization/asap7-cycle.json"
    write_json(characterization, {"status": "characterized"})
    for entry in cost["parameters"].values():
        entry["provenance"] = "characterized" if characterized else "assumed"
        entry["source"] = characterization.relative_to(tmp_path).as_posix()
    cost["comparison_policy"] = policy_identity(contract, "hbm")
    write_json(cost_path, cost)
    cost_table = load_cost_table(cost_path)
    target["cost_policy"]["lock"].update(
        status="locked",
        digest=cost_table.digest,
        source_sha256=sha256_file(cost_path),
    )

    oracle_path = tmp_path / contract["external_oracle"]["path"]
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    oracle_result = oracle["results"][contract["workload"]["workload_id"]]
    oracle_result.update(
        raw_decoded_text="one answer<eos>",
        visible_decoded_text="one answer",
    )
    write_json(oracle_path, oracle)
    contract["external_oracle"]["source_sha256"] = sha256_file(oracle_path)
    write_json(bundle["contract_path"], contract)
    validation = validate_comparison_contract(
        contract,
        repo=tmp_path,
        source_path=bundle["contract_path"],
    )
    assert validation["ready"], validation

    producer = tmp_path / "runtime/cycle/governed.py"
    producer.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / "runtime/cycle/governed.py", producer)
    checkpoint_lock = tmp_path / "results/source/checkpoint.lock.json"
    write_json(
        checkpoint_lock,
        {
            "schema": "opentallas.checkpoint_lock.v1",
            "lock_id": "a" * 64,
        },
    )
    _run(tmp_path, "git", "init", "-q")
    _run(tmp_path, "git", "config", "user.email", "cycle@example.invalid")
    _run(tmp_path, "git", "config", "user.name", "Cycle Export Test")
    _run(tmp_path, "git", "add", "-A")
    _run(tmp_path, "git", "commit", "-qm", "frozen cycle export")
    namespace = "results/abi3/releases/cycle-governed"
    release = build_release_lock(
        repo=tmp_path,
        release_id="cycle-governed-b1",
        comparison_contracts=[bundle["contract_path"]],
        external_locks={"checkpoint": checkpoint_lock},
        result_namespace=namespace,
    )
    release_path = tmp_path / "results/abi3/releases/cycle-governed.lock.json"
    write_json(release_path, release)

    model = CycleModel(
        deployment,
        capability,
        cost_table,
        root=deployment_root,
    )
    scheduler = CycleBatchScheduler(model, 1)
    _stage_token(scheduler, logits, 0, 1, vocabulary=8)
    scheduler.submit_wave(
        [
            _lane(
                scheduler,
                0,
                1,
                generation_policy,
                span=3,
                phase=Phase.PREFILL,
                entrypoint_id=0,
                max_new_tokens=256,
            )
        ]
    )
    _stage_token(scheduler, logits, 0, 7, vocabulary=8)
    scheduler.submit_wave(
        [
            _lane(
                scheduler,
                0,
                2,
                generation_policy,
                span=1,
                phase=Phase.DECODE,
                entrypoint_id=1,
                max_new_tokens=256,
            )
        ]
    )
    timings = list(scheduler.timing_records)
    implementation = {
        "backend": "numpy",
        "device": "host",
        "blocked_association": "fixture",
    }
    association = {"implementation": implementation, "numeric": "exact"}
    association["manifest_sha256"] = digest_of(association)
    source_path = "tools/run_accelerator_tokens.py"
    source_sha = sha256_file(tmp_path / source_path)
    record = {
        "schema": "opentallas.abi3.accelerator_tokens.v1",
        "status": "pass",
        "evidence_class": "functional_artifact_only",
        "tool": source_path,
        "backend": "hbm_sram",
        "target": {
            "target_id": target["target_id"],
            "backend": target["backend"],
            "node_count": target["node_count"],
            "topology_class": target["topology_class"],
            "capability_digest": capability.digest,
            "deployment_digest": deployment.deployment_digest.hex(),
            "technology_view": "asap7",
        },
        "workload": {
            "workload_id": contract["workload"]["workload_id"],
            "workload_digest": contract["workload"]["digest"],
            "prompt_token_ids": [1, 2, 3],
            "prompt_token_count": 3,
            "max_new_tokens": 256,
            "rendered_text_sha256": contract["workload"]["rendered_text_sha256"],
            "prompt_token_ids_sha256": digest_of([1, 2, 3]),
            "tokenizer_sha256": contract["workload"]["tokenizer_sha256"],
        },
        "model": {
            "model_id": contract["model"]["model_id"],
            "graph_id": contract["model"]["graph_id"],
            "numeric_profile": contract["model"]["numeric_profile"],
        },
        "verification": {
            "admitted": True,
            "errors": [],
            "state_resources": 0,
            "checks": {"capacity": True, "authentication": True},
        },
        "engine_coverage": {"missing_count": 0, "missing": []},
        "implementation_identity": implementation,
        "executed_association": association,
        "source_sha256": {source_path: source_sha},
        "generated_token_ids": [1, 7],
        "generated_token_count": 2,
        "stop_reason": "eos",
        "failure": None,
        "token_legitimacy_problems": [],
        "oracle": {
            "artifact": contract["external_oracle"]["path"],
            "artifact_sha256": contract["external_oracle"]["source_sha256"],
            "evidence_class": "external_reference_comparator",
            "generated_token_ids": [1, 7],
            "agreement": True,
            "first_divergence_index": None,
            "compared_tokens": 2,
            "oracle_token_count": 2,
        },
        "terminal_acceptance": {
            "contract": "exact_eos_or_cap",
            "accepted": True,
            "terminal_kind": "eos",
            "failed_checks": [],
            "checks": {"first_official_eos": True, "no_post_eos": True},
        },
        "per_step": [
            {
                "step": index,
                "transaction_id": timing.transaction_id,
                "phase": "prefill" if index == 0 else "decode",
                "status": "SUCCESS",
                "trap": "NONE",
                "produced_tokens": [token],
                "final_token_id": token,
                "eos_reason": 1 if index == 1 else 0,
                "instructions_retired": 8,
                "retired_work": 8,
                "completion_timestamp": timing.token_commit_tick,
                "wall_seconds": 1.0,
            }
            for index, (token, timing) in enumerate(zip([1, 7], timings, strict=True))
        ],
        "execution_timing": {
            "schema": "opentallas.abi3.execution_token_commit_timing.v1",
            "unit": "cycles",
            "clock_domain": "abi3_device_cycle_counter",
            "request_start_tick": timings[0].request_start_tick,
            "request_start_source": "driver_counter_before_fresh_prefill_submission",
            "token_commit_ticks": [row.token_commit_tick for row in timings],
            "token_commit_source": "decoded_abi3_completion.completion_timestamp",
            "token_commits_from_execution": True,
            "problems": [],
        },
        "wall_seconds": 2.0,
    }
    result_root = tmp_path / namespace
    record_path = result_root / "hbm-sequence-0.json"
    write_json(record_path, record)
    workload_file = json.loads(bundle["workload_path"].read_text(encoding="utf-8"))
    raw = oracle_result["raw_decoded_text"]
    visible = oracle_result["visible_decoded_text"]
    acceptance = {
        "schema": "opentallas.abi3.qwen3_w10_acceptance.v1",
        "status": "pass",
        "workload_id": contract["workload"]["workload_id"],
        "problems": [],
        "pair_checks": {"token_sequences_identical": True},
        "claim_boundary": {"acceptance_established": True},
        "records": [
            {
                "path": record_path.relative_to(tmp_path).as_posix(),
                "sha256": sha256_file(record_path),
                "passes": True,
                "problems": [],
            }
        ],
        "text_evidence": {
            "tokenizer": {"sha256": contract["workload"]["tokenizer_sha256"]},
            "input": {
                "token_count": 3,
                "token_ids_sha256": digest_of([1, 2, 3]),
                "rendered_text": workload_file["rendered_text"],
                "rendered_text_sha256": contract["workload"]["rendered_text_sha256"],
                "decode_matches_frozen_text": True,
                "encode_round_trip_matches_ids": True,
            },
            "output": {
                "token_count": 2,
                "token_ids": [1, 7],
                "token_ids_sha256": digest_of([1, 7]),
                "raw_decoded_text": raw,
                "raw_decoded_text_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "visible_decoded_text": visible,
                "visible_decoded_text_sha256": hashlib.sha256(
                    visible.encode()
                ).hexdigest(),
                "raw_matches_frozen_oracle": True,
                "visible_matches_frozen_oracle": True,
            },
        },
    }
    acceptance_path = result_root / "acceptance.json"
    write_json(acceptance_path, acceptance)
    return {
        "repo": tmp_path,
        "scheduler": scheduler,
        "release": {
            "path": release_path.relative_to(tmp_path).as_posix(),
            "sha256": sha256_file(release_path),
        },
        "comparison_id": contract["comparison_id"],
        "acceptance": {
            "path": acceptance_path.relative_to(tmp_path).as_posix(),
            "sha256": sha256_file(acceptance_path),
        },
        "records": [
            {
                "path": record_path.relative_to(tmp_path).as_posix(),
                "sha256": sha256_file(record_path),
            }
        ],
        "record_path": record_path,
        "acceptance_path": acceptance_path,
        "output": result_root / "target-timing.json",
        "release_body": release,
    }


def test_governed_export_binds_correct_sequence_and_release(tmp_path: Path) -> None:
    fixture = _governed_export_fixture(tmp_path)
    trace = publish_governed_target_timing_trace(
        fixture["scheduler"],
        repo=fixture["repo"],
        output_path=fixture["output"],
        execution_release_lock=fixture["release"],
        comparison_id=fixture["comparison_id"],
        correctness_acceptance=fixture["acceptance"],
        execution_records=fixture["records"],
        target_role="hbm",
    )

    assert fixture["output"].is_file()
    assert trace[RELEASE_FILE_DIGEST_FIELD] == fixture["release"]["sha256"]
    assert trace[RELEASE_SEMANTIC_DIGEST_FIELD] == fixture["release_body"][
        "release_sha256"
    ]
    assert trace["full_workload_execution"] is True
    assert trace["provenance"] == {
        "class": "characterized",
        "depends_on_assumed_values": False,
    }
    assert trace["sequences"][0]["token_commit_ticks"] == [
        row.token_commit_tick for row in fixture["scheduler"].timing_records
    ]
    with pytest.raises(GovernedTimingExportError, match="already exists"):
        publish_governed_target_timing_trace(
            fixture["scheduler"],
            repo=fixture["repo"],
            output_path=fixture["output"],
            execution_release_lock=fixture["release"],
            comparison_id=fixture["comparison_id"],
            correctness_acceptance=fixture["acceptance"],
            execution_records=fixture["records"],
            target_role="hbm",
        )


def test_governed_export_rejects_uncharacterized_fixture_timing(
    tmp_path: Path,
) -> None:
    fixture = _governed_export_fixture(tmp_path, characterized=False)
    with pytest.raises(GovernedTimingExportError, match="not characterized"):
        publish_governed_target_timing_trace(
            fixture["scheduler"],
            repo=fixture["repo"],
            output_path=fixture["output"],
            execution_release_lock=fixture["release"],
            comparison_id=fixture["comparison_id"],
            correctness_acceptance=fixture["acceptance"],
            execution_records=fixture["records"],
            target_role="hbm",
        )
    assert not fixture["output"].exists()


@pytest.mark.parametrize(
    "field",
    [
        "host_wall_time_used",
        "retired_instruction_count_used_as_time",
        "projection_used_as_qualified_tpot",
    ],
)
def test_governed_export_rejects_non_target_timebases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    fixture = _governed_export_fixture(tmp_path)
    scheduler = fixture["scheduler"]
    original_evidence = scheduler.evidence

    def evidence_with_forbidden_timebase(*args, **kwargs):
        evidence = original_evidence(*args, **kwargs)
        evidence["timing"]["timebase"][field] = True
        return evidence

    monkeypatch.setattr(scheduler, "evidence", evidence_with_forbidden_timebase)
    with pytest.raises(GovernedTimingExportError, match="target-cycle time"):
        publish_governed_target_timing_trace(
            scheduler,
            repo=fixture["repo"],
            output_path=fixture["output"],
            execution_release_lock=fixture["release"],
            comparison_id=fixture["comparison_id"],
            correctness_acceptance=fixture["acceptance"],
            execution_records=fixture["records"],
            target_role="hbm",
        )
    assert not fixture["output"].exists()


def test_governed_export_rejects_oracle_divergence_and_outside_namespace(
    tmp_path: Path,
) -> None:
    fixture = _governed_export_fixture(tmp_path)
    record = json.loads(fixture["record_path"].read_text(encoding="utf-8"))
    record["oracle"]["generated_token_ids"][0] = 2
    write_json(fixture["record_path"], record)
    fixture["records"][0]["sha256"] = sha256_file(fixture["record_path"])
    acceptance = json.loads(
        fixture["acceptance_path"].read_text(encoding="utf-8")
    )
    acceptance["records"][0]["sha256"] = fixture["records"][0]["sha256"]
    write_json(fixture["acceptance_path"], acceptance)
    fixture["acceptance"]["sha256"] = sha256_file(fixture["acceptance_path"])
    with pytest.raises(GovernedTimingExportError, match="locked oracle"):
        publish_governed_target_timing_trace(
            fixture["scheduler"],
            repo=fixture["repo"],
            output_path=fixture["repo"] / "outside.json",
            execution_release_lock=fixture["release"],
            comparison_id=fixture["comparison_id"],
            correctness_acceptance=fixture["acceptance"],
            execution_records=fixture["records"],
            target_role="hbm",
        )
    assert not (fixture["repo"] / "outside.json").exists()


def test_governed_export_rejects_output_outside_release_namespace(
    tmp_path: Path,
) -> None:
    fixture = _governed_export_fixture(tmp_path)
    outside = fixture["repo"] / "outside.json"
    with pytest.raises(GovernedTimingExportError, match="outside the release namespace"):
        publish_governed_target_timing_trace(
            fixture["scheduler"],
            repo=fixture["repo"],
            output_path=outside,
            execution_release_lock=fixture["release"],
            comparison_id=fixture["comparison_id"],
            correctness_acceptance=fixture["acceptance"],
            execution_records=fixture["records"],
            target_role="hbm",
        )
    assert not outside.exists()


def test_governed_export_rejects_prefix_only_request_binding(
    tmp_path: Path,
) -> None:
    fixture = _governed_export_fixture(tmp_path)
    original = fixture["scheduler"].device.transaction_traces[0]
    symbols = dict(original.request_symbols)
    symbols[int(Symbol.SPAN_TOKENS)] = 1
    symbols[int(Symbol.POSITION_END)] = 1
    symbols[int(Symbol.CONTEXT_LENGTH)] = 1
    symbols[int(Symbol.SPAN_LAST_INDEX)] = 0
    fixture["scheduler"].device.transaction_traces[0] = replace(
        original, request_symbols=tuple(sorted(symbols.items()))
    )

    with pytest.raises(GovernedTimingExportError, match="full-model trajectory"):
        publish_governed_target_timing_trace(
            fixture["scheduler"],
            repo=fixture["repo"],
            output_path=fixture["output"],
            execution_release_lock=fixture["release"],
            comparison_id=fixture["comparison_id"],
            correctness_acceptance=fixture["acceptance"],
            execution_records=fixture["records"],
            target_role="hbm",
        )
    assert not fixture["output"].exists()
