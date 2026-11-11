#!/usr/bin/env python3
"""rowprobe.py PLAN TYPE: finish-row x shifts; per shift p99, gate, tap error, with added tap clk_tN optionally re-sited
(TAPXY env 'name:x,y')."""
import copy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl, common, cgate
plan, tn = sys.argv[1:3]
P, conns = cpl.load(plan); M = common.model(P, conns, tn); G = cgate.Gate(plan, tn, M.t); cfg = cpl.rs_cfg()
pl0 = M.current()
row = [M.ix[i] for i in ["u_c.u_xf.g_cp[0].u_e", "u_c.u_xf.g_cp[1].u_e", "u_c.u_xf.u_f", "u_c.u_xf.g_cp[2].u_e", "u_c.u_xf.g_cp[3].u_e"]]
for k in [-1, -2, -3, -4, -5, -6, -8]:
    pl = list(pl0)
    for i in row:
        x, y, o = pl[i]; pl[i] = (round(x + k * 8.64, 3), y, o)
    for mode in ("resite", "keep"):
        t = M.plan_with(pl)
        if mode == "keep":
            t["internal_stations"] = copy.deepcopy(M.t["internal_stations"])
        for spec in filter(None, os.environ.get("TAPXY", "").split(";")):
            n, xy = spec.split(":"); xs = [float(v) for v in xy.split(",")]
            for a in t["clock"]["added_taps"]:
                if a["name"] == n:
                    a["xy"] = [round(xs[0] + (k * 8.64 if len(xs) > 2 else 0), 3), xs[1]]
        new = G.new(t)
        if new:
            print(tn, k, mode, "gate", new[:1]); continue
        r = cpl.RS.analyze_type(M.name, t, cpl.DIE_DIR, cpl.REPO, conns, cfg)
        print(tn, k, mode, "p99", r["worst"]["p99"], r["worst"]["region"], r["worst"]["dir"], "sc", M.station_check(pl), "tap", (G.taps(t) or "ok")[:120], flush=True)
        break
