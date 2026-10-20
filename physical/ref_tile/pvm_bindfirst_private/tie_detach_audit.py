"""Read-only, exact PVM global-TIE external detach correspondence.

Optional causal mutants act only on the in-memory diagnostic copy. No DNT flag
is cleared and the source/ODB/library files are never written.
"""
import hashlib,json,os,re,sys
from pathlib import Path
import odb
sys.path[:0]=['/src/tools/ref_tile','/src/tools']
from native_census import liberty_roles

def fail(reason):raise ValueError(reason)
def require(ok,reason):
 if not ok:fail(reason)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 d=odb.dbDatabase.create();odb.read_db(d,str(p));return d,d.getChip().getBlock()
def cohort(b):
 pat=re.compile(r'^u_core[.]g_safe[.]g_madd\[([0-9]+)\][.]g_fan32[.]u_m[.]genblk1[.]g_native7[.]u_native[.]')
 return {i.getName():i for i in b.getInsts() if pat.match(i.getName().replace('\\',''))}
def pinrow(t):return (t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType()),t.getNet().getName() if t.getNet() else '')
def endpoint(t):return (t.getInst().getName(),t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType()))
def rows(n):return sorted(endpoint(t) for t in n.getITerms())
def bterms(n):return sorted((t.getName(),str(t.getIoType()),str(t.getSigType())) for t in n.getBTerms())
def outputs(n):return [t for t in n.getITerms() if str(t.getIoType())=='OUTPUT']
def const(t,roles):
 r=roles[t.getInst().getMaster().getName()];p=r['pins'][t.getMTerm().getName()]
 require(not r['sequential'] and p['direction']=='output' and not p['clock'],'TIE_DRIVER_ROLE')
 require(not any(p['direction']=='input' for p in r['pins'].values()),'TIE_DRIVER_HAS_DATA_INPUT')
 v=re.sub(r'[\s()]','',p['function'] or '')
 require(v in ('0','1',"1'b0","1'b1"),'TIE_DRIVER_NONCONSTANT')
 return '1' if v in ('1',"1'b1") else '0'
