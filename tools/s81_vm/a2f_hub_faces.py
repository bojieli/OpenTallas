#!/usr/bin/env python3
"""S81 VM A2-F split4: VM relay reach + internal cut screen with the VM ports pinned to the face SPANS where their
hub peers actually sit (S-VM 2210, for S81-AGGRO hub scoring and the wide-hub fit).

a2f_split4_route_plan.py / a2f_reach_price.py place every VM port group on its face at the median of its consumer
pins (free position along the face).  In a real hub each peer sits on one stretch of one face, so the port group is
clipped to that stretch here: spans {port prefix: (face, lo_um, hi_um)} in VM-local coordinates.
Layouts ('--hub'):
  split4   S-DIE planning faces of the split4 grant (W SU, E capture+CDC, N MIX4, S rest; free spans)  [reference]
  vmc      S81-AGGRO 'VM-centred column' (results/arch/s81_aggro_1015/hub_vm_centred.json key vmc): SU under the VM
           (S, x 0..1890), MIX4 N-W, capture + gather N-E, PQ/sseq W bottom, collective/host/WFC E, HC E above WFC
Internal arrangement ('--arr'):
  midcapd  the split4 placement unchanged (capture lanes in two E columns around the band)
  capne    the same, with the 16 capture lanes moved to the TOP of their E columns (under the N-E capture peer)
Outputs relay edges per hop (a2f_reach_price.measure at R = 900 / 1,118 um) and the PathFinder cut screen.
"""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a2_route_plan as R  # noqa: E402
import a2f_route_plan as F  # noqa: E402
import a2f_split4_route_plan as S4  # noqa: E402
import a2f_reach_price as RP  # noqa: E402

ROOT = HERE.parents[1]
CH_HALF = 10.8
CH = 21.6
CAPROW_PER = 8
SU_X0 = 0.0   # SU W edge along the VM S face (-1 = centred)


def spans_for(hub, W, H):
    if hub == 'split4':
        return None
    if hub == 'vmc':
        # vmc rects (S81-AGGRO 2210): vm [13003.7, 16765.6, 4104, 4644]; su x 13003.7..14893.7 below; mix4 x 12129..15358
        # above; capture/gather x 15379.8..17107.8 above; pq y 16897..17346 / sseq y 16787..16876 W; collective
        # y 16765.6..19487 E (x 17194), wfc y 19530..19858 E, hc_s E beyond the collective column (above the WFC).
        cap0 = W - 1728.0          # capture/gather column aligned to the VM E edge (vmc: 15379.8 - 13003.7)
        su0 = SU_X0 if SU_X0 >= 0 else (W - 1890.0) / 2
        return {
            'f_su': ('S', su0, su0 + 1890.0), 't_su': ('S', su0, su0 + 1890.0), 't_inp_su': ('S', su0, su0 + 1890.0),
            'f_mx': ('N', 0.0, cap0 - 21.6), 't_mx': ('N', 0.0, cap0 - 21.6),
            'f_capture': ('N', cap0, W), 't_gather': ('N', cap0, W), 'col': ('N', cap0, W),
            'f_pqx': ('W', 131.7, 580.9), 't_pqx': ('W', 131.7, 580.9),
            'c_': ('W', 21.6, 110.3),
            't_crs': ('E', 0.0, 2721.6),
            'f_wfc': ('E', 2764.7, 3092.9), 't_wfc': ('E', 2764.7, 3092.9),
            'f_hc': ('E', 3114.5, H), 't_hc': ('E', 3114.5, H), 't_inp_hc': ('E', 3114.5, H),
            'aSW': ('S', su0 + 1911.6 if su0 + 1911.6 < W - 200 else 0.0, W if su0 + 1911.6 < W - 200 else su0),
            'qSW': ('S', su0 + 1911.6 if su0 + 1911.6 < W - 200 else 0.0, W if su0 + 1911.6 < W - 200 else su0),
            'sel': ('S', su0 + 1911.6 if su0 + 1911.6 < W - 200 else 0.0, W if su0 + 1911.6 < W - 200 else su0),
        }
    if hub == 'vmc2':
        # S-DIE 2210 grant (VM-centred cross, E edge fixed x 17,107.7, top fixed y 21,193.6, W grows west):
        # N capture t_vm re-centred on the VM + PQ/gather on the N-face E part; S SU (x 13,003.7..14,893.7 absolute);
        # E collective (bottom 2,721.6), WFC above it, hc_s above y ~19,650 (top-anchored: H - 1,543.6); W MIX4 (3,229
        # tall, centred) + sseq c_* (bottom).
        c0 = (W - 1728.0) / 2
        su0 = W - 4104.0
        hc0 = H - (21193.6 - 19650.0)
        m0 = (H - 3229.2) / 2
        rest = (su0 + 1911.6, W)
        return {
            'f_su': ('S', su0, su0 + 1890.0), 't_su': ('S', su0, su0 + 1890.0), 't_inp_su': ('S', su0, su0 + 1890.0),
            'f_capture': ('N', c0, c0 + 1728.0),
            't_gather': ('N', c0 + 1749.6, W), 'col': ('N', c0 + 1749.6, W),
            'f_pqx': ('N', c0 + 1749.6, W), 't_pqx': ('N', c0 + 1749.6, W),
            'f_mx': ('W', m0, m0 + 3229.2), 't_mx': ('W', m0, m0 + 3229.2),
            'c_': ('W', 21.6, 110.3),
            't_crs': ('E', 0.0, 2721.6),
            'f_wfc': ('E', 2764.7, 3092.9), 't_wfc': ('E', 2764.7, 3092.9),
            'f_hc': ('E', hc0, H), 't_hc': ('E', hc0, H), 't_inp_hc': ('E', hc0, H),
            'aSW': ('S',) + rest, 'qSW': ('S',) + rest, 'sel': ('S',) + rest,
        }
    raise SystemExit('unknown hub ' + hub)


