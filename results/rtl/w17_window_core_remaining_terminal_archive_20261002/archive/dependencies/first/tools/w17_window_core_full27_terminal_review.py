"""Read-only independent semantic/hash review of closed actual-core campaign phases."""
import json,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/tmp/opentallas-core-retained-binary-full27-campaign-20261002-r2')
PLAN=ROOT/'results/uarch/w17_window_core_cancel_retained_binary_campaign_20261002/plan_r1/plan.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
p=json.loads(PLAN.read_text());answers=[]
for job in p['jobs']:
 home=OUT/job['label'];path=home/'phase_closed.json'
 if not path.exists():break
 v=json.loads(path.read_text());assert v['job']==job and v['plan_sha256']==sha(PLAN)
 assert v['GO_commit']=='fd9c4f7be3095b9fc567f6edfd80a1b82dac50e4'
 assert v['status']=='PHASE_SEMANTIC_RECEIPTS_CLOSED' and v['no_source_or_expectation_change']
 for name,meta in v['retained_evidence_files'].items():
  f=home/name;assert f.is_file() and not f.is_symlink();assert sha(f)==meta['sha256'] and f.stat().st_size==meta['bytes']
 snapshot=json.loads((home/'snapshot_sha256.json').read_text())
 assert set(snapshot)==set(p['source_files_sha256'])|{'tb.sv'}
 for name,h in snapshot.items():
  f=home/'sources'/name;assert sha(f)==h==v['source_files'][name]['sha256'];assert f.stat().st_size==v['source_files'][name]['bytes']
  expected=p['source_files_sha256'].get(name,p['source_files_sha256']['rtl/test/w17_window_core_cancel_join_r8/tb.sv'])
  mutation=job['mutation'];target='tb.sv' if mutation and mutation.get('target')=='bench' else 'rtl/test/w17_window_core_cancel_join_r8/actual_fastpp_core_selected_cone.sv'
  if mutation and name==target:
   original=(ROOT/('rtl/test/w17_window_core_cancel_join_r8/tb.sv' if name=='tb.sv' else name)).read_text()
   start=0 if name=='tb.sv' else original.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #(')
   assert original[start:].count(mutation['old'])==1
   changed=original[:start]+original[start:].replace(mutation['old'],mutation['new'])
   expected=hashlib.sha256(changed.encode()).hexdigest()
  assert h==expected,(job['label'],name)
 assert len(v['steps'])==1+len(job['cases']) and v['steps'][0]['returncode']==0
 for case,step in zip(job['cases'],v['steps'][1:]):
  log=Path(step['log']);text=log.read_text();assert sha(log)==step['log_sha256']
  assert step['command']==[str(home/'obj/Vtb')]+case['args'] and step['wall_seconds']<=case['seconds']+.5
  assert all(step['cap_events'].get(k)==0 for k in ('max','oom','oom_kill','oom_group_kill'))
  if case['expected']=='PASS':assert step['returncode']==0 and case['marker'] in text and not re.search(r'%Error|Assertion failed|FAIL_PROVIDER',text)
  else:
   site=case['fatal_receipt'];n=site['line'];marker=re.escape(case['marker']);source=re.escape(str(home/'sources/tb.sv'))
   pat=rf'\A\[[0-9]+\] %Fatal: tb.sv:{n}: Assertion failed in tb: {marker}\n%Error: {source}:{n}: Verilog \$stop\nAborting\.\.\.\n\Z'
   assert step['returncode']==1 and re.fullmatch(pat,text)
 assert digest(v['generated_files'])==v['generated_inventory_sha256']
 assert sum(x['bytes'] for x in v['generated_files'].values())==v['generated_bytes']
 assert v['generated_files']['Vtb']['sha256']==v['binary']['sha256']
 if job['label']=='baseline':assert v['binary']['sha256']==p['compiled_artifact']['binary_sha256']
 answers.append({'phase':job['label'],'cases':len(job['cases']),'closure_sha256':sha(path),'binary_sha256':v['binary']['sha256'],'runtime_seconds':sum(s['wall_seconds'] for s in v['steps'][1:]),'semantic_source_and_evidence_hashes':'PASS','reclaimed_binary':'Receipt/inventory provenance checked; reclaimed copies cannot be rehashed.'})

