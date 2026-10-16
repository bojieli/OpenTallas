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

GRID = 20.0          # um
SPAN = 420.0         # max wire between repeaters (um): M8 r 8.45 ohm/um c 0.104 fF/um -> 0.38RC ~ 64 ps at 420 um
MAX_RUN = 400.0      # max length of a route segment over blocked area (repeater cannot sit there)
BUF = 'BUFx24_ASAP7_75t_R'
PAD = 'BUFx12f_ASAP7_75t_R'
STAGE_PS = 70.0      # model: one repeater stage incl. 420 um M8 (TT); used only to pad, STA measures the result


class Grid:
    def __init__(self, W, H, obstacles, margin=4.0):
        self.W, self.H = W, H
        self.nx, self.ny = int(W // GRID), int(H // GRID)
        self.blk = bytearray(self.nx * self.ny)
        for (x0, y0, x1, y1) in obstacles:
            i0 = max(0, int((x0 - margin) // GRID)); i1 = min(self.nx - 1, int((x1 + margin) // GRID))
            j0 = max(0, int((y0 - margin) // GRID)); j1 = min(self.ny - 1, int((y1 + margin) // GRID))
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
        prev = {}
        pq = [(abs(a[0] - b[0]) + abs(a[1] - b[1]), 0, a, 0)]
        while pq:
            f, g, c, run = heapq.heappop(pq)
            if c == b:
                path = [c]; s = (c, run)
                while s in prev:
                    s = prev[s]; path.append(s[0])
                return path[::-1]
            if dist.get((c, run), 1 << 60) < g:
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
                    dist[s] = ng; prev[s] = (c, run)
                    heapq.heappush(pq, (ng + abs(n[0] - b[0]) + abs(n[1] - b[1]), ng, n, nr))
        raise SystemExit(f'no clock route {a} -> {b}')


def stage_ps(L):
    """model delay of one BUFx24 stage driving L um of M8 into the next repeater (calibrated on the first explicit run:
    ~176 ps per ~420 um stage at TT); used only to choose the root and to pre-balance, STA measures the result."""
    return 25.0 + 8.6e-4 * L * L


PAD_PS = 20.0


def build(W, H, obstacles, root_xy, sinks, quadrant_of, leaf_pads=None, quad_pads=None, root_search_um=3000.0):
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
