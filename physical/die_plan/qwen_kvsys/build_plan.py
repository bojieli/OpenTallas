#!/usr/bin/env python3
"""PLAN-KV 10-23: KV die plan v1 (TOPDOWN-PLAN) from the as-built rtl6 connectivity.

Input : asbuilt.json.gz (extract_asbuilt.py on the rtl6 GEN, source e33504a6f): content blocks + logical connections
        with today's relay depth (stages) and source bit sets.
Output: die_plan.json (opentallas.die_plan.v1, tools/die_plan/schema.py @ claude/plan-tool-1023), plan_report.json
        (coverage, chains, latency parameters, budgets, reuse/rework), consumed by g0_check.py and render_plan.py.

Plan v1 (abutted, no channels):
- 4 quadrants WS/ES/WN/EN (E = MY mirror of W; N half = S half translated), each: HBM PHY (hard) | PC column of 8
  pcrows (4 kvpc + 4 hsl + 1 slg [+ vport]) | head column 0 (4 hgrp: 4 heads + ectl + hst tree) | astk column (4 segs)
  | head column 1 (4 hgrp).  Centre column: 16 PV rows per half (one PV block row: 16 slices + 2 joins, W and E blocks).
- One band row per half (604.8 um): hroot partitions (hroot + kc + fault joins) at the PC columns, band ft partitions over
  the head/astk columns, the attention HUB (ahub + pvfin) in the centre of the mid band, a ft partition in the top band.
- System strip (top): sys_core (kvs_ctl, kvs_attn, kvs_emb, embgw, seq), sys_io (host, d2d, ucie, serdes, pll, dcal,
  bumps) and four ft wings.
- Every inter-partition connection of the as-built netlist becomes lanes: point-to-point lanes over the partition graph,
  BROADCASTS as tap trees (one trunk; each destination partition taps its bits and forwards the rest; branch points are
  tap stations), GATHERS (several sources -> one port, e.g. the PV y mux chain) as chains of mux stations.  Head / hst
  trees are inside the hgrp partition (no die lane).  Clock and reset distribution are die spines (one root / one
  synchroniser per partition), not lanes.
- Stations per crossed partition = ceil(crossing span / reach) (KV reach 1200 um).  Latency = stations + 1 per lane
  (schema), + 1 per intermediate tap; the KV parameters RESPONSE_LAT, RL, PV_LEAD, F_DLY are derived from the lanes.
"""
import argparse
import collections
import gzip
import heapq
import json
import math
import re
import sys
from pathlib import Path

G = 8.64
REACH = 1200.0
# column widths (W half, outer -> centre)
C0, C1, HC, AS, PV = 864.0, 1036.8, 1105.92, 345.6, 1900.8
XW = [0.0]
for w in (C0, C1, HC, AS, HC):
    XW.append(XW[-1] + w)                 # 0, 864, 1814.4, 2920.32, 3265.92, 4371.84
DIE_W = 2 * XW[-1] + PV                   # 10298.88
HALF = 1408 * G                           # 12165.12
BAND = 90 * G                             # 777.6
PCROW = HALF / 8                          # 1520.64
HGRP = HALF / 4                           # 3041.28
PVROW = HALF / 16                         # 760.32
SYS_CORE_H, SYS_IO_H = 120 * G, 200 * G   # 1036.8, 1728
Y_S, Y_MB = 0.0, HALF
Y_N = HALF + BAND
Y_TB = Y_N + HALF
Y_SYS = Y_TB + BAND
DIE_H = Y_SYS + SYS_CORE_H + SYS_IO_H     # 28304.64
CORE_W, IO_W = 512 * G, 512 * G           # 4423.68, 4423.68
QUADS = dict(WS=('W', 'S'), ES=('E', 'S'), WN=('W', 'N'), EN=('E', 'N'))


def r2(v):
    return round(v, 4)


# ------------------------------------------------------------------------------------------------ partitions
def xspan(side, x0, w):
    return (x0, w) if side == 'W' else (DIE_W - x0 - w, w)


