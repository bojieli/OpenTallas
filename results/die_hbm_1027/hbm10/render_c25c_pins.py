"""Render the two C25c pin/outline changes and immediate parent neighbours."""
import json,sys
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D=Path(sys.argv[1]);P=json.load(open(D/'die_plan.json'));fig,axs=plt.subplots(2,2,figsize=(13,11))
for ax,mod in zip(axs[0],('ot_hgi_sm_xload_cl2_bdring','ot_hgi_qw_dec')):
 c=next(c for t in P['partition_types'].values() for c in t.get('hard_cores',[]) if c['module']==mod);w,h=c['outline_um'];pins=json.load(open(D/c['pins_file']))
 ax.add_patch(Rectangle((0,0),w,h,facecolor='#eff6fc',edgecolor='black'));ax.scatter([p['x'] for p in pins],[p['y'] for p in pins],s=2)
 ck=[p for p in pins if p['name']=='clk'];ax.scatter([p['x'] for p in ck],[p['y'] for p in ck],s=90,c='red',marker='*',label='clock unchanged in parent')
 ax.set(xlim=(-12,w+12),ylim=(-12,h+12),title=f'{mod}\n{w:g} x {h:g} um, {len(pins)} pins');ax.set_aspect('equal');ax.legend(fontsize=8)
for ax,tn in zip(axs[1],('q_hub_nw','q_hub_ne')):
 t=P['partition_types'][tn]
 for c in t['hard_cores']:
  x,y=c['origin_um'];w,h=c['outline_um'];hit='bdring' in c['module'];ax.add_patch(Rectangle((x,y),w,h,facecolor='#e55b4f' if hit else '#dbe5ee',edgecolor='#777',linewidth=.5))
  if hit:ax.text(x+w/2,y+h/2,c['inst'],ha='center',fontsize=6,rotation=90)
 ax.set(xlim=(600,4600),ylim=(3100,4000),title=f'{tn}: bdring neighbourhood, zero overlaps');ax.set_aspect('equal')
fig.tight_layout();fig.savefig(D/'c25c_pins.png',dpi=160)
