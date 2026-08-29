"""Shared ABI 3.0 cycle model.

One event-driven timing model consumes the same deployment artifacts as the
functional device in :mod:`runtime.sim.device`.  All four ABI 3.0 targets --
Qwen-HBM on one chip, Qwen-ROM on one chip, DeepSeek-HBM on a 32-node cluster
and DeepSeek-ROM on a wafer-scale logical device -- are timed by this one model
against one counter registry, which is the only reason their numbers are
comparable.

Three modules:

``machine``
    machine parameters, read from a :class:`~runtime.abi3.capability.Capability`
    plus a separately versioned cost table, with per-value provenance.
``fabric``
    the two physical realisations of the one architectural communication
    contract: the 32-node inter-node fabric and the on-wafer fabric.
``model``
    the event-driven core: microsequencer issue, bounded engine queues, engine
    occupancy, memory hierarchy and the event/wait scoreboard.
"""

from __future__ import annotations

from runtime.cycle.machine import (
    CostTable,
    MachineModel,
    Provenance,
    ResolvedParameter,
    load_cost_table,
)
from runtime.cycle.fabric import (
    ClusterFabric,
    FabricTiming,
    WaferFabric,
    build_fabric,
)
from runtime.cycle.model import (
    CycleModel,
    CycleResult,
    CYCLE_RESULT_SCHEMA,
    architectural_counters,
    timing_counters,
)

__all__ = [
    "CYCLE_RESULT_SCHEMA",
    "ClusterFabric",
    "CostTable",
    "CycleModel",
    "CycleResult",
    "FabricTiming",
    "MachineModel",
    "Provenance",
    "ResolvedParameter",
    "WaferFabric",
    "architectural_counters",
    "build_fabric",
    "load_cost_table",
    "timing_counters",
]
