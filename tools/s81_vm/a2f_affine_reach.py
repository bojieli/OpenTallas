#!/usr/bin/env python3
"""S81 VM A2-F client-affine reach (S-VM 0030 for S-FUNC mapping A): per VM port group and per storage slice, the
wire-relay edges of every path class, from actual leaf pin positions in the same placement a2f_hub_faces.py screens.

Placement / pins / port spans: exactly a2f_hub_faces.py (build_split4 -> arrange -> spans_from_plan -> install_spans,
optional hop1).  Every bit connection is a register-to-register hop (every VM leaf registers its pins); a hop of length L
needs ceil(L / R) - 1 relay registers and a hop class pays its longest bit.  Leaf-to-leaf hop lengths are pin-to-pin
Manhattan lengths of shared nets (driver -> farthest sink), NOT the Prim-tree chaining of the VM.RELAY ledger basis.

Client affinity: the compiler places a client's tensors only in its slice set, so its paths only touch that set's leaves.
Port -> slice-leaf hops are RETARGETED: today A2 stripes each port word over all four slices (bit b -> payload[s(b)]),
so for slice s every bit of the group is measured from its actual port pin to the SAME pin/bit of the slice-s copy of
the leaf it lands on (identical masters per slice) -- i.e. the wire an affine re-wiring would need.  Paths:
  raw write    port -> (central cdc/landing/header/cap leaves) -> payload|front[s] -> front -> scatter -> b8 [-> b4] -> bank
  read request port -> (central rsched ...) -> fsr[s] -> b8 [-> b4] -> bank            (= raw read: request at the bank)
  read return  bank -> [b4 ->] b8 -> return[s] -> (central read / cdc leaves) -> port
  commit       b8[s] -> seq (central)
Central chains follow the RTL's own port classes (write data -> payload, write address/valid -> front, capture -> cap ->
x34 -> payload, svc/sel/collector -> x34 -> landing -> payload, read request -> rsched -> fsr, read return -> read leaf).
For a SLICE SET each port bit is assigned to the nearest slice of the set (balance reported, not enforced); central ->
slice hops pay the worst slice of the set.  Edges are UPPER-BOUND planning numbers (screen, not GRT/native); S-FUNC prices them per job class.
"""
import argparse
import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a2f_hub_faces as HF  # noqa: E402

R, RP = HF.R, HF.RP
ROOT = HERE.parents[1]

# path kind -> (port prefixes, class chain).  'port' marks the VM face pin; the first sliced class is per slice.
KINDS = {
    'raw_write': [(('f_su_wqd', 'f_su_wqm', 'f_mx_wqd', 'f_mx_wqm', 'f_hc_wqd', 'f_hc_wqm'), ['port', 'payload']),
                  (('f_su_wq', 'f_su_wqv', 'f_mx_wq', 'f_mx_wqv', 'f_hc_wq', 'f_hc_wqv'), ['port', 'front']),
                  (('f_capture',), ['port', 'cap', 'cdc', 'cdc_t', 'payload']),
                  (('aSW', 'sel', 'col'), ['port', 'cdc', 'cdc_t', 'landing', 'payload'])],
    'read_request': [(('f_su_rq', 'f_su_rqv', 'f_mx_rq', 'f_mx_rqv', 'f_hc_rq', 'f_hc_rqv', 'f_pqx'), ['port', 'rsched', 'fsr'])],
    'read_return': [(('t_su_rs', 't_su_rsv', 't_mx_rs', 't_mx_rsv', 't_hc_rs', 't_hc_rsv', 't_pqx'), ['port', 'read', 'return'])],
}
CLIENT = {'su': 'su', 'mx': 'mix4', 'hc': 'hc', 'pqx': 'pq', 'capture': 'capture', 'aSW': 'svc', 'sel': 'sel', 'col': 'collector'}
MAP_A = {   # S-FUNC mapping A (a8fd3ddd60194f136, 10-15 ~23:2x): consumer-affine slice sets, plus its cross-client pairs
    'su': [0, 1], 'mix4': [0, 2], 'hc': [3], 'pq': [3], 'collector': [3], 'svc': [1], 'sel': [1],
    'capture->su': [0, 1], 'capture->hc/pq': [3], 'su->pq': [3], 'su->coll': [1], 'coll->su': [0, 1], 'svc->su': [0, 1],
    'su->svc': [1], 'hc->mix4': [0, 2], 'hc->su': [0, 1], 'mix4->hc': [3], 'mix4/3slices': [0, 1, 2],
}
SLICED = {'payload', 'front', 'fault', 'scatter', 'b8', 'b4', 'bank', 'return', 'fsr'}


