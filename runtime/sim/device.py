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
    #: **Cluster totals.**  One transaction executes the whole program on every
    #: logical node, so these are the sum over all of them plus the work the
    #: cluster does once -- the collectives and the state bookkeeping.  On a
    #: 32-node topology every architectural quantity here is therefore
    #: thirty-two nodes' worth, not one node's; a consumer that wants one
    #: node's share must read :attr:`node_counters`, not divide.
    counters: dict[str, int] = dc_field(default_factory=dict)
    #: One snapshot per logical node, indexed by ``NODE_ID``, holding exactly
    #: the work that node's engines did.  ``LINK`` and ``STATE`` are issued once
    #: for the cluster and appear in no node's share, so
    #: ``sum(node_counters) + cluster-only == counters`` for every additive
    #: counter.  A single-chip transaction has one entry and it is everything.
    node_counters: tuple[dict[str, int], ...] = ()
    message: str = ""
    wall_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """The recorded form of one transaction.

        ``counters`` here is :attr:`counters` -- the **cluster totals**.  The
        per-node split is deliberately not serialised: every recorded artifact
        in this repository is a single-chip run, where the split is one entry
        holding everything, and adding a key would move evidence that has to
        stay byte-identical to say anything.  A consumer that needs the split
        reads it from the result object.
        """
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
def loop_trip_count(
    payload: Mapping[str, Any], symbols: Mapping[int, int]
) -> int:
    """How many times a loop descriptor runs, given its symbol bindings.

    A symbol-bounded loop's induction variable counts *blocks*: the symbol is
    divided by ``bound_divisor`` first, and only then does ``step`` apply.  A
    backend that sets ``step`` to the divisor therefore divides twice and gets
    one iteration at every span, which is correct exactly while the whole
    request fits in a single block.  That defect shipped once and survived
    every gate, because every gate used a prompt shorter than one block.

    This is the single definition.  Anything that needs to know what the device
    will do -- a backend, a checker, a test -- calls it rather than restating
    the formula, because a restatement is what let the two drift apart.
    """
    step = int(payload["step"])
    if step == 0:
        raise ValueError("a zero-step loop has no finite trip count")
    if payload["bound_selector_kind"] == SelectorKind.CONSTANT:
        span = int(payload["upper_bound"]) - int(payload["lower_bound"])
    else:
        bound = int(symbols[int(payload["bound_symbol_id"])])
        divisor = max(int(payload["bound_divisor"]), 1)
        span = (bound + divisor - 1) // divisor - int(payload["lower_bound"])
    return max((span + step - 1) // step, 0)


class Device:
    """One activated ABI 3.0 deployment on one logical accelerator.

    **A transaction is the cluster's, not a node's.**  A 32-node deployment is
    one logical accelerator: :meth:`run_transaction` runs the whole program on
    every node, and :attr:`counters` and
    :attr:`TransactionResult.counters` are therefore *cluster totals* -- the sum
    over all thirty-two nodes plus the work the cluster does once.  They are not
    one node's share and dividing them by ``node_count`` is not one either,
    because the collectives and the state bookkeeping issue once for the whole
    device and belong to no node.  :attr:`node_counters` and
    :attr:`TransactionResult.node_counters` are the per-node split, indexed by
    ``NODE_ID``; a consumer that wants one node's work reads that.
    """

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
        self.node_count = self._declared_node_count()
        self.node_memories: tuple[DeviceMemory, ...] = self._build_node_memories(root)
        self.node_views: tuple[ViewResolver, ...] = tuple(
            ViewResolver(deployment, memory) for memory in self.node_memories
        )
        #: Node zero's arena and resolver.  Every non-LINK engine issue rebinds
        #: these to the node it is issuing for; they are node zero between
        #: instructions so that a host read, a checkpoint or a trace sees a
        #: definite node rather than whichever one ran last.
        self.memory = self.node_memories[0]
        self.views = self.node_views[0]
        #: Cluster totals across every transaction this device has run.  See the
        #: class docstring: on a multi-node topology these are every node's work
        #: added together, plus the cluster-wide families.
        self.counters = CounterSet()
        #: The same history split by logical node, indexed by ``NODE_ID``.  A
        #: ``LINK`` or ``STATE`` instruction issues once for the cluster and is
        #: in none of these, which is why they sum to less than
        #: :attr:`counters` rather than to it exactly.
        self.node_counters: tuple[CounterSet, ...] = tuple(
            CounterSet() for _ in range(self.node_count)
        )
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
    def _declared_node_count(self) -> int:
        """How many logical nodes the admitted TOPOLOGY declares.

        The node count is a property of the deployment, not of the host: a
        32-node cluster program addresses thirty-two arenas whoever submits it,
        and a single chip addresses one.  It is read from the descriptor rather
        than from the capability so that the device executes the topology it
        was admitted against.
        """
        ids = self.deployment.table.ids_of_type(ExtendedDescriptorType.TOPOLOGY)
        if len(ids) != 1:
            raise DeviceTrap(
                f"the deployment declares {len(ids)} TOPOLOGY descriptors; a "
                "logical accelerator has exactly one",
                TrapClass.DESCRIPTOR_OR_ADDRESS,
            )
        count = int(self.deployment.table[ids[0]].payload["node_count"])
        limit = int(self.capability.limits["max_nodes"])
        if not 1 <= count <= limit:
            raise DeviceTrap(
                f"the admitted topology declares {count} nodes; the capability "
                f"admits {limit}",
                TrapClass.CAPABILITY_OR_RESOURCE,
            )
        return count

    def _build_node_memories(self, root: Path | None) -> tuple[DeviceMemory, ...]:
        """One arena per logical node.

        ADR-003 section 3.3 makes the 32-node cluster a real topology and
        section 8.8 makes the fabric a first-class engine, which together say
        what memory has to look like: node-private state and no implicit
        coherent global address space.  So each node gets its own arena, its own
        activation buffers and its own state images, and the *only* way bytes
        cross from one to another is a LINK instruction naming a COMMUNICATION
        descriptor.  Immutable objects -- the mapped checkpoint above all -- are
        shared by reference, because they are the same bytes on every node and
        each node addresses its own shard of them through the ``NODE_ID`` term
        of a tensor view.  A private copy would be thirty-two mappings of one
        156 GB checkpoint and would prove nothing.
        """
        base = DeviceMemory(self.deployment, root=root)
        if self.node_count == 1:
            return (base,)
        arenas = [base]
        for _node in range(1, self.node_count):
            arenas.append(
                DeviceMemory(self.deployment, root=root, share_from=base)
            )
        return tuple(arenas)

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
        if kind in (PredicateKind.BOOLEAN_OBJECT, PredicateKind.EOS_MEMBER):
            return self._object_predicate(descriptor)
        raise DeviceTrap(
            f"predicate kind {kind.name} is not implemented",
            TrapClass.CAPABILITY_OR_RESOURCE,
        )

    def _object_predicate(self, descriptor: Descriptor) -> bool:
        """A predicate whose truth is a word in device memory.

        Control flow is one program, not thirty-two, so a predicate has one
        answer for the whole device.  Every node is asked and every node must
        give the same answer: a data-dependent branch that came out differently
        on two nodes would mean the nodes are no longer running the same
        program, and continuing would produce a token from a computation that
        never happened on thirty-one of them.
        """
        payload = descriptor.payload
        offset = int(payload["element_index"]) * 4
        answer: bool | None = None
        for node, memory in enumerate(self.node_memories):
            obj = memory[payload["object_id"]]
            taken = int.from_bytes(obj.read(offset, 4), "little") != 0
            if answer is None:
                answer = taken
            elif taken != answer:
                raise DeviceTrap(
                    f"predicate {descriptor.descriptor_id} reads "
                    f"{answer} on node 0 and {taken} on node {node}; control "
                    "flow is one program and cannot diverge across nodes",
                    TrapClass.INTERNAL_INVARIANT,
                )
        return bool(answer)

    def _loop_trip(self, loop: Descriptor, symbols: Mapping[int, int]) -> int:
        payload = loop.payload
        step = payload["step"]
        # The arithmetic lives in loop_trip_count() so that a backend or a test
        # can ask what the device will do without restating the formula.  A
        # restated formula is how the block-loop encoding defect survived: the
        # backend's own tests asserted the fields they had emitted rather than
        # the trip the device would derive from them.
        if step == 0:
            raise DeviceTrap(
                f"loop {loop.descriptor_id} declares a zero step; a zero-step "
                "loop has no finite trip count",
                TrapClass.ILLEGAL_INSTRUCTION_OR_CONTROL_FLOW,
            )
        if payload["bound_selector_kind"] != SelectorKind.CONSTANT:
            symbol = payload["bound_symbol_id"]
            if symbol not in symbols:
                raise DeviceTrap(
                    f"loop {loop.descriptor_id}: symbol {symbol} is unbound",
                    TrapClass.DESCRIPTOR_OR_ADDRESS,
                )
        trip = loop_trip_count(payload, symbols)
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
        # The node dimension.  NODE_COUNT is the admitted topology's and does
        # not change; NODE_ID is rebound by the microsequencer at every engine
        # issue, and is zero for everything that is not one node's work --
        # control flow, state bookkeeping, and the collectives themselves.
        symbols[int(Symbol.NODE_COUNT)] = self.node_count
        symbols[int(Symbol.NODE_ID)] = 0
        # ``counters`` holds only what the *cluster* does once -- control flow,
        # the collectives and the state bookkeeping.  Engine work is accounted
        # to the node that did it and merged in at the end, so the totals this
        # transaction reports are identical to the ones it reported before the
        # split, and the split itself is available beside them.
        counters = CounterSet()
        node_counters: tuple[CounterSet, ...] = tuple(
            CounterSet() for _ in range(self.node_count)
        )
        loops: dict[int, int] = {}
        pending: list[PendingCommit] = []
        signalled: set[int] = set()
        produced: list[int] = []
        selection: dict[str, Any] = {}
        # One token ring and one selection record per node.  Every node runs
        # the whole program and selects its own token; they are required to
        # agree at the end of the transaction, which is the check that says the
        # collectives actually delivered the same activations everywhere.
        node_produced: list[list[int]] = [produced] + [
            [] for _ in range(self.node_count - 1)
        ]
        node_selection: list[dict[str, Any]] = [selection] + [
            {} for _ in range(self.node_count - 1)
        ]
        ctx = EngineContext(
            table=self.deployment.table,
            memory=self.memory,
            views=self.views,
            counters=counters,
            loops=loops,
            symbols=symbols,
            session=session,
            device=self,
            node_memories=self.node_memories if self.node_count > 1 else (),
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
                    self._issue_nodes(
                        ctx,
                        instruction,
                        family,
                        node_produced,
                        node_selection,
                        node_counters,
                    )
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

        def _totals() -> CounterSet:
            """Fold the node sets into the cluster totals, once, at the end.

            Every counter is additive -- nothing in the registry is a maximum
            that any engine writes -- so summing the per-node sets into the
            cluster-only set reproduces exactly the totals a single shared set
            produced before the split.  It is done here rather than per issue so
            that the split costs one merge per transaction rather than one per
            instruction per node.
            """
            for share in node_counters:
                counters.merge(share)
            for node, share in enumerate(node_counters):
                self.node_counters[node].merge(share)
            return counters

        if fault is not None:
            counters.add("fault.traps")
            counters.add("fault.poisoned_transactions")
            # ADR-003 8.6: an abort discards prepared state. Clearing only the
            # resources that reached a staged commit left a resource that was
            # prepared and then faulted before its commit still marked open,
            # which would refuse a legitimate retry as a double prepare. The
            # whole declared state set is discarded, which is what "one atomic
            # architectural transition" means in the failing direction too.
            for resource in session.states.values():
                resource.open_prepare = False
            counters.add("state.discards", len(session.states))
            shares = tuple(share.snapshot() for share in node_counters)
            self.counters.merge(_totals())
            return TransactionResult(
                status=CompletionStatus.FAILED,
                trap_class=fault.trap_class,
                first_fault_instruction=fault.instruction,
                retired=retired,
                fetched=fetched,
                predicated_off=predicated_off,
                counters=counters.snapshot(),
                node_counters=shares,
                message=str(fault),
                wall_seconds=wall,
            )

        # -- every node must have selected the same token
        if self.node_count > 1:
            fault = self._node_agreement(node_produced, node_selection)
            if fault is not None:
                counters.add("fault.traps")
                counters.add("fault.poisoned_transactions")
                for resource in session.states.values():
                    resource.open_prepare = False
                shares = tuple(share.snapshot() for share in node_counters)
                self.counters.merge(_totals())
                return TransactionResult(
                    status=CompletionStatus.FAILED,
                    trap_class=TrapClass.INTERNAL_INVARIANT,
                    first_fault_instruction=pc,
                    retired=retired,
                    fetched=fetched,
                    predicated_off=predicated_off,
                    counters=counters.snapshot(),
                    node_counters=shares,
                    message=fault,
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
        shares = tuple(share.snapshot() for share in node_counters)
        self.counters.merge(_totals())
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
            node_counters=shares,
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

    def _issue_nodes(
        self,
        ctx: EngineContext,
        instruction: Instruction,
        family: Major,
        node_produced: list[list[int]],
        node_selection: list[dict[str, Any]],
        node_counters: Sequence[CounterSet],
    ) -> None:
        """Issue one instruction on every logical node, or once for the cluster.

        A compute engine sees exactly one node: its arena, its state images, and
        ``NODE_ID`` bound to it.  Thirty-two nodes therefore run the same
        program over thirty-two private memories, which is what a cluster is,
        and a node cannot read another's activation because it cannot address
        it.

        Two families are issued once rather than per node.  **LINK** is the
        fabric itself: a collective is one architectural operation over the
        whole participant set, and :mod:`runtime.sim.engines.link` reaches every
        node's arena through :attr:`EngineContext.node_memories` to perform it.
        **STATE** is session bookkeeping -- a prepare, a staged commit, a
        generation advance -- and the bytes it moves are applied per node in
        :meth:`_apply_commit`; running the bookkeeping thirty-two times would
        stage thirty-two commits of the same rows.

        Issuing node by node inside one instruction is a stronger
        synchronisation than the machine needs -- it is a barrier at every
        instruction rather than at every collective -- and it is the reason the
        collectives are trivially well-defined: when a LINK instruction issues,
        every node has retired every instruction before it.  Nothing in the
        program can observe the difference, because a node's only window onto
        another node is a LINK instruction.

        Each node's engine work is accounted to ``node_counters[node]``, which
        is what makes :attr:`TransactionResult.node_counters` a real split
        rather than a division: the collectives and the state bookkeeping above
        are issued once and stay in the cluster-only set.

        Everything this rebinds is restored to **what the caller had**, not to
        node zero.  Restoring a constant was a defect: a caller that had bound
        ``NODE_ID`` itself -- to run a transaction as some particular node --
        found it silently zeroed after the first engine instruction, and every
        later reader of the symbol saw 0 instead of the binding.
        """
        if family is Major.LINK or family is Major.STATE:
            self._issue(ctx, instruction, family)
            return
        previous_memory = ctx.memory
        previous_views = ctx.views
        previous_counters = ctx.counters
        previous_produced = ctx.notes.get("produced_tokens")
        previous_selection = ctx.notes.get("selection")
        had_node_id = int(Symbol.NODE_ID) in ctx.symbols
        previous_node_id = ctx.symbols.get(int(Symbol.NODE_ID))
        try:
            for node in range(self.node_count):
                ctx.memory = self.node_memories[node]
                ctx.views = self.node_views[node]
                ctx.counters = node_counters[node]
                ctx.symbols[int(Symbol.NODE_ID)] = node
                ctx.notes["produced_tokens"] = node_produced[node]
                ctx.notes["selection"] = node_selection[node]
                self._issue(ctx, instruction, family)
        finally:
            ctx.memory = previous_memory
            ctx.views = previous_views
            ctx.counters = previous_counters
            ctx.notes["produced_tokens"] = previous_produced
            ctx.notes["selection"] = previous_selection
            if had_node_id:
                assert previous_node_id is not None
                ctx.symbols[int(Symbol.NODE_ID)] = previous_node_id
            else:
                ctx.symbols.pop(int(Symbol.NODE_ID), None)

    def _node_agreement(
        self,
        node_produced: Sequence[Sequence[int]],
        node_selection: Sequence[Mapping[str, Any]],
    ) -> str | None:
        """Refuse a transaction whose nodes did not select the same token.

        Every node runs the whole program, so every node reaches the vocabulary
        projection and every node selects.  They agree only if the collectives
        actually delivered the same activations to all of them; a collective
        that had degenerated into a node-local copy would leave each node
        holding one thirty-second of the logits and they would not.  So this is
        not a defensive check on an invariant that is obviously true -- it is
        the observation that says the fabric ran.
        """
        first = list(node_produced[0])
        for node, tokens in enumerate(node_produced[1:], start=1):
            if list(tokens) != first:
                return (
                    f"node 0 produced {first} and node {node} produced "
                    f"{list(tokens)}; the nodes of one logical accelerator "
                    "must select the same token, so the collectives did not "
                    "deliver the same activations to every node"
                )
        base = node_selection[0].get("token", NO_ID)
        for node, record in enumerate(node_selection[1:], start=1):
            if record.get("token", NO_ID) != base:
                return (
                    f"node 0 selected token {base} and node {node} selected "
                    f"{record.get('token', NO_ID)}"
                )
        return None

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
        """Apply one staged state commit on every node.

        The resource's cursor and generation are session bookkeeping and advance
        once; the bytes are node-local and are copied in each node's own arena,
        which is what a sharded KV cache is.  Counting the rows and bytes per
        node is deliberate: thirty-two nodes really do write thirty-two state
        images, and the byte counters are what the comparison reads.
        """
        resource = commit.resource
        rows = commit.rows
        nbytes = rows * resource.row_bytes
        for memory in self.node_memories:
            prepared = memory[resource.prepared_object_id]
            committed = memory[resource.committed_object_id]
            payload = prepared.read(0, nbytes)
            committed.write(resource.cursor_rows * resource.row_bytes, payload)
            counters.add("state.rows_committed", rows)
            counters.add("state.bytes_written", nbytes)
        resource.cursor_rows += rows
        resource.generation += 1
        resource.open_prepare = False

    # -- host boundary -----------------------------------------------------
    def host_write(self, object_id: int, byte_offset: int, payload: bytes) -> None:
        """Stage host bytes into ``object_id`` on every node.

        The authenticated input window is the one thing the host may write, and
        a request is submitted to the *device*, not to a node of it.  Every node
        of a cluster runs the whole program, so every node reads the request's
        tokens out of its own input window; staging them on node zero alone
        would leave thirty-one nodes prefilling a window of zeros.  The
        alternative -- a program-emitted broadcast from node zero -- is a
        collective the deployment does not declare, and inventing one here
        would be the host sequencing a device operation.
        """
        for memory in self.node_memories:
            memory[object_id].write(byte_offset, payload)

    def host_object(self, object_id: int):
        """Node zero's instance of ``object_id``, for a host-side read."""
        return self.memory[object_id]

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
