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
    def __init__(self, grid, prefix):
        self.g, self.prefix = grid, prefix
        self.bufs, self.nets, self.parent = [], [], {}
        self.cnt = defaultdict(int)
        self.leaves = {}          # leaf buf -> dict(pins, key, cell)

    def newbuf(self, tag, c, cell=BUF):
        self.cnt[tag] += 1
        n = f'{self.prefix}_{tag}{self.cnt[tag]}'
        x, y = self.g.xy(c)
        self.bufs.append([n, cell, x, y])
        return n

    def plan(self, path):
        """repeater cells along a routed path (cells) and model delay (to the end buffer input)."""
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
        self.leaves[b] = dict(pins=[s[0] for s in pts], key=pts[0][4], cell=c)
        for s in pts:
            self.parent[s[0]] = b
        # subtree record: (root buffer, root cell, model delay from root buffer INPUT to its sinks)
        return dict(buf=b, cell=c, d=stage_ps(min(wire, SPAN)) * max(1.0, wire / SPAN), n=1)

    def merge(self, A, B):
        """zero-skew merge point on the routed path A.cell -> B.cell; new BUF there drives both chains.
        The meeting point uses the closed-form buffered-wire model w(L) (O(path)); the chains are then planned exactly."""
        g = self.g
        path = g.route(A['cell'], B['cell'])
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
            npad = int(round((max(da, db) - dd) / PAD_PS))
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
        path = self.g.route(rc, top['cell'])
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
        return dict(top=top['buf'], model_insertion_ps=round(d + top['d'], 1), leaves=len(leaves), buffers=len(self.bufs),
                    pads=sum(1 for b in self.bufs if b[1] == PAD))
