#!/usr/bin/env python3
"""DIE-CLOCK: instance -> clock region map for a compact plan + root sites (root_sites.py output).

  region_map.py --plan compact.P.json --sites root_sites.json --out region_map.json [--touch-um 200]

Rules (the same map is used by the clock builder, the reset forest and the relay layer):
- Hardened column clusters own a site of the same name (sm_<q><i>), and the instance maps to it.
- Every other instance maps to the NEAREST non-cluster site (Manhattan distance from the instance centre to the site).
  Ties are broken by the site order in the file.
- Neighbour regions = region pairs with any two member instances whose outlines come within --touch-um of each other.
  This is where a bus can cross without a long relay chain. Communicating pairs are judged later by die_clock_check on
  the real netlist; this list only seeds the build's neighbour constraints.
Output: {"instances": {inst: {"region", "site": [x, y]}}, "regions": {region: {"site", "members"}}, "neighbours": [[a, b]]}
"""
import argparse, json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--sites', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--touch-um', type=float, default=200.0)
    a = ap.parse_args()
    P = json.load(open(a.plan))
    S = json.load(open(a.sites))['sites']
    by_name = {s['region']: s for s in S}
    free = [s for s in S if s['region'] not in P]
    inst = {}
    for k, v in P.items():
        cx, cy = v['x'] + v['w'] / 2, v['y'] + v['h'] / 2
        if k in by_name:
            s = by_name[k]
        else:
            s = min(free, key=lambda s_: abs(s_['x'] - cx) + abs(s_['y'] - cy))
        inst[k] = dict(region=s['region'], site=[s['x'], s['y']])
    regions = {}
    for k, r in inst.items():
        regions.setdefault(r['region'], dict(site=r['site'], members=[]))['members'].append(k)
    nb = set()
    items = list(P.items())
    T = a.touch_um
    for i in range(len(items)):
        ki, vi = items[i]
        for j in range(i + 1, len(items)):
            kj, vj = items[j]
            ri, rj = inst[ki]['region'], inst[kj]['region']
            if ri == rj:
                continue
            gx = max(vi['x'], vj['x']) - min(vi['x'] + vi['w'], vj['x'] + vj['w'])
            gy = max(vi['y'], vj['y']) - min(vi['y'] + vi['h'], vj['y'] + vj['h'])
            if max(gx, gy) <= T:
                nb.add(tuple(sorted((ri, rj))))
    json.dump(dict(schema='opentallas.die_clock.region_map.v1', plan=a.plan, sites=a.sites,
                   rule='cluster -> own site; else nearest non-cluster site (Manhattan, centre); neighbours = outlines within '
                        f'{T} um', instances=inst, regions=regions, neighbours=sorted([list(x) for x in nb])),
              open(a.out, 'w'), indent=1)
    print(len(inst), 'instances', len(regions), 'regions', len(nb), 'neighbour pairs')


if __name__ == '__main__':
    main()
