"""face occupancy (die-frame windows from schema.port_segments) of a partition per die face; usage: TOOLS PLAN PART..."""
import json, sys
sys.path.insert(0, sys.argv[1])
import schema as S, lane_add as LA
from collections import defaultdict
raw = json.load(open(sys.argv[2])); P = S.Plan(raw)
for part in sys.argv[3:]:
    x0, y0, x1, y1 = P.rect(part)
    for df in "NSEW":
        occ = LA.face_intervals(P, part, df)
        lo, hi = (x0, x1) if df in "NS" else (y0, y1)
        used = sum(b - a for a, b in occ)
        gaps = sorted(LA.free_gaps(lo, hi, occ, 2.0), key=lambda g: g[0] - g[1])
        # partner edges
        nb = []
        for q in P.parts:
            if q == part: continue
            e = LA.shared_edge(P, part, q)
            if e and e[0] == df:
                eo = [w for w in occ if w[0] < e[2] and w[1] > e[1]]
                fg = LA.free_gaps(e[1], e[2], occ, 2.0)
                nb.append((q, round(e[2] - e[1]), round(sum(min(b, e[2]) - max(a, e[1]) for a, b in eo)), round(max([b - a for a, b in fg] or [0]))))
        print(part, df, "len", round(hi - lo), "used", round(used), "ports", len(occ), "biggest gaps", [(round(a), round(b - a)) for a, b in gaps[:4]])
        for n in nb: print("    edge with %-10s len %6d used %6d maxfree %6d" % n)