record=json.loads((OUT/'record.json').read_text());terminal=json.loads((OUT/'service_receipt.json').read_text());progress=json.loads((OUT/'progress_at_failure.json').read_text())
assert record['verdict']=='FAIL_RUNTIME_PRESERVED' and record['stage']=='physical_QE_gate/runtime_0'
assert terminal['returncode']==1 and all(x in terminal['terminal'] for x in ('MainPID=0','Result=exit-code','ExecMainStatus=1','ActiveState=failed'))
job=p['jobs'][1];home=OUT/job['label'];snapshot=json.loads((home/'snapshot_sha256.json').read_text())
assert set(snapshot)==set(p['source_files_sha256'])|{'tb.sv'}
for name,h in snapshot.items():
 assert sha(home/'sources'/name)==h
 expected=p['source_files_sha256'].get(name,p['source_files_sha256']['rtl/test/w17_window_core_cancel_join_r8/tb.sv'])
 if name=='rtl/test/w17_window_core_cancel_join_r8/actual_fastpp_core_selected_cone.sv':
  original=(ROOT/name).read_text();mut=job['mutation'];start=original.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #(')
  assert original[start:].count(mut['old'])==1
  expected=hashlib.sha256((original[:start]+original[start:].replace(mut['old'],mut['new'])).encode()).hexdigest()
 assert h==expected
steps=progress['steps'];front,cxx,runtime=steps[-3:]
assert front['returncode']==cxx['returncode']==0 and runtime['returncode']==1
for step in (front,cxx,runtime):assert sha(Path(step['log']))==step['log_sha256']
assert front['command']==[x.format(out=str(OUT)) for x in job['frontend_command']]
assert cxx['command']==[x.format(out=str(OUT)) for x in job['CXX_command']]
assert '%Warning-UNOPTFLAT:' not in (home/'frontend.log').read_text()
assert runtime['command']==[str(home/'obj/Vtb'),'+CUT=GO']
assert all(runtime['cap_events'][k]==0 for k in ('max','oom','oom_kill','oom_group_kill'))
actual='local ACK before actual suffix and logical EMPTY';line=1345;text=(home/'runtime_0.log').read_text()
expected_text=f'[13000] %Fatal: tb.sv:{line}: Assertion failed in tb: {actual}\n%Error: {home}/sources/tb.sv:{line}: Verilog $stop\nAborting...\n'
assert text==expected_text and job['cases'][0]['marker'] not in text
binary=json.loads((home/'binary_receipt.json').read_text());assert sha(home/'obj/Vtb')==binary['sha256'] and (home/'obj/Vtb').stat().st_size==binary['bytes']
assert not (home/'phase_closed.json').exists() and all(not (OUT/j['label']).exists() for j in p['jobs'][2:])
cap=json.loads((OUT/'caps_before_compile.json').read_text())['systemd']
for name,value in {'MemoryMax':'34359738368','MemorySwapMax':'0','LimitFSIZE':'1073741824','RuntimeMaxUSec':'1h','KillMode':'control-group','KillSignal':'9','OOMPolicy':'stop'}.items():assert cap[name]==value
assert cap['CPUAffinity'] in ('30-31','30 31')
rows=[json.loads(x) for x in (OUT/'resource_samples.jsonl').read_text().splitlines()]
for row in rows:
 if row.get('memory.events'):
  events=dict(x.split() for x in row['memory.events'].splitlines())
  assert all(int(events[k])==0 for k in ('max','oom','oom_kill','oom_group_kill'))
files=['record.json','service_receipt.json','progress_at_failure.json','caps_before_compile.json','launch.json','resource_samples.jsonl','service_journal.txt','baseline/phase_closed.json','physical_QE_gate/binary_receipt.json','physical_QE_gate/snapshot_sha256.json','physical_QE_gate/frontend.log','physical_QE_gate/CXX.log','physical_QE_gate/runtime_0.log']
print(json.dumps({'review_verdict':'VERIFIED_DECLARED_CAMPAIGN_FAIL_PRESERVED','unit':'w17-recovery-resource-retained-full27-parent-20261002-r2.service','output':str(OUT),'terminal':terminal,'closed_phases':answers,'declared_expected':job['cases'][0],'observed_fatal':{'marker':actual,'line':line,'returncode':1,'wall_seconds':runtime['wall_seconds'],'time_ps':13000},'first_fault_assertion_precedes_expected_assertion':True,'interpretation':'Mutant provoked an earlier real fixture invariant fatal; the exact predeclared mutant predicate rejected it. No reinterpretation as PASS, no expectation edit, no retry. Unmodified baseline passed23cases; remaining3mutants NOT_RUN.','mutant_binary_rehashed':binary,'mutant_source163_plus_alias_exact':True,'compile_seconds':{'frontend':front['wall_seconds'],'CXX':cxx['wall_seconds'],'aggregate':progress['compile_shared_wall_seconds']},'runtime_shared_seconds':progress['runtime_shared_wall_seconds'],'sampled_memory_peak_bytes':max(int(r['memory.peak']) for r in rows if r.get('memory.peak')),'all_cap_OOM_events_clean':True,'retained_file_sha256':{n:sha(OUT/n) for n in files},'plan_sha256':sha(PLAN),'source_pin':'4e38326d6f361bc85e660f48c59c355e2bb95274','no_execution_in_review':True,'physical_provider':False,'fulltoken':False,'full27_qualification':False},indent=2))
