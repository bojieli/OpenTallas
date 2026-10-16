#!/usr/bin/env python3
"""GLOBAL-FP-S option C (S81 33x26 reticle kept): measured road-demand levers on the SA requested-homes replay.

Base model = Codex RP replay (920444f4e results/arch/s81_globalfp_1015/road_repair/rp_requested_SA_homes_replay.json.gz,
'RP_replanned_BFx2_broadcast'): all GEN18c pass0 non-return/non-broadcast source chains (plan chain_paths minus cr*/cx*)
+ 128 RP return lanes to the requested SA hr homes + replanned 566+538(+2 clk) broadcast tree.  Metric identical to
rp_road_replan.stats: every vertical path segment whose x lies in S14W / VCH / S14E (+ requested VCH 18457.2-19040.4)
contributes sum(lanes)+len(lanes) tracks over its y extent; joint peak vs CAP*0.60*(509.76+583.2+509.76).

Levers (each reported alone and combined; no lever changes a logical port, a lane width or a station's function):
  A  U-turn removal: inside one road, a path that runs down then back up (or up then down) is replaced by the monotone
     L through the same road (same entry and exit points, same road).  Pure re-route; stages can only drop.
  B  Link stacks follow the collective: the 8 die-edge link macros (lk_W0..3 / lk_E0..3, UCIe + 3 SerDes per side)
     shift up by DY along their own die edge (same order, same 43.2-um gaps, same pin offsets); the 16 K lanes (512 b +
     1 forwarded clock, collective <-> link) are re-routed: W = collective W face -> S14W -> canonical Roadmap streets
     -> column-0 lane -> edge strip -> link pin; E = collective E face -> VCH north to the free passage above sp_hc_s
     (y 22,762..23,654: stations only, 99 b today) -> S14E -> Roadmap streets -> column-21 lane -> link pin.
  Stage cost: ceil(manhattan / 500 um) per lane vs the source station count (negative = fewer stages).
Screen only: Manhattan centre-lines, no native pin / PG / CTS / station legality claim.
"""
import argparse, ast, gzip, hashlib, heapq, json, math, subprocess, types
from pathlib import Path

CAP = 5484.375 / 260
OLD = {'S14W': (13428.72, 13938.48), 'VCH': (15670.8, 17312.4), 'S14E': (19044.72, 19554.48)}
WIDTH = {'S14W': 509.76, 'VCH': 583.2, 'S14E': 509.76}
BUDGET = CAP * 0.60 * sum(WIDTH.values())
VCH_NEW = (18457.2, 19040.4)
TOP_PASS_Y = 23200.0          # free passage above sp_hc_s (top 22,762.1) and below bk_collector (23,654.2)
VCH_K_X = 16286.77            # source KE VCH sub-lane x (KE0t)
REACH = 500.0


def road_of(x):
    for n, (a, b) in OLD.items():
        if a - 1e-6 <= x <= b + 1e-6:
            return n
    if VCH_NEW[0] <= x <= VCH_NEW[1]:
        return 'VCH'
    return None


def plen(path):
    return sum(abs(u[0] - v[0]) + abs(u[1] - v[1]) for u, v in zip(path, path[1:]))


def segments(chains):
    ss = []
    for c in chains:
        bits = sum(c['lanes']) + len(c['lanes'])
        for u, v in zip(c['path'], c['path'][1:]):
            if abs(u[0] - v[0]) > 1e-6 or abs(u[1] - v[1]) < 1e-9:
                continue
            n = road_of(u[0])
            if n:
                ss.append((n, min(u[1], v[1]), max(u[1], v[1]), bits, c['chain']))
    return ss


def stats(chains, topn=12):
    ss = segments(chains)
    ev = {}
    for n, lo, hi, b, _ in ss:
        ev.setdefault(lo, []).append((n, b)); ev.setdefault(hi, []).append((n, -b))
    cur = {n: 0 for n in WIDTH}; best = (0, None, None); per = {n: (0, None) for n in WIDTH}
    for y in sorted(ev):
        for n, b in ev[y]:
            cur[n] += b
        t = sum(cur.values())
        if t > best[0]:
            best = (t, y, dict(cur))
        for n in WIDTH:
            if cur[n] > per[n][0]:
                per[n] = (cur[n], y)
    y = best[1]
    act = {}
    for n, lo, hi, b, ch in ss:
        if lo <= y < hi:
            act[ch] = act.get(ch, 0) + b
    cls = {}
    for ch, b in act.items():
        k = ('return' if ch.startswith(('RP_', 'cr')) else 'bcast' if ch.startswith(('BC_', 'cx')) else 'K_link'
             if ch[0] == 'K' else 'hub_hb' if ch.startswith('hb') else 'ctrl' if ch[:1] in 'cds' and ch[1:2].isdigit()
             else 'service')
        cls[k] = cls.get(k, 0) + b
    return dict(joint_peak_tracks=best[0], y_um=round(y, 3), by_road=best[2], budget_tracks=round(BUDGET, 3),
                margin_tracks=round(BUDGET - best[0], 1), ideal_share=round(best[0] / CAP / sum(WIDTH.values()), 4),
                joint_cut_pass=best[0] <= BUDGET,
                per_road_peak={n: dict(tracks=per[n][0], y_um=round(per[n][1], 1), share=round(per[n][0] / (CAP * WIDTH[n]), 4))
                               for n in WIDTH},
                by_class_at_peak=dict(sorted(cls.items(), key=lambda kv: -kv[1])),
                top_chains_at_peak=sorted(act.items(), key=lambda kv: -kv[1])[:topn])


