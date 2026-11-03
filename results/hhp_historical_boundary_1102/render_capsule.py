from pathlib import Path
import json,re
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
R=Path('/home/ubuntu/coord/tmp/codex-hhp-historical-boundary-0600');C=R/'capsule_r4';g=R/'geometry';plan=json.loads((g/'selected_plan.json').read_text());place=json.loads((g/'placement.json').read_text());cuts=json.loads((g/'ft_cut_geometry.json').read_text())
# Native rectangles retained per actual pin, no invented bounding-box fill.
pins=[];cur=None;layer=None
for l in (R/'views/qkd_kvs_pc.lef').read_text().splitlines():
 m=re.match(r'\s*PIN\s+(\S+)',l)
 if m:cur=m[1]
 m=re.match(r'\s*LAYER\s+(\w+)\s*;',l)
 if m:layer=m[1]
 m=re.match(r'\s*RECT\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)',l)
 if m and cur and cur not in ('VDD','VSS'):pins.append((cur,layer,list(map(float,m.groups()))))
 if cur and re.match(r'\s*END\s+'+re.escape(cur)+r'\s*$',l):cur=None
text=(g/'die_islands.tcl').read_text();vals={k:[float(x) for x in re.findall(r'round\(([\d.]+)\*\$di_u\)',text) ] for k in []}
xs0=[float(x) for x in re.findall(r'set di_x0 \[expr \{round\(([\d.]+)',text)];ys0=[float(x) for x in re.findall(r'set di_y0 \[expr \{round\(([\d.]+)',text)];xs1=[float(x) for x in re.findall(r'set di_x1 \[expr \{round\(([\d.]+)',text)];ys1=[float(x) for x in re.findall(r'set di_y1 \[expr \{round\(([\d.]+)',text)]
fig,axes=plt.subplots(1,2,figsize=(14,10))
for ax,part in zip(axes,['pc_EN_0','pc_WN_0']):
 ax.add_patch(Rectangle((0,0),*plan['outline_um'],fill=False,lw=1.4))
 for x,y,xx,yy in zip(xs0,ys0,xs1,ys1):ax.add_patch(Rectangle((x,y),xx-x,yy-y,color='#999',alpha=.5))
 for h in plan['hard_cores']:
  x,y=h['origin_um'];dx,dy=h['track_offset_um'];x+=dx;y+=dy;w,hh=h['outline_um'];head=h['inst']=='kvpc0'
  ax.add_patch(Rectangle((x,y),w,hh,fill=False,ls='--' if head else '-',edgecolor='#af7133' if head else '#334d84',lw=1.5));ax.text(x+w/2,y+hh*.55,h['inst']+('\nGENUINE SOFT HEAD\nfull-event source / no hard view' if head else '\nREAL BASE / PC_NOT_SIGNED'),ha='center',fontsize=9)
  if not head:
   pp=[]
   for n,layer,r in pins:
    xx=(r[0]+r[2])/2;yy=(r[1]+r[3])/2
    if h['orient']=='MY':xx=w-xx
    pp.append((x+xx,y+yy))
   ax.scatter([p[0] for p in pp],[p[1] for p in pp],s=.25,color='#294a89',alpha=.6)
 for s in place['SRAMs']:
  print('',end='')
  # Exact c7 source records.
  origin=s.get('origin_um') or s.get('origin');size=s.get('size_um') or [94.824,41.064]
  if origin is None:continue
  ax.add_patch(Rectangle(origin,*size,facecolor='#8ebe98',edgecolor='#275e35'));ax.text(origin[0]+size[0]/2,origin[1]+size[1]/2,s.get('name',s.get('inst','SRAM')),ha='center',fontsize=6)
 record=json.loads((C/part/'SOURCE_BOUNDARY.json').read_text())
 for arc in record['soft_HEAD_normal_cells']:
  for c in arc['cells']:
   ax.add_patch(Rectangle((c['x_um'],c['y_um']),1.62,.27,color='red'));ax.scatter(c['x_um']+.81,c['y_um']+.135,s=26,marker='s',color='red')
 cp=next(p for p in cuts['parts'] if p['part']==part)
 for entry in cp['clock_only_inputs']:
  rr=entry['parent_shapes'];centres=[]
  for sh in rr:
   x0,y0,x1,y1=sh['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color='#b22b99'));centres.append(((x0+x1)/2,(y0+y1)/2))
  x,y=centres[0];ax.scatter(x,y,s=28,marker='x',color='#b22b99');ax.annotate(entry['net'].replace('ckm_w_ckm_n10_','pre:'),(x,y),xytext=(8,6),textcoords='offset points',fontsize=6,color='#9a247e')
 for entry in cp['clock_only_output']['native_FT_sources']:
  x0,y0,x1,y1=entry['declared_canonical_M9_strap_subset_parent_rect_um'];ax.plot([(x0+x1)/2]*2,[y0,y1],color='#dc5252',lw=2)
 ax.set_title(part+' — actual prepared historical source + native model geometry',fontsize=10);ax.set_aspect('equal');ax.set_xlim(-15,1052);ax.set_ylim(-15,1536);ax.grid(alpha=.15);ax.set_xlabel('um');ax.set_ylabel('um')
fig.suptitle('PRIVATE HISTORICAL d25/fullm25 only — canonical cohort HOLD; source capsule, NO GEN/CAD\n3 real BASE models + genuine soft HEAD/normal4BUF + c7 SRAM sites; M1 cut shapes/M9 subsets give NO via/route credit',fontsize=11)
fig.tight_layout();fig.savefig(R/'actual_prepared_historical_capsule.png',dpi=170)
