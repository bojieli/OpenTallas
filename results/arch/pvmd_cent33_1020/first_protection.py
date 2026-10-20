import odb,os,json,collections
from pathlib import Path
r=Path('/frozen/routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base');out=[]
for name in ['1_synth.odb','2_floorplan.odb','2_4_floorplan_pdn.odb','3_2_place_iop.odb','3_3_place_gp-failed.odb']:
 p=r/name
 if not p.exists():continue
 db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();counts=collections.Counter();first=None
 for i in b.getInsts():
  n=i.getName().replace('\\','')
  if '.g_native7.u_native.' not in n:continue
  counts['cells']+=1;counts['protected_cells']+=int(i.isDoNotTouch())
  for t in i.getITerms():
   if str(t.getSigType()) in ['POWER','GROUND']:
    counts['pg_terms']+=1;counts['unbound_pg_terms']+=int(t.getNet() is None)
  if first is None:first=dict(name=i.getName(),master=i.getMaster().getName(),protected=i.isDoNotTouch(),ports=[(t.getMTerm().getName(),t.getNet().getName() if t.getNet() else '',str(t.getSigType())) for t in i.getITerms()])
 out.append(dict(stage=name,global_connect_rules=len(b.getGlobalConnects()),counts=dict(counts),first=first))
Path('/audit/pvm_first_protection.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
