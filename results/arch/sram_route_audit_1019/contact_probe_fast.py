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
def area(rs):
 xs=sorted(set(x for r in rs for x in [r[0],r[2]]));a=0
 for x,y in zip(xs,xs[1:]):
  ys=sorted((r[1],r[3]) for r in rs if r[0]<y and r[2]>x);last=None;h=0
  for lo,hi in ys:
   if last is None:last=[lo,hi]
   elif lo<=last[1]:last[1]=max(last[1],hi)
   else:h+=last[1]-last[0];last=[lo,hi]
  if last:h+=last[1]-last[0]
  a+=(y-x)*h
 return a
ns={t.getNet().getName():t.getNet() for t in i.getITerms() if t.getNet()};ss={n:shapes(v) for n,v in ns.items()};out=[];errs=[]
for t in i.getITerms():
 n=t.getNet();name=t.getMTerm().getName()
 if n is None:errs.append([name,'NO_NET']);continue
 for layer,rr in t.getGeometries():
  r=rect(rr);candidates=[(z,k) for l,z,k in ss[n.getName()] if l==layer.getName()];direct=[(z,k) for z,k in candidates if over(z,r)]
  # Follow the same-layer union containing the pin; this accounts for routed patches and via enclosures.
  comp=[r]+[z for z,k in direct];pending=list(candidates)
  if name in ['VDD','VSS']:pending=[] # A conservative direct-contact union lower bound suffices for PG minimum area.
  while True:
   yes=[(z,k) for z,k in pending if any(touch(z,c) for c in comp)]
   if not yes:break
   comp.extend(z for z,k in yes);pending=[v for v in pending if v not in yes]
  ar=area(comp);minimum=layer.getArea() # area is nm^2 in this 1x tech
  bad=[]
  for other,zs in ss.items():
   if other==n.getName():continue
   for l,z,k in zs:
    if l==layer.getName() and over(z,r):bad.append([other,z,k])
  row=dict(pin=name,net=n.getName(),layer=layer.getName(),rect_nm=r,pin_area_nm2=(r[2]-r[0])*(r[3]-r[1]),route_contact_shapes=len(direct),via_contact_shapes=sum(k=='via' for z,k in direct),connected_same_layer_area_nm2=ar,min_area_nm2=minimum,wrong_net_overlaps=bad)
  if not direct:errs.append([name,'NO_PHYSICAL_CONTACT'])
  if minimum and ar<minimum:errs.append([name,'MINAREA',ar,minimum])
  if bad:errs.append([name,'OTHER_NET_OVERLAP',bad])
  out.append(row)
summary=dict(pg_area_basis='Conservative union of pin and directly overlapping special-wire/via metal, not full global PG polygon',schema='opentallas.sram.contact-route-audit.v1',source='3ff02bde11fe57867215021e1e0b6f4e5690a0c8',dbu_per_um=u,macro=i.getMaster().getName(),instance=i.getName(),contacts=len(out),signal_contacts=sum(x['pin'] not in ['VDD','VSS'] for x in out),pg_contacts=sum(x['pin'] in ['VDD','VSS'] for x in out),errors=errs,contacts_data=out,shape_counts={n:len(v) for n,v in ss.items()},scope='Exact external ODB contact overlap and same-layer union minimum area; does not replace full rule deck or prove internal macro layout.')
open('/audit/contact_audit.json','w').write(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in ['contacts_data','shape_counts']},indent=2))
