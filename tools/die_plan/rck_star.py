#!/usr/bin/env python3
"""Matched-leg star trunk of a pad clock, planned on the PLACED sinks (PRE_CTS; FABLE-FIX-S81-SERDES 2026-11-18).

Why (serdes__t13 H18 placed db, rck trees only, placement RC TT, epyc9 fable-fix-s81-serdes3/E): one TritonCTS tree over the
26.3k io_pma_rck sinks is 34-40 levels and 1.66-2.06 ns deep (span 405 ps before 1,012 balance pads); 16 / 32 k-means roots
under a TritonCTS top tree are no better (span 726 / 606 ps, root means 440 ps apart: TritonCTS does not equalise sub-roots and
buffers the top tree every ~45 um).  A trunk that is equal BY CONSTRUCTION measured span 193 ps (p1..p99 130) with no balance
step at all, and its local trees are 2-4 levels.

Form: the sinks are cut into compact regions (k-d median cuts until a region holds <= max_sinks sinks in <= max_extent um);
every region gets one entry driver at its sink centroid, fed from the hub (the legal point with the smallest longest leg; the
pad reaches it through one common feeder chain) by its OWN leg: the same number of stations and the same leg length for every entry (a shorter distance is made up by a detour whose
corners are stations, so the routed hop length is the planned one).  Equal stages x equal wire = equal delay to first order,
and an RC model error is common to every leg.  TritonCTS then builds one 2-4 level tree per entry.

Output: the data rck_star.tcl builds the trunk from (feeder stations, one leg per entry, the entry of every sink); macro clock
pins go to the entry whose driver is nearest.  Same ports, flops, logic, constraints and cycles.

usage: rck_star.py GEOM.tsv OUT.tcl [--max-sinks N] [--max-extent UM] [--hop UM] [--cell C] [--report OUT.json]
GEOM.tsv (um): PORT name x y | ROW x0 y0 x1 y1 | SINK inst pin master is_block x y
"""
import argparse
import bisect
import json
import math
import sys


def load(path):
    g = dict(rows=[], sinks=[], port=None)
    for line in open(path):
        f = line.rstrip('\n').split('\t')
        if f[0] == 'PORT':
            g['port'] = (f[1], float(f[2]), float(f[3]))
        elif f[0] == 'ROW':
            g['rows'].append(tuple(float(v) for v in f[1:5]))
        elif f[0] == 'SINK':
            g['sinks'].append((float(f[5]), float(f[6]), f[1], f[2], f[3], f[4] == '1'))
    if g['port'] is None or not g['rows'] or not g['sinks']:
        raise ValueError('rck_star: GEOM needs PORT, ROW and SINK lines')
    return g


class Rows:
    """Legal buffer points: inside a placement row, `margin` um off its ends."""
    def __init__(self, rows, margin=3.0):
        self.m = margin
        by = {}
        for x0, y0, x1, y1 in rows:
            by.setdefault(round(y0, 4), []).append((x0, x1, y1))
        self.ys = sorted(by)
        self.by = by

    def _band(self, y):
        i = bisect.bisect_right(self.ys, y + 1e-6) - 1
        return self.by[self.ys[i]] if i >= 0 else []

    def ok(self, x, y):
        return any(x0 + self.m <= x <= x1 - self.m and y <= y1 + 1e-6 for x0, x1, y1 in self._band(y))

    def nearest(self, x, y, toward=None, step=4.0, rmax=600.0):
        if self.ok(x, y):
            return (x, y)
        best = None
        r = step
        while r <= rmax and best is None:
            n = max(1, int(r / step))
            cands = []
            for i in range(-n, n + 1):
                d = i * step
                cands += [(x + d, y + (r - abs(d))), (x + d, y - (r - abs(d)))]
            cands = [c for c in cands if self.ok(*c)]
            if cands:
                key = (lambda c: abs(c[0] - toward[0]) + abs(c[1] - toward[1])) if toward else (lambda c: abs(c[0] - x))
                best = min(cands, key=key)
            r += step
        if best is None:
            raise ValueError(f'rck_star: no legal row point within {rmax:g} um of ({x:.1f}, {y:.1f})')
        return best


