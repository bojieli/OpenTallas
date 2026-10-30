"""Results-local geometric capacity of relay bays beside candidate clock vertices."""
import json,math
from pathlib import Path
R=Path(__file__).parent;G=json.load(open(R/'start_graph_estimate.json'));P=json.load(open(R/'input.json'));parts={p['name']:p for p in P['partitions']}
def glob(p,q):return [p['origin_um'][0]+2885.76-q[0],p['origin_um'][1]+q[1]]
def ov(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-6 and min(a[3],b[3])>max(a[1],b[1])+1e-6
block=[]
for pn,p in parts.items():
 a,b=glob(p,[52.84,75.6]),glob(p,[2682.92,1021.68]);block.append([min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])])
 for band in P['partition_types'][p['type']]['clock']['landing_contract']['bands'].values():
  if 'rect_um' in band:
   a,b=glob(p,band['rect_um'][:2]),glob(p,band['rect_um'][2:]);block.append([min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])])
clocks=[];targets={}
for leg in G['legs']:
 pnames=list(parts) if leg['label'].startswith('dme_') else [None]
 for pn in pnames:
  chain=[glob(parts[pn],q) if pn else q for q in leg['chain']]
  for x,y in chain:clocks.append([x-.81,y-.135,x+.81,y+.135])
  for q in chain[2::2]:targets[tuple(round(a,4) for a in q)]=dict(clock_xy=q,part=pn)
used=[];placed=[];failed=[]
# 8.64 x .81 bay: 7 FF plus data INV8/BUF8s and clock BUF8+INV2 over three rows.
# Site-level capacities only; exact cell shapes and existing unspecified core cells remain actual-build concerns.
offsets=sorted([(dx*1.08,dy*.27) for dx in range(-8,9) for dy in range(-32,33) if abs(dx*1.08)+abs(dy*.27)<=10],key=lambda z:abs(z[0])+abs(z[1]))
for key,t in sorted(targets.items()):
 x,y=t['clock_xy'];found=None
 for dx,dy in offsets:
  cx=round((x+dx)/1.08)*1.08;cy=round((y+dy)/.27)*.27;b=[cx-4.32,cy-.405,cx+4.32,cy+.405]
  if abs(cx-x)+abs(cy-y)>10+1e-6:continue
  if t['part']:
   p=parts[t['part']]
   if b[0]<p['origin_um'][0] or b[2]>p['origin_um'][0]+2885.76 or b[1]<103.68 or b[3]>1330.56:continue
  if any(ov(b,z) for z in block) or any(ov(b,z) for z in clocks) or any(ov(b,z) for z in used):continue
  found=b;break
 if found is None:failed.append(t)
 else:used.append(found);placed.append(dict(**t,bay=found,clock_to_bay_center_um=abs((found[0]+found[2])/2-x)+abs((found[1]+found[3])/2-y)))
res=dict(scope='Analytic reserved-bay estimate, known candidate PG/landing bands and all modeledclockcellbodies only. Unspecified standardcell occupancy not included; not detailed placement.',bay_um=[8.64,.81],target_count=len(targets),placed_count=len(placed),failed=failed,max_clock_to_bay_center_um=max([z['clock_to_bay_center_um'] for z in placed] or [0]),placements=placed,build_allowed=False)
json.dump(res,open(R/'relay_bay_estimate.json','w'),indent=1);print(json.dumps({k:v for k,v in res.items() if k!='placements'}))
