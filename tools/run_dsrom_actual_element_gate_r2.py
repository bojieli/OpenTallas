#!/usr/bin/env python3
"""R2 parent-authorized, single-attempt actual-element gate under one hard cgroup."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
PRESERVED='338141d39a2e847bee2cc42ecfc84303790f891a'
GO_PATH='results/rtl/dsrom_actual_element_prepare_r2_20261001/parent_GO.json'
MODEL_PATH='results/rtl/dsrom_actual_element_prepare_r2_20261001/model.json'
VERILATOR='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'

def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def write(path,record):
    with path.open('x') as f: json.dump(record,f,indent=2,sort_keys=True); f.write('\n')
def prepare_module():
    spec=importlib.util.spec_from_file_location('prepare_r2',ROOT/'tools/prepare_dsrom_actual_element_gate_r2.py')
    prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep);return prep

def verify(go_commit):
    # A new r2 GO binds the reviewed model, bench, and prepared commit. Old GO is rejected.
    raw=git('show',go_commit+':'+GO_PATH);go=json.loads(raw)
    model=prepare_module().verify_pins()
    if go.get('GO')!='BOUNDED_EXISTING_SOURCE_DIFFERENTIAL_VERIFICATION_ONLY' or go.get('bench_revision')!='r2':raise ValueError('explicit new r2 parent GO required')
    if go.get('prepared_model_sha256')!=sha((ROOT/MODEL_PATH).read_bytes()):raise ValueError('GO model pin mismatch')
    if go.get('bench_sha256')!=model['new_artifact_pins'][model['bench_path']]:raise ValueError('GO r2 bench pin mismatch')
    prepared=go.get('prepared_commit')
    if not isinstance(prepared,str) or not re.fullmatch(r'[0-9a-f]{40}',prepared):raise ValueError('full r2 prepared commit required')
    for path in [MODEL_PATH,*model['new_artifact_pins']]:
        if (ROOT/path).read_bytes()!=git('show',prepared+':'+path):raise ValueError('reviewed r2 file changed: '+path)
    return model,raw

def capped_run(a):
    model,raw=verify(a.go_commit)
    cg=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
    def metrics():
        return {n:(cg/n).read_text().strip() if (cg/n).exists() else None for n in ('memory.max','memory.swap.max','memory.peak','memory.events','cpu.max','cgroup.procs')}
    caps=metrics()
    if caps['memory.max']!='4294967296' or caps['memory.swap.max']!='0':raise RuntimeError('aggregate memory caps not applied; refuse execution')
    if not (cg/'cgroup.kill').exists() or not os.access(cg/'cgroup.kill',os.W_OK):raise RuntimeError('whole cgroup kill unavailable; refuse execution')
    cpus=sorted(os.sched_getaffinity(0))
    if len(cpus)>2 or not cpus:raise RuntimeError('two CPU affinity cap not applied; refuse execution')
    a.output.mkdir(parents=True,exist_ok=False)
    record=dict(status='RUNNING',runner_commit=git('rev-parse','HEAD').decode().strip(),runner_sha256=sha(Path(__file__).read_bytes()),prepared_commit=json.loads(raw)['prepared_commit'],parent_GO_commit=a.go_commit,parent_GO_sha256=sha(raw),parent_GO=json.loads(raw),model_sha256=sha((ROOT/MODEL_PATH).read_bytes()),verified_source_pins=len(model['source_pins']),verified_artifact_pins=len(model['new_artifact_pins']),cpu_affinity=cpus,initial_caps=caps,versions={t:subprocess.check_output([t,'--version'],text=True).splitlines()[0] for t in (VERILATOR,'g++','make','systemd-run')},runs=[],used_seconds=dict(build=0.0,simulate=0.0),limits_seconds=dict(build=600,simulate=60),timing_claim=False,arithmetic_claim=False,adoption=False,live_source_selection=False,limitations=model['coverage_limitations'])
    prep=prepare_module()
    receipt=prep.prepare(a.work)
    expected=model['generated_files_sha256']
    if receipt['files_sha256']!=expected:raise RuntimeError('generated package differs from reviewed package')
    record['generated']=receipt
    os.chdir(a.work)
    budget=dict(build=600.0,simulate=60.0)
    compile_failed=False
    def run(case,phase,argv,variant='positive'):
        remaining=budget[phase]-record['used_seconds'][phase]
        if remaining<=0:raise RuntimeError('aggregate '+phase+' budget exhausted')
        start=time.monotonic();log=a.output/(variant+'_'+case+'_'+phase+'.log')
        def kill_all():
            # Emit durable timeout evidence before killing ourselves and all compiler children.
            write(a.output/(variant+'_'+case+'_'+phase+'_hard_timeout.json'),dict(status='HARD_CGROUP_KILL',phase=phase,remaining_seconds_at_start=remaining,elapsed_seconds=time.monotonic()-start,metrics=metrics(),argv=argv))
            (cg/'cgroup.kill').write_text('1')
        watchdog=threading.Timer(remaining,kill_all);watchdog.daemon=True;watchdog.start()
        try:
            with log.open('x') as f:result=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
        finally: watchdog.cancel()
        elapsed=time.monotonic()-start;record['used_seconds'][phase]+=elapsed
        text=log.read_text(errors='replace')
        entry=dict(case=case,phase=phase,variant=variant,argv=argv,elapsed_seconds=elapsed,remaining_seconds_at_start=remaining,returncode=result.returncode,log=log.name,log_sha256=sha(log.read_bytes()),metrics=metrics(),pass_marker=None,explicit_DIFF=bool(re.search(r'\bDIFF\b',text)))
        if phase=='simulate':
            match=re.search(r'PASS actual-element BF=(\d+) cycles=(\d+) partials=(\d+) issues=(\d+) gated=(\d+) opened=(\d+) loads=(\d+)',text)
            if match:
                entry['pass_marker']=match[0];entry['coverage']=dict(zip(('BF','cycles','partials','issues','gated','opened','loads'),map(int,match.groups())))
                # Three comparisons per completed tick, plus reset/initial task comparisons.
                entry['comparison_samples_minimum']=3*entry['coverage']['cycles']
        record['runs'].append(entry);write(a.output/(variant+'_'+case+'_'+phase+'_receipt.json'),entry)
        return entry
    try:
        for case in ('q','bfcolumn'):
            argv=[str(a.work/'dsrom_actual_element_rom.cpp') if x=='/ABS/FRESH/dsrom_actual_element_rom.cpp' else x for x in model['compile_plan_proposed_only'][case]]
            entry=run(case,'build',argv)
            if entry['returncode']:
                compile_failed=True;record['failure']='Compilation failure; stop without retry or geometry change';break
            entry=run(case,'simulate',model['simulate_plan_proposed_only'][case])
            if entry['returncode'] or not entry['pass_marker']:
                record.setdefault('failures',[]).append(dict(case=case,kind='DIFFERENTIAL' if entry['explicit_DIFF'] else 'FIXTURE_OR_IMPLEMENTATION',diagnosis='See exact assertion/compiler log; no PASS qualification'))
        positives_pass=not compile_failed and len(record['runs'])==4 and all(e['returncode']==0 for e in record['runs']) and all(e['pass_marker'] for e in record['runs'] if e['phase']=='simulate')
        # Optional mutant is deliberately omitted if positives fail. No repair/retry.
        record['optional_mutant']='NOT_RUN: conservative omission; positives must pass first' if not positives_pass else 'NOT_RUN: optional omitted to preserve positive package unchanged'
        record['status']='PASS_BOUNDED_DIFFERENTIAL' if positives_pass else 'FAIL_UNQUALIFIED'
    except Exception as e:
        record['status']='FAIL_RUNNER';record['failure']=repr(e)
    finally:
        record['final_caps']=metrics();write(a.output/'record.json',record)
    return 0 if record['status']=='PASS_BOUNDED_DIFFERENTIAL' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capped-child',action='store_true');p.add_argument('--go-commit',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.work=a.work.resolve()
    if a.output.exists() or a.work.exists():p.error('fresh work/output paths required')
    if a.capped_child:sys.exit(capped_run(a))
    verify(a.go_commit)
    if git('status','--porcelain').strip():raise RuntimeError('clean pinned worktree required')
    unit='dsrom-actual-element-r2-bounded-'+str(os.getpid())
    argv=['systemd-run','--user','--wait','--pipe','--unit='+unit,'-p','MemoryMax=4294967296','-p','MemorySwapMax=0','-p','CPUQuota=200%','-p','CPUAffinity=0 1','-p','TasksMax=64','-p','OOMPolicy=kill','-p','RuntimeMaxSec=660s','-p','TimeoutStopSec=1s','-p','KillMode=control-group',sys.executable,str(Path(__file__).resolve()),'--capped-child','--go-commit',a.go_commit,'--output',str(a.output),'--work',str(a.work)]
    # Launcher log lives outside child output so cap/setup failures survive too.
    with Path(str(a.output)+'_launcher.log').open('x') as f:rc=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT).returncode
    props=subprocess.run(['systemctl','--user','show',unit,'-p','Result','-p','ExecMainCode','-p','ExecMainStatus','-p','MemoryPeak','-p','CPUQuotaPerSecUSec','-p','MemoryMax','-p','MemorySwapMax','-p','ControlGroup'],capture_output=True,text=True)
    write(Path(str(a.output)+'_launcher.json'),dict(argv=argv,returncode=rc,unit=unit,systemctl_properties=props.stdout,properties_stderr=props.stderr,properties_returncode=props.returncode))
    sys.exit(rc)
