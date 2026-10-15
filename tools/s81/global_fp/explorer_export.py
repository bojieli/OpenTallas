#!/usr/bin/env python3
"""Write a GLOBAL-FP-S candidate as an explorer links record (opentallas.dataflow.links.v1) for
tools/fleet_viz/dataflow_links.py import --candidate-of s81_gen18c (screen only).

Construction (identical for every candidate, including C0 = GEN18c hubs where they are):
  * start from the canonical explorer record s81_gen18c (GEN18c pass0 plan + exact LEF pins, 78k blocks, 86k links);
  * frames, PHY/ctrl/svc, links, selector/collector bands and every frame-internal link are kept unchanged;
  * the hub blocks take the candidate rectangles (pqrom macros move with sp_pq; the VM takes the candidate shape);
    unbound reservations (MIX4, HCX homes/controller/gatherpack, embed expand, Engram dispatch) are added as blocks;
  * every die-level transport component that touches a hub (its stations, hub ends, link clock stations) is removed
    and its links are replaced by the GLOBAL-FP-S graph edge (graph.py), re-planned on the candidate geometry:
      - p2p links that the plan wires through transport -> L-route relay chain, one station every RELAY um (the
        plan's own hub station reach, 215 um), ends on the facing faces ('box' ends: pins not yet assigned);
      - p2p links the plan wires pin-to-pin (abutted) -> direct link between the facing faces;
      - field trees -> rectilinear MST over the frame street ports (cfifo blocks) and the root's nearest face, every
        edge an L-route relay chain; broadcast segments carry the full width, collect segments min(trunk, bits below);
        the far half reaches the root through the candidate's crossing corridor (detour hop) as in score.py.
  * t (traffic bits/token) on re-planned links = width x class duty x 828,878.4 cycles/token: an ACTIVITY PROXY from
    the measured AR token path class shares, not a per-link calendar (none exists yet); kept frame links t = null.
"""
import collections, gzip, hashlib, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import score as S
from placer import via_len

RELAY = 215.0
CYCLES_PER_TOKEN = 828878.4
TRANSPORT = {'stn', 'hstn', 'hend', 'xstg', 'lkck'}
NONDATA = {'fclk', 'clock', 'reset', 'col_clock', 'col_reset'}


def load(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)


def lroute(a, b, bits):
    """L-route a->b (x first) split into hops of <= RELAY um; returns (hops, stages)"""
    pts = [tuple(a)]
    corner = (b[0], a[1])
    for p, q in ((a, corner), (corner, b)):
        L = abs(q[0] - p[0]) + abs(q[1] - p[1])
        n = max(1, int(math.ceil(L / RELAY))) if L > 0 else 0
        for k in range(1, n + 1):
            t = k / n
            pts.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    hops = [[pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], bits] for i in range(len(pts) - 1)]
    return hops, max(0, len(hops) - 1)


PIN_DENSITY = 10.4      # bits/um of face (GEO-S C3: 6,972 bits on 669 um), as score.Grid
CHUNK = 1024


def spread(ra, rb, width):
    """a wide p2p bus leaves its facing face over span = width / PIN_DENSITY (capped by the face overlap):
    split into ceil(width / CHUNK) parallel sub-links at evenly spaced positions along the overlap."""
    pa, pb = S.facing_points(ra, rb)
    n = max(1, int(math.ceil(width / CHUNK)))
    ax = None
    for k in (0, 1):
        lo, hi = max(ra[k], rb[k]), min(ra[k] + ra[k + 2], rb[k] + rb[k + 2])
        if hi > lo:
            ax, olo, ohi = k, lo, hi
    if n == 1:
        return [(pa, pb, width)]
    if ax is None:
        # diagonal neighbours: nested L's under the x-first L-route the cut metric uses: chunk i leaves a's face
        # that faces b in x at a's corner + o_i along y, and lands on b's face that faces a in y at b's corner + o_i
        # along x (rows and columns distinct, legs never cross each other or either block)
        span = min(ra[3], rb[2], width / PIN_DENSITY)
        da = 1 if pa[1] <= ra[1] + 1e-6 else -1
        db = 1 if pb[0] <= rb[0] + 1e-6 else -1
        out, base = [], width // n
        for i in range(n):
            off = (i + .5) * span / n
            qa, qb = list(pa), list(pb)
            qa[1] += da * off; qb[0] += db * off
            out.append((qa, qb, base + (1 if i < width - base * n else 0)))
        return out
    span = min(ohi - olo, width / PIN_DENSITY)
    c = (olo + ohi) / 2
    out = []
    base = width // n
    for i in range(n):
        off = (i - (n - 1) / 2) * span / n
        qa, qb = list(pa), list(pb)
        qa[ax] = qb[ax] = c + off
        out.append((qa, qb, base + (1 if i < width - base * n else 0)))
    return out


