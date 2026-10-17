#!/usr/bin/env python3
"""Per-bus relay station list for a FROZEN die placement (H-DIE 2026-10-16, coordinator relay rule; consumer: H-ELEM /
H-NETLIST contract insertion, DIE-CLOCK station clock sinks).

    die_relay_stations.py CASE_DIR --contract C.json [--reach 450] --out stations.json

A bus = the nets of one (driver instance, driver port) -> (sink instance set, sink port) family; every bit of a bus
gets the same stations.  Route: driver-pin centroid -> rectilinear Prim tree over the sink-pin centroids (one point
per sink instance); stations every REACH of tree distance from the driver (station k = depth k), branch points of a
multicast tree flagged (H-ELEM relay4 node).  Classes:
  p2p              one sink instance: depth = ceil(L / REACH) - 1
  equal_age_pad    data multicast: every sink sees the deepest depth; near sinks get pad stations at their pins
  cfg_no_pad       host configuration fan-out (host_static_ingress cfg_*/desc_*): addressed writes, no pads
Station master: <= 48 b -> hbfd_rly_48 x ceil(bits/48); else hbfd_rly_624 x ceil(bits/624) (the native-PASS widths);
the flow letter (EW/WE/NS/SN) follows the hop direction.  Clock domain = the driver's (manifest clock_entry_map).
Geometry only: station points are route positions; die_case places each tile at the nearest legal free area
('planned relay home' rule), which may lengthen a hop -- re-run die_relay_pass on the resulting case to verify.
"""
import argparse, collections, json, math, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_relay_pass as RP  # noqa: E402

CFG = re.compile(r'ot_hbm_host_static_ingress\.(cfg_|desc_)')


def tree(root, pts):
    """Prim tree from root over pts (Manhattan); returns parent index list and tree distance per point (root = 0)."""
    P = [root] + pts; n = len(P)
    par = [-1] * n; best = [math.inf] * n; dist = [0.0] * n; done = [False] * n; best[0] = 0.0
    for _ in range(n):
        u = min((i for i in range(n) if not done[i]), key=lambda i: best[i]); done[u] = True
        if par[u] >= 0:
            dist[u] = dist[par[u]] + RP.md(P[par[u]], P[u])
        for v in range(n):
            if not done[v]:
                d = RP.md(P[u], P[v])
                if d < best[v]:
                    best[v] = d; par[v] = u
    return P, par, dist


def along(a, b, t):
    """point at Manhattan distance t from a toward b along an x-then-y L route"""
    dx = b[0] - a[0]
    if t <= abs(dx):
        return (a[0] + math.copysign(t, dx), a[1])
    t -= abs(dx); dy = b[1] - a[1]
    return (b[0], a[1] + math.copysign(min(t, abs(dy)), dy))


def flow(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) >= abs(dy):
        return 'WE' if dx >= 0 else 'EW'
    return 'SN' if dy >= 0 else 'NS'


_ROUTER = None


