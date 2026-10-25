from pathlib import Path
import json,sys,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools'/'die_plan'))
import schema as S,gen_phys,check
# Usage: render_record.py PLAN.json STATION_REPORT.json OUTPUT_DIR
raw=json.load(open(sys.argv[1]));P=S.Plan(raw);report=json.load(open(sys.argv[2]));types=sorted({s['type'] for r in report['rounds'] for s in r['slots']})
out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
fig,axes=plt.subplots(3,6,figsize=(24,15))
for ax,tn in zip(axes.flat,types):
 t=P.types[tn];W,H=t['outline_um'];ax.add_patch(Rectangle((0,0),W,H,fill=False,color='black',lw=.7));pins={(b,i):(x,y,f) for b,i,_,x,y,f in gen_phys.type_pins(P,tn)}
 for c in t.get('hard_cores',[]):
  x,y=c['origin_um'];w,h=c['outline_um'];ax.add_patch(Rectangle((x,y),w,h,color='lightgray',ec='gray',lw=.4))
 n=0
 for index,s in enumerate(t.get('ft_slots',[])):
  name=s['name'];col=plt.get_cmap('tab20')(index%20);k=s.get('stations',1)
  if s.get('bit_sites_um'):
   size=np.array(s['bit_site_cell_um'])/2
   for stage in s['bit_sites_um']:
    pts=np.array(stage)+size;ax.scatter(pts[:,0],pts[:,1],s=.25,color=col,rasterized=True);n+=len(pts)
  for bit in sorted({0,s['width']//2,s['width']}):
   a=pins.get((name+'_i',bit));b=pins.get((name+'_o',bit))
   if not a or not b:continue
   path=check.zroute(a[:2],b[:2],a[2],b[2]);L=check.plen(path);pts=[a[:2]]
   for j in range(1,k):
    if s.get('bit_sites_um'):q=np.array(s['bit_sites_um'][j-1][bit])+np.array(s['bit_site_cell_um'])/2
    elif s.get('regs_um'):q=s['regs_um'][j]
    else:q=check.point_at(path,L*j/k)
    pts.append(q)
   pts.append(b[:2]);pts=np.array(pts)
   boxes=[(c['origin_um'][0]-8.64,c['origin_um'][1]-8.64,c['origin_um'][0]+c['outline_um'][0]+8.64,c['origin_um'][1]+c['outline_um'][1]+8.64) for c in t.get('hard_cores',[])]
   def clear_segment(p,q):
    for x0,y0,x1,y1 in boxes:
     if abs(p[1]-q[1])<1e-7 and y0<p[1]<y1 and min(p[0],q[0])<x1 and max(p[0],q[0])>x0:return False
     if abs(p[0]-q[0])<1e-7 and x0<p[0]<x1 and min(p[1],q[1])<y1 and max(p[1],q[1])>y0:return False
    return True
   for p,q in zip(pts,pts[1:]):
    corner=(q[0],p[1])
    if not (clear_segment(p,corner) and clear_segment(corner,q)):corner=(p[0],q[1])
    ax.plot([p[0],corner[0],q[0]],[p[1],corner[1],q[1]],lw=.45,alpha=.55,color=col)
   ax.scatter(pts[1:-1,0],pts[1:-1,1],s=1.2,color=col)
 taps=gen_phys.clock_pins(P,tn)
 if taps:ax.scatter([v[1] for v in taps],[v[2] for v in taps],marker='*',s=10,color='black')
 ax.set(xlim=(-W*.03,W*1.03),ylim=(-H*.03,H*1.03),title=f'{tn}: {n} explicit cells');ax.set_aspect('equal');ax.tick_params(labelsize=6);ax.title.set_fontsize(9)
fig.suptitle('QC actual-bit station successor: exact row-legal cells outside gray hard cores; each color is one FT slot; black stars=clock entries\nRepresentative first/middle/epoch bit chains follow core-free L routes. Wire capacity and placed drift require separate prototype review.',fontsize=12)
fig.tight_layout(rect=(0,0,1,.95));fig.savefig(out/'all18.png',dpi=110)
print(out/'all18.png')
