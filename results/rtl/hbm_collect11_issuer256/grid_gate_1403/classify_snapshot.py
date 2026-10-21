"""Metadata-only canonical replay; never executes a physical flow or changes its FAIL."""
import hashlib, io, json, os, subprocess, sys, tarfile
from pathlib import Path
sha=lambda x:hashlib.sha256(x).hexdigest()
repo=Path(sys.argv[1]).resolve(); dest=Path(sys.argv[2]).resolve(); dest.mkdir(parents=True,exist_ok=True)
rel=Path('results/rtl/hbm_collect11_issuer256/grid_gate_1403')
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
 replay['classification_archive']={'path':str(archive),'sha256':sha(data),'bytes':len(data)}
 replay['physical_input_comparison']={'original_consumed_physical_count':len(original_physical),'changed_paths':changed,'all_other_physical_bytes_unchanged':True}
 replay['review_state']='PENDING_ROOT_INTEGRATION_VALIDATION_NO_SUBMIT'
 (repo/rel/(k+'.classification_snapshot.json')).write_text(json.dumps(replay,indent=1)+'\n')
 print(k,replay['verdict'],binding['archive_sha256'],len(files),flush=True)
