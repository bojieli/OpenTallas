from pathlib import Path
import subprocess,json,hashlib
r=Path('/srv/opentallas-scratch/claude/codex-pvm-bindfirst-stages-0720');out=r/'tie_matrix_remaining';out.mkdir(exist_ok=False)
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
libs=json.loads((r/'work/current_native_census.json').read_text())['liberty']
env={'PVM_BF_REFERENCE_ODB':'/audit/work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/1_synth.odb','PVM_BF_AUDIT_ODB':'/audit/work/bindfirst_proof/post_floorplan.failed.odb','PVM_BF_TIE_LIBRARIES':'\n'.join(l['path'] for l in libs)}
base=['docker','run','--rm','-v',str(r)+':/audit','-v',str(r/'src')+':/src:ro']
for k,v in env.items():base+=['-e',k+'='+v]
rows=[]
for mode,pattern in [('extra_outside','TIE_EXTERNAL_ADD_OR_RETAIN'),('new_driver','TIE_NEW_DRIVER')]:
 name=mode or 'positive'
 cmd=base+['-e','PVM_BF_AUDIT_MUTANT='+mode,'-e','PVM_BF_TIE_REPORT=/audit/tie_matrix/'+name+'.json','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',img,'-exit','-python','/audit/tie_detach_audit.py']
 with (out/(name+'.log')).open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 d=json.loads((out/(name+'.json')).read_text());ok=(rc==0 and d['status']=='PASS') if not mode else (rc!=0 and pattern in d.get('reason',''))
 row=dict(mode=name,rc=rc,expected=pattern,matched=ok,reason=d.get('reason'));rows.append(row);print(row,flush=True)
 if not ok:break
summary=dict(status='PASS' if len(rows)==2 and all(x['matched'] for x in rows) else 'FAIL',rows=rows,helper_sha256=hashlib.sha256((r/'tie_detach_audit.py').read_bytes()).hexdigest(),image=img)
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');raise SystemExit(0 if summary['status']=='PASS' else 1)
