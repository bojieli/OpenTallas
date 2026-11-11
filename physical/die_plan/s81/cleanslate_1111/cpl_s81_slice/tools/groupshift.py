#!/usr/bin/env python3
"""CPL-S81-SLICE hand street sizing (COORD 04:4x scope).  The slice C route_supply hot spots sit in three plan streets:
(1) the 17.28-um cap|xr macro street (mstreet_H: xr W2070 pins face cap), (2) the 36-um E street between the
eng_finish row and the E outline (ring_V: E-face xring landings run N-S beside the row), (3) the S/N landing under
cap/xr (ring_H).  Hand rule: widen the street the bits cross by moving a whole functional group rigidly (xr alone; the
finish row g_cp0..3 + u_f together, so the chain order and 190-um pitch are kept; the egn/egg block together), one
group at a time on the 8.64 lattice, along x then y.  A move is kept only if it passes the composer gate (cgate: no
new overlap / street / site finding; station regs re-sited, or kept as planned when the re-site lands under a macro),
the station EQ check, the intent link rule (no >=32 b / station link beyond 1.2x+20 um or newly past reach) and the
kit tap rule, and lowers route_supply p99.
usage: groupshift.py PLAN TYPE OUT.json"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl  # noqa: E402
import common  # noqa: E402
import cgate  # noqa: E402
import search  # noqa: E402

LAT = 8.64
TF = float(os.environ.get("TAPFOLLOW", "9.2"))
GROUPS = [("xr", ["u_c.u_xr"]),
          ("finish_row", ["u_c.u_xf.g_cp[0].u_e", "u_c.u_xf.g_cp[1].u_e", "u_c.u_xf.u_f", "u_c.u_xf.g_cp[2].u_e",
                          "u_c.u_xf.g_cp[3].u_e"]),
          ("eg_block", ["u_c.u_eg.u_nh", "u_c.u_eg.u_nk", "u_c.u_eg.u_gg"])]
KS = [k for k in range(-8, 9) if k]
if os.environ.get("SHIFT_GROUPS"):
    GROUPS = json.loads(os.environ["SHIFT_GROUPS"])


def main():
    plan, tn, out = sys.argv[1:4]
    P, conns = cpl.load(plan)
    M = common.model(P, conns, tn)
    G = cgate.Gate(plan, tn, M.t)
    S = search.Search(M)
    S.set_intent(disp=10000.0)          # link rule only (group moves are hand moves, not a displacement-bounded tune)
    cfg = cpl.rs_cfg()
    pl0 = M.current()

    TAPMV = {}

    def follow_taps(t, pl, idx, vec):
        """added clock taps inside (box + 9.2) of a moved group core at its plan spot move rigidly with the group"""
        mv = {}
        for p in (t.get("clock") or {}).get("added_taps", []) or []:
            x, y = map(float, p["xy"])
            for i in idx:
                for pp in (pl0[i],):
                    r = M.rect(i, [pp if j == i else pl0[j] for j in range(len(pl0))])
                    if r[0] - TF < x < r[2] + TF and r[1] - TF < y < r[3] + TF:
                        mv[p["name"]] = [round(x + vec[0], 3), round(y + vec[1], 3)]
            if p["name"] in mv:
                p["xy"] = mv[p["name"]]
        return mv

    def evaluate(pl):
        if M.station_check(pl):
            return None, "station"
        if not S.intent_ok(pl):
            return None, "intent-link"
        t = M.plan_with(pl)
        for (vec, idx) in MOVES:
            follow_taps(t, pl, idx, vec)
        mode = "resite"
        if G.new(t):
            t2 = M.plan_with(pl)
            for (vec, idx) in MOVES:
                follow_taps(t2, pl, idx, vec)
            t2["internal_stations"] = copy.deepcopy(M.t["internal_stations"])
            t = t2
            mode = "keep_regs"
            nw = G.new(t)
            if nw:
                return None, "gate:" + nw[0][-80:]
        r = cpl.RS.analyze_type(M.name, t, cpl.DIE_DIR, cpl.REPO, conns, cfg)
        r.pop("_maps", None)
        return (r["worst"]["p99"], r["worst"]["region"], r["worst"]["dir"], mode, t), None

    base, _ = evaluate(pl0) if False else (None, None)
    r0 = cpl.RS.analyze_type(M.name, M.plan_with(pl0, resite=False), cpl.DIE_DIR, cpl.REPO, conns, cfg)
    cur_p99 = r0["worst"]["p99"]
    print(tn, "plan p99", cur_p99, r0["worst"]["region"], r0["worst"]["dir"], flush=True)
    pl = list(pl0)
    steps = []
    MOVES = []
    mode_final = None
    for gname, insts in GROUPS:
        idx = [M.ix[i] for i in insts if i in M.ix]
        if not idx:
            continue
        best = None
        for axis in (0, 1):
            for k in KS:
                c = list(pl)
                for i in idx:
                    x, y, o = c[i]
                    c[i] = (round(x + (k * LAT if axis == 0 else 0), 3), round(y + (k * LAT if axis == 1 else 0), 3), o)
                if any(M.rect(i, c)[0] < 0 or M.rect(i, c)[1] < 0 or M.rect(i, c)[2] > M.W or M.rect(i, c)[3] > M.H
                       for i in idx):
                    continue
                vec = (k * LAT if axis == 0 else 0.0, k * LAT if axis == 1 else 0.0)
                MOVES.append((vec, idx))
                v, why = evaluate(c)
                MOVES.pop()
                if v is None:
                    continue
                if v[0] < cur_p99 - 1e-3 and (best is None or v[0] < best[0][0] - 1e-6
                                               or (abs(v[0] - best[0][0]) < 1e-6 and abs(k) < abs(best[2]))):
                    best = (v, c, k, axis, vec)
        if best:
            tp = G.taps(best[0][4])
            if tp is not None:
                print(tn, gname, "best shift fails the kit tap rule:", tp[:160], flush=True)
                continue
            pl = best[1]
            MOVES.append((best[4], idx))
            cur_p99 = best[0][0]
            mode_final = best[0][3] if mode_final in (None, "resite") else mode_final
            steps.append(dict(group=gname, axis="x" if best[3] == 0 else "y", shift_um=round(best[2] * LAT, 3),
                              p99=best[0][0], region=best[0][1], dir=best[0][2], station_mode=best[0][3]))
            print(tn, "APPLY", json.dumps(steps[-1]), flush=True)
        else:
            print(tn, gname, "no improving legal shift", flush=True)
    # final legality of the composed result
    t = M.plan_with(pl)
    tapmv = {}
    for (vec, idx) in MOVES:
        tapmv.update(follow_taps(t, pl, idx, vec))
    smode = "resite"
    if G.new(t):
        t["internal_stations"] = copy.deepcopy(M.t["internal_stations"])
        smode = "keep_regs"
    fin = dict(type=tn, plan_p99=r0["worst"]["p99"], plan_region=r0["worst"]["region"], plan_dir=r0["worst"]["dir"],
               p99=cur_p99, steps=steps, gate_new=G.new(t), taps=G.taps(t), station_mode=smode,
               station_check=M.station_check(pl), bitmm0=round(M.bitmm(pl0), 1), bitmm=round(M.bitmm(pl), 1),
               delta={M.cores[i]["inst"]: [round(pl[i][0], 3), round(pl[i][1], 3), pl[i][2]]
                      for i in range(len(pl)) if tuple(pl[i]) != tuple(pl0[i])},
               added_taps_moved=tapmv, stations=t["internal_stations"] if smode == "keep_regs" else None)
    json.dump(fin, open(out, "w"), indent=1)
    print(tn, "FINAL", json.dumps({k: fin[k] for k in ("plan_p99", "p99", "gate_new", "taps", "station_mode")}), flush=True)


if __name__ == "__main__":
    main()
