#!/usr/bin/env python3
"""S-DIE r2 2026-10-15: vertical road demand by net class on an ACTUAL generated plan (canonical_plan.json.gz).

Every vertical segment of every constructed chain path (plan['chain_paths']) and hub service path whose x lies in a
named road contributes its lane bits over its y extent.  Classes: return trees (cr*), return outputs to gather (hr*),
x broadcast (cx*), hub-to-hub (hb*), control lanes (c/d/s/K*), services (qSW/aSW/coSW/ixSW/sel/col/hw/hc...).
Reports the peak cut per road and per class, and the class shares at that cut.  Track demand / capacity use the
die convention: 21.09375 tracks/um usable (M3+M5 vertical, 0.048 pitch x2 layers... as three_road_audit CAP) at 0.60.
Geometry only (no stations/CTS/PG); the same numbers the SA fit decision uses."""
import argparse, gzip, json, re, collections

ROADS = dict(S14W=(13428.7, 13938.5), HUBW=(13942.8, 15670.0), VCH=(15670.0, 17312.0), HUBE=(17312.0, 19040.4),
             S14E=(19044.7, 19554.5))
CAP_PER_UM = 21.09375
CLASS = [('return_tree', r'^cr'), ('return_out', r'^hr'), ('x_bcast', r'^cx'), ('hub_hb', r'^hb'), ('ctrl', r'^(K|c\d|d\d|s\d)'),
         ('service', r'.')]


def cls(name):
    for c, rx in CLASS:
        if re.match(rx, name):
            return c


def road(x):
    for r, (a, b) in ROADS.items():
        if a - 1e-6 <= x <= b + 1e-6:
            return r


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('--out'); ap.add_argument('--step', type=float, default=21.6)
    a = ap.parse_args()
    plan = json.load(gzip.open(a.plan))
    segs = []
    for c in plan['chain_paths']:
        lanes = c['lanes'] if isinstance(c['lanes'], list) else json.loads(c['lanes'])
        path = c['path'] if isinstance(c['path'], list) else json.loads(c['path'])
        bits = sum(lanes)
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            if abs(x0 - x1) < 1e-6 and abs(y1 - y0) > 1e-6 and road(x0):
                segs.append((cls(c['chain']), road(x0), min(y0, y1), max(y0, y1), bits, c['chain']))
    ymax = max(s[3] for s in segs)
    n = int(ymax / a.step) + 2
    prof = collections.defaultdict(lambda: [0] * n)
    for k, r, lo, hi, b, _ in segs:
        for i in range(int(lo / a.step), int(hi / a.step) + 1):
            prof[(k, r)][i] += b
    tot = [sum(prof[key][i] for key in prof) for i in range(n)]
    ip = max(range(n), key=lambda i: tot[i])
    out = dict(plan=a.plan, step_um=a.step, roads=ROADS, cap_tracks_per_um=CAP_PER_UM, util=0.60,
               peak=dict(y_um=round(ip * a.step, 1), bits=tot[ip], width_um_at060=round(tot[ip] / CAP_PER_UM / 0.6, 1),
                         by_class={k: sum(prof[(k, r)][ip] for r in ROADS) for k, _ in CLASS},
                         by_road={r: sum(prof[(k, r)][ip] for k, _ in CLASS) for r in ROADS},
                         by_class_road={f'{k}/{r}': prof[(k, r)][ip] for k, _ in CLASS for r in ROADS if prof[(k, r)][ip]}),
               per_road_peak={}, per_class_peak={})
    for r in ROADS:
        t = [sum(prof[(k, r)][i] for k, _ in CLASS) for i in range(n)]
        j = max(range(n), key=lambda i: t[i])
        out['per_road_peak'][r] = dict(y_um=round(j * a.step, 1), bits=t[j], width_um_at060=round(t[j] / CAP_PER_UM / 0.6, 1),
                                       road_width_um=round(ROADS[r][1] - ROADS[r][0], 1),
                                       by_class={k: prof[(k, r)][j] for k, _ in CLASS if prof[(k, r)][j]})
    for k, _ in CLASS:
        t = [sum(prof[(k, r)][i] for r in ROADS) for i in range(n)]
        j = max(range(n), key=lambda i: t[i])
        out['per_class_peak'][k] = dict(y_um=round(j * a.step, 1), bits=t[j], width_um_at060=round(t[j] / CAP_PER_UM / 0.6, 1))
    s = json.dumps(out, indent=1)
    if a.out:
        open(a.out, 'w').write(s + '\n')
    print(json.dumps(dict(peak=out['peak'], per_road_peak=out['per_road_peak'], per_class_peak=out['per_class_peak']), indent=0))


if __name__ == '__main__':
    main()
