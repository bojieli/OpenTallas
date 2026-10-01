import hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[3]
src=root/'results/rtl/w15b_sram_exact_retry_20261001'
sha=lambda b:hashlib.sha256(b).hexdigest()
c=json.loads((src/'campaign.json').read_text());b=json.loads((src/'binding.json').read_text())
pin=b['source_commit'];assert pin==c['git']['head']
checks=[]
for p,h in c['source_sha256'].items():
 assert sha(subprocess.check_output(['git','show',pin+':'+p],cwd=root))==h,p
 assert sha((root/p).read_bytes())==h,p
checks.append('33 source pins match source commit and recovery checkout')
for name,v in c['configs'].items():
 mpath=src/name/'binary_sources.json';m=json.loads(mpath.read_text());bv=b['configs'][name]
 assert sha(mpath.read_bytes())==bv['binary_sources_sha256']
 assert m['gen']==v['parameters']
 for p,h in m['pins'].items():assert c['source_sha256'][p]==h,p
 assert sha((src/name/'fixture_manifest.json').read_bytes())==v['fixture_manifest_sha256']
 assert v['free_running']['all_passed'] and v['deterministic']['all_passed']
 assert v['deterministic']['distinct_timings']==v['deterministic']['distinct_results']==1
 assert v['deterministic']['late_faults']==0
 assert len(bv['runs'])==40
 for row in bv['runs']:
  data=(src/name/'logs'/row['run']/'log.txt').read_bytes();assert sha(data)==row['log_sha256']
  t=data.decode();assert 'W15DONE' in t and 'faults=0' in t
  assert not any(x in t for x in ['W15FINALMISMATCH','%Fatal','%Error'])
 checks.append(name+': parameters, binary source manifest, fixture manifest, 40 raw logs, exact deterministic gate verified')
assert sha((src/'run2.sh').read_bytes())==b['runner_sha256']
assert sha((src/'validate2.py').read_bytes())==b['validator_sha256']
out={'schema':'w15_current_sram_recovery_v1','verdict':'PASS_COMMITTED_BINDING','source_commit':pin,'evidence_commit':'d98e2396c3dcf710c36faded989febdf18d6cbc8','checks':checks,'claim_boundary':'Supersedes provenance-blocked V4.1 SRAM draft only for the two recorded exact simulation configs. No new simulation, physical closure, or model adoption claimed. Original BLOCKED_PROVENANCE evidence preserved.','artifacts':{p.name:sha(p.read_bytes()) for p in [src/'campaign.json',src/'binding.json',src/'validation.json']}}
(root/'results/rtl/w15_current_recovery_20261001/sram_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
