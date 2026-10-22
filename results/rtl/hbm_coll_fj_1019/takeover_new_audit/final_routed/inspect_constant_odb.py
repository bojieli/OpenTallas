import odb,os,pathlib,json,hashlib
p=pathlib.Path(os.environ['CONST_ODB']);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();out={}
for name in ['fault_cause[15]','fault_cause[14]','fault_cause[8]','issuer_cfg[35]','issuer_cfg[34]']:
 t=b.findBTerm(name);n=t.getNet();drivers=[]
 for it in n.getITerms():
  if str(it.getIoType())=='OUTPUT':drivers.append({'inst':it.getInst().getName(),'master':it.getInst().getMaster().getName(),'pin':it.getMTerm().getName(),'net':n.getName()})
 out[name]=drivers
 assert len(drivers)==1 and drivers[0]['master']=='TIELOx1_ASAP7_75t_R' and drivers[0]['pin']=='L', (name,drivers)
pathlib.Path(os.environ['CONST_OUT']).write_text(json.dumps({'odb':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pins':out},indent=2)+'\n')
print('CONSTANT_ODB_DIRECT_TIELO_PASS',str(p),flush=True)
