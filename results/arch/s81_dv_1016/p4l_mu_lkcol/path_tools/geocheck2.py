#!/usr/bin/env python3
"""Realized-width geometric check: each plan hop as a band of the realized bus width (bits x 0.096 um pin pitch,
or the relay body across the lane, whichever is wider), each station as its relay body; overlaps vs block bodies
and vs other lanes' relay bodies.  Predicts on-obstacle repeaters ~ overlap length / 160 um per bit."""
import json, sys, collections, math
p = json.load(open(sys.argv[1])); EPS = 0.5; PP = 0.096; WIRE = 160.0
B = p['blocks']
REL = {70: (12.96, 17.28), 276: (25.92, 17.28), 512: (58.32, 17.28), 562: (58.32, 17.28), 682: (71.28, 17.28)}   # (across, along)
REL_EW = {70: (17.28, 12.96), 276: (32.4, 17.28), 512: (58.32, 17.28), 562: (62.64, 17.28), 682: (75.6, 17.28)}
def relay_across(bits, horiz):
    t = REL_EW if horiz else REL
    k = min(t, key=lambda b: (b < bits, abs(b - bits)))
    return t[k][0], t[k][1]
def ov(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * (min(a[3], b[3]) > max(a[1], b[1]) + 0) , max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
rects = [(b['x'] + EPS, b['y'] + EPS, b['x'] + b['w'] - EPS, b['y'] + b['h'] - EPS, b['name']) for b in B]
def olen(r, horiz):
    """length along the lane of band r inside each block body"""
    out = []
    for q in rects:
        dx = min(r[2], q[2]) - max(r[0], q[0]); dy = min(r[3], q[3]) - max(r[1], q[1])
        if dx > 0 and dy > 0: out.append((q[4], dx if horiz else dy))
    return out
stations = []
tot = collections.Counter(); cls = collections.Counter(); blk = collections.Counter(); rows = []
for l in p['links']:
    bits = l['b']; hw_bus = bits * PP / 2 + 1.5
    ends = {B[l['e'][0][0]]['name'], B[l['e'][1][0]]['name']}
    s = 0.0; per = collections.Counter()
    for h in l['h']:
        x0, y0, x1, y1 = h[:4]; horiz = abs(y1 - y0) < 1e-6
        if abs(x1 - x0) < 1e-6 and abs(y1 - y0) < 1e-6: continue
        acr, _ = relay_across(bits, horiz); hw = max(hw_bus, acr / 2)
        r = (min(x0, x1), y0 - hw, max(x0, x1), y0 + hw) if horiz else (x0 - hw, min(y0, y1), x0 + hw, max(y0, y1))
        for n, v in olen(r, horiz):
            if n in ends and v < 2.0: continue
            s += v; per[n] += v
    for sx, sy in l['sp']:
        # relay orientation: from the hop through the station
        horiz = any(abs(h[1] - h[3]) < 1e-6 and abs(h[1] - sy) < 1e-6 and min(h[0], h[2]) - 1e-6 <= sx <= max(h[0], h[2]) + 1e-6 for h in l['h'])
        acr, alg = relay_across(bits, horiz)
        w_, h_ = (alg, acr) if horiz else (acr, alg)
        stations.append((sx - w_ / 2, sy - h_ / 2, sx + w_ / 2, sy + h_ / 2, l['i'], bits))
    if s:
        tot[l['i']] = s * bits; cls[l['c']] += s * bits
        for n, v in per.items(): blk[n] += v * bits
        rows.append((s * bits, l['i'], l['c'], bits, round(s, 1), dict((k, round(v, 1)) for k, v in per.most_common(3))))
# relay vs relay overlap (different links)
grid = collections.defaultdict(list)
for k, r in enumerate(stations):
    for gx in range(int(r[0] // 100), int(r[2] // 100) + 1):
        for gy in range(int(r[1] // 100), int(r[3] // 100) + 1): grid[gx, gy].append(k)
rr = set()
for cell in grid.values():
    for i in cell:
        for j in cell:
            if i < j and (i, j) not in rr:
                a, b = stations[i], stations[j]
                if a[4] != b[4] and min(a[2], b[2]) - max(a[0], b[0]) > 0.5 and min(a[3], b[3]) - max(a[1], b[1]) > 0.5: rr.add((i, j))
import os
if os.environ.get("RR"): [print("RR", stations[i][4], stations[j][4], [round(v) for v in stations[i][:4]]) for i, j in sorted(rr)]
rrc = collections.Counter()
for i, j in rr: rrc[p and next(l['c'] for l in p['links'] if l['i'] == stations[i][4])] += 1
rows.sort(reverse=True)
S = sum(tot.values())
print(f'band-over-block bit-mm {S/1000:.1f}  est repeaters {S/WIRE:.0f}  links {len(rows)}  relay-relay overlaps {len(rr)} {dict(rrc)}')
print('by class bit-mm', {k: round(v / 1000, 1) for k, v in cls.most_common()})
print('top blocks', [(k, round(v / 1000, 1)) for k, v in blk.most_common(10)])
for r in rows[:int(sys.argv[2]) if len(sys.argv) > 2 else 20]: print(round(r[0] / 1000, 1), *r[1:])
