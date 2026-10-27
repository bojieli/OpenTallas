import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Patch
from pathlib import Path
base=Path('/srv/opentallas-scratch/claude/codex-hbm-2001/buddy')
fig=plt.figure(figsize=(19,15));gs=fig.add_gridspec(3,1,height_ratios=[5,5,1.2]);axes=[fig.add_subplot(gs[i]) for i in range(2)]
for ax,part in zip(axes,['NW','NE']):
 t=json.load(open(base/(part+'_final.json')));r=json.load(open(base/(part+'_final.json.report.json')));W,H=t['outline_um']
 for s in t['internal_stations']:
  if s.get('serial_k',1)>1:
   p=[s['from_um']]+s.get('regs_um',[])+[s['to_um']]
   ax.plot([q[0] for q in p],[q[1] for q in p],color='#f97316',lw=.16,alpha=.06,zorder=1)
 for h in t['hard_cores']:
  n=h['inst']; x,y=h['origin_um'];w,hh=h['outline_um'];col='#cbd5e1'
  if n.startswith('u_vmb_'):col='#60a5fa'
  elif n.startswith('u_mu_fused_n'):col='#86efac'
  elif n.startswith('u_mu_fused_'):col='#f9a8d4'
  elif n.startswith('u_mu_keybuf_'):col='#fde68a'
  ax.add_patch(Rectangle((x,y),w,hh,facecolor=col,edgecolor='#475569',lw=.5,zorder=2))
  if col!='#cbd5e1':ax.text(x+w/2,y+hh/2,n.replace('u_mu_','').replace('u_vmb_','VM'),fontsize=3.5,ha='center',va='center',clip_on=True,zorder=3)
 for s in t['internal_stations']:
  a,c=s.get('launch',''),s.get('capture','');isvm=('u_mu_fused_'in a and'u_vmb_'in c)or('u_vmb_'in a and'u_mu_fused_'in c);istree=s['conn'].startswith('mu_tree')
  if not(isvm or istree):continue
  p=[s['from_um']]+s.get('regs_um',[])+[s['to_um']]
  ax.plot([q[0] for q in p],[q[1] for q in p],color='#dc2626'if isvm else'#15803d',lw=.9 if isvm else .35,alpha=.85 if isvm else .55,zorder=4)
  if istree and s.get('regs_um'):ax.scatter([q[0] for q in s['regs_um']],[q[1] for q in s['regs_um']],s=1,c='#15803d',zorder=4)
 ax.axvline(3957.12,color='#d97706',ls='--',lw=1)
 ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',title=f"{part}: all 48 native VM links parallel, direct gap / 14 local tree nodes / cut max {r['max_axis']:.3f} <= 0.600")
 ax.set_xlabel('um');ax.set_ylabel('um')
axes[0].legend(handles=[Patch(facecolor='#60a5fa',label='Native VM: four macros'),Patch(facecolor='#f9a8d4',label='FUSED lane'),Patch(facecolor='#86efac',label='Golden tree node'),Patch(facecolor='#fde68a',label='IDXN key buffer'),Patch(facecolor='#f97316',label='Other serialized legs (orange overlay)')],loc='upper left',fontsize=8)
ax=fig.add_subplot(gs[2]);ax.set(xlim=(0,20),ylim=(0,2));ax.axis('off')
ax.add_patch(Rectangle((8.5,.1),3,1.7,facecolor='#fef3c7',edgecolor='#92400e'))
ax.text(10,.95,'CENTRAL ROOT RESERVE\n1 x 345.6 x 345.6 um = 0.11944 mm2\nUNPLACED: real root integration remains',ha='center',va='center',fontsize=9)
ax.annotate('NW two quadrant roots\n542 up + 346 down = 888 bits',xy=(8.4,.95),xytext=(4.3,.95),ha='center',va='center',arrowprops={'arrowstyle':'->'},fontsize=9)
ax.annotate('NE two quadrant roots\n542 up + 346 down = 888 bits',xy=(11.6,.95),xytext=(15.8,.95),ha='center',va='center',arrowprops={'arrowstyle':'->'},fontsize=9)
fig.suptitle('Native MU architecture model: new pin plans, clock/PG/reset, root placement and real timing are still required',fontsize=13)
fig.tight_layout();fig.savefig(base/'review_final.png',dpi=150)
