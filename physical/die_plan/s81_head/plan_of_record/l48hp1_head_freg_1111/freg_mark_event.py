#!/usr/bin/env python3
"""HEAD-94 11-11: FREG-DECL-1 marking event (COORD P1, claude/cland-fregcheck-1111).
 Every HEAD count-aligned ring with landing_ring_wreg.freg declares its +1 on the bind sidecar port: count_aligned.ports[pid]["freg"]=1
 ("this sched_lat includes the FREG cycle").  Per-port audit (queue RESULT 17:0x):
   hd_st_n4 x4   already counted by n4_event (sched_lat/added_cycles +1)  -> mark only
   hd_ctl_n x2, hd_turn_a x12  NOT counted -> sched_lat +1, K +1 (stored K; non-tree K is re-derived from sched_lat at bind), source sidecar
   added_cycles +1, plan clock.landing_network.count_aligned_cycles +1, lane latency regenerated (gen.write_latency).
 usage: freg_mark_event.py REPO BASE_PLAN.json[.gz] SIDECAR.json[.gz] OUT_DIR   -> OUT/source_plan.json, OUT/source_sidecar.json, OUT/lat/*"""
import copy, gzip, json, sys
from pathlib import Path
R = Path(sys.argv[1]).resolve(); out = Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(R / "tools/die_plan"))
import gen as G
def load(p):
    p = Path(p); return json.loads(gzip.open(p).read() if p.suffix == ".gz" else p.read_bytes())
P = load(sys.argv[2]); S = load(sys.argv[3])
parts = {q["name"]: q["type"] for q in P["partitions"]}
ca = S["count_aligned"]["ports"]; srcports = {x["port"]: x for x in S["ports"]}
ln = P["clock"]["landing_network"]; cac = ln["count_aligned_cycles"]
mark, raise_ = [], []
for p in P["ports"]:
    tn = parts.get(p["dst"]["part"])
    w = P["partition_types"].get(tn, {}).get("clock", {}).get("landing_ring_wreg") if tn else None
    if not (w and w.get("freg") and p["dst"]["bus"] in w.get("buses", [])): continue
    pid = p["id"]
    (mark if tn == "hd_st_n4" else raise_).append((pid, tn))
assert len(mark) == 4 and len(raise_) == 14, (len(mark), len(raise_))
for pid, tn in mark + raise_:
    c = ca[pid]
    assert cac[pid] == c["sched_lat"] == srcports[pid]["added_cycles"], (pid, cac[pid], c["sched_lat"], srcports[pid]["added_cycles"])
    c["freg"] = 1
for pid, tn in raise_:
    c = ca[pid]
    c["sched_lat"] += 1; c["K"] += 1
    srcports[pid]["added_cycles"] += 1
    cac[pid] += 1
    print("RAISE", tn, pid, "sched_lat ->", c["sched_lat"], "K ->", c["K"])
for pid, tn in mark: print("MARK ", tn, pid, "sched_lat", ca[pid]["sched_lat"])
tab, pkg, js = G.write_latency(copy.deepcopy(P), out / "lat")
old = P["latency"]["lanes"]
for lid, d in tab.items():
    if lid in old and any(old[lid].get(f) != d.get(f) for f in ("cycles", "natural", "clock_landing")):
        print("LANE", lid, old[lid]["cycles"], "->", d["cycles"])
        for f in ("cycles", "natural", "clock_landing"): old[lid][f] = d[f]
(out / "source_plan.json").write_text(json.dumps(P, indent=1) + "\n")
(out / "source_sidecar.json").write_text(json.dumps(S))
print("written", out)
