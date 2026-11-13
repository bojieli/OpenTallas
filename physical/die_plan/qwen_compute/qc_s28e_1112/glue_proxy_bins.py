#!/usr/bin/env python3
"""QC-S28-E: PROXY sink bins for glue (no retained 3_place.odb on any host; the 11-10 attempt_9 DB was pruned).
Inputs: the 11-10 attempt_9 place density render (layout_review/place/density.png, GEOM-VIS-1 copy) and the per-tap
clock sink counts of the same placement (auto_geom.json tap_sinks: clk family clk, clk_t1..clk_t7 = the R4 grid taps at
pitch 400).  Each grid tap's measured count is spread over its nearest-tap (Voronoi) cell in proportion to the
rendered cell density (colour-bar inverse map, background subtracted, hard cores + halo excluded).  10.8-um bins,
type frame, same JSON keys as make_s28.py bins.  REPLACE with the measured dump (sinkdump28.tcl + make_s28.py bins)
at glue's first s28 3_place.odb."""
import json, sys, math, hashlib
from PIL import Image
png, plan_json, agjson, out = sys.argv[1:5]
W, H = 777.6, 1468.8
X0, X1, Y0, Y1 = 49, 839, 49, 1549          # inner frame pixels (measured)
BIN = 10.8
im = Image.open(png).convert('RGB'); px = im.load()
bar = [(px[858, y], 1.0 - (y - 19) / (147 - 19)) for y in range(19, 148)]
def dens(c):
    if sum(c) < 60: return 0.0
    best = min(bar, key=lambda b: sum((b[0][i] - c[i]) ** 2 for i in range(3)))
    return best[1]
P = json.load(open(plan_json))
t = P['partition_types']['glue']
cores = []
for h in t['hard_cores']:
    (x, y), (w, hh) = h['origin_um'], h['outline_um']; m = h.get('halo_um', 4.32)
    cores.append((x - m, y - m, x + w + m, y + hh + m))
nx, ny = int(math.ceil(W / BIN)), int(math.ceil(H / BIN))
def pix(xu, yu): return (X0 + xu / W * (X1 - X0), Y1 - yu / H * (Y1 - Y0))
D = {}
for i in range(nx):
    for j in range(ny):
        cx, cy = (i + 0.5) * BIN, (j + 0.5) * BIN
        if cx > W or cy > H or any(a <= cx <= c and b <= cy <= d for a, b, c, d in cores): continue
        p0 = pix(i * BIN, (j + 1) * BIN); p1 = pix(min(W, (i + 1) * BIN), j * BIN)
        vals = [dens(px[x, y]) for x in range(int(p0[0]) + 1, int(p1[0])) for y in range(int(p0[1]) + 1, int(p1[1]))]
        D[(i, j)] = sum(vals) / len(vals) if vals else 0.0
bg = sorted(D.values())[len(D) // 2]           # median bin = background render level
D = {k: max(0.0, v - bg) for k, v in D.items()}
ag = json.load(open(agjson)); m = ag.get('metrics', ag); ts = m['tap_sinks']
cols, rows = [194.4, 583.2], [183.6 + 367.2 * k for k in range(4)]
names = ['clk'] + ['clk_t%d' % k for k in range(1, 8)]
grid = {}
k = 0
for r in rows:
    for c in cols:
        grid[names[k]] = (c, r); k += 1
cnt = {}
for n, (gx, gy) in grid.items():
    cell = [b for b in D if min(grid, key=lambda q: math.hypot(grid[q][0] - (b[0] + .5) * BIN, grid[q][1] - (b[1] + .5) * BIN)) == n]
    tot = sum(D[b] for b in cell); need = int(ts[n])
    if tot <= 0:
        cell = sorted(cell, key=lambda b: math.hypot(grid[n][0] - (b[0] + .5) * BIN, grid[n][1] - (b[1] + .5) * BIN))[:max(1, need // 40)]
        w = {b: 1.0 for b in cell}; tot = len(cell)
    else:
        w = {b: D[b] for b in cell}
    acc = 0.0; given = 0
    for b in sorted(w):
        acc += need * w[b] / tot; v = int(round(acc)) - given
        if v > 0: cnt[b] = cnt.get(b, 0) + v; given += v
bins = [[round((i + 0.5) * BIN, 3), round((j + 0.5) * BIN, 3), v] for (i, j), v in sorted(cnt.items())]
doc = dict(bin_um=BIN, n=sum(v for *_, v in bins), bins=bins, type='glue', placed_kit='glue',
           source='PROXY (QC-S28-E 11-12): 11-10 attempt_9 place density render x auto_geom tap_sinks (clk family %d); '
                  'replace with sinkdump28.tcl of the first s28 3_place.odb' % sum(int(ts[n]) for n in names),
           proxy=True, png_sha256=hashlib.sha256(open(png, 'rb').read()).hexdigest(),
           auto_geom_sha256=hashlib.sha256(open(agjson, 'rb').read()).hexdigest())
open(out, 'w').write(json.dumps(doc, separators=(',', ':')) + '\n')
print('glue proxy bins: n=%d bins=%d per-tap %s bg=%.3f' % (doc['n'], len(bins), {n: int(ts[n]) for n in names}, bg))
