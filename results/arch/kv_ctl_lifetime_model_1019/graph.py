import odb,sys,json,collections,hashlib
p,o=sys.argv[1:3];db=odb.dbDatabase.create();odb.read_db(db,p);b=db.getChip().getBlock()
nets={n.getName():n for n in b.getNets()};memo={};active=set()
def transparent(inst):return inst.getMaster().getName().startswith(('BUF','INV','HB'))
def endpoints(n):
 k=n.getName()
 if k in memo:return memo[k]
 if k in active:raise RuntimeError('transparent cycle '+k)
 active.add(k);r=set()
 for t in n.getBTerms():
  if str(t.getIoType())=='OUTPUT':r.add(('PORT',t.getName()))
 for t in n.getITerms():
  if str(t.getIoType())!='INPUT':continue
  inst=t.getInst();pin=t.getMTerm().getName()
  if str(t.getSigType()) in ('POWER','GROUND'):continue
  if transparent(inst):
   ys=[x.getNet() for x in inst.getITerms() if str(x.getIoType())=='OUTPUT' and x.getNet()]
   assert len(ys)==1,(inst.getName(),len(ys));r.update(endpoints(ys[0]))
  elif pin.upper() not in ('CLK','CK','RCLK','WCLK'):r.add((inst.getName(),pin))
 active.remove(k);memo[k]=frozenset(r);return memo[k]
roots=[]
for n in b.getNets():
 if str(n.getSigType()) in ('POWER','GROUND','CLOCK'):continue
 for t in n.getITerms():
  if str(t.getIoType())!='OUTPUT' or transparent(t.getInst()):continue
  inst=t.getInst();m=inst.getMaster().getName();e=endpoints(n)
  if not e:continue
  kind='FF' if m.startswith('DFF') else ('TIE' if m.startswith('TIE') else ('MACRO' if inst.getMaster().isBlock() else 'COMB'))
  roots.append(dict(net=n.getName(),driver=inst.getName()+'/'+t.getMTerm().getName(),master=m,kind=kind,fanout=len(e),endpoints=sorted(e)))
 for t in n.getBTerms():
  if str(t.getIoType())=='INPUT':
   e=endpoints(n)
   if e:roots.append(dict(net=n.getName(),driver='PORT/'+t.getName(),kind='INPUT',fanout=len(e),endpoints=sorted(e)))
summary={k:dict(roots=sum(r['kind']==k for r in roots),maximum=max([r['fanout'] for r in roots if r['kind']==k]or[0]),unsafe=sum(r['kind']==k and r['fanout']>32 for r in roots)) for k in sorted({r['kind']for r in roots})}
result=dict(schema='kv_ctl_all_driver_native_census.v1',odb=p,odb_sha256=hashlib.sha256(open(p,'rb').read()).hexdigest(),method='all FF/comb/input/tie/macro output drivers; BUF/INV/HB-transparent unique native endpoint pins; clocks/PG excluded',cells=len(b.getInsts()),summary=summary,over32=sorted([r for r in roots if r['fanout']>32],key=lambda r:-r['fanout']),roots=roots)
json.dump(result,open(o,'w'),indent=1);print(json.dumps({k:v for k,v in result.items()if k not in ('roots','over32')}))

masters={};pins={}
for inst in b.getInsts():
 m=inst.getMaster();masters[m.getName()]=dict(area_um2=m.getWidth()*m.getHeight()/b.getDbUnitsPerMicron()**2)
 pins[inst.getName()]=[dict(pin=t.getMTerm().getName(),net=t.getNet().getName() if t.getNet() else None) for t in inst.getITerms() if str(t.getIoType())=='INPUT']
json.dump(dict(odb_sha256=result['odb_sha256'],masters=masters,instance_inputs=pins),open('/out/pin_inventory.json','w'))
