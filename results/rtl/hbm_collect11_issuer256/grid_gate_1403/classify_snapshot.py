"""Metadata-only canonical replay; never executes a physical flow or changes its FAIL."""
import hashlib, io, json, os, subprocess, sys, tarfile
from pathlib import Path
sha=lambda x:hashlib.sha256(x).hexdigest()
repo=Path(sys.argv[1]).resolve(); dest=Path(sys.argv[2]).resolve(); dest.mkdir(parents=True,exist_ok=True)
rel=Path('results/rtl/hbm_collect11_issuer256/grid_gate_1403')
published=subprocess.check_output(['git','-C',str(repo),'rev-parse','1a872af33'],text=True).strip()
if len(sys.argv)>3 and sys.argv[3]=='execute':
 sys.path.insert(0,str(repo/'tools/ref_tile'))
 import pre_route_gate as P
 k=sys.argv[4]; kd=repo/'physical/ref_tile'/('hcoll_issuer_r256v8_'+k); inputs=repo/rel/'classification_inputs'/k
 old=json.loads((repo/rel/(k+'.original_spec.json')).read_text()); spec=json.loads((kd/'spec.json').read_text())
 copy=dict(spec); reason=copy.pop('fill_reason'); assert copy==old and reason.get('pin_bound')
 binding=json.loads((inputs/'original_binding.json').read_text()); raw=(inputs/'original.execution.log').read_text()
 original=json.loads((inputs/'original_gate_result.json').read_text()); assert original['verdict']=='FAIL'
 g=P.Gate(); g.source_binding=binding
 P.analyse_remote(g,kd,spec,raw,True,binding,cap=0,host=binding['remote_host'])
 P.gate_layout(g,kd,spec,raw)
 result=dict(vars(g)); result['verdict']=g.verdict
 result['classification_execution_kind']='metadata-classification'; result['qualified_for_submit']=False
 result['physical_parent_binding']=binding
 result['new_spec_sha256']=sha((kd/'spec.json').read_bytes())
 result['semantic_delta']={'fill_reason':reason}
 result['original_gate_result_sha256']=sha((inputs/'original_gate_result.json').read_bytes())
 result['original_execution_log_sha256']=sha((inputs/'original.execution.log').read_bytes())
 result['executed_project_modules']=sorted(str(Path(m.__file__).resolve().relative_to(repo)) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).resolve().is_relative_to(repo))
 result['executed_modules_sha256']={p:sha((repo/p).read_bytes()) for p in result['executed_project_modules'] if p.startswith('tools/')}
 result.pop('source_binding',None)
 (dest/(k+'.replay.json')).write_text(json.dumps(result,indent=1)+'\n')
 g.print(); sys.exit(0 if g.verdict!='FAIL' else 1)
