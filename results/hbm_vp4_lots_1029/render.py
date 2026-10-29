import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;d=json.load(open(P/'vp4_lot_candidates.json'));plan=json.load(open(sys.argv[1]));fig,axes=plt.subplots(2,2,figsize=(13,10))
for ax,r in zip(axes.flat,d['results']):
 t=plan['partition_types'][r['type']];a=r['nearby_partial_pack_candidates'][0];old=r['old_origin_um'];ow,oh=r['old_outline_um'];x,y=a['origin_um'];xc,yc=old[0]+ow/2,old[1]+oh/2
 ax.set_xlim(xc-700,xc+700);ax.set_ylim(yc-700,yc+700);ax.set_aspect('equal')
 cs={c['inst']:c for c in t['hard_cores']}
 for n,c in cs.items():
  xx,yy=c['origin_um'];w,h=c['outline_um'];ax.add_patch(Rectangle((xx,yy),w,h,fc='#dce4ec',ec='#6a8199',lw=.4))
 for c in t['contents']:
  if c['inst']in cs or 'origin_um'not in c:continue
  xx,yy=c['origin_um'];w,h=c['outline_um'];ax.add_patch(Rectangle((xx,yy),w,h,fc='#eeeecc',ec='#aaaa77',lw=.4))
 pts=[p for s in t['internal_stations']for p in s['regs_um']];ax.scatter([p[0]for p in pts],[p[1]for p in pts],s=.5,c='#777777',alpha=.25)
 for h in a['solid_colliders']:
  xx,yy,xxx,yyy=h['rect_um'];ax.add_patch(Rectangle((xx,yy),xxx-xx,yyy-yy,fc='#ffcc88',ec='#bb6600',lw=1))
 ax.add_patch(Rectangle(old,ow,oh,fill=False,ec='#0044ff',lw=1.5));ax.add_patch(Rectangle((x,y),501.12,311.04,fill=False,ec='#cc0000',lw=2))
 ax.set_title(r['type']+' '+r['inst']+'\nRED conditional candidate; ORANGE conflicting lots\n'+str(a['station_site_collisions'])+' station conflicts, '+str(a['endpoint_legs_over405'])+' endpoint legs >405',fontsize=9)
fig.suptitle('VP4 enlargement: no isolated all-obstacle legal lot (ESTIMATE FAIL)',fontsize=14);fig.tight_layout();fig.savefig(P/'nearby_conflicts.png',dpi=150)
