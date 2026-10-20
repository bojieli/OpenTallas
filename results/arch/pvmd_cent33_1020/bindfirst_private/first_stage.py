from pathlib import Path
import subprocess,json,hashlib
r=Path('/srv/opentallas-scratch/claude/codex-pvm-bindfirst-orfs-1020');work=r/'work';proof=work/'bindfirst_proof';proof.mkdir(exist_ok=False)
census=json.loads((work/'native_census.json').read_text());assert census['status']=='PASS',census['status']
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29';orbin='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad';kit='/src/physical/ref_tile/pvm_bindfirst_private'
env={'PVM_BF_EXPECTED':'/work/bindfirst_proof/expected.tcllist','PVM_BF_RECEIPTS':'/work/bindfirst_proof','PVM_BF_ORIGINAL_ODB':'/original/1_synth.odb','PVM_BF_PG_HELPER':'/src/physical/common_flow/native_pg_binding.tcl'}
base=['docker','run','--rm','-v',str(r/'src')+':/src:ro','-v',str(work)+':/work','-v',str(r/'original_s7a_1_synth.odb')+':/original/1_synth.odb:ro','-w','/OpenROAD-flow-scripts/flow']
for k,v in env.items():base+=['-e',k+'='+v]
base+=[img]
def call(cmd,name):
 with (r/name).open('w') as f:rc=subprocess.run(base+cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True)
 if rc:raise SystemExit(rc)
call([orbin,'-exit',kit+'/export_expected.tcl'],'first_reference.log')
p=work/'config.mk'
with p.open('a') as f:
 f.write('\nexport PRE_SYNTH_TCL = '+kit+'/pre_synth.tcl\nexport POST_SYNTH_TCL = '+kit+'/post_synth.tcl\n')
 for k,v in env.items():f.write('export '+k+' = '+v+'\n')
script='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=4 /work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/1_synth.odb'
call(['bash','-lc',script],'first_transaction.log')
audit=base[:-1]+['-e','PVM_BF_AUDIT_ODB=/work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/1_synth.odb','-e','PVM_BF_AUDIT_STAGE=persisted_1_synth',img,orbin,'-exit',kit+'/audit_persisted.tcl']
with (r/'first_persisted.log').open('w') as f:rc=subprocess.run(audit,stdout=f,stderr=subprocess.STDOUT).returncode
print('persisted_1_synth',rc,flush=True)
files=list(proof.glob('*'))+[p,r/'original_s7a_1_synth.odb']+list((r/'src/physical/ref_tile/pvm_bindfirst_private').glob('*.tcl'))
manifest={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
manifest['container_image']=img
(proof/'stage_sha_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
raise SystemExit(rc)