def build_partitions():
    P = {}

    def add(name, cls, x, y, w, h, orient='R0', scope=None, **kw):
        P[name] = dict(name=name, cls=cls, x=r2(x), y=r2(y), w=r2(w), h=r2(h), orient=orient, scope=scope, **kw)

    for q, (side, half) in QUADS.items():
        y0 = Y_S if half == 'S' else Y_N
        o = 'R0'      # ASAP7 M5/M7 track offsets: MY replicas cannot keep N/S pins on track -> E types are own
        x, w = xspan(side, XW[0], C0)
        add(f'phy_{q}', 'phy', x, y0, w, HALF, o, q)
        x, w = xspan(side, XW[1], C1)
        for k in range(8):
            add(f'pcrow_{q}_{k}', 'pcrow', x, y0 + k * PCROW, w, PCROW, o, q, idx=k)
        for c, xc in ((0, XW[2]), (1, XW[4])):
            x, w = xspan(side, xc, HC)
            for g in range(4):
                add(f'hgrp_{q}_{c}_{g}', 'hgrp', x, y0 + g * HGRP, w, HGRP, o, q, idx=g, col=c)
        x, w = xspan(side, XW[3], AS)
        add(f'astk_{q}', 'astk', x, y0, w, HALF, o, q)      # macro partition: the static strip keeps its own chains
        yb = y0 + HALF
        x, w = xspan(side, 0.0, C0 + C1)
        add(f'hroot_{q}', 'hroot', x, yb, w, BAND, o, q)
        x, w = xspan(side, XW[2], 2 * HC + AS)
        add(f'bandft_{q}', 'bandft', x, yb, w, BAND, o, q)
    for half, y0 in (('S', Y_S), ('N', Y_N)):
        for r in range(16):
            add(f'pvrow_{half}_{r}', 'pvrow', XW[-1], y0 + r * PVROW, PV, PVROW, 'R0', half, idx=r)
    add('hub', 'hub', XW[-1], Y_MB, PV, BAND, 'R0', 'die')
    add('bandc', 'bandc', XW[-1], Y_TB, PV, BAND, 'R0', 'die')
    xc = (DIE_W - CORE_W) / 2
    add('sys_core', 'sys_core', xc, Y_SYS, CORE_W, SYS_CORE_H, 'R0', 'die')
    add('syswing_core_W', 'syswing_core', 0.0, Y_SYS, xc, SYS_CORE_H, 'R0', 'die')
    add('syswing_core_E', 'syswing_core', xc + CORE_W, Y_SYS, xc, SYS_CORE_H, 'R0', 'die')
    xi = (DIE_W - IO_W) / 2
    add('sys_io', 'sys_io', xi, Y_SYS + SYS_CORE_H, IO_W, SYS_IO_H, 'R0', 'die')
    add('syswing_io_W', 'syswing_io', 0.0, Y_SYS + SYS_CORE_H, xi, SYS_IO_H, 'R0', 'die')
    add('syswing_io_E', 'syswing_io', xi + IO_W, Y_SYS + SYS_CORE_H, xi, SYS_IO_H, 'R0', 'die')
    return P


# ------------------------------------------------------------------------------------------------ block -> partition
ASTK_G = {}


def astk_groups(asb):
    """astk sub-block -> head group it exchanges the most bits with (ectl / hst of group g)"""
    w = collections.defaultdict(collections.Counter)
    for e in asb['edges']:
        for a_, b_ in ((e['s'], e['d']), (e['d'], e['s'])):
            if a_.startswith('astk_'):
                m = re.match(r'(?:ectl|head|hst)_(WS|ES|WN|EN)_(\d+)', b_)
                if m:
                    w[a_][int(m.group(2)) % 4] += e['bits']
    for n, c in w.items():
        ASTK_G[n] = c.most_common(1)[0][0]


SYS_CORE = ('kvs_ctl', 'kvs_attn', 'kvs_emb', 'embgw', 'seq')
SYS_IO = ('host', 'd2d_kv', 'ucie_rom', 'serdes_host', 'pll', 'dcal', 'fwb_ep', 'fwb_rs', 'ckb_kv')


