#!/usr/bin/env python3
"""dv_route72 + channel capacity (STW-S81-DIE-PLAN G9e 10-21).

Same macro-free construction, same output format and the same 350-um station chopping as dv_route72.py (stations every
<= 350 um of arc, never within 50 um of a corner), with two changes so that wide bundles stop piling onto one line:
  * extra parallel track lines at LAT (43.2 um) pitch inside every free gap between padded bodies (dv_route72 only had
    the padded body edges, so a 302.4-um channel offered 2 lines and an 86.4-um street 1);
  * negotiated congestion (PathFinder): every grid edge has a bit capacity = CAP_BPU bits/um x the band it represents
    (half the distance to the neighbouring parallel lines, <= LAT); a route pays length x (1 + present + history) where
    present = PRES x max(0, (use + b) / cap - 1); after each pass history += HIST x overflow ratio; ITER passes of rip-up
    and re-route.  CAP_BPU 150.9 = the chan.py repeater model at 0.55 of the 0.30 soft cap (bits x 0.175/160/0.30 um2 per
    um of length <= 0.55 x channel width).
The router never crosses a padded body (macro-free), so congestion can only move a route to a parallel line / channel.
Usage: dv_route72c.py PLAN_UNROUTED OUT [--iter 4]
"""
import argparse, heapq, json, math
from pathlib import Path
import numpy as np

