"""LH-GEN2CD: where does the hbm-domain reset reach mask go on the recovered GEN2c case_a? (diagnostic only)"""
import json, sys, collections
sys.path.insert(0, sys.argv[1])
from reset_forest_geometry import Geometry
import reset_forest_layer as L
man = json.load(open(sys.argv[2])); c = json.load(open(sys.argv[3]))
g = Geometry(man, sys.argv[4], sys.argv[5], 405.)
W, H = g.W, g.H; nx, ny = g.grid.nx, g.grid.ny
free = sum(1 for b in g.grid.blk if not b); print('grid', nx, ny, 'free cells', free, 'budget', g.budget)
pors = sorted({(x['domain'], x['source'][1]) for x in c['clock_resets'] if x['kind'] == 'reset' and x['source'][0] == 'hb_ckgen'})
print('pors', pors)
def q(i, j):
    x, y = g.grid.xy((i, j)); return ('N' if y >= H / 2 else 'S') + ('W' if x < W / 2 else 'E')
tot = collections.Counter(q(k % nx, k // nx) for k, b in enumerate(g.grid.blk) if not b)
print('free per quadrant', dict(tot))
for dom, por in pors:
    src = g.pin('hb_ckgen', por); m = g.reach_mask(src)
    cnt = collections.Counter(q(k % nx, k // nx) for k, b in enumerate(m) if b)
    print(dom, por, 'src', [round(v) for v in src], 'reach', sum(m), {k: f'{cnt[k]}/{tot[k]}' for k in sorted(tot)})
    # free cells in 2 km window around top-right and around (13039,29005)
    for pt in ((18531, 30455), (13039, 29005)):
        ci, cj = g.grid.cell(*pt); r = int(1000 // 1)  # cells
        f = a = 0
        for k, b in enumerate(g.grid.blk):
            i, j = k % nx, k // nx
            x, y = g.grid.xy((i, j))
            if abs(x - pt[0]) <= 1000 and abs(y - pt[1]) <= 1000:
                if not b: f += 1; a += m[k]
        print('   window 2x2mm at', pt, 'free', f, 'reachable', a)