def bus_points(b):
    cen = lambda pts: (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return cen(b['dpts']), [cen(b['spts'][s]) for s in b['spts']]


def _plan_job(job):
    import relay_router as RR
    key, (root, spts), W, sinks = job
    P, par, dist = tree(root, spts)
    return key, RR.plan_bus(_ROUTER, P, par, _ROUTER.R, W, sinks)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('case'); ap.add_argument('--contract', required=True); ap.add_argument('--reach', type=float, default=450.0)
    ap.add_argument('--out', required=True)
    ap.add_argument('--clock-manifest', help='manifest with clock_entry_map (a --no-clock case has none: use the clocked case of the same netlist)')
    ap.add_argument('--route-grid', type=float, default=0.0,
                    help='>0: obstacle-aware routed stations on this grid (relay_router.py, d4b-r); 0: legacy L-route points')
    ap.add_argument('--jobs', type=int, default=1)
    a = ap.parse_args()
    c = Path(a.case); R = a.reach
    contract = json.loads(Path(a.contract).read_text())
    man = json.loads((c / 'manifest.json').read_text())
    dom_of = {}
    cm = json.loads(Path(a.clock_manifest).read_text()) if a.clock_manifest else man
    for dom, m in cm.get('clock_entry_map', {}).items():
        for inst in m:
            dom_of.setdefault(inst, dom)
    pl, nets, directions, top_inputs = RP.load_case(c, contract)
    buses = collections.defaultdict(lambda: dict(bits=0, dpts=[], spts=collections.defaultdict(list), nets=[]))
    for n, ends in nets.items():
        if n in top_inputs or len(ends) < 2:
            continue
        drv = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']
        lds = [e for e in ends if directions.get(e[:2]) == 'INPUT']
        if len(drv) != 1 or len(drv) + len(lds) != len(ends):
            continue
        d = drv[0]
        if max(RP.md(d[2], l[2]) for l in lds) <= R:
            continue
        # one bus per (driver instance, sink-instance set): every port of the same route shares the stations
        key = (d[0], tuple(sorted({l[0] for l in lds})))
        b = buses[key]; b['bits'] += 1; b['dpts'].append(d[2]); b['nets'].append(n); b.setdefault('ports', set()).add(RP.base(d[1]))
        for l in lds:
            b['spts'][l[0]].append(l[2])
    rows, tiles, skipped = [], collections.Counter(), collections.defaultdict(list)
    global _ROUTER
    routed = {}
    if a.route_grid > 0:
        import relay_router as RR
        _ROUTER = RR.Router(man['placement'], man['die_um'], R, G=a.route_grid)
        jobs = []
        for (di, sk), b in buses.items():
            if pl[di]['master'] == 'ot_hbm_su_programme' or any(re.match(r'(por_|rst|reset)', p_) for p_ in b['ports']):
                continue
            jobs.append(((di, sk), bus_points(b), 48 if b['bits'] <= 48 else 624, list(b['spts'])))
        import multiprocessing as mp
        with mp.get_context('fork').Pool(a.jobs) as pool:
            for key, res in pool.imap_unordered(_plan_job, jobs, chunksize=4):
                routed[key] = res
        viol = [(h, f'{k[0]} -> {len(k[1])} sinks: {w}') for k, r_ in routed.items() for h, w in r_[3]]
        print(f'routed {len(routed)} buses; hop violations {len(viol)}; worst {sorted(viol)[-5:] if viol else None}', flush=True)
    for (di, sk), b in sorted(buses.items(), key=lambda kv: -kv[1]['bits']):
        dp = '+'.join(sorted(b['ports']))
        root, spts = bus_points(b); sinks = list(b['spts'])
        P, par, dist = tree(root, spts)
        kids = collections.Counter(p for p in par if p >= 0)
        if a.route_grid > 0:
            if (di, sk) not in routed:
                depth = [max(0, math.ceil(dist[i] / R) - 1) for i in range(1, len(P))]
            else:
                rsl, rtail, depth, rviol = routed[(di, sk)]
        else:
            depth = [max(0, math.ceil(dist[i] / R) - 1) for i in range(1, len(P))]
        dmax = max(depth)
        if dmax == 0:
            continue
        fam = f"{pl[di]['master']}.{sorted(b['ports'])[0]}"
        if any(re.match(r'(por_|rst|reset)', p_) for p_ in b['ports']):
            skipped['reset_forest (reset relays/sync per region, not data stations)'].append(f"{di}.{dp} ({b['bits']} b, {len(sinks)} sinks)")
            continue
        if pl[di]['master'] == 'ot_hbm_su_programme':
            skipped['superseded: partitioned su_programme (H-SU b82db77f9, pslice slots 92282bfcb)'].append(f'{di}.{dp}')
            continue
        cls = 'p2p' if len(sinks) == 1 else ('cfg_no_pad' if CFG.match(fam) else 'equal_age_pad')
        bits = b['bits']
        master = (48, math.ceil(bits / 48)) if bits <= 48 else (624, math.ceil(bits / 624))
        stations = []
        if a.route_grid > 0:
            for st_ in rsl:
                stations.append(dict(depth=st_['depth'], x=st_['x'], y=st_['y'], toward=st_['toward'], master=st_['master'],
                                     tiles=master[1], parent=st_['parent'], hop_um=st_['hop_um']))
                tiles[f'hbfd_rly_{master[0]}'] += master[1]
        for v in (range(1, len(P)) if a.route_grid <= 0 else ()):
            u = par[v]; k0 = int(dist[u] // R) + 1; k1 = math.ceil(dist[v] / R) - 1
            for k in range(k0, k1 + 1):
                x, y = along(P[u], P[v], k * R - dist[u])
                stations.append(dict(depth=k, x=round(x, 1), y=round(y, 1), toward=sinks[v - 1],
                                     master=f'hbfd_rly_{master[0]}_{flow(P[u], P[v])}', tiles=master[1]))
                tiles[f'hbfd_rly_{master[0]}'] += master[1]
        branch = [dict(x=round(P[i][0], 1), y=round(P[i][1], 1)) for i, k in kids.items() if k > 1 and i > 0]
        pads = []
        if cls == 'equal_age_pad':
            for i, s in enumerate(sinks):
                if depth[i] < dmax:
                    hp = _ROUTER.nearest_free(spts[i]) if a.route_grid > 0 else spts[i]
                    pads.append(dict(sink=s, stages=dmax - depth[i], x=round(hp[0], 1), y=round(hp[1], 1)))
                    tiles[f'hbfd_rly_{master[0]}'] += (dmax - depth[i]) * master[1]
        rows.append(dict(driver=f'{di}.{dp}', driver_master=pl[di]['master'], bits=bits, cls=cls,
                         domain=dom_of.get(di, 'UNKNOWN'), depth=dmax, sinks=sinks,
                         sink_depths=depth, stations=stations, branch_points=branch, pads=pads,
                         hop_violations=(rviol if a.route_grid > 0 and (di, sk) in routed else []),
                         nets=b['nets'] if bits <= 4 else f"{len(b['nets'])} nets ({b['nets'][0]}..)"))
    res = dict(schema='opentallas.hbm.die_relay_stations.v1', case=str(c), reach_um=R,
               die_um=man['die_um'], placement_sha='see manifest input_sha256', buses=len(rows),
               bits_relayed=sum(r['bits'] for r in rows), station_tiles=dict(tiles),
               by_class=dict(collections.Counter(r['cls'] for r in rows)), not_relayed=dict(skipped),
               clock_rule='each station = a hardened hbfd_rly tile (clk entry pin); DIE-CLOCK balance_group per domain',
               qualification='GEOMETRY_ONLY route points; tiles legalised by die_case (planned relay home)',
               route=(dict(model='relay_router obstacle-aware (stations in free cells, wires may cross macros <= R/2-G deep)',
                           grid_um=a.route_grid) if a.route_grid > 0 else dict(model='legacy L route')),
               hop_violations=sum(len(r['hop_violations']) for r in rows), rows=rows)
    Path(a.out).write_text(json.dumps(res) + '\n')
    print(f"{len(rows)} buses, {res['bits_relayed']} bits, tiles {dict(tiles)}, classes {res['by_class']}")


if __name__ == '__main__':
    main()
