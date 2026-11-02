from pathlib import Path
import json,sys
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');d=json.load(open(P/'chunk_guides.json'));owner={n:r['chunk']for r in d['groups']for n in r['names']};fig,ax=plt.subplots(figsize=(11,6))
for c in D.cells.values():
 if c[4]<1280 or c[2]>1450 or c[3]>130:continue
 n=c[6].replace(chr(92),'');chunk=owner.get(n);color=plt.cm.tab10(chunk)if chunk is not None else '#bf315c'if c[0]=='S'and'u_cland_i_kvpc_Q_N_o_next/'in n else '#899ba3'
 ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],facecolor=color,edgecolor='none',alpha=.65if chunk is not None else.3))
for r in d['groups']:
 x0,y0,x1,y1=r['box'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,lw=2,edgecolor=plt.cm.tab10(r['chunk'])));ax.text((x0+x1)/2,74,f"native {r['chunk']}\n{r['cells']} cells",ha='center',fontsize=8)
ax.plot([1352.0957,1380.6717],[0,0],color='black',lw=4);ax.set(xlim=(1280,1450),ylim=(-5,130),xlabel='x (um)',ylabel='y (um)',title='STATIC native64-bit chunk guide PREP: 4609/5350 actual combinational cells\nExisting FF/pins/source/clock graph held;84 crosschunk +657 output/unowned unclaimed\nActual current bodies shown; guide capacity/site/TAP/PG/postDPL result not qualified');ax.grid(alpha=.12);fig.tight_layout();fig.savefig(P/'chunk_guides.png',dpi=160)
