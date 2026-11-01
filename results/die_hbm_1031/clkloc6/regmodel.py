#!/usr/bin/env python3
"""model (sum physical_leg delay_ps) vs routed arrival for the taps of one region. usage: regmodel.py RUN_DIR REGION PART"""
import json, sys
D, REG, PART = sys.argv[1:4]
t = json.load(open(f"{D}/k1/kit/clock/tree.json")); N = {int(k): v for k, v in t["nodes"].items()}
root = [k for k, n in N.items() if n.get("region_root") == REG][0]
P = json.load(open(f"{D}/proof/tap_arrivals_TT.json"))
arr = {x["port"]: x["late_ps"] for x in P["taps"] if x["part"] == PART}
base = P["node_late_ps"][REG]
# taps: node.taps entries
tapnode = {x["port"]: x["node"] for x in t["taps"]}
def model(k):
    s = 0.0
    while k != root and k is not None:
        s += (N[k].get("physical_leg") or {}).get("delay_ps", 0.0); k = N[k]["parent"]
    return s if k == root else None
rows = []
for p, a in arr.items():
    nm = p.split("__", 1)[1] if "__" in p else p
    k = tapnode.get(nm) or tapnode.get(p)
    if k is None: continue
    m = model(k)
    if m is None: continue
    rows.append((p, N[k]["x"], N[k]["y"], m, a - base))
print("taps", len(arr), "matched", len(rows), "root", root, N[root]["x"], N[root]["y"])
rows.sort(key=lambda r: r[2])
for r in rows[::max(1, len(rows)//40)]:
    print(f"{r[0]:28s} {r[1]:9.1f} {r[2]:9.1f} model {r[3]:7.1f} routed {r[4]:7.1f} d {r[4]-r[3]:+6.1f}")
import statistics
print("model spread", round(max(r[3] for r in rows)-min(r[3] for r in rows),1), "routed spread", round(max(r[4] for r in rows)-min(r[4] for r in rows),1))
