import json,odb,math
from pathlib import Path
r=Path('/out');db=odb.dbDatabase.create();odb.read_db(db,'/work/run/results/asap7/kl_dsdv_bksel_q_signed_source/base/2_4_floorplan_pdn.odb');b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();pitch=int(4.32*u)
idx={};m6=[];via_counts={}
for net in (b.findNet('VDD'),b.findNet('VSS')):
 name=net.getName();nv=0
 for sw in net.getSWires():
  for s in sw.getWires():
   if not s.isVia():
    if s.getTechLayer().getName()=='M6':m6.append([name,s.xMin()/u,s.yMin()/u,s.xMax()/u,s.yMax()/u])
    continue
   via=s.getTechVia() or s.getBlockVia();x,y=s.getViaXY();layers={z.getTechLayer().getName() for z in via.getBoxes() if z.getTechLayer()};nv+=1
   for z in via.getBoxes():
    l=z.getTechLayer()
    if not l or l.getName() not in ('M4','M5'):continue
    q=(z.xMin()+x,z.yMin()+y,z.xMax()+x,z.yMax()+y);item=(q,tuple(sorted(layers)))
    for ix in range(q[0]//pitch,q[2]//pitch+1):
     for iy in range(q[1]//pitch,q[3]//pitch+1):idx.setdefault((name,l.getName(),ix,iy),[]).append(item)
 via_counts[name]=nv
rows=[];errors=[]
for inst in b.getInsts():
 m=inst.getMaster()
 if not m.isBlock():continue
 assert str(inst.getOrient())=='R0',(inst.getName(),inst.getOrient())
 x,y=inst.getLocation();pins=[]
 for pin in ('VDD','VSS'):
  it=inst.findITerm(pin);net=it.getNet();assert net and net.getName()==pin,(inst.getName(),pin,'wrong root net')
  shapes=[]
  for mp in it.getMTerm().getMPins():
   for z in mp.getGeometry():
    l=z.getTechLayer().getName();q=(z.xMin()+x,z.yMin()+y,z.xMax()+x,z.yMax()+y);hits=set()
    for ix in range(q[0]//pitch,q[2]//pitch+1):
     for iy in range(q[1]//pitch,q[3]//pitch+1):
      for v,lays in idx.get((pin,l,ix,iy),[]):
       if min(q[2],v[2])>max(q[0],v[0]) and min(q[3],v[3])>max(q[1],v[1]):hits.add((v,lays))
    if not hits:errors.append([inst.getName(),pin,l,list(q),'no matching-net via enclosure contact'])
    shapes.append(dict(layer=l,rect_um=[v/u for v in q],via_contacts=len(hits)))
  pins.append(dict(name=pin,root_net=net.getName(),shapes=shapes))
 rows.append(dict(inst=inst.getName(),master=m.getName(),origin_um=[x/u,y/u],outline_um=[m.getWidth()/u,m.getHeight()/u],pins=pins))
assert len(rows)==32,len(rows)
report=dict(scope='actual post-PDN same-net via contact, no IR/timing/signoff claim',macros=32,pg_terms=64,m6_special_wires=m6,via_counts=via_counts,rows=rows,errors=errors)
(r/'actual_pg.json').write_text(json.dumps(report,indent=1)+'\n');print('PG_CONTACT_CENSUS',32,64,'errors',len(errors),'M6stripes',len(m6));assert not errors,errors[:8]
