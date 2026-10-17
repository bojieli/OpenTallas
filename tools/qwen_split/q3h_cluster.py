"""q3h hierarchical compute die (Q-DIEPLAN3, owner direction 2026-10-16 19:00): the ROM array becomes 48 instances of ONE
hardened cluster C_B16 (4 columns x 4 rows of ROM tiles = one reduction group: the 4 adder levels stay inside, one
514-b reduction exit 'rs' = today's bword, one broadcast entry 'bc'), the comb broadcast (xs_tap -> xcol head row ->
xcst corridor stations -> tile tap) is replaced by a die-top relay H-tree, and the die top routes only inter-cluster
relays.

apply(v, m) runs in qwen_rom_fulldie_b3r2.selected() after the b2 graph and before the pin grants / relays when
OT_SPLIT_Q3H=1:
  * every tile t_c_r, corridor station s_c_r and column head h_c leaves the die; per reduction group one instance
    c16_<side><g>_<band> of master qfd_c_b16 takes the group's place (outline = the contract's, default the bbox of
    its 16 tiles), orientation per the contract (bands 0-1 MX / 2-3 R0 on W, mirrored on E);
  * tree_block / corridor / tap / head_chain buses go (they are inside the cluster now); every bword keeps its port
    sink and takes (cluster, rs) as its source; the head fault chain becomes the cluster fault chain; rst_field / clock
    trunks lose the retired sinks and gain one rst_n / ck per cluster (regions re-filed from placement afterwards);
  * the broadcast: the die-top H-tree file (OT_SPLIT_Q3H_HTREE, from the HT helper) gives the stations and edges;
    without it the built-in provisional tree is used: per side a root station in the head gap beside the array's inner
    edge, one station per 4-column group in the head gap feeding bands 1 and 2, bands 0 / 3 through the cluster's
    registered feedthrough bc_o.
Contract (OT_SPLIT_Q3H_CONTRACT, from the CB helper) or the built-in provisional port plan: ports with face / layer /
bits, pins at >= 0.167 um pitch (<= 6 pins/um/face).  The cluster RTL (qfd_c_b16) is the CB helper's; until it is on the
source tree the strict port bind fails and a chain must run OT_CHAIN_DIAGNOSTIC=1 (DIAGNOSTIC_ONLY).
"""
import json
import os
import re
from pathlib import Path

PITCH = 0.168          # >= 0.167 um: <= 6 pins / um / face (owner standard), on the 0.024 grid
CMASTER = 'qfd_c_b16'
HEAD_BITS = 1567
RS_BITS = 514

PROVISIONAL_PORTS = {      # face is the MASTER face; bands 0-1 sit MX, so 'S' (bc) faces the head gap there too
    'bc': dict(dir='input', bits=HEAD_BITS, face='S', layer='M5'),
    'bc_o': dict(dir='output', bits=HEAD_BITS, face='N', layer='M5'),
    'rs': dict(dir='output', bits=RS_BITS, face='E', layer='M4'),
    'fault': dict(dir='output', bits=1, face='E', layer='M4'),
    'fault_i': dict(dir='input', bits=1, face='E', layer='M4'),
    'ck': dict(dir='input', bits=1, face='E', layer='M4'),
    'rst_n': dict(dir='input', bits=1, face='E', layer='M4'),
    'cid': dict(dir='input', bits=6, face='E', layer='M4'),
}


def _snap(x, q=0.024):
    return round(round(x / q) * q, 3)


def _load(env):
    p = os.environ.get(env, '').strip()
    return json.loads(Path(p).read_text()) if p else None


def _group_of(name):
    m_ = re.fullmatch(r't_(\d+)_(\d+)', name)
    if not m_:
        return None
    c, r = int(m_.group(1)), int(m_.group(2))
    side = 'W' if c < 24 else 'E'
    g = (23 - c) // 4 if side == 'W' else (c - 24) // 4          # 0 = next to the centre
    return side, g, r // 4


def _orient(side, band):
    lower = band <= 1
    if side == 'W':
        return 'MX' if lower else 'R0'
    return 'R180' if lower else 'MY'


