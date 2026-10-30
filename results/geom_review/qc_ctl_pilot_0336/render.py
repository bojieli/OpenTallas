from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=Path('/srv/opentallas-scratch2/claude/codex-qc-ctl-0336');d=json.load(open(b/'plan/plan_qc46.json'));t=d['partition_types']['sle_ctl__cla4f6f12f'];w,h=t['outline_um'];lc=t['clock']['landing_contract']
fig,ax=plt.subplots(figsize=(11,11));ax.add_patch(Rectangle((0,0),w,h,fill=False,color='k'))
for n,v in lc['bands'].items():
 x0,y0,x1,y1=v['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color='orange',alpha=.35));ax.text((x0+x1)/2,(y0+y1)/2,n,fontsize=6,ha='center',va='center',rotation=90 if y1-y0>x1-x0 else 0)
for p in t['buses']:
 f=p['face'];a,z=p['window_um'];col='green' if p['dir']=='in' else 'blue'
 if f in 'EW':x=w if f=='E' else 0;ax.plot([x,x],[a,z],c=col,lw=3)
 else:y=h if f=='N' else 0;ax.plot([a,z],[y,y],c=col,lw=3)
for p in t['clock'].get('taps',[]):x,y=p['xy'];ax.plot(x,y,'r*',ms=11)
tr=lc['collector_tree'];pts={'rst_root_n':tr['root']}
for p in tr['relays']:
 q=p['xy'];prev=pts.get(p['d']);pts[p['q']]=q
 if prev:ax.plot([prev[0],q[0]],[prev[1],q[1]],c='purple',lw=.4,alpha=.4)
 ax.plot(*q,'.',c='purple',ms=2)
ax.set(xlim=(-30,w+30),ylim=(-30,h+30),aspect='equal',xlabel='um',ylabel='um',title='QC ctl pilot plan46: planned resized ring bands + clocks/reset\nGreen input / blue output windows; orange ring reserves; red glue taps / purple reset relays\nNo actual placement or timing claim')
fig.tight_layout();fig.savefig(b/'plan/ctl46_plan.png');plt.close(fig)
