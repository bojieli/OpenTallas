#!/usr/bin/env python3
"""tile_stats.py DUMP.json -> pin-face crowding / channel / fill numbers for a layout_dump.tcl dump."""
import json, sys, collections

d = json.load(open(sys.argv[1]))
x0, y0, x1, y1 = d["die"]
W, H = x1 - x0, y1 - y0
faces = {"N": W, "S": W, "E": H, "W": H}
cnt = collections.Counter(); lay = collections.defaultdict(collections.Counter); span = collections.defaultdict(list)
buses = collections.defaultdict(collections.Counter)
for name, L, a, b, c, e in d.get("pins", []):
    cx, cy = (a + c) / 2, (b + e) / 2
    dist = {"W": cx - x0, "E": x1 - cx, "S": cy - y0, "N": y1 - cy}
    f = min(dist, key=dist.get)
    if dist[f] > 5:
        f = "INTERIOR"
    cnt[f] += 1; lay[f][L] += 1
    span[f].append(cx if f in "NS" else cy)
    buses[name.split("[")[0]][f] += 1
out = {"top": d.get("top"), "die_um": [round(W, 1), round(H, 1)], "stats": d.get("stats"),
       "n_blocks": len(d.get("blocks", [])), "n_pins": sum(cnt.values()), "faces": {}}
for f, n in cnt.items():
    s = sorted(span[f]); used = (s[-1] - s[0]) if len(s) > 1 else 0
    L = faces.get(f)
    out["faces"][f] = {"pins": n, "layers": dict(lay[f]), "used_span_um": round(used, 1),
                       "face_um": round(L, 1) if L else None,
                       "pins_per_um_used": round(n / used, 2) if used else None,
                       "span_frac": round(used / L, 2) if L else None}
# macro-to-macro and macro-to-edge gaps < 20 um (slivers)
bl = d.get("blocks", []); sl = []
for i, (n1, m1, a1, b1, c1, e1) in enumerate(bl):
    for f, g in (("W", a1 - x0), ("E", x1 - c1), ("S", b1 - y0), ("N", y1 - e1)):
        if 0.5 < g < 20: sl.append([n1, "edge" + f, round(g, 2)])
    for n2, m2, a2, b2, c2, e2 in bl[i + 1:]:
        ov_y = min(e1, e2) - max(b1, b2); ov_x = min(c1, c2) - max(a1, a2)
        if ov_y > 5:
            g = max(a2 - c1, a1 - c2)
            if 0.5 < g < 20: sl.append([n1, n2, round(g, 2)])
        if ov_x > 5:
            g = max(b2 - e1, b1 - e2)
            if 0.5 < g < 20: sl.append([n1, n2, round(g, 2)])
out["slivers_lt20um"] = sl[:40]; out["n_slivers"] = len(sl)
g = [v for v in d.get("density", {}).get("grid", []) if v is not None]
if g:
    g.sort(); out["density"] = {"bins": len(g), "max": g[-1], "p90": g[int(0.9 * len(g))], "frac_empty_lt0.05": round(sum(v < 0.05 for v in g) / len(g), 2),
                                "frac_hot_gt0.85": round(sum(v > 0.85 for v in g) / len(g), 3)}
out["top_buses"] = sorted(((k, dict(v)) for k, v in buses.items()), key=lambda kv: -sum(kv[1].values()))[:12]
print(json.dumps(out, indent=1))
