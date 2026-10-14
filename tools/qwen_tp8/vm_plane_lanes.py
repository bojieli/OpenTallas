#!/usr/bin/env python3
"""x plane-lane router v2 on the VM leaf plan v2 (claude/qwen-tp8-vm PLAN, 2026-10-13).

  python3 tools/qwen_tp8/vm_plane_lanes.py NET_DUMP PLAN.json OUT.json [--ser 1|2] [--pad-density 1|2] [--slack N]

Demand: every xfifo8 xo bit ONCE: 128 x-FIFO leaves x 32 plane leaves = 4,096 lanes of 8 b (bit p of the leaf's 8
elements); --ser 2 = the 2:1 serialised option (4 b per lane on the wires and in the relays).
Model (unchanged rules, results/arch/qwen_tp8_1012/cuts.py CAP_MODE v3):
  capacity   per 260-um window, by layer: die layer M8 (vertical cut) / M9 (horizontal cut) at 75 % everywhere; over an
             M5-capped leaf ALSO M6 / M7 at 75 % (the leaves use M2-M5 for signals and PG, so M6 / M7 over them are the
             die's: this was already so in the 08:35 plan -- the by-layer table printed here makes it explicit); in a
             channel M6 / M7 at 75 % + M4 / M5 at 50 %.  Limit 0.60 of the usable tracks.
  demand     every existing it2 die bus (no discount) + the region's own seams (plan 'seam_segments': the region is die-
             assembled, its wires ride the same tracks) + the lanes.
  hops       register -> wire <= 500 um -> register.  Estimated pin to pin = L1 between the node centres + allowances:
             x-FIFO xo: half its N face; column leaf: half of the face quarter that holds one region's pins; a relay bay facing a terminal: TERM_BAY; bay to bay:
             west -> east the pins face each other (- one tile width), otherwise the wire wraps one tile (+ 25.92).
  relays     only in the plan's bays (me-enabled ot_qfd_vm_xrelay_t, 512 b per tile), bay capacity enforced; every lane
             is padded to the common depth with pad stages placed in bays ON ITS OWN PATH (--pad-density 2: a pad tile
             holds two stages); the pad assignment is part of the verdict.
An independent 100-um cut scan of the booked legs gives the reported worst windows.  PLAN ONLY."""
import argparse, heapq, json, math, sys, collections, hashlib, bisect
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'results/arch/qwen_tp8_1012'))
import cuts as C
LIM = 0.60; TERM_BAY = 51.0; TILE_W = 17.28; PAD2_W = 480; PAD2_WIDE = 640


