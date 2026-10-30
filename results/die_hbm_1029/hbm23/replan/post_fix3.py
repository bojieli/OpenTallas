#!/usr/bin/env python3
"""DIE-HBM-23 post-fix 3: sub-0.05-um window mismatches between the two sides of a port (MY-mirror rounding of an NE
hop whose other end is a NW/NE-shared type) -> snap the declaration on the NON-shared side to the shared side's die
geometry.  Fails closed on any mismatch larger than TOL or of face/layers.  usage: post_fix3.py TOOLS PLAN_JSON"""
import sys, json
from collections import Counter
sys.path.insert(0, sys.argv[1])
import schema as S, lane_add as LA
TOL = 0.05
plan = sys.argv[2]
raw = json.load(open(plan))
cnt = Counter(p["type"] for p in raw["partitions"])
T = raw["partition_types"]
P = S.Plan(raw)
fixed, bad = [], []
for pid, pr in P.ports.items():
    if pr["src"]["part"] == S.DIE_PART or pr["dst"]["part"] == S.DIE_PART:
        continue
    gs, gd = P.port_geom_from(pr, "src"), P.port_geom_from(pr, "dst")
    if not gs or not gd or (gs[0] == gd[0] and list(gs[1]) == list(gd[1])):
        continue
    if gs[0] != gd[0] or list(gs[2]) != list(gd[2]) or max(abs(a - b) for a, b in zip(gs[1], gd[1])) > TOL:
        bad.append(pid); continue
    ts, td = P.parts[pr["src"]["part"]]["type"], P.parts[pr["dst"]["part"]]["type"]
    if cnt[td] == 1:
        side, ref = "dst", gs
    elif cnt[ts] == 1:
        side, ref = "src", gd
    else:
        bad.append(pid); continue
    part, bus = pr[side]["part"], pr[side]["bus"]
    df = ref[0] if side == "src" else LA.OPP[ref[0]]
    tf, tw, flip = LA.to_type_window(P, part, df, list(ref[1]))
    t = T[P.parts[part]["type"]]
    done = False
    for b in t.get("buses", []):
        if b["name"] == bus:
            b["window_um"] = tw; done = True
    for s_ in t.get("ft_slots", []):
        if bus == s_["name"] + "_i":
            s_["in_window_um"] = tw; done = True
        if bus == s_["name"] + "_o":
            s_["out_window_um"] = tw; done = True
    (fixed if done else bad).append(pid)
json.dump(raw, open(plan, "w"), indent=1)
print("snapped", fixed, "unfixable", bad)
if bad:
    sys.exit(1)
