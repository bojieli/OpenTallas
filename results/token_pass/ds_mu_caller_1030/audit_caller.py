import json,shutil,sys
from pathlib import Path
W=Path('/srv/opentallas-scratch/claude/wt/codex-ds-native-slot-1030');R=Path('/srv/opentallas-scratch/claude/codex-ds-native-slot-1030/caller_fixture');A=W/'results/token_pass/pipeline_native_s81_1021'
R.mkdir();sys.path[:0]=[str(W/'tools/s81_dv'),str(W/'tools/s81_dv/layer_prog')]
from layer_prog.pipeline_boot import native_job,compile_pipeline
for name in('A','B'):
 for rel in('manifest.json','lowering.json','prog/calendar.json','prog/host_boot.memh'):
  dest=R/name/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(A/'inputs'/name/rel,dest)
book=json.loads((A/'bookings.json').read_text())
record=next((A/'emitted').glob('R000*/programme.json'));ks=json.loads(record.read_text())['ks53'];(R/'descriptor.memh').write_text(ks+'\n')
calendar=json.loads(Path('/home/ubuntu/OpenTallas/results/token_pass/calendar_pipeline_s81_1021/calendar_rel241_G4_mtp.json').read_text())
r=compile_pipeline(calendar,book,R,R/'emitted')
missing=[g for g in r['gaps']if g['cause']=='selected_native_MU_return_calendar_missing']
assert len(missing)==2 and r['status']=='PARTIAL'and r['emitted']==2
assert not any(g['cause']=='native_MU_KIT_varies_within_one_physical_resource'for g in r['gaps'])
rows=[]
for name in('A','B'):
 j=native_job(R/name);rows.append(dict(programme=name,die_sha256=j['native_die_sha256'],KIT=j['KIT_issues'],END=j['end_issue'],HOST_words=len(j['words']),sealed_programme_held=j['sealed_programme_held'],actual_boot_payload_sha256=j['programme_payload_sha256'],all_stage_ops_lowered=j['all_stage_ops_lowered']))
result=dict(status='PASS_ACTUAL_PIPELINE_CALLER_REFUSES_UNBOUND_RESOURCE_MU_CALENDARS',actual_jobs=rows,emitted=2,pipeline_status=r['status'],new_blockers=missing,no_blanket_conflict_across_R000_R001=True,existing_source_clock_lifetime_production_holds_preserved=True,scope='real old native PWF/bytes and existing TEST-only packetbook; no new physical dates or math qualification',full_token=False)
Path('/srv/opentallas-scratch/claude/codex-ds-native-slot-1030/caller_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
