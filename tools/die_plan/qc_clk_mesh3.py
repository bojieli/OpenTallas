#!/usr/bin/env python3
"""QC-CLK-MESH-3 (12.8e/12.8e1 continuous die mesh, r3): fewer, wider top stages + coarse SPINE mesh + d1 plan-computed
driver sizing (COORD ruling QC-CLK-MESH-2, spec r3 in lanes/QC-CLK-MESH.md).

Structure (all straight legs, no detour; every tree edge routed length == its Manhattan length):
  die input -> trunk -> TOP TREE (wide shielded M9 vertical / M8 horizontal, multi-BUFx24 stages at the SPICE reach)
  -> SPINE drivers at spine-column x gap-row crossings -> SPINE MESH (wide M8 straps on every nk gap row + wide M9 straps
  on every spine column, all in channels free over the full height) -> COLUMN TREES (tap on the spine M8 strap at every
  fine driver column, binary y-tree over the 2m+1 driver rows of the group, <= 4 stages) -> FINE MESH (r2 lattice) ->
  partition entry taps.
  Trees are DELAY-balanced (zero-skew merge with the SPICE stage table, node on the straight segment between the two
  child roots; never a detour) instead of length-balanced: r2's equal-length legs still left 37 ps nominal spread from
  the nonlinear stage delay.  d1: every spine / fine driver is sized from its own plan load (L1-Voronoi strap C) so all
  drivers see the same R_th * C (plan-computed, 12.8; no post-sim trim).

  plan   : build the structure, budgets, render.
  solve  : cascade whole-die linear transient (spine mesh -> column trees -> fine mesh), Thevenin BUFx24 from r2
           (thev_r2.json), hierarchical MC: one Gaussian per tree edge (sigma_stage(type) * sqrt(stages)), per-driver Vt,
           wire 5 %, optional across-die systematic gradient (12.4a b1 g, random direction per sample).
  pairs  : 773 seam pairs, signed-mesh common point (12.4a b exception): mesh uncertainty = the pair's worst MC tap
           difference; below the mesh the APPROVED AOCV table (class A depth sigma, g = 0.21 %/mm distance term,
           differential droop 0 within the one mesh) -> hold pessimism per pair + HOLD-REPAIR demand fragment.
  em     : per-driver J_avg / J_rms / J_peak on the driver-adjacent strap pieces (r2 method, budgets_em.json).
All numbers UNCHECKED until NUMBER-CHECK.
"""
import argparse
import json
import math
import random
import sys
import zlib
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qc_clk_mesh2 as M2  # noqa: E402

ISL = 8.64
VDD = {"TT": 0.70, "FF": 0.77}
F_CLK = 1.2e9
BUF_CIN_FF = 2.3
# QC-CLK-MESH-3 RC (fd2d.py + asap7_m8m9_cal.json of CLOCK-128-R6, claude/clock128-r7-1026; shields 0.04 um at 0.08 um
# both sides): R = R6 rules R / w; C over a full lower-metal plane (M8 over M7, M9 over M8) -- the routed environment
# (signals FT <= M7, M8 straps under M9).  ohm/um, fF/um.  fd2d reproduces R6 0.16 um (0.2465 vs 0.248).  UNCHECKED vs a
# commercial solver.  r2 used the over-substrate C (0.188) and an extrapolated 8W C; r3 C is HIGHER (conservative).
RC3 = {"4w": {"M8": (2.115, 0.2465), "M9": (2.228, 0.2403)},
       "8w": {"M8": (1.058, 0.3352), "M9": (1.114, 0.3282)},
       "16w": {"M8": (0.529, 0.5022), "M9": (0.557, 0.4938)},
       "2x16w": {"M8": (0.2645, 1.0044), "M9": (0.2785, 0.9876)}}
WIDTH_UM = {"4w": 0.16, "8w": 0.32, "16w": 0.64, "2x16w": 1.28}
T_CU_UM = 0.065          # r2 EM method (t from Rs, conservative)
MULT_SET = [0.5, 0.667, 1.0, 1.5, 1.667, 2.0]      # BUFx12f / BUFx16f / BUFx24 / x24+x12 / x24+x16 / 2 x BUFx24


def r3(v):
    return round(float(v), 3)


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ------------------------------------------------------------------------------------------------ stage model
D0 = {"TT": 34.0, "FF": 27.2}


class Stage:
    """D_seg(L) per (width, mult, corner) = quadratic fit of the ngspice stage table; reach = max L at slew <= 320."""

    def __init__(self, table):
        T = json.loads(Path(table).read_text())
        self.rows = [r for r in T["rows"] if "error" not in r]
        self.reach = T["reach"]
        self.fit = {}
        import numpy as np
        for key in {(r["w"], r["mult"], r["corner"]) for r in self.rows}:
            rr = sorted((r for r in self.rows if (r["w"], r["mult"], r["corner"]) == key), key=lambda r: r["L"])
            L = np.array([r["L"] for r in rr], float)
            D = np.array([r["stage_ps"] for r in rr], float)
            S = np.array([r["sigma_stage_ps"] for r in rr], float)
            # short legs (< 450 um): anchor L = 0 at the BUFx24 intrinsic delay (thev_r2 d_int 34.0 TT / 27.2 FF) so
            # the quadratic never extrapolates below it (UNCHECKED interpolation; sigma below 450 = sigma(450), conservative)
            c = np.polyfit(np.concatenate([[0.0], L]), np.concatenate([[D0[key[2]]], D]), 2)
            self.fit[key] = dict(c=[float(x) for x in c], L=L.tolist(), D=D.tolist(), sig=S.tolist(),
                                 slew=[r["slew1090_ps"] for r in rr])

    def seg(self, w, m, c, L):
        f = self.fit[(w, m, c)]["c"]
        return sum(k * L ** (len(f) - 1 - i) for i, k in enumerate(f))

    def sigma(self, w, m, c, L):
        f = self.fit[(w, m, c)]
        Ls, S = f["L"], f["sig"]
        if L <= Ls[0]:
            return S[0]
        for a, b, sa, sb in zip(Ls, Ls[1:], S, S[1:]):
            if L <= b:
                return sa + (sb - sa) * (L - a) / (b - a)
        return S[-1]

    def slew(self, w, m, c, L):
        f = self.fit[(w, m, c)]
        Ls, S = f["L"], f["slew"]
        for a, b, sa, sb in zip(Ls, Ls[1:], S, S[1:]):
            if L <= b:
                return sa + (sb - sa) * max(0.0, L - a) / (b - a)
        return S[-1]


class EdgeType:
    def __init__(self, st, w, m, reach):
        self.st, self.w, self.m, self.reach = st, w, m, reach

    def nseg(self, L):
        return max(1, math.ceil(L / self.reach - 1e-9))

    def delay(self, L, c, n=None):
        n = n or self.nseg(L)
        return n * self.st.seg(self.w, self.m, c, L / n)

    def sigma(self, L, c, n=None):
        n = n or self.nseg(L)
        return self.st.sigma(self.w, self.m, c, L / n) * math.sqrt(n)


# ------------------------------------------------------------------------------------------------ delay-balanced tree
def dtree(leaves, ax, et, tag, nodes, leafmk=None):
    """binary zero-skew (TT) merge over leaves sorted along ax; node on the straight segment between the child roots."""
    if len(leaves) == 1:
        n = leafmk(leaves[0], tag) if leafmk else dict(tag=tag, xy=leaves[0], kids=[], T={"TT": 0.0, "FF": 0.0}, S=0)
        if not leafmk:
            nodes.append(n)
        return n
    h = len(leaves) // 2
    A = dtree(leaves[:h], ax, et, tag + "0", nodes, leafmk)
    B = dtree(leaves[h:], ax, et, tag + "1", nodes, leafmk)
    return merge(A, B, ax, et, tag, nodes)


