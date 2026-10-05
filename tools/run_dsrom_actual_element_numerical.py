#!/usr/bin/env python3
"""Numerical parent-authorized, single-attempt actual-element gate under one hard cgroup."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import signal
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
PREPARED_SOURCE_COMMIT='864b4042cca1b9ee7e2286c01e80e97f135875f7'
GO_PATH='results/rtl/dsrom_actual_element_numerical_prepare_20261002/parent_GO.json'
MODEL_PATH='results/rtl/dsrom_actual_element_numerical_prepare_20261002/model.json'
RUNNER_PATH='tools/run_dsrom_actual_element_numerical.py'
PLAN_PATH='results/rtl/dsrom_actual_element_numerical_runner_prepare_20261002/runner_plan.json'
SOURCEPLAN_PATH='results/rtl/dsrom_actual_element_numerical_prepare_20261002/sourceplan.json'
VERILATOR='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'

def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def write(path,record):
    with path.open('x') as f: json.dump(record,f,indent=2,sort_keys=True); f.write('\n')
def prepare_module():
    spec=importlib.util.spec_from_file_location('prepare_numerical',ROOT/'tools/prepare_dsrom_actual_element_numerical.py')
    prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep);return prep

def package_sha(pins):
    # Canonical complete44-file manifest; does not rely on filesystem iteration order.
    return sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())

def reviewed_plan():
    plan=json.loads((ROOT/PLAN_PATH).read_text())
    if plan['prepared_source_commit']!=PREPARED_SOURCE_COMMIT:raise ValueError('numerical prepared source commit changed')
    for path,pin in plan['artifact_pins'].items():
        if sha((ROOT/path).read_bytes())!=pin:raise ValueError('runner preparation pin mismatch: '+path)
    return plan

def tool_preflight(plan):
    expected=plan['verilator']
    path=Path(VERILATOR)
    if str(path.resolve())!=expected['resolved_path'] or not os.access(path,os.X_OK):raise ValueError('Verilator path mismatch')
    for name,pin in expected['installation_files_sha256'].items():
        if sha(Path(name).read_bytes())!=pin:raise ValueError('Verilator installation pin mismatch: '+name)
    for name in ('VERILATOR_ROOT','VERILATOR_BIN'):
        if os.environ.get(name)!=expected['environment'].get(name):raise ValueError('Verilator environment changed: '+name)
    version=subprocess.run([VERILATOR,'--version'],capture_output=True,text=True,timeout=10,check=True)
    if version.stdout.strip()!=expected['version']:raise ValueError('Verilator version mismatch')
    help_result=subprocess.run([VERILATOR,'--help'],capture_output=True,text=True,timeout=10,check=True)
    help_text=help_result.stdout+help_result.stderr
    for token in expected['help_option_tokens']:
        if token not in help_text:raise ValueError('Verilator option unavailable: '+token)
    sourceplan=json.loads((ROOT/SOURCEPLAN_PATH).read_text())
    for case,argv in sourceplan['compile_plan_proposed_only'].items():
        if argv!=plan['compile_plan_proposed_only'][case]:raise ValueError('compile options changed: '+case)
        if argv[0]!=VERILATOR:raise ValueError('compile path mismatch')
    return dict(path=VERILATOR,resolved_path=str(path.resolve()),version=version.stdout.strip(),installation_files_sha256=expected['installation_files_sha256'],help_sha256=sha(help_text.encode()),options_verified=expected['help_option_tokens'],compiled=False)

def verify(go_commit):
    # A separate GO binds all reviewed sources, package, runner, plan, and full commit.
    raw=git('show',go_commit+':'+GO_PATH);go=json.loads(raw)
    model=prepare_module().verify();plan=reviewed_plan()
    if go.get('GO')!='BOUNDED_NUMERICAL_ACTUAL_ELEMENT_VERIFICATION_ONLY' or go.get('bench_revision')!='numerical':raise ValueError('explicit new numerical parent GO required')
    required=dict(prepared_model_sha256=sha((ROOT/MODEL_PATH).read_bytes()),bench_sha256=model['new_artifact_pins'][model['bench_path']],generated_package_sha256=package_sha(model['generated_files_sha256']),runner_sha256=sha((ROOT/RUNNER_PATH).read_bytes()),runner_plan_sha256=sha((ROOT/PLAN_PATH).read_bytes()),sourceplan_sha256=sha((ROOT/SOURCEPLAN_PATH).read_bytes()))
    for key,pin in required.items():
        if go.get(key)!=pin:raise ValueError('GO pin mismatch: '+key)
    prepared=go.get('prepared_commit')
    if not isinstance(prepared,str) or not re.fullmatch(r'[0-9a-f]{40}',prepared):raise ValueError('full numerical prepared commit required')
    for path in [MODEL_PATH,*model['new_artifact_pins'],RUNNER_PATH,PLAN_PATH,*plan['artifact_pins']]:
        if (ROOT/path).read_bytes()!=git('show',prepared+':'+path):raise ValueError('reviewed numerical file changed: '+path)
    package=prepare_module().package()
    if {name:sha(text.encode()) for name,text in package.items()}!=model['generated_files_sha256']:raise ValueError('reviewed package mismatch')
    if go.get('limits')!=plan['caps']:raise ValueError('GO cap policy mismatch')
    return model,raw

def numerical_completion(text,case,plan):
    """Exact ordered phase counters; tags/causality are enforced inside pinned bench."""
    target=plan['expected_completion'][case]
    events=[list(map(int,m)) for m in re.findall(r'^ORACLE phase=(\d+) positions=(\d+) active_segments=(\d+) nseg=(\d+) cumulative_public_rows=(\d+) value_assertions=(\d+)$',text,re.M)]
    passes=[list(map(int,m)) for m in re.findall(r'^PASS independent-numerical BF=(\d+) rows=(\d+) value_assertions=(\d+) config_assertions=(\d+)$',text,re.M)]
    expected=[[int(case=='bfcolumn'),target['public_rows'],target['value_assertions'],target['config_assertions']]]
    return dict(valid=events==plan['expected_phase_events'][case] and passes==expected,events=events,pass_counters=passes,expected_events=plan['expected_phase_events'][case],expected_counters=expected)

def failure_kinds(text,entry):
    kinds=[]
    if entry['explicit_DIFF']:kinds.append('DIFFERENTIAL')
    if re.search(r'NUMERICAL value',text):kinds.append('NUMERICAL_VALUE')
    if re.search(r'NUMERICAL (metadata|duplicate|missing|output|exact|extended)',text):kinds.append('NUMERICAL_CONTRACT_OR_FIXTURE')
    if not kinds:kinds.append('FIXTURE_OR_IMPLEMENTATION_OR_COMPLETION')
    return kinds

def capped_run(a):
    whole_start=time.monotonic()
    model,raw=verify(a.go_commit)
    cg=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
    def metrics():
        return {n:(cg/n).read_text().strip() if (cg/n).exists() else None for n in ('memory.max','memory.swap.max','memory.peak','memory.events','cpu.max','cgroup.procs')}
    caps=metrics()
    if caps['memory.max']!='4294967296' or caps['memory.swap.max']!='0':raise RuntimeError('aggregate memory caps not applied; refuse execution')
    if not (cg/'cgroup.kill').exists() or not os.access(cg/'cgroup.kill',os.W_OK):raise RuntimeError('whole cgroup kill unavailable; refuse execution')
    cpus=sorted(os.sched_getaffinity(0))
    if len(cpus)!=2:raise RuntimeError('two CPU affinity cap not applied; refuse execution')
    a.output.mkdir(parents=True,exist_ok=False)
    plan=reviewed_plan()
    def whole_kill(*ignored):
        try:
            write(a.output/'whole_cgroup_hard_timeout.json',dict(status='HARD_CGROUP_KILL',limit_seconds=660,elapsed_seconds=time.monotonic()-whole_start,metrics=metrics()))
        finally:
            (cg/'cgroup.kill').write_text('1')
    # RuntimeMaxSec660 remains the enclosing service limit. Termination at that
    # deadline immediately kills the cgroup; no additional graceful-stop interval.
    signal.signal(signal.SIGTERM,whole_kill)
    whole_watchdog=threading.Timer(max(0,660-(time.monotonic()-whole_start)),whole_kill)
    whole_watchdog.daemon=True;whole_watchdog.start()
    record=dict(status='RUNNING',runner_commit=git('rev-parse','HEAD').decode().strip(),runner_sha256=sha(Path(__file__).read_bytes()),prepared_commit=json.loads(raw)['prepared_commit'],parent_GO_commit=a.go_commit,parent_GO_sha256=sha(raw),parent_GO=json.loads(raw),model_sha256=sha((ROOT/MODEL_PATH).read_bytes()),verified_source_pins=len(model['source_pins']),verified_artifact_pins=len(model['new_artifact_pins']),cpu_affinity=cpus,initial_caps=caps,versions={t:subprocess.check_output([t,'--version'],text=True).splitlines()[0] for t in (VERILATOR,'g++','make','systemd-run')},runs=[],used_seconds=dict(build=0.0,simulate=0.0),limits_seconds=dict(build=600,simulate=60),timing_claim=False,arithmetic_claim=False,adoption=False,live_source_selection=False,limitations=model['claims'],whole_limit_seconds=660)
    budget=dict(build=600.0,simulate=60.0)
    compile_failed=False
    def run(case,phase,argv,variant='positive'):
        remaining=budget[phase]-record['used_seconds'][phase]
        if remaining<=0:raise RuntimeError('aggregate '+phase+' budget exhausted')
        start=time.monotonic();log=a.output/(variant+'_'+case+'_'+phase+'.log')
        def kill_all():
            # Emit durable timeout evidence before killing ourselves and all compiler children.
            try:
                write(a.output/(variant+'_'+case+'_'+phase+'_hard_timeout.json'),dict(status='HARD_CGROUP_KILL',phase=phase,remaining_seconds_at_start=remaining,elapsed_seconds=time.monotonic()-start,metrics=metrics(),argv=argv))
            finally:
                (cg/'cgroup.kill').write_text('1')
        watchdog=threading.Timer(remaining,kill_all);watchdog.daemon=True;watchdog.start()
        try:
            with log.open('x') as f:result=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
        finally: watchdog.cancel()
        elapsed=time.monotonic()-start
        if elapsed>=remaining:kill_all()
        record['used_seconds'][phase]+=elapsed
        text=log.read_text(errors='replace')
        entry=dict(case=case,phase=phase,variant=variant,argv=argv,elapsed_seconds=elapsed,remaining_seconds_at_start=remaining,returncode=result.returncode,log=log.name,log_sha256=sha(log.read_bytes()),metrics=metrics(),pass_marker=None,explicit_DIFF=bool(re.search(r'\bDIFF\b',text)))
        if phase=='simulate':
            match=re.search(r'PASS actual-element BF=(\d+) cycles=(\d+) partials=(\d+) issues=(\d+) gated=(\d+) opened=(\d+) loads=(\d+)',text)
            if match and int(match[1])==int(case=='bfcolumn') and len(re.findall(r'^PASS actual-element ',text,re.M))==1:
                entry['pass_marker']=match[0];entry['coverage']=dict(zip(('BF','cycles','partials','issues','gated','opened','loads'),map(int,match.groups())))
                # Three comparisons per completed tick, plus reset/initial task comparisons.
                entry['comparison_samples_minimum']=3*entry['coverage']['cycles']
            entry['numerical_completion']=numerical_completion(text,case,plan)
            entry['failure_kinds']=failure_kinds(text,entry) if result.returncode or not entry['numerical_completion']['valid'] or not entry['pass_marker'] or entry['explicit_DIFF'] else []
        record['runs'].append(entry);write(a.output/(variant+'_'+case+'_'+phase+'_receipt.json'),entry)
        return entry
    try:
        record['tool_preflight']=tool_preflight(plan)
        write(a.output/'tool_preflight.json',record['tool_preflight'])
        receipt=prepare_module().prepare(a.work)
        if receipt['files_sha256']!=model['generated_files_sha256']:raise RuntimeError('generated package differs from reviewed package')
        record['generated']=receipt
        os.chdir(a.work)
        for case in ('q','bfcolumn'):
            argv=[str(a.work/'dsrom_actual_element_numerical_rom.cpp') if x=='/ABS/FRESH/dsrom_actual_element_numerical_rom.cpp' else x for x in plan['compile_plan_proposed_only'][case]]
            entry=run(case,'build',argv)
            if entry['returncode']:
                compile_failed=True;record['failure']='Compilation failure; stop without retry or geometry change';break
            entry=run(case,'simulate',plan['simulate_plan_proposed_only'][case])
            if entry['returncode'] or not entry['pass_marker'] or not entry['numerical_completion']['valid'] or entry['explicit_DIFF']:
                record.setdefault('failures',[]).append(dict(case=case,kinds=entry['failure_kinds'],diagnosis='See exact assertion/compiler log; no PASS qualification'))
        positives_pass=not compile_failed and len(record['runs'])==4 and all(e['returncode']==0 for e in record['runs']) and all(e['pass_marker'] and e['numerical_completion']['valid'] and not e['explicit_DIFF'] for e in record['runs'] if e['phase']=='simulate')
        # Optional mutant is deliberately omitted if positives fail. No repair/retry.
        record['optional_mutant']='NOT_RUN: conservative omission; positives must pass first' if not positives_pass else 'NOT_RUN: optional omitted to preserve positive package unchanged'
        record['classification']='Bounded finite synthetic actual-element numerical oracle plus reference/candidate differential; parent reduction software mapping only; no full arithmetic domain, field, fulltoken or physical qualification'
        record['status']='PASS_BOUNDED_NUMERICAL_AND_DIFFERENTIAL' if positives_pass else 'FAIL_UNQUALIFIED'
    except Exception as e:
        record['status']='FAIL_RUNNER';record['failure']=repr(e)
    finally:
        try:
            record['build_artifacts_sha256']={str(p.relative_to(a.work)):sha(p.read_bytes()) for case in ('q','bfcolumn') for p in sorted((a.work/('obj_'+case)).rglob('*')) if p.is_file()}
            record['final_caps']=metrics();write(a.output/'record.json',record)
        finally:whole_watchdog.cancel()
    return 0 if record['status']=='PASS_BOUNDED_NUMERICAL_AND_DIFFERENTIAL' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capped-child',action='store_true');p.add_argument('--go-commit',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.work=a.work.resolve()
    if a.output.exists() or a.work.exists():p.error('fresh work/output paths required')
    if a.capped_child:sys.exit(capped_run(a))
    verify(a.go_commit)
    if git('status','--porcelain').strip():raise RuntimeError('clean pinned worktree required')
    tool_preflight(reviewed_plan()) # Read-only version/path/options check before launch.
    unit='dsrom-actual-element-numerical-bounded-'+str(os.getpid())
    argv=['systemd-run','--user','--wait','--pipe','--unit='+unit,'-p','MemoryMax=4294967296','-p','MemorySwapMax=0','-p','CPUQuota=200%','-p','CPUAffinity=0 1','-p','TasksMax=64','-p','OOMPolicy=kill','-p','RuntimeMaxSec=660s','-p','TimeoutStopSec=1s','-p','KillMode=control-group',sys.executable,str(Path(__file__).resolve()),'--capped-child','--go-commit',a.go_commit,'--output',str(a.output),'--work',str(a.work)]
    # Launcher log lives outside child output so cap/setup failures survive too.
    with Path(str(a.output)+'_launcher.log').open('x') as f:rc=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT).returncode
    props=subprocess.run(['systemctl','--user','show',unit,'-p','Result','-p','ExecMainCode','-p','ExecMainStatus','-p','MemoryPeak','-p','CPUQuotaPerSecUSec','-p','MemoryMax','-p','MemorySwapMax','-p','ControlGroup'],capture_output=True,text=True)
    write(Path(str(a.output)+'_launcher.json'),dict(argv=argv,returncode=rc,unit=unit,systemctl_properties=props.stdout,properties_stderr=props.stderr,properties_returncode=props.returncode))
    sys.exit(rc)