def by_layer(ax, cp, lo, hi, blocks, cap5):
    """usable tracks of one window by layer (the terms of cuts.usable)"""
    p0, o0 = (0, 1) if ax == 'x' else (1, 0); sel = (blocks[:, p0] < cp) & (cp < blocks[:, p0 + 2]); cov = cov5 = 0.0; iv = []; iv5 = []
    for b, k5 in zip(blocks[sel], cap5[sel]):
        a, e = max(lo, b[o0]), min(hi, b[o0 + 2])
        if e > a: iv.append((a, e)); iv5 += [(a, e)] if k5 else []
    def union(v):
        t = 0.0; end = -1e18
        for a, e in sorted(v):
            if e > end: t += e - max(a, end); end = e
        return t
    cov, cov5 = union(iv), union(iv5); Lw = hi - lo; hi_, lo_, lw_ = ('M8', 'M6', 'M4') if ax == 'x' else ('M9', 'M7', 'M5')
    return {hi_: round(0.75 * Lw * C.TPU[hi_]), lo_ + '_over_M5_leaves': round(cov5 * 0.75 * C.TPU[lo_]), lo_ + '_channel': round((Lw - cov) * 0.75 * C.TPU[lo_]),
            lw_ + '_channel': round((Lw - cov) * 0.5 * C.TPU[lw_]), 'leaf_cover_um': round(cov5, 1), 'other_block_um': round(cov - cov5, 1)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('net'); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('--ser', type=int, default=1)
    ap.add_argument('--pad-density', type=int, default=1); ap.add_argument('--label', default=''); ap.add_argument('--wcong', type=float, default=0.3); ap.add_argument('--bcong', type=float, default=0.2)
    ap.add_argument('--debug', action='store_true'); ap.add_argument('--slack', type=int, default=0); ap.add_argument('--hopw', type=float, default=0.25); ap.add_argument('--passes', type=int, default=12)
    ap.add_argument('--relay-w', type=int, default=1); ap.add_argument('--pad-reserve', type=float, default=128.0); ap.add_argument('--save-routes', default=''); ap.add_argument('--load-routes', default=''); ap.add_argument('--repair', type=int, default=3); ap.add_argument('--pf0', type=float, default=0.5); ap.add_argument('--pfg', type=float, default=1.6); ap.add_argument('--hf', type=float, default=0.3); ap.add_argument('--pad-flow', type=int, default=0); ap.add_argument('--pad-wide', type=int, default=0); ap.add_argument('--pad-prio', type=int, default=0)
    a = ap.parse_args(); d = json.loads(Path(a.net).read_text()); p = json.loads(Path(a.plan).read_text())
    ch = p['children']; bays = p['x_relay_bays']; pins = p['real_pins']; LB = 8 // a.ser
    old = [i for i in d['insts'] if i['n'] not in p['geometry']['removed'] and not i['m'].startswith(('qfd_rly', 'qkd_rly'))]
    C.CAP_MODE = 'v3'; C.CLUSTER = C.CLUSTER + ('UNSIZED_SU64_ACTUAL_LEAF_ENVELOPE',)
    blocks, cap5, clb = C.block_model(old + [p['geometry']['su64_reservation']])
    vm = ch + bays                                                  # every VM leaf: M5-capped, opaque below M6, M6 / M7 over it are the die's
    blocks = np.concatenate((blocks, np.array([(i['x'], i['y'], i['x'] + i['w'], i['y'] + i['h']) for i in vm])))
    cap5 = np.concatenate((cap5, np.ones(len(vm), dtype=bool))); clb = np.concatenate((clb, np.zeros(len(vm), dtype=bool)))
    base = C.Net(a.net)
    seam = np.array([(s['A'][0], s['A'][1], s['Q'][0], s['Q'][1], s['bits']) for s in p['seam_segments']])
    # a region seam is an L like every die bus: book both legs (horizontal first)
    sl = np.concatenate((np.c_[seam[:, 0], seam[:, 1], seam[:, 2], seam[:, 1], seam[:, 4]], np.c_[seam[:, 2], seam[:, 1], seam[:, 2], seam[:, 3], seam[:, 4]]))
    def seam_cut(ax, cp, lo, hi):
        k, o = (0, 1) if ax == 'x' else (1, 0); m = (np.minimum(sl[:, k], sl[:, k + 2]) < cp) & (cp < np.maximum(sl[:, k], sl[:, k + 2])) & (sl[:, o] >= lo) & (sl[:, o] < hi)
        return float(sl[m, 4].sum())
    # ---- nodes ----
    P = []; cap = []; name = []
    for b in bays: P.append((b['x'] + b['w'] / 2, b['y'] + b['h'] / 2)); cap.append(b['tiles'] * 512); name.append(b['n'])
    NB = len(P); AL = []
    def term(pt, n, al): P.append((round(pt[0], 3), round(pt[1], 3))); cap.append(0); name.append(n); AL.append(al); return len(P) - 1
    xo = pins['ot_qfd_vm_xfifo8_t']['xo']['centroid']; xw = next(c['w'] for c in ch if c['m'] == 'ot_qfd_vm_xfifo8_t') / 2
    S = {c['n']: term((c['x'] + xo[0], c['y'] + xo[1]), c['n'] + '.xo', xw) for c in ch if c['m'] == 'ot_qfd_vm_xfifo8_t'}
    # the column leaf takes the lower region row's banks on its S face (d_lo) and the upper row's on its N face (d_hi); the
    # pins of a face are bank-major, i.e. ordered by region column (regions sit left to right in bank order), so the 128 pins
    # of one region are a quarter of the face: one terminal per (column leaf, face, region column), allowance = half a quarter
    K = {(c['plane'], f, k): term((c['x'] + c['w'] * (2 * k + 1) / 8, c['y'] + (c['h'] if f else 0.0)), c['n'] + ('.d_hi' if f else '.d_lo') + f'[r{k}]', c['w'] / 8)
         for c in ch if c['m'] == 'ot_qfd_vm_xcol_t' for f in (0, 1) for k in range(4)}
    regof = {c['n']: c['region'] for c in ch if c['m'] == 'ot_qfd_vm_xfifo8_t'}
    jobs = [dict(name=f'{s}>p{q}', A=S[s], Q=K[q, regof[s] // 4, regof[s] % 4], bits=LB) for s in S for q in range(32)]
    P = np.round(np.array(P), 3); N = len(P); AL = np.concatenate((np.zeros(NB), np.array(AL)))
    padrow = [bool(b_.get('padrow')) for b_ in bays] + [False] * (N - NB); PADROW = any(padrow); KSET = set(K.values()); SSET = set(S.values())
    def est(u, v, dist):
        if u < NB and v < NB:
            # relay tile ot_qfd_vm_xrelay_t: d on its W face, q on its E face.  West -> east: the pins face each other (centre
            # distance less one tile width).  East -> west: the same with the mirrored-pin kit qfd_vm_xrelay_w (same module, d
            # on E, q on W; --relay-w 1), else the wire wraps one tile.  Inside one strip the wire wraps one tile either way.
            dx = float(P[v, 0] - P[u, 0]); dy = abs(float(P[v, 1] - P[u, 1]))
            if abs(dx) <= 30.0: return abs(dx) + TILE_W + 8.64 + dy
            return (abs(dx) - TILE_W if dx > 0 or a.relay_w else abs(dx) + TILE_W + 8.64) + dy
        return float(dist) + float(AL[u]) + float(AL[v]) + (TERM_BAY if (u >= NB) != (v >= NB) else 0.0)
    # ---- cut bookkeeping (booking line per interval between consecutive node coordinates, two overlapping 260-um windows) ----
    ccache = {}; used = collections.defaultdict(int)
    AX = {'x': sorted({float(v) for v in P[:, 0]}), 'y': sorted({float(v) for v in P[:, 1]})}
    IX = {ax: {v: k for k, v in enumerate(vs)} for ax, vs in AX.items()}
    def capof(key):
        if key not in ccache:
            ax, k, w = key; lo, hi = AX[ax][k], AX[ax][k + 1]; bounds = np.array([w, w + 260.0])
            qs = [(lo + hi) / 2] + [float(v) for v in np.arange(math.ceil(lo / 12.5) * 12.5, hi, 12.5) if lo < v < hi]
            ccache[key] = max(0.0, LIM * min(C.usable(ax, q, bounds, blocks, cap5, clb)[0][0] for q in qs) - max(base.cut(ax, q, bounds)[0][0] + seam_cut(ax, q, w, w + 260.0) for q in qs))
        return ccache[key]
    def legkeys(ax, lo, hi, other):
        lo, hi = min(lo, hi), max(lo, hi)
        if hi - lo < 1e-6: return []
        st = math.floor(other / 130) * 130
        return [(ax, k, w) for k in range(IX[ax][float(lo)], IX[ax][float(hi)]) for w in (st - 130.0, float(st))]
    def lkeys(u, v, hfirst):
        (x1, y1), (x2, y2) = P[u], P[v]
        return legkeys('x', x1, x2, y1 if hfirst else y2) + legkeys('y', y1, y2, x2 if hfirst else x1)
    E = collections.defaultdict(list)
    for u in range(N):
        dist = np.abs(P[:, 0] - P[u, 0]) + np.abs(P[:, 1] - P[u, 1])
        for v in np.nonzero((dist <= 500.0) & (dist > 0))[0]:
            v = int(v)
            if u >= NB and v >= NB: continue                         # never terminal to terminal: at least one relay per lane
            # VM3 pad rows: a column face is entered ONLY from a pad-row bay (the last stage of every lane sits at its consumer);
            # an x FIFO never drives a pad-row bay directly (the pad row is not a through route for sources)
            if PADROW and ((u in KSET and not padrow[v]) or (v in KSET and not padrow[u])): continue
            if PADROW and ((u in SSET and v < NB and padrow[v]) or (v in SSET and u < NB and padrow[u])): continue
            if est(u, v, float(dist[v])) <= 500.0: E[u].append((v, float(dist[v]), lkeys(u, v, True), lkeys(u, v, False)))
    # ---- hop lower bounds (static graph, no capacity): the common depth D is set by the farthest lane, every other lane is
    #      padded to D anyway, so it may spend its slack on a detour: a lane is routed with at most D + slack relay stages ----
    INF = 10 ** 6; hopd = {}
    for q in set(j['Q'] for j in jobs):
        dist = {q: 0}; fr = [q]
        while fr:
            nx = []
            for u in fr:
                for v, *_ in E[u]:
                    if v not in dist and (v < NB or v == q): dist[v] = dist[u] + 1; nx.append(v)
                    elif v not in dist and v >= NB: dist[v] = dist[u] + 1                     # a source terminal: reached, never expanded
            fr = nx
        hopd[q] = dist
    for j in jobs: j['lb'] = hopd[j['Q']].get(j['A'], INF) - 1
    unreach = [j['name'] for j in jobs if j['lb'] >= INF - 1]
    DT = max((j['lb'] for j in jobs if j['lb'] < INF - 1), default=0) + a.slack
    nused = collections.defaultdict(int); hist = collections.defaultdict(float); bhist = collections.defaultdict(float)
    def over(k, bits): return max(0.0, used[k] + bits - capof(k)) / (capof(k) + 64.0)
    def wcost(keys, bits, pf):
        c = 0.0
        for k in keys:
            ck = capof(k); c = max(c, hist[k] + pf * max(0.0, used[k] + bits - ck) / (ck + 64.0) + a.wcong * (used[k] / (ck + 64.0)) ** 2)
        return c
    def route(j, pf, hard=False):
        s, g, bits = j['A'], j['Q'], j['bits']; hd = hopd[g]; wh = 1.0 if j['lb'] >= DT - 1 else a.hopw
        heap = [(0.0, 0, s)]; best = {s: (0.0, 0)}; prev = {}; done = set()
        while heap:
            c, hops, u = heapq.heappop(heap)
            if u in done: continue
            if u == g:
                path = []
                while u in prev: path.append(prev[u]); u = prev[u][0]
                return path[::-1]
            done.add(u)
            for v, ln, kh, kv in E[u]:
                if v in done or (v != g and v >= NB): continue
                if hops + 1 + hd.get(v, INF) > DT + 1: continue                               # relay stages = hops - 1 <= DT
                if hard:                                                                      # repair phase: no overuse at all
                    if v < NB and nused[v] + bits > cap[v]: continue
                    fh = all(used[k] + bits <= capof(k) for k in kh); fv = all(used[k] + bits <= capof(k) for k in kv)
                    if not (fh or fv): continue
                ch_, cv_ = wcost(kh, bits, pf), wcost(kv, bits, pf); (cw, hf) = (ch_, True) if ch_ <= cv_ else (cv_, False)
                if hard and not (fh if hf else fv): (cw, hf) = (cv_, False) if hf else (ch_, True)
                cb = 0.0 if v >= NB else bhist[v] + pf * max(0.0, nused[v] + bits - cap[v]) / cap[v] + a.bcong * (nused[v] / cap[v]) ** 2
                alt = c + wh + ln / 5000.0 + cw + cb
                if alt < best.get(v, (float('inf'),))[0]: best[v] = (alt, hops + 1); prev[v] = (u, v, hf); heapq.heappush(heap, (alt, hops + 1, v))
        return None
    jobs.sort(key=lambda j: (-j['lb'], -(abs(P[j['A'], 0] - P[j['Q'], 0]) + abs(P[j['A'], 1] - P[j['Q'], 1]))))
    sol = {}                                                         # job index -> (path, window demand)
    def place(i, path, sign):
        dem = collections.Counter()
        for u, v, hf in path:
            for k in lkeys(u, v, hf): dem[k] += jobs[i]['bits']
            if v != jobs[i]['Q']: nused[v] += sign * jobs[i]['bits']
        for k, n in dem.items(): used[k] += sign * n
        return dem
    pf = a.pf0; passes = []
    if a.load_routes:                                                # resume: the negotiated routes of an earlier run of the SAME plan
        import pickle
        saved = pickle.loads(Path(a.load_routes).read_bytes()); byname = {j['name']: i for i, j in enumerate(jobs)}
        for n, path in saved['paths'].items(): sol[byname[n]] = (path, place(byname[n], path, +1))
        passes = saved['passes']
    for it in range(0 if a.load_routes else a.passes):
        todo = [i for i in range(len(jobs)) if i not in sol or any(used[k] > capof(k) + 1e-6 for k in sol[i][1]) or any(nused[v] > cap[v] for _, v, _ in sol[i][0][:-1])] if it else list(range(len(jobs)))
        for i in todo:
            if i in sol: place(i, sol[i][0], -1); del sol[i]
            if jobs[i]['lb'] >= INF - 1: continue
            path = route(jobs[i], pf)
            if path is not None: sol[i] = (path, place(i, path, +1))
        ow = [k for k, n in used.items() if n > capof(k) + 1e-6]; ob = [v for v in range(NB) if nused[v] > cap[v]]
        for k in ow: hist[k] += a.hf * (used[k] - capof(k)) / (capof(k) + 64.0)
        for v in ob: bhist[v] += a.hf * (nused[v] - cap[v]) / cap[v]
        passes.append(dict(iteration=it, rerouted=len(todo), routed=len(sol), overused_windows=len(ow), overused_bays=len(ob), present_factor=round(pf, 2)))
        print('pass', json.dumps(passes[-1]), file=sys.stderr, flush=True)
        if a.debug:
            top = sorted(ow, key=lambda k: -(used[k] - capof(k)))[:14]
            print('  over', [(k[0], round(AX[k[0]][k[1]]), round(AX[k[0]][k[1] + 1]), int(k[2]), int(used[k]), int(capof(k))) for k in top], file=sys.stderr)
            print('  bays', [(name[v], nused[v], cap[v]) for v in ob[:14]], 'cap<LB windows touched', sum(1 for k in ow if capof(k) < LB), file=sys.stderr, flush=True)
        if not ow and not ob and len(sol) == len(jobs) - len(unreach): break
        pf *= a.pfg
    # ---- repair: for every window / bay still overused, lift just enough lanes (those with the most hop slack first) and
    #      re-route each under HARD capacity (no overuse anywhere); a lane that finds no such path is a FAILED lane ----
    repaired = 0; unrepaired = 0
    for _ in range(a.repair):
        ow = sorted((k for k, n in used.items() if n > capof(k) + 1e-6), key=lambda k: -(used[k] - capof(k))); ob = [v for v in range(NB) if nused[v] > cap[v]]
        if not ow and not ob: break
        lift = []
        for k in ow:
            on = sorted((i for i in sol if k in sol[i][1]), key=lambda i: jobs[i]['lb']); n = used[k]
            for i in on:
                if n <= capof(k) + 1e-6: break
                if i not in lift: lift.append(i); n -= jobs[i]['bits']
        for v in ob:
            on = sorted((i for i in sol if any(x == v for _, x, _ in sol[i][0][:-1])), key=lambda i: jobs[i]['lb']); n = nused[v]
            for i in on:
                if n <= cap[v]: break
                if i not in lift: lift.append(i); n -= jobs[i]['bits']
        for i in lift: place(i, sol[i][0], -1); del sol[i]
        for i in lift:
            path = route(jobs[i], pf, hard=True)
            if path is not None: sol[i] = (path, place(i, path, +1)); repaired += 1
            else: unrepaired += 1
        print('repair', json.dumps(dict(lifted=len(lift), repaired=repaired, unrepaired=unrepaired)), file=sys.stderr, flush=True)
    # a lane that still sits on an overused window or bay after the last pass is a FAILED lane
    bad = {i for i in sol if any(used[k] > capof(k) + 1e-6 for k in sol[i][1]) or any(nused[v] > cap[v] for _, v, _ in sol[i][0][:-1])}
    for i in sorted(bad, key=lambda i: jobs[i]['lb']):
        if any(used[k] > capof(k) + 1e-6 for k in sol[i][1]) or any(nused[v] > cap[v] for _, v, _ in sol[i][0][:-1]): place(i, sol[i][0], -1); del sol[i]
    if a.save_routes:
        import pickle
        Path(a.save_routes).write_bytes(pickle.dumps(dict(paths={jobs[i]['name']: v[0] for i, v in sol.items()}, passes=passes)))
    # ---- equalisation: every lane to the common depth D.  A pad stage is a relay with no reach to make: it sits in a bay ON
    #      the lane's own path (--pad-density 2: pairs go into ot_qfd_vm_xpad2_t, two stages per tile slot).  Pass 1 pads every
    #      lane in the bays of its routed path.  Pass 2 takes the lanes whose bays are full and routes them again in the
    #      layered graph (bay, stage): exactly D stages, each a move to another bay (a real relay hop <= 500 um, its windows
    #      booked under HARD capacity) or a stay (a pad stage), so the lane spends its pads where bays have room. ----
    depth = max(DT, max((len(v[0]) - 1 for v in sol.values()), default=0)); pad_fail = 0; rerouted_for_pads = 0
    padload = collections.defaultdict(float); padat = {}
    def spare(b): return cap[b] - nused[b] - padload[b]
    yb0 = y0b = p['slot']['region_origins']['4'][1] - p['plane_band']['band_um']; yb1 = p['slot']['region_origins']['4'][1]
    landing = [(yb0 - 230.0 < P[v, 1] < yb1 + 230.0) and not PADROW for v in range(NB)]                # the two node rows on either side of the band (no penalty once the pad rows take the landing)
    # tile-slot units (x lane bits) of nst pad stages in one bay.  A pair sits in ot_qfd_vm_xpad2_t: 2 x 480 b per tile slot (the
    # 512-b pair was 60.7 % dense), so a pair costs 512 / 480 of a relay's share; an odd stage is one relay
    # --pad-wide 1 (VM3): in a bay of >= 3 tile slots the pad pairs sit in the TWO-SLOT pad leaf (ot_qfd_vm_xpad2_t W 1,280 in
    # 38.88 x 97.2: no inner margin / channel, 640 b a slot instead of 480); bays of 1 or 2 slots keep the one-slot leaf
    padw = [(PAD2_WIDE if (a.pad_wide and bays[b_]['tiles'] >= 3) else PAD2_W) for b_ in range(NB)]
    def charge(nst, b_): return ((nst // 2) * (512.0 / padw[b_]) + nst % 2) if a.pad_density == 2 else nst
    def pad_simple(i):
        path = sol[i][0]; bits = jobs[i]['bits']; rem_ = depth - (len(path) - 1); via = [v for _, v, _ in path[:-1]]; at = collections.Counter()
        while rem_ > 0:
            # pads keep out of the bays next to the band (every lane must land or start there) and leave each bay a reserve
            # for the relays of the lanes still to be re-routed
            b = max(via, key=lambda n: spare(n) - (charge(at[n] + 1, n) - charge(at[n], n)) * bits - (1e6 if landing[n] else 0.0))
            add = (charge(at[b] + 1, b) - charge(at[b], b)) * bits
            if spare(b) - a.pad_reserve < add: break
            padload[b] += add; at[b] += 1; rem_ -= 1
        padat[i] = at; return rem_
    def unpad(i):
        for b, n in padat.pop(i, {}).items(): padload[b] -= charge(n, b) * jobs[i]['bits']
    pad_failed = []
    def layered(i, ban, bank=frozenset()):
        """exactly `depth` stages from the lane's x FIFO to its column face: state (node, stages used, stayed?).  A move enters
        another bay (one relay: bay room for the lane's bits, both L options tried under hard window capacity); a stay block
        of m pad stages follows the arrival in a bay that has room for them (charge(m) tile-slot units), once per visit."""
        j = jobs[i]; s, g, bits = j['A'], j['Q'], j['bits']; hd = hopd[g]
        heap = [(0.0, 0, s, 1)]; best = set(); prev = {}; cost = {(s, 0, 1): 0.0}; why = collections.Counter()
        while heap:
            c, k, u, f = heapq.heappop(heap)
            if (u, k, f) in best: continue
            best.add((u, k, f))
            if u == g:
                seq = []; st = (u, k, f)
                while st in prev: seq.append(prev[st][1]); st = prev[st][0]
                return seq[::-1]
            if f == 0 and u not in ban:
                room = int((spare(u) - bits) // (bits * (512.0 / padw[u] if a.pad_density == 2 else 1.0))) * a.pad_density   # pad stages this bay can still take for the lane
                for m in range(1, min(depth - k, room) + 1):
                    if k + m + hd.get(u, INF) - 1 > depth: break
                    st = (u, k + m, 1); cs = c + (1.2 if landing[u] else 0.15) * m
                    if st not in best and cs < cost.get(st, float('inf')): cost[st] = cs; prev[st] = ((u, k, f), ('stay', u, m)); heapq.heappush(heap, (cs, k + m, u, 1))
            for v, ln, kh, kv in E[u]:
                if v == g:
                    if k != depth: continue
                    k2 = k
                else:
                    if v >= NB or k >= depth or v in ban: continue
                    if spare(v) < bits: why['bay_full'] += 1; continue
                    if k + 1 + hd.get(v, INF) - 1 > depth: why['too_far'] += 1; continue
                    k2 = k + 1
                st = (v, k2, 0)
                if st in best: continue
                fh = all(x not in bank and used[x] + bits <= capof(x) + 1e-6 for x in kh); fv = fh or all(x not in bank and used[x] + bits <= capof(x) + 1e-6 for x in kv)
                if not fv: why['window'] += 1; continue
                nc = c + 1.0 + ln / 5000.0 + (0.3 * (nused[v] + padload[v]) / cap[v] if v < NB else 0.0)
                if nc < cost.get(st, float('inf')): cost[st] = nc; prev[st] = ((u, k, f), ('move', u, v, fh)); heapq.heappush(heap, (nc, k2, v, 0))
        if a.debug and len(pad_failed) < 6: print('  layered none', j['name'], 'states', len(best), dict(why), 'maxk', max((k_ for _, k_, _ in best), default=0), file=sys.stderr)
        return None
    def pad_flow():
        """pass 1 as ONE transportation problem (--pad-flow 1): lanes -> the bays of their own routed paths, min cost flow.  The
        greedy pass let the long lanes (many bays to choose from) fill the centre bays that the short lanes (one or two bays
        on the path, ten or eleven pads to place) have no alternative to.  Unit = one pad PAIR (2 stages in ot_qfd_vm_xpad2_t,
        bits * 512 / 480 of bay room); an odd last stage is booked as a whole unit here (conservative) and charged exactly
        (one relay share) in padload.  A bay next to the band costs more (lanes land there)."""
        import networkx as nx
        G = nx.DiGraph(); unit = {}; need = {}
        for i in sol:
            path = sol[i][0]; n = depth - (len(path) - 1)
            if n <= 0: padat[i] = collections.Counter(); continue
            need[i] = n; G.add_edge('s', ('l', i), capacity=(n + 1) // 2, weight=0)
            for b in {v for _, v, _ in path[:-1]}: G.add_edge(('l', i), ('b', b), capacity=(n + 1) // 2, weight=(0 if padrow[b] else 6 if landing[b] else 1) + (a.pad_prio * (len(path) - 1) if a.pad_prio else 0))
        for b in range(NB):
            if ('b', b) in G: G.add_edge(('b', b), 't', capacity=max(0, int((spare(b) - a.pad_reserve) // (jobs[0]['bits'] * 512.0 / padw[b]))), weight=0)
        fl = nx.max_flow_min_cost(G, 's', 't'); left = {}
        for i, n in need.items():
            at = collections.Counter(); rem_ = n
            for (_, b), u in sorted(fl[('l', i)].items(), key=lambda kv: -kv[1]):
                st = min(2 * u, rem_)
                if st > 0: at[b] += st; rem_ -= st
            padat[i] = at
            for b, k in at.items(): padload[b] += charge(k, b) * jobs[i]['bits']
            if rem_ > 0: left[i] = rem_
        return left
    if a.pad_flow:
        left = pad_flow(); todo2 = sorted(left, key=lambda i: len(sol[i][0]))
        print('pad_flow', json.dumps(dict(lanes_left=len(left), stages_left=sum(left.values()))), file=sys.stderr, flush=True)
    else:
        todo2 = [i for i in sorted(sol, key=lambda i: -len(sol[i][0])) if pad_simple(i) > 0]; todo2.sort(key=lambda i: len(sol[i][0]))
    for i in todo2:
        old = sol[i]; bits = jobs[i]['bits']; unpad(i); place(i, old[0], -1); ban = set(); bank = set(); okk = False
        for _ in range(10):
            seq = layered(i, ban, bank)
            if seq is None: break
            path = [(m[1], m[2], m[3]) for m in seq if m[0] == 'move']; stays = collections.Counter()
            for m in seq:
                if m[0] == 'stay': stays[m[1]] += m[2]
            visits = collections.Counter(v for _, v, _ in path[:-1]); dem = collections.Counter()
            for u, v, hf in path:
                for x in lkeys(u, v, hf): dem[x] += bits
            over_b = [b for b in set(visits) | set(stays) if spare(b) < (visits[b] + charge(stays[b], b)) * bits]
            over_k = [x for x, n in dem.items() if used[x] + n > capof(x) + 1e-6]
            if over_b or over_k:                                     # the walk used one bay / one window more than once: keep it off both
                ban |= set(over_b); bank |= set(over_k); continue
            sol[i] = (path, place(i, path, +1)); padat[i] = stays
            for b, n in stays.items(): padload[b] += charge(n, b) * bits
            okk = True; rerouted_for_pads += 1; break
        if not okk:
            sol[i] = (old[0], place(i, old[0], +1)); left = pad_simple(i); pad_fail += left; pad_failed.append((jobs[i]['name'], len(old[0]) - 1, left))
    pad_bits = sum(n * jobs[i]['bits'] for i, at in padat.items() for n in at.values())
    pad_tiles2 = sum((n // 2) * jobs[i]['bits'] for i, at in padat.items() for n in at.values()) if a.pad_density == 2 else 0
    pad_wide_bits = sum((n // 2) * jobs[i]['bits'] for i, at in padat.items() for b_, n in at.items() if padw[b_] == PAD2_WIDE) if a.pad_density == 2 else 0
    inserted = rerouted_for_pads
    relay_bits = sum(nused.values())
    done = []; fail = [j for i, j in enumerate(jobs) if i not in sol]; legs = []
    for i, (path, dem) in sol.items():
        j = jobs[i]; ln = 0.0; hops = []
        for u, v, hf in path:
            hops.append(round(est(u, v, float(abs(P[u, 0] - P[v, 0]) + abs(P[u, 1] - P[v, 1]))), 1))
            (x1, y1), (x2, y2) = P[u], P[v]; mid = (x2, y1) if hf else (x1, y2)
            legs.append((x1, y1, mid[0], mid[1], j['bits'])); legs.append((mid[0], mid[1], x2, y2, j['bits'])); ln += abs(x1 - x2) + abs(y1 - y2)
        done.append(dict(name=j['name'], bits=j['bits'], relay_stages=len(path) - 1, min_stages=j['lb'], route_um=round(ln, 1), stage_um=hops,
                         lower_um=round(float(abs(P[j['A'], 0] - P[j['Q'], 0]) + abs(P[j['A'], 1] - P[j['Q'], 1])), 1), via=[int(v) for _, v, _ in path[:-1]]))
    # ---- independent fine scan of the booked legs, with the by-layer capacity of the worst windows ----
    SG = np.array(legs).reshape(-1, 5); worst = []
    x0, y0 = p['slot']['origin_um']; w, h = p['slot']['size_um']
    for ax, axis, other, span, win in (('x', 0, 1, np.arange(x0 - 600, x0 + w + 700, 100.0), np.arange(math.floor((y0 - 700) / 130) * 130, y0 + h + 700, 130.0)),
                                      ('y', 1, 0, np.arange(y0 - 600, y0 + h + 700, 100.0), np.arange(math.floor((x0 - 700) / 130) * 130, x0 + w + 700, 130.0))):
        for cp in span:
            T = SG[(np.minimum(SG[:, axis], SG[:, axis + 2]) < cp) & (cp < np.maximum(SG[:, axis], SG[:, axis + 2]))]
            if not len(T): continue
            for lo in win:
                bits = int(T[(T[:, other] >= lo) & (T[:, other] < lo + 260), 4].sum())
                if not bits: continue
                bounds = np.array([lo, lo + 260.0]); u = float(C.usable(ax, cp, bounds, blocks, cap5, clb)[0][0]); ex = int(base.cut(ax, cp, bounds)[0][0]); sb = int(seam_cut(ax, cp, lo, lo + 260.0))
                worst.append(dict(ax=ax, pos=float(cp), win=[float(lo), float(lo + 260)], lane_bits=bits, region_seam_bits=sb, existing_die_bits=ex, usable=round(u, 1), util=round((ex + sb + bits) / u, 4)))
    worst.sort(key=lambda r: -r['util'])
    for r in worst[:12]: r['tracks_by_layer'] = by_layer(r['ax'], r['pos'], r['win'][0], r['win'][1], blocks, cap5)
    worst_by_axis = {ax: next((r for r in worst if r['ax'] == ax), None) for ax in 'xy'}
    # ---- coarse separators of the envelope ----
    coarse = []
    xs = sorted({v[0] for v in p['slot']['region_origins'].values()}); ys = sorted({v[1] for v in p['slot']['region_origins'].values()})
    ux = p['slot']['unit_x_um'][0] + 130.0; bandh = p['plane_band']['band_um']
    # vertical cuts: the channel between two region columns and a line through the bank column next to it; horizontal cuts: a
    # line through the SU row of the lower regions and one through the first bank row of the upper regions (the lanes cross both)
    for ax, cps, lo, hi in (('x', [v for x in xs[1:] for v in (x - 2.16, x + ux)], y0, y0 + h), ('y', [ys[1] - bandh - 120.0, ys[1] + 120.0], x0, x0 + w)):
        k = 0 if ax == 'x' else 1
        for cp in cps:
            bits = sum(j['bits'] for j in jobs if (P[j['A'], k] - cp) * (P[j['Q'], k] - cp) < 0)
            bounds = np.array([lo, hi]); u = float(C.usable(ax, cp, bounds, blocks, cap5, clb)[0][0]); ex = int(base.cut(ax, cp, bounds)[0][0]); sb = int(seam_cut(ax, cp, lo, hi))
            coarse.append(dict(ax=ax, pos=round(cp, 2), win=[round(lo, 1), round(hi, 1)], lane_bits=bits, region_seam_bits=sb, existing_die_bits=ex, usable=round(u), util=round((ex + sb + bits) / u, 4),
                               tracks_by_layer=by_layer(ax, cp, lo, hi, blocks, cap5)))
    allst = [h_ for v in done for h_ in v['stage_um']]
    stage_audit = dict(rule='every stage (register pin -> wire -> register pin) <= 500 um, estimated pin to pin', stages=len(allst), max_um=max(allst, default=0),
                       over_500=int(sum(h_ > 500 for h_ in allst)), over_450=int(sum(h_ > 450 for h_ in allst)),
                       allowance_um=dict(xfifo8_xo=float(xw), plane=float(AL[-1]), bay_facing_terminal=TERM_BAY, bay_to_bay='strip to strip: - one tile width (pins face each other; westward lanes use the mirrored-pin relay kit qfd_vm_xrelay_w)' if a.relay_w else 'west -> east: - one tile width; east -> west: + tile width + 8.64', same_strip='+ tile width + 8.64'))
    capb = sum(cap[:NB]); spare = capb - relay_bits - sum(padload.values())
    padrow_rep = dict(bays=sum(padrow), tiles=sum(bays[b_]['tiles'] for b_ in range(NB) if padrow[b_]), relay_bits=sum(nused[b_] for b_ in range(NB) if padrow[b_]), pad_load_bits=round(sum(padload[b_] for b_ in range(NB) if padrow[b_])),
                      fullest=[round((nused[b_] + padload[b_]) / cap[b_], 3) for b_ in sorted((b_ for b_ in range(NB) if padrow[b_]), key=lambda b_: -(nused[b_] + padload[b_]) / cap[b_])[:6]],
                      strip_fill=round(sum(nused[b_] + padload[b_] for b_ in range(NB) if not padrow[b_]) / max(1, sum(cap[b_] for b_ in range(NB) if not padrow[b_])), 4)) if PADROW else None
    hist = collections.Counter(v['relay_stages'] for v in done)
    ok = not fail and (not worst or worst[0]['util'] <= LIM) and pad_fail == 0 and max(c['util'] for c in coarse) <= LIM and stage_audit['over_500'] == 0
    bayfill = sorted(((nused[v] + padload[v]) / cap[v] for v in range(NB)), reverse=True)
    rep = dict(status='PLANE_LANES_V2', owner='claude/qwen-tp8-vm-phys', label=a.label, pad_rows=padrow_rep, options=dict(ser=a.ser, pad_density=a.pad_density, slack=a.slack, relay_w=a.relay_w, plan=p['options']), router=dict(kind='negotiated congestion (rip-up and re-route), hop-bounded: every lane <= min depth of the farthest lane + slack', depth_target=DT, passes=passes, repair=dict(rounds=a.repair, repaired=repaired, unrepaired=unrepaired), unreachable=unreach[:20]),
        inputs={str(v): hashlib.sha256(Path(v).read_bytes()).hexdigest() for v in (a.net, a.plan, __file__)},
        verdict='PASS_PLAN_LEVEL' if ok else 'REJECT', limit=LIM, lanes_requested=len(jobs), lanes_routed=len(done), lanes_failed=len(fail),
        bits_requested=sum(j['bits'] for j in jobs), bits_routed=sum(v['bits'] for v in done), lane_bits=LB,
        relay_depth=depth, XPR=depth, relay_depth_histogram={str(k): hist[k] for k in sorted(hist)},
        stage_audit=stage_audit, coarse_cuts=coarse, fine_worst=worst[:12], fine_worst_by_axis=worst_by_axis,
        relay=dict(leaf='ot_qfd_vm_xrelay_t (512 b, me-enabled)', bay_tiles=capb // 512, bay_capacity_bits=capb, routed_relay_bits=relay_bits, pad_bits=pad_bits,
                   pad_density=a.pad_density, pad_stages_unplaced=pad_fail, lanes_rerouted_for_pads=inserted, lanes_padded_on_path=len(sol) - len(todo2), lanes_short_of_depth=len(pad_failed), short_sample=pad_failed[:40], spare_bits=round(spare), fill=round(1 - spare / capb, 4),
                   tiles_needed=math.ceil((relay_bits + sum(padload.values())) / 512), pad2_tiles=math.ceil((pad_tiles2 - pad_wide_bits) / PAD2_W), pad2_bits_per_tile=PAD2_W, pad2_wide_leaves=math.ceil(pad_wide_bits / PAD2_WIDE / 2), pad2_wide_bits_per_leaf=2 * PAD2_WIDE, pad_wide=a.pad_wide, fullest_bays=[round(v, 3) for v in bayfill[:8]]),
        failed_sample=[j['name'] for j in fail[:12]], failed_by_sink=dict(collections.Counter(j['name'].split('>')[1] for j in fail).most_common(40)),
        route_um=dict(total_bit_mm=round(sum(v['bits'] * v['route_um'] for v in done) / 1e3), max=max((v['route_um'] for v in done), default=0),
                      max_detour=max((round(v['route_um'] - v['lower_um'], 1) for v in done), default=0)),
        not_covered=['clock / PDN', 'x output side (xline q -> XQR relays -> xqface -> consumer): the x_q consumer has no physical owner yet',
                     'write / address / SU / row-read die buses to the region leaves (die relay plan)', 'pin-level legality of relay tiles inside a bay'],
        paths=[dict(v, via=[name[n] for n in v['via']]) for v in done])
    sat = collections.Counter()
    for k, n in used.items():
        if capof(k) - n < LB and n: sat[(k[0], round(AX[k[0]][k[1]]), round(AX[k[0]][k[1] + 1]), int(k[2]))] += 1
    rep['saturated_booking_windows'] = [dict(ax=k[0], interval=[k[1], k[2]], window_lo=k[3]) for k, _ in sat.most_common(60)]
    rep['zero_room_windows'] = sum(1 for k in ccache if ccache[k] < LB)
    rep['full_bays'] = sorted(name[v] for v in range(NB) if cap[v] - nused[v] < LB)[:200]
    Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('label', 'verdict', 'options', 'lanes_requested', 'lanes_routed', 'lanes_failed', 'relay_depth', 'relay_depth_histogram', 'route_um')}))
    print('stage_audit', json.dumps(stage_audit)); print('relay', json.dumps(rep['relay']))
    for c in coarse: print('coarse', json.dumps(c))
    for ax in 'xy': print('fine', ax, json.dumps(worst_by_axis[ax]))
    print('fsink', json.dumps(rep['failed_by_sink'])[:600])
    print('sat', len(sat), json.dumps(rep['saturated_booking_windows'][:30])); print('zero_room', rep['zero_room_windows'], 'full_bays', len(rep['full_bays']), rep['full_bays'][:60])

if __name__ == '__main__': main()