def _master(v, w, h, ports):
    q = v.Master(CMASTER, w, h, 9, 'q3h C_B16 cluster: 16 ROM tiles (4x4 reduction group, adders inside) + the '
                 'in-cluster broadcast H-tree stations + regional reset re-time + one regional clock root')
    faces = {}
    for p, d in ports.items():
        faces.setdefault(d['face'], []).append((p, d))
    for f, items in faces.items():
        length = w if f in 'NS' else h
        need = sum((d['bits'] - 1) * PITCH + 4.0 for _, d in items)
        if need > length - 20:
            raise ValueError(f'q3h {CMASTER}.{f}: {need:.1f} um of pins at {PITCH} pitch exceed the face {length:.1f}')
        cur = (length - need) / 2
        for p, d in items:
            if 'range' in d:
                a, b = d['range']
                ps = [_snap(a + (b - a) * k / max(1, d['bits'] - 1)) for k in range(d['bits'])]
            else:
                ps = [_snap(cur + k * PITCH) for k in range(d['bits'])]
            q.ports[p] = ('pins', d['bits'], f, d['layer'], ps, 1)
            q.order.append(p)
            cur = ps[-1] + 4.0
    return q


def _station_master(v, name, w, h, nout, bits):
    q = v.Master(name, w, h, 3, f'q3h die-top broadcast station: one registered {bits}-b stage, {nout} children')
    q.ports['d_in'] = ('pins', bits, 'W', 'M4', [_snap((h - (bits - 1) * PITCH) / 2 + k * PITCH) for k in range(bits)], 1)
    q.order.append('d_in')
    for j in range(nout):
        f = 'ENS'[j % 3]
        L = h if f in 'EW' else w
        q.ports[f'd_out{j}'] = ('pins', bits, f, 'M4' if f in 'EW' else 'M5',
                                [_snap((L - (bits - 1) * PITCH) / 2 + k * PITCH) for k in range(bits)], 1)
        q.order.append(f'd_out{j}')
    q.ports['ck'] = ('pins', 1, 'W', 'M4', [_snap(4.0)], 1)
    q.order.append('ck')
    return q


def _free(rects, r):
    return not any(a < r[2] and r[0] < c and b < r[3] and r[1] < d for a, b, c, d in rects)


def _site(rects, x, y, w, h, die, step=8.64, rings=300):
    for ring in range(rings):
        st = ring * step
        cands = [(0.0, 0.0)] if ring == 0 else \
            [(dx, dy) for dx in (-st, st) for dy in [i * step for i in range(-ring, ring + 1)]] + \
            [(dx, dy) for dy in (-st, st) for dx in [i * step for i in range(-ring + 1, ring)]]
        for dx, dy in sorted(cands, key=lambda t: abs(t[0]) + abs(t[1])):
            x0, y0 = _snap(x - w / 2 + dx, 0.432), _snap(y - h / 2 + dy, 2.16)
            r = (x0, y0, x0 + w, y0 + h)
            if x0 >= 0 and y0 >= 0 and r[2] <= die['w'] and r[3] <= die['h'] and _free(rects, r):
                return x0, y0
    raise ValueError(f'q3h: no free station site near ({x:.0f}, {y:.0f})')