def slice_of(name):
    m = re.search(r'(?:u_mem\.slice|a2f\.payload|w0_payload)\[(\d)\]', name)
    return int(m.group(1)) if m else None


def other_slice_name(name, s):
    return re.sub(r'((?:u_mem\.slice|a2f\.payload|w0_payload)\[)\d(\])', lambda m: m.group(1) + str(s) + m.group(2), name)


def stages(L, reach):
    return max(0, math.ceil(L / reach) - 1)


def client_of(port):
    for k, v in CLIENT.items():
        if port.startswith(('f_' + k, 't_' + k)) or port == k or port.startswith(k):
            return v
    return port


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--hub-plan', required=True)
    ap.add_argument('--assigned-pins')
    ap.add_argument('--hop1', action='store_true')
    ap.add_argument('--center-ctl', action='store_true', help='lever 2: rsched + seq tile at the FSR / b8 centroid')
    ap.add_argument('--reach', type=float, nargs='+', default=[900.0, 1118.0])
    ap.add_argument('--width', type=float, default=5771.4)
    ap.add_argument('--rows', default='f0,f1,f2,f3,f4,f5,f6,f7/ctl,fj,meta')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    HF.CAPROW_PER, HF.SU_X0 = 8, 0.0
    rows = [r.split(',') for r in a.rows.split('/')]
    P, nets, W, H, struct, _ = HF.build_split4(a.width - 734.4, rows, True, False, True)
    assigned = json.loads(Path(a.assigned_pins).read_text()) if a.assigned_pins else None
    W, H = HF.arrange(P, W, H, struct, 'caprow', None)
    moved = HF.center_ctl(P, W, H) if a.center_ctl else None
    if a.hop1:
        nets = HF.hop1(P, nets)
    sp = HF.spans_from_plan(a.hub_plan, W, H)
    HF.install_spans(sp, assigned)
    R.connections(P, nets, W, H)            # fills R._last_port_place with the screen's exact port pins
    place = R._last_port_place
    L = P.leaves
    models = R.pin_models(L)
    by_name = {L[i]['name']: i for i in P.pos}
    cls = {i: RP.cls(L[i]['master']) for i in P.pos}
    slc = {i: slice_of(L[i]['name']) for i in P.pos}

    def pin(i, p, b):
        x, y, fx, fy = P.pos[i]
        return R.pin_xy(L[i], models[L[i]['master']], p, b, x, y, fx, fy)

    portbit = collections.defaultdict(dict)     # port -> {(net, bit): {inst: um}} (sliced targets retargeted to all 4)
    netpts = []                                 # per net: [(inst, xy)] of its leaf pins
    n_raw = 0
    for eps in nets:
        lv = [e for e in eps if e[0] >= 0]
        if not lv:
            continue
        netpts.append([(e[0], pin(*e)) for e in lv])
        for e in eps:
            if e[0] >= 0:
                continue
            pp = place[(n_raw, e[1])]
            dd = {}
            for (i, p, b) in lv:
                tg = [i] if slc[i] is None else [by_name[other_slice_name(L[i]['name'], s)] for s in range(4)]
                for j in tg:
                    assert L[j]['master'] == L[i]['master']
                    q = pin(j, p, b)
                    dd[j] = max(dd.get(j, 0.0), abs(pp[0] - q[0]) + abs(pp[1] - q[1]))
            portbit[e[1]][(n_raw, e[2])] = dd
        n_raw += 1

    def prim_pairs(sset):
        """leaf-to-leaf hops for a client confined to sset: every pin pair of a shared net (driver -> each sink is a
        register-to-register wire at least its Manhattan length, whatever the buffer tree), keeping central leaves and
        the set's slice leaves.  Nets over 64 leaves (reset/select broadcast) are excluded.  NOTE: the VM.RELAY ledger
        (a2f_reach_price) uses Prim-tree edges, which chain sinks (rsched -> fsr: 1,183 um) and so UNDER-state a
        broadcast driver's reach to its farthest sink (rsched -> slice-0/2 fsr: 4,244-4,354 um here)."""
        pair = collections.defaultdict(float)
        for pts in netpts:
            pts = [q for q in pts if slc[q[0]] is None or slc[q[0]] in sset]
            if len(pts) < 2 or len({q[0] for q in pts}) > 64:
                continue
            for k in range(len(pts)):
                for j in range(k + 1, len(pts)):
                    (i1, a1), (i2, a2) = pts[k], pts[j]
                    if i1 != i2:
                        key = (min(i1, i2), max(i1, i2))
                        pair[key] = max(pair[key], abs(a1[0] - a2[0]) + abs(a1[1] - a2[1]))
        adj = collections.defaultdict(set)
        cmax = collections.defaultdict(float)   # frozenset classes -> max um over the set's in-slice/central pairs
        for (i1, i2), d in pair.items():
            adj[i1].add(i2)
            adj[i2].add(i1)
            if slc[i1] is not None and slc[i2] is not None and slc[i1] != slc[i2]:
                continue                        # cross-slice Prim edges are not a register hop of any path class
            if slc[i1] is None and slc[i2] is None:
                continue
            k = frozenset((cls[i1], cls[i2]))
            cmax[k] = max(cmax[k], d)
        return pair, adj, cmax
    store = ['b8', 'bank'] if a.hop1 else ['b8', 'b4', 'bank']

    def internal(kind, first):
        if kind == 'raw_write':
            return ([first] + (['front'] if first == 'payload' else []) + ['scatter'] + store)
        if kind == 'read_request':
            return ['fsr'] + store
        return list(reversed(store)) + ['return']

    def path(port, kind, chain_cls, sset, reach, G):
        """hop list [(name, um, stages)] for one port on slice set sset (data flows port->bank, or bank->port)."""
        pair, adj, cmax = G
        hops = []
        cur = None                                  # current central instance set
        bits = portbit[port]
        balance = None
        for ca, cb in zip(chain_cls, chain_cls[1:]):
            if ca == 'port':
                if cb in SLICED:                    # balanced per-bit assignment to the set's slices
                    prefs = []
                    for key, dd in bits.items():
                        ds = sorted((d, slc[j]) for j, d in dd.items() if cls[j] == cb and slc[j] in sset)
                        if ds:              # bits landing on another class (e.g. wq header-only bits) are skipped
                            prefs.append(ds)
                    assert prefs, (port, cb, sset)
                    quota = {t: -(-len(prefs) // len(sset)) for t in sset}
                    cnt, worst = collections.Counter(), 0.0
                    # most constrained bits first (largest regret between best and second-best slice)
                    for ds in sorted(prefs, key=lambda ds: -(ds[1][0] - ds[0][0]) if len(ds) > 1 else 0.0):
                        d, t = next((d, t) for d, t in ds if cnt[t] < quota[t])
                        cnt[t] += 1
                        worst = max(worst, d)
                    balance = {str(k): v for k, v in sorted(cnt.items())}
                    hops.append((f'port_{cb}', worst, stages(worst, reach)))
                    cur = None
                else:
                    cur = {j for dd in bits.values() for j in dd if cls[j] == cb}
                    worst = max(d for dd in bits.values() for j, d in dd.items() if j in cur)
                    hops.append((f'port_{cb}', worst, stages(worst, reach)))
                continue
            if cb in SLICED:
                nxt = {j for i in cur for j in adj[i] if cls[j] == cb and slc[j] in sset}
            else:
                nxt = {j for i in cur for j in adj[i] if cls[j] == cb}
            assert nxt, (port, ca, cb, sset)
            worst = max(pair[(min(i, j), max(i, j))] for i in cur for j in adj[i] if j in nxt)
            hops.append((f'{ca}_{cb}', worst, stages(worst, reach)))
            cur = nxt
        last = chain_cls[-1]
        tail = internal(kind, last)
        for ca, cb in zip(tail, tail[1:]):
            m = cmax[frozenset((ca, cb))]
            assert m > 0, ('unobserved', ca, cb, sset)
            hops.append((f'{ca}_{cb}', m, stages(m, reach)))
        if kind == 'read_return':          # data flows bank -> return -> read -> port
            nc = len(chain_cls) - 1
            hops = hops[nc:] + hops[:nc][::-1]
        out = dict(edges=sum(h[2] for h in hops), max_um=round(max(h[1] for h in hops), 1),
                   hops=[(h[0], round(h[1], 1), h[2]) for h in hops])
        if balance:
            out['bits_per_slice'] = balance
        if kind == 'raw_write':
            m = cmax[frozenset(('b8', 'seq'))]
            out['commit'] = dict(edges=stages(m, reach), max_um=round(m, 1))
        return out

    ports = sorted(portbit)
    sets = [[0], [1], [2], [3], [0, 1], [0, 2], [1, 3], [2, 3], [0, 1, 2], [0, 1, 3], [0, 2, 3], [0, 1, 2, 3]]
    res = dict(schema='opentallas.s81.vm-affine-reach.v2', status='SCREEN_UPPER_BOUND_NOT_GRT_NOT_NATIVE',
               hub_plan=dict(path=a.hub_plan, sha256=hashlib.sha256(Path(a.hub_plan).read_bytes()).hexdigest()),
               hop1=a.hop1, center_ctl=moved, legality=dict(zip(('spacing', 'outside'), P.check(W, H))), rectangle_um=[W, H], spans=sp, model=__doc__.split('\n\n')[1].replace('\n', ' '),
               mapping_A=MAP_A, by_reach={})
    boxes = {}
    for s in range(4):
        rs = [P.rect(i) for i in P.pos if slc[i] == s]
        boxes[str(s)] = [round(min(r[0] for r in rs), 1), round(min(r[1] for r in rs), 1),
                         round(max(r[0] + r[2] for r in rs), 1), round(max(r[1] + r[3] for r in rs), 1)]
    res['slice_boxes_xyxy_um'] = boxes
    graphs = {tuple(t): prim_pairs(set(t)) for t in sets}
    for reach in a.reach:
        per = collections.defaultdict(dict)
        for kind, specs in KINDS.items():
            for prefixes, chain_cls in specs:
                for port in ports:
                    if port not in prefixes:
                        continue
                    for sset in sets:
                        try:
                            v = path(port, kind, chain_cls, sset, reach, graphs[tuple(sset)])
                        except AssertionError as ex:      # recorded, never priced as zero
                            v = dict(unresolved=repr(ex.args[0]) if ex.args else 'unresolved')
                        per[port].setdefault(kind, {})[','.join(map(str, sset))] = v
        # client x kind x set worst (over the client's ports)
        cl = collections.defaultdict(lambda: collections.defaultdict(dict))
        for port, kinds in per.items():
            c = client_of(port)
            for kind, bys in kinds.items():
                for sk, v in bys.items():
                    if 'unresolved' in v:
                        cl[c].setdefault('unresolved', {}).setdefault(port, []).append(f'{kind}:{sk}')
                        continue
                    o = cl[c][kind].get(sk)
                    e = v['edges'] + (v['commit']['edges'] if kind == 'raw_write' else 0) * 0
                    if o is None or v['edges'] > o['edges']:
                        cl[c][kind][sk] = dict(edges=v['edges'], worst_port=port, commit_edges=v.get('commit', {}).get('edges'))
                    elif kind == 'raw_write' and v['commit']['edges'] > (o.get('commit_edges') or 0):
                        o['commit_edges'] = v['commit']['edges']
        res['by_reach'][str(reach)] = dict(ports=per, clients=cl)
        print('REACH', reach)
        for c, kinds in cl.items():
            print(' ', c, {k: ({s: (v['edges'], v['commit_edges']) if k == 'raw_write' else v['edges']
                               for s, v in bys.items()} if k != 'unresolved' else bys) for k, bys in kinds.items()})
    res['source_tools'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in [Path(__file__), HERE / 'a2f_hub_faces.py', HERE / 'a2f_reach_price.py',
                                     HERE / 'a2f_split4_route_plan.py', HERE / 'a2f_route_plan.py', HERE / 'a2_route_plan.py']}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float) + '\n')


if __name__ == '__main__':
    main()
