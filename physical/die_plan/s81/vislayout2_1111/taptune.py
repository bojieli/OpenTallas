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
_W, _H = P.types[tn]["outline_um"]; _CL = schema.TAP_CLEAR_UM
from placement_obstacles import placement_boxes
_BOX = list(placement_boxes(P.types[tn], halo=_CL).values())
_GRID = [(x, y) for _, x, y in schema._grid_taps(P, tn)]
def illegal_taps():
    """added taps that fail the grid_explicit_sites legality alone (outline / halo / spacing to the grid and earlier taps)"""
    eps = 1e-8; taken = list(_GRID); bad = set()
    for p in ck.get("added_taps") or []:
        x, y = map(float, p["xy"])
        if not (_CL - eps <= x <= _W - _CL + eps and _CL - eps <= y <= _H - _CL + eps
                and not any(abs(x - a) < _CL - eps and abs(y - b) < _CL - eps for a, b in taken)
                and not any(a + eps < x < c - eps and b + eps < y < d - eps for a, b, c, d in _BOX)):
            bad.add(p["name"])
        taken.append((x, y))
    return bad
# pre-pass: an added tap that fails legality alone (a moved macro now covers it) goes to the nearest legal 4.32-grid site
for p in ck.get("added_taps") or []:
    if p["name"] in illegal_taps():
        x0, y0 = map(float, p["xy"]); best = None
        for i in range(-70, 71):
            for j in range(-70, 71):
                d = abs(i) + abs(j)
                if best is not None and d >= best[0]: continue
                p["xy"] = [round(x0 + 4.32 * i, 3), round(y0 + 4.32 * j, 3)]
                if p["name"] not in illegal_taps(): best = (d, p["xy"])
        p["xy"] = best[1] if best else [x0, y0]
        print("legalise", p["name"], [x0, y0], "->", p["xy"])
if out and sys.argv[5:] == ["L"]:                     # legalise-only pass (every type first: sinks read all types' taps)
    raw = json.load(open(path)); raw["partition_types"][tn]["clock"]["added_taps"] = copy.deepcopy(ck["added_taps"])
    json.dump(raw, open(out, "w"), indent=1); sys.exit(0)
sinks = taps.sink_sites(P, tn)
import reset_tree as RT
sinks = sinks + [(float(r["xy"][0]), float(r["xy"][1]), 1.0) for r in RT.for_type(P, tn).get("relays", [])]
def score():
    try:
        sites = taps.grid_explicit_sites(P, tn)
    except ValueError:
        return (50 + len(illegal_taps()), 1e9, None)
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
        hot = {n for n, x, y, l, r in (s[2] or []) if l == 0 or l > cap or r > radius} | illegal_taps()
        if not hot: break
        for p in [q for q in ck["added_taps"] if q["name"] in hot]:
            x0, y0 = map(float, p["xy"]); best = (s[0], s[1], x0, y0)
            R = 25 if p["name"] not in illegal_taps() else 41
            for i in range(-R, R + 1, 2):
                for j in range(-R, R + 1, 2):
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
