#!/usr/bin/env python3
"""resite_stn.py PLAN_IN PLAN_OUT TYPES CONN_PREFIX "x,y;x,y;..." : re-site the register sites of matching internal_stations
along a monotone polyline from_um -> waypoints -> to_um, equally spaced by arc length (same register count, same ends,
so the stage count and cycle are unchanged; only the sites move off the outline)."""
import json, sys, math
P = json.load(open(sys.argv[1])); out = sys.argv[2]; types = sys.argv[3].split(","); pre = sys.argv[4]
wps = [tuple(float(v) for v in w.split(",")) for w in sys.argv[5].split(";") if w]
for tn in types:
    t = P["partition_types"][tn]
    for s in t.get("internal_stations", []):
        if not str(s.get("conn", "")).startswith(pre):
            continue
        pts = [tuple(s["from_um"])] + wps + [tuple(s["to_um"])]
        seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
        L = sum(seg); n = len(s["regs_um"]); regs = []
        for k in range(1, n + 1):
            d = L * k / (n + 1)
            for (a, b), l in zip(zip(pts, pts[1:]), seg):
                if d <= l + 1e-9:
                    f = d / l if l else 0.0
                    regs.append([round(a[0] + f * (b[0] - a[0]), 3), round(a[1] + f * (b[1] - a[1]), 3)])
                    break
                d -= l
        old = s["regs_um"]; s["regs_um"] = regs
        s["note"] = (s.get("note", "") + " | VL2-H10R1 re-sited off the outline (staircase %s, %.1f um, %d regs kept, stage %.1f um)" % (
            ";".join("%g,%g" % w for w in wps), L, n, L / (n + 1)))
        print(tn, s["conn"][:40], "L %.1f stage %.1f" % (L, L / (n + 1)), old, "->", regs)
json.dump(P, open(out, "w"), indent=1)
