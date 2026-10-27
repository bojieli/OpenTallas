#!/usr/bin/env python3
"""QC-MP-REGION (MASTER-PLAN, 12.7 / 12.8 / 12.2a1): the die clock distribution BELOW the die H-tree lattice leaves.

The R5 lattice (die_tree_plan.json lattice.nodes, --tree-lattice cNXxNY) stops at NX x NY region leaves.  This module
declares, from plan geometry only (no measurement, deterministic), the regional distribution from every region leaf
to the planned centre clock entry of every partition in that region (type clock.tap_um, the M9 entry where the
12.3 common latency budget 250 TT / 202.5 FF starts; the partition / core kits own everything below it):

  * one regional tree per leaf: recursive median bipartition of the region's entries (longer bbox side first),
    zero-skew merge points (delay-balanced position on the Manhattan path between the two children), every merge
    point SNAPPED to the 8.64 um island lattice on a legal pushdown-island site (inside a partition, outside every
    hard core, clear of other islands); the region leaf (lattice node) is the region root;
  * legs: Manhattan polylines (x-first / y-first, whichever puts fewer repeater cuts inside hard cores), shielded
    (same NDR / shield rule as the lattice legs), n equal cuts with every cut a partition-bay repeater site;
  * balance by construction: per leg the plan chooses the repeater count n >= ceil(L / 450) and a plan-computed
    U-detour (12.8 d1 per-tap sizing from plan geometry, recorded and frozen with the plan) so every leaf -> entry
    path has the same modelled TT delay, and every region the same leaf -> entry delay (die-wide balance).
    No trims, pads, early taps or post-measurement values: nothing here reads a measured arrival.

QC-MP-REGION-2 plan delta (COORD ruling 10-26 16:57): legs are routed through channels -- L, Z (x-y-x / y-x-y with
the middle run on a channel just outside a hard-core edge), channel overshoot and in-channel hairpin (trombone)
detours, chosen by an analytic blocked-run prefilter + legal partition-bay cuts; a leg with no in-box channel
overshoots to the nearest channel and its parent re-fits (balance stays exact).  The region topology is the lower
ACHIEVABLE TT of median bipartition and greedy-DME; regions far below the die target get one pad leg (pad node beside
the lattice leaf) instead of padding both root legs; a target inside a stage-quantisation gap takes the n-stage leg at
full segment length when <= GAP_TOL_PS short (declared residual TT window).  All plan-computed (12.8 d1).

Delay model (12.9d predict-before-build): per stage d = D0 + K x L_seg, calibrated ONCE on the CLOCK-128-R4
QC tree-only build (claude/clock128-r4-1026@1e8203d640, geometry SPEF of the shielded BUFx24 lattice legs,
epyc1:/srv/opentallas-scratch2/claude/clock128-r4-1026/tree/tree_{TT,FF}.txt + mesh.json, 14 internal legs, least
squares; UNCHECKED basis, not RCX).  The FF residual window is what the TT balance leaves at FF (D0/K differ).
"""
import argparse
import bisect
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# per stage delay d = D0 + K * L_seg (ps, um); CLOCK-128-R4 tree-only calibration, 14 legs (rms TT 13.3 / FF 10.7 ps)
STAGE = {"TT": (52.713, 0.058822), "FF": (38.561, 0.060298)}
STAGE_CAL = dict(source="CLOCK-128-R4 tree-only build claude/clock128-r4-1026@1e8203d640 "
                        "(epyc1:/srv/opentallas-scratch2/claude/clock128-r4-1026/tree, geometry SPEF, not RCX)",
                 legs=14, rms_ps=dict(TT=13.25, FF=10.67), max_err_ps=dict(TT=30.99, FF=25.08), checked="UNCHECKED")
REP_UM = 450.0
GAP_TOL_PS = 8.0                # QC-MP-REGION-2: max TT shortfall accepted at a stage-quantisation gap (window)
ISL = 8.64                      # island side / lattice pitch
CORE_LAT = {"TT": 250.0, "FF": 202.5}
# die_ci_margins.json (repo convention, flat OCV without LVF): cells +-5 %, nets +-3 %, IR +5.1 % late on cells
DERATE = dict(cell_late=0.05, cell_early=0.05, net_late=0.03, net_early=0.03, ir_late=0.051)


def r3(v):
    return round(float(v), 3)


def stage_delay(L, n, c="TT"):
    d0, k = STAGE[c]
    return n * d0 + k * L


def n_min(L):
    return max(1, int(math.ceil(L / REP_UM - 1e-9)))


def fit_leg(L, target, ff_target=None, n_floor=1):
    """(n, detour_um): n * D0 + K * (L + detour) == target (TT) exactly, (L + detour) / n <= REP_UM,
    n >= ceil(L / 450), detour >= 0.  Among the feasible n the plan picks the one whose FF delay is closest to
    ff_target (stages vs wire have different FF/TT ratios), else the smallest detour.  target below the natural
    delay -> (n_min, 0) and the shortfall is reported."""
    d0, k = STAGE["TT"]
    n0 = max(n_min(L), n_floor)
    if target <= stage_delay(L, n0) + 1e-9:
        return n0, 0.0
    n_hi = int(math.floor((target - k * L) / d0 + 1e-9))
    n_lo = max(n0, int(math.ceil(target / (d0 + k * REP_UM) - 1e-9)))
    cand = [(n, (target - n * d0) / k - L) for n in range(n_lo, max(n_lo, n_hi) + 1)]
    cand = [(n, max(0.0, dt)) for n, dt in cand if dt >= -1e-6 and (L + max(0.0, dt)) / n <= REP_UM + 1e-6]
    if not cand:
        # target in a stage-quantisation gap (n full 450 um stages too fast, n + 1 stages too slow): QC-MP-REGION-2
        # takes the n-stage leg at full segment length when it is at most GAP_TOL_PS short (declared residual
        # window), instead of raising the parent node by up to a whole stage
        n_s = max(n0, n_lo - 1)
        if n_s * REP_UM >= L and target - stage_delay(n_s * REP_UM, n_s) <= GAP_TOL_PS:
            return n_s, n_s * REP_UM - L
        cand = [(n_lo, max(0.0, (target - n_lo * d0) / k - L))]
    if ff_target is None:
        return min(cand, key=lambda c: c[1])
    return min(cand, key=lambda c: (abs(stage_delay(L + c[1], c[0], "FF") - ff_target), c[1]))


