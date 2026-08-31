"""Machine parameters for the ABI 3.0 cycle model, with provenance.

ADR-003 section 19 defers every quantitative machine choice -- HBM channel and
stack count, SRAM bank count and macro organization, engine counts and lane
widths, NoC topology, link widths, physical queue depths, operating frequency --
to characterization.  Those are *capability values, not ABI semantics*.  This
module is where that separation is made mechanical:

* structural counts that an implementation advertises (engine lanes and queues,
  SRAM banks, HBM capacity, link fields, outstanding limits) are read from the
  :class:`~runtime.abi3.capability.Capability` record the deployment was
  compiled against;
* rates and latencies (bytes per cycle, cycles of latency, clock frequency) are
  read from a *separately versioned cost table*, so that a new characterization
  run changes timing without touching a deployment, a capability or the ABI.

Every value carries a provenance class:

``characterized``
    produced by a real synthesis / STA / place-and-route / SPICE run in this
    repository, cited by path;
``datasheet``
    a sourced external component -- an HBM stack, a link PHY -- cited by vendor
    document.  Per ADR-003 section 3.3 a public vendor figure is a *sourced
    reference envelope*, never an achieved OpenTallas value;
``assumed``
    a modelling choice with no evidence behind it yet.

A result that reads even one ``assumed`` parameter is labelled ``assumed`` at
the top level.  There is no way to report a rate without also reporting what it
rests on: :meth:`MachineModel.used` records every parameter actually read.
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Iterable, Mapping

from runtime.abi3.capability import Capability, canonical_json
from runtime.abi3.constants import Major, StorageClass, TopologyClass
from runtime.abi3.crc import sha256_hex

COST_TABLE_SCHEMA = "opentallas.abi3.cost_table.v1"

#: Prefix every cost table file must carry, so a table is discoverable and so
#: that ownership of the file set is unambiguous.
COST_TABLE_PREFIX = "abi3_cost_"


class MachineError(ValueError):
    """Raised when a machine parameter is missing, malformed or inconsistent.

    The model fails closed.  A missing cost-table entry is never silently
    defaulted, because a silent default is an unlabelled assumption and this
    module exists to make that impossible.
    """


class Provenance(str, enum.Enum):
    """Evidence class of one quantitative machine value."""

    CHARACTERIZED = "characterized"
    DATASHEET = "datasheet"
    ASSUMED = "assumed"

    @property
    def rank(self) -> int:
        return {"characterized": 0, "datasheet": 1, "assumed": 2}[self.value]


def worst(classes: Iterable[Provenance]) -> Provenance:
    """The weakest provenance in ``classes`` (``assumed`` dominates)."""
    worst_seen = Provenance.CHARACTERIZED
    for item in classes:
        if item.rank > worst_seen.rank:
            worst_seen = item
    return worst_seen


@dataclass(frozen=True, slots=True)
class ResolvedParameter:
    """One machine value together with where it came from."""

    name: str
    value: float | int | str
    unit: str
    provenance: Provenance
    source: str
    origin: str  # "cost_table" | "capability" | "descriptor"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "provenance": self.provenance.value,
            "source": self.source,
            "origin": self.origin,
        }
        if self.note:
            body["note"] = self.note
        return body


# ---------------------------------------------------------------------------
# Cost table
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class CostTable:
    """A separately versioned table of rates and latencies.

    The table is a plain JSON document so that a characterization run can emit
    one, and so that its digest can be bound into a result.  It is *not* part of
    the deployment: two cost tables applied to one deployment must give two
    timings and identical architectural counters.
    """

    cost_table_id: str
    version: str
    technology_view: str
    description: str
    parameters: dict[str, dict[str, Any]]
    path: Path | None = None
    raw: dict[str, Any] = dc_field(default_factory=dict)

    @property
    def digest(self) -> str:
        return sha256_hex(canonical_json(self.raw))

    def has(self, name: str) -> bool:
        return name in self.parameters

    def entry(self, name: str) -> dict[str, Any]:
        try:
            return self.parameters[name]
        except KeyError:
            raise MachineError(
                f"cost table {self.cost_table_id!r} has no parameter {name!r}; "
                "the cycle model refuses to substitute an unlabelled default"
            ) from None

    def resolve(self, name: str) -> ResolvedParameter:
        entry = self.entry(name)
        try:
            provenance = Provenance(entry["provenance"])
        except (KeyError, ValueError):
            raise MachineError(
                f"cost table parameter {name!r} has no legal provenance class; "
                f"expected one of {[p.value for p in Provenance]}"
            ) from None
        source = str(entry.get("source", ""))
        if provenance is not Provenance.ASSUMED and not source:
            raise MachineError(
                f"cost table parameter {name!r} claims provenance "
                f"{provenance.value!r} without citing a source"
            )
        return ResolvedParameter(
            name=name,
            value=entry["value"],
            unit=str(entry.get("unit", "")),
            provenance=provenance,
            source=source,
            origin="cost_table",
            note=str(entry.get("note", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cost_table_id": self.cost_table_id,
            "version": self.version,
            "technology_view": self.technology_view,
            "description": self.description,
            "sha256": self.digest,
            "path": str(self.path) if self.path is not None else "",
            "parameter_count": len(self.parameters),
        }

    @classmethod
    def from_dict(
        cls, body: Mapping[str, Any], *, path: Path | None = None
    ) -> "CostTable":
        if body.get("schema") != COST_TABLE_SCHEMA:
            raise MachineError(
                f"unexpected cost table schema {body.get('schema')!r}, "
                f"expected {COST_TABLE_SCHEMA!r}"
            )
        parameters = body.get("parameters")
        if not isinstance(parameters, dict) or not parameters:
            raise MachineError("cost table declares no parameters")
        for name, entry in parameters.items():
            if not isinstance(entry, dict) or "value" not in entry:
                raise MachineError(f"cost table parameter {name!r} has no value")
            if "provenance" not in entry:
                raise MachineError(
                    f"cost table parameter {name!r} carries no provenance class; "
                    "every quantitative value must be labelled"
                )
        return cls(
            cost_table_id=str(body["cost_table_id"]),
            version=str(body["version"]),
            technology_view=str(body.get("technology_view", "generic")),
            description=str(body.get("description", "")),
            parameters={str(k): dict(v) for k, v in parameters.items()},
            path=path,
            raw=json.loads(json.dumps(body, sort_keys=True)),
        )


def load_cost_table(path: str | Path) -> CostTable:
    """Read and validate a cost table from ``configs/hardware/abi3_cost_*.json``."""
    path = Path(path)
    if not path.exists():
        raise MachineError(f"cost table {path} does not exist")
    if not path.name.startswith(COST_TABLE_PREFIX):
        raise MachineError(
            f"cost table {path.name!r} does not use the reserved "
            f"{COST_TABLE_PREFIX!r} prefix"
        )
    body = json.loads(path.read_text())
    return CostTable.from_dict(body, path=path)


# ---------------------------------------------------------------------------
# Structural view of one capability
# ---------------------------------------------------------------------------
ENGINE_FAMILY_NAMES: dict[int, str] = {
    int(Major.DMA): "dma",
    int(Major.TENSOR): "tensor",
    int(Major.VECTOR): "vector",
    int(Major.ATTENTION): "attention",
    int(Major.ROUTE): "route",
    int(Major.REDUCTION): "reduction",
    int(Major.SELECTION): "selection",
    int(Major.STATE): "state",
    int(Major.LINK): "link",
}

FAMILY_BY_NAME: dict[str, int] = {v: k for k, v in ENGINE_FAMILY_NAMES.items()}

#: Which counter, if any, measures the useful work of one engine family, and how
#: many of those work units one lane retires per cycle is a *cost table* value.
#: An empty tuple means the family has no work counter and is timed from the
#: bytes it actually moved -- which is the right measure for DMA and link.
FAMILY_WORK_COUNTERS: dict[str, tuple[str, ...]] = {
    "dma": (),
    "tensor": ("tensor.multiplications", "tensor.additions"),
    "vector": ("vector.elements", "vector.activation_elements"),
    "attention": (
        "attention.score_multiplications",
        "attention.value_multiplications",
    ),
    "route": ("route.topk_candidates", "route.hash_lookups"),
    "reduction": ("reduction.elements",),
    "selection": ("selection.vocabulary_elements",),
    "state": ("state.rows_committed",),
    "link": (),
}

#: Technology views whose capability-advertised structure is backed by a real
#: characterization run.  Anything else is an advertised structure with no
#: physical evidence yet, and its structural counts are labelled ``assumed``.
CHARACTERIZED_TECHNOLOGY_VIEWS = frozenset({"sky130", "asap7"})


# ---------------------------------------------------------------------------
# Machine model
# ---------------------------------------------------------------------------
class MachineModel:
    """Machine parameters for one (capability, cost table) pair.

    Every read goes through :meth:`value`, which records the resolved parameter.
    :meth:`used` is therefore an exact dependency list for whatever the model
    computed, and :meth:`provenance_class` is the weakest link in it.
    """

    def __init__(self, capability: Capability, cost_table: CostTable) -> None:
        self.capability = capability
        self.cost_table = cost_table
        self._used: dict[str, ResolvedParameter] = {}
        capability.validate()
        self._capability_provenance = (
            Provenance.CHARACTERIZED
            if capability.technology_view in CHARACTERIZED_TECHNOLOGY_VIEWS
            else Provenance.ASSUMED
        )
        self._capability_source = (
            f"capability:{capability.capability_id or capability.digest}"
            f" technology_view={capability.technology_view}"
        )

    # -- resolution ------------------------------------------------------
    def _record(self, parameter: ResolvedParameter) -> ResolvedParameter:
        previous = self._used.get(parameter.name)
        if previous is not None and previous != parameter:
            raise MachineError(
                f"machine parameter {parameter.name!r} resolved twice to "
                f"different values ({previous.value!r} then {parameter.value!r})"
            )
        self._used[parameter.name] = parameter
        return parameter

    def value(self, name: str) -> Any:
        """Read one cost-table parameter and record the dependency."""
        return self._record(self.cost_table.resolve(name)).value

    def integer(self, name: str, *, minimum: int = 0) -> int:
        entry = self.cost_table.entry(name)
        if entry.get("convert") == "ns_to_cycles":
            return self._ns_to_cycles(name, minimum=minimum)
        raw = self.value(name)
        try:
            number = int(raw)
        except (TypeError, ValueError):
            raise MachineError(f"parameter {name!r} is not an integer: {raw!r}") from None
        if number < minimum:
            raise MachineError(
                f"parameter {name!r} is {number}, below the legal minimum {minimum}"
            )
        return number

    def _ns_to_cycles(self, name: str, *, minimum: int) -> int:
        """Convert a physically characterized nanosecond latency into cycles.

        A SPICE or STA result is a time, not a cycle count: turning it into
        cycles needs the clock, so the converted value can be no stronger than
        the weaker of the two inputs.  That composition is done here rather than
        by hand, so a characterized nanosecond figure divided by an assumed
        clock is reported as ``assumed`` and never as ``characterized``.
        """
        entry = self.cost_table.entry(name)
        if str(entry.get("unit", "")) != "ns":
            raise MachineError(
                f"parameter {name!r} requests ns_to_cycles but is not in ns"
            )
        source = self.cost_table.resolve(name)
        clock = self.cost_table.resolve("clock.frequency_hz")
        seconds = float(source.value) * 1e-9
        cycles = int(-(-(seconds * float(clock.value)) // 1))  # ceil
        cycles = max(cycles, minimum, 1)
        combined = worst((source.provenance, clock.provenance))
        self._record(
            ResolvedParameter(
                name=name,
                value=cycles,
                unit="cycles",
                provenance=combined,
                source=(
                    f"{source.source} @ clock.frequency_hz={clock.value} "
                    f"({clock.provenance.value}, {clock.source or 'no source'})"
                ),
                origin="cost_table",
                note=(
                    f"{source.value} ns converted to cycles; provenance is the "
                    f"weaker of the latency ({source.provenance.value}) and the "
                    f"clock ({clock.provenance.value})."
                    + (f"  {source.note}" if source.note else "")
                ),
            )
        )
        return cycles

    def number(self, name: str, *, minimum: float = 0.0) -> float:
        entry = self.cost_table.entry(name)
        if entry.get("convert") == "bytes_per_second_to_bytes_per_cycle":
            return self._bandwidth_to_rate(name, minimum=minimum)
        if entry.get("convert") == "work_over_cycles":
            return self._measured_rate(name, minimum=minimum)
        raw = self.value(name)
        try:
            number = float(raw)
        except (TypeError, ValueError):
            raise MachineError(f"parameter {name!r} is not a number: {raw!r}") from None
        if number < minimum:
            raise MachineError(
                f"parameter {name!r} is {number}, below the legal minimum {minimum}"
            )
        return number

    def _bandwidth_to_rate(self, name: str, *, minimum: float) -> float:
        """Convert a sourced bytes-per-second bandwidth into bytes per cycle.

        A vendor bandwidth is a physical fact about a component; bytes per cycle
        is that fact divided by *our* clock.  Composing them here means a
        datasheet bandwidth over an assumed clock is reported as ``assumed``.
        """
        entry = self.cost_table.entry(name)
        if str(entry.get("unit", "")) != "B/s":
            raise MachineError(
                f"parameter {name!r} requests a bandwidth conversion but is not "
                "expressed in B/s"
            )
        source = self.cost_table.resolve(name)
        clock = self.cost_table.resolve("clock.frequency_hz")
        divisor = float(entry.get("lanes", 1))
        if divisor <= 0:
            raise MachineError(f"parameter {name!r} declares a non-positive lane count")
        rate = float(source.value) / float(clock.value) / divisor
        if rate < minimum:
            raise MachineError(
                f"parameter {name!r} converts to {rate} B/cycle, below {minimum}"
            )
        self._record(
            ResolvedParameter(
                name=name,
                value=rate,
                unit="B/cycle",
                provenance=worst((source.provenance, clock.provenance)),
                source=(
                    f"{source.source} @ clock.frequency_hz={clock.value} "
                    f"({clock.provenance.value}, {clock.source or 'no source'})"
                ),
                origin="cost_table",
                note=(
                    f"{source.value} B/s over {divisor:g} lane(s) at the table's "
                    "clock; provenance is the weaker of the bandwidth "
                    f"({source.provenance.value}) and the clock "
                    f"({clock.provenance.value})."
                    + (f"  {source.note}" if source.note else "")
                ),
            )
        )
        return rate

    def _measured_rate(self, name: str, *, minimum: float) -> float:
        """Divide a measured work count by a measured cycle count, here.

        A per-lane rate taken from an executed RTL campaign is *two* numbers
        from that campaign -- how much work the operation declared and how many
        cycles the engine took to retire it.  Pre-dividing them by hand puts a
        quotient in the table whose derivation lives only in a note, which is
        exactly the shape ``docs/METHODOLOGY.md`` section 0 forbids: "where a
        figure is the author's arithmetic on two cited cells, the document says
        so and shows the division".  So the table carries ``work_units`` and
        ``cycles`` and the division happens here, where the recorded parameter
        can state both operands.

        Unlike :meth:`_ns_to_cycles` and :meth:`_bandwidth_to_rate` this
        conversion does *not* touch the clock: a work-per-cycle rate is a
        property of the RTL's own cycle behaviour and is the same number at any
        frequency.  Its provenance is therefore the campaign's alone.
        """
        entry = self.cost_table.entry(name)
        if str(entry.get("unit", "")) != "work/lane/cycle":
            raise MachineError(
                f"parameter {name!r} requests work_over_cycles but is not "
                "expressed in work/lane/cycle"
            )
        try:
            work = float(entry["work_units"])
            cycles = float(entry["cycles"])
        except (KeyError, TypeError, ValueError):
            raise MachineError(
                f"parameter {name!r} converts work over cycles but does not "
                "carry both a 'work_units' and a 'cycles' operand"
            ) from None
        if work <= 0 or cycles <= 0:
            raise MachineError(
                f"parameter {name!r} declares a non-positive work "
                f"({work}) or cycle ({cycles}) count"
            )
        source = self.cost_table.resolve(name)
        rate = work / cycles
        if rate < minimum:
            raise MachineError(
                f"parameter {name!r} converts to {rate} work/lane/cycle, "
                f"below {minimum}"
            )
        # A table that also states the quotient must state it correctly.  The
        # stated value is the one a reader sees; a disagreement between it and
        # the division is a defect that leaves no trace anywhere else.
        stated = entry.get("value")
        if stated is not None:
            if abs(float(stated) - rate) > 1e-9 * max(1.0, abs(rate)):
                raise MachineError(
                    f"parameter {name!r} states {stated} but "
                    f"{work:g} work over {cycles:g} cycles is {rate!r}"
                )
        self._record(
            ResolvedParameter(
                name=name,
                value=rate,
                unit="work/lane/cycle",
                provenance=source.provenance,
                source=source.source,
                origin="cost_table",
                note=(
                    f"{work:.0f} work units retired in {cycles:.0f} measured "
                    f"cycles by one engine instance."
                    + (f"  {source.note}" if source.note else "")
                ),
            )
        )
        return rate

    def text(self, name: str) -> str:
        return str(self.value(name))

    def capability_value(
        self, name: str, value: int, *, unit: str, note: str = ""
    ) -> int:
        """Record a structural count that came from the capability record."""
        self._record(
            ResolvedParameter(
                name=name,
                value=int(value),
                unit=unit,
                provenance=self._capability_provenance,
                source=self._capability_source,
                origin="capability",
                note=note,
            )
        )
        return int(value)

    def structural(
        self, name: str, capability_path: tuple[str, ...], fallback: str
    ) -> int:
        """A structural count: capability first, cost table when unadvertised.

        ADR-003 section 14 requires the capability to report exact limits.  When
        it does, the capability wins and the value is labelled with the
        capability's technology view.  When it does not, the cost table must
        supply the value and the value is labelled with the cost table's own
        provenance -- never silently invented.
        """
        node: Any = {
            "engines": self.capability.engines,
            "memory": self.capability.memory,
            "limits": self.capability.limits,
            "link": self.capability.link,
        }
        for key in capability_path:
            if not isinstance(node, Mapping) or key not in node:
                node = None
                break
            node = node[key]
        if isinstance(node, (int, float)) and not isinstance(node, bool):
            return self.capability_value(
                name,
                int(node),
                unit="count",
                note=f"capability.{'.'.join(capability_path)}",
            )
        # Unadvertised: the cost table must say, and the value is reported under
        # the structural name so that a rate can cite it by the name it used.
        resolved = self.cost_table.resolve(fallback)
        value = int(resolved.value)
        if value < 1:
            raise MachineError(f"structural parameter {fallback!r} must be positive")
        self._record(
            ResolvedParameter(
                name=name,
                value=value,
                unit=resolved.unit or "count",
                provenance=resolved.provenance,
                source=resolved.source,
                origin="cost_table",
                note=(
                    f"the capability does not advertise "
                    f"{'.'.join(capability_path)}; taken from cost table "
                    f"parameter {fallback!r}."
                    + (f"  {resolved.note}" if resolved.note else "")
                ),
            )
        )
        return value

    # -- reporting -------------------------------------------------------
    def used(self) -> dict[str, ResolvedParameter]:
        return dict(sorted(self._used.items()))

    def provenance_class(self) -> Provenance:
        return worst(p.provenance for p in self._used.values()) if self._used else (
            Provenance.CHARACTERIZED
        )

    def provenance_report(self) -> dict[str, Any]:
        buckets: dict[str, list[str]] = {p.value: [] for p in Provenance}
        for name, parameter in sorted(self._used.items()):
            buckets[parameter.provenance.value].append(name)
        overall = self.provenance_class()
        return {
            "class": overall.value,
            "depends_on_assumed_values": overall is Provenance.ASSUMED,
            "counts": {k: len(v) for k, v in sorted(buckets.items())},
            "by_class": {k: v for k, v in sorted(buckets.items())},
            "parameters": {
                name: parameter.to_dict()
                for name, parameter in sorted(self._used.items())
            },
        }

    def rate_provenance(self, names: Iterable[str]) -> dict[str, Any]:
        """Provenance of one reported rate: every input it depended on."""
        wanted = sorted(set(names))
        missing = [n for n in wanted if n not in self._used]
        if missing:
            raise MachineError(
                f"a rate claims to depend on unread parameters {missing}"
            )
        classes = [self._used[n].provenance for n in wanted]
        overall = worst(classes) if classes else Provenance.ASSUMED
        return {
            "class": overall.value,
            "depends_on_assumed_values": overall is Provenance.ASSUMED,
            "inputs": {n: self._used[n].provenance.value for n in wanted},
        }

    # -- clock -----------------------------------------------------------
    @property
    def clock_hz(self) -> float:
        return self.number("clock.frequency_hz", minimum=1.0)

    def cycles_to_seconds(self, cycles: int) -> float:
        return float(cycles) / self.clock_hz

    # -- sequencer -------------------------------------------------------
    def sequencer(self) -> "SequencerParams":
        return SequencerParams(
            fetch_cycles=self.integer("sequencer.fetch_cycles", minimum=1),
            decode_cycles=self.integer("sequencer.decode_cycles", minimum=0),
            issue_cycles=self.integer("sequencer.issue_cycles", minimum=1),
            predicate_cycles=self.integer("sequencer.predicate_cycles", minimum=0),
            branch_cycles=self.integer("sequencer.branch_cycles", minimum=0),
            loop_cycles=self.integer("sequencer.loop_cycles", minimum=0),
            wait_check_cycles=self.integer("sequencer.wait_check_cycles", minimum=0),
            queue_transit_cycles=self.integer("queue.transit_cycles", minimum=0),
        )

    # -- engines ---------------------------------------------------------
    def engine(self, family: str) -> "EngineParams":
        if family not in FAMILY_BY_NAME:
            raise MachineError(f"unknown engine family {family!r}")
        lanes = self.structural(
            f"engine.{family}.lanes",
            ("engines", family, "lanes"),
            f"engine.{family}.lanes.default",
        )
        queues = self.structural(
            f"engine.{family}.queues",
            ("engines", family, "queues"),
            f"engine.{family}.queues.default",
        )
        depth = self.structural(
            f"engine.{family}.queue_depth",
            ("engines", family, "queue_depth"),
            f"engine.{family}.queue_depth.default",
        )
        outstanding_cap = self.capability_value(
            "limits.max_outstanding_per_queue",
            int(self.capability.limits["max_outstanding_per_queue"]),
            unit="descriptors",
            note="capability.limits.max_outstanding_per_queue",
        )
        return EngineParams(
            family=family,
            lanes=lanes,
            queues=queues,
            queue_depth=depth,
            max_outstanding=min(depth, outstanding_cap),
            work_per_lane_cycle=self.number(
                f"engine.{family}.work_per_lane_cycle", minimum=1e-9
            ),
            fixed_latency_cycles=self.integer(
                f"engine.{family}.fixed_latency_cycles", minimum=0
            ),
            bytes_per_cycle=self.number(f"engine.{family}.bytes_per_cycle", minimum=1e-9),
            minimum_cycles=self.integer(f"engine.{family}.minimum_cycles", minimum=1),
            tile_issue_cycles=self.integer(
                f"engine.{family}.tile_issue_cycles", minimum=1
            ),
            tile_pipeline_depth=self.integer(
                f"engine.{family}.tile_pipeline_depth.default", minimum=1
            ),
        )

    # -- memory ----------------------------------------------------------
    def memory(self) -> "MemoryParams":
        state_backing = self.text("state.backing_storage_class")
        if state_backing not in {"SRAM", "HBM"}:
            raise MachineError(
                f"state.backing_storage_class must be SRAM or HBM, got {state_backing!r}"
            )
        return MemoryParams(
            hbm=MemoryClassParams(
                name="hbm",
                units=self.structural(
                    "hbm.channels", ("memory", "hbm", "channels"), "hbm.channels.default"
                ),
                bytes_per_cycle_per_unit=self.number(
                    "hbm.bytes_per_cycle_per_channel", minimum=1e-9
                ),
                read_latency_cycles=self.integer("hbm.read_latency_cycles", minimum=1),
                write_latency_cycles=self.integer("hbm.write_latency_cycles", minimum=1),
                transaction_bytes=self.integer("hbm.transaction_bytes", minimum=1),
                interleave_bytes=self.integer("hbm.interleave_bytes", minimum=1),
                ports_per_unit=1,
            ),
            sram=MemoryClassParams(
                name="sram",
                units=self.structural(
                    "sram.banks", ("memory", "sram", "banks"), "sram.banks.default"
                ),
                bytes_per_cycle_per_unit=self.number(
                    "sram.bytes_per_cycle_per_port", minimum=1e-9
                ),
                read_latency_cycles=self.integer("sram.read_latency_cycles", minimum=1),
                write_latency_cycles=self.integer("sram.write_latency_cycles", minimum=1),
                transaction_bytes=self.integer("sram.transaction_bytes", minimum=1),
                interleave_bytes=self.integer("sram.interleave_bytes", minimum=1),
                ports_per_unit=self.structural(
                    "sram.ports_per_bank",
                    ("memory", "sram", "ports"),
                    "sram.ports_per_bank.default",
                ),
            ),
            rom=MemoryClassParams(
                name="rom",
                units=self.structural(
                    "rom.arrays", ("memory", "rom", "arrays"), "rom.arrays.default"
                ),
                bytes_per_cycle_per_unit=self.number(
                    "rom.bytes_per_cycle_per_array", minimum=1e-9
                ),
                read_latency_cycles=self.integer("rom.read_latency_cycles", minimum=1),
                write_latency_cycles=1 << 30,  # ROM is immutable; a write is a trap
                transaction_bytes=self.integer("rom.transaction_bytes", minimum=1),
                interleave_bytes=self.integer("rom.interleave_bytes", minimum=1),
                ports_per_unit=1,
            ),
            host=MemoryClassParams(
                name="host",
                units=1,
                bytes_per_cycle_per_unit=self.number("host.bytes_per_cycle", minimum=1e-9),
                read_latency_cycles=self.integer("host.latency_cycles", minimum=1),
                write_latency_cycles=self.integer("host.latency_cycles", minimum=1),
                transaction_bytes=self.integer("host.transaction_bytes", minimum=1),
                interleave_bytes=self.integer("host.transaction_bytes", minimum=1),
                ports_per_unit=1,
            ),
            state_backing=StorageClass[state_backing],
            max_modeled_transactions_per_access=self.integer(
                "model.max_modeled_transactions_per_access", minimum=1
            ),
        )

    # -- fabric ----------------------------------------------------------
    def cluster_fabric(self) -> "ClusterFabricParams":
        return ClusterFabricParams(
            nodes=self.capability_value(
                "limits.max_nodes",
                int(self.capability.limits["max_nodes"]),
                unit="nodes",
                note="capability.limits.max_nodes",
            ),
            links_per_node=self.structural(
                "fabric.cluster.links_per_node",
                ("link", "links_per_node"),
                "fabric.cluster.links_per_node.default",
            ),
            link_bytes_per_cycle=self.number(
                "fabric.cluster.link_bytes_per_cycle", minimum=1e-9
            ),
            link_hop_latency_cycles=self.integer(
                "fabric.cluster.link_hop_latency_cycles", minimum=1
            ),
            switch_latency_cycles=self.integer(
                "fabric.cluster.switch_latency_cycles", minimum=1
            ),
            switch_levels=self.integer("fabric.cluster.switch_levels", minimum=1),
            switch_radix=self.integer("fabric.cluster.switch_radix", minimum=2),
            packet_bytes=self.integer("fabric.cluster.packet_bytes", minimum=1),
            packet_header_bytes=self.integer(
                "fabric.cluster.packet_header_bytes", minimum=0
            ),
            credits=self.integer("fabric.cluster.credits", minimum=1),
            credit_return_cycles=self.integer(
                "fabric.cluster.credit_return_cycles", minimum=1
            ),
            retry_interval_packets=self.integer(
                "fabric.cluster.retry_interval_packets", minimum=1
            ),
            retry_cycles=self.integer("fabric.cluster.retry_cycles", minimum=1),
            barrier_round_cycles=self.integer(
                "fabric.cluster.barrier_round_cycles", minimum=1
            ),
            endpoint_latency_cycles=self.integer(
                "fabric.cluster.endpoint_latency_cycles", minimum=1
            ),
        )

    def wafer_fabric(self) -> "WaferFabricParams":
        return WaferFabricParams(
            reticle_rows=self.integer("fabric.wafer.reticle_rows", minimum=1),
            reticle_cols=self.integer("fabric.wafer.reticle_cols", minimum=1),
            tile_rows=self.integer("fabric.wafer.tile_rows_per_reticle", minimum=1),
            tile_cols=self.integer("fabric.wafer.tile_cols_per_reticle", minimum=1),
            tile_link_bytes_per_cycle=self.number(
                "fabric.wafer.tile_link_bytes_per_cycle", minimum=1e-9
            ),
            tile_hop_cycles=self.integer("fabric.wafer.tile_hop_cycles", minimum=1),
            router_latency_cycles=self.integer(
                "fabric.wafer.router_latency_cycles", minimum=1
            ),
            stitch_bytes_per_cycle=self.number(
                "fabric.wafer.stitch_bytes_per_cycle", minimum=1e-9
            ),
            stitch_hop_cycles=self.integer("fabric.wafer.stitch_hop_cycles", minimum=1),
            packet_bytes=self.integer("fabric.wafer.packet_bytes", minimum=1),
            packet_header_bytes=self.integer(
                "fabric.wafer.packet_header_bytes", minimum=0
            ),
            credits=self.integer("fabric.wafer.credits", minimum=1),
            credit_return_cycles=self.integer(
                "fabric.wafer.credit_return_cycles", minimum=1
            ),
            virtual_channels=self.integer("fabric.wafer.virtual_channels", minimum=1),
            barrier_level_cycles=self.integer(
                "fabric.wafer.barrier_level_cycles", minimum=1
            ),
            endpoint_latency_cycles=self.integer(
                "fabric.wafer.endpoint_latency_cycles", minimum=1
            ),
        )

    def structural_report(self) -> dict[str, Any]:
        """Structural summary of the modelled machine (no timing)."""
        return {
            "capability_digest": self.capability.digest,
            "capability_technology_view": self.capability.technology_view,
            "topology_class": TopologyClass(self.capability.topology_class).name,
            "cost_table": self.cost_table.to_dict(),
            "clock_frequency_hz": self.clock_hz,
        }


# ---------------------------------------------------------------------------
# Parameter bundles
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class SequencerParams:
    """Hardware microsequencer issue parameters (ADR-003 section 5)."""

    fetch_cycles: int
    decode_cycles: int
    issue_cycles: int
    predicate_cycles: int
    branch_cycles: int
    loop_cycles: int
    wait_check_cycles: int
    queue_transit_cycles: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "fetch_cycles": self.fetch_cycles,
            "decode_cycles": self.decode_cycles,
            "issue_cycles": self.issue_cycles,
            "predicate_cycles": self.predicate_cycles,
            "branch_cycles": self.branch_cycles,
            "loop_cycles": self.loop_cycles,
            "wait_check_cycles": self.wait_check_cycles,
            "queue_transit_cycles": self.queue_transit_cycles,
        }


@dataclass(frozen=True, slots=True)
class EngineParams:
    """One engine family's structure and throughput."""

    family: str
    lanes: int
    queues: int
    queue_depth: int
    max_outstanding: int
    work_per_lane_cycle: float
    fixed_latency_cycles: int
    bytes_per_cycle: float
    minimum_cycles: int
    tile_issue_cycles: int = 1
    tile_pipeline_depth: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "lanes": self.lanes,
            "queues": self.queues,
            "queue_depth": self.queue_depth,
            "max_outstanding": self.max_outstanding,
            "work_per_lane_cycle": self.work_per_lane_cycle,
            "fixed_latency_cycles": self.fixed_latency_cycles,
            "bytes_per_cycle": self.bytes_per_cycle,
            "minimum_cycles": self.minimum_cycles,
            "tile_issue_cycles": self.tile_issue_cycles,
            "tile_pipeline_depth_default": self.tile_pipeline_depth,
        }


