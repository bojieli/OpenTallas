import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,'tools/die_plan')
import schema as S,die_trial as D
P=S.Plan(json.load(open(sys.argv[1])));s=D.SiteMap(P)
r=json.load(open(sys.argv[2]));t=json.load(open(sys.argv[3]));fig,axes=plt.subplots(5,2,figsize=(13,22))
for ax,e in zip(axes.flat,r['repairs']):
 a=t['sites'][e['parent']];b=t['sites'][e['child']];ch=[a]+e['sites']+[b]
 xs=[p[0] for p in ch];ys=[p[1] for p in ch];x0,x1=min(xs)-70,max(xs)+70;y0,y1=min(ys)-70,max(ys)+70
 for x,y,u,v,_ in s.forb:
  if u<x0 or x>x1 or v<y0 or y>y1:continue
  ax.add_patch(Rectangle((x,y),u-x,v-y,color='grey',alpha=.25))
 ax.plot(*zip(a,b),'r--',lw=1,label='old unrepeatable span')
 ax.plot(*zip(*e['poly']),'k:',lw=.7,label='legal A* channel path')
 ax.plot(*zip(*ch),'o-',color='green',ms=5,label='new inverter chain')
 ax.scatter([a[0],b[0]],[a[1],b[1]],c=['blue','orange'],s=40,zorder=3)
 ax.set_xlim(x0,x1);ax.set_ylim(y0,y1);ax.set_aspect('equal');ax.tick_params(labelsize=7)
 ax.set_title(e['parent']+' -> '+e['child']+'\n'+str(e['added'])+' inv; max hop '+str(round(e['max_hop_um'],2))+' um',fontsize=9)
axes[0,0].legend(fontsize=7)
fig.suptitle('S81 actual clock repeater reach fix: ten edges, 22 inverters; geometry only',fontsize=13);fig.tight_layout();fig.savefig(sys.argv[4],dpi=130)
