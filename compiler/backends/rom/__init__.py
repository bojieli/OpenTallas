"""Immutable-ROM backend family for ABI 3.0.

Two products share this one backend, one builder and one ABI:

``compiler.backends.rom.qwen3``
    Qwen3-8B on a conventional reticle-bounded single chip/package
    (:class:`~runtime.abi3.constants.TopologyClass.SINGLE_CHIP`) with mask-ROM
    weights and HBM/SRAM mutable state.

``compiler.backends.rom.deepseek_v4``
    DeepSeek-V4-Flash on a mandatory wafer-scale logical accelerator
    (:class:`~runtime.abi3.constants.TopologyClass.WAFER_LOGICAL_DEVICE`): a
    reticle/tile ROM assembly with an on-wafer fabric and distributed HBM
    state, presented to the host as one device.

Both consume the same backend-neutral Tensor Kernel IR v3 that the HBM/SRAM
backend consumes, and both emit through :class:`runtime.abi3.builder.
DeploymentBuilder`.  A ROM deployment therefore differs from an HBM deployment
in storage class, placement and topology, and in nothing else -- which is the
only reason the ROM-versus-HBM comparison means anything.
"""

from __future__ import annotations

__all__ = ["common", "deepseek_v4", "qwen3"]
