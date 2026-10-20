#!/usr/bin/env python3
"""Unplaced geometric plan, never a placement-density receipt."""
from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path.cwd();fp=json.loads((r/'physical/ref_tile/qkd_hr_cdc_pc_sram1/floorplan.json').read_text())
out=r/'results/arch/kv_host_cdc_safe_1020/pc_preflight'
fig,ax=plt.subplots(figsize=(7,7.7));W,H=fp['die'][2:];ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=2))
for n,b in enumerate(fp['blocks']):
 x,y,w,h=[b[k] for k in ('x','y','w','h')]
 ax.add_patch(Rectangle((x-10.8,y-10.8),w+21.6,h+21.6,color='#dfe9f4',alpha=.6))
 ax.add_patch(Rectangle((x,y),w,h,facecolor='#719fc7',edgecolor='#315778'))
 ax.text(x+w/2,y+h/2,('RX' if n<2 else 'TX')+'\n'+('input32x546' if n%2==0 else 'dual32x546')+'\n177.768 x160.392',ha='center',va='center',fontsize=9)
ax.axhspan(214.392,291.6,color='#eaf3d7',alpha=.7)
ax.text(W/2,252,'77.208um clear band after halos\nStd cells:2931.76um2; estimated2.2% of open area',ha='center',va='center',fontsize=9)
for x,c in [(0,'core CK W [242,260]'),(W,'phy CK E [260,278]')]:
 ax.plot([x,x],[204,302],color='#c55342',lw=4);ax.text(x+(7 if x==0 else -7),310,c,ha='left' if x==0 else 'right',fontsize=8,rotation=90 if x==0 else -90)
ax.text(W/2,H+8,'N: core RX data+valid/credits/faults',ha='center',fontsize=9)
ax.text(W/2,-18,'S: PHY TX data+valid/credits',ha='center',fontsize=9)
ax.set(xlim=(-25,W+25),ylim=(-30,H+30),xlabel='um',ylabel='um',aspect='equal')
ax.set_title('PC SRAM candidate: PLANNED GEOMETRY\n475.2 x518.4um; not placed/routed; no density measurement')
ax.grid(alpha=.12);fig.tight_layout();fig.savefig(out/'floorplan_plan.png',dpi=150);plt.close(fig)
fig,ax=plt.subplots(figsize=(7,3.5));ax.bar(['SRAM macro area','Mapped std area','Remaining outline'],[114050.260224,2931.761156,W*H-116982.02138],color=['#719fc7','#85ad54','#ddd']);ax.set_ylabel('um2');ax.set_title('Synthesis area budget, NOT placed density\nTotal measured116982.02um2 / envelope246343.68um2 =47.49%');fig.tight_layout();fig.savefig(out/'density_budget_plan.png',dpi=150)
