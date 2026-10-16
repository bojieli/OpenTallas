#!/usr/bin/env python3
"""Explicit die clock tree for HBM v15 view cases (H-DIE 2026-10-15): the die-level clock delivery from the PLL output at
the hb_ckgen slot to every view clock pin, built as real ASAP7 RVT repeaters and wires, placed ONLY in free die area.

Why not TritonCTS: on this die (132 macro sinks over 31 x 21 mm, 159 block blockages) TritonCTS 26Q3 left leaf buffers
at H-tree points up to 12 mm from their macro sink (clknet_8_94_0: buffer at (6730, 11101) um, sink svc_NW_s1 u_pc7 at
(3305, 20048) um; 2.2 pF leaf, 175 ns wire delay) -- not a usable die tree.

Structure (the hfd_ckgen header's plan: PLL -> four quadrant roots -> tile pins):
  ckgen pin -> global root G (free point nearest the die centre)
  G -> south / north mid roots -> four quadrant roots (free point nearest the centroid of the quadrant's sinks)
  quadrant root -> recursive bisection of the quadrant's sinks sorted along the row (a binary tree whose branch points
  sit at the median gap, so every leaf sees the same number of levels and near-equal wire)
  every tree edge = a Manhattan route over a 20 um grid that may cross blocks on M7-M9 for at most MAX_RUN um (the
  repeater span), with a repeater at a free grid cell at least every SPAN um of wire; the leaf repeater sits at the free
  cell nearest its sink pin.
Balance: each branch point pads its faster child with delay repeaters (each = one BUF stage at the measured-model stage
delay) until the children's model insertions match to within one stage; the case's propagated-clock STA measures the
real spread afterwards (report_clock_skew + per-sink latency).

Output: dict(buffers=[(name, cell, x, y)], nets=[(net, driver_ref, [load_refs])], root_net, model) where a ref is
('port', name) | ('buf', name) | ('pin', inst, pin).
"""
import heapq, math
from collections import defaultdict

GRID = 10.0          # um (10 um so 20-um die gaps between abutted blocks are usable; 20 um left them all blocked)
SPAN = 200.0         # max wire between repeaters (um); stage_ps(L)=25+8.6e-4 L^2 is minimal per um near 170 um (420 um cost 0.42 ps/um, 200 um 0.30)
MAX_RUN = 400.0      # max length of a route segment over blocked area (repeater cannot sit there)
BUF = 'BUFx24_ASAP7_75t_R'
PAD = 'BUFx12f_ASAP7_75t_R'
STAGE_PS = 70.0      # model: one repeater stage incl. 420 um M8 (TT); used only to pad, STA measures the result


