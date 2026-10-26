#!/usr/bin/env python3
"""S81-CORE-LAT: which hard-core types sit where the die clock tree/mesh drivers and the die reset
hops have NO channel site -> need an in-core INFRA ISLAND (top-owned hole, M9->M1 via stack, die
clock + reset drivers ONLY; COORD 10-26: FT stations/repeaters stay pushed down in <=M7 bays).
Method: rasterise every hard core (incl. memory macros: no cells on them) of the plan in the die
frame on the 8.64 um placement grid, Euclidean distance transform from every blocked cell to the
nearest free (std-cell) cell.  A blocked region of half-thickness D forces a die leg/hop crossing it
to run 2D without a driver; island needed if 2D > limit (reset hop / reach 405 um; clock rep 450).
Also reports per core type the wall it forms with abutting cores (connected blocked component) so
FT corridor repeater bays (pushed down, in-core only where a core longer than reach blocks a
corridor) can be judged separately.
usage: island_need.py PLAN.json OUT.json [--grid 8.64]"""
import argparse, collections, json, re, sys
import numpy as np
from scipy import ndimage
ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('--grid', type=float, default=8.64)
a = ap.parse_args(); g = a.grid
d = json.load(open(a.plan)); T = d['partition_types']; W, H = d['die']['outline_um']
reach = float(d['die'].get('reach_um', 405)); rep = float(d['die'].get('rep_um', 450))
nx, ny = int(np.ceil(W / g)), int(np.ceil(H / g))
blk = np.zeros((ny, nx), dtype=np.int32)   # 0 free, else instance index+1
insts = []
def to_die(p, w, h, r):
    x0, y0, x1, y1 = r; o = p.get('orient', 'R0'); ox, oy = p['origin_um']
    if o in ('MY', 'R180'): x0, x1 = w - x1, w - x0
    if o in ('MX', 'R180'): y0, y1 = h - y1, h - y0
    return (ox + x0, oy + y0, ox + x1, oy + y1)
MEM = re.compile(r'^ot_(rom|sram)_\d+x\d+')
for p in d['partitions']:
    t = T[p['type']]; w, h = t['outline_um']
    cores = t.get('hard_cores') or []
    if t.get('hard') and not cores:
        cores = [{'inst': '(hard partition)', 'module': p['type'], 'origin_um': [0, 0], 'outline_um': [w, h]}]
    for c in cores:
        cw, ch = c['outline_um']; cx, cy = c['origin_um']
        r = to_die(p, w, h, (cx, cy, cx + cw, cy + ch))
        insts.append({'part': p['name'], 'ptype': p['type'], 'inst': c['inst'], 'module': c['module'], 'rect': r})
        i0, j0 = int(np.floor(r[0] / g + 1e-6)), int(np.floor(r[1] / g + 1e-6))
        i1, j1 = int(np.ceil(r[2] / g - 1e-6)), int(np.ceil(r[3] / g - 1e-6))
        blk[j0:j1, i0:i1] = len(insts)
mask = blk > 0
edt = ndimage.distance_transform_edt(mask) * g          # um to nearest free cell centre
lab, nlab = ndimage.label(mask)
comp = ndimage.find_objects(lab)
by = collections.defaultdict(list)
for k, it in enumerate(insts, 1):
    r = it['rect']
    i0, j0 = int(np.floor(r[0] / g + 1e-6)), int(np.floor(r[1] / g + 1e-6))
    i1, j1 = int(np.ceil(r[2] / g - 1e-6)), int(np.ceil(r[3] / g - 1e-6))
    sub = edt[j0:j1, i0:i1] * (blk[j0:j1, i0:i1] == k)
    D = float(sub.max()) if sub.size else 0.0
    labs = np.unique(lab[j0:j1, i0:i1][blk[j0:j1, i0:i1] == k])
    wall = (0.0, 0.0)
    for L in labs:
        if L == 0: continue
        sl = comp[L - 1]; wall = max(wall, ((sl[1].stop - sl[1].start) * g, (sl[0].stop - sl[0].start) * g), key=lambda q: q[0] * q[1])
    by[it['module']].append({'part': it['part'], 'inst': it['inst'], 'rect': [round(v, 3) for v in r], 'half_thickness_um': round(D, 2), 'wall_bbox_um': [round(wall[0], 1), round(wall[1], 1)]})
rows = []
for m, L in by.items():
    D = max(x['half_thickness_um'] for x in L); wl = max(L, key=lambda x: x['wall_bbox_um'][0] * x['wall_bbox_um'][1])
    rows.append({'module': m, 'memory_macro': bool(MEM.match(m)), 'replicas': len(L), 'max_half_thickness_um': D, 'max_span_without_site_um': round(2 * D, 1),
                 'island_reset_hop': 2 * D > reach, 'island_clock_rep': 2 * D > rep,
                 'n_replicas_over_reach': sum(2 * x['half_thickness_um'] > reach for x in L),
                 'largest_wall_bbox_um': wl['wall_bbox_um'], 'largest_wall_at': wl['part'] + '/' + wl['inst'], 'instances': L})
rows.sort(key=lambda r: -r['max_half_thickness_um'])
json.dump({'schema': 'opentallas.s81.core_island_need.v1', 'plan': a.plan, 'grid_um': g, 'reach_um': reach, 'rep_um': rep,
           'blocked_frac': round(float(mask.mean()), 4), 'cores': rows}, open(a.out, 'w'), indent=1)
print(f"blocked {mask.mean()*100:.1f}% of die; reach {reach} rep {rep}")
for r in rows[:40]:
    print(f"{r['module']:30s} rep={r['replicas']:5d} span={r['max_span_without_site_um']:7.1f} reset={int(r['island_reset_hop'])} clk={int(r['island_clock_rep'])} over={r['n_replicas_over_reach']:4d} wall={r['largest_wall_bbox_um']} @ {r['largest_wall_at']}")
