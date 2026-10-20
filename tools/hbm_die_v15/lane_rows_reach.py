#!/usr/bin/env python3
"""HBM-GENREACH 10-20: reach-bounded lane-row placement for die_case_v16 (SAFE-DESIGN item 2, release rule 2).

GEN2c case_a census (lanes/L2H-GEN2D-FP2.md, fp/fp_hops_classified.json): 39,871 lane buses planned at ~380 um were placed
up to 4.8 mm apart, because die_case_v16 put 19,113 of 41,352 lane rows at the 'row nearest free area' (an unbounded spiral)
and slid others up to 150 um.  This placer keeps every lane hop inside the reach R (default the measured 405 um):

  * a row (T lane tiles abutted across the travel direction, placed as one unit, as before) may sit only where, for
    EVERY tile and every contract neighbour of that tile (data and forwarded-clock edges; resets excluded: the H.RST
    forest owns them):
      - neighbour already placed  -> pin span (port pin centroids from the REAL LEFs; SYNTH blocks: distance to the
        block rectangle, a lower bound) <= R - margin;
      - neighbour = an unplaced lane tile -> span to that tile's PLANNED site <= R - margin (look-ahead: the neighbour can
        then still take its own planned site, so a chain never paints itself into a corner);
  * candidates: exact site, slides along / across the travel axis (<= slide_um), then a windowed search of every free
    lower-left cell inside the L1 reach diamond of the site -- the feasible candidate nearest the site wins;
  * if no feasible candidate exists the row is placed by the RELAXED rule (placed neighbours only); if even that fails it
    is a REACH FAILURE naming the bus (row id, tiles, the offending neighbour + span).  It is never relocated far: in
    'fail' mode GEN stops after the lane-row step with GEN_REACH_FAIL and out/reach_fail.json; 'diag' mode places the
    row at the least-violating free candidate inside the window and labels the case.
  * planned-hop audit (relay layer did not insert enough stations): any row neighbour pair whose PLANNED sites are
    already > R + tol apart is listed as 'not_inserted' (relay layer / station planner fix, not a GEN placement fix).
All arithmetic uses windowed integral images of the die occupancy grid (the old per-row full-die cumsum was the 2.7 h
GEN wall time).
"""
import collections
import math
import re

import numpy as np

RST = re.compile(r'(^|_)(rst|reset|por)(_|n|$)|rst_n|_rstn|^rs$|^en$')


def _port_centroids(lef_xy_fn, lef_path):
    """pin name -> xy (LEF frame) -> {port base: (cx, cy)}"""
    xy = lef_xy_fn(lef_path)
    acc = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for p, (x, y) in xy.items():
        b = p.split('[')[0]
        a = acc[b]; a[0] += x; a[1] += y; a[2] += 1
    return {b: (a[0] / a[2], a[1] / a[2]) for b, a in acc.items()}


def _xf(o, w, h, px, py):
    """offset of an LEF-frame point inside an instance of footprint w x h (w/h = PLACED footprint) for orientation o"""
    if o == 'R0':
        return px, py
    if o == 'MX':
        return px, h - py
    if o == 'MY':
        return w - px, py
    if o == 'R180':
        return w - px, h - py
    if o == 'R90':
        return w - py, px
    if o == 'R270':
        return py, h - px
    return px, py


