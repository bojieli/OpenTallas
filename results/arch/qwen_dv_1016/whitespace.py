#!/usr/bin/env python3
"""White space of a planning model: 1 - (block area clipped to the die) / die area (blocks > 0.04 mm2; relays / bumps
excluded), and the largest empty axis-aligned rectangle (20-um raster, maximal-rectangle histogram method).
    whitespace.py MODEL.json ... -> json lines"""
import json, sys
import numpy as np
def ws(f, g=20.0):
    d = json.load(open(f)); I = [i for i in d['insts'] if i['w'] * i['h'] > 4e4]
    allI = d['insts']
    W = max(i['x'] + i['w'] for i in allI) + 21.6; H = max(i['y'] + i['h'] for i in allI) + 21.6
    nx, ny = int(W / g) + 1, int(H / g) + 1
    occ = np.zeros((ny, nx), dtype=bool)
    for i in I:
        x0, x1 = int(i['x'] / g), int(np.ceil((i['x'] + i['w']) / g)); y0, y1 = int(i['y'] / g), int(np.ceil((i['y'] + i['h']) / g))
        occ[y0:y1, x0:x1] = True
    white = 1 - occ.sum() / occ.size
    h = np.zeros(nx, dtype=int); best = (0, None)
    for r in range(ny):
        h = np.where(occ[r], 0, h + 1); st = []
        for c in range(nx + 1):
            cur = h[c] if c < nx else 0
            start = c
            while st and st[-1][1] >= cur:
                s, hh = st.pop(); a = hh * (c - s)
                if a > best[0]: best = (a, (s * g, (r - hh + 1) * g, (c - s) * g, hh * g))
                start = s
            st.append((start, cur))
    a, (x, y, w, hh) = best
    return dict(model=f, die_mm2=round(W * H / 1e6, 1), white_pct=round(100 * white, 1), white_mm2=round(white * W * H / 1e6, 1),
                largest_empty=dict(mm2=round(w * hh / 1e6, 2), x=x, y=y, w=w, h=hh))
if __name__ == '__main__':
    for f in sys.argv[1:]: print(json.dumps(ws(f)))