sys.path.insert(0,str(repo/'tools/ref_tile')); import source_binding as SB
commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
tracked=subprocess.check_output(['git','-C',str(repo),'ls-files','tools'],text=True).splitlines()
for k in ('grid','gridb'):
 b=json.loads((repo/rel/'classification_inputs'/k/'original_binding.json').read_text()); entries={x['path']:x for x in b['files']}; files={}
 for p in b['consumed']['paths']:
  data=subprocess.check_output(['git','-C',str(repo),'cat-file','blob',entries[p]['git_blob']]); assert sha(data)==entries[p]['sha256']; files[p]=data
 original_physical={p:sha(v) for p,v in files.items() if not p.startswith('tools/')}
 for p in tracked:
  if (repo/p).is_file(): files[p]=(repo/p).read_bytes()
 for p in [f'physical/ref_tile/hcoll_issuer_r256v8_{k}/spec.json',str(rel/'classify_snapshot.py'),str(rel/(k+'.original_spec.json'))]: files[p]=(repo/p).read_bytes()
 for p in (repo/rel/'classification_inputs'/k).iterdir(): files[str(p.relative_to(repo))]=p.read_bytes()
 changed=[p for p,h in original_physical.items() if sha(files[p])!=h]
 assert changed==[f'physical/ref_tile/hcoll_issuer_r256v8_{k}/spec.json'],changed
 buf=io.BytesIO()
 with tarfile.open(fileobj=buf,mode='w:gz') as tf:
  for p,v in sorted(files.items()):
   ti=tarfile.TarInfo(p);ti.size=len(v);ti.mtime=0;tf.addfile(ti,io.BytesIO(v))
 data=buf.getvalue(); archive=dest/(k+'.classification_inputs.tar.gz');archive.write_bytes(data)
 binding=SB.snapshot(data,repo,commit,repo,commit,[])
 binding['content_identity']=binding['identity']; binding['execution_kind']='metadata-classification'
 binding['remote_archive_verified']=False
 binding['physical_parent']={'binding_sha256':sha((repo/rel/'classification_inputs'/k/'original_binding.json').read_bytes()),'archive_sha256':b['archive_sha256'],'manifest_sha256':b['manifest_sha256'],'start_commit':b['start_commit'],'original_verdict':'FAIL'}
 binding['consumed']=SB.consumed_record(files,binding['files'],'actual staged classification input verification plus canonical parser/tool closure; no new physical execution')
 stage=repo/('.classification_stage_'+k);stage.mkdir(exist_ok=True)
 for p,v in files.items():
  q=stage/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(v)
 command=[sys.executable,str(stage/rel/'classify_snapshot.py'),str(stage),str(dest),'execute',k]
 proc=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (dest/(k+'.classification.stdout.log')).write_text(proc.stdout)
 assert proc.returncode==0,proc.stdout[-4000:]
 replay=json.loads((dest/(k+'.replay.json')).read_text()); replay['source_binding']=binding
 modules=replay['executed_modules_sha256']; assert set(modules)==SB.METADATA_CLASSIFIER_MODULES,(set(modules)^SB.METADATA_CLASSIFIER_MODULES)
 for p,h in modules.items(): assert h==sha(subprocess.check_output(['git','-C',str(repo),'show',published+':'+p])),p
 outrel=rel/'typed_classification'/k; (repo/outrel).mkdir(parents=True,exist_ok=True)
 import shutil
 shutil.copyfile(archive,repo/outrel/'classification_inputs.tar.gz')
 proof={'execution_kind':'metadata-classification','classification_source_commit':commit,'classification_manifest_sha256':binding['manifest_sha256'],'classification_archive_sha256':binding['archive_sha256'],'executed_modules':modules,'published_commit':published}
 proofpath=outrel/'execution.json'; (repo/proofpath).write_text(json.dumps(proof,indent=1)+'\n')
 parentpaths={'binding':rel/'classification_inputs'/k/'original_binding.json','gate':rel/'classification_inputs'/k/'original_gate_result.json','log':rel/'classification_inputs'/k/'original.execution.log','spec':rel/(k+'.original_spec.json')}
 binding['metadata_classification']={'schema':SB.METADATA_CLASSIFICATION_SCHEMA,'parent':{n:{'path':str(p),'sha256':sha((repo/p).read_bytes())} for n,p in parentpaths.items()},'archive':{'path':str(outrel/'classification_inputs.tar.gz'),'sha256':sha(data)},'classifier':{'published_commit':published,'executed_modules':modules,'proof':{'path':str(proofpath),'sha256':sha((repo/proofpath).read_bytes())}}}
 replay['classification_archive']={'path':str(archive),'sha256':sha(data),'bytes':len(data)}
 replay['physical_input_comparison']={'original_consumed_physical_count':len(original_physical),'changed_paths':changed,'all_other_physical_bytes_unchanged':True}
 replay['review_state']='PENDING_ROOT_INTEGRATION_VALIDATION_NO_SUBMIT'
 (repo/rel/(k+'.classification_snapshot.json')).write_text(json.dumps(replay,indent=1)+'\n')
 print(k,replay['verdict'],binding['archive_sha256'],len(files),flush=True)
