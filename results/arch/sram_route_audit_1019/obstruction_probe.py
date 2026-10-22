import odb,json,collections,hashlib
D=odb.dbDatabase.create();odb.read_db(D,'/base/6_final.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron();i=next(i for i in b.getInsts() if i.getMaster().isBlock())
def rect(r):return [r.xMin(),r.yMin(),r.xMax(),r.yMax()]
def touch(a,c):return a[0]<=c[2] and c[0]<=a[2] and a[1]<=c[3] and c[1]<=a[3]
def over(a,c):return a[0]<c[2] and c[0]<a[2] and a[1]<c[3] and c[1]<a[3]
def via(v,xy):
 return [(z.getTechLayer().getName(),[z.xMin()+xy[0],z.yMin()+xy[1],z.xMax()+xy[0],z.yMax()+xy[1]],'via') for z in v.getBoxes()]
def shapes(n):
 out=[];w=n.getWire()
 if w:
  it=odb.dbWirePathItr();it.begin(w);p=odb.dbWirePath();s=odb.dbWirePathShape()
  while it.getNextPath(p):
   while it.getNextShape(s):
    q=s.shape
    if q.isVia():out.extend(via(q.getTechVia() or q.getVia(),q.getViaXY()))
    else:out.append((q.getTechLayer().getName(),rect(q),'wire'))
 for sw in n.getSWires():
  for q in sw.getWires():
   if q.isVia():out.extend(via(q.getTechVia() or q.getBlockVia(),q.getViaXY()))
   else:out.append((q.getTechLayer().getName(),rect(q),'special'))
 return out

xy=i.getLocation();assert str(i.getOrient())=='R0'
obs=[(o.getTechLayer().getName(),[o.xMin()+xy[0],o.yMin()+xy[1],o.xMax()+xy[0],o.yMax()+xy[1]]) for o in i.getMaster().getObstructions()]
nets={t.getNet().getName():t.getNet() for t in i.getITerms() if t.getNet() and t.getMTerm().getName() not in ['VDD','VSS']}
errors=[];count=collections.Counter();near=[]
for name,n in nets.items():
 for l,r,k in shapes(n):
  count[k]+=1
  for ol,orr in obs:
   if ol==l and over(r,orr):errors.append(dict(net=name,layer=l,shape=r,kind=k,obstruction=orr))
  if l=='M4' and (r[0]<xy[0]+1000 and r[2]>xy[0]-1000 or r[0]<xy[0]+32992 and r[2]>xy[0]+30992) and r[1]<xy[1]+17304 and r[3]>xy[1]:near.append(dict(net=name,layer=l,shape=r,kind=k))
result=dict(source='3ff02bde11fe57867215021e1e0b6f4e5690a0c8',macro_origin_nm=xy,orientation=str(i.getOrient()),signal_nets=len(nets),shape_counts=dict(count),signal_macro_obstruction_overlaps=errors,obstructions=obs,edge_m4_shapes=near,scope='All exact signal-net segment/via metal and cut boxes compared to actual transformed macro LEF obstructions; PG pin overlaps separately audited.')
open('/audit/obstruction_audit.json','w').write(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='edge_m4_shapes'},indent=2))
