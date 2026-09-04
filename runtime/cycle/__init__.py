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
    occupancy, memory hierarchy and the event/wait scoreboard -- and the
    schedule-driven tile decomposition.  The program loops over layers, token
    blocks, experts and vocabulary partitions only; one engine instruction names
    a whole contraction and the SCHEDULE descriptor carries its tile shape, so
    this model is the only place tiling becomes time.
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
    CycleRequest,
    CycleResult,
    CYCLE_RESULT_SCHEMA,
    ScheduleError,
    TileMapping,
    architectural_counters,
    functional_counters,
    functional_reference,
    operand_extents,
    prove_acyclic_waits,
    tile_mapping,
    timing_counters,
)
from runtime.cycle.batch import (
    BoundTokenTiming,
    CYCLE_BATCH_SCHEMA,
    CycleBatchScheduler,
    TIMING_RECORD_SCHEMA,
    TimingBindingError,
)

__all__ = [
    "CYCLE_RESULT_SCHEMA",
    "CYCLE_BATCH_SCHEMA",
    "BoundTokenTiming",
    "ClusterFabric",
    "CostTable",
    "CycleModel",
    "CycleRequest",
    "CycleResult",
    "CycleBatchScheduler",
    "FabricTiming",
    "MachineModel",
    "Provenance",
    "ResolvedParameter",
    "ScheduleError",
    "TileMapping",
    "TIMING_RECORD_SCHEMA",
    "TimingBindingError",
    "WaferFabric",
    "architectural_counters",
    "build_fabric",
    "functional_counters",
    "functional_reference",
    "load_cost_table",
    "operand_extents",
    "prove_acyclic_waits",
    "tile_mapping",
    "timing_counters",
]
