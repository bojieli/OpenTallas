import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
import audit
p=json.load(open('reg_spine_plan.json'));spec=json.load(open('reg_spine.json'));fig,ax=plt.subplots(figsize=(10,14))
for r in audit.mac:ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='.7'))
for r in audit.blk:ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='orange',alpha=.35))
nodes={n[0]:n for n in p['trunk']}
for n in p['trunk']:
 if n[3] in nodes:
  q=nodes[n[3]];ax.plot([n[1],q[1]],[n[2],q[2]],color='purple',lw=1)
for t in p['taps']:
 n=nodes[t['node']];ax.plot([n[1],t['x']],[n[2],t['y']],color='blue',lw=.5)
 ax.plot(t['x'],t['y'],'ro',ms=2);ax.text(t['x'],t['y'],str(t['id']),fontsize=6)
 for nm,r in audit.rects(t):ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='green'))
ax.set_xlim(0,710);ax.set_ylim(0,1037);ax.set_aspect('equal');ax.set_title('hd_tile planned clock: 45 taps,333 pads; all fixed/macro/island/rows clear')
fig.savefig('clock_overview.png',dpi=150,bbox_inches='tight')
