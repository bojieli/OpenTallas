#!/usr/bin/env python3
"""One objective for every S81 floorplan candidate (GLOBAL-FP-S; screen only, never a closure).

Same estimator for every candidate, so differences are meaningful even though absolute numbers are block-level:
  * p2p link length = Manhattan gap between the two block rectangles at their facing faces (pins assumed packed on
    the facing face, i.e. the GEO-S pin-override optimum) + the VM internal span when one end is the VM
    (mean Manhattan distance from the entry point to the centres of the VM's bank slices; VM ports reach every bank).
  * tree links (x broadcast PQ->frames, field returns frames->gather): rectilinear MST over the frame street ports and
    the root port (nearest point of the root rectangle to the leaves); broadcast segments carry the full width,
    collect segments carry min(trunk, bits of the frames below them).
  * relays: a register every REACH um of wire (contract v21 recipe hop_r_cc 500 um); p2p stages = ceil(L/REACH)-1.
  * field latency: worst frame of (PQ -> frame along the x tree) + (frame -> gather along its return tree), cycles at
    one stage per REACH.
  * cuts: L-route halves of every segment onto a 200-um gcell grid; capacity = 21.09 bits/um (GEO-S over-tile window:
    5,484.375 bits / 260 um); share = demand / capacity; >0.60 counted.
  * bits_over_500: p2p bits whose block-to-block path exceeds 500 um + tree leaf bits whose root path exceeds 500 um
    (each needs >=1 relay stage).
Outputs metrics + a links.json (opentallas.floorplan.links.v1, the schema agreed in el1015-dataflow-viz.log).
"""
import collections, hashlib, json, math
from pathlib import Path

REACH = 500.0
GC = 200.0
CAP_PER_UM = 5484.375 / 260.0


def nearest_on_rect(r, p):
    x, y, w, h = r
    return [min(max(p[0], x), x + w), min(max(p[1], y), y + h)]


