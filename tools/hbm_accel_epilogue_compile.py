#!/usr/bin/env python3
"""Opt-in HA3 component selection. Caller owns parent wiring and all numerical ops."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ClockLoopComponents:
    issue: str
    bulk_copy: str
    parameters: dict
    adopted: bool = False


def components(*, enable_ha3_clock_lookahead=False):
    """Same original port API; explicit opt-in never implies timing/production qualification."""
    if not enable_ha3_clock_lookahead:
        return ClockLoopComponents("ot_gpu_issue", "ot_gpu_bulk_copy", {})
    return ClockLoopComponents("ot_hbm_accel_issue", "ot_hbm_accel_bulk_copy", {"ENABLE": 1})


def lower_fused_epilogue(*args, **kwargs):
    # The predecessor's arithmetic FAIL is not waived by selecting clock repairs.
    raise ValueError("HA3 numerical fusion unavailable: nonfinite/wide-overflow golden gates remain FAILED")
