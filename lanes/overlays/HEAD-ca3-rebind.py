"""HEAD-99: re-bind ALL 427 count-aligned ports from the both-edge bind sidecar (DIE-HEAD-ROUTE-1 p16r/ca3/out/regions_ca.json), then the FREG rule:
every port whose dst bus has plan landing_ring_wreg.freg gets freg:1, K+1, sched_lat+1 (as regions_ca_fz.json does for its marked ports); count_aligned_cycles = sched_lat.
usage: ca3_rebind.py PLAN SIDECAR REGIONS_CA PLAN_OUT SIDECAR_OUT"""
import json, sys
sys.path.insert(0, "/srv/opentallas-scratch2/claude/kw45/src_head_rp21z19/tools/die_plan")
import clock_landings as CL
pi, si, rc, po, so = sys.argv[1:6]
d = json.load(open(pi)); sc = json.load(open(si)); r = json.load(open(rc))
for k in ("granularity", "added_cycles_per_crossing", "regions", "ports", "count_aligned"):
    sc[k] = r[k]
P = sc["count_aligned"]["ports"]; cac = d["clock"]["landing_network"]["count_aligned_cycles"]
pt = {x["name"]: x["type"] for x in d["partitions"]}; ports = {p["id"]: p for p in d["ports"]}; nf = 0
for pid, c in P.items():
    p = ports[pid]; w = CL.ring_write_reg(d, pt[p["dst"]["part"]], p["dst"]["bus"])
    if w and w.get("freg"): c["K"] += 1; c["sched_lat"] += 1; c["freg"] = 1; nf += 1
    cac[pid] = c["sched_lat"]
    for q in sc["ports"] if isinstance(sc["ports"], list) else []:
        pass
d["note"] += " | HEAD-99: count-aligned K/depth/latency re-bound from the both-edge p16r ca3 plan (all 427, FREG +1 on %d ports)." % nf
json.dump(d, open(po, "w"), indent=1, ensure_ascii=False); json.dump(sc, open(so, "w"), indent=1, ensure_ascii=False)
print("freg ports", nf, "depths", sorted({c["depth"] for c in P.values()}))
