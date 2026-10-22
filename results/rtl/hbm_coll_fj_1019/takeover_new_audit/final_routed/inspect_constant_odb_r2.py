import odb,os,pathlib,json,hashlib
p=pathlib.Path(os.environ['CONST_ODB']);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();out={}
for name in ['fault_cause[15]','fault_cause[14]','fault_cause[8]','issuer_cfg[35]','issuer_cfg[34]']:
 t=b.findBTerm(name);n=t.getNet();drivers=[]
 for it in n.getITerms():
  if str(it.getIoType())=='OUTPUT':drivers.append({'inst':it.getInst().getName(),'master':it.getInst().getMaster().getName(),'pin':it.getMTerm().getName(),'net':n.getName()})
 out[name]=drivers
 assert len(drivers)==1,(name,drivers)
 def upstream(net):
  ds=[t for t in net.getITerms() if str(t.getIoType())=='OUTPUT'];assert len(ds)==1
  t=ds[0];i=t.getInst();m=i.getMaster().getName();record={'master':m,'inst':i.getName(),'pin':t.getMTerm().getName(),'net':net.getName()}
  if m.startswith('BUF'):
   ins=[t for t in i.getITerms() if str(t.getIoType())=='INPUT' and str(t.getSigType()) not in ['POWER','GROUND']];assert len(ins)==1
   record['upstream']=upstream(ins[0].getNet())
  else:assert m in ['TIELOx1_ASAP7_75t_R','CORE_TIELOW'],record
  return record
 out[name]={'direct':drivers,'constant_path':upstream(n)}
pathlib.Path(os.environ['CONST_OUT']).write_text(json.dumps({'odb':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pins':out},indent=2)+'\n')
print('CONSTANT_ODB_DIRECT_TIELO_PASS',str(p),flush=True)
