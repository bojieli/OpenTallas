#!/usr/bin/env python3
"""DIE-HBM-42 d41d face re-window + widen (results script, no shared tool change).

COORD RULING 2026-10-30 15:33 (DIE-HBM-41 ASK default (a)): the hub<->su00/su20 D-class bits ride the EXISTING SU
corridor lanes (same lanes, same stations, same cycles), widened; the 4 SU corridor faces per quadrant are re-windowed
at a per-type face budget (KV RULING 10-25 (a) mechanism: type face_pins_per_um + face_budget_g2, set later by
face_budget.py only when the G2 probe PASSes).

  1. widen: lane widths (ports, end-type buses, crossed ft slots) += add.
  2. re-window: every port that crosses one of the named faces (a|b, both ends exactly a and b) is re-packed along the
     shared edge in its old order; each window = schema.window_for(cursor, pins, layers, per_um=PER, track_max) and
     the leftover length is spread as equal gaps (>= GUARD).  The new die window is written back to every type-frame
     declaration of that port (bus window_um or ft slot in/out_window_um, inverse of Plan.geom_to_die).
  3. bit sites: widened ft slots with explicit bit_sites_um get the new payload bits on free legal row sites nearest
     the stage centroid (RowAllocator, same as DIE-HBM-41 widen.py).
    rewin.py PLANDIR spec.json OUTDIR     spec = {"per_um": 10, "lanes": [{"lane","add"}], "faces": ["A|B", ...]}
"""
import json, os, sys, hashlib, shutil
from pathlib import Path
import numpy as np
T = os.environ.get('OT_TOOLS', '/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan')
sys.path.insert(0, T); sys.path.insert(0, str(Path(T).parents[1]))
import schema as S
import lane_add as LA
from tools.die_trial.legal_sites import RowAllocator
KEEPOFF = 1.08; CELL = (1.404, .27); GUARD = 1.0; EDGE = 2.0


def sha12(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]


def type_decl(raw, part, bus, parts):
    """(container dict, key) holding the type-frame window of `bus` on `part`'s type, or None."""
    t = raw['partition_types'][parts[part]['type']]
    for b in t.get('buses', []):
        if b['name'] == bus and 'window_um' in b and 'face' in b and 'layers' in b:
            return b, 'window_um'
    for s in t.get('ft_slots', []):
        for sfx, wk in (('_i', 'in_window_um'), ('_o', 'out_window_um')):
            if bus == s['name'] + sfx and wk in s:
                return s, wk
    return None


def to_type_win(P, part, face_axis_ew, win):
    p = P.parts[part]; w, h = P.ptype(part)['outline_um']; o = p.get('orient', 'R0')
    if face_axis_ew:
        base, ext, flip = p['origin_um'][1], h, o in ('MX', 'R180')
    else:
        base, ext, flip = p['origin_um'][0], w, o in ('MY', 'R180')
    a, b = win[0] - base, win[1] - base
    if flip:
        a, b = ext - b, ext - a
    return [round(a, 6), round(b, 6)]


