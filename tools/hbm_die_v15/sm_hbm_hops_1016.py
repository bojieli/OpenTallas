#!/usr/bin/env python3
"""SM<->HBM relay-hop witness (H-DIE-V790 10-16, OWNER 07:30): per chain of a link class, the pin-to-pin lane route
(the v6_eval.py / pin_cut lane model), the relay stages at 480-um reach and the LONGEST HOP when relays may only sit
outside hard blocks (greedy: each relay at the farthest legal point within reach; a hard run longer than the reach
forces a long hop).  --free sm_ makes blocks with that prefix relay-legal (the granted 40-um SM feedthrough carve,
option 1: hops <= reach, stage count unchanged).

    sm_hbm_hops_1016.py PLAN [--cls SM_HBM ...] [--free sm_] [--reach 480] [--out FILE]
Geometry only.
"""
import argparse, collections, glob, json, math
from pathlib import Path


def route(p0, p1, ln):
    if 'v' in ln:
        x = ln['v']; return [p0, (x, p0[1]), (x, p1[1]), p1]
    if 'h' in ln:
        y = ln['h']; return [p0, (p0[0], y), (p1[0], y), p1]
    return [p0, (p1[0], p0[1]), p1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan'); ap.add_argument('--cls', nargs='*', default=['SM_HBM'])
    ap.add_argument('--free', nargs='*', default=[]); ap.add_argument('--reach', type=float, default=480.0)
    ap.add_argument('--out')
    a = ap.parse_args()
    d = Path(a.plan)
    P = json.loads((d / 'compact.P.json').read_text())
    pins = json.loads(Path(glob.glob(str(d / 'pins' / '*.pins.json'))[0]).read_text())
    lanes = json.loads((d / 'lanes.json').read_text())
    ends = collections.defaultdict(list)
    for b, v in pins['blocks'].items():
        for f, fx in v['faces'].items():
            for p in fx['pins']:
                ends[p['link']].append((b, p))
    chains = []
    for lk, e in sorted(ends.items()):
        if len(e) != 2 or lk.split(':')[-1] not in a.cls:
            continue
        (b0, q0), (b1, q1) = e
        pts = route((q0['x'], q0['y']), (q1['x'], q1['y']), lanes.get(lk, {}))
        hard = [r for k, r in P.items() if k not in (b0, b1) and not (a.free and k.startswith(tuple(a.free)))]

        def free(x, y):
            return not any(r['x'] < x < r['x'] + r['w'] and r['y'] < y < r['y'] + r['h'] for r in hard)
        samp = []                                  # (arc length, x, y) every 4 um
        t = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            L = abs(x1 - x0) + abs(y1 - y0)
            n = max(1, int(L // 4))
            for k in range(n):
                f = k / n; samp.append((t + f * L, x0 + f * (x1 - x0), y0 + f * (y1 - y0)))
            t += L
        samp.append((t, pts[-1][0], pts[-1][1]))
        total = t
        ok = [free(x, y) for _, x, y in samp]
        hops, cur, i = [], 0.0, 0
        while total - cur > a.reach + 1e-6:
            best = None
            for j in range(i + 1, len(samp)):
                if samp[j][0] - cur > a.reach + 1e-6:
                    break
                if ok[j]:
                    best = j
            if best is None:                       # hard run: the next relay is the first legal point beyond reach
                best = next((j for j in range(i + 1, len(samp)) if samp[j][0] - cur > a.reach and ok[j]), len(samp) - 1)
            hops.append(samp[best][0] - cur); cur = samp[best][0]; i = best
            if best == len(samp) - 1:
                break
        if total - cur > 1e-6:
            hops.append(total - cur)
        chains.append(dict(link=lk, bits=q0['bits'], route_um=round(total, 1), stages=len(hops) - 1 if hops else 0,
                           ideal_stages=max(0, math.ceil(total / a.reach) - 1), max_hop_um=round(max(hops), 1) if hops else 0.0,
                           hops_over_600=sum(h > 600 for h in hops), hops=len(hops)))
    tb = sum(c['bits'] for c in chains) or 1
    out = dict(schema='opentallas.hbm.sm_hbm_hops.v1', plan=str(d), classes=a.cls, free_prefixes=a.free, reach_um=a.reach,
               qualification='GEOMETRY_ONLY_LANE_MODEL',
               summary=dict(chains=len(chains), hops=sum(c['hops'] for c in chains), hops_over_600=sum(c['hops_over_600'] for c in chains),
                            max_hop_um=max((c['max_hop_um'] for c in chains), default=0),
                            max_route_um=max((c['route_um'] for c in chains), default=0),
                            stages_bw=round(sum(c['bits'] * c['stages'] for c in chains) / tb, 3),
                            ideal_stages_bw=round(sum(c['bits'] * c['ideal_stages'] for c in chains) / tb, 3)),
               chains=chains)
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['summary']))


if __name__ == '__main__':
    main()
