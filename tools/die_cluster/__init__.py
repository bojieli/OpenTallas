"""Shared hierarchical cluster-hardening support for every die (HBM, S81, Qwen).

boundary.py: cluster outline handling -- bodies fully inside / outside (never straddling), boundary ports pinned ON the
outline from the parent placement (edge, layer, track-legal, fixed), repair confined to the outline and legalised, and a
fail-closed pre-GRT bounds check (no cell or pin outside the die, every port on the outline).
"""
