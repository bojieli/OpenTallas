#!/usr/bin/env python3
"""DIE-HBM-82-RF 11-06: GEN of the RX BM3 residual no-macro delay forms (view ot_pdie_serdes_rx_bm3_rest@7826e3baf53d,
PART 37 plan pins, same generator args as HBM-GAPS-7 gen_rx_bm3.py vB2 / GAPS-8 vC).
  vA: -DOT_RXBM3_FLOPDLY            (no macros: both fixed-distance delays as shift registers)
  vB: -DOT_RXBM3_SRAM_SPLIT -DOT_RXBM3_FLOPC (word delay = 2 x 64x272 SRAM halves at the vC sites, correction delay = 10-stage SR)
usage: gen_rx.py WT LANEDIR vA|vB"""
import json, sys
from pathlib import Path
WT = Path(sys.argv[1]); L = Path(sys.argv[2]); V = sys.argv[3]
mod = "ot_pdie_serdes_rx_bm3_rest"
base = json.load(open(WT / "physical/die_plan/hbm_arch_cores/recipes_b2.json"))[mod]
rec = dict(base)
rec["files"] = list(base["files"]) + ["rtl/hbm_accel/cores_split/reform_1106/ot_s81_kp4_sp.sv"]
rec["source"] = f"DIE-HBM-82-RF 11-06 RE-FORM {V} of {base['source']}"
rec["read_at_commit"] = False
extra = ["--tag", V]
if V == "vA":
    rec["defines"] = ["OT_RXBM3_FLOPDLY"]; rec["macros"] = []
else:
    rec["defines"] = ["OT_RXBM3_SRAM_SPLIT", "OT_RXBM3_FLOPC"]; rec["macros"] = ["ot_sram_1r1w_64x272_m1_g272"]
    mp = L / "macros_vB.json"
    mp.write_text(json.dumps({"macro_placement": [
        {"k": "u_dly.u_dmem_lo", "macro": "ot_sram_1r1w_64x272_m1_g272", "origin_um": [51.084, 56.172], "orient": "R0"},
        {"k": "u_dly.u_dmem_hi", "macro": "ot_sram_1r1w_64x272_m1_g272", "origin_um": [51.084, 98.268], "orient": "R0"}]}) + "\n")
    extra += ["--macro-placement", str(mp), "--macro-inst-fmt", "{k}"]
vf = L / "views_res.json"
sys.path.insert(0, str(WT / "physical/die_plan/hbm_arch_cores")); sys.path.insert(0, str(WT / "tools/die_plan"))
import gen_core_kit_hbm as G
view = json.load(open(vf))["view_list"][0]["view"]
sys.argv = ["gen_core_kit_hbm.py", "--views", str(vf), "--view", view, "--recipe-key", mod, "--out", str(L / "kits"),
            "--corner", "TC", "--util", "0.4", "--pg-top-layer", "M5", "--clock-pin-entry", "on",
            "--io-tt-ps", "250", "--io-ff-ps", "202.5", "--face-reset-relay", "0"] + extra
print("RF_GEN", V, " ".join(sys.argv[1:]), flush=True)
G.main(recipe_overrides={mod: rec})
