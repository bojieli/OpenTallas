#!/usr/bin/env python3
"""Selected72 relay-station direction binding (the rule that produced plan_routed_r2 station_dirs, reproduced exactly:
0 of 20222 r2 stations differ).

Each planned station takes the existing relay master of its link width whose direction is the direction of travel on the
straight piece that holds the station.  When that width has no closed relay view in that direction (relay_bodies.json),
the station takes the first available direction of the width in sorted order (70 -> NS, 512 -> EW in r2).
Usage: dv_station_dirs72.py PLAN_ROUTED RELAY_BODIES OUT
"""
import collections
import json
import sys
from pathlib import Path


def travel(hops, px, py):
    for x1, y1, x2, y2, _ in hops:
        if abs(x1 - x2) < 1e-6 and abs(x1 - px) < 1e-3 and min(y1, y2) - 1e-3 <= py <= max(y1, y2) + 1e-3 and abs(y2 - y1) > 1e-9:
            return 'SN' if y2 > y1 else 'NS'
        if abs(y1 - y2) < 1e-6 and abs(y1 - py) < 1e-3 and min(x1, x2) - 1e-3 <= px <= max(x1, x2) + 1e-3 and abs(x2 - x1) > 1e-9:
            return 'WE' if x2 > x1 else 'EW'
    raise ValueError(f'station ({px}, {py}) not on any straight hop')


def main():
    plan_p, bodies_p, out_p = sys.argv[1:4]
    p = json.load(open(plan_p))
    avail = collections.defaultdict(set)
    for k in json.load(open(bodies_p)):
        *_, b, d = k.split('_')
        avail[b].add(d)
    sub = collections.Counter()
    for l in p['links']:
        b = str(l['b'])
        dirs = []
        for x, y in l.get('sp', []):
            t = travel(l['h'], x, y)
            if t not in avail[b]:
                if not avail[b]:
                    raise SystemExit(f"{l['i']}: no relay view for width {b}")
                sub[(b, t)] += 1
                t = sorted(avail[b])[0]
            dirs.append(t)
        l['station_dirs'] = dirs
    Path(out_p).write_text(json.dumps(p, indent=1))
    print('STATION_DIRS', sum(len(l['station_dirs']) for l in p['links']), 'substituted', dict((f'{b}:{t}', n) for (b, t), n in sub.items()))


if __name__ == '__main__':
    main()
