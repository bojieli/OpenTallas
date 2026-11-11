#!/usr/bin/env python3
"""CPL-S81-SLICE: added-tap load/radius of one type on a plan (kit rule taps.grid_explicit_taps, no stop).
usage: tapdbg.py PLAN TYPE"""
import os
import sys
from pathlib import Path
REPO = Path(os.environ.get("CPL_REPO", "/srv/opentallas-scratch3/claude/cpl-s81-slice/repo"))
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
import schema as S  # noqa: E402
import taps as TP  # noqa: E402
P = S.Plan(S.load(sys.argv[1]), Path(sys.argv[1]))
tn = sys.argv[2]
ck = P.types[tn]["clock"]
print("mode", ck.get("tap_mode"), "cap", ck.get("tap_max_sinks"), "radius", ck.get("tap_radius_um"), "added", ck.get("added_taps"))
out = TP.grid_explicit_sites(P, tn)
sinks = TP.sink_sites(P, tn)
cap = int(ck.get("tap_max_sinks", 1500)); radius = float(ck.get("tap_radius_um", 200.))
load, far, asg = TP.assign(out, sinks, cap, radius, max_distance_um=radius)
n_grid = len(S._grid_taps(P, tn))
print("sinks", len(sinks), "sum w", sum(s[2] for s in sinks))
for i, ((n, x, y), l, r) in enumerate(zip(out, load, far)):
    print(("ADDED " if i >= n_grid else "grid  ") + n, round(x, 2), round(y, 2), "load", l, "far", round(r, 1))
