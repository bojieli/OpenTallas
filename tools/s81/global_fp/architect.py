#!/usr/bin/env python3
"""GLOBAL-FP-S architect topology: pipeline order around the owner-selected compact 2x2 VM (screen only).

The S81 token pipeline on the die graph (graph.py, widest links in brackets):
  PQ --x broadcast--> 128 frames --return trees--> gather -> capture [6,959] -> VM [13,376]
  VM <-> SU [17,137];  VM <-> HC_s [5,401];  HC_s <-> HC_t [15,660];  HC_s <-> COLL [8,225];  VM <-> COLL [4,921]
  VM <-> MIX4 [12,732 VM-ABI];  COLL <-> 8 links at the die W/E edges [8 x 1,027].
Topology (the 'pipeline core', fixed by construction):
  * VM 2x2 (4,168.8 x 3,715.2) against one side of the hub region; the three towers SU | HC_s | HC_t stand side by
    side directly under it (SU and HC_s each abut the VM S face over their full width, HC_t abuts HC_s over its
    full height), so the three heaviest VM/HC links are face-to-face.
  * the 1,755-um strip beside the VM holds a column whose blocks all abut the VM's free side face (capture, and a
    variant-chosen set from gather / MIX4 / PQ / wfc / sseq), packed against the crossing corridor.
  * one full-width crossing corridor (1,512 um) directly above the VM: the field trees of the far half cross the
    spine there, next to the tree roots (gather, PQ).
  * everything else (COLL, host, wfc/sseq, Engram dispatch, HCX controller/gatherpack, embed expand, and whatever the
    column did not take) is placed above the corridor by the slot-stack annealer restricted to that tier.
Variants: VM side (W/E) x column content.  Each variant is annealed with several seeds; same objective as placer.py.
"""
import copy, math, random
import placer as P

HALO = 21.6
CORR_H = 1512.0
COLUMN_VARIANTS = {
    'gcm': ['sp_gather', 'sp_capture', 'mix4'],                  # trees root + VM feed + Engram on the VM face
    'gcp': ['sp_gather', 'sp_capture', 'sp_pq', 'sp_wfc', 'sp_sseq'],   # whole field pipeline on the VM face
    'pgc': ['sp_pq', 'sp_gather', 'sp_capture', 'mix4'],         # both tree roots at the corridor
    'gcmh': ['sp_gather', 'sp_capture', 'mix4', 'hcx_ctl', 'hcx_gatherpack'],
    'cC': ['sp_capture', 'sp_collective'],                       # COLL at the tower line: ~480 um to HC_s
    'chC': ['sp_capture', 'sp_host', 'sp_collective'],
    'csC': ['sp_capture', 'sp_sseq', 'sp_host', 'sp_collective'],
}


def core(region, dims, side, column, flip=False):
    """fixed pipeline core: VM, towers, side column; returns rects, corridor rect.  flip=True mirrors the core
    vertically (towers hang from the region top, VM under them, corridor under the VM)."""
    x0, y0, x1, y1 = region
    vw, vh = dims['sp_vm']
    towers = ['sp_su_s', 'sp_hc_s', 'sp_hc_t'] if side == 'W' else ['sp_hc_t', 'sp_hc_s', 'sp_su_s']
    tw = sum(dims[t][0] for t in towers) + 2 * HALO
    assert tw <= x1 - x0, 'towers do not fit side by side'
    th = max(dims[t][1] for t in towers)
    vy = y0 + th + HALO                       # VM sits on the tallest tower
    R = {}
    vx = x0 if side == 'W' else x1 - vw
    R['sp_vm'] = [vx, vy, vw, vh]
    x = x0 if side == 'W' else x1 - tw
    for t in towers:
        w, h = dims[t]
        R[t] = [x, vy - HALO - h, w, h]       # tower tops touch the VM bottom (halo)
        x += w + HALO
    # side column beside the VM: packed downward from the VM top (= corridor side)
    cx0 = vx + vw + HALO if side == 'W' else x0
    cx1 = x1 if side == 'W' else vx - HALO
    yy = vy + vh
    for b in column:
        w, h = dims[b]
        assert w <= cx1 - cx0 + 1e-6, (b, w, cx1 - cx0)
        yy -= h
        assert yy >= vy - 1e-6, 'column taller than the VM: ' + ','.join(column)
        bx = (vx + vw + HALO) if side == 'W' else (vx - HALO - w)    # hug the VM face
        R[b] = [bx, yy, w, h]
        yy -= HALO
    corr = [x0, vy + vh + HALO, x1 - x0, CORR_H]
    if flip:
        my = lambda r: [r[0], y0 + y1 - r[1] - r[3], r[2], r[3]]
        R = {k: my(r) for k, r in R.items()}
        corr = my(corr)
    return R, corr


class TopTier(P.SlotStack):
    """slot-stack annealer restricted to the tier above a fixed corridor"""

    def __init__(self, *a, corr_y=None, tier=1, **k):
        super().__init__(*a, **k)
        self.fixed_corr_y = corr_y
        self.tier = tier

    def random_state(self, corr_y=None):
        st = super().random_state(self.fixed_corr_y)
        st['tiers'] = {1 - self.tier: [], self.tier: [c for cols in st['tiers'].values() for c in cols]}
        return st

    def neighbour(self, st):
        s = super().neighbour(st)
        s['corr_y'] = self.fixed_corr_y
        o = 1 - self.tier
        # fold anything the parent move put on the core side of the corridor back into the free tier
        s['tiers'][self.tier] = s['tiers'].get(self.tier, []) + s['tiers'].get(o, []); s['tiers'][o] = []
        return s


def build(g, S, base, region, dims, side, column_key, seeds=(1, 2, 3), iters=20000, mix_shape='2x2', flip=False):
    dims = dict(dims)
    dims['mix4'] = dims.get('mix4_' + mix_shape, dims['mix4'])
    column = COLUMN_VARIANTS[column_key]
    R, corr = core(region, dims, side, column, flip)
    movable_top = [b for b in dims if b in base and b not in R and not b.startswith('mix4_')]
    fixed = {n: r for n, r in base.items() if n not in dims}
    fixed.update(R)
    best = None
    for sd in seeds:
        top = TopTier(g, S, movable_top, {b: dims[b] for b in movable_top}, region, '2x2', fixed, seed=sd,
                      corr_y=corr[1], tier=0 if flip else 1)
        st = top.random_state()
        J, st = top.anneal(st, iters=iters, T0=1.5e7, T1=2e3)
        J, pen, worst = top.cost(st)
        if pen == 0 and (best is None or J < best[0]):
            rects, c2, _ = top.realize(st)
            best = (J, rects, st, worst)
    if best is None:
        return None
    J, rects, st, worst = best
    lay = dict(base); lay.update(R); lay.update(rects)
    return dict(layout=lay, corridor=corr, J=J, worst=worst, side=side, column=column_key, flip=flip,
                free_tier_columns=st['tiers'][0 if flip else 1])