def band_of(x):
    """Physical x band for lever A runs (the two VCH x bands are separate channels: a run never jumps between them)."""
    r = road_of(x)
    return ('VCH_NEW' if r == 'VCH' and VCH_NEW[0] <= x <= VCH_NEW[1] else r)


def uturn_free(path):
    """Lever A: collapse every maximal in-road run to a monotone L (vertical at the run's first x, then the exit jog)."""
    out = [list(path[0])]; i = 0; n = len(path)
    while i < n - 1:
        r = band_of(path[i][0])
        j = i
        if r:
            while j + 1 < n and band_of(path[j + 1][0]) == r:
                j += 1
        if r and j - i >= 2:
            s, e = path[i], path[j]
            ys = [p[1] for p in path[i:j + 1]]
            mono = all(b >= a for a, b in zip(ys, ys[1:])) or all(b <= a for a, b in zip(ys, ys[1:]))
            if not mono:
                for q in ([s[0], e[1]], list(e)):
                    if q != out[-1]:
                        out.append(q)
                i = j
                continue
        out.append(list(path[i + 1])); i += 1
    return out


def bcast_trunks(chains, street_band=None):
    """Lever D: a broadcast tree carries ONE word; where its edges overlap inside one road band (parallel S14W
    copies at x 13547.5 / 13599.6, the hx spine running up past the entry and the edge running back down) or inside
    one field street (parallel horizontal edges of the same tree in the same street), they become one shared trunk
    with taps.  Per side: union of vertical extents per road band and of horizontal extents per street band.
    Every frame's path from hx can only get shorter (calendar re-derived, stages <= 0)."""
    out = []; trunks = {}
    for c in chains:
        if not c['chain'].startswith('BC_'):
            out.append(c); continue
        side = c['chain'][3]
        for u, v in zip(c['path'], c['path'][1:]):
            if abs(u[0] - v[0]) < 1e-6 and band_of(u[0]) and abs(u[1] - v[1]) > 1e-9:
                trunks.setdefault((side, 'V', band_of(u[0])), []).append((min(u[1], v[1]), max(u[1], v[1]), u[0], c['lanes']))
            elif abs(u[1] - v[1]) < 1e-6 and street_band and street_band(u[1]) and abs(u[0] - v[0]) > 1e-9:
                trunks.setdefault((side, 'H', street_band(u[1])), []).append((min(u[0], v[0]), max(u[0], v[0]), u[1], c['lanes']))
            else:
                out.append(dict(chain=c['chain'] + '_s', lanes=c['lanes'], path=[u, v]))
    for (side, o, b), iv in trunks.items():
        iv.sort(); cur = None; k = 0
        def emit(cur, k):
            lo, hi, z, lanes = cur
            path = [[z, lo], [z, hi]] if o == 'V' else [[lo, z], [hi, z]]
            out.append(dict(chain=f'BC_{side}_trunk{o}_{b}_{k}', lanes=lanes, path=path))
        for lo, hi, z, lanes in iv:
            if cur and lo <= cur[1] + 1e-6:
                cur[1] = max(cur[1], hi)
            else:
                if cur:
                    emit(cur, k); k += 1
                cur = [lo, hi, z, lanes]
        emit(cur, k)
    return out


