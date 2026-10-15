#!/usr/bin/env python3
"""Hub-face pin re-assignment search on an exported S81 construction plan (screen only, never a closure).

For every hard hub parent (plan inst kind 'hub': dsfd_sp_*), every face is re-packed as a 1-D legal
assignment: the port slices of the face (overlapping slices merged into rigid groups, so interleaved
tracks keep their exact relative layout) translate along the face toward the bit-weighted projection of
their partner pins, then an abacus pass removes overlaps (minimum bit-weighted squared displacement,
original group order kept, face extents respected).  Groups without a data partner (clock/reset/exempt
or unconnected pins) are anchored with a very large weight so they do not move.

ALL incident edges of the hub are re-measured before/after (pin Manhattan per bit, bit-um, max hop,
bits over the 500 um geometry bound and over the 215 um hub-station reach CC_REACH, and the pin_align
bundle verdict), so a candidate is ranked on TOTAL incident cost, never one shortened leg.  The partner
side (stations, other hubs) is NOT moved: hop finalization still owns stations.  The output is a
reproducible per-port translation table for the die pin tool, not an adopted pin plan.
"""
import argparse, collections, gzip, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import group_placement_opt as G
PA = G.PA
HUB_REACH = 215.0
REORDER = False
GEOM = 500.0
ANCHOR_W = 1e9


def along(face):
    return 1 if face in ('E', 'W') else 0


def edge_stats(e, pts):
    a, b = pts
    ll = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(a, b)]
    q = PA.bundle(a, b)
    return dict(sum_bit_um=sum(ll), max_um=max(ll), over500=sum(x > GEOM + 1e-6 for x in ll),
                over215=sum(x > HUB_REACH + 1e-6 for x in ll), verdict=q['verdict'], jog_cut=q.get('jog_cut'),
                why=q.get('why', []))


def abacus(groups, lo, hi):
    """groups: list of dict(start,width,desired,w) in original order -> new starts (no overlap, in [lo,hi])"""
    clusters = []
    for i, g in enumerate(groups):
        c = dict(first=i, last=i, w=g['w'], q=g['w'] * g['desired'], width=g['width'])
        c['x'] = c['q'] / c['w']
        clusters.append(c)
        while True:
            c = clusters[-1]
            c['x'] = min(max(c['q'] / c['w'], lo), hi - c['width'])
            if len(clusters) > 1 and clusters[-2]['x'] + clusters[-2]['width'] > c['x'] + 1e-9:
                p = clusters[-2]
                p['q'] += c['q'] - c['w'] * p['width']
                p['w'] += c['w']
                p['width'] += c['width']
                p['last'] = c['last']
                clusters.pop()
            else:
                break
    out = [None] * len(groups)
    for c in clusters:
        x = c['x']
        for i in range(c['first'], c['last'] + 1):
            out[i] = x
            x += groups[i]['width']
    return out


