"""Event-driven ABI 3.0 cycle model.

One model, four targets.  The cycle model consumes *exactly* the artifacts the
functional device consumes -- a :class:`~runtime.abi3.deployment.Deployment`, a
:class:`~runtime.abi3.capability.Capability` and a request -- and it obtains its
architectural events by *running the functional device itself*
(:class:`~runtime.sim.device.Device`) through instrumentation hooks.  That is a
deliberate structural choice rather than a shortcut:

* ADR-003 section 13 requires the functional simulator, the cycle simulator and
  RTL to share one counter definition.  A cycle model that re-implemented the
  microsequencer would drift from the functional one the first time either
  changed.  Here they cannot drift, because there is one microsequencer;
* the requirement is that every *architectural* counter agree exactly.  Running
  the same code path makes that agreement structural; the test still checks it,
  but it checks a property that holds by construction;
* timing counters (frozen registry group ``0x0c``) are the only counters the
  cycle model adds.  The functional device leaves all of them at zero.

What the cycle model adds on top of that execution is a real machine:

``microsequencer``
    in-order fetch / decode / predicate / issue through a bounded issue port;
``engine queues``
    per-family bounded submission queues whose depth and outstanding limit come
    from the capability, with credit-gated issue;
``engines``
    occupancy and fixed latency per family, throughput from lanes and rate;
``memory hierarchy``
    HBM channels with per-channel bandwidth and latency, SRAM banks with port
    conflicts, immutable ROM in its own bandwidth/latency class, and host
    memory, all addressed by real object addresses so contention is physical;
``scoreboard``
    single-assignment events with acquire waits, which is what makes a reported
    stall a stall rather than a fudge factor;
``fabric``
    :mod:`runtime.cycle.fabric` for the 32-node cluster and for the wafer.

Two invariants are *proved* rather than asserted in prose (ADR-003 section 9):
bounded queue occupancy for the admitted schedule, and the absence of cyclic
waits.  And no global barrier or collective is ever modelled as zero-latency.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    CompletionStatus,
    Control,
    Link,
    Major,
    NO_ID,
    StorageClass,
    TopologyClass,
    TrapClass,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import (
    CollectiveOp,
    Descriptor,
    ExtendedDescriptorType,
    SelectorKind,
    Symbol,
)
from runtime.sim.counters import CounterSet, COUNTERS, is_timing_counter
from runtime.sim.device import Device, PendingCommit, Session, TransactionResult
from runtime.sim.memory import ResolvedView, ViewResolver
from runtime.cycle.fabric import (
    ClusterFabric,
    FabricTiming,
    WaferFabric,
    assert_no_zero_latency_global_operations,
    build_fabric,
)
from runtime.cycle.machine import (
    ENGINE_FAMILY_NAMES,
    FAMILY_BY_NAME,
    FAMILY_WORK_COUNTERS,
    CostTable,
    EngineParams,
    MachineError,
    MachineModel,
    MemoryClassParams,
    MemoryParams,
    Provenance,
    SequencerParams,
)

CYCLE_RESULT_SCHEMA = "opentallas.abi3.cycle_result.v1"

#: Rounding applied to every derived floating-point figure in the output, so
#: that "same inputs produce byte-identical output" survives any last-bit
#: difference in a division.
FLOAT_DIGITS = 6


def _round(value: float) -> float:
    return round(float(value), FLOAT_DIGITS)


#: Seconds are tiny at any plausible clock, so they get their own precision;
#: six decimals would round a whole transaction to zero.
TIME_DIGITS = 15


def _round_seconds(value: float) -> float:
    return round(float(value), TIME_DIGITS)


def architectural_counters(snapshot: Mapping[str, int]) -> dict[str, int]:
    """The counters on which the functional device and the cycle model agree."""
    return {k: int(v) for k, v in sorted(snapshot.items()) if not is_timing_counter(k)}


def timing_counters(snapshot: Mapping[str, int]) -> dict[str, int]:
    """The counters the functional device leaves at zero (registry group 0x0c)."""
    return {k: int(v) for k, v in sorted(snapshot.items()) if is_timing_counter(k)}


# ---------------------------------------------------------------------------
# Trace records
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class MemoryAccess:
    """One engine-visible memory access, with a real address.

    ``nbytes`` is the *useful* extent -- what the functional device counted.
    ``amplification`` is how many times a tiled schedule actually fetches that
    extent: an operand re-read once per tile of the orthogonal axis moves more
    bytes over the wire than the operation logically consumes.  The two are kept
    apart because tiling changes cycles, never architectural bytes.
    """

    object_id: int
    storage_class: int
    address: int
    nbytes: int
    write: bool
    view_id: int = NO_ID
    amplification: int = 1

    @property
    def transferred_bytes(self) -> int:
        return self.nbytes * self.amplification

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "storage_class": StorageClass(self.storage_class).name,
            "address": self.address,
            "bytes": self.nbytes,
            "transferred_bytes": self.transferred_bytes,
            "amplification": self.amplification,
            "write": self.write,
        }


@dataclass(slots=True)
class TraceStep:
    """One architectural step observed while the functional device executed."""

    index: int
    kind: str  # PREDICATE | CONTROL | ENGINE | COMMIT
    pc: int = NO_ID
    major: int = NO_ID
    sub: int = NO_ID
    mnemonic: str = ""
    family: str = ""
    descriptor_id: int = NO_ID
    wait_set_id: int = NO_ID
    wait_producers: tuple[int, ...] = ()
    signal_event_id: int = NO_ID
    counter_delta: dict[str, int] = dc_field(default_factory=dict)
    accesses: list[MemoryAccess] = dc_field(default_factory=list)
    trapped: bool = False
    predicate_taken: bool | None = None
    operator_id: int = NO_ID
    schedule_id: int = NO_ID
    schedule: dict[str, int] | None = None
    operand_dims: dict[str, tuple[int, ...]] = dc_field(default_factory=dict)
    operand_objects: dict[str, int] = dc_field(default_factory=dict)
    numeric_profile_id: int = NO_ID
    contract_digest: str = ""

    @property
    def bytes_moved(self) -> int:
        return sum(access.nbytes for access in self.accesses)

    @property
    def bytes_transferred(self) -> int:
        return sum(access.transferred_bytes for access in self.accesses)


def effective_symbols(
    request: "CycleRequest", *, node_id: int = 0, node_count: int = 1
) -> dict[int, int]:
    """The symbol binding both models must use for the same request.

    Topology coordinates are request-bound scalars (amendment A5), so they are
    supplied here rather than by either model privately; if the two models bound
    them differently their counters could differ for a reason that has nothing
    to do with timing.
    """
    symbols = {int(k): int(v) for k, v in request.symbols.items()}
    symbols.setdefault(int(Symbol.NODE_ID), node_id)
    symbols.setdefault(int(Symbol.NODE_COUNT), node_count)
    return symbols


def _delta(before: Mapping[str, int], after: Mapping[str, int]) -> dict[str, int]:
    out: dict[str, int] = {}
    for name, value in after.items():
        change = int(value) - int(before.get(name, 0))
        if change:
            out[name] = change
    return dict(sorted(out.items()))


# ---------------------------------------------------------------------------
# Address placement
# ---------------------------------------------------------------------------
class AddressMap:
    """Physical byte addresses for every memory object of one deployment.

    The MEMORY_OBJECT descriptor carries ``base_address`` and ``bank_or_tile``,
    but ABI 3.0 does not *require* a backend to fill them in, and the shared
    builder defaults ``base_address`` to zero.  A deployment whose objects all
    sit at address zero cannot be mapped onto channels or banks at all, so the
    model detects that case and substitutes a deterministic packed placement,
    reporting which of the two it used.  Timing derived from a synthetic
    placement is a statement about the model's placement, not about the
    deployment's -- so it is labelled rather than hidden.
    """

    def __init__(self, deployment: Deployment, alignment: int = 4096) -> None:
        self.alignment = alignment
        declared: dict[int, int] = {}
        classes: dict[int, int] = {}
        sizes: dict[int, int] = {}
        banks: dict[int, int] = {}
        for descriptor in deployment.table.descriptors():
            if descriptor.descriptor_type != ExtendedDescriptorType.MEMORY_OBJECT:
                continue
            oid = descriptor.descriptor_id
            declared[oid] = int(descriptor.payload["base_address"])
            classes[oid] = int(descriptor.payload["storage_class"])
            sizes[oid] = int(descriptor.payload["size_bytes"])
            banks[oid] = int(descriptor.payload["bank_or_tile"])
        self.storage_class = classes
        self.size_bytes = sizes
        self.bank_or_tile = banks
        distinct = {c: set() for c in set(classes.values())}
        for oid, base in declared.items():
            distinct[classes[oid]].add(base)
        collides = any(
            len(distinct[c]) < sum(1 for o in classes if classes[o] == c)
            for c in distinct
        )
        if not collides:
            self.mode = "descriptor_base_address"
            self.base = dict(declared)
            return
        self.mode = "synthetic_packed"
        cursor: dict[int, int] = {}
        packed: dict[int, int] = {}
        for oid in sorted(classes):
            klass = classes[oid]
            start = cursor.get(klass, 0)
            packed[oid] = start
            span = max(sizes[oid], 1)
            span = ((span + alignment - 1) // alignment) * alignment
            cursor[klass] = start + span
        self.base = packed

    def address(self, object_id: int, offset: int) -> int:
        return self.base.get(object_id, 0) + offset

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "alignment_bytes": self.alignment,
            "object_count": len(self.base),
            "note": (
                "descriptor base_address values were distinct and were used"
                if self.mode == "descriptor_base_address"
                else "the deployment did not assign distinct base addresses; a "
                "deterministic packed placement was substituted and channel and "
                "bank conflicts are a property of that placement"
            ),
        }


# ---------------------------------------------------------------------------
# Instrumented functional device
# ---------------------------------------------------------------------------
class _AccessRecorder:
    """Collects the memory accesses of the engine operation currently issuing."""

    def __init__(self, deployment: Deployment, addresses: AddressMap) -> None:
        self.deployment = deployment
        self.addresses = addresses
        self.current: list[MemoryAccess] | None = None

    def begin(self) -> None:
        self.current = []

    def end(self) -> list[MemoryAccess]:
        out = self.current or []
        self.current = None
        return out

    def raw(self, object_id: int, offset: int, nbytes: int, *, write: bool) -> None:
        if self.current is None or nbytes <= 0:
            return
        self.current.append(
            MemoryAccess(
                object_id=object_id,
                storage_class=self.addresses.storage_class.get(
                    object_id, int(StorageClass.HBM)
                ),
                address=self.addresses.address(object_id, offset),
                nbytes=int(nbytes),
                write=write,
            )
        )

    def view(self, view: ResolvedView, array: np.ndarray, *, write: bool) -> None:
        if self.current is None:
            return
        itemsize = int(array.dtype.itemsize)
        nbytes = int(array.size) * itemsize
        self.raw(
            view.object_id,
            int(view.element_offset) * itemsize,
            nbytes,
            write=write,
        )


class _RecordingViews(ViewResolver):
    """A view resolver that reports every array it reads or writes."""

    def __init__(
        self, deployment: Deployment, memory, recorder: _AccessRecorder
    ) -> None:
        super().__init__(deployment, memory)
        self._recorder = recorder

    def read_array(self, view: ResolvedView) -> np.ndarray:
        array = super().read_array(view)
        self._recorder.view(view, array, write=False)
        return array

    def write_array(self, view: ResolvedView, values: np.ndarray) -> None:
        super().write_array(view, values)
        self._recorder.view(view, values, write=True)


class TracingDevice(Device):
    """The functional device, instrumented.

    Every override records what happened and then calls the frozen
    implementation.  No override changes a decision, a counter or an error, so
    the architectural behaviour of this class is the architectural behaviour of
    :class:`~runtime.sim.device.Device`.
    """

    def __init__(
        self,
        deployment: Deployment,
        capability: Capability,
        *,
        root: Path | None = None,
        verify: bool = True,
    ) -> None:
        super().__init__(deployment, capability, root=root, verify=verify, trace=False)
        self.addresses = AddressMap(deployment)
        self._recorder = _AccessRecorder(deployment, self.addresses)
        self.views = _RecordingViews(deployment, self.memory, self._recorder)
        self.steps: list[TraceStep] = []
        self._pc_index = {id(ins): i for i, ins in enumerate(self.instructions)}

    # -- hooks -----------------------------------------------------------
    def _new_step(self, kind: str, **kwargs: Any) -> TraceStep:
        step = TraceStep(index=len(self.steps), kind=kind, **kwargs)
        self.steps.append(step)
        return step

    def _wait_producers(self, wait_set_id: int) -> tuple[int, ...]:
        if wait_set_id == NO_ID:
            return ()
        wait = self.deployment.table.get(
            wait_set_id, ExtendedDescriptorType.EVENT_WAIT_SET
        )
        return tuple(
            wait.payload[f"producer_{slot}"]
            for slot in range(wait.payload["producer_count"])
        )

    def _evaluate_predicate(self, descriptor, loops, symbols):  # type: ignore[override]
        step = self._new_step("PREDICATE", descriptor_id=descriptor.descriptor_id)
        taken = super()._evaluate_predicate(descriptor, loops, symbols)
        step.predicate_taken = bool(taken)
        return taken

    def _execute_control(  # type: ignore[override]
        self, instruction, pc, loops, loop_stack, symbols, counters
    ):
        before = counters.snapshot()
        step = self._new_step(
            "CONTROL",
            pc=pc,
            major=int(instruction.major),
            sub=int(instruction.sub),
            mnemonic=instruction.mnemonic,
            family="control",
            descriptor_id=instruction.descriptor_id,
            wait_set_id=instruction.wait_set_id,
            wait_producers=self._wait_producers(instruction.wait_set_id),
            signal_event_id=instruction.signal_event_id,
        )
        try:
            return super()._execute_control(
                instruction, pc, loops, loop_stack, symbols, counters
            )
        finally:
            step.counter_delta = _delta(before, counters.snapshot())

    def _issue(self, ctx, instruction, family):  # type: ignore[override]
        before = ctx.counters.snapshot()
        step = self._new_step(
            "ENGINE",
            pc=self._pc_index.get(id(instruction), NO_ID),
            major=int(instruction.major),
            sub=int(instruction.sub),
            mnemonic=instruction.mnemonic,
            family=ENGINE_FAMILY_NAMES.get(int(family), "sequencer"),
            descriptor_id=instruction.descriptor_id,
            wait_set_id=instruction.wait_set_id,
            wait_producers=self._wait_producers(instruction.wait_set_id),
            signal_event_id=instruction.signal_event_id,
        )
        self._recorder.begin()
        try:
            super()._issue(ctx, instruction, family)
        except BaseException:
            step.trapped = True
            raise
        finally:
            step.counter_delta = _delta(before, ctx.counters.snapshot())
            step.accesses = self._recorder.end()

    def _apply_commit(self, commit: PendingCommit, counters: CounterSet) -> None:  # type: ignore[override]
        before = counters.snapshot()
        resource = commit.resource
        cursor = resource.cursor_rows
        nbytes = commit.rows * resource.row_bytes
        step = self._new_step(
            "COMMIT",
            major=int(Major.STATE),
            mnemonic="STATE.COMMIT.apply",
            family="state",
            descriptor_id=resource.descriptor_id,
        )
        self._recorder.begin()
        try:
            super()._apply_commit(commit, counters)
        finally:
            self._recorder.raw(
                resource.prepared_object_id, 0, nbytes, write=False
            )
            self._recorder.raw(
                resource.committed_object_id,
                cursor * resource.row_bytes,
                nbytes,
                write=True,
            )
            step.accesses = self._recorder.end()
            step.counter_delta = _delta(before, counters.snapshot())


# ---------------------------------------------------------------------------
# Timing resources
# ---------------------------------------------------------------------------
class _MemoryUnit:
    """One HBM channel, SRAM bank port, ROM array or host port."""

    __slots__ = ("name", "bytes_per_cycle", "free_at", "busy_cycles",
                 "conflict_cycles", "transactions")

    def __init__(self, name: str, bytes_per_cycle: float) -> None:
        self.name = name
        self.bytes_per_cycle = bytes_per_cycle
        self.free_at = 0
        self.busy_cycles = 0
        self.conflict_cycles = 0
        self.transactions = 0

    def occupy(self, arrival: int, nbytes: int) -> tuple[int, int]:
        cycles = max(1, math.ceil(nbytes / self.bytes_per_cycle))
        conflict = max(0, self.free_at - arrival)
        start = arrival + conflict
        self.free_at = start + cycles
        self.busy_cycles += cycles
        self.conflict_cycles += conflict
        self.transactions += 1
        return self.free_at, conflict

    def reserve(self, arrival: int, cycles: int, transactions: int) -> tuple[int, int]:
        conflict = max(0, self.free_at - arrival)
        start = arrival + conflict
        self.free_at = start + cycles
        self.busy_cycles += cycles
        self.conflict_cycles += conflict
        self.transactions += transactions
        return self.free_at, conflict


@dataclass(slots=True)
class MemoryClassStats:
    """Per-storage-class traffic and occupancy."""

    bytes_read: int = 0
    bytes_written: int = 0
    transactions: int = 0
    busy_cycles: int = 0
    conflict_cycles: int = 0
    accesses: int = 0

    def to_dict(self, params: MemoryClassParams, span: int) -> dict[str, Any]:
        capacity = params.units * params.ports_per_unit * max(span, 1)
        total = self.bytes_read + self.bytes_written
        return {
            "bytes_read": self.bytes_read,
            "bytes_written": self.bytes_written,
            "bytes_total": total,
            "accesses": self.accesses,
            "transactions": self.transactions,
            "busy_cycles": self.busy_cycles,
            "conflict_cycles": self.conflict_cycles,
            "unit_utilisation": _round(self.busy_cycles / capacity) if capacity else 0.0,
            "achieved_bytes_per_cycle": _round(total / span) if span else 0.0,
            "peak_bytes_per_cycle": _round(params.peak_bytes_per_cycle),
            "bandwidth_utilisation": (
                _round(total / (params.peak_bytes_per_cycle * span)) if span else 0.0
            ),
            "structure": params.to_dict(),
        }


class MemorySystem:
    """HBM channels, SRAM banks with ports, immutable ROM and host memory.

    A transaction's unit is chosen from its *address*, so two engines reading
    two objects that interleave onto the same channel really do collide, and
    two SRAM reads that hit the same bank really do serialise on that bank's
    port.  That is why ``latency.sram_bank_conflict_cycles`` and
    ``latency.hbm_channel_conflict_cycles`` mean something.
    """

    def __init__(self, params: MemoryParams) -> None:
        self.params = params
        self.units: dict[str, list[_MemoryUnit]] = {}
        self.stats: dict[str, MemoryClassStats] = {}
        for klass in (params.hbm, params.sram, params.rom, params.host):
            self.units[klass.name] = [
                _MemoryUnit(
                    f"{klass.name}.{unit}.{port}", klass.bytes_per_cycle_per_unit
                )
                for unit in range(klass.units)
                for port in range(klass.ports_per_unit)
            ]
            self.stats[klass.name] = MemoryClassStats()

    def _unit_of(self, klass: MemoryClassParams, address: int) -> int:
        lane = (address // klass.interleave_bytes) % klass.units
        port = (address // klass.transaction_bytes) % klass.ports_per_unit
        return lane * klass.ports_per_unit + port

    def schedule(
        self, accesses: Sequence[MemoryAccess], start: int
    ) -> tuple[int, dict[str, int]]:
        """Run ``accesses`` from ``start`` and return ``(finish, conflicts)``."""
        finish = start
        conflicts: dict[str, int] = {}
        for access in accesses:
            klass = self.params.klass(StorageClass(access.storage_class))
            units = self.units[klass.name]
            stats = self.stats[klass.name]
            stats.accesses += 1
            if access.write:
                stats.bytes_written += access.nbytes
                latency = klass.write_latency_cycles
            else:
                stats.bytes_read += access.nbytes
                latency = klass.read_latency_cycles
            count = max(1, math.ceil(access.nbytes / klass.transaction_bytes))
            stats.transactions += count
            conflict = 0
            done = start
            if count <= self.params.max_modeled_transactions_per_access:
                for index in range(count):
                    address = access.address + index * klass.transaction_bytes
                    nbytes = min(
                        klass.transaction_bytes,
                        access.nbytes - index * klass.transaction_bytes,
                    )
                    unit = units[self._unit_of(klass, address)]
                    end, waited = unit.occupy(start, max(nbytes, 1))
                    conflict += waited
                    done = max(done, end)
            else:
                # Bulk reservation: exact total occupancy, coarser interleave.
                per_unit = count // len(units)
                remainder = count % len(units)
                first = self._unit_of(klass, access.address)
                for offset in range(len(units)):
                    unit = units[(first + offset) % len(units)]
                    share = per_unit + (1 if offset < remainder else 0)
                    if not share:
                        continue
                    cycles = share * max(
                        1, math.ceil(klass.transaction_bytes / unit.bytes_per_cycle)
                    )
                    end, waited = unit.reserve(start, cycles, share)
                    conflict += waited
                    done = max(done, end)
            stats.conflict_cycles += conflict
            conflicts[klass.name] = conflicts.get(klass.name, 0) + conflict
            finish = max(finish, done + latency)
        for klass in (
            self.params.hbm, self.params.sram, self.params.rom, self.params.host
        ):
            self.stats[klass.name].busy_cycles = sum(
                unit.busy_cycles for unit in self.units[klass.name]
            )
        return finish, conflicts

    def report(self, span: int) -> dict[str, Any]:
        return {
            "address_interleave": "address // interleave_bytes % units",
            "hbm": self.stats["hbm"].to_dict(self.params.hbm, span),
            "sram": self.stats["sram"].to_dict(self.params.sram, span),
            "rom": self.stats["rom"].to_dict(self.params.rom, span),
            "host": self.stats["host"].to_dict(self.params.host, span),
            "state_backing_storage_class": self.params.state_backing.name,
        }


class _Queue:
    """One bounded engine submission queue with an outstanding limit."""

    __slots__ = ("name", "depth", "max_outstanding", "_completions",
                 "max_occupancy", "stall_cycles", "admitted")

    def __init__(self, name: str, depth: int, max_outstanding: int) -> None:
        self.name = name
        self.depth = depth
        self.max_outstanding = max_outstanding
        self._completions: list[int] = []
        self.max_occupancy = 0
        self.stall_cycles = 0
        self.admitted = 0

    @property
    def bound(self) -> int:
        return max(1, min(self.depth, self.max_outstanding))

    def _drain(self, now: int) -> None:
        if self._completions:
            self._completions = [c for c in self._completions if c > now]

    def admit(self, arrival: int) -> tuple[int, int]:
        """Block until a credit is free; return ``(admit_cycle, stall)``."""
        self._drain(arrival)
        now = arrival
        while len(self._completions) >= self.bound:
            now = min(self._completions)
            self._drain(now)
        stall = max(0, now - arrival)
        self.stall_cycles += stall
        return now, stall

    def push(self, completion: int) -> None:
        self._completions.append(completion)
        self.admitted += 1
        self.max_occupancy = max(self.max_occupancy, len(self._completions))

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "max_outstanding": self.max_outstanding,
            "occupancy_bound": self.bound,
            "observed_max_occupancy": self.max_occupancy,
            "admitted": self.admitted,
            "credit_stall_cycles": self.stall_cycles,
        }


class _EngineUnit:
    """One engine family's datapath occupancy."""

    __slots__ = ("name", "params", "free_at", "busy_cycles", "operations",
                 "compute_cycles", "memory_stall_cycles", "work_units", "bytes")

    def __init__(self, name: str, params: EngineParams) -> None:
        self.name = name
        self.params = params
        self.free_at = 0
        self.busy_cycles = 0
        self.operations = 0
        self.compute_cycles = 0
        self.memory_stall_cycles = 0
        self.work_units = 0
        self.bytes = 0

    def to_dict(self, span: int) -> dict[str, Any]:
        return {
            "operations": self.operations,
            "busy_cycles": self.busy_cycles,
            "idle_cycles": max(0, span - self.busy_cycles),
            "compute_bound_cycles": self.compute_cycles,
            "memory_stall_cycles": self.memory_stall_cycles,
            "work_units": self.work_units,
            "bytes_touched": self.bytes,
            "utilisation": _round(self.busy_cycles / span) if span else 0.0,
            "structure": self.params.to_dict(),
        }


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class CycleRequest:
    """A bounded host request, exactly as the functional device receives it."""

    entrypoint_id: int = 0
    symbols: dict[int, int] = dc_field(default_factory=dict)
    generation_policy_id: int = NO_ID
    transactions: int = 1
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        named: dict[str, int] = {}
        for key, value in sorted(self.symbols.items()):
            try:
                named[Symbol(int(key)).name] = int(value)
            except ValueError:
                named[str(key)] = int(value)
        return {
            "entrypoint_id": self.entrypoint_id,
            "generation_policy_id": self.generation_policy_id,
            "transactions": self.transactions,
            "label": self.label,
            "symbols": named,
        }

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "CycleRequest":
        symbols: dict[int, int] = {}
        for key, value in (body.get("symbols") or {}).items():
            if isinstance(key, str) and not key.lstrip("-").isdigit():
                symbols[int(Symbol[key])] = int(value)
            else:
                symbols[int(key)] = int(value)
        return cls(
            entrypoint_id=int(body.get("entrypoint_id", 0)),
            symbols=symbols,
            generation_policy_id=int(body.get("generation_policy_id", NO_ID)),
            transactions=int(body.get("transactions", 1)),
            label=str(body.get("label", "")),
        )


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class CycleResult:
    """Everything one cycle-model run produced."""

    body: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.body

    @property
    def total_cycles(self) -> int:
        return int(self.body["timing"]["total_cycles"])

    @property
    def architectural(self) -> dict[str, int]:
        return dict(self.body["counters"]["architectural"])

    @property
    def timing(self) -> dict[str, int]:
        return dict(self.body["counters"]["timing"])

    @property
    def provenance_class(self) -> str:
        return str(self.body["provenance"]["class"])


