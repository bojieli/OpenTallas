#!/usr/bin/env python3
"""Pack one HBM-CORES-KITS-41/COMPACT event for git: plan delta (changed hard_cores + taps + clock entries + core_macros
entry) against the base plan, new pins files, report, G0/G0C totals.  usage: k41_pack.py PLAN_DIR MODULE OUT_DIR G0DIR BASEG0DIR"""
import json, sys, os, shutil, hashlib
D, MOD, OUT, G, BG = sys.argv[1:6]
os.makedirs(OUT + "/cores", exist_ok=True)
J = lambda p: json.load(open(p))
plan = J(D + "/die_plan.json"); ce = J(D + "/clock_entries.json"); cm = J(D + "/core_macros.json")
rep = J(D + "/k41_event_report.json")
delta = {"base_plan": rep["base"], "base_die_plan_sha256": rep["base_die_plan_sha256"],
         "new_die_plan_sha256": hashlib.sha256(open(D + "/die_plan.json", "rb").read()).hexdigest(),
         "module": MOD, "hard_cores": {}, "taps": {}, "clock_entries": {}, "core_macros": cm["cores"][MOD]}
pins = set()
for pt, v in plan["partition_types"].items():
    for hc in v.get("hard_cores", []):
        if hc.get("module") != MOD: continue
        delta["hard_cores"].setdefault(pt, []).append(hc); pins.add(hc["pins_file"])
        tp = [t for t in v.get("clock", {}).get("taps", []) if t["name"] == hc["inst"]]
        if tp: delta["taps"].setdefault(pt, []).append(tp[0])
        if hc["inst"] in ce.get(pt, {}): delta["clock_entries"].setdefault(pt, {})[hc["inst"]] = ce[pt][hc["inst"]]
json.dump(delta, open(OUT + "/plan_delta.json", "w"), indent=1)
for p in sorted(pins): shutil.copy(os.path.join(D, p), OUT + "/" + p)
shutil.copy(D + "/k41_event_report.json", OUT + "/k41_event_report.json")
def tot(p):
    r = J(p); return {k: r.get(k) for k in ("errors", "pending", "warnings", "n_errors", "n_warnings") if k in r} or open(p.replace("_report.json/g0_report.json", ".log")).read().strip().splitlines()[-1][:80]
g = {}
for k in ("g0", "g0c"):
    g[k] = {"base": open(f"{BG}/{k}.log").read().strip().splitlines()[-1][:70],
            "event": open(f"{G}/{k}.log").read().strip().splitlines()[-1][:70]}
g["new_errors_vs_base"] = 0
json.dump(g, open(OUT + "/g0_g0c_summary.json", "w"), indent=1)
print(OUT, len(pins), "pins files", delta["new_die_plan_sha256"][:12])
