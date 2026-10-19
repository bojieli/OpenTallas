"""Fresh paired diagnostic kits; no engine or submission."""
from pathlib import Path
import json, subprocess, sys
p=Path(__file__).resolve().parent
root=p.parents[1]
sys.path.insert(0,str(root/'tools/ref_tile'))
sys.path.insert(0,str(root/'tools/closure_loop'))
import ref_tile as RT
import submit_exact as SE
import helper_overlay as HO
frozen=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
base=json.loads((root/'tests/pg_canonical_coupon_1019/spec.json').read_text())
for mode in ('default','strict'):
 s=json.loads(json.dumps(base));s['name']='pg_xor16_cts_'+mode+'_1019';s['pg_strict']=mode=='strict'
 s['route']['peak_ram_gb']=16
 s['job'].update(branch='codex/pg-canonical-coupon-cts-1019',tag='cts_only',purpose='ROOT approved canonical CTS integration coupon only',extra_paths=['tests/pg_canonical_coupon_1019','tests/pg_canonical_coupon_cts_1019'])
 s['orfs_vars']={'PRE_TAPCELL_TCL':'/src/tests/pg_canonical_coupon_1019/band_rows.tcl'}
 sp=p/(mode+'.json');sp.write_text(json.dumps(s,indent=2)+'\n')
 RT.gen(str(sp),commit=frozen)
 kit=root/'physical/ref_tile'/s['name']
 for name in ('clock.sdc','signoff.sdc'):(kit/name).write_bytes((root/'tests/pg_canonical_coupon_1019/component.sdc').read_bytes())
 for name in ('pre_cts.tcl','post_cts.tcl'):
  t=(kit/name).read_text()
  target='source /src/physical/qwen_die_masters/'+('pre_cts_skew.tcl' if name=='pre_cts.tcl' else 'post_plain.tcl')
  assert t.count(target)==1
  replacement='source /src/tests/pg_canonical_coupon_1019/component_boundary.tcl'
  if name=='pre_cts.tcl':replacement='source /src/physical/qwen_die_masters/repair_budget.tcl\n'+replacement+'\nsource /src/tests/pg_canonical_coupon_cts_1019/checkpoint_before_reports.tcl'
  (kit/name).write_text(t.replace(target,replacement))
 job=json.loads((kit/'job.json').read_text())
 job=SE.move_spec(job,frozen)
 plan,payloads=HO.capture_plan(root,root,head='efae17de2128f3813aff8cf76226e8be8d60ea97',pg_strict=mode=='strict')
 job['effective_helper_plan']=plan
 (p/(mode+'_job_frozen.json')).write_text(json.dumps(job,indent=2)+'\n')
 (p/(mode+'_helper_plan.json')).write_text(json.dumps(plan,indent=2)+'\n')
 print(mode,job['name'],frozen,len(plan['files']))
