from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
w=Path('/srv/opentallas-scratch2/claude/wt/codex-sc-cap-0336');o=w/'results/sc_cap_child_0336';p=json.load(open(o/'pins.json'));fig,ax=plt.subplots(figsize=(7,10));W,H=p['outline_um'];ax.add_patch(Rectangle((0,0),W,H,fill=False,color='black'));ax.add_patch(Rectangle((4.32,4.32),W-8.64,H-8.64,fill=False,color='grey',linestyle=':'))
for dr,col in [('in','#225ea8'),('out','#d7301f')]:
 q=[q for q in p['pins'] if q['dir']==dr];ax.scatter([q['x'] for q in q],[q['y'] for q in q],s=9,c=col,label=dr)
labels=[(5,480,'N119 outputs + N160 cfg/AM\nunchanged source bit correspondence'),(W-5,35,'E48 up_o + dn_i\nE403.440um proxy'),(7,247,'W48 dn_o + up_i\nW345.600um proxy'),(W-5,475,'VM input bank\nexisting pd8'),(35,25,'reduction inputs\nexisting fixed6 + strap'),(125,25,'VM upper enables\nexisting pd6')]
for x,y,t in labels:ax.text(x,y,t,fontsize=8,ha='right' if x>W/2 else 'left',va='center')
ax.text(12,15,'ck / rst_n',fontsize=8);ax.set_xlim(-15,W+15);ax.set_ylim(-15,H+15);ax.set_aspect('equal');ax.set_xlabel('child local x (um)');ax.set_ylabel('child local y (um)');ax.set_title('SC complete existing child: 253.2 x 505.44 um\n572 unchanged bits; track/PG checks 0; CONDITIONAL only');ax.legend(loc='center');fig.tight_layout();fig.savefig(o/'pin_plan.png',dpi=160)
