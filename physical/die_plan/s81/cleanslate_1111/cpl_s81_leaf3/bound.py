#!/usr/bin/env python3
"""CPL-S81-LEAF-3: arrangement-independent cut bound per type (S2 step 2 'ideal bound').
For every full cut line c (vertical lines -> H demand, horizontal -> V; every 2nd 21.6-um grid line):
  LB(c)  = rigorous LOWER bound on the bits any placement must carry across c: Lagrangian dual of the
           area-constrained 2-way min-cut (clusters on either side, area_side <= side area, terminals = type
           face/bus/station points fixed by side), each dual value an exact s-t min cut (max-flow);
  FM(c)  = core_place FM heuristic partition at util 1.0 (an achievable partition, so LB <= true min <= FM);
  + ft(c) = die ft hops crossing c (fixed).
Supply: point = tracks on the line with no macro on it (upper bound); mean = mean over all lines of the tracks
  (= integral of the per-bin supply / L, arrangement-independent: macro area and OBS fixed).
BOUND = max( max_c (LB+ft)/S_nomacro , mean_c(LB+ft)/mean_c(S) )   -- worst cut of ANY arrangement >= BOUND.
--no-ft: what-if with the die ft hops removed from the type (die ft diet).
usage: bound.py REPO PLAN TYPE[,TYPE..] OUT.json [--no-ft] [--arr PLAN2]  (--arr: also the arranged worst cut on PLAN2)"""
import collections, json, math, sys
from pathlib import Path
import numpy as np
repo, plan_p, types, outp = sys.argv[1:5]
noft = "--no-ft" in sys.argv
arr = sys.argv[sys.argv.index("--arr") + 1] if "--arr" in sys.argv else None
sys.path.insert(0, str(Path(repo) / "tools" / "die_plan"))
import core_place as CP  # noqa
RS = CP.RS
repo = Path(repo).resolve(); plan = Path(plan_p).resolve()
P = json.loads(plan.read_bytes())
P2 = json.loads(Path(arr).read_bytes()) if arr else None
RS.REF_DIRS[:] = [str(plan.parent)]
die_dir = repo / "physical" / "die_plan" / "s81"
rs_cfg = dict(RS.DEFAULTS, derate=dict(RS.DERATE), core_ceiling=RS.DEFAULTS["core_ceiling"])
for k, f in (("views", "route_supply_views.json"), ("kit_views", "route_supply_kit_views.json")):
    try:
        v = json.loads((CP.HERE / f).read_text()).get("views" if k == "views" else "s81", {})
    except Exception:
        v = {}
    rs_cfg[k] = v
conns = RS.load_conns(die_dir, None, plan.parent, [])
cfg = dict(gap=34.56, sweeps=0, topk=1, lam=4.0, reach=405, grid_um=21.6, grt_halving="full", fixed_re="", rs=rs_cfg,
           flips_only=False, face_clear=[])


def maxflow(n, edges, s, t):
    g = [dict() for _ in range(n)]
    for u, v, c in edges:
        if c <= 0: continue
        g[u][v] = g[u].get(v, 0.0) + c
        g[v].setdefault(u, 0.0)
    f = 0.0
    while True:   # Dinic
        lvl = [-1] * n; lvl[s] = 0; q = [s]
        for u in q:
            for v, c in g[u].items():
                if c > 1e-9 and lvl[v] < 0:
                    lvl[v] = lvl[u] + 1; q.append(v)
        if lvl[t] < 0: return f
        it = [list(g[u].keys()) for u in range(n)]
        def dfs(u, push):
            if u == t: return push
            while it[u]:
                v = it[u][-1]
                c = g[u][v]
                if c > 1e-9 and lvl[v] == lvl[u] + 1:
                    d = dfs(v, min(push, c))
                    if d > 0:
                        g[u][v] -= d; g[v][u] += d; return d
                it[u].pop()
            return 0.0
        while True:
            d = dfs(s, 1e18)
            if d <= 0: break
            f += d


def model(t, tn):
    M = CP.TypeModel(tn, t, die_dir, repo, conns, cfg)
    Gd = CP.Grid(M, cfg)
    return M, Gd