BLOCK = [None]          # predicate xy -> True when a buffer site there would sit on a hard core (+ISL)


def _leg_blocked(p, q, n):
    f = BLOCK[0]
    if f is None:
        return False
    return any(f((p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n)) for k in range(1, n))


def merge(A, B, ax, et, tag, nodes):
    """equal STAGE count on every root->leaf path (the short side gets extra repeaters in its straight leg, r2 rule) and
    zero TT delay difference by the node position on the straight segment between the two child roots (no detour)."""
    i = 0 if ax == "x" else 1
    pa, pb = A["xy"][i], B["xy"][i]
    e = abs(A["xy"][1 - i] - B["xy"][1 - i])           # perpendicular offset (0 on a lattice row/column)
    lo, hi = min(pa, pb), max(pa, pb)
    best = None
    cands = []
    steps = max(1, int((hi - lo) / 1.0))

    def ns(la, lb):
        na0, nb0 = et.nseg(la), et.nseg(lb)
        tot = max(A["S"] + na0, B["S"] + nb0)
        return tot - A["S"], tot - B["S"]
    for k in range(steps + 1):
        p = lo + (hi - lo) * k / steps
        la, lb = abs(p - pa) + e, abs(pb - p)
        na, nb = ns(la, lb)
        d = (A["T"]["TT"] + et.delay(la, "TT", na)) - (B["T"]["TT"] + et.delay(lb, "TT", nb))
        sc = (round(abs(d), 2), na + nb, abs(p - (lo + hi) / 2))
        cands.append((sc, p, la, lb, d, na, nb))
    cands.sort(key=lambda r: r[0])
    for cnd in cands:            # GEOM-REVIEW-10: best-scoring node site with no node / repeater on a hard core
        xy_ = (cnd[1], A["xy"][1]) if ax == "x" else (A["xy"][0], cnd[1])
        if BLOCK[0] is None or not (BLOCK[0](xy_) or _leg_blocked(xy_, A["xy"], cnd[5]) or _leg_blocked(xy_, B["xy"], cnd[6])):
            best = cnd
            break
    if best is None:                                   # every node site blocked: fall back (reported by legalize as in-core)
        BLOCK[0], keep = None, BLOCK[0]
        try:
            return merge(A, B, ax, et, tag, nodes)
        finally:
            BLOCK[0] = keep
    _, p, la, lb, d, na, nb = best
    xy = (p, A["xy"][1]) if ax == "x" else (A["xy"][0], p)
    for ch, L, n_ in ((A, la, na), (B, lb, nb)):
        ch["parent"], ch["leg"], ch["nseg"], ch["et"] = tag, L, n_, et
    T = {c: max(A["T"][c] + et.delay(la, c, na), B["T"][c] + et.delay(lb, c, nb)) for c in ("TT", "FF")}
    n = dict(tag=tag, xy=xy, kids=[A["tag"], B["tag"]], T=T, S=A["S"] + na,
             imbalance_TT=r3(d), imbalance_FF=r3((A["T"]["FF"] + et.delay(la, "FF", na)) - (B["T"]["FF"] + et.delay(lb, "FF", nb))))
    nodes.append(n)
    return n


def lift(r, xy, et, tag, nodes):
    """one straight leg from xy to the subtree root r (|dx| or |dy| only)."""
    L = md(xy, r["xy"])
    r["parent"], r["leg"], r["nseg"], r["et"] = tag, L, et.nseg(L), et
    n = dict(tag=tag, xy=xy, kids=[r["tag"]], T={c: r["T"][c] + et.delay(L, c, r["nseg"]) for c in ("TT", "FF")}, S=r["S"] + r["nseg"])
    nodes.append(n)
    return n


