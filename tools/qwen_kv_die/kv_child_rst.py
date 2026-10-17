#!/usr/bin/env python3
"""KVPLAN 1815 (2026-10-16, COORDINATOR STANDARD items 1-2): REGIONAL REGISTERED RESET INSIDE EXPANDED FRAMES.

kv_die.py plans the HOST reset / boot trees between FRAMES; kv_expand.py then flattens a wires-only frame (head, engine
control, controller strip) into its closed leaves, and every leaf reset pin of one frame lands on ONE die net (no buffering
on the die top): kvs13j per-bit audit -- ctrl strip hrst 33-42 loads over 12.2 mm, head rst_n 86 loads over 1.1 mm.

With OT_KV_CHILD_RST=1 kv_expand.py calls plan() for every expanded frame instance and every reset die net (n_rst_* /
n_hboot*) that reaches its leaves: the frame's reset becomes a LOCAL REGISTERED TREE of qkd_rlys_1 stations (the closed
1-bit relay standard: one flop, no reset, one cycle a hop -- the reset trees' own hop) placed in the frame's free space
(never over a leaf), each leaf reset pin driven by a station <= LEAF_R um away (<= FAN loads a station), every
station-to-station / driver-to-station hop <= HOP um.  The added depth per leaf is recorded (expand.json reset_local) and
checked against the reset flush budget: reset release waits >= RELAY_FLUSH core cycles after the clock runs
(kv_relays / kv_die.RELAY_FLUSH), so die tree depth + local depth stays < RELAY_FLUSH (kv_die checks the die part).
Function is unchanged: a reset leaf sees the same reset value, released a fixed number of cycles later (static, recorded).
"""
import math
import os

import numpy as np

STN = 12.96                       # qkd_rlys_1 outline (um)
HALO = float(os.environ.get('OT_KV_CHILD_RST_HALO', '4.32'))      # keep-out around every leaf / station
HOP = float(os.environ.get('OT_KV_CHILD_RST_HOP', '360'))         # station <- driver / station hop (planning, < 0.9 x reach)
LEAF_R = float(os.environ.get('OT_KV_CHILD_RST_LEAF', '200'))     # station -> leaf reset pin
FAN = int(os.environ.get('OT_KV_CHILD_RST_FAN', '12'))            # leaf pins a station
SFAN = 4                                                           # child stations a station
STEP = 2.16                       # spot lattice (um): the die placer's row pitch


