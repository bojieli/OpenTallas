from pathlib import Path
import json,hashlib,copy,re,os
import odb
from core_cts_open_rebind import snapshot,digest,require
R=Path('/out');mod=os.environ['MOD'];mode=os.environ['MODE'];manifest=json.load(open(R/(mod+'.json')));src=R/(mod+'.input.odb');out=R/(mod+'.allpg.odb');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rules(block):
 mapping={};receipt=[]
 for rule in block.getGlobalConnects():
  pattern=rule.getPinPattern();m=re.fullmatch(r'\^?([A-Za-z_][A-Za-z0-9_]*)\$?',pattern);require(m is not None,'literal PG rule required');pin=m[1];net=rule.getNet();require(net is not None and str(net.getSigType()) in ['POWER','GROUND'],'canonical rule role');region=rule.getRegion();receipt.append(dict(pin_pattern=pattern,inst_pattern=rule.getInstPattern(),net=net.getName(),sig=str(net.getSigType()),region=region.getName() if region else None))
  for inst in rule.getInsts():
   if region and (not inst.getRegion() or inst.getRegion().getId()!=region.getId()):continue
   it=inst.findITerm(pin)
   if not it:continue
   require(str(it.getMTerm().getSigType())==str(net.getSigType()),'rule signal/wrong-role pin');mapping.setdefault((inst.getName(),pin),set()).add(net.getName())
 require(all(len(v)==1 for v in mapping.values()),'ambiguous PG domain')
 return {k:next(iter(v)) for k,v in mapping.items()},receipt
def audit(block,mapping):
 bad=[];total=0
 for inst in block.getInsts():
  for mt in inst.getMaster().getMTerms():
   if str(mt.getSigType()) not in ['POWER','GROUND']:continue
   total+=1;it=inst.findITerm(mt.getName());require(it is not None,'missing actual PG ITerm');key=(inst.getName(),mt.getName());require(key in mapping,'unruled actual PG pin');net=it.getNet();expected=mapping[key]
   if net is None:bad.append([inst.getName(),inst.getMaster().getName(),mt.getName(),str(mt.getSigType()),None,expected])
   else:require(net.getName()==expected and str(net.getSigType())==str(mt.getSigType()),'wrong PG domain (no automatic repair)')
 return total,bad
def masked(state,targets):
 value=copy.deepcopy(state)
 for n,p in targets:value['instances'][n]['pins'][p]['net']='<explicit existing-rule PG-only target>'
 return value
if mode=='repair':
 require(not out.exists() and not Path(str(out)+'.tmp').exists() and not (R/(mod+'.receipt.json')).exists(),'fresh output only');require(sha(src)==manifest['input_sha256'],'exact input SHA');db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock();mapping,rule_receipt=rules(b);total,bad=audit(b,mapping);expected={(r[1],r[3]) for r in manifest['targets']};actual={(r[0],r[2]) for r in bad};require(actual==expected and len(bad)==manifest['expected_open_pins'],'exact observed null manifest');before=snapshot(b)
 for name,master,pin,sig,old,netname in bad:
  inst=b.findInst(name);require(inst.getMaster().getName()==master,'master identity');inst.findITerm(pin).connect(b.findNet(netname))
 after=snapshot(b);_,remaining=audit(b,mapping);require(not remaining,'postrepair PG0');first=digest(masked(before,actual));last=digest(masked(after,actual));require(first==last,'non-target state changed');tmp=Path(str(out)+'.tmp');odb.write_db(db,str(tmp));tmp.rename(out);rec=dict(module=mod,input_sha256=manifest['input_sha256'],output_sha256=sha(out),pg_terms=total,connected_pins=len(bad),wrong_domain=0,preserved_before=first,preserved_after=last,rules=rule_receipt,unchanged='all non-target PG, all CLK/DATA/reset/connections/ports/poses/masters/status/DNT/sourceflags/PGwire shapes; noRC/STA/CTS/place/route',target_pins=sorted(actual));(R/(mod+'.receipt.json')).write_text(json.dumps(rec,indent=2));print('FULL_PG_COPY_PASS',json.dumps({k:v for k,v in rec.items() if k not in ['target_pins','rules']}))
else:
 require(mode=='audit','unknown mode');rec=json.load(open(R/(mod+'.receipt.json')));require(sha(out)==rec['output_sha256'],'saved DB identity');db=odb.dbDatabase.create();odb.read_db(db,str(out));b=db.getChip().getBlock();mapping,rule_receipt=rules(b);total,bad=audit(b,mapping);require(not bad,'saved full PG audit');require(total==rec['pg_terms'],'saved PGterm census');require(digest(masked(snapshot(b),[tuple(x) for x in rec['target_pins']]))==rec['preserved_after'],'saved non-target state');result=dict(module=mod,verdict='PASS',scope='independent fresh native savedDB read; every master POWER/GROUND term/actualITerm/domain',pg_terms=total,open_terms=0,wrong_domain=0,output_sha256=rec['output_sha256'],preserved_snapshot=rec['preserved_after']);(R/(mod+'.saved_full_PG_audit.json')).write_text(json.dumps(result,indent=2));print('SAVED_FULL_PG_PASS',json.dumps(result))
