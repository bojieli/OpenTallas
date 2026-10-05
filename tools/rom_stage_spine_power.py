#!/usr/bin/env python3
"""Gate-level power of the spine-gated S81 ROM element (gated stage clock spine, 2026-10-04).

tools/rom_stage_pg_power.py (route R3 method) applied to ot_v41_rom_elem_q_pg_sp_w10 (PG = 1, SPINE = 1) with the
bench rtl/test/tb_signoff_rom_elem_pg_sp.sv (same timeline and windows: ACTIVE / PG_IDLE / CG_IDLE).  Instance
classes add the spine (the gated trunk after u_spine_cg) and the always-on clock branch (aon_clk tree) to the R3
classes, so the residual's parts are attributed.

    python3 tools/rom_stage_spine_power.py activity --routed <R5 workdir> --work <dir>
    python3 tools/rom_stage_spine_power.py power --routed <R5 workdir> --ao-routed <A3 workdir> --work <dir> --out <json>
    python3 tools/rom_stage_spine_power.py inst --routed <R5 workdir> --work <dir> --out <json>
"""
from __future__ import annotations

import sys

import rom_stage_pg_power as base

base.BENCH = base.ROOT / "rtl/test/tb_signoff_rom_elem_pg_sp.sv"
base.BENCH_TOP = "tb_signoff_rom_elem_pg_sp"
base.DUT = "ot_v41_rom_elem_q_pg_sp_w10"
base.CLASSES = (("domain", ("u_pg.u_elem.", "u_pg.e_clk", "u_pg.u_elem")),
                ("spine", ("g_spine.", "u_ao.s_clk", "_s_clk")),
                ("ao_sched_ctrl", ("u_pg.g_pg.u_ao.u_sched.",)),
                ("ao_element", ("u_pg.g_pg.u_ao.",)))


def classify(name: str) -> str:
    for cls, keys in base.CLASSES:
        if any(k in name for k in keys):
            return cls
    if name.startswith(("clkbuf", "delaybuf", "clkload")) and "aon_clk" in name:
        return "aon_clock"
    if name.startswith(("clkbuf", "delaybuf", "clkload")) and ("_clk" in name):
        return "root_clock"
    return "unnamed"


base.classify = classify

if __name__ == "__main__":
    sys.exit(base.main())
