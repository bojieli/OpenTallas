import json,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-ds-entry-current-1030');S=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029');D0=Path('/srv/opentallas-scratch2/claude/codex-ds-native-1029')
sys.path[:0]=[str(R/'code'),str(R/'code/layer_prog'),str(S/'tools/s81_dv'),str(S/'tools/die_plan')]
from layer_prog.pipeline_boot import compile_pipeline
P=R/'mu_caller/old_caller';read=lambda p:json.loads(p.read_text());book=read(P/'bookings.json')
binding=dict(schema='opentallas.s81.native_mu_return_calendar.v1',local_timing_receipt=str(D0/'timing_current.json'),seqhost_phase_receipt=str(D0/'seqhost_current.json'),initialization_host_file=str(R/'mu_caller/mux.host.memh'),bound_inventory=str(R/'inventory_vn.json'),source_root=str(S),asbuilt_manifest='physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json',clock_reset_identity='LOCAL_SOURCE_FIXTURE_ONLY_NOT_GLOBAL_BOOKING',initialization_last_seq_capture=315,first_KS_seq_capture=2424)
for j in book['jobs']:j['receiver_contract']['native_mu_return_calendar']=binding
report=compile_pipeline(read(P/'calendar.json'),book,P,P/'selected_mu_refusal')
causes=[g['cause']for g in report['gaps']]
assert report['status']=='PARTIAL' and report['emitted']==2
for cause in('native_KIT_disagrees_with_armed_MU_return','native_MU_programme_source_mismatch','native_MU_receiver_source_variant_mismatch','native_KS_off_selected_MU_slot','native_MU_initialization_not_emitted_in_first_resource_boot'):
 assert causes.count(cause)==2,(cause,causes)
assert 'native_MU_KIT_varies_within_one_physical_resource'not in causes
r=dict(status='PASS_ACTUAL_PIPELINE_SELECTED_SOURCE_MU_REFUSAL_BRANCH',emitted=2,pipeline_status='PARTIAL',qualified_selected_MU_source_instantiated=True,native_old_jobs_retagged=False,actual_legacy_KITs=[789,10750],configured_current_entry_RL=489,required_current_KIT=482,per_resource_refusals=[g for g in report['gaps']if g['cause'].startswith(('native_MU','native_KIT','native_KS'))],no_cross_resource_conflict=True,scope='source/return/slot compatibility branch on real prior native bytes with TEST-only transportbook; not global date authority',full_token=False)
(R/'mu_caller/bound_caller.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
