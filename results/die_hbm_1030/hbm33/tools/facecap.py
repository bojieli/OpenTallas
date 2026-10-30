#!/usr/bin/env python3
"""DIE-HBM-33 estimate: free pin capacity on every shared edge of the named partitions (lane_add free_gaps over both
sides' face intervals, guard 2 um, 6 pins/um) -> per edge total free um, largest contiguous gap, pins at 6/um.
usage: facecap.py WT PLANDIR PART [PART...]"""
import sys, json
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import schema as S, lane_add as LA
P = S.Plan(json.load(open(sys.argv[2] + "/die_plan.json")))
for a in sys.argv[3:]:
    tot = 0.0
    for b in sorted(P.parts):
        if b == a:
            continue
        e = LA.shared_edge(P, a, b)
        if not e:
            continue
        df, lo, hi = e
        occ = LA.face_intervals(P, a, df) + LA.face_intervals(P, b, LA.OPP[df])
        gaps = [(g0, g1) for g0, g1 in LA.free_gaps(lo + 1.0, hi - 1.0, occ, 2.0)]
        free = sum(g1 - g0 for g0, g1 in gaps); big = max([g1 - g0 for g0, g1 in gaps] or [0.0])
        tot += free
        print(f"{a:8s}|{b:9s} {df} len {hi-lo:7.1f} free {free:7.1f} um ({int(free*6):5d} pins) largest {big:7.1f} um ({int(big*6):5d} pins)")
    print(f"{a} TOTAL free {tot:.1f} um ({int(tot*6)} pins)")
