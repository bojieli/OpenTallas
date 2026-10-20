#!/usr/bin/env python3
"""H-RELAY 1017 (coordinator 0dg+3, S81-DV lane model on the HBM die): station list -> LANE station list.

run8 measured 6.0 M die nets over the 405 um reach, 99.97 % relay -> relay hops, because the 61.9 k forwarded-clock relay
tiles landed far from their planned homes (median 279 um, p90 1.9 mm).  Three causes, all fixed here + in
relay_layer_d4f.py --lanes + die_case_v16.py (lane rows):
  1. every tile of a station had the SAME home point (T tiles of one bus -> one spot; the free-area spiral scattered
     them; a 48-lane fork station = up to 23 tiles on one point);
  2. sink-root stages were homed at the sink instance CENTRE (inside a mm-sized block: median 1,247 um displaced);
  3. station homes were planned on an older case's pins (run6 rows remapped): 482 / 1,107 p2p chains had
     driver pin -> first station > 405 um on the run8 pins.
This pass (geometry only, no netlist) RE-PLANS every row that has current pins, exactly as die_relay_stations.py
--route-grid does on a case (same Prim tree over the sink pin centroids, same relay_router obstacle-aware Dijkstra and
greedy farthest-free-cell stations, same p2p / equal_age_pad / cfg_no_pad classes and pads), but:
  * pins = the CURRENT case's block pin centroids (case_pin_centroids.py: driver ports of the row, sink ports the
    contract edges feed from them), never relay-to-relay nets (the case already holds relays);
  * stations every PLAN um of routed length (default 380 < 405: 25 um legalisation slack per hop);
  * every row carries pins {driver: [x, y], sinks: {sink: [x, y]}} for the layer (sink-root stage home = sink pin).
Rows without pins (instance not in the case, e.g. renamed by a later layer) keep their listed stations.
Lane rows (the S81-DV station form): the layer turns each station into ONE row of T lane tiles abutted across the
channel at a FIXED site (die_case_v16 places the row as a unit, never tile by tile), one forwarded clock per lane.
    relay_lanes_d4f.py --stations S.json --pins PINS.json.gz --contract C.json.gz --manifest M.json --out L.json
                       [--plan-um 380] [--report REP.json]
"""
import argparse, collections, gzip, json, math, re
from pathlib import Path
import numpy as np

CELL = 10.0


def load(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def flow(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) >= abs(dy):
        return 'WE' if dx > 0 else 'EW'
    return 'SN' if dy > 0 else 'NS'


def rectilinear(pts):
    """L-expand a point list into axis-parallel pieces (x first), dropping zero-length pieces"""
    out = [pts[0]]
    for p in pts[1:]:
        q = out[-1]
        if q[0] != p[0] and q[1] != p[1]:
            out.append((p[0], q[1]))
        if out[-1] != p:
            out.append(p)
    return out


def walk(poly):
    seg, acc = [], 0.0
    for a, b in zip(poly, poly[1:]):
        L = md(a, b); seg.append((acc, a, b, L)); acc += L
    return seg, acc


def at(seg, t):
    for s0, a, b, L in seg:
        if t <= s0 + L or (s0, a, b, L) == seg[-1]:
            f = 0.0 if L == 0 else min(1.0, max(0.0, (t - s0) / L))
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), flow(a, b)
    return seg[-1][2], flow(seg[-1][1], seg[-1][2])


_ROUTER = None


def _job(arg):
    import relay_router as RR
    (bi, P_, par, W, sinks), plan = arg
    return bi, RR.plan_bus(_ROUTER, P_, par, plan, W, sinks)


# ---------------- HBM-DIE9 10-20: capacity-aware station siting (--capacity) ----------------
# r7 S7 (HBM-DIE8): relay_router sites each station in ONE free 10 um cell with no footprint, so up to 31 rows shared a
# site and 572 um windows held 1.17x the free area.  With --capacity the stations are sited SEQUENTIALLY (widest rows
# first) against a per-bin AREA budget: bin capacity = free cells x G^2 x util; a station row of T lane tiles of side s(W)
# (the GEN --relay-outline density sizes: 48 -> 10.8, 136 -> 11.7, 624 -> ~25 um) x halo consumes its area from the bins
# within +-radius of its site; a cell is a legal station site only when that window still holds the row.  Routes
# (Dijkstra on the passable grid) are unchanged and computed in parallel; only the siting is sequential.


