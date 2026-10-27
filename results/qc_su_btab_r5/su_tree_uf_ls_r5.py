#!/usr/bin/env python3

"""MASTER-PLAN-R5 (COORD ruling R4 (1)/(2), METHODOLOGY 12.8 b/d1, 12.2a1): plan-sized in-core clock tree with
UNEQUAL fanout per island, computed from sink geometry before any build.

Structure (same 3-level skeleton as the QC-SU-LAT R5 equal-structure tree, su_tree_model.py):
  entry -> k islands (pushdown driver cells) -> B nodes -> leaf drivers (NL leaves, equal sink load).
Differences (the ruling):
  * island COUNT and SITES follow the sink mass: k-means (Manhattan) clusters, island = legal cell nearest the
    cluster median; every sink belongs to its NEAREST island by maze distance (Voronoi, no equal-load balancing,
    which is what forced R4's vmr north island to span 143 um);
  * leaves per island m_i proportional to the island's sinks (largest remainder, sum NL), B nodes per island
    ceil(m_i / 4), leaves per B as even as possible -> fanout differs island to island;
  * every level keeps ONE wire length (short edges take a legal detour, as in R5) and one repeater count, so the
    wire part of every root->leaf path is identical by construction;
  * the fanout difference is absorbed by PER-BRANCH DRIVER SIZING computed here from geometry + liberty NLDM
    (12.8 d1): each island / B driver cell is chosen from a fixed buffer list so its stage delay matches the
    level's reference stage; chosen cells are recorded and frozen with the plan.  No measurement input.
  * k is chosen by this model (deterministic search over k_min..k_max): smallest predicted TT window, then the
    TT mean nearest the 250 ps common target.
Model scope: PLAN MODEL ONLY (liberty NLDM + setRC x rc_cal 0.8/0.9, Elmore wire, leaf MST load), UNCHECKED.
usage: su_tree_uf.py GEO OUT.json [SMAX_um=100] [KMIN=2] [KMAX=6] [NL=64] [LIBDIR]

su_tree_uf_pc.py (QC-SU-KITS r3, COORD addendum on GEOM-REVIEW-4 prog_m0/btab_m0 FAIL STRUCTURAL): identical model
plus a NODE keepout over every SRAM clock-pin column (PIN_COL_UM = 15.12 um = 3.5 PG pitches beside the macro's
clock-pin face, over the macro height +- the 4.32 row halo): no island / B / leaf site may snap into it; legs still
route through it (the maze is unchanged), so legs run along the gaps between SRAMs and never across one.

su_tree_uf_ls.py (QC-SU-KITS-3, COORD 14:37 btab_m0 structural re-plan): identical model + PIN_COLS node keepout, plus
LEGAL ISLAND SITES: the k clusters are found exactly as before (Manhattan k-means), then each island is sited on the
legal 8.64 um island rect of the 4.32 PG lattice (std-cell rows, outside every macro ROW halo, outside every SRAM
clock-pin column, not on the entry island or another island) nearest its cluster median, so no island can land in an
SRAM clock-pin column or a too-narrow SRAM gap (btab_m0 r3 Q3).  The island point is the rect centre (su_kit_gate G2
keeps the same rect).  Deterministic, no measured input.  PLAN MODEL, UNCHECKED.

su_tree_uf_ls_r5.py (QC-SU-BTAB-R5, GEOM-REVIEW-6 16:23 + 15:34 KITS-3 cond): identical model + a LEG keep-off: every tree
leg (maze path) is kept out of every SRAM clock-pin column widened by LEG_KO_UM (4.32) on its open side, over the macro
height +- the 4.32 row halo.  A leg may therefore cross a pin column only through the centre of an inter-SRAM gap
(15.12 - 2 x 4.32 = 6.5 um free) and never runs along it (btab_m0_r4: the L1 to the SE island ran 99 um down x 233 on the
dense E pin-flop column).  Nodes keep the same keepout (blkN contains blk).  Deterministic, no measured input.  UNCHECKED.
"""
import collections
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lib  # noqa: E402

