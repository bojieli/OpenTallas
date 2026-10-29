import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
R=Path('/srv/opentallas-scratch/claude/codex-qc-import-0824');g=json.load(open(R/'review_geom.json'));f=json.load(open(R/'fix.json'));src=g['reset']['rst_raw_n']['xy'];sx=(src[0]+src[2])/2;sy=(src[1]+src[3])/2
fig,axs=plt.subplots(1,2,figsize=(14,6))
for ax,m in zip(axs,f['moved']):
 stage='r1_1' if 'u_rst_r1_1' in m['inst'] else 'r3_1'
 for pn,(tn,b) in g['parts'].items():
  if pn not in ['sl_E0_fw','sl_E0_stm']:continue
  ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fc='#f1f5f9',ec='#94a3b8'))
 for tag,color,bb in [('old','#ef4444',m['old']),('new','#16a34a',m['new'])]:
  x0,y0,x1,y1=[v/1000 for v in bb];x=(x0+x1)/2;y=(y0+y1)/2
  ax.scatter([x],[y],s=70,c=color,marker='s',label=f'{tag} first reset FF')
  ax.plot([sx,x,x],[sy,sy,y],color=color,ls='--',alpha=.9)
  ax.text((sx+x)/2,sy-8 if tag=='old' else sy+10,f'{abs(x-sx)+abs(y-sy):.1f} µm centre L1',color=color,fontsize=8)
 ck=g['clock']['t_st_'+stage+'__clk']['xy'];cx=(ck[0]+ck[2])/2;cy=(ck[1]+ck[3])/2
 ax.scatter([cx],[cy],marker='^',c='#2563eb',s=70,label='unchanged native clock tap')
 nx=(m['new'][0]+m['new'][2])/2000;ny=(m['new'][1]+m['new'][3])/2000
 ax.plot([cx,nx],[cy,ny],c='#2563eb',lw=1,label='new local CLK branch (~80 µm)')
 ax.scatter([sx],[sy],marker='*',c='#f59e0b',s=150,label='unchanged native reset output')
 ax.set_xlim(min(sx,nx)-35,max(sx,nx)+35);ax.set_ylim(12265,12495);ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2);ax.set_xlabel('Die x (µm)');ax.set_ylabel('Die y (µm)');ax.set_title(stage+' first receive FF: -79.92 µm y')
 ax.legend(fontsize=7,loc='upper center',bbox_to_anchor=(.5,-.18))
fig.suptitle('QC native reset reach fix: same two FFs, same clock/reset graph, 0 added cycles\nNew type-union body windows required; actual fresh-ODB clearance/reach still pending',fontsize=12);fig.tight_layout(rect=(0,.13,1,.88));fig.savefig(R/'reset_reach_fix.png',dpi=150)