class Free:
    """occupancy bitmap of one frame: a spot (x, y) = an STN square whose halo box is free of leaves and stations"""

    def __init__(self, rect, obstacles):
        self.x0, self.y0, x1, y1 = rect
        self.nx = int((x1 - self.x0) // STEP) + 1
        self.ny = int((y1 - self.y0) // STEP) + 1
        self.occ = np.zeros((self.nx, self.ny), dtype=np.int32)
        for o in obstacles:
            self.block(o)
        self.k = int(math.ceil((STN + 2 * HALO) / STEP))

    def block(self, r):
        ax = max(0, int((r[0] - self.x0) // STEP))
        bx = min(self.nx, int(math.ceil((r[2] - self.x0) / STEP)) + 1)
        ay = max(0, int((r[1] - self.y0) // STEP))
        by = min(self.ny, int(math.ceil((r[3] - self.y0) / STEP)) + 1)
        if ax < bx and ay < by:
            self.occ[ax:bx, ay:by] = 1

    def spots(self):
        """(N, 2) array of free STN-square origins (halo included), lattice STEP"""
        c = np.pad(self.occ, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        k = self.k
        if self.nx < k or self.ny < k:
            return np.zeros((0, 2))
        s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
        ix, iy = np.nonzero(s == 0)
        # the halo box starts at the cell; the station origin sits HALO inside it
        return np.stack([self.x0 + ix * STEP + HALO, self.y0 + iy * STEP + HALO], 1)

    def take(self, x, y):
        self.block((x - HALO, y - HALO, x + STN + HALO, y + STN + HALO))


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def plan(name, frame_rect, leaves, loads, driver, clock_of):
    """name: station name prefix; frame_rect (x0, y0, x1, y1) die um; leaves: [(x0, y0, x1, y1)] leaf outlines;
    loads: [(key, (x, y))] leaf reset pin bits; driver: (x, y) of the die net's driver; clock_of(pt) -> clock ref.
    returns stations [dict(name, x, y, parent (None = die net), depth, ck)], assign {key: station name}"""
    fr = Free(frame_rect, leaves)
    cand = fr.spots()
    if not len(cand):
        raise ValueError(f'{name}: no free station spot in the frame')
    cen = cand + STN / 2

    def best_spot(pts, near=None, max_r=None, idx=None):
        """free spot minimising the max distance to pts (ties: nearest to `near`); idx = candidate subset"""
        P = np.array(pts)
        C = cen if idx is None else cen[idx]
        if not len(C):
            return None
        dd = np.abs(C[:, None, 0] - P[None, :, 0]) + np.abs(C[:, None, 1] - P[None, :, 1])
        worst = dd.max(1)
        if near is not None:
            worst = worst + 1e-3 * (np.abs(C[:, 0] - near[0]) + np.abs(C[:, 1] - near[1]))
        i = int(np.argmin(worst))
        if max_r is not None and dd[i].max() > max_r:
            return None
        return i if idx is None else int(idx[i])

    # 1. leaf clusters: greedy from the load farthest from the driver, <= FAN pins within LEAF_R of one free spot
    todo = sorted(loads, key=lambda kv: -_d(kv[1], driver))
    clusters = []
    while todo:
        seed = todo[0]
        near_ = np.nonzero(np.abs(cen[:, 0] - seed[1][0]) + np.abs(cen[:, 1] - seed[1][1]) <= LEAF_R)[0]
        cand_m = sorted(todo, key=lambda kv: _d(kv[1], seed[1]))
        grp = []
        for kv in cand_m:
            if len(grp) >= FAN:
                break
            if _d(kv[1], seed[1]) > 1.6 * LEAF_R:
                break
            trial = grp + [kv]
            if best_spot([p for _, p in trial], max_r=LEAF_R, idx=near_) is None:
                continue
            grp = trial
        far = False
        if not grp:
            # a pin inside / behind a frame that is not flattened (ASSUMED frames, hard macros): its station is the
            # nearest free spot within one hop -- the last wire is the frame's own (reported as a far load)
            dd_ = np.abs(cen[:, 0] - seed[1][0]) + np.abs(cen[:, 1] - seed[1][1])
            i = int(np.argmin(dd_))
            grp, far = [seed], True
        else:
            i = best_spot([p for _, p in grp], near=driver, max_r=LEAF_R, idx=near_)
        x, y = cand[i]
        fr.take(x, y)
        cand = fr.spots()
        cen = cand + STN / 2
        clusters.append(dict(x=float(x), y=float(y), members=[k for k, _ in grp], far=far))
        done = {k for k, _ in grp}
        todo = [kv for kv in todo if kv[0] not in done]
    # 2. connect stations to the driver: nearest-first; a station's parent is a placed node within HOP that keeps its
    # depth smallest; a station with none in reach gets intermediate stations toward the nearest placed node
    st = []
    for c in clusters:
        st.append(dict(name=None, x=c['x'], y=c['y'], members=c['members'], parent=None, depth=None, kids=0, far=c['far']))
    order = sorted(range(len(st)), key=lambda i: _d((st[i]['x'] + STN / 2, st[i]['y'] + STN / 2), driver))
    nodes = [dict(name=None, x=driver[0] - STN / 2, y=driver[1] - STN / 2, depth=0, kids=0, root=True)]

    def ctr(n):
        return (n['x'] + STN / 2, n['y'] + STN / 2)
    extra = []
    for i in order:
        s = st[i]
        while True:
            ok = [n for n in nodes if _d(ctr(n), ctr(s)) <= HOP and (n.get('root') or n['kids'] < SFAN)]
            if ok:
                p = min(ok, key=lambda n: (n['depth'], _d(ctr(n), ctr(s))))
                s['parent'] = p
                s['depth'] = p['depth'] + 1
                if not p.get('root'):
                    p['kids'] += 1
                nodes.append(s)
                break
            # intermediate station: the free spot within HOP of the nearest node that is nearest to s
            q = min(nodes, key=lambda n: _d(ctr(n), ctr(s)))
            qc = ctr(q)
            dq = np.abs(cen[:, 0] - qc[0]) + np.abs(cen[:, 1] - qc[1])
            ds = np.abs(cen[:, 0] - ctr(s)[0]) + np.abs(cen[:, 1] - ctr(s)[1])
            okm = dq <= HOP * 0.97
            if not okm.any():
                raise ValueError(f'{name}: no intermediate station spot within {HOP} um of ({qc[0]:.0f}, {qc[1]:.0f})')
            j = int(np.argmin(np.where(okm, ds, np.inf)))
            if ds[j] >= _d(qc, ctr(s)) - 1.0:
                raise ValueError(f'{name}: intermediate station makes no progress toward ({ctr(s)[0]:.0f}, {ctr(s)[1]:.0f})')
            x, y = cand[j]
            fr.take(x, y)
            cand = fr.spots()
            cen = cand + STN / 2
            p = min([n for n in nodes if _d(ctr(n), (x + STN / 2, y + STN / 2)) <= HOP and (n.get('root') or n['kids'] < SFAN)],
                    key=lambda n: (n['depth'], _d(ctr(n), (x + STN / 2, y + STN / 2))))
            t = dict(name=None, x=float(x), y=float(y), members=[], parent=p, depth=p['depth'] + 1, kids=0)
            if not p.get('root'):
                p['kids'] += 1
            nodes.append(t)
            extra.append(t)
    allst = [n for n in nodes if not n.get('root')]
    for k, n in enumerate(allst):
        n['name'] = f'{name}_s{k}'
    out, assign = [], {}
    for n in allst:
        par = n['parent']
        out.append(dict(name=n['name'], x=round(n['x'], 3), y=round(n['y'], 3), depth=n['depth'],
                        parent=None if par.get('root') else par['name'], ck=clock_of(ctr(n)),
                        hop_um=round(_d(ctr(par), ctr(n)), 1), members=list(n['members']), far=bool(n.get('far'))))
        for k in n['members']:
            assign[k] = n['name']
    return out, assign
