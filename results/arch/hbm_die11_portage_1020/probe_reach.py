import json,sys,collections
from pathlib import Path
sys.path.insert(0,'src/tools/hbm_die_v15')
from relay_router import Router
p=Path('/srv/opentallas-scratch/claude/hbm-die10-1020/planA');m=json.load(open(p/'a/case_a/manifest.json'));sites=json.load(open(p/'artifacts/root_sites.json'))['sites']
r=Router(m['placement'],m['die_um'],405,G=10,carved=m.get('carved_feedthrough'),keepouts=[s['keepout'] for s in sites])
l=json.load(open('freechannel_layer_report.json'));st=json.load(open('freechannel_stations.json'));bad={x['bus'] for x in l['hops_over_reach']};out=[]
for row in st['rows']:
 if row['driver'] not in bad or not row.get('pins'):continue
 anchors=[('source',row['driver'].split('.')[0],row['pins'].get('driver'))]+[('sink',n,pt) for n,pt in row['pins'].get('sinks',{}).items()]
 for kind,n,pt in anchors:
  if pt is None:continue
  free=r.nearest_free(pt);dist=abs(free[0]-pt[0])+abs(free[1]-pt[1])
  # Actual blocking rectangles at the physical endpoint, no invented channel.
  cover=[]
  for name,v in m['placement'].items():
   if name==n:continue
   if v['x']<=pt[0]<=v['x']+v['w'] and v['y']<=pt[1]<=v['y']+v['h']:cover.append(name)
  out.append(dict(bus=row['driver'],kind=kind,inst=n,pin=pt,nearest_legal_cell=free,distance_um=round(dist,2),endpoint_other_obstacles=cover))
json.dump(out,open('reach_endpoint_probe.json','w'),indent=2)
blocked=[x for x in out if x['distance_um']>405]
print('ENDPOINT_REACH_PROBE',len(out),'physically_over405',len(blocked),'instances',sorted({x['inst'] for x in blocked}))
for x in sorted(blocked,key=lambda x:-x['distance_um'])[:12]:print(x)