# ---------------------------------------------------------------------------
# Static proofs
# ---------------------------------------------------------------------------
def prove_acyclic_waits(device: Device) -> dict[str, Any]:
    """Prove that no admitted wait can close a cycle on an in-order sequencer.

    ADR-003 section 5 makes the microsequencer deterministic and in-order, and
    section 9 makes events single-assignment.  Under those two rules a wait can
    only deadlock if it names an event whose single signaller is *at or after*
    the waiting instruction in program order: the sequencer would never reach
    the signaller.  Both conditions are decidable statically over the program,
    so this is a proof for the admitted schedule and not a sampled observation.
    """
    signaller: dict[int, int] = {}
    duplicates: list[dict[str, int]] = []
    for index, instruction in enumerate(device.instructions):
        event = instruction.signal_event_id
        if event == NO_ID:
            continue
        if event in signaller:
            duplicates.append({"event": event, "instruction": index})
            continue
        signaller[event] = index
    edges = 0
    violations: list[dict[str, Any]] = []
    for index, instruction in enumerate(device.instructions):
        if instruction.wait_set_id == NO_ID:
            continue
        wait = device.deployment.table.get(
            instruction.wait_set_id, ExtendedDescriptorType.EVENT_WAIT_SET
        )
        for slot in range(wait.payload["producer_count"]):
            event = wait.payload[f"producer_{slot}"]
            producer = signaller.get(event)
            edges += 1
            if producer is None:
                violations.append(
                    {
                        "kind": "unsignalled_event",
                        "instruction": index,
                        "event": event,
                    }
                )
            elif producer >= index:
                violations.append(
                    {
                        "kind": "wait_on_later_or_self_signal",
                        "instruction": index,
                        "event": event,
                        "producer_instruction": producer,
                    }
                )
    return {
        "proved": not violations and not duplicates,
        "rule": (
            "in-order issue plus single-assignment events: a wait is acyclic "
            "iff every producer is signalled strictly earlier in program order"
        ),
        "dependency_edges": edges,
        "events_signalled": len(signaller),
        "duplicate_signals": duplicates,
        "violations": violations,
    }


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------
class CycleModel:
    """One event-driven cycle model for all four ABI 3.0 targets."""

    def __init__(
        self,
        deployment: Deployment,
        capability: Capability,
        cost_table: CostTable,
        *,
        root: Path | None = None,
        verify: bool = True,
    ) -> None:
        self.deployment = deployment
        self.capability = capability
        self.machine = MachineModel(capability, cost_table)
        self.root = root
        self.verify = verify
        self.topology_class = TopologyClass(int(deployment.topology_class))
        self.sequencer: SequencerParams = self.machine.sequencer()
        self.memory_params: MemoryParams = self.machine.memory()
        self.engine_params: dict[str, EngineParams] = {
            name: self.machine.engine(name)
            for name in sorted(ENGINE_FAMILY_NAMES.values())
        }
        self.fabric = build_fabric(self.machine, self.topology_class)
        self.gaps: list[dict[str, str]] = []

    # -- gap reporting ---------------------------------------------------
    def _gap(self, where: str, detail: str) -> None:
        record = {"where": where, "detail": detail}
        if record not in self.gaps:
            self.gaps.append(record)

    # -- one node --------------------------------------------------------
    def run_node(
        self,
        request: CycleRequest,
        *,
        node_id: int = 0,
        node_count: int = 1,
        fabric: ClusterFabric | WaferFabric | None = None,
    ) -> dict[str, Any]:
        """Execute and time one logical node's share of ``request``."""
        device = TracingDevice(
            self.deployment, self.capability, root=self.root, verify=self.verify
        )
        session = device.create_session()
        symbols = effective_symbols(request, node_id=node_id, node_count=node_count)

        queues = {
            name: _Queue(name, params.queue_depth, params.max_outstanding)
            for name, params in sorted(self.engine_params.items())
        }
        engines = {
            name: _EngineUnit(name, params)
            for name, params in sorted(self.engine_params.items())
        }
        memory = MemorySystem(self.memory_params)
        counters = CounterSet()
        architectural = CounterSet()

        seq = self.sequencer
        seq_free = 0
        events: dict[int, int] = {}
        totals = {
            "issue_cycles": 0,
            "fetch_cycles": 0,
            "wait_stall": 0,
            "queue_stall": 0,
            "compute": 0,
            "memory_stall": 0,
            "transaction_cycles": 0,
        }
        fabric_timings: list[FabricTiming] = []
        results: list[TransactionResult] = []
        produced: list[int] = []
        end_cycle = 0
        step_cursor = 0

        for _ in range(max(1, request.transactions)):
            if session.finished:
                break
            transaction_start = seq_free
            result = device.run_transaction(
                session,
                entrypoint_id=request.entrypoint_id,
                symbols=symbols,
                generation_policy_id=request.generation_policy_id,
            )
            results.append(result)
            produced.extend(result.produced_tokens)
            for name, value in result.counters.items():
                architectural.add(name, value)
            steps = device.steps[step_cursor:]
            step_cursor = len(device.steps)
            events.clear()  # events are single-assignment *within* a transaction
            seq_free, end_cycle = self._time_steps(
                steps,
                seq_free,
                queues=queues,
                engines=engines,
                memory=memory,
                events=events,
                totals=totals,
                counters=counters,
                fabric=fabric if fabric is not None else self.fabric,
                fabric_timings=fabric_timings,
                node_id=node_id,
                node_count=node_count,
            )
            totals["transaction_cycles"] += max(0, end_cycle - transaction_start)
            if result.status != CompletionStatus.SUCCESS:
                break

        span = max(end_cycle, seq_free, 1)
        engine_busy = sum(unit.busy_cycles for unit in engines.values())
        link_cycles = sum(
            t.cycles for t in fabric_timings if not t.operation.startswith("collective")
            and t.operation != "barrier"
        )
        collective_cycles = sum(
            t.cycles for t in fabric_timings if t.operation.startswith("collective")
        )
        barrier_cycles = sum(t.cycles for t in fabric_timings if t.operation == "barrier")

        counters.add("latency.transaction_cycles", totals["transaction_cycles"])
        counters.add("latency.issue_cycles", totals["issue_cycles"])
        counters.add(
            "latency.stall_cycles", totals["wait_stall"] + totals["queue_stall"]
        )
        counters.add("latency.queue_stall_cycles", totals["queue_stall"])
        counters.add("latency.wait_stall_cycles", totals["wait_stall"])
        counters.add("latency.sequencer_fetch_cycles", totals["fetch_cycles"])
        counters.add("latency.compute_cycles", totals["compute"])
        counters.add("latency.memory_stall_cycles", totals["memory_stall"])
        counters.add("latency.engine_busy_cycles", engine_busy)
        counters.add(
            "latency.engine_idle_cycles",
            max(0, span * len(engines) - engine_busy),
        )
        counters.add("latency.hbm_busy_cycles", memory.stats["hbm"].busy_cycles)
        counters.add("latency.sram_busy_cycles", memory.stats["sram"].busy_cycles)
        counters.add("latency.rom_busy_cycles", memory.stats["rom"].busy_cycles)
        counters.add("latency.host_busy_cycles", memory.stats["host"].busy_cycles)
        counters.add(
            "latency.sram_bank_conflict_cycles", memory.stats["sram"].conflict_cycles
        )
        counters.add(
            "latency.hbm_channel_conflict_cycles", memory.stats["hbm"].conflict_cycles
        )
        counters.add("latency.collective_cycles", collective_cycles)
        counters.add("latency.barrier_cycles", barrier_cycles)
        for timing in fabric_timings:
            for name, value in timing.counters().items():
                if is_timing_counter(name):
                    counters.add(name, value)

        # ``queue.max_occupancy`` lives in registry group 0x02, which is an
        # architectural group, but only a queue-modelling implementation can
        # fill it in.  Writing it here would break agreement with the functional
        # device, so it is reported in the queue and proof blocks instead and
        # the registry wrinkle is recorded as a contract gap.
        occupancy = 0
        for name, queue in queues.items():
            occupancy = max(occupancy, queue.max_occupancy)
            if queue.max_occupancy > queue.bound:
                raise MachineError(
                    f"queue {name} reached occupancy {queue.max_occupancy} above "
                    f"its proved bound {queue.bound}"
                )

        return {
            "node_id": node_id,
            "device": device,
            "session": session,
            "results": results,
            "produced_tokens": produced,
            "span": span,
            "end_cycle": end_cycle,
            "queues": queues,
            "engines": engines,
            "memory": memory,
            "counters": counters,
            "architectural": architectural,
            "totals": totals,
            "fabric_timings": fabric_timings,
            "link_cycles": link_cycles,
            "collective_cycles": collective_cycles,
            "barrier_cycles": barrier_cycles,
            "engine_busy": engine_busy,
            "addresses": device.addresses,
            "queue_max_occupancy": occupancy,
        }

    # -- the event loop ---------------------------------------------------
    def _time_steps(
        self,
        steps: Sequence[TraceStep],
        seq_free: int,
        *,
        queues: dict[str, _Queue],
        engines: dict[str, _EngineUnit],
        memory: MemorySystem,
        events: dict[int, int],
        totals: dict[str, int],
        counters: CounterSet,
        fabric: ClusterFabric | WaferFabric | None,
        fabric_timings: list[FabricTiming],
        node_id: int,
        node_count: int,
    ) -> tuple[int, int]:
        """Advance the machine over one transaction's architectural steps."""
        seq = self.sequencer
        end_cycle = seq_free
        for step in steps:
            if step.kind == "PREDICATE":
                # A predicated-off instruction still costs fetch and predicate
                # evaluation; that is why predicates are timed separately.
                seq_free += seq.fetch_cycles + seq.predicate_cycles
                totals["fetch_cycles"] += seq.fetch_cycles
                end_cycle = max(end_cycle, seq_free)
                continue
            if step.kind == "COMMIT":
                # The atomic state commit happens at the end of the transaction
                # and moves real bytes; it is timed on the state engine.
                unit = engines["state"]
                start = max(seq_free, unit.free_at)
                finish, conflicts = memory.schedule(step.accesses, start)
                service = max(finish - start, unit.params.minimum_cycles)
                unit.free_at = start + service
                unit.busy_cycles += service
                unit.operations += 1
                unit.bytes += step.bytes_moved
                unit.memory_stall_cycles += max(0, finish - start)
                totals["memory_stall"] += max(0, finish - start)
                seq_free = start + service
                end_cycle = max(end_cycle, seq_free)
                continue

            arrival = seq_free + seq.fetch_cycles + seq.decode_cycles
            totals["fetch_cycles"] += seq.fetch_cycles
            if step.wait_producers:
                ready = arrival
                for event in step.wait_producers:
                    ready = max(ready, events.get(event, arrival))
                ready += seq.wait_check_cycles
                if ready > arrival:
                    totals["wait_stall"] += ready - arrival
                arrival = ready

            if step.kind == "CONTROL":
                cost = seq.issue_cycles
                sub = Control(step.sub)
                if sub is Control.BRANCH:
                    cost += seq.branch_cycles
                elif sub in (Control.LOOP_SETUP, Control.LOOP_NEXT):
                    cost += seq.loop_cycles
                seq_free = arrival + cost
                totals["issue_cycles"] += cost
                if step.signal_event_id != NO_ID:
                    events[step.signal_event_id] = seq_free
                end_cycle = max(end_cycle, seq_free)
                continue

            if step.family not in queues:
                # OBSERVATION and RECOVERY retire in the microsequencer itself:
                # ADR-003 section 7 gives them no engine queue, so they cost an
                # issue slot and nothing else.
                seq_free = arrival + seq.issue_cycles
                totals["issue_cycles"] += seq.issue_cycles
                if step.signal_event_id != NO_ID:
                    events[step.signal_event_id] = seq_free
                end_cycle = max(end_cycle, seq_free)
                continue
            family = step.family
            queue = queues[family]
            unit = engines[family]
            admitted, stall = queue.admit(arrival)
            totals["queue_stall"] += stall
            seq_free = admitted + seq.issue_cycles
            totals["issue_cycles"] += seq.issue_cycles

            if step.trapped:
                # The transaction faults at issue: nothing is enqueued and the
                # engine never runs.  Timing stops where the device stopped.
                end_cycle = max(end_cycle, seq_free)
                continue

            start = max(admitted + seq.queue_transit_cycles, unit.free_at)
            compute = self._compute_cycles(step, unit.params)
            memory_finish, _conflicts = memory.schedule(step.accesses, start)
            memory_span = max(0, memory_finish - start)
            service = max(compute, memory_span, unit.params.minimum_cycles)
            if family == "link" and fabric is not None:
                timing = self._time_link(step, fabric, start, node_id, node_count)
                if timing is not None:
                    fabric_timings.append(timing)
                    # Only the *timing* half of the fabric's counters is
                    # applied.  Architectural link counters (group 0x0a) come
                    # from the functional engine, never from the fabric model,
                    # so the two models cannot disagree on a non-timing counter.
                    service = max(service, timing.cycles)
            unit.free_at = start + service
            unit.busy_cycles += service
            unit.operations += 1
            unit.compute_cycles += compute
            unit.memory_stall_cycles += max(0, memory_span - compute)
            unit.work_units += self._work_units(step, family)
            unit.bytes += step.bytes_moved
            totals["compute"] += compute
            totals["memory_stall"] += max(0, memory_span - compute)
            finish = start + service + unit.params.fixed_latency_cycles
            queue.push(finish)
            if step.signal_event_id != NO_ID:
                events[step.signal_event_id] = finish
            end_cycle = max(end_cycle, finish)
        return seq_free, max(end_cycle, seq_free)

    @staticmethod
    def _work_units(step: TraceStep, family: str) -> int:
        return sum(
            step.counter_delta.get(name, 0)
            for name in FAMILY_WORK_COUNTERS.get(family, ())
        )

    def _compute_cycles(self, step: TraceStep, params: EngineParams) -> int:
        work = self._work_units(step, params.family)
        if work:
            rate = params.lanes * params.work_per_lane_cycle
            cycles = math.ceil(work / rate)
        else:
            nbytes = step.bytes_moved
            cycles = math.ceil(nbytes / params.bytes_per_cycle) if nbytes else 0
        return max(cycles, params.minimum_cycles)

    def _time_link(
        self,
        step: TraceStep,
        fabric: ClusterFabric | WaferFabric,
        start: int,
        node_id: int,
        node_count: int,
    ) -> FabricTiming | None:
        """Time one executed LINK operation on the physical fabric."""
        try:
            descriptor = self.deployment.table.get(
                step.descriptor_id, ExtendedDescriptorType.COMMUNICATION
            )
        except Exception:
            self._gap(
                "LINK instruction",
                "the LINK instruction does not reference a COMMUNICATION "
                "descriptor, so the fabric has nothing to time",
            )
            return None
        payload = descriptor.payload
        endpoints = fabric.endpoints()
        source = int(payload["source_node"])
        destination = int(payload["destination_node"])
        if source >= endpoints:
            source = node_id % endpoints
        if destination >= endpoints:
            destination = (node_id + 1) % endpoints
        nbytes = int(payload["byte_extent"])
        sub = Link(step.sub)
        participants = list(
            range(min(max(int(payload["participant_count"]), 1), endpoints))
        )
        if sub is Link.BARRIER:
            return fabric.barrier(participants, start_cycle=start)
        if sub in (Link.COLLECTIVE, Link.MULTICAST, Link.GATHER, Link.SCATTER):
            op = int(payload["collective_op"])
            if sub is Link.MULTICAST:
                op = int(CollectiveOp.BROADCAST)
            elif sub is Link.GATHER:
                op = int(CollectiveOp.CONCAT)
            elif sub is Link.SCATTER:
                op = int(CollectiveOp.REDUCE_SCATTER)
            return fabric.collective(
                op,
                participants,
                nbytes,
                start_cycle=start,
                chunk_bytes=int(payload["chunk_bytes"]),
            )
        return fabric.unicast(
            source,
            destination,
            nbytes,
            start_cycle=start,
            operation=f"link.{sub.name}",
        )

    # -- declared (not executed) communication ---------------------------
    def declared_communication(
        self, fabric: ClusterFabric | WaferFabric
    ) -> dict[str, Any]:
        """Time every COMMUNICATION descriptor the deployment declares.

        This is *not* an execution result.  It is what the fabric would cost if
        every declared transfer ran once, and it exists so that a topology cost
        is visible even before the link engine is implemented.  It is reported
        under its own key and is never folded into the executed timing.
        """
        entries: list[dict[str, Any]] = []
        total = 0
        for did in self.deployment.table.ids_of_type(
            ExtendedDescriptorType.COMMUNICATION
        ):
            descriptor = self.deployment.table[did]
            payload = descriptor.payload
            endpoints = fabric.endpoints()
            participants = list(
                range(min(max(int(payload["participant_count"]), 1), endpoints))
            )
            op = int(payload["collective_op"])
            nbytes = int(payload["byte_extent"])
            if CollectiveOp(op) is CollectiveOp.POINT_TO_POINT:
                source = int(payload["source_node"])
                destination = int(payload["destination_node"])
                timing = fabric.unicast(
                    source if source < endpoints else 0,
                    destination if destination < endpoints else min(1, endpoints - 1),
                    nbytes,
                    operation="declared.unicast",
                )
            else:
                timing = fabric.collective(op, participants, nbytes)
            total += timing.cycles
            entries.append({"descriptor_id": did, **timing.to_dict()})
        return {
            "status": "declared_not_executed",
            "note": (
                "cost of every COMMUNICATION descriptor in the deployment, timed "
                "once on this fabric; it is not an execution measurement and is "
                "not included in the executed timing"
            ),
            "descriptor_count": len(entries),
            "total_cycles": total,
            "entries": entries,
        }

    # -- public entry points ---------------------------------------------
    def run(self, request: CycleRequest) -> CycleResult:
        """Run ``request`` on this deployment's own topology class."""
        if self.topology_class is TopologyClass.CLUSTER_32:
            return self._run_cluster(request)
        return self._run_single(request)

    # -- single logical device -------------------------------------------
    def _run_single(self, request: CycleRequest) -> CycleResult:
        node = self.run_node(request, node_id=0, node_count=1, fabric=self.fabric)
        body = self._common_body(request, [node])
        span = node["span"]
        body["timing"] = self._timing_block(node, span)
        body["engines"] = {
            name: unit.to_dict(span) for name, unit in sorted(node["engines"].items())
        }
        body["queues"] = {
            name: queue.to_dict() for name, queue in sorted(node["queues"].items())
        }
        body["memory"] = node["memory"].report(span)
        body["memory"]["address_placement"] = node["addresses"].to_dict()
        body["counters"] = self._counter_block(node)
        body["proofs"] = self._proof_block(node)
        body["rates"] = self._rate_block(node, span)
        if self.fabric is not None:
            body["fabric"] = self.fabric.to_dict()
            body["fabric"]["executed"] = self._fabric_block(node)
            body["fabric"]["declared"] = self.declared_communication(self.fabric)
        body["gaps"] = list(self.gaps)
        body["provenance"] = self.machine.provenance_report()
        return CycleResult(body)

    # -- 32-node cluster ---------------------------------------------------
    def _run_cluster(self, request: CycleRequest) -> CycleResult:
        assert isinstance(self.fabric, ClusterFabric)
        nodes = self.fabric.endpoints()
        topology_nodes = self._topology_node_count()
        if topology_nodes and topology_nodes != nodes:
            self._gap(
                "topology descriptor vs capability",
                f"the topology descriptor declares {topology_nodes} nodes but the "
                f"capability admits {nodes}; the fabric was built for {nodes}",
            )
        spmd = self._node_invariant()
        replays = 1 if spmd else nodes
        per_node: list[dict[str, Any]] = []
        for index in range(replays):
            per_node.append(
                self.run_node(
                    request, node_id=index, node_count=nodes, fabric=self.fabric
                )
            )
        if spmd and nodes > 1:
            # Every node executes the identical instruction stream: the model
            # replays one and states that it did, rather than pretending to 32
            # independent measurements of the same thing.
            per_node = [dict(per_node[0], node_id=n) for n in range(nodes)]

        ends = [node["end_cycle"] for node in per_node]
        critical = max(ends) if ends else 0
        slowest = min(ends) if ends else 0
        body = self._common_body(request, per_node)
        span = max(critical, 1)
        primary = per_node[0]
        body["timing"] = self._timing_block(primary, span)
        body["timing"]["cluster_critical_path_cycles"] = critical
        body["engines"] = {
            name: unit.to_dict(span) for name, unit in sorted(primary["engines"].items())
        }
        body["queues"] = {
            name: queue.to_dict() for name, queue in sorted(primary["queues"].items())
        }
        body["memory"] = primary["memory"].report(span)
        body["memory"]["address_placement"] = primary["addresses"].to_dict()
        body["counters"] = self._counter_block(primary)
        body["proofs"] = self._proof_block(primary)
        body["rates"] = self._rate_block(primary, span)
        body["fabric"] = self.fabric.to_dict()
        body["fabric"]["executed"] = self._fabric_block(primary)
        body["fabric"]["declared"] = self.declared_communication(self.fabric)
        body["cluster"] = {
            "nodes": nodes,
            "replay_mode": "spmd_identical" if spmd else "per_node",
            "replays_executed": replays,
            "blended_total_reported": False,
            "note": (
                "per-node compute, link, collective and idle/skew are reported "
                "separately; there is deliberately no single blended cluster "
                "number, because the four costs have different physical causes"
            ),
            "per_node": [
                {
                    "node": node["node_id"],
                    "compute_cycles": node["totals"]["compute"],
                    "engine_busy_cycles": node["engine_busy"],
                    "memory_stall_cycles": node["totals"]["memory_stall"],
                    "issue_cycles": node["totals"]["issue_cycles"],
                    "queue_stall_cycles": node["totals"]["queue_stall"],
                    "wait_stall_cycles": node["totals"]["wait_stall"],
                    "link_cycles": node["link_cycles"],
                    "collective_cycles": node["collective_cycles"],
                    "barrier_cycles": node["barrier_cycles"],
                    "end_cycle": node["end_cycle"],
                    "idle_cycles": max(
                        0, node["end_cycle"] - node["engine_busy"]
                    ),
                    "skew_cycles": critical - node["end_cycle"],
                }
                for node in per_node
            ],
            "aggregate": {
                "critical_path_cycles": critical,
                "earliest_node_end_cycle": slowest,
                "skew_cycles": critical - slowest,
                "compute_cycles_total": sum(
                    n["totals"]["compute"] for n in per_node
                ),
                "link_cycles_total": sum(n["link_cycles"] for n in per_node),
                "collective_cycles_total": sum(
                    n["collective_cycles"] for n in per_node
                ),
                "barrier_cycles_total": sum(n["barrier_cycles"] for n in per_node),
                "idle_skew_cycles_total": sum(
                    critical - n["end_cycle"] for n in per_node
                ),
            },
        }
        counters = primary["counters"]
        counters.add(
            "latency.node_skew_cycles", sum(critical - n["end_cycle"] for n in per_node)
        )
        body["counters"] = self._counter_block(primary)
        body["gaps"] = list(self.gaps)
        body["provenance"] = self.machine.provenance_report()
        return CycleResult(body)

    # -- report blocks ----------------------------------------------------
    def _topology_node_count(self) -> int:
        for did in self.deployment.table.ids_of_type(ExtendedDescriptorType.TOPOLOGY):
            return int(self.deployment.table[did].payload["node_count"])
        return 0

    def _node_invariant(self) -> bool:
        """True when no descriptor makes the program depend on ``NODE_ID``."""
        node_symbol = int(Symbol.NODE_ID)
        for descriptor in self.deployment.table.descriptors():
            kind = descriptor.descriptor_type
            payload = descriptor.payload
            if kind == ExtendedDescriptorType.TENSOR_VIEW:
                for slot in range(payload["dynamic_term_count"]):
                    if (
                        payload[f"term{slot}_kind"] == int(SelectorKind.RUNTIME_SYMBOL)
                        and payload[f"term{slot}_index"] == node_symbol
                    ):
                        return False
            elif kind == ExtendedDescriptorType.PREDICATE:
                if payload["selector_index"] == node_symbol:
                    return False
            elif kind == ExtendedDescriptorType.LOOP_CONTROL:
                if payload["bound_symbol_id"] == node_symbol:
                    return False
        return True

    def _timing_block(self, node: dict[str, Any], span: int) -> dict[str, Any]:
        totals = node["totals"]
        clock = self.machine.clock_hz
        return {
            "total_cycles": span,
            "clock_frequency_hz": clock,
            "seconds": _round_seconds(span / clock),
            "transaction_cycles": totals["transaction_cycles"],
            "issue_cycles": totals["issue_cycles"],
            "sequencer_fetch_cycles": totals["fetch_cycles"],
            "stall_cycles": totals["wait_stall"] + totals["queue_stall"],
            "queue_stall_cycles": totals["queue_stall"],
            "wait_stall_cycles": totals["wait_stall"],
            "compute_cycles": totals["compute"],
            "memory_stall_cycles": totals["memory_stall"],
            "engine_busy_cycles": node["engine_busy"],
            "link_cycles": node["link_cycles"],
            "collective_cycles": node["collective_cycles"],
            "barrier_cycles": node["barrier_cycles"],
        }

    def _counter_block(self, node: dict[str, Any]) -> dict[str, Any]:
        architectural = node["architectural"].snapshot()
        timing = node["counters"].snapshot()
        overlap = sorted(set(architectural) & set(timing))
        return {
            "registry_size": len(COUNTERS),
            "architectural": architectural_counters(architectural),
            "timing": timing_counters(timing),
            "microarchitectural": {
                "queue.max_occupancy": node["queue_max_occupancy"],
            },
            "timing_group": "0x0c",
            "overlap": overlap,
            "agreement_rule": (
                "every counter outside registry group 0x0c must equal the "
                "functional device's value for the same deployment and request"
            ),
        }

    def _proof_block(self, node: dict[str, Any]) -> dict[str, Any]:
        queues = node["queues"]
        observed = {name: q.max_occupancy for name, q in sorted(queues.items())}
        bounds = {name: q.bound for name, q in sorted(queues.items())}
        violations = [
            name for name in queues if observed[name] > bounds[name]
        ]
        proofs: dict[str, Any] = {
            "bounded_queue_occupancy": {
                "proved": not violations,
                "rule": (
                    "issue is credit-gated: an engine descriptor enters a queue "
                    "only when occupancy is below min(queue_depth, "
                    "max_outstanding), so occupancy is bounded by construction"
                ),
                "bounds": bounds,
                "observed_max": observed,
                "violations": violations,
            },
            "acyclic_waits": prove_acyclic_waits(node["device"]),
        }
        if self.fabric is not None:
            proofs["no_zero_latency_global_operations"] = (
                assert_no_zero_latency_global_operations(self.fabric)
            )
        else:
            proofs["no_zero_latency_global_operations"] = {
                "proved": True,
                "rule": (
                    "single-chip topology has no inter-node fabric; no global "
                    "barrier or collective is expressible, so none is modelled "
                    "as zero-latency"
                ),
                "checked": [],
            }
        return proofs

    def _fabric_block(self, node: dict[str, Any]) -> dict[str, Any]:
        timings = node["fabric_timings"]
        return {
            "operations": len(timings),
            "link_cycles": node["link_cycles"],
            "collective_cycles": node["collective_cycles"],
            "barrier_cycles": node["barrier_cycles"],
            "detail": [timing.to_dict() for timing in timings],
        }

    def _rate_block(self, node: dict[str, Any], span: int) -> list[dict[str, Any]]:
        """Every reported rate, with the provenance of every input it used."""
        clock = self.machine.clock_hz
        seconds = span / clock if clock else 0.0
        architectural = node["architectural"].snapshot()
        rates: list[dict[str, Any]] = []

        def emit(name: str, value: float, unit: str, inputs: list[str], note: str = ""):
            entry = {
                "name": name,
                "value": _round(value),
                "unit": unit,
                "provenance": self.machine.rate_provenance(inputs),
            }
            if note:
                entry["note"] = note
            rates.append(entry)

        emit(
            "transactions_per_second",
            (len(node["results"]) / seconds) if seconds else 0.0,
            "1/s",
            ["clock.frequency_hz"],
        )
        tokens = len(node["produced_tokens"])
        emit(
            "tokens_per_second",
            (tokens / seconds) if seconds and tokens else 0.0,
            "tokens/s",
            ["clock.frequency_hz"],
            "" if tokens else "no token was selected in this run",
        )
        emit(
            "instructions_per_cycle",
            architectural.get("instructions.retired", 0) / span if span else 0.0,
            "1/cycle",
            ["clock.frequency_hz"],
        )
        for klass, prefix in (
            ("hbm", "hbm"),
            ("sram", "sram"),
            ("rom", "rom"),
        ):
            stats = node["memory"].stats[klass]
            total = stats.bytes_read + stats.bytes_written
            params = self.memory_params.klass(StorageClass[klass.upper()])
            inputs = ["clock.frequency_hz"]
            for candidate in (
                f"{prefix}.bytes_per_cycle_per_channel",
                f"{prefix}.bytes_per_cycle_per_port",
                f"{prefix}.bytes_per_cycle_per_array",
                f"{prefix}.channels",
                f"{prefix}.banks",
                f"{prefix}.arrays",
                f"{prefix}.read_latency_cycles",
                f"{prefix}.transaction_bytes",
                f"{prefix}.interleave_bytes",
            ):
                if candidate in self.machine.used():
                    inputs.append(candidate)
            emit(
                f"{klass}_bytes_per_second",
                (total / seconds) if seconds else 0.0,
                "B/s",
                inputs,
            )
            emit(
                f"{klass}_bandwidth_utilisation",
                (total / (params.peak_bytes_per_cycle * span)) if span else 0.0,
                "fraction",
                inputs,
            )
        return rates

    def _common_body(
        self, request: CycleRequest, nodes: list[dict[str, Any]]
    ) -> dict[str, Any]:
        primary = nodes[0]
        results = primary["results"]
        last = results[-1] if results else None
        return {
            "schema": CYCLE_RESULT_SCHEMA,
            "abi": {"major": 3, "minor": 0},
            "inputs": {
                "deployment_id": self.deployment.deployment_id,
                "deployment_generation": self.deployment.generation,
                "deployment_digest": self.deployment.deployment_digest.hex(),
                "target_id": self.deployment.target_id,
                "model_id": self.deployment.model_id,
                "backend": self.deployment.backend,
                "topology_class": self.topology_class.name,
                "capability_digest": self.capability.digest,
                "capability_technology_view": self.capability.technology_view,
                "cost_table": self.machine.cost_table.to_dict(),
                "request": request.to_dict(),
            },
            "machine": {
                "sequencer": self.sequencer.to_dict(),
                "memory": self.memory_params.to_dict(),
                "engines": {
                    name: params.to_dict()
                    for name, params in sorted(self.engine_params.items())
                },
            },
            "execution": {
                "transactions": len(results),
                "status": CompletionStatus(last.status).name if last else "NONE",
                "trap_class": TrapClass(last.trap_class).name if last else "NONE",
                "first_fault_instruction": last.first_fault_instruction if last else NO_ID,
                "message": last.message if last else "",
                "retired": sum(r.retired for r in results),
                "fetched": sum(r.fetched for r in results),
                "predicated_off": sum(r.predicated_off for r in results),
                "produced_tokens": list(primary["produced_tokens"]),
                "trace_steps": len(primary["device"].steps),
            },
        }


