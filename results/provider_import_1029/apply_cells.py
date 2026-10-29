#!/usr/bin/env python3
"""Import every mapped provider cell into a freshly reviewed actual OpenDB.
Requires a clean fresh-source preflight. Existing cells, pin positions, wires and
native ITerm connections stay immutable; only provider loads/cells/nets append.
"""
import argparse,collections,hashlib,json,sys
from pathlib import Path
import odb

def fhash(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),sort_keys=True).encode()).hexdigest()
def native_snapshot(b,names):
 cells=[];bindings=[]
 for name in sorted(names):
  i=b.findInst(name);cells.append([name,i.getMaster().getName(),list(i.getOrigin()),str(i.getOrient()),str(i.getPlacementStatus())])
  bindings.extend([name,it.getMTerm().getName(),it.getNet().getName() if it.getNet() else None] for it in i.getITerms())
 nets=[]
 for n in b.getNets():
  w=n.getWire();regular=[(w.getOpcode(k),w.getData(k)) for k in range(w.length())] if w else [];special=[]
  for sw in n.getSWires():
   rr=[]
   for s in sw.getWires():
    if s.isVia():v=s.getTechVia() or s.getBlockVia();rr.append(['via',v.getName(),*s.getViaXY()])
    else:rr.append(['wire',s.getTechLayer().getName(),s.xMin(),s.yMin(),s.xMax(),s.yMax()])
   special.append([sw.getId(),rr])
  pins=sorted([bt.getName(),str(bt.getIoType()),[[z.getTechLayer().getName(),z.xMin(),z.yMin(),z.xMax(),z.yMax()] for bp in bt.getBPins() for z in bp.getBoxes()]] for bt in n.getBTerms())
  nets.append([n.getName(),str(n.getSigType()),regular,special,pins])
 return dict(cells=digest(cells),native_connections=digest(sorted(bindings)),wires={r[0]:r[1:] for r in nets})
