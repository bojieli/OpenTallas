import hashlib,json,sys
from pathlib import Path
root=Path('/srv/opentallas-scratch2/claude/codex-hbm-parent-1106')
sys.path.insert(0,str(root/'component_source/tools/die_plan'))
sys.path.insert(0,'/srv/opentallas-scratch2/claude/codex-kit-component-consumer-1106/runtime')
import kit_topology as K
proof=root/'component_q_spb2_v1.json'
bind=Path('/srv/opentallas-scratch2/claude/hbm-bind-9/g_t11m79f')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=(sha(proof),sha(bind/'bind_report.json'),(bind/'native_topology.json').exists())
r=K.verify_component_source(proof,context_plan=root/'bind_context_banks20_taps/die_plan.json',
 prepared_plan=root/'xcal_subplan/die_plan_banks20_taps_TRIAL.json',bind_out=bind,
 type_name='q_spb2',instance='NW_spb2',asbuilt='/srv/opentallas-scratch2/claude/hbm-bind-6/tip2/physical/die_plan/hbm/bind/d44v/asbuilt_t11.json')
try:
 K.verify_component_source(proof,context_plan=root/'bind_context_banks20_taps/die_plan.json',prepared_plan=root/'xcal_subplan/die_plan_banks20_taps_TRIAL.json',bind_out=bind,type_name='q_spb2',instance='WRONG_INSTANCE')
except ValueError:
 wrong_identity_refused=True
else:
 raise AssertionError('wrong selected identity accepted')
after=(sha(proof),sha(bind/'bind_report.json'),(bind/'native_topology.json').exists())
assert before==after and r['scope']=='LOCAL_COMPONENT' and r['source_preparation_only'] is True
assert r['global_bind']['status']=='FAIL',r['global_bind']
o=Path('/srv/opentallas-scratch2/claude/codex-kit-component-consumer-1106')
(o/'actual_probe.json').write_text(json.dumps({'scope':r['scope'],'source_preparation_only':r['source_preparation_only'],
 'global_bind':r['global_bind'],'read_only_inputs_unchanged':before==after,'native_receipt_written':False,'wrong_identity_refused':wrong_identity_refused},indent=2)+'\n')
print((o/'actual_probe.json').read_text())
