"""Central, opt-in cache for immutable decoded weight slices.

The cache changes host materialization cost only.  A hit does not change the
simulated memory reads, scale multiplications, contraction call, association,
or output rounding.  Its default budget is zero, so existing executions retain
the uncached path unless a governed runner explicitly opts in.

Admission is scan-resistant.  One active routed weight scope (resolved layer
and matrix family) owns protected per-node quotas; entries are never cyclically
evicted inside that scope.  When the program moves to another scope, the old
scope is released as a unit.  Thus a budget smaller than the working set keeps
a deterministic prefix on every node instead of evicting each expert just
before the next block reuses it.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from runtime.sim.performance import HostPerformanceObservations


@dataclass(frozen=True, slots=True)
class CacheProbe:
    """Result of one lookup and whether a miss may be admitted."""

    value: np.ndarray | None
    admissible: bool
    admission_epoch: int


@dataclass(frozen=True, slots=True)
class _Entry:
    value: np.ndarray
    node_id: int
    nbytes: int


def backend_identity_digest(identity: Mapping[str, Any]) -> str:
    """Canonical identity of the fields that fix backend arithmetic.

    ``device_memory_bytes`` is an observation of currently free capacity, not
    part of the blocked matmul association.  It is excluded here for the same
    reason :meth:`Backend.executed_association_manifest` excludes it: changing
    free memory must neither change a cache key nor flush valid entries.
    """

    stable = dict(identity)
    stable.pop("device_memory_bytes", None)
    encoded = json.dumps(
        stable,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


class DecodedWeightCache:
    """One exact byte budget shared by all nodes of one activated Device."""

    __slots__ = (
        "budget_bytes",
        "entry_budget_bytes",
        "node_count",
        "per_node_budget_bytes",
        "working_reserve_bytes",
        "_active_backend",
        "_active_scope",
        "_entries",
        "_epoch",
        "_live_by_node",
        "_lock",
        "_observations",
    )

    def __init__(
        self,
        *,
        budget_bytes: int,
        working_reserve_bytes: int,
        node_count: int,
        observations: HostPerformanceObservations,
    ) -> None:
        budget = int(budget_bytes)
        reserve = int(working_reserve_bytes)
        nodes = int(node_count)
        if budget < 0 or reserve < 0:
            raise ValueError("decoded-weight cache budget and reserve are non-negative")
        if nodes <= 0:
            raise ValueError("decoded-weight cache needs at least one logical node")
        self.budget_bytes = budget
        self.working_reserve_bytes = min(reserve, budget)
        self.entry_budget_bytes = budget - self.working_reserve_bytes
        self.node_count = nodes
        self.per_node_budget_bytes = self.entry_budget_bytes // nodes
        self._observations = observations
        self._lock = threading.Lock()
        self._entries: dict[tuple[Any, ...], _Entry] = {}
        self._epoch = 0
        self._live_by_node = [0] * nodes
        self._active_scope: tuple[Any, ...] | None = None
        self._active_backend: str | None = None
        observations.set_value("decoded_weight_cache_budget_bytes", budget)

    def configuration(self) -> dict[str, Any]:
        return {
            "enabled": self.entry_budget_bytes > 0,
            "policy": "one_active_scope_protected_per_node_v1",
            "budget_bytes": self.budget_bytes,
            "working_reserve_bytes": self.working_reserve_bytes,
            "entry_budget_bytes": self.entry_budget_bytes,
            "node_count": self.node_count,
            "per_node_budget_bytes": self.per_node_budget_bytes,
        }

    def bypass(
        self,
        *,
        scope: tuple[Any, ...] | None = None,
        backend_identity: Mapping[str, Any] | None = None,
    ) -> None:
        """Record an ineligible request and honor any scope transition.

        Mutable or unauthenticated weights are never looked up, but seeing one
        still means execution left the previous resolved matrix scope.  Clear
        that scope so returning to it cannot retain entries longer than the
        declared one-active-scope policy allows.
        """

        with self._lock:
            if backend_identity is not None:
                backend = backend_identity_digest(backend_identity)
                if self._active_backend is not None and self._active_backend != backend:
                    self._clear_locked()
                    self._active_scope = None
                self._active_backend = backend
            if scope is not None:
                if self._active_scope is not None and self._active_scope != scope:
                    self._clear_locked()
                self._active_scope = scope
        self._observations.add("decoded_weight_cache_bypasses")

    def probe(
        self,
        *,
        scope: tuple[Any, ...],
        key: tuple[Any, ...],
        node_id: int,
        backend_identity: Mapping[str, Any],
    ) -> CacheProbe:
        """Look up one key after enforcing scope/backend epoch boundaries."""

        node = int(node_id)
        if not 0 <= node < self.node_count:
            raise ValueError(
                f"cache node {node} is outside the {self.node_count}-node device"
            )
        if self.entry_budget_bytes == 0:
            self._observations.add("decoded_weight_cache_bypasses")
            return CacheProbe(None, False, self._epoch)
        backend = backend_identity_digest(backend_identity)
        with self._lock:
            if self._active_backend is not None and self._active_backend != backend:
                self._clear_locked()
                self._active_scope = None
            self._active_backend = backend
            if self._active_scope is not None and self._active_scope != scope:
                self._clear_locked()
            self._active_scope = scope
            entry = self._entries.get(key)
            if entry is not None:
                self._observations.add("decoded_weight_cache_hits")
                return CacheProbe(entry.value, False, self._epoch)
            self._observations.add("decoded_weight_cache_misses")
            return CacheProbe(None, True, self._epoch)

    def admit(
        self,
        *,
        key: tuple[Any, ...],
        node_id: int,
        value: np.ndarray,
        admission_epoch: int,
    ) -> np.ndarray:
        """Protect one validated value, or return it uncached on a full quota."""

        node = int(node_id)
        if not 0 <= node < self.node_count:
            raise ValueError(
                f"cache node {node} is outside the {self.node_count}-node device"
            )
        try:
            array = np.ascontiguousarray(value, dtype=np.float32)
            nbytes = int(array.nbytes)
        except MemoryError:
            self._observations.add("decoded_weight_cache_allocation_failures")
            self._observations.add("decoded_weight_cache_bypasses")
            return value
        with self._lock:
            if int(admission_epoch) != self._epoch:
                # Another issue crossed a scope/backend boundary after this
                # caller's probe.  The decoded value remains usable for its
                # current contraction, but must not enter the new scope.
                self._observations.add("decoded_weight_cache_bypasses")
                return array
            existing = self._entries.get(key)
            if existing is not None:
                # A future concurrent issue may race between probe and admit.
                # Both decoded values are immutable and bit-identical; retain
                # the first central owner and discard the duplicate reference.
                return existing.value
            if (
                nbytes > self.per_node_budget_bytes
                or self._live_by_node[node] + nbytes > self.per_node_budget_bytes
            ):
                self._observations.add("decoded_weight_cache_bypasses")
                return array
            try:
                array.setflags(write=False)
                self._entries[key] = _Entry(array, node, nbytes)
            except MemoryError:
                self._observations.add(
                    "decoded_weight_cache_allocation_failures"
                )
                self._observations.add("decoded_weight_cache_bypasses")
                return array
            self._live_by_node[node] += nbytes
            live = sum(self._live_by_node)
            self._observations.add("decoded_weight_cache_admissions")
            self._observations.set_value("decoded_weight_cache_live_bytes", live)
            self._observations.maximum(
                "decoded_weight_cache_high_water_bytes", live
            )
            return array

    def clear(self) -> None:
        """Drop all values at an explicit device/backend epoch boundary."""

        with self._lock:
            self._clear_locked()
            self._active_scope = None
            self._active_backend = None

    def _clear_locked(self) -> None:
        self._epoch += 1
        count = len(self._entries)
        self._entries.clear()
        self._live_by_node[:] = [0] * self.node_count
        if count:
            self._observations.add("decoded_weight_cache_evictions", count)
        self._observations.set_value("decoded_weight_cache_live_bytes", 0)
