#!/usr/bin/env python3
"""Relay-home feasibility of the v5 lane plan inside wide blocks (H-DIE r3, 2026-10-15).

    relay_homes.py [--reach 480] [--out results/arch/hbm_die_v15/views_v5/relay_homes.json]

Every laned die link (compact660_v5 lanes2.json, band_lanes.py) runs pin -> lane -> pin as an L/Z route.  Relays sit
every <= REACH um along it.  Where a route segment crosses a block that is not one of its own ends for more than REACH,
a relay home must exist INSIDE that block (a feedthrough relay column/row the block reserves) -- otherwise the plan is
not buildable without moving the lane.  Reported per block kind: crossings, bits, longest crossing, and whether the v5
grant reserves a feedthrough (SU slices: 40 um column at w/2).  Crossings <= REACH need no inside home (relays land in
the channel on either side).
"""
import argparse, json, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'results/arch/hbm_die_v15/compact660_v5'
FEED = {'su': 'v5 grant: 40 um feedthrough relay column at x = w/2 (vertical through-traffic)'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reach', type=float, default=480.0)
    ap.add_argument('--lanes', default=str(D / 'lanes2.json'))
    ap.add_argument('--out', default=str(ROOT / 'results/arch/hbm_die_v15/views_v5/relay_homes.json'))
    a = ap.parse_args()
    pins = json.loads((D / 'pins/compact660_v5.pins.json').read_text())
    P = json.loads((D / 'compact.P.json').read_text()); lanes = json.loads(Path(a.lanes).read_text())
    ends = defaultdict(list)
    for b, v in pins['blocks'].items():
        for f, fx in v['faces'].items():
            for p in fx['pins']:
                ends[p['link']].append((b, p))
    kind = lambda b: re.match(r'([a-z]+)', b).group(1)
    agg = defaultdict(lambda: dict(crossings=0, bits=0, max_um=0.0, blocks=set(), links=[]))
    total = 0
    for lk, ln in lanes.items():
        e = ends.get(lk)
        if not e or len(e) != 2:
            continue
        (b1, p1), (b2, p2) = e
        bits = p1['bits']
        if 'h' in ln:
            y = ln['h']
            segs = [('v', p1['x'], p1['y'], y), ('h', y, p1['x'], p2['x']), ('v', p2['x'], y, p2['y'])]
        else:
            x = ln['v']
            segs = [('h', p1['y'], p1['x'], x), ('v', x, p1['y'], p2['y']), ('h', p2['y'], x, p2['x'])]
        for t, c, s0, s1 in segs:
            s0, s1 = sorted((s0, s1))
            for b, r in P.items():
                if b in (b1, b2):
                    continue
                if t == 'h':
                    if not (r['y'] < c < r['y'] + r['h']):
                        continue
                    L = min(s1, r['x'] + r['w']) - max(s0, r['x'])
                else:
                    if not (r['x'] < c < r['x'] + r['w']):
                        continue
                    L = min(s1, r['y'] + r['h']) - max(s0, r['y'])
                if L > a.reach:
                    total += 1
                    g = agg[(kind(b), t)]
                    g['crossings'] += 1; g['bits'] += bits; g['max_um'] = max(g['max_um'], L); g['blocks'].add(b)
                    if len(g['links']) < 6:
                        g['links'].append(f'{lk} crosses {b} {L:.0f} um ({t})')
    rows = {f'{k}:{t}': dict(v, blocks=sorted(v['blocks']), feedthrough=FEED.get(k) if t == 'v' else None,
                             max_um=round(v['max_um'], 1)) for (k, t), v in sorted(agg.items())}
    unhomed = {k: v for k, v in rows.items() if not v['feedthrough']}
    res = dict(schema='opentallas.hbm_v15.relay_homes.v1', reach_um=a.reach, laned_links=len(lanes),
               crossings_over_reach=total, by_block_kind=rows,
               verdict='OK' if not unhomed else f'{sum(v["crossings"] for v in unhomed.values())} crossings need a '
                                                f'relay home inside blocks without a feedthrough reservation: '
                                                f'{sorted(unhomed)}')
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ('laned_links', 'crossings_over_reach', 'verdict')}))
    for k, v in rows.items():
        print(k, v['crossings'], v['bits'], v['max_um'], len(v['blocks']), v['feedthrough'], v['links'][:2])


if __name__ == '__main__':
    main()