# ------------------------------------------------------------------------------------------------ plan
def lattice(a):
    """r2 fine lattice (same columns / gaps / rows as r2_plan_m4f) + the r2 plan record."""
    rec = json.loads(Path(a.r2).read_text())
    import qc_clk_mesh as Q
    P, dtp, parts, cores, psha = Q.load(rec["plan"], rec["tree_plan"])
    xs = [r3(x) for x in rec["xs"]]
    # GEOM-REVIEW-10 (1): keep ALL array channels.  r2 dropped the channels crossed by one crh core (276 of 26266 um);
    # r3 keeps them as driver columns and drops only the driver rows whose site is on that core (+ISL).  Channels off the
    # fine-mesh extent (x < first M9 strap, the die-edge keep-out) carry no fine strap and stay out.
    # the driver column sits on the channel's M9 fine strap (3 channels have it 8.64 um off the channel centre)
    added = []
    for x in rec.get("blocked_channels", []):
        v = min(xs, key=lambda q: abs(q - x))
        if xs[0] <= x <= xs[-1] and abs(v - x) <= 2 * ISL + 1e-6:
            added.append(r3(v))
    cols = sorted({r3(x) for x in rec["driver_columns"]} | set(added))
    lattice.added = added
    drv = [n for n in rec["nodes"] if n["driver"]]
    rows = sorted({r3(n["site"][1]) for n in drv})
    m = (len(rows) // 19 - 1) // 2 if len(rows) % 19 == 0 else 4
    ng = len(rows) // (2 * m + 1)
    gaps = [rows[g * (2 * m + 1) + m] for g in range(ng)]
    dy = r3(rows[1] - rows[0])
    return rec, P, dtp, parts, cores, cols, gaps, rows, m, dy


def build(a, st):
    rec, P, dtp, parts, cores, cols, gaps, rows, m, dy = lattice(a)
    free = lambda x: not any(c[0] - ISL < x < c[2] + ISL for c in cores)
    bk = defaultdict(list)
    for c in cores:
        for ix in range(int((c[0] - ISL) // 500), int((c[2] + ISL) // 500) + 1):
            bk[ix].append(c)
    incore = lambda q: any(c[0] - ISL < q[0] < c[2] + ISL and c[1] - ISL < q[1] < c[3] + ISL for c in bk.get(int(q[0] // 500), ()))
    BLOCK[0] = incore
    dropped = []
    top = EdgeType(st, a.top_w, a.top_m, a.top_reach)
    col = EdgeType(st, a.col_w, a.col_m, a.col_reach)
    scols = list(cols) if a.no_spine else cols[a.spine_off::a.spine_stride]
    if cols[-1] not in scols and a.spine_stride > 1 and cols[-1] - scols[-1] > (scols[1] - scols[0]) * 0.75:
        scols.append(cols[-1])
    nodes = []
    # TOP TREE: per gap row an x-tree along the row over the spine columns, then a y-tree over the rows in one free
    # channel (every group root has the same x: identical x-trees).  The group-root x is moved to the nearest FREE
    # column by one equal leg per group (same for all).
    groots = []
    for gi, g in enumerate(gaps):
        r = dtree([(x, g) for x in scols], "x", top, f"t{gi:02d}_", nodes)
        if not free(r["xy"][0]):
            xc = min(cols, key=lambda x: abs(x - r["xy"][0]))
            r = lift(r, (xc, g), top, f"t{gi:02d}_L", nodes)
        groots.append(r)
    xs0 = {r3(r["xy"][0]) for r in groots}
    assert len(xs0) == 1, xs0

    def ytree(items, tag):
        if len(items) == 1:
            return items[0]
        h = len(items) // 2
        return merge(ytree(items[:h], tag + "0"), ytree(items[h:], tag + "1"), "y", top, tag, nodes)
    root = ytree(groots, "T")
    root["parent"] = None
    spine_drv = [n for n in nodes if not n["kids"]]
    # COLUMN TREES: tap on the spine M8 strap at (x_c, g); y-tree over the 2m+1 rows; tap buffer drives a straight leg
    # to the column-tree root (on the same column).
    ctrees = []
    cnodes = []
    BLOCK[0] = None        # column trees: identical topology on every column; buffers over the 276-um core are moved
                           # along their own column wire by legalize() (reported as bumps)
    for gi, g in enumerate(gaps):
        grow = rows[gi * (2 * m + 1):(gi + 1) * (2 * m + 1)]
        for ci, x in enumerate(cols):
            # full 2m+1-row tree (same topology / stage count / balance as every other column), then the driver rows on a
            # hard core of an ADDED channel are pruned with any branch left without a driver (r2 columns keep r2 drivers)
            leaves = [(x, y) for y in grow]
            t0 = len(cnodes)
            r = dtree(leaves, "y", col, f"c{gi:02d}_{ci:02d}_", cnodes)
            r = lift(r, (x, g), col, f"c{gi:02d}_{ci:02d}_tap", cnodes) if md(r["xy"], (x, g)) > 1e-6 else r
            r["parent"] = None
            if r3(x) in lattice.added:
                cut = {n["tag"] for n in cnodes[t0:] if not n["kids"] and incore(n["xy"])}
                dropped += [tuple(n["xy"]) for n in cnodes[t0:] if n["tag"] in cut]
                while True:
                    more = set()
                    for n in cnodes[t0:]:
                        if n["tag"] in cut:
                            continue
                        if n["kids"]:
                            n["kids"] = [k for k in n["kids"] if k not in cut]
                            if not n["kids"]:
                                more.add(n["tag"])
                    if not more:
                        break
                    cut |= more
                cnodes[t0:] = [n for n in cnodes[t0:] if n["tag"] not in cut]
                assert r["tag"] not in cut
            ctrees.append(dict(g=gi, c=ci, tap=(x, g), root=r["tag"], nodes=cnodes[t0:]))
    return dict(rec=rec, P=P, dtp=dtp, parts=parts, cores=cores, cols=cols, gaps=gaps, rows=rows, m=m, dy=dy,
                scols=scols, top_nodes=nodes, top_root=root, spine_drv=spine_drv, ctrees=ctrees, cnodes=cnodes,
                et=dict(top=top, col=col), free=free, incore=incore, added_cols=lattice.added, dropped_rows=dropped)


# ------------------------------------------------------------------------------------------------ legal sites
DX_LANE = 8.64      # column / trunk tree lane: buffers one ISL beside the driver column (same nk channel)
DY_LANE = 4.32      # top x-tree lane: buffers 16 rows above the gap-row strap line (fine drivers sit on the line)
CELL_W = 6.48       # BUFx24 footprint width incl. spacing (UNCHECKED vs LEF; conservative)
ROW_H = 0.27        # ASAP7 row


def legalize(B):
    """GEOM-REVIEW-10 (2): one legal site per cell.  Merges the zero-length level (top-tree leaf == column-tree tap
    buffer, one cell), puts tree buffers in lanes beside the fine-driver line, then bumps residual footprint overlaps
    along the lane.  Every net is a Manhattan L between its two cell sites (ratio 1.0 by construction)."""
    cells = []          # dict(kind, xy0, site, units, lane)
    side = {}

    def lane_sign(x):
        """tree lane on the wider side of the channel (nearest core edge left / right of the column, any y)."""
        k = r3(x)
        if k not in side:
            L = max([c[2] for c in B["cores"] if c[2] <= x + 1e-6] or [-1e9])
            R = min([c[0] for c in B["cores"] if c[0] >= x - 1e-6] or [1e9])
            side[k] = 1.0 if R - x >= x - L else -1.0
        return side[k]

    def add(kind, xy, units, lane):
        dx, dy = (DX_LANE * lane_sign(xy[0]), 0.0) if lane == "v" else ((0.0, DY_LANE) if lane == "h" else (0.0, 0.0))
        cells.append(dict(kind=kind, xy0=(r3(xy[0]), r3(xy[1])), site=[xy[0] + dx, xy[1] + dy], units=units, lane=lane))
        return len(cells) - 1
    top, col = B["et"]["top"], B["et"]["col"]
    site_of = {}
    tby = {n["tag"]: n for n in B["top_nodes"]}
    for n in B["top_nodes"]:
        if not n["kids"]:
            continue          # top leaf = column tap cell (merged level), added with the column tree
        site_of[("t", n["tag"])] = add("top_node", n["xy"], top.m, "v" if n["tag"].startswith("T") else "h")
    for ct in B["ctrees"]:
        for n in ct["nodes"]:
            if not n["kids"]:
                site_of[("c", n["tag"])] = add("fine_driver", n["xy"], 2, "d")
            else:
                site_of[("c", n["tag"])] = add("col_tap" if not n.get("parent") else "col_node", n["xy"], col.m, "v")
    leafpos = {(r3(n["xy"][0]), r3(n["xy"][1])): n["tag"] for n in B["top_nodes"] if not n["kids"]}
    ctap = {(r3(ct["tap"][0]), r3(ct["tap"][1])): ct for ct in B["ctrees"]}
    assert set(leafpos) == set(ctap), "top leaves must coincide with column taps (merged level)"
    nrep = {"top": 0, "col": 0}
    for kind, nodes, et in (("top", B["top_nodes"], top), ("col", B["cnodes"], col)):
        by = {n["tag"]: n for n in nodes}
        for n in nodes:
            if not n.get("parent"):
                continue
            p = by[n["parent"]]["xy"]
            lane = "h" if abs(p[1] - n["xy"][1]) < 1e-6 and abs(p[0] - n["xy"][0]) > 1e-6 else "v"
            for k in range(1, n["nseg"]):
                q = (p[0] + (n["xy"][0] - p[0]) * k / n["nseg"], p[1] + (n["xy"][1] - p[1]) * k / n["nseg"])
                add(kind + "_rep", q, et.m, lane)
                nrep[kind] += 1
    # exact coincidences before the bump (the GEOM-REVIEW-10 metric on the raw tree coordinates)
    from collections import Counter
    raw = Counter((r3(c["site"][0]), r3(c["site"][1])) for c in cells)
    pre_coinc = sum(v for v in raw.values() if v > 1)
    # footprint occupancy on a (CELL_W x ROW_H) grid; bump along the lane until free and off-core
    occ = set()
    bumped, maxbump = 0, 0.0
    inc = B["incore"]

    def boxes(site, units):
        ix = int(math.floor(site[0] / CELL_W + 0.5))
        iy = int(math.floor(site[1] / ROW_H + 0.5))
        return [(ix, iy + u) for u in range(units)]
    order = sorted(range(len(cells)), key=lambda i: (cells[i]["kind"] != "fine_driver", i))   # drivers keep the strap sites
    for i in order:
        c = cells[i]
        s0 = list(c["site"])
        step = (0.0, ROW_H * c["units"]) if c["lane"] in ("v", "d") else (CELL_W, 0.0)
        for t in range(2400):
            sgn = 1 if t % 2 == 0 else -1
            k = (t + 1) // 2
            cand = [s0[0] + sgn * k * step[0], s0[1] + sgn * k * step[1]]
            b = boxes(cand, c["units"])
            r2site = c["kind"] == "fine_driver" and r3(c["xy0"][0]) not in B["added_cols"]   # r2 driver: r2-legal site
            if not any(q in occ for q in b) and (r2site or not inc(cand)):
                break
        else:
            raise RuntimeError(f"no legal site near {s0}")
        if t:
            bumped += 1
            maxbump = max(maxbump, md(cand, s0))
        c["site"] = cand
        occ.update(b)
    post = Counter((r3(c["site"][0]), r3(c["site"][1])) for c in cells)
    strict = lambda q: any(c[0] < q[0] < c[2] and c[1] < q[1] < c[3] for c in B["cores"])
    oncore = sum(1 for c in cells if strict(c["site"]))
    near_isl = sum(1 for c in cells if inc(c["site"]))
    # merged-level check: every column tap cell is ALSO the top-tree leaf (one cell, no zero-length edge)
    stats = dict(cells=len(cells), by_kind=dict(Counter(c["kind"] for c in cells)), raw_coincident_items=pre_coinc,
                 coincident_items=sum(v for v in post.values() if v > 1), footprint_overlaps=0, cells_on_core=oncore,
                 cells_within_ISL_of_core=near_isl, cells_within_ISL_note="r2 fine-driver sites kept as r2 placed them (r2 seam_channel)",
                 bumped=bumped, max_bump_um=r3(maxbump), merged_top_leaf_eq_col_tap=len(ctap),
                 lane_offsets_um=dict(dx_tree_lane=DX_LANE, dy_top_lane=DY_LANE, lanes_left=sum(1 for v in side.values() if v < 0),
                                      lanes_right=sum(1 for v in side.values() if v > 0)), repeaters=nrep,
                 max_net_extra_vs_leg_um=r3(DX_LANE + DY_LANE + maxbump),
                 note="net = Manhattan L between cell sites (ratio 1.0); planned legs differ by <= max_net_extra_vs_leg_um, "
                      "same on every root->driver path of a level (common, not skew). UNCHECKED")
    return cells, stats


def paths(nodes):
    by = {n["tag"]: n for n in nodes}
    out = {}
    for n in nodes:
        if n["kids"]:
            continue
        ch, t = [], n
        while t.get("parent"):
            ch.append(t)
            t = by[t["parent"]]
        out[n["tag"]] = ch
    return out, by


def edge_geom(nodes):
    """every edge: straight leg parent->child, routed length = Manhattan (both share x or y by construction)."""
    by = {n["tag"]: n for n in nodes}
    rows = []
    for n in nodes:
        if not n.get("parent"):
            continue
        p = by[n["parent"]]
        man = md(p["xy"], n["xy"])
        straight = abs(p["xy"][0] - n["xy"][0]) < 1e-6 or abs(p["xy"][1] - n["xy"][1]) < 1e-6
        rows.append(dict(tag=n["tag"], p=p["xy"], q=n["xy"], leg_um=n["leg"], manhattan_um=man, straight=straight,
                         ratio=(n["leg"] / man) if man > 1e-9 else 1.0, nseg=n["nseg"]))
    return rows


def cmd_plan(a):
    st = Stage(a.stage)
    B = build(a, st)
    top, col = B["et"]["top"], B["et"]["col"]
    tp, _ = paths(B["top_nodes"])
    stages_top = sorted({sum(e["nseg"] for e in ch) for ch in tp.values()})
    arr_top = {c: [sum(e["et"].delay(e["leg"], c, e["nseg"]) for e in ch) for ch in tp.values()] for c in ("TT", "FF")}
    cp, _ = paths(B["cnodes"])
    stages_col = sorted({sum(e["nseg"] for e in ch) for ch in cp.values()})
    arr_col = {c: [sum(e["et"].delay(e["leg"], c, e["nseg"]) for e in ch) for ch in cp.values()] for c in ("TT", "FF")}
    eg = edge_geom(B["top_nodes"]) + edge_geom(B["cnodes"])
    on_core = lambda q: any(c[0] < q[0] < c[2] and c[1] < q[1] < c[3] for c in B["cores"])
    top_on_core = sum(1 for n in B["top_nodes"] if on_core(n["xy"]))
    # top-tree repeater sites (equal pieces along each leg): count those on a hard core (pushdown would be needed)
    rep_core, reps = 0, []
    by = {n["tag"]: n for n in B["top_nodes"]}
    for n in B["top_nodes"]:
        if not n.get("parent"):
            continue
        p = by[n["parent"]]["xy"]
        for k in range(1, n["nseg"]):
            q = (p[0] + (n["xy"][0] - p[0]) * k / n["nseg"], p[1] + (n["xy"][1] - p[1]) * k / n["nseg"])
            reps.append(q)
            rep_core += on_core(q)
    cells, lstat = legalize(B)
    B["cells"] = cells
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    plan = dict(legal=lstat, added_columns=B["added_cols"], dropped_driver_rows=B["dropped_rows"], driver_columns=len(B["cols"]),
                schema="ot_qc_clk_mesh3/1", argv=sys.argv, r2=a.r2, stage_table=a.stage,
                top=dict(w=top.w, mult=top.m, reach_um=top.reach), col=dict(w=col.w, mult=col.m, reach_um=col.reach),
                spine=dict(none=a.no_spine, w=a.spine_w, columns=B["scols"], rows=B["gaps"], drivers=len(B["spine_drv"]), base_mult=a.spine_m),
                fine=dict(w=a.fine_w, stub_w=a.stub_w, stub_um=a.stub_um, drivers=sum(1 for n in B["cnodes"] if not n["kids"])),
                stages=dict(top_root_to_spine_driver=stages_top, column_tap_to_fine_driver=stages_col,
                            root_to_fine_driver=sorted({a_ + b_ for a_ in stages_top for b_ in stages_col}),
                            note="top leaf IS the column-tap buffer (merged level, GEOM-REVIEW-10)", r2_root_to_driver=70),
                top_arr_spread_ps={c: r3(max(v) - min(v)) for c, v in arr_top.items()},
                top_arr_ps={c: r3(max(v)) for c, v in arr_top.items()},
                col_arr_spread_ps={c: r3(max(v) - min(v)) for c, v in arr_col.items()},
                col_arr_ps={c: r3(max(v)) for c, v in arr_col.items()},
                edges=dict(n=len(eg), straight=sum(e["straight"] for e in eg), max_ratio=r3(max(e["ratio"] for e in eg)),
                           over_1p10=[e["tag"] for e in eg if e["ratio"] > 1.10]),
                top_nodes_on_core=top_on_core, top_repeaters=len(reps), top_repeaters_on_core=rep_core,
                top_root_xy=B["top_root"]["xy"],
                top_wire_um=r3(sum(e["leg_um"] for e in edge_geom(B["top_nodes"]))),
                col_wire_um=r3(sum(e["leg_um"] for e in edge_geom(B["cnodes"]))),
                nodes=[dict(tag=n["tag"], xy=n["xy"], parent=n.get("parent"), leg=n.get("leg"), nseg=n.get("nseg"),
                            T=n["T"], imb=n.get("imbalance_TT")) for n in B["top_nodes"]],
                checked="UNCHECKED")
    (out / "r3_plan.json").write_text(json.dumps(plan, indent=1, default=str))
    print(json.dumps({k: v for k, v in plan.items() if k not in ("nodes", "argv")}, indent=1, default=str))
    if not a.no_render:
        render(B, plan, out / "r3_plan.png", None)
        cx, cy = B["P"].W / 2, B["P"].H / 2
        render(B, plan, out / "r3_zoom_centre.png", (cx - 2500, cy - 2000, cx + 2500, cy + 2000))
        if B["dropped_rows"]:
            q = min(B["dropped_rows"], key=lambda v: abs(v[0] - cx))
            render(B, plan, out / "r3_zoom_blocked.png", (q[0] - 700, q[1] - 550, q[0] + 700, q[1] + 550))
    return 0


def render(B, plan, path, box):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(16, 13.5))
    for p in B["parts"]:
        ax.add_patch(Rectangle((p[0], p[1]), p[2] - p[0], p[3] - p[1], fill=False, lw=0.3, ec="#999999"))
    for c in B["cores"]:
        ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fc="#e4e4e4", ec="none"))
    xs, ys = B["rec"]["xs"], B["rec"]["ys"]
    lw = 0.12 if box is None else 0.5
    for x in xs:
        ax.plot([x, x], [ys[0], ys[-1]], "-", c="#a9cbff", lw=lw)
    for y in ys:
        ax.plot([xs[0], xs[-1]], [y, y], "-", c="#bfe3bf", lw=lw)
    # spine mesh (not drawn for --no-spine: the top tree then feeds every column tap directly)
    for x in ([] if plan["spine"].get("none") else B["scols"]):
        ax.plot([x, x], [B["gaps"][0], B["gaps"][-1]], "-", c="#1f5fd0", lw=1.6)
    for y in ([] if plan["spine"].get("none") else B["gaps"]):
        ax.plot([B["cols"][0], B["cols"][-1]], [y, y], "-", c="#1a8a1a", lw=1.6)
    by = {n["tag"]: n for n in B["top_nodes"]}
    for n in B["top_nodes"]:
        if not n.get("parent"):
            continue
        p, q = by[n["parent"]]["xy"], n["xy"]
        ax.plot([p[0], q[0]], [p[1], q[1]], "-", c="k", lw=2.2)
        for k in range(1, n["nseg"]):
            ax.plot(p[0] + (q[0] - p[0]) * k / n["nseg"], p[1] + (q[1] - p[1]) * k / n["nseg"], "^", c="#c06000", ms=4 if box else 2.5)
    if box:
        cby = {n["tag"]: n for n in B["cnodes"]}
        for n in B["cnodes"]:
            if n.get("parent"):
                p, q = cby[n["parent"]]["xy"], n["xy"]
                ax.plot([p[0] + 6, q[0] + 6], [p[1], q[1]], "-", c="#8000a0", lw=1.0)
    sp = [n["xy"] for n in B["spine_drv"]]
    ax.plot([p[0] for p in sp], [p[1] for p in sp], "s", c="#d00000", ms=6 if box else 3.5, label=(f"column-tap buffer = top-tree leaf ({len(sp)})" if plan["spine"].get("none") else f"spine driver ({len(sp)})"))
    ax.plot(*B["top_root"]["xy"], "*", c="#ff00ff", ms=14, label="top-tree root")
    ax.plot([], [], "^", c="#c06000", label=f"top repeater ({plan['top_repeaters']})")
    if not plan["spine"].get("none"):
        ax.plot([], [], "-", c="#1f5fd0", lw=1.6, label=f"spine M9 {plan['spine']['w']} ({len(B['scols'])})")
        ax.plot([], [], "-", c="#1a8a1a", lw=1.6, label=f"spine M8 {plan['spine']['w']} ({len(B['gaps'])})")
    if box and B.get("cells"):
        for kind, mk, col_, lab in (("fine_driver", "o", "#2060ff", "fine driver"), ("col_node", "D", "#8000a0", "column-tree node"),
                                    ("col_rep", "v", "#8000a0", "column repeater"), ("col_tap", "s", "#d00000", None),
                                    ("top_node", "P", "#000000", "top-tree node")):
            q = [c["site"] for c in B["cells"] if c["kind"] == kind]
            if q and lab:
                ax.plot([v[0] for v in q], [v[1] for v in q], mk, c=col_, ms=3, mfc="none", label=f"{lab} legal site ({len(q)})")
        ax.plot([], [], "-", c="#8000a0", label="column y-trees (offset 6 um for view)")
    ax.set_aspect("equal")
    if box:
        ax.set_xlim(box[0], box[2])
        ax.set_ylim(box[1], box[3])
    else:
        ax.set_xlim(0, B["P"].W)
        ax.set_ylim(0, B["P"].H)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title(f"QC-CLK-MESH-3 r3: top tree {plan['top']['w']} x{plan['top']['mult']} BUFx24 reach {plan['top']['reach_um']} um, "
                 f"stages root->spine {plan['stages']['top_root_to_spine_driver']}, tap->fine {plan['stages']['column_tap_to_fine_driver']} "
                 f"(r2: 70); fine mesh r2 lattice. UNCHECKED", fontsize=9)
    fig.savefig(path, dpi=110 if box else 100, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ mesh netlist + solve
def mesh(hs, vs, drivers, taps, wtab, stub, seg_um=54.0, wire_rel=0.0, rnd=None):
    """hs: [(y, x0, x1)] M8, vs: [(x, y0, y1)] M9; drivers/taps: [(x, y)] on a strap.  Nodes keyed by coordinate.
    stub = (wtab_stub, length): pieces within `length` of a driver use the stub RC (EM straps)."""
    att_h, att_v = defaultdict(set), defaultdict(set)
    for y, x0, x1 in hs:
        att_h[y] |= {x0, x1}
    for x, y0, y1 in vs:
        att_v[x] |= {y0, y1}
    span_h = {y: (x0, x1) for y, x0, x1 in hs}
    span_v = {x: (y0, y1) for x, y0, y1 in vs}
    for y, (x0, x1) in span_h.items():
        for x, (y0, y1) in span_v.items():
            if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
                att_h[y].add(x)
                att_v[x].add(y)
    dset = set()
    for q in list(drivers) + list(taps):
        if q[1] in span_h:
            att_h[q[1]].add(q[0])
        elif q[0] in span_v:
            att_v[q[0]].add(q[1])
        else:
            raise SystemExit(f"point {q} not on a strap")
    dset = {tuple(q) for q in drivers}
    nid, xy = {}, []

    def node(q):
        k = (round(q[0], 3), round(q[1], 3))
        if k not in nid:
            nid[k] = len(nid)
            xy.append(k)
        return nid[k]
    R, C = [], defaultdict(float)
    sw, sl = stub

    def wire(a_, b_, layer):
        L = md(a_, b_)
        n = max(1, int(math.ceil(L / seg_um)))
        prev = node(a_)
        for q in range(1, n + 1):
            f0, f1 = (q - 1) / n, q / n
            pt = (a_[0] + (b_[0] - a_[0]) * f1, a_[1] + (b_[1] - a_[1]) * f1)
            cur = node(pt)
            mid0 = L * (f0 + f1) / 2
            near = (tuple(a_) in dset and mid0 <= sl) or (tuple(b_) in dset and L - mid0 <= sl)
            r, c = (sw if near else wtab)[layer]
            f = rnd.gauss(1.0, wire_rel) if (wire_rel and rnd) else 1.0
            R.append((prev, cur, r * L / n * f))
            C[prev] += c * L / n / 2 * f
            C[cur] += c * L / n / 2 * f
            prev = cur
    for y, pts in att_h.items():
        p = sorted(pts)
        for u, w in zip(p, p[1:]):
            wire((u, y), (w, y), "M8")
    for x, pts in att_v.items():
        p = sorted(pts)
        for u, w in zip(p, p[1:]):
            wire((x, u), (x, w), "M9")
    dn = [nid[(round(q[0], 3), round(q[1], 3))] for q in drivers]
    tn = [nid[(round(q[0], 3), round(q[1], 3))] for q in taps]
    return dict(R=R, C=C, xy=xy, dn=dn, tn=tn, n=len(nid))


def voronoi_c(N):
    """plan load per driver: strap C of the nodes whose nearest driver (L1) it is."""
    import numpy as np
    from scipy.spatial import cKDTree
    P = np.array(N["xy"])
    D = P[N["dn"]]
    _, idx = cKDTree(D).query(P, p=1)
    cv = np.zeros(len(P))
    for k, v in N["C"].items():
        cv[k] += v
    out = np.zeros(len(D))
    np.add.at(out, idx, cv)
    return out


def size(cvor, base, mode):
    import numpy as np
    if mode == "none":
        return np.full(len(cvor), float(base))
    ref = float(np.median(cvor))
    want = base * cvor / ref
    ms = np.array([base * m for m in MULT_SET])          # (a BUFx4-quantum variant measured worse nominal: 24.2 vs 20.2 ps)
    return ms[np.abs(ms[None, :] - want[:, None]).argmin(axis=1)]


def solve(N, arr, mult, dvt_mv, th, corner, extra_C=None, dt=0.5, t_extra=400.0):
    """backward-Euler linear transient; driver k = ramp (50 % at arr_k + d_int) behind R_th / mult_k + 51.2 ohm via.
    Returns per tap: t50 and 10-90 slew (ps, relative to min(arr))."""
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    n = N["n"]
    rows, cols, vals = [], [], []
    for a_, b_, r in N["R"]:
        g = 1.0 / max(r, 1e-6)
        rows += [a_, b_, a_, b_]
        cols += [a_, b_, b_, a_]
        vals += [g, g, -g, -g]
    Cv = np.zeros(n)
    for k, v in N["C"].items():
        Cv[k] += v * 1e-15
    for k in N["tn"]:
        Cv[k] += BUF_CIN_FF * 1e-15
    if extra_C is not None:
        Cv += extra_C
    dn = np.array(N["dn"])
    rth = (th["R_ohm"] + 51.2) / np.asarray(mult)      # each parallel BUFx24 has its own M1->M9 via stack
    gd = np.zeros(n)
    np.add.at(gd, dn, 1.0 / rth)
    G = sp.csc_matrix((vals, (rows, cols)), shape=(n, n)) + sp.diags(gd)
    dts = dt * 1e-12
    lu = spl.splu((G + sp.diags(Cv / dts)).tocsc())
    arr = np.asarray(arr, float)
    t0 = arr.min()
    t50 = arr - t0 + th["d_int_ps"] + th.get("dvt_ps_per_mV", 0.0) * np.asarray(dvt_mv)
    tr = th["tr_ps"]
    vdd = VDD[corner]
    T = t50.max() + tr + t_extra
    mi = np.array(N["tn"])
    v = np.zeros(n)
    lv = {q: np.full(len(mi), np.nan) for q in (0.1, 0.5, 0.9)}
    prev = np.zeros(len(mi))
    t = 0.0
    while t < T:
        t += dt
        vs = np.clip((t - (t50 - tr / 2)) / tr, 0.0, 1.0) * vdd
        rhs = Cv / dts * v
        np.add.at(rhs, dn, vs / rth)
        v = lu.solve(rhs)
        cur = v[mi]
        for q, arrq in lv.items():
            hit = np.isnan(arrq) & (cur >= q * vdd) & (prev < q * vdd)
            if hit.any():
                f = (q * vdd - prev[hit]) / np.maximum(cur[hit] - prev[hit], 1e-12)
                arrq[hit] = t - dt + f * dt
        prev = cur
        if not np.isnan(lv[0.9]).any():
            break
    return lv[0.5] + t0, lv[0.9] - lv[0.1]


def seeded(*k):
    return random.Random(zlib.crc32(("|".join(map(str, k))).encode()))


def cmd_solve(a):
    import numpy as np
    st = Stage(a.stage)
    B = build(a, st)
    thev = json.loads(Path(a.thev).read_text())
    sens = json.loads(Path(a.slew_sens).read_text()) if a.slew_sens else {}
    sg = json.loads(Path(a.sigma[1:]).read_text() if a.sigma.startswith("@") else a.sigma)
    c = a.corner
    th = thev[c]
    s = a.sample
    rnd = seeded("w", s) if s else None
    g_mm = sg.get("grad_per_mm", 0.0) if s else 0.0
    cx, cy = B["P"].W / 2, B["P"].H / 2
    th_dir = seeded("grad", s).uniform(0, 2 * math.pi)
    u = (math.cos(th_dir), math.sin(th_dir))

    def edge_var(tag, p, q, L, et, n):
        d = et.delay(L, c, n)
        v = 0.0
        if s and sg.get("tree", 1.0):
            v += seeded("e", s, tag).gauss(0.0, et.sigma(L, c, n) * sg.get("tree", 1.0))
        if g_mm:
            mx, my = (p[0] + q[0]) / 2 - cx, (p[1] + q[1]) / 2 - cy
            v += d * g_mm * (mx * u[0] + my * u[1]) / 1000.0
        return d + v
    # 1) top tree -> spine driver arrivals (die input reference: trunk from the r2 plan model, common to all)
    tp, by = paths(B["top_nodes"])
    trunk = json.loads(a.trunk_ps)[c]
    sarr = []
    for dnode in B["spine_drv"]:
        tt = trunk
        for e in tp[dnode["tag"]]:
            tt += edge_var(e["tag"], by[e["parent"]]["xy"], e["xy"], e["leg"], e["et"], e["nseg"])
        sarr.append(tt)
    # 2) spine mesh (or, --no-spine, the top tree feeds every column-tree tap directly)
    if a.no_spine:
        pos = {tuple(n["xy"]): k for k, n in enumerate(B["spine_drv"])}
        t_tap = np.array([sarr[pos[tuple(ct["tap"])]] for ct in B["ctrees"]])    # merged level: top leaf = tap buffer
        sl_tap = np.full(len(t_tap), 150.0)
        NS, smult = dict(n=0), np.zeros(1)
        sdrv = [0]
    sw = RC3[a.spine_w]
    hs = [(g, B["cols"][0], B["cols"][-1]) for g in B["gaps"]]
    vs = [(x, B["gaps"][0], B["gaps"][-1]) for x in B["scols"]]
    sdrv = [tuple(n["xy"]) for n in B["spine_drv"]]
    staps = [ct["tap"] for ct in B["ctrees"]]
    if not a.no_spine:
      NS = mesh(hs, vs, sdrv, staps, sw, (RC3[a.spine_stub_w], a.stub_um), wire_rel=sg.get("wire_rel", 0.0) if s else 0.0, rnd=rnd)
      smult = size(voronoi_c(NS), a.spine_m, a.sizing)
      sdvt = [(seeded("vs", s, k).gauss(0, sg["vt_mV"]) + seeded("vs2", s, k).gauss(0, sg["vt_mV"])) / 2 / math.sqrt(max(1.0, smult[k]))
              if s else 0.0 for k in range(len(sdrv))]
      t_tap, sl_tap = solve(NS, sarr, smult, sdvt, th, c, t_extra=a.t_extra)
    # 3) column trees -> fine driver arrivals
    sref = float(np.median(sl_tap))
    farr = {}
    for k, ct in enumerate(B["ctrees"]):
        cpath, cby = paths(ct["nodes"])
        base = t_tap[k] + sens.get(c, {}).get("sens_ps_per_ps", 0.0) * (sl_tap[k] - sref)
        for leaf, ch in cpath.items():
            tt = base
            for e in ch:
                tt += edge_var(e["tag"], cby[e["parent"]]["xy"], e["xy"], e["leg"], e["et"], e["nseg"])
            farr[(r3(cby[leaf]["xy"][0]), r3(cby[leaf]["xy"][1]))] = tt
    # 4) fine mesh (r2 lattice, straps over the r2 extents) + partition entry taps
    rec = B["rec"]
    xs, ys = [r3(x) for x in rec["xs"]], [r3(y) for y in rec["ys"]]
    fw = RC3[a.fine_w]
    hs = [(y, xs[0], xs[-1]) for y in ys]
    vs = [(x, ys[0], ys[-1]) for x in xs]
    fdrv = sorted(farr)
    taps = [(r3(t["tap"][0]), r3(t["tap"][1])) for t in rec["taps"]]
    NF = mesh(hs, vs, fdrv, taps, fw, (RC3[a.stub_w], a.stub_um), wire_rel=sg.get("wire_rel", 0.0) if s else 0.0, rnd=rnd)
    cvor = voronoi_c(NF)
    fmult = size(cvor, a.fine_m, a.sizing)
    fdvt = [(seeded("vf", s, k).gauss(0, sg["vt_mV"]) + seeded("vf2", s, k).gauss(0, sg["vt_mV"])) / 2 / math.sqrt(max(1.0, fmult[k]))
            if s else 0.0 for k in range(len(fdrv))]
    t_ent, sl_ent = solve(NF, [farr[q] for q in fdrv], fmult, fdvt, th, c, t_extra=a.t_extra)
    parts = [t["part"] for t in rec["taps"]]
    tap_arr = {p: r3(v) for p, v in zip(parts, t_ent)}
    fa = np.array([farr[q] for q in fdrv])
    out = dict(schema="ot_qc_clk_mesh3_solve/1", corner=c, sample=s, sigma=sg, sizing=a.sizing, grad_dir=u if g_mm else None,
               spine=dict(nodes=NS["n"], drivers=len(sdrv), mult_hist={str(k): int(v) for k, v in zip(*np.unique(smult, return_counts=True))},
                          arr_spread_ps=r3(max(sarr) - min(sarr)), top_arr_ps=dict(min=r3(min(sarr)), max=r3(max(sarr))), tap_spread_ps=r3(float(t_tap.max() - t_tap.min())),
                          tap_slew_ps=dict(min=r3(sl_tap.min()), max=r3(sl_tap.max()))),
               fine=dict(nodes=NF["n"], drivers=len(fdrv), mult_hist={str(k): int(v) for k, v in zip(*np.unique(fmult, return_counts=True))},
                         driver_arr_spread_ps=r3(float(fa.max() - fa.min())),
                         voronoi_C_fF=dict(min=r3(cvor.min()), med=r3(float(np.median(cvor))), max=r3(cvor.max())),
                         entry_slew_ps=dict(min=r3(sl_ent.min()), max=r3(sl_ent.max()))),
               insertion_ps=dict(min=r3(float(np.nanmin(t_ent))), max=r3(float(np.nanmax(t_ent)))),
               tap_skew_ps=r3(float(np.nanmax(t_ent) - np.nanmin(t_ent))), tap_arr_ps=tap_arr, checked="UNCHECKED")
    if a.dump_loads:
        out["fine_drivers"] = [[q[0], q[1], r3(cvor[k]), float(fmult[k])] for k, q in enumerate(fdrv)]
        out["spine_tap_ps"] = [[ct["tap"][0], ct["tap"][1], r3(t_tap[k]), r3(sl_tap[k])] for k, ct in enumerate(B["ctrees"])]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("tap_arr_ps", "fine_drivers", "spine_tap_ps")}), flush=True)
    return 0


def cmd_collect(a):
    """merge per-sample solve jsons into the r2 die-solve format (samples[].tap_arr_ps) for pairs + a summary."""
    rows = [json.loads(Path(f).read_text()) for f in a.files]
    rows.sort(key=lambda r: r["sample"])
    mc = [r for r in rows if r["sample"] > 0]
    nom = [r for r in rows if r["sample"] == 0]
    summ = dict(corner=rows[0]["corner"], samples=len(mc), nominal_tap_skew_ps=nom[0]["tap_skew_ps"] if nom else None,
                mc_worst_tap_skew_ps=max(r["tap_skew_ps"] for r in mc) if mc else None,
                mc_mean_tap_skew_ps=r3(sum(r["tap_skew_ps"] for r in mc) / len(mc)) if mc else None,
                insertion_ps=dict(min=min(r["insertion_ps"]["min"] for r in rows), max=max(r["insertion_ps"]["max"] for r in rows)),
                nominal=nom[0] if nom else None)
    summ["nominal"] = {k: v for k, v in (summ["nominal"] or {}).items() if k != "tap_arr_ps"}
    out = dict(summary=summ, samples=[dict(sample=r["sample"], tap_skew_ps=r["tap_skew_ps"], tap_arr_ps=r["tap_arr_ps"]) for r in rows],
               checked="UNCHECKED")
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(summ, indent=1))
    return 0