def run_deployment(
    deployment: Deployment,
    capability: Capability,
    cost_table: CostTable,
    request: CycleRequest,
    *,
    root: Path | None = None,
    verify: bool = True,
) -> CycleResult:
    """Convenience wrapper: build the model and run one request."""
    model = CycleModel(
        deployment, capability, cost_table, root=root, verify=verify
    )
    return model.run(request)


def functional_counters(
    deployment: Deployment,
    capability: Capability,
    request: CycleRequest,
    *,
    root: Path | None = None,
    verify: bool = True,
    node_id: int = 0,
    node_count: int = 1,
) -> dict[str, int]:
    """Architectural counters produced by the *functional* device alone.

    This is the reference side of the agreement test: a plain
    :class:`~runtime.sim.device.Device`, with no cycle-model instrumentation,
    running the same deployment and request.
    """
    device = Device(deployment, capability, root=root, verify=verify)
    session = device.create_session()
    counters = CounterSet()
    for _ in range(max(1, request.transactions)):
        if session.finished:
            break
        result = device.run_transaction(
            session,
            entrypoint_id=request.entrypoint_id,
            symbols=effective_symbols(request, node_id=node_id, node_count=node_count),
            generation_policy_id=request.generation_policy_id,
        )
        for name, value in result.counters.items():
            counters.add(name, value)
        if result.status != CompletionStatus.SUCCESS:
            break
    return architectural_counters(counters.snapshot())
