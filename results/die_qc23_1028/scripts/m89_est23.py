"""DIE-QC-23 M8/M9 clock track use inside the A0 array (c_* partitions) from a routed clock-only GRT guide, for the
QC-PG-5 75-um A0 bump field budget (OWNER 10-28 19:58 option c).  Clock = 2W2S NDR: 5 tracks per wire (mk_clkfirst13
obstruction width).  usage: m89_est23.py PLAN GUIDE DBU"""
import json, sys
from collections import defaultdict
plan, guide, dbu = sys.argv[1], sys.argv[2], float(sys.argv[3])
P = json.load(open(plan)); T = P["partition_types"]
box = []
for q in P["partitions"]:
    if q["name"].startswith("c_"):
        w, h = T[q["type"]]["outline_um"]
        if q.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        x, y = q["origin_um"]; box.append((x, y, x + w, y + h))
area = sum((c - a) * (d - b) for a, b, c, d in box)
xs0, ys0 = min(b[0] for b in box), min(b[1] for b in box); xs1, ys1 = max(b[2] for b in box), max(b[3] for b in box)
L = defaultdict(float)
for ln in open(guide):
    p = ln.split()
    if len(p) != 5 or p[4] not in ("M8", "M9"): continue
    x0, y0, x1, y1 = (float(v) / dbu for v in p[:4])
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    if not any(a <= xc <= c and b <= yc <= d for a, b, c, d in box): continue
    L[p[4]] += (x1 - x0) if p[4] == "M8" else (y1 - y0)
PITCH, TR = 0.08, 5
for m in ("M8", "M9"):
    # average track fraction over the array = wire length x 5 tracks x pitch / area
    print(m, "clock wire mm", round(L[m] / 1000, 1), "avg track use %", round(100 * L[m] * TR * PITCH / area, 3))
print("A0 array c_* area mm2", round(area / 1e6, 2), "bbox", (round(xs0), round(ys0), round(xs1), round(ys1)))
