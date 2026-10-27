import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
k=sys.argv[1];c=json.load(open(k+'/pv_clock_census.json'));fig,ax=plt.subplots(figsize=(7,7))
for r in c['pg_M5']:
 if r[0]<92 and r[2]>81:ax.add_patch(Rectangle((r[0],81),r[2]-r[0],11,color='orange',alpha=.45))
ax.add_patch(Rectangle((82.08,82.08),8.64,8.64,fill=False,ls='--',ec='navy',label='plan clock/reset entry island'))
ax.add_patch(Rectangle((86.238,86.4),.378,.27,fc='lime',ec='green',label='1 BUFx4 planned trunk'))
ax.scatter([86.424,86.808],[86.4,86.4],c=['red','blue'],s=25)
ax.plot([86.424,86.427],[86.4,86.535],c='red');ax.annotate('clk 86.424,86.4',(86.424,86.4),xytext=(83,85),arrowprops={'arrowstyle':'->'});ax.annotate('rst_n unchanged',(86.808,86.4),xytext=(87.2,85),arrowprops={'arrowstyle':'->'})
ax.set_xlim(81,92);ax.set_ylim(81,92);ax.set_aspect('equal');ax.set_title('PV join R0 pass2 planned entry trunk\n1 BUFx4 -> single CTS-open domain:15763 sinks; no added cycle');ax.legend(loc='upper left');ax.set_xlabel('um');ax.set_ylabel('um');fig.tight_layout();fig.savefig(k+'/pv_trunk_plan.png',dpi=150)
