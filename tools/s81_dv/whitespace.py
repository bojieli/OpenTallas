#!/usr/bin/env python3
"""White space of a dv_plan.py plan (owner rule no-empty-regions-1017): rasterise the die at GRID um, mark every
block, report the free %, the largest empty rectangle, and every empty rectangle wider AND taller than CHANNEL um
(a routing channel; anything larger needs a cut-model reason or a fill)."""
import json, sys, gzip
import numpy as np
GRID, CHANNEL = 50.0, 450.0


def load(p):
    return json.load(gzip.open(p) if p.endswith('.gz') else open(p))


def largest_rect(free):
    """maximal all-True rectangle (histogram method) -> (area_cells, r0, c0, h, w)"""
    R, C = free.shape
    h = np.zeros(C, int); best = (0, 0, 0, 0, 0)
    for r in range(R):
        h = np.where(free[r], h + 1, 0)
        st = []
        for c in range(C + 1):
            cur = h[c] if c < C else 0
            s = c
            while st and st[-1][1] >= cur:
                s, hh = st.pop()
                a = hh * (c - s)
                if a > best[0]:
                    best = (a, r - hh + 1, s, hh, c - s)
            st.append((s, cur))
    return best


def analyse(plan):
    W, H = plan['facts']['die_um']
    R, C = int(H // GRID), int(W // GRID)
    occ = np.zeros((R, C), bool)
    for b in plan['blocks']:
        r0, r1 = int(b['y'] // GRID), int(np.ceil((b['y'] + b['h']) / GRID))
        c0, c1 = int(b['x'] // GRID), int(np.ceil((b['x'] + b['w']) / GRID))
        occ[max(0, r0):min(R, r1), max(0, c0):min(C, c1)] = True
    free = ~occ
    rects = []
    f = free.copy()
    while True:
        a, r0, c0, hh, ww = largest_rect(f)
        if hh * GRID < CHANNEL or ww * GRID < CHANNEL or a == 0:
            # the largest remaining rectangle is channel-sized in one dimension; but there may be other big ones
            # with a smaller area: knock this one out and keep looking a little
            if a == 0 or (hh * GRID < CHANNEL and ww * GRID < CHANNEL):
                break
            f[r0:r0 + hh, c0:c0 + ww] = False
            continue
        rects.append(dict(x=c0 * GRID, y=r0 * GRID, w=ww * GRID, h=hh * GRID, mm2=round(a * GRID * GRID / 1e6, 2)))
        f[r0:r0 + hh, c0:c0 + ww] = False
    a, r0, c0, hh, ww = largest_rect(free)
    return dict(grid_um=GRID, channel_um=CHANNEL, die_mm2=round(W * H / 1e6, 1),
                white_pct=round(100 * free.mean(), 1), white_mm2=round(free.sum() * GRID * GRID / 1e6, 1),
                largest_empty=dict(x=c0 * GRID, y=r0 * GRID, w=ww * GRID, h=hh * GRID),
                over_channel=sorted(rects, key=lambda r: -r['mm2']),
                over_channel_mm2=round(sum(r['mm2'] for r in rects), 1))


if __name__ == '__main__':
    r = analyse(load(sys.argv[1]))
    print(json.dumps({k: v for k, v in r.items() if k != 'over_channel'}, indent=1))
    print('over-channel rectangles:', len(r['over_channel']))
    for x in r['over_channel'][:12]:
        print(' ', x)
