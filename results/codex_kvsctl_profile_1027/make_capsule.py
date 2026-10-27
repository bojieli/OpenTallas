import pathlib,json,subprocess,hashlib,shutil,sys
W=pathlib.Path(__file__).resolve().parents[2];R=pathlib.Path('results/codex_kvsctl_profile_1027');O=W/R;O.mkdir(parents=True,exist_ok=True);SHA=subprocess.check_output(['git','rev-parse','bc1a556176'],cwd=W,text=True).strip();base='results/kv_cores_r2/kvsctl3';manifest={}
def read(p):return subprocess.check_output(['git','show',f'{SHA}:{p}'],cwd=W)
def snap(p):
 target=O/'proof_src'/p
 if p not in manifest:
  b=read(p);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b);blob=subprocess.check_output(['git','rev-parse',f'{SHA}:{p}'],cwd=W,text=True).strip();manifest[p]={'snapshot':str(R/'proof_src'/p),'git_blob':blob,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
 return str(R/'proof_src'/p)
corepath=base+'/rtl/qkd_kvs_ctl_core.json';kitpath=base+'/kit_rtl/kv3_hub_C/kit_rtl.json';core=json.loads(read(corepath));kit=json.loads(read(kitpath));assert len(core['files'])==46
for p in core['files']+kit['files']+[corepath,kitpath,core['bound'],base+'/kit_rtl/kv3_hub_C/kit_rtl.f',base+'/rtl/dead_drop.json',core['landing']['plan'],base+'/README.md']:
 snap(p)
for h in kit['hard_macros'].values():
 for k,v in h.items():
  if k=='dir':continue
  for p in v if isinstance(v,list) else [v]:snap(p)
# Pin metadata is part of this exact profile, not an assertion it fits the current physical plan.
snap(core['report']['pins_file'])
core['files']=[snap(p) for p in core['files']];core['bound']=snap(core['bound']);core['report']['pins_file']=snap(core['report']['pins_file']);core['landing']['plan']=snap(core['landing']['plan']);core['dead_drop']['file']=snap(base+'/rtl/dead_drop.json')
core['source_profile']={'source_commit':SHA,'scope':'Exact46-file BC profile matching composed face proof; current native binding/G5 not claimed','proof_kind':'source-identical COMPOSED: reused positive plus fresh mutant'}
kit['files']=[snap(p) for p in kit['files']]
for h in kit['hard_macros'].values():
 for k,v in list(h.items()):
  h[k]=str(R/'proof_src'/v) if k=='dir' else [snap(p) for p in v] if isinstance(v,list) else snap(v)
kit['bind_out']=str(R/'proof_src'/base/'kit_rtl');kit['source_profile']=core['source_profile']
(O/'core.json').write_text(json.dumps(core,indent=1)+'\n');(O/'kit_rtl.json').write_text(json.dumps(kit,indent=1)+'\n');(O/'kit_rtl.f').write_text('\n'.join(kit['files'])+'\n');(O/'landing_ledger.json').write_text(json.dumps(core['landing'],indent=1)+'\n')
face=O/'face';face.mkdir(exist_ok=True);src=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else face;actual={}
for n in ['qkd_kvs_ctl.v','hr_face_ports.json','eq_rc.txt','composed_proof.json']:
 b=(src/n).read_bytes();(face/n).write_bytes(b);actual[n]={'source':str(src/n),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
(O/'manifest.json').write_text(json.dumps({'source_commit':SHA,'core_dependency_count':46,'source_files':manifest,'actual_composed_face':actual},indent=1)+'\n')
# Verify raw snapshots hash-identical and every rewritten functional input resolves repo-relative.
for p,v in manifest.items():assert hashlib.sha256((W/v['snapshot']).read_bytes()).hexdigest()==v['sha256']
for p in core['files']+kit['files']+[core['bound']]:assert not pathlib.Path(p).is_absolute() and (W/p).is_file(),p
print('PROFILE_CAPSULE_PASS',SHA,'core46',len(core['files']),'snapshots',len(manifest),'actualface4',len(actual))
