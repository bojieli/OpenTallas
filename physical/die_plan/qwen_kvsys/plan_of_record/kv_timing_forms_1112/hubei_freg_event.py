#!/usr/bin/env python3
"""KV-TIMING-FORMS-1 11-12 (COORD ruling via DIE-KV-98): kv3_hub_Ei ring FREG +1 data cycle on the dsel -> bin hop of
hp_fault (hub_Ei a24 TT -159.5: u_cland_i_hp_fault_N_q_d1 ring dch[0].u_dsel -> u_bin_i_hp_fault_N_q_d1).
Form = freg_mark_event.py (HEAD-94) for ONE crossing: plan clock.landing_ring_wreg {buses:[i_hp_fault_N_q_d1], dsrep:1, freg:true}
on kv3_hub_Ei; sidecar count_aligned.ports[pid] sched_lat+1, K+1, freg=1; source sidecar added_cycles+1; plan
clock.landing_network.count_aligned_cycles[pid]+1; lane latency row regenerated (gen.write_latency).
usage: hubei_freg_event.py REPO PLAN_IN SIDECAR_IN OUT_DIR  -> OUT/plan_c.json, OUT/eW_sidecar.json, OUT/lat/*"""
import copy, json, sys
from pathlib import Path
R = Path(sys.argv[1]).resolve(); out = Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(R / "tools/die_plan"))
import gen as G
P = json.loads(Path(sys.argv[2]).read_text()); S = json.loads(Path(sys.argv[3]).read_text())
BUS = "i_hp_fault_N_q_d1"; TN = "kv3_hub_Ei"
t = P["partition_types"][TN]["clock"]
assert not t.get("landing_ring_wreg"), "hub_Ei already has a landing_ring_wreg"
t["landing_ring_wreg"] = {"buses": [BUS], "dsrep": 1, "freg": True}
ei = {q["name"] for q in P["partitions"] if q["type"] == TN}
pids = [p["id"] for p in P["ports"] if p["dst"]["part"] in ei and p["dst"]["bus"] == BUS]
ca = S["count_aligned"]["ports"]; src = {x["port"]: x for x in S["ports"]}
cac = P["clock"]["landing_network"]["count_aligned_cycles"]
assert pids and all(i in ca for i in pids)
for pid in pids:
    c = ca[pid]
    assert cac[pid] == c["sched_lat"] == src[pid]["added_cycles"], (pid, cac[pid], c["sched_lat"], src[pid]["added_cycles"])
    assert not c.get("freg")
    c["freg"] = 1; c["sched_lat"] += 1; c["K"] += 1; src[pid]["added_cycles"] += 1; cac[pid] += 1
    print("RAISE", TN, pid, "sched_lat ->", c["sched_lat"], "K ->", c["K"])
tab, pkg, js = G.write_latency(copy.deepcopy(P), out / "lat")
old = P["latency"]["lanes"]
for lid, d in tab.items():
    if lid in old and any(old[lid].get(f) != d.get(f) for f in ("cycles", "natural", "clock_landing")):
        print("LANE", lid, old[lid]["cycles"], "->", d["cycles"])
        for f in ("cycles", "natural", "clock_landing"): old[lid][f] = d[f]
(out / "plan_c.json").write_text(json.dumps(P, indent=1) + "\n")
(out / "eW_sidecar.json").write_text(json.dumps(S))
print("written", out)
