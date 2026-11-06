from pathlib import Path
import json,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).parent;data=json.loads((R/'render_inputs.json').read_text());fig,axes=plt.subplots(1,len(data),figsize=(7,7))
axes=[axes] if len(data)==1 else axes
for ax,(tn,a) in zip(axes,data.items()):
 w,h=a['outline_um'];ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=1.5))
 for c in a['hard_cores']:
  x,y=c['origin_um'];ww,hh=c['outline_um'];ax.add_patch(Rectangle((x,y),ww,hh,facecolor='#c8c8c8',edgecolor='#666',lw=.5))
 bins=a['bins'];ax.scatter([r[0] for r in bins],[r[1] for r in bins],s=[max(1,math.sqrt(r[2])) for r in bins],c='#2d76ac',alpha=.35,linewidths=0)
 taps=a['taps'];ax.scatter([r[1] for r in taps],[r[2] for r in taps],marker='x',s=18,c='#d1382b',linewidths=.7)
 ax.set_title(tn.replace('__','\n')+'\n'+str(len(taps))+' taps',fontsize=8);ax.set_aspect('equal');ax.set_xlim(-20,w+20);ax.set_ylim(-20,h+20);ax.tick_params(labelsize=6);ax.set_xlabel('µm',fontsize=7)
fig.suptitle('QC EAST measured-density tap proposal\nRetained soft sinks (blue), proposed taps (red), macros (grey)\nPlan estimate; source windows unchanged; no CTS/sign-off claim',fontsize=10);fig.tight_layout(rect=(0,0,1,.91));fig.savefig(R/'tap_split_geometry.png',dpi=160)
