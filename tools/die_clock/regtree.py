#!/usr/bin/env python3
"""DIE-CLOCK regional clock tree topology (Claude DIE-CLOCK 2026-10-16), shared by S81 / Qwen / HBM die flows.

Why (diagnosis of the 10-16 S81 pilots, el1016-die-clock.log): the earlier die trees were balanced only in a MODEL
(H-DIE die_clock_tree stage_ps + fixed 20 ps pads).  A full-die H-tree for a 7 x 8 mm sink box gave 14.8 ns model /
30-34 ns measured insertion with 1,283 pads and 57 slew-violating 1-mm runs; the graph tree is unbalanced by
construction.  Error per stage x 100 stages = ns of spread.

Method here:
  1. REGIONS: one tree per clock region (a PLL domain's synchronous hub, one field column, the meso cfifo trunk);
     the tree is bounded by its own sinks, never routed through the die centre.
  2. LEAVES: sinks clustered by (instance master, LEAF_UM cell), <= LEAF_MAX pins, one BUFx24 leaf at the nearest free
     cell; pins of one leaf share one in-arc insertion target.
  3. TOPOLOGY: bottom-up zero-skew merge (DME-like) of leaf subtrees, paired by recursive median bisection; the merge
     point is chosen ON THE ROUTED obstacle-aware path between the two child roots where the model delays meet, so
     balance comes from geometry (wire), not from pads; pads only where one child is slower than the whole path.
  4. MEASURED TRIM (build.py): propagated STA -> per-leaf deficit to the region target (arrival + in-arc insertion
     R of the leaf's master pin) -> real pad buffers at the leaf input -> re-measure; iterate.  The model only seeds.
Refs: ('port', name) | ('buf', name) | ('pin', 'inst/pin').
"""
from collections import defaultdict
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hbm_die_v15'))
import die_clock_tree as dct  # noqa: E402  Grid, route, stage_ps (H-DIE, measured-calibrated stage model)

GRID, SPAN, MAX_RUN = dct.GRID, dct.SPAN, dct.MAX_RUN
BUF, PAD = 'BUFx24_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R'
LEAF_UM, LEAF_MAX = 60.0, 12
PAD_PS = 20.0     # seed only; build.py measures the real per-pad delay in context
# QW-DIECLK3 10-19 SAFE TREE (spec "safe_tree": true; Qwen dv2f19g2 root cause): the legacy plan let a clock edge run up
# to MAX_RUN = 400 um over hard blocks (1200 um on retry) with the repeater only at the last free cell, and a leaf sit at
# the nearest free cell up to 4 mm from its pins, so leaf nets n_dc_r*_L* ran 1-2.5 mm unbuffered over CB16 columns
# (281 > 1 mm, <= 9.8 ns, all M4 GRT overflow, 29-34 ns region insertion).  Safe mode: every unbuffered clock segment
# <= SEG_MAX (repeater target SPAN, forced at the last free cell before SEG_MAX), runs over blocks <= SAFE_RUNS (short
# hops over relay / rst_rep cells only; a CB16 column is routed AROUND through the gaps and channels), every leaf within
# LEAF_REACH of its farthest pin; anything that cannot meet that is a recorded violation (build.py fails closed).
SAFE = False
SEG_MAX = 220.0          # um, max unbuffered clock wire between two clock cells (plan target SPAN = 200)
SAFE_RUNS = (40.0, 100.0, 200.0)   # um over blocks, tried in order; never more (a block wider than 200 um is avoided)
LEAF_REACH = 160.0       # um, leaf buffer -> farthest pin of its cluster (cluster cell 60 um)
REACH_LIMIT = 405.0      # um, owner reach rule: no single unbuffered net longer (clock_reach_check.py)


def stage_ps(L):
    return dct.stage_ps(L)


def wire_ps(L):
    """model delay of L um of buffered clock wire (repeater every SPAN) incl. the end stage."""
    if L <= SPAN:
        return stage_ps(max(L, 10.0))
    return stage_ps(SPAN) * L / SPAN


