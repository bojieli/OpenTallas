#!/usr/bin/env python3
"""Add reviewed native QC PG joins to an actual ODB, preserving existing wires.
Default requires physical canonical PG already present. --seed-canonical-grid
adds only the scoped actual canonical stripes required by this PG vehicle.
It never claims full-grid IR, distributed current capacity or clock closure.
Run under OpenROAD Python. The input ODB is never overwritten.
"""
import argparse,collections,hashlib,json,struct
from pathlib import Path
import odb

def inside(a,b):return b[0]<=a[0] and b[1]<=a[1] and a[2]<=b[2] and a[3]<=b[3]
def native_rect(i,s):
 sx,sy={'R0':(1,1),'MX':(1,-1),'MY':(-1,1),'R180':(-1,-1)}[str(i.getOrient())];x,y=i.getOrigin();xx=sorted([x+sx*s.xMin(),x+sx*s.xMax()]);yy=sorted([y+sy*s.yMin(),y+sy*s.yMax()]);return[xx[0],yy[0],xx[1],yy[1]]
def sha(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),sort_keys=True).encode()).hexdigest()
def special_record(s):
 if s.isVia():return ['via',s.getTechVia().getName(),*s.getViaXY()]
 return ['wire',s.getTechLayer().getName(),s.xMin(),s.yMin(),s.xMax(),s.yMax()]
def pg_swire_hash(sw):
 h=hashlib.sha256();h.update(str(sw.getWireType()).encode());count=0
 for shape in sw.getWires():
  if shape.isVia():
   via=shape.getTechVia();kind=1
   if not via:via=shape.getBlockVia();kind=2
   x,y=shape.getViaXY();record=(via.getId(),x,y,0,0)
  else:kind=0;record=(shape.getTechLayer().getId(),shape.xMin(),shape.yMin(),shape.xMax(),shape.yMax())
  h.update(struct.pack('<B5q',kind,*record));count+=1
 return dict(count=count,sha256=h.hexdigest())
def snapshot(b,original_pg_swires=None):
 nets=[];pg={};pg_ids={};found=set()
 for n in b.getNets():
  if str(n.getSigType()) in ['POWER','GROUND']:
   ids=[]
   for sw in n.getSWires():
    key=n.getName()+':'+str(sw.getId())
    if original_pg_swires is not None and key not in original_pg_swires:continue
    pg[key]=pg_swire_hash(sw);ids.append(sw.getId());found.add(key)
   pg_ids[n.getName()]=ids
   continue
  # Do not retain even a temporary list of PG SBoxes (production has22M vias).
  rec=[(sw.getId(),shape.getId(),special_record(shape)) for sw in n.getSWires() for shape in sw.getWires()]
  w=n.getWire();raw=None if not w else [(w.getOpcode(j),w.getData(j)) for j in range(w.length())]
  nets.append([n.getName(),str(n.getSigType()),raw,rec,sorted([it.getInst().getName(),it.getMTerm().getName()] for it in n.getITerms())])
 if original_pg_swires is not None and found!=set(original_pg_swires):raise ValueError('an original PG/clock-shield SWire disappeared')
 insts=sorted([i.getName(),i.getMaster().getName(),list(i.getOrigin()),str(i.getOrient())] for i in b.getInsts())
 return dict(nonpg_sha=sha(sorted(nets)),inst_sha=sha(insts),pg=pg,pg_swire_ids=pg_ids,pg_record_count=sum(v['count'] for v in pg.values()),nonpg_nets=len(nets),instances=len(insts))
