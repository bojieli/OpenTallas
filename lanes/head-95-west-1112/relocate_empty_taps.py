#!/usr/bin/env python3
"""relocate_empty_taps.py REPO SIDEROOT PLAN OUT TYPE : an explicit tap that taps.explicit_taps reports EMPTY (load 0) is
moved (name kept, tap order kept) onto the sink farthest from its tap inside the most-loaded tap's cluster, so it splits
that cluster; candidates tried farthest-first until the type's explicit taps load.  Deterministic."""
import json, math, re, sys
from pathlib import Path
repo, side, plan, out, tn = sys.argv[1:6]
sys.path.insert(0, repo + "/tools/die_plan")
import schema as S, taps as TP
TP._root = lambda: Path(side)
P = json.load(open(plan))
for it in range(10):
    Pl = S.Plan(P, plan)
    try:
        TP.explicit_taps(Pl, tn); print("taps load OK after", it, "moves"); break
    except ValueError as e:
        m = re.search(r"explicit tap (\S+) load=0/", str(e))
        if not m: print("UNHANDLED", e); sys.exit(2)
        empty = m.group(1)
    ck = P["partition_types"][tn]["clock"]
    sites = TP.explicit_tap_sites(Pl, tn)
    sinks = TP.sink_sites(Pl, tn)
    cap = int(ck.get("tap_max_sinks", 1500)); radius = float(ck.get("tap_radius_um", 200.))
    load, far, asg = TP.assign(sites, sinks, cap, radius, max_distance_um=radius)
    heavy = max(range(len(sites)), key=lambda i: load[i])
    hx, hy = sites[heavy][1], sites[heavy][2]
    pts = []
    for s, a in zip(sinks, asg if isinstance(asg, list) and len(asg) == len(sinks) else [None] * len(sinks)):
        xy = s[:2]
        try:
            x, y = float(xy[0]), float(xy[1])
        except Exception:
            continue
        if a is None or a == heavy or (isinstance(a, (list, tuple)) and heavy in a):
            pts.append((abs(x - hx) + abs(y - hy), x, y))
    pts.sort(reverse=True)
    done = False
    for d, x, y in pts[:200]:
        for t in ck["taps"]:
            if t["name"] == empty: old = t["xy"]; t["xy"] = [round(x, 3), round(y, 3)]
        try:
            TP.explicit_tap_sites(S.Plan(P, plan), tn)
            print(f"MOVE {tn} {empty} {old} -> {[round(x, 3), round(y, 3)]} (splits {sites[heavy][0]} load {load[heavy]})"); done = True; break
        except ValueError:
            for t in ck["taps"]:
                if t["name"] == empty: t["xy"] = old
    if not done: print("NO LEGAL SITE for", empty); sys.exit(3)
json.dump(P, open(out, "w"), indent=1)
