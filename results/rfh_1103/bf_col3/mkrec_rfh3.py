#!/usr/bin/env python3
"""DIE-S81-51/RF-H 2026-11-03: specs + recipes of the 3-core bf_col (run from the repo root)."""
import json, copy
from pathlib import Path
old = json.load(open("physical/die_plan/s81/cores/legacy/specs/ot_v41_bf_col/spec.json"))
D = Path("results/rfh_1103/bf_col3/specs")
c = copy.deepcopy(old); c["top"] = "ot_v41_bf_col3_c"
c["sources"] = old["sources"] + ["rtl/v41rom/ot_v41_bf_col3_c.sv"]
c["params"] = dict(old["params"], BRNECUT=1)
c["route"] = {"pd": 0.62}
c["notes"] = ("DIE-S81-51/RF-H 2026-11-03 3-core bf_col: column core (pins, ROM pair, FP lanes, chains, pair, segment tree, "
              "outputs, BF root adder, half faces). Sources = the ot_v41_bf_col spec + ot_v41_bf_col3_c.sv; params = the "
              "S81 die instantiation + BRNECUT 1 (the halves' RNE cut; FP partials delayed DEQ = 3 to keep the BF/FP spacing).")
c["provenance"] = "RF-H 3-core split of physical/die_plan/s81/cores/legacy/specs/ot_v41_bf_col (results/rfh_1103/bf_col3)"
h = copy.deepcopy(old); h["top"] = "ot_v41_bf16_half"
h["sources"] = [s for s in old["sources"] if not s.endswith("_bb.v")] + ["rtl/v41rom/ot_v41_bf16_half.sv"]
h["params"] = {"NCHB": 8, "GRADUAL_RNE": 1, "TRW": 7, "RC": 1, "TNODE": 1, "RNECUT": 1}
h["reset_ports"] = ["rst_c"]; h["macros"] = []; h["route"] = {"pd": 0.65}
h["notes"] = ("DIE-S81-51/RF-H 2026-11-03 3-core bf_col: one BF16 half (8 lanes, tree levels 1-3) of ot_v41_bf16_lanes3 "
              "at the S81 bf_col parameters (TRW = HTG = 7, RC = 1 for QBF 2, TNODE = RCG = 1, RNECUT = BRNECUT = 1); "
              "rst_c / ze_c = the column core's face copies of g_pin.r_rst / r_ze. One master for u_ha and u_hb.")
h["provenance"] = c["provenance"]
for m, s in (("ot_v41_bf_col3_c", c), ("ot_v41_bf16_half", h)):
    (D / m).mkdir(parents=True, exist_ok=True)
    (D / m / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
rec = json.load(open("results/rfh_1103/bf_col/recipes_rfh_1103.json"))["ot_v41_bf_col"]
common = {"rtl_dirs": True, "hold_ff_margin": 0, "suffix": "rfh3"}
R = {"_doc": "DIE-S81-51/RF-H 2026-11-03 3-core bf_col recipes (plan delta physical/die_plan/s81/rfh3/plan_h2_2249_rfh3_bfcol3.json.gz). "
             "Conservative form: each core <= 150k cells, own N-face clock entry, regional taps <= 5k sinks per region, "
             "registered faces on every inter-core cut. util: the unchanged slot cannot hold 3 cores at 0.45 "
             "(est. cell util C ~0.53 / H ~0.57 of the core rows); PLACE_DENSITY just above the estimate.",
     "ot_v41_bf_col3_c": dict(common, params={"KEEP_XPOS": 1, "BRNECUT": 1}, lec_hints=rec["lec_hints"],
                              ref_tile="results/rfh_1103/bf_col3/specs/ot_v41_bf_col3_c", util=0.62,
                              macro_sites=rec["macro_sites"],
                              regional_taps={"nx": 2, "ny": 4, "split": "count", "win_ps": 20},
                              _why="ROM pair at the old core-local sites (x 42.12, R180 / MY): read bits face both logic "
                                   "channels (W: half faces + capture, E: pin faces + FP lanes); 2x4 regions of ~2.4k sinks"),
     "ot_v41_bf16_half": dict(common, params={}, ref_tile="results/rfh_1103/bf_col3/specs/ot_v41_bf16_half", util=0.65,
                              regional_taps={"nx": 4, "ny": 2, "split": "count", "win_ps": 20},
                              _why="one master for u_ha / u_hb (241.92 x 95.04, E-face pins toward the column core); "
                                   "4x2 regions of ~2.3k sinks (~18.3k flops)")}
Path("results/rfh_1103/bf_col3/recipes_rfh3.json").write_text(json.dumps(R, indent=1) + "\n")
print("ok")
