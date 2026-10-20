from pathlib import Path
import subprocess,json,hashlib
r=Path('/srv/opentallas-scratch/claude/codex-pvm-bindfirst-stages-0720');out=r/'guard_validation';libs=json.loads((r/'work/current_native_census.json').read_text())['liberty']
env={'PVM_BF_REFERENCE_ODB':'/audit/work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/1_synth.odb','PVM_BF_EXPECTED':'/audit/work/bindfirst_proof/expected.tcllist','PVM_BF_RECEIPTS':'/audit/guard_validation/proof','PVM_BF_REVIEWED_TIE_DETACH':'1','PVM_BF_TIE_HELPER':'/audit/guard_validation/source/tie_detach_audit.py','PVM_BF_PG_HELPER':'/src/physical/common_flow/native_pg_binding.tcl','CORNERS':'WC BC','WC_LIB_FILES':' '.join(x['path'] for x in libs if '_TT_' in x['path'] or x['path'].endswith('_tt.lib')),'BC_LIB_FILES':' '.join(x['path'] for x in libs if '_FF_' in x['path'] or x['path'].endswith('_ff.lib'))}
assert len(env['WC_LIB_FILES'].split())+len(env['BC_LIB_FILES'].split())==12
cmd=['docker','run','--rm','-v',str(r)+':/audit','-v',str(r/'src')+':/src:ro']
for k,v in env.items():cmd+=['-e',k+'='+v]
cmd+=['--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','-exit','/audit/validate_guard.tcl']
with (out/'validation.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
text=(out/'validation.log').read_text();ok=rc==0 and 'PVM_BF_REVIEWED_TIE_DETACH_PASS post_floorplan' in text and 'ordinary_tiePG_pending=3918 NOT_QUALIFIED' in text
summary=dict(status='PASS' if ok else 'FAIL',rc=rc,matched=ok,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'source').glob('*') if p.is_file()},physical_stage_launched=False)
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary,flush=True);raise SystemExit(0 if ok else 1)
