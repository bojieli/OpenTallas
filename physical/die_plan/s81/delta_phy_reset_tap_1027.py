#!/usr/bin/env python3
"""S81 plan event 2026-10-27 (DIE-S81, base G0C error 13/13 "reset wavefront: phy_hbm IN 788.4 um").

Why: phy__t1 (hard HBM3E PHY slot, 8657.28 x 1226.88, S die edge) has no reset.tap_um, so reset_tree places its
arst_n at the outline centre (15975.33, 725.79 die).  Its only reset neighbour is svc_6.rst_o_0 at (15967.20, 1506.02):
hop 788.4 um > 405 (G0C ERROR, owner rule relay every <= 405 um).
Fix (the remedy the check names): reset.tap_um on the N face toward that neighbour: local (4320.00, 1226.88)
= die (15966.72, 1330.56), on the 8.64 lattice, hop = 0.48 + 175.46 = 175.9 um.  No other field changes; the
clock tap (centre, M9) is unchanged; the PHY macro view must expose arst_n there (plan pin, hard view regenerated).
  python3 physical/die_plan/s81/delta_phy_reset_tap_1027.py [--check]
"""
import argparse, json, sys
PLAN = "physical/die_plan/s81/die_plan.json"
TAP = [4320.0, 1226.88]
ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
raw = json.load(open(PLAN))
t = raw["partition_types"]["phy__t1"]
cur = (t.get("reset") or {}).get("tap_um")
if a.check:
    print("phy__t1 reset.tap_um", cur, "OK" if cur == TAP else "NOT APPLIED"); sys.exit(0 if cur == TAP else 1)
# textual edit (the plan file uses a mixed compact/indented layout; keep every other byte)
txt = open(PLAN).read()
k = txt.index('  "phy__t1": {')
old = '   "reset": {\n    "sync_stages": 2\n   },'
j = txt.index(old, k)
assert j < txt.index('"note": "phy partition', k)
new = '   "reset": {\n    "sync_stages": 2,\n    "tap_um": [\n     %s,\n     %s\n    ]\n   },' % (TAP[0], TAP[1])
txt = txt[:j] + new + txt[j + len(old):]
assert json.loads(txt)["partition_types"]["phy__t1"]["reset"]["tap_um"] == TAP
open(PLAN, "w").write(txt)
print("applied phy__t1 reset.tap_um", TAP)
