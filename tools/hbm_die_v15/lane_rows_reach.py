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

HBM-DIE8 10-20 lookahead='chain' (GEN2e4 r7 S7 fix; default 'site' = the behaviour above, byte-identical):
  r7 S7 failed 3659 rows: the relay router (relay_router.py) sites every station in a FREE cell with NO capacity model,
  so the stations of many buses (and whole equal-age pad chains: up to 31 rows on one point) share one site in the thin
  channels between the grant-slot SM frames / SU slices (failing 572 um windows 74 % blocked, row demand 1.17x the free
  area).  The planned site is a HINT, not a constraint: the binding rule is every PLACED hop <= R.  'chain' replaces the
  look-ahead "span to the unplaced neighbour's planned site <= R" by the exact necessary condition of the chain: walk
  from that neighbour through unplaced lane tiles (h edges from this tile) to every FIXED anchor (placed instance, or a
  planned relay home placed later within 64.8 um) and require span(this pin, anchor pin) <= h*R - margin; h = 1 is the
  direct placed-neighbour check exactly as before.  A chain thereby uses its real slack ((N+1)*R - route length) to
  leave a full window.  The candidate window grows to window_um (bounded, never the die-wide fallback); the nearest
  feasible candidate to the planned site still wins.  The reach is never relaxed: the post-placement per-bus audit
  (audit_edges) is the authority and every hop listed 'not_inserted' on the PLANNED basis is re-measured on the
  PLACED basis (placed_not_inserted) -- the GEN fails if any placed hop is over R.
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
                 lef_path_of, lef_xy_fn, pl, mode, lookahead='site', window_um=None, chain_depth=48, chain_nodes=4000):
        self.occ, self.CELL, self.W, self.H = occ, cell, W, H
        self.R, self.margin, self.slide, self.tol, self.mode = R, margin, slide_um, tol_um, mode
        self.rows, self.inst_rows, self.I, self.cell_of, self.size, self.pl = rows, inst_rows, I, cell_of, size, pl
        self.kinds, self.lef_path_of, self.lef_xy_fn = kinds, lef_path_of, lef_xy_fn
        self.lookahead, self.window = lookahead, float(window_um or R)
        self.chain_depth, self.chain_nodes = chain_depth, chain_nodes
        self._pc = {}
        # planned relay homes placed AFTER the lane rows (die_case 'planned relay home (bounded)', <= 64.8 um from home)
        self.home = {}
        for n_, v_ in I.items():
            m_ = re.search(r'home \(([\d.]+), ([\d.]+)\) um', v_.get('note', '') or '')
            if m_ and n_ not in inst_rows and n_ in cell_of:
                w_, h_ = size[cell_of[n_]]
                self.home[n_] = (float(m_.group(1)) + w_ / 2, float(m_.group(2)) + h_ / 2)
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
        self.chain_stats = collections.Counter()
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
                off = self.port_off(n, port)
                if off is None:
                    w_, h_ = g['dims'][k]; off = (w_ / 2, h_ / 2)
                d_ = (ox + off[0], oy + off[1])
                geo, kind = self.nb_point(m, mport)
                if self.lookahead == 'chain' and kind != 'placed':
                    anc = self.anchors(n, m, mport, rid)
                    self.chain_stats['terms'] += 1; self.chain_stats['anchors'] += len(anc)
                    for geo_, h_, kind_, lab_ in anc:
                        out.append((k, d_, geo_, kind_, f'{n}.{port} -> {m}.{mport} ~> {lab_} ({h_} hops)', h_))
                    if anc:
                        continue
                    self.chain_stats['no_anchor'] += 1
                if geo is None:
                    self.stats['nb_unplaced_block'] += 1
                    continue
                out.append((k, d_, geo, kind, f'{n}.{port} -> {m}.{mport}', 1))
        return out

    def anchors(self, n, m, mport, rid):
        """HBM-DIE8 chain look-ahead: fixed anchors reachable from this tile n through its unplaced neighbour m (entered on
        port mport) along unplaced lane tiles, never re-entering row rid -> [(geo, h edges from n, kind, label)]"""
        out, seen = [], {n, m}
        frontier = [(m, mport, 1)]
        nodes = 0
        while frontier:
            nxt = []
            for u, up, h in frontier:
                if u in self.pl or (u not in self.inst_rows and u in self.home):
                    if u in self.pl:
                        geo, _ = self.nb_point(u, up)
                    else:
                        geo = ('pt',) + self.home[u]
                    out.append((geo, h, 'chain' if h > 1 else 'placed', f'{u}.{up}'))
                    continue
                if u not in self.inst_rows or h >= self.chain_depth:
                    if u not in self.inst_rows:
                        self.chain_stats['open_end'] += 1
                    else:
                        self.chain_stats['depth_cap'] += 1
                    continue
                for _p, v, vp in self.nb[u]:
                    if v in seen or self.inst_rows.get(v) == rid:
                        continue
                    seen.add(v); nodes += 1
                    if nodes > self.chain_nodes:
                        self.chain_stats['node_cap'] += 1
                        return out
                    nxt.append((v, vp, h + 1))
            frontier = nxt
        return out

    @staticmethod
    def span(geo, X, Y):
        if geo[0] == 'pt':
            return np.abs(X - geo[1]) + np.abs(Y - geo[2])
        _, x0, y0, x1, y1 = geo
        return np.maximum(0, np.maximum(x0 - X, X - x1)) + np.maximum(0, np.maximum(y0 - Y, Y - y1))

    def worst(self, T, X, Y, relaxed=False):
        """max span over constraint terms for candidate row lower-left arrays X, Y -> (max span array, argmax term).
        A chain term (h edges to its anchor) counts as its span minus (h - 1) R: <= R - margin <=> span <= h R - margin."""
        mx = np.zeros(np.shape(X)); arg = np.full(np.shape(X), -1)
        for t, (k, (dx, dy), geo, kind, lab, h) in enumerate(T):
            if relaxed and kind in ('planned', 'chain'):
                continue
            s = self.span(geo, X + dx, Y + dy) - (h - 1) * self.R
            upd = s > mx
            mx = np.where(upd, s, mx); arg = np.where(upd, t, arg)
        return mx, arg

    # ---------- place one row ----------
    def place(self, rid):
        g = self.row_geom[rid]; rw, rh = g['rw'], g['rh']
        cx, cy = g['site']; x0, y0 = cx - rw / 2, cy - rh / 2
        T = self.terms(rid)
        lim = self.R - self.margin
        # planned-hop audit: the relay layer's own sites already over reach (direct neighbour terms, site basis)
        if self.lookahead == 'chain':
            la_, self.lookahead = self.lookahead, 'site'
            T0 = self.terms(rid); self.lookahead = la_
        else:
            T0 = T
        for k, (dx, dy), geo, kind, lab, h in T0:
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
        r = int(math.ceil(self.window / C))
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

    # ---------- HBM-DIE8 negotiated repair (rip-up and re-place) ----------
    def _cells(self, x, y, w, h):
        C = self.CELL
        return (max(0, int(x / C)), max(0, int(y / C)), min(self.occ.nx, int(math.ceil((x + w) / C))),
                min(self.occ.ny, int(math.ceil((y + h) / C))))

    def _tile_rects(self, rid, got):
        g = self.row_geom[rid]
        return [(n, got[0] + ox, got[1] + oy, w_, h_) for ((n, *_), (ox, oy), (w_, h_)) in zip(g['tiles'], g['offs'], g['dims'])]

    def _mark(self, rid, got, sgn):
        """+1: occupy the row's tile cells and enter its tiles in pl; -1: release them (blocks below never change)"""
        B = 108
        for n, x, y, w_, h_ in self._tile_rects(rid, got):
            i0, j0, i1, j1 = self._cells(x, y, w_, h_)
            self.cnt[j0:j1, i0:i1] += sgn
            self.occ.g[j0:j1, i0:i1] = np.where(self.cnt[j0:j1, i0:i1] > 0, 1, self.base[j0:j1, i0:i1])
            if sgn > 0:
                self.pl[n] = dict(m=self.cell_of[n], x=round(x, 3), y=round(y, 3), o='R0', w=w_, h=h_, rule='lane row (LP)')
            else:
                self.pl.pop(n, None)
            for bx in range(int(x // B), int((x + w_) // B) + 1):
                for by in range(int(y // B), int((y + h_) // B) + 1):
                    (self.bucket[(bx, by)].add if sgn > 0 else self.bucket[(bx, by)].discard)(rid)
        self.occ._ii = None

    def _victims(self, rid, x, y, rw, rh):
        B = 108; ci = self._cells(x, y, rw, rh); out = set()
        for bx in range(int(x // B) - 1, int((x + rw) // B) + 2):
            for by in range(int(y // B) - 1, int((y + rh) // B) + 2):
                for q in self.bucket.get((bx, by), ()):
                    if q == rid or q in out or self.res.get(q, (None,))[0] is None:
                        continue
                    for _n, tx, ty, tw, th in self._tile_rects(q, self.res[q][0]):
                        c2 = self._cells(tx, ty, tw, th)
                        if c2[0] < ci[2] and ci[0] < c2[2] and c2[1] < ci[3] and ci[1] < c2[3]:
                            out.add(q); break
        return out

    def _place_rec(self, rid):
        """place() with the per-row failure / relaxed bookkeeping kept per row (re-placement replaces it)"""
        nf, nn = len(self.fails), len(self.not_inserted)
        got, how, ws = self.place(rid)
        new_f = self.fails[nf:]; del self.fails[nf:]
        if self._ni_done.get(rid):
            del self.not_inserted[nn:]
        self._ni_done[rid] = True
        if new_f:
            self.fail_by[rid] = new_f
        else:
            self.fail_by.pop(rid, None)
        return got, how, ws

    def run(self, order, repair_rounds=0, cands=4):
        """place every row (as the die_case loop does) then up to repair_rounds of negotiated repair: a failing row takes
        the nearest reach-feasible spot that is free of BLOCKS, the rows it overlaps are ripped up and re-placed under
        their own exact constraints; the move is kept only if every ripped row re-places without a reach failure (the
        failure count never rises).  -> {rid: (lower-left or None, how, worst span)}"""
        self.base = self.occ.g.copy(); self.cnt = np.zeros(self.occ.g.shape, np.int16)
        self.bucket = collections.defaultdict(set); self.res = {}; self.fail_by = {}; self._ni_done = {}
        for rid in order:
            got, how, ws = self._place_rec(rid)
            self.res[rid] = (got, how, ws)
            if got is not None:
                self._mark(rid, got, +1)
        for rnd in range(repair_rounds):
            failed = [r for r in order if r in self.fail_by]
            fixed = 0
            for rid in failed:
                fixed += self._repair(rid, cands)
            self.stats[f'repair_round{rnd}_fixed'] = fixed
            self.stats[f'repair_round{rnd}_tried'] = len(failed)
            if not fixed:
                break
        self.fails = [e for r in order for e in self.fail_by.get(r, [])]
        self.relaxed = [r for r in order if self.res[r][1].startswith('relaxed')]
        return self.res

    def _repair(self, rid, cands):
        g = self.row_geom[rid]; rw, rh = g['rw'], g['rh']; C = self.CELL
        cx, cy = g['site']; x0, y0 = cx - rw / 2, cy - rh / 2
        nw, nh = int(math.ceil(rw / C)), int(math.ceil(rh / C)); r = int(math.ceil(self.window / C))
        ci, cj = int(x0 / C), int(y0 / C)
        occ_g = self.occ.g; self.occ.g = self.base          # candidates free of BLOCKS (rows may be ripped up)
        try:
            fm, i0, j0 = self.free_mask(ci - r, cj - r, ci + r, cj + r, nw, nh)
        finally:
            self.occ.g = occ_g
        if fm is None or not fm.any():
            return 0
        jj, ii = np.nonzero(fm)
        X = (i0 + ii) * C; Y = (j0 + jj) * C
        old = self.res[rid]
        if old[0] is not None:
            self._mark(rid, old[0], -1)
        T = self.terms(rid)
        m, _ = self.worst(T, X, Y)
        ok = m <= self.R - self.margin
        if not ok.any():
            m, _ = self.worst(T, X, Y, True); ok = m <= self.R - self.margin
        if not ok.any():
            if old[0] is not None:
                self._mark(rid, old[0], +1)
            return 0
        X, Y = X[ok], Y[ok]
        # rank by row cells overlapped (fewest rip-ups), then displacement from the planned site
        wj1, wi1 = min(self.cnt.shape[0], j0 + fm.shape[0] + nh), min(self.cnt.shape[1], i0 + fm.shape[1] + nw)
        rows_ = (self.cnt[j0:wj1, i0:wi1] > 0).astype(np.int32)          # window only
        ii_ = np.zeros((rows_.shape[0] + 1, rows_.shape[1] + 1), np.int32); ii_[1:, 1:] = rows_.cumsum(0).cumsum(1)
        I_ = (X / C).round().astype(int) - i0; J_ = (Y / C).round().astype(int) - j0
        I1 = np.minimum(I_ + nw, rows_.shape[1]); J1 = np.minimum(J_ + nh, rows_.shape[0])
        ov = ii_[J1, I1] - ii_[J_, I1] - ii_[J1, I_] + ii_[J_, I_]
        disp = np.abs(X - x0) + np.abs(Y - y0)
        for k in np.lexsort((disp, ov))[:cands]:
            x, y = float(X[k]), float(Y[k])
            vic = self._victims(rid, x, y, rw, rh)
            saved = {q: self.res[q] for q in vic}
            sf = {q: self.fail_by.get(q) for q in vic}
            for q in vic:
                self._mark(q, self.res[q][0], -1)
            if not self.rect_free(x, y, rw, rh):
                for q in vic:
                    self._mark(q, saved[q][0], +1)
                continue
            self._mark(rid, (x, y), +1)
            placed, good = [], True
            for q in sorted(vic, key=lambda q_: -self.row_geom[q_]['rw'] * self.row_geom[q_]['rh']):
                gq, hq, wq = self._place_rec(q)
                self.res[q] = (gq, hq, wq)
                if gq is None or q in self.fail_by:
                    good = False
                    break
                self._mark(q, gq, +1); placed.append(q)
            if good:
                self.res[rid] = ((x, y), 'repair (rip-up %d rows)' % len(vic), float(self.worst(T, np.array([x]), np.array([y]))[0][0]))
                self.fail_by.pop(rid, None); self.stats['repair_moves'] += 1; self.stats['repair_ripped'] += len(vic)
                return 1
            for q in placed:
                self._mark(q, self.res[q][0], -1)
            self._mark(rid, (x, y), -1)
            for q in vic:
                self.res[q] = saved[q]; self._mark(q, saved[q][0], +1)
                if sf[q]:
                    self.fail_by[q] = sf[q]
                else:
                    self.fail_by.pop(q, None)
        if old[0] is not None:
            self._mark(rid, old[0], +1)
        return 0

    def order(self, how='area'):
        """area: widest rows first (packing, as before).  chain: breadth-first from the rows that touch an already placed
        instance (block ends first, then their successors ...), widest first inside a BFS level, so each row is placed
        with its chain neighbour toward a placed end already fixed (hard constraint) and only the far side planned."""
        if how == 'chain':
            area = lambda k: -sum(self.size[self.cell_of[v[0]]][0] * self.size[self.cell_of[v[0]]][1] for v in self.rows[k].values())
            adj = collections.defaultdict(set); lvl = {}
            for n, lst in self.nb.items():
                r0 = self.inst_rows[n]
                for _, m, _ in lst:
                    r1 = self.inst_rows.get(m)
                    if r1 is None:
                        if m in self.pl:
                            lvl[r0] = 0
                    elif r1 != r0:
                        adj[r0].add(r1)
            frontier = sorted(lvl, key=area); d = 0
            while frontier:
                nxt = set()
                for r in frontier:
                    for q in adj[r]:
                        if q not in lvl:
                            lvl[q] = d + 1; nxt.add(q)
                d += 1; frontier = sorted(nxt, key=area)
            return sorted(self.rows, key=lambda k: (lvl.get(k, 10 ** 9), area(k)))
        return sorted(self.rows, key=lambda k: -sum(self.size[self.cell_of[v[0]]][0] * self.size[self.cell_of[v[0]]][1]
                                                     for v in self.rows[k].values()))

    def report(self):
        return dict(reach_um=self.R, margin_um=self.margin, slide_um=self.slide, tol_um=self.tol, mode=self.mode,
                    rows=len(self.rows), stats=dict(self.stats), relaxed_rows=len(self.relaxed),
                    lookahead=self.lookahead, window_um=self.window, chain_stats=dict(self.chain_stats),
                    reach_fail_rows=len(self.fails), not_inserted_hops=len(self.not_inserted),
                    not_inserted_rows=len({x['row'] for x in self.not_inserted}),
                    worst_placed_hop_hist=dict(self.max_hop))


def audit_edges(edges, pl, I, cell_of, size, R, lef_path_of, lef_xy_fn, tol=0.0):
    """Placed-hop audit after GEN placement, PER BUS = (driver inst, driver port, load inst, load port).
    Span = LOWER bound of the routed wire: REAL view -> port pin centroid (LEF), SYNTH block -> its rectangle (pins are
    assigned later, on a face), relay tile without LEF pins -> its centre.  Resets excluded (H.RST forest).
    Classes: hop (a relay at either end: lane / station hop placed over reach), not_inserted (block -> block bus over reach
    with no relay at all: the relay layer never planned it)."""
    pcs, pxy = {}, {}

    def geo(n, port, bits=None):
        v = pl[n]; c = cell_of[n]
        if c not in pcs:
            lp = lef_path_of(c)
            try:
                pxy[c] = lef_xy_fn(lp) if lp else {}
                pcs[c] = _port_centroids(lambda _p: pxy[c], lp) if lp else {}
            except Exception:
                pcs[c] = {}; pxy[c] = {}
        p = pcs[c].get(port)
        if bits and pxy.get(c):
            # HBM-DIE8: the bus's OWN bits (a ctl_pNN slice of a die-wide PHY port), not the whole-port centroid
            xs = [pxy[c][f'{port}[{k}]'] for k in bits if f'{port}[{k}]' in pxy[c]]
            if xs:
                p = (sum(x for x, _ in xs) / len(xs), sum(y for _, y in xs) / len(xs))
        if p is not None:
            dx, dy = _xf(v['o'], v['w'], v['h'], p[0], p[1])
            return ('pt', v['x'] + dx, v['y'] + dy, v['x'] + dx, v['y'] + dy)
        if I[n]['master'].startswith('hbfd'):
            return ('pt', v['x'] + v['w'] / 2, v['y'] + v['h'] / 2, v['x'] + v['w'] / 2, v['y'] + v['h'] / 2)
        return ('rect', v['x'], v['y'], v['x'] + v['w'], v['y'] + v['h'])

    def gap(a, b):
        dx = max(0.0, a[1] - b[3], b[1] - a[3]); dy = max(0.0, a[2] - b[4], b[2] - a[4])
        return dx + dy
    bus, bb = {}, collections.defaultdict(lambda: (set(), set()))
    for e in edges:
        (si, sp), (ti, tp) = e['source'][:2], e['sink'][:2]
        if si == ti or si not in pl or ti not in pl or RST.search(sp.lower()) or RST.search(tp.lower()):
            continue
        k = (si, sp, ti, tp)
        s_, t_ = e['source'], e['sink']
        sb_, tb_ = bb[k]
        if len(s_) >= 4 and len(t_) >= 4:
            sb_.update(range(s_[2], s_[3])); tb_.update(range(t_[2], t_[3]))
    for k, (sb, tb) in bb.items():
        si, sp, ti, tp = k
        bus[k] = gap(geo(si, sp, sorted(sb)), geo(ti, tp, sorted(tb)))
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
