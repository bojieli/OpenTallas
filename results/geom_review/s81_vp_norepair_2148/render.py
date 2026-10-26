from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parents[3];p=json.load(open(r/'physical/die_plan/s81/die_plan.json'))
types=['ot_s81sl_leaf__t1','ot_s81sl_leaf__t17','ot_s81sl_leaf__t34','ot_s81sl_leaf__t53','ot_s81sl_leaf__t55','ot_s81sl_leaf__t56','ot_s81sl_leaf__t65']
fig,axs=plt.subplots(2,4,figsize=(20,9),dpi=130)
for ax,tn in zip(axs.flat,types):
 t=p['partition_types'][tn];W,H=t['outline_um'];ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1,ec='black'))
 for c in t.get('channels',[]):
  a,b,x,y=c['rect_um'];ax.add_patch(Rectangle((a,b),x-a,y-b,fc='khaki',alpha=.4))
 for h in t.get('hard_cores',[]):
  x,y=h['origin_um'];w,ht=h['outline_um'];isvp=h['module'].endswith('_r0c0');ax.add_patch(Rectangle((x,y),w,ht,fc='tab:blue' if isvp else '#d1d5db',ec='black',alpha=.8,lw=.5))
  if isvp:
   a,b=174.12,29.736;ax.add_patch(Rectangle((x,y),a,b,fill=False,ec='red',ls='--',lw=.9));ax.text(x,y+ht+5,h['inst'].split('.')[-1]+' '+h.get('orient','R0'),size=6,color='blue')
 for c in t.get('clock',{}).get('taps',[]):
  if 'xy' in c:ax.plot(*c['xy'],marker='*',color='darkorange',ms=4)
 ax.set_xlim(-20,W+20);ax.set_ylim(-20,H+20);ax.set_aspect('equal');ax.set_title(tn,size=10);ax.tick_params(labelsize=6);ax.set_xlabel('um',size=7)
axs.flat[-1].axis('off');fig.suptitle('True S81 VP r0c0 macro swap: blue=new; dashed red=old r2c2; grey=unchanged hard cores. Representative leaf placement samples; no route or closure claim.',size=12);fig.tight_layout()
out=r/'results/geom_review/s81_vp_norepair_2148';out.mkdir(parents=True,exist_ok=True);fig.savefig(out/'leaf_samples.png')