def bound(M, Gd):
    if noft:
        M.static = []
    area = np.array([M.cbb[k, 2] * M.cbb[k, 3] for k in range(M.m)])
    E = collections.defaultdict(float); T = collections.defaultdict(list)
    for (a, bb, w, kind) in M.L:
        ka = M.cid[a[0]] if a[0] is not None else None
        kb = M.cid[bb[0]] if bb[0] is not None else None
        if ka is not None and kb is not None:
            if ka != kb: E[(min(ka, kb), max(ka, kb))] += w
        elif ka is not None: T[ka].append((bb[1], w))
        elif kb is not None: T[kb].append((a[1], w))
    SH, SV = Gd.supply()
    out = {}
    m = M.m; S_, T_ = m, m + 1
    lam0 = sum(E.values()) + sum(w for k in T for _, w in T[k])
    lam0 = lam0 / max(area.sum(), 1.0)
    lams = [0.0] + [lam0 * 2 ** e for e in range(-6, 7)]
    for d, ax, L, other, S in (("H", 0, M.W, M.H, SH), ("V", 1, M.H, M.W, SV)):
        b = Gd.b
        nc = Gd.nx if ax == 0 else Gd.ny
        sup = S.sum(axis=0) if ax == 0 else S.sum(axis=1)       # per column/row: tracks across a line in it
        s_nomac = (Gd.sH0 if d == "H" else Gd.sV0) * other / b
        rows = []
        # never cut through a fixed die geometry: every 2nd grid line, inside the outline
        for ci in range(2, nc - 1, 2):
            c = ci * b
            capL, capR = c * other, (L - c) * other
            ft = sum(n for (p, q, n) in M.static if min(p[ax], q[ax]) < c < max(p[ax], q[ax]))
            # terminal cost of each side: side 0 = left/below
            tL = [sum(w for (p, w) in T[k] if p[ax] > c) for k in range(m)]   # cost if k on left
            tR = [sum(w for (p, w) in T[k] if p[ax] <= c) for k in range(m)]  # cost if k on right
            best = -1.0
            for which in (0, 1):
                for lam in lams:
                    if lam == 0 and which == 1: continue
                    l1, l2 = (lam, 0.0) if which == 0 else (0.0, lam)
                    # node in S-side = left.  cost(left)=tL+l1*a -> edge k->T ; cost(right)=tR+l2*a -> edge S->k
                    ed = []
                    for k in range(m):
                        ed.append((k, T_, tL[k] + l1 * area[k]))
                        ed.append((S_, k, tR[k] + l2 * area[k]))
                    for (i, j), w in E.items():
                        ed.append((i, j, w)); ed.append((j, i, w))
                    val = maxflow(m + 2, ed, S_, T_) - l1 * capL - l2 * capR
                    best = max(best, val)
            lb = max(0.0, best)
            rows.append(dict(at_um=round(c, 1), lb_bits=int(lb), ft_bits=int(ft), s_nomacro=int(s_nomac),
                             s_here=int(sup[ci]), r_point=round((lb + ft) / s_nomac, 3)))
        rp = max(r["r_point"] for r in rows)
        mean_d = float(np.mean([r["lb_bits"] + r["ft_bits"] for r in rows]))
        mean_s = float(sup.mean())
        out[d] = dict(point=rp, mean=round(mean_d / mean_s, 3), mean_dem=int(mean_d), mean_sup=int(mean_s),
                      bound=round(max(rp, mean_d / mean_s), 3), rows=rows)
    # STAR (closed-contour) bound per cluster k: contour = k's bbox grown by r; at most the partners that fit in the
    # ring area (fractional knapsack by bits/area, outline ignored = optimistic) sit inside; the rest of k's link
    # bits cross the contour; supply = no-macro tracks across its perimeter (H across the vertical sides, V across
    # the horizontal ones).  FACE escape: pins on one face of a core leave through the tracks in front of that face.
    dH, dV = Gd.sH0 / Gd.b, Gd.sV0 / Gd.b          # tracks per um, no macro
    adjk = collections.defaultdict(lambda: collections.defaultdict(float)); Bk = collections.defaultdict(float)
    for (i, j), w in E.items():
        adjk[i][j] += w; adjk[j][i] += w; Bk[i] += w; Bk[j] += w
    star = []
    for k in range(m):
        w, h = M.cbb[k, 2], M.cbb[k, 3]
        part = sorted(adjk[k].items(), key=lambda jw: -jw[1] / max(area[jw[0]], 1.0))
        best = (0.0, 0.0, 0)
        for r in (10.8, 21.6, 43.2, 64.8, 86.4, 129.6, 172.8, 259.2, 345.6, 432.0):
            room = (w + 2 * r) * (h + 2 * r) - w * h
            inside = 0.0
            for j, bw in part:
                if area[j] <= room:
                    inside += bw; room -= area[j]
                else:
                    inside += bw * room / area[j]; break
            dem = Bk[k] - inside
            sup = 2 * (h + 2 * r) * dH + 2 * (w + 2 * r) * dV
            if dem / sup > best[0]:
                best = (dem / sup, r, int(dem))
        star.append(dict(cl=k, insts=[M.inst[i] for i in M.CL[k]][:3], bits=int(Bk[k]), ratio=round(best[0], 3),
                         r_um=best[1], cross_bits=best[2]))
    star.sort(key=lambda d: -d["ratio"])
    out["star"] = dict(bound=star[0]["ratio"] if star else 0.0, top=star[:4])
    fe = []
    for i in range(M.n):
        w, h = M.dim[i]
        for f, cnt in M.lface[i].items():
            o = M.ori0[i]
            ln = h if f in "EW" else w
            # lface is in the local frame; R0/MX/MY/R180 keep the E/W vs N/S axis, so the face length is right
            fe.append(dict(inst=M.inst[i], face_local=f, pins=int(cnt), len_um=round(ln, 1),
                           ratio=round(cnt / (ln * (dH if f in "EW" else dV)), 3)))
    fe.sort(key=lambda d: -d["ratio"])
    out["face_escape"] = dict(bound=fe[0]["ratio"] if fe else 0.0, top=fe[:4])
    # TYPE-FACE windows (fixed by the die plan): bits of each window (buses + ft in/out) over the perpendicular
    # no-macro tracks in front of it (all layers, window grown by the 97.2-um detour on each side = optimistic),
    # and the 1-D face strip: windows merged where their grown spans overlap.
    t = M.t
    win = []
    for bu in t.get("buses", []) or []:
        if bu.get("face") and bu.get("window_um"):
            win.append((bu["face"], bu["window_um"], int(bu.get("width", 0)), bu["name"]))
    if not noft:
        for f in t.get("ft_slots", []) or []:
            for fk, wk in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
                if f.get(fk) and f.get(wk):
                    win.append((f[fk], f[wk], int(f.get("width", 1)), f["name"] + "." + fk[:-5]))
    fw = []
    for face in "NSEW":
        ws = sorted([(w[1][0] - 97.2, w[1][1] + 97.2, w[2], w[3]) for w in win if w[0] == face])
        grp = []
        for a0, a1, bits, nm in ws:
            if grp and a0 <= grp[-1][1]:
                g = grp[-1]; grp[-1] = (g[0], max(g[1], a1), g[2] + bits, g[3] + [nm])
            else:
                grp.append((a0, a1, bits, [nm]))
        Lf = M.W if face in "NS" else M.H
        dens = dV if face in "NS" else dH
        for a0, a1, bits, nms in grp:
            ln = min(a1, Lf) - max(a0, 0.0)
            fw.append(dict(face=face, span_um=[round(max(a0, 0), 1), round(min(a1, Lf), 1)], bits=bits, names=nms,
                           ratio=round(bits / (ln * dens), 3)))
    fw.sort(key=lambda d: -d["ratio"])
    out["face_windows"] = dict(bound=fw[0]["ratio"] if fw else 0.0, top=fw[:3])
    out["line_bound"] = max(out["H"]["bound"], out["V"]["bound"])
    out["bound"] = max(out["line_bound"], out["star"]["bound"], out["face_escape"]["bound"],
                       out["face_windows"]["bound"])
    return out