# ------------------------------------------------------------------------------------------------ pairs (approved AOCV)
def cmd_pairs(a):
    import qc_clk_mesh as Q
    import region_clock as RC
    rec = json.loads(Path(a.r2).read_text())
    P, dtp, parts, cores, psha = Q.load(rec["plan"], rec["tree_plan"])
    pairs = RC.seam_pairs(P, parts)
    solve_ = {c: json.loads(Path(v).read_text())["samples"] for c, v in json.loads(a.mesh_skew).items()}
    aocv = json.loads(Path(a.aocv).read_text())["clock_aocv"]
    g = a.g_per_mm
    tap = {t["part"]: t for t in rec["taps"]}
    CORE = RC.CORE_LAT
    rows, demand = [], {}
    for x, y, edge in pairs:
        if x not in tap or y not in tap:
            continue
        r = dict(a=x, b=y, edge_um=edge, common="continuous signed die mesh (12.4a b exception)")
        q1, q2 = tap[x]["tap"], tap[y]["tap"]
        e1, e2 = tap[x]["entry"], tap[y]["entry"]
        bx = [min(q1[0], q2[0], e1[0], e2[0]), min(q1[1], q2[1], e1[1], e2[1]), max(q1[0], q2[0], e1[0], e2[0]), max(q1[1], q2[1], e1[1], e2[1])]
        dmm = math.hypot(bx[2] - bx[0], bx[3] - bx[1]) / 1000.0
        for c in ("TT", "FF"):
            f = aocv["classes"]["A"][c]["path_fit"]
            sgm = lambda n: math.sqrt(max(0.0, f["a_ps2_per_stage"] * n + f["b_ps2_per_stage2"] * n * n))
            na, nb = (max(1, math.ceil(tap[q]["stub_um"] / 450.0 - 1e-9)) + 10 for q in (x, y))
            rnd_ = aocv["k_sigma"] * math.sqrt(sgm(na) ** 2 + sgm(nb) ** 2)
            nc = max(RC.stage_delay(tap[x]["stub_um"], 1, c), RC.stage_delay(tap[y]["stub_um"], 1, c)) + CORE[c]
            sys_ = g * dmm * nc           # approved g (0.21 %/mm) x bbox diagonal x unshared delay (half each side)
            mesh_u = r3(max(abs(s_["tap_arr_ps"][x] - s_["tap_arr_ps"][y]) for s_ in solve_[c]))
            r[c] = dict(noncommon_ps=r3(nc), aocv_random_ps=r3(rnd_), aocv_distance_ps=r3(sys_), droop_ps=0.0,
                        mesh_uncertainty_ps=mesh_u, total_ps=r3(rnd_ + sys_ + mesh_u))
        r["bbox_diag_mm"] = r3(dmm)
        rows.append(r)
        demand["|".join(sorted((x, y)))] = math.ceil(r["FF"]["total_ps"] * 10) / 10.0
    import statistics as S

    def stat(key, c):
        v = sorted(r[c][key] for r in rows)
        return dict(p50=r3(S.median(v)), p90=r3(v[int(0.9 * (len(v) - 1))]), max=r3(v[-1]))
    summ = dict(pairs=len(rows), g_per_mm=g, aocv=a.aocv, mesh_skew_source=json.loads(a.mesh_skew),
                **{c: {k: stat(k, c) for k in ("mesh_uncertainty_ps", "aocv_random_ps", "aocv_distance_ps", "total_ps")} for c in ("TT", "FF")})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pairs_r3.json").write_text(json.dumps(dict(summary=summ, rows=rows, checked="UNCHECKED"), indent=1))
    frag = dict(clock=dict(io_hold="plan_demand", hold_demand=dict(
        source="plan", schema="opentallas.hold_demand.v1",
        basis="QC-CLK-MESH-3 r3 continuous signed-mesh (12.4a b): FF approved AOCV below the mesh (class A depth sigma, k=3, "
              "g=0.21 %/mm x bbox diagonal x unshared delay), differential droop 0 within one mesh, + the pair's MC mesh skew; UNCHECKED",
        pairs=demand, landed=[], default_ps=max(demand.values()))))
    (out / "hold_demand_fragment.json").write_text(json.dumps(frag, indent=1))
    print(json.dumps(summ, indent=1))
    return 0


