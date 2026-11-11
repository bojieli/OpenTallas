#!/usr/bin/env python3
"""CPL-S81-SLICE: open the cap|xr macro street (plan 17.28 um).  Move u_c.u_xr away from u_c.u_cap by k x 8.64 along
the axis that separates them (and optionally off the face by j x 8.64); every candidate must pass the composer gate
(cgate), the station EQ check and the kit tap rule; score route_supply.  usage: xrshift.py PLAN TYPE OUT.json"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl, common, cgate  # noqa: E402
LAT = 8.64
plan, tn, out = sys.argv[1:4]
P, conns = cpl.load(plan)
M = common.model(P, conns, tn)
G = cgate.Gate(plan, tn, M.t)
cfg = cpl.rs_cfg()
pl0 = M.current()
ic, ix = M.ix["u_c.u_cap"], M.ix["u_c.u_xr"]
rc, rx = M.rect(ic, pl0), M.rect(ix, pl0)
sx = 1 if rx[0] >= rc[2] - 1e-6 else (-1 if rx[2] <= rc[0] + 1e-6 else 0)
sy = 0
if sx == 0:
    sy = 1 if rx[1] >= rc[3] - 1e-6 else -1
face_dy = 1 if pl0[ix][1] < M.H / 2 else -1      # off the S face (up) or off the N face (down)
r0 = cpl.rs_summary(M.rs(pl0, cfg, conns, resite=True))
print(tn, "plan p99", r0.get("p99"), r0.get("region"), r0.get("dir"), "street axis", sx, sy, flush=True)
res = []
for k in range(1, 9):
    for j in (0, 1, 2, 4):
        pl = list(pl0)
        x, y, o = pl0[ix]
        nx = round(x + sx * k * LAT, 3) if sx else round(x + face_dy * 0 + 0, 3)
        ny = round(y + sy * k * LAT + face_dy * j * LAT, 3) if sy else round(y + face_dy * j * LAT, 3)
        pl[ix] = (nx, ny, o)
        sc = M.station_check(pl)
        t = M.plan_with(pl)
        new = G.new(t)
        mode = "resite"
        if new and not sc:
            # keep the plan station regs (only the xr-side end hop changes; core taps still move rigidly)
            t2 = M.plan_with(pl)
            import copy as _c
            t2["internal_stations"] = _c.deepcopy(M.t["internal_stations"])
            new2 = G.new(t2)
            if not new2:
                t, new, mode = t2, [], "keep_regs"
        if sc or new:
            print(tn, "k", k, "j", j, "reject", "station" if sc else "", new[:2], flush=True)
            continue
        tp = G.taps(t)
        if mode == "resite":
            r = cpl.rs_summary(M.rs(pl, cfg, conns, resite=True))
        else:
            rr = cpl.RS.analyze_type(M.name, t, cpl.DIE_DIR, cpl.REPO, conns, cfg)
            r = cpl.rs_summary(rr)
        wv, wh = M.worst_cut(pl)
        row = dict(mode=mode, k=k, j=j, xr=[nx, ny, o], rs_p99=r.get("p99"), region=r.get("region"), dir=r.get("dir"), taps=tp,
                   bitmm=round(M.bitmm(pl), 1), cut=round(max(wv[3], wh[3]), 3))
        res.append(row)
        print(tn, json.dumps(row), flush=True)
res.sort(key=lambda r: (r["taps"] is not None, r["rs_p99"] or 9))
json.dump(dict(type=tn, plan=r0, bitmm0=round(M.bitmm(pl0), 1), cands=res), open(out, "w"), indent=1)
print(tn, "BEST", res[0] if res else None)