def cluster(sinks, leaf_um=LEAF_UM, leaf_max=LEAF_MAX):
    """sinks [(pin, master, x, y, key)] -> [[sink, ...]] leaves; key = trim class (e.g. master/pin)."""
    cells = defaultdict(list)
    for s in sinks:
        cells[(s[4], int(s[2] // leaf_um), int(s[3] // leaf_um))].append(s)
    leaves = []
    for k in sorted(cells):
        pts = sorted(cells[k], key=lambda s: (s[2], s[3], s[0]))
        n = math.ceil(len(pts) / leaf_max)
        for i in range(n):
            leaves.append(pts[i * len(pts) // n:(i + 1) * len(pts) // n])
    return leaves


class Builder:
    def __init__(self, grid, prefix, r_of=None, pads=True):
        self.g, self.prefix = grid, prefix
        # pads=False (QW-DIECLK 10-19 forwarded regional spine): geometric merge only, never a pad buffer; the
        # regions it feeds are mesochronous (every crossing landed), so no arrival is balanced across them
        self.pads = pads
        # r_of(key) -> the leaf's in-arc insertion R (TT): the merge balances FLOP arrival (pin + R), so the tree
        # delivers each pin at phi - R by construction instead of leaving the whole R spread to measured trim pads
        self.r_of = r_of or (lambda k: 0.0)
        self.bufs, self.nets, self.parent = [], [], {}
        self.cnt = defaultdict(int)
        self.leaves = {}          # leaf buf -> dict(pins, key, cell)
        self.safe = SAFE
        self.violations = []      # safe mode: [dict(kind, ...)] edges / leaves that cannot meet SEG_MAX / LEAF_REACH
        self.run_escalations = 0  # safe mode: routes that needed more than SAFE_RUNS[0] over blocks

    def newbuf(self, tag, c, cell=BUF):
        self.cnt[tag] += 1
        n = f'{self.prefix}_{tag}{self.cnt[tag]}'
        x, y = self.g.xy(c)
        self.bufs.append([n, cell, x, y])
        return n

    def route(self, a, b):
        """legacy: dct route (<= MAX_RUN over blocks, 3 x on retry).  safe: <= SAFE_RUNS[i] over blocks, else violation."""
        if not self.safe:
            return self.g.route(a, b)
        for i, r in enumerate(SAFE_RUNS):
            try:
                p = self.g._route(a, b, r)
                self.run_escalations += i > 0
                return p
            except SystemExit:
                continue
        self.violations.append(dict(kind='no_route_within_safe_run', a=list(self.g.xy(a)), b=list(self.g.xy(b)),
                                    max_run_um=SAFE_RUNS[-1]))
        return self.g.route(a, b)

    def plan_safe(self, path):
        """SAFE: repeater at the first free cell >= SPAN from the last clock cell, forced at the last free cell before
        the segment would exceed SEG_MAX; every segment (incl. the last, into the end buffer) <= SEG_MAX."""
        g = self.g
        reps, ks, d, rep_k, last_free = [], [], 0.0, 0, None
        n = len(path) - 1
        for k in range(1, n):
            if g.free(path[k]):
                last_free = k
                if (k - rep_k) * GRID >= SPAN:
                    reps.append(path[k]); ks.append(k); d += stage_ps((k - rep_k) * GRID); rep_k, last_free = k, None
                    continue
            if (k + 1 - rep_k) * GRID > SEG_MAX:
                if last_free is None:
                    continue          # the run over a block is longer than SEG_MAX: recorded below
                reps.append(path[last_free]); ks.append(last_free); d += stage_ps((last_free - rep_k) * GRID)
                rep_k, last_free = last_free, None
        prev = 0
        for k in ks + [n]:
            if (k - prev) * GRID > SEG_MAX + 1e-6:
                self.violations.append(dict(kind='unbuffered_clock_segment', um=(k - prev) * GRID,
                                            a=list(g.xy(path[prev])), b=list(g.xy(path[k]))))
            prev = k
        d += stage_ps((n - rep_k) * GRID)
        return reps, d

    def plan(self, path):
        """repeater cells along a routed path (cells) and model delay (to the end buffer input)."""
        if self.safe:
            return self.plan_safe(path)
        g = self.g
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

    def chain(self, src, path, tag):
        """repeaters along path from driver ref src; returns (last driver ref, model delay)."""
        reps, d = self.plan(path)
        drv = src
        for c in reps:
            b = self.newbuf(tag, c)
            self.nets.append([f'n_{b}', drv, [('buf', b)]])
            self.parent[b] = drv[1]
            drv = ('buf', b)
        return drv, d

    def leaf(self, pts):
        cx = sum(s[2] for s in pts) / len(pts); cy = sum(s[3] for s in pts) / len(pts)
        c = self.g.nearest_free(cx, cy)
        b = self.newbuf('L', c)
        self.nets.append([f'n_{b}_o', ('buf', b), [('pin', s[0]) for s in pts]])
        x, y = self.g.xy(c)
        wire = max(abs(s[2] - x) + abs(s[3] - y) for s in pts)
        if self.safe and wire > LEAF_REACH:
            self.violations.append(dict(kind='leaf_beyond_reach', leaf=b, um=round(wire, 1), at=[x, y],
                                        pins=[s[0] for s in pts][:4]))
        self.leaves[b] = dict(pins=[s[0] for s in pts], key=pts[0][4], cell=c)
        for s in pts:
            self.parent[s[0]] = b
        # subtree record: (root buffer, root cell, model delay from root buffer INPUT to its sinks)
        return dict(buf=b, cell=c, d=stage_ps(min(wire, SPAN)) * max(1.0, wire / SPAN) + self.r_of(pts[0][4]), n=1)

    def merge(self, A, B):
        """zero-skew merge point on the routed path A.cell -> B.cell; new BUF there drives both chains.
        The meeting point uses the closed-form buffered-wire model w(L) (O(path)); the chains are then planned exactly."""
        g = self.g
        path = self.route(A['cell'], B['cell'])
        n = len(path) - 1
        best = None
        for k in range(len(path)):
            if not g.free(path[k]):
                continue
            da = A['d'] + wire_ps(k * GRID)
            db = B['d'] + wire_ps((n - k) * GRID)
            sk = abs(da - db)
            if best is None or sk < best[0]:
                best = (sk, k, da, db)
        sk, k, da, db = best
        c = path[k]
        m = self.newbuf('B', c)
        out = dict(buf=m, cell=c, n=A['n'] + B['n'])
        for child, sub, dd in ((A, path[k::-1], da), (B, path[k:], db)):
            npad = int(round((max(da, db) - dd) / PAD_PS)) if self.pads else 0
            if len(sub) > 1:
                drv, _ = self.chain(('buf', m), sub, 'R')
            else:
                drv = ('buf', m)
            for _ in range(npad):
                p = self.newbuf('P', child['cell'], PAD)
                self.nets.append([f'n_{p}', drv, [('buf', p)]])
                self.parent[p] = drv[1]
                drv = ('buf', p)
            self.nets.append([f'n_{child["buf"]}_i', drv, [('buf', child['buf'])]])
            self.parent[child['buf']] = drv[1]
        out['d'] = max(da, db) + stage_ps(10.0)
        return out

    def subtree(self, leaves):
        if len(leaves) == 1:
            return self.leaf(leaves[0])
        cen = [(sum(s[2] for s in L) / len(L), sum(s[3] for s in L) / len(L)) for L in leaves]
        xs = [c[0] for c in cen]; ys = [c[1] for c in cen]
        ax = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
        order = sorted(range(len(leaves)), key=lambda i: (cen[i][ax], cen[i][1 - ax]))
        h = len(order) // 2
        A = self.subtree([leaves[i] for i in order[:h]])
        B = self.subtree([leaves[i] for i in order[h:]])
        return self.merge(A, B)

    def build(self, root_pin, root_xy, leaves):
        top = self.subtree(leaves)
        rc = self.g.nearest_free(*root_xy)
        path = self.route(rc, top['cell'])
        drv, d = self.chain(('pin', root_pin), path, 'T') if len(path) > 1 else (('pin', root_pin), 0.0)
        self.nets.append([f'n_{top["buf"]}_i', drv, [('buf', top['buf'])]])
        self.parent[top['buf']] = drv[1]
        # one net per driver
        by = {}
        for n, d_, loads in self.nets:
            if d_ in by:
                by[d_][2].extend(loads)
            else:
                by[d_] = [n, d_, list(loads)]
        self.nets = list(by.values())
        r = dict(top=top['buf'], model_insertion_ps=round(d + top['d'], 1), leaves=len(leaves), buffers=len(self.bufs),
                 pads=sum(1 for b in self.bufs if b[1] == PAD))
        if self.safe:
            r.update(safe=True, violations=len(self.violations), run_escalations=self.run_escalations)
        return r


def spine_members(trees, built, root_buffer, spine):
    """SPINE (landed-regions standard, GEN16 10-19): the region trees fed by ONE forwarded clock spine from the generator.
    trees: expanded tree specs; built: names of trees actually built; root_buffer: root pin -> root buffer name.
    A member has a local_root (regional clock entry), a root buffer, and the spine's period (or is listed by name).
    Returns [(tree spec, root buffer)].  A listed tree that cannot join raises (fail closed)."""
    per = float(spine.get('period', 833.333333))
    sel = spine.get('trees')
    out = []
    for t in trees:
        if t['name'] not in built:
            continue
        listed = isinstance(sel, list) and t['name'] in sel
        if isinstance(sel, list) and not listed:
            continue
        if not isinstance(sel, list) and abs(float(t.get('period', 833.333333)) - per) > 1e-3:
            continue
        rb = root_buffer.get(t['root'])
        if not t.get('local_root') or not rb:
            if listed:
                raise ValueError(f"spine tree {t['name']} has no local_root / root buffer")
            continue
        out.append((t, rb))
    return out


def spine_leaves(members, cell_xy):
    """one spine leaf per regional entry: sink = the entry's root buffer input, key = the tree name (so its region
    tree's model insertion is compensated by the merge: neighbour regions meet at their FLOPS, not at their entries)."""
    return [[(f'{rb}/A', BUF, cell_xy[rb][0], cell_xy[rb][1], t['name'])] for t, rb in members]