# ------------------------------------------------------------------------------------------------ EM + power
def cmd_em(a):
    """r2 method: per driver Q = C_cell V; I_avg = C V f; I_peak = C V / tr; I_rms = I_peak sqrt(2 tr f / 3) (rise + fall
    triangles); branch = I / 4 (driver at a strap crossing, 4 strap pieces); J on the driver-adjacent piece width."""
    d = json.loads(Path(a.loads).read_text())
    c = "TT"
    V, tr = VDD[c], a.tr_ps * 1e-12
    out = {}
    for name, rowsk in (("fine", "fine_drivers"),):
        C = max(r[2] / (r[3] if a.per_mult else 1.0) for r in d[rowsk]) if not a.per_mult else None
        worst = None
        for x, y, cf, mlt in d[rowsk]:
            I_avg = cf * 1e-15 * V * F_CLK
            I_pk = cf * 1e-15 * V / tr
            I_rms = I_pk * math.sqrt(2 * tr * F_CLK / 3)
            for w in (a.mesh_w, a.stub_w):
                A = WIDTH_UM[w] * T_CU_UM * 1e-8           # cm2
                J = dict(J_avg=I_avg / 4 / A / 1e6, J_rms=I_rms / 4 / A / 1e6, J_peak=I_pk / 4 / A / 1e6)
                k = (name, w)
                if k not in out or J["J_rms"] > out[k]["J_rms"]:
                    out[k] = dict(C_cell_fF=r3(cf), mult=mlt, I_avg_mA=r3(I_avg * 1e3), I_peak_mA=r3(I_pk * 1e3),
                                  I_rms_mA=r3(I_rms * 1e3), **{kk: r3(vv) for kk, vv in J.items()})
    res = {f"{k[0]}_{k[1]}": v for k, v in out.items()}
    res["budget_MA_cm2"] = dict(J_avg=1.0, J_rms=1.0, source="r2 budgets_em.json declared (UNCHECKED)")
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