def apply(v, m):
    contract = _load('OT_SPLIT_Q3H_CONTRACT') or {}
    htree = _load('OT_SPLIT_Q3H_HTREE')
    ports = contract.get('ports') or PROVISIONAL_PORTS
    by = {i.name: i for i in m['insts']}
    groups = {}
    for i in m['insts']:
        k = _group_of(i.name)
        if k:
            groups.setdefault(k, []).append(i)
    if len(groups) != 48 or any(len(t) != 16 for t in groups.values()):
        raise ValueError(f'q3h: expected 48 groups of 16 tiles, got {len(groups)}')
    retired = {i.name for i in m['insts'] if re.fullmatch(r'(t_\d+_\d+|s_\d+_\d+|h_\d+)', i.name)}
    bb = {k: (min(t.x for t in ts), min(t.y for t in ts), max(t.x + t.w for t in ts), max(t.y + t.h for t in ts))
          for k, ts in groups.items()}
    W0 = max(b[2] - b[0] for b in bb.values())
    H0 = max(b[3] - b[1] for b in bb.values())
    w, h = contract.get('outline', [round(W0, 3), round(H0, 3)])
    M = v.masters(m, 1)
    M[CMASTER] = _master(v, w, h, ports)
    names = {}
    new = []
    for (side, g, band), b in sorted(bb.items()):
        n = f'c16_{side}{g}_{band}'
        names[(side, g, band)] = n
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        new.append(v.Inst(n, CMASTER, _snap(cx - w / 2, 0.432), _snap(cy - h / 2, 2.16), w, h,
                          orient=_orient(side, band), kind='cluster', region='field', domain='stream_1p2'))
    # tile of each bword source -> its cluster
    tile_group = {t.name: names[k] for k, ts in groups.items() for t in ts}
    keep, dropped = [], {}
    for bid, cl, bits, eps in m['buses']:
        if cl in ('tree_block', 'corridor', 'tap', 'head_chain'):
            dropped[cl] = dropped.get(cl, 0) + 1
            continue
        if bid.startswith('bword'):
            src = eps[0][0]
            if src not in tile_group:
                raise ValueError(f'q3h: {bid} source {src} not a tile')
            keep.append((bid, cl, bits, [(tile_group[src], 'rs')] + list(eps[1:])))
            continue
        if cl == 'clock_trunk':
            e2 = [e for e in eps if e[0] not in retired]
            add = sorted({tile_group[e[0]] for e in eps if e[0] in tile_group})
            e2 += [(c, 'ck') for c in add if not any(x == c for x, _ in e2)]
            if len(e2) > 1:
                keep.append((bid, cl, bits, e2))
            continue
        if cl == 'reset':
            e2 = [e for e in eps if e[0] not in retired]
            add = sorted({tile_group[e[0]] for e in eps if e[0] in tile_group})
            e2 += [(c, 'rst_n') for c in add]
            keep.append((bid, cl, bits, e2))
            continue
        if any(e[0] in retired for e in eps):
            raise ValueError(f'q3h: bus {bid} ({cl}) touches a retired tile/station/head: {eps[:3]}')
        keep.append((bid, cl, bits, eps))
    # every cluster has exactly one ck / rst_n
    have_ck = {e[0] for b in keep if b[1] == 'clock_trunk' for e in b[3]}
    have_rst = {e[0] for b in keep if b[1] == 'reset' for e in b[3]}
    miss = [n for n in names.values() if n not in have_ck or n not in have_rst]
    if miss:
        raise ValueError(f'q3h: clusters without ck/rst_n: {miss[:4]}')
    m['insts'] = [i for i in m['insts'] if i.name not in retired] + new
    m['ties'] = [t for t in m.get('ties', []) if t[0] not in retired]
    for k, n in sorted(names.items()):
        idx = sorted(names).index(k)
        m['ties'].append((n, 'cid', 6, idx))
    # fault chain: outermost group inward along each band, bands chained toward the head gap, last -> xs_tap
    for side, port in (('W', 'hw_f'), ('E', 'he_f')):
        order = [names[(side, g, b)] for b in (0, 3, 1, 2) for g in range(5, -1, -1)]
        m['ties'].append((order[0], 'fault_i', 1, 0))
        for a, c in zip(order, order[1:]):
            keep.append((f'q3h_fault_{a}', 'tree_spine', 1, [(a, 'fault'), (c, 'fault_i')]))
        keep.append((f'q3h_fault_{side}', 'tree_spine', 1, [(order[-1], 'fault'), ('xs_tap', port)]))
    # broadcast H-tree
    rects = [(i.x, i.y, i.x + i.w, i.y + i.h) for i in m['insts']]
    if htree:
        for s in htree['stations']:
            mn = s.get('m') or f"qfd_q3h_st{len(s.get('children', [])) or 2}_{round(s['w'])}x{round(s['h'])}"
            if mn not in M:
                M[mn] = _station_master(v, mn, s['w'], s['h'], len(s.get('children', [])) or 2, s.get('down_bits', HEAD_BITS))
            m['insts'].append(v.Inst(s['n'], mn, s['x'], s['y'], s['w'], s['h'], kind='station', region='field'))
        for e in htree['edges']:
            keep.append((e['b'], 'tree_spine', e['n'], [tuple(e['src']), tuple(e['dst'])]))
        src = 'htree-file'
    else:
        src = 'provisional'
        gap = _head_gap(m, new)
        for side, port in (('W', 'hw_d'), ('E', 'he_d')):
            cl = [n for k, n in names.items() if k[0] == side]
            gx = {g: [i for i in new if i.name in (names[(side, g, 1)], names[(side, g, 2)])] for g in range(6)}
            xs = {g: sum(i.cx for i in gx[g]) / 2 for g in range(6)}
            SW, SH = 285.12, 285.12
            # root: inner edge of the array in the head gap
            rx = xs[0] + (1 if side == 'W' else -1) * (w / 2 + 400.0)
            rn = f'q3h_root_{side}'
            mnr = f'qfd_q3h_st2_{round(SW)}x{round(SH)}'
            M.setdefault(mnr, _station_master(v, mnr, SW, SH, 2, HEAD_BITS))
            x0, y0 = _site(rects, rx, gap, SW, SH, m['die'])
            m['insts'].append(v.Inst(rn, mnr, x0, y0, SW, SH, kind='station', region='field'))
            rects.append((x0, y0, x0 + SW, y0 + SH))
            keep.append((f'q3h_bc_{side}_root', 'tree_spine', HEAD_BITS, [('xs_tap', port), (rn, 'd_in')]))
            # root -> two half stations (groups 0-2 / 3-5) -> group stations -> bands 1 / 2 -> feedthrough bands 0 / 3
            for hlf, gs in ((0, (0, 1, 2)), (1, (3, 4, 5))):
                hn = f'q3h_half_{side}{hlf}'
                mnh = f'qfd_q3h_st3_{round(SW)}x{round(SH)}'
                M.setdefault(mnh, _station_master(v, mnh, SW, SH, 3, HEAD_BITS))
                hx = sum(xs[g] for g in gs) / 3
                x0, y0 = _site(rects, hx, gap, SW, SH, m['die'])
                m['insts'].append(v.Inst(hn, mnh, x0, y0, SW, SH, kind='station', region='field'))
                rects.append((x0, y0, x0 + SW, y0 + SH))
                keep.append((f'q3h_bc_{side}_h{hlf}', 'tree_spine', HEAD_BITS, [(rn, f'd_out{hlf}'), (hn, 'd_in')]))
                for j, g in enumerate(gs):
                    gn = f'q3h_grp_{side}{g}'
                    mng = f'qfd_q3h_st2_{round(SW)}x{round(SH)}'
                    x0, y0 = _site(rects, xs[g], gap, SW, SH, m['die'])
                    m['insts'].append(v.Inst(gn, mng, x0, y0, SW, SH, kind='station', region='field'))
                    rects.append((x0, y0, x0 + SW, y0 + SH))
                    keep.append((f'q3h_bc_{side}_g{g}', 'tree_spine', HEAD_BITS, [(hn, f'd_out{j}'), (gn, 'd_in')]))
                    for k_, band in enumerate((1, 2)):
                        keep.append((f'q3h_bc_{side}{g}_{band}', 'tree_spine', HEAD_BITS,
                                     [(gn, f'd_out{k_}'), (names[(side, g, band)], 'bc')]))
                    keep.append((f'q3h_bc_{side}{g}_0', 'tree_spine', HEAD_BITS,
                                 [(names[(side, g, 1)], 'bc_o'), (names[(side, g, 0)], 'bc')]))
                    keep.append((f'q3h_bc_{side}{g}_3', 'tree_spine', HEAD_BITS,
                                 [(names[(side, g, 2)], 'bc_o'), (names[(side, g, 3)], 'bc')]))
    # band-3/0 clusters drive nothing on bc_o: their feedthrough output is an open output (no tie on an output)
    m['buses'] = keep
    # the relay planner judges row gaps from the tile bodies; clusters are the bodies now
    m['q3h'] = dict(clusters=len(new), master=CMASTER, outline=[w, h], ports={p: d['bits'] for p, d in ports.items()},
                    contract=os.environ.get('OT_SPLIT_Q3H_CONTRACT') or 'provisional', htree=src,
                    retired=len(retired), dropped_buses=dropped)

    def fixed(model, k=1, port_bits=None):
        return dict(M)
    v.masters = fixed
    return m['q3h']


def _head_gap(m, clusters):
    """centre y of the widest horizontal gap between cluster bands (the head gap between bands 1 and 2)"""
    spans = sorted({(round(i.y, 1), round(i.y + i.h, 1)) for i in clusters})
    best = max(((b[0] - a[1], (a[1] + b[0]) / 2) for a, b in zip(spans, spans[1:])), default=None)
    if best is None or best[0] < 300:
        raise ValueError(f'q3h: no head gap between cluster bands ({spans})')
    return best[1]
