#!/usr/bin/env python3
"""HBM-HUBMESH-2: split the hub intra kit-contract damage (FF) into mesh skew vs planned early-core-tap offsets.
    contract_split.py PROOF_DIR PLAN [W ...]   (what-if windows -> violation counts)"""
import json, sys, itertools
sys.path.insert(0, sys.argv[0].rsplit("/results/", 1)[0] + "/tools/die_plan")
import die_sta_related as DSR
d, plan_p = sys.argv[1], sys.argv[2]
Ws = [float(x) for x in sys.argv[3:]] or [0, 40, 80, 120, 160, 200, 260]
plan = json.load(open(plan_p))
T = {t["port"]: t for t in json.load(open(f"{d}/tap_arrivals_FF.json"))["taps"]}
ecm = DSR.early_core_map(plan, T, plan_path=plan_p)
off = {p: m[0]["early_ps"]["FF"] for p, m in ecm.items()}
ov = sorted(off.values())
print("early core taps", len(off), "FF earliness min/med/max", ov[0], ov[len(ov)//2], ov[-1], "nonzero", sum(v > 0 for v in ov))
arr = {p: t["late_ps"] for p, t in T.items()}
print("FF arrival spread", round(max(arr.values()) - min(arr.values()), 2))
for lab, ko in (("mesh only (offsets 0)", {}), ("plan offsets (gate)", off)):
    dm = [arr[b] - arr[a] + ko.get(b, 0) - ko.get(a, 0) for a, b in itertools.permutations(arr, 2)]
    print(lab, "max damage", round(max(dm), 2), " violations at W:", {w: sum(x > w for x in dm) for w in Ws})
# delivered-early what-if: core taps delivered exactly at their plan earliness (v2 early branches) -> damage = mesh skew only
