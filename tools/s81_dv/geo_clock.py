#!/usr/bin/env python3
"""S81.CLK (STW-S81-DIE-CLK 10-21): GEOMETRIC regional clock roots for the S81 die GEN.

Replaces the LOGICAL cluster roots ck_cl0N..ck_cl7S / ck_south<c> / ck_void<c> / ck_edge<c> (plan 'group' of the
nearest block: one root spread over up to 20.7 x 23.9 mm, G9d) with roots of a fixed geometric grid:

  * grid       nx x ny equal cells over the die outline, origin = die origin (the floorplan's coordinate frame);
               region g<i>_<j> = cell column i (x), row j (y); top port ck_g<i>_<j>.  Cell target CELL_UM =
               (3000, 4334) um -> 33 x 26 mm die: 11 x 6 cells of 3000 x 4333 um.  The rows are tall enough for the
               die's 3.8-4.2 mm column blocks (svc_rs 3802, SerDes 3845, bk_sel 4190 um) to sit whole in one region,
               the columns narrow enough for the spread model below.
  * sizing     die_clock_check's wire model (tools/die_clock_check.wire_ps = H-DIE stage_ps 25 + 8.6e-4 L^2 per
               420-um BUFx24/M8 stage) of a region tree fed at the cell centre: the root -> farthest-sink wire is
               cw/2 + ch/2 = 3667 um -> modelled insertion wire_ps(3667) = 1543 ps.  Two sinks of one region differ at
               most by their NON-COMMON path (<= the insertion); at a TT/FF de-tracking of TRACK_DERATE = 5 % of that
               path the in-region spread bound is 77.1 ps <= the owner's 80 ps (rule 10-20: 80 ps WITHIN a region).
               10 x 6 (3300 x 4333) models 80.3 ps and 8 x 6 89 ps > 80; 9 x 7 (77.6 ps) splits the 3.8 mm column
               blocks into own roots (G9 plan: 215 vs 148 cross-root 0-stage pairs, legacy logical roots 141).  The
               80 ps is then MEASURED by die STA + die_clock_check per region (the model only sizes the cell).
  * blocks     a block whose own clock comes from the bind table (frames: ck_frame_<f>_r{0,1,2}; LEP slices:
               ck_ep_*; masters with a fixed clock_port, e.g. the PHY ck_hbm) keeps it; its grid region is the cell of
               its centre (used only by the region-root fallbacks).  Every other block takes the root of the cell
               containing its centre and BELONGS WHOLLY to that region (regions are snapped to whole blocks: a block
               is never split between two roots).  A block larger than a cell (w > cw or h > ch: the 1.25 x 6.7 mm
               slices, the 3.8 mm SerDes / svc_rs columns, bk_sel) gets ONE root of its own, ck_b_<block>, at its clock
               pin (its sinks: the block, its landings and gate-calendar stations); recorded as `own_root`.
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

import math

CELL_UM = (3000.0, 4334.0)   # target cell (x, y) edge (see grid / sizing above)
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
    def __init__(self, W, H, cell=CELL_UM):
        cx, cy = (cell, cell) if isinstance(cell, (int, float)) else cell
        if W <= 0 or H <= 0 or cx <= 0 or cy <= 0:
            raise ValueError(f'geo_clock: bad grid {W} x {H} / {cell}')
        self.W, self.H = float(W), float(H)
        self.nx, self.ny = int(math.ceil(W / cx - 1e-9)), int(math.ceil(H / cy - 1e-9))
        self.cw, self.ch = self.W / self.nx, self.H / self.ny

    @classmethod
    def from_spec(cls, spec):
        """the grid a bind recorded (bind_case.json clock_regions.grid)"""
        g = cls.__new__(cls)
        g.W, g.H = (float(v) for v in spec['die_um'])
        g.nx, g.ny = int(spec['nx']), int(spec['ny'])
        g.cw, g.ch = g.W / g.nx, g.H / g.ny
        return g

    def ij(self, x, y):
        return (min(max(int(x // self.cw), 0), self.nx - 1), min(max(int(y // self.ch), 0), self.ny - 1))

    def region(self, x, y):
        i, j = self.ij(x, y)
        return f'g{i}_{j}'

    def box(self, region):
        i, j = (int(t) for t in region[1:].split('_'))
        return (i * self.cw, j * self.ch, (i + 1) * self.cw, (j + 1) * self.ch)

    def spec(self):
        return dict(nx=self.nx, ny=self.ny, cell_um=[round(self.cw, 3), round(self.ch, 3)], die_um=[self.W, self.H],
                    model_spread_ps=round(region_spread_ps(self.cw, self.ch), 1), budget_ps=SPREAD_PS,
                    model='TRACK_DERATE x die_clock_check.wire_ps(cw/2 + ch/2)')


def own_clock(table, block):
    """True when the bind table already gives this block its own clock (frames, LEP slices, fixed clock_port)."""
    m = table['masters'][block['master']]
    return block['name'] in table.get('instance_clock_ports', {}) or bool(m.get('clock_port'))


def block_regions(blocks, grid, table):
    """{block: region}, {block: info}.  Region = grid cell of the centre; an oversize block without its own table
    clock gets its own root region b_<block>."""
    reg, info = {}, {}
    for b in blocks:
        cx, cy = b['x'] + b['w'] / 2.0, b['y'] + b['h'] / 2.0
        cell = grid.region(cx, cy)
        if own_clock(table, b):
            reg[b['name']] = cell
            info[b['name']] = dict(kind='table_clock', cell=cell)
        elif b['w'] > grid.cw + 1e-6 or b['h'] > grid.ch + 1e-6:
            reg[b['name']] = f'b_{b["name"]}'
            info[b['name']] = dict(kind='own_root', cell=cell, bbox=[b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']])
        else:
            reg[b['name']] = cell
            info[b['name']] = dict(kind='grid', cell=cell)
    return reg, info


def extents(grid, blocks, reg):
    """{region: (x0, y0, x1, y1)}: grid cells grown by the whole blocks they own; own-root regions = their block."""
    ext = {}
    for b in blocks:
        r = reg[b['name']]
        bb = (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h'])
        if r.startswith('b_'):
            ext[r] = bb
        elif r.startswith('g'):
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