def main():
    plan, spec, out = Path(sys.argv[1]), json.load(open(sys.argv[2])), Path(sys.argv[3])
    PER = float(spec['per_um'])
    raw = json.loads((plan / 'die_plan.json').read_text()); P = S.Plan(raw)
    T_ = raw['partition_types']; parts = {p['name']: p for p in raw['partitions']}
    tm = float(P.budgets.get('pin_track_max', 0.6))
    rep = dict(base=str(plan), base_sha=sha12(plan / 'die_plan.json'), per_um=PER, lanes=[], buses={}, slots={}, faces={})
    done_bus, done_slot = {}, {}
    rp = {p['id']: p for p in raw['ports']}
    newslots = {}   # (type, slot) -> stage centroids (type frame) for brand-new slots
    # 0. clone-reverse: a new lane on the corridor of an existing single-crossing lane, opposite direction, same
    #    stations (reversed), same cycles; bus/slot base name `bus` (mirror lanes share it, plan convention L120/L120m)
    for c in spec.get('clones', []):
        tl = P.lanes[c['rev_of']]; assert len(tl['ports']) == 2, c
        p0, p1 = (P.ports[q] for q in tl['ports'])
        A, X, B = p0['src']['part'], p0['dst']['part'], p1['dst']['part']   # template A -> X -> B; new B -> X -> A
        nid, base, w = c['new'], c['bus'], int(c['width'])
        sl_t = next(s for s in T_[parts[X]['type']]['ft_slots'] if s['name'] + '_i' == p0['dst']['bus'])
        tnX = parts[X]['type']; sname = base + 'x1'
        assert not any(s['name'] == sname for s in T_[tnX]['ft_slots']), sname
        ns = dict(name=sname, in_face=sl_t['out_face'], out_face=sl_t['in_face'], width=w, stations=sl_t['stations'],
                  regs_um=[list(r) for r in reversed(sl_t['regs_um'])],
                  in_window_um=[v + 0.001 for v in sl_t['out_window_um']], in_layers=list(sl_t['out_layers']),
                  in_order=sl_t.get('out_order', 'lsb_low'),
                  out_window_um=[v + 0.001 for v in sl_t['in_window_um']], out_layers=list(sl_t['in_layers']),
                  out_order=sl_t.get('in_order', 'lsb_low'), bit_site_cell_um=list(sl_t.get('bit_site_cell_um', CELL)),
                  note=f"DIE-HBM-42 d41d: reverse of {sl_t['name']} (same stations reversed, same cycles)")
        cw, ch = ns['bit_site_cell_um']
        cents = [list(np.mean([[x + cw / 2, y + ch / 2] for x, y in st], axis=0)) for st in reversed(sl_t['bit_sites_um'])]
        ns['bit_sites_um'] = [[] for _ in cents]
        T_[tnX]['ft_slots'].append(ns); newslots[(tnX, sname)] = cents
        tbA = next(b for b in T_[parts[A]['type']]['buses'] if b['name'] == p0['src']['bus'])
        tbB = next(b for b in T_[parts[B]['type']]['buses'] if b['name'] == p1['dst']['bus'])
        nbA = dict(tbA, name=base + '_i', dir='in', width=w)
        if 'window_um' in nbA: nbA['window_um'] = [v + 0.001 for v in tbA['window_um']]
        nbB = dict(tbB, name=base + '_o', dir='out', width=w)
        if 'window_um' in nbB: nbB['window_um'] = [v + 0.001 for v in tbB['window_um']]
        for tn, nb in ((parts[A]['type'], nbA), (parts[B]['type'], nbB)):
            assert not any(b['name'] == nb['name'] for b in T_[tn]['buses']), (tn, nb['name'])
            T_[tn]['buses'].append(nb)
        kind = p0.get('kind', 'data')
        raw['ports'] += [dict(id=nid + '_0', src=dict(part=B, bus=base + '_o'), dst=dict(part=X, bus=sname + '_i'), width=w, kind=kind),
                         dict(id=nid + '_1', src=dict(part=X, bus=sname + '_o'), dst=dict(part=A, bus=base + '_i'), width=w, kind=kind)]
        raw['lanes'].append(dict(id=nid, ports=[nid + '_0', nid + '_1'], note=c.get('note', f'DIE-HBM-42 d41d: {B}->{A} reverse of {c["rev_of"]}')))
        raw['latency']['lanes'][nid] = dict(raw['latency']['lanes'][c['rev_of']], param='LAT_' + nid)
        rep.setdefault('clones', []).append(dict(c, path=[B, X, A], slot=f'{tnX}/{sname}', cycles=raw['latency']['lanes'][nid]['cycles']))
    P = S.Plan(raw); rp = {p['id']: p for p in raw['ports']}
    # 1. widen
    for a in spec['lanes']:
        lid, add = a['lane'], int(a['add'])
        ports = [P.ports[q] for q in P.lanes[lid]['ports']]
        w0 = ports[0]['width']; w1 = w0 + add
        assert all(x['width'] == w0 and not x.get('segments') for x in ports), lid
        for x in ports:
            rp[x['id']]['width'] = w1
        ends = [(ports[0]['src']['part'], ports[0]['src']['bus']), (ports[-1]['dst']['part'], ports[-1]['dst']['bus'])]
        for part, bus in ends:
            tn = parts[part]['type']; key = (tn, bus)
            b = next(b for b in T_[tn]['buses'] if b['name'] == bus)
            if key in done_bus:
                assert done_bus[key] == (w0, w1), key; continue
            assert b['width'] == w0, (key, b['width'], w0)
            b['width'] = w1; done_bus[key] = (w0, w1); rep['buses'][f'{tn}/{bus}'] = [w0, w1]
        for part, slot, _, _ in P.lane_crossings(lid):
            if not slot: continue
            tn = parts[part]['type']; key = (tn, slot)
            if key in done_slot:
                assert done_slot[key] == (w0, w1), key; continue
            s = next(s for s in T_[tn]['ft_slots'] if s['name'] == slot)
            assert s['width'] == w0, (key, s['width'], w0)
            s['width'] = w1; done_slot[key] = (w0, w1)
            rep['slots'][f'{tn}/{slot}'] = dict(width=[w0, w1], bit_sites=bool(s.get('bit_sites_um')))
        rep['lanes'].append(dict(lane=lid, width=[w0, w1], cycles=raw['latency']['lanes'].get(lid, {}).get('cycles')))
    # 2. re-window (geometry from the widened raw)
    P = S.Plan(raw)
    widened = {q for l in [a['lane'] for a in spec['lanes']] + [c['new'] for c in spec.get('clones', [])] for q in P.lanes[l]['ports']}
    written = {}
    for fe in spec['faces']:
        a, b = fe.split('|')
        df, lo, hi = LA.shared_edge(P, a, b)
        ew = df in 'EW'
        ps = []
        for pid, pr in P.ports.items():
            ends = {pr['src']['part'], pr['dst']['part']}
            if ends != {a, b}:
                continue
            assert not pr.get('segments'), pid
            ps.append(pr)
        old = {x['id']: [round(v, 3) for v in x['window_um']] for x in ps}
        key = {x['id']: sum(x['window_um']) / 2 for x in ps}
        hint = [h for h in spec.get('order_hint', {}).get(fe, []) if h in key]   # ascending coordinate order
        for k_, h in zip(sorted(key[h] for h in hint), hint):
            key[h] = k_
        ps.sort(key=lambda x: key[x['id']])
        assert all(lo - 1e-6 <= min(w) and max(w) <= hi + 1e-6 for w in old.values()), (fe, old, lo, hi)
        changed = {x['id'] for x in ps if x['id'] in widened}
        perlen = {x['id']: S.window_for(lo, S.port_pins_count(x), x['layers'], P.layers, per_um=PER, track_max=tm) - lo for x in ps}
        oldlen = {x['id']: old[x['id']][1] - old[x['id']][0] for x in ps}
        free = hi - lo - 2 * EDGE - GUARD * (len(ps) - 1)
        compress = sum(perlen[k] if k in changed else oldlen[k] for k in perlen) > free
        Ls = [perlen[x['id']] if (x['id'] in changed or compress) else oldlen[x['id']] for x in ps]
        need = sum(Ls)
        # minimal displacement (L2 isotonic regression with bounds), order kept, gap GUARD
        C, acc = [], 0.0
        for L_ in Ls: C.append(acc); acc += L_ + GUARD
        tgt = [key[x['id']] - Ls[i] / 2 - C[i] for i, x in enumerate(ps)]
        wt = [1.0 / (L_ + 1.0) for L_ in Ls]          # small (control) windows stay, wide data windows absorb the moves
        blocks = []
        for v, w_ in zip(tgt, wt):
            blocks.append([v, w_, 1])
            while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
                v2, w2, n2 = blocks.pop(); v1, w1, n1 = blocks.pop()
                blocks.append([(v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2, n1 + n2])
        t = [bv for bv, _, n in blocks for _ in range(n)]
        tlo, thi = lo + EDGE, hi - EDGE - (C[-1] + Ls[-1])
        t = [min(max(v, tlo), thi) for v in t]
        starts = [round(t[i] + C[i], 3) for i in range(len(ps))]
        def wlen(x, s0):
            if x['id'] in changed or compress:
                return S.window_for(round(s0, 3), S.port_pins_count(x), x['layers'], P.layers, per_um=PER, track_max=tm) - round(s0, 3)
            return oldlen[x['id']]
        for _ in range(4):
            wins, cur = {}, lo + EDGE
            for i, x in enumerate(ps):                    # forward: no overlap
                s0 = max(starts[i], cur); e = round(s0 + wlen(x, s0), 4)
                wins[x['id']] = [round(s0, 3), e]; cur = e + GUARD
            if cur - GUARD <= hi - EDGE + 1e-6:
                break
            nxt = hi - EDGE                               # backward: inside the edge
            for i in range(len(ps) - 1, -1, -1):
                x = ps[i]; s0, e = wins[x['id']]
                if e > nxt:
                    L_ = e - s0; e = nxt; s0 = e - L_ - 0.05
                starts[i] = round(s0, 3); nxt = s0 - GUARD
        ok = cur - GUARD <= hi - EDGE + 1e-6
        gap = GUARD
        pins = sum(S.port_pins_count(x) for x in ps)
        rep['faces'][fe] = dict(face=df, edge=[round(lo, 3), round(hi, 3)], ports=len(ps), pins=pins,
                                pins_per_um_edge=round(pins / (hi - lo), 2), need_um=round(need, 1), gap_um=round(gap, 2),
                                fits=ok, compress=compress, end=round(cur - gap, 3), max_move_um=round(max(abs(sum(wins[k])/2-sum(old[k])/2) for k in wins if k not in changed),1),
                                moved={k: [old[k], wins[k]] for k in wins})
        if not ok:
            print('FACE DOES NOT FIT', fe, rep['faces'][fe]['need_um'], hi - lo); continue
        for x in ps:
            for side in ('src', 'dst'):
                part, bus = x[side]['part'], x[side]['bus']
                d = type_decl(raw, part, bus, parts)
                if d is None: continue
                cont, k = d
                tw = to_type_win(P, part, ew, wins[x['id']])
                key = (parts[part]['type'], bus, k)
                if key in written:
                    assert written[key] == tw, (key, written[key], tw); continue
                cont[k] = tw; written[key] = tw
    # 2b. clones with `respace`: stations evenly along in-window centre -> (x|y strip) -> out-window centre
    P = S.Plan(raw)
    for c in spec.get('clones', []):
        rs = c.get('respace')
        if not rs: continue
        lid = c['new']; p0, p1 = (P.ports[q] for q in P.lanes[lid]['ports'])
        X = p0['dst']['part']; tnX = parts[X]['type']
        s = next(s for s in T_[tnX]['ft_slots'] if s['name'] == c['bus'] + 'x1')
        a = P.to_type(X, P.port_point(p0['id'])); b = P.to_type(X, P.port_point(p1['id']))
        pts = [a] + [tuple(v) for v in rs['via']] + [b]
        segl = [abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
        tot = sum(segl); k = int(s['stations']); regs = []
        for j in range(1, k + 1):
            d = tot * j / (k + 1); i = 0
            while d > segl[i] and i < len(segl) - 1: d -= segl[i]; i += 1
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]; f = d / segl[i] if segl[i] else 0
            # Manhattan segment: move x first then y
            dx, dy = x1 - x0, y1 - y0; L1 = abs(dx) + abs(dy)
            m = f * L1
            if m <= abs(dx): q = (x0 + (m if dx >= 0 else -m), y0)
            else: q = (x1, y0 + ((m - abs(dx)) if dy >= 0 else -(m - abs(dx))))
            regs.append([round(q[0], 4), round(q[1], 4)])
        s['regs_um'] = regs
        newslots[(tnX, s['name'])] = [[x_ + 0.702, y_ + 0.135] for x_, y_ in regs[-len(newslots[(tnX, s['name'])]):]] \
            if len(regs) >= len(newslots[(tnX, s['name'])]) else newslots[(tnX, s['name'])]
        rep.setdefault('respaced', {})[f'{tnX}/{s["name"]}'] = dict(in_pt=a, out_pt=b, hop_um=round(tot / (k + 1), 1), regs=regs)
    # 3. bit sites for widened slots
    by_type = {}
    for k, v in rep['slots'].items():
        if v['bit_sites']:
            tn, sl = k.split('/', 1); by_type.setdefault(tn, []).append(sl)
    for tn, sl in newslots:
        by_type.setdefault(tn, [])
    for tn, sls in by_type.items():
        t = T_[tn]; w, h = t['outline_um']
        boxes = list(S.placed_macro_boxes(t, halo=KEEPOFF).values())
        al = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=CELL, column_pitch=2.16,
                          row_pitch=.27, origin=(4.32, 4.32))
        for s in t['ft_slots']:
            cw, ch = s.get('bit_site_cell_um', CELL)
            for st in s.get('bit_sites_um') or []:
                for x, y in st: al.reserve_rectangle((x, y, x + cw, y + ch))
            if not s.get('bit_sites_um'):
                for x, y in s.get('regs_um') or []: al.reserve_rectangle((x - 2, y - 2, x + 2, y + 2))
        for s_ in t.get('internal_stations', []) or []:
            for x, y in s_.get('regs_um', []) or []: al.reserve_rectangle((x - 2, y - 2, x + 2, y + 2))
        for bb in (t.get('clock') or {}).get('branch_buffers') or []:
            xy = bb.get('xy_um') or bb.get('at_um') or bb.get('xy')
            if xy: al.reserve_rectangle((xy[0] - 2.5, xy[1] - 2.5, xy[0] + 2.5, xy[1] + 2.5))
        for (tn2, sl), cents in newslots.items():
            if tn2 != tn: continue
            s = next(s for s in t['ft_slots'] if s['name'] == sl)
            cw, ch = s['bit_site_cell_um']; n_new = s['width'] + 1; dmax = 0.0
            for j, c in enumerate(cents):
                pts, info = al.allocate(np.array(c), n_new, max_radius_um=float(spec.get('site_radius_um', 140.)))
                assert len(pts) == n_new, (tn, sl, j, len(pts))
                s['bit_sites_um'][j] = [[round(float(p[0] - cw / 2), 6), round(float(p[1] - ch / 2), 6)] for p in pts]
                for x, y in s['bit_sites_um'][j]: al.reserve_rectangle((x, y, x + cw, y + ch))
                dmax = max(dmax, float(np.max(np.abs(pts - np.array(c)).sum(axis=1))))
            rep['slots'][f'{tn}/{sl}'] = dict(width=[0, s['width']], new=True, sites_per_stage=n_new, max_new_site_from_centroid_um=round(dmax, 2))
        for sl in sls:
            s = next(s for s in t['ft_slots'] if s['name'] == sl)
            cw, ch = s.get('bit_site_cell_um', CELL)
            n_new = s['width'] + 1 - len(s['bit_sites_um'][0]); dmax = 0.0
            for j, st in enumerate(s['bit_sites_um']):
                c = np.mean([[x + cw / 2, y + ch / 2] for x, y in st], axis=0)
                pts, info = al.allocate(c, n_new, max_radius_um=float(spec.get("site_radius_um", 140.)))
                assert len(pts) == n_new, (tn, sl, j, len(pts))
                new = [[round(float(p[0] - cw / 2), 6), round(float(p[1] - ch / 2), 6)] for p in pts]
                for x, y in new: al.reserve_rectangle((x, y, x + cw, y + ch))
                dmax = max(dmax, float(np.max(np.abs(pts - c).sum(axis=1))))
                s['bit_sites_um'][j] = st[:-1] + new + [st[-1]]
            rep['slots'][f'{tn}/{sl}']['new_sites_per_stage'] = n_new
            rep['slots'][f'{tn}/{sl}']['max_new_site_from_centroid_um'] = round(dmax, 2)
    raw['die']['label'] = spec.get('label', 'DIE-HBM-42 d41d') + ' | ' + raw['die'].get('label', '')
    out.mkdir(parents=True, exist_ok=False)
    for f in plan.iterdir():
        if f.name in ('die_plan.json',) or f.name.endswith('_report.json'): continue
        shutil.copy2(f, out / f.name) if f.is_file() else os.symlink(f.resolve(), out / f.name)
    (out / 'die_plan.json').write_text(json.dumps(raw, indent=1))
    rep['out_sha'] = sha12(out / 'die_plan.json')
    (out / 'd41d_rewin_report.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps(dict(lanes=rep['lanes'], out_sha=rep['out_sha']), indent=1))
    for k, v in rep['faces'].items(): print('FACE', k, {kk: vv for kk, vv in v.items() if kk != 'moved'})
    for k, v in rep['slots'].items(): print('SLOT', k, v)


if __name__ == '__main__':
    main()
