#!/usr/bin/env python3
"""core_latency.py: DECLARED cycles inside a hard core (CORE-LAT-1, DIE-QC-103 11-14, COORD 11-14).

Why: LATCHECK (lane_asbuilt_latency.py) and the bind's kit-source-station pricing (native_istations.annotate_kit) only count
stations they can see in the plan (internal_stations regs_um) and the bound RTL.  Registers INSIDE a hard core (e.g.
qfd_dv_s8_tap_bounded form d: all data inputs registered, +1 on its hw/cid/tap_fault outputs) were invisible, so a hand-built
core could add cycles and the lane check still said PASS.

Declaration (plan hard_cores[] row):   "core_latency": {"out": {"<type out bus>": <cycles>, ...}, "note": "..."}
  = the core adds <cycles> on every path that ends on that OUT bus of the type (all bits of the bus must come from the core).
Effect: the bus's source-station depth is (kit stations in internal_stations regs_um) + the declared core cycles, in BOTH the
bind pricing (annotate_kit) and LATCHECK (side_stages / kit_source_pricing).  A type that declares +1 but keeps its old station
count, or drops the station without declaring the core cycle, delivers != table and fails LANE_ASBUILT (class
UNPRICED_KIT_STATIONS / OTHER), instead of hiding.  No declaration = 0, byte-identical to before."""


def out_cycles(typ, bus):
    """declared hard-core cycles on OUT bus <bus> of plan type <typ> (0 = none)"""
    n = 0
    for h in (typ or {}).get("hard_cores", []) or []:
        cl = h.get("core_latency") or {}
        n += int((cl.get("out") or {}).get(bus, 0) or 0)
    return n