class LanePlacer:
    def __init__(self, *, occ, cell, W, H, R, margin, slide_um, tol_um, inst_rows, rows, I, edges, cell_of, size, kinds,
                 lef_path_of, lef_xy_fn, pl, mode):
        self.occ, self.CELL, self.W, self.H = occ, cell, W, H
        self.R, self.margin, self.slide, self.tol, self.mode = R, margin, slide_um, tol_um, mode
        self.rows, self.inst_rows, self.I, self.cell_of, self.size, self.pl = rows, inst_rows, I, cell_of, size, pl
        self.kinds, self.lef_path_of, self.lef_xy_fn = kinds, lef_path_of, lef_xy_fn
        self._pc = {}
        # tile -> [(own port, neighbour inst, neighbour port)]
        self.nb = collections.defaultdict(list)
        seen = set()
        for e in edges:
            s, t = e['source'], e['sink']
            si, sp, ti, tp = s[0], s[1], t[0], t[1]
            if si == ti or si not in cell_of or ti not in cell_of:
                continue
            if RST.search(sp.lower()) or RST.search(tp.lower()):
                continue
            for a_, ap_, b_, bp_ in ((si, sp, ti, tp), (ti, tp, si, sp)):
                if a_ in inst_rows and (a_, ap_, b_, bp_) not in seen:
                    seen.add((a_, ap_, b_, bp_)); self.nb[a_].append((ap_, b_, bp_))
        # planned lower-left of every lane tile (row centred on its site, tiles abutted as die_case puts them)
        self.plan_ll, self.row_geom = {}, {}
        for rid, tl in rows.items():
            g = self.geom(rid)
            self.row_geom[rid] = g
            x0, y0 = g['site'][0] - g['rw'] / 2, g['site'][1] - g['rh'] / 2
            for (n, *_), (ox, oy) in zip(g['tiles'], g['offs']):
                self.plan_ll[n] = (x0 + ox, y0 + oy)
        self.fails, self.not_inserted, self.relaxed = [], [], []
        self.stats = collections.Counter()
        self.max_hop = collections.Counter()

    # ---------- geometry ----------
    def geom(self, rid):
        tl = [self.rows[rid][t] for t in sorted(self.rows[rid])]
        fl = tl[0][1]; cx, cy = tl[0][2], tl[0][3]
        along_x = fl in ('WE', 'EW')
        dims = [self.size[self.cell_of[n]] for n, *_ in tl]
        rw = max(d[0] for d in dims) if along_x else sum(d[0] for d in dims)
        rh = sum(d[1] for d in dims) if along_x else max(d[1] for d in dims)
        offs, off = [], 0.0
        for w_, h_ in dims:
            offs.append((0.0, off) if along_x else (off, 0.0))
            off += h_ if along_x else w_
        return dict(tiles=tl, fl=fl, site=(cx, cy), along_x=along_x, dims=dims, rw=rw, rh=rh, offs=offs)

    def port_off(self, n, port, o='R0', wh=None):
        """offset of the port pin centroid from the instance lower-left (None when the view has no LEF pins)"""
        c = self.cell_of[n]
        if c not in self._pc:
            lp = self.lef_path_of(c)
            try:
                self._pc[c] = _port_centroids(self.lef_xy_fn, lp) if lp else {}
            except Exception:
                self._pc[c] = {}
        p = self._pc[c].get(port)
        if p is None:
            return None
        w, h = wh or self.size[c]
        return _xf(o, w, h, p[0], p[1])

    def nb_point(self, n, port):
        """('pt', x, y) for a placed / planned neighbour pin, ('rect', x0, y0, x1, y1) for a SYNTH block without pins"""
        if n in self.pl:
            v = self.pl[n]
            off = self.port_off(n, port, v['o'], (v['w'], v['h']))
            if off is not None:
                return ('pt', v['x'] + off[0], v['y'] + off[1]), 'placed'
            if self.I[n]['master'].startswith('hbfd'):
                return ('pt', v['x'] + v['w'] / 2, v['y'] + v['h'] / 2), 'placed'
            return ('rect', v['x'], v['y'], v['x'] + v['w'], v['y'] + v['h']), 'placed'
        if n in self.plan_ll:
            ll = self.plan_ll[n]; off = self.port_off(n, port)
            if off is None:
                w, h = self.size[self.cell_of[n]]; off = (w / 2, h / 2)
            return ('pt', ll[0] + off[0], ll[1] + off[1]), 'planned'
        return None, 'unplaced'

    # ---------- occupancy ----------
    def free_mask(self, i0, j0, i1, j1, nw, nh):
        """free[jj, ii] for lower-left cells (i0+ii, j0+jj), rect nw x nh cells"""
        occ = self.occ
        i0 = max(0, i0); j0 = max(0, j0); i1 = min(occ.nx - nw, i1); j1 = min(occ.ny - nh, j1)
        if i1 < i0 or j1 < j0:
            return None, i0, j0
        sub = (occ.g[j0:j1 + nh, i0:i1 + nw] != 0).astype(np.int32)
        ii = np.zeros((sub.shape[0] + 1, sub.shape[1] + 1), np.int32)
        ii[1:, 1:] = sub.cumsum(0).cumsum(1)
        s = ii[nh:nh + j1 - j0 + 1, nw:nw + i1 - i0 + 1] - ii[0:j1 - j0 + 1, nw:nw + i1 - i0 + 1] \
            - ii[nh:nh + j1 - j0 + 1, 0:i1 - i0 + 1] + ii[0:j1 - j0 + 1, 0:i1 - i0 + 1]
        return s == 0, i0, j0

    def rect_free(self, x, y, w, h):
        if x < 0 or y < 0 or x + w > self.W or y + h > self.H:
            return False
        C = self.CELL
        i0, j0 = int(x / C), int(y / C); i1, j1 = int(math.ceil((x + w) / C)), int(math.ceil((y + h) / C))
        return not self.occ.g[j0:min(j1, self.occ.ny), i0:min(i1, self.occ.nx)].any()

    # ---------- constraints ----------
    def terms(self, rid):
        """[(tile index, own port offset (dx, dy) from the ROW lower-left, neighbour geometry, kind, label)]"""
        g = self.row_geom[rid]; out = []
        for k, ((n, *_), (ox, oy)) in enumerate(zip(g['tiles'], g['offs'])):
            for port, m, mport in self.nb[n]:
                if self.inst_rows.get(m) == rid:
                    continue        # tile of the same row (abutted)
                geo, kind = self.nb_point(m, mport)
                if geo is None:
                    self.stats['nb_unplaced_block'] += 1
                    continue
                off = self.port_off(n, port)
                if off is None:
                    w_, h_ = g['dims'][k]; off = (w_ / 2, h_ / 2)
                out.append((k, (ox + off[0], oy + off[1]), geo, kind, f'{n}.{port} -> {m}.{mport}'))
        return out

    @staticmethod
    def span(geo, X, Y):
        if geo[0] == 'pt':
            return np.abs(X - geo[1]) + np.abs(Y - geo[2])
        _, x0, y0, x1, y1 = geo
        return np.maximum(0, np.maximum(x0 - X, X - x1)) + np.maximum(0, np.maximum(y0 - Y, Y - y1))

    def worst(self, T, X, Y, relaxed=False):
        """max span over constraint terms for candidate row lower-left arrays X, Y -> (max span array, argmax term)"""
        mx = np.zeros(np.shape(X)); arg = np.full(np.shape(X), -1)
        for t, (k, (dx, dy), geo, kind, lab) in enumerate(T):
            if relaxed and kind == 'planned':
                continue
            s = self.span(geo, X + dx, Y + dy)
            upd = s > mx
            mx = np.where(upd, s, mx); arg = np.where(upd, t, arg)
        return mx, arg

    # ---------- place one row ----------
    def place(self, rid):
        g = self.row_geom[rid]; rw, rh = g['rw'], g['rh']
        cx, cy = g['site']; x0, y0 = cx - rw / 2, cy - rh / 2
        T = self.terms(rid)
        lim = self.R - self.margin
        # planned-hop audit: the relay layer's own sites already over reach
        for k, (dx, dy), geo, kind, lab in T:
            m_ = lab.split(' -> ')[1].rsplit('.', 1)
            if m_[0] in self.plan_ll:          # planned basis on BOTH ends: the relay layer's sites (not GEN's placement)
                ll = self.plan_ll[m_[0]]; off = self.port_off(m_[0], m_[1])
                if off is None:
                    w_, h_ = self.size[self.cell_of[m_[0]]]; off = (w_ / 2, h_ / 2)
                geo = ('pt', ll[0] + off[0], ll[1] + off[1])
            s0 = float(self.span(geo, np.array(x0 + dx), np.array(y0 + dy)))
            if s0 > self.R + self.tol:
                self.not_inserted.append(dict(row=rid, hop=lab, planned_um=round(s0, 1), basis=kind))
        # 1 exact site / slides (cheap path)
        steps = [0.0] + [s * k for k in range(1, int(self.slide / self.CELL) + 1) for s in (self.CELL, -self.CELL)]
        for ax, tag in ((g['along_x'], 'slid along'), (not g['along_x'], 'slid across')):
            for d in steps:
                x, y = (x0 + d, y0) if ax else (x0, y0 + d)
                if not self.rect_free(x, y, rw, rh):
                    continue
                m, _ = self.worst(T, np.array([x]), np.array([y]))
                if m[0] <= lim:
                    return (x, y), ('exact site' if d == 0 else f'{tag} {abs(d):.1f} um'), float(m[0])
        # 2 windowed search inside the reach diamond of the site
        C = self.CELL
        nw, nh = int(math.ceil(rw / C)), int(math.ceil(rh / C))
        r = int(math.ceil(self.R / C))
        ci, cj = int(x0 / C), int(y0 / C)
        fm, i0, j0 = self.free_mask(ci - r, cj - r, ci + r, cj + r, nw, nh)
        if fm is not None and fm.any():
            jj, ii = np.nonzero(fm)
            X = (i0 + ii) * C; Y = (j0 + jj) * C
            disp = np.abs(X - x0) + np.abs(Y - y0)
            for relaxed in (False, True):
                m, arg = self.worst(T, X, Y, relaxed)
                ok = m <= lim
                if ok.any():
                    k = np.argmin(np.where(ok, disp, np.inf))
                    how = f"{'relaxed' if relaxed else 'reach'} window {disp[k]:.1f} um"
                    if relaxed:
                        self.relaxed.append(rid)
                    return (float(X[k]), float(Y[k])), how, float(self.worst(T, X[k:k + 1], Y[k:k + 1])[0][0])
            # 3 reach failure: name the bus; never relocate far
            m, arg = self.worst(T, X, Y, True)
            k = int(np.argmin(m))
            lab = T[int(arg[k])][4] if arg[k] >= 0 else '?'
            self.fails.append(dict(row=rid, tiles=[n for n, *_ in g['tiles']], flow=g['fl'], site=[round(cx, 1), round(cy, 1)],
                                   best_span_um=round(float(m[k]), 1), offending_hop=lab, reason='no free spot keeps every hop <= reach'))
            return (float(X[k]), float(Y[k])), f'REACH_FAIL least-violating window {disp[k]:.1f} um', float(m[k])
        self.fails.append(dict(row=rid, tiles=[n for n, *_ in g['tiles']], flow=g['fl'], site=[round(cx, 1), round(cy, 1)],
                               best_span_um=None, offending_hop=None, reason='no free spot of the row size inside the reach window'))
        return None, 'REACH_FAIL no free spot in window', None

    def order(self):
        """widest rows first (packing), as before"""
        return sorted(self.rows, key=lambda k: -sum(self.size[self.cell_of[v[0]]][0] * self.size[self.cell_of[v[0]]][1]
                                                     for v in self.rows[k].values()))

    def report(self):
        return dict(reach_um=self.R, margin_um=self.margin, slide_um=self.slide, tol_um=self.tol, mode=self.mode,
                    rows=len(self.rows), stats=dict(self.stats), relaxed_rows=len(self.relaxed),
                    reach_fail_rows=len(self.fails), not_inserted_hops=len(self.not_inserted),
                    not_inserted_rows=len({x['row'] for x in self.not_inserted}),
                    worst_placed_hop_hist=dict(self.max_hop))


