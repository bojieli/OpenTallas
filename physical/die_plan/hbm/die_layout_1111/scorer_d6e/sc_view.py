"""scorer-row render: hard cores, bus rows of BUS (grey), scorer row (red). usage: PLAN TYPE BUS OUT"""
import json, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pl, tn, bus, out = sys.argv[1:5]
t = json.load(open(pl))['partition_types'][tn]; W, H = t['outline_um']
fig, ax = plt.subplots(figsize=(14, 14 * H / W + 1), facecolor='white')
ax.add_patch(Rectangle((0, 0), W, H, fc='#f7f7f7', ec='k'))
for h in t['hard_cores']:
    ax.add_patch(Rectangle(h['origin_um'], *h['outline_um'], fc='#bbbbbb', ec='k', lw=0.4))
for r in t['internal_stations']:
    if r.get('conn') != 'bus:' + bus:
        continue
    sc = 'scorer' in str(r.get('capture', '')) + str(r.get('launch', ''))
    pts = [r['from_um']] + list(r['regs_um']) + [r['to_um']]
    xs, ys = zip(*pts)
    ax.plot(xs, ys, '-o' if sc else '-', color='#d62828' if sc else '#3a86ff', lw=2.5 if sc else 0.5, ms=4, alpha=1 if sc else 0.5, zorder=5 if sc else 3)
    if sc:
        ax.annotate('scorer %s b' % r['bits'], r['to_um'], fontsize=10, color='#d62828')
ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect('equal')
ax.set_title('%s  bus %s: scorer row (red) + other rows (blue), plan base0+d6e+scorer 9fadbce8' % (tn, bus))
fig.savefig(out, dpi=80, bbox_inches='tight')
