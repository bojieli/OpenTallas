"""Conservative reference contract for the asynchronous RTL dependence table.

Reservation is atomic with respect to younger issue. Every candidate range is
checked before insertion; overflow creates a sticky wildcard until completion.
This module is a reference for integration, not a replacement execution backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .constants import NO_ID
from .descriptors import ExtendedDescriptorType


@dataclass(frozen=True)
class AccessRange:
    object_id: int
    lo: int
    hi: int
    write: bool

    def __post_init__(self) -> None:
        if not 0 <= self.object_id < 65536:
            raise ValueError("object ID does not fit the 16-bit dependence interface")
        if not 0 <= self.lo <= self.hi < 1 << 40:
            raise ValueError("range must fit the 40-bit half-open address interface")

    def conflicts(self, other: AccessRange) -> bool:
        return (self.lo < self.hi and other.lo < other.hi and
                self.object_id == other.object_id and self.lo < other.hi and
                other.lo < self.hi and (self.write or other.write))


@dataclass(frozen=True)
class Footprint:
    ranges: tuple[AccessRange, ...]
    wildcard: bool = False

    def conflicts(self, candidate: Iterable[AccessRange]) -> bool:
        queries = tuple(r for r in candidate if r.lo < r.hi)
        return bool(queries) and (self.wildcard or any(a.conflicts(b) for a in self.ranges for b in queries))


def compress_ranges(ranges: Iterable[AccessRange], capacity: int = 4) -> Footprint:
    if capacity <= 0:
        raise ValueError("range capacity must be positive")
    merged: dict[int, AccessRange] = {}
    wildcard = False
    for r in ranges:
        if r.lo == r.hi:
            continue
        old = merged.get(r.object_id)
        if old is not None:
            merged[r.object_id] = AccessRange(r.object_id, min(old.lo, r.lo), max(old.hi, r.hi), old.write or r.write)
        elif len(merged) < capacity:
            merged[r.object_id] = r
        else:
            wildcard = True
    return Footprint(tuple(merged.values()), wildcard)


class DependenceTable:
    def __init__(self, entries: int = 32, ranges_per_entry: int = 4):
        if not 1 <= entries <= 32 or not 1 <= ranges_per_entry <= 4:
            raise ValueError("table exceeds the frozen RTL interface")
        self.entries = entries
        self.ranges_per_entry = ranges_per_entry
        self.live: dict[int, Footprint] = {}

    def reserve(self, slot: int, accesses: Iterable[AccessRange]) -> bool:
        if not 0 <= slot < self.entries or slot in self.live:
            raise ValueError("reservation requires a valid unused slot")
        # Check ALL candidate ranges, including ones that will overflow storage.
        accesses = tuple(accesses)
        if any(entry.conflicts(accesses) for entry in self.live.values()):
            return False
        self.live[slot] = compress_ranges(accesses, self.ranges_per_entry)
        return True

    def complete(self, slot: int) -> None:
        if slot not in self.live:
            raise ValueError("completion requires a live slot")
        del self.live[slot]


def operator_whole_object_accesses(deployment, operator) -> tuple[AccessRange, ...]:
    """Collect six operand views AND separate scale objects without data reads.

    Whole-object bounds deliberately overestimate dynamic/strided views. LINK,
    STATE, predicate reads and host accesses require their own collectors at
    integration; passing one here is an error, never an empty footprint.
    """
    kind = ExtendedDescriptorType
    if operator.descriptor_type != kind.OPERATOR:
        raise ValueError("only OPERATOR descriptors are accepted by this collector")
    accesses = []
    for role in [*(f"input_view_{i}" for i in range(4)), *(f"output_view_{i}" for i in range(2))]:
        view_id = int(operator.payload[role])
        if view_id == NO_ID:
            continue
        view = deployment.table.get(view_id, kind.TENSOR_VIEW)
        obj = deployment.table.get(view.primary_object_id, kind.MEMORY_OBJECT)
        accesses.append(AccessRange(obj.descriptor_id, 0, int(obj.payload["size_bytes"]), role.startswith("output")))
        scale_id = int(view.payload["scale_object_id"])
        if scale_id != NO_ID:
            scale = deployment.table.get(scale_id, kind.MEMORY_OBJECT)
            # An output's scale plane may itself be produced. Conservatively
            # reserve it as writable without relying on engine-specific rules.
            accesses.append(AccessRange(scale.descriptor_id, 0, int(scale.payload["size_bytes"]), role.startswith("output")))
    return tuple(accesses)
