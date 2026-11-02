import json,gzip
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
R=Path(__file__).resolve().parent;d=json.loads(gzip.decompress((R/'FP_NATIVE_GEOMETRY.json.gz').read_bytes()));fig,axes=plt.subplots(1,2,figsize=(13,7),gridspec_kw={'width_ratios':[2.3,1]});ax=axes[0];x0,y0,W,H=d['outline'];ax.add_patch(Rectangle((x0,y0),W,H,fill=False,lw=1.4))
for row in d['rows']:
 x,y,xx,yy=row['box'];ax.plot([x,xx],[y,y],color='#bbb',lw=.25)
for net,color in [('VDD','#cf645f'),('VSS','#4179ad')]:
 patches=[]
 for r in d['PG'][net]['metal_rects']:
  if r['layer']=='M1':continue
  x,y,xx,yy=r['box'];patches.append(Rectangle((x,y),xx-x,yy-y))
 ax.add_collection(PatchCollection(patches,facecolor=color,edgecolor='none',alpha=.55,label=net))
for p in d['pins']:
 if p['signal_type'] in ('POWER','GROUND'):continue
 x,y,xx,yy=p['box'];color='#3064aa' if p['dir']=='INPUT' else '#e4912d';ax.scatter((x+xx)/2,(y+yy)/2,s=9,color=color)
 if p['name'] in ('clk','rst_n','x[31]'):ax.annotate(p['name'],((x+xx)/2,(y+yy)/2),xytext=(4,4),textcoords='offset points',fontsize=8)
ax.set_title('Native final2_floorplan.odb: 496 rows / real PG metal / actual IO');ax.set_aspect('equal');ax.set_xlim(-4,W+4);ax.set_ylim(-4,H+4);ax.set_xlabel('um');ax.set_ylabel('um')
a=axes[1]
for i,p in enumerate([p for p in d['pins'] if p['name']=='x[31]']):
 x,y,xx,yy=p['box'];a.add_patch(Rectangle((x,y),xx-x,yy-y,fill=False,lw=2,edgecolor=['#3563b2','#d47924'][i]));a.text(xx+.007,(y+yy)/2,f"M5 shape{i+1}\ny[{y:.3f},{yy:.3f}]",fontsize=9)
a.axhline(138.24,color='black',ls='--',lw=1);a.set_xlim(13.36,13.53);a.set_ylim(138.06,138.27);a.set_aspect('equal');a.grid(alpha=.2);a.set_title('Actual x[31]: both original shapes, contained');a.set_xlabel('um');a.set_ylabel('um')
fig.suptitle('Corrected compact RECIP — native FP ONLY\nNo new SYNTH/PLACE/CTS/route/STA; KWRS FULL retained / manual physical continuation',fontsize=11);fig.tight_layout();fig.savefig(R/'actual_native_FP_review.png',dpi=160)
