"""Deterministic exact-fit allocation for backend activation lifetimes.

The neutral graph gives every intermediate a logical identity.  A physical
backend does not need one allocation per identity when two values have
disjoint lifetimes, but that decision must be shared and inspectable: ROM and
HBM are storage choices, not two different definitions of liveness.

This module deliberately does only the backend-neutral part.  Callers derive
the program-order intervals and decide which buffers must remain exclusive;
the allocator then performs one deterministic, exact-size, exact-dtype greedy
packing.  It never changes an extent, truncates a context, or guesses that two
overlapping values may alias.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class ActivationLivenessError(ValueError):
    """Raised when a liveness request is incomplete or contradictory."""


@dataclass(frozen=True, slots=True)
class LiveBuffer:
    """One logical mutable buffer and its closed program-order lifetime."""

    key: str
    size_bytes: int
    dtype: str
    first_use: int
    last_use: int
    exclusive: bool = False

    def validate(self) -> None:
        if not self.key:
            raise ActivationLivenessError("a live buffer has an empty key")
        if self.size_bytes <= 0:
            raise ActivationLivenessError(
                f"live buffer {self.key!r} has non-positive size {self.size_bytes}"
            )
        if not self.dtype:
            raise ActivationLivenessError(
                f"live buffer {self.key!r} has no element type"
            )
        if self.first_use < 0 or self.last_use < self.first_use:
            raise ActivationLivenessError(
                f"live buffer {self.key!r} has invalid closed interval "
                f"[{self.first_use}, {self.last_use}]"
            )


@dataclass(frozen=True, slots=True)
class ArenaTenant:
    """The interval during which one logical buffer owns an arena slot."""

    key: str
    first_use: int
    last_use: int


@dataclass(frozen=True, slots=True)
class LiveArena:
    """One physical allocation shared by non-overlapping logical tenants."""

    slot_id: str
    size_bytes: int
    dtype: str
    tenants: tuple[ArenaTenant, ...]
    exclusive: bool = False


def allocate_live_buffers(
    buffers: Iterable[LiveBuffer], *, slot_prefix: str = "arena"
) -> tuple[tuple[LiveArena, ...], dict[str, str]]:
    """Pack closed lifetimes into deterministic exact-fit arena slots.

    Reuse is legal only when the prior tenant's closed interval ends strictly
    before the next tenant starts.  Exact size and dtype matching keeps the
    physical contract stable across backends and avoids silently widening a
    view merely because a larger hole happened to be available.  An exclusive
    request neither enters an existing slot nor admits a later tenant.
    """

    requests = tuple(buffers)
    seen: set[str] = set()
    for request in requests:
        request.validate()
        if request.key in seen:
            raise ActivationLivenessError(
                f"live buffer key {request.key!r} is declared more than once"
            )
        seen.add(request.key)

    slots: list[dict[str, object]] = []
    allocation: dict[str, str] = {}
    for request in sorted(requests, key=lambda item: (item.first_use, item.key)):
        chosen: dict[str, object] | None = None
        if not request.exclusive:
            for slot in slots:
                if bool(slot["exclusive"]):
                    continue
                if int(slot["size_bytes"]) != request.size_bytes:
                    continue
                if str(slot["dtype"]) != request.dtype:
                    continue
                if int(slot["free_at"]) <= request.first_use:
                    chosen = slot
                    break
        if chosen is None:
            chosen = {
                "slot_id": f"{slot_prefix}{len(slots):04d}",
                "size_bytes": request.size_bytes,
                "dtype": request.dtype,
                "free_at": 0,
                "exclusive": request.exclusive,
                "tenants": [],
            }
            slots.append(chosen)
        tenants = chosen["tenants"]
        assert isinstance(tenants, list)
        tenants.append(
            ArenaTenant(request.key, request.first_use, request.last_use)
        )
        chosen["free_at"] = request.last_use + 1
        allocation[request.key] = str(chosen["slot_id"])

    arenas = tuple(
        LiveArena(
            slot_id=str(slot["slot_id"]),
            size_bytes=int(slot["size_bytes"]),
            dtype=str(slot["dtype"]),
            tenants=tuple(slot["tenants"]),  # type: ignore[arg-type]
            exclusive=bool(slot["exclusive"]),
        )
        for slot in slots
    )
    return arenas, allocation


__all__ = [
    "ActivationLivenessError",
    "ArenaTenant",
    "LiveArena",
    "LiveBuffer",
    "allocate_live_buffers",
]
