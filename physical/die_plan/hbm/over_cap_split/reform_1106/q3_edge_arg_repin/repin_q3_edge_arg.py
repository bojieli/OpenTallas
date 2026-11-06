#!/usr/bin/env python3
"""HBM-GAPS-8 11-06 (DIE-HBM-81 plan-owner ruling 13:3x): same-slot re-pin of ot_hfd_coll_q3_edge_arg (276.48 x 43.2).
Cause: 548 S/M5 pins packed into x 138.3-275.5 + 425 E/M4 pins on the 43.2-um edge -> GRT-0232 corner overflow (vA+vB).
Rule: S-face M5 pins (y = 0.096) spread evenly over x 8.64-267.84 on M5 tracks ((n+0.5)*0.048), bit order (sorted by
old x, then name) kept; E-face M4 pins stay on E (already at the legal 0.096 pitch over the full edge: unchanged);
every other pin (interior) unchanged.  Deterministic: output depends only on the input table.
usage: repin_q3_edge_arg.py IN.json OUT.json"""
import json, sys
T = 0.048
src = json.load(open(sys.argv[1]))
S = sorted([p for p in src if p["layer"] == "M5" and abs(p["y"] - 0.096) < 1e-6], key=lambda p: (p["x"], p["name"]))
x0, x1 = 8.64, 267.84
n = len(S); step = (x1 - x0) / (n - 1)
new = {}
prev = None
for i, p in enumerate(S):
    k = round((x0 + i * step) / T - 0.5)
    if prev is not None and k <= prev: k = prev + 2
    new[p["name"]] = round((k + 0.5) * T, 3); prev = k
assert len(set(new.values())) == n and max(new.values()) <= 276.48 - 4.32
out = [dict(p, x=new[p["name"]]) if p["name"] in new else dict(p) for p in src]
json.dump(out, open(sys.argv[2], "w"))
open(sys.argv[2], "a").write("\n")
print(f"REPIN S/M5 {n} pins x {min(new.values())}-{max(new.values())} (step {step:.4f}); unchanged {len(src)-n}")