@dataclass(frozen=True, slots=True)
class MemoryClassParams:
    """One storage class: banks/channels/arrays, bandwidth and latency."""

    name: str
    units: int
    bytes_per_cycle_per_unit: float
    read_latency_cycles: int
    write_latency_cycles: int
    transaction_bytes: int
    interleave_bytes: int
    ports_per_unit: int

    @property
    def peak_bytes_per_cycle(self) -> float:
        return self.bytes_per_cycle_per_unit * self.units * self.ports_per_unit

    def to_dict(self) -> dict[str, Any]:
        return {
            "units": self.units,
            "ports_per_unit": self.ports_per_unit,
            "bytes_per_cycle_per_unit": self.bytes_per_cycle_per_unit,
            "peak_bytes_per_cycle": self.peak_bytes_per_cycle,
            "read_latency_cycles": self.read_latency_cycles,
            "write_latency_cycles": self.write_latency_cycles,
            "transaction_bytes": self.transaction_bytes,
            "interleave_bytes": self.interleave_bytes,
        }


@dataclass(frozen=True, slots=True)
class MemoryParams:
    """The whole memory hierarchy of one node."""

    hbm: MemoryClassParams
    sram: MemoryClassParams
    rom: MemoryClassParams
    host: MemoryClassParams
    state_backing: StorageClass
    max_modeled_transactions_per_access: int

    def klass(self, storage_class: StorageClass) -> MemoryClassParams:
        if storage_class is StorageClass.STATE:
            storage_class = self.state_backing
        return {
            StorageClass.HBM: self.hbm,
            StorageClass.SRAM: self.sram,
            StorageClass.ROM: self.rom,
            StorageClass.HOST: self.host,
        }[storage_class]

    def to_dict(self) -> dict[str, Any]:
        return {
            "hbm": self.hbm.to_dict(),
            "sram": self.sram.to_dict(),
            "rom": self.rom.to_dict(),
            "host": self.host.to_dict(),
            "state_backing_storage_class": self.state_backing.name,
            "max_modeled_transactions_per_access": (
                self.max_modeled_transactions_per_access
            ),
        }


