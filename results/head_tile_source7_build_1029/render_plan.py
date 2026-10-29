import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path('run/head_tile_source7_1029');p=json.load(open(r/'head_start_source7/source7/source_plan_statuscopy.json'));t=p['partition_types']['hd_tile'];pins=json.load(open(r/'gen2/hd_tile/pins.json'))
fig,ax=plt.subplots(figsize=(10,13));w,h=t['outline_um'];ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=2))
for c in t['hard_cores']:
 x,y=c['origin_um'];ww,hh=c['outline_um'];ax.add_patch(Rectangle((x,y),ww,hh,color='.75'));ax.text(x+ww/2,y+hh/2,c['inst'].split('.')[-1]+'\n'+c['orient'],ha='center')
for b in t['clock'].get('die_islands_um',[]):ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],color='orange',alpha=.4))
for side,color in [('i','blue'),('o','purple')]:
 q=[q for q in pins if q['bus']==side];ax.scatter([q['x'] for q in q],[q['y'] for q in q],s=3,color=color,label=side+' data pins')
for e in t['reset_start_raw_exports']:
 x,y=e['xy_um'];ax.plot(x,y,'ro',ms=4);ax.text(x+2,y,e['port'],fontsize=5)
for b in t['clock']['landing_contract']['bands'].values():
 x0,y0,x1,y1=b['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ls='--',edgecolor='green',lw=2))
ax.plot(354.24,354.24,'*',ms=15,color='black',label='clock/reset entry')
ax.set_aspect('equal');ax.set_xlim(-15,w+15);ax.set_ylim(-15,h+15);ax.legend(loc='upper left');ax.set_title('SOURCE7 hd_tile trial: native hard cores,15 registered reset exports, same-cycle status-copy +8FF')
fig.savefig('results/head_tile_source7_build_1029/source7_tile_plan.png',dpi=150,bbox_inches='tight')