def return_tdm(chains, band='S14W', pairs=8):
    """Lever C: static 2:1 time-division of return lanes in one road.  Two RP lanes of the SAME tree (same hr sink) that
    run together in the band share one 70-b(+1 clk) lane from the point where the second joins: serializer slot at the
    join (odd/even edges, compiler-assigned), deserializer at the hr input.  Modelled as the in-band union of the two
    lanes' vertical extents.  Chooses the pairs with the largest overlap at the band's own peak first."""
    rp = {c['chain']: c for c in chains if c['chain'].startswith('RP_')}
    def vseg(c):
        return [(min(u[1], v[1]), max(u[1], v[1]), u[0]) for u, v in zip(c['path'], c['path'][1:])
                if abs(u[0] - v[0]) < 1e-6 and band_of(u[0]) == band and abs(u[1] - v[1]) > 1e-9]
    peak = road_split(chains)[band]['y_um']
    live = [n for n, c in rp.items() if any(lo <= peak < hi for lo, hi, _ in vseg(c))]
    bytree = {}
    for n in live:
        bytree.setdefault(n.split('_')[1], []).append(n)
    cand = []
    for t, ns in bytree.items():
        ns.sort(key=lambda n: -sum(hi - lo for lo, hi, _ in vseg(rp[n])))
        for a, b in zip(ns[0::2], ns[1::2]):
            ov = sum(max(0, min(h1, h2) - max(l1, l2)) for l1, h1, _ in vseg(rp[a]) for l2, h2, _ in vseg(rp[b]))
            cand.append((ov, a, b))
    cand.sort(reverse=True); chosen = cand[:pairs]; out = []; drop = set()
    for ov, a, b in chosen:
        sa, sb = vseg(rp[a]), vseg(rp[b])
        rest = []
        for lo, hi, x in sb:                      # b's in-band extent outside a's extent stays (before the join)
            cuts = [(lo, hi)]
            for l2, h2, _ in sa:
                cuts = [piece for c0, c1 in cuts for piece in ((c0, min(c1, l2)), (max(c0, h2), c1)) if piece[1] - piece[0] > 1e-6]
            rest += [(c0, c1, x) for c0, c1 in cuts]
        drop.add(b)
        out.append(dict(chain=b + '_tdm', lanes=[70], path=[]))
        out += [dict(chain=f'{b}_pre{i}', lanes=[70], path=[[x, lo], [x, hi]]) for i, (lo, hi, x) in enumerate(rest)]
        out += [dict(chain=f'{b}_h{i}', lanes=[70], path=[u, v]) for i, (u, v) in enumerate(zip(rp[b]['path'], rp[b]['path'][1:]))
                if not (abs(u[0] - v[0]) < 1e-6 and band_of(u[0]) == band)]
    return [c for c in chains if c['chain'] not in drop] + [c for c in out if c['path']], [dict(a=a, b=b, overlap_um=round(ov, 1)) for ov, a, b in chosen]


def road_split(chains):
    """Per physical band peak share (the two VCH bands separately, each at its own width)."""
    wid = dict(WIDTH, VCH=OLD['VCH'][1] - OLD['VCH'][0], VCH_NEW=VCH_NEW[1] - VCH_NEW[0])
    segs = {}
    for c in chains:
        bits = sum(c['lanes']) + len(c['lanes'])
        for u, v in zip(c['path'], c['path'][1:]):
            b = band_of(u[0]) if abs(u[0] - v[0]) < 1e-6 else None
            if b and abs(u[1] - v[1]) > 1e-9:
                segs.setdefault(b, []).append((min(u[1], v[1]), max(u[1], v[1]), bits, c['chain']))
    out = {}
    for b, ss in segs.items():
        ev = {}
        for lo, hi, bits, _ in ss:
            ev[lo] = ev.get(lo, 0) + bits; ev[hi] = ev.get(hi, 0) - bits
        cur = 0; best = (0, 0)
        for y in sorted(ev):
            cur += ev[y]
            if cur > best[0]:
                best = (cur, y)
        top = {}
        for lo, hi, bits, ch in ss:
            if lo <= best[1] < hi:
                top[ch] = top.get(ch, 0) + bits
        out[b] = dict(tracks=best[0], y_um=round(best[1], 1), width_um=round(wid[b], 2),
                      share_own_width=round(best[0] / (CAP * wid[b]), 4),
                      share_SA_width=round(best[0] / (CAP * WIDTH['VCH' if b.startswith('VCH') else b]), 4),
                      top=sorted(top.items(), key=lambda kv: -kv[1])[:10])
    return out


def roadmap(plan):
    cp = 'results/physical/die_iter_1012/s81/canonical_gen_1015/capacity_service_gap_broad_reroot_E.json'
    cb = subprocess.check_output(['git', 'show', 'eb9cfa044:' + cp])
    assert hashlib.sha256(cb).hexdigest() == plan['variant']['canonical_layout']['sha256']
    code = subprocess.check_output(['git', 'show', 'eb9cfa044:tools/s81/canonical_layout.py']).decode()
    node = next(x for x in ast.parse(code).body if isinstance(x, ast.ClassDef) and x.name == 'Roadmap')
    ns = {'heapq': heapq}; exec(compile(ast.Module(body=[node], type_ignores=[]), '<Roadmap eb9cfa044>', 'exec'), ns)
    G = types.SimpleNamespace(COL_W8=1182.816, RSC_W=47.52, s14_x=lambda m, side, tag: 13500.55 if side == 'W' else 19116.55,
                              stn_dims=lambda lanes, horiz: (54.84, 17.256))
    frames = {int(k): v for k, v in plan['frames'].items()}
    road = ns['Roadmap'](G, {'frames': frames, 'canonical_layout': json.loads(cb)}, {}, return_lanes=True)
    for side in 'WE':
        es = sorted(road.entry[side], key=lambda q: q[1])
        for u, v in zip(es, es[1:]):
            road.add(u, v)
    rsc = set(road.sx.values())
    for u, edges in road.graph.items():          # as rp_road_replan: prefer streets over RSC verticals
        for v, w in list(edges.items()):
            if u[0] == v[0] and u[0] in rsc:
                edges[v] = 2 * w
    return road, hashlib.sha256(code.encode()).hexdigest()