LAT = 43.2
CAP_BPU = 0.55 * 0.30 * 160 / 0.175
PRES, HIST = 4.0, 1.0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('--iter', type=int, default=4)
    a = ap.parse_args(); p = json.load(open(a.plan)); bs = p['blocks']; W, H = p['facts']['die_um']; pad = 43.2; stub = 43.2
    rect = [(b['x'] - pad, b['y'] - pad, b['x'] + b['w'] + pad, b['y'] + b['h'] + pad) for b in bs + p.get('blockages', [])]

    def outer(e, f):
        x, y = e[2:4]
        return (round(x + (-stub if f == 'W' else stub if f == 'E' else 0), 4), round(y + (-stub if f == 'S' else stub if f == 'N' else 0), 4))
    terms = {l['i']: [outer(e, f) for e, f in zip(l['e'], l['endpoint_faces'])] for l in p['links']}
    base_x = {32.4, W - 32.4} | {round(v, 4) for r in rect for v in (r[0], r[2], (r[0] + r[2]) / 2) if 0 < v < W} | {q[0] for t in terms.values() for q in t}
    base_y = {32.4, H - 32.4} | {round(v, 4) for r in rect for v in (r[1], r[3], (r[1] + r[3]) / 2) if 0 < v < H} | {q[1] for t in terms.values() for q in t}

    def gap_lines(lo_i, hi_i, lo_o, hi_o, axis):
        """parallel lines at LAT pitch inside free gaps along `axis` (0: x lines in vertical streets)"""
        out = set()
        # gaps: intervals between padded rect edges on this axis, for rects overlapping the other-axis span
        edges = sorted({(r[2 * 0 + axis], r[2 + axis]) for r in rect})
        cuts = sorted([lo_i] + [e for r in edges for e in r] + [hi_i])
        for u, w in zip(cuts, cuts[1:]):
            if w - u >= 2 * LAT:
                n = int((w - u) // LAT)
                for k in range(1, n):
                    out.add(round(u + k * (w - u) / n, 4))
        return out
    xs = sorted(base_x | gap_lines(0, W, 0, H, 0)); ys = sorted(base_y | gap_lines(0, H, 0, W, 1))
    nx, ny = len(xs), len(ys); xa, ya = np.array(xs), np.array(ys); blocked = np.zeros((ny, nx), dtype=np.bool_)
    for x0, y0, x1, y1 in rect:
        ix = np.flatnonzero((xa > x0 + 1e-5) & (xa < x1 - 1e-5)); iy = np.flatnonzero((ya > y0 + 1e-5) & (ya < y1 - 1e-5))
        if len(ix) and len(iy): blocked[iy[0]:iy[-1] + 1, ix[0]:ix[-1] + 1] = True
    xi = {x: i for i, x in enumerate(xs)}; yi = {y: i for i, y in enumerate(ys)}
    # edge capacities: horizontal edge (j, i)->(j, i+1) represents the band of row j; vertical (j, i)->(j+1, i) col i
    def band(arr, k):
        lo = (arr[k] - arr[k - 1]) / 2 if k > 0 else LAT / 2
        hi = (arr[k + 1] - arr[k]) / 2 if k + 1 < len(arr) else LAT / 2
        return min(lo, LAT / 2) + min(hi, LAT / 2)
    rb = np.array([band(ys, j) for j in range(ny)]); cb = np.array([band(xs, i) for i in range(nx)])
    hcap = np.repeat((rb * CAP_BPU)[:, None], nx - 1, axis=1); vcap = np.repeat((cb * CAP_BPU)[None, :], ny - 1, axis=0)
    huse = np.zeros((ny, nx - 1)); vuse = np.zeros((ny - 1, nx)); hhis = np.zeros_like(huse); vhis = np.zeros_like(vuse)
    dxs = np.diff(xa); dys = np.diff(ya)
    print('GRID', nx, ny, 'cap_bpu', round(CAP_BPU, 1), flush=True)

    def route(s, t, b):
        start = (xi[s[0]], yi[s[1]]); goal = (xi[t[0]], yi[t[1]])
        if blocked[start[1], start[0]] or blocked[goal[1], goal[0]]: return None, 'endpoint stub blocked'
        todo = [(abs(s[0] - t[0]) + abs(s[1] - t[1]), 0, start)]; dist = {start: 0}; prev = {}
        while todo:
            _, g, u = heapq.heappop(todo)
            if g > dist.get(u, math.inf) + 1e-6: continue
            if u == goal:
                path = [u]
                while u in prev: u = prev[u]; path.append(u)
                return path[::-1], None
            x, y = u
            for xx, yy in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if xx < 0 or yy < 0 or xx >= nx or yy >= ny or blocked[yy, xx]: continue
                if yy == y:
                    i = min(x, xx); ln = dxs[i]; u0 = huse[y, i]; c0 = hcap[y, i]; hs = hhis[y, i]
                else:
                    j = min(y, yy); ln = dys[j]; u0 = vuse[j, x]; c0 = vcap[j, x]; hs = vhis[j, x]
                pres = PRES * max(0.0, (u0 + b) / c0 - 1.0)
                ng = g + ln * (1.0 + pres + hs)
                v = (xx, yy)
                if ng + 1e-6 >= dist.get(v, math.inf): continue
                dist[v] = ng; prev[v] = u; h = abs(xs[xx] - t[0]) + abs(ys[yy] - t[1]); heapq.heappush(todo, (ng + h, ng, v))
        return None, 'no macro-free path'

    def use(path, b, sgn):
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            if y0 == y1: huse[y0, min(x0, x1)] += sgn * b
            else: vuse[min(y0, y1), x0] += sgn * b
    links = p['links']; paths = {}; failed = []
    order = sorted(range(len(links)), key=lambda k: -links[k]['b'] * (abs(terms[links[k]['i']][0][0] - terms[links[k]['i']][1][0]) + abs(terms[links[k]['i']][0][1] - terms[links[k]['i']][1][1])))
    for it in range(a.iter):
        for n, k in enumerate(order):
            l = links[k]
            if k in paths: use(paths[k], l['b'], -1)
            q, err = route(*terms[l['i']], l['b'])
            if q is None:
                if it == 0: failed.append(dict(link=l['i'], reason=err))
                paths.pop(k, None); continue
            paths[k] = q; use(q, l['b'], +1)
        ho = np.maximum(0, huse / hcap - 1); vo = np.maximum(0, vuse / vcap - 1)
        hhis += HIST * ho; vhis += HIST * vo
        print('ITER', it, 'overflow_edges', int((ho > 0).sum() + (vo > 0).sum()), 'max_ratio', round(float(max((huse / hcap).max(), (vuse / vcap).max())), 3),
              'wirelength_bit_mm', round(sum(links[k]['b'] * sum(abs(xs[a[0]] - xs[b[0]]) + abs(ys[a[1]] - ys[b[1]]) for a, b in zip(q, q[1:])) for k, q in paths.items()) / 1000), flush=True)
    stations = []; channels = []
    for k, l in enumerate(links):
        if k not in paths: continue
        q = [(xs[x], ys[y]) for x, y in paths[k]]
        pts = [tuple(l['e'][0][2:4])] + q + [tuple(l['e'][1][2:4])]; clean = []
        for q0 in pts:
            if clean and q0 == clean[-1]: continue
            if len(clean) > 1 and ((clean[-2][0] == clean[-1][0] == q0[0]) or (clean[-2][1] == clean[-1][1] == q0[1])): clean[-1] = q0
            else: clean.append(q0)
        legs = []; length = 0.; corners = []
        for u, v in zip(clean, clean[1:]):
            ll = abs(v[0] - u[0]) + abs(v[1] - u[1]); legs.append((length, length + ll, u, v)); length += ll; corners.append(length)
        n = max(1, math.ceil(length / 350.)); cuts = []
        for kk in range(1, n):
            t = kk * length / n
            for c in corners[:-1]:
                if abs(t - c) < 50: t = c - 50 if t <= c else c + 50
            cuts.append(t)

        def at(t):
            for lo, hi, u, v in legs:
                if t <= hi + 1e-5:
                    z = 0 if hi == lo else (t - lo) / (hi - lo); return [u[0] + (v[0] - u[0]) * z, u[1] + (v[1] - u[1]) * z]
            return list(clean[-1])
        sp = [at(t) for t in cuts]; marks = sorted(set([0., length] + corners + cuts)); hops = []
        for lo, hi in zip(marks, marks[1:]): hops.append([*at(lo), *at(hi), l['b']])
        l.update(h=hops, sp=sp, s=len(sp), L=round(length, 3)); stations += sp
        for u, v in zip(clean[1:-1], clean[2:-1]): channels.append([min(u[0], v[0]) - 16.2, min(u[1], v[1]) - 16.2, max(u[0], v[0]) + 16.2, max(u[1], v[1]) + 16.2])
    ho = huse / hcap; vo = vuse / vcap
    p['facts']['physical72'].update(routing='CONSTRUCTION_FAILED' if failed else 'CONSTRUCTED_PENDING_REAL_PIN_PROJECTION_AND_SOURCE_GEN',
                                    routing_failures=failed, grid=[nx, ny], relay_station_count=len(stations),
                                    router=dict(tool='dv_route72c.py', lattice_um=LAT, cap_bits_per_um=round(CAP_BPU, 2), iterations=a.iter,
                                                overflow_edges=int((ho > 1).sum() + (vo > 1).sum()), max_edge_ratio=round(float(max(ho.max(), vo.max())), 3)),
                                    relay_cell_packing='PENDING exact master bodies/station collision legalization; no fictitious cell-site claim')
    p['facts']['physical72']['package_ports'] = dict(placement_model='package bumps over/along actual existing interior PMA pin faces; no outer-shoreline path assumed', source_ports='retain all existing PMA external connections; actual kit/view pin manifest owed')
    p['facts'].update(relays=len(stations), bit_mm=sum(l.get('L', 0) * l['b'] for l in links) / 1000, relay_channels_seed=channels)
    Path(a.out).write_text(json.dumps(p, indent=1)); print('ROUTE_DONE failed', len(failed), 'stations', len(stations), flush=True)


if __name__ == '__main__':
    main()
