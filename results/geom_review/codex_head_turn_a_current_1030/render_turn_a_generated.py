import json,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
b=Path(__file__).parent;d=json.load(open(b/'turn_a_generated_geometry.json'));t=d['type'];c=t['clock'];lc=d['landing']
rect=[float(x) for x in re.search(r'export DIE_AREA = (.*)',d['config']).group(1).split()]
fig,ax=plt.subplots(figsize=(5,14));ax.set(xlim=(-15,190),ylim=(-12,1050),aspect='equal',xlabel='um',ylabel='um',title='hd_turn_a actual generated kit: legal88')
ax.add_patch(Rectangle((0,0),rect[2],rect[3],fill=False,ec='k'))
for row in c['landing_contract']['bands'].values():
 x0,y0,x1,y1=row['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='lightblue',ec='blue',alpha=.45))
p=d['pins'];ax.scatter([q['x'] for q in p],[q['y'] for q in p],s=2,c='grey',label='actual generated pins')
for name,xy in c['landing_status_anchors'].items():
 ax.scatter(*xy,c='orange',s=25);ax.annotate(name,xy,fontsize=5)
o=c['landing_reader_start']['origin_rect_um'];ax.add_patch(Rectangle((o[0],o[1]),o[2]-o[0],o[3]-o[1],fill=False,ec='purple'))
path=[c['start_capture_um']]+[q['xy_um'] for q in c['landing_reader_start']['branches']['t_i']['stages']]
ax.plot(*zip(*path),'m.-',label='declared reader START')
for row in c['landing_local_resets']:
 ax.scatter(*row['xy_um'],s=24,c='red');ax.annotate('reset '+row['name'],row['xy_um'],fontsize=6)
for q in c['landing_contract']['pins']:
 if q['name'] in ('cland_tstart_in','cland_fstart_out_t_o','cland_fstart_in_t_i'):
  ax.scatter(*q['xy_um'],c='green',s=30);ax.annotate(q['name'],q['xy_um'],fontsize=6)
ax.scatter(*c['tap_um'],marker='*',s=90,c='brown',label='core clock entry');ax.legend(fontsize=6,loc='upper right');ax.grid(alpha=.15)
fig.tight_layout();fig.savefig(b/'turn_a_generated_geometry.png',dpi=140)