def audit():
 ref=Path(os.environ['PVM_BF_REFERENCE_ODB']);actual=Path(os.environ['PVM_BF_AUDIT_ODB']);out=Path(os.environ['PVM_BF_TIE_REPORT'])
 libs=os.environ['PVM_BF_TIE_LIBRARIES'].splitlines();roles,receipts=liberty_roles(libs)
 rd,rb=load(ref);ad,ab=load(actual);rc=cohort(rb);ac=cohort(ab)
 require(len(rc)==56000 and set(rc)==set(ac),'KERNEL_INSTANCE_SET')
 tn=os.environ['PVM_BF_TIE_NET'];rn=rb.findNet(tn);an=ab.findNet(tn);require(rn is not None and an is not None,'TIE_NET_MISSING')
 oldrows=rows(rn);kernelrows=[x for x in oldrows if x[0] in rc];drivers=outputs(rn)
 require(len(kernelrows)==112 and all(x[1]=='SETN' for x in kernelrows) and len(drivers)==1,'REFERENCE_TIE_INVENTORY')
 driver=drivers[0];identity=(driver.getInst().getName(),driver.getInst().getMaster().getName(),driver.getMTerm().getName())
 require(const(driver,roles)=='1' and not driver.getInst().isDoNotTouch(),'REFERENCE_TIE_VALUE_OR_PROTECTION')
 removed=[x for x in oldrows if x[0] not in rc and x[2]=='INPUT'];require(len(removed)==len(oldrows)-113 and len(removed)>0,'REFERENCE_EXTERNAL_COUNT')
 mode=os.environ.get('PVM_BF_AUDIT_MUTANT','')
 if mode=='kernel_rewire':
  t=ac[kernelrows[0][0]].findITerm(kernelrows[0][1]);t.connect(odb.dbNet.create(ab,'PVM_BF_NEG_KERNEL_NET'))
 elif mode in ('extra_outside','new_driver'):
  master=ad.findMaster('INVxp33_ASAP7_75t_R') if mode=='extra_outside' else ab.findInst(identity[0]).getMaster()
  i=odb.dbInst.create(ab,master,'PVM_BF_NEG_'+mode)
  t=i.findITerm('A') if mode=='extra_outside' else i.findITerm(identity[2]);t.connect(an)
 elif mode=='constant_flip':
  inst,pin,*_=removed[0];net=ab.findInst(inst).findITerm(pin).getNet();old=outputs(net)[0];old.disconnect()
  master=ad.findMaster('TIELOx1_ASAP7_75t_R');require(master is not None,'MUTANT_TIELO_MASTER_MISSING')
  i=odb.dbInst.create(ab,master,'PVM_BF_NEG_CONST_ZERO')
  term=next(t for t in i.getITerms() if str(t.getIoType())=='OUTPUT');term.connect(net)
 elif mode:fail('UNKNOWN_MUTANT')
 for name,ri in rc.items():
  ai=ac[name]
  require(ri.getMaster().getName()==ai.getMaster().getName(),'KERNEL_MASTER '+name)
  require(sorted(pinrow(t) for t in ri.getITerms())==sorted(pinrow(t) for t in ai.getITerms()),'KERNEL_EVERY_PIN_NET '+name)
  require(ai.isDoNotTouch(),'KERNEL_PROTECTION '+name)
 ds=outputs(an);require(len(ds)==1,'TIE_NEW_DRIVER')
 d=ds[0];require((d.getInst().getName(),d.getInst().getMaster().getName(),d.getMTerm().getName())==identity,'TIE_DRIVER_IDENTITY')
 require(const(d,roles)=='1' and not d.getInst().isDoNotTouch(),'TIE_DRIVER_VALUE_OR_PROTECTION')
 keep=sorted(kernelrows+[endpoint(driver)])
 require(rows(an)==keep and not bterms(an),'TIE_EXTERNAL_ADD_OR_RETAIN')
 nets={t.getNet().getName():t.getNet() for i in rc.values() for t in i.getITerms() if t.getNet() and str(t.getSigType()) not in ('POWER','GROUND')}
 for name,n in nets.items():
  other=ab.findNet(name);require(other is not None,'KERNEL_NET_MISSING '+name)
  if name==tn:continue
  require(str(n.getSigType())==str(other.getSigType()) and rows(n)==rows(other) and bterms(n)==bterms(other),'NON_TIE_NET_GRAPH '+name)
 evidence=[];private_nets=set();tie_drivers=set()
 for inst,pin,direction,sig in removed:
  i=ab.findInst(inst);require(i is not None and inst not in ac,'DETACHED_INSTANCE')
  t=i.findITerm(pin);require(t is not None and str(t.getIoType())==direction and str(t.getSigType())==sig,'DETACHED_PIN_ROLE')
  n=t.getNet();require(n is not None and n.getName()!=tn and not bterms(n),'DETACHED_NET_BOUNDARY')
  terms=list(n.getITerms());ds=outputs(n);require(len(terms)==2 and len(ds)==1 and sum(str(t.getIoType())=='INPUT' for t in terms)==1,'DETACHED_OWN_DRIVER_SHAPE')
  dt=ds[0];di=dt.getInst();require(di.getName() not in ac and not di.isDoNotTouch(),'DETACHED_TIE_PROTECTED_OR_KERNEL')
  require(const(dt,roles)=='1','DETACHED_CONSTANT_VALUE')
  require(n.getName() not in private_nets and di.getName() not in tie_drivers,'DETACHED_DRIVER_SHARED')
  private_nets.add(n.getName());tie_drivers.add(di.getName())
  evidence.append(dict(load=inst+'/'+pin,net=n.getName(),driver=di.getName()+'/'+dt.getMTerm().getName(),master=di.getMaster().getName(),value='1',protected=False))
 report=dict(status='PASS',schema='opentallas.pvm_exact_tie_external_detach.v1',reference_odb_sha256=sha(ref),actual_odb_sha256=sha(actual),kernel_cells=56000,every_kernel_pin_including_pg_exact=True,global_net=tn,original_terms=len(oldrows),current_terms=113,kernel_setn_terms=112,original_driver=identity,driver_constant='1',all_loaded_liberty=receipts,detached_external_loads=len(evidence),own_unprotected_constant_drivers=len(tie_drivers),evidence=evidence,mutant=mode)
 out.write_text(json.dumps(report,indent=2)+'\n');print('TIE_DETACH_PASS kernel56000/allpins exact;112SETN+same1driver;%ddistinctunprotectedconstant1drivers net=%s'%(len(evidence),tn))
try:audit()
except Exception as e:
 out=Path(os.environ['PVM_BF_TIE_REPORT']);out.write_text(json.dumps(dict(status='FAIL',reason=str(e),mutant=os.environ.get('PVM_BF_AUDIT_MUTANT','')),indent=2)+'\n');print('TIE_DETACH_REFUSED',e);raise SystemExit(1)
