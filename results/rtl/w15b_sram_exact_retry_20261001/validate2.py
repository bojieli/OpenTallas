import hashlib,json,pathlib,subprocess,os,shutil
root=pathlib.Path.cwd();out=root/'results/rtl/w15b_sram_exact_retry_20261001';rec=json.loads((out/'campaign.json').read_text());head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert rec['git']['head']==head
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
for p,h in rec['source_sha256'].items():assert sha(root/p)==h,p
build=pathlib.Path(os.environ['W15_BUILD']);vec=pathlib.Path(os.environ['W15_VEC']);binding={'schema':'w15b_sram_exact_binding_v1','source_commit':head,'runner_sha256':sha('/tmp/claude-1000/w15b_codex_sram_20261001/run2.sh'),'validator_sha256':sha(__file__),'claim_boundary':'Exact RTL simulation on merged renamed modules; no P&R or SS/FF closure claimed. Model-config: SS lane-map, 0.833 ns, wire 32, LAT7, pace 7/8, 32 lanes, SRAM 512.','configs':{}}
for name,c in rec['configs'].items():
 assert c['free_running']['all_passed'] and c['deterministic']['all_passed'];assert c['deterministic']['distinct_timings']==1 and c['deterministic']['distinct_results']==1 and c['deterministic']['late_faults']==0
 manifest=build/c['binary']/'w15_sources.json';m=json.loads(manifest.read_text());assert m['gen']==c['parameters']
 for p,h in m['pins'].items():assert sha(root/p)==h and rec['source_sha256'][p]==h,p
 fixture=vec/c['fixture'];fm=json.loads((fixture/'manifest.json').read_text());assert sha(fixture/'manifest.json')==c['fixture_manifest_sha256']
 for p,h in fm['images_sha256'].items():assert sha(fixture/p)==h
 target=out/name;target.mkdir();shutil.copy2(manifest,target/'binary_sources.json');shutil.copy2(build/c['binary']/('V'+c['top']+'__verFiles.dat'),target/'verFiles.dat');shutil.copy2(fixture/'manifest.json',target/'fixture_manifest.json')
 rows=[]
 for p in sorted((build/'runs'/name).iterdir()):
  t=(p/'log.txt').read_text();assert 'W15DONE' in t and 'faults=0' in t and 'W15FINALMISMATCH' not in t and '%Fatal' not in t and '%Error' not in t
  dest=target/'logs'/p.name;dest.mkdir(parents=True);shutil.copy2(p/'log.txt',dest/'log.txt');rows.append({'run':p.name,'log_sha256':sha(p/'log.txt'),'vm_sha256':sha(p/'vm.hex')})
 assert len(rows)==40
 binding['configs'][name]={'binary_sha256':sha(build/c['binary']/('V'+c['top'])),'binary_sources_sha256':sha(manifest),'runs':rows,'sum_cycles':c['sum_issue_to_last_commit_cycles']}
(out/'binding.json').write_text(json.dumps(binding,indent=2,sort_keys=True)+'\n');print('EXACT_BINDING_PASS',head,flush=True)
