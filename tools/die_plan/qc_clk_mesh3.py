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
import os
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
CORR = [{}]             # R12 re-solve: per-edge (child tag) {corner: legal - model ps} from the previous legal placement
ISLANDS = [None]        # R12: per-type island lattice (Islands) -> merge() candidates + repeater sites snap to it


class Islands:
    """INFRA-FIRST-QC-R12 (COORD ruling INFRA-FIRST-QC-R11, 12.2a1 + 12.2c): ONE per-TYPE island lattice.  Every partition
    type T carries the same slot grid in its own frame (x_k, y_j; both symmetric so R0/MX/MY instances map the grid onto
    itself), minus every slot whose 2-unit BUFx24 body (1.62 x 0.54 um) touches a hard core (+CLR) in ANY instance of T
    -> the surviving slot set is IDENTICAL on every instance (no union windows).  The die lattice is the image of the type
    lattices (die lattice == island lattice); the top tree is solved and placed only on slots.  A horizontal tree row uses
    ONE slot row per partition (the one nearest the row), a vertical leg ONE slot column per partition."""
    CW, BH, EDGE, CLR = 1.62, 0.54, 8.64, 1.08

    def __init__(self, P, cores, pitch=19.3, pitch_x=4.86, margin=2, vss=False, edge_sym=False):
        import numpy as np
        self.np = np
        self.vss = vss
        self.edge_sym = edge_sym
        self.P, self.pitch, self.pitch_x = P, pitch, pitch_x
        self.margin = margin * pitch_x       # reach margin for slot conflicts (a taken slot -> the next one, +-pitch_x)
        bt = defaultdict(list)
        for n in P.parts:
            bt[P.parts[n]["type"]].append(n)
        own = defaultdict(list)
        for c in cores:
            own[c[4]].append(c)
        self.types, self.tgrid = {}, {}
        for t, insts in bt.items():
            r0 = P.rect(insts[0])
            w, h = r0[2] - r0[0], r0[3] - r0[1]
            gx = np.array(self.grid(w, self.CW, 0.054, pitch_x))
            # R15 (COORD ruling INFRA-FIRST-QC-R14): slot rows VSS-phase locked -- type-frame y = k * 8.64 (partition
            # origins and heights are 8.64 multiples, M8 VSS stripes at 8.64k): R0 cell origin / MX body top on a VSS stripe
            gy = np.array(self.vss_grid(h, self.BH) if vss else self.grid(h, self.BH, 0.27, pitch))
            ok = np.ones((len(gx), len(gy)), bool)
            for n in insts:
                x0, y0, x1, y1 = P.rect(n)
                o = P.parts[n].get("orient", "R0")
                for c in own.get(n, ()):
                    cx0, cx1 = (x1 - c[2], x1 - c[0]) if o in ("MY", "R180") else (c[0] - x0, c[2] - x0)
                    cy0, cy1 = (y1 - c[3], y1 - c[1]) if o in ("MX", "R180") else (c[1] - y0, c[3] - y0)
                    kx = (gx < cx1 + self.CLR) & (gx + self.CW > cx0 - self.CLR)
                    jy = (gy < cy1 + self.CLR) & (gy + self.BH > cy0 - self.CLR)
                    ok[np.ix_(kx, jy)] = False
            self.tgrid[t] = (gx, gy, ok)
            self.types[t] = dict(w=r3(w), h=r3(h), nx=len(gx), ny=len(gy), grid=int(ok.size), slots=int(ok.sum()),
                                 instances=len(insts), orients=sorted({P.parts[n].get("orient", "R0") for n in insts}))
        self.prect = {n: P.rect(n) for n in P.parts}
        self.pby_x = sorted(self.prect, key=lambda n: self.prect[n][0])
        self._rx, self._cy, self.at = {}, {}, {}
        self.nslots = int(sum(self.tgrid[P.parts[n]["type"]][2].sum() for n in P.parts))

    def grid(self, L, body, q, pitch):
        """symmetric slot grid over [EDGE, L - EDGE - body] at ~pitch, on the placement grid q (row / site)."""
        lo, hi = self.EDGE, L - self.EDGE - body
        n = max(2, int(round((hi - lo) / pitch)))
        n += n % 2
        half = [round(round((lo + (hi - lo) * k / n) / q) * q, 4) for k in range(n // 2 + 1)]
        mid = round(round(((L - body) / 2) / q) * q, 4)
        half[-1] = mid
        return sorted(set(half + [round(L - body - v, 4) for v in half]))

    def vss_grid(self, L, body):
        """R15: slot rows on the VSS phase (type frame k * ISL), inside [EDGE, L - EDGE - body]."""
        # R16 --island-edge-sym (COORD ruling R15: risers fixed by island windows): the type-frame TOP edge keeps the
        # same VSS lane as the bottom edge (slot k * ISL <= L - EDGE, body top EDGE - body from the edge), so an MX
        # instance's die-bottom lane (and an R0 instance's die-top lane) at seam +- 8.64 exists; R15 dropped it (slot
        # <= L - EDGE - body) and pushed the nudged / centre local-row lane-0 repeaters onto lane 1 (riser collisions)
        top = L - self.EDGE if self.edge_sym else L - self.EDGE - body
        return [round(ISL * k, 4) for k in range(1, int(top / ISL + 1e-9) + 1) if ISL * k >= self.EDGE - 1e-9]

    def to_die(self, part, sx, sy):
        x0, y0, x1, y1 = self.prect[part]
        o = self.P.parts[part].get("orient", "R0")
        x = x1 - sx - self.CW if o in ("MY", "R180") else x0 + sx
        y = y1 - sy - self.BH if o in ("MX", "R180") else y0 + sy
        return x, y

    def _reg(self, part, k, j):
        t = self.P.parts[part]["type"]
        gx, gy, _ = self.tgrid[t]
        ox, oy = self.to_die(part, float(gx[k]), float(gy[j]))
        key = (r3(ox + self.CW / 2), r3(oy + ROW_H / 2))
        self.at[key] = (key[0], key[1], part, t, int(k), int(j), round(ox, 4), round(oy, 4))
        return key

    def row_x(self, y, tol=25.0):
        """slot centre-x along a horizontal tree row at y: per partition crossing the row, its ONE slot row nearest y."""
        k_ = r3(y)
        if k_ in self._rx:
            return self._rx[k_]
        np = self.np
        out = []
        for n, (x0, y0, x1, y1) in self.prect.items():
            if not (y0 - tol <= y <= y1 + tol):
                continue
            gx, gy, ok = self.tgrid[self.P.parts[n]["type"]]
            o = self.P.parts[n].get("orient", "R0")
            ycs = (y1 - gy - self.BH + ROW_H / 2) if o in ("MX", "R180") else (y0 + gy + ROW_H / 2)
            j = int(np.argmin(np.abs(ycs - y)))
            if abs(ycs[j] - y) > tol:
                continue
            inside = y0 - 1e-6 <= y < y1 - 1e-6
            for k in np.nonzero(ok[:, j])[0]:
                out.append(self._reg(n, k, j) + (inside,))
        best, pri = {}, {}
        for kx, ky, ins in out:     # one slot per x: the partition HOLDING the row line wins (a seam row -> the upper)
            sc = (not ins, abs(ky - y))
            if kx not in best or sc < pri[kx]:
                best[kx], pri[kx] = ky, sc
        self._rx[k_] = (sorted(best), best)
        return self._rx[k_]

    def col_y(self, x, tol=None):
        """slot centre-y along a vertical leg at x: per partition crossing it, its ONE slot column nearest x."""
        tol = self.pitch_x / 2 + 0.5 if tol is None else tol
        k_ = r3(x)
        if k_ in self._cy:
            return self._cy[k_]
        np = self.np
        out = []
        for n, (x0, y0, x1, y1) in self.prect.items():
            if not (x0 - tol <= x <= x1 + tol):
                continue
            gx, gy, ok = self.tgrid[self.P.parts[n]["type"]]
            o = self.P.parts[n].get("orient", "R0")
            xcs = (x1 - gx - self.CW + self.CW / 2) if o in ("MY", "R180") else (x0 + gx + self.CW / 2)
            k = int(np.argmin(np.abs(xcs - x)))
            if abs(xcs[k] - x) > tol:
                continue
            inside = x0 - 1e-6 <= x < x1 - 1e-6
            for j in np.nonzero(ok[k, :])[0]:
                out.append(self._reg(n, k, j) + (inside,))
        best, pri = {}, {}
        for kx, ky, ins in out:
            sc = (not ins, abs(kx - x))
            if ky not in best or sc < pri[ky]:
                best[ky], pri[ky] = kx, sc
        self._cy[k_] = (sorted(best), best)
        return self._cy[k_]

    @staticmethod
    def nearest(L, v):
        import bisect
        i = bisect.bisect_left(L, v)
        c = [L[k] for k in (i - 1, i) if 0 <= k < len(L)]
        return min(c, key=lambda q: abs(q - v)) if c else None

    def snap_axis(self, ax, fixed, v):
        L = (self.row_x(fixed) if ax == "x" else self.col_y(fixed))[0]
        q = self.nearest(L, v)
        return v if q is None else q

    def slot_xy(self, ax, fixed, v):
        """die centre (x, y) of the slot a leg point snaps to (the perpendicular jog included)."""
        L, m = self.row_x(fixed) if ax == "x" else self.col_y(fixed)
        q = self.nearest(L, v)
        if q is None:
            return (v, fixed) if ax == "x" else (fixed, v)
        return (q, m[q]) if ax == "x" else (m[q], q)

    def chain_delay(self, et, c, ax, fixed, p0, p1, n):
        """delay of an n-stage straight leg p0 -> p1 along ax with the n-1 repeaters on their snapped island slots."""
        pts = [p0] + [self.snap_axis(ax, fixed, p0 + (p1 - p0) * k / n) for k in range(1, n)] + [p1]
        return sum(et.st.seg(et.w, et.m, c, abs(b - a)) for a, b in zip(pts, pts[1:]))

    def chain_max_seg(self, ax, fixed, p0, p1, n):
        pts = [p0] + [self.snap_axis(ax, fixed, p0 + (p1 - p0) * k / n) for k in range(1, n)] + [p1]
        return max(abs(b - a) for a, b in zip(pts, pts[1:]))


def nseg_snap(I, et, ax, fixed, p0, p1):
    """fewest stages whose island-snapped segments all stay within the reach (R12)."""
    n = et.nseg(abs(p1 - p0))
    while n < et.nseg(abs(p1 - p0)) + 6 and I.chain_max_seg(ax, fixed, p0, p1, n) > et.reach - I.margin + 1e-6:
        n += 1
    return n


def merge_islands(A, B, ax, et, tag, nodes, I):
    """R12: merge() on the island lattice -- the node is a slot on the row / column, every repeater sits on its snapped
    slot and the delay balance is solved with those snapped segment lengths (no post-snap trim)."""
    i = 0 if ax == "x" else 1
    fixed = A["xy"][1 - i]
    pa, pb = A["xy"][i], B["xy"][i]
    e = abs(A["xy"][1 - i] - B["xy"][1 - i])
    lo, hi = min(pa, pb), max(pa, pb)
    L = (I.row_x(fixed) if ax == "x" else I.col_y(fixed))[0]
    cand_p = [p for p in L if lo - 1e-6 <= p <= hi + 1e-6]
    if not cand_p:
        return None
    cands = []
    for p in cand_p:
        na0, nb0 = nseg_snap(I, et, ax, fixed, p, pa), nseg_snap(I, et, ax, fixed, p, pb)
        tot = max(A["S"] + na0, B["S"] + nb0)
        na, nb = tot - A["S"], tot - B["S"]
        ca, cb = CORR[0].get(A["tag"], {}), CORR[0].get(B["tag"], {})
        dl = {c: (A["T"][c] + I.chain_delay(et, c, ax, fixed, p, pa, na) + ca.get(c, 0.0)
                  + (et.st.seg(et.w, et.m, c, e) - et.st.seg(et.w, et.m, c, 0.0) if e > 1e-6 else 0.0),
                  B["T"][c] + I.chain_delay(et, c, ax, fixed, p, pb, nb) + cb.get(c, 0.0)) for c in ("TT", "FF")}
        d = dl["TT"][0] - dl["TT"][1]
        cands.append(((round(abs(d), 2), na + nb, abs(p - (lo + hi) / 2)), p, na, nb, dl))
    cands.sort(key=lambda r: r[0])
    best = None
    for cnd in cands:
        xy_ = (cnd[1], fixed) if ax == "x" else (fixed, cnd[1])
        if BLOCK[0] is None or not BLOCK[0](xy_):
            best = cnd
            break
    best = best or cands[0]
    _, p, na, nb, dl = best
    xy = (p, fixed) if ax == "x" else (fixed, p)
    for ch, n_ in ((A, na), (B, nb)):
        ch["parent"], ch["leg"], ch["nseg"], ch["et"] = tag, md(ch["xy"], xy), n_, et
    T = {c: max(dl[c]) for c in ("TT", "FF")}
    n = dict(tag=tag, xy=xy, kids=[A["tag"], B["tag"]], T=T, S=A["S"] + na,
             imbalance_TT=r3(dl["TT"][0] - dl["TT"][1]), imbalance_FF=r3(dl["FF"][0] - dl["FF"][1]))
    nodes.append(n)
    return n


def merge(A, B, ax, et, tag, nodes):
    """equal STAGE count on every root->leaf path (the short side gets extra repeaters in its straight leg, r2 rule) and
    zero TT delay difference by the node position on the straight segment between the two child roots (no detour)."""
    if ISLANDS[0] is not None and et is ISLANDS[0].et:
        r = merge_islands(A, B, ax, et, tag, nodes, ISLANDS[0])
        if r is not None:
            return r
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
    _ca, _cb = CORR[0].get(A["tag"], {}), CORR[0].get(B["tag"], {})     # R13 channel x-tree re-solve (empty = r3 behaviour)
    for k in range(steps + 1):
        p = lo + (hi - lo) * k / steps
        la, lb = abs(p - pa) + e, abs(pb - p)
        na, nb = ns(la, lb)
        d = (A["T"]["TT"] + et.delay(la, "TT", na) + _ca.get("TT", 0.0)) - (B["T"]["TT"] + et.delay(lb, "TT", nb) + _cb.get("TT", 0.0))
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
    T = {c: max(A["T"][c] + et.delay(la, c, na) + _ca.get(c, 0.0), B["T"][c] + et.delay(lb, c, nb) + _cb.get(c, 0.0)) for c in ("TT", "FF")}
    n = dict(tag=tag, xy=xy, kids=[A["tag"], B["tag"]], T=T, S=A["S"] + na,
             imbalance_TT=r3(d), imbalance_FF=r3((A["T"]["FF"] + et.delay(la, "FF", na) + _ca.get("FF", 0.0))
                                                 - (B["T"]["FF"] + et.delay(lb, "FF", nb) + _cb.get("FF", 0.0))))
    nodes.append(n)
    return n


def lift(r, xy, et, tag, nodes, n=None):
    """one straight leg from xy to the subtree root r (|dx| or |dy| only); n > nseg = extra repeaters in the same
    straight leg (equal stage count, r2 rule)."""
    L = md(xy, r["xy"])
    r["parent"], r["leg"], r["nseg"], r["et"] = tag, L, max(n or 0, et.nseg(L)), et
    I = ISLANDS[0]
    if I is not None and et is I.et and (abs(xy[0] - r["xy"][0]) < 1e-6 or abs(xy[1] - r["xy"][1]) < 1e-6) and L > 1e-6:
        ax = "x" if abs(xy[1] - r["xy"][1]) < 1e-6 else "y"
        i = 0 if ax == "x" else 1
        fixed, p0, p1 = xy[1 - i], xy[i], r["xy"][i]
        r["nseg"] = max(r["nseg"], nseg_snap(I, et, ax, fixed, p0, p1))
        T = {c: r["T"][c] + I.chain_delay(et, c, ax, fixed, p0, p1, r["nseg"]) + CORR[0].get(r["tag"], {}).get(c, 0.0)
             for c in ("TT", "FF")}
    else:
        T = {c: r["T"][c] + et.delay(L, c, r["nseg"]) for c in ("TT", "FF")}
    n = dict(tag=tag, xy=xy, kids=[r["tag"]], T=T, S=r["S"] + r["nseg"])
    nodes.append(n)
    return n


# ------------------------------------------------------------------------------------------------ R15 per-level lanes
LANE = [None]     # R15: dict(step=8.64) -> every tree node level on its own lane (COORD ruling INFRA-FIRST-QC-R14)


def lane_pts(I, ax, fixed, p0, p1, n):
    """along-axis stage points of an n-stage leg ON THE DRIVING NODE'S LANE `fixed` (repeaters snapped to slots)."""
    mid = [p0 + (p1 - p0) * k / n for k in range(1, n)]
    if I is not None and getattr(I, "vss", False) and ax == "y":
        # vertical leg: repeaters on the die VSS row grid (8.64k, mirror-symmetric: H = 3040 x 8.64) so the mirrored
        # half lands on the same type-frame slot row (slot centres R0 / MX differ by 0.27 um)
        mid = [r3(round(v / ISL) * ISL) for v in mid]
    elif I is not None:
        mid = [I.snap_axis(ax, fixed, v) for v in mid]
    return [p0] + mid + [p1]


def lane_segs(I, ax, fixed, p0, p1, n, e):
    """segment lengths of the leg: n-1 repeaters on the driver lane, the last segment carries the lane jog e (M9 drop)."""
    pts = lane_pts(I, ax, fixed, p0, p1, n)
    L = [abs(b - a) for a, b in zip(pts, pts[1:])]
    L[-1] += e
    return L


def nseg_lane(I, et, ax, fixed, p0, p1, e):
    marg = I.margin if I is not None else 0.0
    n = et.nseg(abs(p1 - p0) + e)
    while n < et.nseg(abs(p1 - p0) + e) + 6 and max(lane_segs(I, ax, fixed, p0, p1, n, e)) > et.reach - marg + 1e-6:
        n += 1
    return n


def lane_delay(I, et, c, ax, fixed, p0, p1, n, e):
    return sum(et.st.seg(et.w, et.m, c, L) for L in lane_segs(I, ax, fixed, p0, p1, n, e))


def merge_lane(A, B, ax, et, tag, nodes, perp):
    """R15 merge: the node sits on ITS lane `perp` (one lane before its children); each child leg runs along the node
    lane (repeaters there) and drops to the child lane at its end.  Equal stage count (r2 rule) and zero TT difference by
    the node position (no detour); every leg is priced with its real snapped segments + jog (plan computation)."""
    I = ISLANDS[0] if (ISLANDS[0] is not None and et is ISLANDS[0].et) else None
    i = 0 if ax == "x" else 1
    pa, pb = A["xy"][i], B["xy"][i]
    ea, eb = abs(A["xy"][1 - i] - perp), abs(B["xy"][1 - i] - perp)
    lo, hi = min(pa, pb), max(pa, pb)
    if I is not None:
        L = (I.row_x(perp) if ax == "x" else I.col_y(perp))[0]
        cand_p = [p for p in L if lo - 1e-6 <= p <= hi + 1e-6]
    else:
        cand_p = []
    if not cand_p:
        steps = max(1, int((hi - lo) / 1.0))
        cand_p = [lo + (hi - lo) * k / steps for k in range(steps + 1)]
    ca, cb = CORR[0].get(A["tag"], {}), CORR[0].get(B["tag"], {})
    cands = []
    for p in cand_p:
        na0, nb0 = nseg_lane(I, et, ax, perp, p, pa, ea), nseg_lane(I, et, ax, perp, p, pb, eb)
        tot = max(A["S"] + na0, B["S"] + nb0)
        na, nb = tot - A["S"], tot - B["S"]
        dl = {c: (A["T"][c] + lane_delay(I, et, c, ax, perp, p, pa, na, ea) + ca.get(c, 0.0),
                  B["T"][c] + lane_delay(I, et, c, ax, perp, p, pb, nb, eb) + cb.get(c, 0.0)) for c in ("TT", "FF")}
        d = dl["TT"][0] - dl["TT"][1]
        cands.append(((round(abs(d), 2), na + nb, abs(p - (lo + hi) / 2)), p, na, nb, dl))
    cands.sort(key=lambda r: r[0])
    best = None
    for cnd in cands:
        xy_ = (cnd[1], perp) if ax == "x" else (perp, cnd[1])
        if BLOCK[0] is None or not BLOCK[0](xy_):
            best = cnd
            break
    best = best or cands[0]
    _, p, na, nb, dl = best
    xy = (p, perp) if ax == "x" else (perp, p)
    for ch, n_, e_ in ((A, na, ea), (B, nb, eb)):
        ch["parent"], ch["leg"], ch["nseg"], ch["et"], ch["lane_ax"] = tag, abs(ch["xy"][i] - p) + e_, n_, et, ax
    T = {c: max(dl[c]) for c in ("TT", "FF")}
    n = dict(tag=tag, xy=xy, kids=[A["tag"], B["tag"]], T=T, S=A["S"] + na,
             imbalance_TT=r3(dl["TT"][0] - dl["TT"][1]), imbalance_FF=r3(dl["FF"][0] - dl["FF"][1]))
    nodes.append(n)
    return n


def lift_lane(r, xy, et, tag, nodes, ax):
    """R15 lift: node at xy (its lane), child r one lane past; along ax on the node lane, jog to r's lane at the end."""
    I = ISLANDS[0] if (ISLANDS[0] is not None and et is ISLANDS[0].et) else None
    i = 0 if ax == "x" else 1
    fixed, p0, p1, e = xy[1 - i], xy[i], r["xy"][i], abs(r["xy"][1 - i] - xy[1 - i])
    n_ = nseg_lane(I, et, ax, fixed, p0, p1, e)
    r["parent"], r["leg"], r["nseg"], r["et"], r["lane_ax"] = tag, abs(p1 - p0) + e, n_, et, ax
    T = {c: r["T"][c] + lane_delay(I, et, c, ax, fixed, p0, p1, n_, e) + CORR[0].get(r["tag"], {}).get(c, 0.0)
         for c in ("TT", "FF")}
    n = dict(tag=tag, xy=xy, kids=[r["tag"]], T=T, S=r["S"] + n_)
    nodes.append(n)
    return n


def tree_depths(n, d=0):
    """leaf depths of the binary split tree over n items (split h = n // 2, as dtree / yt)."""
    if n == 1:
        return [d]
    h = n // 2
    return tree_depths(h, d + 1) + tree_depths(n - h, d + 1)


def dtree_lane(leaves, ax, et, tag, nodes, lane_of, depth=0, leafT=None):
    """R15 binary delay-balanced tree with per-level lanes: node at depth d on lane_of(d); leaves already on their
    lane (lane_of(depth of the leaf)); leafT = initial arrival offset of the leaves (downstream plan delay)."""
    if len(leaves) == 1:
        n = dict(tag=tag, xy=leaves[0], kids=[], T=dict(leafT or {"TT": 0.0, "FF": 0.0}), S=0)
        nodes.append(n)
        return n
    h = len(leaves) // 2
    A = dtree_lane(leaves[:h], ax, et, tag + "0", nodes, lane_of, depth + 1, leafT)
    B = dtree_lane(leaves[h:], ax, et, tag + "1", nodes, lane_of, depth + 1, leafT)
    return merge_lane(A, B, ax, et, tag, nodes, lane_of(depth))


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
    I = None
    ISLANDS[0] = None
    if getattr(a, "islands", "none") == "type":
        I = Islands(P, cores, pitch=a.island_pitch, pitch_x=a.island_pitch_x, vss=getattr(a, "lanes", "none") == "vss",
                    edge_sym=bool(getattr(a, "island_edge_sym", False)))
        CORR[0] = json.loads(Path(a.island_corr).read_text())["corr"] if getattr(a, "island_corr", None) else {}
        I.et = top
        ISLANDS[0] = I
    leafx = {}

    def ytree(items, tag):
        if len(items) == 1:
            return items[0]
        h = len(items) // 2
        return merge(ytree(items[:h], tag + "0"), ytree(items[h:], tag + "1"), "y", top, tag, nodes)

    def xrow(gi, g, xs_, tag):
        if I is not None:           # R12: the leaf (column-tap cell) is the island slot nearest the column
            for x in xs_:
                leafx[(r3(x), r3(g))] = I.snap_axis("x", g, x)
            r = dtree([(leafx[(r3(x), r3(g))], g) for x in xs_], "x", top, tag, nodes)
        else:
            r = dtree([(x, g) for x in xs_], "x", top, tag, nodes)
        if not free(r["xy"][0]):
            xc = min(cols, key=lambda x: abs(x - r["xy"][0]))
            if I is not None:
                xc = I.snap_axis("x", g, xc)
            r = lift(r, (xc, g), top, tag + "L", nodes)
        return r
    r9 = None
    PERIODIC = None
    LANE[0] = dict(step=ISL, split=getattr(a, "centre_split", ISL)) if getattr(a, "lanes", "none") == "vss" else None
    if getattr(a, "feed", "mesh3") == "periodic":
        root, leafxy, colmap, lofg = periodic_feed(a, top, P, cols, gaps, nodes, rows=rows, m=m, col=col, cores=cores)
        PERIODIC = (leafxy, colmap, lofg)
        build.periodic = periodic_feed.info
    elif getattr(a, "feed", "mesh3") == "r9":
        r9, root = r9_feed(a, top, gaps, scols, xrow, ytree, nodes)
    else:
        # TOP TREE: per gap row an x-tree along the row over the spine columns, then a y-tree over the rows in one free
        # channel (every group root has the same x: identical x-trees).  The group-root x is moved to the nearest FREE
        # column by one equal leg per group (same for all).
        groots = [xrow(gi, g, scols, f"t{gi:02d}_") for gi, g in enumerate(gaps)]
        xs0 = {r3(r["xy"][0]) for r in groots}
        assert len(xs0) == 1 or I is not None, xs0
        if I is not None and len(xs0) > 1:      # R12: one trunk column -> equal straight lifts to the majority slot x
            from collections import Counter as _C
            xt = _C(r3(r["xy"][0]) for r in groots).most_common(1)[0][0]
            build.groot_x = sorted(xs0)
            groots = [r if abs(r["xy"][0] - xt) < 1e-6 else lift(r, (xt, r["xy"][1]), top, r["tag"] + "J", nodes) for r in groots]
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
        grow_all = rows[gi * (2 * m + 1):(gi + 1) * (2 * m + 1)]
        halves = [("", grow_all, None)]
        if PERIODIC is not None and len(PERIODIC[2][r3(g)]) == 2:      # R13 centre group: two mirrored half trees
            halves = [("b", grow_all[:m + 1], PERIODIC[2][r3(g)][0]), ("m", grow_all[m:], PERIODIC[2][r3(g)][1])]
            if LANE[0] is not None:     # R15 (COORD R13 ASK-2): centre fine row split at the seam, one driver per half
                gb_, gm_ = centre_rows(grow_all, m, LANE[0]["split"])
                halves = [("b", gb_, PERIODIC[2][r3(g)][0]), ("m", gm_, PERIODIC[2][r3(g)][1])]
        for ci, x in enumerate(cols):
            for hs_, grow, ytap in halves:
                if PERIODIC is not None:
                    kk, ii = PERIODIC[1][r3(x)]
                    tapxy = PERIODIC[0][(kk, ii, r3(ytap if ytap is not None else PERIODIC[2][r3(g)][0]))]
                else:
                    tapxy = (leafx.get((r3(x), r3(g)), x), g)
                # full 2m+1-row tree (same topology / stage count / balance as every other column), then the driver rows on
                # a hard core of an ADDED channel are pruned with any branch left without a driver (r2 columns keep r2 drivers)
                leaves = [(x, y) for y in grow]
                t0 = len(cnodes)
                r = dtree(leaves, "y", col, f"c{gi:02d}{hs_}_{ci:02d}_", cnodes)
                r = lift(r, tapxy, col, f"c{gi:02d}{hs_}_{ci:02d}_tap", cnodes) if md(r["xy"], tapxy) > 1e-6 else r
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
                ctrees.append(dict(g=gi, c=ci, tap=tapxy, root=r["tag"], nodes=cnodes[t0:]))
    return dict(rec=rec, P=P, dtp=dtp, parts=parts, cores=cores, cols=cols, gaps=gaps, rows=rows, m=m, dy=dy,
                scols=scols, top_nodes=nodes, top_root=root, spine_drv=spine_drv, ctrees=ctrees, cnodes=cnodes,
                et=dict(top=top, col=col), free=free, incore=incore, added_cols=lattice.added, dropped_rows=dropped, r9=r9,
                islands=I, groot_x=getattr(build, "groot_x", None),
                periodic=(build.__dict__.pop("periodic", None) if PERIODIC is not None else None))


# ------------------------------------------------------------------------------------------------ R13 periodic feed
PER_X = 2471.04            # QC partition-array x period (2 partitions = 4 nk columns)
PER_OFF = (0.0, 622.08, 1235.52, 1848.96)   # column-tap offsets from the period trunk column (template; <= 17.28 um from the strap;
#   the 4th tap sits 8.64 um inside the ODD partition right edge so the east-edge column 31207.68 is periodic too)
PER_NUDGE = 8.64           # a gap row on a partition seam -> local row 8.64 um into the partition NEARER the die centre


def centre_rows(grow_all, m, split):
    """R15: the centre gap group's fine rows per half; the shared centre row (index m, on the seam) is split into
    YC - split (bottom half only) and YC + split (top half only): one driver per half, no two-driver net."""
    yc = grow_all[m]
    return list(grow_all[:m]) + [r3(yc - split)], [r3(yc + split)] + list(grow_all[m + 1:])


def col_down(col, ys, x, tap, cores=None):
    """R15 plan computation: downstream delay of one column tree (tap leg + tree to its fine drivers) per corner,
    built exactly as build() builds it (dtree over the rows on column x, straight lift to the tap)."""
    keep = ISLANDS[0], BLOCK[0]
    ISLANDS[0], BLOCK[0] = None, None
    try:
        tmp = []
        r = dtree([(x, y) for y in ys], "y", col, "z", tmp)
        L = md(r["xy"], tap)
        return {c: r["T"][c] + (col.delay(L, c) if L > 1e-6 else 0.0) for c in ("TT", "FF")}
    finally:
        ISLANDS[0], BLOCK[0] = keep


def periodic_feed(a, top, P, cols, gaps, nodes, rows=None, m=None, col=None, cores=None):
    """INFRA-FIRST-QC-R13 (COORD ruling R12 ASK1, 12.2a1): every partition-hosted top-tree cell is x-PERIODIC with the
    partition-array period (2471.04 um) and y-MIRRORED about the die centre, so every instance of a type holds the
    identical cell set (cb types: MX bottom / R0 top; cbx rows 2 and 4 host the same two local rows).  Structure:
      die root -> CHANNEL x-tree (die-level cells in ONE centre clock channel, the only non-periodic part; 12.2a infra
      strip) -> 12 period trunk columns (even-partition mid column, core-free r2 driver column) -> per column a y-tree:
      bottom subtree over 10 local rows, top subtree = exact mirror, root on the centre line -> per local row a 4-leaf
      local x-tree to the period's 4 column taps.  The centre gap group is split into two mirrored half column trees
      (taps YC -/+ 8.64; its centre fine-driver row is driven by both halves).  Returns (root, leafxy, local_of)."""
    H = float(P.H)
    YC = H / 2
    rects = [P.rect(n) for n in P.parts]
    seams = {round(r[1], 3) for r in rects} | {round(r[3], 3) for r in rects}
    trunk = [c for c in cols if any(abs(c - (cols[0] + PER_X * k)) < 0.5 for k in range(len(cols)))]
    gb = [g for g in gaps if g < YC - 1]
    gc = [g for g in gaps if abs(g - YC) < 1e-3]
    assert len(gc) == 1 and len(gb) * 2 + 1 == len(gaps), (len(gb), gc)
    # R16 (COORD ruling R15: su_c hold, structural): a gap row whose local x-tree lanes run into hard cores (row 10471.68:
    # its lanes +8.64..+25.92 hit the su_l0 lane cores at partition y 34.56, the midpoint merge is pushed 127 um off
    # centre -> 41 ps template imbalance, su_c taps early) is moved to a core-free band of the partition AWAY from the
    # centre (--row-at G=Y, plan geometry, mirrored in the top half; its lanes step away, see local())
    row_at = {r3(float(kv.split("=")[0])): r3(float(kv.split("=")[1]))
              for kv in (getattr(a, "row_at", None) or "").split(",") if kv.strip()}
    lb = [row_at[r3(g)] if r3(g) in row_at else (r3(g + PER_NUDGE) if round(g, 3) in seams else g) for g in gb] + [r3(YC - PER_NUDGE)]
    K = len(trunk) // 2
    x0 = trunk[K]
    keep = ISLANDS[0], BLOCK[0]
    if keep[0] is None:
        BLOCK[0] = None
    tmpl = []          # template column K: merges / repeaters on the island slots of period K (translated below)
    LN = LANE[0]
    if LN is not None:
        return periodic_feed_lanes(a, top, P, cols, gaps, nodes, rows, m, col, cores, H, YC, trunk, gb, gc, lb, K, x0, keep, tmpl)

    def local(y, tag):
        r = dtree([(x0 + o, y) for o in PER_OFF], "x", top, tag, tmpl)
        if abs(r["xy"][0] - x0) > 1e-6:
            r = lift(r, (x0, y), top, tag + "L", tmpl)
        return r

    def yt(items, t):
        if len(items) == 1:
            return items[0]
        h = len(items) // 2
        return merge(yt(items[:h], t + "0"), yt(items[h:], t + "1"), "y", top, t, tmpl)
    Bt = yt([local(y, f"t_b{i:02d}_") for i, y in enumerate(sorted(lb))], "T_b")
    nb = list(tmpl)
    mir = []
    for n in nb:
        q = dict(n, tag=n["tag"].replace("_b", "_m", 1), xy=(n["xy"][0], H - n["xy"][1]), kids=[k.replace("_b", "_m", 1) for k in n["kids"]])
        if n.get("parent"):
            q["parent"] = n["parent"].replace("_b", "_m", 1)
        mir.append(q)
    tmpl += mir
    Tm = [n for n in mir if n["tag"] == Bt["tag"].replace("_b", "_m", 1)][0]
    Lc = abs(YC - Bt["xy"][1])
    nc = top.nseg(Lc)
    for ch in (Bt, Tm):
        ch["parent"], ch["leg"], ch["nseg"], ch["et"] = "H_c", Lc, nc, top
    tmpl.append(dict(tag="H_c", xy=(x0, YC), kids=[Bt["tag"], Tm["tag"]], S=Bt["S"] + nc,
                     T={c: Bt["T"][c] + top.delay(Lc, c, nc) for c in ("TT", "FF")}))
    ISLANDS[0], BLOCK[0] = keep
    leafxy, croots = {}, []
    lrows = sorted(lb + [r3(H - y) for y in lb])
    for k, xt in enumerate(trunk):
        dx = xt - x0
        pre = f"{k:02d}"
        ren = lambda t: (t[0] + pre + t[1:]) if t else t
        for n in tmpl:
            q = dict(n, tag=ren(n["tag"]), xy=(r3(n["xy"][0] + dx), n["xy"][1]), kids=[ren(c) for c in n["kids"]])
            if n.get("parent"):
                q["parent"] = ren(n["parent"])
            if q["tag"].startswith("H"):
                croots.append(q)
            nodes.append(q)
            if not n["kids"]:
                leafxy[(k, PER_OFF.index(r3(n["xy"][0] - x0)), r3(n["xy"][1]))] = q["xy"]
    for q in croots:
        q.pop("parent", None)
    ISLANDS[0], BLOCK[0] = None, None          # channel x-tree: die-level cells in the centre channel (no partition slots)
    hr = dtree([q["xy"] for q in croots], "x", top, "H", nodes,
               leafmk=lambda xy, tag: [q for q in croots if abs(q["xy"][0] - xy[0]) < 1e-6][0])
    hr["parent"] = None
    ISLANDS[0], BLOCK[0] = keep
    # every column -> (period, offset index)
    colmap = {}
    for c in cols:
        k, i = min(((k, i) for k in range(len(trunk)) for i in range(len(PER_OFF))), key=lambda ki: abs(trunk[ki[0]] + PER_OFF[ki[1]] - c))
        assert abs(trunk[k] + PER_OFF[i] - c) <= 17.28 + 1e-6, (c, k, i)
        colmap[r3(c)] = (k, i)
    lofg = {r3(gc[0]): (r3(YC - PER_NUDGE), r3(YC + PER_NUDGE))}
    gt = sorted((g for g in gaps if g > YC + 1), reverse=True)
    for i_, g in enumerate(sorted(gb)):
        lofg[r3(g)] = (r3(sorted(lb)[i_]),)
        lofg[r3(gt[i_])] = (r3(H - sorted(lb)[i_]),)     # top gap i from the edge -> exact mirror of bottom local row i
    periodic_feed.info = dict(trunk=trunk, local_rows=lrows, template_nodes=len(tmpl), channel_root=hr["xy"], nc=nc,
                              period_um=PER_X, offsets=PER_OFF)
    return hr, leafxy, colmap, lofg


def periodic_feed_lanes(a, top, P, cols, gaps, nodes, rows, m, col, cores, H, YC, trunk, gb, gc, lb, K, x0, keep, tmpl):
    """INFRA-FIRST-QC-R15 (COORD ruling INFRA-FIRST-QC-R14): the R13 periodic structure with ONE 8.64-um lane per tree
    level, every lane on the VSS phase.  A node / leaf sits one lane past its parent node; repeaters stay on the lane of
    the node driving their edge; the lane step is the leg's end jog (M9 drop).  Local row x-trees step in y (toward the
    die centre: lanes stay in the nudged partition; the centre rows step away from the centre), the column y-trees step
    in x on M9 lanes (side away from the column-tree lane).  Leaves start with their downstream column-tree delay
    (plan-computed), so the y-tree merges re-balance the 25.92-um leaf offset and the split centre halves."""
    st = LANE[0]["step"]
    split = LANE[0]["split"]
    gi_of = {r3(g): gi for gi, g in enumerate(gaps)}
    # column-tree lane side of the trunk column (legalize lane_sign) -> y-tree M9 lanes on the other side
    Lc_ = max([c[2] for c in cores if c[2] <= x0 + 1e-6] or [-1e9])
    Rc_ = min([c[0] for c in cores if c[0] >= x0 - 1e-6] or [1e9])
    sx = -1.0 if Rc_ - x0 >= x0 - Lc_ else 1.0
    free_lanes = int(((x0 - Lc_) if sx < 0 else (Rc_ - x0)) // st) - 1
    srows = sorted(lb)
    # R16 --ytree-split TAG=H: the y-tree subtree TAG splits its rows h | n - h instead of n // 2 (plan topology).  Used
    # so the two cbx_q10 rows of one type (local rows i and i + 4) get the SAME y-tree depth -> the same lift lane in
    # every instance (12.2a1 identity) after --row-at moves rows 3 / 7 into the cbx top band
    ysplit = {kv.split("=")[0]: int(kv.split("=")[1]) for kv in (getattr(a, "ytree_split", None) or "").split(",") if kv.strip()}

    def ydeps(n, t, d):
        if n == 1:
            return [d]
        h = ysplit.get(t, n // 2)
        return ydeps(h, t + "0", d + 1) + ydeps(n - h, t + "1", d + 1)
    ndep = ydeps(len(srows), "T_b", 1)          # y-tree leaf depth (H_c = 0, half-tree root = 1)
    lane_x = lambda d: r3(x0 + sx * st * d)
    info_rows = []

    def grows(i):
        """fine rows of the gap group of local row i (bottom half) -> (ys, centre?)"""
        if i == len(gb):
            g = gc[0]
            gi = gi_of[r3(g)]
            return centre_rows(rows[gi * (2 * m + 1):(gi + 1) * (2 * m + 1)], m, split)[0], True
        g = sorted(gb)[i]
        gi = gi_of[r3(g)]
        return rows[gi * (2 * m + 1):(gi + 1) * (2 * m + 1)], False

    def local(i, y, tag):
        ys, centre = grows(i)
        dy = -1.0 if (centre or y < sorted(gb)[i] - 1e-6) else 1.0   # toward the die centre (bottom half: +y); centre
        #                                       rows and R16 --nudge-away rows away from it (lanes stay in their partition)
        lane_y = lambda d: r3(y + dy * st * d)
        dl = tree_depths(len(PER_OFF), 1)       # dtree root = lane 1 (local root = lane 0)
        lv = [(x0 + o, lane_y(d)) for o, d in zip(PER_OFF, dl)]
        # downstream plan delay: column tree of THIS row's gap group on the template column (identical per period)
        down = [col_down(col, ys, x0 + o, xy) for o, xy in zip(PER_OFF, lv)]
        if os.environ.get("QC_R15_NO_LEAF_T"):     # diagnostic only: leaves without the downstream plan delay
            down = [{"TT": 0.0, "FF": 0.0} for _ in down]
        lt = {c: max(d_[c] for d_ in down) for c in ("TT", "FF")}
        info_rows.append(dict(row=y, centre=centre, leaf_y=lv[0][1], down_TT=r3(lt["TT"]), down_FF=r3(lt["FF"]),
                              down_spread_TT=r3(max(d_["TT"] for d_ in down) - min(d_["TT"] for d_ in down))))
        # leaf T = its downstream delay, so the balance includes it (plan computation, no trim)
        r = dtree_lane_T(lv, "x", top, tag, tmpl, lambda d: lane_y(d + 1), down, y)
        xr = lane_x(ndep[i])
        return lift_lane(r, (xr, r3(y)), top, tag + "L", tmpl, "x")

    def yt(items, t, d):
        if len(items) == 1:
            return items[0]
        h = ysplit.get(t, len(items) // 2)
        return merge_lane(yt(items[:h], t + "0", d + 1), yt(items[h:], t + "1", d + 1), "y", top, t, tmpl, lane_x(d))
    Bt = yt([local(i, y, f"t_b{i:02d}_") for i, y in enumerate(srows)], "T_b", 1)
    nb = list(tmpl)
    mir = []
    for n in nb:
        q = dict(n, tag=n["tag"].replace("_b", "_m", 1), xy=(n["xy"][0], r3(H - n["xy"][1])), kids=[k.replace("_b", "_m", 1) for k in n["kids"]])
        if n.get("parent"):
            q["parent"] = n["parent"].replace("_b", "_m", 1)
        if "row_y" in n:
            q["row_y"] = r3(H - n["row_y"])
        mir.append(q)
    tmpl += mir
    Tm = [n for n in mir if n["tag"] == Bt["tag"].replace("_b", "_m", 1)][0]
    hc = dict(tag="H_c", xy=(lane_x(0), YC), kids=[Bt["tag"], Tm["tag"]])
    I = ISLANDS[0] if (ISLANDS[0] is not None and top is ISLANDS[0].et) else None
    e = abs(Bt["xy"][0] - lane_x(0))
    nc = nseg_lane(I, top, "y", lane_x(0), YC, Bt["xy"][1], e)
    for ch in (Bt, Tm):
        ch["parent"], ch["leg"], ch["nseg"], ch["et"], ch["lane_ax"] = "H_c", abs(YC - Bt["xy"][1]) + e, nc, top, "y"
    hc.update(S=Bt["S"] + nc, T={c: Bt["T"][c] + lane_delay(I, top, c, "y", lane_x(0), YC, Bt["xy"][1], nc, e) for c in ("TT", "FF")})
    tmpl.append(hc)
    ISLANDS[0], BLOCK[0] = keep
    leafxy, croots = {}, []
    lrows = sorted(lb + [r3(H - y) for y in lb])
    for k, xt in enumerate(trunk):
        dx = xt - x0
        pre = f"{k:02d}"
        ren = lambda t: (t[0] + pre + t[1:]) if t else t
        for n in tmpl:
            q = dict(n, tag=ren(n["tag"]), xy=(r3(n["xy"][0] + dx), n["xy"][1]), kids=[ren(c) for c in n["kids"]])
            if n.get("parent"):
                q["parent"] = ren(n["parent"])
            if q["tag"].startswith("H"):
                croots.append(q)
            nodes.append(q)
            if not n["kids"]:
                leafxy[(k, PER_OFF.index(r3(n["xy"][0] - x0)), r3(n["row_y"]))] = q["xy"]
    for q in croots:
        q.pop("parent", None)
    ISLANDS[0], BLOCK[0] = None, None          # channel x-tree: die-level cells in the centre channel (no partition slots)
    hr = dtree([q["xy"] for q in croots], "x", top, "H", nodes,
               leafmk=lambda xy, tag: [q for q in croots if abs(q["xy"][0] - xy[0]) < 1e-6][0])
    hr["parent"] = None
    ISLANDS[0], BLOCK[0] = keep
    colmap = {}
    for c in cols:
        k, i = min(((k, i) for k in range(len(trunk)) for i in range(len(PER_OFF))), key=lambda ki: abs(trunk[ki[0]] + PER_OFF[ki[1]] - c))
        assert abs(trunk[k] + PER_OFF[i] - c) <= 17.28 + 1e-6, (c, k, i)
        colmap[r3(c)] = (k, i)
    PN = PER_NUDGE
    lofg = {r3(gc[0]): (r3(YC - PN), r3(YC + PN))}
    gt = sorted((g for g in gaps if g > YC + 1), reverse=True)
    for i_, g in enumerate(sorted(gb)):
        lofg[r3(g)] = (r3(srows[i_]),)
        lofg[r3(gt[i_])] = (r3(H - srows[i_]),)
    tl = [n for n in tmpl if n["kids"]]
    periodic_feed.info = dict(trunk=trunk, local_rows=lrows, template_nodes=len(tmpl), channel_root=hr["xy"], nc=nc,
                              period_um=PER_X, offsets=PER_OFF, lanes=dict(step_um=st, ytree_side=sx, ytree_lanes=max(ndep) + 1,
                              ytree_free_lanes=free_lanes, local_lanes=1 + max(tree_depths(len(PER_OFF), 1)),
                              centre_split_um=split, rows=info_rows,
                              template_imbalance_TT_max=r3(max(abs(n.get("imbalance_TT", 0.0)) for n in tl)),
                              template_imbalance_FF_max=r3(max(abs(n.get("imbalance_FF", 0.0)) for n in tl))))
    return hr, leafxy, colmap, lofg


def dtree_lane_T(lv, ax, et, tag, nodes, lane_of, down, row_y, depth=0, idx=None):
    """dtree_lane whose leaves carry their own downstream plan delay (down[k]) and the local row y (leafxy key)."""
    idx = list(range(len(lv))) if idx is None else idx
    if len(idx) == 1:
        k = idx[0]
        n = dict(tag=tag, xy=lv[k], kids=[], T=dict(down[k]), S=0, row_y=r3(row_y))
        nodes.append(n)
        return n
    h = len(idx) // 2
    A = dtree_lane_T(lv, ax, et, tag + "0", nodes, lane_of, down, row_y, depth + 1, idx[:h])
    B = dtree_lane_T(lv, ax, et, tag + "1", nodes, lane_of, down, row_y, depth + 1, idx[h:])
    return merge_lane(A, B, ax, et, tag, nodes, lane_of(depth))


# ------------------------------------------------------------------------------------------------ R9 global H-tree feed
def load_r9(d):
    """R9 physical tree/stack canary (codex/qc-r9-2000@c540e671da tree5: DRC 0, RCX ndr016): lattice nodes + per-node
    RCX late/early arrival (ps from the die clock input) per corner."""
    d = Path(d)
    lat = json.loads((d / "r9_lattice.json").read_text())
    nodes = {n["tag"]: dict(n, xy=tuple(n["xy_um"])) for n in lat["nodes"]}
    rcx = {}
    for c in ("TT", "FF"):
        rcx[c] = {}
        for ln in (d / f"r9_tree5_tree_{c}_rcx.txt").read_text().splitlines():
            f = ln.split()
            if len(f) < 4 or f[0] != "N":
                continue
            m = f[1]
            tag = "t" if m == "ckm_n0" else ("t" + m.split("_t", 1)[1] if m.startswith("ckm_n") and "_t" in m else None)
            if tag in nodes:
                rcx[c][tag] = dict(late=float(f[2]), early=float(f[3]), slew=float(f[4]) if len(f) > 4 else None)
        miss = [t for t in nodes if t not in rcx[c]]
        if miss:
            raise SystemExit(f"R9 RCX {c}: no arrival for {miss}")
    return dict(nodes=nodes, rcx=rcx, leg_reps=lat.get("leg_repeaters", {}), source=lat.get("source"), dir=str(d))


def r9_feed(a, top, gaps, scols, xrow, ytree, nodes):
    """the R9 16-leaf H-tree as the global tree: every column tap goes to its nearest R9 leaf (L1 lattice cell; ties to
    the lower index); per leaf region the same delay-balanced x-rows + y-tree as the mesh3 top tree, then straight legs
    (y then x) to the leaf.  Equal stage count on every leaf->tap path: extra repeaters in the longer leaf leg."""
    R9 = load_r9(a.r9_dir)
    lv = sorted(t for t, n in R9["nodes"].items() if n["depth"] == max(m["depth"] for m in R9["nodes"].values()))
    LX = sorted({R9["nodes"][t]["xy"][0] for t in lv})
    LY = sorted({R9["nodes"][t]["xy"][1] for t in lv})
    byxy = {(R9["nodes"][t]["xy"][0], R9["nodes"][t]["xy"][1]): t for t in lv}
    near = lambda v, L: min(range(len(L)), key=lambda i: (abs(L[i] - v), i))
    reg = defaultdict(lambda: defaultdict(list))
    for gi, g in enumerate(gaps):
        for x in scols:
            reg[byxy[(LX[near(x, LX)], LY[near(g, LY)])]][gi].append(x)
    subs = []
    for ri, tl in enumerate(lv):
        rows_ = [xrow(gi, gaps[gi], reg[tl][gi], f"t{gi:02d}r{ri:02d}_") for gi in sorted(reg[tl])]
        assert len({r3(r["xy"][0]) for r in rows_}) == 1, (tl, {r3(r["xy"][0]) for r in rows_})
        subs.append((ri, tl, ytree(rows_, f"T{ri:02d}_")))
    legs = []
    for ri, tl, rr in subs:
        lx, ly = R9["nodes"][tl]["xy"]
        Lv, Lh = abs(rr["xy"][1] - ly), abs(rr["xy"][0] - lx)
        nv, nh = (top.nseg(Lv) if Lv > 1e-6 else 0), (top.nseg(Lh) if Lh > 1e-6 else 0)
        legs.append([Lv, Lh, nv, nh])
    need = [rr["S"] + max(1, lg[2] + lg[3]) for (_, _, rr), lg in zip(subs, legs)]
    target = max(need)
    info = []
    for (ri, tl, rr), lg, nd in zip(subs, legs, need):
        lx, ly = R9["nodes"][tl]["xy"]
        Lv, Lh, nv, nh = lg
        extra = target - nd
        if Lv >= Lh and Lv > 1e-6:
            nv += extra
        elif Lh > 1e-6:
            nh += extra
        cur = rr
        if Lv > 1e-6 and Lh > 1e-6:
            cur = lift(cur, (rr["xy"][0], ly), top, f"T{ri:02d}_Lv", nodes, n=nv)
            cur = lift(cur, (lx, ly), top, f"T{ri:02d}_Lh", nodes, n=nh)
        else:
            cur = lift(cur, (lx, ly), top, f"T{ri:02d}_L", nodes, n=max(1, nv + nh))
        cur["parent"] = None
        cur["ext"], cur["r9_tag"] = "r9", tl
        info.append(dict(leaf=tl, xy=[lx, ly], region_rows=sorted(reg[tl]), region_cols=len(next(iter(reg[tl].values()))),
                         taps=sum(len(v) for v in reg[tl].values()), sub_root=[r3(rr["xy"][0]), r3(rr["xy"][1])],
                         leg_v_um=r3(Lv), leg_h_um=r3(Lh), stages=cur["S"], padded_stages=extra,
                         T_TT_ps=r3(cur["T"]["TT"]), T_FF_ps=r3(cur["T"]["FF"])))
    tts = [i["T_TT_ps"] + R9["rcx"]["TT"][i["leaf"]]["late"] for i in info]
    R9["regions"] = info
    R9["region_nominal_spread_TT_ps"] = r3(max(tts) - min(tts))
    root = dict(tag="r9_root", xy=R9["nodes"]["t"]["xy"], T={c: 0.0 for c in ("TT", "FF")}, kids=[], S=0)
    return R9, root


# ------------------------------------------------------------------------------------------------ legal sites
DX_LANE = 8.64      # column / trunk tree lane: buffers one ISL beside the driver column (same nk channel)
DY_LANE = 4.32      # top x-tree lane: buffers 16 rows above the gap-row strap line (fine drivers sit on the line)
CELL_W = 6.48       # BUFx24 footprint width incl. spacing (UNCHECKED vs LEF; conservative)
ROW_H = 0.27        # ASAP7 row


# ASAP7 R 1x LEF (asap7sc7p5t_28_R_1x_220121a.lef, ORFS asap7lock): master -> (width, A-pin access centroid x, Y-pin
# access centroid x) from the cell origin, um; both pins span the row (y centroid = row middle).
LEF_BUF = {"BUFx24": (1.62, 0.048, 0.956), "BUFx16f": (1.188, 0.039, 0.74), "BUFx12f": (0.972, 0.046, 0.632)}
BUF_STRENGTH = {"BUFx24": 1.0, "BUFx16f": 0.667, "BUFx12f": 0.5}


def decompose(mult):
    """d1 driver strength (BUFx24 units, MULT_SET x base) -> the fewest real cells (BUFx24 / BUFx16f / BUFx12f)."""
    best = None
    for a_ in range(6):
        for b_ in range(4):
            for c_ in range(3):
                v = a_ + 0.667 * b_ + 0.5 * c_
                if abs(v - mult) <= 0.01 and (best is None or a_ + b_ + c_ < best[0]):
                    best = (a_ + b_ + c_, ["BUFx24"] * a_ + ["BUFx16f"] * b_ + ["BUFx12f"] * c_)
    if best is None:
        raise ValueError(f"no BUFx24/x16f/x12f decomposition for mult {mult}")
    return best[1]


def legalize(B, fine_masters=None):
    """GEOM-REVIEW-10 (2): one legal site per cell.  Merges the zero-length level (top-tree leaf == column-tree tap
    buffer, one cell), puts tree buffers in lanes beside the fine-driver line, then bumps residual footprint overlaps
    along the lane.  Every net is a Manhattan L between its two cell sites (ratio 1.0 by construction)."""
    cells = []          # dict(kind, xy0, site, units, lane, ref, masters)
    side = {}
    fine_masters = fine_masters or {}

    def lane_sign(x):
        """tree lane on the wider side of the channel (nearest core edge left / right of the column, any y)."""
        k = r3(x)
        if k not in side:
            L = max([c[2] for c in B["cores"] if c[2] <= x + 1e-6] or [-1e9])
            R = min([c[0] for c in B["cores"] if c[0] >= x - 1e-6] or [1e9])
            side[k] = 1.0 if R - x >= x - L else -1.0
        return side[k]

    def add(kind, xy, units, lane, ref=None, masters=None):
        dx, dy = (DX_LANE * lane_sign(xy[0]), 0.0) if lane == "v" else ((0.0, DY_LANE) if lane == "h" else (0.0, 0.0))
        if LANE[0] is not None and kind.startswith("chan"):
            dx = dy = 0.0       # R15: centre-channel cells on the VSS lane at YC (the split centre fine rows left it free)
        if kind == "r9_leaf":
            dx = dy = 0.0       # the R9 leaf buffer is already placed by the R9 tree (DRC-clean); no new cell
        masters = masters if masters is not None else ["BUFx24"] * int(units)
        cells.append(dict(kind=kind, xy0=(r3(xy[0]), r3(xy[1])), site=[xy[0] + dx, xy[1] + dy], units=len(masters), lane=lane,
                          ref=ref, masters=masters))
        return len(cells) - 1
    top, col = B["et"]["top"], B["et"]["col"]
    site_of = {}
    tby = {n["tag"]: n for n in B["top_nodes"]}
    for n in B["top_nodes"]:
        if not n["kids"]:
            continue          # top leaf = column tap cell (merged level), added with the column tree
        if n.get("ext") == "r9":
            site_of[("t", n["tag"])] = add("r9_leaf", n["xy"], 0, "x", ("t", n["tag"]), masters=[])
            continue
        site_of[("t", n["tag"])] = add("chan_node" if n["tag"].startswith("H") else "top_node", n["xy"], top.m,
                                       "v" if n["tag"].startswith("T") else "h", ("t", n["tag"]))
    for ct in B["ctrees"]:
        for n in ct["nodes"]:
            if not n["kids"]:
                fm = fine_masters.get((r3(n["xy"][0]), r3(n["xy"][1])))
                site_of[("c", n["tag"])] = add("fine_driver", n["xy"], 2, "d", ("c", n["tag"]), masters=fm)
            else:
                site_of[("c", n["tag"])] = add("col_tap" if not n.get("parent") else "col_node", n["xy"], col.m, "v", ("c", n["tag"]))
    leafpos = {(r3(n["xy"][0]), r3(n["xy"][1])): n["tag"] for n in B["top_nodes"] if not n["kids"]}
    ctap = {(r3(ct["tap"][0]), r3(ct["tap"][1])): ct for ct in B["ctrees"]}
    assert set(leafpos) == set(ctap), "top leaves must coincide with column taps (merged level)"
    for k, tg in leafpos.items():           # merged level: the top leaf IS the column-tap cell
        site_of[("t", tg)] = site_of[("c", ctap[k]["root"])]
    nrep = {"top": 0, "col": 0}
    for kind, nodes, et in (("top", B["top_nodes"], top), ("col", B["cnodes"], col)):
        by = {n["tag"]: n for n in nodes}
        for n in nodes:
            if not n.get("parent"):
                continue
            p = by[n["parent"]]["xy"]
            lane = "h" if abs(p[1] - n["xy"][1]) < 1e-6 and abs(p[0] - n["xy"][0]) > 1e-6 else "v"
            lax = n.get("lane_ax")
            if lax:                     # R15: repeaters on the DRIVING node's lane (snapped as the solver priced them)
                lane = "h" if lax == "x" else "v"
                I_ = B.get("islands") if (B.get("islands") is not None and et is B["islands"].et) else None
                i_ = 0 if lax == "x" else 1
                pts = lane_pts(I_, lax, p[1 - i_], p[i_], n["xy"][i_], n["nseg"])
            for k in range(1, n["nseg"]):
                q = (p[0] + (n["xy"][0] - p[0]) * k / n["nseg"], p[1] + (n["xy"][1] - p[1]) * k / n["nseg"])
                if lax:
                    q = (pts[k], p[1]) if lax == "x" else (p[0], pts[k])
                ck = "chan_rep" if (kind == "top" and n["tag"].startswith("H")) else kind + "_rep"   # R13 channel x-tree
                site_of[(kind + "_rep", n["tag"], k)] = add(ck, q, et.m, lane, (kind + "_rep", n["tag"], k))
                nrep[kind] += 1
    # exact coincidences before the bump (the GEOM-REVIEW-10 metric on the raw tree coordinates)
    from collections import Counter
    raw = Counter((r3(c["site"][0]), r3(c["site"][1])) for c in cells if c["kind"] != "r9_leaf")
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
    I = B.get("islands")
    TOPK = ("top_node", "top_rep", "col_tap")
    for i in order:
        c = cells[i]
        if c["kind"] == "r9_leaf" or (I is not None and c["kind"] in TOPK):
            continue
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
    isl = None
    if I is not None:
        isl = assign_periodic(B, I, cells, TOPK) if B.get("periodic") else assign_islands(B, I, cells, TOPK)
    B["site_of"] = site_of
    phys = [c for c in cells if c["kind"] != "r9_leaf"]
    post = Counter((r3(c["site"][0]), r3(c["site"][1])) for c in phys)
    strict = lambda q: any(c[0] < q[0] < c[2] and c[1] < q[1] < c[3] for c in B["cores"])
    oncore = sum(1 for c in phys if strict(c["site"]))
    near_isl = sum(1 for c in phys if inc(c["site"]))
    # merged-level check: every column tap cell is ALSO the top-tree leaf (one cell, no zero-length edge)
    stats = dict(cells=len(phys), by_kind=dict(Counter(c["kind"] for c in cells)), raw_coincident_items=pre_coinc,
                 instances=sum(c["units"] for c in phys),
                 instances_by_master=dict(Counter(m for c in phys for m in c["masters"])),
                 coincident_items=sum(v for v in post.values() if v > 1), footprint_overlaps=0, cells_on_core=oncore,
                 cells_within_ISL_of_core=near_isl, cells_within_ISL_note="r2 fine-driver sites kept as r2 placed them (r2 seam_channel)",
                 bumped=bumped, max_bump_um=r3(maxbump), merged_top_leaf_eq_col_tap=len(ctap),
                 lane_offsets_um=dict(dx_tree_lane=DX_LANE, dy_top_lane=DY_LANE, lanes_left=sum(1 for v in side.values() if v < 0),
                                      lanes_right=sum(1 for v in side.values() if v > 0)), repeaters=nrep,
                 max_net_extra_vs_leg_um=r3(DX_LANE + DY_LANE + maxbump), islands=isl,
                 note="net = Manhattan L between cell sites (ratio 1.0); planned legs differ by <= max_net_extra_vs_leg_um, "
                      "same on every root->driver path of a level (common, not skew). UNCHECKED")
    return cells, stats


def assign_islands(B, I, cells, topk):
    """R12: every top-tree cell group (top node / repeater / column-tap leaf) takes ONE island slot: on its row's slot row
    (horizontal) or its leg's slot column (vertical) at the tree coordinate (exact by construction for nodes / snapped
    repeaters), else the nearest free slot along the same row / column.  Non-top cells (column trees, fine drivers) keep
    their legalize() sites; a slot whose body overlaps one is not used."""
    import bisect
    other = defaultdict(list)
    for c in cells:
        if c["kind"] in topk or not c["masters"]:
            continue
        w = max(LEF_BUF[m][0] for m in c["masters"])
        bx = (c["site"][0] - w / 2, c["site"][1] - ROW_H / 2, c["site"][0] + w / 2, c["site"][1] - ROW_H / 2 + ROW_H * len(c["masters"]))
        for ix in range(int(bx[0] // 20), int(bx[2] // 20) + 1):
            other[ix].append(bx)
    ov = lambda s_: any(s_[6] < b[2] and b[0] < s_[6] + I.CW and s_[7] < b[3] and b[1] < s_[7] + I.BH
                        for ix in range(int(s_[6] // 20) - 1, int((s_[6] + I.CW) // 20) + 2) for b in other.get(ix, ()))
    used, moves, ex = set(), [], []
    order = sorted((i for i, c in enumerate(cells) if c["kind"] in topk),
                   key=lambda i: ({"top_node": 0, "col_tap": 1, "top_rep": 2}[cells[i]["kind"]], i))
    for i in order:
        c = cells[i]
        x0, y0 = c["xy0"]
        vert = c["lane"] == "v" and c["kind"] != "col_tap"
        L, m = I.col_y(x0) if vert else I.row_x(y0)
        v = y0 if vert else x0
        k = bisect.bisect_left(L, v)
        best = None
        for t in range(400):
            for kk in ((k + t // 2) if t % 2 == 0 else (k - 1 - t // 2),):
                if not 0 <= kk < len(L):
                    continue
                key = (m[L[kk]], L[kk]) if vert else (L[kk], m[L[kk]])
                s_ = I.at[key]
                if key in used or ov(s_):
                    continue
                cand = (abs(key[0] - x0) + abs(key[1] - y0), s_, key)
                if best is None or cand[0] < best[0]:
                    best = cand
            if best is not None and t > 2:
                break
        if best is None:
            raise RuntimeError(f"no free island slot near {c['xy0']}")
        d, s_, key = best
        used.add(key)
        c["site"] = [s_[6] + LEF_BUF[c["masters"][0]][0] / 2, s_[7] + ROW_H / 2]
        c["island"] = dict(part=s_[2], type=s_[3], k=s_[4], j=s_[5])
        moves.append(d)
        if d > 1.0 and len(ex) < 8:
            ex.append(dict(kind=c["kind"], xy0=c["xy0"], slot=[s_[0], s_[1]], d_um=r3(d)))
    per_type = defaultdict(lambda: defaultdict(set))
    for c in cells:
        if "island" in c:
            per_type[c["island"]["type"]][c["island"]["part"]].add((c["island"]["k"], c["island"]["j"]))
    T = {}
    for t, info in I.types.items():
        u = per_type.get(t, {})
        T[t] = dict(info, hosting_instances=len(u), used_slots_max_inst=max((len(v) for v in u.values()), default=0),
                    used_slots_union=len(set().union(*u.values())) if u else 0)
    return dict(slots_total=I.nslots, types=len(I.types), groups_on_slots=len(moves),
                exact=sum(1 for d in moves if d < 1e-6), moved_gt_1um=sum(1 for d in moves if d > 1.0),
                max_move_um=r3(max(moves or [0.0])), examples=ex, pitch_um=[I.pitch_x, I.pitch], per_type=T,
                rule="slot grid identical per type (type frame, symmetric), slots on a core in ANY instance removed")


def assign_periodic(B, I, cells, topk):
    """R13 (12.2a1 identical cell set per type): every partition-hosted top-tree cell takes the island slot NEAREST its
    plan point in its host's TYPE FRAME, decided once per (type, frame point) CLASS for all instances of the type:
    a slot is accepted only when it is free and clear of every non-top clock cell in EVERY instance of the type, so
    each type's instances end with the identical slot set.  A class whose member count != instance count is an
    identity violation (reported).  Channel cells (chan_*) are die-level and not assigned here."""
    import numpy as np
    other = defaultdict(list)
    for c in cells:
        if c["kind"] in topk or not c["masters"] or c["kind"].startswith("chan"):
            continue
        w = max(LEF_BUF[m][0] for m in c["masters"])
        bx = (c["site"][0] - w / 2, c["site"][1] - ROW_H / 2, c["site"][0] + w / 2, c["site"][1] - ROW_H / 2 + ROW_H * len(c["masters"]))
        for ix in range(int(bx[0] // 20), int(bx[2] // 20) + 1):
            other[ix].append(bx)

    def ov(ox, oy):
        return any(ox < b[2] and b[0] < ox + I.CW and oy < b[3] and b[1] < oy + I.BH
                   for ix in range(int(ox // 20) - 1, int((ox + I.CW) // 20) + 2) for b in other.get(ix, ()))
    P = I.P
    rects = I.prect
    bx_ = defaultdict(list)
    for n, r in rects.items():
        for ix in range(int(r[0] // 500), int(r[2] // 500) + 1):
            bx_[ix].append(n)

    def host(x, y):
        for n in bx_.get(int(x // 500), ()):
            r = rects[n]
            if r[0] - 1e-6 <= x < r[2] - 1e-6 and r[1] - 1e-6 <= y < r[3] - 1e-6:
                return n
        return None

    def frame(n, x, y):
        x0, y0, x1, y1 = rects[n]
        o = P.parts[n].get("orient", "R0")
        return ((x1 - x) if o in ("MY", "R180") else (x - x0)), ((y1 - y) if o in ("MX", "R180") else (y - y0))
    insts = defaultdict(list)
    for n in P.parts:
        insts[P.parts[n]["type"]].append(n)
    cls = defaultdict(list)
    for i, c in enumerate(cells):
        if c["kind"] not in topk:
            continue
        n = host(*c["xy0"])
        if n is None:
            raise RuntimeError(f"top cell outside partitions {c['xy0']}")
        fx, fy = frame(n, *c["xy0"])
        if getattr(I, "vss", False):    # R15: class by the VSS slot row (R0 / MX slot centres differ by 0.27 um in frame)
            gy_ = I.tgrid[P.parts[n]["type"]][1]
            fy = float(gy_[int(np.argmin(np.abs(gy_ + ROW_H / 2 - fy)))]) + ROW_H / 2
        cls[(P.parts[n]["type"], round(fx), round(fy), c["kind"] == "top_node")].append((i, n))
    used = defaultdict(set)
    moves, viol, ex = [], [], []
    split = []
    for key in sorted(cls, key=lambda k: (not k[3], k)):
        t = key[0]
        per = defaultdict(list)
        for i, n in cls[key]:
            per[n].append((i, n))
        ms = {len(v) for v in per.values()}
        if len(per) != len(insts[t]) or len(ms) != 1:
            viol.append(dict(type=t, frame=list(key[1:3]), members=len(cls[key]), instances=len(insts[t]),
                             hosting=len(per), per_instance=sorted(ms)))
        for r_ in range(max(ms)):        # coincident plan points (m per instance) -> m classes, r-th member in each
            split.append((key, [v[r_] for v in per.values() if len(v) > r_]))
    for key, mem in split:
        t, fx, fy, _ = key
        gx, gy, ok = I.tgrid[t]
        cxs = gx + I.CW / 2
        cys = gy + ROW_H / 2
        dxa = np.abs(cxs - fx)
        dya = np.abs(cys - fy)
        kk = np.argsort(dxa)[:24]
        jj = np.argsort(dya)[:24]
        cand = sorted(((dxa[k] + dya[j], int(k), int(j)) for k in kk for j in jj if ok[k, j]))
        pick = None
        for d, k, j in cand:
            if (k, j) in used[t]:
                continue
            sites = [I.to_die(n, float(gx[k]), float(gy[j])) for _, n in mem]
            if any(ov(ox, oy) for ox, oy in sites):
                continue
            pick = (d, k, j, sites)
            break
        if pick is None:
            raise RuntimeError(f"no common slot for class {key}")
        d, k, j, sites = pick
        used[t].add((k, j))
        for (i, n), (ox, oy) in zip(mem, sites):
            c = cells[i]
            c["site"] = [ox + LEF_BUF[c["masters"][0]][0] / 2, oy + ROW_H / 2]
            c["island"] = dict(part=n, type=t, k=k, j=j)
            I._reg(n, k, j)             # slot -> die image registry (physical export looks slots up by (part, k, j))
            moves.append(md(c["site"], c["xy0"]))
    per_type = defaultdict(lambda: defaultdict(set))
    for c in cells:
        if "island" in c:
            per_type[c["island"]["type"]][c["island"]["part"]].add((c["island"]["k"], c["island"]["j"]))
    T = {}
    for t, u in per_type.items():
        sets = {frozenset(v) for v in u.values()}
        T[t] = dict(instances=len(insts[t]), hosting_instances=len(u), slots_per_instance=sorted({len(v) for v in u.values()}),
                    distinct_slot_sets=len(sets), identical=len(sets) == 1 and len(u) == len(insts[t]))
    return dict(mode="periodic", groups_on_slots=len(moves), classes=len(cls), max_move_um=r3(max(moves or [0.0])),
                moved_gt_1um=sum(1 for d in moves if d > 1.0), identity_violations=viol[:20], n_identity_violations=len(viol),
                types_hosting=len(T), types_identical=sum(1 for v in T.values() if v["identical"]), per_type=T,
                rule="one slot per (type, frame point) class, free + clear in every instance -> identical slot set per type")


def pin_xy(c, which):
    """centroid of a cell group's A (input) or Y (output) pins + the tie strap joining its stacked units (um)."""
    if not c["masters"]:
        return (c["site"][0], c["site"][1]), 0.0
    xs, ys = [], []
    for u, m in enumerate(c["masters"]):
        w, ax, yx = LEF_BUF[m]
        xs.append(c["site"][0] - w / 2 + (ax if which == "A" else yx))
        ys.append(c["site"][1] + u * ROW_H + ROW_H / 2)
    return (sum(xs) / len(xs), sum(ys) / len(ys)), (len(xs) - 1) * ROW_H


def net_um(src, dst):
    """pin-to-pin net length between two legal cell groups: Manhattan Y-centroid -> A-centroid + both unit ties."""
    (p, tp), (q, tq) = pin_xy(src, "Y"), pin_xy(dst, "A")
    return md(p, q) + tp + tq


def phys_edges(B):
    """every tree edge (namespace, child tag) -> [(driver cell, load cell, net um)] over the LEGAL cells: parent cell,
    its repeaters in order, child cell (legalize() geometry, units expanded)."""
    cells, so = B["cells"], B["site_of"]
    out = {}
    for ns, kind, nodes in (("t", "top", B["top_nodes"]), ("c", "col", B["cnodes"])):
        for n in nodes:
            if not n.get("parent"):
                continue
            chain = ([cells[so[(ns, n["parent"])]]] + [cells[so[(kind + "_rep", n["tag"], k)]] for k in range(1, n["nseg"])]
                     + [cells[so[(ns, n["tag"])]]])
            out[(ns, n["tag"])] = [(a_, b_, net_um(a_, b_)) for a_, b_ in zip(chain, chain[1:])]
    return out


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
                feed=getattr(a, "feed", "mesh3"),
                r9_feed=(dict(source=B["r9"]["source"], regions=B["r9"]["regions"],
                              region_nominal_spread_TT_ps=B["r9"]["region_nominal_spread_TT_ps"]) if B.get("r9") else None),
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
    if B.get("r9"):
        N9 = B["r9"]["nodes"]
        for t, n in N9.items():
            if n.get("parent"):
                p = N9[n["parent"]]["xy"]
                ax.plot([p[0], n["xy"][0], n["xy"][0]], [p[1], p[1], n["xy"][1]], "-", c="#e07000", lw=3.0, alpha=0.8)
        lv = [n["xy"] for n in N9.values() if not any(m.get("parent") == n["tag"] for m in N9.values())]
        ax.plot([q[0] for q in lv], [q[1] for q in lv], "o", c="#e07000", ms=9, mfc="none", mew=2, label="R9 H-tree leaf (16)")
        ax.plot([], [], "-", c="#e07000", lw=3, label="R9 physical H-tree (tree5 DRC 0)")
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


def r9_sample(R, st, c, s, sg, g_mm, ctr, u):
    """R9 leaf arrivals for one sample: RCX late arrival per node (nominal) + per R9 leg one Gaussian (stage sigma of
    the 4w x1 BUFx24 table at the leg piece length x sqrt(stages); stages = declared leg repeaters + 1) + gradient."""
    N, A = R["nodes"], R["rcx"][c]
    memo = {}

    def arr(t):
        if t in memo:
            return memo[t]
        n = N[t]
        if not n.get("parent"):
            memo[t] = A[t]["late"]
            return memo[t]
        p = N[n["parent"]]
        d = A[t]["late"] - A[n["parent"]]["late"]
        v = 0.0
        if s:
            ns_ = R["leg_reps"].get(t, 0) + 1
            L = md(p["xy"], n["xy"])
            if sg.get("tree", 1.0):
                v += seeded("r9", s, t).gauss(0.0, st.sigma("4w", 1, c, L / ns_) * math.sqrt(ns_) * sg.get("tree", 1.0))
            if g_mm:
                mx, my = (p["xy"][0] + n["xy"][0]) / 2 - ctr[0], (p["xy"][1] + n["xy"][1]) / 2 - ctr[1]
                v += d * g_mm * (mx * u[0] + my * u[1]) / 1000.0
        memo[t] = arr(n["parent"]) + d + v
        return memo[t]
    return {t: arr(t) for t, n in N.items() if n["depth"] == max(m["depth"] for m in N.values())}


def cmd_solve(a):
    import numpy as np
    st = Stage(a.stage)
    B = build(a, st)
    legal = a.geometry == "legal"
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

    def edge_var_phys(ns, tag, et):
        """LEGAL geometry: one stage per real driver->load net (pin-to-pin), sigma per real stage, gradient per net."""
        d = v = s2 = 0.0
        for a_, b_, L in PE[(ns, tag)]:
            di = et.st.seg(et.w, et.m, c, L)
            d += di
            s2 += et.st.sigma(et.w, et.m, c, L) ** 2
            if g_mm:
                mx, my = (a_["site"][0] + b_["site"][0]) / 2 - cx, (a_["site"][1] + b_["site"][1]) / 2 - cy
                v += di * g_mm * (mx * u[0] + my * u[1]) / 1000.0
        if s and sg.get("tree", 1.0):
            v += seeded("e", s, tag).gauss(0.0, math.sqrt(s2) * sg.get("tree", 1.0))
        return d + v

    def edge_var(tag, p, q, L, et, n, ns=None):
        if legal:
            return edge_var_phys(ns, tag, et)
        d = et.delay(L, c, n)
        v = 0.0
        if s and sg.get("tree", 1.0):
            v += seeded("e", s, tag).gauss(0.0, et.sigma(L, c, n) * sg.get("tree", 1.0))
        if g_mm:
            mx, my = (p[0] + q[0]) / 2 - cx, (p[1] + q[1]) / 2 - cy
            v += d * g_mm * (mx * u[0] + my * u[1]) / 1000.0
        return d + v
    rec = B["rec"]
    xs, ys = [r3(x) for x in rec["xs"]], [r3(y) for y in rec["ys"]]
    fw = RC3[a.fine_w]
    taps = [(r3(t["tap"][0]), r3(t["tap"][1])) for t in rec["taps"]]
    hs_f = [(y, xs[0], xs[-1]) for y in ys]
    vs_f = [(x, ys[0], ys[-1]) for x in xs]
    fine_masters = None
    if legal:
        # d1 sizing is plan-computed: Voronoi strap C of the NOMINAL plan netlist (ideal driver points), then every
        # driver group is decomposed into real cells and legalised with its true unit count
        fd0 = sorted({(r3(n["xy"][0]), r3(n["xy"][1])) for ct in B["ctrees"] for n in ct["nodes"] if not n["kids"]})
        N0 = mesh(hs_f, vs_f, fd0, taps, fw, (RC3[a.stub_w], a.stub_um))
        m0 = size(voronoi_c(N0), a.fine_m, a.sizing)
        fine_masters = {q: decompose(float(m)) for q, m in zip(fd0, m0)}
        cells, lstat = legalize(B, fine_masters)
        B["cells"] = cells
        PE = phys_edges(B)
    # 1) top tree -> spine driver arrivals (die input reference: trunk from the r2 plan model, common to all; with
    #    --feed r9 the measured R9 RCX arrival at the leaf + R9 per-edge variation)
    tp, by = paths(B["top_nodes"])
    trunk = json.loads(a.trunk_ps)[c]
    r9arr = r9_sample(B["r9"], st, c, s, sg, g_mm, (cx, cy), u) if B.get("r9") else None
    sarr = []
    for dnode in B["spine_drv"]:
        ch = tp[dnode["tag"]]
        rt = by[ch[-1]["parent"]] if ch else dnode
        tt = r9arr[rt["r9_tag"]] if rt.get("ext") == "r9" else trunk
        for e in ch:
            tt += edge_var(e["tag"], by[e["parent"]]["xy"], e["xy"], e["leg"], e["et"], e["nseg"], ns="t")
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
                tt += edge_var(e["tag"], cby[e["parent"]]["xy"], e["xy"], e["leg"], e["et"], e["nseg"], ns="c")
            if legal:
                q = B["cells"][B["site_of"][("c", leaf)]]["site"]
                farr[(r3(q[0]), r3(q[1]))] = tt
            else:
                farr[(r3(cby[leaf]["xy"][0]), r3(cby[leaf]["xy"][1]))] = tt
    # 4) fine mesh (r2 lattice, straps over the r2 extents) + partition entry taps; LEGAL: drivers attach at their
    #    legal sites on their own column strap, strength = the real cells of the group
    fdrv = sorted(farr)
    NF = mesh(hs_f, vs_f, fdrv, taps, fw, (RC3[a.stub_w], a.stub_um), wire_rel=sg.get("wire_rel", 0.0) if s else 0.0, rnd=rnd)
    cvor = voronoi_c(NF)
    if legal:
        fm_at = {(r3(B["cells"][B["site_of"][("c", n["tag"])]]["site"][0]), r3(B["cells"][B["site_of"][("c", n["tag"])]]["site"][1])):
                 B["cells"][B["site_of"][("c", n["tag"])]]["masters"] for ct in B["ctrees"] for n in ct["nodes"] if not n["kids"]}
        fmult = np.array([sum(BUF_STRENGTH[m] for m in fm_at[q]) for q in fdrv])
    else:
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
               tap_skew_ps=r3(float(np.nanmax(t_ent) - np.nanmin(t_ent))), tap_arr_ps=tap_arr,
               tap_slew_ps={p: r3(v) for p, v in zip(parts, sl_ent)}, geometry=a.geometry, feed=getattr(a, "feed", "mesh3"),
               checked="UNCHECKED")
    if legal:
        ets = dict(t=B["et"]["top"], c=B["et"]["col"])
        uq = [(L, ets[k[0]]) for k, v in PE.items() for _, _, L in v]       # every real net once
        Ls = [L for L, _ in uq]
        over = [(L, et) for L, et in uq if L > et.reach + 1e-6]
        out["physical"] = dict(legal=lstat, nets=len(Ls), net_um=dict(min=r3(min(Ls)), max=r3(max(Ls))),
                               nets_over_reach=len(over), worst_over_reach_slew_ps=r3(max((et.st.slew(et.w, et.m, c, L) for L, et in over), default=0.0)),
                               note="every tree stage = one real driver->load net between legal cell pins (units expanded); "
                                    "the stage table is extrapolated above reach (slew reported)")
    if B.get("r9"):
        R = B["r9"]
        out["r9_feed"] = dict(source=R["source"], regions=R["regions"], region_nominal_spread_TT_ps=R["region_nominal_spread_TT_ps"],
                              leaf_arr_ps={k: r3(v) for k, v in r9arr.items()})
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
    if mc and "physical" in mc[0]:
        summ["mc_net_um_max"] = max(r["physical"]["net_um"]["max"] for r in rows)
    out = dict(summary=summ, samples=[dict(sample=r["sample"], tap_skew_ps=r["tap_skew_ps"], tap_arr_ps=r["tap_arr_ps"]) for r in rows],
               checked="UNCHECKED")
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in summ.items() if k != "nominal"}, indent=1))
    return 0


# ------------------------------------------------------------------------------------------------ pairs (approved AOCV)
def pair_u(x, y, tap, solve_, aocv, g):
    """per related pair (partition entries x, y on the one signed mesh): mesh uncertainty = the pair's worst MC tap
    difference |t_x - t_y| over the samples (signed-mesh common point, 12.4a b), plus the approved AOCV below the mesh
    (class A depth sigma k=3 on stub + 10 stages each side; g x bbox diagonal x unshared delay), droop 0 (one mesh)."""
    import region_clock as RC
    CORE = RC.CORE_LAT
    r = dict(a=x, b=y, common="continuous signed die mesh (12.4a b exception)")
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
    return r


def cmd_sta_export(a):
    """die_sta_related.py input from the mesh solves: OUT/tap_arrivals_<C>.json (one entry tap per partition, nominal
    arrival late = early, one cppr node 'm' = the signed mesh with range 0: no mesh-node credit) + OUT/pair_unc.json
    (pair_u total per corner for every port-connected partition pair and every seam pair)."""
    import qc_clk_mesh as Q
    import region_clock as RC
    rec = json.loads(Path(a.r2).read_text())
    P, dtp, parts, cores, psha = Q.load(rec["plan"], rec["tree_plan"])
    solve_ = {c: json.loads(Path(v).read_text()) for c, v in json.loads(a.mesh_skew).items()}
    aocv = json.loads(Path(a.aocv).read_text())["clock_aocv"]
    tap = {t["part"]: t for t in rec["taps"]}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # real core views (signed-off RCX / GRT model) per hard-core module: the partition's core clock latency range is the
    # union over its hard cores (a viewed module -> its [early, late]; others -> the declared 12.3 common latency),
    # folded into the entry arrivals as the delta to the declared latency (die_sta_related cancels the declared value)
    decl = {k: float(v) for k, v in (kv.split("=") for kv in a.declared.split(","))}
    views = {}
    for cv in a.core_view:
        mod, vals = cv.split("=")
        te, tl, fe, fl = (float(v) for v in vals.split(","))
        views[mod] = {"TT": (te, tl), "FF": (fe, fl)}
    ptype = {q["name"]: q["type"] for q in json.loads(Path(rec["plan"]).read_text())["partitions"]}
    PT = json.loads(Path(rec["plan"]).read_text())["partition_types"]
    delta, used = {}, defaultdict(list)
    for part, ty in ptype.items():
        mods = {h["module"] for h in PT.get(ty, {}).get("hard_cores", [])}
        if not mods & set(views):
            continue
        for c in ("TT", "FF"):
            lo = min([views[m][c][0] for m in mods if m in views] + ([decl[c]] if mods - set(views) else []))
            hi = max([views[m][c][1] for m in mods if m in views] + ([decl[c]] if mods - set(views) else []))
            delta[(part, c)] = (lo - decl[c], hi - decl[c])
        used[part] = sorted(mods & set(views))
    for c, d in solve_.items():
        nom = [s_ for s_ in d["samples"] if s_["sample"] == 0][0]
        sl = d["summary"]["nominal"].get("tap_slew_ps") or {}
        rows = [dict(port=p, part=p, late_ps=v + delta.get((p, c), (0.0, 0.0))[1], early_ps=v + delta.get((p, c), (0.0, 0.0))[0],
                     cppr_node="m", slew_ps=sl.get(p, 190.0), xy_um=tap[p]["entry"], stages_from_root=None,
                     core_view=used.get(p)) for p, v in nom["tap_arr_ps"].items()]
        (out / f"tap_arrivals_{c}.json").write_text(json.dumps(dict(
            corner=c, basis=f"qc_clk_mesh3 solve nominal ({d['summary']['nominal'].get('geometry', 'ideal')} geometry, "
                            f"feed {d['summary']['nominal'].get('feed', 'mesh3')}); per-pair MC+AOCV in pair_unc.json",
            cppr_node_range_ps={"m": 0.0, "h": 0.0}, core_views=dict(views={m: v[c] for m, v in views.items()},
                                                                      declared_ps=decl[c], partitions=sorted(used)),
            taps=rows), indent=1))
    plan = json.loads(Path(rec["plan"]).read_text())
    keys = set()
    for pr in plan["ports"]:
        s_, t_ = pr["src"]["part"], pr["dst"]["part"]
        if s_ != t_ and s_ in tap and t_ in tap:
            keys.add(tuple(sorted((s_, t_))))
    seam = {tuple(sorted((x, y))) for x, y, _ in RC.seam_pairs(P, parts) if x in tap and y in tap}
    U = {"TT": {}, "FF": {}}
    rows = []
    for x, y in sorted(keys | seam):
        r = pair_u(x, y, tap, {c: d["samples"] for c, d in solve_.items()}, aocv, a.g_per_mm)
        r["port_connected"], r["seam"] = (x, y) in keys, (x, y) in seam
        for c, d in solve_.items():
            # the STA carries the NOMINAL arrivals, so its pair uncertainty takes only the MC spread AROUND the
            # nominal pair difference (no double count of the nominal skew): max_s |dt_s - dt_0| + AOCV below the mesh
            sm = d["samples"]
            d0 = [s_ for s_ in sm if s_["sample"] == 0][0]["tap_arr_ps"]
            var = max(abs((s_["tap_arr_ps"][x] - s_["tap_arr_ps"][y]) - (d0[x] - d0[y])) for s_ in sm)
            r[c]["mesh_mc_var_ps"] = r3(var)
            r[c]["nominal_dt_ps"] = r3(d0[x] - d0[y])
            r[c]["sta_unc_ps"] = r3(r[c]["aocv_random_ps"] + r[c]["aocv_distance_ps"] + var)
            U[c][f"{x}|{y}"] = r[c]["sta_unc_ps"]
        rows.append(r)
    (out / "pair_unc.json").write_text(json.dumps(dict(schema="ot_qc_pair_unc/1", g_per_mm=a.g_per_mm, aocv=a.aocv,
                                                       mesh_skew=json.loads(a.mesh_skew), U=U, rows=rows,
                                                       checked="UNCHECKED"), indent=1))
    print(json.dumps(dict(port_pairs=len(keys), seam_pairs=len(seam), union=len(rows),
                          TT_max=max(U["TT"].values()), FF_max=max(U["FF"].values()))))
    return 0


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
        r = pair_u(x, y, tap, solve_, aocv, g)
        r["edge_um"] = edge
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
    p.add_argument("--feed", default="mesh3", choices=["mesh3", "r9", "periodic"],
                   help="global tree: mesh3 own top tree (default) or the R9 16-leaf physical H-tree (--r9-dir)")
    p.add_argument("--islands", default="none", choices=["none", "type"],
                   help="R12: type = solve + place the top tree on ONE per-partition-type island lattice (12.2a1/12.2c)")
    p.add_argument("--island-pitch", type=float, default=19.3, help="island slot pitch um, y (type frame)")
    p.add_argument("--island-corr", default=None,
                   help="R12 re-solve: json {corr: {edge_tag: {TT, FF}}} = legal - model edge delay of the previous placement")
    p.add_argument("--island-pitch-x", type=float, default=4.86, help="island slot pitch um, x (type frame; 3 BUFx24 widths)")
    p.add_argument("--lanes", default="none", choices=["none", "vss"],
                   help="R15 (opt-in, --feed periodic --islands type): VSS-phase slot rows + one 8.64-um lane per tree level, "
                        "leaves re-balanced by their plan-computed downstream delay, centre fine row split at the seam")
    p.add_argument("--island-edge-sym", action="store_true",
                   help="R16 (with --lanes vss): VSS slot rows keep the 8.64 lane at BOTH type-frame edges (see vss_grid)")
    p.add_argument("--ytree-split", default=None,
                   help="R16 (with --lanes vss): comma list TAG=H, y-tree subtree TAG (T_b, T_b0, T_b1, ...) splits h | n-h")
    p.add_argument("--row-at", default=None,
                   help="R16: comma list G=Y: bottom-half gap row G gets its local row at Y (< G: lanes step away from the "
                        "die centre; mirrored in the top half); default none = R15 behaviour")
    p.add_argument("--centre-split", type=float, default=ISL, help="R15: centre fine row split -> YC -/+ this (um)")
    p.add_argument("--r9-dir", default=str(HERE.parent.parent / "results/qc_clk_mesh3/r10_inputs"),
                   help="r9_lattice.json + r9_tree5_tree_{TT,FF}_rcx.txt")


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
    s.add_argument("--geometry", default="legal", choices=["legal", "ideal"],
                   help="legal (default, r10): time the legalize() cells with units expanded and pin-to-pin nets; "
                        "ideal = the r3 plan-model geometry (comparison only)")
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
    x = sub.add_parser("sta-export")
    x.add_argument("--r2", required=True)
    x.add_argument("--mesh-skew", required=True, help='{"TT": collect.json, "FF": collect.json}')
    x.add_argument("--aocv", required=True)
    x.add_argument("--g-per-mm", type=float, default=0.0021)
    x.add_argument("--core-view", action="append", default=[],
                   help="MODULE=TTearly,TTlate,FFearly,FFlate core clock latency range of a real (signed / GRT) core view")
    x.add_argument("--declared", default="TT=250,FF=202.5", help="12.3 declared common core latency per corner")
    x.add_argument("--out", required=True)
    x.set_defaults(fn=cmd_sta_export)
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