geo, out = sys.argv[1], sys.argv[2]
SMAX = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0
KMIN = int(sys.argv[4]) if len(sys.argv) > 4 else 2
KMAX = int(sys.argv[5]) if len(sys.argv) > 5 else 6
NL = int(sys.argv[6]) if len(sys.argv) > 6 else 64
LIBDIR = Path(sys.argv[7]) if len(sys.argv) > 7 else Path(__file__).parent
G = 0.54
HALO = 2.2
sinks, macros, macpins = [], [], []
PIN_COL_UM, ROW_HALO = 15.12, 4.32
for line in open(geo):
    f = line.split()
    if not f:
        continue
    if f[0] == "CORE":
        core = tuple(map(float, f[1:5]))
    if f[0] == "PIN" and f[1] == "ck":
        entry = (float(f[2]), float(f[3]))
    if f[0] == "SINK":
        sinks.append((float(f[1]), float(f[2]), f[4], f[5]))
    if f[0] == "MACRO":
        macros.append((f[1], tuple(map(float, f[3:7]))))
        macpins.append((float(f[8]), float(f[9])))
NX = int((core[2] - core[0]) / G)
NY = int((core[3] - core[1]) / G)
W = NY + 1
blk = bytearray((NX + 1) * W)
for i in range(NX + 1):
    x = core[0] + i * G
    for _, r in macros:
        if r[0] - HALO < x < r[2] + HALO:
            for j in range(NY + 1):
                y = core[1] + j * G
                if r[1] - HALO < y < r[3] + HALO:
                    blk[i * W + j] = 1


def pin_columns():
    out = []
    for (_, r_), (px, _py) in zip(macros, macpins):
        x0, x1 = (r_[2], r_[2] + PIN_COL_UM) if abs(px - r_[2]) < abs(px - r_[0]) else (r_[0] - PIN_COL_UM, r_[0])
        out.append((x0, r_[1] - ROW_HALO, x1, r_[3] + ROW_HALO))
    return out


PIN_COLS = pin_columns()
import os as _os
LEG_KO_UM = float(_os.environ.get("OT_LEG_PINCOL_KO", "4.32"))
LEG_KO = []
for (_, r_), q in zip(macros, PIN_COLS):
    e_side = abs(q[0] - r_[2]) < 1e-6
    LEG_KO.append((q[0], q[1], q[2] + LEG_KO_UM, q[3]) if e_side else (q[0] - LEG_KO_UM, q[1], q[2], q[3]))
_nko = 0
for i in range(NX + 1):
    x = core[0] + i * G
    for q in LEG_KO:
        if q[0] <= x <= q[2]:
            for j in range(NY + 1):
                y = core[1] + j * G
                if q[1] <= y <= q[3] and not blk[i * W + j]:
                    blk[i * W + j] = 1
                    _nko += 1
print("LEG_KO", LEG_KO_UM, "um rects", [[round(v, 2) for v in q] for q in LEG_KO], "cells", _nko)
# node keepout = maze blockage + SRAM clock-pin columns + the 4.32 kit macro ROW halo (a node is a std cell: G3 rule)
blkN = bytearray(blk)
for i in range(NX + 1):
    x = core[0] + i * G
    for q in PIN_COLS + [(r_[0] - ROW_HALO, r_[1] - ROW_HALO, r_[2] + ROW_HALO, r_[3] + ROW_HALO) for _, r_ in macros]:
        if q[0] <= x <= q[2]:
            for j in range(NY + 1):
                y = core[1] + j * G
                if q[1] <= y <= q[3]:
                    blkN[i * W + j] = 1


def cell(p):
    i = min(NX, max(0, round((p[0] - core[0]) / G)))
    j = min(NY, max(0, round((p[1] - core[1]) / G)))
    if not blkN[i * W + j]:
        return (i, j)
    for r in range(1, 600):
        for di in range(-r, r + 1):
            for dj in (-r, r):
                for a, b in ((i + di, j + dj), (i + dj, j + di)):
                    if 0 <= a <= NX and 0 <= b <= NY and not blkN[a * W + b]:
                        return (a, b)


def xy(c):
    return (round(core[0] + c[0] * G, 3), round(core[1] + c[1] * G, 3))


_bfs = {}


def bfs(c):
    if c in _bfs:
        return _bfs[c]
    D = [-1] * ((NX + 1) * W)
    s = c[0] * W + c[1]
    D[s] = 0
    q = collections.deque([s])
    while q:
        u = q.popleft()
        du = D[u] + 1
        i, j = divmod(u, W)
        for v, ok in ((u + W, i < NX), (u - W, i > 0), (u + 1, j < NY), (u - 1, j > 0)):
            if ok and D[v] < 0 and not blk[v]:
                D[v] = du
                q.append(v)
    _bfs[c] = D
    return D