@dataclass(frozen=True, slots=True)
class ClusterFabricParams:
    """32-node inter-node fabric: link, switch, credit and retry parameters."""

    nodes: int
    links_per_node: int
    link_bytes_per_cycle: float
    link_hop_latency_cycles: int
    switch_latency_cycles: int
    switch_levels: int
    switch_radix: int
    packet_bytes: int
    packet_header_bytes: int
    credits: int
    credit_return_cycles: int
    retry_interval_packets: int
    retry_cycles: int
    barrier_round_cycles: int
    endpoint_latency_cycles: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": self.nodes,
            "links_per_node": self.links_per_node,
            "link_bytes_per_cycle": self.link_bytes_per_cycle,
            "link_hop_latency_cycles": self.link_hop_latency_cycles,
            "switch_latency_cycles": self.switch_latency_cycles,
            "switch_levels": self.switch_levels,
            "switch_radix": self.switch_radix,
            "packet_bytes": self.packet_bytes,
            "packet_header_bytes": self.packet_header_bytes,
            "credits": self.credits,
            "credit_return_cycles": self.credit_return_cycles,
            "retry_interval_packets": self.retry_interval_packets,
            "retry_cycles": self.retry_cycles,
            "barrier_round_cycles": self.barrier_round_cycles,
            "endpoint_latency_cycles": self.endpoint_latency_cycles,
        }


