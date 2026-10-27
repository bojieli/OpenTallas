#!/usr/bin/env python3
"""HBM-KITS-1: trial core slices from the planU4f plan-defined clock entry (clock_entries.json, 12.8a) + kit gen.
  mk_kits.py PLANDIR VIEWS SLICEDIR KITDIR WT mod1,mod2,...
Slice = centre ck_entry island from the plan (identical for every instance, else refused), TT 250 / FF 202.5 +-20,
master_plan_sha256 TRIAL-no-frozen-master-plan (HBM plan not frozen). Kit = gen_core_kit_hbm.py --trial."""
import json, sys, subprocess, os
from pathlib import Path
plan, views, sdir, kdir, wt, mods = [os.path.abspath(x) for x in sys.argv[1:6]] + [sys.argv[6]]; mods = mods.split(",")
V = {v["module"]: v for v in json.load(open(views))["view_list"]}
CE = json.load(open(f"{plan}/clock_entries.json"))
Path(sdir).mkdir(parents=True, exist_ok=True); Path(kdir).mkdir(parents=True, exist_ok=True)
res = {}
for m in mods:
    v = V.get(m)
    if not v: res[m] = "NO_VIEW"; continue
    ents = [e for part in CE.values() if isinstance(part, dict) for e in part.values()
            if isinstance(e, dict) and e.get("module") == m]
    keys = {(tuple(e["xy_um"]), tuple(e["island_um"]), e["port"], tuple(e.get("merged_clock_ports") or [])) for e in ents}
    if len(keys) != 1:
        res[m] = f"ENTRY_NOT_UNIQUE {len(ents)} inst {len(keys)} forms"; continue
    xy, isl, port, merged = next(iter(keys))
    W, H = v["outline_um"]
    sl = {"schema": "opentallas.master_plan_slice.v1", "die": "hbm", "kind": "core", "type": m, "module": m,
          "instances": [], "master_plan_sha256": "TRIAL-no-frozen-master-plan", "frozen": False,
          "outline_um": [W, H], "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 20,
          "early_taps": False}, "keepouts": [], "bays": [], "entry_pins": [], "hard_cores": [], "corridors": [],
          "gates": {}, "core_clock_port": port or (merged[0] if merged else "clk"),
          "islands": [{"name": "ck_entry", "rect_um": list(isl), "centre_um": list(xy), "use": "clock_driver",
                       "via_stack": ["M9", "M5"], "clock_pin": {"layer": "M5", "xy_um": list(xy)}}],
          "note": f"HBM-KITS-1 trial slice: plan clock entry planU4f clock_entries.json ({len(ents)} inst identical); merged ports {list(merged)}"}
    json.dump(sl, open(f"{sdir}/{m}.json", "w"), indent=1)
    log = f"{kdir}/gen_{m}.log"
    cmd = ["python3", f"{wt}/physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py", "--views", views, "--view", v["view"],
           "--out", kdir, "--master-slice", sdir, "--trial", "--tag", "_k1"]
    r = subprocess.run(cmd, cwd=f"{wt}/physical/die_plan/hbm_arch_cores", stdout=open(log, "w"), stderr=subprocess.STDOUT)
    tail = open(log).read().strip().splitlines()[-1:] or [""]
    res[m] = f"rc={r.returncode} entry={list(xy)} port={port} merged={list(merged)} :: {tail[0][:300]}"
for m, r in res.items(): print(m, "|", r)
json.dump(res, open(f"{kdir}/mk_kits_result.json", "w"), indent=1)
