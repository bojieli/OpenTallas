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


def plan(g, max_sinks=200, max_extent=100.0, hop=92.0, cell='BUFx24_ASAP7_75t_R', s0_pitch=2.4):
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
    # hub = the legal point with the smallest longest leg (L1 1-centre of the drivers on a 20-um grid; ties: nearest the pad);
    # the pad reaches it through ONE common feeder chain, which no pair of sinks sees as skew.
    dx0, dx1 = min(d[0] for d in drv), max(d[0] for d in drv)
    dy0, dy1 = min(d[1] for d in drv), max(d[1] for d in drv)
    best = None
    gx = dx0
    while gx <= dx1 + 1e-6:
        gy = dy0
        while gy <= dy1 + 1e-6:
            if rows.ok(gx, gy):
                c = (round(max(abs(gx - d[0]) + abs(gy - d[1]) for d in drv), 3), abs(gx - pad[0]) + abs(gy - pad[1]))
                if best is None or c < best[0]:
                    best = (c, (gx, gy))
            gy += 20.0
        gx += 20.0
    far_pad = max(abs(pad[0] - d[0]) + abs(pad[1] - d[1]) for d in drv)
    hub = pad if best is None or far_pad - best[0][0] < hop else best[1]
    feeder = []
    fd = abs(hub[0] - pad[0]) + abs(hub[1] - pad[1])
    if fd > 1e-6:
        nf = math.ceil(fd / hop)
        cands = []
        for P in ([pad, (hub[0], pad[1]), hub], [pad, (pad[0], hub[1]), hub]):
            st = [_along(P, i * fd / nf) for i in range(nf)]
            cands.append((sum(not rows.ok(*p) for p in st), st))
        feeder = [p if rows.ok(*p) else rows.nearest(*p) for p in min(cands, key=lambda c: c[0])[1]]
    order = sorted(range(K), key=lambda k: (drv[k][0], drv[k][1]))
    ncol = 16
    start = {}
    for i, k in enumerate(order):
        r, c = divmod(i, ncol)
        start[k] = rows.nearest(hub[0] + (c - (ncol - 1) / 2) * s0_pitch, hub[1] - r * 0.54, toward=hub, step=1.0)
    dmax = max(abs(start[k][0] - drv[k][0]) + abs(start[k][1] - drv[k][1]) for k in range(K))
    nh = max(1, math.ceil((dmax + 0.2 * hop) / hop))
    R = nh * hop
    entries = []
    moved = 0
    short = 0
    step = R / nh
    for k in range(K):
        best = None
        for P in leg_shapes(start[k], drv[k], R, bounds):
            st = [_along(P, i * step) for i in range(nh)]
            nb = sum(not rows.ok(*p) for p in st)
            # a hop that spans both corners of a narrow U is shorter as the router sees it (L1) than as planned: such a
            # shape is not an equal leg, so it only wins when nothing better exists
            pts = st + [drv[k]]
            ns = sum(abs(abs(a[0] - b[0]) + abs(a[1] - b[1]) - step) > 1.0 for a, b in zip(pts, pts[1:]))
            if best is None or nb + ns < best[0] + best[1]:
                best = (nb, ns, st)
            if nb + ns == 0:
                break
        if best is None:
            raise ValueError(f'rck_star: no leg shape for entry {k}')
        nb, ns, st = best
        moved += nb
        short += ns
        st = [p if rows.ok(*p) else rows.nearest(*p) for p in st]
        rect, pts = T[k]
        entries.append(dict(name=f'rck_r{k}', xy=drv[k], stations=st, region=rect, n=len(pts), macros=[]))
    owner = {}
    for k, (_rect, pts) in enumerate(T):
        for p in pts:
            owner[(p[2], p[3])] = k
    for s in mac:
        k = min(range(K), key=lambda k: abs(drv[k][0] - s[0]) + abs(drv[k][1] - s[1]))
        owner[(s[2], s[3])] = k
        entries[k]['macros'].append((s[4], s[3]))
    assign = [owner[(s[2], s[3])] for s in g['sinks']]
    ns = sorted(e['n'] for e in entries)
    rep = dict(port=g['port'][0], hub=hub, pad=pad, feeder=len(feeder), entries=K, hops=nh, hop_um=hop, leg_um=R, stations=K * nh, cell=cell,
               sinks=len(std), macro_pins=len(mac), sinks_min=ns[0], sinks_median=ns[K // 2], sinks_max=ns[-1],
               nudged_stations=moved, short_hops=short, max_sinks=max_sinks, max_extent_um=max_extent)
    rep['feeder_um'] = feeder
    rep['assign'] = assign
    return entries, rep


def _tl(v):
    if isinstance(v, (list, tuple)):
        return '{' + ' '.join(_tl(x) for x in v) + '}'
    return ('%.3f' % v) if isinstance(v, float) else str(v)


def emit(entries, rep, out):
    """rck_star.tcl data: feeder stations, one leg per entry {name {stations} {driver xy}}, and the entry index of every
    SINK line of GEOM in file order (a macro pin goes to the entry whose driver is nearest)."""
    with open(out, 'w') as f:
        f.write('# GENERATED by rck_star.py (matched-leg star trunk): feeder, legs {name stations driver_xy}, entry index per sink\n')
        f.write('set ::rks_cell ' + rep['cell'] + '\n')
        f.write('set ::rks_feeder ' + _tl([[float(a), float(b)] for a, b in rep['feeder_um']]) + '\n')
        f.write('set ::rks_legs {\n')
        for e in entries:
            f.write('  ' + _tl([e['name'], [[float(a), float(b)] for a, b in e['stations']], [float(e['xy'][0]), float(e['xy'][1])]]) + '\n')
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
    ap.add_argument('--report')
    a = ap.parse_args(argv)
    g = load(a.geom)
    entries, rep = plan(g, a.max_sinks, a.max_extent, a.hop, a.cell)
    emit(entries, rep, a.out)
    if a.report:
        json.dump({k: v for k, v in rep.items() if k != 'assign'}, open(a.report, 'w'), indent=1, sort_keys=True)
    print('OT_RCK_STAR plan: port %s feeder %d stations, hub (%.1f, %.1f), %d entries (%d..%d sinks, median %d), %d hops x %g um = leg %g um, '
          '%d stations (%d nudged, %d short hops), %d macro pins' % (rep['port'], rep['feeder'], rep['hub'][0], rep['hub'][1], rep['entries'], rep['sinks_min'],
                                                       rep['sinks_max'], rep['sinks_median'], rep['hops'], rep['hop_um'],
                                                       rep['leg_um'], rep['stations'], rep['nudged_stations'], rep['short_hops'], rep['macro_pins']))


if __name__ == '__main__':
    sys.exit(main())
