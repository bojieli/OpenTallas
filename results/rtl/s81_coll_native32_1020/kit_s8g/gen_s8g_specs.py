#!/usr/bin/env python3
"""S81-COLLECT2/COLLE (10-21) DRC successors of dscoll_lane_e_s8 / _s8k: macro-edge via guard (s8g / s8kg).

Why: route dscoll_lane_e_s8-s8-84d7d9b8f (ot-agidock128) closed timing (TT +44.77 / FF +3.75 ps at the routed
insertion) but kept DRC 51 = 33 "Short" + 18 "Metal Spacing", ALL on M4, ALL "inst:<ot_sram_1r1w2c_256x64_m1> net:<n>",
ALL on the EAST vertical edge of a 256x64 bank (the mirrored R180/MY pin face): Short bbox x = macro_x + 34.501..34.512
(the M4 OBS ends at 34.512, macro edge 34.584), Spacing bbox ending 0.035 um inside the edge; 18 on the RX FIFO bank
columns (x 43.2 / 129.6 / 216.0), 33 on the RB bank columns (388.8 / 561.6); none on the 32x64 GB banks, none at the tile
faces, PG or channels.  It is the known recipe-2 shape (physical/common_flow/macro_edge_via_guard.tcl, el1014-root-macro-
edge): M5 is free over the SRAM (OBS M1-M4), so GRT assigns a net an over-macro M5 track in the GCell straddling the edge
and DRT leaves it by an M4 jog through the macro OBS.  These kits are recipe 1, so the generator never added the guard
(e_s7 DRC 50 / e_s7k DRC 32 are the same kits' same shape).

Fix: spec boundary_tcl += physical/qwen_die_masters/sram_edge_guard.tcl (the supported recipe-1 opt-in: added before GRT,
removed after DRT, re-applied by the hold ECO) with OT_MEG_OUT_UM = 1.2 (guard extends 1.2 um outside each edge so the
straddling GCell has no M5 capacity; macro halo 5.4 um >= that).  Cost ~25 M5 tracks per macro edge over the macro, no
pin-stub access lost.  Same RTL, outline, macro map, pins / bit order, PDN, layer contract, CTS recipe and cycles.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BR = "claude/s81-colle-drc-1021"
GUARD = "physical/qwen_die_masters/sram_edge_guard.tcl"

if __name__ == "__main__":
    for base, tag in (("s8", "s8g"), ("s8k", "s8kg")):
        s = json.loads((ROOT / f"physical/ref_tile/dscoll_lane_e_{base}/spec.json").read_text())
        name = f"dscoll_lane_e_{tag}"
        s["name"] = name
        s["boundary_tcl"] = list(s.get("boundary_tcl", [])) + [GUARD]
        s.setdefault("orfs_vars", {})["OT_MEG_OUT_UM"] = "1.2"
        s["structural_change"] = __doc__.strip() + f"\n\n--- {base} base ---\n" + s["structural_change"]
        j = s["job"]
        j.update(owner="Claude:S81-COLLECT2", branch=BR, tag=tag,
                 views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
                 purpose=j["purpose"] + " + macro-edge via guard (s8 route DRC 51 = M4 jogs through SRAM OBS at the east bank edge).")
        d = ROOT / "physical/ref_tile" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", d / "spec.json")
