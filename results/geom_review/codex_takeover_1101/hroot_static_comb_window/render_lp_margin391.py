from pathlib import Path
import json,sys
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');rows=json.load(open(P/'current_graph_lp_margin391.json'))
fig,axs=plt.subplots(1,2,figsize=(16,7),sharey=True)
for ax,r in zip(axs,rows):
 xs=[];ys=[]
 for c in D.cells.values():
  if c[0]=='S':x,y=g.ctr(c);xs.append(x);ys.append(y)
 ax.scatter(xs,ys,s=.15,c='#9aaab0',alpha=.3)
 for z in r['targets']:
  x,y=z['old'];xx,yy=z['new'];reset='u_rrl_101/' in z['name'];color='#cf2c58' if reset else '#087ca7'
  ax.annotate('',(xx,yy),(x,y),arrowprops=dict(arrowstyle='->',color=color,lw=.8,alpha=.8));ax.scatter([xx],[yy],s=10,color=color)
  if reset:ax.text(xx+8,yy+8,'existing reset101',fontsize=8,color=color)
 ax.set(xlim=(0,1900.8),ylim=(0,838.08),xlabel='x (um)',title=f"Current graph static variant {r['variant']}: 65 existing FF moves\n80 allowed endpoints; fullgraph 391.00um / zero >405")
 ax.grid(alpha=.15)
axs[0].set_ylabel('y (um)');fig.suptitle('Continuous PREP only: paired landing translations + existing endpoints\nNo legal-site/TAP/PG/pin/clock qualification; 14um reach margin before legalization; no physical dispatch')
fig.tight_layout();fig.savefig(P/'current_graph_lp_margin391.png',dpi=160)
