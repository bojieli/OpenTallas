#!/usr/bin/env python3
"""DIE-LAYOUT-HBM LADDER (COORD ruling 11-11: 2x4 ladder approved, no growth; built as variant C, see README).

    python3 -I ladder.py TOOLS_DIR PLAN_DIR SPEC.json OUT_DIR

Opt-in die_plan transform on the HBM bank block (NE + NW, 8 bank partitions each):
  1. GEOMETRY  b000 keeps its full-height column next to the hub (type, cores and hub face unchanged); the other 7
     banks become a 2-row ladder over the rest of the block: top b001 b002 b003, bottom b010 b011 b012 b013 (SPEC:
     bottom-row height and the u seams, u = distance from the hub edge; every edge on the 4.32 lattice, seams chosen so
     no fixed neighbour window straddles a seam).  Block bbox, hub, io, N/S neighbours unchanged: no growth.
  2. CORES     hard cores of the 7 reshaped types re-packed on shelves (pack.py: lanes 34.56 um, 4.32 lattice, old x
     order kept inside a shelf).
  3. LANES     every lane run through the bank block is re-routed on the new abutment graph (lgeom.route: shortest
     Manhattan route, crossing points on shared edges); neighbour windows (hub, io, b1xx, su0x/su2x) are FIXED (never
     moved: they are other types' faces); bank-bank windows are allocated with lane_add.Builder.alloc (free gaps, plan
     face budget, guard 2 um); faces that need it get 4 face layers (3 layers: M7/M5+M6 on N/S, M6/M4+M5 on E/W; check.py faces rule: listed by
     both ends).  Crossed banks get ft slots (stations = ceil(route / ft_station_max), registers off every core
     +halo, lane_add resite solver when even spacing hits a core or a hop > reach).  Runs that only touch b000 and
     stay in b000 are kept byte-identical.
  4. LATENCY   every touched lane keeps its old cycles: pad = old cycles - new natural (ring links: stations -> 0,
     latency held by pads); a lane whose new natural exceeds its old cycles is reported (latency_up) and its
     latency group mates get the same cycles.
  5. STATIONS  internal stations of the reshaped types (and of b000 buses whose window moved) are regenerated with
     hub_repack.route_station (face end follows its bus window at the same fraction, core end follows its core;
     register count kept when the route allows it).
  6. taps follow cores; type clock/reset taps move to the nearest free lattice point of the scaled old spot; soft
     contents boxes = bbox of their hard cores (else scaled); die_ft_bands of reshaped types dropped (core layout gone).
All numbers are plan geometry: UNCHECKED until NUMBER-CHECK.  DO_NOT_COUNT.
"""
import collections
import copy
import hashlib
import json
import math
import os
import shutil
import sys
from pathlib import Path

TOOLS = sys.argv[1]
HERE = str(Path(__file__).resolve().parent)
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)
import schema as S          # noqa: E402
import lane_add as LA       # noqa: E402
import hub_repack as HR     # noqa: E402
import check as C           # noqa: E402
import lgeom as G           # noqa: E402
import runs as RU           # noqa: E402
import pack as PK           # noqa: E402
import placement_obstacles as PO   # noqa: E402

OPP = G.OPP
EPS = 1e-6
CAP_MARGIN = 0.96   # routing capacity share of an edge (fragmentation reserve)
CUT_DENS, CUT_FILL, CUT_PEN = 5.0, 0.5, 3000.0   # bank cut model for the router (tracks/um, fill, cost per 1000 over-bits)
LAT_W = 0.0003     # router cost per um of lateral travel per bit in a crossed bank (its cuts)
DENS_B000 = 6.2    # pins/um on the b000 east edges (face check allowance: 6/um + 2 pins per layer per 10 um)
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def r4(v):
    return round(float(v), 4)


def slot_of(t, bus):
    for s in t.get('ft_slots', []):
        if bus in (s['name'] + '_i', s['name'] + '_o'):
            return s
    return None


def bus_of(t, name):
    for b in t.get('buses', []):
        if b['name'] == name:
            return b
    return None


def type_window(P, part, df, win):
    return LA.to_type_window(P, part, df, win)


_FREEPTS = {}


def free_pts(B, part):
    """die-frame free lattice points of a partition: inside the rect (halo), off every placed core/macro + halo."""
    import numpy as np
    import station_resite as SR
    if part in _FREEPTS:
        return _FREEPTS[part]
    P, Gq, Hh = B.P, SR.G, SR.HALO
    x0, y0, x1, y1 = P.rect(part)
    xs = np.arange(math.ceil((x0 + Hh) / Gq), math.floor((x1 - Hh) / Gq) + 1) * Gq
    ys = np.arange(math.ceil((y0 + Hh) / Gq), math.floor((y1 - Hh) / Gq) + 1) * Gq
    m = np.ones((len(xs), len(ys)), bool)
    for bx0, by0, bx1, by1 in PO.placement_boxes(P.ptype(part), halo=Hh).values():
        c0, c1 = P.to_die(part, (bx0, by0)), P.to_die(part, (bx1, by1))
        ux0, ux1 = sorted((c0[0], c1[0])); uy0, uy1 = sorted((c0[1], c1[1]))
        m &= ~((xs[:, None] > ux0 - EPS) & (xs[:, None] < ux1 + EPS) & (ys[None, :] > uy0 - EPS)
               & (ys[None, :] < uy1 + EPS))
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    pts = np.stack([X[m], Y[m]], axis=1)
    _FREEPTS[part] = pts
    return pts


def chain_solve(B, slots, prev, nxt, reach, margin=8.0):
    """greedy register chain through the crossed banks (slot order): each bank >= max(1, k) registers on its free
    lattice, every hop (prev, regs..., nxt) <= reach - margin.  Returns [[die regs] per slot] or None."""
    import numpy as np
    R = reach - margin
    cur = np.array(prev, float)
    out = []
    for i, sl in enumerate(slots):
        pts = free_pts(B, sl[0])
        if len(pts) == 0:
            return None
        ex = np.array(LA.Builder.face_pt(B.P, sl[0], sl[5], sl[6]), float)       # exit face point
        last = i == len(slots) - 1
        tgt = np.array(nxt, float) if last else ex
        regs = []
        need = max(1, int(sl[8]))
        guard = 0
        while True:
            guard += 1
            if guard > 60:
                return None
            d_cur = np.abs(pts - cur).sum(axis=1)
            ok = d_cur <= R
            if not ok.any():
                return None
            d_t = np.abs(pts - tgt).sum(axis=1)
            remaining = need - len(regs)
            if remaining > 1:
                # spread: aim at the point a 1/(remaining) fraction of the way to the exit
                aim = cur + (ex - cur) / remaining
                cost = np.abs(pts - aim).sum(axis=1)
            else:
                cost = d_t
            j = int(np.where(ok, cost, 1e18).argmin())
            p = pts[j]
            regs.append((round(float(p[0]), 4), round(float(p[1]), 4)))
            cur = p
            if len(regs) >= need:
                if last:
                    if np.abs(cur - tgt).sum() <= R:
                        break
                else:
                    # the next bank must be reachable: some free point of it within R of cur
                    nb = free_pts(B, slots[i + 1][0])
                    if (np.abs(nb - cur).sum(axis=1) <= R).any() and np.abs(cur - ex).sum() <= R / 2:
                        break
        out.append(regs)
    return out


def _dil(m, r):
    out = m.copy()
    cur = m
    for _ in range(r):
        nxt = cur.copy()
        nxt[1:, :] |= cur[:-1, :]
        nxt[:-1, :] |= cur[1:, :]
        nxt[:, 1:] |= cur[:, :-1]
        nxt[:, :-1] |= cur[:, 1:]
        if (nxt == cur).all():
            break
        cur = nxt
    return out | cur


