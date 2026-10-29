import json, gzip
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
p=Path(__file__).parent
t=json.loads(gzip.decompress((p/'tree_a1.json.gz').read_bytes())); plan=json.loads(gzip.decompress((p/'plan_hk4.json.gz').read_bytes())); nodes=t['nodes']
fig,axs=plt.subplots(1,2,figsize=(15,8))
for ax in axs:
 for part in plan['partitions']:
  x,y=part['origin_um']; w,h=plan['partition_types'][part['type']]['outline_um']
  ax.add_patch(Rectangle((x,y),w,h,facecolor='#edf1f4',edgecolor='#aab4bf',linewidth=.4))
 edges=[]
 for n in nodes.values():
  if n['parent'] is None: continue
  q=nodes[str(n['parent'])]; edges.append([(q['x'],q['y']),(n['x'],n['y'])])
 ax.add_collection(LineCollection(edges,colors='#5881a0',linewidths=.5))
 for pol,col in [(0,'#286f44'),(1,'#d26323')]:
  ns=[n for n in nodes.values() if n.get('pol',0)==pol]
  ax.scatter([n['x'] for n in ns],[n['y'] for n in ns],s=4,c=col,label='True branch' if pol==0 else 'Inverted branch')
 ax.set_aspect('equal'); ax.set_xlabel('um'); ax.set_ylabel('um')
axs[0].set_xlim(0,17522);axs[0].set_ylim(0,17556);axs[0].set_title('HEAD hk4 diagnostic: alternating DME + FEED')
axs[1].set_xlim(6500,11000);axs[1].set_ylim(6500,11500);axs[1].set_title('Centre feed / relay detail');axs[1].legend(loc='upper right')
fig.tight_layout();fig.savefig(p/'tree_review.png',dpi=140)
