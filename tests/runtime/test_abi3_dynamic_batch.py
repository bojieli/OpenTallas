"""Focused structural tests for ABI 3.0 session batching."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from runtime.abi3.builder import DeploymentBuilder, DynamicTerm
from runtime.abi3.constants import (
    CompletionStatus,
    Control,
    DType,
    HostOpcode,
    Major,
    Permission,
    Selection,
    StorageClass,
    SubmissionFlag,
    TopologyClass,
    TrapClass,
)
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import Phase, SelectionMode, Symbol
from runtime.abi3.fixture import FIXTURE_VOCAB, build_fixture, fixture_capability
from runtime.abi3.records import EosReason, Submission
from runtime.abi3.request import RequestSymbolDescriptor
from runtime.abi3.verifier import verify_deployment
from runtime.driver import (
    BatchGenerationDriver,
    BatchGenerationRequest,
    GenerationDriver,
)
from runtime.sim.batch import BatchError, BatchLaneSubmission, BatchScheduler
from runtime.sim.device import Device
from runtime.sim.engines import load_engines


VOCABULARY = 4


def _selection_deployment(
    *,
    batch_probe_bytes: int | None = None,
    max_sessions: int = 4,
    with_prefill: bool = False,
):
    capability = fixture_capability(TopologyClass.SINGLE_CHIP)
    capability.limits = {**capability.limits, "max_sessions": max_sessions}
    capability.validate()
    builder = DeploymentBuilder(
        target_id="abi3-dynamic-batch-structural",
        model_id="abi3-dynamic-batch-fixture",
        backend="batch-test",
        capability=capability,
    )
    builder.topology(
        topology_class=TopologyClass.SINGLE_CHIP,
        node_count=1,
        hbm_bytes_per_node=capability.memory["hbm"]["bytes"],
        sram_bytes_per_node=capability.memory["sram"]["bytes"],
        key="topology",
    )
    immutable = builder.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=64,
        source=ObjectSource.zeros(64),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
        key="obj.shared.immutable",
    )
    if batch_probe_bytes is not None:
        batch_probe = builder.memory_object(
            storage_class=StorageClass.HBM,
            size_bytes=batch_probe_bytes,
            source=ObjectSource.zeros(batch_probe_bytes),
            permissions=int(Permission.READ | Permission.IMMUTABLE),
            key="obj.batch.probe",
        )
        builder.tensor_view(
            object_id=batch_probe,
            dtype=DType.U32,
            dims=[1],
            dynamic=[DynamicTerm.symbol(Symbol.BATCH, 1)],
            key="view.batch.probe",
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
        source=ObjectSource.zeros((1 + capability.limits["max_context_positions"]) * 4),
        permissions=int(Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE),
        key="obj.tokens",
    )
    numeric = builder.numeric(
        contract="exact_index_select_v1",
        input_dtype=DType.FP32,
        output_dtype=DType.U32,
        accumulator_dtype=DType.FP32,
        key="numeric.selection",
    )
    schedule = builder.schedule(
        engine_family=Major.SELECTION,
        tile_rows=1,
        tile_cols=VOCABULARY,
        tile_depth=1,
        max_outstanding=1,
        key="schedule.selection",
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
    argmax = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.ARGMAX,
        inputs=[logits_view],
        outputs=[selected_view],
        numeric_profile_id=numeric,
        schedule_id=schedule,
        source_kernel_id=0,
        key="op.argmax",
    )
    append = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.TOKEN_APPEND,
        inputs=[selected_view],
        outputs=[ring_view],
        numeric_profile_id=numeric,
        schedule_id=schedule,
        source_kernel_id=1,
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
    builder.source_identity = {"fixture": "abi3-dynamic-batch-structural-v1"}
    return builder.finish(), capability, immutable, logits, tokens, policy


def _submission(
    device: Device,
    session,
    *,
    transaction_id: int,
    policy_id: int,
    request_descriptor_id: int,
) -> bytes:
    return Submission(
        host_opcode=int(HostOpcode.GENERATE),
        deployment_id=device.deployment.deployment_id,
        deployment_generation=device.deployment.generation,
        session_id=session.session_id,
        session_generation=session.generation,
        request_descriptor_id=request_descriptor_id,
        transaction_id=transaction_id,
        idempotency_key=hashlib.sha256(
            f"{session.session_id}:{session.generation}:{transaction_id}".encode()
        ).digest()[:16],
        entrypoint_id=0,
        generation_policy_id=policy_id,
        flags=int(SubmissionFlag.DECODE_PHASE),
    ).encode()


def _lane(
    device: Device,
    session,
    lane_index: int,
    transaction_id: int,
    policy_id: int,
    *,
    batch: int = 2,
    max_new_tokens: int = 8,
) -> BatchLaneSubmission:
    symbols = {
        int(Symbol.SPAN_TOKENS): 1,
        int(Symbol.POSITION_START): len(session.generated),
        int(Symbol.POSITION_END): len(session.generated) + 1,
        int(Symbol.CONTEXT_LENGTH): len(session.generated) + 1,
        int(Symbol.PHASE): int(Phase.DECODE),
        int(Symbol.GENERATION_INDEX): len(session.generated),
        int(Symbol.MAX_NEW_TOKENS): max_new_tokens,
        int(Symbol.BATCH): batch,
        int(Symbol.NODE_ID): 0,
        int(Symbol.NODE_COUNT): device.node_count,
        int(Symbol.ACTIVE_EXPERT_COUNT): 0,
        int(Symbol.SPARSE_INDEX_COUNT): 0,
        int(Symbol.LAYER_COUNT): 0,
        int(Symbol.VOCABULARY_PARTITIONS): 1,
        int(Symbol.SPAN_LAST_INDEX): 0,
    }
    descriptor_id = device.next_request_descriptor_id
    descriptor = RequestSymbolDescriptor.from_symbols(
        request_descriptor_id=descriptor_id,
        deployment_id=device.deployment.deployment_id,
        deployment_generation=device.deployment.generation,
        session_id=session.session_id,
        session_generation=session.generation,
        transaction_id=transaction_id,
        symbols=symbols,
    )
    device.register_request_descriptor(descriptor.encode())
    return BatchLaneSubmission(
        lane_index=lane_index,
        record=_submission(
            device,
            session,
            transaction_id=transaction_id,
            policy_id=policy_id,
            request_descriptor_id=descriptor_id,
        ),
    )


def _stage_logits(scheduler: BatchScheduler, logits: int, lane: int, values) -> None:
    scheduler.stage_host_bytes(
        lane, logits, 0, np.asarray(values, dtype=np.float32).tobytes()
    )


def test_shared_batch_has_private_mutable_memory_and_independent_eos() -> None:
    load_engines()
    deployment, capability, immutable, logits, tokens, policy = _selection_deployment()
    device = Device(deployment, capability)
    sessions = device.create_batch_sessions(2)
    scheduler = BatchScheduler(device, sessions)

    # The checkpoint object is resident once.  Every writable activation,
    # selected-token/ring and state-like object is a distinct Python memory
    # object, and a lane write does not alter its sibling or the legacy arena.
    assert sessions[0].node_memories[0][immutable] is device.node_memories[0][immutable]
    assert sessions[1].node_memories[0][immutable] is device.node_memories[0][immutable]
    for object_id in (logits, tokens):
        assert (
            sessions[0].node_memories[0][object_id]
            is not (sessions[1].node_memories[0][object_id])
        )
        assert (
            sessions[0].node_memories[0][object_id]
            is not (device.node_memories[0][object_id])
        )

    _stage_logits(scheduler, logits, 0, [0.0, 0.0, 0.0, 9.0])  # lane 0 -> EOS
    _stage_logits(scheduler, logits, 1, [0.0, 9.0, 0.0, 0.0])  # lane 1 -> token 1
    first = scheduler.submit_wave(
        [
            _lane(device, sessions[0], 0, 10, policy),
            _lane(device, sessions[1], 1, 11, policy),
        ]
    )
    assert first.active_mask_before == (True, True)
    assert first.active_mask_after == (False, True)
    assert [lane.result.produced_tokens for lane in first.lanes] == [(3,), (1,)]
    assert first.lanes[0].completion.eos_reason == EosReason.OFFICIAL_EOS
    assert first.lanes[1].completion.eos_reason == EosReason.NONE

    # An EOS lane is blocked at both the memory and submission boundaries.
    with pytest.raises(BatchError, match="post-terminal host write"):
        _stage_logits(scheduler, logits, 0, [9.0, 0.0, 0.0, 0.0])
    with pytest.raises(BatchError, match="every active lane exactly once"):
        scheduler.submit_wave(
            [
                _lane(device, sessions[0], 0, 12, policy),
                _lane(device, sessions[1], 1, 13, policy),
            ]
        )

    _stage_logits(scheduler, logits, 1, [0.0, 0.0, 0.0, 9.0])
    second = scheduler.submit_wave([_lane(device, sessions[1], 1, 14, policy)])
    assert second.active_mask_before == (False, True)
    assert second.active_mask_after == (False, False)
    with pytest.raises(BatchError, match="all batch lanes are retired"):
        scheduler.submit_wave([])

    evidence = scheduler.evidence(expected_tokens=[[3], [1, 3]])
    assert evidence["status"] == "structurally_executed"
    assert evidence["physical_batch_size"] == 2
    assert evidence["symbol_batch"] == 2
    assert evidence["memory_contract"] == {
        "status": "verified",
        "mutable_objects_are_session_private": True,
        "immutable_objects_are_shared": True,
        "private_mutable_object_ids": sorted([logits, tokens]),
        "shared_immutable_object_ids": [immutable],
    }
    assert evidence["sequences"][0]["generated_token_ids"] == [3]
    assert evidence["sequences"][1]["generated_token_ids"] == [1, 3]
    assert evidence["sequences"][0]["submitted_waves"] == [0]
    assert evidence["sequences"][1]["submitted_waves"] == [0, 1]
    assert all(
        sequence["no_post_eos_transaction"] for sequence in evidence["sequences"]
    )
    assert evidence["sequences"][0]["token_commit_ticks"] == [3]
    assert evidence["sequences"][1]["token_commit_ticks"] == [6, 9]
    assert evidence["claim_boundary"]["engine_coissue_implemented"] is False
    assert (
        evidence["claim_boundary"]["eligible_for_full_model_token_correctness_gate"]
        is False
    )
    assert evidence["claim_boundary"]["eligible_for_target_tpot"] is False


def test_batch_rejects_b1_substitution_and_any_lane_token_mismatch() -> None:
    load_engines()
    deployment, capability, _immutable, logits, _tokens, policy = (
        _selection_deployment()
    )
    device = Device(deployment, capability)
    sessions = device.create_batch_sessions(2)
    scheduler = BatchScheduler(device, sessions)
    _stage_logits(scheduler, logits, 0, [0.0, 0.0, 0.0, 9.0])
    _stage_logits(scheduler, logits, 1, [0.0, 0.0, 0.0, 9.0])

    with pytest.raises(BatchError, match="Symbol.BATCH=2"):
        scheduler.submit_wave(
            [
                _lane(device, sessions[0], 0, 20, policy, batch=1),
                _lane(device, sessions[1], 1, 21, policy, batch=1),
            ]
        )

    scheduler.submit_wave(
        [
            _lane(device, sessions[0], 0, 22, policy),
            _lane(device, sessions[1], 1, 23, policy),
        ]
    )
    evidence = scheduler.evidence(expected_tokens=[[3], [2]])
    assert evidence["status"] == "rejected"
    assert evidence["sequences"][0]["expected_tokens_match"] is True
    assert evidence["sequences"][1]["expected_tokens_match"] is False
    assert evidence["sequences"][1]["first_divergence_index"] == 0
    assert any("lane 1 token mismatch" in problem for problem in evidence["problems"])


def test_batch_requires_isolated_sessions() -> None:
    deployment, capability, *_ = _selection_deployment()
    device = Device(deployment, capability)
    scalar_sessions = (device.create_session(), device.create_session())
    with pytest.raises(BatchError, match="no private writable address space"):
        BatchScheduler(device, scalar_sessions)


def test_batch_sessions_cannot_bypass_or_join_two_schedulers() -> None:
    deployment, capability, *_ = _selection_deployment()
    device = Device(deployment, capability)
    sessions = device.create_batch_sessions(2)
    scheduler = BatchScheduler(device, sessions)

    bypass = device.run_transaction(sessions[0], entrypoint_id=0, symbols={})
    assert bypass.status == CompletionStatus.FAILED
    assert bypass.trap_class == TrapClass.STATE_TRANSACTION
    assert scheduler.batch_execution_id in bypass.message
    with pytest.raises(BatchError, match="already belongs to batch execution"):
        BatchScheduler(device, sessions)


def test_session_fork_privatises_kv_activations_logits_and_token_state() -> None:
    capability = fixture_capability()
    deployment = build_fixture(storage_class=StorageClass.HBM, capability=capability)
    device = Device(deployment, capability)
    sessions = device.create_batch_sessions(2)
    scheduler = BatchScheduler(device, sessions)

    private_ids = scheduler.memory_contract["private_mutable_object_ids"]
    private_classes = {
        device.node_memories[0][object_id].storage_class for object_id in private_ids
    }
    assert StorageClass.STATE in private_classes  # committed and prepared KV
    assert StorageClass.SRAM in private_classes  # activations and logits
    assert StorageClass.HOST in private_classes  # selected token and token ring

    state_id = next(
        object_id
        for object_id in private_ids
        if device.node_memories[0][object_id].storage_class is StorageClass.STATE
    )
    sessions[0].node_memories[0][state_id].write(0, b"\x5a\xa5")
    assert sessions[0].node_memories[0][state_id].read(0, 2) == b"\x5a\xa5"
    assert sessions[1].node_memories[0][state_id].read(0, 2) == b"\x00\x00"
    assert device.node_memories[0][state_id].read(0, 2) == b"\x00\x00"


def test_batch_affine_views_are_proved_against_max_sessions() -> None:
    admitted, capability, *_ = _selection_deployment(batch_probe_bytes=16)
    report = verify_deployment(admitted, capability)
    assert report.admitted, report.errors

    too_small, _, *_ = _selection_deployment(batch_probe_bytes=4)
    report = verify_deployment(too_small, capability)
    assert not report.admitted
    assert any("needs" in error and "object" in error for error in report.errors)


@pytest.mark.parametrize("batch_size", [2, 4, 8])
def test_scheduler_preserves_the_physical_batch_symbol(batch_size: int) -> None:
    deployment, capability, *_ = _selection_deployment(max_sessions=8)
    device = Device(deployment, capability)
    scheduler = BatchScheduler(device, device.create_batch_sessions(batch_size))
    evidence = scheduler.evidence()
    assert evidence["status"] == "in_progress"
    assert evidence["physical_batch_size"] == batch_size
    assert evidence["symbol_batch"] == batch_size
    assert len(evidence["active_mask"]) == batch_size


@pytest.mark.parametrize("batch_size", [2, 4, 8])
def test_each_lane_transports_the_exact_physical_batch_symbol(batch_size: int) -> None:
    load_engines()
    deployment, capability, _immutable, logits, _tokens, policy = (
        _selection_deployment(max_sessions=8)
    )
    device = Device(deployment, capability)
    sessions = device.create_batch_sessions(batch_size)
    scheduler = BatchScheduler(device, sessions)
    for lane in range(batch_size):
        _stage_logits(scheduler, logits, lane, [0.0, 0.0, 0.0, 9.0])

    wave = scheduler.submit_wave(
        [
            _lane(device, session, lane, 100 + lane, policy, batch=batch_size)
            for lane, session in enumerate(sessions)
        ]
    )

    assert wave.status == "executed"
    assert [lane.symbol_batch for lane in wave.lanes] == [batch_size] * batch_size
    assert all(lane.result.produced_tokens == (3,) for lane in wave.lanes)
    assert device.live_request_descriptor_count == 0


def test_heterogeneous_request_caps_retire_each_lane_on_device() -> None:
    """Independent lanes stop at their own authenticated request cap."""

    load_engines()
    deployment, capability, _immutable, logits, _tokens, policy = (
        _selection_deployment()
    )
    device = Device(deployment, capability)
    sessions = device.create_batch_sessions(2)
    scheduler = BatchScheduler(device, sessions)

    # Neither selected token is EOS. Lane zero asks for one token; lane one
    # asks for two. The device, not a host-side loop, supplies both retirements.
    _stage_logits(scheduler, logits, 0, [0.0, 9.0, 0.0, 0.0])
    _stage_logits(scheduler, logits, 1, [0.0, 0.0, 9.0, 0.0])
    first = scheduler.submit_wave(
        [
            _lane(
                device,
                sessions[0],
                0,
                200,
                policy,
                max_new_tokens=1,
            ),
            _lane(
                device,
                sessions[1],
                1,
                201,
                policy,
                max_new_tokens=2,
            ),
        ]
    )
    assert first.active_mask_after == (False, True)
    assert first.lanes[0].completion.eos_reason == EosReason.MAX_NEW_TOKENS
    assert first.lanes[1].completion.eos_reason == EosReason.NONE
    assert sessions[0].finished
    assert not sessions[1].finished

    with pytest.raises(BatchError, match="post-terminal host write"):
        _stage_logits(scheduler, logits, 0, [9.0, 0.0, 0.0, 0.0])

    _stage_logits(scheduler, logits, 1, [9.0, 0.0, 0.0, 0.0])
    second = scheduler.submit_wave(
        [
            _lane(
                device,
                sessions[1],
                1,
                202,
                policy,
                max_new_tokens=2,
            )
        ]
    )
    assert second.active_mask_after == (False, False)
    assert second.lanes[0].completion.eos_reason == EosReason.MAX_NEW_TOKENS
    assert sessions[1].finished

    evidence = scheduler.evidence(expected_tokens=[[1], [2, 0]])
    assert evidence["status"] == "structurally_executed"
    assert [row["eos_reason"] for row in evidence["sequences"]] == [
        EosReason.MAX_NEW_TOKENS,
        EosReason.MAX_NEW_TOKENS,
    ]
    assert all(
        row["post_retirement_transaction_count"] == 0
        for row in evidence["sequences"]
    )


@pytest.mark.parametrize("batch_size", [1, 2, 4, 8])
def test_generation_driver_executes_independent_ragged_batch_to_device_caps(
    batch_size: int,
) -> None:
    """The production driver owns one real B=N flow, not cloned B=1 loops."""

    load_engines()
    capability = fixture_capability()
    capability.limits = {**capability.limits, "max_sessions": 8}
    capability.validate()
    deployment = build_fixture(
        storage_class=StorageClass.HBM,
        capability=capability,
    )
    device = Device(deployment, capability)
    sessions = (
        (device.create_session(),)
        if batch_size == 1
        else device.create_batch_sessions(batch_size)
    )
    scheduler = BatchScheduler(device, sessions)
    driver = BatchGenerationDriver(scheduler)
    requests = tuple(
        BatchGenerationRequest(
            sequence_id=f"sequence-{lane}",
            prompt_token_ids=tuple(
                (lane + offset) % FIXTURE_VOCAB for offset in range(lane + 1)
            ),
            max_new_tokens=lane % 4 + 1,
        )
        for lane in range(batch_size)
    )
    progress: list[tuple[int, int, int]] = []

    result = driver.generate_batch(requests, progress=lambda *row: progress.append(row))

    assert result.physical_batch_size == batch_size
    assert result.batch_execution_id == scheduler.batch_execution_id
    assert len(result.waves) == max(row.max_new_tokens for row in requests)
    last_progress = {lane: (count, limit) for lane, count, limit in progress}
    for lane, (request, sequence) in enumerate(zip(requests, result.sequences)):
        expected_count = request.max_new_tokens
        assert sequence.lane_index == lane
        assert sequence.sequence_id == request.sequence_id
        assert sequence.generation.prompt_token_ids == request.prompt_token_ids
        assert sequence.generation.generated_token_ids == (0,) * expected_count
        assert sequence.generation.stop_reason == "max_new_tokens"
        assert sequence.generation.eos_token_id is None
        assert sequence.generation.transactions == expected_count
        assert sequence.generation.prefill_tokens == len(request.prompt_token_ids)
        assert sequence.generation.decode_steps == expected_count - 1
        assert sequence.generation.failure is None
        assert scheduler.history[lane].transaction_ids == list(
            range(1, expected_count + 1)
        )
        assert last_progress[lane] == (expected_count, expected_count)

    for wave in result.waves:
        active_before = {
            lane for lane, active in enumerate(wave["active_mask_before"]) if active
        }
        assert {row["lane_index"] for row in wave["lanes"]} == active_before
        assert all(
            row["symbol_batch"] == batch_size for row in wave["lanes"]
        )
    assert result.scheduler_evidence["status"] == "structurally_executed"
    assert result.scheduler_evidence["physical_batch_size"] == batch_size
    assert all(
        row["no_post_eos_transaction"]
        for row in result.scheduler_evidence["sequences"]
    )
    assert device.live_request_descriptor_count == 0


def test_generation_driver_b1_wrapper_preserves_scalar_trajectory() -> None:
    """Extracting submission construction must not change the scalar path."""

    load_engines()
    capability = fixture_capability()
    deployment = build_fixture(
        storage_class=StorageClass.HBM,
        capability=capability,
    )
    prompt = (1, 2, 3)
    scalar = GenerationDriver(Device(deployment, capability)).generate(
        prompt,
        max_new_tokens=3,
    )

    batch_device = Device(deployment, capability)
    scheduler = BatchScheduler(batch_device, (batch_device.create_session(),))
    batched = BatchGenerationDriver(scheduler).generate_batch(
        (
            BatchGenerationRequest(
                sequence_id="scalar-control",
                prompt_token_ids=prompt,
                max_new_tokens=3,
            ),
        )
    ).sequences[0].generation

    assert batched.generated_token_ids == scalar.generated_token_ids
    assert batched.stop_reason == scalar.stop_reason
    assert batched.eos_token_id == scalar.eos_token_id
    assert batched.transactions == scalar.transactions
    assert batched.decode_steps == scalar.decode_steps
    assert batched.counters == scalar.counters
    assert [step["phase"] for step in batched.per_step] == [
        step["phase"] for step in scalar.per_step
    ]
    assert [step["completion_timestamp"] for step in batched.per_step] == [
        step["completion_timestamp"] for step in scalar.per_step
    ]


def test_generation_driver_preserves_independent_eos_and_cap_retirement() -> None:
    """EOS and length-cap lanes retire independently with no later transaction."""

    load_engines()
    deployment, capability, _immutable, logits, _tokens, _policy = (
        _selection_deployment(max_sessions=8, with_prefill=True)
    )
    device = Device(deployment, capability)
    scheduler = BatchScheduler(device, device.create_batch_sessions(2))
    _stage_logits(scheduler, logits, 0, [0.0, 0.0, 0.0, 9.0])
    _stage_logits(scheduler, logits, 1, [0.0, 9.0, 0.0, 0.0])

    result = BatchGenerationDriver(scheduler).generate_batch(
        (
            BatchGenerationRequest("eos-lane", (1,), 8),
            BatchGenerationRequest("cap-lane", (2, 1, 0), 2),
        )
    )

    eos_lane, cap_lane = result.sequences
    assert eos_lane.generation.generated_token_ids == (3,)
    assert eos_lane.generation.stop_reason == "eos"
    assert eos_lane.generation.eos_token_id == 3
    assert cap_lane.generation.generated_token_ids == (1, 1)
    assert cap_lane.generation.stop_reason == "max_new_tokens"
    assert cap_lane.generation.eos_token_id is None
    assert [row["lane_index"] for row in result.waves[0]["lanes"]] == [0, 1]
    assert [row["lane_index"] for row in result.waves[1]["lanes"]] == [1]
    assert scheduler.history[0].transaction_ids == [1]
    assert scheduler.history[1].transaction_ids == [1, 2]
    assert all(
        row["no_post_eos_transaction"]
        for row in result.scheduler_evidence["sequences"]
    )
    assert device.live_request_descriptor_count == 0
