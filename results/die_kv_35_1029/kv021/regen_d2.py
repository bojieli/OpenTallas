#!/usr/bin/env python3
"""DIE-KV-35: regenerate count-align port d intervals (ca_mixed_replan.json form) from a clock proof with MAIN
count_align_plan.load_rows + sta_rows_hull (the gate's per-port interval, table OCV, shared droop, spice_edge, inv).
usage: regen_d.py TOOLS_DIR LPO_JSON PROOF STA_PLAN TEMPLATE_BIND OUT [CHECK]"""
import json, sys, types
tools, lpo, proof, plan, tmpl, out = sys.argv[1:7]
sys.path.insert(0, tools)
import count_align_plan as CAP
a = types.SimpleNamespace(corner="TT_droop-regions_corelat250,FF_droop-regions_corelat202.5", sta_proof=proof,
    sta_plan=plan, sta_clock_cal="spice_edge", sta_cppr_lca=True, sta_clock_ocv="table", sta_clock_droop="shared",
    sta_droop_regions=proof + "/droop_regions.json", sta_core_latency_ff=202.5, sta_clock_cell="inv")
rows = CAP.load_rows(lpo, a.corner, 1.0)
summ = CAP.sta_rows_hull(rows, a)
# DIE-KV-35: hull BOTH gate calibrations (spice_edge + spice_cell): the brief gates CA >=100 on both
import copy
rows2 = CAP.load_rows(lpo, a.corner, 1.0); a2 = copy.copy(a); a2.sta_clock_cal = "spice_cell"
summ2 = CAP.sta_rows_hull(rows2, a2)
by2 = {r["port"]: r for r in rows2}
for r in rows:
    o = by2[r["port"]]
    lo = min(r["d_ps"] - r["p_dn_ps"], o["d_ps"] - o["p_dn_ps"]); hi = max(r["d_ps"] + r["p_up_ps"], o["d_ps"] + o["p_up_ps"])
    r["p_dn_ps"], r["p_up_ps"] = r["d_ps"] - lo, hi - r["d_ps"]
    r["unshared_sta_ps"] = max(r.get("unshared_sta_ps", 0.0), o.get("unshared_sta_ps", 0.0))
summ = dict(edge=summ, cell=summ2)
print("HULL", json.dumps(summ), flush=True)
b = json.load(open(tmpl))
by = {r["port"]: r for r in rows}
miss = 0
for p, v in b["ports"].items():
    r = by.get(p)
    if r is None:
        miss += 1; continue
    v["d_lo_ps"] = round(r["d_ps"] - r["p_dn_ps"], 1); v["d_hi_ps"] = round(r["d_ps"] + r["p_up_ps"], 1)
    v["wander_ps"] = round(0.05 * max(r.get("unshared_a_ps", 0.0), r.get("unshared_b_ps", 0.0), r.get("unshared_sta_ps", 0.0)), 1)
b["regen"] = dict(by="DIE-KV-35 regen_d.py", proof=proof, sta_plan=plan, lpo=lpo, hull=summ, missing=miss)
json.dump(b, open(out, "w"), indent=0)
print("MISSING", miss, "PORTS", len(b["ports"]))
if len(sys.argv) > 7:
    ref = json.load(open(sys.argv[7]))["ports"]; worst = 0; n = 0
    for p, v in b["ports"].items():
        for k in ("d_lo_ps", "d_hi_ps", "wander_ps"):
            dlt = abs(v[k] - ref[p][k]); worst = max(worst, dlt); n += dlt > 0.11
    print("CHECK vs", sys.argv[7], "max |delta|", round(worst, 2), "ports differing", n)
