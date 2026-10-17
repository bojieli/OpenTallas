#!/usr/bin/env python3
"""Q-DIEPLAN3 (2026-10-16): q3h5 = q3h4 grid + DIE-CLOCK keep-outs (regional root sites, trunk strips, clk_rx lanes).

usage: mk_q3h5_clock.py GRID_IN HOMES OUT_GRID

DIE-CLOCK plan (2026-10-16 ~21:00): one balanced distribution to the 48 C_B16 ck entries and the 48 x 9 head clock pins:
four 100 x 100 root sites (RS_lo band-gap-low, RS_hi band-gap-high, RS_hgW / RS_hgE head gap at the centre-column edges),
four 20-um relay-free trunk strips across the arrays (in the band gaps and at the head-gap lane edges, so the 129.6 /
109-um relay lanes stay whole), and 40-um vertical clk_rx -> root lanes through the centre white space.  A root site
that collides with a block takes the nearest free spot within 300 um (the plan's allowance).  All keep-outs reach the
relay planner (m['relay_keepouts'], b3r2 occupancy) and the grid JSON.
"""
import json, sys
G = json.load(open(sys.argv[1])); H = json.load(open(sys.argv[2]))['homes']
rects = [(h['x'], h['y'], h['x'] + h['w'], h['y'] + h['h'], n) for n, h in H.items()
         if not n.startswith(('t_', 's_'))] + [(c['x'], c['y'], c['x'] + c['w'], c['y'] + c['h'], c['n']) for c in G['clusters']]
W, Hd = G['die']['w'], G['die']['h']


def free(r):
    return all(not (a < r[2] and r[0] < c and b < r[3] and r[1] < d) for a, b, c, d, _ in rects)


def site(x, y, w=100.0, h=100.0, lim=300.0, step=4.32):
    best = None
    k = 0
    while k * step <= lim:
        for dx in (-k * step, k * step):
            for dy in [j * step for j in range(-k, k + 1)]:
                for ddx, ddy in ((dx, dy), (dy, dx)):
                    r = (x - w / 2 + ddx, y - h / 2 + ddy, x + w / 2 + ddx, y + h / 2 + ddy)
                    if free(r) and (best is None or abs(ddx) + abs(ddy) < best[0]):
                        best = (abs(ddx) + abs(ddy), r)
        if best:
            return [round(z, 3) for z in best[1]]
        k += 1
    raise SystemExit(f'no free root site within {lim} um of ({x}, {y})')


hg0, hg1 = G['channels']['head_gap']
bg = G['channels']['band_gaps']
keep = []
roots = {'RS_lo': (16650.0, (bg[0][0] + bg[0][1]) / 2), 'RS_hi': (16650.0, (bg[1][0] + bg[1][1]) / 2),
         'RS_hgW': (13950.0, (hg0 + hg1) / 2), 'RS_hgE': (19350.0, (hg0 + hg1) / 2)}
for n, (x, y) in roots.items():
    r = site(x, y)
    keep.append(dict(n=n, kind='clock_root', rect=r))
    rects.append((*r, n))
# trunk strips at the lane edges (head gap: the lower / upper edge; band gaps: the lower edge), arrays only
strips = {'L_lo': bg[0][0], 'L_hg1': hg0, 'L_hg2': hg1 - 20.0, 'L_hi': bg[1][0]}
xw1 = max(c['x'] + c['w'] for c in G['clusters'] if c['side'] == 'W')
xe0 = min(c['x'] for c in G['clusters'] if c['side'] == 'E')
for n, y in strips.items():
    keep.append(dict(n=n + '_W', kind='clock_strip', rect=[0.0, round(y, 3), round(xw1, 3), round(y + 20.0, 3)]))
    keep.append(dict(n=n + '_E', kind='clock_strip', rect=[round(xe0, 3), round(y, 3), W, round(y + 20.0, 3)]))
# clk_rx -> root vertical / horizontal lanes (40 um): the free x through the centre white space nearest each root
ck = H['clk_rx']
cx, cy = ck['x'] + ck['w'] / 2, ck['y'] + ck['h'] / 2
lanes = []


def vlane(y0, y1, xs):
    for x in xs:
        r = (x - 20.0, min(y0, y1), x + 20.0, max(y0, y1))
        if free(r):
            return [round(z, 3) for z in r]
    return None


cand = sorted(set(round(14014.0 + 8.64 * k, 3) for k in range(int((19263 - 14014) / 8.64))), key=lambda x: abs(x - cx))
for n in ('RS_lo', 'RS_hi'):
    rr = next(k['rect'] for k in keep if k['n'] == n)
    ry = (rr[1] + rr[3]) / 2
    y0 = ck['y'] if ry < cy else ck['y'] + ck['h']
    ln = vlane(y0, ry, cand)
    if ln is None:
        print(f'WARN no straight 40-um lane clk_rx -> {n}: DIE-CLOCK routes it around (obstacle-aware trunk)')
    else:
        keep.append(dict(n=f'LANE_{n}', kind='clock_lane', rect=ln))
G['keepouts'] = keep
G['dieclock'] = dict(source='DIE-CLOCK 2026-10-16 plan (a)/(b)', clk_rx=[round(cx, 3), round(cy, 3)],
                     note='strips at lane edges (not mid-gap) so the 109 / 129.6-um relay lanes stay whole')
json.dump(G, open(sys.argv[3], 'w'), indent=1)
for k in keep:
    print(k['n'], k['kind'], k['rect'])