def chain_dp(B, slots, start, end, reach, margin=4.0, Gc=8.64, kmax=40):
    """minimum-register chain through the crossed banks in order: bank j gets >= need_j registers (need_j =
    max(1, ceil(route_j / ft_station_max))), registers on free 8.64-lattice points (off cores/macros + 4.32 halo),
    every hop (start, regs..., end) <= reach - margin (Manhattan).  Layered reachability + back-trace toward the
    straight line.  Returns [[die regs] per slot] or None."""
    import numpy as np
    import station_resite as SR
    P = B.P
    R = reach - margin
    rs = int(R // Gc)
    parts_ = [sl[0] for sl in slots]
    need = [max(1, int(math.ceil(sl[10] / B.smax - 1e-9))) for sl in slots]
    rects = [P.rect(p) for p in parts_]
    X0 = math.floor(min(min(r[0] for r in rects), start[0], end[0]) / Gc) * Gc
    Y0 = math.floor(min(min(r[1] for r in rects), start[1], end[1]) / Gc) * Gc
    X1 = max(max(r[2] for r in rects), start[0], end[0])
    Y1 = max(max(r[3] for r in rects), start[1], end[1])
    xs = X0 + np.arange(int((X1 - X0) / Gc) + 2) * Gc
    ys = Y0 + np.arange(int((Y1 - Y0) / Gc) + 2) * Gc
    H = SR.HALO
    F = []
    for p, (x0, y0, x1, y1) in zip(parts_, rects):
        m = (xs[:, None] > x0 + H) & (xs[:, None] < x1 - H) & (ys[None, :] > y0 + H) & (ys[None, :] < y1 - H)
        for bx0, by0, bx1, by1 in PO.placement_boxes(P.ptype(p), halo=H).values():
            c0, c1 = P.to_die(p, (bx0, by0)), P.to_die(p, (bx1, by1))
            ux0, ux1 = sorted((c0[0], c1[0])); uy0, uy1 = sorted((c0[1], c1[1]))
            m &= ~((xs[:, None] > ux0 - EPS) & (xs[:, None] < ux1 + EPS) & (ys[None, :] > uy0 - EPS)
                   & (ys[None, :] < uy1 + EPS))
        F.append(m)
    ds = np.abs(xs[:, None] - start[0]) + np.abs(ys[None, :] - start[1])
    de = np.abs(xs[:, None] - end[0]) + np.abs(ys[None, :] - end[1])
    states = [(j, c) for j in range(len(slots)) for c in range(1, need[j] + 1)]
    sidx = {s_: i for i, s_ in enumerate(states)}

    def preds(j, c):
        out = []
        if c > 1:
            out.append((j, c - 1))
        if c == need[j]:
            out.append((j, c))
        if c == 1 and j > 0:
            out.append((j - 1, need[j - 1]))
        return out
    layers = []
    cur = {s_: None for s_ in states}
    cur[(0, 1)] = F[0] & (ds <= R)
    layers.append(cur)
    fin = (len(slots) - 1, need[-1])
    K = None
    for k in range(1, kmax + 1):
        L = layers[-1]
        if L.get(fin) is not None and (L[fin] & (de <= R)).any():
            K = k
            break
        nxt = {}
        dil = {s_: _dil(m, rs) for s_, m in L.items() if m is not None and m.any()}
        for (j, c) in states:
            acc = None
            for pq in preds(j, c):
                if pq in dil:
                    acc = dil[pq] if acc is None else (acc | dil[pq])
            nxt[(j, c)] = (F[j] & acc) if acc is not None else None
        layers.append(nxt)
    if K is None:
        return None
    # back-trace
    tot = K
    m = layers[K - 1][fin] & (de <= R)
    st_ = fin
    i, jx = np.unravel_index(np.where(m, de, 1e20).argmin(), m.shape)
    seq = [(st_, (int(i), int(jx)))]
    for k in range(K - 2, -1, -1):
        cx, cy = xs[seq[-1][1][0]], ys[seq[-1][1][1]]
        near = (np.abs(xs[:, None] - cx) + np.abs(ys[None, :] - cy)) <= R + 1e-6
        tx = start[0] + (end[0] - start[0]) * (k + 1) / (tot + 1)
        ty = start[1] + (end[1] - start[1]) * (k + 1) / (tot + 1)
        cost = np.abs(xs[:, None] - tx) + np.abs(ys[None, :] - ty)
        best = None
        for pq in preds(*seq[-1][0]):
            mm = layers[k].get(pq)
            if mm is None:
                continue
            g = mm & near
            for _, q in seq:
                g[q] = False
            if not g.any():
                continue
            i, jx = np.unravel_index(np.where(g, cost, 1e20).argmin(), g.shape)
            c = cost[i, jx]
            if best is None or c < best[0]:
                best = (c, pq, (int(i), int(jx)))
        if best is None:
            return None
        seq.append((best[1], best[2]))
    seq = seq[::-1]
    out = [[] for _ in slots]
    for (j, c), (i, jx) in seq:
        out[j].append((round(float(xs[i]), 4), round(float(ys[jx]), 4)))
    if any(not o for o in out):
        return None
    pts = [tuple(start)] + [q for o in out for q in o] + [tuple(end)]
    if max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])) > reach + 1e-6:
        return None
    return out


