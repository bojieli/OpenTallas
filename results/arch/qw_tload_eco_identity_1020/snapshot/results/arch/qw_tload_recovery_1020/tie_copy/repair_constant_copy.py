import odb,json,hashlib,sys
from pathlib import Path
src,out,rolefile=map(Path,sys.argv[1:4]);out.mkdir(exist_ok=True)
roles=json.load(open(rolefile));allowed=roles['constant_output_functions']
for r in roles['lib_sources']:
 p=Path(r['path']);assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r
original_sha=hashlib.sha256(src.read_bytes()).hexdigest()
db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock()
def drv(net):return [t for t in net.getITerms() if str(t.getIoType())=='OUTPUT']
def constant(net):
 ds=drv(net)
 if len(ds)!=1:return None
 t=ds[0];n=t.getInst().getMaster().getName();r=allowed.get(n)
 if not r or r['pin']!=t.getMTerm().getName():return None
 assert not [t for t in net.getBTerms() if str(t.getIoType()) in ['INPUT','OUTPUT']],net.getName()
 return t,r
repairs=[]
for n in list(b.getNets()):
 pair=constant(n)
 if pair is None:continue
 source,r=pair;ss=sorted([t for t in n.getITerms() if str(t.getIoType())=='INPUT'],key=lambda t:t.getInst().getName()+'/'+t.getMTerm().getName())
 if len(ss)<=32:continue
 for start in range(32,len(ss),32):
  name='ot_const_copy32_'+str(len(repairs));assert not b.findInst(name) and not b.findNet(name+'_net')
  cp=odb.dbInst.create(b,source.getInst().getMaster(),name);nn=odb.dbNet.create(b,name+'_net')
  cp.findITerm(source.getMTerm().getName()).connect(nn)
  changed=[]
  for s in ss[start:start+32]:changed.append(s.getInst().getName()+'/'+s.getMTerm().getName());s.disconnect();s.connect(nn)
  repairs.append({'original_net':n.getName(),'copy':name,'master':source.getInst().getMaster().getName(),'function':r['function'],'moved_pins':changed})
dst=out/'1_synth_tie32.odb';odb.write_db(db,str(dst))
assert hashlib.sha256(src.read_bytes()).hexdigest()==original_sha
# Reopen the untouched original and prove every original pin/net identity, allowing only equivalent constant moves.
da=odb.dbDatabase.create();odb.read_db(da,str(src));a=da.getChip().getBlock();changes=[]
for ia in a.getInsts():
 ib=b.findInst(ia.getName());assert ib and ia.getMaster().getName()==ib.getMaster().getName()
 for ta in ia.getITerms():
  tb=ib.findITerm(ta.getMTerm().getName());na=ta.getNet();nb=tb.getNet();an=na.getName() if na else None;bn=nb.getName() if nb else None
  if an==bn:continue
  assert str(ta.getIoType())=='INPUT' and str(ta.getSigType()) not in ['CLOCK','POWER','GROUND']
  pa=constant(na);pb=constant(nb);assert pa and pb
  assert pa[0].getInst().getMaster().getName()==pb[0].getInst().getMaster().getName() and pa[1]==pb[1]
  changes.append(ia.getName()+'/'+ta.getMTerm().getName())
for pa in a.getBTerms():
 pb=b.findBTerm(pa.getName());assert pb and pa.getNet().getName()==pb.getNet().getName()
added=[i for i in b.getInsts() if not a.findInst(i.getName())]
assert len(added)==len(repairs) and all(i.getMaster().getName() in allowed for i in added)
proof={'original_sha256':original_sha,'repaired_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'original_cells':len(a.getInsts()),'repaired_cells':len(b.getInsts()),'added_same_master_constant_cells':len(added),'moved_constant_input_pins':changes,'repairs':repairs,'all_original_nonconstant_connectivity_identical':True,'all_BTerms_identical':True,'liberty_functions_verified':roles,'physical_scope':'mapped unplaced copy only; no placement, PG conductor or route proof'}
(out/'repair_proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('TIE_COPY_IDENTITY_PASS',len(added),'copies',len(changes),'constant sinks')
