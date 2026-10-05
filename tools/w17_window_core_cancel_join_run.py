#!/usr/bin/env python3
"""One fresh-GO actual core/SU/QE/selected-owner gate; stop first failure."""
import argparse,importlib.util,json,subprocess,hashlib,re,sys,time,shutil,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import w17_window_recovery_fatal_gate_run as cap
MODEL=ROOT/'results/uarch/w17_window_core_cancel_join_preparation_r5_20261002/model.json'
STATUS='PARENT_ACTUAL_CORE_SU_QE_OWNER_CANCEL_SINGLE_GATE_GO'
PRODUCER='rtl/test/w17_window_actual_producer_cancel_declaration_repaired/ot_hdc_v41x_window_kv_blocks_cancel.sv'
RECORD=ROOT/'results/rtl/w17_window_recovery_candidate_prepared_20261002/record.json'
TOOL=Path(__file__).resolve()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def inputs():
 m=json.loads(MODEL.read_text());r=json.loads(RECORD.read_text())
 files=dict(m['original_source_sha256'])
 files.update({m['runtime_cone_path']:m['runtime_cone_sha256'],PRODUCER:sha(ROOT/PRODUCER),
  'rtl/test/w17_window_core_cancel_join_r5/tb.sv':m['bench_sha256'],
  str(MODEL.relative_to(ROOT)):sha(MODEL),str(RECORD.relative_to(ROOT)):sha(RECORD),
  'tools/w17_window_recovery_fatal_gate_run.py':sha(ROOT/'tools/w17_window_recovery_fatal_gate_run.py'),
  'tools/w17_window_core_cancel_source_prepare.py':sha(ROOT/'tools/w17_window_core_cancel_source_prepare.py'),
  'tools/w17_window_core_cancel_join_prepare.py':m['generator_sha256']})
 files.update(r['prepared_files_sha256'])
 for p,h in files.items():
  if sha(ROOT/p)!=h:raise ValueError('pin mismatch '+p)
 # Commit-bound producer repair, selected provider preparation, original live manifest.
 if (ROOT/PRODUCER).read_bytes()!=cap.git('show','3625a502b889d3a69aada6796cd9ceb8eefb6810:'+PRODUCER):raise ValueError('repaired producer changed')
 for p,h in m['original_source_sha256'].items():
  if hashlib.sha256(cap.git('show',m['pin']+':'+p)).hexdigest()!=h:raise ValueError('original pin '+p)
 if m['accounting']['concrete']!=269 or m['accounting']['envelope']!=278:raise ValueError('allocation')
 return m,r,files

def fatal_site(marker):
 p=ROOT/'rtl/test/w17_window_core_cancel_join_r5/tb.sv';lines=p.read_text().splitlines()
 hits=[n for n,line in enumerate(lines,1) if '$fatal' in line and '"'+marker+'"' in line]
 if len(hits)!=1:raise ValueError('exact fatal source site '+marker)
 return {'basename':'tb.sv','line':hits[0],'top':'tb'}
cap.fatal_site=fatal_site