def replaced_transport(plan, moved):
    """transport instances of every die-level component that touches a moved block"""
    ins = {i[0]: i for i in plan['insts']}
    par = {}

    def f(x):
        while par.setdefault(x, x) != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for b in plan['buses']:
        if b[1] in NONDATA:
            continue
        tr = [n for n, _ in b[3] if n in ins and ins[n][7] in TRANSPORT]
        for t in tr[1:]:
            par[f(tr[0])] = f(t)
    touch = set()
    for b in plan['buses']:
        if b[1] in NONDATA:
            continue
        ends = [n for n, _ in b[3] if n in ins]
        tr = [n for n in ends if ins[n][7] in TRANSPORT]
        if tr and any(n in moved for n in ends):
            touch.add(f(tr[0]))
    return {n for n, i in ins.items() if i[7] in TRANSPORT and f(n) in touch}


def export(canon, plan, graph, layout, vm_shape, cid, label, corridor=None, region_x=None, inputs=()):
    """inputs: [{path, sha256, role}] provenance of canonical record, plan, graph, candidates file"""
    B = canon['blocks']; n0 = len(B['name'])
    idx = {nm: k for k, nm in enumerate(B['name'])}
    hubs = {nm for nm, k in zip(B['name'], B['kind']) if k in ('hub', 'pqrom')}
    rem = replaced_transport(plan, hubs)
    keep = [k for k in range(n0) if B['name'][k] not in rem]
    remap = {k: j for j, k in enumerate(keep)}
    NB = {c: [B[c][k] for k in keep] for c in ('name', 'master', 'kind', 'group', 'reg', 'x', 'y', 'w', 'h')}
    nidx = {nm: j for j, nm in enumerate(NB['name'])}
    # move hubs
    rects = {n: list(layout.get(n, v['rect'])) for n, v in graph['nodes'].items()}
    dpq = (rects['sp_pq'][0] - graph['nodes']['sp_pq']['rect'][0], rects['sp_pq'][1] - graph['nodes']['sp_pq']['rect'][1])
    for nm, j in nidx.items():
        if nm in rects and B['kind'][idx[nm]] == 'hub':
            r = rects[nm]
            w = r[2] if nm != 'sp_pq' else NB['w'][j]           # sp_pq keeps its own width; pqroms sit E of it
            NB['x'][j], NB['y'][j], NB['w'][j], NB['h'][j] = r[0], r[1], w, r[3]
            if nm == 'sp_vm':
                NB['master'][j] = 'dsfd_sp_vm[%s candidate shape]' % vm_shape
        elif nm.startswith('pqrom'):
            NB['x'][j] += dpq[0]; NB['y'][j] += dpq[1]
    for n, v in graph['nodes'].items():                          # unbound reservations
        if v.get('movable') == 'reservation' and n not in nidx:
            r = rects[n]
            nidx[n] = len(NB['name'])
            for c, val in (('name', n), ('master', v.get('master', 'res')), ('kind', 'res'), ('group', 'reservation'),
                           ('reg', 0), ('x', r[0]), ('y', r[1]), ('w', r[2]), ('h', r[3])):
                NB[c].append(val)
    # kept links
    dropped = [l for l in canon['links'] if any(e[0] >= 0 and (B['name'][e[0]] in rem or B['name'][e[0]] in hubs) for e in l['e'])]
    dropped_ids = {l['i'] for l in dropped}
    links = []
    for l in canon['links']:
        if l['i'] in dropped_ids:
            continue
        l2 = {k: v for k, v in l.items() if k not in ('x', 'xb')}
        l2['e'] = [[remap[e[0]] if e[0] >= 0 else -1] + e[1:] for e in l['e']]
        links.append(l2)
    # re-planned die links from the graph
    cfifo = {}
    for nm, j in nidx.items():
        if NB['kind'][j] == 'cfifo' and str(NB['group'][j]).startswith('frame_'):
            cfifo['F' + NB['group'][j][6:]] = j
    ports = {}
    for n, v in graph['nodes'].items():
        if 'port' in v:
            ports[n] = v['port']
    nodes = graph['nodes']
    added_bits = 0
    # root port slots: the m trees of one root take m equal strips of the root block along its longer side, in the
    # order of their leaf centroids (a port assignment; without it every trunk would land on one point)
    slots, byroot = {}, collections.defaultdict(list)
    for e in graph['edges']:
        if e['kind'] == 'tree':
            byroot[e['ends'][0]].append(e)
    for root, es in byroot.items():
        r = rects[root]; k = 0 if r[2] >= r[3] else 1
        es = sorted(es, key=lambda e: sum(ports[f][k] for f in e['ends'][1:]) / (len(e['ends']) - 1))
        for j, e in enumerate(es):
            q = list(r); q[k] = r[k] + r[k + 2] * j / len(es); q[k + 2] = r[k + 2] / len(es)
            slots[e['id']] = q
    for e in graph['edges']:
        t = round(e['width'] * e['duty'] * CYCLES_PER_TOKEN)
        cr = 1 if e['critical'] else 0
        def bidx(nm):
            return cfifo[nm] if nm.startswith('F') else nidx[nm]
        if e['kind'] == 'tree':
            e['_half'] = {f: nodes[f]['half'] for f in e['ends'] if f.startswith('F')}
            rp, segs, plen = S.tree_geometry(e, rects, ports, corridor, region_x, root_rect=slots.get(e['id']))
            hops, depth = [], {}
            for a, b, w in segs:
                h, s = lroute(a, b, round(w))
                hops += h
            leaves = [f for f in e['ends'] if f.startswith('F')]
            length = max(plen.values())
            stages = int(math.ceil(length / RELAY)) - 1 if length > RELAY else 0
            ends = [[nidx[e['ends'][0]], 'tree_root', rp[0], rp[1], 'box']] + [[cfifo[f], 'street', ports[f][0], ports[f][1], 'box'] for f in leaves]
            if e.get('tree_mode') != 'broadcast':
                ends = ends[1:] + ends[:1]      # collect: frames drive, root sinks; first end = one driver
            bits = e['width']
            links.append(dict(i='gfp_' + e['id'], c=e['cls'], b=bits, d=0, e=ends, h=hops, s=stages, L=round(length, 1),
                              t=t, cr=cr, n='GLOBAL-FP-S re-planned %s tree (%d frames), %s' % (e.get('tree_mode'), len(leaves), e['prov'])))
            added_bits += bits
        else:
            a, b = e['ends']
            relayed = 'transport' in e['prov']
            for k, (pa, pb, bits) in enumerate(spread(rects[a], rects[b], e['width'])):
                L = S.man(pa, pb)
                ends = [[bidx(a), 'face', pa[0], pa[1], 'box'], [bidx(b), 'face', pb[0], pb[1], 'box']]
                rec = dict(i='gfp_%s_%d' % (e['id'], k), c=e['cls'], b=bits, d=0, e=ends,
                           t=round(t * bits / e['width']), cr=cr,
                           n='GLOBAL-FP-S re-planned p2p (%s), %s' % ('relayed L-route' if relayed else 'direct', e['prov']))
                if relayed and L > RELAY:
                    hops, st = lroute(pa, pb, bits)
                    rec.update(h=hops, s=st, L=round(L, 1))
                else:   # one explicit hop so the importer keeps the spread face points (no re-clip)
                    rec.update(h=[[pa[0], pa[1], pb[0], pb[1], bits]], s=0, L=round(L, 1))
                links.append(rec)
            added_bits += e['width']
    rec = dict(schema='opentallas.dataflow.links.v1', id=cid, label=label, design=canon['design'],
               token_designs=canon.get('token_designs', []), revision='GLOBAL-FP-S ' + cid, role='candidate',
               scope='SCREEN_ONLY_BLOCK_LEVEL_CANDIDATE_NOT_ADOPTED_NOT_NATIVE', outline=canon['outline'],
               reach_um=canon.get('reach_um', 500.0), reach_source=canon.get('reach_source'),
               relay_reach_um=RELAY, stages_explicit=True,
               relay_reach_source='re-planned links: one station per %.0f um (plan hub_station_reach_um); kept frame links: plan register instances' % RELAY,
               registers='kept links: plan register chains; re-planned hub links: synthesized stations every %.0f um on L-routes' % RELAY,
               direction='kept links: plan driver first; re-planned links: undirected (d=0)',
               pins='kept links: exact LEF pin centroids; re-planned hub links: facing-face points (box), pins not yet assigned',
               blocks=NB, links=links,
               provenance=dict(inputs=list(inputs)),
               replan=dict(removed_transport_blocks=len(rem), dropped_canonical_links=len(dropped),
                           dropped_canonical_bits=sum(l['b'] or 0 for l in dropped), replanned_links=len(graph['edges']),
                           replanned_bits=added_bits))
    return rec
