import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent;d=json.load(open(p/'prog_static_proposal.json'));w=json.load(open(p/'prog_Ewrite_cohort.json'));m=json.load(open(p/'prog_readmux.json'))
fig,axs=plt.subplots(1,2,figsize=(15,8))
for ax in axs:
 for c in d['obstacles']:
  a,b,x,y=c['box'];ax.add_patch(Rectangle((a,b),x-a,y-b,color='lightgray',alpha=.6))
 for o in m['outputs']:
  a,b,x,y=o['ff']['box'];ax.add_patch(Rectangle((a,b),x-a,y-b,color='purple'))
 for c in d['placements']:
  a,b,x,y=c['box'];col={'readmux_core':'#2677b5','write_capture':'#d95120','write_restore':'#e3a620'}[c['role']]
  ax.add_patch(Rectangle((a,b),x-a,y-b,color=col))
 for b in w['cohort']:ax.plot([263.54,270.648],[b['piny'],b['piny']],color='green',lw=.3,alpha=.5)
 ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_xlabel('x (um)');ax.set_ylabel('y (um)')
axs[0].set_xlim(260,351);axs[0].set_ylim(80,183);axs[0].set_title('STATIC proposal: blue mux core, purple unchanged output FF')
axs[1].set_xlim(262,279);axs[1].set_ylim(112,130)
axs[1].add_patch(Rectangle((263.544,127.164),7.074,2.46,fill=False,edgecolor='red',ls='--',label='existing routing-only corner keepoff'))
axs[1].axvline(270.618,color='black',ls=':',lw=.6)
axs[1].set_title('136 paired captures: orange FF / gold INV; green pin escape')
fig.suptitle('PROG actual-GRT-based placement proposal — no P&R or timing qualification')
fig.tight_layout();fig.savefig(p/'prog_static_proposal.png',dpi=170)