def prepare(out):
 m,r,files=inputs();jobs=[{'label':'baseline','mutation':None,'cases':[
  {'args':['+CUT='+c['CUT']]+(['+PREFIX='+str(c['PREFIX'])] if 'PREFIX' in c else []),
   'expected':'PASS','marker':'ACTUAL_CORE_CANCEL_PASS cut='+c['CUT'],'seconds':1} for c in m['cases']]}]
 for label,mutation in m['future_mutants'].items():
  jobs.append({'label':label,'mutation':mutation,'cases':[{'args':['+CUT='+mutation['case']],
    'expected':'FAIL','marker':mutation['failure'],'fatal_receipt':fatal_site(mutation['failure']),'seconds':1}]})
 # No full core/die: exact extracted active cone plus original dependency files.
 sources=[p for p in m['original_source_sha256'] if p.endswith(('.sv','.v'))]
 sources+=[m['runtime_cone_path'],PRODUCER]
 sources += [p for p in r['future_compile_inputs']['sources'] if Path(p).name!='tb.sv']
 sources=list(dict.fromkeys(sources))
 if len({Path(p).name for p in sources})!=len(sources):raise ValueError('source basename collision')
 options=['--binary','--timing','--assert','--top-module','tb','-j','2','-Wno-fatal',
  '--unroll-count','1','--unroll-limit','131072','--output-split','20000','--output-split-cfuncs','2000',
  '-CFLAGS','-O0','-MAKEFLAGS','OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0']
 for job in jobs:
  job['compile_command']=[cap.compiler()['wrapper']]+options+['--Mdir','{run}/'+job['label']+'/obj',
    '-I{run}/'+job['label']+'/sources/rtl/hdc/v41']+['{run}/'+job['label']+'/sources/'+p for p in sources]+['{run}/'+job['label']+'/sources/tb.sv']
 plan={'status':'PREPARED_NOT_GO','runner_sha256':sha(TOOL),'model_sha256':sha(MODEL),'source_files_sha256':files,
  'source_inputs':sources,'compiler':cap.compiler(),'caps':cap.CAPS,'jobs':jobs,
  'budget':{'compile_shared_seconds':130,'runtime_shared_seconds':26,'reserve_seconds':24,'whole_seconds':180,
     'aggregate_generated_output_bytes':268435456,'no_retry':True},
  'unmeasured_output_peak':'No complete SU256/QE join has been compiled. cap refusal is preserved FAIL; no fallback/shrink.',
  'physical_causal_visibility':False,'causal_certificates_ever_true':False,'provider_service':False,'fulltoken':False}
 out=Path(out);out.mkdir(parents=True,exist_ok=False);write(out/'plan.json',plan)
 write(out/'parent_GO_template.json',{'status':'PENDING_NOT_AUTHORIZATION','requested_status':STATUS,
  'plan_sha256':sha(out/'plan.json'),'runner_sha256':sha(TOOL),'model_sha256':sha(MODEL),
  'source_digest':cap.digest(files),'jobs_digest':cap.digest(jobs),'caps':cap.CAPS,'budget':plan['budget']})
 return plan

def validate_plan(path):
 p=json.loads(Path(path).read_text());m,r,f=inputs()
 if p['runner_sha256']!=sha(TOOL) or p['model_sha256']!=sha(MODEL) or p['source_files_sha256']!=f:raise ValueError('plan pins')
 if p['caps']!=cap.CAPS or p['compiler']!=cap.compiler():raise ValueError('plan tool/caps')
 if p['budget']!={'compile_shared_seconds':130,'runtime_shared_seconds':26,'reserve_seconds':24,'whole_seconds':180,'aggregate_generated_output_bytes':268435456,'no_retry':True}:raise ValueError('budget')
 # Bind exact prepared commands/cases via independently regenerated pure object.
 import tempfile
 with tempfile.TemporaryDirectory(prefix='window-core-join-plan-verify-') as t:
  regenerated=prepare(Path(t)/'plan')
 if p!=regenerated:raise ValueError('commands/cases/expectations changed')
 return p

def go(args,plan):
 if not re.fullmatch('[0-9a-f]{40}',args.go_commit or ''):raise ValueError('fresh committed GO required')
 g=json.loads(cap.git('show',args.go_commit+':'+args.go_path))
 expected={'status':STATUS,'requested_status':STATUS,'plan_sha256':sha(args.plan),'runner_sha256':sha(TOOL),
  'model_sha256':sha(MODEL),'source_digest':cap.digest(plan['source_files_sha256']),
  'jobs_digest':cap.digest(plan['jobs']),'caps':cap.CAPS,'budget':plan['budget']}
 for k,v in expected.items():
  if g.get(k)!=v:raise ValueError('GO binding '+k)
 if cap.git('status','--porcelain').strip():raise ValueError('clean committed worktree required')
 return g

