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
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.abi3.records import EosReason, Submission
from runtime.abi3.verifier import verify_deployment
from runtime.sim.batch import BatchError, BatchLaneSubmission, BatchScheduler
from runtime.sim.device import Device
from runtime.sim.engines import load_engines


VOCABULARY = 4


def _selection_deployment(
    *, batch_probe_bytes: int | None = None, max_sessions: int = 4
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
) -> bytes:
    return Submission(
        host_opcode=int(HostOpcode.GENERATE),
        deployment_id=device.deployment.deployment_id,
        deployment_generation=device.deployment.generation,
        session_id=session.session_id,
        session_generation=session.generation,
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
) -> BatchLaneSubmission:
    return BatchLaneSubmission(
        lane_index=lane_index,
        record=_submission(
            device,
            session,
            transaction_id=transaction_id,
            policy_id=policy_id,
        ),
        symbols={
            int(Symbol.BATCH): batch,
            int(Symbol.GENERATION_INDEX): len(session.generated),
            int(Symbol.SPAN_TOKENS): 1,
            int(Symbol.POSITION_START): len(session.generated),
            int(Symbol.POSITION_END): len(session.generated) + 1,
            int(Symbol.CONTEXT_LENGTH): len(session.generated) + 1,
            int(Symbol.MAX_NEW_TOKENS): 8,
            int(Symbol.SPAN_LAST_INDEX): 0,
        },
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
    with pytest.raises(BatchError, match="post-EOS host write"):
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
