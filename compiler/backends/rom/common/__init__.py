"""Shared ROM backend machinery: region planning, repair, and lowering.

``image``
    the immutable region plan -- layout, alignment, zero-padded gaps, per-region
    content digests, per-tile shard coordinates and the repair map.

``program``
    the loop-compressed, IR-driven lowering both ROM products share with the
    HBM/SRAM backend's contract: one instruction per *kernel*, never one per
    tile or per layer.

``inverse``
    the independent proof.  It deliberately imports neither of the other two.
"""

from __future__ import annotations

__all__ = ["image", "inverse", "program"]
