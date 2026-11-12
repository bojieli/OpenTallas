"""type render: hard cores + named ft slots' stations (type frame) + their in/out windows. usage: PLAN TYPE OUT SLOT..."""
import json, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pl, tn, out = sys.argv[1:4]; slots = sys.argv[4:]
t = json.load(open(pl))['partition_types'][tn]; W, H = t['outline_um']
fig, ax = plt.subplots(figsize=(8, 8 * H / W + 1), facecolor='white')
ax.add_patch(Rectangle((0, 0), W, H, fc='#f7f7f7', ec='k'))
for h in t['hard_cores']:
    ax.add_patch(Rectangle(h['origin_um'], *h['outline_um'], fc='#bbbbbb', ec='k', lw=0.4))
for m in t.get('macros', []) or []:
    if 'rect_um' in m:
        x0, y0, x1, y1 = m['rect_um']; ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#9999cc', ec='k', lw=0.3))
cols = ['#d62828', '#2a9d8f', '#f77f00', '#7b2cbf', '#3a86ff', '#e76f51']
fs = {s['name']: s for s in t.get('ft_slots', [])}
for i, sn in enumerate(slots):
    s = fs.get(sn)
    if not s: print('no slot', sn); continue
    c = cols[i % len(cols)]
    r = s.get('regs_um') or []
    if r:
        xs, ys = zip(*r); ax.plot(xs, ys, '-o', color=c, ms=3, lw=1, label='%s k%s %s->%s' % (sn, s.get('stations'), s.get('in_face'), s.get('out_face')))
    for k in ('in_window_um', 'out_window_um', 'in_um', 'out_um'):
        if k in s: print(sn, k, s[k])
ax.legend(fontsize=7, loc='lower left'); ax.set_aspect('equal'); ax.set_title(tn, fontsize=9)
fig.savefig(out, dpi=70, bbox_inches='tight')
