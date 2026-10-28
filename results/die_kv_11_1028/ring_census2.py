#!/usr/bin/env python3
"""DIE-KV-11 step 2: ring (W,D) census for the local-form depth set (ESTIMATE).  Depth per CA port from the re-tree
cap reading (count_align_plan via locality.cap_reading, clk_aocv table + droop + spice, fork start ports) instead of
the bind's ring_depth.  Classes = DIE-KV-10 global rounded-up width buckets (COORD 07:43 accepted), W>=250 hardened.
usage: ring_census2.py BIND_CLOCK_LANDINGS PLAN RING_AREA PV_COUNTS OUT NAME=ROWS.json ..."""
import json, sys, collections
B, PLAN, AREA, PVC, OUT = sys.argv[1:6]
runs = dict(a.split("=", 1) for a in sys.argv[6:])
L = json.load(open(B)); P = json.load(open(PLAN)); area = json.load(open(AREA)); pvc = json.load(open(PVC))
BUCK = [300, 416, 573, 672, 800, 909, 1119, 1560]
fit = {}
for D in (4, 8):
    pts = [(int(k[9:].split("d")[0]), v["cells"]) for k, v in area.items() if k.endswith(f"d{D}")]
    n = len(pts); mx = sum(x for x, _ in pts) / n; my = sum(y for _, y in pts) / n
    b = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts); fit[D] = (my - b * mx, b)
cells = lambda W, D: fit[D][0] + fit[D][1] * W
ptype = {p["name"]: p["type"] for p in P["partitions"]}
res = dict(fit=fit, scenarios={})
for name, f in [("now", None)] + list(runs.items()):
    dep = None if f is None else {str(r["id"]): r["depth"] for r in json.load(open(f))["rows"]}
    rings = []; miss = 0
    for r in L["ports"]:
        d = int(r["ring_depth"]) if dep is None else dep.get(str(r["port"]))
        if d is None: miss += 1; d = 8
        rings.append(dict(W=int(r["width"]), D=int(d), dst=r["dst"]))
    mix = collections.Counter(f"D{x['D']}" for x in rings)
    exact = collections.Counter((x["W"], x["D"]) for x in rings if x["W"] >= 250)
    buck = collections.Counter((next(b for b in BUCK if b >= x["W"] + 1), x["D"]) for x in rings if x["W"] >= 250)
    waste = sum((next(b for b in BUCK if b >= x["W"] + 1) - x["W"] - 1) * fit[x["D"]][1] for x in rings if x["W"] >= 250)
    tot = sum((x["W"] + 1) * fit[x["D"]][1] for x in rings if x["W"] >= 250)
    ring_cells = sum(cells(x["W"], x["D"]) for x in rings)
    res["scenarios"][name] = dict(rings=len(rings), unmatched=miss, depth_mix=dict(mix), exact_classes_w250=len(exact),
                                  bucket_classes_w250=len(buck), bucket_list=sorted("%dd%dx%d" % (b, d, n) for (b, d), n in buck.items()),
                                  pad_pct=round(100 * waste / tot, 1), ring_cells_total=round(ring_cells),
                                  d8_rings=mix.get("D8", 0))
    print(name, {k: v for k, v in res["scenarios"][name].items() if k != "bucket_list"})
json.dump(res, open(OUT, "w"), indent=1, default=str)