def facing_points(a, b):
    """closest pair of points of two rectangles (pins on the facing faces)"""
    pa, pb = [0, 0], [0, 0]
    for k in (0, 1):
        a0, a1 = a[k], a[k] + a[k + 2]
        b0, b1 = b[k], b[k] + b[k + 2]
        if a1 < b0:
            pa[k], pb[k] = a1, b0
        elif b1 < a0:
            pa[k], pb[k] = a0, b1
        else:
            m = (max(a0, b0) + min(a1, b1)) / 2
            pa[k] = pb[k] = m
    return pa, pb


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def vm_slices(r, shape):
    x, y, w, h = r
    if shape == '2x2':
        sw, sh = (w - 21.6) / 2, (h - 561.6 - 2 * 21.6) / 2
        return [[x + (sw + 21.6) * (s % 2) + sw / 2, y + (sh + 21.6) * (s // 2) + sh / 2] for s in range(4)]
    if shape == '1x4v':
        sh = (h - 561.6 - 4 * 21.6) / 4
        return [[x + w / 2, y + (sh + 21.6) * s + sh / 2] for s in range(4)]
    if shape == '4x1h':
        sw = (w - 561.6 - 4 * 21.6) / 4
        return [[x + (sw + 21.6) * s + sw / 2, y + h / 2] for s in range(4)]
    return [[x + w / 2, y + h * (s + .5) / 4] for s in range(4)]   # legacy slab: 4 bank groups stacked


def vm_internal(r, shape, entry):
    sl = vm_slices(r, shape)
    return sum(man(entry, c) for c in sl) / len(sl)


def mst(points, root=0):
    """Prim, rectilinear; returns parent list"""
    n = len(points)
    INF = float('inf')
    d = [INF] * n; par = [-1] * n; done = [False] * n
    d[root] = 0
    for _ in range(n):
        u = min((i for i in range(n) if not done[i]), key=lambda i: d[i])
        done[u] = True
        pu = points[u]
        for v in range(n):
            if not done[v]:
                dv = abs(pu[0] - points[v][0]) + abs(pu[1] - points[v][1])
                if dv < d[v]:
                    d[v] = dv; par[v] = u
    return par


def tree_geometry(e, rects, ports, corr=None, region_x=None, root_rect=None):
    """root_rect: optional port slot of the root block (root point only; direct-side test uses the whole block)"""
    leaves = [f for f in e['ends'] if f.startswith('F')]
    roots = [r for r in e['ends'] if not r.startswith('F')]
    lp = [ports[f] for f in leaves]
    cx = sum(p[0] for p in lp) / len(lp); cy = sum(p[1] for p in lp) / len(lp)
    rp = nearest_on_rect(root_rect or rects[roots[0]], [cx, cy])
    pts = [rp] + lp
    par = mst(pts, 0)
    W = e['width']
    bits = [0.0] + [e['leaf_bits'][f] for f in leaves]
    order = sorted(range(1, len(pts)), key=lambda i: -_depth(par, i))
    sub = bits[:]
    for i in order:
        sub[par[i]] += sub[i]
    segs = []
    for i in range(1, len(pts)):
        w = W if e.get('tree_mode') == 'broadcast' else min(W, sub[i])
        segs.append((pts[par[i]], pts[i], w))
    # root -> leaf latency: Manhattan (a rectilinear Steiner arborescence reaches every leaf at its Manhattan distance;
    # the MST is used for wire only)
    # spine crossing: leaves on a side the root does not face reach it through the corridor band only
    from placer import via_len
    r = rects[roots[0]]
    wd = region_x is None or r[0] <= region_x[0] + 60
    ed = region_x is None or r[0] + r[2] >= region_x[1] - 60
    half = e['_half']
    plen = {}
    for i in range(1, len(pts)):
        f = leaves[i - 1]
        direct = (half[f] == 'W' and wd) or (half[f] == 'E' and ed)
        plen[f] = via_len(pts[0], pts[i], corr, direct)
    trunk = W if e.get('tree_mode') == 'broadcast' else min(W, sum(bits))
    for side in ('W', 'E'):
        sl = [i for i in range(1, len(pts)) if half[leaves[i - 1]] == side]
        if not sl or (side == 'W' and wd) or (side == 'E' and ed) or corr is None:
            continue
        i = min(sl, key=lambda i: man(pts[0], pts[i]))
        extra = via_len(pts[0], pts[i], corr, False) - man(pts[0], pts[i])
        if extra > 0:
            segs.append((pts[0], [pts[0][0], pts[0][1] + (extra / 2 if pts[0][1] < corr[1] else -extra / 2)], trunk))
            segs.append(([pts[0][0], pts[0][1] + (extra / 2 if pts[0][1] < corr[1] else -extra / 2)], pts[0], trunk))
    return rp, segs, plen


def _depth(par, i):
    d = 0
    while par[i] != -1:
        i = par[i]; d += 1
    return d


class Grid:
    def __init__(self, W, H):
        self.nx, self.ny = int(math.ceil(W / GC)), int(math.ceil(H / GC))
        self.h = collections.Counter(); self.v = collections.Counter()

    def add(self, p, q, w, pin_density=10.4):
        # a wide bus leaves its face over span = bits / pin density (GEO-S C3: 6,972 bits on 669 um of face):
        # spread across that span perpendicular to the longer direction, then two L routes, half the bits each
        span = w / pin_density
        n = max(1, int(math.ceil(span / GC)))
        horiz = abs(q[0] - p[0]) >= abs(q[1] - p[1])
        for k in range(n):
            off = (k - (n - 1) / 2) * GC
            pp = [p[0], p[1] + off] if horiz else [p[0] + off, p[1]]
            qq = [q[0], q[1] + off] if horiz else [q[0] + off, q[1]]
            self._add(pp, qq, w / n)

    def _add(self, p, q, w):
        for a, b in ((p, q), (q, p)):
            self._hseg(a[0], b[0], a[1], w / 2); self._vseg(a[1], b[1], b[0], w / 2)

    def _hseg(self, x0, x1, y, w):
        if x0 > x1: x0, x1 = x1, x0
        j = min(max(int(y // GC), 0), self.ny - 1)
        for i in range(int(x0 // GC), int(x1 // GC)):
            self.h[(i, j)] += w        # crosses vertical gcell boundary at x=(i+1)*GC

    def _vseg(self, y0, y1, x, w):
        if y0 > y1: y0, y1 = y1, y0
        i = min(max(int(x // GC), 0), self.nx - 1)
        for j in range(int(y0 // GC), int(y1 // GC)):
            self.v[(i, j)] += w

    def stats(self):
        cap = CAP_PER_UM * GC
        sh = [v / cap for v in list(self.h.values()) + list(self.v.values())]
        sh.sort()
        return dict(max_share=round(sh[-1], 3) if sh else 0, p99_share=round(sh[int(.99 * (len(sh) - 1))], 3) if sh else 0,
                    gcell_edges_over_060=sum(s > .6 for s in sh), gcell_edges_over_100=sum(s > 1.0 for s in sh))


def score(graph, layout, name, vm_shape, notes=None, corridor=None, region_x=None):
    """layout: {node: [x,y,w,h]} overrides; returns (metrics, links_json)"""
    nodes = graph['nodes']
    rects = {n: list(layout.get(n, v['rect'])) for n, v in nodes.items()}
    ports = {}
    for n, v in nodes.items():
        if 'port' in v:
            dx, dy = rects[n][0] - v['rect'][0], rects[n][1] - v['rect'][1]
            ports[n] = [v['port'][0] + dx, v['port'][1] + dy]
    W, H = graph['die_um']
    grid = Grid(W, H)
    links = []
    tot = collections.Counter()
    long_links = []
    xpath, rpath = {}, {}
    for e in graph['edges']:
        if e['kind'] == 'tree':
            e['_half'] = {f: nodes[f]['half'] for f in e['ends'] if f.startswith('F')}
            rp, segs, plen = tree_geometry(e, rects, ports, corridor, region_x)
            wl = sum(man(a, b) * w for a, b, w in segs)
            L = sum(man(a, b) for a, b, _ in segs)
            relays = sum(w * math.floor(man(a, b) / REACH) for a, b, w in segs)
            for a, b, w in segs:
                grid.add(a, b, w)
            over = sum(e['leaf_bits'][f] for f, l in plen.items() if l > REACH)
            store = xpath if e.get('tree_mode') == 'broadcast' else rpath
            for f, l in plen.items():
                store[f] = l
            src = dict(node=e['ends'][0], port='tree_root', x_um=rp[0], y_um=rp[1])
            dst = [dict(node=f, port='street', x_um=ports[f][0], y_um=ports[f][1]) for f in e['ends'] if f.startswith('F')]
            length = max(plen.values())
            stages = int(math.ceil(length / REACH)) - 1 if length > REACH else 0
            tw = sum(e['leaf_bits'].values()) if e.get('tree_mode') != 'broadcast' else e['width']
        else:
            a, b = e['ends']
            pa, pb = facing_points(rects[a], rects[b])
            L = man(pa, pb)
            if 'sp_vm' in (a, b):
                L += vm_internal(rects['sp_vm'], vm_shape, pa if a == 'sp_vm' else pb)
            wl = L * e['width']
            stages = int(math.ceil(L / REACH)) - 1 if L > REACH else 0
            relays = stages * e['width']
            over = e['width'] if L > REACH else 0
            grid.add(pa, pb, e['width'])
            src = dict(node=a, port='face', x_um=pa[0], y_um=pa[1]); dst = [dict(node=b, port='face', x_um=pb[0], y_um=pb[1])]
            length = L
            tw = e['width']
            if L > 3000 and e['width'] >= 256:
                long_links.append(dict(id=e['id'], ends=e['ends'], bits=e['width'], length_um=round(L), cls=e['cls']))
        traffic_wl = wl * e['duty']
        tot['bit_um'] += wl; tot['traffic_bit_um'] += traffic_wl; tot['relay_flops'] += relays; tot['bits_over_500'] += over
        if e['critical']:
            tot['critical_traffic_bit_um'] += traffic_wl
        tot['cls:' + e['cls']] += traffic_wl
        links.append(dict(id=e['id'], **{'class': e['cls']}, bits=e['width'], src=src, dst=dst,
                          activations_per_token=None, traffic_bits_per_token=None,
                          duty=e['duty'], traffic_bits_per_cycle=round(e['width'] * e['duty'], 2),
                          critical=('layer_loop' if e['critical'] else 'none'),
                          length_um=round(length, 1), hpwl_bit_um=round(wl, 1), stages=stages, relays=int(relays),
                          over_reach=length > REACH, tree_mode=e.get('tree_mode'), provenance=e['prov']))
    lat = {f: xpath.get(f, 0) + rpath.get(f, 0) for f in set(xpath) | set(rpath)}
    worst_f = max(lat, key=lat.get)
    g = grid.stats()
    legal = legality(graph, rects)
    m = dict(candidate=name, vm_shape=vm_shape,
             sum_bit_um_M=round(tot['bit_um'] / 1e6, 2), sum_traffic_bit_um_M=round(tot['traffic_bit_um'] / 1e6, 3),
             critical_traffic_bit_um_M=round(tot['critical_traffic_bit_um'] / 1e6, 3),
             relay_flops=int(tot['relay_flops']), bits_over_500=int(tot['bits_over_500']),
             field_worst_path_um=round(lat[worst_f]), field_worst_frame=worst_f,
             field_worst_cycles=int(math.ceil(lat[worst_f] / REACH)),
             field_mean_path_um=round(sum(lat.values()) / len(lat)),
             cut=g, long_links=sorted(long_links, key=lambda r: -r['bits'] * r['length_um']),
             by_class_traffic_bit_um_M={k[4:]: round(v / 1e6, 3) for k, v in tot.items() if k.startswith('cls:')},
             legality=legal, notes=notes or [], corridor=corridor, region_x=region_x)
    lj = dict(schema='opentallas.floorplan.links.v1', design='ds_rom_s81', candidate=name,
              die=dict(w_um=W, h_um=H, mm2=W * H / 1e6), reach_um=REACH,
              nodes=[dict(id=n, master=v.get('master', v['kind']), x_um=rects[n][0], y_um=rects[n][1], w_um=rects[n][2],
                          h_um=rects[n][3], orient='R0', group=v['kind'], fixed=v['movable'] in ('fixed_io', 'field_array'),
                          area_mm2=rects[n][2] * rects[n][3] / 1e6) for n, v in nodes.items()],
              links=links, metrics=m, unknowns=[u['node'] + ': ' + u['why'] for u in graph['unknowns']])
    return m, lj


def legality(graph, rects):
    W, H = graph['die_um']
    names = list(rects)
    bad, outside = [], []
    for n in names:
        x, y, w, h = rects[n]
        if x < -1e-6 or y < -1e-6 or x + w > W + 1e-6 or y + h > H + 1e-6:
            outside.append(n)
    srt = sorted(names, key=lambda n: rects[n][0])
    for i, a in enumerate(srt):
        ax, ay, aw, ah = rects[a]
        for b in srt[i + 1:]:
            bx, by, bw, bh = rects[b]
            if bx >= ax + aw - 1e-6:
                break
            if ay < by + bh - 1e-6 and by < ay + ah - 1e-6:
                bad.append([a, b])
    return dict(overlaps=len(bad), overlap_examples=bad[:12], outside=outside)
