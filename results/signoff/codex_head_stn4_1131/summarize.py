import json,re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
b=Path('/home/ubuntu/coord/codex-head-1131/st_n4_diag');j=json.loads((b/'trace.json').read_text());summary=[]
fig,axes=plt.subplots(2,2,figsize=(12,8));
for ax,(n,d) in zip(axes.flat,j['nets'].items()):
 seg=[]
 for layer,body in re.findall(r'(?:ROUTED|NEW)\s+(M\d+)\s+([^\n]+)',d['route_def'] or ''):
  prev=None
  for x,y in re.findall(r'\(\s*(\*|\d+)\s+(\*|\d+)\s*\)',body):
   if '*' in [x,y] and prev is None:continue
   p=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y))
   if prev:seg.append((layer,prev,p))
   prev=p
 route=sum(abs(a[0]-c[0])+abs(a[1]-c[1]) for l,a,c in seg)/1000
 for l,a,c in seg:ax.plot([a[0]/1000,c[0]/1000],[a[1]/1000,c[1]/1000],lw=.8,alpha=.6)
 points=[]
 for i,p in d['connections']:
  q=j['cells'][i].get('placement');
  if q:points.append((i,p,int(q[1])/1000,int(q[2])/1000))
 drivers=[p for p in points if p[1] in ['Y','Q','QN']]
 for i,p,x,y in points:ax.scatter(x,y,s=18,c='red' if p in ['Y','Q','QN'] else 'black')
 bbox=[min(p[2] for p in points),min(p[3] for p in points),max(p[2] for p in points),max(p[3] for p in points)]
 maxhop=max((abs(p[2]-drivers[0][2])+abs(p[3]-drivers[0][3]) for p in points),default=0) if drivers else None
 row={'net':n,'connections':len(points),'driver':drivers,'placement_origin_bbox_um':bbox,'max_driver_origin_manhattan_um':maxhop,'routed_segment_length_um':route,'route_def_units_per_um':1000};summary.append(row)
 ax.set_title(n.split('/')[-1]+f' / {len(points)-1} loads\nroute {route:.2f}um, origin maxhop {maxhop:.2f}um');ax.set_aspect('equal');ax.grid(alpha=.25);ax.set_xlabel('X um');ax.set_ylabel('Y um')
fig.suptitle('st_n4 actual final DEF data-net overlays; dots = placement origins, lines = routed metal')
fig.tight_layout();fig.savefig(b/'actual_routes.png',dpi=150)
(b/'summary.json').write_text(json.dumps(summary,indent=1));print(json.dumps(summary,indent=1))
