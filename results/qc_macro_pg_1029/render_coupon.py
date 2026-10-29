import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
inv=json.load(open(sys.argv[1]));plan=json.load(open(sys.argv[2]));pg=json.load(open(sys.argv[3]));fig,ax=plt.subplots(1,2,figsize=(14,7));D=plan['dbu']
for m in inv['macros']:
 x,y,X,Y=[q/D for q in m['bbox_dbu']];ax[0].add_patch(Rectangle((x,y),X-x,Y-y,facecolor='#edf0f4',edgecolor='#c5cbd3',linewidth=.3))
for n,col in [('VDD','#e03c31'),('VSS','#1764b2')]:
 q=[c for c in plan['contacts'] if c['net']==n];ax[0].scatter([c['xy_dbu'][0]/D for c in q],[c['xy_dbu'][1]/D for c in q],s=2,c=col,label=n)
ax[0].set(xlim=(0,31216.32),ylim=(0,26265.6),title='377 macros / 754 native PG contact coupon',xlabel='um',ylabel='um');ax[0].legend();ax[0].set_aspect('equal')
c=plan['contacts'][0];xx,yy=[q/D for q in c['xy_dbu']];m=next(m for m in inv['macros'] if m['inst']==c['inst'])
for p in m['pins']:
 for ly,x,y,X,Y in p['shapes_dbu']:
  if x/D>xx+1 or X/D<xx-1 or y/D>yy+1 or Y/D<yy-1:continue
  ax[1].add_patch(Rectangle((x/D,y/D),(X-x)/D,(Y-y)/D,facecolor='#f6a29d' if p['kind']=='POWER' else '#a2c4eb',alpha=.65))
for n,ly,x,y,X,Y in pg:
 if ly=='M8' and y<=yy+1 and Y>=yy-1:ax[1].add_patch(Rectangle((xx-1,y),2,Y-y,facecolor='#e03c31' if n=='VDD' else '#1764b2',alpha=.45))
for ly,r in c['metal_dbu'].items():
 x,y,X,Y=[v/D for v in r];ax[1].add_patch(Rectangle((x,y),X-x,Y-y,fill=False,edgecolor='black',linewidth=1.4))
ax[1].plot(xx,yy,'k+',ms=8);ax[1].set(xlim=(xx-1,xx+1),ylim=(yy-1,yy+1),title=c['inst']+'/'+c['pin']+' actual VIA78 enclosure',xlabel='um',ylabel='um');ax[1].set_aspect('equal');fig.suptitle('Direct same-net M7 pin → M8 stripe; no added wire metal. Diagnostic only, no IR claim.');fig.tight_layout();fig.savefig(sys.argv[4],dpi=160)
