#!/usr/bin/env python3
"""DIE-HBM-24/L7: hub S-face occupancy census (read-only). usage: hubface.py TOOLS PLAN_JSON [HUB]"""
import sys, json
sys.path.insert(0, sys.argv[1])
import schema as S, lane_add as LA
raw = json.load(open(sys.argv[2])); hub = sys.argv[3] if len(sys.argv) > 3 else "NW_hub"
P = S.Plan(raw)
lane_of = {}
for l in raw["lanes"]:
    for q in l["ports"]:
        lane_of[q] = l["id"]
print("hub rect", P.rect(hub))
for n in sorted(P.parts):
    e = LA.shared_edge(P, hub, n)
    if not e:
        continue
    df, lo, hi = e
    occ = []
    for pid, pr in P.ports.items():
        if "face" not in pr or "window_um" not in pr: continue
        if {pr["src"]["part"], pr["dst"]["part"]} != {hub, n}: continue
        for _, _, w in S.port_segments(pr):
            occ.append((round(min(w), 1), round(max(w), 1), lane_of.get(pid, pid), pr.get("width")))
    occ.sort()
    allocc = LA.face_intervals(P, hub, df) + LA.face_intervals(P, n, LA.OPP[df])
    gaps = LA.free_gaps(lo + 1, hi - 1, allocc, 2.0)
    print(f"{n:10s} face {df} edge {lo:.1f}-{hi:.1f} ({hi-lo:.1f})  P.rect={tuple(round(v,1) for v in P.rect(n))}")
    for o in occ: print("     ", o)
    print("      free gaps:", [(round(a,1), round(b,1), round(b-a,1)) for a, b in gaps if b - a > 5])