def apply_joins(source_odb,direct_plan,bridge_plan,output_odb,seed_grid=None):
 if Path(source_odb).resolve()==Path(output_odb).resolve():raise ValueError('input ODB is immutable')
 direct=json.load(open(direct_plan));bridges=json.load(open(bridge_plan));assert not direct['failed'] and not bridges['failed'];assert direct['dbu']==bridges['dbu']
 d=odb.dbDatabase.create();odb.read_db(d,str(source_odb));b=d.getChip().getBlock();tech=d.getTech();assert b.getDbUnitsPerMicron()==direct['dbu'];D=direct['dbu'];before=snapshot(b)
 for vn,expected in [('VIA78',{'M7':[-16,-27,16,27],'M8':[-27,-20,27,20]}),('VIA89',{'M8':[-20,-20,20,20],'M9':[-20,-20,20,20]})]:
  tv=tech.findVia(vn)
  if not tv:raise ValueError('missing actual technology via '+vn)
  pads={z.getTechLayer().getName():[z.xMin(),z.yMin(),z.xMax(),z.yMax()] for z in tv.getBoxes() if z.getTechLayer().getName().startswith('M')}
  if pads!=expected:raise ValueError('technology enclosure changed: '+vn+' '+str(pads))
 wanted_vias=collections.defaultdict(set)
 for c in direct['contacts']:wanted_vias[c['net'],'VIA78'].add(tuple(c['xy_dbu']))
 for c in bridges['paths']:
  wanted_vias[c['net'],'VIA78'].add(tuple(c['via78']));wanted_vias[c['net'],'VIA89'].add(tuple(c['via89']))
 wires=collections.defaultdict(list);vias=collections.defaultdict(set)
 for n in b.getNets():
  if str(n.getSigType()) not in ['POWER','GROUND']:continue
  for sw in n.getSWires():
   for s in sw.getWires():
    if s.isVia():
     tv=s.getTechVia()
     # pdngen canonical M8/M9 arrays are block vias. They remain immutable
     # under the streamed preservation guard; they are not requested native
     # tech VIA78 contacts or gap VIA89 duplicates.
     if not tv:continue
     key=n.getName(),tv.getName();xy=tuple(s.getViaXY())
     if xy in wanted_vias.get(key,()):vias[key].add(xy)
    elif s.getTechLayer().getName() in ['M8','M9']:wires[n.getName(),s.getTechLayer().getName()].append([s.xMin(),s.yMin(),s.xMax(),s.yMax()])
 physical_rects={k:list(v) for k,v in wires.items()}
 required=[];ops=[];terms={}
 for c in direct['contacts']:
  x,y=c['xy_dbu'];required.append((c['net'],'M8',c['metal_dbu']['M8']));ops.append((c['inst'],c['pin'],c['net'],[x,y],None,None));terms[c['inst'],c['pin']]=c['net']
 for c in bridges['paths']:
  x,y=c['via78'];xx,yy=c['via89'];required.append((c['net'],'M9',[xx-20,yy-20,xx+20,yy+20]));ops.append((c['inst'],c['pin'],c['net'],[x,y],[xx,yy],c['m8_dbu']));terms[c['inst'],c['pin']]=c['net']
 # Preflight EVERY actual native pin before mutating anything.
 for inst,pin,n,(x,y),v89,bridge in ops:
  i=b.findInst(inst)
  if not i:raise ValueError('missing actual macro '+inst)
  it=i.findITerm(pin)
  if not it or str(it.getMTerm().getSigType())!=('POWER' if n=='VDD' else 'GROUND'):raise ValueError('invalid actual native supply '+inst+'/'+pin)
  if it.getNet() and it.getNet().getName()!=n:raise ValueError('opposing existing supply '+inst+'/'+pin)
  en=[x-16,y-27,x+16,y+27];rr=[native_rect(i,s) for mp in it.getMTerm().getMPins() for s in mp.getGeometry() if s.getTechLayer() and s.getTechLayer().getName()=='M7']
  if not any(inside(en,r) for r in rr):raise ValueError('contact outside actual native PG metal '+inst+'/'+pin)
 seed=[];seedvias=set()
 if seed_grid:
  pg=json.load(open(seed_grid));canon=[(n,ly,*[round(v*D) for v in r]) for n,ly,*r in pg if ly in ['M8','M9']];selected=set()
  # Direct access needs its canonical M8 row. Every bridge needs its canonical M9 stripe.
  for n,ly,r in required:
   matches=[z for z in canon if z[0]==n and z[1]==ly and inside(r,z[2:])]
   if not matches:raise ValueError('required contact has no canonical PG source')
   selected.add(min(matches))
  # Two actual canonical anchor stripes join the selected bipartite grid without
  # constructing every redundant row/column crossing. This is connectivity only.
  for n in ['VDD','VSS']:
   h0=min((z for z in canon if z[0]==n and z[1]=='M8'),key=lambda z:z[3])
   v0=min((z for z in canon if z[0]==n and z[1]=='M9'),key=lambda z:z[2])
   selected.add(h0);selected.add(v0)
   for nn,ly,*r in list(selected):
    if nn!=n:continue
    h=r if ly=='M8' else h0[2:];v=r if ly=='M9' else v0[2:];x=(v[0]+v[2])//2;y=(h[1]+h[3])//2
    if not inside([x-20,y-20,x+20,y+20],h) or not inside([x-20,y-20,x+20,y+20],v):raise ValueError('canonical grid crossing lacks actual VIA89 enclosure')
    seedvias.add((n,x,y))
  seed=sorted(selected)
  for n,ly,*r in seed:wires[n,ly].append(r)
 missing=[(n,ly,r) for n,ly,r in required if not any(inside(r,z) for z in wires[n,ly])]
 if missing:raise ValueError('actual canonical PG grid absent at '+str(missing[:3]))
 # No failed preflight can produce a partially written ODB.
 sw={};counts=collections.Counter()
 for n,st in [('VDD','POWER'),('VSS','GROUND')]:
  net=b.findNet(n)
  if not net:net=odb.dbNet_create(b,n)
  net.setSigType(st);net.setSpecial();sw[n]=odb.dbSWire_create(net,'FIXED')
 def addwire(n,ly,r):
  if any(inside(r,z) for z in physical_rects.get((n,ly),[])):return
  odb.dbSBox_create(sw[n],tech.findLayer(ly),*r,'STRIPE');physical_rects.setdefault((n,ly),[]).append(r);counts['new_wire_rectangles']+=1
 def addvia(n,v,x,y):
  if (x,y) in vias[n,v]:return
  tv=tech.findVia(v)
  if not tv:raise ValueError('missing actual technology via '+v)
  odb.dbSBox_create(sw[n],tv,x,y,'STRIPE');vias[n,v].add((x,y));counts['new_'+v]+=1
 for n,ly,*r in seed:addwire(n,ly,r)
 for n,x,y in sorted(seedvias):addvia(n,'VIA89',x,y)
 for inst,pin,n,(x,y),v89,bridge in ops:
  if bridge:addwire(n,'M8',bridge)
  addvia(n,'VIA78',x,y)
  if v89:addvia(n,'VIA89',*v89)
  b.findInst(inst).findITerm(pin).connect(b.findNet(n))
 after=snapshot(b,original_pg_swires=before['pg'])
 assert before['nonpg_sha']==after['nonpg_sha'],'non-PG wires or native net connections changed'
 assert before['inst_sha']==after['inst_sha'],'instance placement/master changed'
 assert all(after['pg'].get(k)==r for k,r in before['pg'].items()),'existing PG or clock-shield wire changed'
 for (inst,pin),n in terms.items():assert b.findInst(inst).findITerm(pin).getNet().getName()==n
 odb.write_db(d,str(output_odb))
 return dict(verdict='APPLIED_NATIVE_PG_JOINS',source=str(source_odb),output=str(output_odb),unique_supply_terms=len(terms),direct_contacts=len(direct['contacts']),short_fragment_contacts=len(bridges['paths']),counts=dict(counts),clock_and_signal_wire_sha_before=before['nonpg_sha'],clock_and_signal_wire_sha_after=after['nonpg_sha'],instances_sha_before=before['inst_sha'],instances_sha_after=after['inst_sha'],existing_PG_clockshield_records_preserved=before['pg_record_count'],existing_PG_clockshield_swires_preserved=len(before['pg']),PG_preservation_memory='streamed original-SWire hashes; no per-PG-shape Python retention',seeded_canonical_rectangles=len(seed),scope='Actual additive native PG source application only; no full-clock, distributed-current or IR closure')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--direct-plan',required=True);p.add_argument('--bridge-plan',required=True);p.add_argument('--output',required=True);p.add_argument('--receipt',required=True);p.add_argument('--seed-canonical-grid');a=p.parse_args();r=apply_joins(a.source,a.direct_plan,a.bridge_plan,a.output,a.seed_canonical_grid);Path(a.receipt).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
