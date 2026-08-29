"""Shared HBM/SRAM accelerator backend (ABI 3.0).

One backend, one code path, two deployment topologies: Qwen on a single chip
and DeepSeek on exactly 32 identical chips.  Model identity selects checkpoint
bindings, descriptors and the topology profile.  It never selects a code path:
:func:`compiler.backends.hbm_sram.lower.lower_to_abi3` is model-blind and reads
only the neutral graph, the capability and the topology.

Modules
-------
``capability``
    the shared-chip capability records (single chip and 32-node cluster).
``plan``
    the HBM/SRAM Physical Plan IR -- weight placement, SRAM tiling, bank
    assignment, loop schedules and topology, with a canonical digest.
``lower``
    the plan-driven ABI 3.0 emitter.
``check``
    an independent legality report that reconstructs the expected placement and
    program shape without importing the lowering.
"""

from .capability import (  # noqa: F401
    PROFILES,
    capability_for,
    cluster32_capability,
    profile_difference,
    single_chip_capability,
)
from .plan import PhysicalPlan, PlanError, TileConfig, build_plan, read_kernel_graph  # noqa: F401

__all__ = [
    "PROFILES",
    "PhysicalPlan",
    "PlanError",
    "TileConfig",
    "build_plan",
    "capability_for",
    "cluster32_capability",
    "profile_difference",
    "read_kernel_graph",
    "single_chip_capability",
]