res = {}
for tn in types.split(","):
    M, Gd = model(P["partition_types"][tn], tn)
    r = dict(cores=M.n, clusters=M.m, outline=[M.W, M.H],
             core_area_frac=round(float(sum(M.dim[i, 0] * M.dim[i, 1] for i in range(M.n)) / (M.W * M.H)), 3))
    st = list(M.static)
    r["ft_bits_total_hops"] = int(sum(n for (_, _, n) in st))
    r["arranged_base"] = {k: v["worst_ratio"] for k, v in CP.cut_table(M, Gd).items()}
    if noft:
        M.static = []
        r["arranged_base_noft"] = {k: v["worst_ratio"] for k, v in CP.cut_table(M, Gd).items()}
        M.static = st
    if P2 is not None:
        M2, G2 = model(P2["partition_types"][tn], tn)
        r["arranged_arr"] = {k: v["worst_ratio"] for k, v in CP.cut_table(M2, G2).items()}
        if noft:
            M2.static = []
            r["arranged_arr_noft"] = {k: v["worst_ratio"] for k, v in CP.cut_table(M2, G2).items()}
    r.update(bound(M, Gd))
    res[tn] = r
    print(tn, r["bound"], "line", r["line_bound"], "star", r["star"]["bound"], r["star"]["top"][:1],
          "face", r["face_escape"]["bound"], "win", r["face_windows"]["top"][:1], "H", r["H"]["point"], r["H"]["mean"], "V", r["V"]["point"], r["V"]["mean"],
          "arr", r["arranged_base"], r.get("arranged_arr"), flush=True)
json.dump(res, open(outp, "w"), indent=1)
