from pathlib import Path
import json,gzip,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/s81_head'));import head_tile_clock_legalize as L
p=json.load(open('reg_spine_plan.json'));s=json.load(open('reg_spine.json'));fig,ax=plt.subplots(figsize=(10,14))
for line in gzip.open('blk.tsv.gz','rt'):
 f=line.strip().split('\t');r=list(map(float,f[1:5]))
 if f[0]=='F' and f[5].startswith('ot_'):ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='.7'))
 elif f[0]=='B':ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='orange',alpha=.4))
nodes={n[0]:n for n in p['trunk']}
for n in p['trunk']:
 if n[3] in nodes:
  q=nodes[n[3]];ax.plot([n[1],q[1]],[n[2],q[2]],color='purple',lw=1)
for t in p['taps']:
 n=nodes[t['node']];ax.plot([n[1],t['x']],[n[2],t['y']],color='blue',lw=.5);ax.text(t['x'],t['y'],str(t['id']),fontsize=6)
for g,rs in L.groups(s,p).items():
 for nm,r in rs:ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='green'))
ax.set_xlim(0,710);ax.set_ylim(0,1037);ax.set_aspect('equal');ax.set_title('hd_tile declared FIRM homes:435 clock bodies/332 pads,fullfixed/halo/row clearance')
fig.savefig('clock_overview.png',dpi=150,bbox_inches='tight')