def worker(args):
 plan=validate_plan(args.plan);go(args,plan);out=Path(args.out)
 receipts=[];status='FAIL_PRESERVED_NO_RETRY';compile_used=runtime_used=0
 try:
  caps=cap.caps_receipt(args.unit);write(out/'caps_before_compile.json',caps)
  cap.BUDGET['generated_output_total_bytes']=plan['budget']['aggregate_generated_output_bytes']
  for job in plan['jobs']:
   home=out/job['label'];src=home/'sources';src.mkdir(parents=True,exist_ok=False)
   for p in plan['source_files_sha256']:
    target=src/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
   shutil.copyfile(ROOT/'rtl/test/w17_window_core_cancel_join_r5/tb.sv',src/'tb.sv')
   if job['mutation']:
    p=src/json.loads(MODEL.read_text())['runtime_cone_path'];s=p.read_text();mut=job['mutation']
    start=s.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #(')
    if s[start:].count(mut['old'])!=1:raise ValueError('mutant not unique in selected body')
    p.write_text(s[:start]+s[start:].replace(mut['old'],mut['new']))
   write(home/'snapshot_sha256.json',{p.relative_to(src).as_posix():sha(p) for p in src.rglob('*') if p.is_file()})
   remaining=130-compile_used
   if remaining<=0:raise ValueError('shared compile budget exhausted')
   cmd=[x.format(run=str(out.resolve())) for x in job['compile_command']]
   step=cap.supervised(cmd,home/'compile.log',remaining,out);compile_used+=step['wall_seconds'];phase=[step];receipts.append(step)
   if step['returncode']!=0:raise ValueError('compile nonzero; preserve first failure')
   binary=home/'obj/Vtb';write(home/'binary_receipt.json',{'sha256':sha(binary),'bytes':binary.stat().st_size})
   for i,case in enumerate(job['cases']):
    seconds=min(case['seconds'],26-runtime_used)
    if seconds<=0:raise ValueError('shared runtime budget exhausted')
    step=cap.supervised([str(binary.resolve())]+case['args'],home/('runtime_'+str(i)+'.log'),seconds,out)
    runtime_used+=step['wall_seconds'];step['cap_events']=cap.read_clean_runtime_events(caps['kernel_cgroup'])
    step['runtime_source_directory']=str(src.resolve());phase.append(step);receipts.append(step)
    cap.verify_runtime(case,step['returncode'],Path(step['log']).read_text(),step['cap_events'],str(src.resolve()))
   cap.close_and_reclaim(out,home,job,phase,sha(args.plan),args.go_commit)
  status='PASS_ACTUAL_CORE_SU_QE_SELECTED_OWNER_CANCEL_SIMULATION_ONLY'
 except BaseException as e:
  write(out/'first_terminal_failure.json',{'error':repr(e),'no_retry':True})
 finally:
  write(out/'record.json',{'verdict':status,'GO_commit':args.go_commit,'plan_sha256':sha(args.plan),'unit':args.unit,
   'steps':receipts,'compile_shared_wall_seconds':compile_used,'runtime_shared_wall_seconds':runtime_used,
   'sampled_output_peak_bytes':cap.OUTPUT_PEAK,'source_pins':plan['source_files_sha256'],
   'local_ACK_not_owner_retirement':True,'projected_deadline_not_causal_PHY':True,
   'causal_certificates_ever_true':False,'physical_provider':False,'fulltoken':False,'adoption':False})
 return 0 if status.startswith('PASS_') else 1

def launch(args):
 plan=validate_plan(args.plan);go(args,plan)
 if not re.fullmatch(r'w17-recovery-core-[A-Za-z0-9_-]+',args.unit or ''):raise ValueError('fresh user-unit name')
 out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
 claim=cap.claim_go(args.go_commit);write(claim/'receipt.json',{'unit':args.unit,'out':str(out.resolve()),'plan_sha256':sha(args.plan)})
 props=['MemoryMax=4294967296','MemorySwapMax=0','CPUAffinity=30 31','LimitFSIZE=268435456','LimitCORE=0','RuntimeMaxSec=180','KillMode=control-group','KillSignal=9','OOMPolicy=stop','Nice=10']
 command=['systemd-run','--user','--wait','--pipe','--unit='+args.unit]+['--property='+p for p in props]+['--working-directory='+str(ROOT),sys.executable,str(TOOL),'--worker','--plan',str(Path(args.plan).resolve()),'--out',str(out.resolve()),'--unit',args.unit,'--go-commit',args.go_commit,'--go-path',args.go_path]
 write(out/'launch.json',{'command':command,'GO_commit':args.go_commit,'plan_sha256':sha(args.plan)})
 with (out/'service.log').open('x') as f:rc=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT).returncode
 state=subprocess.check_output(['systemctl','--user','show',args.unit,'--property=ActiveState','--property=MainPID','--property=Result','--property=ExecMainStatus'],text=True)
 write(out/'service_receipt.json',{'returncode':rc,'terminal':state})
 return rc
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepare',action='store_true');ap.add_argument('--worker',action='store_true');ap.add_argument('--plan');ap.add_argument('--out',required=True);ap.add_argument('--unit');ap.add_argument('--go-commit');ap.add_argument('--go-path');a=ap.parse_args()
 if a.prepare:prepare(a.out)
 else:raise SystemExit(worker(a) if a.worker else launch(a))
