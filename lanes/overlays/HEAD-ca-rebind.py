"""HEAD-99 (FABLE-PD-HEAD-CLK fix 2): re-bind K / DEPTH / lane latency from the count-aligned plan built on the p16r clock (ca2/plan.json).
usage: ca_rebind.py PLAN_IN SIDECAR_IN CA_PLAN PLAN_OUT SIDECAR_OUT   (then: gen.py latency PLAN_OUT --inplace; G0; head_bind_latcheck)"""
import json, sys
pi, si, cp, po, so = sys.argv[1:6]
d = json.load(open(pi)); sc = json.load(open(si)); c = json.load(open(cp))["crossings"]
cac = d["clock"]["landing_network"]["count_aligned_cycles"]; P = sc["count_aligned"]["ports"]
ch = dict(cyc=0, K=0, depth=0)
for x in c:
    p = x["port"]; assert p in cac and p in P, p
    lat = x["lat_cycles"] + (1 if P[p].get("freg") else 0)   # FREG-DECL-1: sched_lat includes the FREG cycle
    if cac[p] != lat: cac[p] = lat; ch["cyc"] += 1
    if P[p]["K"] != x["K"]: P[p]["K"] = x["K"]; ch["K"] += 1
    if P[p]["depth"] != x["depth"]: P[p]["depth"] = x["depth"]; ch["depth"] += 1
    P[p]["sched_lat"] = lat
d["note"] += " | HEAD-99 CA re-bind from the p16r clock (FABLE-PD-HEAD-CLK): count_aligned_cycles / K / depth from ca2/plan.json."
json.dump(d, open(po, "w"), indent=1, ensure_ascii=False); json.dump(sc, open(so, "w"), indent=1, ensure_ascii=False)
print("changed", ch)
