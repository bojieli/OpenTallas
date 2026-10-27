#!/usr/bin/env python3
"""HBM-CORE-LAT-R4 HUB: copy planS2 (B2o) -> OUT with the pin tables of MODULES snapped to the M4/M5 track lattice
0.024 + k*0.048 um along the face (same rule as R3 xcal planS2snap: off-face coordinate kept), collision-checked;
writes OUT/snap_report.json and one trial core slice per module (centre clock-entry island, M5 clock pin at the
outline centre snapped to the lattice; master_plan_sha256 TRIAL-no-frozen-master-plan, frozen false).
  snap_hub.py PLAN OUT SLICEDIR mod1,mod2,...   (die_plan.json untouched -> same sha)"""
import json, os, shutil, sys, math
plan, out, sdir, mods = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
P, O = 0.048, 0.024
def snap(v): return round(O + P * round((v - O) / P), 3)
if not os.path.isdir(out):
    shutil.copytree(plan, out, copy_function=os.link)      # hard links; snapped tables rewritten as new files
d = json.load(open(f"{plan}/die_plan.json"))
rep = {}; os.makedirs(sdir, exist_ok=True)
for k, t in d["partition_types"].items():
    for h in t.get("hard_cores", []):
        m = h["module"]
        if m not in mods or not h.get("pins_file"): continue
        f = h["pins_file"]; W, H = h["outline_um"]
        if f in rep: continue
        j = json.load(open(f"{plan}/{f}")); pins = j if isinstance(j, list) else j["pins"]
        disp = 0.0; seen = {}; coll = 0; layers = set()
        for q in pins:
            layers.add(q["layer"])
            onW, onE = q["x"] < 0.1, q["x"] > W - 0.1
            if onW or onE:   # W/E face: slide along y
                n = snap(q["y"]); disp = max(disp, abs(n - q["y"])); q["y"] = n
            else:            # N/S face: slide along x
                n = snap(q["x"]); disp = max(disp, abs(n - q["x"])); q["x"] = n
            key = (q["layer"], q["x"], q["y"])
            if key in seen: coll += 1
            seen[key] = 1
        tmp = f"{out}/{f}.tmp"; json.dump(j, open(tmp, "w")); os.unlink(f"{out}/{f}"); os.rename(tmp, f"{out}/{f}")
        rep[f] = dict(module=m, pins=len(pins), max_disp_um=round(disp, 4), collisions=coll, layers=sorted(layers),
                      clocks=[q["name"] for q in pins if q["name"].lower().startswith(("clk", "ck_", "hck"))])
        if not os.path.exists(f"{sdir}/{m}.json"):
            cx, cy = snap(W / 2), snap(H / 2)
            sl = {"schema": "opentallas.master_plan_slice.v1", "die": "hbm", "kind": "core", "type": m, "module": m,
                  "instances": [], "master_plan_sha256": "TRIAL-no-frozen-master-plan", "frozen": False,
                  "outline_um": [W, H], "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 20,
                  "early_taps": False}, "keepouts": [], "bays": [], "entry_pins": [], "hard_cores": [], "corridors": [],
                  "gates": {}, "core_clock_port": rep[f]["clocks"][0] if rep[f]["clocks"] else "clk",
                  "islands": [{"name": "ck_entry", "rect_um": [cx - 2.16, cy - 2.16, cx + 2.16, cy + 2.16],
                               "centre_um": [cx, cy], "use": "clock_driver", "via_stack": ["M9", "M5"],
                               "clock_pin": {"layer": "M5", "xy_um": [cx, cy]}}]}
            json.dump(sl, open(f"{sdir}/{m}.json", "w"), indent=1)
json.dump(rep, open(f"{out}/snap_report.json", "w"), indent=1)
for f, r in sorted(rep.items()): print(r["module"], f.split("__")[-1], r["pins"], r["max_disp_um"], r["collisions"], r["layers"], r["clocks"])
