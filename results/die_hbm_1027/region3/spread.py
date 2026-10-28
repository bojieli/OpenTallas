#!/usr/bin/env python3
"""DIE-HBM-3 region3: in-region balanced local clock spread estimate per region map (12.14b content, CROSS-DIE NOTE).
Balanced equal-length tree from the region bbox centre (locality model): I_r = v x (w + h) / 2.  Two leaves of one
region worst case part at the root: unshared = I_r each side.  Spread = I_r x (droop 5.11 % one-sided + nets 3 %
random + AOCV 0.21 %/mm x bbox diagonal) + 20 ps balance residual (12.3 +-20).  UNCHECKED model.
usage: spread.py PLAN V MAP.json [MAP.json ...]"""
import json, math, sys
P = json.load(open(sys.argv[1])); v = float(sys.argv[2])
T = P['partition_types']
rect = {}
for p in P['partitions']:
    w, h = T[p['type']]['outline_um']; x, y = p['origin_um']; rect[p['name']] = (x, y, x + w, y + h)
for mp in sys.argv[3:]:
    r = json.load(open(mp)); r = r.get('part_region', r)
    box = {}
    for n, g in r.items():
        if n not in rect:
            continue
        a = rect[n]; b = box.get(g, a)
        box[g] = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
    worst = (0, None)
    span = 0
    rows = []
    for g, b in box.items():
        w, h = (b[2] - b[0]) / 1000, (b[3] - b[1]) / 1000
        span = max(span, w, h)
        I = v * (w + h) / 2
        s = I * (0.0511 + 0.03 + 0.0021 * math.hypot(w, h)) + 20
        rows.append((round(s, 1), g, round(w, 2), round(h, 2), sorted(n for n, gg in r.items() if gg == g)[:3]))
        if s > worst[0]:
            worst = (s, g, round(w, 2), round(h, 2), round(I))
    print(json.dumps(dict(map=mp.split('/')[-1], v=v, regions=len(box), max_span_mm=round(span, 2),
                          worst_spread_ps=round(worst[0], 1), worst_region=worst[1:],
                          over150=[x for x in sorted(rows, reverse=True) if x[0] > 150][:6],
                          worst_non_hub=next((x for x in sorted(rows, reverse=True) if not any('hub' in n for n in x[4])), None))))