def dijkstra(road, src, targets, weight=None):
    """targets: {node: terminal cost}.  weight(u, v, w) may inflate an edge (street congestion)."""
    dist = {src: 0}; prev = {src: None}; q = [(0, src)]; best = (1e30, None)
    while q:
        d, u = heapq.heappop(q)
        if d != dist[u] or d >= best[0]:
            continue
        if u in targets and d + targets[u] < best[0]:
            best = (d + targets[u], u)
        for v, w in road.graph.get(u, {}).items():
            w = weight(u, v, w) if weight else w
            if d + w < dist.get(v, 1e30):
                dist[v] = d + w; prev[v] = u; heapq.heappush(q, (d + w, v))
    if best[1] is None:
        raise RuntimeError('unreachable')
    out = []; u = best[1]
    while u is not None:
        out.append(list(u)); u = prev[u]
    return out[::-1]


class Streets:
    """Congestion book for lever B routing: horizontal field-street load (bits) per frame street band and x bucket
    (between Roadmap RSC lanes) + vertical S14W/S14E road load per 50-um y bin.  Capacities at 0.60."""
    BIN = 50.0
    def __init__(self, plan, road, chains):
        self.bands = sorted({(f['street'][1], f['street'][3]) for f in plan['frames'].values()})
        self.xs = sorted(road.sx.values()) + [33000.0]
        self.load = {}; self.vload = {}; self.hist = {}
        for c in chains:
            self.add(c)
    def band(self, y):
        return next((b for b in self.bands if b[0] - 1 <= y <= b[1] + 1), None)
    def buckets(self, x0, x1):
        lo, hi = min(x0, x1), max(x0, x1)
        return [i for i, (a, b) in enumerate(zip([0.0] + self.xs, self.xs))
                if b > lo + 1e-6 and a < hi - 1e-6 and not (a < 13942.8 and b > 19040.4)]   # hub interior is not a field street
    def bins(self, y0, y1):
        return range(int(min(y0, y1) / self.BIN), int(math.ceil(max(y0, y1) / self.BIN)))
    def add(self, c, sign=1):
        bits = sum(c['lanes']) + len(c['lanes'])
        for u, v in zip(c['path'], c['path'][1:]):
            if abs(u[1] - v[1]) < 1e-6 and abs(u[0] - v[0]) > 1e-6:
                b = self.band(u[1])
                if b:
                    for i in self.buckets(u[0], v[0]):
                        self.load[(b, i)] = self.load.get((b, i), 0) + sign * bits
            elif abs(u[0] - v[0]) < 1e-6 and band_of(u[0]) in ('S14W', 'S14E'):
                for k in self.bins(u[1], v[1]):
                    key = (band_of(u[0]), k); self.vload[key] = self.vload.get(key, 0) + sign * bits
    def cap(self, b):
        return CAP * (b[1] - b[0]) * 0.60
    def vcap(self, r):
        return CAP * WIDTH[r] * 0.60
    def keys(self, u, v):
        if abs(u[1] - v[1]) < 1e-6 and abs(u[0] - v[0]) > 1e-6:
            b = self.band(u[1])
            return [('h', (b, i), self.load.get((b, i), 0), self.cap(b)) for i in self.buckets(u[0], v[0])] if b else []
        if abs(u[0] - v[0]) < 1e-6 and band_of(u[0]) in ('S14W', 'S14E'):
            r = band_of(u[0])
            return [('v', (r, k), self.vload.get((r, k), 0), self.vcap(r)) for k in self.bins(u[1], v[1])]
        return []
    def weight(self, bits):
        def f(u, v, w):
            ks = self.keys(u, v)
            if not ks:
                return w
            over = max(max(0.0, (ld + bits) / cp - 1.0) for _, _, ld, cp in ks)
            hist = max(self.hist.get((t, k), 0.0) for t, k, _, _ in ks)
            return w * (1.0 + 50.0 * over + hist)
        return f
    def bump_history(self):
        for (b, i), ld in self.load.items():
            if ld > self.cap(b):
                self.hist[('h', (b, i))] = self.hist.get(('h', (b, i)), 0) + 1.0
        for (r, k), ld in self.vload.items():
            if ld > self.vcap(r):
                self.hist[('v', (r, k))] = self.hist.get(('v', (r, k)), 0) + 1.0
    def worst(self):
        return max(((v / (CAP * (b[1] - b[0])), b, i) for (b, i), v in self.load.items()), default=(0, None, None))