class Legal:
    """legal pushdown-island sites: 8.64 lattice, island inside a partition, clear of every hard core (+ island)."""

    def __init__(self, parts, cores, B=400.0):
        self.parts, self.cores, self.B = parts, cores, B
        self.cb = defaultdict(list)
        for c in cores:
            for i in range(int(c[0] // B), int(c[2] // B) + 1):
                for j in range(int(c[1] // B), int(c[3] // B) + 1):
                    self.cb[(i, j)].append(c)
        self.pb = defaultdict(list)
        for p in parts:
            for i in range(int(p[0] // B), int(p[2] // B) + 1):
                for j in range(int(p[1] // B), int(p[3] // B) + 1):
                    self.pb[(i, j)].append(p)
        self.taken = set()

    def in_core(self, xy, m=0.0):
        for c in self.cb.get((int(xy[0] // self.B), int(xy[1] // self.B)), []):
            if c[0] - m <= xy[0] <= c[2] + m and c[1] - m <= xy[1] <= c[3] + m:
                return c
        return None

    def part(self, xy, m=0.0):
        for p in self.pb.get((int(xy[0] // self.B), int(xy[1] // self.B)), []):
            if p[0] + m <= xy[0] <= p[2] - m and p[1] + m <= xy[1] <= p[3] - m:
                return p[4]
        return None

    def bay(self, xy):
        """partition-bay repeater point: inside a partition (1 row in), outside every hard core (+1 um)."""
        return self.part(xy, 0.27) is not None and self.in_core(xy, 1.0) is None

    def ok(self, xy):
        h = ISL / 2
        return (self.part(xy, h) is not None and self.in_core(xy, h) is None
                and (round(xy[0] / ISL), round(xy[1] / ISL)) not in self.taken)

    def blocked(self, poly, m=1.0):
        """continuous runs (um) along a Manhattan polyline that lie inside a hard core (+m): a run longer than one
        repeater segment cannot host a partition-bay cut (analytic prefilter of place_reps)."""
        runs, cur, s0 = [], 0.0, 0.0
        for i in range(len(poly) - 1):
            a, b = poly[i], poly[i + 1]
            L = md(a, b)
            if L <= 1e-9:
                continue
            ax = 0 if abs(b[0] - a[0]) > 1e-9 else 1          # running axis
            lo, hi = min(a[ax], b[ax]), max(a[ax], b[ax])
            fx = a[1 - ax]
            iv = []
            seen = set()
            for k in range(int(lo // self.B), int(hi // self.B) + 1):
                key = (k, int(fx // self.B)) if ax == 0 else (int(fx // self.B), k)
                for c in self.cb.get(key, []):
                    if id(c) in seen:
                        continue
                    seen.add(id(c))
                    if c[1 - ax] - m <= fx <= c[3 - ax] + m:
                        u0, u1 = max(lo, c[ax] - m), min(hi, c[2 + ax] + m)
                        if u1 > u0:
                            iv.append((u0, u1))
            iv.sort()
            mg = []
            for u0, u1 in iv:
                if mg and u0 <= mg[-1][1] + 1e-6:
                    mg[-1][1] = max(mg[-1][1], u1)
                else:
                    mg.append([u0, u1])
            fwd = b[ax] >= a[ax]
            # map to arc length along this segment from a
            arcs = sorted(((u0 - lo, u1 - lo) if fwd else (hi - u1, hi - u0)) for u0, u1 in mg)
            pos = 0.0
            for s_, e_ in arcs:
                if s_ <= pos + 1e-6 and cur > 0:
                    cur += e_ - pos
                else:
                    if cur > 0:
                        runs.append(cur)
                    cur = e_ - s_
                pos = e_
            if pos < L - 1e-6 and cur > 0:
                runs.append(cur)
                cur = 0.0
        if cur > 0:
            runs.append(cur)
        return runs

    def channels(self, ax, lo, hi, span, m=2.16):
        """candidate channel coordinates on axis ax (0: x of a vertical run) just outside the edges of every hard
        core that overlaps the run's span [span0, span1] and lies within [lo, hi]."""
        out = set()
        s0, s1 = min(span), max(span)
        for k in range(int(lo // self.B) - 1, int(hi // self.B) + 2):
            for j in range(int(s0 // self.B), int(s1 // self.B) + 1):
                key = (k, j) if ax == 0 else (j, k)
                for c in self.cb.get(key, []):
                    if c[3 - ax] < s0 or c[1 - ax] > s1:
                        continue
                    for v in (c[ax] - m, c[2 + ax] + m):
                        if lo - 1e-6 <= v <= hi + 1e-6:
                            out.add(round(v, 3))
        return sorted(out)

    def snap(self, xy, rmax=800.0):
        """nearest legal island-lattice point (Manhattan rings on the 8.64 lattice)."""
        i0, j0 = round(xy[0] / ISL), round(xy[1] / ISL)
        R = int(rmax / ISL)
        for r in range(0, R + 1):
            best = None
            for di in range(-r, r + 1):
                for dj in {r - abs(di), -(r - abs(di))}:
                    q = ((i0 + di) * ISL, (j0 + dj) * ISL)
                    if self.ok(q):
                        d = abs(q[0] - xy[0]) + abs(q[1] - xy[1])
                        if best is None or d < best[0]:
                            best = (d, q)
            if best:
                self.taken.add((round(best[1][0] / ISL), round(best[1][1] / ISL)))
                return best[1], best[0]
        return None, None


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def point_on(a, b, s, xfirst=True):
    """point at Manhattan arc length s from a on the L path a -> b."""
    d1 = abs(b[0] - a[0]) if xfirst else abs(b[1] - a[1])
    if xfirst:
        if s <= d1:
            return (a[0] + math.copysign(s, b[0] - a[0]), a[1])
        return (b[0], a[1] + math.copysign(s - d1, b[1] - a[1]))
    if s <= d1:
        return (a[0], a[1] + math.copysign(s, b[1] - a[1]))
    return (a[0] + math.copysign(s - d1, b[0] - a[0]), b[1])


def polyline(a, b, xfirst, detour, at_end=False):
    """Manhattan polyline a -> b; a plan detour is a U of depth detour/2 on the secondary axis, pointing AWAY from
    the other end (so the drawn length is exactly L + detour), at the start (or at the end) of the leg."""
    if detour <= 1e-6:
        mid = (b[0], a[1]) if xfirst else (a[0], b[1])
        return [list(a), list(mid), list(b)]
    h = detour / 2.0
    j = 1 if xfirst else 0              # secondary axis index
    if not at_end:
        sg = -1.0 if b[j] > a[j] else 1.0
        o = list(a)
        o[j] = a[j] + sg * h
        m = list(o)
        m[1 - j] = b[1 - j]
        return [list(a), o, m, list(b)]
    sg = -1.0 if a[j] > b[j] else 1.0
    o = list(b)
    o[j] = b[j] + sg * h
    m = list(o)
    m[1 - j] = a[1 - j]
    return [list(a), m, o, list(b)]


def _plen(poly):
    return sum(md(poly[i], poly[i + 1]) for i in range(len(poly) - 1))


def _clean(poly):
    out = [list(poly[0])]
    for p in poly[1:]:
        if md(p, out[-1]) > 1e-9:
            out.append(list(p))
    # drop collinear midpoints
    k = 1
    while k < len(out) - 1:
        a, b, c = out[k - 1], out[k], out[k + 1]
        if (abs(a[0] - b[0]) < 1e-9 and abs(b[0] - c[0]) < 1e-9 and (b[1] - a[1]) * (c[1] - b[1]) > 0) or \
           (abs(a[1] - b[1]) < 1e-9 and abs(b[1] - c[1]) < 1e-9 and (b[0] - a[0]) * (c[0] - b[0]) > 0):
            out.pop(k)
        else:
            k += 1
    return out


HAIR = ISL      # hairpin pitch: the return run of a plan detour sits one island pitch beside the outgoing run


def zroute(a, b, ax, v, det, at_end):
    """QC-MP-REGION-2 channel route a -> b of drawn length exactly md(a, b) + det, or None.
    ax 0 ('Zx'): a -> (v, a.y) -> (v, b.y) -> b, the vertical run in the channel at x = v (x-y-x);
    ax 1 ('Zy'): a -> (a.x, v) -> (b.x, v) -> b, the horizontal run in the channel at y = v (y-x-y).
    v outside the a-b box costs 2 x the overshoot; any remaining detour is a hairpin (trombone) of the channel run
    past its far end (at_end) or before its start, return run HAIR beside it in the same channel."""
    j = 1 - ax                              # run axis of the channel run (y for Zx)
    L = md(a, b)
    lo, hi = min(a[ax], b[ax]), max(a[ax], b[ax])
    over = max(0.0, lo - v, v - hi)
    r = det - 2.0 * over
    if r < -1e-6:
        return None
    p1 = list(a)
    p1[ax] = v
    p2 = list(b)
    p2[ax] = v
    if r <= 1e-6:
        return _clean([list(a), p1, p2, list(b)])
    # hairpin: run from p1 along j past p2 (at_end) or backwards past p1 (start), step HAIR toward b[ax], return
    d = HAIR if b[ax] >= v else -HAIR
    if abs(b[ax] - v) < HAIR - 1e-6:
        d = HAIR if a[ax] <= v else -HAIR
    sgn = 1.0 if p2[j] >= p1[j] else -1.0
    if at_end:
        def mk(t):
            e1 = list(p2)
            e1[j] = p2[j] + sgn * t
            e2 = list(e1)
            e2[ax] = v + d
            e3 = list(e2)
            e3[j] = p2[j]
            return [list(a), list(p1), e1, e2, e3, list(b)]
    else:
        def mk(t):
            e1 = list(p1)
            e1[j] = p1[j] - sgn * t
            e2 = list(e1)
            e2[ax] = v + d
            e3 = list(e2)
            e3[j] = p2[j]
            return [list(a), list(p1), e1, e2, e3, list(b)]
    base_len = _plen(mk(0.0))
    t = (L + det - base_len) / 2.0
    if t < -1e-6:
        return None
    poly = _clean(mk(max(0.0, t)))
    if abs(_plen(poly) - (L + det)) > 1e-3:
        return None
    return poly


def route_cands(a, b, det, legal, kmax=6):
    """all channel route candidates a -> b with drawn length md + det (L, Z through channels, overshoot, hairpin
    detour, and the R1 U shapes), ranked by the analytic blocked-run prefilter; returns the best kmax as
    (name, poly)."""
    L = md(a, b)
    cands = []
    for xf in (True, False):
        for at_end in ((False, True) if det > 1e-6 else (False,)):
            cands.append((("x_first" if xf else "y_first") + ("+U_end" if at_end else ("+U_start" if det > 1e-6 else "")),
                          polyline(a, b, xf, det, at_end)))
    for ax in (0, 1):
        lo, hi = min(a[ax], b[ax]), max(a[ax], b[ax])
        reach = det / 2.0
        vs = set(legal.channels(ax, lo - reach, hi + reach, (a[1 - ax], b[1 - ax])))
        vs.update((a[ax], b[ax]))
        for v in sorted(vs):
            for at_end in ((False, True) if det > 1e-6 else (False,)):
                p = zroute(a, b, ax, v, det, at_end)
                if p is not None:
                    cands.append((("Zx@%.2f" if ax == 0 else "Zy@%.2f") % v + ("+hair_end" if at_end and det > 1e-6 else
                                                                               ("+hair_start" if det > 1e-6 else "")), p))
    scored = []
    for name, p in cands:
        runs = legal.blocked(p)
        hard = sum(int(math.ceil((r_ - 0.6 * REP_UM) / REP_UM)) for r_ in runs if r_ > 0.6 * REP_UM)
        scored.append(((hard, len(p), round(sum(runs), 1), name), name, p))
    scored.sort(key=lambda z: z[0])
    out, seen = [], set()
    for _, name, p in scored:
        k = tuple(map(tuple, p))
        if k in seen:
            continue
        seen.add(k)
        out.append((name, p))
        if len(out) >= kmax:
            break
    return out


def place_reps(poly, n, legal, step=4.32):
    """repeater sites along the polyline: every segment <= REP_UM, exactly n segments, every cut on a legal
    partition-bay point (inside a partition, outside hard cores).  The stage model is additive per segment, so
    unequal cuts keep the modelled delay n * D0 + K * L.  Returns (points, ok)."""
    segs = [(poly[i], poly[i + 1], md(poly[i], poly[i + 1])) for i in range(len(poly) - 1)]
    L = sum(s_[2] for s_ in segs)

    def at(s):
        for a, b, l in segs:
            if s <= l + 1e-9:
                t = s / l if l else 0.0
                return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            s -= l
        return tuple(poly[-1])
    m = int(L // step)
    good = [i * step for i in range(1, m + 1) if i * step < L - 1e-6 and legal.bay(at(i * step))]
    cutsS, last, ok = [], 0.0, True
    while L - last > REP_UM + 1e-6:
        c = [s for s in good if last + 1e-6 < s <= last + REP_UM]
        if not c:
            ok = False
            last = last + REP_UM
            cutsS.append(last)
            continue
        last = max(c)
        cutsS.append(last)
    # add cuts until n segments: split the longest segment at the legal point closest to its middle
    while len(cutsS) + 1 < n:
        b_ = [0.0] + cutsS + [L]
        i = max(range(len(b_) - 1), key=lambda i: b_[i + 1] - b_[i])
        mid = (b_[i] + b_[i + 1]) / 2
        c = [s for s in good if b_[i] + 1e-6 < s < b_[i + 1] - 1e-6 and s not in cutsS]
        if not c:
            ok = False
            cutsS.append(mid)
        else:
            cutsS.append(min(c, key=lambda s: abs(s - mid)))
        cutsS.sort()
    return [at(s) for s in cutsS], ok, L, cutsS


def cuts(poly, n):
    segs = [(poly[i], poly[i + 1], md(poly[i], poly[i + 1])) for i in range(len(poly) - 1)]
    L = sum(s[2] for s in segs)
    out = []
    for k in range(1, n):
        s = L * k / n
        for a, b, l in segs:
            if s <= l + 1e-9:
                t = s / l if l else 0.0
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
                break
            s -= l
    return out, L


def endpoints(P, sites):
    """one planned centre clock entry per partition (type clock.tap_um -> die), bound to its die_node island."""
    by_part = {q["inst"]: q for q in sites if q.get("role") == "die_node"}
    out = []
    for part in sorted(P.parts):
        t = P.ptype(part)
        xy = (t.get("clock") or {}).get("tap_um")
        w, h = t["outline_um"]
        src = "type clock.tap_um"
        if not xy:
            xy, src = (w / 2, h / 2), "outline centre (no clock.tap_um)"
        X, Y = P.to_die(part, tuple(xy))
        q = by_part.get(part)
        out.append(dict(part=part, type=P.parts[part]["type"], xy_um=[r3(X), r3(Y)], source=src,
                        island_site=(q or {}).get("id"),
                        island_offset_um=r3(md(q["xy_um"], (X, Y))) if q else None,
                        centre_offset_um=r3(abs(xy[0] - w / 2) + abs(xy[1] - h / 2))))
    return out


def region_of(leaves, xy):
    xs = sorted({n["xy_um"][0] for n in leaves})
    ys = sorted({n["xy_um"][1] for n in leaves})
    bx = [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)]
    by = [(ys[i] + ys[i + 1]) / 2 for i in range(len(ys) - 1)]
    key = (xs[bisect.bisect(bx, xy[0])], ys[bisect.bisect(by, xy[1])])
    return key


def build(P, dtp, parts, cores, plan_sha=None, die_balance=True):
    lat = dtp["lattice"]["nodes"]
    kids = defaultdict(list)
    for n_ in lat:
        if n_["parent"] is not None:
            kids[n_["parent"]].append(n_["tag"])
    by_tag = {n_["tag"]: n_ for n_ in lat}
    leaves = [n_ for n_ in lat if not kids[n_["tag"]]]
    leaf_at = {tuple(n_["xy_um"]): n_ for n_ in leaves}
    eps = endpoints(P, dtp["sites"])
    legal = Legal(parts, cores)
    for n_ in lat:
        legal.taken.add((round(n_["xy_um"][0] / ISL), round(n_["xy_um"][1] / ISL)))
    for e in eps:
        legal.taken.add((round(e["xy_um"][0] / ISL), round(e["xy_um"][1] / ISL)))
    groups = defaultdict(list)
    for e in eps:
        groups[region_of(leaves, e["xy_um"])].append(e)
    nodes, perr = [], []

    # ---- topology + snapped merge points (bottom-up), delay-balanced merge position
    def rate(c="TT"):
        d0, k = STAGE[c]
        return d0 / REP_UM + k

    def tree(items, tag, depth):
        if len(items) == 1:
            e = items[0]
            return dict(tag=tag, kind="entry", xy=tuple(e["xy_um"]), part=e["part"], T=0.0, kids=[])
        xs = [i["xy_um"][0] for i in items]
        ys = [i["xy_um"][1] for i in items]
        ax = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
        items = sorted(items, key=lambda i: (i["xy_um"][ax], i["xy_um"][1 - ax], i["part"]))
        m = len(items) // 2
        a, b = tree(items[:m], tag + "0", depth + 1), tree(items[m:], tag + "1", depth + 1)
        d = md(a["xy"], b["xy"])
        x = (d + (b["T"] - a["T"]) / rate()) / 2
        x = min(max(x, 0.0), d)
        ideal = point_on(a["xy"], b["xy"], x, xfirst=True)
        xy, disp = legal.snap(ideal)
        if xy is None:
            perr.append(dict(kind="no_island_site", name=tag, detail=f"no legal 8.64 island within 800 um of {ideal}"))
            xy, disp = ideal, None
        nd = dict(tag=tag, kind="node", xy=xy, ideal=ideal, disp=disp, kids=[a, b], depth=depth)
        nd["T"] = max(stage_delay(md(xy, k_["xy"]), n_min(md(xy, k_["xy"]))) + k_["T"] for k_ in (a, b))
        return nd

    def gdme(items, rt):
        """QC-MP-REGION-2 topology alternative: greedy bottom-up zero-skew merging (Greedy-DME): repeatedly merge the
        pair of subtrees with the least balanced merge wire max(d, |dT| / rate), merge point delay-balanced on the
        Manhattan path and snapped to the island lattice like the bipartition; the region leaf feeds the final
        merge node through ONE root leg (which also carries the die-wide padding)."""
        subs = [dict(tag=None, kind="entry", xy=tuple(e["xy_um"]), part=e["part"], T=0.0, kids=[]) for e in
                sorted(items, key=lambda i: i["part"])]
        while len(subs) > 1:
            best = None
            for i in range(len(subs)):
                for j in range(i + 1, len(subs)):
                    a, b = subs[i], subs[j]
                    c = max(md(a["xy"], b["xy"]), abs(a["T"] - b["T"]) / rate())
                    if best is None or c < best[0] - 1e-9:
                        best = (c, i, j)
            _, i, j = best
            a, b = subs[i], subs[j]
            d = md(a["xy"], b["xy"])
            x = min(max((d + (b["T"] - a["T"]) / rate()) / 2, 0.0), d)
            ideal = point_on(a["xy"], b["xy"], x, xfirst=True)
            xy, disp = legal.snap(ideal)
            if xy is None:
                perr.append(dict(kind="no_island_site", name=rt, detail=f"no legal 8.64 island within 800 um of {ideal}"))
                xy, disp = ideal, None
            nd = dict(tag=None, kind="node", xy=xy, ideal=ideal, disp=disp, kids=[a, b], depth=0)
            nd["T"] = max(stage_delay(md(xy, k_["xy"]), n_min(md(xy, k_["xy"]))) + k_["T"] for k_ in (a, b))
            subs = [s_ for k, s_ in enumerate(subs) if k not in (i, j)] + [nd]
        top = subs[0]

        def retag(nd, tag, depth):
            nd["tag"], nd["depth"] = tag, depth
            for k, k_ in enumerate(nd["kids"]):
                retag(k_, tag + str(k), depth + 1)
        retag(top, rt + "_0", 1)
        return top

    regions = []
    alts = {}
    base_taken = set(legal.taken)
    for key in sorted(groups):
        leaf = leaf_at[key]
        items = groups[key]
        rt = "r" + leaf["tag"][1:]
        opts = []
        for topo in ("bipartition", "greedy_dme"):
            legal.taken = set(base_taken)
            if topo == "greedy_dme" or len(items) == 1:
                kids = [gdme(items, rt) if topo == "greedy_dme" else tree(items, rt + "_0", 1)]
            else:
                xs = [i["xy_um"][0] for i in items]
                ys = [i["xy_um"][1] for i in items]
                ax = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
                its = sorted(items, key=lambda i: (i["xy_um"][ax], i["xy_um"][1 - ax], i["part"]))
                m = len(its) // 2
                kids = [tree(its[:m], rt + "_0", 1), tree(its[m:], rt + "_1", 1)]
            root = dict(tag=rt, kind="leaf", xy=tuple(leaf["xy_um"]), depth=0, kids=kids)
            root["T"] = max(stage_delay(md(root["xy"], k_["xy"]), n_min(md(root["xy"], k_["xy"]))) + k_["T"]
                            for k_ in root["kids"])
            opts.append((topo, root, legal.taken - base_taken))
        alts[key] = opts
        regions.append(dict(key=key, leaf=leaf["tag"], root=None, n=len(items)))
    legal.taken = set(base_taken)

    # ---- balance by construction, bottom-up: every node's children reach the entries with the SAME modelled TT
    # delay (the slowest child's natural one); the FF delay is matched as closely as the integer stage choice allows.
    # Then every region root is padded (on its own legs) to the die-wide slowest region (TT), FF matched likewise.
    legs, reps = [], []
    _nl = {}

    def n_legal(a, b):
        """fewest stages a straight (no detour) leg a -> b needs with every cut on a partition-bay site (best
        channel route: fewest cuts off bay sites first)."""
        key = (tuple(a), tuple(b))
        if key not in _nl:
            L = md(a, b)
            best = None
            for name, poly in route_cands(a, b, 0.0, legal, kmax=3):
                pts = place_reps(poly, n_min(L), legal)[0]
                sc = (sum(1 for p in pts if not legal.bay(p)), len(pts) + 1)
                best = sc if best is None or sc < best else best
            _nl[key] = best[1]
        return _nl[key]

    def nat_d(a, b, c="TT"):
        return stage_delay(md(a, b), n_legal(a, b), c)

    def mk_leg(nd, k_, want, want_ff):
        L = md(nd["xy"], k_["xy"])
        n, det = fit_leg(L, want, want_ff, n_floor=n_legal(nd["xy"], k_["xy"]))
        best = None
        for _ in range(4):
            res = []
            for name, poly in route_cands(nd["xy"], k_["xy"], det, legal):
                pts, okp, Ltot, cs = place_reps(poly, n, legal)
                bad = [p for p in pts if not legal.bay(p)]
                b_ = [0.0] + cs + [Ltot]
                mseg = max(b_[i + 1] - b_[i] for i in range(len(b_) - 1))
                score = (len(bad), 1 if len(pts) + 1 > n else 0, round(abs(stage_delay(Ltot, len(pts) + 1) - want), 1),
                         0 if okp else 1, len(poly))
                res.append((score, name, poly, pts, Ltot, bad, len(pts) + 1, det, mseg))
            res.sort(key=lambda z: z[0])
            best = res[0]
            if best[6] <= n:
                break
            # legality forced extra cuts on the best route: one more stage, the plan re-fits the detour (exact TT)
            n = best[6]
            det = max(0.0, (want - n * STAGE["TT"][0]) / STAGE["TT"][1] - L)
        if best[0][0] > 0:
            # no in-box channel: overshoot to the nearest channel outside the box (2 x overshoot more wire). The leg
            # then runs above its target and the parent node re-fits all its legs to it (settle loop): balance
            # stays exact by construction, the node target rises by the overshoot delay.
            a, b = nd["xy"], k_["xy"]
            alt = []
            for ax in (0, 1):
                lo, hi = min(a[ax], b[ax]), max(a[ax], b[ax])
                for v in legal.channels(ax, lo - 1500.0, hi + 1500.0, (a[1 - ax], b[1 - ax])):
                    over = max(0.0, lo - v, v - hi)
                    if over <= 1e-6:
                        continue
                    d2 = max(det, 2.0 * over)
                    for at_end in (False, True):
                        p = zroute(a, b, ax, v, d2, at_end)
                        if p is None:
                            continue
                        n2 = max(n, n_min(L + d2))
                        pts, okp, Ltot, cs = place_reps(p, n2, legal)
                        bad = [q for q in pts if not legal.bay(q)]
                        if len(bad) >= best[0][0]:
                            continue
                        b_ = [0.0] + cs + [Ltot]
                        mseg = max(b_[i + 1] - b_[i] for i in range(len(b_) - 1))
                        alt.append(((len(bad), round(stage_delay(Ltot, len(pts) + 1), 1)),
                                    ("Zx@%.2f" if ax == 0 else "Zy@%.2f") % v + "+overshoot", p, pts, Ltot, bad,
                                    len(pts) + 1, d2, mseg))
            if alt:
                alt.sort(key=lambda z: z[0])
                best = alt[0]
        _, name, poly, pts, Ltot, bad, n, det, mseg = best
        short = want - stage_delay(Ltot, n)
        leg = dict(tag=k_["tag"], parent=nd["tag"], a=[r3(nd["xy"][0]), r3(nd["xy"][1])],
                   b=[r3(k_["xy"][0]), r3(k_["xy"][1])], manhattan_um=r3(L), detour_um=r3(det),
                   len_um=r3(Ltot), n_seg=n, max_seg_um=r3(mseg), route=name,
                   polyline=[[r3(p[0]), r3(p[1])] for p in poly], to=k_["kind"], part=k_.get("part"),
                   tt_ps=r3(stage_delay(Ltot, n, "TT")), ff_ps=r3(stage_delay(Ltot, n, "FF")),
                   tt_shortfall_ps=r3(max(0.0, short)), tt_excess_ps=r3(max(0.0, -short)), repeaters_bad=len(bad))
        rrows = []
        for i, p in enumerate(pts, 1):
            inc = legal.in_core(p, 1.0)
            rrows.append(dict(leg=k_["tag"], k=i, xy_um=[r3(p[0]), r3(p[1])], part=legal.part(p),
                             binding="partition_bay" if legal.bay(p) else
                             ("in_core_conflict" if inc else "outside_partitions"), core=(inc[5] if inc else None)))
        return stage_delay(Ltot, n, "TT"), stage_delay(Ltot, n, "FF"), leg, rrows

    def settle(nd, pad_tt=None, pad_ff=None):
        """finalise nd's subtree; returns (TT, FF) from nd's driver input to its entries."""
        if nd["kind"] == "entry":
            return 0.0, 0.0
        sub = [settle(k_) for k_ in nd["kids"]]
        nat = [nat_d(nd["xy"], k_["xy"]) + s_[0] for k_, s_ in zip(nd["kids"], sub)]
        T = max(nat) if pad_tt is None else max(max(nat), pad_tt)
        iref = nat.index(max(nat))
        if pad_ff is None:
            pad_ff = nat_d(nd["xy"], nd["kids"][iref]["xy"], "FF") + sub[iref][1]
        for _ in range(12):       # a leg whose legal cuts force an extra stage raises the node target, re-fit all
            res, rows = [], []
            for k_, s_ in zip(nd["kids"], sub):
                tt, ff, leg, rr = mk_leg(nd, k_, T - s_[0], pad_ff - s_[1])
                res.append((tt + s_[0], ff + s_[1]))
                rows.append((leg, rr))
            Tm = max(r_[0] for r_ in res)
            if Tm <= T + 0.5:
                break
            pad_ff += (Tm - T) * (pad_ff / T if T else 1.0)
            T = Tm
        for leg, rr in rows:
            legs.append(leg)
            reps.extend(rr)
            if leg["repeaters_bad"]:
                perr.append(dict(kind="leg_rep_site", name=leg["tag"], detail=f"{leg['repeaters_bad']} cuts without a "
                                 "partition-bay site"))
        nd["T"] = T
        nd["T_nat"] = max(nat)
        return T, sum(r_[1] for r_ in res) / len(res)

    # natural per-region TT / FF first (dry run on copies is avoided: the region roots are settled once, padded to the
    # slowest region computed from the natural tree delays)
    def natural(nd):
        if nd["kind"] == "entry":
            return 0.0, 0.0
        v = []
        for k_ in nd["kids"]:
            t_, f_ = natural(k_)
            v.append((nat_d(nd["xy"], k_["xy"]) + t_, nat_d(nd["xy"], k_["xy"], "FF") + f_))
        return max(v)
    # topology per region (plan-computed, deterministic): the alternative with the lower achievable (settled,
    # legal-cut, unpadded) TT leaf -> entry
    def achievable(root):
        """dry-run settle (no die padding): the region's achievable balanced leaf -> entry TT with legal cuts."""
        n0 = (len(legs), len(reps), len(perr))
        t = settle(root)[0]
        del legs[n0[0]:], reps[n0[1]:], perr[n0[2]:]
        return t
    for r_ in regions:
        sc = [(achievable(root), k, topo, root, tk) for k, (topo, root, tk) in enumerate(alts[r_["key"]])]
        sc.sort(key=lambda z: (round(z[0], 3), z[1]))
        nat_t, _, topo, root, tk = sc[0]
        r_["root"], r_["topology"], r_["achievable_tt_ps"] = root, topo, nat_t
        r_["topology_natural_tt_ps"] = {z[2]: r3(z[0]) for z in sc}     # achievable (settled, unpadded) TT
        clash = legal.taken & tk
        if clash:
            perr.append(dict(kind="island_clash", name=r_["leaf"], detail=f"{len(clash)} island sites reused"))
        legal.taken |= tk
    # QC-MP-REGION-2 single pad leg: a region far below the die-wide target whose root drives two subtrees gets
    # ONE pad node (pushdown island next to the lattice leaf); the leaf -> pad-node leg carries the die-wide padding
    # once instead of on both root legs (half the padding wire).  The slowest regions keep the direct root.
    T_est = max(r_["achievable_tt_ps"] for r_ in regions)
    for r_ in regions:
        root = r_["root"]
        if die_balance and len(root["kids"]) > 1 and T_est - r_["achievable_tt_ps"] > 2.0 * STAGE["TT"][0]:
            xy, disp = legal.snap(root["xy"])
            if xy is None:
                continue
            pn = dict(tag=root["tag"] + "_p", kind="node", xy=xy, ideal=root["xy"], disp=disp, kids=root["kids"],
                      depth=1)
            root["kids"] = [pn]
            r_["pad_node"] = pn["tag"]
    nat_reg = [natural(r_["root"]) for r_ in regions]
    T_die, F_die = max(nat_reg)
    n_perr = len(perr)
    for _ in range(8):            # die-wide: re-pad all regions if a legal-cut stage raised any region root
        del legs[:], reps[:], perr[n_perr:]
        for r_ in regions:
            # OPTION A preparation (die_balance False): every region balanced on its own (no die-wide padding);
            # only valid when every seam between regions is a landed/forwarded hop
            settle(r_["root"], T_die if die_balance else None, F_die if die_balance else None)
        Tm = max(r_["root"]["T"] for r_ in regions)
        if not die_balance or Tm <= T_die + 0.5:
            break
        F_die += (Tm - T_die) * F_die / T_die
        T_die = Tm

    # ---- arrivals per entry (model), per corner
    par = {lg["tag"]: lg for lg in legs}
    arr = {}

    def walk(nd, acc):
        for k_ in nd["kids"]:
            lg = par[k_["tag"]]
            a2 = {c: acc[c] + lg[c.lower() + "_ps"] for c in ("TT", "FF")}
            if k_["kind"] == "entry":
                arr[k_["part"]] = dict(a2, path=_path(k_["tag"]))
            else:
                walk(k_, a2)

    def _path(tag):
        return tag

    for r_ in regions:
        walk(r_["root"], {"TT": 0.0, "FF": 0.0})

    def flat(nd, region):
        if nd["kind"] == "node":
            nodes.append(dict(tag=nd["tag"], region=region, depth=nd["depth"], xy_um=[r3(nd["xy"][0]), r3(nd["xy"][1])],
                              ideal_xy_um=[r3(nd["ideal"][0]), r3(nd["ideal"][1])],
                              displacement_um=None if nd["disp"] is None else r3(nd["disp"]),
                              binding="new_partition_island", host=legal.part(nd["xy"]),
                              children=[k_["tag"] for k_ in nd["kids"]],
                              parent=None))
        for k_ in nd["kids"]:
            flat(k_, region)
    for r_ in regions:
        flat(r_["root"], r_["leaf"])
    ptag = {lg["tag"]: lg["parent"] for lg in legs}
    for n_ in nodes:
        n_["parent"] = ptag.get(n_["tag"])
    reg_rows = []
    for r_ in regions:
        a = [arr[e["part"]] for e in groups[r_["key"]]]
        row = dict(leaf=r_["leaf"], leaf_xy_um=list(r_["key"]), entries=r_["n"], topology=r_["topology"],
                   pad_node=r_.get("pad_node"), achievable_tt_ps=r3(r_["achievable_tt_ps"]),
                   topology_natural_tt_ps=r_["topology_natural_tt_ps"],
                   natural_tt_ps=r3(nat_reg[regions.index(r_)][0]),
                   far_um=r3(max(md(r_["key"], e["xy_um"]) for e in groups[r_["key"]])))
        for c in ("TT", "FF"):
            v = [x[c] for x in a]
            row[c] = dict(min_ps=r3(min(v)), max_ps=r3(max(v)), window_ps=r3(max(v) - min(v)))
        reg_rows.append(row)
    out = dict(schema="opentallas.region_distribution.v1", plan_sha256=plan_sha,
               basis="leaf (lattice node) -> partition centre clock entry (type clock.tap_um, M9); 12.3 core latency below",
               topology="regional tree per leaf: median bipartition OR greedy-DME (lower achievable TT, QC-MP-REGION-2), delay-balanced merge points snapped to the 8.64 island lattice; channel Z / hairpin legs; one pad leg per region",
               stage_model=dict(STAGE, cal=STAGE_CAL, rep_um=REP_UM), die_target_tt_ps=r3(T_die),
               regions=reg_rows, nodes=nodes, legs=legs, repeater_sites=reps, entries=eps, arrivals=arr,
               plan_errors=perr)
    return out


# ------------------------------------------------------------------------------------------------ trunk + lattice
def trunk_sites(P, lat_nodes, legal):
    """CLOCK-128-R4 derived trunk cuts declared by the plan: die clock input (clock.spine.root_um) -> lattice root,
    straight, n = ceil(L / 450) equal segments (ckm_t_1..n-1), each a partition-bay site."""
    sp = P.clock.get("spine", {}) or {}
    root_in = tuple(sp.get("die_root_um") or sp.get("root_um"))
    rt = next(n_ for n_ in lat_nodes if n_["parent"] is None)
    txy = tuple(rt["xy_um"])
    L = md(root_in, txy)
    n = n_min(L)
    rows = []
    for k in range(1, n):
        p = (root_in[0] + (txy[0] - root_in[0]) * k / n, root_in[1] + (txy[1] - root_in[1]) * k / n)
        inc = legal.in_core(p, ISL / 2)
        part = legal.part(p)
        rows.append(dict(cell=f"ckm_t_{k}", xy_um=[r3(p[0]), r3(p[1])], part=part,
                         binding="partition_bay" if part and inc is None else ("in_core_conflict" if inc else
                                                                                "outside_partitions")))
    straight = abs(root_in[0] - txy[0]) < 1e-6 or abs(root_in[1] - txy[1]) < 1e-6
    return dict(die_input_um=list(root_in), lattice_root_um=list(txy), len_um=r3(L), n_seg=n, straight=straight,
                sites=rows, verdict="PASS" if straight and all(r["binding"] == "partition_bay" for r in rows) else "FAIL",
                note="build PG-snaps the die input on M9 (<= MAX_MOVE); cuts are re-derived on the snapped input and must "
                     "match these sites within the 0.5 um site tolerance")


def lattice_delay(lat_nodes, gate, trunk):
    """model die input -> each lattice leaf (TT/FF), same stage model as the regions."""
    by = {n_["tag"]: n_ for n_ in lat_nodes}
    out = {}
    base = {c: stage_delay(trunk["len_um"], trunk["n_seg"], c) for c in ("TT", "FF")}
    kids = defaultdict(list)
    for n_ in lat_nodes:
        if n_["parent"]:
            kids[n_["parent"]].append(n_["tag"])

    def rec(tag, acc):
        for ct in kids[tag]:
            L = md(by[tag]["xy_um"], by[ct]["xy_um"])
            a2 = {c: acc[c] + stage_delay(L, n_min(L), c) for c in ("TT", "FF")}
            if not kids[ct]:
                out[ct] = a2
            else:
                rec(ct, a2)
    rt = next(n_ for n_ in lat_nodes if n_["parent"] is None)
    rec(rt["tag"], base)
    return out


# ------------------------------------------------------------------------------------------------ related pairs
def seam_pairs(P, parts, tol=1.0):
    """abutting partition pairs (shared edge > 0 within tol): the die seams with related launch/capture flops."""
    rs = sorted(parts, key=lambda p: p[0])
    out = []
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            if b[0] > a[2] + tol:
                break
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if (abs(ox) <= tol and oy > tol) or (abs(oy) <= tol and ox > tol):
                out.append((a[4], b[4], r3(max(ox, oy))))
    return out


def nc_estimate(R, lat_nodes, lat_arr, trunk, pairs):
    """per related seam pair: last common tree node (lattice + region trees), modelled non-common clock delay per
    side (die part + core 12.3 latency), and the flat-OCV setup/hold pessimism CPPR leaves (die_ci_margins.json)."""
    lat_par = {n_["tag"]: n_["parent"] for n_ in lat_nodes}
    leaf_of = {}
    reg_par = {lg["tag"]: lg["parent"] for lg in R["legs"]}
    ent_tag = {lg["part"]: lg["tag"] for lg in R["legs"] if lg["to"] == "entry"}
    reg_leaf = {r["leaf"]: r for r in R["regions"]}

    def chain(part):
        t = ent_tag[part]
        c = [t]
        while t in reg_par:
            t = reg_par[t]
            c.append(t)
        # region root tag 'r<lattice suffix>' -> lattice leaf 't<suffix>'
        lt = "t" + c[-1][1:]
        while lt is not None:
            c.append(lt)
            lt = lat_par.get(lt)
        return c
    # modelled arrival at every node (TT/FF) from die input
    node_arr = {}
    for lt, a in lat_arr.items():
        node_arr["r" + lt[1:]] = a
    todo = list(R["legs"])
    while todo:
        nxt = []
        for lg in todo:
            pa = node_arr.get(lg["parent"])
            if pa is not None:
                node_arr[lg["tag"]] = {c: pa[c] + lg[c.lower() + "_ps"] for c in ("TT", "FF")}
            else:
                nxt.append(lg)
        if len(nxt) == len(todo):
            break
        todo = nxt
    # lattice node arrivals
    by = {n_["tag"]: n_ for n_ in lat_nodes}
    base = {c: stage_delay(trunk["len_um"], trunk["n_seg"], c) for c in ("TT", "FF")}
    lat_node_arr = {}
    for n_ in sorted(lat_nodes, key=lambda x: x["depth"]):
        if n_["parent"] is None:
            lat_node_arr[n_["tag"]] = dict(base)
        else:
            L = md(by[n_["parent"]]["xy_um"], n_["xy_um"])
            pa = lat_node_arr[n_["parent"]]
            lat_node_arr[n_["tag"]] = {c: pa[c] + stage_delay(L, n_min(L), c) for c in ("TT", "FF")}
    for k, v in lat_node_arr.items():
        node_arr.setdefault(k, v)
    fc = {c: STAGE[c][0] / (STAGE[c][0] + STAGE[c][1] * REP_UM) for c in ("TT", "FF")}   # cell share of a full stage
    rows = []
    for a, b, edge in pairs:
        if a not in ent_tag or b not in ent_tag:
            continue
        ca, cb = chain(a), chain(b)
        sb = set(cb)
        common = next(t for t in ca if t in sb)
        ea, eb = node_arr[ent_tag[a]], node_arr[ent_tag[b]]
        cn = node_arr[common]
        row = dict(a=a, b=b, edge_um=edge, common=common,
                   common_level=("die_root" if common == "t" else "lattice" if common.startswith("t") else
                                 "region_root" if common.startswith("r") and ("_" not in common or common.endswith("_p")) else
                                 "region_node"))
        for c in ("TT", "FF"):
            nc = max(ea[c], eb[c]) - cn[c] + CORE_LAT[c]
            cell = fc[c] * nc
            net = nc - cell
            # setup (TT): launch late (cell +5 % +IR 5.1 %, net +3 %), capture early (cell -5 %, net -3 %)
            # hold (FF): launch early, capture late (+IR on the late capture clock, die_ci convention)
            pess = cell * (DERATE["cell_late"] + DERATE["ir_late"] + DERATE["cell_early"]) + net * (
                DERATE["net_late"] + DERATE["net_early"])
            row[c] = dict(noncommon_ps=r3(nc), ocv_pessimism_ps=r3(pess))
        rows.append(row)
    return rows


def summarise_pairs(rows):
    by = defaultdict(list)
    for r in rows:
        by[r["common_level"]].append(r)
    out = {}
    for k, v in sorted(by.items()):
        out[k] = dict(pairs=len(v), **{c: dict(noncommon_ps_max=max(x[c]["noncommon_ps"] for x in v),
                                              noncommon_ps_min=min(x[c]["noncommon_ps"] for x in v),
                                              pessimism_ps_max=max(x[c]["ocv_pessimism_ps"] for x in v))
                                       for c in ("TT", "FF")})
    return out


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(plan_path, dtp_path, out_dir, render=True, argv=None, die_balance=True):
    import schema as S
    import master_plan as MP
    import master_rulings as MR
    import infra_sites as IS
    P = S.Plan(S.load(plan_path), Path(plan_path))
    dtp = json.loads(Path(dtp_path).read_text())
    psha = sha(plan_path)
    if dtp.get("plan_sha256") != psha:
        raise SystemExit(f"die_tree_plan cut from {dtp.get('plan_sha256', '')[:12]}, plan {psha[:12]}")
    parts_die, cores_die = MR.die_geometry(P, MP.core_to_type, IS.rect_pts)
    inputs = dict(plan=str(plan_path), plan_sha256=psha, die_tree_plan=str(dtp_path), die_tree_plan_sha256=sha(dtp_path))
    return analyse(P, dtp, parts_die, cores_die, psha, out_dir, inputs, render=render, argv=argv, die_balance=die_balance)


def analyse(P, dtp, parts_die, cores_die, psha, out_dir, inputs, render=True, argv=None, die_balance=True):
    """regional distribution + trunk sites + predictions + related-pair estimate; writes region_plan.json,
    region_summary.json (+ renders) into out_dir; returns the record."""
    R = build(P, dtp, parts_die, cores_die, psha, die_balance=die_balance)
    legal = Legal(parts_die, cores_die)
    lat_nodes = dtp["lattice"]["nodes"]
    tr = trunk_sites(P, lat_nodes, legal)
    lat_arr = lattice_delay(lat_nodes, dtp["lattice"]["gate"], tr)
    full = {}
    for part, a in R["arrivals"].items():
        pass
    # die input -> entry -> + core latency
    reg_by_leaf = {}
    for lg in R["legs"]:
        pass
    ent_leaf = {}
    for r_ in R["regions"]:
        reg_by_leaf[r_["leaf"]] = r_
    # each entry's region leaf
    leaves = [n_ for n_ in lat_nodes if not any(m["parent"] == n_["tag"] for m in lat_nodes)]
    for e in R["entries"]:
        key = region_of(leaves, e["xy_um"])
        lf = next(n_["tag"] for n_ in leaves if tuple(n_["xy_um"]) == key)
        a = R["arrivals"][e["part"]]
        full[e["part"]] = {c: lat_arr[lf][c] + a[c] for c in ("TT", "FF")}
    die_path = {}
    for c in ("TT", "FF"):
        v = [x[c] for x in full.values()]
        lv = [x[c] for x in lat_arr.values()]
        die_path[c] = dict(input_to_leaf_ps=dict(min=r3(min(lv)), max=r3(max(lv))),
                           input_to_entry_ps=dict(min=r3(min(v)), max=r3(max(v)), window=r3(max(v) - min(v))),
                           core_latency_ps=CORE_LAT[c],
                           input_to_core_sinks_ps=dict(min=r3(min(v) + CORE_LAT[c]), max=r3(max(v) + CORE_LAT[c])))
    pairs = seam_pairs(P, parts_die)
    nc = nc_estimate(R, lat_nodes, lat_arr, tr, pairs)
    # gate
    nodes_bad = [n_ for n_ in R["nodes"] if n_["displacement_um"] is None or n_["host"] is None]
    reps_bad = [r for r in R["repeater_sites"] if r["binding"] != "partition_bay"]
    seg_bad = [lg for lg in R["legs"] if lg["max_seg_um"] > REP_UM + 1e-6]
    short = [lg for lg in R["legs"] if lg["tt_shortfall_ps"] > GAP_TOL_PS + 0.5 or lg.get("tt_excess_ps", 0) > 0.5]
    winTT = max(r["TT"]["window_ps"] for r in R["regions"])
    winFF = max(r["FF"]["window_ps"] for r in R["regions"])
    gate = dict(verdict="PASS" if not (nodes_bad or reps_bad or seg_bad or short or R["plan_errors"]) and
                tr["verdict"] == "PASS" else "FAIL",
                regions=len(R["regions"]), entries=len(R["entries"]), nodes=len(R["nodes"]), legs=len(R["legs"]),
                repeaters=len(R["repeater_sites"]), repeaters_bad=len(reps_bad), nodes_bad=len(nodes_bad),
                seg_over_450=len(seg_bad), tt_shortfall_legs=len(short),
                max_node_displacement_um=r3(max((n_["displacement_um"] or 0) for n_ in R["nodes"])),
                detour_um=dict(total=r3(sum(lg["detour_um"] for lg in R["legs"])),
                               max=r3(max(lg["detour_um"] for lg in R["legs"])),
                               legs=sum(1 for lg in R["legs"] if lg["detour_um"] > 0)),
                model_window_ps=dict(TT=winTT, FF=winFF), trunk=tr["verdict"], die_balance=die_balance,
                rule="12.7/12.8d/d1/12.2a1: regional tree per lattice leaf, nodes on 8.64 pushdown-island lattice in "
                     "partitions outside hard cores, legs <= 450 um segments at partition-bay sites, balance by "
                     "plan-computed repeater count + U detour (no measured input)")
    rec = dict(schema="opentallas.qc_mp_region.v1", argv=argv or sys.argv,
               inputs=dict(inputs, tool_sha256=sha(__file__)),
               gate=gate, die_path=die_path, trunk=tr, lattice_leaf_model=lat_arr,
               lattice_check=dict(note="model vs CLOCK-128-R4 measured (geometry SPEF, UNCHECKED): TT 3943.3-3956.2, "
                                       "FF 3257.9-3268.9 die input -> leaf node"),
               pairs=dict(seams=len(pairs), summary=summarise_pairs(nc), derate=DERATE,
                          note="non-common = modelled die clock below the last common tree node + the 12.3 core latency "
                               "on each side (blocks as ILMs); pessimism = flat OCV of die_ci_margins.json on that "
                               "non-common delay (cell share from the stage model). UNCHECKED plan estimate."),
               region_distribution=R, pair_rows=nc)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "region_plan.json").write_text(json.dumps(rec, indent=None) + "\n")
    summ = {k: rec[k] for k in ("argv", "inputs", "gate", "die_path", "trunk", "pairs")}
    summ["regions"] = R["regions"]
    (out / "region_summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    if render:
        draw(P, dtp, R, tr, parts_die, cores_die, out)
    return rec


def draw(P, dtp, R, tr, parts, cores, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    cols = plt.get_cmap("tab20")
    regs = sorted({n_["region"] for n_ in R["nodes"]})
    cidx = {r: cols(i % 20) for i, r in enumerate(regs)}
    par_reg = {}
    for n_ in R["nodes"]:
        par_reg[n_["tag"]] = n_["region"]
    lat = dtp["lattice"]["nodes"]
    by = {n_["tag"]: n_ for n_ in lat}

    def panel(ax, box=None):
        for p in parts:
            ax.add_patch(Rectangle((p[0], p[1]), p[2] - p[0], p[3] - p[1], fill=False, lw=0.3, ec="#999999"))
        for c in cores:
            ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fc="#dddddd", ec="none"))
        a, b = tr["die_input_um"], tr["lattice_root_um"]
        ax.plot([a[0], b[0]], [a[1], b[1]], "-", c="k", lw=2.0)
        for n_ in lat:
            if n_["parent"]:
                p = by[n_["parent"]]["xy_um"]
                q = n_["xy_um"]
                if n_.get("leg_route") == "y_first":
                    xs, ys = [p[0], p[0], q[0]], [p[1], q[1], q[1]]
                else:
                    xs, ys = [p[0], q[0], q[0]], [p[1], p[1], q[1]]
                ax.plot(xs, ys, "-", c="k", lw=1.6)
        for lg in R["legs"]:
            reg = "t" + lg["tag"].split("_")[0][1:]
            pl = lg["polyline"]
            ax.plot([p[0] for p in pl], [p[1] for p in pl], "-", c=cidx.get(reg, "b"), lw=0.9)
        nx = [n_["xy_um"][0] for n_ in R["nodes"]]
        ny = [n_["xy_um"][1] for n_ in R["nodes"]]
        ax.plot(nx, ny, "s", ms=2.5, c="#c00000", label="region tree node island")
        ex = [e["xy_um"][0] for e in R["entries"]]
        ey = [e["xy_um"][1] for e in R["entries"]]
        ax.plot(ex, ey, "o", ms=2.0, mfc="none", c="#0050c0", label="partition centre entry")
        lx = [n_["xy_um"][0] for n_ in lat if not any(m["parent"] == n_["tag"] for m in lat)]
        ly = [n_["xy_um"][1] for n_ in lat if not any(m["parent"] == n_["tag"] for m in lat)]
        ax.plot(lx, ly, "D", ms=4, c="k", label="lattice leaf (region root)")
        rx = [r["xy_um"][0] for r in R["repeater_sites"]]
        ry = [r["xy_um"][1] for r in R["repeater_sites"]]
        ax.plot(rx, ry, ".", ms=1.0, c="#008000", label="leg repeater site")
        bad = [r for r in R["repeater_sites"] if r["binding"] != "partition_bay"]
        if bad:
            ax.plot([r["xy_um"][0] for r in bad], [r["xy_um"][1] for r in bad], "x", ms=5, c="r", label="bad rep site")
        ax.set_aspect("equal")
        if box:
            ax.set_xlim(box[0], box[2])
            ax.set_ylim(box[1], box[3])
        else:
            ax.set_xlim(0, P.W)
            ax.set_ylim(0, P.H)
    fig, ax = plt.subplots(figsize=(16, 13.5))
    panel(ax)
    ax.legend(loc="upper right", fontsize=7)
    g = R
    ax.set_title(f"{P.name} regional clock distribution: {len(R['nodes'])} nodes, {len(R['legs'])} legs, "
                 f"{len(R['repeater_sites'])} reps, die target TT {R['die_target_tt_ps']:.0f} ps leaf->entry")
    fig.savefig(out / "region_plan.png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    # zoom: one interior region (around the leaf closest to the die centre-left)
    leaves = [n_ for n_ in lat if not any(m["parent"] == n_["tag"] for m in lat)]
    lf = min(leaves, key=lambda n_: md(n_["xy_um"], (P.W * 0.4, P.H * 0.35)))
    cx, cy = lf["xy_um"]
    fig, ax = plt.subplots(figsize=(14, 10))
    panel(ax, (cx - 4200, cy - 3300, cx + 4200, cy + 3300))
    ax.set_title(f"zoom region {lf['tag']} (leaf {cx:.0f},{cy:.0f})")
    fig.savefig(out / "region_zoom.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--tree-plan", required=True, help="die_tree_plan.json with lattice.nodes (master-plan --tree-lattice c..)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--region-only", action="store_true",
                    help="OPTION A preparation: balance each region on its own, no die-wide padding (valid only with "
                         "landed/forwarded hops on every seam between regions); not a plan to build by default")
    a = ap.parse_args(argv)
    rec = run(a.plan, a.tree_plan, a.out, render=not a.no_render, argv=[sys.argv[0]] + list(argv or sys.argv[1:]),
              die_balance=not a.region_only)
    print(json.dumps(dict(gate=rec["gate"], die_path=rec["die_path"], trunk=dict(rec["trunk"], sites=len(rec["trunk"]["sites"])),
                          pairs=rec["pairs"]["summary"]), indent=1))
    return 0 if rec["gate"]["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
