#!/usr/bin/env python3
"""DIE-HBM-36 V-A measure: per strip-column shared edge, pins actually on it (check.check_abutment face_pins),
free face (lane_add.free_gaps), and capacity at 6 / 12 pins/um. usage: strip_faces.py WT PLANDIR OUT_JSON"""
import sys, json, collections
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import schema as S, lane_add as LA, check as C
P = S.Plan(json.load(open(sys.argv[2] + "/die_plan.json")), None)
R = C.Report(False)
fp = C.check_abutment(P, R)
col = ["hub", "b000", "b010", "b001", "b011", "b002", "b012", "b003", "b013", "io"]
out = []
for half in ("NE", "NW"):
    names = [f"{half}_{c}" for c in col]
    names = [n if n in P.parts else (half + "_io" if n.endswith("_io") else n) for n in names]
    for a, b in zip(names, names[1:]):
        if a not in P.parts or b not in P.parts:
            out.append(dict(edge=f"{a}|{b}", missing=True)); continue
        e = LA.shared_edge(P, a, b)
        if not e:
            out.append(dict(edge=f"{a}|{b}", shared=None)); continue
        df, lo, hi = e
        pins_a = fp.get((a, df), [])
        pins = [p for p in pins_a if lo - 1e-6 <= p[0] <= hi + 1e-6]
        occ = LA.face_intervals(P, a, df) + LA.face_intervals(P, b, LA.OPP[df])
        gaps = list(LA.free_gaps(lo + 1.0, hi - 1.0, occ, 2.0))
        free = sum(g1 - g0 for g0, g1 in gaps)
        L = hi - lo
        bylayer = collections.Counter(p[1] for p in pins)
        occ_um = L - free
        out.append(dict(edge=f"{a}|{b}", face=df, len_um=round(L, 2), pins=len(pins), pins_per_um=round(len(pins) / L, 3),
                        layers=dict(bylayer), occupied_um=round(occ_um, 1), free_um=round(free, 1),
                        dens_in_occupied=round(len(pins) / occ_um, 2) if occ_um > 0 else None,
                        cap6=int(L * 6), cap12=int(L * 12), headroom12_vs_pins=int(L * 12) - len(pins)))
json.dump(out, open(sys.argv[3], "w"), indent=1)
for o in out:
    print(o)
