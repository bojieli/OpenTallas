#!/usr/bin/env python3
"""HBM-GAPS-7 11-06: private GEN of the RX BM3 safe form (Codex source d727c112224 / 58e1b7b1825).
Two views from Codex Model-A pin tables (not plan-adopted): BM child (x3 replicas) and residual (SEAM 6).
Face shell ON for both (registered faces; +1 in/+1 out per crossing; BM round trip +4 absorbed by SEAM 2->6)."""
import hashlib, json, shutil, sys
from pathlib import Path
WT = Path(sys.argv[1]); OUT = Path(sys.argv[2]); PLANSRC = Path(sys.argv[3]); WHICH = sys.argv[4]
SRC = "d727c1122244e484d0d2d0a0fb72f6fc9ae51e42"
P = WT / "physical/die_plan/hbm/over_cap_split/reform_1106/rx_bm3/prep_modelA"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
pdir = OUT / "plan"; (pdir / "cores").mkdir(parents=True, exist_ok=True)
for f in ("die_plan.json", "core_macros.json"):
    if not (pdir / f).exists(): shutil.copy2(PLANSRC / f, pdir / f)
base = json.load(open(WT / "physical/die_plan/hbm_arch_cores/recipes_b2.json"))["ot_pdie_serdes_rx"]
files = list(base["files"]) + ["rtl/hbm_accel/cores_split/reform_1106/ot_pdie_serdes_rx_bm3.sv"]
note = "HBM-GAPS-7 11-06 private RX BM3 safe form from Codex d727c112224 (58e1b7b1825); face shell registered seams; not plan-adopted"
R = {"ot_pdie_serdes_rx_bm_native": dict(top="ot_pdie_serdes_rx_bm_native", files=files, defines=[], params={"BMTHC": 1},
          macros=[], source=note + "; BM child", source_commit=SRC, read_at_commit=True, util=0.4),
     "ot_pdie_serdes_rx_bm3_rest": dict(top="ot_pdie_serdes_rx_bm3_rest", files=files, defines=[], params={"BMTHC": 1, "SEAM": int(__import__("os").environ.get("HG7_SEAM", "6"))},
          macros=list(base["macros"]), source=note + "; residual SEAM from HG7_SEAM (default 6: BM round trip +4)", source_commit=SRC, read_at_commit=True, util=0.4)}
V = {"bm": ("ot_pdie_serdes_rx_bm_native", [95.904, 106.56], "bm_pins.json"),
     "res": ("ot_pdie_serdes_rx_bm3_rest", [197.856, 345.6], "residual_pins.json")}
mod, ol, pf = V[WHICH]
dst = pdir / "cores" / f"{mod}__{ol[0]}x{ol[1]}__hg7_modelA.json"
shutil.copy2(P / pf, dst)
if WHICH == "res":
    # source ABI: rest has o_ne[4:0], unread; the F1 shell drops it and drives zero, as in the frozen rx kit. Model-A omitted
    # it; five free S-face M5 lattice points next to o_unc (dropped again by the face shell, never reach the parent).
    t = json.load(open(dst)); assert not any(q["name"].startswith("o_ne") for q in t)
    t += [dict(name=f"o_ne[{i}]", layer="M5", x=x, y=0.096) for i, x in enumerate((196.872, 197.064, 197.16, 197.256, 197.352))]
    dst.write_text(json.dumps(t) + "\n")
s = sha(dst)
view = dict(view=f"{mod}@{s[:12]}", module=mod, outline_um=ol, pins_file=str(dst.relative_to(pdir)), pins_sha256=s,
            pins=len(json.load(open(dst))), family="LINK", instances=([f"u_lk_rx.g_native.g_bm[{i}].u_bm" for i in range(3)] if WHICH == "bm" else ["u_lk_rx.g_native.u_rest"]), placed=3 if WHICH == "bm" else 1,
            tables_for_module=1, canonical_type=None, recipe_keys=[mod], blockers=[])
views = dict(schema="opentallas.hbm_arch.core_views.v1", plan=str(pdir / "die_plan.json"), plan_sha256=sha(pdir / "die_plan.json"),
             views=1, placed=view["placed"], modules=1, no_pins_table=[], view_list=[view])
vf = OUT / f"views_{WHICH}.json"; vf.write_text(json.dumps(views, indent=1) + "\n")
(OUT / f"recipe_{WHICH}.json").write_text(json.dumps({mod: R[mod]}, indent=1) + "\n")
sys.path.insert(0, str(WT / "physical/die_plan/hbm_arch_cores"))
import gen_core_kit_hbm as G
extra = sys.argv[5:]
sys.argv = ["gen_core_kit_hbm.py", "--views", str(vf), "--view", view["view"], "--recipe-key", mod, "--out", str(OUT / "kits"),
            "--corner", "TC", "--util", "0.4", "--pg-top-layer", "M5", "--clock-pin-entry", "on",
            "--io-tt-ps", "250", "--io-ff-ps", "202.5", "--face-reset-relay", "0"] + extra
print("HG7_GEN", WHICH, view["view"], " ".join(sys.argv[1:]), flush=True)
G.main(recipe_overrides={mod: R[mod]})