def tiles(std, max_sinks, max_extent, bounds, min_sinks=24):
    """k-d cuts: a region with more than max_sinks sinks is cut into near-equal counts (parts = ceil(n / max_sinks), so the
    regions end close to max_sinks, not anywhere in max/2..max); a wider-than-max_extent region is cut at its median while
    both halves keep min_sinks.  A cut always sits between two different coordinates (a flop column shares one x)."""
    out = []

    def split(rect, pts):
        n = len(pts)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ex, ey = max(xs) - min(xs), max(ys) - min(ys)
        parts = math.ceil(n / max_sinks)
        if parts > 1 or (max(ex, ey) > max_extent and n >= 2 * min_sinks):
            want = n * (parts // 2) // parts if parts > 1 else n // 2
            lo = 1 if parts > 1 else min_sinks
            for ax in ((0, 1) if ex >= ey else (1, 0)):
                s = sorted(pts, key=lambda p: (p[ax], p[1 - ax], p[2], p[3]))
                cand = [i for i in range(lo, n - lo + 1) if s[i - 1][ax] < s[i][ax]]
                if not cand:
                    continue
                i = min(cand, key=lambda i: abs(i - want))
                cut = round((s[i - 1][ax] + s[i][ax]) / 2, 4)
                if not (s[i - 1][ax] < cut < s[i][ax]):
                    continue
                r1, r2 = list(rect), list(rect)
                r1[2 + ax] = cut
                r2[ax] = cut
                split(r1, s[:i])
                split(r2, s[i:])
                return
        out.append((rect, pts))

    split(list(bounds), std)
    return out


def _plen(P):
    return sum(abs(P[i + 1][0] - P[i][0]) + abs(P[i + 1][1] - P[i][1]) for i in range(len(P) - 1))


def _along(P, s):
    for i in range(len(P) - 1):
        d = abs(P[i + 1][0] - P[i][0]) + abs(P[i + 1][1] - P[i][1])
        if s <= d + 1e-9:
            t = 0.0 if d == 0 else s / d
            return (P[i][0] + (P[i + 1][0] - P[i][0]) * t, P[i][1] + (P[i + 1][1] - P[i][1]) * t)
        s -= d
    return P[-1]


def leg_shapes(a, d, R, bounds):
    """Rectilinear polylines of length exactly R from a to d (R >= Manhattan distance): the detour is a U whose depth
    takes the surplus; tried downwards, upwards, left and right, and behind several side-step columns."""
    (x0, y0), (xd, yd) = a, d
    e = R - (abs(x0 - xd) + abs(y0 - yd))
    bx0, by0, bx1, by1 = bounds
    out = []
    for lo in (min(y0, yd) - e / 2, max(y0, yd) + e / 2):
        if by0 < lo < by1:
            out.append([(x0, y0), (x0, lo), (xd, lo), (xd, yd)])
    for xm in (min(x0, xd) - e / 2, max(x0, xd) + e / 2):
        if bx0 < xm < bx1:
            out.append([(x0, y0), (xm, y0), (xm, yd), (xd, yd)])
    # side-step first: the U bottom is then |x0 + side - xd| or the dip, whichever the surplus allows; both signs, several widths
    for side in (110.0, -110.0, 200.0, -200.0, 320.0, -320.0, 480.0, -480.0, 700.0, -700.0):
        xa = x0 + side
        if bx0 < xa < bx1:
            e2 = R - (abs(x0 - xa) + abs(xa - xd) + abs(y0 - yd))
            if e2 >= 0:
                for lo in (min(y0, yd) - e2 / 2, max(y0, yd) + e2 / 2):
                    if by0 < lo < by1:
                        out.append([(x0, y0), (xa, y0), (xa, lo), (xd, lo), (xd, yd)])
        ya = y0 + side
        if by0 < ya < by1:
            e2 = R - (abs(y0 - ya) + abs(ya - yd) + abs(x0 - xd))
            if e2 >= 0:
                for xm in (min(x0, xd) - e2 / 2, max(x0, xd) + e2 / 2):
                    if bx0 < xm < bx1:
                        out.append([(x0, y0), (x0, ya), (xm, ya), (xm, yd), (xd, yd)])
    return [P for P in out if abs(_plen(P) - R) < 1e-3]


def _l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _centre(pts, rows):
    """legal point nearest the L1 1-centre of pts (mid-range in the rotated u = x + y, v = x - y frame)"""
    us = [p[0] + p[1] for p in pts]
    vs = [p[0] - p[1] for p in pts]
    u = (min(us) + max(us)) / 2
    v = (min(vs) + max(vs)) / 2
    return rows.nearest((u + v) / 2, (u - v) / 2)


def _starts(centre, ks, dest, rows, s0_pitch, ncol=16):
    """first-station sites of the legs that leave one driver: a compact grid next to it, ordered by destination"""
    order = sorted(ks, key=lambda k: (dest[k][0], dest[k][1]))
    out = {}
    for i, k in enumerate(order):
        r, c = divmod(i, ncol)
        out[k] = rows.nearest(centre[0] + (c - (ncol - 1) / 2) * s0_pitch, centre[1] - r * 0.54, toward=centre, step=1.0)
    return out


def _walk(a, d, nh, step, rows, res=0.5):
    """stations a = p0 .. p(nh-1) with every hop p(i) -> p(i+1) and p(nh-1) -> d exactly `step` um in L1 (within res), on
    legal row points where one exists: the fallback when no U shape gives equal hops (a short leg of a long common R, where a
    narrow U would put two stations one short hop apart).  Each station is picked on the L1 circle of radius step around the
    previous one, heading for d while the hops left can still end on d; the surplus is spent near the entry, not the hub."""
    pts = [a]
    q = a
    n = int(round(2 * step / res))
    for i in range(1, nh):
        rem = nh - i
        best = None
        for j in range(n + 1):
            t = -step + j * res
            for p in ((q[0] + t, q[1] + (step - abs(t))), (q[0] + t, q[1] - (step - abs(t)))):
                L = _l1(p, d)
                err = abs(L - step) if rem == 1 else max(0.0, L - rem * step)
                key = (not rows.ok(*p), round(err, 3), L)
                if best is None or key < best[0]:
                    best = (key, p)
        q = best[1]
        pts.append(q)
    return pts


def _legs(start, dest, hop, rows, bounds, nh=None, Rk=None):
    """one leg per key from start[k] to dest[k], ALL with the same stage count nh; length R = nh * hop for every leg (detours
    make up a shorter distance), or Rk[k] per leg when given (stations then sit Rk[k] / nh apart); nh may be a per-key dict
    -> ({k: stations}, nh, R, nudged, short)"""
    if nh is None:
        dmax = max(_l1(start[k], dest[k]) for k in start)
        nh = max(1, math.ceil((dmax + 0.2 * hop) / hop))
    nk = nh if isinstance(nh, dict) else {k: nh for k in start}
    R = max(nk.values()) * hop
    out, moved, short = {}, 0, 0
    for k in start:
        n = nk[k]
        Rl = Rk[k] if Rk else n * hop
        step = Rl / n
        best = None
        for P in leg_shapes(start[k], dest[k], Rl, bounds):
            st = [_along(P, i * step) for i in range(n)]
            nb = sum(not rows.ok(*p) for p in st)
            # a hop that spans both corners of a narrow U is shorter as the router sees it (L1) than as planned: such a
            # shape is not an equal leg, so it only wins when nothing better exists
            pts = st + [dest[k]]
            ns = sum(abs(_l1(a, b) - step) > 1.0 for a, b in zip(pts, pts[1:]))
            if best is None or nb + ns < best[0] + best[1]:
                best = (nb, ns, st)
            if nb + ns == 0:
                break
        if best is None or best[0] + best[1]:
            st = _walk(start[k], dest[k], n, step, rows)
            pts = st + [dest[k]]
            nb = sum(not rows.ok(*p) for p in st)
            ns = sum(abs(_l1(a, b) - step) > 1.0 for a, b in zip(pts, pts[1:]))
            if best is None or nb + ns < best[0] + best[1]:
                best = (nb, ns, st)
        nb, ns, st = best
        moved += nb
        short += ns
        out[k] = [p if rows.ok(*p) else rows.nearest(*p) for p in st]
    return out, nh, R, moved, short


def leg_density(paths, win=100.0):
    """max number of distinct legs whose wire (Manhattan, x first then y between consecutive points) crosses one win x win
    um window, and that window's lower-left corner.  The routing pinch of a one-hub star: ~200 legs leave one hub."""
    cells = {}
    for li, P in enumerate(paths):
        seen = set()
        for a, b in zip(P, P[1:]):
            for (x0, y0), (x1, y1) in (((a[0], a[1]), (b[0], a[1])), ((b[0], a[1]), (b[0], b[1]))):
                n = max(1, int(_l1((x0, y0), (x1, y1)) / (win / 4)))
                for i in range(n + 1):
                    x = x0 + (x1 - x0) * i / n
                    y = y0 + (y1 - y0) * i / n
                    seen.add((math.floor(x / win), math.floor(y / win)))
        for c in seen:
            cells[c] = cells.get(c, 0) + 1
    if not cells:
        return 0, None
    c, n = max(cells.items(), key=lambda kv: (kv[1], kv[0]))
    return n, (c[0] * win, c[1] * win)


def _ksplit(pts, parts):
    """exactly `parts` compact groups of near-equal count (k-d median cuts across the wider extent) -> [[key, ...]]"""
    if parts <= 1 or len(pts) <= 1:
        return [[p[2] for p in pts]]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax = 0 if max(xs) - min(xs) >= max(ys) - min(ys) else 1
    s = sorted(pts, key=lambda p: (p[ax], p[1 - ax], p[2]))
    p1 = parts // 2
    i = max(1, min(len(s) - 1, round(len(s) * p1 / parts)))
    return _ksplit(s[:i], p1) + _ksplit(s[i:], parts - p1)


def plan(g, max_sinks=200, max_extent=100.0, hop=92.0, cell='BUFx24_ASAP7_75t_R', s0_pitch=2.4, sub_hubs=14):
    """sub_hubs 0 / 1: one-level star (every entry leg leaves the hub).  sub_hubs >= 2 (two-level matched tree, FABLE-FIX-S81-SERDES
    11-19, after the one-hub star failed detail route on serdes__t13 H20/H21 with ~200 legs leaving one hub): the entry drivers are
    cut into sub_hubs compact groups of near-equal count; each group gets a sub-hub driver at its L1 centre, fed from the hub by
    its own level-1 leg (all level-1 legs equal); each entry is fed from its sub-hub by its own level-2 leg (all level-2 legs
    equal across ALL groups).  Every entry therefore sees feeder + n1 + 1 + n2 + 1 equal stages, no hop exceeds hop_um, and no
    driver has more than ceil(entries / sub_hubs) legs leaving it."""
    rows = Rows(g['rows'])
    std = [s for s in g['sinks'] if not s[5]]
    mac = [s for s in g['sinks'] if s[5]]
    if not std:
        raise ValueError('rck_star: no std-cell sinks on the port net')
    bx0 = min(r[0] for r in g['rows'])
    by0 = min(r[1] for r in g['rows'])
    bx1 = max(r[2] for r in g['rows'])
    by1 = max(r[3] for r in g['rows'])
    bounds = (bx0, by0, bx1, by1)
    cx = sum(s[0] for s in std) / len(std)
    cy = sum(s[1] for s in std) / len(std)
    _, px, py = g['port']
    pad = rows.nearest(min(max(px, bx0 + 8), bx1 - 8), min(max(py, by0 + 2), by1 - 2), toward=(cx, cy))
    T = tiles(std, max_sinks, max_extent, (bx0 - 10, by0 - 10, bx1 + 10, by1 + 10))
    drv = []
    for rect, pts in T:
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
        drv.append(rows.nearest(x, y))
    K = len(T)
    G = int(sub_hubs) if sub_hubs and int(sub_hubs) >= 2 and K > int(sub_hubs) else 0
    groups, subs = [], []
    if G:
        groups = _ksplit([(d[0], d[1], k) for k, d in enumerate(drv)], G)
        subs = [_centre([drv[k] for k in ks], rows) for ks in groups]
    roots = subs if G else drv
    # hub = the legal point with the smallest longest leg to the roots it feeds (L1 1-centre on a 20-um grid; ties: nearest
    # the pad); the pad reaches it through ONE common feeder chain, which no pair of sinks sees as skew.
    dx0, dx1 = min(d[0] for d in roots), max(d[0] for d in roots)
    dy0, dy1 = min(d[1] for d in roots), max(d[1] for d in roots)
    best = None
    gx = dx0
    while gx <= dx1 + 1e-6:
        gy = dy0
        while gy <= dy1 + 1e-6:
            if rows.ok(gx, gy):
                c = (round(max(_l1((gx, gy), d) for d in roots), 3), _l1((gx, gy), pad))
                if best is None or c < best[0]:
                    best = (c, (gx, gy))
            gy += 20.0
        gx += 20.0
    if best is None:
        best = ((0.0, 0.0), rows.nearest(*_centre(roots, rows)))
    far_pad = max(_l1(pad, d) for d in roots)
    hub = pad if far_pad - best[0][0] < hop else best[1]
    feeder = []
    fd = _l1(hub, pad)
    if fd > 1e-6:
        nf = math.ceil(fd / hop)
        cands = []
        for P in ([pad, (hub[0], pad[1]), hub], [pad, (pad[0], hub[1]), hub]):
            st = [_along(P, i * fd / nf) for i in range(nf)]
            cands.append((sum(not rows.ok(*p) for p in st), st))
        feeder = [p if rows.ok(*p) else rows.nearest(*p) for p in min(cands, key=lambda c: c[0])[1]]
    moved = short = 0
    sub_rows = []
    parent = [-1] * K
    n1 = 0
    R1 = 0.0
    R2k = None
    if G:
        # equal hub -> entry path: each group's entry legs are only as long and as deep as its own spread needs (R2_j, n2_j),
        # and its sub-hub leg takes the rest (R1_j = path - R2_j, n1_j = N - n2_j).  The length and stage surplus of a compact
        # group is spent on ONE sub-hub leg, not on its ~14 entry legs, so every entry sees the same N stages and the same
        # wire length while no compact group bunches stations.
        gidx = list(range(len(groups)))
        s1start = _starts(hub, gidx, subs, rows, s0_pitch)
        start = {}
        for j, ks in enumerate(groups):
            start.update(_starts(subs[j], ks, drv, rows, s0_pitch))
        r2 = [max(_l1(start[k], drv[k]) for k in ks) for ks in groups]
        n2 = [max(2, math.ceil((v + 0.2 * hop) / hop)) for v in r2]      # >= 2: one hop cannot take a detour
        R2 = [max(v + 0.2 * hop, 0.25 * n2[j] * hop) for j, v in enumerate(r2)]
        path = max(_l1(s1start[j], subs[j]) + 0.2 * hop + R2[j] for j in gidx)
        R1k = {j: path - R2[j] for j in gidx}
        N = max(max(2, math.ceil(R1k[j] / hop - 1e-9)) + n2[j] for j in gidx)
        n1k = {j: N - n2[j] for j in gidx}
        s1, _n, _R, m, s = _legs(s1start, {j: subs[j] for j in gidx}, hop, rows, bounds, nh=n1k, Rk=R1k)
        n1 = max(n1k.values())
        R1 = max(R1k.values())
        moved += m
        short += s
        for j in gidx:
            sub_rows.append(dict(name=f'rck_h{j}', xy=subs[j], stations=s1[j], n=len(groups[j]), leg_um=R1k[j]))
            for k in groups[j]:
                parent[k] = j
        R2k = {k: R2[j] for j, ks in enumerate(groups) for k in ks}
        s2, _n, R, m, s = _legs(start, {k: drv[k] for k in range(K)}, hop, rows, bounds,
                                nh={k: n2[j] for j, ks in enumerate(groups) for k in ks}, Rk=R2k)
        R = max(R2)
        nh = max(n2)
    else:
        start = _starts(hub, range(K), drv, rows, s0_pitch)
        s2, nh, R, m, s = _legs(start, {k: drv[k] for k in range(K)}, hop, rows, bounds)
    moved += m
    short += s
    entries = []
    for k in range(K):
        rect, pts = T[k]
        entries.append(dict(name=f'rck_r{k}', xy=drv[k], stations=s2[k], region=rect, n=len(pts), macros=[], parent=parent[k],
                            leg_um=R2k[k] if R2k else R))
    owner = {}
    for k, (_rect, pts) in enumerate(T):
        for p in pts:
            owner[(p[2], p[3])] = k
    for s_ in mac:
        k = min(range(K), key=lambda k: _l1(drv[k], s_))
        owner[(s_[2], s_[3])] = k
        entries[k]['macros'].append((s_[4], s_[3]))
    assign = [owner[(s_[2], s_[3])] for s_ in g['sinks']]
    paths = [[hub] + h['stations'] + [h['xy']] for h in sub_rows]
    paths += [[(subs[e['parent']] if e['parent'] >= 0 else hub)] + e['stations'] + [e['xy']] for e in entries]
    dens, dens_at = leg_density(paths)
    fan = [sum(1 for e in entries if e['parent'] == j) for j in range(len(sub_rows))] if G else [K]
    ns = sorted(e['n'] for e in entries)
    rep = dict(port=g['port'][0], hub=hub, pad=pad, feeder=len(feeder), entries=K, hops=nh, hop_um=hop, leg_um=R, stations=sum(len(e['stations']) for e in entries) + sum(len(h['stations']) for h in sub_rows),
               cell=cell, sinks=len(std), macro_pins=len(mac), sinks_min=ns[0], sinks_median=ns[K // 2], sinks_max=ns[-1],
               nudged_stations=moved, short_hops=short, max_sinks=max_sinks, max_extent_um=max_extent,
               sub_hubs=len(sub_rows), hops1=n1, leg1_um=R1, path_um=path if G else R, fanout_max=max([len(sub_rows)] + fan) if G else K,
               legs_per_100um_max=dens, legs_per_100um_at=dens_at,
               stages_per_entry=len(feeder) + (N + 2 if G else nh + 1))
    rep['feeder_um'] = feeder
    rep['subs'] = sub_rows
    rep['assign'] = assign
    return entries, rep


def _tl(v):
    if isinstance(v, (list, tuple)):
        return '{' + ' '.join(_tl(x) for x in v) + '}'
    return ('%.3f' % v) if isinstance(v, float) else str(v)


def emit(entries, rep, out):
    """rck_star.tcl data: feeder stations, sub-hub legs {name stations xy} (empty for a one-level star), one leg per entry
    {name stations driver_xy parent_sub (-1 = hub)}, and the entry index of every SINK line of GEOM in file order (a macro pin
    goes to the entry whose driver is nearest)."""
    with open(out, 'w') as f:
        f.write('# GENERATED by rck_star.py (matched-leg trunk): feeder, sub-hub legs, entry legs {name stations driver_xy parent}, entry per sink\n')
        f.write('set ::rks_cell ' + rep['cell'] + '\n')
        f.write('set ::rks_feeder ' + _tl([[float(a), float(b)] for a, b in rep['feeder_um']]) + '\n')
        f.write('set ::rks_subs {\n')
        for h in rep.get('subs', []):
            f.write('  ' + _tl([h['name'], [[float(a), float(b)] for a, b in h['stations']], [float(h['xy'][0]), float(h['xy'][1])]]) + '\n')
        f.write('}\n')
        f.write('set ::rks_legs {\n')
        for e in entries:
            f.write('  ' + _tl([e['name'], [[float(a), float(b)] for a, b in e['stations']], [float(e['xy'][0]), float(e['xy'][1])],
                                e.get('parent', -1)]) + '\n')
        f.write('}\n')
        f.write('set ::rks_assign {' + ' '.join(str(i) for i in rep['assign']) + '}\n')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('geom')
    ap.add_argument('out')
    ap.add_argument('--max-sinks', type=int, default=200)
    ap.add_argument('--max-extent', type=float, default=100.0)
    ap.add_argument('--hop', type=float, default=92.0)
    ap.add_argument('--cell', default='BUFx24_ASAP7_75t_R')
    ap.add_argument('--sub-hubs', type=int, default=14)
    ap.add_argument('--report')
    a = ap.parse_args(argv)
    g = load(a.geom)
    entries, rep = plan(g, a.max_sinks, a.max_extent, a.hop, a.cell, sub_hubs=a.sub_hubs)
    emit(entries, rep, a.out)
    if a.report:
        json.dump({k: v for k, v in rep.items() if k not in ('assign',)}, open(a.report, 'w'), indent=1, sort_keys=True)
    print('OT_RCK_STAR plan: port %s feeder %d stations, hub (%.1f, %.1f), %d sub-hubs (%d hops x %g um = leg %g um), %d entries '
          '(%d..%d sinks, median %d), %d hops x %g um = leg %g um, %d stations (%d nudged, %d short hops), %d stages per entry, '
          'max legs leaving one driver %d, max legs per 100 um window %d at %s, %d macro pins'
          % (rep['port'], rep['feeder'], rep['hub'][0], rep['hub'][1], rep['sub_hubs'], rep['hops1'], rep['hop_um'], rep['leg1_um'],
             rep['entries'], rep['sinks_min'], rep['sinks_max'], rep['sinks_median'], rep['hops'], rep['hop_um'], rep['leg_um'],
             rep['stations'], rep['nudged_stations'], rep['short_hops'], rep['stages_per_entry'], rep['fanout_max'],
             rep['legs_per_100um_max'], rep['legs_per_100um_at'], rep['macro_pins']))


if __name__ == '__main__':
    sys.exit(main())
