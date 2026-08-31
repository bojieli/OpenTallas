"""Independent ABI 3.0 program and deployment verifier.

This module implements the admission proofs required by ADR-003 section 5.1 and
section 14.  It is deliberately written against the *decoded* artifact only: it
imports no compiler backend, reconstructs every bound from the descriptor table,
and never consults the generator's intermediate state.  A deployment that this
module rejects must not be issued to any engine.

The proofs performed are:

1.  version, digest and capability admission;
2.  structural instruction legality (opcode, subopcode, flag, predicate);
3.  descriptor resolution and per-family type agreement;
4.  proper loop nesting with finite, capability-bounded trip counts;
5.  a retired-work bound -- the sum over instructions of the product of the
    enclosing loop trip counts -- that must not exceed the header's declared
    bound, which in turn must not exceed the capability;
6.  forward-only branching inside the authenticated body, so termination follows
    from the loop bounds alone;
7.  every wait names an event some instruction can signal, and no event ID
    named by either exceeds the capability's ID space (amendment A23);
8.  every prepared state resource has exactly one reachable commit or discard,
    and the deployment declares no more state resources than the capability
    holds slots for (amendment A22);
9.  every terminal path reaches exactly one COMPLETE;
10. permission agreement -- no write to an immutable object, no engine output
    into a read-only object, no ROM write path; and
11. tensor-view bounds under the maximum value of every dynamic index term;
    and
12. the join axis and operand geometry of every ``REDUCTION.GROUPED_CONCAT``
    (amendment A17).
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Mapping, Sequence

from .capability import Capability
from .constants import (
    DTYPE_BITS,
    ENGINE_FAMILIES,
    NO_ID,
    CommitPolicy,
    Control,
    DType,
    InstructionFlag,
    Major,
    ParticipantScope,
    Permission,
    Reduction,
    Selection,
    State,
    StorageClass,
    SUBOPCODES,
    TopologyClass,
)
from .deployment import (
    Deployment,
    DescriptorTable,
    DeploymentError,
    derive_commit_policies,
    ring_staged_objects,
)
from .descriptors import (
    Descriptor,
    ExtendedDescriptorType,
    MAX_DYNAMIC_TERMS,
    MAX_RANK,
    MAX_WAIT_PRODUCERS,
    PredicateKind,
    SelectorKind,
    Symbol,
    decode_entrypoint_table,
    iteration_extent,
)
from .records import Instruction, decode_body, split_program


class VerificationError(Exception):
    """Raised when a deployment fails an admission proof."""


#: Amendment A17: the join axes ``REDUCTION.GROUPED_CONCAT`` defines.  Zero is
#: the axis it has always joined on; one is the feature join.  The set is
#: closed, so an axis outside it is refused rather than interpreted.
JOIN_AXES: tuple[int, ...] = (0, 1)

#: The operand rank each join axis requires, or ``None`` for "any rank".  A
#: feature join is defined on rank-2 operands only: on a higher-rank operand an
#: input's block is not one contiguous run of the output, and A17 refuses the
#: shape rather than compute one no released model emits.
JOIN_RANK: Mapping[int, int | None] = {0: None, 1: 2}


def _view_dims(payload: Mapping[str, Any]) -> tuple[int, ...]:
    return tuple(int(payload[f"dim{axis}"]) for axis in range(int(payload["rank"])))


def _join_frame(axis: int, payload: Mapping[str, Any]) -> tuple[int, ...]:
    """Every extent of a view except the one a join on ``axis`` consumes."""
    dims = _view_dims(payload)
    return dims[:axis] + dims[axis + 1 :]


def _comparable(
    dims: Sequence[int], removed_axis: int, leading_is_static: bool
) -> tuple[int, ...]:
    """The extents of ``dims`` that the descriptor alone settles.

    Only axis 0 of a view can differ at issue from the value the descriptor
    states, and only through amendment A13's clamp.  ``removed_axis`` says which
    axis a join has already consumed from ``dims`` (``-1`` for none), so that
    "axis 0 of the view" is identified correctly in a frame that has had an
    earlier axis removed.
    """
    if leading_is_static or removed_axis == 0:
        return tuple(int(d) for d in dims)
    return tuple(int(d) for d in dims[1:])



@dataclass
class VerificationReport:
    """Machine-readable outcome of a verification run."""

    admitted: bool
    instruction_count: int
    descriptor_count: int
    proved_retired_work: int
    declared_retired_work: int
    loop_depth: int
    event_count: int
    state_resources: int
    errors: list[str] = dc_field(default_factory=list)
    warnings: list[str] = dc_field(default_factory=list)
    checks: dict[str, bool] = dc_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "admitted": self.admitted,
            "instruction_count": self.instruction_count,
            "descriptor_count": self.descriptor_count,
            "proved_retired_work": self.proved_retired_work,
            "declared_retired_work": self.declared_retired_work,
            "loop_depth": self.loop_depth,
            "event_count": self.event_count,
            "state_resources": self.state_resources,
            "checks": dict(sorted(self.checks.items())),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


# Descriptor type expected in an instruction's ``descriptor_id`` per family.
_FAMILY_DESCRIPTOR: dict[int, int] = {
    Major.DMA: ExtendedDescriptorType.OPERATOR,
    Major.TENSOR: ExtendedDescriptorType.OPERATOR,
    Major.VECTOR: ExtendedDescriptorType.OPERATOR,
    Major.ATTENTION: ExtendedDescriptorType.OPERATOR,
    Major.ROUTE: ExtendedDescriptorType.OPERATOR,
    Major.REDUCTION: ExtendedDescriptorType.OPERATOR,
    Major.SELECTION: ExtendedDescriptorType.OPERATOR,
    Major.LINK: ExtendedDescriptorType.COMMUNICATION,
    Major.STATE: ExtendedDescriptorType.STATE,
    Major.OBSERVATION: ExtendedDescriptorType.COUNTER_CLASS,
}


class Verifier:
    """Stateless-by-construction verifier over one decoded deployment."""

    def __init__(self, deployment: Deployment, capability: Capability) -> None:
        self.deployment = deployment
        self.capability = capability
        self.table = deployment.table
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.checks: dict[str, bool] = {}
        self.header, body = split_program(deployment.program)
        self.instructions = decode_body(body)
        self._loop_trip: dict[int, int] = {}
        self._depth = 0
        self._work = 0
        self._events_signalled: set[int] = set()
        self._events_waited: set[int] = set()

    # -- helpers ---------------------------------------------------------
    def _fail(self, message: str) -> None:
        self.errors.append(message)

    def _check(self, name: str, ok: bool, message: str) -> bool:
        self.checks[name] = self.checks.get(name, True) and ok
        if not ok:
            self._fail(message)
        return ok

    def _descriptor(self, did: int, expected: int | None, context: str) -> Descriptor | None:
        if did == NO_ID:
            self._fail(f"{context}: descriptor ID is NO_ID")
            return None
        if not 0 <= did < len(self.table):
            self._fail(f"{context}: descriptor ID {did} is out of range")
            return None
        descriptor = self.table[did]
        if expected is not None and descriptor.descriptor_type != expected:
            self._fail(
                f"{context}: descriptor {did} is "
                f"{ExtendedDescriptorType(descriptor.descriptor_type).name}, "
                f"expected {ExtendedDescriptorType(expected).name}"
            )
            return None
        return descriptor

    # -- 1. version, digest and capability -------------------------------
    def _verify_admission(self) -> None:
        ok, missing = self.capability.admits(self.header.required_features)
        self._check(
            "capability_features",
            ok,
            f"capability does not implement required feature bits {missing}",
        )
        limits = self.capability.limits
        self._check(
            "instruction_count_bound",
            self.header.instruction_count <= limits["max_instructions"],
            f"program has {self.header.instruction_count} instructions, capability "
            f"admits {limits['max_instructions']}",
        )
        self._check(
            "descriptor_count_bound",
            len(self.table) <= limits["max_descriptors"],
            f"deployment has {len(self.table)} descriptors, capability admits "
            f"{limits['max_descriptors']}",
        )
        self._check(
            "declared_work_bound",
            self.header.max_retired_work <= limits["max_retired_work"],
            "declared maximum retired work exceeds the capability bound",
        )
        events = {
            i.signal_event_id
            for i in self.instructions
            if i.signal_event_id != NO_ID
        }
        self._check(
            "event_count_bound",
            len(events) <= limits["max_events"],
            f"program signals {len(events)} distinct events, capability admits "
            f"{limits['max_events']}",
        )
        # Amendment A23.  The count above bounds how many events are live; it
        # does not bound the *identifiers*.  An implementation whose scoreboard
        # is a bit per event ID is bounded by the largest ID, and the two
        # coincide only when IDs are dense from zero -- which no real program's
        # are.  A program using three IDs numbered 4000, 4001 and 4002 passes
        # the count check and then indexes past the end of any scoreboard.
        # Wait-set producers are bounded too: the scoreboard is addressed on
        # the wait path as well as the signal path.
        named = set(events)
        for wait_id in self.table.ids_of_type(
            ExtendedDescriptorType.EVENT_WAIT_SET
        ):
            payload = self.table[wait_id].payload
            count = int(payload["producer_count"])
            for slot in range(min(count, MAX_WAIT_PRODUCERS)):
                producer = payload[f"producer_{slot}"]
                if producer != NO_ID:
                    named.add(int(producer))
        largest = max(named) if named else 0
        self._check(
            "event_id_bound",
            largest <= limits["max_event_id"],
            f"program names event ID {largest}, capability admits IDs up to "
            f"{limits['max_event_id']}",
        )
        # Amendment A22.  One STATE descriptor is one state resource, and a
        # transactional-state implementation holds a slot for each declared
        # resource for the life of a transaction.  Before A22 no capability
        # field named that slot count, so a deployment declaring more
        # resources than the sequencer has slots was admitted here and
        # discovered at run time as a capability trap.
        state_resources = len(
            self.table.ids_of_type(ExtendedDescriptorType.STATE)
        )
        self._check(
            "state_resource_bound",
            state_resources <= limits["max_state_resources"],
            f"deployment declares {state_resources} state resources, capability "
            f"admits {limits['max_state_resources']}",
        )
        for did in self.table.ids_of_type(ExtendedDescriptorType.GENERATION_POLICY):
            payload = self.table[did].payload
            if payload["vocabulary_size"] > limits["max_vocabulary"]:
                self._fail(
                    f"generation policy {did} declares vocabulary "
                    f"{payload['vocabulary_size']}, capability admits "
                    f"{limits['max_vocabulary']}"
                )
            if payload["max_new_tokens"] > limits["max_context_positions"]:
                self._fail(
                    f"generation policy {did} admits {payload['max_new_tokens']} "
                    f"new tokens, capability context bound is "
                    f"{limits['max_context_positions']}"
                )
        self.checks.setdefault("generation_policy_bounds", True)
        self._check(
            "descriptor_table_digest",
            self.header.descriptor_table_digest == self.table.digest,
            "program header does not bind the descriptor table",
        )
        self._check(
            "deployment_digest",
            self.header.deployment_digest == self.deployment.deployment_digest,
            "program header does not bind the deployment manifest",
        )
        self._check(
            "capability_digest_declared",
            bool(self.deployment.capability_digest),
            "deployment does not name the capability it was compiled against",
        )
        if self.deployment.capability_digest != self.capability.digest:
            self._fail(
                "deployment was compiled against capability "
                f"{self.deployment.capability_digest[:16]}, admitting implementation "
                f"is {self.capability.digest[:16]}"
            )
            self.checks["capability_identity"] = False
        else:
            self.checks.setdefault("capability_identity", True)

    # -- 2/3. instruction and descriptor legality -------------------------
    def _verify_instructions(self) -> None:
        for index, instruction in enumerate(self.instructions):
            context = f"instruction {index} ({instruction.mnemonic})"
            try:
                instruction.validate()
            except Exception as exc:  # structural legality
                self._fail(f"{context}: {exc}")
                continue
            family = Major(instruction.major)
            if instruction.predicate_id != NO_ID:
                self._descriptor(
                    instruction.predicate_id,
                    ExtendedDescriptorType.PREDICATE,
                    f"{context} predicate",
                )
            if instruction.wait_set_id != NO_ID:
                self._descriptor(
                    instruction.wait_set_id,
                    ExtendedDescriptorType.EVENT_WAIT_SET,
                    f"{context} wait set",
                )
            expected = _FAMILY_DESCRIPTOR.get(family)
            if expected is not None:
                self._descriptor(instruction.descriptor_id, expected, context)
            if family is Major.CONTROL:
                self._verify_control_operands(index, instruction, context)
            if instruction.signal_event_id != NO_ID:
                if instruction.signal_event_id in self._events_signalled:
                    self._fail(
                        f"{context}: event {instruction.signal_event_id} is signalled "
                        "more than once; events are single-assignment"
                    )
                self._events_signalled.add(instruction.signal_event_id)
        self.checks.setdefault("instruction_legality", not self.errors)

    def _verify_control_operands(
        self, index: int, instruction: Instruction, context: str
    ) -> None:
        sub = Control(instruction.sub)
        if sub in (Control.LOOP_SETUP, Control.LOOP_NEXT):
            self._descriptor(
                instruction.control_id, ExtendedDescriptorType.LOOP_CONTROL, context
            )
        elif sub is Control.BRANCH:
            target = instruction.control_id
            if not 0 <= target < len(self.instructions):
                self._fail(f"{context}: branch target {target} is outside the body")
            elif target <= index:
                self._fail(
                    f"{context}: branch target {target} is not forward; only "
                    "LOOP_NEXT may transfer control backwards"
                )
        elif sub is Control.WAIT:
            if instruction.wait_set_id == NO_ID:
                self._fail(f"{context}: WAIT without a wait set")

    # -- 4/5/6. loops, work bound, termination ---------------------------
    def _verify_control_flow(self) -> None:
        limits = self.capability.limits
        stack: list[tuple[int, int, int]] = []  # (loop descriptor id, setup index, trip)
        multiplier = 1
        work = 0
        max_depth = 0
        completes: list[int] = []
        for index, instruction in enumerate(self.instructions):
            family = Major(instruction.major)
            if family is Major.CONTROL:
                sub = Control(instruction.sub)
                if sub is Control.LOOP_SETUP:
                    descriptor = self._descriptor(
                        instruction.control_id,
                        ExtendedDescriptorType.LOOP_CONTROL,
                        f"instruction {index} LOOP_SETUP",
                    )
                    if descriptor is None:
                        continue
                    payload = descriptor.payload
                    trip = self._loop_trip_count(index, descriptor)
                    if payload["body_start"] != index + 1:
                        self._fail(
                            f"instruction {index}: loop body_start "
                            f"{payload['body_start']} must be {index + 1}"
                        )
                    # The LOOP_SETUP instruction itself retires once, at the
                    # enclosing multiplier -- before the loop it opens starts
                    # multiplying. Counting it after the multiplier update, or
                    # not at all, under-counts the bound and lets the device's
                    # own watchdog fire on a program the verifier admitted.
                    work += multiplier
                    stack.append((instruction.control_id, index, trip))
                    multiplier *= max(trip, 1)
                    max_depth = max(max_depth, len(stack))
                    if len(stack) > limits["max_loop_depth"]:
                        self._fail(
                            f"instruction {index}: loop nesting {len(stack)} exceeds "
                            f"capability depth {limits['max_loop_depth']}"
                        )
                    continue
                if sub is Control.LOOP_NEXT:
                    if not stack:
                        self._fail(f"instruction {index}: LOOP_NEXT with no open loop")
                        continue
                    loop_id, setup_index, trip = stack[-1]
                    if instruction.control_id != loop_id:
                        self._fail(
                            f"instruction {index}: LOOP_NEXT closes loop "
                            f"{instruction.control_id} but loop {loop_id} is innermost"
                        )
                    descriptor = self.table[loop_id]
                    if descriptor.payload["body_end"] != index:
                        self._fail(
                            f"instruction {index}: loop body_end "
                            f"{descriptor.payload['body_end']} does not match"
                        )
                    work += multiplier  # the LOOP_NEXT itself retires each iteration
                    stack.pop()
                    multiplier //= max(trip, 1)
                    continue
                if sub is Control.COMPLETE:
                    completes.append(index)
                    if stack:
                        self._fail(
                            f"instruction {index}: COMPLETE inside an open loop body"
                        )
            work += multiplier
        self._check("loops_closed", not stack, "program ends with an open loop")
        self._check(
            "single_completion",
            len(completes) == 1,
            f"program declares {len(completes)} COMPLETE instructions, expected 1",
        )
        if completes:
            self._check(
                "completion_is_terminal",
                completes[-1] == len(self.instructions) - 1,
                "COMPLETE is not the final instruction",
            )
        self._work = work
        self._depth = max_depth
        self._check(
            "proved_work_bound",
            work <= self.header.max_retired_work,
            f"proved retired work {work} exceeds the declared bound "
            f"{self.header.max_retired_work}",
        )

    def _loop_trip_count(self, index: int, descriptor: Descriptor) -> int:
        payload = descriptor.payload
        limits = self.capability.limits
        step = payload["step"]
        if step == 0:
            self._fail(f"instruction {index}: loop step is zero")
            return 1
        selector = payload["bound_selector_kind"]
        if selector == SelectorKind.CONSTANT:
            span = payload["upper_bound"] - payload["lower_bound"]
        else:
            # A symbol-bounded loop is proved against its declared maximum, which
            # is what the capability and the work bound must cover.
            span = payload["max_iterations"] * step
            try:
                Symbol(payload["bound_symbol_id"])
            except ValueError:
                self._fail(
                    f"instruction {index}: loop bound symbol "
                    f"{payload['bound_symbol_id']} is not in the frozen registry"
                )
        if span <= 0:
            self._fail(f"instruction {index}: loop has a non-positive span")
            return 1
        trip = (span + step - 1) // step
        declared = payload["max_iterations"]
        if declared <= 0:
            self._fail(f"instruction {index}: loop declares no maximum iteration count")
            return 1
        if trip > declared:
            self._fail(
                f"instruction {index}: loop trip {trip} exceeds its declared "
                f"maximum {declared}"
            )
        if declared > limits["max_loop_trip"]:
            self._fail(
                f"instruction {index}: loop maximum {declared} exceeds capability "
                f"{limits['max_loop_trip']}"
            )
        self._loop_trip[descriptor.descriptor_id] = min(trip, declared)
        return min(trip, declared)

    # -- 7. events -------------------------------------------------------
    def _verify_events(self) -> None:
        signal_index: dict[int, int] = {}
        for index, instruction in enumerate(self.instructions):
            if instruction.signal_event_id != NO_ID:
                signal_index.setdefault(instruction.signal_event_id, index)
        # A wait whose only producer is a later instruction deadlocks.  Control
        # flow is forward-only apart from LOOP_NEXT back edges, so requiring the
        # producer to precede the wait is both sound and sufficient to prove the
        # absence of cyclic waits that ADR-003 section 9 demands.
        for index, instruction in enumerate(self.instructions):
            if instruction.wait_set_id == NO_ID:
                continue
            wait = self.table.get(
                instruction.wait_set_id, ExtendedDescriptorType.EVENT_WAIT_SET
            )
            for slot in range(wait.payload["producer_count"]):
                event = wait.payload[f"producer_{slot}"]
                producer = signal_index.get(event)
                if producer is not None and producer > index:
                    self._fail(
                        f"instruction {index} waits on event {event}, whose only "
                        f"producer is instruction {producer}; the wait can never "
                        "be satisfied"
                    )
        self.checks.setdefault("wait_ordering", True)
        for descriptor in self.table.descriptors():
            if descriptor.descriptor_type != ExtendedDescriptorType.EVENT_WAIT_SET:
                continue
            payload = descriptor.payload
            count = payload["producer_count"]
            if count == 0:
                self._fail(
                    f"wait set {descriptor.descriptor_id} declares no producers"
                )
                continue
            for slot in range(count):
                event = payload[f"producer_{slot}"]
                self._events_waited.add(event)
                if event not in self._events_signalled:
                    self._fail(
                        f"wait set {descriptor.descriptor_id} waits on event {event}, "
                        "which no instruction signals"
                    )
            for slot in range(count, 12):
                if payload[f"producer_{slot}"] != NO_ID:
                    self._fail(
                        f"wait set {descriptor.descriptor_id} has a producer beyond "
                        "its declared count"
                    )
        self.checks.setdefault("events_producible", True)

    # -- 8. state discipline ---------------------------------------------
    def _verify_state(self) -> None:
        prepared: dict[int, int] = {}
        resolved: set[int] = set()
        for index, instruction in enumerate(self.instructions):
            if Major(instruction.major) is not Major.STATE:
                continue
            descriptor = self._descriptor(
                instruction.descriptor_id,
                ExtendedDescriptorType.STATE,
                f"instruction {index} state",
            )
            if descriptor is None:
                continue
            sid = descriptor.descriptor_id
            sub = State(instruction.sub)
            if sub is State.PREPARE:
                if sid in prepared:
                    self._fail(
                        f"instruction {index}: state {sid} is prepared twice without "
                        "an intervening commit or discard"
                    )
                prepared[sid] = index
                if not descriptor.permissions & Permission.STATE_PREPARE:
                    self._fail(
                        f"instruction {index}: state {sid} lacks STATE_PREPARE "
                        "permission"
                    )
            elif sub in (State.COMMIT, State.DISCARD):
                if sid not in prepared:
                    self._fail(
                        f"instruction {index}: state {sid} is "
                        f"{sub.name.lower()}ed without a preceding prepare"
                    )
                else:
                    prepared.pop(sid)
                    resolved.add(sid)
                if sub is State.COMMIT and not (
                    descriptor.permissions & Permission.STATE_COMMIT
                ):
                    self._fail(
                        f"instruction {index}: state {sid} lacks STATE_COMMIT "
                        "permission"
                    )
        for sid, index in prepared.items():
            self._fail(
                f"state {sid} prepared at instruction {index} has no reachable "
                "commit or discard"
            )
        self._check("state_discipline", not prepared, "unresolved prepared state")
        self._verify_commit_policies()
        self._state_resources = len(
            self.table.ids_of_type(ExtendedDescriptorType.STATE)
        )

    def _verify_commit_policies(self) -> None:
        """Wire format sections 12.11 and 12.16: a commit's rows are declared.

        ``commit_policy`` says what a ``STATE.COMMIT`` publishes, and it is a
        fact about the deployment rather than an opinion held by whichever
        backend emitted it: ``UNSTAGED`` exactly when no descriptor names the
        resource's prepared image as a destination, ``SATURATING`` exactly when
        a scatter addresses that image through a ring whose modulus divides the
        declared ``capacity_rows``, ``REQUEST_SPAN`` otherwise.  So it is
        re-derived here from the same shared rule the builder used and the two
        must agree.  A hand-edited or mis-emitted declaration is refused with
        the resource named, rather than silently changing how many rows the
        device publishes.
        """
        registry = {int(member) for member in CommitPolicy}
        objects = self.deployment.objects
        policies, problems = derive_commit_policies(self.table, objects)
        rings = ring_staged_objects(self.table, objects)
        agreed = not problems
        for problem in problems:
            self._fail(problem)
        for state_id in self.table.ids_of_type(ExtendedDescriptorType.STATE):
            descriptor = self.table[state_id]
            declared = int(descriptor.payload["commit_policy"])
            expected = int(policies[state_id])
            if declared not in registry:
                agreed = False
                self._fail(
                    f"state {state_id} declares commit policy {declared}, which "
                    "is not in the amendment A21/A25 registry"
                )
            elif declared != expected:
                agreed = False
                prepared = descriptor.payload["prepared_object_id"]
                reached = {
                    int(CommitPolicy.UNSTAGED): (
                        "is named as a destination by no descriptor"
                    ),
                    int(CommitPolicy.REQUEST_SPAN): (
                        "is named as a destination by at least one descriptor "
                        "and is addressed by no ring"
                    ),
                    int(CommitPolicy.SATURATING): (
                        "is staged through a ring of "
                        + ", ".join(
                            str(m) for m in sorted(rings.get(int(prepared), ()))
                        )
                        + " rows"
                    ),
                }[expected]
                self._fail(
                    f"state {state_id} declares commit policy "
                    f"{CommitPolicy(declared).name}, but its prepared image "
                    f"{prepared} {reached}, which is "
                    f"{CommitPolicy(expected).name}"
                )
        self._check(
            "commit_policy_declared", agreed, "a declared commit policy is wrong"
        )

    # -- 9/10. permissions and storage ------------------------------------
    def _verify_permissions(self) -> None:
        for descriptor in self.table.descriptors():
            if descriptor.descriptor_type != ExtendedDescriptorType.MEMORY_OBJECT:
                continue
            payload = descriptor.payload
            oid = descriptor.descriptor_id
            storage = payload["storage_class"]
            try:
                StorageClass(storage)
            except ValueError:
                self._fail(f"object {oid}: unknown storage class {storage}")
                continue
            writable = bool(
                descriptor.permissions
                & (Permission.WRITE | Permission.STATE_COMMIT | Permission.STATE_PREPARE)
            )
            if storage == StorageClass.ROM and writable:
                self._fail(
                    f"object {oid}: ROM storage declares a write permission; "
                    "immutable ROM has no functional write path"
                )
            if descriptor.permissions & Permission.IMMUTABLE and writable:
                self._fail(f"object {oid}: IMMUTABLE object declares a write path")
            if payload["size_bytes"] == 0:
                self._fail(f"object {oid}: zero-size memory object")
            if oid not in self.deployment.objects:
                self._fail(f"object {oid}: no source declared in the manifest")
            elif self.deployment.objects[oid].size_bytes != payload["size_bytes"]:
                self._fail(
                    f"object {oid}: manifest source is "
                    f"{self.deployment.objects[oid].size_bytes} bytes, descriptor "
                    f"declares {payload['size_bytes']}"
                )
        self.checks.setdefault("permissions", True)

    # -- 11. tensor-view bounds -------------------------------------------
    def _verify_views(self) -> None:
        symbol_max = {
            Symbol.SPAN_TOKENS: self.capability.limits["max_context_positions"],
            Symbol.POSITION_START: self.capability.limits["max_context_positions"],
            Symbol.POSITION_END: self.capability.limits["max_context_positions"],
            Symbol.CONTEXT_LENGTH: self.capability.limits["max_context_positions"],
            Symbol.PHASE: 1,
            Symbol.GENERATION_INDEX: self.capability.limits["max_context_positions"],
            Symbol.MAX_NEW_TOKENS: self.capability.limits["max_context_positions"],
            Symbol.BATCH: 1,
            Symbol.NODE_ID: max(self.capability.limits["max_nodes"] - 1, 0),
            Symbol.NODE_COUNT: self.capability.limits["max_nodes"],
            Symbol.ACTIVE_EXPERT_COUNT: self.capability.limits["max_topk"],
            Symbol.SPARSE_INDEX_COUNT: self.capability.limits["max_context_positions"],
            Symbol.LAYER_COUNT: 1024,
            Symbol.VOCABULARY_PARTITIONS: 1024,
            Symbol.SPAN_LAST_INDEX: self.capability.limits["max_context_positions"],
        }
        for descriptor in self.table.descriptors():
            if descriptor.descriptor_type != ExtendedDescriptorType.TENSOR_VIEW:
                continue
            payload = descriptor.payload
            vid = descriptor.descriptor_id
            rank = payload["rank"]
            if not 1 <= rank <= MAX_RANK:
                self._fail(f"view {vid}: rank {rank} out of range")
                continue
            try:
                dtype = DType(payload["dtype"])
            except ValueError:
                self._fail(f"view {vid}: unknown dtype {payload['dtype']}")
                continue
            for axis in range(rank, MAX_RANK):
                if payload[f"dim{axis}"] or payload[f"stride{axis}"]:
                    self._fail(f"view {vid}: axis {axis} beyond rank is nonzero")
            last = payload["element_offset"]
            for axis in range(rank):
                dim = payload[f"dim{axis}"]
                if dim == 0:
                    self._fail(f"view {vid}: axis {axis} has zero extent")
                    dim = 1
                last += (dim - 1) * payload[f"stride{axis}"]
            terms = payload["dynamic_term_count"]
            if terms > MAX_DYNAMIC_TERMS:
                self._fail(f"view {vid}: {terms} dynamic terms exceed the maximum")
                continue
            walked = False
            self._verify_extent_declaration(vid, payload, rank)
            for slot in range(terms):
                kind = payload[f"term{slot}_kind"]
                sel = payload[f"term{slot}_index"]
                stride = payload[f"term{slot}_stride"]
                if kind == SelectorKind.LOOP_INDUCTION:
                    trip = self._loop_trip.get(sel)
                    if trip is None:
                        self._fail(
                            f"view {vid} term {slot}: loop descriptor {sel} is not a "
                            "verified loop"
                        )
                        continue
                    last += (trip - 1) * stride
                    if self._verify_block_extent(vid, sel, payload, stride):
                        walked = True
                elif kind == SelectorKind.RUNTIME_SYMBOL:
                    try:
                        maximum = symbol_max[Symbol(sel)]
                    except (ValueError, KeyError):
                        self._fail(f"view {vid} term {slot}: unknown symbol {sel}")
                        continue
                    last += max(maximum - 1, 0) * stride
                else:
                    self._fail(f"view {vid} term {slot}: unknown selector kind {kind}")
            for slot in range(terms, MAX_DYNAMIC_TERMS):
                if (
                    payload[f"term{slot}_kind"]
                    or payload[f"term{slot}_index"]
                    or payload[f"term{slot}_stride"]
                ):
                    self._fail(f"view {vid}: dynamic term beyond declared count")
            self._verify_extent_reachable(vid, payload, walked)
            obj = self._descriptor(
                descriptor.primary_object_id,
                ExtendedDescriptorType.MEMORY_OBJECT,
                f"view {vid} object",
            )
            if obj is None:
                continue
            bits = DTYPE_BITS[dtype]
            needed_bits = (last + 1) * bits
            needed = (needed_bits + 7) // 8
            if needed > obj.payload["size_bytes"]:
                self._fail(
                    f"view {vid}: maximum element {last} needs {needed} bytes but "
                    f"object {obj.descriptor_id} is {obj.payload['size_bytes']} bytes"
                )
            self._verify_block_scale(vid, payload)
        self.checks.setdefault("view_bounds", True)
        self.checks.setdefault("block_extent", True)
        self.checks.setdefault("block_scale", True)
        self.checks.setdefault("extent_axis", True)

    def _verify_block_scale(self, vid: int, payload: Mapping[str, Any]) -> None:
        """A block-scaled view's geometry must admit an exact scale index.

        Amendment A15 (wire format section 12.6) addresses a scale with two
        blocks -- ``scale_block_elements`` along the last axis and
        ``scale_block_rows`` along the leading one -- and states three
        requirements for the index to be exact: last-axis stride one,
        ``cols % scale_block_elements == 0`` and ``rows % scale_block_rows == 0``.
        A view that meets none of them has no defined scale for some of its
        elements, so it is refused here rather than trapped mid-operator, where
        it would already have read weights.  A zero row block is the amendment's
        A8 case and means one, which every view divides.
        """
        if payload["scale_object_id"] == NO_ID:
            return
        rank = int(payload["rank"])
        block = int(payload["scale_block_elements"])
        if block <= 0:
            self._fail(
                f"view {vid}: names a scale object but no scale block size"
            )
            self.checks["block_scale"] = False
            return
        if int(payload[f"stride{rank - 1}"]) != 1:
            self._fail(
                f"view {vid}: a block-scaled view must have last-axis stride 1, "
                f"not {payload[f'stride{rank - 1}']}"
            )
            self.checks["block_scale"] = False
        width = int(payload[f"dim{rank - 1}"])
        if width % block:
            self._fail(
                f"view {vid}: last axis {width} is not a multiple of its "
                f"{block}-element scale block"
            )
            self.checks["block_scale"] = False
        row_block = max(int(payload["scale_block_rows"]), 1)
        rows = 1
        for axis in range(rank - 1):
            rows *= max(int(payload[f"dim{axis}"]), 1)
        if rows % row_block:
            self._fail(
                f"view {vid}: leading extent {rows} is not a multiple of its "
                f"{row_block}-row scale block"
            )
            self.checks["block_scale"] = False

    def _verify_extent_declaration(
        self, vid: int, payload: Mapping[str, Any], rank: int
    ) -> None:
        """Amendment A18: an extent declaration must name an axis this view has.

        Both fields are zero on every view written before the amendment, which
        is axis 0 in the bound symbol's own units -- amendment A13's rule
        exactly -- so this refuses only a declaration that could not be
        resolved at all.
        """
        axis = int(payload["extent_axis"])
        if not 0 <= axis < rank:
            self._fail(
                f"view {vid}: amendment A18 extent axis {axis} is outside the "
                f"rank-{rank} view that declares it"
            )
            self.checks["extent_axis"] = False
        for name in ("extent_unit", "extent_numerator"):
            if int(payload[name]) == 1:
                self._fail(
                    f"view {vid}: amendment A18 encodes a {name.split('_')[1]} "
                    "of one as zero, so a declared one is a value the wire "
                    "format does not assign; write zero"
                )
                self.checks["extent_axis"] = False

    def _verify_extent_reachable(
        self, vid: int, payload: Mapping[str, Any], walked: bool
    ) -> None:
        """A declared request-dependent extent must have a loop that resolves it.

        A view that names an axis, a unit, a numerator or a bias is saying the
        request decides that extent.  If no term walks the axis, nothing sets it
        and
        the operand silently presents its declared maximum -- which is the
        failure this amendment exists to remove, not a shape to admit: the
        DeepSeek index key presented 65,536 candidates and the attention join
        262,272 rows, and both executed.  So a declaration nothing can resolve
        is refused here rather than discovered as a wrong answer.

        A view that declares neither field is untouched: axis 0 and unit one is
        A13, and A13 has always been silent about views no loop indexes.
        """
        declared = any(
            int(payload[name])
            for name in (
                "extent_axis",
                "extent_unit",
                "extent_numerator",
                "extent_bias",
            )
        )
        if not declared or walked:
            return
        self._fail(
            f"view {vid}: amendment A18 declares axis "
            f"{int(payload['extent_axis'])} as "
            f"{max(int(payload['extent_numerator']), 1)} * symbol / "
            f"{max(int(payload['extent_unit']), 1)} + "
            f"{int(payload['extent_bias'])}, but no dynamic term walks that "
            "axis in that unit, so the request cannot set it and the operand "
            "would present its declared maximum"
        )
        self.checks["extent_axis"] = False

    def _verify_block_extent(
        self,
        vid: int,
        loop_id: int,
        payload: Mapping[str, Any],
        term_stride: int,
    ) -> bool:
        """A block-loop-indexed leading axis may not exceed the block.

        Amendment A13 clamps a view's leading extent in the final iteration of
        a symbol-bounded block loop.  Section 12.4 states the clamp as
        ``dim0 = remaining if 0 < remaining < dim0``; ``ViewResolver`` applies
        it only while ``remaining < bound_divisor``.  The two are the same
        function on every program where ``dim0 <= bound_divisor`` and differ on
        every program where it does not -- checked exhaustively over divisors
        1..8, extents 1..11, bounds 0..19 and iterations 0..5: 1,027
        disagreements, every one of them with ``dim0 > bound_divisor``, and none
        without.

        Rather than pick a winner between two formulations of the same
        intent, this refuses the programs that can tell them apart.  Such a
        program is malformed anyway: iteration *i* of a block loop covers rows
        ``[i*divisor, (i+1)*divisor)``, so a view indexed by that loop claiming
        more than ``divisor`` rows is claiming rows belonging to the next
        iteration.  With this check the wire format's rule and the resolver's
        implementation are provably the same rule.
        """
        try:
            loop = self.deployment.table.get(
                loop_id, ExtendedDescriptorType.LOOP_CONTROL
            )
        except Exception:  # not a loop descriptor: _verify_views said so
            return False
        loop_payload = loop.payload
        if loop_payload["bound_selector_kind"] != SelectorKind.RUNTIME_SYMBOL:
            return False
        divisor = int(loop_payload["bound_divisor"])
        if divisor <= 0:
            return False
        # Amendment A18: the axis, the unit, the numerator and the bias are the
        # view's to declare; all zero is axis 0, the symbol's own value and no
        # bias, which is A13.
        axis = int(payload["extent_axis"])
        unit = max(int(payload["extent_unit"]), 1)
        numerator = max(int(payload["extent_numerator"]), 1)
        bias = int(payload["extent_bias"])
        step = iteration_extent(divisor, numerator, unit)
        if step is None:
            return False
        # Only a loop that walks the *clamped* axis can clamp it, and the
        # arithmetic says which loops those are: one iteration advances by one
        # whole block of that axis.  A view indexed along some other axis -- the
        # mHC branch reduction steps over tokens while its leading axis is the
        # four hyper-connection streams -- is not a partial final iteration of
        # anything, and neither the clamp nor this rule applies to it.
        if int(term_stride) != int(payload[f"stride{axis}"]) * step:
            return False
        block = step + bias
        extent = int(payload[f"dim{axis}"])
        if extent > block:
            self._fail(
                f"view {vid}: axis-{axis} extent {extent} exceeds the {block} "
                f"element(s) one iteration of loop {loop_id} covers, and that "
                "loop indexes it; iteration i covers exactly those, so the "
                "view claims elements belonging to the next iteration, and "
                "amendment A13's clamp is ambiguous on exactly this shape"
            )
            self.checks["block_extent"] = False
        return True

    # -- schedule completeness ----------------------------------------------
    def _verify_schedules(self) -> None:
        """Every engine operator must carry a usable tile mapping.

        ADR-003 section 6.2 defines the Schedule descriptor as carrying the tile
        mapping, and the cycle model derives all tile-level time from it. An
        operator with no schedule, or with a zeroed one, produces a deployment
        that executes but cannot be evaluated -- and a timing result computed
        from an absent tile mapping is meaningless rather than merely imprecise.
        Admitting it would let that meaninglessness reach a comparison table.
        """
        for index, instruction in enumerate(self.instructions):
            family = Major(instruction.major)
            if family not in ENGINE_FAMILIES or family in (Major.STATE, Major.LINK):
                continue
            descriptor = self._descriptor(
                instruction.descriptor_id,
                ExtendedDescriptorType.OPERATOR,
                f"instruction {index} operator",
            )
            if descriptor is None:
                continue
            schedule_id = descriptor.payload["schedule_id"]
            if schedule_id == NO_ID:
                self._fail(
                    f"instruction {index} ({instruction.mnemonic}): operator "
                    f"{descriptor.descriptor_id} carries no SCHEDULE descriptor, "
                    "so its tile mapping is unknown and it cannot be timed"
                )
                continue
            schedule = self._descriptor(
                schedule_id,
                ExtendedDescriptorType.SCHEDULE,
                f"instruction {index} schedule",
            )
            if schedule is None:
                continue
            payload = schedule.payload
            if payload["engine_family"] != int(family):
                self._fail(
                    f"instruction {index}: schedule {schedule_id} is for "
                    f"{Major(payload['engine_family']).name}, not {family.name}"
                )
            # tile_depth is required too: the cycle model decomposes an
            # operation into tiles of (rows, cols, depth), and a zero in any of
            # the three means it cannot be timed. A pass-shaped operation
            # declares depth 1; it must declare something.
            zeroed = [
                name
                for name in ("tile_rows", "tile_cols", "tile_depth")
                if payload[name] == 0
            ]
            if zeroed:
                self._fail(
                    f"instruction {index}: schedule {schedule_id} leaves "
                    f"{zeroed} at zero; a tile mapping with a zero extent "
                    "cannot be evaluated"
                )
            if payload["max_outstanding"] == 0:
                self._fail(
                    f"instruction {index}: schedule {schedule_id} admits zero "
                    "outstanding operations"
                )
        self.checks.setdefault("schedule_completeness", True)

    # -- engine write paths ------------------------------------------------
    def _verify_engine_write_paths(self) -> None:
        """Every engine output must name a writable, mutable destination.

        Without this the ROM immutability claim is unenforced: a TENSOR.MATMUL
        may name a view over an IMMUTABLE or ROM object as its destination and
        still be admitted.  Object permissions alone do not catch it, because
        nothing else connects an operator's output view to the object behind
        it.
        """
        for index, instruction in enumerate(self.instructions):
            family = Major(instruction.major)
            if family not in ENGINE_FAMILIES or family in (Major.STATE, Major.LINK):
                continue
            descriptor = self._descriptor(
                instruction.descriptor_id,
                ExtendedDescriptorType.OPERATOR,
                f"instruction {index} operator",
            )
            if descriptor is None:
                continue
            for slot in range(2):
                view_id = descriptor.payload[f"output_view_{slot}"]
                if view_id == NO_ID:
                    continue
                view = self._descriptor(
                    view_id,
                    ExtendedDescriptorType.TENSOR_VIEW,
                    f"instruction {index} output view",
                )
                if view is None:
                    continue
                if not view.permissions & Permission.WRITE:
                    self._fail(
                        f"instruction {index} ({instruction.mnemonic}): output "
                        f"view {view_id} has no WRITE permission"
                    )
                obj = self._descriptor(
                    view.primary_object_id,
                    ExtendedDescriptorType.MEMORY_OBJECT,
                    f"instruction {index} output object",
                )
                if obj is None:
                    continue
                storage = obj.payload["storage_class"]
                if storage == StorageClass.ROM:
                    self._fail(
                        f"instruction {index} ({instruction.mnemonic}): writes "
                        f"into object {obj.descriptor_id}, which is immutable "
                        "ROM; ROM has no functional write path"
                    )
                if obj.permissions & Permission.IMMUTABLE:
                    self._fail(
                        f"instruction {index} ({instruction.mnemonic}): writes "
                        f"into IMMUTABLE object {obj.descriptor_id}"
                    )
                if not obj.permissions & (
                    Permission.WRITE | Permission.STATE_PREPARE | Permission.STATE_COMMIT
                ):
                    self._fail(
                        f"instruction {index} ({instruction.mnemonic}): object "
                        f"{obj.descriptor_id} grants no write permission"
                    )
        self.checks.setdefault("engine_write_paths", True)

    # -- join axis (amendment A17) -----------------------------------------
    def _verify_join_axis(self) -> None:
        """Wire format section 12.7: a concatenation states the axis it joins.

        ``REDUCTION.GROUPED_CONCAT`` reads its join axis from ``aux_id_0``.
        ``NO_ID`` -- what :class:`runtime.abi3.builder.DeploymentBuilder` writes
        into an unnamed auxiliary slot -- and ``0`` both mean axis 0, so every
        program written before A17 keeps exactly the behaviour it had.  Axis 1
        joins rank-2 operands on their feature axis.

        Four things are refused here rather than trapped in an engine that has
        already read operands: an axis A17 does not define; a join axis at or
        beyond an operand's rank; a feature join on an operand that is not rank
        2; and a join whose operands disagree about a *statically known* extent.

        The last qualification is not a loophole, it is amendments A4 and A13.
        A view's ``dim0`` is a function of the live loop and symbol bindings --
        the resolver clamps it in a block loop's final iteration, and nothing
        else about a view's extents ever moves -- so ``dim0`` is compared here
        only when no operand carries a term that walks it, and the engine
        compares the resolved value at every issue regardless.  Every other axis
        is static in the descriptor and is compared unconditionally.
        """
        for index, instruction in enumerate(self.instructions):
            if (
                Major(instruction.major) is not Major.REDUCTION
                or instruction.sub != int(Reduction.GROUPED_CONCAT)
            ):
                continue
            descriptor = self._descriptor(
                instruction.descriptor_id,
                ExtendedDescriptorType.OPERATOR,
                f"instruction {index} operator",
            )
            if descriptor is None:
                continue
            where = f"instruction {index} (GROUPED_CONCAT)"
            aux = descriptor.payload["aux_id_0"]
            axis = 0 if aux == NO_ID else int(aux)
            if axis not in JOIN_AXES:
                self._fail(
                    f"{where}: aux_id_0 names join axis {axis}; amendment A17 "
                    f"defines {', '.join(str(a) for a in JOIN_AXES)} and "
                    "nothing else"
                )
                continue
            inputs: list[Mapping[str, Any]] = []
            for slot in range(4):
                vid = descriptor.payload[f"input_view_{slot}"]
                if vid == NO_ID:
                    continue
                view = self._descriptor(
                    vid, ExtendedDescriptorType.TENSOR_VIEW, f"{where} input view"
                )
                if view is not None:
                    inputs.append(view.payload)
            out_id = descriptor.payload["output_view_0"]
            out = (
                None
                if out_id == NO_ID
                else self._descriptor(
                    out_id, ExtendedDescriptorType.TENSOR_VIEW, f"{where} output view"
                )
            )
            if not inputs or out is None:
                self._fail(f"{where}: names no input view or no output view")
                continue
            operands = [*inputs, out.payload]
            if not all(self._join_rank_ok(where, axis, payload) for payload in operands):
                continue
            # An axis a block loop moves is compared only when no operand is
            # indexed along it.  Under A18 that axis is the one each operand
            # declares, so the question is asked about axis 0 -- the axis a join
            # on the feature axis holds constant -- rather than assumed of it.
            leading_is_static = not any(
                self._walks_clamped_axis(payload, 0) for payload in operands
            )
            frame = _join_frame(axis, inputs[0])
            joined = 0
            for payload in inputs:
                other = _join_frame(axis, payload)
                if _comparable(frame, axis, leading_is_static) != _comparable(
                    other, axis, leading_is_static
                ):
                    self._fail(
                        f"{where}: input views disagree on the extents the join "
                        f"does not touch -- {other} against {frame}; a "
                        f"concatenation on axis {axis} is defined only when "
                        "every other axis matches"
                    )
                    break
                joined += int(payload[f"dim{axis}"])
            else:
                if axis == 0 and not leading_is_static:
                    continue
                expected = frame[:axis] + (joined,) + frame[axis:]
                actual = _view_dims(out.payload)
                if _comparable(actual, -1, leading_is_static) != _comparable(
                    expected, -1, leading_is_static
                ):
                    self._fail(
                        f"{where}: output view {out.descriptor_id} is {actual} "
                        f"but the axis-{axis} concatenation of its inputs is "
                        f"{expected}"
                    )
        self.checks.setdefault("join_axis", True)

    def _join_rank_ok(self, where: str, axis: int, payload: Mapping[str, Any]) -> bool:
        rank = int(payload["rank"])
        if axis >= rank:
            self._fail(
                f"{where}: joins on axis {axis} but an operand has rank {rank}"
            )
            return False
        required = JOIN_RANK[axis]
        if required is not None and rank != required:
            self._fail(
                f"{where}: joins on axis {axis}, which amendment A17 defines for "
                f"rank-{required} operands only, but an operand has rank {rank}"
            )
            return False
        return True

    def _walks_clamped_axis(self, payload: Mapping[str, Any], axis: int) -> bool:
        """True when a loop term steps this view along ``axis`` in blocks.

        The same derivation :meth:`_verify_block_extent` and the functional
        resolver use: one iteration advances by one whole block of that axis, so
        the term stride is ``stride[axis] * (numerator * bound_divisor / unit)``.
        Such a view's ``dim[axis]`` is the block, not the extent, and A13/A18
        set it at the live binding.
        """
        if int(payload["extent_axis"]) != axis:
            return False
        unit = max(int(payload["extent_unit"]), 1)
        numerator = max(int(payload["extent_numerator"]), 1)
        for slot in range(int(payload["dynamic_term_count"])):
            if payload[f"term{slot}_kind"] != SelectorKind.LOOP_INDUCTION:
                continue
            try:
                loop = self.deployment.table.get(
                    int(payload[f"term{slot}_index"]),
                    ExtendedDescriptorType.LOOP_CONTROL,
                )
            except Exception:  # not a loop descriptor: _verify_views said so
                continue
            divisor = int(loop.payload["bound_divisor"])
            if divisor <= 0:
                continue
            step = iteration_extent(divisor, numerator, unit)
            if step is None:
                continue
            if int(payload[f"term{slot}_stride"]) == int(
                payload[f"stride{axis}"]
            ) * step:
                return True
        return False

    # -- scope and optional-feature flags -----------------------------------
    def _verify_flags(self) -> None:
        """Wire format section 3: a scope flag inconsistent with its descriptor
        is illegal, and an OPTIONAL_FEATURE instruction needs an alternative."""
        for index, instruction in enumerate(self.instructions):
            family = Major(instruction.major)
            if instruction.flags & InstructionFlag.GLOBAL_SCOPE:
                if family is not Major.LINK:
                    self._fail(
                        f"instruction {index} ({instruction.mnemonic}): "
                        "the GLOBAL_SCOPE flag names a cluster or wafer "
                        "participant set, and only a link communication "
                        "descriptor carries one; this scope flag is "
                        "inconsistent with its descriptor"
                    )
                elif self.deployment.topology_class == int(TopologyClass.SINGLE_CHIP):
                    self._fail(
                        f"instruction {index}: the GLOBAL_SCOPE scope flag has "
                        "no participant set on a single-chip topology"
                    )
            if instruction.flags & InstructionFlag.OPTIONAL_FEATURE:
                # The alternative path is the predicated-off path, so the
                # instruction must be predicated for one to exist at all.
                if not instruction.flags & InstructionFlag.PREDICATED:
                    self._fail(
                        f"instruction {index} ({instruction.mnemonic}): "
                        "OPTIONAL_FEATURE requires an authenticated alternative "
                        "path, so the instruction must be predicated"
                    )
        self.checks.setdefault("flag_consistency", True)

    # -- participant scope (amendment A14) ---------------------------------
    def _verify_participant_scope(self) -> None:
        """Wire format section 12.5: a collective may only name a fabric the
        admitted topology actually has.

        ``participant_scope`` decides what a collective's members are, and the
        engine derives the member count from the TOPOLOGY descriptor:
        ``NODE`` from ``node_count``, ``RETICLE`` from ``reticle_count``,
        ``TILE`` from ``reticle_count * tiles_per_reticle``.  Two rules keep the
        field honest, and both are admission rules rather than engine faults
        because a deployment that cannot run its own collectives should be
        refused before it is activated, not when it reaches the instruction:

        * a scope the topology cannot support is refused -- ``RETICLE`` against
          a zero ``reticle_count``, ``TILE`` against a zero
          ``tiles_per_reticle``; and
        * a ``SINGLE_CHIP`` topology admits only ``NODE``, because a chip has
          no reticle or tile fabric to address.

        A pre-amendment program carries zero at payload offset 80 -- the byte
        was reserved-zero and reserved bytes must be zero -- so it declares
        ``NODE`` and passes both rules exactly as it did before A14 existed.
        """
        communications = self.table.ids_of_type(
            int(ExtendedDescriptorType.COMMUNICATION)
        )
        if not communications:
            return
        topology_ids = self.table.ids_of_type(int(ExtendedDescriptorType.TOPOLOGY))
        topology = (
            self.table[topology_ids[0]].payload if len(topology_ids) == 1 else None
        )
        if topology is None:
            topology_class = int(self.deployment.topology_class)
            reticles = 0
            tiles = 0
        else:
            topology_class = int(topology["topology_class"])
            reticles = int(topology["reticle_count"])
            tiles = int(topology["tiles_per_reticle"])
        for did in communications:
            payload = self.table[did].payload
            raw = int(payload["participant_scope"])
            try:
                scope = ParticipantScope(raw)
            except ValueError:
                self._check(
                    "participant_scope_registry",
                    False,
                    f"COMMUNICATION descriptor {did} declares participant scope "
                    f"{raw}, which is not in the frozen registry",
                )
                continue
            self.checks.setdefault("participant_scope_registry", True)
            if scope is ParticipantScope.RETICLE:
                self._check(
                    "participant_scope_supported",
                    reticles >= 1,
                    f"COMMUNICATION descriptor {did} is RETICLE-scoped; the "
                    f"admitted topology declares {reticles} reticles, so it has "
                    "no reticle fabric to address",
                )
            elif scope is ParticipantScope.TILE:
                self._check(
                    "participant_scope_supported",
                    reticles >= 1 and tiles >= 1,
                    f"COMMUNICATION descriptor {did} is TILE-scoped; the "
                    f"admitted topology declares {reticles} reticles of {tiles} "
                    "tiles, so it has no tile fabric to address",
                )
            if topology_class == int(TopologyClass.SINGLE_CHIP):
                self._check(
                    "participant_scope_topology_class",
                    scope is ParticipantScope.NODE,
                    f"COMMUNICATION descriptor {did} is {scope.name}-scoped on a "
                    "SINGLE_CHIP topology; a chip has no reticle or tile fabric, "
                    "so a single-chip deployment admits only NODE",
                )
        self.checks.setdefault("participant_scope_supported", True)
        self.checks.setdefault("participant_scope_topology_class", True)

    # -- entrypoints ------------------------------------------------------
    def _verify_entrypoints(self) -> None:
        eid = self.header.entrypoint_table_descriptor
        descriptor = self._descriptor(
            eid, ExtendedDescriptorType.ENTRYPOINT_TABLE, "entrypoint table"
        )
        if descriptor is None or descriptor.raw_payload is None:
            return
        entries = decode_entrypoint_table(descriptor.raw_payload)
        self._check(
            "entrypoint_count",
            len(entries) == self.header.entrypoint_count,
            "entrypoint table length does not match the program header",
        )
        # The manifest and the authenticated descriptor table are separately
        # digest-bound, so a divergence between them survives a disk round trip.
        # Left unchecked, a bundle whose table declares a generation policy and
        # whose manifest declares NO_ID is admitted with no on-device selection
        # at all -- the host-side-argmax path ADR-003 8.7 forbids.
        manifest = list(self.deployment.entrypoints)
        if len(manifest) != len(entries):
            self._fail(
                f"manifest declares {len(manifest)} entrypoints, the "
                f"authenticated table declares {len(entries)}"
            )
        else:
            for position, (declared, authenticated) in enumerate(
                zip(manifest, entries)
            ):
                for field in (
                    "entrypoint_id",
                    "first_instruction",
                    "phase",
                    "generation_policy_id",
                ):
                    if int(declared.get(field, NO_ID)) != int(authenticated[field]):
                        self._fail(
                            f"entrypoint {position}: manifest {field}="
                            f"{declared.get(field)} disagrees with the "
                            f"authenticated table's {authenticated[field]}"
                        )
        self.checks.setdefault("entrypoint_manifest_agreement", True)
        for entry in entries:
            first = entry["first_instruction"]
            if not 0 <= first < len(self.instructions):
                self._fail(f"entrypoint {entry['entrypoint_id']}: bad first instruction")
            if entry["generation_policy_id"] != NO_ID:
                self._descriptor(
                    entry["generation_policy_id"],
                    ExtendedDescriptorType.GENERATION_POLICY,
                    f"entrypoint {entry['entrypoint_id']} policy",
                )

    # -- selection --------------------------------------------------------
    def _verify_selection(self) -> None:
        """ADR-003 8.7: on-device selection is mandatory; EOS stops execution."""
        has_argmax = any(
            Major(i.major) is Major.SELECTION and Selection(i.sub) is Selection.ARGMAX
            for i in self.instructions
        )
        has_append = any(
            Major(i.major) is Major.SELECTION
            and Selection(i.sub) is Selection.TOKEN_APPEND
            for i in self.instructions
        )
        generative = any(
            entry.get("generation_policy_id", NO_ID) != NO_ID
            for entry in self.deployment.entrypoints
        )
        if generative:
            self._check(
                "on_device_selection",
                has_argmax or has_append,
                "a generative entrypoint exists but the program contains no "
                "device selection instruction; host-side argmax is prohibited",
            )
            self._check(
                "token_append_present",
                has_append,
                "a generative entrypoint exists but the program never appends a token",
            )

    # -- entry point ------------------------------------------------------
    def verify(self) -> VerificationReport:
        self._state_resources = 0
        self._verify_admission()
        self._verify_instructions()
        self._verify_control_flow()
        self._verify_events()
        self._verify_state()
        self._verify_permissions()
        self._verify_engine_write_paths()
        self._verify_schedules()
        self._verify_flags()
        self._verify_views()
        self._verify_join_axis()
        self._verify_participant_scope()
        self._verify_entrypoints()
        self._verify_selection()
        return VerificationReport(
            admitted=not self.errors,
            instruction_count=len(self.instructions),
            descriptor_count=len(self.table),
            proved_retired_work=self._work,
            declared_retired_work=self.header.max_retired_work,
            loop_depth=self._depth,
            event_count=len(self._events_signalled),
            state_resources=self._state_resources,
            errors=list(self.errors),
            warnings=list(self.warnings),
            checks=dict(self.checks),
        )


def verify_deployment(
    deployment: Deployment, capability: Capability
) -> VerificationReport:
    """Verify ``deployment`` against ``capability`` and return the report."""
    return Verifier(deployment, capability).verify()


def require_admitted(
    deployment: Deployment, capability: Capability
) -> VerificationReport:
    """Verify and raise :class:`VerificationError` unless the deployment passes."""
    report = verify_deployment(deployment, capability)
    if not report.admitted:
        raise VerificationError(
            "deployment rejected:\n  " + "\n  ".join(report.errors)
        )
    return report
