#!/usr/bin/env python3
import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(sys.argv[1]);plan=json.load(open(r/'../inputs/event/plan_sites_astk.json'));st=json.load(open(r/'start_stages.json'));g=json.load(open(r/'native_graph.json'))
boxes=[]
for p in plan['partitions']:
 t=plan['partition_types'][p['type']];wh=t.get('size_um', t.get('outline_um'));xy=p['origin_um'];boxes.append((xy,wh,p['name']))
print('type keys',list(next(iter(plan['partition_types'].values()))))
fig,ax=plt.subplots(figsize=(12,19));
for xy,wh,name in boxes:
 if wh is None:continue
 ax.add_patch(Rectangle(xy,wh[0],wh[1],facecolor='#e5eef5',edgecolor='#899aa9',linewidth=.3))
by={x['region']:[(x['rect_um'][0]+x['rect_um'][2])/2,(x['rect_um'][1]+x['rect_um'][3])/2] for x in st['stages']}
for e in g['start_edges']:
 a,b=by.get(e['src']),by.get(e['dst'])
 if a and b:ax.plot([a[0],b[0]],[a[1],b[1]],color='#d89c43',linewidth=.45,alpha=.7)
ax.scatter([p[0] for p in by.values()],[p[1] for p in by.values()],s=2,c='#b1272c',label='1139 legal START stage rows')
ax.autoscale();ax.set_aspect('equal');ax.set_title('KV native-clock START: 160 partition origins, bounded neighbour hops\n1139 stages / 4464 FF; row-envelope max394.537um (405um rule)\nClock load / sourceDB / real START pin update pending');ax.set_xlabel('die x (um)');ax.set_ylabel('die y (um)');ax.legend(loc='upper right');fig.tight_layout();fig.savefig(r/'native_start.png',dpi=130)