def md(a, b):
    return bfs(a)[b[0] * W + b[1]] * G


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def balanced(points, k, targets, centres):
    """split points into k groups of the given target sizes (Manhattan to centres, iterative weights + fix-up)."""
    n = len(points)
    Dm = [[man(p, c) for c in centres] for p in points]
    w = [0.0] * k
    a = [0] * n
    for it in range(300):
        a = [min(range(k), key=lambda c: Dm[i][c] + w[c]) for i in range(n)]
        cnt = collections.Counter(a)
        if all(cnt[c] == targets[c] for c in range(k)):
            break
        for c in range(k):
            w[c] += 0.5 * (cnt[c] - targets[c]) / max(1, n / k) * 20 / (1 + it / 50)
    cnt = collections.Counter(a)
    while any(cnt[c] > targets[c] for c in range(k)):
        best = None
        for i in range(n):
            if cnt[a[i]] <= targets[a[i]]:
                continue
            for c in range(k):
                if cnt[c] < targets[c]:
                    cost = Dm[i][c] - Dm[i][a[i]]
                    if best is None or cost < best[0]:
                        best = (cost, i, c)
        _, i, c = best
        cnt[a[i]] -= 1
        cnt[c] += 1
        a[i] = c
    return [[points[i] for i in range(n) if a[i] == c] for c in range(k)]


