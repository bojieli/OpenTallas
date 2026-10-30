#!/usr/bin/env python3
"""DIE-HEAD-34 (2026-10-29): why hd_tile clock.tap_mode density r200 fails closed, and the smallest local fix.
usage: tile_tap_dead_zone.py PLAN_JSON (sink_bins_file resolvable)  -> prints uncoverable sinks + density_taps on
the plan as-is and with u_eA1 shifted -4.32 um (one macro lattice step).  Read-only estimate, writes tile_dense_eA1m432.json."""
import sys, json, collections
sys.path.insert(0, sys.argv[2] if len(sys.argv) > 2 else "tools/die_plan")
import schema, taps
def plan(d): return schema.Plan(d)
def uncoverable(P, tn="hd_tile", r=200.0, c=8.64, step=1.08):
    t = P.types[tn]; w, h = t["outline_um"]
    bb = list(schema.placed_macro_boxes(t, halo=schema.TAP_CLEAR_UM).values())
    xs = [round(c + i*step, 4) for i in range(int((w-2*c)/step)+1)]
    ys = [round(c + i*step, 4) for i in range(int((h-2*c)/step)+1)]
    leg = [(x, y) for x in xs for y in ys if not any(x0 < x < x1 and y0 < y < y1 for x0, y0, x1, y1 in bb)]
    g = collections.defaultdict(list)
    for x, y in leg: g[(int(x//50), int(y//50))].append((x, y))
    bad = []
    for p in taps.sink_sites(P, tn, True):
        gx, gy = int(p[0]//50), int(p[1]//50)
        best = min([abs(p[0]-x)+abs(p[1]-y) for i in range(gx-5, gx+6) for j in range(gy-5, gy+6) for x, y in g.get((i, j), ())] or [1e9])
        if best > r: bad.append((round(p[0], 1), round(p[1], 1), round(best, 1), p[2] if len(p) > 2 else 1))
    return bb, bad
d = json.load(open(sys.argv[1]))
for tag in ("as_is", "eA1_m4.32"):
    if tag != "as_is":
        for hc in d["partition_types"]["hd_tile"]["hard_cores"]:
            if (hc.get("inst") or hc.get("name")).endswith("u_eA1"): hc["origin_um"][0] = round(hc["origin_um"][0]-4.32, 4)
        json.dump(d, open("tile_dense_eA1m432.json", "w"))
    P = plan(d); bb, bad = uncoverable(P)
    try:
        r = taps.density_taps(P, "hd_tile"); v = f"PASS taps {len(r)} max load {max(x[3] for x in r)} max r {max(x[4] for x in r)}"
    except Exception as e: v = f"FAIL {e}"
    print(tag, "eA1 box+halo", [round(v, 3) for v in bb[1]], "uncoverable", bad, "| density_taps", v)
