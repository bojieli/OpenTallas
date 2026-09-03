"""Decoded-weight cache policy and byte-ceiling conformance."""

from __future__ import annotations

import numpy as np

from runtime.sim.performance import HostPerformanceObservations
from runtime.sim.weight_cache import DecodedWeightCache, backend_identity_digest


IDENTITY = {
    "backend": "numpy",
    "library": "numpy",
    "library_version": "test",
    "device": "host",
    "flags": {"allow_tf32": False, "threads": 1},
}


def _cache(
    *, budget: int, reserve: int = 0, nodes: int = 1
) -> tuple[DecodedWeightCache, HostPerformanceObservations]:
    observations = HostPerformanceObservations()
    return (
        DecodedWeightCache(
            budget_bytes=budget,
            working_reserve_bytes=reserve,
            node_count=nodes,
            observations=observations,
        ),
        observations,
    )


def _admit(
    cache: DecodedWeightCache,
    *,
    scope: tuple[object, ...],
    key: tuple[object, ...],
    node: int,
    value: np.ndarray,
    identity=IDENTITY,
) -> np.ndarray:
    probe = cache.probe(
        scope=scope,
        key=key,
        node_id=node,
        backend_identity=identity,
    )
    assert probe.value is None and probe.admissible
    return cache.admit(
        key=key,
        node_id=node,
        value=value,
        admission_epoch=probe.admission_epoch,
    )


def test_zero_budget_is_an_explicit_bypass() -> None:
    cache, observations = _cache(budget=0, reserve=64)
    probe = cache.probe(
        scope=("layer",),
        key=("expert",),
        node_id=0,
        backend_identity=IDENTITY,
    )
    assert probe.value is None
    assert probe.admissible is False
    assert cache.configuration() == {
        "enabled": False,
        "policy": "one_active_scope_protected_per_node_v1",
        "budget_bytes": 0,
        "working_reserve_bytes": 0,
        "entry_budget_bytes": 0,
        "node_count": 1,
        "per_node_budget_bytes": 0,
    }
    totals = observations.snapshot()["totals"]
    assert totals["decoded_weight_cache_bypasses"] == 1
    assert totals["decoded_weight_cache_misses"] == 0
    assert totals["decoded_weight_cache_live_bytes"] == 0


def test_reserve_and_equal_node_quotas_bound_the_central_owner() -> None:
    cache, observations = _cache(budget=100, reserve=20, nodes=2)
    assert cache.configuration()["entry_budget_bytes"] == 80
    assert cache.configuration()["per_node_budget_bytes"] == 40

    first = _admit(
        cache,
        scope=("matrix",),
        key=(0, "expert"),
        node=0,
        value=np.arange(10, dtype=np.float32),
    )
    second = _admit(
        cache,
        scope=("matrix",),
        key=(1, "expert"),
        node=1,
        value=np.arange(10, dtype=np.float32),
    )
    assert first.flags.writeable is False
    assert second.flags.writeable is False

    # Each node owns exactly half of the entry budget.  A third value cannot
    # consume another node's protected quota or exceed the central ceiling.
    rejected = _admit(
        cache,
        scope=("matrix",),
        key=(0, "second"),
        node=0,
        value=np.arange(1, dtype=np.float32),
    )
    assert rejected.flags.writeable
    totals = observations.snapshot()["totals"]
    assert totals["decoded_weight_cache_admissions"] == 2
    assert totals["decoded_weight_cache_bypasses"] == 1
    assert totals["decoded_weight_cache_live_bytes"] == 80
    assert totals["decoded_weight_cache_high_water_bytes"] == 80
    assert totals["decoded_weight_cache_live_bytes"] <= cache.entry_budget_bytes


def test_scope_and_backend_changes_evict_as_units() -> None:
    cache, observations = _cache(budget=64)
    _admit(
        cache,
        scope=("layer-0",),
        key=("expert-0",),
        node=0,
        value=np.arange(4, dtype=np.float32),
    )
    hit = cache.probe(
        scope=("layer-0",),
        key=("expert-0",),
        node_id=0,
        backend_identity=IDENTITY,
    )
    assert hit.value is not None and hit.value.flags.writeable is False

    changed_scope = cache.probe(
        scope=("layer-1",),
        key=("expert-1",),
        node_id=0,
        backend_identity=IDENTITY,
    )
    assert changed_scope.value is None
    assert observations.snapshot()["totals"]["decoded_weight_cache_live_bytes"] == 0

    cache.admit(
        key=("expert-1",),
        node_id=0,
        value=np.arange(4, dtype=np.float32),
        admission_epoch=changed_scope.admission_epoch,
    )
    different_backend = {
        **IDENTITY,
        "flags": {"allow_tf32": False, "threads": 2},
    }
    invalidated = cache.probe(
        scope=("layer-1",),
        key=("expert-1",),
        node_id=0,
        backend_identity=different_backend,
    )
    assert invalidated.value is None
    totals = observations.snapshot()["totals"]
    assert totals["decoded_weight_cache_evictions"] == 2
    assert totals["decoded_weight_cache_live_bytes"] == 0


def test_volatile_backend_capacity_is_not_an_identity_or_epoch() -> None:
    cache, _ = _cache(budget=64)
    observed_a = {**IDENTITY, "device_memory_bytes": {"free": 1, "total": 8}}
    observed_b = {**IDENTITY, "device_memory_bytes": {"free": 2, "total": 8}}
    assert backend_identity_digest(observed_a) == backend_identity_digest(observed_b)
    _admit(
        cache,
        scope=("matrix",),
        key=("expert",),
        node=0,
        value=np.arange(4, dtype=np.float32),
        identity=observed_a,
    )
    hit = cache.probe(
        scope=("matrix",),
        key=("expert",),
        node_id=0,
        backend_identity=observed_b,
    )
    assert hit.value is not None


def test_oversize_and_stale_admissions_are_bypassed() -> None:
    cache, observations = _cache(budget=16)
    oversized = _admit(
        cache,
        scope=("matrix",),
        key=("large",),
        node=0,
        value=np.arange(5, dtype=np.float32),
    )
    assert oversized.flags.writeable

    stale = cache.probe(
        scope=("old",),
        key=("old",),
        node_id=0,
        backend_identity=IDENTITY,
    )
    cache.probe(
        scope=("new",),
        key=("new",),
        node_id=0,
        backend_identity=IDENTITY,
    )
    cache.admit(
        key=("old",),
        node_id=0,
        value=np.arange(2, dtype=np.float32),
        admission_epoch=stale.admission_epoch,
    )
    totals = observations.snapshot()["totals"]
    assert totals["decoded_weight_cache_admissions"] == 0
    assert totals["decoded_weight_cache_bypasses"] == 2
    assert totals["decoded_weight_cache_live_bytes"] == 0


def test_canonical_backend_identity_is_mapping_order_independent() -> None:
    reordered = {
        "flags": {"threads": 1, "allow_tf32": False},
        "device": "host",
        "library_version": "test",
        "library": "numpy",
        "backend": "numpy",
    }
    assert backend_identity_digest(IDENTITY) == backend_identity_digest(reordered)