def clean(path):
    out = []
    for p in path:
        p = [round(p[0], 3), round(p[1], 3)]
        if not out or p != out[-1]:
            out.append(p)
    return out


def k_paths(plan, road, dy, streets=None, rounds=4):
    """Lever B: K lanes after shifting the link stacks by dy (die edge, same order/gaps/pin offsets)."""
    insts = {i[0]: i for i in plan['insts']}
    src = {c['chain']: c for c in plan['chain_paths'] if c['chain'][0] == 'K' and c['chain'][1] in 'WE' and len(c['chain']) == 4}
    x_sx = sorted(road.sx.values()); col0, col21 = x_sx[0], x_sx[-1]
    out = []; rows = []
    for name, c in sorted(src.items()):
        side, idx, d = name[1], int(name[2]), name[3]
        lk = insts[f'lk_{side}{idx}']
        p0, p1 = c['path'][0], c['path'][-1]
        coll_end, link_end = (p0, p1) if d == 't' else (p1, p0)
        yl = link_end[1] + dy; xl = link_end[0]
        assert lk[3] - 1 <= link_end[1] <= lk[3] + lk[5] + 1, (name, link_end, lk[:6])
        assert 279 <= lk[3] + dy and lk[3] + lk[5] + dy <= 26000 - 279, ('link stack leaves the die edge', name, dy)
        yc = coll_end[1]
        if side == 'W':
            ex = road.entry['W'][0][0]
            es = sorted(road.entry['W'], key=lambda q: q[1])
            near = min(es, key=lambda q: abs(q[1] - yc))
            head = [coll_end, [ex, yc], list(near)]
            tgt = {n: 3 * abs(n[1] - yl) for n in road.graph if abs(n[0] - col0) < 1e-6}
            mid = dijkstra(road, near, tgt, streets.weight(513) if streets else None)
            tail = [[304.344, mid[-1][1]], [304.344, yl], [xl, yl]]
        else:
            ex = road.entry['E'][0][0]
            es = sorted(road.entry['E'], key=lambda q: q[1])
            top = es[-1]
            head = [coll_end, [VCH_K_X, yc], [VCH_K_X, TOP_PASS_Y], [ex, TOP_PASS_Y], list(top)]
            tgt = {n: 3 * abs(n[1] - yl) for n in road.graph if abs(n[0] - col21) < 1e-6}
            mid = dijkstra(road, top, tgt, streets.weight(513) if streets else None)
            tail = [[32695.704, mid[-1][1]], [32695.704, yl], [xl, yl]]
        path = clean(head + mid + tail)
        if d == 'r':
            path = path[::-1]
        old_st = len(c.get('stations', [])); new_st = math.ceil(plen(path) / REACH)
        edge_stub = abs(yl - mid[-1][1])
        rows.append(dict(chain=name, old_len_um=round(plen(c['path'])), new_len_um=round(plen(path)), old_stations=old_st,
                         new_stations_at500=new_st, delta_stages=new_st - old_st, edge_strip_stub_um=round(edge_stub, 1),
                         street_y=round(mid[-1][1], 1)))
        out.append(dict(chain=name, lanes=c['lanes'], path=path))
        if streets:
            streets.add(out[-1])
    return out, rows


def k_paths_negotiated(plan, road, dy, streets, rounds=4):
    """PathFinder-style: route all 16 K lanes, then rip up and reroute each against present loads + history."""
    out, rows = k_paths(plan, road, dy, streets)
    for _ in range(rounds):
        streets.bump_history()
        for c in out:
            streets.add(c, -1)
        out2, rows2 = [], []
        for c in out:
            o, r = k_paths_one(plan, road, dy, streets, c['chain'])
            out2.append(o); rows2.append(r)
        out, rows = out2, rows2
    return out, rows


def k_paths_one(plan, road, dy, streets, name):
    src = {c['chain']: c for c in plan['chain_paths'] if c['chain'] == name}
    sub = dict(plan); sub['chain_paths'] = list(src.values())
    o, r = k_paths(sub, road, dy, streets)
    return o[0], r[0]


