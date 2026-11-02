from pathlib import Path
import gzip,json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
r=Path(__file__).resolve().parent;d=json.loads(gzip.decompress((r/'FP_NATIVE_GEOMETRY.json.gz').read_bytes()));fig,(ax,ay)=plt.subplots(1,2,figsize=(13,7),gridspec_kw={'width_ratios':[2,1]});_,_,W,H=d['outline'];ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.3))
for row in d['rows']:
 x,y,xx,yy=row['box'];ax.plot([x,xx],[y,y],color='#bbb',lw=.25)
for net,color in [('VDD','#cf645f'),('VSS','#4179ad')]:
 patches=[]
 for z in d['PG'][net]['metal_rects']:
  if z['layer']=='M1':continue
  x,y,xx,yy=z['box'];patches.append(Rectangle((x,y),xx-x,yy-y))
 ax.add_collection(PatchCollection(patches,facecolor=color,edgecolor='none',alpha=.5))
for p in d['pins']:
 if p['signal_type'] in ('POWER','GROUND'):continue
 x,y,xx,yy=p['box'];col='#3064aa' if p['dir']=='INPUT' else '#e4912d';ax.scatter((x+xx)/2,(y+yy)/2,s=8,color=col)
 if p['name'] in ('clk','rst_n'):ax.annotate(p['name'],((x+xx)/2,(y+yy)/2),xytext=(4,5),textcoords='offset points',fontsize=8)
 if y==0:ay.add_patch(Rectangle((x,y),xx-x,yy-y,facecolor=col,edgecolor='none'))
ax.set_aspect('equal');ax.set_xlim(-4,W+4);ax.set_ylim(-4,H+4);ax.set_xlabel('um');ax.set_ylabel('um');ax.set_title(f"Native final2_floorplan.odb: {len(d['rows'])} rows, real PG,338signal pins")
ay.set_xlim(0,W);ay.set_ylim(-.01,.12);ay.set_xlabel('south-face x (um)');ay.set_ylabel('y (um), expanded');ay.grid(alpha=.2);ay.set_title('All268south pins: actual full-face spread')
fig.suptitle('Corrected standalone Q6 ZH — actual native FP ONLY\nNo new SYNTH/PLACE/CTS/route/STA; manual physical continuation / KWRS FULL retained',fontsize=11);fig.tight_layout();fig.savefig(r/'actual_native_FP_review.png',dpi=160)
