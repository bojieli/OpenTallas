import odb,json,re
from collections import defaultdict
from pathlib import Path
D=odb.dbDatabase.create();odb.read_db(D,'/input.odb');b=D.getChip().getBlock();dbu=b.getDbUnitsPerMicron()
point=lambda p:(p.x(),p.y())
box=lambda r:(r.xMin(),r.yMin(),r.xMax(),r.yMax())
clocknets=['clk','o0','o1','o2','o3','ck_mesh'];regions={};port_regions={};report={};totals=defaultdict(int)
for inst in b.getInsts():
 r=inst.getBBox();cx=(r.xMin()+r.xMax())/2;cy=(r.yMin()+r.yMax())/2
 regions[inst.getName()]=[cx-2*dbu,cy-.7*dbu,cx+2*dbu,cy+.7*dbu]
for name in clocknets:
 for t in b.findNet(name).getBTerms():port_regions[t.getName()]=[box(r) for pin in t.getBPins() for r in pin.getBoxes()]
Path('/work/access_regions.json').write_text(json.dumps({'schema':'opentallas.clock_access_regions.v1','units':'DBU','dbu_per_um':dbu,'basis':'Explicit4x1.4umcellislands centered onactualBUF24bbox; nativeBPinboxes only','cells':regions,'ports':port_regions},indent=2)+'\n')
def uncovered(a,z,rects):
 if a==z:return []
 vertical=a[0]==z[0];assert vertical or a[1]==z[1]
 k=1 if vertical else 0;p=1-k;lo,hi=sorted((a[k],z[k]));spans=[]
 for r in rects:
  if r[p]<=a[p]<=r[p+2]:
   l,h=max(lo,r[k]),min(hi,r[k+2])
   if l<=h:spans.append((l,h))
 result=[];cur=lo
 for l,h in sorted(spans):
  if l>cur:result.append((cur,l))
  cur=max(cur,h)
 if cur<hi:result.append((cur,hi))
 return [(tuple((a[0],l)) if vertical else tuple((l,a[1])),tuple((a[0],h)) if vertical else tuple((h,a[1]))) for l,h in result]
def distance(p,r):return max(r[0]-p[0],p[0]-r[2],r[1]-p[1],p[1]-r[3],0)
def maximum_distance(a,z,rects):
 if not rects:return float('inf')
 k=1 if a[0]==z[0] else 0;p=1-k;lo,hi=sorted((a[k],z[k]));lines=[]
 for r in rects:lines += [(-1,r[k]),(1,-r[k+2]),(0,max(r[p]-a[p],a[p]-r[p+2],0))]
 candidates={lo,hi}
 for i,(m,q) in enumerate(lines):
  for n,t in lines[:i]:
   if m!=n:
    x=(t-q)/(m-n)
    if lo<=x<=hi:candidates.add(x)
 return max(min(distance((a[0],t) if k==1 else (t,a[1]),r) for r in rects) for t in candidates)
for name in clocknets:
 n=b.findNet(name);allowed=[];kind={}
 for i in n.getITerms():
  r=regions[i.getInst().getName()];allowed.append(r);kind[tuple(r)]='cell:'+i.getInst().getName()
 for t in n.getBTerms():
  for r in port_regions[t.getName()]:allowed.append(r);kind[tuple(r)]='port:'+t.getName()
 layers=defaultdict(int);violations=[];segments=[];mismatch=[]
 if n.getWire():
  it=odb.dbWirePathItr();it.begin(n.getWire());p=odb.dbWirePath();e=odb.dbWirePathShape()
  while it.getNextPath(p):
   a=point(p.point)
   while it.getNextShape(e):
    q=e.shape;z=point(e.point)
    if not q.isVia():
     layer=q.getTechLayer().getName();length=abs(z[0]-a[0])+abs(z[1]-a[1]);layers[layer]+=length;totals[layer]+=length
     if length!=q.getLength():mismatch.append([layer,a,z,length,q.getLength()])
     if int(layer[1:])<=7:
      for u,v in uncovered(a,z,allowed):
       mid=((u[0]+v[0])/2,(u[1]+v[1])/2);near=min(allowed,key=lambda r:distance(mid,r))
       violations.append({'layer':layer,'a_um':[t/dbu for t in u],'b_um':[t/dbu for t in v],'length_um':(abs(u[0]-v[0])+abs(u[1]-v[1]))/dbu,'max_linf_outside_um':maximum_distance(u,v,allowed)/dbu,'nearest_declared_region':kind[tuple(near)]})
    a=z
 report[name]={'decoded_regular_lengths_um':{k:v/dbu for k,v in sorted(layers.items())},'lower_centerline_outside_um':sum(v['length_um'] for v in violations),'max_lower_centerline_distance_outside_um':max([v['max_linf_outside_um'] for v in violations] or [0]),'violations':violations,'decoded_vs_native_length_mismatches':mismatch}
odb.write_def(b,'/work/audit_native.def')
s=Path('/work/audit_native.def').read_text();section=re.search(r'(?ms)^SPECIALNETS\s+\d+\s*;(.*?)^END SPECIALNETS',s).group(1)
mesh=re.search(r'(?ms)^\s*-\s+ck_mesh\b(.*?);',section).group(1);special=defaultdict(int)
for path in re.split(r'\+\s+(?:FIXED|ROUTED|COVER)\s+|\bNEW\s+',mesh)[1:]:
 layer=path.split()[0];prev=None
 for x,y in re.findall(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)',path):
  x=int(x) if x!='*' else prev[0];y=int(y) if y!='*' else prev[1]
  if prev is not None:special[layer]+=abs(x-prev[0])+abs(y-prev[1])
  prev=(x,y)
result={'schema':'opentallas.clock_wire_audit.v1','source':'shared_m89_r3/infra.odb','regular_layer_lengths_um':{k:v/dbu for k,v in sorted(totals.items())},'mesh_special_centerline_lengths_um':{k:v/dbu for k,v in sorted(special.items())},'nets':report,'access_regions':'access_regions.json','verdict':'FAIL' if any(r['violations'] for r in report.values()) else 'PASS','method':'Exactnative dbWirePathItr point deltas; fixedspecialnets fromnativeDEFcenterlinecoordinates; explicitcell4x1.4um/nativeBPinaccessregions','freeze_qualified':False}
Path('/work/wire_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('CLOCK_WIRE_AUDIT',result['verdict'],result['regular_layer_lengths_um'])
for n,r in report.items():print(n,'outside_um',r['lower_centerline_outside_um'],'maxdistance',r['max_lower_centerline_distance_outside_um'],'regions',sorted({v['nearest_declared_region'] for v in r['violations']}))
