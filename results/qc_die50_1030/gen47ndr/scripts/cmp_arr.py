#!/usr/bin/env python3
"""DIE-QC-50/gen47ndr: compare two tap_arrivals json (A = GRT-NDR estimate, B = mixed DRT+RCX) per tap / region.
usage: cmp_arr.py A.json B.json REGION[,REGION..] [PAIR launch:capture ...]"""
import json, sys
A = {t["port"]: t for t in json.load(open(sys.argv[1]))["taps"]}
B = {t["port"]: t for t in json.load(open(sys.argv[2]))["taps"]}
regs = sys.argv[3].split(",")
out = {"changed_outside_regions": 0, "max_abs_delta_outside_ps": 0.0, "regions": {}, "pairs": []}
for p, a in A.items():
    d = B[p]["late_ps"] - a["late_ps"]
    if a["cppr_node"] in regs:
        r = out["regions"].setdefault(a["cppr_node"], {"n": 0, "dmin": 1e9, "dmax": -1e9})
        r["n"] += 1; r["dmin"] = round(min(r["dmin"], d), 2); r["dmax"] = round(max(r["dmax"], d), 2)
    elif abs(d) > 0.01:
        out["changed_outside_regions"] += 1; out["max_abs_delta_outside_ps"] = round(max(out["max_abs_delta_outside_ps"], abs(d)), 2)
for r in regs:
    L = [t["late_ps"] for t in B.values() if t["cppr_node"] == r]; La = [t["late_ps"] for t in A.values() if t["cppr_node"] == r]
    if L: out["regions"][r].update(spread_B=round(max(L) - min(L), 2), spread_A=round(max(La) - min(La), 2))
for pr in sys.argv[4:]:
    l, c = pr.split(":")
    out["pairs"].append(dict(launch=l, capture=c, A_launch_minus_capture=round(A[l]["late_ps"] - A[c]["early_ps"], 2),
                             B_launch_minus_capture=round(B[l]["late_ps"] - B[c]["early_ps"], 2),
                             A_late=(round(A[l]["late_ps"], 2), round(A[c]["late_ps"], 2)), B_late=(round(B[l]["late_ps"], 2), round(B[c]["late_ps"], 2))))
print(json.dumps(out, indent=1))