def tile_um(W):
    """SYNTH die lane/relay tile side under die_case_v16 --relay-outline density (pins <= 6/um, 10.8 floor, never above
    the old floor rule, which is pin-bound grown for wide tiles)"""
    bits = 2 * W + 8
    new = max(10.8, bits / 24.0)
    old = max(21.6, bits * 0.048 * 1.5 / 0.9 / 4.0)
    return min(new, old)


class Capacity:
    def __init__(self, router, util, bin_um, radius):
        from scipy import ndimage
        self.R = router; G = router.G
        self.k = max(1, int(round(bin_um / G))); self.r = radius
        nbx, nby = -(-router.nx // self.k), -(-router.ny // self.k)
        fr = np.zeros((nbx * self.k, nby * self.k)); fr[:router.nx, :router.ny] = router.free
        self.cap0 = fr.reshape(nbx, self.k, nby, self.k).sum(axis=(1, 3)) * G * G * util
        self.cap = self.cap0.copy()
        w = 2 * radius + 1
        self.win = ndimage.uniform_filter(self.cap, size=w, mode='constant') * w * w
        self.used = np.zeros_like(self.cap); self.forced = 0

    def bin_of(self, cells):
        return cells[:, 0] // self.k, cells[:, 1] // self.k

    def ok_cells(self, xy, fp):
        bx, by = xy[:, 0] // self.k, xy[:, 1] // self.k
        return self.R.free[xy[:, 0], xy[:, 1]] & (self.win[bx, by] >= fp)

    def consume(self, cx, cy, fp, forced=False):
        bx, by = cx // self.k, cy // self.k; r = self.r; nbx, nby = self.cap.shape
        left = fp
        order = sorted(((abs(i), abs(j), i, j) for i in range(-r, r + 1) for j in range(-r, r + 1)))
        for _, _, i, j in order:
            x, y = bx + i, by + j
            if 0 <= x < nbx and 0 <= y < nby and self.cap[x, y] > 0 and left > 0:
                d = min(self.cap[x, y], left); self._dec(x, y, d); left -= d
        if left > 1e-6:                      # forced (violation) station: book the rest on its own bin (may go negative)
            self._dec(bx, by, left); self.forced += 1

    def _dec(self, x, y, d):
        r = self.r
        self.cap[x, y] -= d; self.used[x, y] += d
        self.win[max(0, x - r):x + r + 1, max(0, y - r):y + r + 1] -= d


def _route_job(arg):
    bi, P_, par = arg
    R_ = _ROUTER; out = {}
    for v in range(1, len(P_)):
        u = par[v]
        path = R_.route(P_[u], P_[v])
        _, sa = R_.node(P_[u]); _, sb = R_.node(P_[v])
        out[v] = (np.asarray(path, dtype=np.int64), sa, sb)
    return bi, out


def plan_bus_cap(router, cap, P, par, R, W, sinks, paths, fp):
    """relay_router.plan_bus with capacity: same tree, same routes, same greedy farthest-legal-cell rule, but a legal
    cell = free AND its window still holds this station row (fp um2).  A hop that cannot meet R takes the next legal
    cell (violation, as before)."""
    G = router.G
    kids = {}
    for v in range(1, len(P)):
        kids.setdefault(par[v], []).append(v)
    order, q = [], [0]
    while q:
        u = q.pop(0)
        for v in kids.get(u, []):
            order.append(v); q.append(v)
    sl, viol = [], []
    state = {0: (None, 0.0, 0, P[0])}

    def cxy(path):
        xy = np.empty((len(path), 2), dtype=np.int64)
        pos = path >= 0
        xy[pos] = router.cell[path[pos]]
        neg = -1 - path[~pos]
        xy[~pos, 0], xy[~pos, 1] = neg // router.ny, neg % router.ny
        return xy

    def put(xy, i, prev, dep, ppt, run):
        x, y = int(xy[i, 0]), int(xy[i, 1]); pt = ((x + 0.5) * G, (y + 0.5) * G)
        sl.append(dict(id=len(sl), depth=dep + 1, x=round(pt[0], 1), y=round(pt[1], 1), toward=None,
                       master=f'hbfd_rly_{W}_{flow(ppt, pt)}', parent=prev, pt=pt, hop_um=round(run, 1)))
        return sl[-1]['id'], dep + 1, pt

    for v in order:
        u = par[v]
        prev, run, dep, ppt = state[u]
        path, snap_a, snap_b = paths[v]
        xy = cxy(path); n = len(path)
        run += snap_a
        s = 0; base = run                     # run at path index i (i > s) = base + G * (i - s)
        okv = cap.ok_cells(xy, fp)
        i = 1 if n > 1 else n
        while i < n:
            lim = max(s, s + int(math.floor((R - base) / G + 1e-9)))   # last index with run <= R
            if lim >= n - 1:
                break
            seg = np.flatnonzero(okv[max(i, s + 1):lim + 1]) + max(i, s + 1)
            if len(seg):
                ci = int(seg[-1])
                if not cap.ok_cells(xy[ci:ci + 1], fp)[0]:
                    okv = cap.ok_cells(xy, fp); continue
                crun = base + G * (ci - s)
                prev, dep, ppt = put(xy, ci, prev, dep, ppt, crun)
                cap.consume(int(xy[ci, 0]), int(xy[ci, 1]), fp)
                okv = cap.ok_cells(xy, fp)
                s, base, i = ci, 0.0, ci + 1
                continue
            nxt = np.flatnonzero(okv[lim + 1:]) + lim + 1
            if not len(nxt):                   # no legal cell to the end: free cell ignoring capacity, else end-of-path
                fr = np.flatnonzero(router.free[xy[lim + 1:, 0], xy[lim + 1:, 1]]) + lim + 1
                if not len(fr):
                    viol.append((round(base + G * (n - 1 - s), 1), f'toward sink {v - 1} (end of path)'))
                    s, base, i = n - 1, base + G * (n - 1 - s), n
                    break
                j = int(fr[0]); forced = True
            else:
                j = int(nxt[0]); forced = False
            jr = base + G * (j - s)
            viol.append((round(jr, 1), f'station depth {dep + 1}' + (' (capacity forced)' if forced else '')))
            prev, dep, ppt = put(xy, j, prev, dep, ppt, jr)
            cap.consume(int(xy[j, 0]), int(xy[j, 1]), fp, forced=forced)
            okv = cap.ok_cells(xy, fp)
            s, base, i = j, 0.0, j + 1
        run = base + G * (n - 1 - s) if n > 1 else base
        run += snap_b
        if run > R + 1e-6:
            viol.append((round(run, 1), f'last hop into sink {v - 1}'))
        state[v] = (prev, run, dep, ppt)
    owner = {}
    for v in order:
        sid = state[v][0]
        while sid is not None and sid not in owner:
            owner[sid] = sinks[v - 1]
            sid = sl[sid]['parent']
    for s_ in sl:
        s_['toward'] = owner.get(s_['id'], sinks[0])
    tail = {v: state[v][0] for v in state}
    depth = [state[v][2] for v in range(1, len(P))]
    return sl, tail, depth, viol


def nearest_cap(router, cap, p, fp):
    G = router.G; fc = router._free_cells
    d = np.abs(fc[:, 0] - int(p[0] // G)) + np.abs(fc[:, 1] - int(p[1] // G))
    for k in np.argsort(d, kind='stable')[:20000]:
        if cap.ok_cells(fc[k:k + 1], fp)[0]:
            return fc[k], False
    return fc[int(np.argmin(d))], True


def window_report(router, cap, win_um=572.0):
    """per window: demand (booked station area) vs capacity (free area x util) -- the r7 S7 capacity metric"""
    k = max(1, int(round(win_um / (router.G * cap.k))))
    nbx, nby = cap.cap0.shape; out = []
    for x in range(0, nbx, k):
        for y in range(0, nby, k):
            c0 = cap.cap0[x:x + k, y:y + k].sum(); u = cap.used[x:x + k, y:y + k].sum()
            if u > 0:
                out.append((round(u / c0, 3) if c0 > 0 else float('inf'), [round(x * cap.k * router.G), round(y * cap.k * router.G)],
                            round(u), round(c0)))
    out.sort(key=lambda t: -t[0])
    return dict(window_um=round(k * cap.k * router.G, 1), windows=len(out), over_1=sum(1 for t in out if t[0] > 1.0 + 1e-6),
                worst=out[:25])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('--stations', '--pins', '--contract', '--manifest', '--out'):
        ap.add_argument(k, required=True)
    ap.add_argument('--plan-um', type=float, default=380.0)
    ap.add_argument('--report')
    ap.add_argument('--grid', type=float, default=10.0)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--root-keepouts', help='DIE-CLOCK root sites (keepout boxes are station-free)')
    ap.add_argument('--capacity', action='store_true', help='HBM-DIE9: capacity-aware sequential station siting (area budget per bin)')
    ap.add_argument('--cap-util', type=float, default=0.5, help='HBM-DIE9: share of free area lane rows may book (rest: forest, repeaters, clock, homes)')
    ap.add_argument('--cap-bin-um', type=float, default=50.0)
    ap.add_argument('--cap-radius', type=int, default=2, help='bins each side a station row may spread over (GEN slides rows <= 150 um)')
    ap.add_argument('--cap-halo', type=float, default=1.2, help='row footprint factor over the bare tile area (legalisation)')
    a = ap.parse_args()
    st = load(a.stations); P = load(a.pins)['instances']; c = load(a.contract); man = load(a.manifest)
    R = st['reach_um']; PLAN = a.plan_um
    W, H = man['die_um']
    occ = np.zeros((int(H / CELL) + 2, int(W / CELL) + 2), bool)
    for n, v in man['placement'].items():
        if v.get('m', v.get('master', '')).startswith('hbfd_rly'):
            continue
        occ[int(v['y'] / CELL):int(math.ceil((v['y'] + v['h']) / CELL)), int(v['x'] / CELL):int(math.ceil((v['x'] + v['w']) / CELL))] = True
    free = lambda p: 0 <= p[0] < W and 0 <= p[1] < H and not occ[int(p[1] / CELL), int(p[0] / CELL)]
    # sink ports fed by each driver port (contract edges)
    sport = collections.defaultdict(set)
    for e in c['edges']:
        sport[(e['source'][0], e['source'][1], e['sink'][0])].add(e['sink'][1])

    def pc(inst, ports):
        d = P.get(inst, {}); xs = [d[p] for p in ports if p in d]
        if not xs:
            return None
        n = sum(x[2] for x in xs)
        return (sum(x[0] * x[2] for x in xs) / n, sum(x[1] * x[2] for x in xs) / n)
    import sys as _s
    _s.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hbm_die_v15'))
    import relay_router as RR, die_relay_stations as DS
    keep = [s_['keepout'] for s_ in load(a.root_keepouts)['sites']] if a.root_keepouts else None
    global _ROUTER
    _ROUTER = RR.Router(man['placement'], man['die_um'], R, G=a.grid, carved=man.get('carved_feedthrough'), keepouts=keep)
    rep = collections.Counter(); delta = collections.Counter(); jobs = {}
    for bi, r in enumerate(st['rows']):
        di, ports = r['driver'].split('.', 1); ports = ports.split('+')
        dp = pc(di, ports)
        sp = {s_: pc(s_, {q for p in ports for q in sport.get((di, p, s_), ())}) for s_ in r['sinks']}
        r['pins'] = dict(driver=dp and [round(dp[0], 1), round(dp[1], 1)], sinks={k: v and [round(v[0], 1), round(v[1], 1)] for k, v in sp.items()})
        if dp is None or any(v is None for v in sp.values()):
            rep['kept_no_pins'] += 1; continue
        P_, par, dist = DS.tree(dp, [sp[s_] for s_ in r['sinks']])
        jobs[bi] = (bi, P_, par, 48 if r['bits'] <= 48 else 624, list(r['sinks']))
    import multiprocessing as mp
    cap = None
    if a.capacity:
        with mp.get_context('fork').Pool(a.jobs) as pool:
            routes = dict(pool.imap_unordered(_route_job, [(bi, j[1], j[2]) for bi, j in jobs.items()], chunksize=4))
        cap = Capacity(_ROUTER, a.cap_util, a.cap_bin_um, a.cap_radius)
        fps = {}
        for bi, j in jobs.items():
            r = st['rows'][bi]; Wd = j[3]
            T = (r['stations'][0].get('tiles') if r['stations'] else None) or math.ceil(r['bits'] / Wd)
            fps[bi] = T * tile_um(Wd) ** 2 * a.cap_halo
        kept = 0
        for bi, r in enumerate(st['rows']):          # rows kept without current pins: their listed stations book first
            if bi in jobs:
                continue
            for x in r['stations']:
                Wd = 48 if r['bits'] <= 48 else 624
                fp = (x.get('tiles') or math.ceil(r['bits'] / Wd)) * tile_um(Wd) ** 2 * a.cap_halo
                cx = min(_ROUTER.nx - 1, max(0, int(x['x'] // _ROUTER.G))); cy = min(_ROUTER.ny - 1, max(0, int(x['y'] // _ROUTER.G)))
                cap.consume(cx, cy, fp); kept += 1
        print('CAPACITY kept-row stations booked', kept, 'forced', cap.forced, flush=True)
        res = {}
        for bi in sorted(jobs, key=lambda b: -fps[b]):
            _, P_, par, Wd, sinks = jobs[bi]
            res[bi] = plan_bus_cap(_ROUTER, cap, P_, par, PLAN, Wd, sinks, routes[bi], fps[bi])
        print('CAPACITY sited', len(res), 'buses; forced', cap.forced, flush=True)
    else:
        with mp.get_context('fork').Pool(a.jobs) as pool:
            res = dict(pool.imap_unordered(_job, [(j, PLAN) for j in jobs.values()], chunksize=4))
    rows = []
    viol = []
    for bi, r in enumerate(st['rows']):
        r = dict(r)
        if bi not in res:
            rows.append(r); continue
        sl, tail, depth, rv = res[bi]
        old = len(r['stations']); dmax = max(depth) if depth else 0
        if dmax == 0:
            rep['now_within_plan'] += 1; continue
        cls = r['cls']
        T = r['stations'][0].get('tiles') if r['stations'] else None
        r['stations'] = [dict(depth=x['depth'], x=x['x'], y=x['y'], toward=x['toward'], master=x['master'], tiles=T,
                              parent=x['parent'], hop_um=x['hop_um']) for x in sl]
        r['sink_depths'] = depth; r['depth'] = dmax
        pads = []
        if cls == 'equal_age_pad':
            for i, s_ in enumerate(r['sinks']):
                if depth[i] < dmax:
                    if cap is not None:
                        fpp = (T or 1) * tile_um(48 if r['bits'] <= 48 else 624) ** 2 * a.cap_halo * (dmax - depth[i])
                        c_, forced = nearest_cap(_ROUTER, cap, tuple(r['pins']['sinks'][s_]), fpp)
                        cap.consume(int(c_[0]), int(c_[1]), fpp, forced=forced)
                        hp = ((c_[0] + 0.5) * _ROUTER.G, (c_[1] + 0.5) * _ROUTER.G)
                    else:
                        hp = _ROUTER.nearest_free(tuple(r['pins']['sinks'][s_]))
                    pads.append(dict(sink=s_, stages=dmax - depth[i], x=round(hp[0], 1), y=round(hp[1], 1)))
        r['pads'] = pads; r['hop_violations'] = rv; viol += [(h, r['driver'], w) for h, w in rv]
        r['replanned'] = dict(plan_um=PLAN, old_stations=old)
        delta[len(sl) - old] += 1; rep['replanned'] += 1
        rows.append(r)
    st = dict(st, rows=rows, lanes=dict(tool='tools/hbm_die_v16/relay_lanes_d4f.py', plan_um=PLAN, grid_um=a.grid,
              pins=a.pins, placement=a.manifest, stats=dict(rep), depth_delta=dict(sorted(delta.items()))),
              hop_violations=len(viol), route=dict(model='relay_router obstacle-aware on current pins (relay_lanes_d4f)', grid_um=a.grid))
    if cap is not None:
        st['lanes']['capacity'] = dict(util=a.cap_util, bin_um=a.cap_bin_um, radius=a.cap_radius, halo=a.cap_halo,
                                       forced=cap.forced, windows=window_report(_ROUTER, cap))
    Path(a.out).write_text(json.dumps(st) + '\n')
    out = dict(stats=dict(rep), depth_delta_hist=dict(sorted(delta.items())), hop_violations=len(viol),
               capacity=st['lanes'].get('capacity'),
               worst_violations=sorted(viol)[-20:],
               stations_before=sum(len(r['stations']) for r in load(a.stations)['rows']),
               stations_after=sum(len(r['stations']) for r in st['rows']))
    if a.report:
        Path(a.report).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'worst_violations'}))


if __name__ == '__main__':
    main()
