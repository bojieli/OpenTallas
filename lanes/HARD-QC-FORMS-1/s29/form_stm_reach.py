#!/usr/bin/env python3
"""QC-FORMS-2 form F-STM-REACH (R-REACH-3 / R-RTL-1 row 4, stm x11): the su stream buses x_su_l0_i / x_su_l1_i (S face)
and the fe bus x_fe_i (E face, y 166-264) land 0.9-1.2 mm from the stm logic band (post-CTS: u_stream wd_q -> lane_c
1.0-1.2 mm with 5-10 cells, -400..-644 ps, 697 endpoints; u_cland_x_fe_i ring -> top regs -258 ps, 542 endpoints).
Declares reach_home 'stm_logic' and adds an internal_stations chain bus:<name> per bus on a macro-free corridor
(k = ceil(L/340) - 1 FIRM stations, +k cycles on that bus, pre-approved), then reach_fix.sync_fixed_cycles prices the
lanes.  Run from a tree root (tools/die_plan importable).  usage: form_stm_reach.py PLAN_IN PLAN_OUT REPORT.json"""
import os, copy, hashlib, json, math, sys
sys.path.insert(0, "tools/die_plan")
import kv_start_corridor_event as KS
from start_obstacle_path import length, relay_sites
import reach_fix as RF
STEP, REACH = 340.0, 405.0
HOME = {"name": "stm_logic", "rect_um": [86.4, 1101.6, 527.04, 1502.0], "buses": ["x_su_l0_i", "x_su_l1_i", "x_fe_i"]}
pin, pout, rep = sys.argv[1:4]
raw_b = open(pin, "rb").read(); raw = json.loads(raw_b); Q = copy.deepcopy(raw)
R = {"form": "F-STM-REACH (QC-FORMS-2 11-13)", "plan_in_sha256": hashlib.sha256(raw_b).hexdigest(), "types": {}}
for tn in sorted(Q["partition_types"]):
    if "_stm_" not in tn: continue
    t = Q["partition_types"][tn]; W, H = t["outline_um"]
    have = {str(e.get("conn")) for e in t.get("internal_stations", []) or []}
    if os.environ.get("HQF_WRITE_REACH_HOMES") == "1":   # schema key of claude/rules-reach-1-1113 (not on main): opt-in only
        homes = [h for h in t.get("reach_homes") or [] if h.get("name") != HOME["name"]] + [copy.deepcopy(HOME)]
        t["reach_homes"] = homes
    obs = KS.corridor_obstacles(t, 4.32, 10.8); r = HOME["rect_um"]; added = []
    for b in t["buses"]:
        n = b["name"]
        if n not in HOME["buses"] or f"bus:{n}" in have: continue
        assert b["dir"] == "in", (tn, n)
        w0, w1 = b["window_um"]; c = (w0 + w1) / 2
        f = b["face"]
        a = {"S": (c, 0.0), "N": (c, H), "W": (0.0, c), "E": (W, c)}[f]
        a = KS._free_point((min(max(a[0], 4.32), W - 4.32), min(max(a[1], 4.32), H - 4.32)), obs)
        q = KS._free_point((min(max(a[0], r[0]), r[2]), min(max(a[1], r[1]), r[3])), obs)
        rt = KS._route(a, q, obs, W, H); L = length(rt)
        if L <= REACH: continue
        k = max(1, math.ceil(L / STEP) - 1)
        regs = relay_sites(rt, k, max_hop_um=REACH, clearance_um=KS.CLEAR_UM)
        t.setdefault("internal_stations", []).append(dict(conn=f"bus:{n}", from_um=[round(v, 3) for v in a], to_um=[round(v, 3) for v in q],
            regs_um=regs, bits=int(b.get("width", 1)), launch=f"face:{f}",
            note=f"R-REACH-3 / R-RTL-1 (QC-FORMS-2 F-STM-REACH 11-13): {L:.0f} um window -> reach_home stm_logic: {k} FIRM station(s), +{k} cycle(s)"))
        added.append(dict(bus=n, bits=b.get("width"), corridor_um=round(L, 1), stations=k, regs_um=regs))
    R["types"][tn] = added
rec = RF.sync_fixed_cycles(raw, Q, pin)
R["sync_fixed_cycles"] = {k: rec[k] for k in ("bus_deltas", "rule_broken")} | {"lanes": len(rec.get("lanes", {})), "latency": len(rec.get("latency", {}))}
out = json.dumps(Q).encode(); open(pout, "wb").write(out); R["plan_out_sha256"] = hashlib.sha256(out).hexdigest()
json.dump(R, open(rep, "w"), indent=1)
print("out", R["plan_out_sha256"][:12], "bus_deltas", len(rec["bus_deltas"]), "lanes", len(rec.get("lanes", {})), "rule_broken", rec.get("rule_broken"))
for tn, a in R["types"].items(): print(tn, [(x["bus"], x["corridor_um"], x["stations"]) for x in a])
