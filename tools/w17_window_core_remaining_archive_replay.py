#!/usr/bin/env python3
"""Export/replay terminal evidence only. No simulation, build, service or absolute-path reads during replay."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REMAINING=Path('/tmp/opentallas-core-remaining-acceptance-edge-parent-20261002-r1')
FIRST=Path('/tmp/opentallas-core-first-acceptance-edge-parent-20261002-r1')
BASELINE=Path('/tmp/opentallas-core-retained-binary-full27-campaign-20261002-r2')
CAP=134217728

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load(p):return json.loads(p.read_text())
def need(ok,msg):
 if not ok:raise ValueError(msg)
def put(p,data):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
def within(path):
 p=Path(path);need(not p.is_absolute() and '..' not in p.parts,'relative archive path required');return p

def export(out,remaining=REMAINING,first=FIRST,baseline=BASELINE):
 # Refuse before creating archive while either service lacks a final receipt.
 for run in (remaining,first):
  need((run/'record.json').exists() and (run/'service_receipt.json').exists(),'terminal evidence not available; no archive created')
 out=Path(out);need(not out.exists(),'fresh archive directory required')
 records={'remaining':load(remaining/'record.json'),'first':load(first/'record.json')}
 for name,run in [('remaining',remaining),('first',first)]:
  t=load(run/'service_receipt.json');need('MainPID=0' in t['terminal'] and 'ActiveState=active\n' not in t['terminal'],'terminal service required')
 out.mkdir(parents=True)
 context={'schema':1,'runs':{},'archive_claim':'Offline receipt/source/expectation replay only, not RTL rerun or binary qualification.','binary_files_included':False,'physical_provider':False,'fulltoken':False,'changed_bench_healthy23_qualification':False}
 for name,run in [('remaining',remaining),('first',first),('baseline',baseline)]:
  launch=load(run/'launch.json');command=launch['command'];plan=Path(command[command.index('--plan')+1]);go_path=command[command.index('--go-path')+1]
  put(out/'plans'/f'{name}.json',plan.read_bytes())
  go=subprocess.check_output(['git','show',launch['GO_commit']+':'+go_path],cwd=ROOT)
  put(out/'GO'/f'{name}.json',go)
  runner=Path(command[command.index('--worker')-1]);spec=load(plan)
  need(sha(runner)==spec['runner_sha256'],'actual runner source hash')
  put(out/'runners'/f'{name}.py',runner.read_bytes())
  for path,h in spec['dependencies_sha256'].items():
   need(sha(ROOT/within(path))==h,'runner dependency source hash '+path)
   put(out/'dependencies'/name/within(path),(ROOT/path).read_bytes())
  context['runs'][name]={'original_output':str(run),'GO_commit':launch['GO_commit'],'GO_path':go_path,'record_verdict':load(run/'record.json')['verdict']}
  for f in sorted(run.iterdir()):
   if f.is_file() and not f.is_symlink():put(out/'runs'/name/f.name,f.read_bytes())
  labels=['physical_QE_gate'] if name=='first' else ['baseline'] if name=='baseline' else [j['label'] for j in load(plan)['jobs']]
  for label in labels:
   home=run/label
   if not home.exists():continue
   for f in sorted(home.iterdir()):
    if f.is_file() and not f.is_symlink():put(out/'runs'/name/label/f.name,f.read_bytes())
   if (home/'snapshot_sha256.json').exists():
    snapshot=load(home/'snapshot_sha256.json')
    for path,h in snapshot.items():need(sha(home/'sources'/within(path))==h,'actual source snapshot mismatch '+path)
 # Canonical sources come from the completed actual first-control snapshot,
 # reversing ONLY its unique declared mutation and verifying all166 original pins.
 firstplan=load(out/'plans/first.json');job=firstplan['jobs'][0];m=job['mutation'];target='rtl/test/w17_window_core_cancel_join_r8/actual_fastpp_core_selected_cone.sv'
 for path,h in firstplan['source_files_sha256'].items():
  data=(first/'physical_QE_gate/sources'/within(path)).read_bytes()
  if path==target:
   text=data.decode();start=text.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #(')
   need(text[start:].count(m['new'])==1,'unique first mutation inverse')
   data=(text[:start]+text[start:].replace(m['new'],m['old'])).encode()
  need(hashlib.sha256(data).hexdigest()==h,'canonical source identity '+path)
  put(out/'canonical_sources'/within(path),data)
 put(out/'context.json',(json.dumps(context,indent=2)+'\n').encode())
 put(out/'replay.py',Path(__file__).read_bytes())
 files={p.relative_to(out).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file()}
 need(sum(x['bytes'] for x in files.values())<=CAP,'bounded archive output cap')
 put(out/'manifest.json',(json.dumps({'schema':1,'files':files,'bytes':sum(x['bytes'] for x in files.values())},indent=2)+'\n').encode())
 result=verify(out)
 put(out/'review.json',(json.dumps(result,indent=2)+'\n').encode())
 return result

def check_runtime(case,step,text,source):
 clean=all(step.get('cap_events',{}).get(k)==0 for k in ('max','oom','oom_kill','oom_group_kill'))
 need(clean,'runtime cap/OOM receipt')
 if case['expected']=='PASS':need(step['returncode']==0 and case['marker'] in text and not re.search(r'%Error|Assertion failed|FAIL_PROVIDER',text),'positive receipt')
 else:
  site=case['fatal_receipt'];n=site['line'];marker=re.escape(case['marker']);filename=re.escape(str(Path(source)/site['basename']))
  pattern=rf'\A\[[0-9]+\] %Fatal: {re.escape(site["basename"])}:{n}: Assertion failed in {re.escape(site["top"])}: {marker}\n%Error: {filename}:{n}: Verilog \$stop\nAborting\.\.\.\n\Z'
  need(step['returncode']==1 and re.fullmatch(pattern,text) is not None,'exact negative exit1/source/marker/site receipt')

def verify(out):
 out=Path(out);manifest=load(out/'manifest.json');context=load(out/'context.json')
 need(set(context['runs'])=={'first','remaining','baseline'},'exact archived run scope')
 for path,meta in manifest['files'].items():
  f=out/within(path);need(f.is_file() and not f.is_symlink() and f.resolve().is_relative_to(out.resolve()) and sha(f)==meta['sha256'] and f.stat().st_size==meta['bytes'],'archive hash '+path)
 need(sum(x['bytes'] for x in manifest['files'].values())==manifest['bytes']<=CAP,'archive bounded size')
 plans={name:load(out/'plans'/f'{name}.json') for name in context['runs']}
 first=plans['first'];remaining=plans['remaining'];need(first['source_files_sha256']==remaining['source_files_sha256'],'same first/remaining source166')
 canonical=out/'canonical_sources'
 for path,h in first['source_files_sha256'].items():need(sha(canonical/within(path))==h,'canonical source '+path)
 need(remaining['source_geometry']==first['source_geometry']=={'SUN':256,'SUM':64,'BL':16,'IL':8,'NBMAX':192,'CHUNK8':1,'MP':1,'AW':30,'NW':21},'full source geometry')
 summaries=[];closed_labels={};terminal={}
 for name,p in plans.items():
  run=out/'runs'/name;meta=context['runs'][name];t=load(run/'service_receipt.json');record=load(run/'record.json');terminal[name]=t
  need('MainPID=0' in t['terminal'],'terminal PID0')
  launch=load(run/'launch.json');need(launch['plan_sha256']==sha(out/'plans'/f'{name}.json'),'plan launch SHA')
  g=load(out/'GO'/f'{name}.json');need(g['plan_sha256']==sha(out/'plans'/f'{name}.json'),'GO plan SHA')
  for key in ('runner_sha256','caps','budget'):need(g[key]==p[key],'GO '+key)
  need(g['source_digest']==digest(p['source_files_sha256']),'GO source digest')
  expected_status={'first':'PARENT_ACTUAL_CORE_ACCEPTANCE_EDGE_FIRST_SINGLE_GO','remaining':'PARENT_ACTUAL_CORE_ACCEPTANCE_EDGE_REMAINING_SINGLE_GO','baseline':'PARENT_ACTUAL_CORE_RETAINED_BINARY_FULL27_SINGLE_GO'}[name]
  need(g['status']==g['requested_status']==expected_status,'exact GO status')
  for key,field in [('jobs_digest','jobs'),('dependencies_digest','dependencies_sha256'),('build_toolchain_digest','build_toolchain')]:need(g[key]==digest(p[field]),'GO field digest '+key)
  if name!='baseline':need(record['source_pins']==p['source_files_sha256'] and record['physical_provider'] is False and record['fulltoken'] is False,'record scope/source pins')
  need(sha(out/'runners'/f'{name}.py')==p['runner_sha256'],'archived actual runner SHA')
  for path,h in p['dependencies_sha256'].items():need(sha(out/'dependencies'/name/within(path))==h,'archived runner dependency SHA')
  caps=load(run/'caps_before_compile.json')['systemd']
  need(caps['MemoryMax']=='34359738368' and caps['MemorySwapMax']=='0' and caps['LimitFSIZE']=='1073741824' and caps['CPUAffinity'] in ('30-31','30 31'),'actual resource caps')
  if name=='first':need(caps['RuntimeMaxUSec'] in ('12min','720000000'),'first whole cap')
  if name=='remaining':need(caps['RuntimeMaxUSec'] in ('37min 30s','2250000000'),'remaining whole cap')
  rows=[json.loads(line) for line in (run/'resource_samples.jsonl').read_text().splitlines()]
  for row in rows:
   if row.get('memory.events'):
    e=dict(line.split() for line in row['memory.events'].splitlines());need(all(int(e[k])==0 for k in ('max','oom','oom_kill','oom_group_kill')),'sampled cap/OOM events')
  closed_labels[name]=[]
  jobs=p['jobs'] if name!='baseline' else [p['jobs'][0]]
  for job in jobs:
   home=run/job['label'];closure=home/'phase_closed.json'
   if not closure.exists():continue
   c=load(closure);need(c['status']=='PHASE_SEMANTIC_RECEIPTS_CLOSED' and c['job']==job and c['GO_commit']==meta['GO_commit'] and c['plan_sha256']==sha(out/'plans'/f'{name}.json'),'phase job/GO identity')
   for path,e in c['retained_evidence_files'].items():need(sha(home/within(path))==e['sha256'] and (home/path).stat().st_size==e['bytes'],'phase evidence '+path)
   need(digest(c['generated_files'])==c['generated_inventory_sha256'] and sum(x['bytes'] for x in c['generated_files'].values())==c['generated_bytes'],'generated inventory closure')
   need(c['generated_files']['Vtb']['sha256']==c['binary']['sha256'],'binary inventory hash provenance')
   snapshot=load(home/'snapshot_sha256.json');need(set(snapshot)==set(p['source_files_sha256'])|{'tb.sv'},'snapshot file scope')
   for path,h in snapshot.items():
    original=canonical/within(path) if path!='tb.sv' else canonical/('rtl/test/w17_window_core_cancel_join_r8/tb.sv' if name=='baseline' else 'rtl/test/w17_window_core_cancel_join_acceptance_edge/tb.sv')
    data=original.read_bytes();m=job['mutation'];target='tb.sv' if m and m.get('target')=='bench' else 'rtl/test/w17_window_core_cancel_join_r8/actual_fastpp_core_selected_cone.sv'
    if m and path==target:
     text=data.decode();start=0 if target=='tb.sv' else text.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #(')
     need(text[start:].count(m['old'])==1,'unique mutation');data=(text[:start]+text[start:].replace(m['old'],m['new'])).encode()
    need(hashlib.sha256(data).hexdigest()==h==c['source_files'][path]['sha256'] and len(data)==c['source_files'][path]['bytes'],'exact compiled snapshot '+path)
   need(len(c['steps'])==1+len(job['cases']) and c['steps'][0]['returncode']==0,'all phase cases and successful compile')
   need(sha(home/Path(c['steps'][0]['log']).name)==c['steps'][0]['log_sha256'],'compile receipt log SHA')
   if (home/'frontend.log').exists():need('%Warning-UNOPTFLAT:' not in (home/'frontend.log').read_text(),'loop-free frontend')
   for case,step in zip(job['cases'],c['steps'][1:]):
    log=home/Path(step['log']).name;need(sha(log)==step['log_sha256'],'runtime log SHA')
    need(step['command']==[str(Path(meta['original_output'])/job['label']/'obj/Vtb')]+case['args'],'runtime command')
    check_runtime(case,step,log.read_text(),step['runtime_source_directory'])
   closed_labels[name].append(job['label']);summaries.append({'run':name,'phase':job['label'],'cases':len(job['cases']),'closure_sha256':sha(closure),'binary_receipt':c['binary'],'runtime_seconds':sum(s['wall_seconds'] for s in c['steps'][1:])})
  if name=='first':need(record['verdict']=='PASS_ACCEPTANCE_EDGE_FIRST_CONTROL_ONLY' and closed_labels[name]==['physical_QE_gate'] and t['returncode']==0 and 'Result=success' in t['terminal'],'first strict PASS dependency')
  if name=='remaining' and record['verdict']=='PASS_ACCEPTANCE_EDGE_REMAINING_CONTROL_ONLY':need(len(closed_labels[name])==3 and t['returncode']==0 and 'Result=success' in t['terminal'],'remaining strict PASS')
  elif name=='remaining':need(t['returncode']!=0 and record.get('no_retry',True),'remaining FAIL preserved')
 # The fresh remaining GO binds the actual reviewed first terminal and phase hashes.
 g=load(out/'GO/remaining.json');d=g['first_control_dependency'];need(d['status']=='PARENT_REVIEWED_ACCEPTANCE_EDGE_FIRST_CONTROL_PASS','parent-reviewed first dependency')
 for path,key in [('record.json','record_sha256'),('service_receipt.json','service_sha256'),('physical_QE_gate/phase_closed.json','closure_sha256')]:need(sha(out/'runs/first'/path)==d[key],'first dependency hash '+key)
 need(d['output']==context['runs']['first']['original_output'],'first dependency output identity')
 return {'status':'OFFLINE_REPLAY_VERIFIED_TERMINAL_EVIDENCE','remaining_verdict':load(out/'runs/remaining/record.json')['verdict'],'remaining_terminal':terminal['remaining'],'phases':summaries,'canonical_source_count':len(first['source_files_sha256']),'manifest_sha256':sha(out/'manifest.json'),'archive_bytes':manifest['bytes'],'actual_binaries_replayed':False,'binary_scope':'Closed inventory/hash provenance only; no binary files or RTL execution.','first_dependency_verified':True,'historical_baseline23':'Original bench only','changed_bench_healthy23_qualification':False,'full27_newbench_qualification':False,'physical_provider':False,'fulltoken':False}

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--export',action='store_true');group.add_argument('--verify',action='store_true');ap.add_argument('--out',required=True);ap.add_argument('--remaining',default=str(REMAINING));ap.add_argument('--first',default=str(FIRST));ap.add_argument('--baseline',default=str(BASELINE));a=ap.parse_args()
 print(json.dumps(export(a.out,Path(a.remaining),Path(a.first),Path(a.baseline)) if a.export else verify(a.out),indent=2))
