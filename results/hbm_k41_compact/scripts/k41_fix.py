#!/usr/bin/env python3
"""HBM-CORES-KITS-41/COMPACT G0C follow-up fixes on an event plan dir (copied, files rewritten in place).
usage: k41_fix.py tnode PLAN_DIR  -> u_mu_fused_n4 orient R0->MX (dn S-face pins then face the W/N station); tap recomputed
       k41_fix.py vms PLAN_DIR    -> wq_done0 of the R180 pose pins file moved core W (die E) -> core N (die S, its partners)"""
import json, sys, os, hashlib
B, D = sys.argv[1:3]
r6 = lambda v: round(v + 0.0, 6)
J = lambda p: json.load(open(os.path.join(D, p)))
def dump(name, obj):
    p = os.path.join(D, name)
    if os.path.islink(p): os.remove(p)
    json.dump(obj, open(p, "w"), indent=0 if name.startswith("cores/") else 1)
rep = J("k41_event_report.json"); rep.setdefault("fixes", [])
if B == "tnode":
    plan = J("die_plan.json"); ce = J("clock_entries.json")
    for pt in ("q_hub_nw", "q_hub_ne"):
        t = plan["partition_types"][pt]
        hc = next(h for h in t["hard_cores"] if h["inst"] == "u_mu_fused_n4")
        old = hc.get("orient", "R0"); hc["orient"] = "MX"
        W, H = hc["outline_um"]; ox, oy = hc["origin_um"]; x, y = ce[pt]["u_mu_fused_n4"]["xy_um"]
        tap = next(tp for tp in t["clock"]["taps"] if tp["name"] == "u_mu_fused_n4")
        o = list(tap["xy"]); tap["xy"] = [r6(ox + x), r6(oy + H - y)]
        hc["note"] += " | k41 G0C fix: orient MX so the dn S-face bus faces station n4x_dn_i"
        rep["fixes"].append({"type": pt, "inst": "u_mu_fused_n4", "orient": [old, "MX"], "tap": [o, tap["xy"]]})
    dump("die_plan.json", plan)
elif B == "vms":
    f = "cores/hnx_vms_bank_q0_faces__vecd4ae__224.64x272.16__k41c_f9c1bd05a046.json"
    ps = J(f); H = 272.16
    p = next(q for q in ps if q["name"] == "wq_done0"); o = dict(p)
    p.update({"layer": "M5", "x": 72.552, "y": r6(H - 0.096), "w": 0.024, "h": 0.192})
    dump(f, ps); rep["fixes"].append({"pins_file": f, "pin": "wq_done0", "old": o, "new": p,
        "sha256": hashlib.sha256(open(os.path.join(D, f), "rb").read()).hexdigest()})
dump("k41_event_report.json", rep)
print(json.dumps(rep["fixes"])[:600])
print("die_plan sha", hashlib.sha256(open(os.path.join(D, "die_plan.json"), "rb").read()).hexdigest()[:12])
