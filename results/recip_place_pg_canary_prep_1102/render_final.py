from pathlib import Path
import gzip,json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
r=Path(__file__).resolve().parent;d=json.loads(gzip.decompress((r/'final_read/PLACE_INVENTORY.json.gz').read_bytes()));c=json.loads((r/'final_read/RETAINED_CHANGES.json').read_text());fig,(ax,z)=plt.subplots(1,2,figsize=(14,7),gridspec_kw={'width_ratios':[2.3,1]});_,_,W,H=d['outline'];ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5));patches=[]
for inst in d['instances'].values():
 x,y,xx,yy=inst['box'];patches.append(Rectangle((x,y),xx-x,yy-y))
ax.add_collection(PatchCollection(patches,facecolor='#a3aab0',edgecolor='none',alpha=.45))
for net,color in [('VDD','#b85e5b'),('VSS','#487aab')]:
 patches=[]
 for p in d['PG'][net]['metal_rects']:
  if p['layer']=='M1':continue
  x,y,xx,yy=p['box'];patches.append(Rectangle((x,y),xx-x,yy-y))
 ax.add_collection(PatchCollection(patches,facecolor=color,edgecolor='none',alpha=.4))
added=list(c['added_instances'].values());ax.scatter([(p['box'][0]+p['box'][2])/2 for p in added],[(p['box'][1]+p['box'][3])/2 for p in added],s=2,c='#287a3b',alpha=.5,label='628 retained added buffers')
changed=[d['instances'][x['instance']] for x in c['changed_master_instances'] if x['sequential_candidate']];ax.scatter([(p['box'][0]+p['box'][2])/2 for p in changed],[(p['box'][1]+p['box'][3])/2 for p in changed],s=38,facecolors='none',edgecolors='#b82493',lw=1.1,label='9 retained FF strength changes')
for p in d['pins']:
 if p['signal_type'] in ('POWER','GROUND'):continue
 x,y,xx,yy=p['box'];ax.scatter((x+xx)/2,(y+yy)/2,s=8,c='#2d61a5' if p['dir']=='INPUT' else '#df8a26')
ax.set_aspect('equal');ax.set_xlim(-3,W+3);ax.set_ylim(-3,H+3);ax.set_xlabel('um');ax.set_ylabel('um');ax.legend(loc='upper right',fontsize=8);ax.set_title('Actual saved 3_place: 53,105 cells, 496 rows, real PG')
for i,p in enumerate([p for p in d['pins'] if p['name']=='x[31]']):
 x,y,xx,yy=p['box'];z.add_patch(Rectangle((x,y),xx-x,yy-y,fill=False,lw=2,edgecolor=['#3064a8','#d67a28'][i]));z.text(xx+.007,(y+yy)/2,f"M5 shape {i+1}\ny {y:.3f}..{yy:.3f}",fontsize=9)
z.axhline(H,c='black',ls='--',lw=1);z.set_xlim(13.36,13.54);z.set_ylim(138.06,138.27);z.set_aspect('equal');z.grid(alpha=.2);z.set_title('Exact pin metal retained from reviewed FP');z.set_xlabel('um');z.set_ylabel('um')
fig.suptitle('Private RECIP native-birth PLACE canary — independent saved PG audit: 106,210 / 0 failures\n8,994 sequential identities and clock nets retained; 9 FF masters upsized. No CTS / GRT / route / signoff or EQ claim.',fontsize=11);fig.tight_layout();fig.savefig(r/'actual_saved_PLACE_review.png',dpi=170)
