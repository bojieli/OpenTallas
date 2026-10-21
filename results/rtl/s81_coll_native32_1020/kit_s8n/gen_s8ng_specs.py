#!/usr/bin/env python3
"""GAP-SKQ/GSKQ-LKTO (10-21) successors of dscoll_lane_{w,e}_s8nq / _s8nr: SRAM macro-edge via guard.

Why: dscoll_lane_e_s8-s8-84d7d9b8f (same lane RTL family, same 55-SRAM lattice, same recipe-1 kit flow) routed
TT +44.77 / FF +3.75 ps but DRC 51 (DRT stalled 56 -> 51 from iter 40 to 64); e_s7 DRC 50 / e_s7k DRC 32 the same.
All 51 markers are M4 Short (33) / Metal Spacing (18) "inst:<ot_sram_1r1w2c_256x64_m1> net:<n>", every bbox 0.06-0.08 um
inside the macro M4 OBS end (x = macro pin edge 77.784 / 164.184 / 250.584 / 423.384 / 596.184 minus 0.072..0.083):
the net sits on the first over-macro M5 track (77.724, between the OBS end 77.712 and the pin stub 77.760) and its
V4 enclosure / M4 jog cuts the macro OBS -- exactly the shape physical/common_flow/macro_edge_via_guard.tcl was written
for (s81su qnq/qbe, qkd_sbufp q14, qfd_tt_head h16c, qkd_embedding_row_tx).  The lane kits are recipe 1, so
ref_tile.macro_edge_guard() never added the guard.  Fix (structural, routing-resource level; no timing relaxed): source
the guard (physical/qwen_die_masters/sram_edge_guard.tcl as boundary_tcl: added before GRT, removed after DRT) with
OT_MEG_DEPTH_UM 6.0 (the depth that closed qfd_tt_head h16c / qkd_embedding_row_tx r2 DRC 0).
  s8ng = s8nq (K=24, best pin-flop spread W 55.5/51.7, E 53.9/53.1) + guard depth 6.0            (MAIN)
  s8nh = s8nr (K=32) + guard depth 6.0 + OT_MEG_OUT_UM 1.2 (straddling GCell outside the edge too,
         KV r7t-hd2 lesson; halo 5.4 um > 1.2)                                                      (FALLBACK)
Same RTL, outline, macros, pins / bit order, PDN, layer contract, CTS and cycles.  M5 over each macro loses 2 x 6 um of
its 34.6 um width; trial GRT had headroom (overflow 0, worst layer M2 13 %).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BR = "claude/s81-coll-1021"
GUARD = "physical/qwen_die_masters/sram_edge_guard.tcl"

if __name__ == "__main__":
    for side in ("w", "e"):
        for tag, base, extra in (("s8ng", "s8nq", {}), ("s8nh", "s8nr", {"OT_MEG_OUT_UM": "1.2"})):
            s = json.loads((ROOT / f"physical/ref_tile/dscoll_lane_{side}_{base}/spec.json").read_text())
            name = f"dscoll_lane_{side}_{tag}"
            s["name"] = name
            s["boundary_tcl"] = [*s.get("boundary_tcl", []), GUARD]
            s["orfs_vars"].update({"OT_MEG_DEPTH_UM": "6.0", **extra})
            s["structural_change"] = __doc__.strip() + f"\n\n--- {base} base ---\n" + s["structural_change"]
            j = s["job"]
            j.update(owner="Claude:GAP-SKQ", branch=BR, tag=tag,
                     views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
                     purpose=j["purpose"] + f" + SRAM macro-edge via guard (depth 6.0{' out 1.2' if extra else ''}) for the e_s8 DRC 51 M4 OBS-jog shape.")
            d = ROOT / "physical/ref_tile" / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
            print("wrote", d / "spec.json")
