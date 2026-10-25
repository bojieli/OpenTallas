#!/usr/bin/env python3
"""Structured die clock (lane CLOCK, owner decision 5 2026-10-24: industry multi-source CTS).

A die plan's partitions each publish clock tap ports (schema.tap_grid R4 grid + early core taps).  This tool builds the
die-level distribution from the die clock root to EVERY tap port, balanced by construction:

    die_clock.py run    PLAN --out DIR [--leaf-um 1000] [--rep-um 450] [--core-early off|pad]   # build+sta+report
    die_clock.py build  PLAN --out DIR [--leaf-um 1000] [--rep-um 450] [--core-early off|pad]
    die_clock.py sta    DIR [--corner TT --corner FF] [--libdir D]     # OpenSTA on ctree.v + ctree.spef (light)
    die_clock.py report DIR --plan PLAN                                 # pair skew, CPPR, spine_<corner>.json
    die_clock.py render DIR --plan PLAN                                 # tree + taps + keep-outs PNG

Structure (all die-level cells are BUFx24, all wires on M8 (horizontal) / M9 (vertical) with a 2W2S NDR + shields):
  * trunk: the plan's spine root (clock entry, clock.spine.root_um) -> the die centre: common to every tap.
  * H-tree: binary bisection of the die outline (axis per level from the regular bisection, longer axis first, so
    every leg of a level runs on the same layer).  On the top AWARE_LEVELS levels a split may move up to +-window of
    the region extent onto a partition edge when that cuts less related-pair weight (seam launch/capture taps by bits,
    neighbouring taps of one partition): seam neighbours stay on one branch (decision 5 (f)).  Each level has one cut
    count n (escalated until every legalised segment <= 1.15 rep_um) and ONE padded segment length (the level's
    longest), so every leg of a level is electrically identical.  Branches without taps are pruned to a DUMMY first
    stage (first segment + a buffer input), so every node buffer drives the identical load.
  * leaves: regions <= leaf_um.  The leaf buffer drives F tap drivers clustered at the leaf (F = the largest tap count
    of any leaf; leaves with fewer taps get dummy drivers), so every leaf buffer sees the identical load.
  * last mile: every tap driver feeds its tap through a chain padded to the SAME length on each layer: x on M8 padded
    to Lx = the die-wide max |dx| (leaf -> tap), y on M9 padded to Ly, cut into equal repeated segments.  Padding is
    wire length (serpentine in the die route), never cell delay, so the balance holds at every corner.
  * legalisation: no die buffer on a hard core / PHY macro (keep-outs): a buffer that lands on one slides along its
    leg (or sideways with a stub) to the nearest free site; every segment of the same (level, index) is then padded to
    the longest one, so the balance survives.
  Every root -> tap path therefore has the identical sequence of cells, wire lengths per layer and loads: nominal
  tap skew is zero by construction at every corner; STA on the exact RC (ctree.spef) measures the residue.
  Core-latency contract (CP2): a core tap (clk_c<k>, early_ps = core insertion - common latency) is delivered early by
  removing padded wire from its last-mile chain (--core-early pad); --core-early off delivers it on time (trial dies
  with budget stand-ins, whose core-tap flops carry no core insertion).

Outputs (DIR): ctree.v (module die_ctree: input root, outputs t_<inst>__<port>), ctree.spef (exact ladder RC of every
net, NDR M8/M9 + via stacks), place.json (every cell xy), tree.json (nodes, taps, cell path per tap), sta_<C>.tcl.
`report`: per corner insertion, tap skew, related pair skew of every seam (launch tap = nearest src-part tap to each
pin, capture tap = nearest dst-part tap: the stand-in / kit nearest-tap rule) and of neighbouring taps inside a
partition, CPPR from the lowest common tree node with a flat OCV derate on the uncommon path (INFO), and die_sta.py
spine files spine_<C>.json (per tap source latency offsets).  Gate (decision 5): related pair skew <= 80 ps at TT and
FF; design target <= 20 ps.
"""
import argparse
import bisect
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

BUF = "BUFx24_ASAP7_75t_R"
BUF_CIN_FF = 2.35                       # BUFx24 A pin (TT lib)
TAP_LOAD_FF = 3.0                       # partition tap port load (the partition's first tap buffer, ASSUMED)
PERIOD_PS = 833.000
GATE_PS = 80.0                          # decision 5: related pair skew <= 80 ps (TT, FF)
TARGET_PS = 20.0                        # design window
OCV = (0.03, 0.05)                      # INFO derates on the uncommon clock path
# ASAP7 setRC.tcl (kohm / fF per um); clock NDR 2W2S: R / 2, C x 1.1 (die_trial.py, hbm_arch clock_htree.py)
LAYER_RC = {"M8": (8.44765e-3, 1.03962e-1), "M9": (8.89556e-3, 9.28446e-2)}
NDR_R, NDR_C = 0.5, 1.1
PAD_CAP_UM = 440.0                      # balance pads fill segments up to this length before any goes wide
SNAKE_UM = 440.0                        # a pad beyond the segment cap becomes delay stages: BUF + SNAKE_UM wire each
WIDE_UM = 520.0                         # longer segments use the 4W NDR
VIA_KOHM = {"M8": 0.0172 * 3 + 0.0118 * 2 + 0.0082 * 2, "M9": 0.0172 * 3 + 0.0118 * 2 + 0.0082 * 2 + 0.0063}
LADDER_UM = 50.0                        # pi-section length of the RC ladder
STUB_UM = 4.32                          # leaf buffer -> clustered tap driver stub
STEP_UM = 2.16                          # legalisation search step
SPLIT_WINDOW = 0.25                     # a split may move +-25 % of the region extent to a partition edge
AWARE_LEVELS = 4                        # partition-aware splits on the top levels (largest uncommon latency)
INTRA_W = 256                           # split weight of two neighbouring taps of one partition (seam pairs: bits)
CORRIDOR_WINDOW = 0.25                  # a node may move +-25 % of its region extent along its incoming leg
CORRIDOR_STEP_UM = 17.28
MAX_SEG_X = 1.15                        # a legalised segment may reach 1.15 x rep_um, else the level gets a repeater more
SIDE_MAX_UM = 1500.0


def layer_rc(layer, length_um=0.0):
    """NDR wire RC per um; a segment longer than WIDE_UM (a legalised hop over a macro, or a balance pad) gets the
    wide NDR (4W: R / 4, C x 1.3) so its slew stays inside the 320-ps limit."""
    r, c = LAYER_RC[layer]
    if length_um > WIDE_UM:
        return r * 0.25, c * 1.3
    return r * NDR_R, c * NDR_C


def sv(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


# ------------------------------------------------------------------------------------------------------------ inputs
def plan_taps(P):
    """[(part, port, x_die, y_die, early_ps)]: every partition clock tap exactly as the kits / stand-ins see it."""
    import gen_phys
    out = []
    for n, p in sorted(P.parts.items()):
        tn = p["type"]
        early = {nm: S.core_tap_early_ps(P, tp) for nm, _, _, tp in S.core_taps(P, tn)}
        for port, x, y in gen_phys.clock_pins(P, tn) + gen_phys.core_tap_pins(P, tn):
            X, Y = P.to_die(n, (x, y))
            out.append((n, port, round(X, 3), round(Y, 3), float(early.get(port, 0.0))))
    return out


def keepouts(P):
    """die-frame rects no die buffer may sit on: every hard core / ROM macro of every partition + die PHY macros."""
    out = []
    for n, p in P.parts.items():
        t = P.types[p["type"]]
        for hc in t.get("hard_cores", []) or []:
            (x0, y0), (w, h) = hc["origin_um"], hc["outline_um"]
            a, b = P.to_die(n, (x0, y0)), P.to_die(n, (x0 + w, y0 + h))
            out.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), f"{n}/{hc['inst']}"))
    for io in P.die.get("io", []) or []:
        if io.get("rect_um") and io.get("kind", "") in ("phy_macro", "phy", "serdes", "hbm_phy"):
            x0, y0, x1, y1 = io["rect_um"]
            out.append((x0, y0, x1, y1, f"io/{io.get('name')}"))
    return out


