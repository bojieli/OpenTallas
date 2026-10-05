import argparse,hashlib,json,pathlib,subprocess
parser=argparse.ArgumentParser(description='Validate historical SRAM bindings; report current checkout drift without repinning the run.')
parser.add_argument('--root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[3],help='Current checkout whose drift is reported')
parser.add_argument('--source-git',type=pathlib.Path,help='Git repository containing the historical source commit (defaults to root)')
parser.add_argument('--output',type=pathlib.Path,help='Audit output path; defaults to the recovery record under root')
args=parser.parse_args()
root=args.root.resolve()
source_git=(args.source_git or root).resolve()
src=root/'results/rtl/w15b_sram_exact_retry_20261001'
sha=lambda b:hashlib.sha256(b).hexdigest()
c=json.loads((src/'campaign.json').read_text());b=json.loads((src/'binding.json').read_text())
pin=b['source_commit'];assert pin==c['git']['head']
checks=[]
drift={}
for p,h in c['source_sha256'].items():
 assert sha(subprocess.check_output(['git','show',pin+':'+p],cwd=source_git))==h,('historical source pin mismatch',p)
 current=sha((root/p).read_bytes()) if (root/p).is_file() else None
 if current!=h:drift[p]={'historical_sha256':h,'current_sha256':current}
checks.append(f"{len(c['source_sha256'])} source pins match the historical source commit in source_git")
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
out={'schema':'w15_current_sram_recovery_v1','verdict':'PASS_COMMITTED_BINDING','source_commit':pin,'source_git':str(source_git),'current_checkout':{'root':str(root),'source_drift':drift,'matches_historical_sources':not drift,'claim_boundary':'Informational comparison only; current source drift does not invalidate historical evidence or establish current execution.'},'evidence_commit':'d98e2396c3dcf710c36faded989febdf18d6cbc8','checks':checks,'claim_boundary':'Supersedes provenance-blocked V4.1 SRAM draft only for the two recorded exact simulation configs at the original source commit. No new simulation, physical closure, current-model calibration, or model adoption claimed. Original BLOCKED_PROVENANCE evidence preserved.','artifacts':{p.name:sha(p.read_bytes()) for p in [src/'campaign.json',src/'binding.json',src/'validation.json']}}
output=args.output or root/'results/rtl/w15_current_recovery_20261001/sram_audit.json'
output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
