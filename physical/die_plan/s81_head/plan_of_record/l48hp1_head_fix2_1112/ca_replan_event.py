#!/usr/bin/env python3
"""HEAD-94 11-12: K re-selection from DIE-PROTO-1 (claude/die-proto-3-1111, ca_replan.py) for the 8 lep0N/nst4 crossings that read below
100 ps after the lepB move.  The non-tree K is derived from sched_lat at bind (K = sched_lat - 1 - (n_dst - n_src)), so the event sets
sched_lat (sidecar count_aligned.ports, source ports[].added_cycles, plan clock.landing_network.count_aligned_cycles) and the stored K
consistently; lane latency is regenerated (gen.write_latency).
 usage: ca_replan_event.py REPO BASE_PLAN[.gz] SIDECAR[.gz] BIND_CA2.json OUT_DIR"""
import copy, gzip, json, sys
from pathlib import Path
R = Path(sys.argv[1]); out = Path(sys.argv[5]); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(R / "tools/die_plan"))
import gen as G
def load(p):
    p = Path(p); return json.loads(gzip.open(p).read() if p.suffix == ".gz" else p.read_bytes())
P = load(sys.argv[2]); S = load(sys.argv[3]); B = load(sys.argv[4])
NEW = {  # pid: (new sched_lat, expected new K)  DIE-PROTO-1 ca_lag_rows_freg_ca3 / ca_replan.py
    "coll_WN3_d__0": (5, 11), "ctrl_lep__0": (4, 10), "head_lep_fault_return__0": (4, 10), "head_lep_landing__0": (4, 10),
    "ku__0": (4, 0), "coll_WN0_d__0": (3, -13), "coll_WN1_u__2": (2, 24), "coll_WN2_u__4": (2, 24)}
ca = S["count_aligned"]["ports"]; src = {x["port"]: x for x in S["ports"]}
cac = P["clock"]["landing_network"]["count_aligned_cycles"]; parts = B["parts"]
for pid, (sl, k_exp) in NEW.items():
    c = ca[pid]; b = B["ports"][pid]
    dn = parts[b["dst_part"]]["n_nominal"] - parts[b["src_part"]]["n_nominal"]
    k = sl - 1 - dn
    assert c["sched_lat"] == cac[pid], (pid, c["sched_lat"], cac[pid])
    if src[pid]["added_cycles"] != c["sched_lat"]: print("NOTE source added_cycles", src[pid]["added_cycles"], "!= sched_lat", c["sched_lat"], pid)
    print(f"{pid}: sched_lat {c['sched_lat']} -> {sl}, K {c['K']} -> {k} (DIE-PROTO K {k_exp}; bind K was {b['K']}, FREG mark {c.get('freg')})")
    c["sched_lat"] = sl; c["K"] = k; src[pid]["added_cycles"] = sl; cac[pid] = sl
old = copy.deepcopy(P["latency"]["lanes"])
tab, pkg, js = G.write_latency(copy.deepcopy(P), out / "lat")
for lid, d in tab.items():
    if lid in old and (old[lid]["cycles"] != d["cycles"]):
        print("LANE", lid, old[lid]["cycles"], "->", d["cycles"])
        for f in ("cycles", "natural", "clock_landing"): P["latency"]["lanes"][lid][f] = d[f]
(out / "source_plan.json").write_text(json.dumps(P, indent=1) + "\n")
(out / "source_sidecar.json").write_text(json.dumps(S))
