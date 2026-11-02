from pathlib import Path
import odb,json,hashlib,copy,re
from core_cts_open_rebind import snapshot,digest,require
R=Path('/work');out=R/'run/results/asap7/kl_ot_s81sl_cap_rt_m5tall_balanced3/base/5_1_grt.odb';expected=R/'baseline/reviewed_WEST2.odb';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
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

require(sha(expected)=='e6b6b31ab2101c2dbd010ef60b2e8c98ceeacae75d9c52727e50b2f16aa0e845','reviewed geometry identity')
old=odb.dbDatabase.create();odb.read_db(old,str(expected));new=odb.dbDatabase.create();odb.read_db(new,str(out));ob=old.getChip().getBlock();nb=new.getChip().getBlock()
mapping,domainrules=rules(nb);total,bad=audit(nb,mapping);require(not bad,'all actualmasterPG0/wrongdomain0')
a=snapshot(ob);z=snapshot(nb);dirty=['net19290','_14198_','_14199_','net19400','_14200_','net17964']
for state in [a,z]:
 for n in dirty:state['nets'][n]['wire']='EXACT_SIX_GRT_DATA_NETS'
require(digest(a)==digest(z),'saved all instance/master/pose/orient/status/DNT/PG/connectivity/port/netflags matchreviewedWEST2')
r=dict(verdict='PASS_GRT_ONLY',source_expected_sha256=sha(expected),output_sha256=sha(out),all_master_pg_terms=total,PG_open=0,wrong_domain=0,reviewed_all_state_digest=digest(a),saved_all_state_digest=digest(z),dirty_DATA_nets=dirty,claim='GRT CHECKPOINT ONLY; old routed RC not reused; no DRT/fill/finish/SIGNED/proof credit')
(R/'SAVED_GRT_AUDIT.json').write_text(json.dumps(r,indent=2));print('CAP_SAVED_GRT_AUDIT_PASS',json.dumps(r))
