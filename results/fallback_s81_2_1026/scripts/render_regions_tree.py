#!/usr/bin/env python3
"""FALLBACK-S81-2: render the region local trees (die_trial --region-trees kit clock/tree.json) over the region map.
usage: render_regions_tree.py PLAN REGIONS.json TREE.json OUT.png [SUMMARY.json]"""
import json, sys, collections, colorsys
sys.path.insert(0, 'tools/die_plan')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
import schema as S
import die_trial as DT
plan, regf, treef, out = sys.argv[1:5]
P = S.Plan(S.load(plan), plan)
reg = json.load(open(regf))['part_region']; tr = json.load(open(treef))
tags = sorted(set(reg.values())); col = {t: colorsys.hsv_to_rgb((i * 0.618) % 1, 0.35, 0.95) for i, t in enumerate(tags)}
W, H = P.W / 1000, P.H / 1000
fig, ax = plt.subplots(figsize=(18, 18 * H / W + 0.8), dpi=150)
for n, p in P.parts.items():
    w, h = P.types[p['type']]['outline_um']; x, y = p['origin_um']
    ax.add_patch(Rectangle((x / 1e3, y / 1e3), w / 1e3, h / 1e3, facecolor=col.get(reg.get(n), (1, 1, 1)), edgecolor='0.55', lw=0.3))
for tl, x0, y0, x1, y1 in DT.core_rects_die(P):
    ax.add_patch(Rectangle((x0 / 1e3, y0 / 1e3), (x1 - x0) / 1e3, (y1 - y0) / 1e3, facecolor='0.45', edgecolor='none', alpha=0.45))
# region boundaries: edges between partitions of different regions (thick black)
nodes = {int(k): v for k, v in tr['nodes'].items()}
inreg = {}
def region_of(i):
    if i in inreg: return inreg[i]
    nd = nodes[i]; r = nd.get('region_root')
    if r is None and nd['parent'] is not None: r = region_of(nd['parent'])
    inreg[i] = r; return r
top, loc = [], collections.defaultdict(list)
for i, nd in nodes.items():
    if nd['parent'] is None: continue
    p = nodes[nd['parent']]; seg = [(p['x'] / 1e3, p['y'] / 1e3), (nd['x'] / 1e3, nd['y'] / 1e3)]
    r = region_of(i)
    (loc[r] if r else top).append(seg)
ax.add_collection(LineCollection(top, colors='k', linewidths=1.4, alpha=0.9))
lc = [s for v in loc.values() for s in v]
ax.add_collection(LineCollection(lc, colors='tab:blue', linewidths=0.6, alpha=0.9))
legs = [((nodes[t['node']]['x'] / 1e3, nodes[t['node']]['y'] / 1e3), (t['xy'][0] / 1e3, t['xy'][1] / 1e3)) for t in tr['taps']]
ax.add_collection(LineCollection(legs, colors='tab:green', linewidths=0.4))
rr = [n for n in nodes.values() if n.get('region_root')]
ax.scatter([n['x'] / 1e3 for n in rr], [n['y'] / 1e3 for n in rr], s=14, c='red', marker='s', zorder=5, label=f'region roots ({len(rr)})')
ax.scatter([t['xy'][0] / 1e3 for t in tr['taps']], [t['xy'][1] / 1e3 for t in tr['taps']], s=3, c='green', zorder=4, label=f"partition entries ({len(tr['taps'])})")
sl = tr['meta'].get('site_legal', {})
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
ax.set_title(f"S81 G=2 landed-region fallback clock: {len(rr)} region roots, black = die reference tree, blue = region local trees "
             f"(full depth, leaf {tr['meta']['leaf_um']:.0f} um), green = leaf->entry; site_legal illegal={sl.get('illegal')}; "
             f"nodes {tr['meta']['nodes']} reps {tr['meta']['repeaters']}", fontsize=8)
ax.legend(loc='upper right', fontsize=7)
fig.savefig(out, bbox_inches='tight'); print(out)
# summary: per region local-tree depth (levels below the region root) and max root->entry wire
def depth_below(i):
    ks = nodes[i]['kids']
    return 0 if not ks else 1 + max(depth_below(k) for k in ks)
summ = dict(regions=len(rr), region_depth=collections.Counter(depth_below(n['id']) for n in rr),
            root_levels=collections.Counter(n['level'] for n in rr), meta=tr['meta'])
if len(sys.argv) > 5: json.dump(summ, open(sys.argv[5], 'w'), indent=1, default=str)
print(json.dumps(summ, default=str)[:1500])
