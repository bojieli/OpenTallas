#!/usr/bin/env python3
"""HUBMESH-6: per-tap compensated FF arrival c = arr + plan_earliness; show extremes by class."""
import json, sys
sys.path.insert(0, sys.argv[0].rsplit("/results/", 1)[0] + "/tools/die_plan") if "/results/" in sys.argv[0] else None
W = "/srv/opentallas-scratch2/claude/wt/hbm-hubmesh-6"
sys.path.insert(0, W + "/tools/die_plan")
import die_sta_related as DSR
d, plan_p = sys.argv[1], sys.argv[2]
plan = json.load(open(plan_p))
T = {t["port"]: t for t in json.load(open(f"{d}/tap_arrivals_FF.json"))["taps"]}
ecm = DSR.early_core_map(plan, T, plan_path=plan_p)
off = {p: m[0]["early_ps"]["FF"] for p, m in ecm.items()}
rows = []
for p, t in T.items():
    cls = "early_sub" if t.get("early_subtree") else ("core_off" if off.get(p, 0) > 0 else ("core0" if p in off else "mesh"))
    rows.append((t["late_ps"] + off.get(p, 0), t["late_ps"], off.get(p, 0), cls, p, t.get("xy_um")))
rows.sort()
import collections
by = collections.defaultdict(list)
for r in rows: by[r[3]].append(r[0])
for k, v in by.items(): print(f"{k:10s} n={len(v):4d} comp min {min(v):8.1f} max {max(v):8.1f}")
print("LOW 12"); [print(f"  {r[0]:8.1f} arr {r[1]:8.1f} off {r[2]:6.1f} {r[3]:9s} {r[4]} {r[5]}") for r in rows[:12]]
print("HIGH 12"); [print(f"  {r[0]:8.1f} arr {r[1]:8.1f} off {r[2]:6.1f} {r[3]:9s} {r[4]} {r[5]}") for r in rows[-12:]]
# taps with nonzero offset not delivered by early sub-tree
und = [r for r in rows if r[2] > 0 and r[3] != "early_sub"]
print("undelivered early (off>0, mesh-fed):", len(und), "offs", sorted(round(r[2],1) for r in und))
print("delivered early sub:", sorted(round(r[2],1) for r in rows if r[3]=="early_sub"))
