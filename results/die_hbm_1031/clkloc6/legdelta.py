#!/usr/bin/env python3
"""per-leg routed vs model delay along tap paths of a region: finds the legs whose routed delay exceeds the model.
usage: legdelta.py RUN_DIR REGION PART [N]"""
import json, sys
from collections import defaultdict
D, REG, PART = sys.argv[1:4]; NSHOW = int(sys.argv[4]) if len(sys.argv) > 4 else 25
t = json.load(open(f"{D}/k1/kit/clock/tree.json")); N = {int(k): v for k, v in t["nodes"].items()}
P = json.load(open(f"{D}/proof/tap_arrivals_TT.json")); NL = P["node_late_ps"]
tp = {x["port"]: x for x in P["taps"] if x["part"] == PART}
root = [k for k, n in N.items() if n.get("region_root") == REG][0]
ex = {}
for x in t["taps"]:
    if x["part"] != PART: continue
    path = tp[x["port"]]["tree_path"]; cells = x["path"]
    if len(cells) != len(path): raise SystemExit(f"path len {len(cells)} vs {len(path)}")
    pos = {c: i for i, c in enumerate(cells)}
    ch = []; k = x["node"]
    while k is not None:
        ch.append(k); k = N[k]["parent"]
    ch.reverse()
    if root not in ch: continue
    for i in range(ch.index(root) + 1, len(ch)):
        k, kp = ch[i], ch[i - 1]
        ia, ib = pos.get(f"b{kp}"), pos.get(f"b{k}")
        if ia is None or ib is None: continue
        pa, pb = path[:ia + 1], path[:ib + 1]
        if pa in NL and pb in NL:
            m = (N[k].get("physical_leg") or {}).get("delay_ps")
            if m is None: continue
            ex[k] = (NL[pb] - NL[pa], m, N[kp]["x"], N[kp]["y"], N[k]["x"], N[k]["y"], (N[k].get("physical_leg") or {}).get("wire_um"))
rows = sorted(ex.items(), key=lambda kv: -(kv[1][0] - kv[1][1]))
print("legs", len(ex))
for k, (r, m, x0, y0, x1, y1, w) in rows[:NSHOW]:
    print(f"node {k:6d} ({x0:8.1f},{y0:8.1f})->({x1:8.1f},{y1:8.1f}) wire {w} routed {r:7.1f} model {m:7.1f} excess {r-m:+7.1f}")
