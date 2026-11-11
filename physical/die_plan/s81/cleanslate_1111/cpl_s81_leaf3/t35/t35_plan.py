#!/usr/bin/env python3
"""CPL-S81-LEAF-3 t35 plan change (COORD 04:10 ruling on p4: one intent sheet + delta), no new taps/ports/cycles/RTL:
 (a) N-face landing strip spread (p4 hotspot a: u_cland_ft1_i ring s_d, leafup_o0_is0_q, ft1_i pins at x 100-200):
     ft0_i / ft1_i landing bands (276 b, 1600 padded flops each) were two 60-um bands side by side at x 65-187;
     each becomes 194 um wide (x 6.48-200.88 / 209.52-403.92, same y 1183.68-1209.6); monitor_0 moves E of them.
 (b) channel W of u_vn.u_b (p4 hotspot b: w_u_vn_u_b_hq_d 56 + vp driver 25 at x 300-330, y 100-190): the inner lanes
     g_ln[2] (y 34.56) and g_ln[14] (y 164.16) move W to the 8.64 core gap next to g_ln[12]/g_ln[9] (x 192.24 / 183.6),
     so the u_b W-face channel grows from 15.1 to 21.6 um (g_ln[2]) and 30.2 um (g_ln[14]). The outer lanes cannot
     move W: the grid root tap site clk (59.4, 153.36) sits in their row gap and would snap 246 um E.
 (c) clk_t1 1604 / clk_t37 1610 sinks over the 1500 cap: clock.tap_max_sinks = 1500 (kit OT_TAP_MAX_SINKS 3000 ->
     1500); the kit cap pass moves the ~110 excess sinks to neighbour taps with room within OT_TAP_REASSIGN_UM 200
     (clk_t36 149 @152 um of clk_t1; clk_t22 584 @171 um / clk_t29 559 @193 um of clk_t37). Tap sites unchanged,
     so the reset collector contract is untouched.
usage: t35_plan.py TOOLS BASE OUTDIR"""
import copy, hashlib, json, os, sys
sys.path.insert(0, sys.argv[1])
import schema as S, taps, reset_tree as RT
import core_place as CP
base, od = sys.argv[2:4]
tn = "ot_s81sl_leaf__t35"
raw = json.load(open(base)); new = copy.deepcopy(raw)
t = new["partition_types"][tn]; ck = t["clock"]; b = ck["landing_contract"]["bands"]
b["ft0_i"]["rect_um"] = [6.48, 1183.68, 200.88, 1209.6]
b["ft1_i"]["rect_um"] = [209.52, 1183.68, 403.92, 1209.6]
b["monitor_0"]["rect_um"] = [412.56, 1136.16, 421.2, 1183.68]
ck["tap_max_sinks"] = 1500
MV = {"u_lf.u_vp.g_ln[2].u_l": 192.24, "u_lf.u_vp.g_ln[14].u_l": 183.6}
delta = {}
for h in t["hard_cores"]:
    if h["inst"] in MV:
        h["origin_um"] = [MV[h["inst"]], h["origin_um"][1]]
        delta[h["inst"]] = [h["origin_um"][0], h["origin_um"][1], h.get("orient", "R0")]
# overlap / spacing among cores (outline-based)
R = [(h["inst"], h["origin_um"][0], h["origin_um"][1], h["outline_um"][0], h["outline_um"][1]) for h in t["hard_cores"]]
W, H = t["outline_um"]; bad = []
for i, (a, x, y, w, hh) in enumerate(R):
    if x < 0 or y < 0 or x + w > W or y + hh > H: bad.append(("outside", a))
    for (c, X, Y, ww, HH) in R[i + 1:]:
        gx = max(X - (x + w), x - (X + ww)); gy = max(Y - (y + hh), y - (Y + HH))
        if gx < 8.64 - 1e-6 and gy < 8.64 - 1e-6: bad.append(("gap<8.64", a, c, round(gx, 2), round(gy, 2)))
print("core spacing issues", bad)
eq = CP.eq_gate(raw["partition_types"][tn], t)
print("EQ", eq[:3] if eq else "OK")
P0 = S.Plan(raw, base); P1 = S.Plan(new, base)
s0 = taps.grid_explicit_sites(P0, tn); s1 = taps.grid_explicit_sites(P1, tn)
print("tap sites same", s0 == s1)
try:
    print("grid_explicit_taps new OK", len(taps.grid_explicit_taps(P1, tn)))
except Exception as e:
    print("grid_explicit_taps new ERR", e)
GUARD = ("root", "entry", "sync_stages", "depth", "own_depth", "tap_depth", "taps", "n_clock_taps",
         "n_reset_consumers", "local_reset_taps", "outs", "core_resets")
r0 = RT.for_type(P0, tn); r1 = RT.for_type(P1, tn)
print("reset contract keys differing:", [k for k in GUARD if r0.get(k) != r1.get(k)])
base_errs = set(map(str, S.validate(copy.deepcopy(raw))))
errs = [e for e in map(str, S.validate(copy.deepcopy(new))) if e not in base_errs]
print("G0 schema new errors", len(errs), errs[:3])
os.makedirs(od, exist_ok=True)
json.dump({tn: delta}, open(f"{od}/leaf_t35.delta.json", "w"), indent=1)
json.dump({tn: {"hard_cores": t["hard_cores"], "clock": ck}}, open(f"{od}/leaf_t35.types_after.json", "w"), indent=1)
txt = json.dumps(new, indent=1) + "\n"
open(f"{od}/plan_t35.json", "w").write(txt)
print("plan", hashlib.sha256(txt.encode()).hexdigest()[:12])
