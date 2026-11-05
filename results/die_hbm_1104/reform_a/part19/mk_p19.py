#!/usr/bin/env python3
"""HBM-REFORM-A3 d44v part 19 plan delta.   mk_p19.py PLAN_DIR PART_DIR REPO
PLAN_DIR: a plan copy with parts 17, 18 applied. Runs results/die_hbm_1103/reform/mk_split.py unchanged; adds the htile recipe. No macros and no reset pin on htile."""
import json, os, subprocess, sys
from pathlib import Path
pd, part, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
H = "ot_hgi_coll_tkm_tp192_htile_core"
subprocess.run([sys.executable, str(repo / "results/die_hbm_1103/reform/mk_split.py"), str(pd), str(part / "split_p19.json"), str(part)], check=True, stdout=open(pd / "split_p19.log", "w"))
print((pd / "split_p19.log").read_text()[-900:])
# TKM corridor clock buffers name the tile taps; each tile tap is now __ha + __hb. Each leg splits, repeaters per sub (hb copy offset one cell width), legs re-derived.
D = json.loads((pd / "die_plan.json").read_text()); ck = D["partition_types"]["root"]["clock"]; tx = {t["name"]: t["xy"] for t in ck["taps"]}; nb = 0
for b in ck.get("branch_buffers") or []:
    if not b["name"].startswith("u_tkmclk_"): continue
    dr = [d + s for d in b["drives"] for s in ("__ha", "__hb")]; assert all(d in tx for d in dr), b["name"]
    reps = []
    for r in b.get("leg_repeaters") or []:
        for s, dx in (("__ha", 0.0), ("__hb", -1.62 if r["name"].split("_r")[-1].split("_")[0] in ("20", "27") else 1.62)):
            q = json.loads(json.dumps(r)); q["name"] = r["name"] + s; q["tap"] = r["tap"] + s
            q["xy"] = [round(r["xy"][0] + dx, 3), r["xy"][1]]; q["cell_ll_um"] = [round(r["cell_ll_um"][0] + dx, 3), r["cell_ll_um"][1]]; reps.append(q)
    b["drives"] = dr; b["leg_repeaters"] = reps
    b["legs_um"] = [round(abs(tx[d][0] - b["xy"][0]) + abs(tx[d][1] - b["xy"][1]), 3) for d in dr]; nb += 1
(pd / "die_plan.json").unlink(); (pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n"); print("tkm branch buffers", nb)
f = pd / "core_clock_regions.json"; G = json.loads(f.read_text()); gone = []
if isinstance(G.get("modules"), dict):
    for m in ("ot_hgi_coll_tkm_tp192_tile_core__idpin__strap", "ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap"):
        if m in G["modules"]:
            e = G["modules"].pop(m); gone.append(m)
    t = f.with_suffix(".tmp"); t.write_text(json.dumps(G, indent=1) + "\n"); os.replace(t, f)
print("regions removed", gone)
f = repo / "physical/die_plan/hbm_arch_cores/recipes_b2.json"; R = json.loads(f.read_text())
R[H] = dict(top=H, files=["rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm.sv", "rtl/hbm_accel/cores_split/reform_1103/tkm_tile/" + H + ".sv"], defines=[], params={}, macros=[],
            source="HBM-REFORM-A3 d44v part 19: half tile, the chain element at PT 32 (reform_1103 reduced-chain receipt); plan pins == RTL top ports")
t = f.with_suffix(".tmp"); t.write_text(json.dumps(R, indent=1) + "\n"); os.replace(t, f)
print("recipe", H)
