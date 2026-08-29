"""ABI 3.0 functional device: microsequencer, state transactions, host queue.

This is the single execution engine for all four targets.  A target is a set of
descriptors, not a code path: Qwen on one HBM chip, DeepSeek on 32 HBM nodes,
Qwen on a ROM chip and DeepSeek on a ROM wafer all enter here, and every counter
they produce comes from the same registry and the same accounting sites.  That
is the structural reason their numbers are comparable.

Control comes only from the compiled program.  The host may submit a bounded
request, and it may read back token IDs; it may not sequence device operations,
select a token, or supply an activation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Control,
    CompletionStatus,
    DType,
    HostOpcode,
    InstructionFlag,
    Major,
    NO_ID,
    Observation,
    Recovery,
    Selection,
    State,
    StorageClass,
    SubmissionFlag,
    CompletionFlag,
    TrapClass,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import (
    Comparison,
    Descriptor,
    ExtendedDescriptorType,
    Phase,
    PredicateKind,
    SelectorKind,
    Symbol,
    decode_entrypoint_table,
)
from runtime.abi3.records import (
    Completion,
    EosReason,
    Instruction,
    Submission,
    decode_body,
    split_program,
)
from runtime.abi3.verifier import require_admitted, VerificationReport
from runtime.sim.counters import CounterSet
from runtime.sim.engine import EngineContext, EngineError, dispatch
from runtime.sim.memory import DeviceMemory, MemoryError_, ViewResolver


class DeviceTrap(Exception):
    """A precise or asynchronous trap.  Never converted into a success."""

    def __init__(self, message: str, trap_class: int, instruction: int = NO_ID) -> None:
        super().__init__(message)
        self.trap_class = int(trap_class)
        self.instruction = instruction


# ---------------------------------------------------------------------------
# Transactional state
# ---------------------------------------------------------------------------
@dataclass
class StateResource:
    """One session-bound mutable state resource."""

    descriptor_id: int
    state_class: int
    committed_object_id: int
    prepared_object_id: int
    row_bytes: int
    capacity_rows: int
    cursor_rows: int = 0
    generation: int = 0
    open_prepare: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "descriptor_id": self.descriptor_id,
            "state_class": self.state_class,
            "cursor_rows": self.cursor_rows,
            "generation": self.generation,
            "capacity_rows": self.capacity_rows,
            "row_bytes": self.row_bytes,
        }


@dataclass
class Session:
    """Host-visible session state: position, generation, tokens, resources."""

    session_id: int
    generation: int = 1
    position: int = 0
    states: dict[int, StateResource] = dc_field(default_factory=dict)
    tokens: list[int] = dc_field(default_factory=list)
    generated: list[int] = dc_field(default_factory=list)
    finished: bool = False
    eos_reason: int = EosReason.NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "generation": self.generation,
            "position": self.position,
            "token_count": len(self.tokens),
            "generated_count": len(self.generated),
            "finished": self.finished,
            "eos_reason": self.eos_reason,
            "states": [s.to_dict() for s in self.states.values()],
        }


@dataclass
class PendingCommit:
    """A staged state commit, applied only when the transaction completes."""

    resource: StateResource
    rows: int


# ---------------------------------------------------------------------------
# Transaction result
# ---------------------------------------------------------------------------
@dataclass
class TransactionResult:
    status: int
    trap_class: int = TrapClass.NONE
    first_fault_instruction: int = NO_ID
    retired: int = 0
    fetched: int = 0
    predicated_off: int = 0
    selected_token: int = NO_ID
    eos_reason: int = EosReason.NONE
    produced_tokens: tuple[int, ...] = ()
    counters: dict[str, int] = dc_field(default_factory=dict)
    message: str = ""
    wall_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": int(self.status),
            "status_name": CompletionStatus(self.status).name,
            "trap_class": int(self.trap_class),
            "trap_name": TrapClass(self.trap_class).name,
            "first_fault_instruction": self.first_fault_instruction,
            "retired": self.retired,
            "fetched": self.fetched,
            "predicated_off": self.predicated_off,
            "selected_token": self.selected_token,
            "eos_reason": self.eos_reason,
            "produced_tokens": list(self.produced_tokens),
            "message": self.message,
            "counters": dict(sorted(self.counters.items())),
        }


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------
class Device:
    """One activated ABI 3.0 deployment on one logical accelerator."""

    def __init__(
        self,
        deployment: Deployment,
        capability: Capability,
        *,
        root: Path | None = None,
        verify: bool = True,
        trace: bool = False,
        on_issue: Any = None,
    ) -> None:
        self.deployment = deployment
        self.capability = capability
        self.report: VerificationReport | None = None
        if verify:
            self.report = require_admitted(deployment, capability)
        self.header, body = split_program(deployment.program)
        self.instructions = decode_body(body)
        self.memory = DeviceMemory(deployment, root=root)
        self.views = ViewResolver(deployment, self.memory)
        self.counters = CounterSet()
        self.sessions: dict[int, Session] = {}
        self.trace_enabled = trace
        self.trace: list[dict[str, Any]] = []
        self.on_issue = on_issue
        """Optional hook called after each engine issue.

        Signature ``(pc, instruction, family, ctx) -> None``. It exists because
        arena slots are reused: ``sequence.embedding`` shares a slot with all
        thirty-six layer residuals, so reading an activation after a
        transaction returns whichever tensor last occupied that slot, not the
        one asked for. Any comparison against a reference has to sample at the
        moment the producing engine writes, and this is that moment.
        """
        self._entrypoints = self._load_entrypoints()
        self._next_session = 1
        self._device_cycle = 0

    # -- setup -----------------------------------------------------------
    def _load_entrypoints(self) -> dict[int, dict[str, int]]:
        descriptor = self.deployment.table.get(
            self.header.entrypoint_table_descriptor,
            ExtendedDescriptorType.ENTRYPOINT_TABLE,
        )
        assert descriptor.raw_payload is not None
        return {e["entrypoint_id"]: e for e in decode_entrypoint_table(descriptor.raw_payload)}

    def create_session(self) -> Session:
        session = Session(session_id=self._next_session)
        self._next_session += 1
        for did in self.deployment.table.ids_of_type(ExtendedDescriptorType.STATE):
            payload = self.deployment.table[did].payload
            session.states[did] = StateResource(
                descriptor_id=did,
                state_class=payload["state_class"],
                committed_object_id=payload["committed_object_id"],
                prepared_object_id=payload["prepared_object_id"],
                row_bytes=payload["row_bytes"],
                capacity_rows=payload["capacity_rows"],
                cursor_rows=payload["initial_cursor_rows"],
            )
        self.sessions[session.session_id] = session
        return session

    # -- predicate evaluation --------------------------------------------
    def _evaluate_predicate(
        self, descriptor: Descriptor, loops: Mapping[int, int], symbols: Mapping[int, int]
    ) -> bool:
        payload = descriptor.payload
        kind = PredicateKind(payload["predicate_kind"])
        if kind is PredicateKind.ALWAYS:
            return True
        if kind is PredicateKind.PHASE_IS:
            return symbols[int(Symbol.PHASE)] == payload["immediate"]
        if kind in (PredicateKind.COMPARE_SYMBOL, PredicateKind.COMPARE_LOOP):
            if kind is PredicateKind.COMPARE_SYMBOL:
                left = symbols.get(payload["selector_index"])
                if left is None:
                    raise DeviceTrap(
                        f"predicate {descriptor.descriptor_id}: unbound symbol",
                        TrapClass.DESCRIPTOR_OR_ADDRESS,
                    )
            else:
                left = loops.get(payload["selector_index"])
                if left is None:
                    raise DeviceTrap(
                        f"predicate {descriptor.descriptor_id}: loop not active",
                        TrapClass.ILLEGAL_INSTRUCTION_OR_CONTROL_FLOW,
                    )
            right = payload["immediate"]
            return _compare(Comparison(payload["comparison"]), left, right)
        if kind is PredicateKind.LOOP_FIRST:
            return loops.get(payload["selector_index"], -1) == 0
        if kind is PredicateKind.LOOP_LAST:
            loop = self.deployment.table[payload["selector_index"]]
            trip = self._loop_trip(loop, symbols)
            return loops.get(payload["selector_index"], -1) == trip - 1
        if kind is PredicateKind.BOOLEAN_OBJECT:
            obj = self.memory[payload["object_id"]]
            raw = obj.read(payload["element_index"] * 4, 4)
            return int.from_bytes(raw, "little") != 0
        if kind is PredicateKind.EOS_MEMBER:
            obj = self.memory[payload["object_id"]]
            raw = obj.read(payload["element_index"] * 4, 4)
            return int.from_bytes(raw, "little") != 0
        raise DeviceTrap(
            f"predicate kind {kind.name} is not implemented",
            TrapClass.CAPABILITY_OR_RESOURCE,
        )

    def _loop_trip(self, loop: Descriptor, symbols: Mapping[int, int]) -> int:
        payload = loop.payload
        step = payload["step"]
        if step == 0:
            raise DeviceTrap(
                f"loop {loop.descriptor_id} declares a zero step; a zero-step "
                "loop has no finite trip count",
                TrapClass.ILLEGAL_INSTRUCTION_OR_CONTROL_FLOW,
            )
        if payload["bound_selector_kind"] == SelectorKind.CONSTANT:
            span = payload["upper_bound"] - payload["lower_bound"]
        else:
            symbol = payload["bound_symbol_id"]
            try:
                bound = symbols[symbol]
            except KeyError:
                raise DeviceTrap(
                    f"loop {loop.descriptor_id}: symbol {symbol} is unbound",
                    TrapClass.DESCRIPTOR_OR_ADDRESS,
                ) from None
            divisor = max(payload["bound_divisor"], 1)
            bound = (bound + divisor - 1) // divisor
            span = bound - payload["lower_bound"]
        trip = max((span + step - 1) // step, 0)
        if trip > payload["max_iterations"]:
            raise DeviceTrap(
                f"loop {loop.descriptor_id}: runtime trip {trip} exceeds the "
                f"verified maximum {payload['max_iterations']}",
                TrapClass.CAPABILITY_OR_RESOURCE,
            )
        return trip

    # -- transaction ------------------------------------------------------
    def run_transaction(
        self,
        session: Session,
        *,
        entrypoint_id: int,
        symbols: Mapping[int, int],
        generation_policy_id: int = NO_ID,
    ) -> TransactionResult:
        """Execute one device transaction to COMPLETE or to a trap.

        State commits are staged and applied only on a successful COMPLETE, so a
        fault can never expose a partially advanced token position.
        """
        started = time.perf_counter()
        entry = self._entrypoints.get(entrypoint_id)
        if entry is None:
            return TransactionResult(
                status=CompletionStatus.FAILED,
                trap_class=TrapClass.ADMISSION_OR_VERSION,
                message=f"unknown entrypoint {entrypoint_id}",
            )
        if session.finished:
            return TransactionResult(
                status=CompletionStatus.FAILED,
                trap_class=TrapClass.STATE_TRANSACTION,
                message="session already returned EOS; no post-EOS transaction",
            )
        symbols = dict(symbols)
        symbols.setdefault(int(Symbol.PHASE), entry["phase"])
        symbols.setdefault(int(Symbol.GENERATION_INDEX), len(session.generated))
        counters = CounterSet()
        loops: dict[int, int] = {}
        pending: list[PendingCommit] = []
        signalled: set[int] = set()
        produced: list[int] = []
        selection: dict[str, Any] = {}
        ctx = EngineContext(
            table=self.deployment.table,
            memory=self.memory,
            views=self.views,
            counters=counters,
            loops=loops,
            symbols=symbols,
            session=session,
            device=self,
        )
        ctx.notes["produced_tokens"] = produced
        ctx.notes["selection"] = selection
        ctx.notes["generation_policy_id"] = generation_policy_id
        ctx.notes["pending_commits"] = pending

        pc = entry["first_instruction"]
        loop_stack: list[tuple[int, int, int]] = []  # (loop id, trip, body_start)
        retired = 0
        fetched = 0
        predicated_off = 0
        fault: DeviceTrap | None = None
        completed = False
        work_bound = self.header.max_retired_work

        try:
            while 0 <= pc < len(self.instructions):
                instruction = self.instructions[pc]
                fetched += 1
                counters.add("instructions.fetched")
                if retired > work_bound:
                    raise DeviceTrap(
                        f"retired work exceeded the verified bound {work_bound}",
                        TrapClass.TIMEOUT_OR_WATCHDOG,
                        pc,
                    )
                # -- predicate
                if instruction.flags & InstructionFlag.PREDICATED:
                    descriptor = self.deployment.table.get(
                        instruction.predicate_id, ExtendedDescriptorType.PREDICATE
                    )
                    taken = self._evaluate_predicate(descriptor, loops, symbols)
                    if instruction.flags & InstructionFlag.PREDICATE_INVERT:
                        taken = not taken
                    if not taken:
                        predicated_off += 1
                        counters.add("instructions.predicated_off")
                        pc += 1
                        continue
                # -- wait
                if instruction.wait_set_id != NO_ID:
                    wait = self.deployment.table.get(
                        instruction.wait_set_id, ExtendedDescriptorType.EVENT_WAIT_SET
                    )
                    counters.add("queue.wait_events")
                    for slot in range(wait.payload["producer_count"]):
                        event = wait.payload[f"producer_{slot}"]
                        if event not in signalled:
                            raise DeviceTrap(
                                f"wait on event {event} that has not been signalled",
                                TrapClass.INTERNAL_INVARIANT,
                                pc,
                            )
                family = Major(instruction.major)
                if family is Major.CONTROL:
                    try:
                        pc, done = self._execute_control(
                            instruction, pc, loops, loop_stack, symbols, counters
                        )
                    except DeviceTrap as trap:
                        # A trap raised below the control handler may not know
                        # its own program counter; a completion that reports
                        # NO_ID where a precise index exists is a worse
                        # diagnostic than the fault itself.
                        if trap.instruction == NO_ID:
                            trap.instruction = pc
                        raise
                    if instruction.signal_event_id != NO_ID:
                        # Nothing in the wire format exempts CONTROL from
                        # publishing an event; the asymmetry was accidental.
                        signalled.add(instruction.signal_event_id)
                    retired += 1
                    counters.add("instructions.retired")
                    if done:
                        completed = True
                        break
                    continue
                # -- engine issue
                counters.add("instructions.issued")
                try:
                    self._issue(ctx, instruction, family)
                except DeviceTrap as trap:
                    if trap.instruction == NO_ID:
                        trap.instruction = pc
                    raise
                if self.on_issue is not None:
                    self.on_issue(pc, instruction, family, ctx)
                if instruction.signal_event_id != NO_ID:
                    signalled.add(instruction.signal_event_id)
                retired += 1
                counters.add("instructions.retired")
                if self.trace_enabled:
                    self.trace.append(
                        {
                            "pc": pc,
                            "mnemonic": instruction.mnemonic,
                            "descriptor": instruction.descriptor_id,
                            "loops": dict(loops),
                        }
                    )
                pc += 1
            else:
                if not completed:
                    raise DeviceTrap(
                        "program ran off the end without COMPLETE",
                        TrapClass.ILLEGAL_INSTRUCTION_OR_CONTROL_FLOW,
                        pc,
                    )
        except DeviceTrap as trap:
            fault = trap
        except (EngineError, MemoryError_) as exc:
            trap_class = getattr(exc, "trap_class", TrapClass.ENGINE)
            fault = DeviceTrap(str(exc), trap_class, pc)

        wall = time.perf_counter() - started
        if fault is not None:
            counters.add("fault.traps")
            counters.add("fault.poisoned_transactions")
            for commit in pending:
                commit.resource.open_prepare = False
            self.counters.merge(counters)
            return TransactionResult(
                status=CompletionStatus.FAILED,
                trap_class=fault.trap_class,
                first_fault_instruction=fault.instruction,
                retired=retired,
                fetched=fetched,
                predicated_off=predicated_off,
                counters=counters.snapshot(),
                message=str(fault),
                wall_seconds=wall,
            )

        # -- atomic commit of the whole declared state set
        for commit in pending:
            self._apply_commit(commit, counters)
        session.generation += 1
        for token in produced:
            session.tokens.append(token)
            session.generated.append(token)
        eos_reason = int(selection.get("eos_reason", EosReason.NONE))
        if eos_reason == EosReason.OFFICIAL_EOS:
            session.finished = True
            session.eos_reason = eos_reason
            counters.add("selection.eos_stops")
        session.position = symbols.get(int(Symbol.POSITION_END), session.position)
        self.counters.merge(counters)
        self._device_cycle += retired
        return TransactionResult(
            status=CompletionStatus.SUCCESS,
            retired=retired,
            fetched=fetched,
            predicated_off=predicated_off,
            selected_token=int(selection.get("token", NO_ID)),
            eos_reason=eos_reason,
            produced_tokens=tuple(produced),
            counters=counters.snapshot(),
            wall_seconds=wall,
        )

    # -- control ----------------------------------------------------------
    def _execute_control(
        self,
        instruction: Instruction,
        pc: int,
        loops: dict[int, int],
        loop_stack: list[tuple[int, int, int]],
        symbols: Mapping[int, int],
        counters: CounterSet,
    ) -> tuple[int, bool]:
        sub = Control(instruction.sub)
        if sub is Control.NOP:
            return pc + 1, False
        if sub is Control.LOOP_SETUP:
            loop = self.deployment.table.get(
                instruction.control_id, ExtendedDescriptorType.LOOP_CONTROL
            )
            trip = self._loop_trip(loop, symbols)
            if trip == 0:
                # Zero-trip loop: skip the body and its LOOP_NEXT.
                return loop.payload["body_end"] + 1, False
            loops[instruction.control_id] = loop.payload["lower_bound"]
            loop_stack.append(
                (instruction.control_id, trip, loop.payload["body_start"])
            )
            return pc + 1, False
        if sub is Control.LOOP_NEXT:
            if not loop_stack:
                raise DeviceTrap(
                    "LOOP_NEXT with no open loop",
                    TrapClass.ILLEGAL_INSTRUCTION_OR_CONTROL_FLOW,
                    pc,
                )
            loop_id, trip, body_start = loop_stack[-1]
            loop = self.deployment.table[loop_id]
            step = loop.payload["step"]
            current = loops[loop_id] + step
            counters.add("control.loop_iterations")
            if (current - loop.payload["lower_bound"]) // step < trip:
                loops[loop_id] = current
                return body_start, False
            loop_stack.pop()
            loops.pop(loop_id, None)
            return pc + 1, False
        if sub is Control.BRANCH:
            counters.add("control.branches_taken")
            return instruction.control_id, False
        if sub is Control.WAIT:
            return pc + 1, False
        if sub is Control.FENCE:
            return pc + 1, False
        if sub is Control.ASSERT:
            return pc + 1, False
        if sub is Control.COMPLETE:
            return pc, True
        if sub is Control.TRAP:
            raise DeviceTrap(
                "program executed an explicit TRAP",
                TrapClass.ILLEGAL_INSTRUCTION_OR_CONTROL_FLOW,
                pc,
            )
        raise DeviceTrap(
            f"unhandled control subopcode {sub.name}",
            TrapClass.ILLEGAL_INSTRUCTION_OR_CONTROL_FLOW,
            pc,
        )

    # -- engine issue ------------------------------------------------------
    _FAMILY_COUNTER = {
        Major.DMA: "engine.dma.descriptors",
        Major.TENSOR: "engine.tensor.descriptors",
        Major.VECTOR: "engine.vector.descriptors",
        Major.ATTENTION: "engine.attention.descriptors",
        Major.ROUTE: "engine.route.descriptors",
        Major.REDUCTION: "engine.reduction.descriptors",
        Major.SELECTION: "engine.selection.descriptors",
        Major.STATE: "engine.state.descriptors",
        Major.LINK: "engine.link.descriptors",
    }

    def _issue(self, ctx: EngineContext, instruction: Instruction, family: Major) -> None:
        counter = self._FAMILY_COUNTER.get(family)
        if counter:
            ctx.counters.add(counter)
        if family is Major.STATE:
            self._execute_state(ctx, instruction)
            return
        if family is Major.OBSERVATION:
            return
        if family is Major.RECOVERY:
            sub = Recovery(instruction.sub)
            if sub is Recovery.ABORT:
                raise DeviceTrap(
                    "program executed RECOVERY.ABORT",
                    TrapClass.INTERNAL_INVARIANT,
                    NO_ID,
                )
            ctx.counters.add("fault.drains")
            return
        descriptor = self.deployment.table[instruction.descriptor_id]
        dispatch(ctx, int(family), instruction.sub, descriptor)

    def _execute_state(self, ctx: EngineContext, instruction: Instruction) -> None:
        session: Session = ctx.session
        descriptor = self.deployment.table.get(
            instruction.descriptor_id, ExtendedDescriptorType.STATE
        )
        resource = session.states.get(descriptor.descriptor_id)
        if resource is None:
            raise DeviceTrap(
                f"state {descriptor.descriptor_id} is not bound to this session",
                TrapClass.STATE_TRANSACTION,
            )
        sub = State(instruction.sub)
        pending: list[PendingCommit] = ctx.notes["pending_commits"]
        if sub is State.PREPARE:
            if resource.open_prepare:
                raise DeviceTrap(
                    f"state {resource.descriptor_id} is already prepared",
                    TrapClass.STATE_TRANSACTION,
                )
            resource.open_prepare = True
            ctx.counters.add("state.prepares")
            return
        if sub is State.READ:
            ctx.counters.add("state.reads")
            return
        if sub is State.COMMIT:
            if not resource.open_prepare:
                raise DeviceTrap(
                    f"state {resource.descriptor_id} committed without a prepare",
                    TrapClass.STATE_TRANSACTION,
                )
            rows = int(ctx.symbols.get(int(Symbol.SPAN_TOKENS), 0))
            if rows <= 0:
                raise DeviceTrap(
                    "state commit with a non-positive row count",
                    TrapClass.STATE_TRANSACTION,
                )
            # Capacity must be checked against the *staged* total, not the
            # committed cursor: several commits staged in one transaction can
            # each pass individually and still overflow when they are applied.
            staged = sum(
                p.rows for p in pending if p.resource is resource
            )
            if resource.cursor_rows + staged + rows > resource.capacity_rows:
                raise DeviceTrap(
                    f"state {resource.descriptor_id}: committing {rows} rows at "
                    f"cursor {resource.cursor_rows} with {staged} already staged "
                    f"exceeds capacity {resource.capacity_rows}",
                    TrapClass.CAPABILITY_OR_RESOURCE,
                )
            pending.append(PendingCommit(resource, rows))
            ctx.counters.add("state.commits")
            return
        if sub is State.DISCARD:
            resource.open_prepare = False
            ctx.counters.add("state.discards")
            return
        if sub is State.GENERATION_ADVANCE:
            ctx.counters.add("state.generation_advances")
            return
        raise DeviceTrap(
            f"unhandled state subopcode {sub.name}", TrapClass.STATE_TRANSACTION
        )

    def _apply_commit(self, commit: PendingCommit, counters: CounterSet) -> None:
        resource = commit.resource
        rows = commit.rows
        prepared = self.memory[resource.prepared_object_id]
        committed = self.memory[resource.committed_object_id]
        nbytes = rows * resource.row_bytes
        payload = prepared.read(0, nbytes)
        committed.write(resource.cursor_rows * resource.row_bytes, payload)
        resource.cursor_rows += rows
        resource.generation += 1
        resource.open_prepare = False
        counters.add("state.rows_committed", rows)
        counters.add("state.bytes_written", nbytes)

    # -- host queue --------------------------------------------------------
    def submit(self, record: bytes) -> bytes:
        """Execute one encoded host submission and return an encoded completion.

        This is the only entry point a driver uses.  It performs no model
        reasoning: everything after admission is the compiled program.
        """
        try:
            request = Submission.decode(record)
        except Exception as exc:
            return Completion(
                status=CompletionStatus.FAILED,
                transaction_id=0,
                trap_class=TrapClass.AUTHENTICATION_OR_INTEGRITY,
            ).encode()
        opcode = HostOpcode(request.host_opcode)
        if opcode is HostOpcode.CREATE_SESSION:
            session = self.create_session()
            return Completion(
                status=CompletionStatus.SUCCESS,
                transaction_id=request.transaction_id,
                deployment_id=self.deployment.deployment_id,
                deployment_generation=self.deployment.generation,
                session_id=session.session_id,
                session_generation=session.generation,
                idempotency_key=request.idempotency_key,
                completion_timestamp=self._device_cycle,
            ).encode()
        if opcode is HostOpcode.DESTROY_SESSION:
            self.sessions.pop(request.session_id, None)
            return Completion(
                status=CompletionStatus.SUCCESS,
                transaction_id=request.transaction_id,
                session_id=request.session_id,
                idempotency_key=request.idempotency_key,
            ).encode()
        raise NotImplementedError(
            f"host opcode {opcode.name} is driven through the runtime driver"
        )


def _compare(op: Comparison, left: int, right: int) -> bool:
    if op is Comparison.EQ:
        return left == right
    if op is Comparison.NE:
        return left != right
    if op is Comparison.LT:
        return left < right
    if op is Comparison.LE:
        return left <= right
    if op is Comparison.GT:
        return left > right
    return left >= right
