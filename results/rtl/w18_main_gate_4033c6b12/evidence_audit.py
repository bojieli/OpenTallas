import datetime,hashlib,json,os,shutil,subprocess
from pathlib import Path
R=Path('/home/ubuntu/w18work/main_gate_4033c6b12_src'); W=Path(__file__).resolve().parent; E=W/'evidence'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda n:json.loads((E/n).read_text())
p=load('preflight.json');b=load('baseline_full.json');f=load('reconciliation_fresh.json');c=load('reconciliation_cached.json');x=load('exhaustive.json');done=load('completion.json')
assert len(p['main_rtl_inputs'])==14 and x['compiler_inputs']==['rtl/test/tb_chip_v41x_karb_local_hash_parallel.sv',*p['main_rtl_inputs']]
assert len(x['sources'])==17 and x['source_commit']==p['source_commit'] and x['log_sha256']==sha(E/'exhaustive.log')
assert len(b['runs'])==54 and len(b['kv_prefetch_bench'])==5 and all(t['pass'] for t in b['runs']+b['kv_prefetch_bench']) and b['pass'] is False
assert f['pass_'] and c['pass_'] and f['sources']==c['sources']==p['sources'] and done['source_pins_unchanged']
assert {s:sha(R/s) for s in p['sources']}==p['sources'] and x['sources_unchanged']
assert not f['runs']['exhaustive']['reused'] and c['runs']['exhaustive']['reused'] and load('cli_provenance_negative.json')['pass_']
for s in p['sources']:
 gitdata=subprocess.check_output(['git','-C',str(R),'show',p['source_commit']+':'+s]);assert hashlib.sha256(gitdata).hexdigest()==p['sources'][s]
build=W/'baseline_build';bins=sorted([*build.glob('*.vvp'),*build.glob('kvobj_*/Vtb_chip_v41x_kv_prefetch')]);assert len(bins)==8
manifest={str(t.relative_to(build)):dict(sha256=sha(t),bytes=t.stat().st_size) for t in bins}
(E/'baseline_build_binary_pins.json').write_text(json.dumps(dict(build_root=str(build),artifacts=manifest,source_commit=p['source_commit'],compiler_recipe_source='tools/rtl_chip_v41x_karb_local.py',compiler_recipe_sha256=p['sources']['tools/rtl_chip_v41x_karb_local.py']),indent=1)+'\n')
for src,dest in [('run.py','bounded_runner.py'),('verify_after.py','cache_cli_runner.py'),('runner.log','runner.log'),('finalize_evidence.py','evidence_audit.py')]:shutil.copyfile(W/src,E/dest)
proc=subprocess.check_output(['ps','-eo','pid,ppid,etime,rss,args'],text=True)
lines=[l for l in proc.splitlines() if ('/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad' in l and 'global_route.tcl' in l) or '/home/ubuntu/w18work/jobs/rebase_wait_only.sh' in l]
status=Path('/home/ubuntu/w18work/karb13/status.log').read_text()
assert 'PROOT_DLV_DONE' not in status
route=next(Path('/home/ubuntu/w18work/karb21/proot/orfs/logs/asap7').glob('*/base/5_1_grt.tmp.log'))
(E/'karb21_observation.json').write_text(json.dumps(dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),live_processes=lines,global_route_log=str(route),intermediate_tail=route.read_text().splitlines()[-15:],status_tail=status.splitlines()[-8:],final_ss_ff_pending=True,restarted=False,timing_claim=False),indent=1)+'\n')
summary=dict(source_commit=p['source_commit'],source_root=str(R),sources_match_git_commit=True,all_24_source_pins_unchanged=True,baseline=dict(pass_=False,transaction_pass=54,transaction_total=54,kv_pass=5,kv_total=5,hash=b['hash_steering_exhaustive'],diagnosis='Legacy bench increments multi for simultaneous pipelined outputs at different PCs. Unequal region HOPS allow this concurrency. Preserve raw FAIL; separate parallel bench retains local one-hot and checks destination/tag/address and exactly-once delivery.'),fresh_exhaustive=dict(pass_=True,sectors_per_arm=131072,compiler_inputs=15,rtl_inputs=14,source_pins=17,record='exhaustive.json',log='exhaustive.log'),fresh_and_cached_reconciliation_pass=True,delivery_negative_controls=['wrong_tag','duplicate','missing_pc0'],cli_provenance_negatives=['stale_rtl','stale_bench','changed_log'],unit_regressions=7,adoption=False,rtl_changes=False,constraint_changes=False,model_changes=False,physical_verdicts_unchanged=True,claim='Fresh functional reconciliation on actual main sources pinned at 4033c6b12; no claim about a later main HEAD, physical signoff or model gain.',integration_prerequisites=['Parent cherry-picks only this evidence commit onto main; parent owns TASKS and push.','Compare all recorded source hashes to integration main. Any mismatch requires a new baseline and fresh exhaustive record, not historical RTL transplantation.','Retain baseline_full.json FAIL and historical failure/reconciliation files byte-identical.','Karb21 final SS/FF remains pending; KSREG and clock-tree levers remain rejected.','Hardware adoption still requires model-priced gain and contextual SS setup / FF hold with unchanged 60ps / 25ps uncertainty.'],remaining_blockers=['karb21 global route live; final SS/FF unavailable','W10 p12q/c2 abstracts pending; parent diagnoses W10'],resource_observations=dict(disk_free_after_bytes=shutil.disk_usage(W).free,limits=p),legacy_tree='Dirty agent-a617e8fc25350daf6 preserved; prior BF16 stand-in review remains evidence, no CKV transplant.')
(E/'assessment.json').write_text(json.dumps(summary,indent=1)+'\n')
(E/'evidence_sha256.json').write_text(json.dumps({t.name:sha(t) for t in sorted(E.iterdir()) if t.is_file()},indent=1)+'\n')
print('All pinned-main assertions pass;',len(list(E.iterdir())),'evidence files; binaries',len(bins))