def add_common(p):
    p.add_argument("--r2", required=True, help="r2 plan json (fine lattice, taps, plan/tree-plan paths)")
    p.add_argument("--stage", required=True, help="stage_table.json (ngspice)")
    p.add_argument("--top-w", default="16w")
    p.add_argument("--top-m", type=int, default=2)
    p.add_argument("--top-reach", type=float, default=900.0)
    p.add_argument("--col-w", default="4w")
    p.add_argument("--col-m", type=int, default=1)
    p.add_argument("--col-reach", type=float, default=450.0)
    p.add_argument("--spine-w", default="2x16w")
    p.add_argument("--spine-stub-w", default="2x16w")
    p.add_argument("--spine-m", type=float, default=2.0)
    p.add_argument("--spine-stride", type=int, default=3)
    p.add_argument("--spine-off", type=int, default=1)
    p.add_argument("--fine-w", default="8w")
    p.add_argument("--fine-m", type=float, default=2.0, help="base parallel BUFx24 per fine driver island (d1 scales it)")
    p.add_argument("--stub-w", default="2x16w")
    p.add_argument("--stub-um", type=float, default=54.0)
    p.add_argument("--sizing", default="d1", choices=["d1", "none"])
    p.add_argument("--no-spine", action="store_true", help="comparison: top tree straight to every column tap")
    p.add_argument("--t-extra", type=float, default=1500.0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    add_common(p)
    p.add_argument("--out", required=True)
    p.add_argument("--no-render", action="store_true")
    p.set_defaults(fn=cmd_plan)
    s = sub.add_parser("solve")
    add_common(s)
    s.add_argument("--thev", required=True)
    s.add_argument("--slew-sens", default=None)
    s.add_argument("--corner", default="TT")
    s.add_argument("--sample", type=int, default=0)
    s.add_argument("--sigma", default='{"vt_mV": 10.0, "wire_rel": 0.05, "tree": 1.0, "grad_per_mm": 0.0021}')
    s.add_argument("--dump-loads", action="store_true")
    s.add_argument("--trunk-ps", default='{"TT": 319.5, "FF": 261.1}', help="die input -> tree root (r2 insertion_spice_r6.json)")
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_solve)
    k = sub.add_parser("collect")
    k.add_argument("files", nargs="+")
    k.add_argument("--out", required=True)
    k.set_defaults(fn=cmd_collect)
    r = sub.add_parser("pairs")
    r.add_argument("--r2", required=True)
    r.add_argument("--mesh-skew", required=True)
    r.add_argument("--aocv", required=True)
    r.add_argument("--g-per-mm", type=float, default=0.0021)
    r.add_argument("--out", required=True)
    r.set_defaults(fn=cmd_pairs)
    e = sub.add_parser("em")
    e.add_argument("loads")
    e.add_argument("--mesh-w", default="8w")
    e.add_argument("--stub-w", default="2x16w")
    e.add_argument("--tr-ps", type=float, default=25.0)
    e.add_argument("--per-mult", action="store_true")
    e.add_argument("--out", required=True)
    e.set_defaults(fn=cmd_em)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
