"""Compare full native clock bodies to actual upper-PG metals and via enclosures."""
import odb,json,collections,sys
sys.path.insert(0,'tools/die_plan')
from infra_replay import route_shapes
D=odb.dbDatabase.create();odb.read_db(D,'pgkit02/psm/pdn_top_only.odb');B=D.getChip().getBlock();u=B.getDbUnitsPerMicron()
t=json.load(open('body_pack02/tree_native.json'));grid=collections.defaultdict(list);rects={};step=10000
for n,(x,y) in t['sites'].items():
 r=(round(x*u)-120,round(y*u)-120,round((x+1.62)*u)+120,round((y+.27)*u)+120);rects[n]=r
 for a in range(r[0]//step,r[2]//step+1):
  for b in range(r[1]//step,r[3]//step+1):grid[a,b].append(n)
counts=collections.Counter();hitnames=set();hits=[];paircount=0
for net in B.getNets():
 if net.getSigType() not in ('POWER','GROUND'):continue
 for layer,r,kind in route_shapes(net):
  ln=layer.getName()
  if ln not in ('M8','M9'):continue
  counts[ln+'_'+kind]+=1;seen=set()
  for a in range(r[0]//step,r[2]//step+1):
   for b in range(r[1]//step,r[3]//step+1):seen.update(grid.get((a,b),()))
  for n in seen:
   q=rects[n]
   if q[0]<r[2] and q[2]>r[0] and q[1]<r[3] and q[3]>r[1]:
    paircount+=1;hitnames.add(n)
    if len(hits)<100:hits.append(dict(cell=n,layer=ln,kind=kind,net=net.getName(),shape_dbu=r,body_clearance_dbu=q))
out=dict(scope='actual generated upper PG versus native clock body plus .12um; macro-disconnected top-grid prototype, no IR/RC claim',cells=len(rects),shape_counts=dict(counts),conflict_pairs=paircount,conflicting_bodies=len(hitnames),sample=hits,verdict='PASS' if not paircount else 'FAIL')
json.dump(out,open('body_pack02/actual_pg.json','w'),indent=1);print(json.dumps({k:v for k,v in out.items() if k!='sample'}),flush=True)