class Grid:
    def __init__(self, W, H, obstacles, margin=0.0):
        self.W, self.H = W, H
        self.nx, self.ny = int(W // GRID), int(H // GRID)
        self.blk = bytearray(self.nx * self.ny)
        for (x0, y0, x1, y1) in obstacles:
            # a cell is blocked iff it overlaps the obstacle grown by margin (exact: a 20-um abutment gap keeps its two
            # 10-um cells free at margin 0; the old floor/floor rule blocked both)
            i0 = max(0, int(math.floor((x0 - margin) / GRID))); i1 = min(self.nx - 1, int(math.ceil((x1 + margin) / GRID)) - 1)
            j0 = max(0, int(math.floor((y0 - margin) / GRID))); j1 = min(self.ny - 1, int(math.ceil((y1 + margin) / GRID)) - 1)
            for j in range(j0, j1 + 1):
                row = j * self.nx
                for i in range(i0, i1 + 1):
                    self.blk[row + i] = 1

    def cell(self, x, y):
        return min(self.nx - 1, max(0, int(x // GRID))), min(self.ny - 1, max(0, int(y // GRID)))

    def xy(self, c):
        return (c[0] + 0.5) * GRID, (c[1] + 0.5) * GRID

    def free(self, c):
        return not self.blk[c[1] * self.nx + c[0]]

    def nearest_free(self, x, y, rmax=4000.0):
        ci, cj = self.cell(x, y)
        if self.free((ci, cj)):
            return (ci, cj)
        for r in range(1, int(rmax // GRID) + 1):
            best = None
            for di in range(-r, r + 1):
                for dj in (-r, r) if abs(di) != r else range(-r, r + 1):
                    c = (ci + di, cj + dj)
                    if 0 <= c[0] < self.nx and 0 <= c[1] < self.ny and self.free(c):
                        d = abs(di) + abs(dj)
                        if best is None or d < best[0]:
                            best = (d, c)
            if best:
                return best[1]
        raise SystemExit(f'no free cell within {rmax} um of ({x}, {y})')

    def route(self, a, b, max_run=None):
        """shortest grid path a->b (cells) whose runs over blocked cells are <= MAX_RUN; returns the cell list.
        A sink in a pocket enclosed by more than MAX_RUN of blocks retries once at 3 x MAX_RUN (reported by STA as a
        long repeater-free span, never hidden)."""
        try:
            return self._route(a, b, max_run or MAX_RUN)
        except SystemExit:
            if max_run:
                raise
            return self._route(a, b, 3 * MAX_RUN)

    def _route(self, a, b, max_run):
        R = int(max_run // GRID)
        start = (a, 0)
        dist = {start: 0}
        # At a cell, a path no longer in steps and no longer into a blocked
        # run dominates the other label: it has every remaining continuation
        # available to that label. Keep this exact Pareto frontier instead of
        # expanding up to R equivalent labels throughout a large die detour.
        # Preserve predecessor records even when a queued label is dominated;
        # an already-discovered child's valid path may still refer to it.
        labels = {a: [(0, 0)]}
        prev = {}
        # Among equal admissible f values, advance the deeper path first. The
        # old smaller-g tie break floods an entire rectangle of equally short
        # Manhattan paths before taking the final step to a distant endpoint.
        pq = [(abs(a[0] - b[0]) + abs(a[1] - b[1]), 0, a, 0)]
        while pq:
            f, neg_g, c, run = heapq.heappop(pq)
            g = -neg_g
            if c == b:
                path = [c]; s = (c, run)
                while s in prev:
                    s = prev[s]; path.append(s[0])
                return path[::-1]
            if dist.get((c, run)) != g:
                continue
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if not (0 <= n[0] < self.nx and 0 <= n[1] < self.ny):
                    continue
                nr = 0 if self.free(n) else run + 1
                if nr > R:
                    continue
                s = (n, nr); ng = g + 1
                if ng < dist.get(s, 1 << 60):
                    old = labels.get(n, ())
                    if any(lr <= nr and lg <= ng for lr, lg in old):
                        continue
                    for lr, lg in old:
                        if nr <= lr and ng <= lg:
                            dist.pop((n, lr), None)
                    labels[n] = [(lr, lg) for lr, lg in old if not (nr <= lr and ng <= lg)] + [(nr, ng)]
                    dist[s] = ng; prev[s] = (c, run)
                    heapq.heappush(pq, (ng + abs(n[0] - b[0]) + abs(n[1] - b[1]), -ng, n, nr))
        raise SystemExit(f'no clock route {a} -> {b}')


def stage_ps(L):
    """model delay of one BUFx24 stage driving L um of M8 into the next repeater (calibrated on the first explicit run:
    ~176 ps per ~420 um stage at TT); used only to choose the root and to pre-balance, STA measures the result."""
    return 25.0 + 8.6e-4 * L * L


PAD_PS = 20.0


def ckgen_pin_xy(slot, pin):
    """Die coordinate (um) of a hb_ckgen output pin (H-DIE-CKGEN 2026-10-16): the die tree of a domain starts at the
    ckgen's pll_<domain> pin (the generated clock of the hardened hfd_ckgen parent), not at the slot centre.  The slot
    pin carries face + offset (um from the W edge for N/S, from the S edge for E/W); R0 slots only (every ckgen grant)."""
    o, w, h = slot['origin'], slot['outline']['w'], slot['outline']['h']
    if o.get('orient', 'R0') != 'R0':
        raise ValueError(f"ckgen slot orient {o.get('orient')}: only R0 is mapped")
    p = next((q for q in slot.get('pins', []) if q['name'] == pin), None)
    if p is None or 'offset' not in p:
        raise KeyError(f"ckgen slot has no placed pin {pin}")
    f, off = p['face'], float(p['offset'])
    return {'S': (o['x'] + off, o['y']), 'N': (o['x'] + off, o['y'] + h),
            'W': (o['x'], o['y'] + off), 'E': (o['x'] + w, o['y'] + off)}[f]


def build(W, H, obstacles, root_xy, sinks, quadrant_of, leaf_pads=None, quad_pads=None, root_search_um=3000.0,
          mode='htree', bin_um=1600.0):
    """sinks: [(inst, pin, x, y)]; quadrant_of(inst) -> 'SW'|'SE'|'NW'|'NE'.
    leaf_pads {inst: n} / quad_pads {quadrant: n}: measured skew corrections (STA feedback), outside the model."""
    leaf_pads = leaf_pads or {}
    quad_pads = quad_pads or {}
    g = Grid(W, H, obstacles)
    bufs, nets = [], []
    cnt = defaultdict(int)

    def newbuf(tag, c, cell=BUF):
        cnt[tag] += 1
        n = f'dck_{tag}_{cnt[tag]}'
        x, y = g.xy(c)
        bufs.append((n, cell, round(x, 3), round(y, 3)))
        return n

    def plan(path):
        """repeater cells along a routed path and the model delay of the chain (excluding the end buffer's input)."""
        reps, since, last_free, lf_since, d = [], 0.0, None, 0.0, 0.0
        for k in range(1, len(path)):
            since += GRID
            c = path[k]
            if g.free(c):
                last_free, lf_since = c, since
            if since >= SPAN - GRID and last_free is not None and k < len(path) - 1:
                reps.append(last_free); d += stage_ps(lf_since); since -= lf_since; last_free = None
        d += stage_ps(since)
        return reps, d

    def chain(src_ref, src_c, dst_c, tag, path=None):
        path = path or g.route(src_c, dst_c)
        reps, d = plan(path)
        drv = src_ref
        for c in reps:
            b = newbuf(tag, c)
            nets.append((f'n_{b}', drv, [('buf', b)]))
            drv = ('buf', b)
        return drv, d

    def pad(load_buf, c, n, tag):
        if n <= 0:
            return
        net = next(nn for nn in nets if nn[2] == [('buf', load_buf)])
        nets.remove(net)
        drv = net[1]
        for k in range(n):
            pb = newbuf(tag, c, PAD)
            nets.append((f'n_{pb}', drv, [('buf', pb)]))
            drv = ('buf', pb)
        nets.append((net[0], drv, [('buf', load_buf)]))

    quads = defaultdict(list)
    for s in sinks:
        quads[quadrant_of(s[0])].append(s)

    def subtree(items, drv_ref, drv_c, tag):
        """drive items from drv_ref at drv_c; returns model insertion (ps) per sink from drv_ref's output."""
        if len(items) == 1:
            inst, pin, x, y = items[0]
            c = g.nearest_free(x, y)
            d, dl = chain(drv_ref, drv_c, c, tag)
            for k in range(leaf_pads.get(inst, 0)):
                pb = newbuf(tag + 'LP', c, PAD)
                nets.append((f'n_{pb}', d, [('buf', pb)]))
                d = ('buf', pb)
            leaf = newbuf(tag + 'L', c)
            nets.append((f'n_{leaf}', d, [('buf', leaf)]))
            nets.append((f'n_{leaf}_o', ('buf', leaf), [('pin', inst, pin)]))
            return {inst: dl + stage_ps(10.0)}
        items = sorted(items, key=lambda s: (s[2], s[3]))
        h = len(items) // 2
        res = []
        for part in (items[:h], items[h:]):
            cx = sum(s[2] for s in part) / len(part); cy = sum(s[3] for s in part) / len(part)
            c = g.nearest_free(cx, cy)
            d, dl = chain(drv_ref, drv_c, c, tag)
            b = newbuf(tag + 'B', c)
            nets.append((f'n_{b}', d, [('buf', b)]))
            sub = subtree(part, ('buf', b), c, tag)
            res.append((b, c, dl, sub))
        mx = [dl + max(sub.values()) for _, _, dl, sub in res]
        top = max(mx)
        out = {}
        for (b, c, dl, sub), m in zip(res, mx):
            n = int(round((top - m) / PAD_PS))
            pad(b, c, n, tag + 'P')
            for inst, v in sub.items():
                out[inst] = dl + v + n * PAD_PS
        return out

    if mode == 'lane':
        return _lane(W, H, g, root_xy, sinks, bufs, nets, newbuf, chain, pad)
    if mode == 'htree':
        return _htree(W, H, g, root_xy, sinks, bufs, nets, newbuf, chain, pad, subtree, bin_um)
    # quadrant roots, then the global root that best equalises the four model branch delays
    qc = {}
    for q, pts in quads.items():
        cx = sum(s[2] for s in pts) / len(pts); cy = sum(s[3] for s in pts) / len(pts)
        qc[q] = g.nearest_free(cx, cy)
    # separable 1-D searches (x on the die mid-line, then y) for the root that equalises the four branch model delays
    best = None
    cache = {}

    def evaluate(cand):
        if cand not in cache:
            paths = {q: g.route(cand, c) for q, c in qc.items()}
            cache[cand] = (paths, {q: plan(pth)[1] for q, pth in paths.items()})
        return cache[cand]
    step = 200.0
    k = int(root_search_um // step)
    bx = None
    for i in range(-k, k + 1):
        try:
            cand = g.nearest_free(W / 2 + i * step, H / 2, rmax=step)
        except SystemExit:
            continue
        paths, dly = evaluate(cand)
        ew = abs((dly.get('SE', 0) + dly.get('NE', 0)) - (dly.get('SW', 0) + dly.get('NW', 0)))
        if bx is None or ew < bx[0]:
            bx = (ew, g.xy(cand)[0])
    for j in range(-k, k + 1):
        try:
            cand = g.nearest_free(bx[1], H / 2 + j * step, rmax=step)
        except SystemExit:
            continue
        paths, dly = evaluate(cand)
        spread = max(dly.values()) - min(dly.values())
        if best is None or (spread, max(dly.values())) < best[0]:
            best = ((spread, max(dly.values())), cand, paths, dly)
    (spread, worst), gc, gpaths, gdly = best
    rc = g.nearest_free(*root_xy)
    d0, dl0 = chain(('port', 'clk_hbm'), rc, gc, 'g')
    G = newbuf('gR', gc)
    nets.append(('n_' + G, d0, [('buf', G)]))
    ins, qtot = {}, {}
    qroot = {}
    for q in sorted(quads):
        d, dlq = chain(('buf', G), gc, qc[q], 'q' + q, path=gpaths[q])
        Q = newbuf('q' + q + 'R', qc[q])
        nets.append(('n_' + Q, d, [('buf', Q)]))
        sub = subtree(quads[q], ('buf', Q), qc[q], 'q' + q)
        qroot[q] = Q
        qtot[q] = {inst: dl0 + dlq + v for inst, v in sub.items()}
    top = max(max(v.values()) for v in qtot.values())
    qpad = {}
    for q, v in qtot.items():
        n = int(round((top - max(v.values())) / PAD_PS)) + quad_pads.get(q, 0)
        qpad[q] = n
        pad(qroot[q], qc[q], n, 'qP' + q)
        for inst, x in v.items():
            ins[inst] = x + n * PAD_PS
    by = defaultdict(list)
    for n, d, loads in nets:
        by[d].append((n, loads))
    merged = [(lst[0][0], d, [l for _, ls in lst for l in ls]) for d, lst in by.items()]
    v = list(ins.values())
    model = dict(buffers=len(bufs), leaf_pad_buffers=sum(leaf_pads.values()), quad_pad_buffers=qpad,
                 global_root_um=[round(x, 1) for x in g.xy(gc)], root_branch_model_ps={q: round(x, 1) for q, x in gdly.items()},
                 model_insertion_ps=[round(min(v), 1), round(max(v), 1)],
                 grid_um=GRID, span_um=SPAN, max_run_over_blocks_um=MAX_RUN, pad_ps_model=PAD_PS,
                 free_cells_frac=round(1 - sum(g.blk) / len(g.blk), 4))
    return dict(buffers=bufs, nets=merged, model=model)


def _htree(W, H, g, root_xy, sinks, bufs, nets, newbuf, chain, pad, subtree, bin_um):
    """H-DIE 0030 (coordinator D1, 10-16): d2's median-bisection tree over all sinks padded every branch (46k of 67k stream
    repeaters were pads, model insertion 20.2 ns). Here: a geometric H-tree over the die (split the longer side at its
    midpoint, branch points at region centres snapped to the nearest free die cell, so every root-to-region path has the
    same nominal length), ending in BIN roots (<= bin_um square regions holding sinks); each bin is a small local
    bisection tree (the old subtree, short wires); ONE balancing level: pads only at the bin roots, to the slowest bin."""
    bins = defaultdict(list)
    for s in sinks:
        bins[(int(s[2] // bin_um), int(s[3] // bin_um))].append(s)
    binroots = {}      # bin -> (buf, cell, model ps from the die root buffer output)

    def region(x0, y0, x1, y1, drv_ref, drv_c, d_in, tag):
        keys = [k for k in bins if x0 <= (k[0] + 0.5) * bin_um < x1 and y0 <= (k[1] + 0.5) * bin_um < y1]
        if not keys:
            return
        if len(keys) == 1 or (x1 - x0 <= bin_um and y1 - y0 <= bin_um):
            for k in keys:
                pts = bins[k]
                cx = sum(s[2] for s in pts) / len(pts); cy = sum(s[3] for s in pts) / len(pts)
                c = g.nearest_free(cx, cy)
                d, dl = chain(drv_ref, drv_c, c, tag)
                b = newbuf(tag + 'R', c)
                nets.append((f'n_{b}', d, [('buf', b)]))
                binroots[k] = (b, c, d_in + dl)
            return
        halves = ([(x0, y0, (x0 + x1) / 2, y1), ((x0 + x1) / 2, y0, x1, y1)] if x1 - x0 >= y1 - y0 else
                  [(x0, y0, x1, (y0 + y1) / 2), (x0, (y0 + y1) / 2, x1, y1)])
        for i, (a0, b0, a1, b1) in enumerate(halves):
            if not any(a0 <= (k[0] + 0.5) * bin_um < a1 and b0 <= (k[1] + 0.5) * bin_um < b1 for k in keys):
                continue
            c = g.nearest_free((a0 + a1) / 2, (b0 + b1) / 2)
            d, dl = chain(drv_ref, drv_c, c, tag)
            b = newbuf(tag + 'H', c)
            nets.append((f'n_{b}', d, [('buf', b)]))
            region(a0, b0, a1, b1, ('buf', b), c, d_in + dl + stage_ps(10.0), tag)

    rc = g.nearest_free(*root_xy)
    gc = g.nearest_free(W / 2, H / 2)
    d0, dl0 = chain(('port', 'clk_hbm'), rc, gc, 'g')
    G = newbuf('gR', gc)
    nets.append(('n_' + G, d0, [('buf', G)]))
    region(0.0, 0.0, W, H, ('buf', G), gc, 0.0, 'h')
    # local trees, then one balancing level at the bin roots
    tot = {}
    for k, (b, c, d) in binroots.items():
        sub = subtree(bins[k], ('buf', b), c, 'l')
        tot[k] = (d, sub)
    top = max(d + max(sub.values()) for d, sub in tot.values())
    ins, npad = {}, 0
    for k, (d, sub) in tot.items():
        n = int(round((top - d - max(sub.values())) / PAD_PS))
        b, c, _ = binroots[k]
        # pad on the bin root's input (pad() splices pads on the net that loads this buffer)
        pad(b, c, n, 'bP')
        npad += n
        for inst, v in sub.items():
            ins[inst] = dl0 + d + v + n * PAD_PS
    by = defaultdict(list)
    for n_, d_, loads in nets:
        by[d_].append((n_, loads))
    merged = [(lst[0][0], d_, [l for _, ls in lst for l in ls]) for d_, lst in by.items()]
    v = list(ins.values())
    local_pads = sum(1 for b in bufs if b[0].startswith('dck_lP'))
    model = dict(mode='htree', bin_um=bin_um, bins=len(bins), buffers=len(bufs), bin_pad_buffers=npad,
                 local_pad_buffers=local_pads, global_root_um=[round(x, 1) for x in g.xy(gc)],
                 model_insertion_ps=[round(min(v), 1), round(max(v), 1)], grid_um=GRID, span_um=SPAN,
                 max_run_over_blocks_um=MAX_RUN, pad_ps_model=PAD_PS, free_cells_frac=round(1 - sum(g.blk) / len(g.blk), 4))
    return dict(buffers=bufs, nets=merged, model=model)


LANE_RE = __import__('re').compile(r'^(?:rly_|svg_|sm_)(SW|SE|NW|NE)(\d+)(?:_(\d+))?$')


def _lane(W, H, g, root_xy, sinks, bufs, nets, newbuf, chain, pad):
    """H-DIE 0600 (10-16): clock follows data.  The stream sinks of one SM_HBM lane (svg_<q><k> -> rly_<q><k>_NN ->
    sm_<q><k>) are driven by ONE buffered spine laid along the lane in data order, so two communicating neighbours share
    the whole clock path except the one spine hop between them (non-common = one hop, ~200 ps model, instead of up to
    the full H-tree depth).  The lane heads are fed from the die root by direct routed chains and padded to the slowest
    head (lanes do not exchange stream data with each other in this case; pads only at the 32 heads).  The capture
    clock of hop n is one spine hop later than its launch: +setup, -hold on the forward data path (STA measures it)."""
    import re as _re
    groups = defaultdict(list)
    for s in sinks:
        m = LANE_RE.match(s[0])
        if m:
            order = -1 if s[0].startswith('svg_') else (10 ** 6 if s[0].startswith('sm_') else int(m.group(3)))
            groups[(m.group(1), m.group(2))].append((order, s))
        else:
            groups[('X', s[0])].append((0, s))
    rc = g.nearest_free(*root_xy)
    gc = g.nearest_free(W / 2, H / 2)
    d0, dl0 = chain(('port', 'clk_hbm'), rc, gc, 'g')
    G = newbuf('gR', gc)
    nets.append(('n_' + G, d0, [('buf', G)]))
    heads, lane_ins, hops = {}, {}, []
    for key in sorted(groups):
        lst = [s for _, s in sorted(groups[key], key=lambda t: t[0])]
        hc = g.nearest_free(lst[0][2], lst[0][3])
        d, dl = chain(('buf', G), gc, hc, 'z')
        hb = newbuf('zH', hc)
        nets.append((f'n_{hb}', d, [('buf', hb)]))
        heads[key] = (hb, hc, dl)
        drv, dc, t = ('buf', hb), hc, 0.0
        ins = {}
        for i, (inst, pin, x, y) in enumerate(lst):
            c = g.nearest_free(x, y)
            if i:
                dd, dlh = chain(drv, dc, c, 'zS')
                sb = newbuf('zT', c)
                nets.append((f'n_{sb}', dd, [('buf', sb)]))
                hops.append(dlh + stage_ps(10.0))
                t += dlh + stage_ps(10.0)
                drv, dc = ('buf', sb), c
            leaf = newbuf('zL', c)
            nets.append((f'n_{leaf}', drv, [('buf', leaf)]))
            nets.append((f'n_{leaf}_o', ('buf', leaf), [('pin', inst, pin)]))
            ins[inst] = t + stage_ps(10.0)
        lane_ins[key] = ins
    top = max(heads[k][2] for k in heads)
    out, npad = {}, 0
    for key, (hb, hc, dl) in heads.items():
        n = int(round((top - dl) / PAD_PS))
        pad(hb, hc, n, 'zP')
        npad += n
        for inst, v in lane_ins[key].items():
            out[inst] = dl0 + dl + n * PAD_PS + v
    by = defaultdict(list)
    for n_, d_, loads in nets:
        by[d_].append((n_, loads))
    merged = [(lst[0][0], d_, [l for _, ls in lst for l in ls]) for d_, lst in by.items()]
    v = list(out.values())
    hops.sort()
    model = dict(mode='lane', lanes=len(heads), buffers=len(bufs), head_pad_buffers=npad,
                 global_root_um=[round(x, 1) for x in g.xy(gc)], model_insertion_ps=[round(min(v), 1), round(max(v), 1)],
                 neighbour_hop_ps=dict(median=round(hops[len(hops) // 2], 1), max=round(hops[-1], 1)) if hops else None,
                 grid_um=GRID, span_um=SPAN, max_run_over_blocks_um=MAX_RUN, pad_ps_model=PAD_PS,
                 free_cells_frac=round(1 - sum(g.blk) / len(g.blk), 4))
    return dict(buffers=bufs, nets=merged, model=model)