def audit_edges(edges, pl, I, cell_of, size, R, lef_path_of, lef_xy_fn, tol=0.0):
    """Placed-hop audit after GEN placement, PER BUS = (driver inst, driver port, load inst, load port).
    Span = LOWER bound of the routed wire: REAL view -> port pin centroid (LEF), SYNTH block -> its rectangle (pins are
    assigned later, on a face), relay tile without LEF pins -> its centre.  Resets excluded (H.RST forest).
    Classes: hop (a relay at either end: lane / station hop placed over reach), not_inserted (block -> block bus over reach
    with no relay at all: the relay layer never planned it)."""
    pcs = {}

    def geo(n, port):
        v = pl[n]; c = cell_of[n]
        if c not in pcs:
            lp = lef_path_of(c)
            try:
                pcs[c] = _port_centroids(lef_xy_fn, lp) if lp else {}
            except Exception:
                pcs[c] = {}
        p = pcs[c].get(port)
        if p is not None:
            dx, dy = _xf(v['o'], v['w'], v['h'], p[0], p[1])
            return ('pt', v['x'] + dx, v['y'] + dy, v['x'] + dx, v['y'] + dy)
        if I[n]['master'].startswith('hbfd'):
            return ('pt', v['x'] + v['w'] / 2, v['y'] + v['h'] / 2, v['x'] + v['w'] / 2, v['y'] + v['h'] / 2)
        return ('rect', v['x'], v['y'], v['x'] + v['w'], v['y'] + v['h'])

    def gap(a, b):
        dx = max(0.0, a[1] - b[3], b[1] - a[3]); dy = max(0.0, a[2] - b[4], b[2] - a[4])
        return dx + dy
    bus = {}
    for e in edges:
        (si, sp), (ti, tp) = e['source'][:2], e['sink'][:2]
        if si == ti or si not in pl or ti not in pl or RST.search(sp.lower()) or RST.search(tp.lower()):
            continue
        k = (si, sp, ti, tp)
        if k in bus:
            continue
        bus[k] = gap(geo(si, sp), geo(ti, tp))
    over = []
    by = collections.Counter()
    for (si, sp, ti, tp), s in bus.items():
        if s <= R + tol:
            continue
        rs, rt = I[si]['master'].startswith('hbfd'), I[ti]['master'].startswith('hbfd')
        cls = 'hop' if (rs or rt) else 'not_inserted'
        fwd = I[si]['master'].startswith('hbfd_lh') and I[ti]['master'].startswith(('hbfd_lh', 'hbfd_land'))
        by[cls + ('_fwd' if fwd else '')] += 1
        over.append(dict(bus=f'{si}.{sp} -> {ti}.{tp}', driver_master=I[si]['master'], load_master=I[ti]['master'],
                         span_lb_um=round(s, 1), cls=cls, fwd=fwd, driver_rule=pl[si].get('rule', '')[:80],
                         load_rule=pl[ti].get('rule', '')[:80]))
    over.sort(key=lambda r: -r['span_lb_um'])
    return dict(buses_checked=len(bus), over_buses=len(over), by_class=dict(by), reach_um=R,
                basis='lower bound: REAL LEF port pin centroids / SYNTH block rectangles; resets excluded', buses=over)
