from pathlib import Path
import json,runpy,contextlib,io
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
P=Path('/home/ubuntu/coord/tmp/codex-caprt-0148');x=json.load(open('/home/ubuntu/coord/tmp/codex-cap-west2-0730/actual_saved_DEF.json'));q=json.load(open(P/'balanced_west_same_orient_options.json'));pg=json.load(open(P/'west_actual_PG.json'))
# Reuse exact actual same-platform master extents, not a nominal cell grid.
dims={}
for line in Path('/home/ubuntu/coord/tmp/caprt1131/BclassF_final_geom.tsv').open():
 a=line.rstrip().split('\t')
 if a[0]=='C':dims[a[3]]=[float(a[6])-float(a[4]),float(a[7])-float(a[5])]
dims.update({r['name']:r['size_um'] for r in json.load(open(P/'physical_master_dims.json'))})
fig,axs=plt.subplots(1,3,figsize=(17,9),gridspec_kw={'width_ratios':[1.3,1,1]});ch=q['options'][0]['changes'];old=x['targets'];ax=axs[0];ax.add_patch(Rectangle((43.2,43.2),174.12,29.736,fc='#777',alpha=.35));ax.add_patch(Rectangle((38.88,38.88),182.76,38.376,fill=False,ls='--',ec='red'));ax.text(130,57,'u_st SRAM',ha='center');
for n in ['_27644_','_27645_','wire19289','wire19399','lweco_219418']:
 r=old[n];ax.scatter(r['x'],r['y'],s=18,c='black');ax.annotate(n,(r['x'],r['y']),xytext=(4,5 if n!='_27645_' else -17),textcoords='offset points',fontsize=8)
a=ch['_27646_']['origin_um'];b=ch['wire17963']['origin_um'];end=[old['lweco_219418']['x'],old['lweco_219418']['y']]
for n,r in ch.items():
 if n not in ['_27646_','wire17963']:continue
 ax.scatter(*r['origin_um'],s=55,c='green');ax.annotate(n,r['origin_um'],xytext=(-15,12),textcoords='offset points',fontsize=8)
ax.plot([a[0],a[0],b[0],end[0]],[a[1],b[1],b[1],end[1]],c='green',lw=2);ax.set(xlim=(20,225),ylim=(25,100),title='Balanced west route proxy; no timing prediction');ax.set_aspect('equal')
for ax,region,title in zip(axs[1:],[(28,42,30,88),(97,101,35.6,38.6)],['West actual row/PG/TAP/clock-cell clearance','South A2/B source drivers preserved']):
 for group,color,alpha in [('ordinary','#777',.4),('spacer','#aaa',.08),('tap','#743a89',1)]:
  patches=[]
  for r in x['region_instances']:
   if r['name'] in ch:continue
   kind='spacer' if r['master'].startswith('DECAP') else ('tap' if r['master'].startswith('TAPCELL') else 'ordinary')
   if kind!=group:continue
   w,h=dims[r['master']]
   if r['x']+w<region[0] or r['x']>region[1] or r['y']+h<region[2] or r['y']>region[3]:continue
   patches.append(Rectangle((r['x'],r['y']),w,h))
  ax.add_collection(PatchCollection(patches,fc=color,ec='none',alpha=alpha))
 for r in pg['region_pg_shapes']:
  a,b,c,d=r['rect_um']
  if c<region[0] or a>region[1] or d<region[2] or b>region[3]:continue
  ax.add_patch(Rectangle((a,b),c-a,d-b,fc='#e4a12a',ec='none',alpha=.27))
 for n,r in ch.items():
  a,b,c,d=r['bbox_um']
  if c<region[0] or a>region[1] or d<region[2] or b>region[3]:continue
  ax.add_patch(Rectangle((a,b),c-a,d-b,fc='#28b354',ec='black',lw=.8));ax.annotate(n+(' x2' if n in ['_27644_','_27645_'] else ''),((a+c)/2,(b+d)/2),xytext=(8,14),textcoords='offset points',fontsize=8,arrowprops=dict(arrowstyle='-'))
 ax.set(xlim=region[:2],ylim=region[2:],title=title);ax.set_aspect('equal')
for ax in axs:ax.set(xlabel='µm',ylabel='µm')
fig.suptitle('Cap A actual saved WEST2 geometry copy:2 DATA poses moved, same N orientation/masters\nExact source DEF rows/all locked cells/TAP + actual PG envelopes with conservative .096µm keepout; CORE SPACER removal only\nA2/B actual setup headroom37ps remains a risk: route distance is not timing; all clocks/reset/RTL/cycles unchanged',fontsize=11);fig.tight_layout();fig.savefig(Path('/home/ubuntu/coord/tmp/codex-cap-west2-0730/actual_saved_WEST2.png'),dpi=150)