def slg_row(k):
    """plan row of slg_k: beside its ECTL (ectl_k = head column k // 4, group k % 4; hgrp g spans pcrows 2g, 2g+1)"""
    return 2 * (k % 4) + k // 4


def vport_row(j):
    """vport_j serves slg 2j, 2j+1 (plan rows r, r+2): sits in the row between them"""
    return (slg_row(2 * j) + slg_row(2 * j + 1)) // 2


def pc_relabel(asb, B):
    """PC-group relabel (data layout, compiler): slg_k now owns the 4 PCs physically in its plan row.  Every as-built
    edge slg_k <-> kvpc_n / hsl_n (n in slg_k's as-built row) is re-pointed to the PC of the same slot in the plan row.
    The kvpc / hsl neighbour chains and the PHY channel edges stay physical."""
    rowmap = {}
    for n, b in B.items():
        m = re.match(r'slg_(WS|ES|WN|EN)_(\d)$', n)
        if m:
            q, k = m.group(1), int(m.group(2))
            phy = B[f'phy_{q}']
            r_asb = min(7, max(0, int((b['y'] + b['h'] / 2 - phy['y']) // 1512)))
            rowmap[(q, r_asb)] = (k, slg_row(k))
    moved = 0
    for e in asb['edges']:
        ends = [e['s'], e['d']]
        if not any(x.startswith('slg_') for x in ends):
            continue
        for i, x in enumerate(ends):
            m = re.match(r'(kvpc|hsl)_(WS|ES|WN|EN)_(\d+)(.*)$', x)
            if m:
                cls, q, nn, tail = m.group(1), m.group(2), int(m.group(3)), m.group(4)
                k, r_new = rowmap[(q, nn // 4)]
                other = ends[1 - i]
                if other.split('__')[0] != f'slg_{q}_{k}':
                    continue
                ends[i] = f'{cls}_{q}_{4 * r_new + nn % 4}{tail}'
                moved += ends[i] != x
        e['s'], e['d'] = ends
    return moved


def assign_blocks(B):
    """as-built block -> plan partition (and its local name inside the partition)"""
    ext = collections.defaultdict(lambda: [1e9, 1e9, -1e9, -1e9])
    for n, b in B.items():
        t = n.split('__')[0]
        e = ext[t]
        e[0], e[1] = min(e[0], b['x']), min(e[1], b['y'])
        e[2], e[3] = max(e[2], b['x'] + b['w']), max(e[3], b['y'] + b['h'])
    mid_x = 13735.872 / 2
    out = {}

    def hslot(q, r):
        """head group r (ectl_r) sits beside its slg_r: pcrow k of slg_r -> hgrp column k % 2, group k // 2"""
        b = B[f'slg_{q}_{r}']
        k = min(7, max(0, int((b['y'] + b['h'] / 2 - ext[f'phy_{q}'][1]) // 1512)))
        return f'hgrp_{q}_{k % 2}_{k // 2}'
    for n, b in B.items():
        t = n.split('__')[0]
        rest = n[len(t):]
        yc = b['y'] + b['h'] / 2
        m = re.match(r'(phy|kvpc|hsl|slg|vport|head|ectl|hst|astk|kc|kvs_hroot)_(WS|ES|WN|EN)(?:_(\d+))?(?:_(\d+))?(.*)$', t)
        if m:
            cls, q, i1, i2, tail = m.groups()
            if cls == 'phy':
                out[n] = (f'phy_{q}', 'phy')
            elif cls in ('kvpc', 'hsl'):
                k = int(i1)
                out[n] = (f'pcrow_{q}_{k // 4}', f'{cls}{k % 4}{rest}')
            elif cls in ('slg', 'vport'):
                y0 = ext[f'phy_{q}'][1]
                k = min(7, max(0, int((yc - y0) // 1512)))
                out[n] = (f'pcrow_{q}_{k}', f'{cls}{rest}')
            elif cls == 'head':
                r, i = int(i1), int(i2)
                out[n] = (hslot(q, r), f'head{i}{rest}')
            elif cls == 'ectl':
                r = int(i1)
                out[n] = (hslot(q, r), f'ectl{rest}')
            elif cls == 'hst':
                r, i = int(i1), int(i2)
                out[n] = (hslot(q, r), f'hst{i}{tail}{rest}')
            elif cls == 'astk':
                e = ext[t]
                g = min(3, max(0, int((yc - e[1]) // ((e[3] - e[1]) / 4))))
                out[n] = (f'astk_{q}', f'astk{rest}')
            elif cls in ('kc', 'kvs_hroot'):
                out[n] = (f'hroot_{q}', cls)
            continue
        m = re.match(r'pvw_([01])$', t)
        if m:
            half = 'S' if m.group(1) == '0' else 'N'
            e = ext[t]
            r = min(15, max(0, int((yc - e[1]) // ((e[3] - e[1]) / 16))))
            out[n] = (f'pvrow_{half}_{r}', 'pv' + rest)
            continue
        if t.startswith('hp_fault'):
            side = 'W' if b['x'] < mid_x else 'E'
            half = 'S' if yc < 18000 else 'N'
            out[n] = (f'hroot_{side}{half}', t)
            continue
        if t in ('ahub', 'pvfin'):
            out[n] = ('hub', t + rest)
        elif t in SYS_CORE:
            out[n] = ('sys_core', t + rest)
        elif t in SYS_IO:
            out[n] = ('sys_io', t + rest)
        else:
            raise ValueError(f'unassigned block {n}')
    return out


# ------------------------------------------------------------------------------------------------ partition graph
def faces_between(a, b):
    """shared face of a (die frame) with b: (face of a, lo, hi) or None"""
    eps = 1e-3
    ax0, ay0, ax1, ay1 = a['x'], a['y'], a['x'] + a['w'], a['y'] + a['h']
    bx0, by0, bx1, by1 = b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']
    if abs(ax1 - bx0) < eps or abs(bx1 - ax0) < eps:
        lo, hi = max(ay0, by0), min(ay1, by1)
        if hi - lo > 1.0:
            return ('E' if abs(ax1 - bx0) < eps else 'W', lo, hi)
    if abs(ay1 - by0) < eps or abs(by1 - ay0) < eps:
        lo, hi = max(ax0, bx0), min(ax1, bx1)
        if hi - lo > 1.0:
            return ('N' if abs(ay1 - by0) < eps else 'S', lo, hi)
    return None


def adjacency(P):
    names = sorted(P)
    adj = collections.defaultdict(dict)
    # bucket by coarse grid to avoid O(n^2) on 200 partitions (cheap anyway)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            f = faces_between(P[a], P[b])
            if f:
                adj[a][b] = f
                fb = dict(E='W', W='E', N='S', S='N')[f[0]]
                adj[b][a] = (fb, f[1], f[2])
    return adj


# traversal (ft) rules per partition class: allowed (in_face, out_face) pairs, die frame
STRAIGHT = {('W', 'E'), ('E', 'W'), ('N', 'S'), ('S', 'N')}
ALL = {(i, o) for i in 'NSEW' for o in 'NSEW' if i != o}
FT_RULE = dict(phy=set(), hgrp={('W', 'E'), ('E', 'W')}, astk={('W', 'E'), ('E', 'W')},
               pcrow=ALL, pvrow=ALL, hroot=ALL, bandft=ALL, hub=ALL, bandc=ALL, sys_core=ALL, sys_io=ALL,
               syswing_core=ALL, syswing_io=ALL)


def centre(p):
    return (p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)


def span(p, fi, fo):
    if {fi, fo} == {'E', 'W'}:
        return p['w']
    if {fi, fo} == {'N', 'S'}:
        return p['h']
    return (p['w'] + p['h']) / 2


def route(P, adj, src, dst, small=False, cache={}):
    """cheapest partition path from src (a name or a set of tree nodes) -> dst honouring FT_RULE in crossed partitions"""
    srcs = frozenset([src]) if isinstance(src, str) else frozenset(src)
    key = (srcs, dst, small)
    if key in cache:
        return cache[key]
    hgrp_end = P[dst]['cls'] == 'hgrp' or any(P[s_]['cls'] == 'hgrp' for s_ in srcs)
    dist = {(s_, None): 0.0 for s_ in srcs}
    pos = {(s_, None): centre(P[s_]) for s_ in srcs}
    prev = {}
    pq = [(0.0, s_, None) for s_ in sorted(srcs)]
    heapq.heapify(pq)
    best = None
    while pq:
        d, u, fin = heapq.heappop(pq)
        if d > dist.get((u, fin), 1e18):
            continue
        if u == dst:
            best = (u, fin)
            break
        for v, (fo, lo, hi) in adj[u].items():
            if fin is not None:
                if (fin, fo) not in FT_RULE[P[u]['cls']]:
                    continue
                if small and P[u]['cls'] in ('hgrp', 'astk') and not hgrp_end:
                    continue          # control lanes stay in the corridors (PC column, bands, PV column)
            fv = dict(E='W', W='E', N='S', S='N')[fo]
            cu = pos[(u, fin)]
            mid = (lo + hi) / 2
            pu_ = P[u]
            cv = {'E': (pu_['x'] + pu_['w'], mid), 'W': (pu_['x'], mid), 'N': (mid, pu_['y'] + pu_['h']),
                  'S': (mid, pu_['y'])}[fo]
            if v == dst:
                cd_ = centre(P[v])
                cv2 = cd_
            else:
                cv2 = cv
            nd = d + abs(cu[0] - cv[0]) + abs(cu[1] - cv[1]) + abs(cv[0] - cv2[0]) + abs(cv[1] - cv2[1]) + 150.0
            if fin is not None and P[u]['cls'] == 'pcrow' and fo in 'NS':
                nd += 150.0          # PC column: 2 stations per 1.5-mm row
            if nd < dist.get((v, fv), 1e18):
                dist[(v, fv)] = nd
                pos[(v, fv)] = cv
                prev[(v, fv)] = (u, fin, fo)
                heapq.heappush(pq, (nd, v, fv))
    if best is None:
        cache[key] = None
        return None
    path = []
    st = best
    while st in prev:
        u, fin, fo = prev[st]
        path.append((u, st[0], fo))         # hop u -> v leaving u by face fo
        st = (u, fin)
    path.reverse()
    cache[key] = path
    return path


# ------------------------------------------------------------------------------------------------ connections
CLOCK_PORT = re.compile(r'^(pll_|ck|clk)')
RESET_PORT = re.compile(r'rst')


def nbits(rs):
    return sum(b - a + 1 for a, b in rs)


def union(rs_list):
    s = set()
    for rs in rs_list:
        for a, b in rs:
            s.update(range(a, b + 1))
    return s


def connections(asb, where):
    """inter-partition signal groups: key (src block, src port) -> {dst part: [(dst block, dst port, bits, srcbitset,
    stages)]}; plus spine (clock/reset) and internal tallies"""
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    tally = collections.Counter()
    for e in asb['edges']:
        s, d = e['s'], e['d']
        ps, pd = where[s][0], where[d][0]
        if CLOCK_PORT.match(e['sp']) or CLOCK_PORT.match(e['dp']):
            tally['clock_bits'] += e['bits']
            continue
        if RESET_PORT.search(e['dp']) and (RESET_PORT.search(e['sp']) or e['sp'] in ('b', 'q')):
            tally['reset_bits'] += e['bits']
            continue
        if ps == pd:
            tally['internal_bits'] += e['bits']
            continue
        tally['lane_bits'] += e['bits']
        groups[(s, e['sp'])][pd].append((d, e['dp'], e['bits'], e['sbits'], e['stages']))
    return groups, tally


# ------------------------------------------------------------------------------------------------ main build
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--asbuilt', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    asb = json.load(gzip.open(a.asbuilt))
    B = asb['blocks']
    P = build_partitions()
    moved = 0
    where = assign_blocks(B)
    for n, (p, _) in where.items():
        if p not in P:
            raise ValueError(f'{n} -> unknown partition {p}')
    adj = adjacency(P)
    groups, tally = connections(asb, where)

    # gathers: one dst (block, port) fed from several source partitions -> mux chain (dst port width)
    by_dst = collections.defaultdict(list)
    for (s, sp), dd in groups.items():
        for pd, lst in dd.items():
            for (d, dp, bits, sb, st) in lst:
                by_dst[(d, dp)].append((s, sp, bits, st))
    gather_dst = {k: v for k, v in by_dst.items() if len({where[s][0] for s, _, _, _ in v}) > 2
                  and max(b for _, _, b, _ in v) >= 128}     # wide time-multiplexed collections only

    # control-bundle families (o_c0..o_c7, dcfg__age_vport__*, ...) of one source block -> one bundle (one tree)
    fam = collections.defaultdict(lambda: collections.defaultdict(list))
    for (s_, sp_), dd in groups.items():
        width = sum(len(union([x[3] for x in lst])) for lst in dd.values())
        key = (s_, re.sub(r'\d+', '#', sp_)) if width <= 64 else (s_, sp_)
        off = 4096 * len(fam[key]) if key[1] != sp_ else 0
        for pd, lst in dd.items():
            for (d, dp, bits, sb, st) in lst:
                fam[key][pd].append((d, dp, bits, [[a_ + off, b_ + off] for a_, b_ in sb], st))
    groups = fam

    trees = []        # each: dict(root=(part, sigid), edges=[(u, v, face, bits)], dests={part: bits}, kind)
    hops_asbuilt = {}
    for (s, sp), dd in sorted(groups.items()):
        ps = where[s][0]
        dests = {}
        asb_st = {}
        for pd, lst in dd.items():
            if all((d, dp) in gather_dst for d, dp, _, _, _ in lst):
                continue
            dests[pd] = union([x[3] for x in lst])
            asb_st[pd] = max(x[4] for x in lst)
        if not dests:
            continue
        # tap tree: union of shortest paths, bits per tree edge = union of bits needed below
        tedges = {}
        children = collections.defaultdict(set)
        tree_nodes = {ps}
        cps = centre(P[ps])
        small = len(set().union(*dests.values())) <= 96
        for pd in sorted(dests, key=lambda p: (abs(centre(P[p])[0] - cps[0]) + abs(centre(P[p])[1] - cps[1]), p)):
            if pd in tree_nodes:
                continue
            path = route(P, adj, tree_nodes, pd, small)     # Steiner growth: attach to the nearest tree node
            if path is None:
                raise ValueError(f'no route {ps} -> {pd} for {s}.{sp}')
            for (u, v, fo) in path:
                if (u, v) not in tedges and v not in tree_nodes:
                    tedges[(u, v)] = fo
                    children[u].add(v)
                tree_nodes.add(u)
                tree_nodes.add(v)
        # a node may be reached by two parents (path merge) -> keep the first parent only
        parent = {}
        order = [ps]
        seen = {ps}
        while order:
            u = order.pop(0)
            for v in sorted(children[u]):
                if v not in seen:
                    seen.add(v)
                    parent[v] = u
                    order.append(v)
        need = {}

        def below(u):
            bset = set(dests.get(u, ()))
            for v in [w for w, pu in parent.items() if pu == u]:
                bset |= below(v)
            need[u] = bset
            return bset
        below(ps)
        allbits = need[ps]
        if len(allbits) <= 96:          # control bundle: full-width trunk (one regular bus through every partition)
            for k_ in need:
                if need[k_]:
                    need[k_] = allbits
        edges = [(parent[v], v, tedges[(parent[v], v)], len(need[v])) for v in parent if need[v]]
        trees.append(dict(src=s, sp=sp, root=ps, edges=edges, dests={k: len(v) for k, v in dests.items()},
                          asbuilt_stages=asb_st, kind='p2p' if len(dests) == 1 else 'tap_tree'))
    gathers = []
    for (d, dp), srcs in sorted(gather_dst.items()):
        pd = where[d][0]
        width = max(b for _, _, b, _ in srcs)
        sparts = sorted({where[s][0] for s, _, _, _ in srcs})
        # chain: order source partitions by distance to the destination (farthest first)
        cd = centre(P[pd])
        sparts.sort(key=lambda p: -(abs(centre(P[p])[0] - cd[0]) + abs(centre(P[p])[1] - cd[1])))
        gathers.append(dict(dst=d, dp=dp, dpart=pd, width=width, srcparts=sparts,
                            asbuilt_stages=max(st for _, _, _, st in srcs), n_src=len(srcs)))

    # ---- lanes: tree edge sequences between functional nodes; stations per crossed partition
    def stations(part, fi, fo):
        return max(1, math.ceil(span(P[part], fi, fo) / REACH - 1e-9))
    OPPF = dict(E='W', W='E', N='S', S='N')
    lanes = []
    dest_lat = {}
    for t in trees:
        kids = collections.defaultdict(list)
        for (u, v, fo, bits) in t['edges']:
            kids[u].append((v, fo, bits))
        functional = {t['root']} | set(t['dests']) | {u for u in kids if len(kids[u]) > 1}
        # walk
        lat_at = {t['root']: 0}
        stack = [(t['root'], v, fo, bits) for (v, fo, bits) in kids[t['root']]]
        while stack:
            start, v, fo, bits = stack.pop()
            hops = [(start, v, fo, bits)]
            cur = v
            while cur not in functional:
                (nv, nfo, nb), = kids[cur]
                hops.append((cur, nv, nfo, nb))
                cur = nv
            st = 0
            for (u, w, f, b), (u2, w2, f2, b2) in zip(hops, hops[1:]):
                st += stations(w, OPPF[f], f2)
            lid = f"L{len(lanes)}"
            lat = st + 1
            lanes.append(dict(id=lid, src=t['src'], sp=t['sp'], hops=hops, stations=st, cycles=lat,
                              width=max(b for *_, b in hops), kind=t['kind']))
            tap = 1 if start != t['root'] else 0
            lat_at[cur] = lat_at[start] + lat + tap
            for (nv, nfo, nb) in kids[cur]:
                stack.append((cur, nv, nfo, nb))
        for d in t['dests']:
            dest_lat[(t['src'], t['sp'], d)] = (lat_at[d], t['asbuilt_stages'][d])
    for g in gathers:
        chain = g['srcparts'] + ([g['dpart']] if g['dpart'] not in g['srcparts'] else [])
        tot = 0
        for a_, b_ in zip(chain, chain[1:]):
            path = route(P, adj, a_, b_, g['width'] <= 96)
            hops = [(u, v, fo, g['width']) for (u, v, fo) in path]
            st = 0
            for (u, w, f, b), (u2, w2, f2, b2) in zip(hops, hops[1:]):
                st += stations(w, OPPF[f], f2)
            lid = f"L{len(lanes)}"
            lanes.append(dict(id=lid, src=g['dst'], sp='gather:' + g['dp'], hops=hops, stations=st, cycles=st + 1,
                              width=g['width'], kind='gather_chain'))
            tot += st + 1 + 1
        g['chain_cycles'] = tot

    json.dump(dict(P=P, where=where, trees=trees, gathers=gathers, lanes=lanes, tally=tally,
                   dest_lat={'|'.join(k): v for k, v in dest_lat.items()}),
              gzip.open(a.out, 'wt'))
    print(f'partitions {len(P)}, trees {len(trees)} (tap {sum(t["kind"] == "tap_tree" for t in trees)}), '
          f'gathers {len(gathers)}, lanes {len(lanes)}, pc relabel edges {moved}, tally {dict(tally)}', file=sys.stderr)


if __name__ == '__main__':
    main()
