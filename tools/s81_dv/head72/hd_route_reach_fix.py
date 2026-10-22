#!/usr/bin/env python3
"""H11 r4 (STW-S81c-DIE2-C25 10-22): re-cut the relay stations of any routed link whose longest station hop exceeds the
405-um reach (dv_route72 cuts n = ceil(L / 350) stations and shifts a cut that falls within 50 um of a corner by 50 um,
so two shifted neighbours can open a 350 + 100 um hop; the R6 glue endpoints re-grid the router and two FB links hit
413 / 416 um).  Same path, same corner rule, n + 1 (+2 ...) stations until every hop <= 405 um; every other link
unchanged.  The land plan (MODEL rows) re-derives K from the new station count.
Usage: hd_route_reach_fix.py ROUTED_IN ROUTED_OUT"""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hd_plan import REACH, stations_hops   # noqa: E402


def recut(l, n):
    clean = [tuple(l['h'][0][0:2])] + [tuple(h[2:4]) for h in l['h']]
    pts = []
    for q in clean:
        if pts and q == pts[-1]:
            continue
        if len(pts) > 1 and ((pts[-2][0] == pts[-1][0] == q[0]) or (pts[-2][1] == pts[-1][1] == q[1])):
            pts[-1] = q
        else:
            pts.append(q)
    legs = []; length = 0.0; corners = []
    for u, v in zip(pts, pts[1:]):
        ll = abs(v[0] - u[0]) + abs(v[1] - u[1]); legs.append((length, length + ll, u, v)); length += ll; corners.append(length)
    cuts = []
    for k in range(1, n):
        t = k * length / n
        for c in corners[:-1]:
            if abs(t - c) < 50:
                t = c - 50 if t <= c else c + 50
        cuts.append(t)

    def at(t):
        for lo, hi, u, v in legs:
            if t <= hi + 1e-5:
                z = 0 if hi == lo else (t - lo) / (hi - lo)
                return [u[0] + (v[0] - u[0]) * z, u[1] + (v[1] - u[1]) * z]
        return list(pts[-1])
    sp = [at(t) for t in cuts]
    marks = sorted(set([0.0, length] + corners + cuts))
    hops = [[*at(lo), *at(hi), l['b']] for lo, hi in zip(marks, marks[1:])]
    return dict(h=hops, sp=sp, s=len(sp), L=round(length, 3))


def main():
    src, out = sys.argv[1:3]
    p = json.load(open(src)); fixed = []
    for l in p['links']:
        if not l.get('h') or max(stations_hops(l)) <= REACH:
            continue
        before = (l['s'], round(max(stations_hops(l)), 1))
        for n in range(l['s'] + 2, l['s'] + 8):
            t = dict(l, **recut(l, n))
            if max(stations_hops(t)) <= REACH and abs(t['L'] - l['L']) < 1e-2:
                l.update(recut(l, n)); break
        else:
            raise SystemExit(f'REACH_FIX FAIL {l["i"]}')
        fixed.append(dict(link=l['i'], stations=[before[0], l['s']], hop_um=[before[1], round(max(stations_hops(l)), 1)]))
    f = p['facts']; f['physical72']['relay_station_count'] = sum(l.get('s', 0) for l in p['links'])
    f['relays'] = f['physical72']['relay_station_count']; f['reach_fix'] = fixed
    Path(out).write_text(json.dumps(p, indent=1))
    print('REACH_FIX', len(fixed), json.dumps(fixed))


if __name__ == '__main__':
    main()
