#!/usr/bin/env python3
"""S81.CLK (STW-S81-DIE-CLK 10-21): GEOMETRIC regional clock roots for the S81 die GEN.

Replaces the LOGICAL cluster roots ck_cl0N..ck_cl7S / ck_south<c> / ck_void<c> / ck_edge<c> (plan 'group' of the
nearest block: one root spread over up to 20.7 x 23.9 mm, G9d) with roots of a fixed geometric grid:

  * grid       nx x ny cells over the die outline, origin = die origin (the floorplan's coordinate frame); region
               g<i>_<j> = cell column i (x), row j (y); top port ck_g<i>_<j>.  Cells <= CELL_UM = (3000, 4334) um,
               edges FLOORPLAN-ALIGNED (Grid.aligned, below); the uniform reference grid is 11 x 6 cells of
               3000 x 4333 um on the 33 x 26 mm die.  Tall rows keep the die's 3.8-4.2 mm column blocks (svc_rs 3802,
               SerDes 3845, bk_sel 4190 um) inside one row where an edge does not cut them.
  * sizing     die_clock_check's wire model (tools/die_clock_check.wire_ps = H-DIE stage_ps 25 + 8.6e-4 L^2 per
               420-um BUFx24/M8 stage) of a region tree fed at the cell centre: the root -> farthest-sink wire is
               cw/2 + ch/2 <= 3667 um -> modelled insertion wire_ps(3667) = 1543 ps.  Two sinks of one region differ at
               most by their NON-COMMON path (<= the insertion); at a TT/FF de-tracking of TRACK_DERATE = 5 % of that
               path the in-region spread bound is 77.1 ps <= the owner's 80 ps (rule 10-20: 80 ps WITHIN a region).
               3300 x 4333 cells model 80.3 ps, 4125 x 4333 89 ps > 80.  The 80 ps is then MEASURED by die STA +
               die_clock_check per region (the model only sizes the cell).
  * blocks     a block whose own clock comes from the bind table (frames: ck_frame_<f>_r{0,1,2}; LEP slices:
               ck_ep_*; masters with a fixed clock_port, e.g. the PHY ck_hbm) keeps it; the region-root fallbacks of
               dv_bind (gate / landing calendar stations beside the block) use its main instance clock root (frames,
               LEP slices) or, for a fixed clock_port master, the cell of its centre.  Every other block takes the root of the cell
               containing its centre when it lies WHOLLY inside that cell.  A block larger than the cell target (the
               1.25 x 6.7 mm slices) or cut by a region edge gets ONE root of its own, ck_b_<block>, at its clock pin
               (its sinks: the block, its landings and gate-calendar stations, all on its own outline); recorded as
               `own_root` with the reason.  The edges are FLOORPLAN-ALIGNED (Grid.aligned): per axis the cuts (cells
               <= the target) that cut the fewest blocks (weight BLOCK_CUT_W) and 0-stage neighbour pairs (weight 1).
  * reset      every reset station (street cell / lane companion) is clocked by the root of the cell holding its
               point.  A reset-tree edge whose two stations are in different regions is a RESET RELEASE CROSSING:
               the child gets ONE EXTRA registered stage <child>_xk (dsfd_rly_1 on the RECEIVING region's root,
               beside the child, async assert / sync release) in front of it, so the release is re-registered twice
               in the receiving region before it propagates (two-flop landing of a monotonic 1-bit level).  The
               release depth of every node below a crossing is +1 per crossing (dv_bind reset calendar: depth, block
               release depth, gate / frame-epoch calendars all read that depth, so they stay exact).
  * crossings  reset-tree crossings (above) and lanes landed by a ring (dsfd_dvland_* tile or the frame's crs4)
               are LANDED pairs in case/landed.json (die_clock_check --landed).  0-stage block pairs (abutted
               neighbours, e.g. slice xring, svc / idx neighbours) are NOT claimed landed: they stay judged as
               neighbour-matched boundaries (80 ps TT+FF) and are counted as `unlanded_neighbour_pairs`.
  * gate       a non-frame region root whose PLACED sink bbox exceeds its extent (cell U member blocks; own-root
               block bbox) + reach (405 um) FAILS the GEN (root_gate).
"""
from __future__ import annotations

