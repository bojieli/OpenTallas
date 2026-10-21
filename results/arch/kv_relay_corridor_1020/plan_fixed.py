import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'tools/qwen_kv_die')
import kv_die as K
m=K.build(kv_wq_mirror=True,split=True,host_v14=True,host_north=True,host_trees=True,v143=True,reserve_native_astk=True)
M=K.masters(m,1)
report=dict(source='e0dc985f1',mode='ANALYTICAL_ONLY_NO_GEN_QUALIFICATION',die=m['die'],
 instances=len(m['insts']),pin_reach=K.pin_reach(m,M),relay_stages=m.get('relay_stages'),
 bundle_eq=m.get('bundle_eq'),pv_start_eq=m.get('pv_start_eq'),pvfin_align=m.get('pvfin_align'),
 k_rt_eq=m.get('k_rt_eq'),land_slots=m.get('land_slots'),geo=m['geo'])
p=Path('/srv/opentallas-scratch/claude/codex-kv-relay-plan-2210')/f'fixed_plan_{sys.argv[1]}.json'
p.write_text(json.dumps(report,indent=2,default=str))
print(json.dumps(dict(variant=sys.argv[1],status='ANALYTICAL_PLAN_RETURNED',instances=len(m['insts']),reach=report['pin_reach']['violations'])))
