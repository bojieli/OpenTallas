import odb,json,hashlib,sys,gzip,re
from pathlib import Path
B=Path('/stage');sys.path.insert(0,str(B/'source658/tools/ref_tile'));import native_census as NC
rows=json.loads((B/'cases.json').read_text());expected=json.loads((B/'classified_admission.json').read_text());exp={r['master']:r for r in expected['cases']};sources=json.loads((B/'current_image_native_sources.json').read_text());outdir=B/'repair';outdir.mkdir(exist_ok=True)
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
pgroles={}
for r in sources['Liberty']:
 p=Path(r['path']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256'];txt=(gzip.decompress(raw) if p.suffix=='.gz' else raw).decode();txt=re.sub(r'/\*.*?\*/|//[^\n]*','',txt,flags=re.S)
 for kind,_,body in NC.groups(txt):
  if kind!='library':continue
  for typ,m,cell in NC.groups(body):
   if typ!='cell':continue
   ps={pin:dict(pg_type=NC.attr(pb,'pg_type'),voltage_name=NC.attr(pb,'voltage_name')) for k,pin,pb in NC.groups(cell) if k=='pg_pin'}
   if m in pgroles:assert pgroles[m]==ps,(m,'corner PG mismatch')
   pgroles[m]=ps

def snapshot(b):
 insts=[];signal=[];masters={}
 for i in b.getInsts():
  m=i.getMaster();insts.append([i.getName(),m.getName(),list(i.getLocation()),str(i.getOrient()),str(i.getPlacementStatus()),i.isDoNotTouch()]);masters[m.getName()]=[m.getWidth(),m.getHeight(),sorted((t.getName(),str(t.getIoType()),str(t.getSigType())) for t in m.getMTerms())]
  for t in i.getITerms():
   if str(t.getSigType()) not in ['POWER','GROUND']:signal.append([i.getName(),t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None])
 bt=sorted([t.getName(),str(t.getIoType()),str(t.getSigType()),t.getNet().getName() if t.getNet() else None] for t in b.getBTerms())
 return dict(instances=sorted(insts),masters=masters,all_signal_topology=sorted(signal),bterms=bt)

def validate(b,before,approved):
 assert snapshot(b)==before,'instance/master/geometry/signal or clock topology changed'
 for i in b.getInsts():
  for t in i.getITerms():
   sig=str(t.getSigType())
   if sig not in ['POWER','GROUND']:continue
   net=t.getNet();assert net is not None,'unbound PG'
   assert str(net.getSigType())==sig,'wrong rail sigtype'
   assert net.getName()==('VDD' if sig=='POWER' else 'VSS'),'wrong rail netname'
 for name,pin in approved:
  t=b.findInst(name).findITerm(pin);role=pgroles[t.getInst().getMaster().getName()][pin];sig=str(t.getSigType());assert role==dict(pg_type='primary_power' if sig=='POWER' else 'primary_ground',voltage_name='VDD' if sig=='POWER' else 'VSS'),('LibertyPGrole',role)
def change_pg(t, rail):
 i=t.getInst();protected=i.isDoNotTouch()
 try:
  if protected:i.setDoNotTouch(False)
  if rail is None:t.disconnect()
  else:t.connect(rail)
 finally:
  if protected:i.setDoNotTouch(True)
results=[]
for row in rows:
 name=row['master'];original=next(f['path'] for f in row['files'] if f['path'].endswith('6_final.odb'));rawsha=hashlib.sha256(Path(original).read_bytes()).hexdigest();db=odb.dbDatabase.create();odb.read_db(db,original);b=db.getChip().getBlock();before=snapshot(b);approved={(r['instance'],r['pin']) for r in exp[name]['nativePG_evidence']};missing={(i.getName(),t.getMTerm().getName()) for i in b.getInsts() for t in i.getITerms() if str(t.getSigType()) in ['POWER','GROUND'] and t.getNet() is None};assert missing==approved
 original_pg=[(i.getName(),t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for i in b.getInsts() for t in i.getITerms() if str(t.getSigType()) in ['POWER','GROUND']]
 for inst,pin in sorted(approved):
  t=b.findInst(inst).findITerm(pin);assert sources['cell_roles'][t.getInst().getMaster().getName()]['pins']['Y']['function']=='A';rail=b.findNet('VDD' if str(t.getSigType())=='POWER' else 'VSS');assert rail and rail.getSWires();change_pg(t,rail)
 validate(b,before,approved)
 changes=[(i,p,old,b.findInst(i).findITerm(p).getNet().getName()) for i,p,old in original_pg if old!=(b.findInst(i).findITerm(p).getNet().getName() if b.findInst(i).findITerm(p).getNet() else None)];assert {(i,p) for i,p,_,_ in changes}==approved
 causal=[];it=b.findInst(sorted(approved)[0][0]).findITerm(sorted(approved)[0][1]);good=it.getNet()
 for mode in ['wrongrail','unbound','signalrewire']:
  sigt=None;old=None
  if mode=='wrongrail':change_pg(it,b.findNet('VSS' if good.getName()=='VDD' else 'VDD'))
  elif mode=='unbound':change_pg(it,None)
  else:
   sigt=next(t for i in b.getInsts() for t in i.getITerms() if str(t.getSigType())=='SIGNAL' and t.getNet() and not i.isDoNotTouch());old=sigt.getNet();sigt.connect(b.findNet('VDD'))
  try:validate(b,before,approved)
  except AssertionError as err:causal.append(dict(case=mode,rejected=True,reason=str(err)))
  else:raise AssertionError('causal accepted '+mode)
  if sigt:sigt.connect(old)
  else:change_pg(it,good)
 validate(b,before,approved);dest=outdir/(name+'_PG_REPAIRED_MODEL_ONLY.odb');odb.write_db(db,str(dest));db2=odb.dbDatabase.create();odb.read_db(db2,str(dest));validate(db2.getChip().getBlock(),before,approved);assert hashlib.sha256(Path(original).read_bytes()).hexdigest()==rawsha
 results.append(dict(master=name,status='PROSPECTIVE_PG_ONLY_MODEL_NO_SIGNOFF',original_pg_status='FAIL',original_odb=original,original_sha256=rawsha,repaired_odb=str(dest),repaired_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),nativePG_unbound_after=0,changes=changes,geometry_all_signal_and_clock_topology_sha256=digest(before),causals=causal,Liberty_pg_roles={b.findInst(i).getMaster().getName():pgroles[b.findInst(i).getMaster().getName()] for i,p in approved}))
 print('PRIVATE_PG_MODEL',name,len(changes),'3CAUSALS_REJECT',flush=True)
(outdir/'repair_receipt.json').write_text(json.dumps(dict(scope='ROOT08:02 private PG-only model; no historical signoff or original rewrite; no ETM timing yet',cases=results),indent=2)+'\n')