import bisect
import math

CELL_UM = (3000.0, 4334.0)   # target cell (x, y) edge (see grid / sizing above)
BLOCK_CUT_W = 10          # a cut block (region tree stretched over two cells) outweighs a cut 0-stage neighbour pair
TRACK_DERATE = 0.05       # TT/FF de-tracking of a non-common clock path (sizing assumption; STA measures the result)
SPREAD_PS = 80.0          # owner 10-20: spread budget WITHIN a region
REACH_UM = 405.0          # owner reach (registered hop)
STAGE_UM = 420.0          # die_clock_check SPAN


def stage_ps(L):
    """H-DIE stage model (tools/hbm_die_v15/die_clock_tree.stage_ps, 9bcff2c0b): one BUFx24 stage over L um of M8."""
    return 25.0 + 8.6e-4 * L * L


def wire_ps(L):
    """tools/die_clock_check.wire_ps: buffered clock wire of L um."""
    return stage_ps(min(L, STAGE_UM)) * max(1.0, L / STAGE_UM)


def region_spread_ps(cw, ch, derate=TRACK_DERATE):
    """modelled in-region spread bound of a centre-fed region tree of a cw x ch cell (see module doc)"""
    return derate * wire_ps(cw / 2.0 + ch / 2.0)


class Grid:
    """Regions = the cells between edges xs[0] = 0 < ... < xs[-1] = W and ys likewise (g<i>_<j>: column i, row j)."""

    def __init__(self, W, H, cell=CELL_UM, xs=None, ys=None):
        cx, cy = (cell, cell) if isinstance(cell, (int, float)) else cell
        if W <= 0 or H <= 0 or cx <= 0 or cy <= 0:
            raise ValueError(f'geo_clock: bad grid {W} x {H} / {cell}')
        self.W, self.H = float(W), float(H)
        self.maxc = (float(cx), float(cy))          # cell target: blocks larger than it get their own root
        if xs is None:
            n = int(math.ceil(W / cx - 1e-9)); xs = [self.W * k / n for k in range(n + 1)]
        if ys is None:
            n = int(math.ceil(H / cy - 1e-9)); ys = [self.H * k / n for k in range(n + 1)]
        self.xs, self.ys = [float(v) for v in xs], [float(v) for v in ys]
        if (self.xs[0], self.ys[0]) != (0.0, 0.0) or abs(self.xs[-1] - self.W) > 1e-6 or abs(self.ys[-1] - self.H) > 1e-6 \
                or any(b <= a for a, b in zip(self.xs, self.xs[1:])) or any(b <= a for a, b in zip(self.ys, self.ys[1:])):
            raise ValueError(f'geo_clock: bad grid edges {self.xs} / {self.ys}')
        self.nx, self.ny = len(self.xs) - 1, len(self.ys) - 1
        self.cw = max(b - a for a, b in zip(self.xs, self.xs[1:]))     # largest cell (the oversize test / model)
        self.ch = max(b - a for a, b in zip(self.ys, self.ys[1:]))

    @classmethod
    def aligned(cls, W, H, blocks, table, cell=CELL_UM, step=50.0, pairs=()):
        """Floorplan-aligned grid: per axis, the cut positions (cells <= cell) that cut the fewest (a) whole blocks
        that take a region root (no table clock, not oversize: a cut block stretches its region's tree over both cells,
        its landings / calendar stations sit on its whole outline) and (b) 0-stage block pairs (`pairs`: abutted
        neighbours without a landing ring, which a cut turns into an unlanded cross-root pair), then the fewest cells."""
        cx, cy = (cell, cell) if isinstance(cell, (int, float)) else cell
        grid_b = {b['name']: b for b in blocks if not own_clock(table, b) and b['w'] <= cx + 1e-6 and b['h'] <= cy + 1e-6}
        cen = {n: (b['x'] + b['w'] / 2.0, b['y'] + b['h'] / 2.0) for n, b in grid_b.items()}
        pr = [(cen[a], cen[b]) for a, b in pairs if a in cen and b in cen and a != b]
        xs = _cuts(float(W), [(b['x'], b['x'] + b['w'], BLOCK_CUT_W) for b in grid_b.values()] +
                   [(min(p[0], q[0]), max(p[0], q[0]), 1) for p, q in pr], cx, step)
        ys = _cuts(float(H), [(b['y'], b['y'] + b['h'], BLOCK_CUT_W) for b in grid_b.values()] +
                   [(min(p[1], q[1]), max(p[1], q[1]), 1) for p, q in pr], cy, step)
        return cls(W, H, (cx, cy), xs, ys)

    @classmethod
    def from_spec(cls, spec):
        """the grid a bind recorded (bind_case.json clock_regions.grid)"""
        W, H = (float(v) for v in spec['die_um'])
        cell = tuple(spec.get('cell_target_um', CELL_UM))
        if 'xs' in spec:
            return cls(W, H, cell, xs=spec['xs'], ys=spec['ys'])
        return cls(W, H, cell, xs=[W * k / spec['nx'] for k in range(spec['nx'] + 1)], ys=[H * k / spec['ny'] for k in range(spec['ny'] + 1)])

    def ij(self, x, y):
        return (min(max(bisect.bisect_right(self.xs, x) - 1, 0), self.nx - 1),
                min(max(bisect.bisect_right(self.ys, y) - 1, 0), self.ny - 1))

    def region(self, x, y):
        i, j = self.ij(x, y)
        return f'g{i}_{j}'

    def box(self, region):
        i, j = (int(t) for t in region[1:].split('_'))
        return (self.xs[i], self.ys[j], self.xs[i + 1], self.ys[j + 1])

    def spec(self):
        return dict(nx=self.nx, ny=self.ny, xs=[round(v, 3) for v in self.xs], ys=[round(v, 3) for v in self.ys],
                    max_cell_um=[round(self.cw, 3), round(self.ch, 3)], cell_target_um=list(self.maxc), die_um=[self.W, self.H],
                    model_spread_ps=round(region_spread_ps(self.cw, self.ch), 1), budget_ps=SPREAD_PS,
                    model='TRACK_DERATE x die_clock_check.wire_ps(cw/2 + ch/2) of the largest cell')


