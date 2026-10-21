#!/usr/bin/env python3
"""S81 head die H1 land plan (S81-HEAD / HD-CHAIN, 10-21) in the G7 land-plan row format (release72/mk_land_plan_g7.py).

One row per routed link that carries >= 1 relay station (every such lane ends in a dsfd_dvland tile in dv_bind: all head
input ports are land rules).  region_crossing marks the links that cross clock regions (region = dv_bind.region_of: the
block group for cl* groups, the SerDes 'edge' group = one region); in-region rows are the stationed chain U-turns.
0-station links have no landing tile in dv_bind (as G7); the cross-region ones (abutted neighbours) are listed in
zero_station_crossings, not as rows.
Model (G7 MODEL row, fit of the p4l3 die-STA rows; die STA re-derives): F = ceil(0.47 N) (N = routed stations),
E = max(2, F + 1).  Multi-lane bundles (<stem>_l<i> into one receiver) read at ONE age ceil(N/2) + K + 1:
K = E + (bundle age - lane age) (S81-LBGAP/G8).  Tile: dsfd_dvland_<W> (D 4, K <= 7) when K <= 7, else dsfd_dvland_276l
(D 8, K <= 63) for 276-b lanes.  A non-276 lane with K > 7 has no closed tile: FAIL (no K 1 placeholder is ever emitted).
Usage: hd_land_plan.py ROUTED_PLAN OUT"""
import collections, json, math, re, sys

LAND_W = (70, 276, 512, 562, 682)


def region(b, pitch):
    g = b['group']
    return g if g.startswith('cl') else f"{g}{int((b['x'] + b['w'] / 2) // pitch)}"


def main():
    routed, out = sys.argv[1:3]
    p = json.load(open(routed)); B = p['blocks']; pitch = p['facts']['cluster_pitch_um']
    rows, zero, bad = [], [], []
    for l in p['links']:
        a, b = B[l['e'][0][0]], B[l['e'][1][0]]
        nm = l['i'].replace('-', '_'); N = l.get('s', 0)
        cross = region(a, pitch) != region(b, pitch)
        if N == 0:
            if cross:
                zero.append(dict(link=nm, src=a['name'], dst=b['name'], bits=l['b']))
            continue
        F = math.ceil(0.47 * N); E = max(2, F + 1)
        m = re.fullmatch(r'(.+)_l(\d+)', nm)
        rows.append(dict(link=nm, cls=l['c'], src=a['name'], dst=b['name'], bits=l['b'], stages=N,
                         s1={'tt': None, 'ff': None}, h0={'tt': None, 'ff': None}, E=E, K=E,
                         src_region=region(a, pitch), dst_region=region(b, pitch), region_crossing=cross,
                         K_source=f'H1 MODEL (HD-CHAIN): F = ceil(0.47 x {N} stations) = {F}, K = E = F + 1; die STA re-derives',
                         window_ok=None, model=True, _bundle=(m.group(1), b['name']) if m else None))
    g = collections.defaultdict(list)
    for r in rows:
        if r['_bundle']:
            g[r['_bundle']].append(r)
    for (stem, dst), rs in g.items():
        if len(rs) < 2:
            continue
        age = {r['link']: math.ceil(r['stages'] / 2) + r['E'] + 1 for r in rs}
        A = max(age.values())
        for r in rs:
            r['K'] = r['E'] + A - age[r['link']]
            r['bundle'] = f'{stem}->{dst}'; r['lane_age_E'] = age[r['link']]; r['bundle_age'] = A
            if r['K'] != r['E']:
                r['K_source'] += f'; S81-LBGAP/G8 bundle age: K = E + ({A} - {age[r["link"]]})'
    for r in rows:
        r.pop('_bundle')
        if r['K'] <= 7 and r['bits'] in LAND_W:
            r['D'], r['master'] = 4, f"dsfd_dvland_{r['bits']}"
        elif r['bits'] == 276 and r['K'] <= 63:
            r['D'], r['master'] = 8, 'dsfd_dvland_276l'
        else:
            bad.append(dict(link=r['link'], bits=r['bits'], stages=r['stages'], K=r['K']))
    d = dict(schema='opentallas.s81_dv.land_plan.v1', T_ps=833.333, D=4, corners=['tt', 'ff'],
             rule='HD-CHAIN H1 MODEL rows (G7 model): F = ceil(0.47 N), K = E = max(2, F + 1), bundle-age equalised; die STA re-derives',
             source_plan=routed, links=rows, zero_station_crossings=zero,
             summary=dict(rows=len(rows), by_master=dict(collections.Counter(r.get('master') for r in rows)),
                          zero_station_crossings=len(zero), no_tile=bad, bundles=len([k for k, v in g.items() if len(v) > 1])))
    json.dump(d, open(out, 'w'), indent=1)
    print('HD_LAND_PLAN', json.dumps(d['summary']))
    if bad:
        raise SystemExit(f'hd_land_plan: {len(bad)} landed lanes need K > 7 on a width without a long closed tile: {bad[:6]}')


if __name__ == '__main__':
    main()
