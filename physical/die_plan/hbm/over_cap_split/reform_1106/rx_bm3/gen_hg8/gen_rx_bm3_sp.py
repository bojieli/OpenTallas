#!/usr/bin/env python3
"""HBM-GAPS-8 11-06: RX BM3 residual SRAM-split safe form (vC), GEN only.
Residual ot_pdie_serdes_rx_bm3_rest (HG7 Model-A pins, SEAM 7, face shell) with `define OT_RXBM3_SRAM_SPLIT: the two
178-um 546-bit macros (pins on both 81-um vertical edges; 5-um side channels in the 197.856-um tile -> GRT congestion on
every form) become four 95.7 x 28.6 um 272-bit 1R1W halves in a centre column with ~47-um std-cell channels on both sides.
usage: gen_rx_bm3_sp.py WT OUT PLANSRC [extra gen args]   (WT = this repo checkout at the commit that holds this file)"""
import hashlib, json, shutil, subprocess, sys
from pathlib import Path
WT = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]); PLANSRC = Path(sys.argv[3])
SRC = subprocess.check_output(["git", "-C", str(WT), "rev-parse", "HEAD"], text=True).strip()
HERE = WT / "physical/die_plan/hbm/over_cap_split/reform_1106/rx_bm3/gen_hg8"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
pdir = OUT / "plan"; (pdir / "cores").mkdir(parents=True, exist_ok=True)
for f in ("die_plan.json", "core_macros.json"):
    if not (pdir / f).exists(): shutil.copy2(PLANSRC / f, pdir / f)
base = json.load(open(WT / "physical/die_plan/hbm_arch_cores/recipes_b2.json"))["ot_pdie_serdes_rx"]
files = list(base["files"]) + ["rtl/hbm_accel/cores_split/reform_1106/ot_pdie_serdes_rx_bm3.sv",
                               "rtl/hbm_accel/cores_split/reform_1106/ot_s81_kp4_sp.sv"]
mod, ol = "ot_pdie_serdes_rx_bm3_rest", [197.856, 345.6]
R = {mod: dict(top=mod, files=files, defines=["OT_RXBM3_SRAM_SPLIT"], params={"BMTHC": 1, "SEAM": 7},
               macros=["ot_sram_1r1w_64x272_m1_g272", "ot_sram_1r1w_32x272_m1_g272"],
               source="HBM-GAPS-8 11-06 RX BM3 residual SRAM-split safe form (HG7 SEAM 7 form + `define OT_RXBM3_SRAM_SPLIT)",
               source_commit=SRC, read_at_commit=True, util=float(__import__("os").environ.get("HG8_UTIL", "0.4")))}
dst = pdir / "cores" / f"{mod}__{ol[0]}x{ol[1]}__hg7_modelA.json"
shutil.copy2(HERE / f"{mod}__{ol[0]}x{ol[1]}__hg7_modelA.json", dst)   # HG7 residual pins (+ o_ne) unchanged
s = sha(dst)
view = dict(view=f"{mod}@{s[:12]}", module=mod, outline_um=ol, pins_file=str(dst.relative_to(pdir)), pins_sha256=s,
            pins=len(json.load(open(dst))), family="LINK", instances=["u_lk_rx.g_native.u_rest"], placed=1,
            tables_for_module=1, canonical_type=None, recipe_keys=[mod], blockers=[])
views = dict(schema="opentallas.hbm_arch.core_views.v1", plan=str(pdir / "die_plan.json"), plan_sha256=sha(pdir / "die_plan.json"),
             views=1, placed=1, modules=1, no_pins_table=[], view_list=[view])
vf = OUT / "views_res_sp.json"; vf.write_text(json.dumps(views, indent=1) + "\n")
(OUT / "recipe_res_sp.json").write_text(json.dumps(R, indent=1) + "\n")
sys.path.insert(0, str(WT / "physical/die_plan/hbm_arch_cores"))
import gen_core_kit_hbm as G
sys.argv = ["gen_core_kit_hbm.py", "--views", str(vf), "--view", view["view"], "--recipe-key", mod, "--out", str(OUT / "kits"),
            "--corner", "TC", "--util", R[mod]["util"].__str__(), "--pg-top-layer", "M5", "--clock-pin-entry", "on",
            "--io-tt-ps", "250", "--io-ff-ps", "202.5", "--face-reset-relay", "0",
            "--macro-placement", str(HERE / "macros_res_sp.json"), "--macro-inst-fmt", "{k}"] + sys.argv[4:]
print("HG8_GEN", view["view"], SRC, " ".join(sys.argv[1:]), flush=True)
G.main(recipe_overrides=R)