def transform(i,s):
 sx,sy={'R0':(1,1),'MX':(1,-1),'MY':(-1,1),'R180':(-1,-1)}[str(i.getOrient())];x,y=i.getOrigin();xx=sorted([x+sx*s.xMin(),x+sx*s.xMax()]);yy=sorted([y+sy*s.yMin(),y+sy*s.yMax()]);return[xx[0],yy[0],xx[1],yy[1]]
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--inventory',required=True);p.add_argument('--mapped',required=True);p.add_argument('--top',default='ot_die_start_stages');p.add_argument('--placements',required=True);p.add_argument('--bindings',required=True);p.add_argument('--preflight',required=True);p.add_argument('--review',required=True);p.add_argument('--out',required=True);a=p.parse_args();proof=json.load(open(a.preflight));assert proof['verdict']=='READY_FOR_REVIEW' and not proof['issues'],'actual fresh source preflight HOLD';assert Path(a.review).is_file(),'visual review record required';assert proof['source_odb_sha256']==fhash(a.source),'source ODB differs from actual fresh clearance'
 for key,path in [('inventory',a.inventory),('mapped',a.mapped),('placements',a.placements),('bindings',a.bindings)]:assert proof[key+'_sha256']==fhash(path),'stale import input '+key
 inv=json.load(open(a.inventory));pl=json.load(open(a.placements));bd=json.load(open(a.bindings));mapped=json.load(open(a.mapped))['modules'][a.top];assert len(pl['cells'])==len(inv['cells']) and not pl['failed'];out=Path(a.out);out.mkdir(parents=True,exist_ok=True);assert (out/'provider.odb').resolve()!=Path(a.source).resolve(),'input ODB is immutable';d=odb.dbDatabase.create();odb.read_db(d,a.source);b=d.getChip().getBlock();assert b.getDbUnitsPerMicron()==pl['dbu'];names={i.getName() for i in b.getInsts()};before=native_snapshot(b,names);places={c['inst']:c for c in pl['cells']};bits=collections.defaultdict(set)
 for n,q in mapped['ports'].items():
  binding=bd['ports'][n];net=b.findNet(binding['net'])
  if not net:raise ValueError('missing actual native boundary net '+n+' '+binding['net'])
  if q['direction']=='input':
   drivers=[it for it in net.getITerms() if str(it.getMTerm().getIoType())=='OUTPUT'];drivers+= [t for t in net.getBTerms() if str(t.getIoType())=='INPUT']
   if not drivers:raise ValueError('actual input boundary has no native driver '+n)
   if binding['role']!='clock' and len(drivers)!=1:raise ValueError('actual data/reset boundary has multiple native drivers '+n)
  elif any(str(it.getMTerm().getIoType())=='OUTPUT' for it in net.getITerms()) or any(str(t.getIoType())=='INPUT' for t in net.getBTerms()):raise ValueError('actual output boundary already driven '+n)
  for endpoint in binding.get('native_endpoints',[]):
   i=b.findInst(endpoint['inst']);it=i.findITerm(endpoint['pin']) if i else None
   if not it or not it.getNet() or it.getNet().getName()!=binding['net']:raise ValueError('native endpoint mismatch '+str(endpoint))
  bits[q['bits'][0]].add(binding['net'])
 if any(len(v)!=1 for v in bits.values()):raise ValueError('distinct physical nets alias one mapped provider bit')
 bitnet={bit:next(iter(nn)) for bit,nn in bits.items()}
 allbits={v for c in inv['cells'] for vv in c['connections'].values() for v in vv}
 for bit in sorted(allbits):
  if not isinstance(bit,int):raise ValueError('unmapped literal in mapped physical cell graph')
  if bit not in bitnet:
   n='start_provider_n'+str(bit)
   if b.findNet(n):raise ValueError('internal provider namespace collision '+n)
   bitnet[bit]=n
 # Complete preflight actual LEF bodies/pins/rows before adding ANY object.
 rowindex=collections.defaultdict(list)
 for row in b.getRows():
  if str(row.getOrient())=='R0':rowindex[row.getOrigin()[1]].append(row)
 for c in inv['cells']:
  q=places[c['inst']];m=d.findMaster(c['master']);x,y=q['xy_dbu']
  if b.findInst(q['odb_inst']):raise ValueError('provider cell already exists '+q['odb_inst'])
  if not m or [m.getWidth(),m.getHeight()]!=[q['bbox_dbu'][2]-x,q['bbox_dbu'][3]-y]:raise ValueError('actual LEF body differs '+c['inst'])
  if not any(row.getBBox().xMin()<=x and x+m.getWidth()<=row.getBBox().xMax() and (x-row.getOrigin()[0])%row.getSpacing()==0 for row in rowindex.get(y,[])):raise ValueError('not on an actual R0 placement row '+c['inst'])
  for pin,bb in c['connections'].items():
   mt=m.findMTerm(pin)
   if len(bb)!=1 or not mt or str(mt.getIoType()).lower()!=c['directions'][pin]:raise ValueError('actual pin shape/direction mismatch '+c['inst']+'/'+pin)
 for nn,kind in [('VDD','POWER'),('VSS','GROUND')]:
  supply=b.findNet(nn)
  if supply and str(supply.getSigType())!=kind:raise ValueError('existing supply net has wrong actual type '+nn)
 for name in set(bitnet.values()):
  if not b.findNet(name):odb.dbNet_create(b,name)
 for n,st in [('VDD','POWER'),('VSS','GROUND')]:
  net=b.findNet(n)
  if not net:net=odb.dbNet_create(b,n);net.setSigType(st)
 for c in inv['cells']:
  q=places[c['inst']];i=odb.dbInst_create(b,d.findMaster(c['master']),q['odb_inst']);i.setOrient('R0');i.setOrigin(*q['xy_dbu']);i.setPlacementStatus('FIRM')
  for pin,bb in c['connections'].items():i.findITerm(pin).connect(b.findNet(bitnet[bb[0]]))
  for it in i.getITerms():
   st=str(it.getMTerm().getSigType())
   if st in ['POWER','GROUND']:it.connect(b.findNet('VDD' if st=='POWER' else 'VSS'))
 actual=[];pg=[];clocks=[]
 for c in inv['cells']:
  q=places[c['inst']];i=b.findInst(q['odb_inst']);bb=i.getBBox();r=[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()];assert r==q['bbox_dbu'],'actual imported body differs';actual.append(dict(mapped_inst=c['inst'],inst=i.getName(),stage=c['stage'],role=c.get('role','origin'),master=c['master'],bbox_dbu=r,sequential=c['sequential']))
  for pin,bit in c['connections'].items():assert i.findITerm(pin).getNet().getName()==bitnet[bit[0]],'mapped actual bit connection mismatch'
  for it in i.getITerms():
   st=str(it.getMTerm().getSigType());pin=it.getMTerm().getName();rr=[]
   for mp in it.getMTerm().getMPins():
    for z in mp.getGeometry():
     ly=z.getTechLayer()
     if ly and ly.getRoutingLevel()>0:rr.append([ly.getName(),*transform(i,z)])
   if st in ['POWER','GROUND']:pg.append(dict(inst=i.getName(),pin=pin,net=it.getNet().getName(),shapes_dbu=rr))
   if c['sequential'] and pin=='CLK':clocks.append(dict(inst=i.getName(),stage=c['stage'],net=it.getNet().getName(),master=c['master'],shapes_dbu=rr))
 after=native_snapshot(b,names);assert before['cells']==after['cells'],'native cell/master/placement moved';assert before['native_connections']==after['native_connections'],'existing native ITerm connection changed';assert all(after['wires'].get(n)==r for n,r in before['wires'].items()),'existing native routes/pins changed';odb.write_db(d,str(out/'provider.odb'))
 for name,data in [('all_cells.json',dict(dbu=pl['dbu'],cells=actual)),('provider_pg_terms.json',dict(dbu=pl['dbu'],terms=pg)),('clock_loads.json',dict(dbu=pl['dbu'],loads=clocks)),('bit_nets.json',bitnet)]:json.dump(data,open(out/name,'w'),separators=(',',':'))
 receipt=dict(verdict='ALL_MAPPED_CELLS_IMPORTED',cells=len(actual),flops=len(clocks),comb=len(actual)-len(clocks),new_pg_terms=len(pg),native_cells_preserved=len(names),native_cells_sha=before['cells'],native_connections_sha=before['native_connections'],existing_net_routes_preserved=len(before['wires']),inventory_sha256=fhash(a.inventory),placements_sha256=fhash(a.placements),scope='Physical all-cell source import only; full PG access, routed clock load timing, native seam/reset phase and token gates still required');(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