@dataclass(frozen=True, slots=True)
class WaferFabricParams:
    """On-wafer fabric: reticle/tile mesh, stitch class, credits, barriers."""

    reticle_rows: int
    reticle_cols: int
    tile_rows: int
    tile_cols: int
    tile_link_bytes_per_cycle: float
    tile_hop_cycles: int
    router_latency_cycles: int
    stitch_bytes_per_cycle: float
    stitch_hop_cycles: int
    packet_bytes: int
    packet_header_bytes: int
    credits: int
    credit_return_cycles: int
    virtual_channels: int
    barrier_level_cycles: int
    endpoint_latency_cycles: int

    @property
    def tiles(self) -> int:
        return self.reticle_rows * self.reticle_cols * self.tile_rows * self.tile_cols

    def to_dict(self) -> dict[str, Any]:
        return {
            "reticle_rows": self.reticle_rows,
            "reticle_cols": self.reticle_cols,
            "tile_rows_per_reticle": self.tile_rows,
            "tile_cols_per_reticle": self.tile_cols,
            "tiles": self.tiles,
            "tile_link_bytes_per_cycle": self.tile_link_bytes_per_cycle,
            "tile_hop_cycles": self.tile_hop_cycles,
            "router_latency_cycles": self.router_latency_cycles,
            "stitch_bytes_per_cycle": self.stitch_bytes_per_cycle,
            "stitch_hop_cycles": self.stitch_hop_cycles,
            "packet_bytes": self.packet_bytes,
            "packet_header_bytes": self.packet_header_bytes,
            "credits": self.credits,
            "credit_return_cycles": self.credit_return_cycles,
            "virtual_channels": self.virtual_channels,
            "barrier_level_cycles": self.barrier_level_cycles,
            "endpoint_latency_cycles": self.endpoint_latency_cycles,
        }