def split(pts, targets):
    """balanced k-means split along the longer axis seeds, 6 Lloyd rounds."""
    k = len(targets)
    if k == 1:
        return [pts]
    xs = sorted(p[0] for p in pts)
    ys = sorted(p[1] for p in pts)
    srt = sorted(pts, key=(lambda p: p[0]) if xs[-1] - xs[0] > ys[-1] - ys[0] else (lambda p: p[1]))
    acc, cs = 0, []
    for t in targets:
        cs.append(srt[min(len(srt) - 1, acc + t // 2)][:2])
        acc += t
    grp = None
    for _ in range(6):
        grp = balanced(pts, k, targets, cs)
        cs = [(sorted(p[0] for p in g)[len(g) // 2], sorted(p[1] for p in g)[len(g) // 2]) for g in grp]
    return grp


def kmeans(pts, k):
    """deterministic Manhattan k-means (medians), farthest-point seeding from the entry."""
    cs = [max(pts, key=lambda p: man(p, entry))[:2]]
    while len(cs) < k:
        cs.append(max(pts, key=lambda p: min(man(p, c) for c in cs))[:2])
    for _ in range(25):
        grp = [[] for _ in cs]
        for p in pts:
            grp[min(range(k), key=lambda c: man(p, cs[c]))].append(p)
        new = [(sorted(p[0] for p in g)[len(g) // 2], sorted(p[1] for p in g)[len(g) // 2]) if g else cs[i]
               for i, g in enumerate(grp)]
        if new == cs:
            break
        cs = new
    return cs


def centroid(g):
    return cell((sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g)))


def best_site(cells_):
    """legal cell minimising the max maze distance to the given cells (search box around their centroid)."""
    for c in cells_:
        bfs(c)
    cx = sum(c[0] for c in cells_) / len(cells_)
    cy = sum(c[1] for c in cells_) / len(cells_)
    best = None
    for i in range(max(0, int(cx) - 80), min(NX, int(cx) + 80) + 1, 2):
        for j in range(max(0, int(cy) - 80), min(NY, int(cy) + 80) + 1, 2):
            if blkN[i * W + j]:
                continue
            ds = [bfs(c)[i * W + j] for c in cells_]
            if min(ds) < 0:
                continue
            v = max(ds)
            if best is None or v < best[0]:
                best = (v, (i, j))
    return best[1]


# ---- liberty NLDM (same constants as su_tree_model.py / plan_r5) ----
SIZES = ["BUFx8_ASAP7_75t_R", "BUFx10_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R", "BUFx16f_ASAP7_75t_R",
         "BUFx24_ASAP7_75t_R"]
REP = "BUFx16f_ASAP7_75t_R"
BIG = "BUFx24_ASAP7_75t_R"
LIBS = {k: lib.cells(str(LIBDIR / f"invbuf_{k.lower()}.lib"), SIZES) for k in ("TT", "FF")}
FFC = {"TT": 0.474736, "FF": 0.522010}
r = 0.5 * (1.80365e-2 + 1.89935e-2) * 0.8
c = 0.5 * (1.78475e-1 + 1.64264e-1) * 0.9


def interp(tab, s, C):
    i1, i2, v = tab

    def idx(a, x):
        for k in range(len(a) - 1):
            if x <= a[k + 1]:
                return k
        return len(a) - 2
    a = idx(i1, s)
    b = idx(i2, C)
    ta = (s - i1[a]) / (i1[a + 1] - i1[a])
    tb = (C - i2[b]) / (i2[b + 1] - i2[b])
    return v[a][b] * (1 - ta) * (1 - tb) + v[a + 1][b] * ta * (1 - tb) + v[a][b + 1] * (1 - ta) * tb + v[a + 1][b + 1] * ta * tb


def stage(corner, cname, sin, fo, w, cp):
    """driver cname, input slew sin, fo branches of wire w each ending in pin cap cp -> (delay to branch end, slew)."""
    L = LIBS[corner][cname]
    C = fo * (c * w + cp)
    d = 0.5 * (interp(L["rise"], sin, C) + interp(L["fall"], sin, C))
    so = interp(L["trise"], sin, C)
    return d + r * w * (c * w / 2 + cp), so


def mst(ptsl):
    n = len(ptsl)
    inn = [False] * n
    dd = [1e18] * n
    dd[0] = 0
    tot = 0
    for _ in range(n):
        u = min((i for i in range(n) if not inn[i]), key=lambda i: dd[i])
        inn[u] = True
        tot += dd[u]
        for v in range(n):
            if not inn[v]:
                e = man(ptsl[u], ptsl[v])
                if e < dd[v]:
                    dd[v] = e
    return tot


def level_chain(corner, drv, sin, fo, T, K, nxt_cin):
    """one level: driver drv with fanout fo into K equal segments (K-1 REP repeaters) of total length T."""
    w = T / K
    t = 0.0
    s = sin
    for i in range(K):
        cp = LIBS[corner][REP]["cin"] if i < K - 1 else nxt_cin
        d, s = stage(corner, drv if i == 0 else REP, s, fo if i == 0 else 1, w, cp)
        t += d
    return t, s


LAT_, ISL_, ISL_TOL = 4.32, 8.64, 5.4


def _isl_rect_ok(R, taken):
    if R[0] < core[0] - 1e-6 or R[1] < core[1] - 1e-6 or R[2] > core[2] + 1e-6 or R[3] > core[3] + 1e-6:
        return False
    for _, r_ in macros:
        if R[0] < r_[2] + ROW_HALO and R[2] > r_[0] - ROW_HALO and R[1] < r_[3] + ROW_HALO and R[3] > r_[1] - ROW_HALO:
            return False
    for q in PIN_COLS + taken:
        if R[0] < q[2] and R[2] > q[0] and R[1] < q[3] and R[3] > q[1]:
            return False
    return True


def _ent_rect():
    e0 = [math.floor(entry[0] / LAT_) * LAT_, math.floor(entry[1] / LAT_) * LAT_]
    e0 = [e0[0] - LAT_ if entry[0] - e0[0] < LAT_ / 2 else e0[0], e0[1] - LAT_ if entry[1] - e0[1] < LAT_ / 2 else e0[1]]
    return [e0[0], e0[1], e0[0] + ISL_, e0[1] + ISL_]


_RECTS = None


def _all_rects():
    global _RECTS
    if _RECTS is None:
        D = bfs(cell(entry))
        er = _ent_rect()
        out = []
        for a in range(int(core[0] / LAT_), int(core[2] / LAT_) + 1):
            for b in range(int(core[1] / LAT_), int(core[3] / LAT_) + 1):
                R = [round(a * LAT_, 3), round(b * LAT_, 3), round(a * LAT_ + ISL_, 3), round(b * LAT_ + ISL_, 3)]
                if not _isl_rect_ok(R, [er]):
                    continue
                cc = cell(((R[0] + R[2]) / 2, (R[1] + R[3]) / 2))
                if D[cc[0] * W + cc[1]] < 0:
                    continue
                out.append((R, cc, D[cc[0] * W + cc[1]] * G))
        _RECTS = out
    return _RECTS


def legal_sites(cs):
    """su_tree_uf_ls.py: each island = the legal 8.64 island rect (rows, outside macro ROW halo + SRAM clock-pin columns,
    not on the entry / another island) whose centre is nearest (Manhattan) to its cluster median; larger clusters first."""
    taken, sites = [], [None] * len(cs)
    sizes = [0] * len(cs)
    for p in sinks:
        sizes[min(range(len(cs)), key=lambda q: man(p, cs[q]))] += 1
    for q in sorted(range(len(cs)), key=lambda q: -sizes[q]):
        best = None
        for R, cc, d in _all_rects():
            if not _isl_rect_ok(R, taken):
                continue
            ctr = ((R[0] + R[2]) / 2, (R[1] + R[3]) / 2)
            v = man(ctr, cs[q])
            if best is None or v < best[0]:
                best = (v, R, cc)
        taken.append(best[1])
        sites[q] = best[2]
    return sites, None


def plan(k):
    cs = kmeans(sinks, k)
    isl, _reach = legal_sites(cs)
    for q in isl:
        bfs(q)
    scell = {s: cell(s[:2]) for s in sinks}
    groups = [[] for _ in isl]
    for s in sinks:
        sc = scell[s]
        groups[min(range(k), key=lambda q: (_bfs[isl[q]][sc[0] * W + sc[1]] if _bfs[isl[q]][sc[0] * W + sc[1]] >= 0
                                            else 1e9))].append(s)
    keep = [i for i, g in enumerate(groups) if g]
    isl = [isl[i] for i in keep]
    groups = [groups[i] for i in keep]
    k = len(isl)
    # re-site each island at the legal cell minimising its group's max maze reach to the group's quartile points
    n = len(sinks)
    raw = [NL * len(g) / n for g in groups]
    m = [max(1, int(v)) for v in raw]
    for i in sorted(range(k), key=lambda i: -(raw[i] - int(raw[i]))):
        if sum(m) >= NL:
            break
        m[i] += 1
    while sum(m) > NL:
        i = max(range(k), key=lambda i: m[i] - raw[i])
        m[i] -= 1
    # equal sink load per leaf: global leaf size n / NL; island i keeps its own sinks, leaves split them evenly
    tree = []                                    # (q, b, l, sinks)
    Bs = {}
    for q, g in enumerate(groups):
        nb = math.ceil(m[q] / 4)
        lpb = [m[q] // nb + (1 if i < m[q] % nb else 0) for i in range(nb)]
        tb = [round(len(g) * v / m[q]) for v in lpb]
        tb[-1] = len(g) - sum(tb[:-1])
        for b, bg in enumerate(split(g, tb)):
            tl = [len(bg) // lpb[b] + (1 if i < len(bg) % lpb[b] else 0) for i in range(lpb[b])]
            for li, lg in enumerate(split(bg, tl)):
                tree.append((q, b, li, lg))
            Bs[(q, b)] = lpb[b]
    leafc = {(q, b, l): centroid(lg) for q, b, l, lg in tree}
    Bc = {qb: best_site([v for kk, v in leafc.items() if kk[:2] == qb]) for qb in Bs}
    ent = cell(entry)
    L1 = [md(ent, isl[q]) for q in range(k)]
    L2 = [md(isl[qb[0]], v) for qb, v in Bc.items()]
    L3 = [md(Bc[kk[:2]], v) for kk, v in leafc.items()]
    T1, T2, T3 = max(L1), max(L2), max(L3)
    K1, K2, K3 = (max(1, math.ceil(t / SMAX)) for t in (T1, T2, T3))
    nB = {q: sum(1 for qb in Bs if qb[0] == q) for q in range(k)}
    # ---- per-branch driver sizing (12.8 d1): reference = the max-fanout node of each level driven by BIG
    sizing = {}
    pred = {}
    for corner in ("TT", "FF"):
        cin = {s_: LIBS[corner][s_]["cin"] for s_ in SIZES}
        s0 = 20.0
        t1, s1 = level_chain(corner, BIG, s0, k, T1, K1, cin[BIG])
        # level 2 reference: island driver BIG with the largest B fanout
        fo2 = max(nB.values())
        ref2, _ = level_chain(corner, BIG, s1, fo2, T2, K2, cin[BIG])
        fo3 = max(Bs.values())
        ref3, _ = level_chain(corner, BIG, s1, fo3, T3, K3, cin[BIG])   # slew approx: level-1 output slew
        res = {}
        for q in range(k):
            if corner == "TT":
                sizing[("Q", q)] = min(SIZES, key=lambda s_: abs(level_chain("TT", s_, s1, nB[q], T2, K2,
                                                                             cin[BIG])[0] - ref2))
            t2, s2 = level_chain(corner, sizing[("Q", q)], s1, nB[q], T2, K2, cin[BIG])
            for (qq, b), fo in Bs.items():
                if qq != q:
                    continue
                if corner == "TT":
                    sizing[("B", q, b)] = min(SIZES, key=lambda s_: abs(level_chain("TT", s_, s2, fo, T3, K3,
                                                                                    cin[BIG])[0] - ref3))
                t3, s3 = level_chain(corner, sizing[("B", q, b)], s2, fo, T3, K3, cin[BIG])
                for q2, b2, l, lg in tree:
                    if (q2, b2) != (q, b):
                        continue
                    lc = xy(leafc[(q, b, l)])
                    wl = mst([lc] + [p[:2] for p in lg])
                    C = c * wl + len(lg) * FFC[corner]
                    L = LIBS[corner][BIG]
                    d = 0.5 * (interp(L["rise"], s3, C) + interp(L["fall"], s3, C))
                    rad = sum(man(p, lc) for p in lg) / len(lg)
                    res[f"Q{q}B{b}L{l}"] = round(t1 + t2 + t3 + d + r * rad * C / 2, 2)
        v = list(res.values())
        pred[corner] = dict(mean=round(sum(v) / len(v), 2), min=min(v), max=max(v), window=round(max(v) - min(v), 2),
                            leaf=res)
    return dict(k=k, islands=[xy(q) for q in isl], island_sinks=[len(g) for g in groups], leaves_per_island=m,
                B_per_island=[nB[q] for q in range(k)], leaves_per_B={f"Q{q}B{b}": v for (q, b), v in Bs.items()},
                leaf_load=[min(len(x[3]) for x in tree), max(len(x[3]) for x in tree)],
                level_len_um=dict(T1=round(T1, 2), T2=round(T2, 2), T3=round(T3, 2)),
                shortest_um=dict(L1=[round(min(L1), 2), round(max(L1), 2)], L2=[round(min(L2), 2), round(max(L2), 2)],
                                 L3=[round(min(L3), 2), round(max(L3), 2)]),
                repeaters_per_edge=dict(K1=K1 - 1, K2=K2 - 1, K3=K3 - 1),
                sizing={"_".join(map(str, kk)): v for kk, v in sizing.items()},
                B_sites={f"Q{q}B{b}": xy(v) for (q, b), v in Bc.items()},
                leaf_sites={f"Q{q}B{b}L{l}": xy(v) for (q, b, l), v in leafc.items()},
                pred={kk: {a: b for a, b in v.items() if a != "leaf"} for kk, v in pred.items()}, pred_leaf=pred)


runs = []
for k in range(KMIN, KMAX + 1):
    p = plan(k)
    runs.append(p)
    print(k, p["island_sinks"], p["B_per_island"], p["level_len_um"], p["pred"]["TT"], p["pred"]["FF"], flush=True)
best = min(runs, key=lambda p: (p["pred"]["TT"]["window"] > 20, max(0.0, p["pred"]["TT"]["mean"] - 270.0),
                                p["pred"]["TT"]["window"], abs(p["pred"]["TT"]["mean"] - 250.0)))
rep = dict(scope="PLAN MODEL ONLY (liberty NLDM + setRC x rc_cal 0.8/0.9, Elmore, leaf MST; no measured input); "
                 "UNCHECKED", geo=geo, entry=list(entry), smax_um=SMAX, n_sinks=len(sinks), n_leaves=NL,
           choice="k with TT window <= 20 and mean <= 270 first, then smallest window, then mean nearest 250",
           best=best, search=[{kk: v for kk, v in p.items() if kk not in ("pred_leaf", "leaf_sites", "B_sites")}
                              for p in runs])
Path(out).write_text(json.dumps(rep, indent=1))
print("BEST", best["k"], best["pred"])