def _cuts(L, intervals, maxc, step):
    """edges 0 < ... < L, gaps <= maxc, minimising (weighted intervals strictly cut, number of cells); intervals =
    (lo, hi, weight); candidates = just outside
    every block edge + a `step` lattice"""
    cand = {0.0, L} | {float(k * step) for k in range(1, int(L // step) + 1) if k * step < L}
    for lo, hi, _ in intervals:
        cand |= {v for v in (lo - 1.0, hi + 1.0) if 0.0 < v < L}
    cand = sorted(cand)
    cost = [sum(w for lo, hi, w in intervals if lo < c < hi) for c in cand]
    best = [None] * len(cand)
    best[0] = (0, 0, None)
    lo_k = 0
    for k in range(1, len(cand)):
        while cand[k] - cand[lo_k] > maxc + 1e-6:
            lo_k += 1
        opts = [(best[p][0] + (cost[k] if k < len(cand) - 1 else 0), best[p][1] + 1, p) for p in range(lo_k, k) if best[p]]
        best[k] = min(opts) if opts else None
    if best[-1] is None:
        raise ValueError(f'geo_clock: no cut sequence for {L} at cell {maxc}')
    out, k = [], len(cand) - 1
    while k is not None:
        out.append(cand[k]); k = best[k][2]
    return out[::-1]


def own_clock(table, block):
    """True when the bind table already gives this block its own clock (frames, LEP slices, fixed clock_port)."""
    m = table['masters'][block['master']]
    return block['name'] in table.get('instance_clock_ports', {}) or bool(m.get('clock_port'))


def inside(box, b, tol=1.0):
    return box[0] - tol <= b['x'] and b['x'] + b['w'] <= box[2] + tol and box[1] - tol <= b['y'] and b['y'] + b['h'] <= box[3] + tol


def block_regions(blocks, grid, table):
    """{block: region}, {block: info}.  Region = grid cell of the centre; a block without its own table clock that is
    larger than the cell target or cut by a region edge gets its own root region b_<block> (its tree spans only its
    own outline, <= the cell target or its own size), so every grid region's tree stays inside its cell."""
    reg, info = {}, {}
    for b in blocks:
        cx, cy = b['x'] + b['w'] / 2.0, b['y'] + b['h'] / 2.0
        cell = grid.region(cx, cy)
        icp = table.get('instance_clock_ports', {}).get(b['name'])
        main = icp.get(table['masters'][b['master']]['clk']) if icp else None
        if main and main.startswith('ck_'):
            # frames / LEP slices: the region-root fallbacks (gate / landing calendar stations beside the block) take
            # the block's own main clock root, the root of the gate / landing they feed
            reg[b['name']] = main[3:]
            info[b['name']] = dict(kind='table_clock', cell=cell, root=main)
        elif own_clock(table, b):
            reg[b['name']] = cell
            info[b['name']] = dict(kind='table_clock', cell=cell)
        elif b['w'] > grid.maxc[0] + 1e-6 or b['h'] > grid.maxc[1] + 1e-6 or not inside(grid.box(cell), b):
            reg[b['name']] = f'b_{b["name"]}'
            info[b['name']] = dict(kind='own_root', cell=cell, bbox=[b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']],
                                   why='oversize' if b['w'] > grid.maxc[0] + 1e-6 or b['h'] > grid.maxc[1] + 1e-6
                                   else 'cut by a region edge')
        else:
            reg[b['name']] = cell
            info[b['name']] = dict(kind='grid', cell=cell)
    return reg, info


def extents(grid, blocks, reg, table_clocked=()):
    """{region: (x0, y0, x1, y1)}: grid cells grown by the whole blocks they own (blocks clocked by a table clock
    are not grown into the cell); own-root regions = their block."""
    own_clock_kind = {n: True for n in table_clocked}
    ext = {}
    for b in blocks:
        r = reg[b['name']]
        bb = (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h'])
        if r.startswith('b_'):
            ext[r] = bb
        elif r.startswith('g') and not own_clock_kind.get(b['name']):
            e = ext.get(r, grid.box(r))
            ext[r] = (min(e[0], bb[0]), min(e[1], bb[1]), max(e[2], bb[2]), max(e[3], bb[3]))
    for i in range(grid.nx):
        for j in range(grid.ny):
            ext.setdefault(f'g{i}_{j}', grid.box(f'g{i}_{j}'))
    return ext


def bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def root_gate(sinks, ext, reach=REACH_UM):
    """sinks: {region: [(inst, x, y)]} placed sink points of each non-frame root.  FAIL rows: a root whose sink bbox
    leaves its extent grown by `reach`, or a root with no extent (not a geometric / own-block root)."""
    rows, fails = {}, []
    for r, pts in sorted(sinks.items()):
        if not pts:
            continue
        bb = bbox([(x, y) for _, x, y in pts])
        e = ext.get(r)
        row = dict(sinks=len(pts), bbox=[round(v, 1) for v in bb], span_um=[round(bb[2] - bb[0], 1), round(bb[3] - bb[1], 1)])
        if e is None:
            row['verdict'] = 'FAIL'; row['why'] = 'not a geometric or own-block root'
        else:
            row['extent'] = [round(v, 1) for v in e]
            out = [(i, round(x, 1), round(y, 1)) for i, x, y in pts
                   if not (e[0] - reach <= x <= e[2] + reach and e[1] - reach <= y <= e[3] + reach)]
            row['verdict'] = 'FAIL' if out else 'PASS'
            if out:
                row['outside'] = len(out); row['first_outside'] = out[:5]
        if row['verdict'] == 'FAIL':
            fails.append(r)
        rows[r] = row
    return dict(verdict='FAIL' if fails else 'PASS', fails=fails, reach_um=reach, roots=rows,
                max_span_um=max((max(v['span_um']) for v in rows.values()), default=0.0))
