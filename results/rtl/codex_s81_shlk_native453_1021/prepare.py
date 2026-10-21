from pathlib import Path
import json,hashlib,shutil,subprocess
base=Path('/srv/opentallas-scratch/claude/ref_gate');out=Path('/srv/opentallas-scratch/claude/codex-s81-shlk-native453-1021')
for view in ['gu','hu']:
 root=base/('dsdv_sh_lk_s10'+view+'-20261021-145415');work=root/'routes/gate/work/orfs';dst=out/view;dst.mkdir(exist_ok=True)
 prior=json.loads((work/'native_census.json').read_text());mapped=work/'results/asap7/opentallas_dsdv_sh_lk_asap7_ref_gate/base/1_2_yosys.v'
 assert hashlib.sha256(mapped.read_bytes()).hexdigest()==prior['netlist']['sha256']
 shutil.copy2(mapped,dst/'1_2_yosys.v');shutil.copy2(work/'native_census.json',dst/'original_native_census.json')
 shutil.copy2(base/(root.name+'.source_snapshot.json'),dst/'original_source_snapshot.json')
 binding=json.loads((dst/'original_source_snapshot.json').read_text());script=Path('/tmp/ref_gate_dsdv_sh_lk_s10'+view+'_20261021-145415.sh')
 assert hashlib.sha256(script.read_bytes()).hexdigest()==binding['remote_script_sha256'];shutil.copy2(script,dst/'original_execution.sh')
 # Copy original library bytes out of the exact original ORFS image; source is read-only.
 (dst/'libs').mkdir(exist_ok=True);(dst/'lib_manifest.json').write_text(json.dumps(prior['liberty']))
 code="""import json,pathlib,shutil,hashlib
root=pathlib.Path('/audit');items=json.loads((root/'lib_manifest.json').read_text())
for i,x in enumerate(items):
 p=pathlib.Path(x['path']);b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==x['sha256'];shutil.copy2(p,root/'libs'/('%02d_'%i+p.name))
"""
 subprocess.run(['docker','run','--rm','-v',str(root/'src')+':/src:ro','-v',str(dst)+':/audit','sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','python3','-c',code],check=True)
 paths=[mapped,work/'config.mk',root/'cts.log',root/'ck.json',work/'results/asap7/opentallas_dsdv_sh_lk_asap7_ref_gate/base/4_cts.odb',work/'results/asap7/opentallas_dsdv_sh_lk_asap7_ref_gate/base/4_cts.sdc',script,base/(root.name+'.source_snapshot.json')]
 receipt={'original_run':str(root),'original_archive_sha256':binding['archive_sha256'],'original_manifest_sha256':binding['manifest_sha256'],'original_archive_blob':'Gate intentionally removed.tgz after successful extraction; extractedsrc and originalscript preserved','original_artifacts_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'new_inputs_only':True,'liberty':prior['liberty']}
 (dst/'input_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(view,'prepared',prior['netlist']['sha256'],'libs',len(prior['liberty']))
