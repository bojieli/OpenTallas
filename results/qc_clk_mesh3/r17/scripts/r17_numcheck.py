#!/usr/bin/env python3
"""INFRA-FIRST-QC-R17 NUMBER-CHECK (independent of qc_clk_mesh3 sta-export / die_sta_related): kit-contract FF hold with the
F4G RP1 + VMR core views, recomputed from the nominal FF solve tap arrivals (FF_s000.json) + the plan hard-core modules,
over every port-connected partition pair of the plan AND every pair_unc seam row, both directions.
damage(a -> b) = late(b) - early(a); late/early = nominal + (core range of the partition vs the declared 202.5 FF)
Also: nominal tap skew TT / FF from the s000 solves; worst seam TT setup bound as 833.333 - 60 - ... is NOT recomputed.
Usage: r17_numcheck.py RUN_DIR PLAN"""
import json
import sys
from pathlib import Path

d, plan_p = Path(sys.argv[1]), sys.argv[2]
VIEWS = {"qfd_dv_s8_crh_rp1": (181.9, 203.8), "qfd_dv_s8x_vmr": (194.06, 206.66)}   # FF early, late (F4G RCX / VMR GRT)
DECL = 202.5
plan = json.loads(Path(plan_p).read_text())
types = plan["partition_types"]
ptype = {p["name"]: p["type"] for p in plan["partitions"]}
ff = json.loads((d / "FF_s000.json").read_text())["tap_arr_ps"]
tt = json.loads((d / "TT_s000.json").read_text())["tap_arr_ps"]
rng = {}
for p, t in ptype.items():
    mods = [hc.get("module") for hc in types[t].get("hard_cores", []) or []]
    vals = [VIEWS[m] for m in mods if m in VIEWS]
    if vals:
        lo = min(v[0] for v in vals + ([(DECL, DECL)] if any(m not in VIEWS for m in mods) else []))
        hi = max(v[1] for v in vals + ([(DECL, DECL)] if any(m not in VIEWS for m in mods) else []))
        rng[p] = (lo - DECL, hi - DECL)
late = {p: v + rng.get(p, (0, 0))[1] for p, v in ff.items()}
early = {p: v + rng.get(p, (0, 0))[0] for p, v in ff.items()}
pairs = {(pr["src"]["part"], pr["dst"]["part"]) for pr in plan["ports"]
         if pr["src"].get("part") in ff and pr["dst"].get("part") in ff and pr["src"]["part"] != pr["dst"]["part"]}
pu = json.loads((d / "sta_in_cv" / "pair_unc.json").read_text())["rows"]
for r in pu:
    pairs |= {(r["a"], r["b"]), (r["b"], r["a"])}
dm = sorted(((late[b] - early[a], a, b) for a, b in pairs), reverse=True)
W = 40.0
out = dict(pairs_checked=len(pairs), viewed_partitions=len(rng), worst_damage_ps=round(dm[0][0], 2), worst=dm[0][1:],
           kit_contract_hold_ps=round(W - dm[0][0], 2), verdict="PASS" if dm[0][0] <= W else "FAIL",
           nominal_tap_skew_TT=round(max(tt.values()) - min(tt.values()), 3), nominal_tap_skew_FF=round(max(ff.values()) - min(ff.values()), 3))
print(json.dumps(out))
# TT setup recompute (numcheck.py r10 method): per port-connected ordered pair, U = AOCV random + distance + max |MC
# pair-difference change| over the 13 samples, slack = T - 60 - (launch + clkq_max_wire) + (capture - setup) - U
import glob
S = {}
for f in glob.glob(str(d / "TT_s*.json")):
    j = json.loads(Path(f).read_text())
    S[j["sample"]] = j["tap_arr_ps"]
reg = json.loads((d / "sta" / "regchar" / "TT.json").read_text())
rows = {"|".join(sorted((r["a"], r["b"]))): r for r in json.loads((d / "sta_in" / "pair_unc.json").read_text())["rows"]}
pp = {(pr["src"]["part"], pr["dst"]["part"]) for pr in plan["ports"]
      if pr["src"].get("part") in tt and pr["dst"].get("part") in tt and pr["src"]["part"] != pr["dst"]["part"]}
t0 = S[0]
ws = None
for a, b in pp:
    r = rows["|".join(sorted((a, b)))]["TT"]
    var = max(abs((s[a] - s[b]) - (t0[a] - t0[b])) for s in S.values())
    U = r["aocv_random_ps"] + r["aocv_distance_ps"] + var
    st = 833.333 - 60.0 - (t0[a] + reg["clkq_max_wire_ps"]) + (t0[b] - reg["setup_ps"]) - U
    ws = st if ws is None else min(ws, st)
print(json.dumps(dict(tt_setup_pairs=len(pp), tt_setup_worst_ps=round(ws, 2), samples=len(S))))
