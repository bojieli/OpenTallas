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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('--stations', '--pins', '--contract', '--manifest', '--out'):
        ap.add_argument(k, required=True)
    ap.add_argument('--plan-um', type=float, default=380.0)
    ap.add_argument('--report')
    ap.add_argument('--grid', type=float, default=10.0)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--root-keepouts', help='DIE-CLOCK root sites (keepout boxes are station-free)')
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
                    hp = _ROUTER.nearest_free(tuple(r['pins']['sinks'][s_]))
                    pads.append(dict(sink=s_, stages=dmax - depth[i], x=round(hp[0], 1), y=round(hp[1], 1)))
        r['pads'] = pads; r['hop_violations'] = rv; viol += [(h, r['driver'], w) for h, w in rv]
        r['replanned'] = dict(plan_um=PLAN, old_stations=old)
        delta[len(sl) - old] += 1; rep['replanned'] += 1
        rows.append(r)
    st = dict(st, rows=rows, lanes=dict(tool='tools/hbm_die_v16/relay_lanes_d4f.py', plan_um=PLAN, grid_um=a.grid,
              pins=a.pins, placement=a.manifest, stats=dict(rep), depth_delta=dict(sorted(delta.items()))),
              hop_violations=len(viol), route=dict(model='relay_router obstacle-aware on current pins (relay_lanes_d4f)', grid_um=a.grid))
    Path(a.out).write_text(json.dumps(st) + '\n')
    out = dict(stats=dict(rep), depth_delta_hist=dict(sorted(delta.items())), hop_violations=len(viol),
               worst_violations=sorted(viol)[-20:],
               stations_before=sum(len(r['stations']) for r in load(a.stations)['rows']),
               stations_after=sum(len(r['stations']) for r in st['rows']))
    if a.report:
        Path(a.report).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'worst_violations'}))


if __name__ == '__main__':
    main()