def install_spans(spans):
    """replace R.port_face / R.connections port placement by the span-clipped version (same Prim tree otherwise)."""
    if spans is None:
        return
    keys = sorted(spans, key=len, reverse=True)

    def look(p):
        for k in keys:
            if p.startswith(k):
                return spans[k]
        raise KeyError('VM port without a hub span: ' + p)
    R.port_face = lambda p: look(p)[0]
    base = R.connections

    def connections(P, nets, W, H, models=None, port_density=8.0):
        L = P.leaves
        models = models or R.pin_models(L)
        raw, groups = [], collections.defaultdict(list)
        for eps in nets:
            pts, tags = [], []
            for e in eps:
                if e[0] >= 0:
                    i, p, b = e
                    x, y, fx, fy = P.pos[i]
                    pts.append(R.pin_xy(L[i], models[L[i]['master']], p, b, x, y, fx, fy))
                    tags.append(L[i]['master'])
            if not pts:
                continue
            ports = [e for e in eps if e[0] < 0]
            for e in ports:
                groups[e[1]].append((len(raw), pts[0]))
            raw.append((pts, tags, [e[1] for e in ports]))
        place, face_bits = {}, collections.Counter()
        for pname, lst in groups.items():
            f, lo, hi = look(pname)
            face_bits[f] += len(lst)
            proj = sorted((p[1] if f in 'WE' else p[0]) for _, p in lst)
            c = proj[len(proj) // 2]
            span = min(max(len(lst) / port_density, proj[-1] - proj[0] if len(proj) > 1 else 0.0), hi - lo)
            a = min(max(c - span / 2, lo), hi - span)
            order = sorted(range(len(lst)), key=lambda k: (lst[k][1][1] if f in 'WE' else lst[k][1][0]))
            for r, k in enumerate(order):
                t = a + span * (r + 0.5) / len(lst)
                place[(lst[k][0], pname)] = {'W': (0.0, t), 'E': (W, t), 'N': (t, H), 'S': (t, 0.0)}[f]
        out = []
        for n, (pts, tags, ports) in enumerate(raw):
            pts, tags = list(pts), list(tags)
            for pname in ports:
                pts.append(place[(n, pname)])
                tags.append('PORT_' + look(pname)[0] + ':' + pname)
            done, todo = [0], list(range(1, len(pts)))
            while todo:
                best = None
                for k in todo:
                    for d in done:
                        dd = abs(pts[k][0] - pts[d][0]) + abs(pts[k][1] - pts[d][1])
                        if best is None or dd < best[0]:
                            best = (dd, k, d)
                _, k, d = best
                todo.remove(k)
                done.append(k)
                out.append((pts[d], pts[k], tags[d], tags[k]))
        return out, face_bits
    R.connections = connections
    R._base_connections = base


def _install_read_near():
    """F.build_mid with opts['read_near']: each slice's read strip (read_q/read_v/return/FSR leaves) sits right after
    its payload, i.e. against the central band, instead of at the far (outer-face) end of the slice block.  Every port
    word gathers from all four slices, so a central read strip bounds every client's port -> read reach by about half
    the VM perimeter instead of a full crossing."""
    import inspect
    src = inspect.getsource(F.build_mid)
    a = """        off = PH + ch
        for row in rows:"""
    b = """        off = PH + ch
        near = lambda i: read_like(i) and not (opts.get('return_far') and 'return' in M[i])
        if opts.get('read_near'):
            items = [i for i in range(len(N)) if slice_of.get(i) == x and near(i)]
            grp = [(i,) for i in sorted(items, key=lambda i: read_key(opts, M[i], leaves[i]['h'], N[i]))]
            if mirror:
                far0 = R.skyline(P, grp, cx, cx + CW, base - off, ch, flip=True)
            else:
                far0 = R.skyline(P, grp, cx, cx + CW, base + off, ch)
            off = abs(far0 - base) + ch
        for row in rows:"""
    assert src.count(a) == 1
    src = src.replace(a, b)
    a2 = """        items = [i for i in range(len(N)) if slice_of.get(i) == x and read_like(i)]
        grp = [(i,) for i in sorted(items, key=lambda i: read_key(opts, M[i], leaves[i]['h'], N[i]))]
        if mirror:
            far = R.skyline(P, grp, cx, cx + CW, base - off, ch, flip=True)
        else:
            far = R.skyline(P, grp, cx, cx + CW, base + off, ch)"""
    b2 = """        if opts.get('read_near') and not opts.get('return_far'):
            far = base - (off - ch) if mirror else base + (off - ch)
        else:
          items = [i for i in range(len(N)) if slice_of.get(i) == x and read_like(i) and not (opts.get('read_near') and near(i))]
          grp = [(i,) for i in sorted(items, key=lambda i: read_key(opts, M[i], leaves[i]['h'], N[i]))]
          if mirror:
            far = R.skyline(P, grp, cx, cx + CW, base - off, ch, flip=True)
          else:
            far = R.skyline(P, grp, cx, cx + CW, base + off, ch)"""
    assert src.count(a2) == 1, 'read strip block'
    src = src.replace(a2, b2)
    ns = dict(F.__dict__)
    exec(compile(src, F.__file__, 'exec'), ns)
    F.build_mid = ns['build_mid']


# the capture write enters at the capture port and runs port -> cap_leaf -> x34_s -> x34_t -> payload; a2f_reach_price
# counts only the x34_t -> payload leg (its PATHS 'ingress'), which is exact only when the capture port sits beside the
# capture lanes (the split4 E-face grant).  With the capture peer elsewhere the port -> cap_leaf leg is a real
# sequential hop: count it.
RP.PATHS['write'].insert(0, ('capture_port_cap', {('port', 'cap')}))


def build_split4(body_w=3369.6, rows=None, read_near=False, return_far=False):
    """exactly a2f_split4_route_plan.main's placement (midcapd + field4 expansion)."""
    F.install_pin_models()
    baseface = R.port_face
    cdc = ('aSW', 't_wfc', 'f_wfc', 'sel', 'col', 'qSW', 't_gather')
    R.port_face = lambda p: 'E' if p.startswith(cdc) else baseface(p)
    leaves, nets = R.load()
    ol = dict(F.OUTLINES)
    ol.update(s81_a2f_field16=(194.4, 280.8), s81_a2f_meta26=(259.2, 162.0), s81_a2f_control4=(194.4, 129.6))
    leaves, nets = F.transform(leaves, nets, ol)
    import copy
    vo = copy.deepcopy(F.VARIANTS['midcapd'])
    vo['read_near'] = read_near
    vo['return_far'] = return_far
    if read_near:
        _install_read_near()
    vo['rows'] = rows or [['f0', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6'], ['ctl', 'fj', 'meta', 'f7']]
    P, W, H, struct = F.build_mid(leaves, nets, body_w, vo)
    P, nets = S4.expand(P, nets)
    oldpm = R.pin_models

    def pm(lv):
        models = oldpm([l for l in lv if l['master'] not in (S4.FIELD, S4.CTL)])
        models[S4.FIELD] = {}
        models[S4.CTL] = {}
        return models
    R.pin_models = pm
    return P, nets, W, H, struct, baseface


RELAY_PAIRS = ('rv', 'wv', 'ra', 'wa', 'rt', 'wt', 'wm', 'wd', 'sv', 'cv', 'sd', 'st', 'ct', 'ca', 'cm')


def hop1(P, nets):
    """A2-F hop 1: the eight b4 quarter relays (dsfd_vm_static_relay128_b4, one register per direction) are removed;
    each b8 bridge drives its eight bank128 directly (RTL: o_X of b8 -> bank, bank -> i_X of b8, -1 edge each way).
    Nets through a b4 (i_X bit b == o_X bit b) are merged and the b4 endpoints dropped.  Every storage unit is
    re-packed inside its own box: [bank column B (mirrored, inputs E) | scatter + b8 column | bank column A], b8 kept
    at its row, so b8 -> farthest bank stays well inside one cycle's reach."""
    L = P.leaves
    M = [l['master'] for l in L]
    b4 = {i for i in P.pos if M[i] == 'dsfd_vm_static_relay128_b4'}
    # nets: union through b4 (i_X[b] <-> o_X[b])
    parent = list(range(len(nets)))

    def f(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    where = {}
    for n, eps in enumerate(nets):
        for e in eps:
            if e[0] in b4:
                i, p, b = e
                key = (i, p[2:], b)
                if key in where:
                    parent[f(n)] = f(where[key])
                else:
                    where[key] = n
    groups = collections.defaultdict(list)
    for n in range(len(nets)):
        groups[f(n)].append(n)
    new = []
    for g in groups.values():
        eps = [e for n in g for e in nets[n] if e[0] not in b4]
        seen, out = set(), []
        for e in eps:
            if e not in seen:
                seen.add(e)
                out.append(e)
        if len(out) > 1:
            new.append(out)
    # re-pack each unit: members by adjacency of the (old) graph
    for i in b4:
        del P.pos[i]
    b8s = [i for i in P.pos if M[i] == 'dsfd_vm_static_relay128_b8']
    adj = collections.defaultdict(set)
    for eps in new:
        ls = {e[0] for e in eps if e[0] >= 0}
        if len(ls) <= 4:
            for a in ls:
                adj[a] |= ls
    for j in b8s:
        banks = sorted([i for i in adj[j] if M[i] == 'dsfd_vm_static_bank128'], key=lambda i: L[i]['name'])
        scs = [i for i in adj[j] if M[i] == 'dsfd_vm_static_scatter_b8_out']
        assert len(banks) == 8, (L[j]['name'], len(banks))
        mem = banks + scs + [j]
        x0 = min(P.pos[i][0] for i in mem)
        bw = L[banks[0]]['w']
        colw = max(L[i]['w'] for i in scs + [j])
        xs = x0 + bw + CH
        xa = xs + colw + CH
        bx, by, bfx, bfy = P.pos[j]
        P.pos[j] = (round(xs, 4), by, bfx, bfy)
        for i in scs:
            _, y, fx, fy = P.pos[i]
            P.pos[i] = (round(xs, 4), y, fx, fy)
        ys = sorted({P.pos[i][1] for i in banks})
        rows = collections.defaultdict(list)
        for i in banks:
            rows[P.pos[i][1]].append(i)
        for y, ids in rows.items():
            ids = sorted(ids, key=lambda i: P.pos[i][0])
            for k, i in enumerate(ids):
                _, _, fx, fy = P.pos[i]
                P.pos[i] = ((round(x0, 4), y, True, fy) if k == 0 else (round(xa, 4), y, False, fy))
    return new


def arrange(P, W, H, struct, arr):
    """returns the (possibly new) outline"""
    if arr == 'caprow':
        # the capture lanes leave the two E columns and form a capture ROW across the top of the body (directly
        # under a centred N capture peer): lane groups (cap_leaf | x34_s | x34_t, kept as built) in rows of PER,
        # centred on the body width; the outline loses the 734.4-um columns and gains the row height
        capw = struct['capture_columns_um'][0]
        body = W - capw
        cap = [i for i, (x, y, fx, fy) in P.pos.items() if x >= body - 1e-6]
        rows = collections.defaultdict(list)
        for i in cap:
            x, y, fx, fy = P.pos[i]
            col = 0 if x >= W - (capw / 2) - 1e-6 else 1
            rows[(col, round(y, 1))].append(i)
        groups = sorted(rows.values(), key=lambda g: (P.pos[g[0]][1], -P.pos[g[0]][0]))
        per = CAPROW_PER
        gw = max(max(P.pos[i][0] + P.leaves[i]['w'] for i in g) - min(P.pos[i][0] for i in g) for g in groups)
        gh = max(max(P.pos[i][1] + P.leaves[i]['h'] for i in g) - min(P.pos[i][1] for i in g) for g in groups)
        nrow = -(-len(groups) // per)
        roww = per * gw + (per - 1) * CH
        assert roww <= body + 1e-6, ('capture row wider than the body', roww, body)
        x0 = (body - roww) / 2
        for n, g in enumerate(groups):
            r, c = n // per, n % per
            gx0 = min(P.pos[i][0] for i in g)
            gy0 = min(P.pos[i][1] for i in g)
            for i in g:
                x, y, fx, fy = P.pos[i]
                P.pos[i] = (round(x0 + c * (gw + CH) + (x - gx0), 4), round(H + CH + r * (gh + CH) + (y - gy0), 4), fx, fy)
        Hn = H + CH + nrow * (gh + CH) - CH
        # the capture controller (cap_ctl, fed by f_capture valid/control bits) joins the row at its E end
        for i, l in enumerate(P.leaves):
            if l['master'] == 'dsfd_vm_static_cap_ctl' and i in P.pos:
                _, _, fx, fy = P.pos[i]
                P.pos[i] = (round(x0 + roww + CH, 4), round(H + CH, 4), fx, fy)
        return body, Hn
    if arr == 'midcapd':
        return W, H
    if arr == 'capne':
        capw = struct['capture_columns_um'][0]
        ids = [i for i, (x, y, fx, fy) in P.pos.items() if x >= W - capw - 1e-6]
        top = max(P.pos[i][1] + P.leaves[i]['h'] for i in ids)
        dy = H - top
        for i in ids:
            x, y, fx, fy = P.pos[i]
            P.pos[i] = (x, round(y + dy, 4), fx, fy)
        return W, H
    if arr in ('capmid', 'capmidtop'):
        # the two capture columns between the two slice columns (centred under a centred N capture peer); every
        # leaf right of the body centre moves right by the capture width
        capw = struct['capture_columns_um'][0]
        body = W - capw
        split = body / 2
        cap = [i for i, (x, y, fx, fy) in P.pos.items() if x >= body - 1e-6]
        cx0 = min(P.pos[i][0] for i in cap)
        for i, (x, y, fx, fy) in list(P.pos.items()):
            if i in cap:
                continue
            if x + P.leaves[i]['w'] / 2 > split:
                P.pos[i] = (round(x + capw, 4), y, fx, fy)
        dx = (split + CH_HALF) - cx0
        dy = 0.0
        if arr == 'capmidtop':
            dy = H - max(P.pos[i][1] + P.leaves[i]['h'] for i in cap)
        for i in cap:
            x, y, fx, fy = P.pos[i]
            P.pos[i] = (round(x + dx, 4), round(y + dy, 4), fx, fy)
        return W, H
    raise SystemExit('unknown arrangement ' + arr)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--hub', default='vmc')
    ap.add_argument('--arr', default='midcapd')
    ap.add_argument('--reach', type=float, nargs='+', default=[900.0, 1118.0])
    ap.add_argument('--route', action='store_true', help='also run the PathFinder cut screen (slow)')
    ap.add_argument('--passes', type=int, default=10)
    ap.add_argument('--out', required=True)
    ap.add_argument('--width', type=float, default=4104.0, help='total VM width (body = width - capture columns)')
    ap.add_argument('--caprow-per', type=int, default=8)
    ap.add_argument('--hop1', action='store_true', help='remove the b4 relay level (b8 drives the banks)')
    ap.add_argument('--read-near', action='store_true')
    ap.add_argument('--return-far', action='store_true', help='with --read-near: return lanes stay at the outer end (beside the storage)')
    ap.add_argument('--su-x0', type=float, default=0.0, help='SU W edge along the VM S face; -1 centred')
    ap.add_argument('--rows', default=None, help="front rows, e.g. 'f0,f1,f2,f3,f4,f5,f6,f7/ctl,fj,meta'")
    a = ap.parse_args()
    global SU_X0, CAPROW_PER
    CAPROW_PER = a.caprow_per
    SU_X0 = a.su_x0
    rows = [r.split(',') for r in a.rows.split('/')] if a.rows else None
    P, nets, W, H, struct, baseface = build_split4(a.width - 734.4, rows, a.read_near, a.return_far)
    print('outline', W, H, struct, flush=True)
    W, H = arrange(P, W, H, struct, a.arr)
    if a.hop1:
        nets = hop1(P, nets)
        for path in ('write', 'read'):
            RP.PATHS[path] = [h for h in RP.PATHS[path] if h[0] not in ('b8_b4', 'b4_bank')]
        RP.PATHS['write'].append(('b8_bank', {('b8', 'bank')}))
        RP.PATHS['read'].insert(RP.PATHS['read'].index(next(h for h in RP.PATHS['read'] if h[0] == 'b8_return')),
                                ('b8_bank', {('b8', 'bank')}))
    print('arranged', W, H, flush=True)
    sp = spans_for(a.hub, W, H)
    if sp is None:          # split4 reference: the grant's face map, free spans
        cdc = ('aSW', 't_wfc', 'f_wfc', 'sel', 'col', 'qSW', 't_gather')
        R.port_face = lambda p: 'E' if p.startswith(cdc) else baseface(p)
    install_spans(sp)
    bad, outside = P.check(W, H)
    res = dict(schema='opentallas.s81.vm-a2f-hub-faces.v1', status='SCREEN_NOT_GRT', hub=a.hub, arrangement=a.arr,
               rectangle_um=[W, H], area_mm2=round(W * H / 1e6, 4), legality=dict(spacing=bad, outside=outside),
               spans=sp, by_reach={})
    for rr in a.reach:
        m = RP.measure(P, nets, W, H, rr)
        m['price'] = RP.price(m['write']['added_edges'], m['read']['added_edges'])
        res['by_reach'][str(rr)] = m
        print(a.hub, a.arr, rr, {k: (v['added_edges'], [(h['hop'], h['max_um'], h['relay_stages']) for h in v['hops']])
                                 for k, v in m.items() if k != 'price'}, flush=True)
        print('   price AR %.3f %% MTP %.3f %%' % (m['price']['ar']['upper_every_node']['e2e_loss_pct'],
                                                    m['price']['mtp']['upper_every_node']['e2e_loss_pct']), flush=True)
    conns, _ = R.connections(P, nets, W, H)
    per = collections.defaultdict(float)
    for (pa, pb, ta, tb) in conns:
        for t, o in ((ta, tb), (tb, ta)):
            if t.startswith('PORT_') and ':' in t:
                k = (t.split(':')[1], RP.cls(o))
                per[k] = max(per[k], abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]))
    res['port_reach_um'] = {'%s->%s' % k: round(v, 1) for k, v in sorted(per.items(), key=lambda kv: -kv[1])}
    print('port reach', list(res['port_reach_um'].items())[:14], flush=True)
    if a.route:
        pg = R.pg_plan(P, W, H)
        ev = R.routed_report(P, nets, W, H, 100.0, pg=pg, passes=a.passes)
        res['cuts'] = ev
        print(json.dumps({k: v for k, v in ev.items() if k not in ('hot', 'over_reach_pairs')}), flush=True)
    res['source_tools'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in [Path(__file__), HERE / 'a2f_split4_route_plan.py', HERE / 'a2f_route_plan.py',
                                     HERE / 'a2_route_plan.py', HERE / 'a2f_reach_price.py']}
    res['placement'] = {P.leaves[i]['name']: [P.leaves[i]['master']] + list(P.rect(i)) + list(P.pos[i][2:])
                        for i in sorted(P.pos)}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=float) + '\n')
    import a2_floorplan as FP
    FP.svg(P, W, H, str(out.with_suffix('.svg')))


if __name__ == '__main__':
    main()