def run(plan_path, lef_path, out_path, iters, only=None):
    plan = json.loads(G.read(plan_path))
    hubs = {r[0] for r in plan['insts'] if len(r) > 7 and r[7] == 'hub'}
    keep = [b for b in plan['buses'] if any(n in hubs for n, _ in b[3])]
    sub = dict(plan); sub['buses'] = keep
    m = G.Model(sub, [G.read(lef_path)], plan['die'])
    # every pin of every hub (die frame) to find occupied face spans incl. unconnected/exempt pins
    report = dict(schema='opentallas.s81.hub_face_repin_search.v1',
                  scope='SCREEN_ONLY_HUB_FACE_PIN_REASSIGNMENT_NOT_ADOPTED_NOT_NATIVE',
                  source_sha256={str(p.name): hashlib.sha256(p.read_bytes()).hexdigest() for p in (plan_path, lef_path)},
                  tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  rules=dict(reorder=REORDER, hub_station_reach_um=HUB_REACH, geometry_bound_um=GEOM, partner_side_fixed=True,
                             anchored='pins without a data edge in the plan (clock/reset/exempt/unused) do not move'),
                  missing_edges=m.missing, hubs={})
    # map (inst, port) -> list of (edge index, end index)
    use = collections.defaultdict(list)
    for i, e in enumerate(m.edges):
        for k, (n, p) in enumerate(e['ends']):
            if n in hubs:
                use[(n, p)].append((i, k))
    base_pts = [[list(map(tuple, side)) for side in e['points']] for e in m.edges]
    pts = [[list(side) for side in s] for s in base_pts]
    shift = {}            # (inst, port) -> translation along its face
    for it_ in range(iters):
        for h in sorted(hubs):
            if only and h not in only:
                continue                                   # hub kept at its exported pins (partner of moved hubs only)
            inst = m.insts[h]
            W, H_, pp = m.pins[inst.master]
            # all pins of the hub, by face, as (along coordinate) for anchored occupancy
            faces = collections.defaultdict(list)          # face -> list of slices
            used_pins = set()
            for (n, p), refs in use.items():
                if n != h:
                    continue
                i, k = refs[0]
                side = base_pts[i][k]
                f = side[0][2]
                if f is None or any(s[2] != f for s in side):
                    continue                               # area pins / multi-face ports are not re-packed
                ax = along(f)
                coords = [s[ax] for s in side]
                # desired translation: bit-weighted mean of partner minus own, over all edges of this port
                num = den = 0.0
                for (ii, kk) in refs:
                    own = pts[ii][kk]; oth = pts[ii][1 - kk]
                    num += sum(o[ax] - s[ax] for s, o in zip(own, oth)); den += len(own)
                cur = shift.get((n, p), 0.0)
                faces[f].append(dict(port=p, lo=min(coords) - 0.048, hi=max(coords) + 0.048, w=float(len(side)),
                                     t=cur + num / den, base_shift=cur))
                pn = PA.default_names(h, p, len(side))
                used_pins.update(pn)
            # anchored pins: every hub pin on a face not in a used port slice
            for pname, (px, py, f, lay) in pp.items():
                if f is None or pname in used_pins:
                    continue
                X, Y, F, _ = PA.place(inst, W, H_, (px, py, f, lay))
                ax = along(F)
                faces[F].append(dict(port=None, lo=(X, Y)[ax] - 0.048, hi=(X, Y)[ax] + 0.048, w=ANCHOR_W, t=0.0,
                                     base_shift=0.0))
            for f, sl in faces.items():
                ax = along(f)
                flo = (inst.x, inst.y)[ax]; fhi = flo + (inst.w, inst.h)[ax]
                # base positions (without current shift) -> merge overlapping slices into rigid groups
                for s in sl:
                    s['lo0'], s['hi0'] = s['lo'], s['hi']          # unshifted base coordinates
                sl.sort(key=lambda s: s['lo0'])
                groups = []
                for s in sl:
                    if groups and s['lo0'] < groups[-1]['hi0'] - 1e-9:
                        g = groups[-1]; g['m'].append(s); g['hi0'] = max(g['hi0'], s['hi0'])
                    else:
                        groups.append(dict(m=[s], lo0=s['lo0'], hi0=s['hi0']))
                rows = []
                for g in groups:
                    anchored = any(s['port'] is None for s in g['m'])
                    w = sum(s['w'] for s in g['m'])
                    t = 0.0 if anchored else sum(s['w'] * s['t'] for s in g['m']) / w
                    rows.append(dict(start=g['lo0'], width=g['hi0'] - g['lo0'], desired=g['lo0'] + t,
                                     w=ANCHOR_W if anchored else w))
                if REORDER:                                # permit slice-order swaps: pack in desired order
                    order = sorted(range(len(rows)), key=lambda i: rows[i]['desired'])
                    rows = [rows[i] for i in order]; groups = [groups[i] for i in order]
                new = abacus(rows, flo, fhi)
                for g, x in zip(groups, new):
                    for s in g['m']:
                        if s['port'] is not None:
                            shift[(h, s['port'])] = x - g['lo0']
            # apply shifts of this hub to the working points
            for (n, p), refs in use.items():
                if n != h or (n, p) not in shift:
                    continue
                for (i, k) in refs:
                    side = base_pts[i][k]; ax = along(side[0][2]); d = shift[(n, p)]
                    pts[i][k] = [tuple(v + (d if j == ax else 0.0) for j, v in enumerate(s[:2])) + tuple(s[2:]) for s in side]
    # measure every hub-incident edge before/after
    per_hub = collections.defaultdict(lambda: dict(edges=0, bits=0, before=collections.Counter(), after=collections.Counter(),
                                                   fail_before=0, fail_after=0, worst_before=0.0, worst_after=0.0))
    rows = []
    for i, e in enumerate(m.edges):
        b = edge_stats(e, base_pts[i]); a = edge_stats(e, pts[i])
        for n, _ in e['ends']:
            if n in hubs:
                r = per_hub[n]; r['edges'] += 1; r['bits'] += e['bits']
                for k in ('sum_bit_um', 'over500', 'over215'):
                    r['before'][k] += b[k]; r['after'][k] += a[k]
                r['fail_before'] += b['verdict'] == 'FAIL'; r['fail_after'] += a['verdict'] == 'FAIL'
                r['worst_before'] = max(r['worst_before'], b['max_um']); r['worst_after'] = max(r['worst_after'], a['max_um'])
        rows.append(dict(bus=e['bus'], cls=e['cls'], ends=e['ends'], bits=e['bits'],
                         before={k: (round(v, 3) if isinstance(v, float) else v) for k, v in b.items() if k != 'why'},
                         after={k: (round(v, 3) if isinstance(v, float) else v) for k, v in a.items() if k != 'why'},
                         why_after=a['why']))
    tot_b = collections.Counter(); tot_a = collections.Counter()
    for r in rows:
        for k in ('sum_bit_um', 'over500', 'over215'):
            tot_b[k] += r['before'][k] * 1.0; tot_a[k] += r['after'][k] * 1.0
        tot_b['fail'] += r['before']['verdict'] == 'FAIL'; tot_a['fail'] += r['after']['verdict'] == 'FAIL'
        tot_b['max'] = max(tot_b['max'], r['before']['max_um']); tot_a['max'] = max(tot_a['max'], r['after']['max_um'])
    report['totals'] = dict(edges=len(rows), before=dict(tot_b), after=dict(tot_a))
    report['moved_hubs'] = sorted(only) if only else sorted(hubs)
    report['worsened_edges'] = [dict(bus=r['bus'], bits=r['bits'], ends=r['ends'], max_before=r['before']['max_um'],
                                     max_after=r['after']['max_um'], verdict=[r['before']['verdict'], r['after']['verdict']])
                                for r in rows if r['after']['max_um'] > r['before']['max_um'] + 1e-3
                                or r['after']['over500'] > r['before']['over500'] or r['after']['over215'] > r['before']['over215']
                                or (r['after']['verdict'] == 'FAIL' and r['before']['verdict'] != 'FAIL')]
    report['hubs'] = {h: dict(edges=r['edges'], bits=r['bits'], before=dict(r['before']), after=dict(r['after']),
                              fail_before=r['fail_before'], fail_after=r['fail_after'],
                              worst_before=round(r['worst_before'], 3), worst_after=round(r['worst_after'], 3))
                      for h, r in sorted(per_hub.items())}
    report['port_shifts_um'] = sorted([dict(inst=n, port=p, shift_um=round(d, 3)) for (n, p), d in shift.items()
                                       if abs(d) > 0.0005], key=lambda r: -abs(r['shift_um']))
    rows.sort(key=lambda r: -(r['before']['sum_bit_um'] - r['after']['sum_bit_um']))
    report['edges'] = rows
    out_path.write_text(json.dumps(report, indent=1) + '\n')
    print('FINAL', json.dumps(report['totals']))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--lef', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--iters', type=int, default=2)
    ap.add_argument('--only', default='', help='comma list of hubs whose faces are re-packed (default all)')
    ap.add_argument('--reorder', action='store_true', help='allow slice-order permutations on a face')
    a = ap.parse_args()
    REORDER = a.reorder
    run(a.plan, a.lef, a.out, a.iters, set(filter(None, a.only.split(','))) or None)
