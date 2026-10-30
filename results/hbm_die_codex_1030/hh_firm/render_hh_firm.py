import sys,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
sys.path.insert(0,sys.argv[1]+'/tools/die_plan')
import schema as S
from matplotlib.patches import Rectangle
p=json.load(open(sys.argv[2]));fig,axs=plt.subplots(1,3,figsize=(18,8))
for ax,tn in zip(axs,['q_b112','root','q_b112__physical_v1']):
 t=p['partition_types'][tn];W,H=t['outline_um']
 for x,y,xx,yy in S.placed_macro_boxes(t,halo=4.32).values():ax.add_patch(Rectangle((x,y),xx-x,yy-y,fc='#d5d9dc',ec='#7d858d',lw=.3))
 for s in t['ft_slots']:
  if not s['name'].startswith(('L700','L701')):continue
  col='#ba3a24' if s['name'].startswith('L700') else '#2161a4'
  for j,st in enumerate(s['bit_sites_um']):
   a=np.array(st);ax.scatter(a[:,0]+.702,a[:,1]+.135,s=.3,color=col,rasterized=True)
  a=np.array(s['bit_sites_um'][0]);ax.annotate(s['name'],(a[:,0].mean(),a[:,1].mean()),fontsize=8,color=col)
 if tn=='root':ax.set_xlim(0,W);ax.set_ylim(6400,7550);ax.set_title('root (HH corridor crop)')
 else:ax.set_xlim(0,W);ax.set_ylim(0,H);ax.set_title(tn)
 ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.grid(alpha=.15)
fig.suptitle('HH same-cycle per-bit site candidate: red L700 / blue L701; grey hardcore +4.32um halos\nPlan allocation only. Actual cell placement, clock, reset, START, PG and routed gates remain OPEN.',fontsize=13)
fig.tight_layout();fig.savefig(sys.argv[3],dpi=140)
