"""Session-batched execution over the frozen ABI 3.0 host records.

ABI 3.0 deliberately has one session identity and one scalar token result in a
submission/completion record.  A dynamic batch is therefore a scheduler-owned
set of ordinary records, not a new vector record.  :class:`BatchScheduler`
keeps that set together, binds ``Symbol.BATCH`` to the physical batch size,
executes one wave for every active lane, retires EOS lanes independently, and
retains the per-session completion timestamps that a later timing tier needs.

This first executable slice is intentionally conservative.  Engine calls are
still lane-serial inside a wave; no shared-resource cycle model or RTL co-issue
claim follows from it.  Its evidence says so and is ineligible for Gate 1 and
TPOT promotion.  What it closes is the prerequisite that repeated independent
``B=1`` driver loops cannot close: one scheduler, one batch identity, private
mutable session address spaces, a physical ``B=N`` symbol binding, an active
mask, and fail-closed per-lane result accounting.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field as dc_field
from typing import Any, Mapping, Sequence

from runtime.abi3.constants import (
    CompletionStatus,
    HostOpcode,
    NO_ID,
    SubmissionFlag,
    TrapClass,
)
from runtime.abi3.descriptors import Symbol
from runtime.abi3.records import Completion, EosReason, Submission
from runtime.sim.device import Device, Session, TransactionResult


STRUCTURAL_BATCH_SCHEMA = "opentallas.abi3.structural_batch_execution.v1"


class BatchError(Exception):
    """A fail-closed refusal at the shared batch boundary."""


@dataclass(frozen=True)
class BatchLaneSubmission:
    """One existing ABI 3.0 submission plus its request-symbol bindings."""

    lane_index: int
    record: bytes
    symbols: Mapping[int, int]


@dataclass
class BatchLaneCompletion:
    """One scalar ABI completion produced within a shared batch wave."""

    lane_index: int
    session_id: int
    record: bytes
    completion: Completion
    result: TransactionResult
    symbol_batch: int
    active_after: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_index": self.lane_index,
            "session_id": self.session_id,
            "transaction_id": self.completion.transaction_id,
            "status": CompletionStatus(self.completion.status).name,
            "trap_class": TrapClass(self.completion.trap_class).name,
            "produced_tokens": list(self.result.produced_tokens),
            "final_token_id": (
                None
                if self.completion.final_token_id == NO_ID
                else self.completion.final_token_id
            ),
            "eos_reason": self.completion.eos_reason,
            "completion_timestamp": self.completion.completion_timestamp,
            "symbol_batch": self.symbol_batch,
            "active_after": self.active_after,
        }


@dataclass
class BatchWaveResult:
    """The completions and active-mask transition for one scheduler wave."""

    batch_execution_id: str
    wave_index: int
    physical_batch_size: int
    active_mask_before: tuple[bool, ...]
    active_mask_after: tuple[bool, ...]
    lanes: tuple[BatchLaneCompletion, ...]
    status: str
    problems: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_execution_id": self.batch_execution_id,
            "wave_index": self.wave_index,
            "physical_batch_size": self.physical_batch_size,
            "symbol_batch": self.physical_batch_size,
            "active_mask_before": list(self.active_mask_before),
            "active_mask_after": list(self.active_mask_after),
            "status": self.status,
            "problems": list(self.problems),
            "lanes": [lane.to_dict() for lane in self.lanes],
        }


@dataclass
class _LaneHistory:
    session: Session
    tokens: list[int] = dc_field(default_factory=list)
    commit_ticks: list[int] = dc_field(default_factory=list)
    transaction_ids: list[int] = dc_field(default_factory=list)
    submitted_waves: list[int] = dc_field(default_factory=list)
    retired_wave: int | None = None
    eos_reason: int = EosReason.NONE


class BatchScheduler:
    """One physical dynamic-batch execution over independent ABI sessions.

    The scheduler admits exactly one submission for every currently active
    lane in each wave.  After a lane returns EOS (or the declared length stop),
    its active-mask bit clears and any later attempt to submit it is rejected
    before the device can read or write its memory.
    """

    def __init__(self, device: Device, sessions: Sequence[Session]) -> None:
        self.device = device
        self.sessions = tuple(sessions)
        self.batch_size = len(self.sessions)
        maximum = int(device.capability.limits["max_sessions"])
        if not 2 <= self.batch_size <= maximum:
            raise BatchError(
                f"physical batch size {self.batch_size} is outside 2..{maximum}"
            )
        if len({session.session_id for session in self.sessions}) != self.batch_size:
            raise BatchError("a batch must contain distinct sessions")
        for lane, session in enumerate(self.sessions):
            if device.sessions.get(session.session_id) is not session:
                raise BatchError(
                    f"lane {lane} session {session.session_id} is not live on device"
                )
            if not session.isolated_memory:
                raise BatchError(
                    f"lane {lane} session {session.session_id} has no private "
                    "writable address space"
                )
            if session.batch_execution_id is not None:
                raise BatchError(
                    f"lane {lane} session {session.session_id} already belongs to "
                    f"batch execution {session.batch_execution_id}"
                )

        self.memory_contract = self._verify_memory_contract()
        self.active = [True] * self.batch_size
        self.history = [_LaneHistory(session=session) for session in self.sessions]
        self.waves: list[BatchWaveResult] = []
        self.failed = False
        self.problems: list[str] = []
        self.batch_execution_id = self._execution_id()
        for session in self.sessions:
            session.batch_execution_id = self.batch_execution_id

    def _execution_id(self) -> str:
        material = {
            "deployment_id": int(self.device.deployment.deployment_id),
            "deployment_generation": int(self.device.deployment.generation),
            "device_start_tick": int(self.device._device_cycle),
            "session_ids": [session.session_id for session in self.sessions],
            "session_generations": [session.generation for session in self.sessions],
            "physical_batch_size": self.batch_size,
        }
        return hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _verify_memory_contract(self) -> dict[str, Any]:
        """Prove mutable disjointness and immutable sharing for every lane."""

        private: list[int] = []
        shared: list[int] = []
        for node in range(self.device.node_count):
            baseline = self.device.node_memories[node]
            lane_memories = [session.node_memories[node] for session in self.sessions]
            if any(memory.node_id != node for memory in lane_memories):
                raise BatchError(f"node {node} session arena has a wrong node binding")
            for object_id, base_object in baseline.objects.items():
                objects = [memory[object_id] for memory in lane_memories]
                identities = {id(obj) for obj in objects}
                if base_object.writable:
                    if len(identities) != self.batch_size or any(
                        obj is base_object for obj in objects
                    ):
                        raise BatchError(
                            f"writable object {object_id} on node {node} is not "
                            "private to every batch session"
                        )
                    private.append(object_id)
                else:
                    if any(obj is not base_object for obj in objects):
                        raise BatchError(
                            f"immutable object {object_id} on node {node} is not "
                            "shared by every batch session"
                        )
                    shared.append(object_id)
        return {
            "status": "verified",
            "mutable_objects_are_session_private": True,
            "immutable_objects_are_shared": True,
            "private_mutable_object_ids": sorted(set(private)),
            "shared_immutable_object_ids": sorted(set(shared)),
        }

    def stage_host_bytes(
        self, lane_index: int, object_id: int, byte_offset: int, payload: bytes
    ) -> None:
        """Write one lane's host window without touching any sibling lane."""

        self._require_lane(lane_index)
        if not self.active[lane_index]:
            raise BatchError(
                f"lane {lane_index} is retired; no post-EOS host write is allowed"
            )
        self.device.host_write(
            object_id,
            byte_offset,
            payload,
            session=self.sessions[lane_index],
        )

    def _require_lane(self, lane_index: int) -> None:
        if not 0 <= int(lane_index) < self.batch_size:
            raise BatchError(
                f"lane {lane_index} is outside physical batch {self.batch_size}"
            )

    def _decode_wave(
        self, submissions: Sequence[BatchLaneSubmission]
    ) -> list[tuple[BatchLaneSubmission, Submission]]:
        if self.failed:
            raise BatchError("the batch has failed; no later wave may execute")
        expected = {lane for lane, active in enumerate(self.active) if active}
        if not expected:
            raise BatchError("all batch lanes are retired; no later wave may execute")
        observed = [int(item.lane_index) for item in submissions]
        if len(set(observed)) != len(observed):
            raise BatchError("a scheduler wave contains a duplicate lane")
        if set(observed) != expected:
            raise BatchError(
                f"wave must submit every active lane exactly once; active="
                f"{sorted(expected)}, submitted={sorted(observed)}"
            )

        decoded: list[tuple[BatchLaneSubmission, Submission]] = []
        transaction_ids: set[int] = set()
        phase_flags: int | None = None
        entrypoint_id: int | None = None
        for item in sorted(submissions, key=lambda value: value.lane_index):
            lane = int(item.lane_index)
            self._require_lane(lane)
            try:
                request = Submission.decode(item.record)
            except Exception as exc:
                raise BatchError(
                    f"lane {lane} has an invalid ABI submission: {exc}"
                ) from exc
            session = self.sessions[lane]
            if request.host_opcode != int(HostOpcode.GENERATE):
                raise BatchError(f"lane {lane} submission is not GENERATE")
            if (
                request.deployment_id != self.device.deployment.deployment_id
                or request.deployment_generation != self.device.deployment.generation
            ):
                raise BatchError(f"lane {lane} submission names a different deployment")
            if request.session_id != session.session_id:
                raise BatchError(
                    f"lane {lane} submission names session {request.session_id}, "
                    f"expected {session.session_id}"
                )
            if request.session_generation != session.generation:
                raise BatchError(
                    f"lane {lane} submission generation {request.session_generation} "
                    f"does not match live generation {session.generation}"
                )
            if request.transaction_id in transaction_ids:
                raise BatchError("transaction IDs must be unique within a batch wave")
            transaction_ids.add(request.transaction_id)
            if item.symbols.get(int(Symbol.BATCH)) != self.batch_size:
                raise BatchError(
                    f"lane {lane} does not bind Symbol.BATCH={self.batch_size}"
                )
            flags = int(request.flags) & int(
                SubmissionFlag.PREFILL_PHASE | SubmissionFlag.DECODE_PHASE
            )
            if flags not in {
                int(SubmissionFlag.PREFILL_PHASE),
                int(SubmissionFlag.DECODE_PHASE),
            }:
                raise BatchError(f"lane {lane} does not declare exactly one phase")
            if phase_flags is None:
                phase_flags = flags
                entrypoint_id = request.entrypoint_id
            elif flags != phase_flags or request.entrypoint_id != entrypoint_id:
                raise BatchError(
                    "one batch wave must use one phase and one entrypoint; ragged "
                    "request extents remain legal through per-lane symbols"
                )
            decoded.append((item, request))
        return decoded

    def submit_wave(
        self, submissions: Sequence[BatchLaneSubmission]
    ) -> BatchWaveResult:
        """Execute one shared active-mask wave and return scalar completions."""

        decoded = self._decode_wave(submissions)
        before = tuple(self.active)
        completions: list[BatchLaneCompletion] = []
        problems: list[str] = []
        wave_index = len(self.waves)

        # Structural slice boundary: the scheduler owns one B=N wave, but the
        # functional engine dispatcher is still invoked lane-serially.  This is
        # deliberately visible in evidence and cannot qualify timing.
        for item, request in decoded:
            lane = int(item.lane_index)
            session = self.sessions[lane]
            policy_id = request.generation_policy_id
            if policy_id == NO_ID:
                entry = self.device._entrypoints.get(request.entrypoint_id)
                policy_id = NO_ID if entry is None else entry["generation_policy_id"]
            result = self.device.run_transaction(
                session,
                entrypoint_id=request.entrypoint_id,
                symbols=dict(item.symbols),
                generation_policy_id=policy_id,
                batch_execution_id=self.batch_execution_id,
            )
            completion = Completion(
                status=result.status,
                transaction_id=request.transaction_id,
                deployment_id=request.deployment_id,
                deployment_generation=request.deployment_generation,
                session_id=request.session_id,
                session_generation=session.generation,
                trap_class=result.trap_class,
                committed_token_position=session.position,
                produced_token_count=len(result.produced_tokens),
                committed_state_generation=session.generation,
                first_fault_instruction=result.first_fault_instruction,
                idempotency_key=request.idempotency_key,
                final_token_id=result.selected_token,
                eos_reason=result.eos_reason,
                retired_work=result.retired,
                completion_timestamp=self.device._device_cycle,
            )
            record = completion.encode()
            completion = Completion.decode(record)
            history = self.history[lane]
            history.submitted_waves.append(wave_index)
            history.transaction_ids.append(completion.transaction_id)
            history.tokens.extend(int(token) for token in result.produced_tokens)
            if result.produced_tokens:
                history.commit_ticks.append(completion.completion_timestamp)

            active_after = result.status == CompletionStatus.SUCCESS
            if (
                result.status == CompletionStatus.SUCCESS
                and len(result.produced_tokens) != 1
            ):
                active_after = False
                problems.append(
                    f"lane {lane} successful GENERATE transaction produced "
                    f"{len(result.produced_tokens)} tokens; one scalar ABI "
                    "completion cannot provide independent commit ticks for it"
                )
            if result.eos_reason != EosReason.NONE:
                active_after = False
                history.retired_wave = wave_index
                history.eos_reason = int(result.eos_reason)
            if result.status != CompletionStatus.SUCCESS:
                active_after = False
                problems.append(
                    f"lane {lane} transaction {request.transaction_id} failed: "
                    f"{result.message}"
                )
            self.active[lane] = active_after
            completions.append(
                BatchLaneCompletion(
                    lane_index=lane,
                    session_id=session.session_id,
                    record=record,
                    completion=completion,
                    result=result,
                    symbol_batch=self.batch_size,
                    active_after=active_after,
                )
            )

        if problems:
            self.failed = True
            self.problems.extend(problems)
            # First-fault policy is fail-stop at the wave boundary.  Successful
            # sibling completions remain diagnostic but no later wave runs.
            self.active = [False] * self.batch_size
        wave = BatchWaveResult(
            batch_execution_id=self.batch_execution_id,
            wave_index=wave_index,
            physical_batch_size=self.batch_size,
            active_mask_before=before,
            active_mask_after=tuple(self.active),
            lanes=tuple(completions),
            status="rejected" if problems else "executed",
            problems=tuple(problems),
        )
        self.waves.append(wave)
        return wave

    def evidence(
        self, expected_tokens: Sequence[Sequence[int]] | None = None
    ) -> dict[str, Any]:
        """Return fail-closed structural evidence for the execution so far.

        ``expected_tokens`` is an independent caller-supplied stream.  Every
        lane must match exactly; one mismatch rejects the whole structural
        result.  Even a matching result remains explicitly ineligible for the
        project's full-model Gate 1 until co-issue and the governed workload
        runner bind this scheduler to a production execution.
        """

        problems = list(self.problems)
        expected: tuple[tuple[int, ...], ...] | None = None
        if expected_tokens is not None:
            expected = tuple(
                tuple(int(token) for token in row) for row in expected_tokens
            )
            if len(expected) != self.batch_size:
                problems.append(
                    f"expected stream count {len(expected)} does not match batch "
                    f"size {self.batch_size}"
                )

        sequences: list[dict[str, Any]] = []
        for lane, history in enumerate(self.history):
            actual = tuple(history.tokens)
            match: bool | None = None
            first_divergence: int | None = None
            if expected is not None and len(expected) == self.batch_size:
                wanted = expected[lane]
                match = actual == wanted
                if not match:
                    common = min(len(actual), len(wanted))
                    first_divergence = next(
                        (
                            index
                            for index in range(common)
                            if actual[index] != wanted[index]
                        ),
                        common,
                    )
                    problems.append(
                        f"lane {lane} token mismatch at index {first_divergence}: "
                        f"actual={list(actual)}, expected={list(wanted)}"
                    )
            later_waves = (
                []
                if history.retired_wave is None
                else [
                    wave
                    for wave in history.submitted_waves
                    if wave > history.retired_wave
                ]
            )
            if later_waves:
                problems.append(
                    f"lane {lane} executed waves {later_waves} after retirement at "
                    f"wave {history.retired_wave}"
                )
            sequences.append(
                {
                    "sequence_index": lane,
                    "session_id": history.session.session_id,
                    "generated_token_ids": list(actual),
                    "token_commit_ticks": list(history.commit_ticks),
                    "transaction_ids": list(history.transaction_ids),
                    "submitted_waves": list(history.submitted_waves),
                    "retired_wave": history.retired_wave,
                    "eos_reason": history.eos_reason,
                    "active": self.active[lane],
                    "expected_tokens_match": match,
                    "first_divergence_index": first_divergence,
                    "post_retirement_transaction_count": len(later_waves),
                    "no_post_eos_transaction": not later_waves,
                }
            )

        in_progress = any(self.active)

        return {
            "schema": STRUCTURAL_BATCH_SCHEMA,
            "status": (
                "rejected"
                if problems
                else "in_progress"
                if in_progress
                else "structurally_executed"
            ),
            "batch_execution_id": self.batch_execution_id,
            "physical_batch_size": self.batch_size,
            "symbol_batch": self.batch_size,
            "scheduler": "shared_session_wave_v1",
            "active_mask": list(self.active),
            "memory_contract": self.memory_contract,
            "sequences": sequences,
            "waves": [wave.to_dict() for wave in self.waves],
            "problems": problems,
            "claim_boundary": {
                "one_shared_batch_scheduler": True,
                "repeated_independent_b1_driver_loops": False,
                "abi3_wire_format_changed": False,
                "scalar_completion_per_session": True,
                "symbol_batch_bound_to_physical_batch_size": True,
                "engine_coissue_implemented": False,
                "shared_resource_cycle_timing_implemented": False,
                "eligible_for_full_model_token_correctness_gate": False,
                "eligible_for_target_tpot": False,
                "remaining_boundary": (
                    "inter-instruction engine co-issue, shared-resource timing, "
                    "governed full-model batch runner, and RTL session scheduler"
                ),
            },
        }


__all__ = [
    "BatchError",
    "BatchLaneCompletion",
    "BatchLaneSubmission",
    "BatchScheduler",
    "BatchWaveResult",
    "STRUCTURAL_BATCH_SCHEMA",
]
