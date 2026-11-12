#!/usr/bin/env python3
"""taptune.py REPO PLAN TYPE [OUT] : kit-split check of clock.added_taps (taps.grid_explicit_taps = the bind kit-rtl
rule: each added tap non-empty, <= cap, radius <= 1.10 x tap_radius_um).  With OUT: coordinate search (8.64 lattice,
+-216 um) of each added tap minimising (failures, max added radius), legality by grid_explicit_sites; writes OUT."""
import json, sys, time, copy
from pathlib import Path
repo = Path(sys.argv[1]); sys.path.insert(0, str(repo / "tools/die_plan"))
import schema, taps
path, tn = sys.argv[2], sys.argv[3]; out = sys.argv[4] if len(sys.argv) > 4 else None
P = schema.Plan(schema.load(path), path)
ck = P.types[tn]["clock"]
n_grid = len(schema._grid_taps(P, tn))
cap = int(ck.get("tap_max_sinks", 1500)); radius = float(ck.get("tap_radius_um", 200.))
sinks = taps.sink_sites(P, tn)
import reset_tree as RT
sinks = sinks + [(float(r["xy"][0]), float(r["xy"][1]), 1.0) for r in RT.for_type(P, tn).get("relays", [])]
def score():
    try:
        sites = taps.grid_explicit_sites(P, tn)
    except ValueError:
        return (99, 1e9, None)
    load, far, _ = taps.assign(sites, sinks, cap, radius, max_distance_um=radius)
    bad = 0; mx = 0.
    for i, (n, r) in enumerate(zip(load, far)):
        if i >= n_grid:
            if n > cap or n == 0 or r > radius * 1.10 + 1e-6: bad += 1
            mx = max(mx, r if n else 1e6)
    return (bad, mx, [(sites[i][0], sites[i][1], sites[i][2], load[i], round(far[i], 1)) for i in range(n_grid, len(sites))])
t = time.time(); s = score(); print("now", s[0], round(s[1], 1), s[2], "eval %.1fs" % (time.time() - t))
if out:
    for rnd in range(2):
        hot = {n for n, x, y, l, r in (s[2] or []) if l == 0 or l > cap or r > radius}
        if not hot: break
        for p in [q for q in ck["added_taps"] if q["name"] in hot]:
            x0, y0 = map(float, p["xy"]); best = (s[0], s[1], x0, y0)
            for i in range(-25, 26, 2):
                for j in range(-25, 26, 2):
                    p["xy"] = [round(x0 + 8.64 * i, 2), round(y0 + 8.64 * j, 2)]
                    r = score()
                    if (r[0], r[1]) < best[:2]: best = (r[0], r[1], p["xy"][0], p["xy"][1])
            p["xy"] = [best[2], best[3]]; s = score()
            print("round", rnd, p["name"], p["xy"], s[0], round(s[1], 1))
        if s[0] == 0 and s[1] <= radius: break
    print("final", s[2])
    raw = json.load(open(path))
    raw["partition_types"][tn]["clock"]["added_taps"] = copy.deepcopy(ck["added_taps"])
    json.dump(raw, open(out, "w"), indent=1)
