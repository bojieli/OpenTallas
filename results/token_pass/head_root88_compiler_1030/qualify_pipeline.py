import json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-event3-1030');S=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029')
sys.path[:0]=[str(R/'code'),str(R/'code/layer_prog'),str(S/'tools/s81_dv'),str(S/'tools/die_plan')]
from layer_prog.pipeline_boot import compile_pipeline
from layer_prog.head_root_boot import PINS
P=Path('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030/mu_caller/old_caller');read=lambda p:json.loads(p.read_text())
book=read(P/'bookings.json');book['head_root88_witness']=dict(schema='opentallas.head.root88_source_selection.v1',bundle_root=str(R/'headroot_bundle'))
book['selected_HEAD_source_plan_sha256']=PINS['source_plan.json']
result=compile_pipeline(read(P/'calendar.json'),book,P,R/'headroot_pipeline')
assert result['status']=='PARTIAL'and result['emitted']==2
w=result['head_root_boot_contract'];assert w['root_settle_cycles']==88 and w['delta_boot_cycles']==14 and w['added_steady_cycles']==0
assert any(g['cause']=='HEAD_physical_START_HOST_PMA_authority_missing'for g in result['gaps'])
assert not any(g['cause'].startswith('current_HEAD_ROOT88_source_witness_')for g in result['gaps'])
summary=dict(verdict='PASS_ACTUAL_TWO_JOB_PIPELINE_CURRENT_HEAD_WITNESS',emitted=2,status=result['status'],HEAD_boot=w,
 existing_job_gaps_preserved=result['gaps'],full_token=False)
(R/'headroot_pipeline_summary.json').write_text(json.dumps(summary,indent=1)+'\n');print(summary['verdict'],w['delta_boot_cycles'],'bootcycles',result['status'])
