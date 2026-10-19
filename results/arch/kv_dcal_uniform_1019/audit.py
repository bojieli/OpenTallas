import odb,json,hashlib,sys,collections
path,out=sys.argv[1:]; db=odb.dbDatabase.create(); odb.read_db(db,path); b=db.getChip().getBlock(); errors=[]
def name(t): return t.getInst().getName()+'/'+t.getMTerm().getName()
def role(t,driver=False):
 m=t.getInst().getMaster().getName(); p=t.getMTerm().getName()
 if 'TIEHI' in m:return 'constant_1'
 if 'TIELO' in m:return 'constant_0'
 if 'DFF' in m:
  if p in ('CLK','CK','CP'):return 'clock'
  if p in ('RESETN','SETN','RESET','SET'):return 'reset_or_preset'
  return 'FF_output' if driver else ('FF_data' if p=='D' else 'unknown_FF_pin')
 if t.getInst().getMaster().isBlock():return 'macro'
 if 'BUF' in m:return 'transparent_buffer'
 if 'INV' in m:return 'transparent_inverter'
 return 'combinational'
def trans(i):return ('BUF' in i.getMaster().getName() or 'INV' in i.getMaster().getName()) and 'DFF' not in i.getMaster().getName()
def walk(n,chain=(),parity=0):
 if n.getName() in chain:errors.append(['transparent_cycle',list(chain),n.getName()]);return []
 chain=chain+(n.getName(),); ans=[]
 for t in n.getITerms():
  if str(t.getIoType())!='INPUT':continue
  if trans(t.getInst()):
   outs=[q for q in t.getInst().getITerms() if str(q.getIoType())=='OUTPUT']
   if len(outs)!=1 or not outs[0].getNet():errors.append(['bad_transparent_driver',name(t)]);continue
   ans+=walk(outs[0].getNet(),chain,parity ^ ('INV' in t.getInst().getMaster().getName()))
  else:ans.append(dict(pin=name(t),role=role(t),master=t.getInst().getMaster().getName(),transparent_inversion_parity=int(parity),net_path=list(chain)))
 for p in n.getBTerms():
  if str(p.getIoType())=='OUTPUT':ans.append(dict(pin='PORT/'+p.getName(),role='top_output',transparent_inversion_parity=int(parity),net_path=list(chain)))
 return ans
records=[];pin_census=[]; netissues=[]
for n in b.getNets():
 if str(n.getSigType()) in ('POWER','GROUND'):continue
 drivers=[t for t in n.getITerms() if str(t.getIoType())=='OUTPUT']; ins=[p for p in n.getBTerms() if str(p.getIoType())=='INPUT']
 sinks=[t for t in n.getITerms() if str(t.getIoType())=='INPUT']
 if len(drivers)+len(ins)!=1:netissues.append(dict(net=n.getName(),drivers=[name(t) for t in drivers]+['PORT/'+p.getName() for p in ins],sink_count=len(sinks)))
 for t in list(n.getITerms()):pin_census.append(dict(pin=name(t),master=t.getInst().getMaster().getName(),direction=str(t.getIoType()),role=role(t,str(t.getIoType())=='OUTPUT'),net=n.getName()))
 for p in n.getBTerms():pin_census.append(dict(pin='PORT/'+p.getName(),direction=str(p.getIoType()),role='top_input' if str(p.getIoType())=='INPUT' else 'top_output',net=n.getName()))
 for d in drivers+ins:
  isport=d in ins; r='top_input' if isport else role(d,True); endpoints=walk(n); unique={x['pin']:x for x in endpoints}
  if len(unique)!=len(endpoints):errors.append(['duplicate_reconvergent_endpoint',n.getName()])
  records.append(dict(driver='PORT/'+d.getName() if isport else name(d),driver_role=r,net=n.getName(),transparent_driver=(False if isport else trans(d.getInst())),logical_pin_count=len(unique),role_counts=dict(collections.Counter(x['role'] for x in endpoints)),endpoints=sorted(unique.values(),key=lambda x:x['pin'])))
# Boundary owns first functional logic pins; only explicit FF_data endpoints qualify as fixed input captures.
boundary=[r for r in records if r['driver_role']=='top_input']
outputs=[]
for r in records:
 if r['transparent_driver']:continue
 for e in r['endpoints']:
  if e['role']=='top_output':outputs.append(dict(port=e['pin'],source=r['driver'],source_role=r['driver_role'],source_net=r['net'],inversion_parity=e['transparent_inversion_parity']))
unconnected=[]
for i in b.getInsts():
 for t in i.getITerms():
  if str(t.getSigType()) in ('POWER','GROUND'):continue
  if not t.getNet():
   x=dict(pin=name(t),master=i.getMaster().getName(),direction=str(t.getIoType()),role=role(t,str(t.getIoType())=='OUTPUT'),net=None);pin_census.append(x);unconnected.append(x)
unknown=[x for x in pin_census if 'unknown' in x['role']]
ff=[i for i in b.getInsts() if 'DFF' in i.getMaster().getName()]
area=sum(i.getMaster().getWidth()*i.getMaster().getHeight() for i in b.getInsts())/(b.getDbUnitsPerMicron()**2)
roots=[r for r in records if not r['transparent_driver']]
functional=[r for r in roots if r['driver_role'] not in ('constant_0','constant_1') and r['net']!='ck']
summary=dict(odb_sha256=hashlib.sha256(open(path,'rb').read()).hexdigest(),source_commit='190b12e9f',ff_count=len(ff),stdcell_area_um2=area,all_driver_count=len(records),root_driver_count=len(roots),physical_pin_count=len(pin_census),unconnected_signal_pins=unconnected,unknown_pin_roles=unknown,macro_count=sum(i.getMaster().isBlock() for i in b.getInsts()),all_driver_over32=[{k:r[k] for k in ('driver','driver_role','net','logical_pin_count','role_counts')} for r in records if r['logical_pin_count']>32],functional_max=max(r['logical_pin_count'] for r in functional),net_driver_issues=netissues,walk_errors=errors,uniform_all_signal_roots_le32=all(r['logical_pin_count']<=32 for r in roots),qualified_for_parent=False,physical_gate_run=False)
json.dump(dict(summary=summary,all_drivers=records,all_physical_signal_pins=pin_census,input_boundary=boundary,output_boundary=outputs),open(out,'w'),indent=2);print(json.dumps(summary,indent=2))
