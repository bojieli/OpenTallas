#!/usr/bin/env python3
"""Gate-level power of the K-element spine-gated stage with synchronised crossings (2026-10-04).

tools/rom_stage_pg_power.py (route R3 method: Icarus gate-level activity of the routed netlist, one SAIF per window,
OpenSTA report_power TT on the routed SPEF) applied to ot_v41_rom_stage_q_pg_cdc_w10 with the bench
rtl/test/tb_signoff_rom_stage_pg_cdc_k<K>.sv (same timeline and windows: ACTIVE / PG_IDLE / CG_IDLE).  Instance
classes: domain (elements + their domain-side interfaces), spine, shared scheduler/controller, per-element always-on
parts, always-on clock branch, the remaining root clock buffers.

    python3 tools/rom_stage_cdc_power.py --k K activity --routed <workdir> --work <dir>
    python3 tools/rom_stage_cdc_power.py --k K power --routed <workdir> --ao-routed <AO workdir> --work <dir> --out <json>
    python3 tools/rom_stage_cdc_power.py --k K inst --routed <workdir> --work <dir> --out <json>
"""
from __future__ import annotations

import sys

import rom_stage_pg_power as base

k = 1
if "--k" in sys.argv:
    i = sys.argv.index("--k")
    k = int(sys.argv[i + 1])
    del sys.argv[i:i + 2]
base.BENCH = base.ROOT / f"rtl/test/tb_signoff_rom_stage_pg_cdc_k{k}.sv"
base.BENCH_TOP = f"tb_signoff_rom_stage_pg_cdc_k{k}"
base.DUT = "ot_v41_rom_stage_q_pg_cdc_w10"
base.CLASSES = (("domain", (".u_elem.", ".u_dif.")),
                ("spine", ("u_spine_cg", "s_clk")),
                ("ao_sched_ctrl", ("u_ao.u_ctl.",)),
                ("ao_element", ("u_ao.g_e[",)))


def classify(name: str) -> str:
    for cls, keys in base.CLASSES:
        if any(x in name for x in keys):
            return cls
    if name.startswith(("clkbuf", "delaybuf", "clkload")) and "aon_clk" in name:
        return "aon_clock"
    if name.startswith(("clkbuf", "delaybuf", "clkload")) and ("_clk" in name):
        return "root_clock"
    return "unnamed"


base.classify = classify

if __name__ == "__main__":
    sys.exit(base.main())