def slot_dp(B, part, a, hw, b, m_min, reach=405.0, margin=6.0, Gc=8.64, mmax=30):
    """registers of one crossed slot under the check.py station model: S0 sits on the input pins (regs_um[0] is the
    input site), S1..Sm are placed here on free 8.64-lattice points of `part` (off cores/macros + 4.32 halo) with
    every input bit -> S1 <= reach (window half-length hw added), Si -> Si+1 <= reach and Sm -> output pin <= reach,
    m >= m_min (R3: route / stations <= ft_station_max).  Returns [die points S1..Sm] or None."""
    import numpy as np
    import station_resite as SR
    P = B.P
    R = reach - margin
    if m_min <= 0 and abs(a[0] - b[0]) + abs(a[1] - b[1]) <= R:
        return []
    x0, y0, x1, y1 = P.rect(part)
    H = SR.HALO
    xs = np.arange(math.ceil((x0 + H) / Gc), math.floor((x1 - H) / Gc) + 1) * Gc
    ys = np.arange(math.ceil((y0 + H) / Gc), math.floor((y1 - H) / Gc) + 1) * Gc
    F = np.ones((len(xs), len(ys)), bool)
    for bx0, by0, bx1, by1 in PO.placement_boxes(P.ptype(part), halo=H).values():
        c0, c1 = P.to_die(part, (bx0, by0)), P.to_die(part, (bx1, by1))
        ux0, ux1 = sorted((c0[0], c1[0])); uy0, uy1 = sorted((c0[1], c1[1]))
        F &= ~((xs[:, None] > ux0 - EPS) & (xs[:, None] < ux1 + EPS) & (ys[None, :] > uy0 - EPS)
               & (ys[None, :] < uy1 + EPS))
    da = np.abs(xs[:, None] - a[0]) + np.abs(ys[None, :] - a[1])
    db = np.abs(xs[:, None] - b[0]) + np.abs(ys[None, :] - b[1])
    rs = int(R // Gc)
    layers = [F & (da <= R - hw)]
    if not layers[0].any():
        return None
    m = None
    for k in range(1, mmax + 1):
        if k >= max(1, m_min) and (layers[-1] & (db <= R)).any():
            m = k
            break
        layers.append(F & _dil(layers[-1], rs))
    if m is None:
        return None
    cur_m = layers[m - 1] & (db <= R)
    i, j = np.unravel_index(np.where(cur_m, db, 1e20).argmin(), cur_m.shape)
    seq = [(int(i), int(j))]
    for k in range(m - 2, -1, -1):
        cx, cy = xs[seq[-1][0]], ys[seq[-1][1]]
        g = layers[k] & ((np.abs(xs[:, None] - cx) + np.abs(ys[None, :] - cy)) <= R + 1e-6)
        for q in seq:
            g[q] = False
        if not g.any():
            return None
        tx = a[0] + (b[0] - a[0]) * (k + 1) / (m + 1)
        ty = a[1] + (b[1] - a[1]) * (k + 1) / (m + 1)
        cost = np.abs(xs[:, None] - tx) + np.abs(ys[None, :] - ty)
        i, j = np.unravel_index(np.where(g, cost, 1e20).argmin(), g.shape)
        seq.append((int(i), int(j)))
    return [(round(float(xs[i]), 4), round(float(ys[j]), 4)) for i, j in seq[::-1]]


INSET = {'E': (-1.0, 0.0), 'W': (1.0, 0.0), 'N': (0.0, -1.0), 'S': (0.0, 1.0)}


def solve_slot(B, part, din, win_in, dout, win_out):
    """(stations, die regs incl. the S0 input site) for one crossed slot, or None."""
    a = LA.Builder.face_pt(B.P, part, din, win_in)
    b = LA.Builder.face_pt(B.P, part, dout, win_out)
    hw = abs(win_in[1] - win_in[0]) / 2.0
    k, seg, Lr = B.stations_for(part, din, win_in, dout, win_out)
    s0 = (a[0] + INSET[din][0], a[1] + INSET[din][1])
    for extra in range(0, 4):
        got = slot_dp(B, part, a, hw, b, k - 1 + extra)
        if got is not None:
            return 1 + len(got), [s0] + got, Lr
    return None


def pack_edge(items, lo, hi, guard=2.0):
    """1-D window packing on one edge: items = [dict(key, len, want (centre or None), w (bits))]; order by want with
    the free items (want None) inserted where they cost least; positions by weighted isotonic regression (PAV) on the
    shifted starts, clamped into [lo, hi].  Returns {key: (start, end)} or None if they do not fit."""
    import itertools
    # free items (no wanted height) get a near-zero weight pull to the edge middle: no permutation search
    items = [dict(it, want=(lo + hi) / 2, w=0.001) if it['want'] is None else it for it in items]
    fixed = sorted(items, key=lambda it: it['want'])
    free = []
    total = sum(it['len'] for it in items) + guard * (len(items) + 1)
    if total > hi - lo:
        return ('total', total, hi - lo)

    def solve(order):
        n = len(order)
        off, acc = [], lo + guard
        for it in order:
            off.append(acc)
            acc += it['len'] + guard
        # q_i = start_i - (off_i - lo - guard) non-decreasing; target start = want - len/2
        tgt, wt = [], []
        for i, it in enumerate(order):
            if it['want'] is None:
                tgt.append(None); wt.append(0.0)
            else:
                tgt.append(it['want'] - it['len'] / 2 - (off[i] - lo - guard)); wt.append(float(it['w']) + 1.0)
        blocks = []                                   # [sum_w, sum_wt, count]
        for i in range(n):
            if wt[i] == 0.0:
                blocks.append([0.0, 0.0, 1])
            else:
                blocks.append([wt[i], wt[i] * tgt[i], 1])
            while len(blocks) > 1:
                a_, b_ = blocks[-2], blocks[-1]
                ma = a_[1] / a_[0] if a_[0] else None
                mb = b_[1] / b_[0] if b_[0] else None
                if ma is not None and mb is not None and ma > mb:
                    blocks[-2:] = [[a_[0] + b_[0], a_[1] + b_[1], a_[2] + b_[2]]]
                else:
                    break
        q, last = [], None
        for bw, bs, c in blocks:
            m = bs / bw if bw else last
            q += [m] * c
            if m is not None:
                last = m
        # fill leading Nones, enforce monotone + bounds
        first = next((v for v in q if v is not None), lo)
        qq, cur = [], lo
        span_max = hi - (off[-1] - lo - guard) - order[-1]['len'] - guard   # max q (all share the shift)
        for v in q:
            v = first if v is None else v
            v = max(v, cur, lo + guard)
            cur = v
            qq.append(v)
        qq = [min(v, span_max) for v in qq]
        for i in range(1, n):
            qq[i] = max(qq[i], qq[i - 1])
        pos = {}
        cost = 0.0
        for i, it in enumerate(order):
            st = qq[i] + (off[i] - lo - guard)
            st = math.ceil(st / 0.016 - 1e-9) * 0.016
            pos[it['key']] = (round(st, 4), round(st + it['len'], 4))
            if it['want'] is not None:
                cost += it['w'] * abs(st + it['len'] / 2 - it['want'])
        if any(it['w'] < 0.01 for it in order):
            pass
        return cost, pos
    best = None
    nf = len(fixed)
    for slots_ in itertools.combinations(range(nf + len(free)), len(free)):
        for perm in itertools.permutations(free):
            order, fi, pi = [], 0, 0
            for i in range(nf + len(free)):
                if i in slots_:
                    order.append(perm[pi]); pi += 1
                else:
                    order.append(fixed[fi]); fi += 1
            got = solve(order)
            if best is None or got[0] < best[0]:
                best = got
    if best is None:
        return None
    pos = best[1]
    ks = sorted(pos.values())
    for (a, b), (c, d) in zip(ks, ks[1:]):
        if c < b + guard - 0.05 or a < lo - 1e-6 or d > hi + 1e-6:
            return ('bad', a, b, c, d)
    return pos


def main():
    plan_dir, spec_path, out_dir = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    raw = json.loads((plan_dir / 'die_plan.json').read_text())
    src_sha = hashlib.sha256((plan_dir / 'die_plan.json').read_bytes()).hexdigest()
    spec = json.loads(spec_path.read_text())
    P0 = S.Plan(copy.deepcopy(raw))
    T = raw['partition_types']
    parts = {p['name']: p for p in raw['partitions']}
    portmap = {p['id']: p for p in raw['ports']}
    lanes = {l['id']: l for l in raw['lanes']}
    lat = raw['latency']['lanes']
    rep = dict(schema='opentallas.die_layout_hbm.ladder.v1', source_plan_sha256=src_sha, spec=spec, runs=[],
               latency_up=[], failed=[], types={}, stations={})

    # ------------------------------------------------------------------ 1. geometry + routes
    newR = {}
    for side in ('NE', 'NW'):
        newR.update(G.rects(side, spec[side]))
    reshaped = sorted(n for n in newR if not n.endswith('b000'))
    RR = RU.runs(P0, S)
    for r in RR:
        R = {k: v for k, v in newR.items() if k.startswith(r['side'])}
        if r['start'][0] == 'bank':
            sb = r['start'][1]
            x0, y0, x1, y1 = R[sb]
            sp = ((x0 + x1) / 2, (y0 + y1) / 2)
        else:
            _, part, nf, win, pid = r['start']
            sp = RU.win_point(P0, part, nf, win)
            sb = RU.entry_bank(R, nf, win, sp)
        if r['end'][0] == 'bank':
            eb = r['end'][1]
            x0, y0, x1, y1 = R[eb]
            ep = ((x0 + x1) / 2, (y0 + y1) / 2)
        else:
            _, part, nf, win, pid = r['end']
            ep = RU.win_point(P0, part, nf, win)
            eb = RU.entry_bank(R, nf, win, ep)
        if sb is None or eb is None:
            raise SystemExit(f"{r['lane']}: neighbour window straddles a ladder seam ({r['start'][:2]} {r['end'][:2]})")
        sf = OPP[r['start'][2]] if r['start'][0] == 'win' else None
        ef = OPP[r['end'][2]] if r['end'][0] == 'win' else None
        r['sf'], r['ef'] = sf, ef
        got = G.route(R, sb, sp, eb, ep, start_is_bank=r['start'][0] == 'bank', end_is_bank=r['end'][0] == 'bank',
                      start_face=sf, end_face=ef)
        if got is None:      # e.g. a same-side dip with one bank: handled as a dip below
            got = (0.0, [sb], [])
        cost, path, pts = got
        r.update(path=path, pts=pts, sp=sp, ep=ep)
        b0 = f"{r['side']}_b000"
        r['keep'] = (r['run'] == [b0] and path == [b0])
        r['dip'] = False
        if r['start'][0] == 'win' and r['end'][0] == 'win' and r['start'][2] == r['end'][2] and \
                LA.shared_edge(P0, r['start'][1], r['end'][1]):
            # both neighbours on the same side of the block and abutting each other: the lane only dips into the
            # bank block -> direct neighbour-to-neighbour hop on their shared edge (no bank crossing)
            r['dip'], r['keep'] = True, False
    keep = [r for r in RR if r['keep']]
    todo = [r for r in RR if not r['keep']]
    log(f'runs {len(RR)}: kept {len(keep)} (b000 only), rebuilt {len(todo)}')

    # capacity-aware re-route (face budget 6 pins/um on 2 layers; the b000 east edges at DENS_B000, inside the
    # check.py faces allowance 6 + 2 per layer per 10 um): direct runs first (one choice), then crossing runs by width
    def per_of(a, b):
        return DENS_B000 if (a.endswith('b000') or b.endswith('b000')) else 6.0
    cap = {}
    for side in ('NE', 'NW'):
        names = [k for k in newR if k.startswith(side)]
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                e = G.shared_edge(newR[a], newR[b])
                if e:
                    if a.endswith('b000') or b.endswith('b000'):
                        cap[tuple(sorted((a, b)))] = e[2] - e[1] - 2.0 - 30.0   # um of window + guard (pack_edge)
                    else:
                        cap[tuple(sorted((a, b)))] = (e[2] - e[1] - 4.0) * per_of(a, b) * CAP_MARGIN

    def need_on(a, b, w):
        if a.endswith('b000') or b.endswith('b000'):
            df_ = G.shared_edge(newR[a], newR[b])[0]
            lay = LA.face_layers(P0, a, df_)
            return S.window_for(0.0, w + 1, lay, P0.layers, per_um=per_of(a, b) * len(lay) / 2.0,
                                track_max=float(P0.budgets.get('pin_track_max', 0.6))) + 2.0
        return w + 1 + 2.0 * 6.0

    def ncross(r):
        return len(r['path']) - (r['start'][0] == 'bank') - (r['end'][0] == 'bank')

    # bank cut load (check.py cuts, limit 0.6 of the free tracks): a crossed bank's slot travel |dx| loads its
    # vertical cuts, |dy| its horizontal cuts; capacity ~ CUT_DENS tracks/um x the bank extent x CUT_FILL
    cutload = collections.defaultdict(float)

    def cut_terms(u, p, q, w):
        x0, y0, x1, y1 = newR[u]
        out = []
        if abs(p[0] - q[0]) > 1.0:
            out.append(((u, 'v'), w * abs(p[0] - q[0]) / (x1 - x0), CUT_DENS * (y1 - y0) * CUT_FILL))
        if abs(p[1] - q[1]) > 1.0:
            out.append(((u, 'h'), w * abs(p[1] - q[1]) / (y1 - y0), CUT_DENS * (x1 - x0) * CUT_FILL))
        return out

    def make_pen(w):
        def pen(u, p, q):
            c = 0.0
            for k, add, capb in cut_terms(u, p, q, w):
                over = max(0.0, cutload[k] + add - capb) - max(0.0, cutload[k] - capb)
                c += CUT_PEN * over / 1000.0 + 0.05 * add * cutload[k] / capb
            return c
        return pen

    def add_load(r):
        pts = [r['sp']] + list(r['pts']) + [r['ep']]
        for i, u in enumerate(r['path']):
            if (i == 0 and r['start'][0] == 'bank') or (i == len(r['path']) - 1 and r['end'][0] == 'bank'):
                continue
            for k, add, capb in cut_terms(u, pts[i], pts[i + 1], r['width']):
                cutload[k] += add
    for r in sorted([r for r in todo if not r['dip']], key=lambda r: (ncross(r) > 0, -r['width'])):
        avoid = {e for e, c in cap.items() if c < need_on(e[0], e[1], r['width'])}
        Rs = {k_: v_ for k_, v_ in newR.items() if k_.startswith(r['side'])}
        got = G.route(Rs, r['path'][0], r['sp'], r['path'][-1], r['ep'], start_is_bank=r['start'][0] == 'bank',
                      end_is_bank=r['end'][0] == 'bank', avoid=avoid, start_face=r['sf'], end_face=r['ef'],
                      width=r['width'], lat_w=LAT_W, seg_pen=make_pen(r['width']))
        if got is None:
            rep.setdefault('over_capacity', []).append(dict(lane=r['lane'], width=r['width'], path=r['path']))
        else:
            r['path'], r['pts'] = got[1], got[2]
        add_load(r)
        for a_, b_ in zip(r['path'], r['path'][1:]):
            cap[tuple(sorted((a_, b_)))] -= need_on(a_, b_, r['width'])
    rep['cut_load'] = {f'{k[0]}.{k[1]}': round(v) for k, v in sorted(cutload.items())}
    log('cut load (bit-fraction):', rep['cut_load'])
    rep['edge_slack_bits'] = {f'{a}|{b}': round(c) for (a, b), c in sorted(cap.items())}
    log('edge slack (bits):', rep['edge_slack_bits'])

    # ------------------------------------------------------------------ 2. remove the rebuilt runs' bank-side objects
    old_bus = {}            # (part, bus) -> copy of the old bus (face/window) for internal station remap
    for n in newR:
        for b in T[parts[n]['type']].get('buses', []):
            old_bus[(n, b['name'])] = copy.deepcopy(b)
    old_outline = {n: tuple(T[parts[n]['type']]['outline_um']) for n in newR}
    old_cores = {n: {h['inst']: tuple(h['origin_um']) + tuple(h['outline_um'])
                     for h in T[parts[n]['type']].get('hard_cores', [])} for n in newR}
    drop_ports = set()
    end_bus = {}            # (part, bus) -> run (end buses re-sited)
    del_slots = collections.defaultdict(set)
    for r in todo:
        ln = lanes[r['lane']]
        ids = ln['ports'][r['i0']:r['i1']]
        drop_ports.update(ids)
        for pid in ids:
            pr = portmap[pid]
            for sd in ('src', 'dst'):
                part, bus = pr[sd]['part'], pr[sd]['bus']
                if part not in newR:
                    continue
                t = T[parts[part]['type']]
                s = slot_of(t, bus)
                if s is not None:
                    del_slots[part].add(s['name'])
                elif bus_of(t, bus) is not None:
                    end_bus[(part, bus)] = r
                else:
                    raise SystemExit(f'{pid}: {part}.{bus} not found')
    for part, names in del_slots.items():
        t = T[parts[part]['type']]
        t['ft_slots'] = [s for s in t.get('ft_slots', []) if s['name'] not in names]
    log(f'dropped {len(drop_ports)} ports, {sum(len(v) for v in del_slots.values())} ft slots; '
        f'{len(end_bus)} end buses to re-site')

    # ------------------------------------------------------------------ 3. reshape + core re-pack
    shift = {}              # (part, inst) -> (dx, dy) type frame
    streets = {}
    for n in reshaped:
        t = T[parts[n]['type']]
        x0, y0, x1, y1 = newR[n]
        Wn, Hn = r4(x1 - x0), r4(y1 - y0)
        t['outline_um'] = [Wn, Hn]
        parts[n]['origin_um'] = [r4(x0), r4(y0)]
        cores = [dict(inst=h['inst'], w=h['outline_um'][0], h=h['outline_um'][1], ocx=h['origin_um'][0])
                 for h in t.get('hard_cores', [])]
        got = PK.pack(Wn, Hn, cores)
        if got is None:
            raise SystemExit(f'{n}: cores do not fit {Wn}x{Hn}')
        place, info = got
        for h in t['hard_cores']:
            nx, ny = place[h['inst']]
            shift[(n, h['inst'])] = (nx - h['origin_um'][0], ny - h['origin_um'][1])
            h['origin_um'] = [r4(nx), r4(ny)]
        streets[n] = info
        ow, oh = old_outline[n]
        rep['types'][n] = dict(type=parts[n]['type'], old_outline=[ow, oh], outline=[Wn, Hn], origin=[r4(x0), r4(y0)],
                               cores=len(cores), shelves=info['shelves'], lane_um=info['lane_um'])
        t['note'] = (t.get('note', '') + f' | DIE-LAYOUT-HBM LADDER 11-11: outline {ow}x{oh} -> {Wn}x{Hn} '
                     f'(bank block 2-row ladder, b000 column kept), {len(cores)} hard cores re-packed on '
                     f'{info["shelves"]} shelves ({info["lane_um"]} um streets)').strip(' |')
        if t.get('die_ft_bands'):
            t['note'] += f' | die_ft_bands ({len(t["die_ft_bands"])}) dropped: their core layout is gone'
            rep['types'][n]['die_ft_bands_dropped'] = len(t['die_ft_bands'])
            del t['die_ft_bands']

    # ------------------------------------------------------------------ 4. lanes
    stash_lanes = {}
    touched = sorted({r['lane'] for r in todo})
    for lid in touched:
        stash_lanes[lid] = lanes[lid]
    tl_ports = {pid for lid in touched for pid in lanes[lid]['ports']}
    stash_ports = {pid: portmap[pid] for pid in tl_ports}
    raw['lanes'] = [l for l in raw['lanes'] if l['id'] not in stash_lanes]
    raw['ports'] = [p for p in raw['ports'] if p['id'] not in tl_ports]
    B = LA.Builder(raw, guard_um=2.0)
    P = B.P
    _alloc0 = B.alloc

    def alloc_d(u, v, width, prefer=None):
        per = per_of(u, v) if (u in newR and v in newR) else 6.0
        B.pins_need = lambda w, layers: (w + 1, per * len(layers) / 2.0)
        try:
            return _alloc0(u, v, width, prefer=prefer)
        finally:
            del B.pins_need
    B.alloc = alloc_d
    # fixed neighbour windows pre-reserved on the bank faces
    for r in todo:
        for key in ('start', 'end'):
            e = r[key]
            if e[0] != 'win':
                continue
            _, nb, nf, win, pid = e
            bank = r['path'][0] if key == 'start' else r['path'][-1]
            B.taken[(bank, OPP[nf])].append(tuple(win))
    new_ports_of = {}
    # ---- dips: direct neighbour-to-neighbour hop
    nb_old_bus = {}
    for r in [r for r in todo if r['dip']]:
        lid, width = r['lane'], r['width']
        X, Y = r['start'][1], r['end'][1]
        opx, opy = stash_ports[r['start'][4]], stash_ports[r['end'][4]]
        xb, yb = opx['src']['bus'], opy['dst']['bus']
        df, lo, hi = LA.shared_edge(P, X, Y)
        line = r['sp'][1] if r['start'][2] in 'NS' else r['sp'][0]     # the block-side end of the X|Y edge
        got = B.alloc(X, Y, width, prefer=min(max(line, lo + 30.0), hi - 30.0))
        if got is None:
            rep['failed'].append(dict(lane=lid, why=f'dip: no free window {X}|{Y}', width=width))
            continue
        df, win, layers = got
        for part, bus, face in ((X, xb, df), (Y, yb, OPP[df])):
            t = T[parts[part]['type']]
            tf, tw, flip = type_window(P, part, face, win)
            o = 'lsb_high' if flip else 'lsb_low'
            sl = slot_of(t, bus)
            if sl is not None:
                stem = 'out' if bus.endswith('_o') else 'in'
                sl[stem + '_face'], sl[stem + '_window_um'], sl[stem + '_layers'], sl[stem + '_order'] = \
                    tf, tw, list(layers), o
                # re-solve this slot's registers on its new route
                fi, wi, li, _ = P.geom_to_die(part, (sl['in_face'], sl['in_window_um'], sl['in_layers'], 'lsb_low'))
                fo, wo, lo2, _ = P.geom_to_die(part, (sl['out_face'], sl['out_window_um'], sl['out_layers'], 'lsb_low'))
                got_ = solve_slot(B, part, fi, wi, fo, wo)
                if got_ is None:
                    rep['failed'].append(dict(lane=lid, why=f'dip: no station chain in {part}', width=width))
                    continue
                regs = [got_[1]]
                sl['stations'] = len(regs[0])
                sl['regs_um'] = [[r4(v) for v in P.to_type(part, q)] for q in regs[0]]
                for kk in ('bit_sites_um', 'bit_site_cell_um'):
                    sl.pop(kk, None)
                sl['note'] = (sl.get('note', '') + f' | DIE-LAYOUT-HBM LADDER 11-11: {lid} dip removed, '
                              f'{stem} window on the {X}|{Y} edge, {len(regs[0])} station(s)').strip(' |')
            else:
                bb = bus_of(t, bus)
                nb_old_bus[(part, bus)] = copy.deepcopy(bb)
                bb['face'], bb['window_um'], bb['layers'], bb['order'] = tf, tw, list(layers), o
                bb['note'] = (bb.get('note', '') + f' | DIE-LAYOUT-HBM LADDER 11-11: {lid} dip removed, window on '
                              f'the {X}|{Y} edge').strip(' |')
        nid = 50
        while f'{lid}_{nid}' in portmap or f'{lid}_{nid}' in stash_ports:
            nid += 1
        newp = [dict(id=f'{lid}_{nid}', src=dict(part=X, bus=xb), dst=dict(part=Y, bus=yb), width=width,
                     kind=opx.get('kind', 'data'))]
        new_ports_of[(lid, r['i0'])] = (r, newp)
        rep.setdefault('dips', []).append(dict(lane=lid, old_run=r['run'], edge=f'{X}|{Y}', face=df,
                                               window_um=[r4(win[0]), r4(win[1])], layers=layers))
        log(f'dip {lid}: {X}->{Y} direct on {df} {win}')
    todo = [r for r in todo if not r['dip']]

    def n_crossed(r):
        n = len(r['path'])
        return n - (r['start'][0] == 'bank') - (r['end'][0] == 'bank')
    # phase A: runs with crossed banks (window position sets their stations), widest first; phase B: direct
    # bank-to-bank / bank-to-neighbour runs (no station: position is free), placed in what is left
    big = [r for r in todo if n_crossed(r) == 0 and r['width'] >= 1000 and len(r['path']) == 2]
    order = sorted(big, key=lambda r: -r['width']) + \
        sorted([r for r in todo if n_crossed(r) > 0], key=lambda r: -r['width']) + \
        sorted([r for r in todo if n_crossed(r) == 0 and r not in big], key=lambda r: -r['width'])
    # phase-A crossing preferences per edge (where the transits want to cross)
    want = collections.defaultdict(list)
    for r in todo:
        if n_crossed(r) == 0:
            continue
        for k, (u, v) in enumerate(zip(r['path'], r['path'][1:])):
            e = G.shared_edge(newR[u], newR[v])
            pt = r['pts'][k]
            lay_ = LA.face_layers(P, u, e[0])
            pn_, per_ = B.pins_need(r['width'], lay_)
            lw_ = S.window_for(0.0, pn_, lay_, P.layers, per_um=per_, track_max=float(P.budgets.get('pin_track_max', 0.6)))
            want[tuple(sorted((u, v)))].append(((pt[1] if e[0] in 'EW' else pt[0]), r['width'], lw_))
    # b000 east edges: every window placed together (pack_edge), transits at their hub / N / S entry height, the
    # ring windows in the gaps -> least travel along the narrow b000 column (its cuts)
    pre = {}
    for side in ('NE', 'NW'):
        b0 = f'{side}_b000'
        for nbk in (f'{side}_b001', f'{side}_b010'):
            e = G.shared_edge(newR[b0], newR[nbk])
            if not e:
                continue
            df0, lo, hi, line = e
            items = []
            for r in todo:
                if r['dip']:
                    continue
                pth = r['path']
                for k, (u, v) in enumerate(zip(pth, pth[1:])):
                    if {u, v} != {b0, nbk}:
                        continue
                    lay = LA.face_layers(P, u, G.shared_edge(newR[u], newR[v])[0])
                    Lw = S.window_for(0.0, r['width'] + 1, lay, P.layers, per_um=per_of(u, v) * len(lay) / 2.0,
                                      track_max=float(P.budgets.get('pin_track_max', 0.6)))
                    want = None
                    i0 = pth.index(b0)
                    crossed = not ((i0 == 0 and r['start'][0] == 'bank') or (i0 == len(pth) - 1 and r['end'][0] == 'bank'))
                    if crossed:
                        other = r['start'] if i0 == 0 else (r['end'] if i0 == len(pth) - 1 else None)
                        if other is not None and other[0] == 'win':
                            nf_ = other[2]
                            if OPP[nf_] in 'EW':
                                want = (other[3][0] + other[3][1]) / 2
                            else:
                                want = hi - 20.0 if OPP[nf_] == 'N' else lo + 20.0
                    items.append(dict(key=(id(r), (u, v)), len=Lw, want=want, w=r['width'], bits=r['width'],
                                      lane=r['lane']))
            got = pack_edge(items, lo, hi)
            if isinstance(got, tuple) and got[0] == 'total':
                # squeeze: windows at 6.3 pins/um (face allowance 6 + 2 per layer per 10 um = 6.4)
                for it in items:
                    u, v = it['key'][1]
                    lay = LA.face_layers(P, u, G.shared_edge(newR[u], newR[v])[0])
                    it['per'] = 6.3
                    it['len'] = S.window_for(0.0, it['bits'] + 1, lay, P.layers, per_um=6.3 * len(lay) / 2.0,
                                             track_max=float(P.budgets.get('pin_track_max', 0.6)))
                log(f'b000 edge {b0}|{nbk}: squeezed to 6.3/um')
                got = pack_edge(items, lo, hi)
            if got is not None and not isinstance(got, tuple):
                # PG-stripe aware lengths at the actual position (left to right, push on)
                tm = float(P.budgets.get('pin_track_max', 0.6))
                prev_end, fixd, ok_ = lo, {}, True
                for it in sorted(items, key=lambda it: got[it['key']][0]):
                    u, v = it['key'][1]
                    lay = LA.face_layers(P, u, G.shared_edge(newR[u], newR[v])[0])
                    st = max(got[it['key']][0], prev_end + 2.0)
                    st = math.ceil(st / 0.016 - 1e-9) * 0.016
                    per = it.get('per', DENS_B000) * len(lay) / 2.0
                    en = S.window_for(st, it['bits'] + 1, lay, P.layers, per_um=per, track_max=tm)
                    en = max(en, st + (got[it['key']][1] - got[it['key']][0]) if st == got[it['key']][0] else en)
                    fixd[it['key']] = (round(st, 4), round(en, 4))
                    prev_end = en
                if prev_end > hi - 1.0:
                    log(f'b000 edge {b0}|{nbk}: PG-aware lengths overflow by {prev_end - hi + 1.0:.1f} um')
                    got = ('pg', prev_end, hi)
                else:
                    got = fixd
            if got is None or isinstance(got, tuple):
                log(f'b000 edge {b0}|{nbk}: pack_edge does not fit ({len(items)} windows) {got}, alloc fallback')
                continue
            for it in items:
                pre[it['key']] = got[it['key']]
            log(f'b000 edge {b0}|{nbk}: {len(items)} windows packed '
                f'(travel {sum(it["w"] * abs((got[it["key"]][0] + got[it["key"]][1]) / 2 - it["want"]) for it in items if it["want"] is not None) / max(1, sum(it["w"] for it in items if it["want"] is not None)):.0f} um bit-mean)')
    # simulate phase A (crossing runs) to see where the transit windows land, then put the big direct windows in
    # what they leave (overlap with the simulated transit windows is the cost)
    for (rid, (u, v)), win in pre.items():
        df_ = G.shared_edge(newR[u], newR[v])[0]
        B.taken[(u, df_)].append(tuple(win))
        B.taken[(v, OPP[df_])].append(tuple(win))
    saved = copy.deepcopy(B.taken)
    sim = collections.defaultdict(list)
    for r in sorted([r for r in todo if n_crossed(r) > 0], key=lambda r: -r['width']):
        for k, (u, v) in enumerate(zip(r['path'], r['path'][1:])):
            e = G.shared_edge(newR[u], newR[v])
            pt = r['pts'][k]
            if (id(r), (u, v)) in pre:
                continue
            got = B.alloc(u, v, r['width'], prefer=(pt[1] if e[0] in 'EW' else pt[0]))
            if got is not None:
                sim[tuple(sorted((u, v)))].append(tuple(got[1]))
    B.taken = saved
    big_pref = {}
    for r in sorted(big, key=lambda r: -r['width']):
        u, v = r['path']
        df, lo, hi, line = G.shared_edge(newR[u], newR[v])
        layers = LA.face_layers(P, u, df)
        pins, per = r['width'] + 1, per_of(u, v) * len(layers) / 2.0
        Lw = S.window_for(0.0, pins, layers, P.layers, per_um=per, track_max=float(P.budgets.get('pin_track_max', 0.6)))
        occ = LA.face_intervals(P, u, df) + LA.face_intervals(P, v, OPP[df]) + B.taken[(u, df)] + \
            [w for (q, w) in big_pref.values() if q == (u, v) or q == (v, u)]
        best = None
        x = lo + 2.0
        while x + Lw <= hi - 2.0:
            if not any(a - 4.0 < x + Lw and x < b + 4.0 for a, b in occ):
                c = sum(max(0.0, min(b, x + Lw + 4.0) - max(a, x - 4.0)) for a, b in sim[tuple(sorted((u, v)))])
                c += 1e-3 * min(x - lo, hi - (x + Lw))
                if best is None or c < best[0]:
                    best = (c, x)
            x += 4.32
        if best is not None:
            big_pref[id(r)] = ((u, v), (best[1], best[1] + Lw))
    for r in order:
        lid, side, width = r['lane'], r['side'], r['width']
        path = r['path']
        hops = []              # (u, v, df(u side die face), win, layers, die_order or None, fixed_pid)
        if r['start'][0] == 'win':
            _, X, nf, win, pid = r['start']
            op = P0.ports[pid]
            hops.append((X, path[0], nf, list(win), list(op['layers']), op.get('order', 'lsb_low'), pid))
        avoid = set()
        for attempt in range(4):
            ok = True
            mine = []
            for k, (u, v) in enumerate(zip(path, path[1:])):
                pt = r['pts'][k]
                e = G.shared_edge(newR[u], newR[v])
                pref = (pt[1] if e[0] in 'EW' else pt[0]) if n_crossed(r) > 0 else None
                if id(r) in big_pref:
                    a_, b_ = big_pref[id(r)][1]
                    pref = (a_ + b_) / 2
                if (id(r), (u, v)) in pre and attempt == 0:
                    df_ = G.shared_edge(newR[u], newR[v])[0]
                    got = (df_, list(pre[(id(r), (u, v))]), LA.face_layers(P, u, df_))
                else:
                    got = B.alloc(u, v, width, prefer=pref)
                if got is None:
                    ok = False
                    avoid.add(tuple(sorted((u, v))))
                    break
                df, win, layers = got
                mine.append((u, v, df, list(win), list(layers), 'lsb_low', None))
            if ok:
                hops.extend(mine)
                break
            for (u, v, df, win, _, _, _) in mine:          # roll back this attempt's windows
                B.taken[(u, df)].remove(tuple(win))
                B.taken[(v, OPP[df])].remove(tuple(win))
            Rs = {k_: v_ for k_, v_ in newR.items() if k_.startswith(side)}
            got = G.route(Rs, path[0], r['sp'], path[-1], r['ep'], start_is_bank=r['start'][0] == 'bank',
                          end_is_bank=r['end'][0] == 'bank', avoid=avoid, start_face=r['sf'], end_face=r['ef'],
                      width=r['width'], lat_w=LAT_W)
            if got is None:
                break
            _, path, pts_ = got
            r['path'], r['pts'] = path, pts_
            rep.setdefault('rerouted', []).append(dict(lane=lid, avoid=sorted(avoid), path=path))
        if not ok:
            rep['failed'].append(dict(lane=lid, why=f'no free window on {sorted(avoid)}', width=width))
            continue
        if r['end'][0] == 'win':
            _, Y, nf, win, pid = r['end']
            op = P0.ports[pid]
            hops.append((path[-1], Y, OPP[nf], list(win), list(op['layers']), op.get('order', 'lsb_low'), pid))
        # crossed banks = path members that are not the lane's own end
        first_end = r['start'][0] == 'bank'
        last_end = r['end'][0] == 'bank'
        slots = []
        hi_ = 0
        for i, part in enumerate(path):
            if (i == 0 and first_end) or (i == len(path) - 1 and last_end):
                continue
            # hop into part, hop out of part
            hin = [h for h in hops if h[1] == part][0]
            hout = [h for h in hops if h[0] == part][0]
            din, win_in, lin = OPP[hin[2]], hin[3], hin[4]
            dout, win_out, lout = hout[2], hout[3], hout[4]
            k, seg, Lr = B.stations_for(part, din, win_in, dout, win_out)
            even = [C.point_at(seg, Lr * (j + 0.5) / k) for j in range(k)]
            slots.append([part, i, din, win_in, lin, dout, win_out, lout, k, even, Lr, 0, even])

        for sl in slots:
            got = solve_slot(B, sl[0], sl[2], sl[3], sl[5], sl[6])
            if got is None:
                rep['failed'].append(dict(lane=lid, why=f'no station chain in {sl[0]}', width=width, path=path))
                continue
            sl[8], sl[9], sl[10] = got[0], got[1], got[2]
            sl[11] = B.macro_hits(sl[0], sl[9][1:])
            hi_ += sl[11]
        # ---- write: buses / slots / ports
        base = None
        p_first = stash_ports[stash_lanes[lid]['ports'][0]]
        b = p_first['src']['bus']
        base = b[:-2] if b.endswith('_o') else b
        if 'x' in base and base.split('x')[-1].isdigit():
            base = base.rsplit('x', 1)[0]
        names = {}
        for sl in slots:
            part = sl[0]
            t = T[parts[part]['type']]
            nm = f'{base}y{sl[1]}'
            while slot_of(t, nm + '_i') is not None or bus_of(t, nm + '_i') is not None:
                nm += 'a'
            s = B.add_slot(part, nm, width, sl[2], sl[3], sl[4], sl[5], sl[6], sl[7], sl[8], regs_die=sl[9])
            s['note'] = (f'DIE-LAYOUT-HBM LADDER 11-11: {lid} through {part} ({sl[10]:.0f} um, {sl[8]} station(s), '
                         f'macro hits {sl[11]})')
            names[part] = nm
        # end buses
        for (part, bus), rr in list(end_bus.items()):
            if rr is not r:
                continue
            t = T[parts[part]['type']]
            bb = bus_of(t, bus)
            h = hops[0] if part == path[0] and first_end else hops[-1]
            df = h[2] if h[0] == part else OPP[h[2]]
            tf, tw, flip = type_window(P, part, df, h[3])
            bb['face'], bb['window_um'], bb['layers'] = tf, tw, list(h[4])
            bb['order'] = 'lsb_high' if flip else 'lsb_low'
            bb['note'] = (bb.get('note', '') + ' | DIE-LAYOUT-HBM LADDER 11-11: window re-sited').strip(' |')
        # neighbour-side fixed hops: bank side order follows the die order of the neighbour
        newp = []
        old_ids = stash_lanes[lid]['ports']
        used = set(old_ids)
        nid = 50
        for k, h in enumerate(hops):
            u, v = h[0], h[1]
            if h[6] is not None:
                op = stash_ports[h[6]]
                src = dict(op['src']) if u not in newR else None
                dst = dict(op['dst']) if v not in newR else None
            else:
                src = dst = None
            if src is None:
                if u in names:
                    src = dict(part=u, bus=names[u] + '_o')
                else:   # lane start bank: its out bus
                    src = dict(part=u, bus=stash_ports[old_ids[r['i0']]]['src']['bus'])
            if dst is None:
                if v in names:
                    dst = dict(part=v, bus=names[v] + '_i')
                else:
                    dst = dict(part=v, bus=stash_ports[old_ids[r['i1'] - 1]]['dst']['bus'])
            while f'{lid}_{nid}' in used or f'{lid}_{nid}' in portmap:
                nid += 1
            pid = f'{lid}_{nid}'
            used.add(pid)
            newp.append(dict(id=pid, src=src, dst=dst, width=width, kind=stash_ports[old_ids[0]].get('kind', 'data')))
        # the bank side of a fixed hop: the slot/bus window = the neighbour's window (type frame of the bank)
        for h, pr in zip(hops, newp):
            if h[6] is None:
                continue
            bank = h[1] if h[1] in newR else h[0]
            df_b = OPP[h[2]] if bank == h[1] else h[2]
            t = T[parts[bank]['type']]
            bus = pr['dst']['bus'] if bank == h[1] else pr['src']['bus']
            tf, tw, flip = type_window(P, bank, df_b, h[3])
            s = slot_of(t, bus)
            o = h[5]
            if flip:
                o = 'lsb_high' if o == 'lsb_low' else 'lsb_low'
            if s is not None:
                stem = 'in' if bus.endswith('_i') else 'out'
                s[stem + '_face'], s[stem + '_window_um'], s[stem + '_layers'] = tf, tw, list(h[4])
                s[stem + '_order'] = o
            else:
                bb = bus_of(t, bus)
                bb['face'], bb['window_um'], bb['layers'], bb['order'] = tf, tw, list(h[4]), o
        new_ports_of[(lid, r['i0'])] = (r, newp)
        rep['runs'].append(dict(lane=lid, side=side, width=width, old_run=r['run'], path=path,
                                slots=[dict(part=sl[0], name=names[sl[0]], stations=sl[8], route_um=round(sl[10], 1),
                                            macro_hits=sl[11]) for sl in slots],
                                windows=[dict(edge=f'{h[0]}|{h[1]}', face=h[2], window_um=[r4(h[3][0]), r4(h[3][1])],
                                              layers=h[4], fixed=bool(h[6])) for h in hops]))
    # ---- restore lanes / ports
    for lid in touched:
        ln = stash_lanes[lid]
        ids = list(ln['ports'])
        runs_l = sorted([v for (l, i0), v in new_ports_of.items() if l == lid], key=lambda z: -z[0]['i0'])
        failed = any(f['lane'] == lid for f in rep['failed'])
        if failed:
            log(f'{lid}: FAILED, lane left broken')
        for r, newp in runs_l:
            ids[r['i0']:r['i1']] = [p['id'] for p in newp]
            for p in newp:
                stash_ports[p['id']] = p
        for pid in drop_ports & set(ln['ports']):
            if pid not in ids:
                stash_ports.pop(pid, None)
        ln['ports'] = ids
        ln['note'] = (ln.get('note', '') + ' | DIE-LAYOUT-HBM LADDER 11-11 re-route').strip(' |')
        raw['lanes'].append(ln)
        raw['ports'].extend(stash_ports[p] for p in ids)

    # ------------------------------------------------------------------ 5. latency
    # every touched lane keeps its old NATURAL cycles: the cycles the new route no longer needs become lane
    # fixed_cycles (the plan's pad mechanism: bind lands them as pad stages at the face); a lane whose new route needs
    # more is reported (latency_up).  The table is regenerated from schema.Plan.lane_latency (R8 group pads included).
    P2 = S.Plan(raw)
    for lid in touched:
        if any(f['lane'] == lid for f in rep['failed']):
            continue
        ln = P2.lanes[lid]
        old_nat = int(lat[lid].get('natural', lat[lid]['cycles']))
        nat = P2.lane_natural(lid)['cycles']
        fx = int(ln.get('fixed_cycles', 0))
        d = old_nat - nat
        if d > 0:
            ln['fixed_cycles'] = fx + d
        elif d < 0:
            if fx + d >= 0:
                ln['fixed_cycles'] = fx + d
            else:
                if fx:
                    ln['fixed_cycles'] = 0
                rep['latency_up'].append(dict(lane=lid, old_natural=old_nat, new_natural=nat - fx,
                                              old_cycles=int(lat[lid]['cycles'])))
        if ln.get('fixed_cycles') == 0:
            ln.pop('fixed_cycles')
        rep.setdefault('fixed_cycles', {})[lid] = dict(old=fx, new=int(ln.get('fixed_cycles', 0)))
    P3 = S.Plan(raw)
    changed_untouched = []
    for lid in P3.lanes:
        new = P3.lane_latency(lid)
        old = lat.get(lid)
        ent = dict(new, param=(old or {}).get('param', 'LAT_' + lid.upper()))
        if old is not None and lid not in touched and int(old['cycles']) != int(ent['cycles']):
            changed_untouched.append(dict(lane=lid, old=int(old['cycles']), new=int(ent['cycles'])))
        if lid in touched or old is None:
            if old is not None and lid in touched and int(old['cycles']) != int(ent['cycles']):
                rep.setdefault('latency_changed_touched', []).append(
                    dict(lane=lid, old=int(old['cycles']), new=int(ent['cycles'])))
            lat[lid] = ent
        # an untouched lane keeps its table entry (pre-existing table/plan mismatches stay as they were)
    rep['latency_changed_untouched_lanes'] = changed_untouched

    # ------------------------------------------------------------------ 6. internal stations + taps + contents
    reach_i = 360.0
    for (n, bus), ob in sorted(nb_old_bus.items()):
        t = T[parts[n]['type']]
        nb = bus_of(t, bus)
        Wn, Hn = t['outline_um']
        Rz = HR.Raster(Wn, Hn, list(PO.placement_boxes(t).values()))
        cr = {h['inst']: HR._core_rect(h) for h in t.get('hard_cores', [])}
        st = rep['stations'].setdefault(n, dict(stations=0, regenerated=0, kept=0, regs_old=0, regs_new=0,
                                                latency_up=[], short=[], failed=[]))
        for e in t.get('internal_stations', []):
            if e['conn'] != 'bus:' + bus:
                continue
            st['stations'] += 1
            ends = []
            for p in (e['from_um'], e['to_um']):
                if any(x0 - 0.5 <= p[0] <= x1 + 0.5 and y0 - 0.5 <= p[1] <= y1 + 0.5 for (x0, y0, x1, y1) in cr.values()):
                    ends.append((r4(p[0]), r4(p[1])))
                    continue
                f0, (a0, b0) = ob['face'], sorted(ob['window_um'])
                f1, (a1, b1) = nb['face'], sorted(nb['window_um'])
                c = p[1] if f0 in 'EW' else p[0]
                fr = min(1.0, max(0.0, (c - a0) / max(b0 - a0, 1e-6)))
                c1 = a1 + fr * (b1 - a1)
                q = {'E': (Wn, c1), 'W': (0.0, c1), 'N': (c1, Hn), 'S': (c1, 0.0)}[f1]
                ends.append((r4(q[0]), r4(q[1])))
            n_old = len(e.get('regs_um', []))
            st['regs_old'] += n_old
            res = HR.route_station(Rz, ends[0], ends[1], n_old, reach_i, [], [])
            e['from_um'], e['to_um'] = [ends[0][0], ends[0][1]], [ends[1][0], ends[1][1]]
            if res is None:
                st['failed'].append(dict(conn=e['conn']))
                st['regs_new'] += n_old
                continue
            st['regenerated'] += 1
            st['regs_new'] += len(res['regs'])
            if len(res['regs']) > n_old:
                st['latency_up'].append(dict(conn=e['conn'], regs_old=n_old, regs_new=len(res['regs'])))
            e['regs_um'] = [list(q) for q in res['regs']]
            e['note'] = (f"DIE-LAYOUT-HBM LADDER 11-11 regenerated after the dip removal ({res['kind']}, "
                         f"{res['length_um']} um, {len(res['regs'])} station(s))")
        log(f'{n}: {bus} internal stations {st}')
    for n in sorted(newR):
        t = T[parts[n]['type']]
        Wn, Hn = t['outline_um']
        ow, oh = old_outline[n]
        oc = old_cores[n]
        Rz = HR.Raster(Wn, Hn, list(PO.placement_boxes(t).values()))
        info = streets.get(n, {})
        sy = [PK.fl(y) for y in info.get('streets_y', [])]
        sx = [PK.fl(x) for x in info.get('streets_x', [])]
        st = dict(stations=0, regenerated=0, kept=0, regs_old=0, regs_new=0, latency_up=[], short=[], failed=[])
        for e in t.get('internal_stations', []):
            st['stations'] += 1
            bus = e['conn'][4:]
            ob, nb = old_bus.get((n, bus)), bus_of(t, bus)
            moved_bus = ob is not None and nb is not None and (ob['face'] != nb['face'] or ob['window_um'] != nb['window_um'])
            if n not in reshaped and not moved_bus:
                st['kept'] += 1
                continue
            ends = []
            for p in (e['from_um'], e['to_um']):
                inst = next((i for i, (x, y, w, h) in oc.items()
                             if x - 0.5 <= p[0] <= x + w + 0.5 and y - 0.5 <= p[1] <= y + h + 0.5), None)
                if inst is not None and (n, inst) in shift:
                    dx, dy = shift[(n, inst)]
                    ends.append((r4(p[0] + dx), r4(p[1] + dy)))
                elif inst is not None:
                    ends.append((r4(p[0]), r4(p[1])))
                else:
                    # face end: same fraction along the new bus window
                    f0, (a0, b0) = ob['face'], sorted(ob['window_um'])
                    f1, (a1, b1) = nb['face'], sorted(nb['window_um'])
                    c = p[1] if f0 in 'EW' else p[0]
                    fr = min(1.0, max(0.0, (c - a0) / max(b0 - a0, 1e-6)))
                    c1 = a1 + fr * (b1 - a1)
                    q = {'E': (Wn, c1), 'W': (0.0, c1), 'N': (c1, Hn), 'S': (c1, 0.0)}[f1]
                    ends.append((r4(q[0]), r4(q[1])))
            n_old = len(e.get('regs_um', []))
            st['regs_old'] += n_old
            res = HR.route_station(Rz, ends[0], ends[1], n_old, reach_i, sy, sx)
            e['from_um'], e['to_um'] = [ends[0][0], ends[0][1]], [ends[1][0], ends[1][1]]
            if res is None:
                st['failed'].append(dict(conn=e['conn'], from_um=e['from_um'], to_um=e['to_um']))
                st['regs_new'] += n_old
                continue
            st['regenerated'] += 1
            st['regs_new'] += len(res['regs'])
            if len(res['regs']) > n_old:
                st['latency_up'].append(dict(conn=e['conn'], regs_old=n_old, regs_new=len(res['regs'])))
            elif len(res['regs']) < n_old:
                st['short'].append(dict(conn=e['conn'], regs_old=n_old, regs_new=len(res['regs'])))
            e['regs_um'] = [list(q) for q in res['regs']]
            e['note'] = (f"DIE-LAYOUT-HBM LADDER 11-11 regenerated ({res['kind']}, {res['length_um']} um, "
                         f"{len(res['regs'])} station(s), hops <= {reach_i:g} um)")
        rep['stations'][n] = st
        log(f"{n}: stations {st['stations']} regen {st['regenerated']} kept {st['kept']} regs {st['regs_old']}->"
            f"{st['regs_new']} up {len(st['latency_up'])} short {len(st['short'])} failed {len(st['failed'])}")
        if n not in reshaped:
            continue
        # taps follow cores
        for tp in t.get('clock', {}).get('taps', []):
            inst = tp['name'].rsplit('.', 1)[0]
            if (n, inst) in shift:
                dx, dy = shift[(n, inst)]
                tp['xy'] = [r4(tp['xy'][0] + dx), r4(tp['xy'][1] + dy)]
        for key in ('clock', 'reset'):
            tap = t.get(key, {}).get('tap_um')
            if not tap:
                continue
            tx, ty = tap[0] * Wn / ow, tap[1] * Hn / oh
            best = None
            for i in range(Rz.nx):
                for j in range(Rz.ny):
                    if Rz.f[i, j]:
                        d = abs(i * HR.G - tx) + abs(j * HR.G - ty)
                        if best is None or d < best[0]:
                            best = (d, i * HR.G, j * HR.G)
            t[key]['tap_um'] = [r4(best[1]), r4(best[2])]
        # soft contents: bbox of their hard cores, else scaled
        for c in t.get('contents', []):
            if 'origin_um' not in c or 'outline_um' not in c:
                continue
            hs = [h for h in t['hard_cores'] if h['inst'] == c['inst'] or h['inst'].startswith(c['inst'] + '.')]
            if hs:
                x0 = min(h['origin_um'][0] for h in hs)
                y0 = min(h['origin_um'][1] for h in hs)
                x1 = max(h['origin_um'][0] + h['outline_um'][0] for h in hs)
                y1 = max(h['origin_um'][1] + h['outline_um'][1] for h in hs)
                c['origin_um'], c['outline_um'] = [r4(x0), r4(y0)], [r4(x1 - x0), r4(y1 - y0)]
            else:
                x, y = c['origin_um']
                w, h = c['outline_um']
                w2, h2 = min(w, Wn), min(h, Hn)
                x2 = min(max(0.0, x * Wn / ow), Wn - w2)
                y2 = min(max(0.0, y * Hn / oh), Hn - h2)
                c['origin_um'] = [r4(PK.fl(x2)), r4(PK.fl(y2))]
                c['outline_um'] = [r4(w2), r4(h2)]

    raw['note'] = (raw.get('note', '') + ' | DIE-LAYOUT-HBM LADDER 11-11 (bank block 2-row ladder, b000 column kept, '
                   'ring stations -> 0 with latency pads)').strip(' |')
    # ------------------------------------------------------------------ write
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(plan_dir, out_dir, copy_function=os.link, symlinks=True)
    for name in ('die_plan.json', 'die_plan.sha256'):
        q = out_dir / name
        if q.exists():
            q.unlink()
    (out_dir / 'die_plan.json').write_text(json.dumps(raw, indent=1) + '\n')
    sha = hashlib.sha256((out_dir / 'die_plan.json').read_bytes()).hexdigest()
    (out_dir / 'die_plan.sha256').write_text(f'{sha}  die_plan.json\n')
    rep['plan_sha256'] = sha
    (out_dir / 'ladder_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    log(f'plan {sha[:12]}  failed {len(rep["failed"])}  latency_up {len(rep["latency_up"])}')


if __name__ == '__main__':
    main()
