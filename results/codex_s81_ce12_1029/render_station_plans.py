from pathlib import Path
import json,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
here=Path(__file__).resolve().parent
repo=here.parents[1]
p=json.loads((repo/'physical/die_plan/s81/plan_s13r2.json').read_text())
types=['slice_station__t'+str(i) for i in (8,23,31,43,44,49,52)]
fig,axs=plt.subplots(2,4,figsize=(18,9))
for ax,tn in zip(axs.flat,types):
 t=p['partition_types'][tn];w,h=t['outline_um']
 assert not t.get('hard_cores')
 ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=2))
 def point(face,window):
  q=sum(window)/2
  return {'W':(0,q),'E':(w,q),'N':(q,h),'S':(q,0)}[face]
 for sl in t['ft_slots']:
  a=point(sl['in_face'],sl['in_window_um']);b=point(sl['out_face'],sl['out_window_um'])
  # Centreline guide only; actual stage sites are generated in the kit's Tcl.
  ax.plot([a[0],b[0]],[a[1],b[1]],color='teal',alpha=.55,lw=.5+math.sqrt(sl['width'])/20)
  ax.plot(*a,'o',color='navy',ms=2);ax.plot(*b,'o',color='navy',ms=2)
 for c in t.get('clock',{}).get('edge_clocks',[]):
  x,y=c['tap_um'];ax.plot(x,y,'*',color='darkorange',ms=7)
 ax.set_title(tn+f"\n{len(t['ft_slots'])} bundles; {w:g} × {h:g} µm",fontsize=10)
 ax.set_aspect('equal');ax.grid(alpha=.15)
for ax in list(axs.flat)[len(types):]:ax.axis('off')
fig.suptitle('S81 bound station kit plans: macro-free bundle corridors, forwarded clock entries (orange)\nBus centreline guides shown; actual stage/landing placement and clock/PG are reviewed after PLACE.')
fig.tight_layout();fig.savefig(here/'station_plan_review.png',dpi=150)