def reroute_returns(chains, road, streets, rounds=5, limit=0.60):
    """Lever E: W-half RP return lanes that ride an over-0.60 field-street bucket are ripped up and re-routed on the
    canonical Roadmap from their own column root to any S14W entry, against street + S14W congestion (negotiated),
    then down/up S14W to their hr home (same sink, same tree, same lane).  Stage delta reported per lane."""
    W_ex = road.entry['W'][0][0]; ents = {tuple(n): 0.0 for n in road.entry['W']}
    by = {c['chain']: i for i, c in enumerate(chains)}
    def hot(c):
        bits = sum(c['lanes']) + len(c['lanes'])
        for u, v in zip(c['path'], c['path'][1:]):
            for t, k, ld, cp in streets.keys(u, v):
                if t == 'h' and ld > cp / 0.60 * limit:
                    return True
        return False
    moved = {}
    for _ in range(rounds):
        cand = [c for c in chains if c['chain'].startswith('RP_W') and hot(c)]
        if not cand:
            break
        for c in cand:
            root = int(c['chain'].split('_cf')[1]); src = road.rootnode[(root, 'r')]
            gx, gy = c['path'][-1]
            streets.add(c, -1)
            mid = dijkstra(road, tuple(src), ents, streets.weight(71))
            new = clean(c['path'][:c['path'].index(list(src)) + 1 if list(src) in c['path'] else 2] + mid + [[W_ex, gy], [gx, gy]])
            new = uturn_free(new)
            nc = dict(c, path=new); streets.add(nc)
            old = moved.get(c['chain'], c['path'])
            moved[c['chain']] = old
            chains[by[c['chain']]] = nc
        streets.bump_history()
    rows = [dict(chain=n, old_len_um=round(plen(p0)), new_len_um=round(plen(chains[by[n]]['path'])),
                 delta_stages_at500=math.ceil(plen(chains[by[n]]['path']) / REACH) - math.ceil(plen(p0) / REACH)) for n, p0 in moved.items()]
    return chains, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default='/home/ubuntu/geometry-s81-gen17/g18c/construction_pass0_plan.json.gz')
    ap.add_argument('--replay', required=True)
    ap.add_argument('--dy', type=float, nargs='*', default=[0, 2000, 4000])
    ap.add_argument('--pick', type=float, default=2000, help='dy of the delivered candidate (must be in --dy)')
    ap.add_argument('--pairs', type=int, default=12, help='lever C pairs in the delivered candidate')
    ap.add_argument('--homes', help='write the delivered homes/roads file (JSON) here')
    ap.add_argument('--scan', type=float, default=0, help='also scan dy 0..8500 at this step (A+B), report the frontier')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    plan = json.load(gzip.open(a.plan)); rp = json.load(gzip.open(a.replay))
    svc = [dict(chain=c['chain'], lanes=c['lanes'] if isinstance(c['lanes'], list) else json.loads(c['lanes']),
                path=c['path'] if isinstance(c['path'], list) else json.loads(c['path']))
           for c in plan['chain_paths'] if not c['chain'].startswith(('cr', 'cx'))]
    base = svc + rp['replanned_return_chains'] + rp['replanned_BFx2_broadcast_chains']
    res = dict(scope='SCREEN_SOURCE_CANONICAL_GRAPH_NO_PHYSICAL_ADMISSION', plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
               replay_sha256=hashlib.sha256(Path(a.replay).read_bytes()).hexdigest(), replay_commit='920444f4e',
               script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), cap_tracks_per_um=CAP,
               road_widths_um=WIDTH, budget_tracks_at060=round(BUDGET, 3))
    res['baseline'] = stats(base)
    assert res['baseline']['joint_peak_tracks'] == rp['RP_replanned_BFx2_broadcast']['peak_bits'], res['baseline']['joint_peak_tracks']
    A = [dict(c, path=uturn_free(c['path'])) for c in base]
    changed = [c['chain'] for c, o in zip(A, base) if c['path'] != o['path']]
    res['A_uturn'] = dict(stats(A), chains_changed=len(changed), changed=changed[:60],
                          length_saved_um=round(sum(plen(o['path']) - plen(c['path']) for c, o in zip(A, base)), 1))
    road, rsha = roadmap(plan); res['roadmap_source_sha256'] = rsha
    sb = Streets(plan, road, [])
    AD = bcast_trunks(A, sb.band)
    res['A_D'] = dict(stats(AD), bands=road_split(AD), field_street_worst=dict(zip(('share', 'band', 'bucket'), Streets(plan, road, AD).worst())),
                      field_street_worst_base=dict(zip(('share', 'band', 'bucket'), Streets(plan, road, base).worst())))
    res['B'] = {}; res['A_plus_B'] = {}
    for dy in a.dy:
        st0 = Streets(plan, road, [c for c in AD if c['chain'][0] != 'K'])
        stb = Streets(plan, road, base)
        try:
            kp, rows = k_paths_negotiated(plan, road, dy, st0)
        except AssertionError as e:
            res['B'][str(dy)] = dict(infeasible=str(e)); continue
        kmap = {c['chain']: c for c in kp}
        B = [kmap.get(c['chain'], c) for c in base]
        AB = [dict(kmap[c['chain']], path=uturn_free(kmap[c['chain']]['path'])) if c['chain'] in kmap else c for c in A]
        summ = dict(link_shift_um=dy, k_lanes=rows, k_delta_stages_total=sum(r['delta_stages'] for r in rows),
                    k_delta_stages_max=max(r['delta_stages'] for r in rows),
                    worst_edge_strip_stub_um=max(r['edge_strip_stub_um'] for r in rows),
                    field_street_worst_share_after=dict(zip(('share', 'band', 'bucket'), st0.worst())),
                    field_street_worst_share_baseline=dict(zip(('share', 'band', 'bucket'), stb.worst())))
        res['B'][str(dy)] = dict(stats(B), **summ)
        res['A_plus_B'][str(dy)] = dict(stats(AB), **{k: v for k, v in summ.items() if k != 'k_lanes'})
        res['A_plus_B'][str(dy)]['k_paths'] = [dict(chain=c['chain'], path=c['path']) for c in AB if c['chain'] in kmap]
        ABD = [dict(kmap[c['chain']], path=uturn_free(kmap[c['chain']]['path'])) if c['chain'] in kmap else c for c in AD]
        res.setdefault('A_B_D', {})[str(dy)] = dict(stats(ABD), bands=road_split(ABD), field_street_worst=dict(zip(('share', 'band', 'bucket'), Streets(plan, road, ABD).worst())), **{k: v for k, v in summ.items() if k != 'k_lanes'})
        stE = Streets(plan, road, ABD)
        ABDE, erows = reroute_returns([dict(c) for c in ABD], road, stE)
        res.setdefault('A_B_D_E', {})[str(dy)] = dict(stats(ABDE), bands=road_split(ABDE), field_street_worst=dict(zip(('share', 'band', 'bucket'), Streets(plan, road, ABDE).worst())),
                                                     rerouted_returns=erows)
        for npair in (4, 8, 12, 24):
            ABDEC, chosen = return_tdm(ABDE, 'S14W', npair)
            res.setdefault('A_B_D_E_C', {}).setdefault(str(dy), {})[str(npair)] = dict(stats(ABDEC), bands=road_split(ABDEC), pairs=chosen,
                field_street_worst=dict(zip(('share', 'band', 'bucket'), Streets(plan, road, ABDEC).worst())))
            ABDC, chosen = return_tdm(ABD, 'S14W', npair)
            res.setdefault('A_B_D_C', {}).setdefault(str(dy), {})[str(npair)] = dict(stats(ABDC), bands=road_split(ABDC), pairs=chosen)
    if a.homes:
        dy = a.pick; insts = {i[0]: i for i in plan['insts']}
        st0 = Streets(plan, road, [c for c in AD if c['chain'][0] != 'K'])
        kp, krows = k_paths_negotiated(plan, road, dy, st0); kmap = {c['chain']: c for c in kp}
        ABD = [dict(kmap[c['chain']], path=uturn_free(kmap[c['chain']]['path'])) if c['chain'] in kmap else c for c in AD]
        ABDE, erows = reroute_returns([dict(c) for c in ABD], road, Streets(plan, road, ABD))
        fin, pairs = return_tdm(ABDE, 'S14W', a.pairs)
        emap = {c['chain']: c for c in ABDE}
        homes = dict(
            candidate=f'OPTC-1 (A+B dy={dy}+D+E+C{a.pairs})', scope=res['scope'], base='Codex RP SA requested-homes replay 920444f4e + GEN18c pass0 plan',
            result=dict(stats(fin), bands=road_split(fin), field_street_worst=dict(zip(('share', 'band', 'bucket'), Streets(plan, road, fin).worst()))),
            links=[dict(inst=n, master=insts[n][1], xywh=[insts[n][2], round(insts[n][3] + dy, 3), insts[n][4], insts[n][5]], orient=insts[n][6],
                        old_y=insts[n][3], rule='same die edge, same order and 43.2-um gaps; whole W and E stacks shift by dy (mirrored UCIe neighbours stay aligned)')
                   for n in sorted(insts) if n.startswith('lk_')] +
                  [dict(inst=n, master=insts[n][1], xywh=[insts[n][2], round(insts[n][3] + dy, 3), insts[n][4], insts[n][5]], old_y=insts[n][3]) for n in sorted(insts) if n.startswith('kc_K')],
            k_lanes=[dict(r, path=emap[r['chain']]['path']) for r in krows],
            uturn_rule='generator road compaction: a lane never runs back along the road it is in (monotone in-road runs); 64 chains change in the base model',
            broadcast_rule='one shared trunk per side per road band and per field street; taps at streets; per-frame broadcast stages re-derived (each <= today)',
            rerouted_returns=[dict(r, path=emap[r['chain']]['path']) for r in erows],
            return_tdm_pairs=pairs,
            return_tdm_rule='2:1 static slot sharing (odd/even edges, compiler-assigned) from the join point to the hr input; serializer at the join, deserializer at hr; +2 fixed stages on each paired path',
            open=['native pin rectangles, station legality, PG/CTS footprints not modelled (centre-line screen)',
                  'hub-internal hb VM<->collective/pq/wfc/gather lanes are GEN18c paths in the old VCH x band (9,926 tracks = 0.287 of that 1,641-um band, 0.807 if squeezed into the SA 583-um VCH): they belong to the SA hub re-plan with the A2 VM reservation',
                  'edge-strip stubs at the link faces up to ~2.2 mm (today 2.5 mm): pin-face plan for lk_* with S-NET',
                  'return TDM burst skid needs the S-FUNC per-root emission calendar'])
        Path(a.homes).write_text(json.dumps(homes, indent=1))
        print('HOMES', homes['candidate'], homes['result']['joint_peak_tracks'], {b: v['share_own_width'] for b, v in homes['result']['bands'].items()}, round(homes['result']['field_street_worst']['share'], 3))
    if a.scan:
        base_stub = 0.0
        for c in plan['chain_paths']:
            if c['chain'][0] == 'K':
                pa = c['path']; e = pa[-1] if c['chain'][3] == 't' else pa[0]; f = pa[-2] if c['chain'][3] == 't' else pa[1]
                g = pa[-3] if c['chain'][3] == 't' else pa[2]
                base_stub = max(base_stub, abs(f[1] - g[1]) if abs(f[0] - g[0]) < 1e-6 else 0)
        frontier = []; dy = 0.0
        while dy <= 8500:
            sts = Streets(plan, road, [c for c in AD if c['chain'][0] != 'K'])
            try:
                kp, rows = k_paths_negotiated(plan, road, dy, sts)
            except AssertionError:
                break
            kmap = {c['chain']: c for c in kp}
            AB = [dict(kmap[c['chain']], path=uturn_free(kmap[c['chain']]['path'])) if c['chain'] in kmap else c for c in AD]
            st = stats(AB)
            frontier.append(dict(dy=round(dy, 1), joint=st['joint_peak_tracks'], y=st['y_um'], shares={n: v['share'] for n, v in st['per_road_peak'].items()},
                                 stub=max(r['edge_strip_stub_um'] for r in rows), dstages=sum(r['delta_stages'] for r in rows),
                                 street=round(sts.worst()[0], 3), worst_lane_dstage=max(r['delta_stages'] for r in rows)))
            dy += a.scan
        res['scan'] = dict(baseline_worst_edge_stub_um=round(base_stub, 1), rows=frontier)
    Path(a.out).write_bytes(gzip.compress(json.dumps(res, indent=1).encode(), mtime=0) if a.out.endswith('.gz') else json.dumps(res, indent=1).encode())
    pr = lambda s: (s['joint_peak_tracks'], s['y_um'], s['margin_tracks'], {n: v['share'] for n, v in s['per_road_peak'].items()})
    print('baseline', pr(res['baseline']))
    print('A', pr(res['A_uturn']), res['A_uturn']['chains_changed'])
    print('A+D', pr(res['A_D']), 'street', res['A_D']['field_street_worst_base']['share'], '->', res['A_D']['field_street_worst']['share'])
    for dy in a.dy:
        b = res['B'][str(dy)]
        if 'infeasible' in b:
            print('B', dy, b); continue
        print('B', dy, pr(b), b['k_delta_stages_total'], b['worst_edge_strip_stub_um'], 'street', b['field_street_worst_share_baseline']['share'], '->', b['field_street_worst_share_after']['share'])
        ab = res['A_plus_B'][str(dy)]; print('A+B', dy, pr(ab), ab['by_class_at_peak'])
        abd = res['A_B_D'][str(dy)]; print('A+B+D', dy, pr(abd), 'street', round(abd['field_street_worst']['share'], 3), {b: (v['tracks'], v['share_own_width'], v['share_SA_width']) for b, v in abd['bands'].items()})
        e = res['A_B_D_E'][str(dy)]
        print('A+B+D+E', dy, pr(e), 'street', round(e['field_street_worst']['share'], 3), {b: (v['tracks'], v['share_own_width']) for b, v in e['bands'].items()},
              'moved', len(e['rerouted_returns']), 'dstages', sum(r['delta_stages_at500'] for r in e['rerouted_returns']))
        for npair, v in res['A_B_D_E_C'][str(dy)].items():
            print('  +E+C', npair, v['joint_peak_tracks'], 'street', round(v['field_street_worst']['share'], 3), {b: (w['tracks'], w['share_own_width']) for b, w in v['bands'].items()})
        for npair, v in res['A_B_D_C'][str(dy)].items():
            print('  +C', npair, v['joint_peak_tracks'], {b: (w['tracks'], w['share_own_width']) for b, w in v['bands'].items()})


if __name__ == '__main__':
    main()
