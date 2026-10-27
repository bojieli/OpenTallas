"""KV-PLAN-DELTA-3 hm_r26q5 part (d) D-KV-PG-G12 (COORD 12:35 PG-GRID-AUDIT one-grid ruling (2)): plan die.pg.grid = the grid
the measured-activity IR passed on (PG-ACTIVITY-KVHBM 48f939873f, 27.9 mV = 21.8 above M7 + 6.05 below, 150-um bumps /
70-um pads) = HEAD-5 G12: M8 0.48 @ 4.32 (offset 2.16), M9 12.96 @ 34.56 (offset 17.28), VDD/VSS, exactly as in
s81_head die_plan e5f4fb2cd1 (plan 33029005).  Was PL 0.48 @ 8.64 both layers (67.4 mV FAIL, PG-GRID-AUDIT).
PHY domain grids (die.pg.domains) unchanged.  Nothing else changes (asserted).
    q5_pg.py PLAN_IN PLAN_OUT"""
import json, sys, copy
pin_, pout = sys.argv[1:3]
P = json.load(open(pin_)); q = copy.deepcopy(P)
G = [dict(layer="M8", width_um=0.48, pitch_um=4.32, offset_um=2.16, nets=["VDD", "VSS"]),
     dict(layer="M9", width_um=12.96, pitch_um=34.56, offset_um=17.28, nets=["VDD", "VSS"])]
old = P["die"]["pg"]["grid"]; assert [g["layer"] for g in old] == ["M8", "M9"]
P["die"]["pg"]["grid"] = G
GN = ("hm_r26q5 D-KV-PG-G12 (COORD 12:35 one-grid ruling): = IR-checked grid (PG-ACTIVITY-KVHBM 27.9 mV, "
                               "150-um bumps/70-um pads, measured activity); was 0.48@8.64 M8/M9 (67.4 mV FAIL)")
q["die"]["pg"]["grid"] = G
assert P == q
P["note"] = P.get("note", "") + " | " + GN
open(pout, "w").write(json.dumps(P, indent=1) + "\n")
print("old", old); print("new", G)
