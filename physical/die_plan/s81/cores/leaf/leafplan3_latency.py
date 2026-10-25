#!/usr/bin/env python3
"""S81/LEAFPLAN3: re-price the die latency table for the lanes whose leaf ft stations changed (G0 'latency' findings
'lane X: table says A cycles, plan gives B'): cycles / stations / natural += B - A; writes the delta table.
usage: lat.py PLAN G0_REPORT OUT_PLAN DELTA_JSON"""
import json
import re
import sys

P = json.load(open(sys.argv[1]))
R = json.load(open(sys.argv[2]))
d = {}
for f in R["findings"]:
    if f.get("check") == "latency" and f.get("level") == "ERROR":
        m = re.search(r"table says (\d+) cycles, plan gives (\d+)", f["msg"])
        d[f["lane"]] = (int(m.group(1)), int(m.group(2)))
for ln, (a, b) in d.items():
    e = P["latency"]["lanes"][ln]
    for k in ("cycles", "stations", "natural"):
        e[k] += b - a
json.dump(P, open(sys.argv[3], "w"), indent=0)
json.dump(dict(lanes=len(d), net_cycles=sum(b - a for a, b in d.values()),
               max_added=max([b - a for a, b in d.values()] or [0]), min_added=min([b - a for a, b in d.values()] or [0]),
               rows={k: dict(old=a, new=b) for k, (a, b) in sorted(d.items())}), open(sys.argv[4], "w"), indent=1)
print(len(d), sum(b - a for a, b in d.values()))
