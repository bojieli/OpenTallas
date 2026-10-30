import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
r=json.loads((p/'source_plan.json').read_text());s=json.loads((p/'source_sidecar.json').read_text());bad=[];points=[]
fig,axs=plt.subplots(5,5,figsize=(22,22))
for ax,(tn,t) in zip(axs.flat,sorted(r['partition_types'].items())):
 w,h=t['outline_um'];ck=t.get('clock',{});ax.add_patch(Rectangle((0,0),w,h,fill=False,ec='k',lw=.6));boxes=[]
 for c in t.get('hard_cores',[]):
  off=c.get('track_offset_um',[0,0]);x,y=[a+b for a,b in zip(c['origin_um'],off)];cw,ch=c['outline_um'];boxes.append((x,y,x+cw,y+ch,c['inst']));ax.add_patch(Rectangle((x,y),cw,ch,fc='#f7d889',ec='#ae8030',lw=.35))
 def point(xy,kind):
  points.append(dict(type=tn,kind=kind,xy_um=xy))
  for x0,y0,x1,y1,n in boxes:
   if x0<xy[0]<x1 and y0<xy[1]<y1:bad.append(dict(type=tn,kind=kind,xy_um=xy,macro=n))
 bands=ck.get('landing_contract',{}).get('bands',{})
 assert bands==s.get('collector',{}).get('types',{}).get(tn,{}).get('bands',{}),(tn,'Plan/sidecar band mismatch')
 for b in bands.values():
  x0,y0,x1,y1=b['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#9be5e5',ec='#3b9999',lw=.3,alpha=.3))
 for key,color in [('landing_reader_start','#2478bb'),('landing_writer_start','#2b9c48')]:
  spec=ck.get(key,{})
  for name,b in spec.get('branches',{}).items():
   xy=[v['xy_um'] for v in b['stages']]
   for q in xy:point(q,key+':'+name)
   if xy:ax.plot(*zip(*xy),'-o',color=color,lw=.6,ms=1.6)
 for target,ins in ck.get('landing_status_input_stages',{}).items():
  for name,st in ins.items():
   xy=[v['xy_um'] for v in st]
   for q in xy:point(q,'status:'+target+':'+name)
   if xy:ax.plot(*zip(*xy),'-o',c='#bc58aa',lw=.5,ms=1.4)
 for v in ck.get('landing_local_resets',[]):point(v['xy_um'],'reset_copy');ax.plot(*v['xy_um'],'x',c='#df511c',ms=2.5)
 for q in ck.get('landing_status_anchors',{}).values():point(q,'status_anchor');ax.plot(*q,'s',c='#bc58aa',ms=1.8)
 for v in t.get('reset_start_raw_exports',[]):ax.plot(*v['xy_um'],'.',c='#333333',ms=1.5)
 ax.set(xlim=(-w*.025,w*1.025),ylim=(-h*.025,h*1.025),title=tn);ax.set_aspect('equal');ax.tick_params(labelsize=5)
fig.suptitle('HEAD ROOT88 third-core candidate — declared control sites, yellow hard cores, cyan native rings\nBlue reader START; green writer START; purple status; orange local reset; black raw source. Actual G1/clock/PG/timing still required.',fontsize=11)
fig.tight_layout();fig.savefig(out/'control_atlas.png',dpi=130);plt.close(fig)
(out/'site_scan.json').write_text(json.dumps(dict(points=len(points),strictly_inside_hardcore=bad),indent=1)+'\n');print('DECLARED_CONTROL_SITES',len(points),'INSIDE_MACRO',len(bad))