class KeepIndex:
    def __init__(self, rects, bucket=500.0, die=None):
        self.b = bucket
        self.die = die
        self.g = defaultdict(list)
        for r in rects:
            for i in range(int(r[0] // bucket), int(r[2] // bucket) + 1):
                for j in range(int(r[1] // bucket), int(r[3] // bucket) + 1):
                    self.g[(i, j)].append(r)

    def hit(self, x, y, m=0.5):
        if self.die and not (1.0 <= x <= self.die[0] - 1.0 and 1.0 <= y <= self.die[1] - 1.0):
            return (0, 0, 0, 0, "outside die")
        for r in self.g.get((int(x // self.b), int(y // self.b)), ()):
            if r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m:
                return r
        return None


# ------------------------------------------------------------------------------------------------------------- build
class Tree:
    """cells {name: dict(x, y, kind, level)}; nets [dict(name, drv, branches[(length_um, layer, load, geo_um)])];
    a branch load is a cell name (its A pin) or 'port:<name>'."""

    def __init__(self):
        self.cells, self.nets, self.ports = {}, [], []

    def cell(self, name, x, y, kind, level=None):
        self.cells[name] = dict(x=round(x, 3), y=round(y, 3), kind=kind, level=level)
        return name


def _leg_points(a, b, n):
    """n equal cuts of the straight leg a -> b: the n points after a (the last is b)."""
    return [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]


def _slide(pt, a, b, K, fixed=False):
    """legal site for a buffer planned at pt on leg a -> b: pt if free, else the nearest free point along the leg, else
    sideways (stub).  -> (x, y, side_um)."""
    if K is None or not K.hit(*pt):
        return pt[0], pt[1], 0.0
    horiz = abs(b[0] - a[0]) >= abs(b[1] - a[1])
    lo = (min(a[0], b[0]), max(a[0], b[0])) if horiz else (min(a[1], b[1]), max(a[1], b[1]))
    for k in range(1, 100000):
        d = k * STEP_UM
        if d > lo[1] - lo[0] and d > SIDE_MAX_UM:
            break
        for s in (d, -d):
            if not fixed:
                q = (pt[0] + s, pt[1]) if horiz else (pt[0], pt[1] + s)
                if lo[0] <= (q[0] if horiz else q[1]) <= lo[1] and not K.hit(*q):
                    return q[0], q[1], 0.0
            if d <= SIDE_MAX_UM:
                q = (pt[0], pt[1] + s) if horiz else (pt[0] + s, pt[1])
                if not K.hit(*q):
                    return q[0], q[1], d
    # A wide macro may cover the entire incoming leg and SIDE_MAX_UM. Never silently
    # put a buffer back at its blocked starting point. Search obstacle edges for the
    # nearest legal channel; the caller accounts for the detour in the wire RC.
    rects = {tuple(r) for rs in K.g.values() for r in rs}
    xs, ys = {pt[0]}, {pt[1]}
    for r in rects:
        xs.update((r[0] - 1.0, r[2] + 1.0))
        ys.update((r[1] - 1.0, r[3] + 1.0))
    if K.die:
        xs = {min(max(x, 1.0), K.die[0] - 1.0) for x in xs}
        ys = {min(max(y, 1.0), K.die[1] - 1.0) for y in ys}
    # Axial candidates normally suffice; cross products also handle overlapping walls.
    candidates = {(x, pt[1]) for x in xs} | {(pt[0], y) for y in ys}
    legal = [q for q in candidates if not K.hit(*q)]
    if not legal:
        legal = [(x, y) for x in xs for y in ys if not K.hit(x, y)]
    if not legal:
        raise ValueError(f"no legal clock buffer site near {pt}; macro/PHY keepouts cover the die")
    q = min(legal, key=lambda q: (abs(q[0] - pt[0]) + abs(q[1] - pt[1]), q))
    side = abs(q[1] - pt[1]) if horiz else abs(q[0] - pt[0])
    return q[0], q[1], side


def split_pairs(P, taps):
    """[(tap index a, tap index b, weight)]: related tap pairs the H-tree should keep on one branch (decision 5 (f)):
    every seam's launch / capture tap pair weighted by its bits, neighbouring taps of one partition by INTRA_W."""
    tb = defaultdict(list)
    for k, t in enumerate(taps):
        tb[t[0]].append(dict(port=k, xy=[t[2], t[3]]))
    out = [(a, b, w) for (a, b, _), w in seam_pairs(P, tb).items()]
    out += [(a, b, INTRA_W) for a, b, _ in intra_pairs(tb, float(P.budgets.get("tap_pitch_um", 400.0)))]
    return out


def choose_split(lo, hi, ax, coords, pairs, edges, window):
    """split coordinate of region [lo, hi) on axis ax: the candidate (region midpoint or a partition edge within
    +-window x extent of it) cutting the least pair weight; ties -> nearest the midpoint.  -> (s, cut weight)."""
    mid = (lo + hi) / 2
    span = window * (hi - lo)
    cands = sorted({mid} | {e for e in edges if mid - span <= e <= mid + span and lo < e < hi})
    ev = []
    for a, b, w in pairs:
        ca, cb = coords[a], coords[b]
        if ca == cb:
            continue
        ev.append((min(ca, cb), max(ca, cb), w))
    best = None
    for c in cands:                                   # pair cut iff min < c <= max (a tap at c goes right)
        cost = sum(w for u, v, w in ev if u < c <= v)
        key = (cost, abs(c - mid))
        if best is None or key < best[0]:
            best = (key, c)
    return best[1], best[0][0]


def build(P, leaf_um=1000.0, rep_um=450.0, core_early="off", taps=None, keep=None, window=None, aware_levels=None,
          pad="sta"):
    W, H = float(P.W), float(P.H)
    window = SPLIT_WINDOW if window is None else window
    aware_levels = AWARE_LEVELS if aware_levels is None else aware_levels
    taps = plan_taps(P) if taps is None else taps
    K = KeepIndex(keep if keep is not None else keepouts(P), die=(W, H))
    T = Tree()
    sp = P.clock.get("spine", {}) or {}
    root = tuple(sp.get("die_root_um") or sp.get("root_um") or (W / 2, H / 2))
    # --- level axes: the regular bisection's (longer axis first) -> every level has one leg layer
    levels = []
    w, h = W, H
    while max(w, h) > leaf_um:
        ax = 0 if w >= h else 1
        levels.append(ax)
        if ax == 0:
            w /= 2
        else:
            h /= 2
    D = len(levels)
    # --- partition-aware bisection: split near the midpoint, on a partition edge when that keeps related taps together
    pairs = split_pairs(P, taps)
    xs = [t[2] for t in taps]
    ys = [t[3] for t in taps]
    edges = ({r[0] for r in map(P.rect, P.parts)} | {r[2] for r in map(P.rect, P.parts)},
             {r[1] for r in map(P.rect, P.parts)} | {r[3] for r in map(P.rect, P.parts)})
    region = {(0, 0): (0.0, 0.0, W, H)}
    members = {(0, 0): list(range(len(taps)))}
    npairs = {(0, 0): pairs}
    cut_w = defaultdict(float)
    for lev in range(D):
        ax = levels[lev]
        co = xs if ax == 0 else ys
        for (l2, idx), reg in sorted(region.items()):
            if l2 != lev:
                continue
            lo, hi = (reg[0], reg[2]) if ax == 0 else (reg[1], reg[3])
            mem = members.get((lev, idx), [])
            pr = npairs.get((lev, idx), [])
            if mem and pr and lev < aware_levels:
                s_, cw = choose_split(lo, hi, ax, co, pr, edges[ax], window)
            elif mem and pr:
                s_, cw = choose_split(lo, hi, ax, co, pr, (), 0.0)
            else:
                s_, cw = (lo + hi) / 2, 0.0
            cut_w[lev] += cw
            a_ = (reg[0], reg[1], s_, reg[3]) if ax == 0 else (reg[0], reg[1], reg[2], s_)
            b_ = (s_, reg[1], reg[2], reg[3]) if ax == 0 else (reg[0], s_, reg[2], reg[3])
            for c, rr in ((0, a_), (1, b_)):
                region[(lev + 1, 2 * idx + c)] = rr
            side = {k: int(co[k] >= s_) for k in mem}
            for c in (0, 1):
                m = [k for k in mem if side[k] == c]
                if m:
                    members[(lev + 1, 2 * idx + c)] = m
            for c in (0, 1):
                pc = [q for q in pr if side.get(q[0]) == c and side.get(q[1]) == c]
                if pc:
                    npairs[(lev + 1, 2 * idx + c)] = pc
    live = set(members)

    def centre(key):
        r = region[key]
        return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)

    def ncell(key):
        return f"n{key[0]}_{key[1]}"
    # --- corridor-aware node placement: a node moves along its incoming leg (up to +-CORRIDOR_WINDOW of its region
    # extent) to the spot where its two outgoing legs cross the shortest blocked (macro) run, so repeaters find sites
    # (die channels between hard cores) instead of hopping over them.
    keep_rects = keep if keep is not None else keepouts(P)

    def blocked_run(x0, y0, x1, y1, rects):
        """longest continuous run of the axis-parallel line (x0,y0)-(x1,y1) over keep-out rects."""
        horiz = abs(y1 - y0) < 1e-9
        lo, hi = (min(x0, x1), max(x0, x1)) if horiz else (min(y0, y1), max(y0, y1))
        iv = []
        for r in rects:
            if horiz and r[1] <= y0 <= r[3]:
                iv.append((max(lo, r[0]), min(hi, r[2])))
            elif not horiz and r[0] <= x0 <= r[2]:
                iv.append((max(lo, r[1]), min(hi, r[3])))
        iv = sorted(v for v in iv if v[1] > v[0])
        best, cur = 0.0, None
        for a_, b_ in iv:
            if cur and a_ <= cur[1] + STEP_UM:
                cur = (cur[0], max(cur[1], b_))
            else:
                cur = (a_, b_)
            best = max(best, cur[1] - cur[0])
        return best

    def corridor(key, x, y, along):
        """best coordinate on axis `along` for node key's outgoing legs (they run on the other axis)."""
        lev = key[0]
        r = region[key]
        oax = levels[lev]
        ext_out = (r[2] - r[0]) if oax == 0 else (r[3] - r[1])
        span = ext_out / 4.0
        ext_al = (r[2] - r[0]) if along == 0 else (r[3] - r[1])
        w_ = CORRIDOR_WINDOW * ext_al
        c = x if along == 0 else y
        box = (x - w_ - span, y - span, x + w_ + span, y + span) if along == 0 else \
            (x - span, y - w_ - span, x + span, y + w_ + span)
        rects = [q for q in keep_rects if q[0] < box[2] and q[2] > box[0] and q[1] < box[3] and q[3] > box[1]]
        if not rects:
            return c
        best = None
        k = 0
        while True:
            for sgn in ((1,) if k == 0 else (1, -1)):
                v = c + sgn * k * CORRIDOR_STEP_UM
                if along == 0:
                    run = blocked_run(v, y - span, v, y + span, rects)
                else:
                    run = blocked_run(x - span, v, x + span, v, rects)
                if best is None or run < best[0] - 1e-6:
                    best = (run, v)
            k += 1
            if k * CORRIDOR_STEP_UM > w_ or best[0] <= 0:
                break
        return best[1]
    npos = {}
    for lev in range(0, D + 1):
        for key in sorted(k for k in region if k[0] == lev):
            cx, cy = centre(key)
            if lev:
                ax = levels[lev - 1]
                px, py = npos[(lev - 1, key[1] // 2)]
                cx, cy = (cx, py) if ax == 0 else (px, cy)
                if lev < D and levels[lev] != ax and key in live:
                    v = corridor(key, cx, cy, ax)
                    cx, cy = (v, cy) if ax == 0 else (cx, v)
            elif D:
                oax = levels[0]
                v = corridor(key, cx, cy, 1 - oax)
                cx, cy = (cx, v) if oax == 0 else (v, cy)
            npos[key] = (cx, cy)
    # --- segments: plan every leg from the legalised parent, one cut count per level, pad to the level standard

    def plan_leg(a0, a, b, n):
        """cut points of leg a -> b (planned straight line) driven from the legalised parent a0."""
        out, prev = [], a0
        for q in _leg_points(a, b, n):
            x, y, side = _slide(q, a, b, K, fixed=False)
            out.append((x, y, abs(x - prev[0]) + abs(y - prev[1]) + side))
            prev = (x, y)
        return out
    # trunk (root -> the die-region centre): common to every tap
    c0 = npos[(0, 0)]
    tl = abs(c0[0] - root[0]) + abs(c0[1] - root[1])
    trunk = []
    if tl > 1e-6:
        corner = (c0[0], root[1])
        prev = root
        for a, b in ((root, corner), (corner, c0)):
            L = abs(b[0] - a[0]) + abs(b[1] - a[1])
            if L <= 1e-6:
                continue
            n = max(1, math.ceil(L / rep_um - 1e-9))
            for q in _leg_points(a, b, n):
                x, y, side = _slide(q, a, b, K)
                trunk.append((x, y, abs(x - prev[0]) + abs(y - prev[1]) + side, "M8" if a[1] == b[1] else "M9"))
                prev = (x, y)
    legs = {}
    pos = {(0, 0): c0}
    leg_len = {}
    max_seg = MAX_SEG_X * rep_um
    for lev in range(1, D + 1):
        parents = sorted(k for k in live if k[0] == lev - 1)
        kids = [(pk, (lev, 2 * pk[1] + c)) for pk in parents for c in (0, 1)]
        Lmax = max(abs(npos[ck][0] - npos[pk][0]) + abs(npos[ck][1] - npos[pk][1]) for pk, ck in kids)
        n0 = max(1, math.ceil(Lmax / rep_um - 1e-9))
        n = n0
        while True:                                 # one n per level: escalate until every legalised segment fits
            plan = {}
            for pk, ck in kids:
                segs = plan_leg(pos[pk], npos[pk], npos[ck], n)
                plan[ck if ck in live else ("dummy",) + ck] = segs if ck in live else segs[:1]
            worst = max(g for segs in plan.values() for _, _, g in segs)
            if worst <= max(max_seg, Lmax / n + 1e-6) or n >= n0 + 2:
                break
            n += 1
        leg_len[lev] = (Lmax, n)
        legs.update(plan)
        for k, segs in plan.items():
            if k[0] != "dummy":
                pos[k] = (segs[-1][0], segs[-1][1])
    seg_std = {}
    for lev, (L, n) in leg_len.items():
        # every segment of a level is padded to the level's longest legalised segment (balance by construction)
        seg_std[lev] = max([L / n] + [g for k, segs in legs.items() if (k[1] if k[0] == "dummy" else k[0]) == lev
                                      for _, _, g in segs])
    # --- last mile
    leaf_keys = sorted(k for k in live if k[0] == D)
    by_leaf = {k: [taps[i] for i in members[k]] for k in leaf_keys}
    F = max(len(v) for v in by_leaf.values())
    Lx = max(abs(t[2] - pos[k][0]) for k in leaf_keys for t in by_leaf[k])
    Ly = max(abs(t[3] - pos[k][1]) for k in leaf_keys for t in by_leaf[k])
    kx = max(1, math.ceil(Lx / rep_um - 1e-9)) if Lx > 1e-6 else 0
    ky = max(1, math.ceil(Ly / rep_um - 1e-9)) if Ly > 1e-6 else 0
    chain_std = [Lx / kx] * kx + [Ly / ky] * ky if (kx or ky) else [0.0]
    chain_layer = ["M8"] * kx + ["M9"] * ky if (kx or ky) else ["M8"]
    # ------------------------------------------------------------------ netlist
    nets = T.nets
    T.ports.append(("input", "root"))
    lay = {0: "M8", 1: "M9"}
    prev_cell = None
    for k, (x, y, geo, layer) in enumerate(trunk):
        nm = T.cell(f"tr{k}", x, y, "trunk", 0)
        nets.append(dict(name=f"ntr{k}" if prev_cell else "root", drv=prev_cell or "port:root",
                         branches=[(geo, layer, nm, geo)]))
        prev_cell = nm
    T.cell(ncell((0, 0)), *c0, "node", 0)
    nets.append(dict(name=f"ntr{len(trunk)}" if prev_cell else "root", drv=prev_cell or "port:root",
                     branches=[(1e-3, "M8", ncell((0, 0)), 0.0)]))
    path_of = {(0, 0): [f"tr{k}" for k in range(len(trunk))] + [ncell((0, 0))]}
    children = defaultdict(list)                    # node cell -> [(child node cell, pad net, branch index)]
    for key in sorted(k for k in live if k[0] < D):
        lev, idx = key
        layer = lay[levels[lev]]
        S_ = seg_std[lev + 1]

        def el(geo):
            return S_ if pad == "level" else max(geo, 1.0)
        branches = []
        for c in (0, 1):
            ck = (lev + 1, 2 * idx + c)
            if ck in live:
                segs = legs[ck]
                names = [f"r{ck[0]}_{ck[1]}_{k}" for k in range(len(segs) - 1)] + [ncell(ck)]
                for k, (x, y, geo) in enumerate(segs):
                    T.cell(names[k], x, y, "node" if k == len(segs) - 1 else "rep", lev + 1)
                branches.append((el(segs[0][2]), layer, names[0], segs[0][2]))
                for k in range(1, len(segs)):
                    nets.append(dict(name=f"w_{names[k - 1]}", drv=names[k - 1],
                                     branches=[(el(segs[k][2]), layer, names[k], segs[k][2])]))
                path_of[ck] = path_of[key] + names
                children[ncell(key)].append((ncell(ck), [[f"w_{ncell(key)}", len(branches) - 1]] +
                                             [[f"w_{names[k - 1]}", 0] for k in range(1, len(segs))]))
            else:                                   # pruned branch: dummy first stage (the identical load)
                x, y, geo = legs[("dummy",) + ck][0]
                dn = T.cell(f"d{ck[0]}_{ck[1]}", x, y, "dummy", lev + 1)
                branches.append((el(geo), layer, dn, geo))
        nets.append(dict(name=f"w_{ncell(key)}", drv=ncell(key), branches=branches))
    tap_rows = []
    for key in leaf_keys:
        lx, ly = pos[key]
        tl_ = sorted(by_leaf[key], key=lambda t: (t[0], t[1]))
        branches = []
        for f in range(F):
            dn = f"td{key[1]}_{f}"
            T.cell(dn, lx, ly, "tapdrv" if f < len(tl_) else "dummy", D + 1)
            branches.append((STUB_UM, "M8", dn, STUB_UM))
        nets.append(dict(name=f"w_{ncell(key)}", drv=ncell(key), branches=branches))
        for f, (part, port, X, Y, early) in enumerate(tl_):
            dn = f"td{key[1]}_{f}"
            out = f"t_{sv(part)}__{port}"
            T.ports.append(("output", out))
            # chain geometry: x run then y run along the real L, cells at proportional cuts, padded electrically
            corner = (X, ly)
            cuts = [(lx + (X - lx) * (k + 1) / kx, ly, "M8") for k in range(kx)]
            cuts += [(X, ly + (Y - ly) * (k + 1) / ky, "M9") for k in range(ky)]
            std = list(chain_std)
            if core_early == "pad" and early > 0:
                std = early_chain(std, chain_layer, early)
            prev, prevpt = dn, (lx, ly)
            cells = []
            for k, (x, y, layer) in enumerate(cuts):
                if k == len(cuts) - 1:
                    geo = abs(X - prevpt[0]) + abs(Y - prevpt[1])
                    nets.append(dict(name=out, drv=prev, branches=[(max(std[k], geo), layer, "port:" + out, geo)],
                                     ck=k, cut=chain_std[k] - std[k]))
                else:
                    a, b = ((lx, ly), corner) if layer == "M8" else (corner, (X, Y))
                    xx, yy, side = _slide((x, y), a, b, K)
                    geo = abs(xx - prevpt[0]) + abs(yy - prevpt[1]) + side
                    cn = T.cell(f"c_{sv(part)}__{port}_{k}", xx, yy, "chain", D + 2 + k)
                    nets.append(dict(name=f"w_{cn}", drv=prev, branches=[(max(std[k], geo), layer, cn, geo)],
                                     ck=k, cut=chain_std[k] - std[k]))
                    cells.append(cn)
                    prev, prevpt = cn, (xx, yy)
            if not cuts:
                nets.append(dict(name=out, drv=prev, branches=[(STUB_UM, "M8", "port:" + out, 0.0)]))
            tap_rows.append(dict(part=part, tap=port, port=out, xy=[X, Y], early_ps=early, leaf=ncell(key),
                                 path=path_of[key] + [dn] + cells, pad_nets=[[f"w_{c}", 0] for c in cells] + [[out, 0]]))
    # chain standard per segment index = the longest legalised chain segment of that index (balance by construction);
    # a core-early chain keeps its cut below the standard
    cmax = defaultdict(float)
    for n in nets:
        if "ck" in n:
            cmax[n["ck"]] = max(cmax[n["ck"]], n["branches"][0][3])
    for n in nets:
        if "ck" in n:
            L, layer, load, geo = n["branches"][0]
            std_k = max(chain_std[n["ck"]], cmax[n["ck"]]) if pad == "level" else max(geo, 1.0)
            n["branches"][0] = (max(1.0, std_k - n.pop("cut")), layer, load, geo)
            n.pop("ck")
    # a legalised hop still longer than 1.15 rep_um (a cut that had to slide far off a macro) gets a local repeater at
    # its free midpoint; the STA balance pads every other path up by that one stage (pad=sta only)
    split = 0
    if pad == "sta":
        tap_xy = {"port:" + t["port"]: tuple(t["xy"]) for t in tap_rows}
        extra = defaultdict(list)
        for _ in range(3):
            todo = [n for n in nets if len(n["branches"]) == 1 and n["branches"][0][3] > max_seg
                    and n["drv"] in T.cells]
            if not todo:
                break
            for n in todo:
                L, layer, load, geo = n["branches"][0]
                a_ = (T.cells[n["drv"]]["x"], T.cells[n["drv"]]["y"])
                b_ = tap_xy.get(load) or (T.cells[load]["x"], T.cells[load]["y"])
                m_ = ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)
                x, y, side = _slide(m_, a_, b_, K)
                g1 = abs(x - a_[0]) + abs(y - a_[1]) + side
                g2 = max(abs(b_[0] - x) + abs(b_[1] - y) + side, geo - g1)
                # A macro may force the midpoint back beside an endpoint. Such a
                # repeater adds a detour and delay without shortening the long hop.
                if max(g1, g2) >= geo - 1e-3:
                    continue
                hn = T.cell(f"h{split}_{n['drv']}", x, y, "rep", None)
                n["branches"][0] = (max(g1, 1.0), layer, hn, g1)
                if load.startswith("port:"):            # the port net keeps its name on the last hop
                    nets.append(dict(name=n["name"], drv=hn, branches=[(max(g2, 1.0), layer, load, g2)]))
                    n["name"] = f"w_{hn}"
                    extra[nets[-1]["name"]].append(n["name"])
                else:
                    nets.append(dict(name=f"w_{hn}", drv=hn, branches=[(max(g2, 1.0), layer, load, g2)]))
                    extra[n["name"]].append(f"w_{hn}")
                split += 1
        for t in tap_rows:
            t["pad_nets"] += [[e, 0] for nn, _ in list(t["pad_nets"]) for e in extra.get(nn, [])]
        for kl in children.values():
            for _, targets in kl:
                targets += [[e, 0] for nn, _ in list(targets) for e in extra.get(nn, [])]
    over = max(geo - L for n in nets for L, _, _, geo in n["branches"])
    tot_w = sum(w for _, _, w in pairs)
    meta = dict(leaf_um=leaf_um, rep_um=rep_um, pad=pad, levels=D, split_axes="".join("xy"[a] for a in levels),
                split_window=window, aware_levels=aware_levels, root_um=list(root), centre_um=list(c0), trunk_um=round(tl, 1), taps=len(taps),
                leaves_live=len(leaf_keys), tap_drivers_per_leaf=F,
                last_mile_pad_um=[round(Lx, 2), round(Ly, 2)], last_mile_stages=[kx, ky],
                core_early=core_early, core_taps=sum(1 for t in taps if t[4] > 0),
                long_hop_repeaters=split, cells=len(T.cells), dummies=sum(1 for c in T.cells.values() if c["kind"] == "dummy"),
                buffer=BUF, ndr="2W2S R/2 C*1.1", geometry_over_standard_um=round(over, 3),
                level_segments={lev: dict(leg_max_um=round(L, 1), cuts=n, std_um=round(seg_std[lev], 1))
                                for lev, (L, n) in leg_len.items()},
                pair_weight=tot_w, cut_weight_per_level={lev: round(v) for lev, v in sorted(cut_w.items())},
                wire_um=round(sum(L for n in nets for L, *_ in n["branches"]), 1),
                padding_um=round(sum(L - g for n in nets for L, _, _, g in n["branches"]), 1))
    tok = [f"{t[0]}/{t[1]}" for t in taps if K.hit(t[2], t[3])]
    meta["taps_on_keepout"] = len(tok)
    meta["taps_on_keepout_list"] = tok[:50]
    meta["cells_on_keepout"] = sum(1 for c in T.cells.values() if c["kind"] != "dummy" and K.hit(c["x"], c["y"]))
    nodes = {ncell(k): dict(level=k[0], xy=list(pos.get(k, npos[k])), region=[round(v, 3) for v in region[k]],
                            path=path_of.get(k), kids=children.get(ncell(k), [])) for k in live}
    tree = dict(meta=meta, taps=tap_rows, nodes=nodes, root_node=ncell((0, 0)))
    return T, tree


def early_chain(std, layers, early_ps, ps_per_um=None):
    """core-latency contract: shorten the padded chain so the tap arrives early_ps sooner (wire removed from the last
    segments; ps_per_um = the NDR stage delay per um, estimated from the Elmore delay of a full segment)."""
    out = list(std)
    rem = early_ps
    for k in range(len(out) - 1, -1, -1):
        r, c = layer_rc(layers[k])
        L = out[k]
        # delay of a segment ~ driver (0.15 kohm) * C + 0.5 R C  (ps: kohm * fF)
        d = 0.15 * c * L + 0.5 * r * c * L * L
        if d <= 1e-9:
            continue
        if rem >= d:
            out[k] = 1.0
            rem -= d
        else:
            # solve 0.15 c x + 0.5 r c x^2 = d - rem
            a, b, cc = 0.5 * r * c, 0.15 * c, -(d - rem)
            out[k] = (-b + math.sqrt(b * b - 4 * a * cc)) / (2 * a)
            rem = 0
            break
    return out


# ------------------------------------------------------------------------------------------------------------ writers
def expand_pads(T, pads, snake_um=SNAKE_UM):
    """the electrical tree: every balance pad folded into its branch length; the part of a branch beyond
    PAD_CAP_UM + its routed hop that is pad becomes delay stages (BUF + snake_um of 2W2S wire each, placed at the
    driver), so a large balance delay never stretches one RC segment (slew) -- the industry delay-buffer pad.
    -> (Tree, stages).  The netlist/SPEF writers take this tree; tree.json paths are unchanged (stages sit below
    their driver, inside the uncommon path)."""
    E = Tree()
    E.ports = list(T.ports)
    E.cells = dict(T.cells)
    E.nets = []
    stages = 0
    for n in T.nets:
        branches = []
        for bi, (L, layer, load, geo) in enumerate(n["branches"]):
            p = pads.get((n["name"], bi), 0.0)
            tot = L + p
            m = int(max(0.0, min(p, tot - max(geo, PAD_CAP_UM))) // snake_um) if snake_um > 0 else 0
            if m <= 0:
                branches.append((tot, layer, load, geo))
                continue
            dx, dy = (T.cells[n["drv"]]["x"], T.cells[n["drv"]]["y"]) if n["drv"] in T.cells else (0.0, 0.0)
            names = [f"s{stages + j}_{n['name']}" for j in range(m)]
            for j, sn in enumerate(names):
                E.cells[sn] = dict(x=dx, y=dy, kind="snake", level=None)
            branches.append((snake_um, layer, names[0], min(geo, snake_um)))
            for j in range(m):
                last = j == m - 1
                E.nets.append(dict(name=n["name"] if (last and load.startswith("port:")) else f"w_{names[j]}",
                                   drv=names[j], branches=[(tot - m * snake_um, layer, load, geo) if last
                                                           else (snake_um, layer, names[j + 1], min(geo, snake_um))]))
            stages += m
        E.nets.append(dict(n, branches=branches))
    # a port net whose last stage took its name: the driver-side net is renamed
    names = defaultdict(int)
    for x in E.nets:
        names[x["name"]] += 1
    for x in E.nets:
        if names[x["name"]] > 1 and not x["drv"].startswith("s"):
            names[x["name"]] -= 1
            x["name"] = f"w_pre_{x['name']}"
    return E, stages


def write_verilog(T, path):
    outs = [p for d, p in T.ports if d == "output"]
    L = ["// GENERATED by tools/die_plan/die_clock.py: structured die clock tree", "module die_ctree (root, " +
         ", ".join(outs) + ");", "  input root;"]
    L += [f"  output {p};" for p in outs]
    drv_net = {}
    for n in T.nets:
        drv_net[n["drv"]] = n["name"]
    wires = sorted({n["name"] for n in T.nets} - set(outs) - {"root"})
    L += [f"  wire {w};" for w in wires]
    in_net = {}
    for n in T.nets:
        for _, _, load, _ in n["branches"]:
            if not load.startswith("port:"):
                in_net[load] = n["name"]
    for c in sorted(T.cells):
        a = in_net.get(c)
        y = drv_net.get(c)
        pins = [f".A({a})"] if a else []
        if y:
            pins.append(f".Y({y})")
        L.append(f"  {BUF} {c} ({', '.join(pins)});")
    L.append("endmodule")
    Path(path).write_text("\n".join(L) + "\n")


def write_spef(T, path, design="die_ctree", pads=None):
    """exact ladder RC per net: every branch from the driver pin node, LADDER_UM pi sections, via stack R at both
    pin ends, the padded (electrical) length (+ the balance pads {(net, branch): um})."""
    pads = pads or {}
    f = open(path, "w")
    f.write('*SPEF "IEEE 1481-1998"\n*DESIGN "%s"\n*DATE "%s"\n*VENDOR "OpenTallas"\n*PROGRAM "die_clock.py"\n'
            '*VERSION "1"\n*DESIGN_FLOW "NAME_SCOPE LOCAL"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER [ ]\n'
            '*T_UNIT 1 PS\n*C_UNIT 1 FF\n*R_UNIT 1 KOHM\n*L_UNIT 1 HENRY\n\n' % (design, time.ctime()))
    for n in T.nets:
        name = n["name"]
        drv = n["drv"]
        dpin = drv[5:] if drv.startswith("port:") else f"{drv}:Y"
        caps, ress = [], []
        conn = [f"*P {dpin} I" if drv.startswith("port:") else f"*I {dpin} O"]
        k = [0]

        def node():
            k[0] += 1
            return f"{name}:{k[0]}"
        for bi, (L, layer, load, geo) in enumerate(n["branches"]):
            L = L + pads.get((name, bi), 0.0)
            r, c = layer_rc(layer, geo)         # NDR class fixed by the routed hop, never by a pad
            lpin = load[5:] if load.startswith("port:") else f"{load}:A"
            conn.append(f"*P {lpin} O" if load.startswith("port:") else f"*I {lpin} I")
            a = node()
            ress.append((dpin, a, VIA_KOHM[layer]))
            m = max(1, math.ceil(L / LADDER_UM))
            seg = L / m
            prev = a
            for s in range(m):
                b = node()
                ress.append((prev, b, r * seg))
                caps.append((prev, c * seg / 2))
                caps.append((b, c * seg / 2))
                prev = b
            ress.append((prev, lpin, VIA_KOHM[layer]))
        cap = defaultdict(float)
        for nd, v in caps:
            cap[nd] += v
        tot = sum(cap.values())
        f.write(f"*D_NET {name} {tot:.5f}\n*CONN\n" + "\n".join(conn) + "\n*CAP\n")
        for i, (nd, v) in enumerate(sorted(cap.items()), 1):
            f.write(f"{i} {nd} {v:.5f}\n")
        f.write("*RES\n")
        for i, (a, b, v) in enumerate(ress, 1):
            f.write(f"{i} {a} {b} {v:.6f}\n")
        f.write("*END\n\n")
    f.close()


def sta_tcl(d, corner, libdir):
    lib = f"{libdir}/asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz"
    return "\n".join([
        f"read_liberty {lib}", f"read_verilog {d}/ctree.v", "link_design die_ctree", f"read_spef {d}/ctree.spef",
        f"create_clock -name vclk -period {PERIOD_PS}",
        "set_input_delay 0 -clock vclk [get_ports root]", "set_input_transition 20 [get_ports root]",
        f"set_load {TAP_LOAD_FF} [all_outputs]", "set_output_delay 0 -clock vclk [all_outputs]",
        "set ot_w [sta::worst_slack_cmd max]",
        f"set fh [open {d}/arr_{corner}.txt w]",
        "foreach p [get_ports t_*] { puts $fh \"T [get_full_name $p] [expr {"
        f"{PERIOD_PS} - [get_property $p slack_max_rise]" "}] [get_property $p slack_min_rise] "
        "[get_property $p slew_max_rise]\" }",
        "foreach i [get_cells n*] { set q [get_pins [get_full_name $i]/Y]; puts $fh \"N [get_full_name $i] "
        "[get_property $q arrival_max_rise] [get_property $q arrival_min_rise]\" }",
        "close $fh",
        "report_check_types -max_slew -max_capacitance -violators",
        "puts OT_DONE"]) + "\n"


def cmd_build(a):
    raw = S.load(a.plan)
    P = S.Plan(raw)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    T, tree = build(P, a.leaf_um, a.rep_um, a.core_early, window=a.window, aware_levels=a.aware_levels, pad=a.pad)
    write_verilog(T, out / "ctree.v")
    write_spef(T, out / "ctree.spef")
    import hashlib
    tree["meta"]["plan"] = str(a.plan)
    tree["meta"]["plan_sha256"] = hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()
    tree["meta"]["build_s"] = round(time.time() - t0, 1)
    (out / "tree.json").write_text(json.dumps(tree) + "\n")
    (out / "place.json").write_text(json.dumps(T.cells) + "\n")
    (out / "nets.json").write_text(json.dumps(dict(ports=T.ports, nets=T.nets)) + "\n")
    print(json.dumps(tree["meta"], indent=1))
    return 0


def find_libdir(arg=None):
    for d in [arg, "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM", "~/.cache/opentallas/asap7_nldm",
              "~/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM"]:
        if d and Path(os.path.expanduser(d), "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz").is_file():
            return os.path.expanduser(d)
    raise SystemExit("die_clock: no ASAP7 NLDM lib dir (--libdir)")


def cmd_sta(a):
    d = Path(a.dir).resolve()
    libdir = find_libdir(a.libdir)
    sta = os.path.expanduser("~/.local/opentallas-tools/bin/sta")
    sta = sta if Path(sta).is_file() else "sta"
    for c in a.corner:
        tcl = d / f"sta_{c}.tcl"
        tcl.write_text(sta_tcl(d, c, libdir))
        t0 = time.time()
        with open(d / f"sta_{c}.log", "w") as lf:
            rc = subprocess.call([sta, "-no_splash", "-exit", str(tcl)], stdout=lf, stderr=subprocess.STDOUT)
        print(f"{c}: exit {rc} {time.time() - t0:.1f}s")
        if rc:
            return rc
    return 0


# ----------------------------------------------------------------------------------------------------------- balance
R_DRV_KOHM = 0.12                       # BUFx24 effective drive (ASSUMED; only scales the pad step, STA closes it)
STAGE_PS = 15.0                         # BUFx24 intrinsic (ASSUMED; only scales the pad step, STA closes it)


def load_tree(d):
    T = Tree()
    nj = json.loads((Path(d) / "nets.json").read_text())
    T.ports = [tuple(p) for p in nj["ports"]]
    T.nets = nj["nets"]
    T.cells = json.loads((Path(d) / "place.json").read_text())
    return T


def pad_step(T, tree, arrs, pads, damp=0.9, max_step_um=600.0, take_back=False):
    """one balance pass: every tap up to the latest tap of its leaf, every child subtree up to its latest sibling,
    by wire pads on the child's last leg segment (a tap's last chain segment).  arrs: [(tap arr, node arr)] per
    corner; the delta is the corner mean.  Returns the largest residual delta (ps) before this pass."""
    nets = {n["name"]: n for n in T.nets}
    leaf_taps = defaultdict(list)
    tap_pad = {t["port"]: t["pad_nets"] for t in tree["taps"]}
    for t in tree["taps"]:
        leaf_taps[t["leaf"]].append(t["port"])

    def tap_a(p):
        return sum(ta[p] for ta, _ in arrs) / len(arrs)
    memo = {}

    def smax(node):
        if node not in memo:
            v = [tap_a(p) for p in leaf_taps.get(node, ()) if all(p in ta for ta, _ in arrs)]
            v += [smax(k) for k, _ in tree["nodes"][node]["kids"]]
            memo[node] = max(v) if v else None
        return memo[node]
    sys.setrecursionlimit(100000)
    smax(tree["root_node"])
    worst = 0.0

    def sens(net, bi):
        L, layer, load, geo = nets[net]["branches"][bi]
        L += pads.get((net, bi), 0.0)
        r, c = layer_rc(layer, geo)
        cl = TAP_LOAD_FF if load.startswith("port:") else BUF_CIN_FF
        if L > max(geo, PAD_CAP_UM) + SNAKE_UM:      # the pad is now delay stages: one stage per SNAKE_UM
            r2, c2 = layer_rc(layer, min(geo, SNAKE_UM))
            S_ = SNAKE_UM
            return (STAGE_PS + R_DRV_KOHM * c2 * S_ + r2 * c2 * S_ * S_ / 2 + r2 * S_ * BUF_CIN_FF) / S_
        return R_DRV_KOHM * c + r * c * L + r * cl

    def elen(net, bi):
        return nets[net]["branches"][bi][0] + pads.get((net, bi), 0.0)

    def add(targets, dps):
        """spread the pad over the leg / chain: always lengthen the currently shortest segment (keeps every segment
        short: slew), in steps of <= 50 um, until the delay deficit is covered."""
        targets = [tuple(t) for t in targets]
        need = damp * dps
        moved = 0.0
        while need > 1e-3 and moved < max_step_um * len(targets):
            net, bi = min(targets, key=lambda t: elen(*t))
            room = PAD_CAP_UM - elen(net, bi)
            if room > 1.0:                          # fill up to the cap first (normal NDR, slew)
                um = min(50.0, room, need / sens(net, bi))
            else:                                   # every segment full: grow the shortest
                um = min(50.0, need / sens(net, bi))
            pads[(net, bi)] = pads.get((net, bi), 0.0) + um
            need -= um * sens(net, bi)
            moved += um
    def removable(targets):
        return sum(pads.get(tuple(t), 0.0) * sens(*t) for t in targets)

    def rem(targets, dps):
        """take pad back (longest pad first) until the delay surplus is removed: pads are never a ratchet."""
        targets = [tuple(t) for t in targets]
        need = damp * dps
        while need > 1e-3:
            t = max(targets, key=lambda t: pads.get(t, 0.0))
            have = pads.get(t, 0.0)
            if have <= 1e-6:
                break
            um = min(50.0, have, need / sens(*t))
            pads[t] = have - um
            if pads[t] <= 1e-6:
                del pads[t]
            need -= um * sens(*t)
    # bottom-up: the level each node's members can all reach (the lowest common level once surplus pad is taken
    # back), then every member moves to it: kids by their leg pads, taps by their chain pads
    level = {}

    def members(node):
        out = [(level[k], targets) for k, targets in tree["nodes"][node]["kids"] if level.get(k) is not None]
        out += [(tap_a(p), tap_pad[p]) for p in leaf_taps.get(node, ()) if all(p in ta for ta, _ in arrs)]
        return out

    order = []

    def walk(node):
        for k, _ in tree["nodes"][node]["kids"]:
            walk(k)
        mm = members(node)
        level[node] = max((v - (removable(t) if take_back else 0.0) for v, t in mm), default=None) if mm else None
        if mm:
            level[node] = max(level[node], min(v for v, _ in mm))
            order.append(node)
    walk(tree["root_node"])
    for node in order:
        mm = members(node)
        vals = [v for v, _ in mm]
        worst = max(worst, max(vals) - min(vals))
        L = level[node]
        for v, t in mm:
            if L - v > 0.05:
                add(t, L - v)
            elif v - L > 0.05:
                rem(t, v - L)
    return worst


def cmd_run(a):
    """build + STA-driven wire-pad balance (iterations) + final STA + report: the full die clock step."""
    out = Path(a.out)
    cmd_build(a)
    T = load_tree(out)
    tree = json.loads((out / "tree.json").read_text())
    pads = {}
    hist = []
    best = None
    def emit(pads):
        E, st = expand_pads(T, pads)
        write_verilog(E, out / "ctree.v")
        write_spef(E, out / "ctree.spef")
        return st
    for it in range(a.iters + 1):
        st = emit(pads)
        rc = cmd_sta(argparse.Namespace(dir=str(out), corner=a.corner, libdir=a.libdir))
        if rc:
            return rc
        arrs = [read_arr(out / f"arr_{c}.txt") for c in a.corner]
        sk = {c: round(max(x[0].values()) - min(x[0].values()), 2) for c, x in zip(a.corner, arrs)}
        hist.append(dict(iter=it, tap_skew_ps=sk, pads=len(pads), pad_um=round(sum(pads.values()), 1), stages=st))
        print(json.dumps(hist[-1]))
        if best is None or max(sk.values()) < best[0]:
            best = (max(sk.values()), it, dict(pads))
        if it == a.iters or max(sk.values()) <= a.stop_ps:
            break
        pad_step(T, tree, [(x[0], x[3]) for x in arrs], pads, take_back=getattr(a, "take_back", False))
    if best[1] != hist[-1]["iter"]:                 # keep the best iteration (the loop may oscillate)
        pads = best[2]
        st = emit(pads)
        cmd_sta(argparse.Namespace(dir=str(out), corner=a.corner, libdir=a.libdir))
        hist.append(dict(iter=f"best={best[1]}", tap_skew_ps=best[0]))
    tree["meta"]["balance"] = hist
    tree["meta"]["pads"] = len(pads)
    tree["meta"]["pad_um"] = round(sum(pads.values()), 1)
    tree["meta"]["delay_stages"] = st
    (out / "tree.json").write_text(json.dumps(tree) + "\n")
    (out / "pads.json").write_text(json.dumps([[k[0], k[1], round(v, 3)] for k, v in sorted(pads.items())]) + "\n")
    return cmd_report(argparse.Namespace(dir=str(out), plan=a.plan))


# ------------------------------------------------------------------------------------------------------------ report
def read_arr(f):
    tarr, tmin, slew, narr = {}, {}, {}, {}
    for ln in Path(f).read_text().splitlines():
        x = ln.split()
        if len(x) < 4:
            continue
        try:
            v = [float(z) for z in x[2:]]
        except ValueError:
            continue
        if x[0] == "T":
            tarr[x[1]], tmin[x[1]] = v[0], v[1]
            if len(v) > 2:
                slew[x[1]] = v[2]
        elif x[0] == "N":
            narr[x[1]] = v[0]
    return tarr, tmin, slew, narr


def seam_pairs(P, taps_by_part):
    """{(launch port, capture port): bits} from every abutted port bit: nearest src-part tap / dst-part tap to the pin
    (the stand-in and kit nearest-tap rule)."""
    pairs = defaultdict(int)
    for pid, pr in P.ports.items():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if S.DIE_PART in (a, b) or a not in taps_by_part or b not in taps_by_part:
            continue
        ra = P.rect(a)
        f = pr["face"]
        memo = {}
        for _, _, c in P.port_pins(pid):
            q = round(c / 4.32)
            if q in memo:
                pairs[memo[q]] += 1
                continue
            pt = ((ra[2] if f == "E" else ra[0]), c) if f in "EW" else (c, (ra[3] if f == "N" else ra[1]))
            ta = min(taps_by_part[a], key=lambda t: abs(t["xy"][0] - pt[0]) + abs(t["xy"][1] - pt[1]))
            tb = min(taps_by_part[b], key=lambda t: abs(t["xy"][0] - pt[0]) + abs(t["xy"][1] - pt[1]))
            memo[q] = (ta["port"], tb["port"], pid)
            pairs[memo[q]] += 1
    return pairs


def intra_pairs(taps_by_part, pitch=400.0):
    """neighbouring taps of one partition (flops near a tap-cell border talk across taps): Manhattan <= 1.5 pitch."""
    out = []
    for part, tl in taps_by_part.items():
        for i in range(len(tl)):
            for j in range(i + 1, len(tl)):
                a, b = tl[i], tl[j]
                if abs(a["xy"][0] - b["xy"][0]) + abs(a["xy"][1] - b["xy"][1]) <= 1.5 * pitch:
                    out.append((a["port"], b["port"], part))
    return out


def pctl(v, q):
    if not v:
        return None
    v = sorted(v)
    return v[min(len(v) - 1, int(math.ceil(q * len(v))) - 1)]


def cmd_report(a):
    d = Path(a.dir)
    P = S.Plan(S.load(a.plan))
    tree = json.loads((d / "tree.json").read_text())
    taps = tree["taps"]
    by_port = {t["port"]: t for t in taps}
    taps_by_part = defaultdict(list)
    for t in taps:
        taps_by_part[t["part"]].append(t)
    paths = {t["port"]: t["path"] for t in taps}
    sp = seam_pairs(P, taps_by_part)
    ip = intra_pairs(taps_by_part, float(P.budgets.get("tap_pitch_um", 400.0)))
    res = dict(meta=tree["meta"], gate_ps=GATE_PS, target_ps=TARGET_PS, corners={})
    for corner in ("SS", "TT", "FF"):
        f = d / f"arr_{corner}.txt"
        if not f.is_file():
            continue
        tarr, tmin, slew, narr = read_arr(f)
        cellarr = {}
        for k, v in narr.items():
            cellarr[k] = v
        ins = sorted(tarr.values())
        cr = dict(taps=len(ins), insertion_max_ps=round(ins[-1], 2), insertion_min_ps=round(ins[0], 2),
                  tap_skew_ps=round(ins[-1] - ins[0], 2), tap_slew_max_ps=round(max(slew.values()), 2) if slew else None)
        early = [t for t in taps if t["early_ps"] > 0]
        if early:
            std = [tarr[t["port"]] for t in taps if t["early_ps"] == 0 and t["port"] in tarr]
            ref = max(std) if std else ins[-1]
            err = [abs((ref - tarr[t["port"]]) - t["early_ps"]) for t in early if t["port"] in tarr]
            cr["core_early_err_max_ps"] = round(max(err), 2) if err else None

        def lca_arr(pa, pb):
            A, B = paths[pa], paths[pb]
            k = 0
            while k < min(len(A), len(B)) and A[k] == B[k]:
                k += 1
            # deepest common NODE buffer with a measured arrival
            for c in reversed(A[:k]):
                if c in cellarr:
                    return c, cellarr[c]
            return None, 0.0

        def eff(port):
            # effective flop clock: a core tap's early shift is paid back by the core insertion (contract)
            return tarr[port] + (by_port[port]["early_ps"] if tree["meta"].get("core_early") == "pad" else 0.0)

        def rows_of(pairs, weight=None):
            rows = []
            for key in pairs:
                pa, pb = key[0], key[1]
                if pa not in tarr or pb not in tarr:
                    continue
                nom = eff(pb) - eff(pa)
                lc, la = lca_arr(pa, pb)
                ua, ub = tarr[pa] - la, tarr[pb] - la
                r = dict(launch=pa, capture=pb, where=key[2], nominal_ps=round(nom, 2), lca=lc,
                         uncommon_ps=round(max(ua, ub), 1), bits=(weight or {}).get(key, 1))
                for k in OCV:
                    r[f"ocv{int(k * 100)}_ps"] = round(max(abs(ub * (1 - k) - ua * (1 + k)), abs(ub * (1 + k) - ua * (1 - k))), 1)
                rows.append(r)
            return rows
        for nm, rows in (("seam", rows_of(list(sp), sp)), ("intra", rows_of(ip))):
            av = [abs(r["nominal_ps"]) for r in rows]
            bits = [r["bits"] for r in rows]
            s = dict(pairs=len(rows), bits=sum(bits), max_abs_ps=round(max(av), 2) if av else None,
                     max_pos_ps=round(max(r["nominal_ps"] for r in rows), 2) if rows else None,
                     min_neg_ps=round(min(r["nominal_ps"] for r in rows), 2) if rows else None,
                     p99_abs_ps=round(pctl(av, 0.99), 2) if av else None,
                     over_gate=sum(1 for x in av if x > GATE_PS), over_target=sum(1 for x in av if x > TARGET_PS))
            for k in OCV:
                key = f"ocv{int(k * 100)}_ps"
                v = [r[key] for r in rows]
                s[f"{key}_max_info"] = max(v) if v else None
                s[f"{key}_p99_info"] = pctl(v, 0.99)
            s["worst"] = sorted(rows, key=lambda r: -abs(r["nominal_ps"]))[:10]
            s["worst_ocv_info"] = sorted(rows, key=lambda r: -r[f"ocv{int(OCV[-1] * 100)}_ps"])[:5]
            cr[nm] = s
        res["corners"][corner] = cr
        mn = ins[0]
        br = dict(model="die_clock", corner=corner, core_early=tree["meta"].get("core_early"), parts={})
        for t in taps:
            if t["port"] in tarr:
                br["parts"].setdefault(t["part"], dict(taps={}))["taps"][t["tap"]] = dict(
                    offset_ps=round(eff(t["port"]) - mn, 3), arrival_ps=round(tarr[t["port"]], 3))
        (d / f"spine_{corner}.json").write_text(json.dumps(br) + "\n")
    v = {}
    for c in ("TT", "FF"):
        cr = res["corners"].get(c)
        if not cr:
            v[c] = "NOT RUN"
            continue
        m = max(cr["seam"]["max_abs_ps"] or 0, cr["intra"]["max_abs_ps"] or 0)
        v[c] = dict(pair_skew_max_ps=m, gate="PASS" if m <= GATE_PS else "FAIL",
                    target="MET" if m <= TARGET_PS else "MISSED")
    res["verdict"] = v
    (d / "clock_report.json").write_text(json.dumps(res, indent=1) + "\n")
    short = {c: {k: (x if not isinstance(x, dict) else {kk: vv for kk, vv in x.items() if kk not in ("worst", "worst_ocv_info")})
                 for k, x in cr.items()} for c, cr in res["corners"].items()}
    print(json.dumps(dict(verdict=v, corners=short), indent=1))
    return 0


# ------------------------------------------------------------------------------------------------------------ render
def cmd_render(a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    d = Path(a.dir)
    P = S.Plan(S.load(a.plan))
    cells = json.loads((d / "place.json").read_text())
    tree = json.loads((d / "tree.json").read_text())
    rep = json.loads((d / "clock_report.json").read_text()) if (d / "clock_report.json").is_file() else None
    fig, ax = plt.subplots(figsize=(14, 14 * P.H / P.W))
    for n in P.parts:
        x0, y0, x1, y1 = P.rect(n)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=0.3, ec="0.6"))
    for r in keepouts(P):
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="tan", ec="none", alpha=0.5))
    for k, nd in tree["nodes"].items():
        for kid, _ in nd.get("kids", []):
            pth = tree["nodes"][kid]["path"]
            leg = [c for c in pth[len(nd["path"]) - 1:] if c in cells]
            for u, w in zip(leg, leg[1:]):
                L = abs(cells[u]["x"] - cells[w]["x"]) + abs(cells[u]["y"] - cells[w]["y"])
                ax.plot([cells[u]["x"], cells[w]["x"]], [cells[u]["y"], cells[w]["y"]], "-",
                        lw=1.2 if L > WIDE_UM else 0.5, c="tab:red" if L > WIDE_UM else "tab:blue")
    arr = {}
    if (d / "arr_TT.txt").is_file():
        arr = read_arr(d / "arr_TT.txt")[0]
    xs = [t["xy"][0] for t in tree["taps"]]
    ys = [t["xy"][1] for t in tree["taps"]]
    cs = [arr.get(t["port"], 0) for t in tree["taps"]]
    sc = ax.scatter(xs, ys, c=cs, s=3, cmap="viridis")
    if arr:
        fig.colorbar(sc, ax=ax, shrink=0.6, label="tap arrival TT (ps)")
    dm = [c for c in cells.values() if c["kind"] == "dummy"]
    ax.scatter([c["x"] for c in dm], [c["y"] for c in dm], s=2, c="r", marker="x")
    ax.set_xlim(0, P.W)
    ax.set_ylim(0, P.H)
    ax.set_aspect("equal")
    m = tree["meta"]
    t = (f"{Path(a.plan).parent.name}: die clock H-tree {m['levels']} levels (leaf {m['leaf_um']:g} um), "
         f"{m['taps']} taps, {m['cells']} cells, wire {m['wire_um'] / 1e6:.2f} m + pads {m.get('pad_um', 0) / 1e6:.2f} m; "
         f"red = hop > {WIDE_UM:g} um (4W NDR), x = dummy load")
    if rep and "TT" in rep["corners"]:
        cr = rep["corners"]["TT"]
        t += (f"\nTT insertion {cr['insertion_max_ps']} ps, tap skew {cr['tap_skew_ps']} ps, pair skew max seam "
              f"{cr['seam']['max_abs_ps']} / intra {cr['intra']['max_abs_ps']} ps, tap slew max {cr['tap_slew_max_ps']} ps")
    ax.set_title(t, fontsize=9)
    out = Path(a.out) if a.out else d / "die_clock.png"
    fig.savefig(out, dpi=a.dpi, bbox_inches="tight")
    print(out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("plan")
    b.add_argument("--out", required=True)
    b.add_argument("--leaf-um", type=float, default=1000.0)
    b.add_argument("--rep-um", type=float, default=450.0)
    b.add_argument("--core-early", choices=("off", "pad"), default="off")
    b.add_argument("--window", type=float, default=SPLIT_WINDOW)
    b.add_argument("--pad", choices=("sta", "level"), default="sta")
    b.add_argument("--aware-levels", type=int, default=AWARE_LEVELS)
    u = sub.add_parser("run")
    u.add_argument("plan")
    u.add_argument("--out", required=True)
    u.add_argument("--leaf-um", type=float, default=1000.0)
    u.add_argument("--rep-um", type=float, default=450.0)
    u.add_argument("--core-early", choices=("off", "pad"), default="off")
    u.add_argument("--window", type=float, default=SPLIT_WINDOW)
    u.add_argument("--pad", choices=("sta", "level"), default="sta")
    u.add_argument("--aware-levels", type=int, default=AWARE_LEVELS)
    u.add_argument("--corner", action="append")
    u.add_argument("--libdir")
    u.add_argument("--iters", type=int, default=10)
    u.add_argument("--take-back", action="store_true",
                   help="balance may take surplus pad back (lower insertion; oscillates on very unbalanced trees)")
    u.add_argument("--stop-ps", type=float, default=2.0)
    s = sub.add_parser("sta")
    s.add_argument("dir")
    s.add_argument("--corner", action="append")
    s.add_argument("--libdir")
    r = sub.add_parser("report")
    r.add_argument("dir")
    r.add_argument("--plan", required=True)
    g = sub.add_parser("render")
    g.add_argument("dir")
    g.add_argument("--plan", required=True)
    g.add_argument("--out")
    g.add_argument("--dpi", type=int, default=110)
    a = ap.parse_args(argv)
    if a.cmd in ("sta", "run") and not a.corner:
        a.corner = ["TT", "FF"]
    return dict(build=cmd_build, run=cmd_run, sta=cmd_sta, report=cmd_report, render=cmd_render)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
