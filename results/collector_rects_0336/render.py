from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=Path('/srv/opentallas-scratch2/claude/codex-qc-kits-0336/collector_budget');o=Path('/srv/opentallas-scratch2/claude/wt/codex-collector-rects-0336/results/collector_rects_0336');p=json.load(open(b/'candidate_plan.json'));t=p['partition_types']['sle_fw_v3'];c=t['clock']['landing_contract'];budget=json.load(open(o/'budget.json'));new=budget['shared_rect_um'];old=[153.36,500.04,157.68,504.36]
fig,(a,z)=plt.subplots(1,2,figsize=(11,8),gridspec_kw={'width_ratios':[1,1.7]})
for ax in (a,z):
 for name,band in c['bands'].items():
  x0,y0,x1,y1=band['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#93b6d6',edgecolor='#3a668b',alpha=.5))
  if ax is z and 450<y0<610:ax.text((x0+x1)/2,(y0+y1)/2,name,fontsize=7,clip_on=True,ha='center',va='center')
 for r,color,label in [(old,'#c93434','old shared 4.32um box'),(new,'#189447','new shared 9.72um box')]:
  x0,y0,x1,y1=r;ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor=color,lw=2,label=label))
 ax.plot(155.52,502.2,'k*',markersize=9,label='unchanged clock/reset node')
 ax.set_aspect('equal');ax.set_xlabel('x (um)');ax.set_ylabel('y (um)');ax.grid(alpha=.15)
a.set_xlim(0,t['outline_um'][0]);a.set_ylim(0,t['outline_um'][1]);a.set_title('sle_fw_v3: same parent outline')
z.set_xlim(110,205);z.set_ylim(475,535);z.annotate('17 mapped cells\n6.561 um² total .4 reserve\n94.4784 um² shared bay',xy=(129.6,502.2),xytext=(112,520),fontsize=9,arrowprops={'arrowstyle':'->','color':'#189447'})
z.set_title('Collector cohort clears rd_ei ring');z.legend(loc='lower right',fontsize=8)
fig.suptitle('Physical-only model: 0 RTL / cycle changes; all relay nodes, taps and public pins unchanged\nConservative affected hops: reset/status <=374.76um, clock <=39.96um; actual occupancy and G1 pending',fontsize=11)
fig.tight_layout();fig.savefig(o/'collector_model.png',dpi=150)
