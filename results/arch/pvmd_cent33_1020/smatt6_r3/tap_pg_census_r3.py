import odb,json,collections,hashlib
from pathlib import Path
p=Path('/work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/2_3_floorplan_tapcell.odb')
db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();pg=collections.Counter();tap=collections.Counter();bad=[];empty=[]
for i in b.getInsts():
 master=i.getMaster().getName();is_tap=master=='TAPCELL_ASAP7_75t_R';cohort='.g_native7.u_native.' in i.getName();fixed=str(i.getPlacementStatus()) in ('FIRM','LOCKED','COVER')
 if is_tap:tap['instances']+=1;tap['protected']+=int(i.isDoNotTouch());tap['fixed']+=int(fixed)
 if cohort:pg['kernel_cells']+=1;pg['kernel_dnt']+=int(i.isDoNotTouch())
 for t in i.getITerms():
  role=str(t.getSigType())
  if role not in ('POWER','GROUND'):continue
  n=t.getNet();state='empty' if n is None else ('bound_role' if str(n.getSigType())==role else 'wrong_role');kind='protected' if i.isDoNotTouch() else ('fixed' if fixed else 'ordinary');pg[kind+'_'+state]+=1
  if cohort:pg['kernel_'+state]+=1
  if is_tap:tap['PG_'+state]+=1
  if state=='wrong_role':bad.append([i.getName(),t.getMTerm().getName()])
  if state=='empty' and len(empty)<20:empty.append([i.getName(),master,t.getMTerm().getName()])
nempty=sum(v for k,v in pg.items() if k.endswith('_empty') and not k.startswith('kernel'))
ok=nempty==0 and not bad and pg['protected_bound_role']==112000 and pg['kernel_dnt']==56000
out=dict(status='PASS' if ok else 'FAIL',empty_pg=nempty,odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),PG_counts=dict(pg),tap_cohort=dict(tap),wrong_role_terms=bad,empty_examples=empty,global_rules=[dict(inst=x.getInstPattern(),pin=x.getPinPattern(),net=x.getNet().getName()) for x in b.getGlobalConnects()])
Path('/work/post_tapcell_pg_census.json').write_text(json.dumps(out,indent=2)+'\n');print('PVM_R3_TAP_PG_CENSUS',out['status'],out['empty_pg'],dict(pg),flush=True)
