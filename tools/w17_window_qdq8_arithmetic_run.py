#!/usr/bin/env python3
"""Prepare/probe a pinned, single-GO QDQ8 run; no fallback or retry."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'results/uarch/w17_window_qdq8_arithmetic_preparation_20261002'
PREPARED=Path('/tmp/window-qdq8-arithmetic-prepared-20261002-r4')
SOURCE='4e38326d6f361bc85e660f48c59c355e2bb95274'
REVIEWED='c7bfb32c2b44f3887247350a0b51d2e3392aa6d3'
CPUS=[30,31]
CAPS=dict(memory_max='4294967296',swap_max='0',affinity=CPUS,file_limit=[268435456,268435456],
          runtime_usec='3min',kill_mode='control-group',kill_signal='9')
BUDGET=dict(whole_service_seconds=180,compile_seconds=150,case_seconds=5,
            cases=3,total_case_seconds=15,supervision_reserve_seconds=15)
ENV_BLOCK=('VERILATOR_ROOT','VERILATOR_BIN','VERILATOR_GDB','VERILATOR_VALGRIND',
           'VERILATOR_TEST_FLAGS','VERILATOR_RUNNING','MAKEFLAGS','MFLAGS','CXX','CC',
           'CXXFLAGS','CPPFLAGS','LDFLAGS','LD_PRELOAD','LD_LIBRARY_PATH','PERL5OPT','PERL5LIB')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def objsha(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,o):Path(p).write_text(json.dumps(o,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


def compiler_receipt(command):
    wrapper=Path(command[0]);binary=wrapper.with_name('verilator_bin')
    assert wrapper.is_file() and binary.is_file()
    assert not any(os.environ.get(k) for k in ENV_BLOCK),'Compiler environment override; no fallback'
    version=subprocess.check_output([str(wrapper),'--version'],text=True,timeout=5).strip()
    assert version=='Verilator 5.050 2026-07-01 rev v5.050'
    return dict(version=version,wrapper=str(wrapper),wrapper_sha256=sha(wrapper),
                binary=str(binary),binary_sha256=sha(binary),options=command[1:],command_sha256=objsha(command),
                environment_overrides_absent=list(ENV_BLOCK))


def provenance():
    model=json.loads((EVIDENCE/'model.json').read_bytes())
    manifest=json.loads((EVIDENCE/'preparation_sha256.json').read_bytes())
    assert model['source_commit']==SOURCE
    diffs=[]
    for path,h in model['source_sha256'].items():
        old=git('show',SOURCE+':'+path)
        assert hashlib.sha256(old).hexdigest()==h and sha(ROOT/path)==h
        diffs.append(dict(path=path,source_sha256=h,current_sha256=sha(ROOT/path),byteidentical=True))
    for path,h in model['fixture_sha256'].items():assert sha(ROOT/path)==h
    for path,h in manifest.items():
        assert sha(EVIDENCE/path)==h and sha(PREPARED/path)==h
    expected_files=set(manifest)|{'preparation_sha256.json'}
    actual_files={str(p.relative_to(PREPARED)) for p in PREPARED.rglob('*') if p.is_file()}
    assert actual_files==expected_files,'Prepared tree added/removed files or prior build; no retry'
    assert sha(EVIDENCE/'preparation_sha256.json')==sha(PREPARED/'preparation_sha256.json')
    assert sha(ROOT/'tools/w17_window_qdq8_arithmetic_model.py')==model['generator_sha256']
    assert model['parameters']==dict(AW=30,NW=21,BL=16,IL=8,NBMAX=192,CHUNK8=1,QLB=272,MP=1,
        mode=1,fp4=0,nb=16,xbase=54720,obase=55232,SEPARATE_ROWS=1,KVT_SH=13,POS_W=21)
    assert [c['case'] for c in model['preparation']['runtime_commands']]==['fp32_rounding','bf16_input','nonfinite_flags']
    assert not(PREPARED/'obj').exists()
    return model,manifest,diffs


def prepare(out):
    model,manifest,diffs=provenance();command=model['preparation']['compile_command']
    compiler=compiler_receipt(command)
    plan=dict(schema='opentallas.window.qdq8_single_run_plan.v1',reviewed_commit=REVIEWED,
       runner_sha256=sha(Path(__file__)),source_commit=SOURCE,source_diffs=diffs,
       model_sha256=sha(EVIDENCE/'model.json'),manifest_sha256=sha(EVIDENCE/'preparation_sha256.json'),
       prepared_file_sha256=manifest,compiler=compiler,compile_command=command,
       runtime_commands=model['preparation']['runtime_commands'],caps=CAPS,budget=BUDGET,
       go_contract=dict(status='PARENT_QDQ8_ARITHMETIC_SINGLE_RUN_GO',required_fields=[
          'status','plan_sha256','runner_sha256','model_sha256','manifest_sha256','compile_command_sha256','caps','budget']),
       scope='Arithmetic to original blocks/guard only, no HBM physical drain, full token or recovery. No geometry/helper/options/expected-file changes, retries, fallback or fit.',
       state='PREPARED_NOT_COMPILED_NOT_RUN_FRESH_PARENT_GO_REQUIRED')
    out.mkdir(parents=True,exist_ok=False);write(out/'plan.json',plan)
    write(out/'source_diff_receipt.json',dict(verdict='PASS_BYTEIDENTICAL_ORIGINAL_SOURCE',diffs=diffs,
        fixture_sha256=model['fixture_sha256'],snapshot_sha256=model['preparation']['snapshot_sha256']))
    write(out/'compiler_receipt.json',compiler)
    return plan


def validate_plan(path):
    plan=json.loads(path.read_bytes());model,manifest,diffs=provenance()
    assert plan['runner_sha256']==sha(Path(__file__))
    assert plan['model_sha256']==sha(EVIDENCE/'model.json') and plan['manifest_sha256']==sha(EVIDENCE/'preparation_sha256.json')
    assert plan['prepared_file_sha256']==manifest and plan['source_diffs']==diffs
    assert plan['compile_command']==model['preparation']['compile_command']
    assert plan['runtime_commands']==model['preparation']['runtime_commands']
    assert plan['compiler']==compiler_receipt(plan['compile_command'])
    assert plan['caps']==CAPS and plan['budget']==BUDGET
    return plan,model


def validate_go(go,plan,path):
    assert go['status']=='PARENT_QDQ8_ARITHMETIC_SINGLE_RUN_GO'
    for key in ('runner_sha256','model_sha256','manifest_sha256','caps','budget'):assert go[key]==plan[key],key
    assert go['plan_sha256']==sha(path)
    assert go['compile_command_sha256']==objsha(plan['compile_command'])


def cap_values(unit):
    cg=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
    props=subprocess.check_output(['systemctl','--user','show',unit,'--property=RuntimeMaxUSec',
        '--property=KillMode','--property=KillSignal','--property=MemoryMax','--property=MemorySwapMax',
        '--property=CPUAffinity','--property=LimitFSIZE'],text=True)
    d=dict(line.split('=',1) for line in props.splitlines())
    values=dict(memory_max=(cg/'memory.max').read_text().strip(),swap_max=(cg/'memory.swap.max').read_text().strip(),
      affinity=sorted(os.sched_getaffinity(0)),file_limit=list(resource.getrlimit(resource.RLIMIT_FSIZE)),
      runtime_usec=d['RuntimeMaxUSec'],kill_mode=d['KillMode'],kill_signal=d['KillSignal'])
    return values,cg,props


def validate_caps(values):
    assert values==CAPS,'FAIL_CAPS_NO_COMPILE_NO_FALLBACK'


def compare(log,which,model):
    cal=model['edge_calendar'];healthy=which!=2
    checks={}
    def check(name,pattern,expected,radix=None):
        got=[]
        for match in re.finditer(pattern,log):
            got.append([int(x,16 if radix and i in radix else 10) for i,x in enumerate(match.groups())])
        checks[name]=dict(exact=got==expected,actual_count=len(got),expected_count=len(expected))
        if got!=expected:checks[name].update(actual=got,expected=expected)
    name=['fp32_rounding','bf16_input','nonfinite_flags'][which]
    gold=json.loads((EVIDENCE/name/'oracle.json').read_bytes())
    pack=lambda a,w:sum(n<<(i*w) for i,n in enumerate(a))
    check('reads',r'XR_SAMPLE cycle=(\d+) block=(\d+) address=(\d+)',[[c,b,54720+32*b] for b,c in enumerate(cal['read_sample'])])
    check('VM',r'VM_SAMPLE cycle=(\d+) block=(\d+) address=(\d+) data=([0-9a-fA-F]+)',
      [[c,b,55232+32*b,pack(gold[b]['bf16_widened'],32)] for b,c in enumerate(cal['capture_sample'])] if healthy else [],{3}) if healthy else None
    if not healthy:
        # Invalid data is intentionally not arithmetic-qualified; require exact valid-write pulse calendar/address.
        check('invalid_VM_edges',r'VM_SAMPLE cycle=(\d+) block=(\d+) address=(\d+) data=[0-9a-fA-F]+',[[c,b,55232+32*b] for b,c in enumerate(cal['capture_sample'])])
    check('capture',r'CAPTURE cycle=(\d+) block=(\d+) address=(\d+) codes=([0-9a-fA-F]+) scale=([0-9a-fA-F]+)',
      [[c,b,55232+32*b,pack(gold[b]['codes'],8),gold[b]['scale']] for b,c in enumerate(cal['capture_sample'])] if healthy else [],{3,4})
    check('blocks',r'BLOCK_ACCEPT cycle=(\d+) block=(\d+) first=(\d+) user=(\d+) codes=([0-9a-fA-F]+) scale=([0-9a-fA-F]+)',
      [[c,b,57359+512*b,37,pack(gold[b]['codes'],8),gold[b]['scale']] for b,c in enumerate(cal['block_accept'])] if healthy else [],{4,5})
    check('terminal',r'QDQ8_ARITHMETIC_PASS case=(\d+) cycle=(\d+) reads=(\d+) VMblocks=(\d+) captures=(\d+) blocks=(\d+) faults=(\d+)',
      [[which,cal['healthy_terminal_sample'] if healthy else cal['invalid_terminal_sample'],16,16,16 if healthy else 0,16 if healthy else 0,0 if healthy else 16]])
    return dict(verdict='PASS' if all(x['exact'] for x in checks.values()) else 'FAIL_NO_FIT',checks=checks)


def execute(command,cwd,log,timeout):
    before=time.monotonic()
    with log.open('x') as f:
        try:code=subprocess.run(command,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:code='TIME_BUDGET_EXCEEDED'
    return dict(status=code,command=command,cwd=str(cwd),timeout_seconds=timeout,
                wall_seconds=time.monotonic()-before,log_sha256=sha(log))


def worker(a):
    out=Path(a.out);start=time.monotonic();record=dict(mode='CAP_PROBE_ONLY' if a.probe else 'SINGLE_PARENT_GO_RUN',results=[])
    try:
        plan,model=validate_plan(Path(a.plan))
        if not a.probe:
            assert not git('status','--porcelain'),'Clean worktree required before compile'
            assert re.fullmatch('[0-9a-f]{40}',a.go_commit)
            assert a.go_path.startswith('results/rtl/')
            go_raw=git('show',a.go_commit+':'+a.go_path);go=json.loads(go_raw)
            validate_go(go,plan,Path(a.plan));(out/'parent_go.json').write_bytes(go_raw)
            record['go_commit']=a.go_commit
        values,cg,props=cap_values(a.unit)
        caps=dict(actual=values,properties=props,cgroup=str(cg),compiler_verified_before_compile=plan['compiler'])
        try:validate_caps(values);caps['verdict']='PASS_VERIFIED_BEFORE_COMPILE'
        except AssertionError:caps['verdict']='FAIL_CAPS_NO_COMPILE_NO_FALLBACK';raise
        finally:write(out/'caps_before_compile.json',caps)
        record.update(plan_sha256=sha(a.plan),runner_sha256=sha(Path(__file__)),source_head=git('rev-parse','HEAD').decode().strip())
        if a.probe:
            record['verdict']='PASS_CAP_PROBE_NO_COMPILE_NO_RUNTIME'
        else:
            record['compile']=execute(plan['compile_command'],ROOT,out/'compile.log',BUDGET['compile_seconds'])
            if record['compile']['status']!=0:raise RuntimeError('Compile failed/capped; no runtime/fallback/retry')
            for which,c in enumerate(plan['runtime_commands']):
                assert time.monotonic()-start+BUDGET['case_seconds']<BUDGET['whole_service_seconds']
                item=dict(case=c['case'],runtime=execute(c['command'],Path(c['cwd']),out/(c['case']+'_runtime.log'),BUDGET['case_seconds']))
                record['results'].append(item)
                item['comparison']=compare((out/(c['case']+'_runtime.log')).read_text(),which,model)
                write(out/'in_progress.json',record)
                if item['runtime']['status']!=0 or item['comparison']['verdict']!='PASS':raise RuntimeError('Runtime/model mismatch; no retry/adjustment')
            record['verdict']='PASS_BOUNDED_QDQ8_ARITHMETIC_TO_BLOCKS_GUARD'
        record['memory_peak_bytes']=int((cg/'memory.peak').read_text());record['memory_events']=(cg/'memory.events').read_text()
    except Exception as e:
        record.update(verdict='FAIL_PRESERVED_NO_COMPILE_FALLBACK_OR_RETRY',error_type=type(e).__name__,error=str(e))
    record['worker_wall_seconds']=time.monotonic()-start
    write(out/'record.json',record)
    return 0 if record['verdict'].startswith('PASS') else 1


def launch(a):
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    try:
        plan,model=validate_plan(Path(a.plan))
        if not a.probe:
            assert a.go_commit and a.go_path,'Fresh explicit parent GO required'
            assert re.fullmatch('[0-9a-f]{40}',a.go_commit) and a.go_path.startswith('results/rtl/')
            validate_go(json.loads(git('show',a.go_commit+':'+a.go_path)),plan,Path(a.plan))
            assert not git('status','--porcelain')
        assert subprocess.check_output(['systemctl','--user','show',a.unit,'--property=LoadState'],text=True).strip()=='LoadState=not-found','Unit reuse forbidden'
        write(out/'preflight_receipt.json',dict(verdict='PASS_LAUNCH_PREFLIGHT_NO_COMPILE_YET',plan_sha256=sha(a.plan),probe=a.probe))
    except Exception as e:
        write(out/'preflight_receipt.json',dict(verdict='FAIL_LAUNCH_PREFLIGHT_NO_SERVICE_NO_COMPILE_NO_FALLBACK',error_type=type(e).__name__,error=str(e)))
        return 2
    command=['systemd-run','--user','--unit='+a.unit,'--wait','--pipe','--property=MemoryMax=4294967296',
      '--property=MemorySwapMax=0','--property=CPUAffinity=30 31','--property=RuntimeMaxSec=180',
      '--property=KillMode=control-group','--property=KillSignal=SIGKILL','--property=OOMPolicy=kill',
      '--property=LimitFSIZE=268435456','--property=LimitCORE=0','--property=Nice=10',
      '--working-directory='+str(ROOT),sys.executable,str(Path(__file__).resolve()),'--worker',
      '--plan',str(Path(a.plan).resolve()),'--out',str(out.resolve()),'--unit',a.unit]
    if a.probe:command+=['--probe']
    else:command+=['--go-commit',a.go_commit,'--go-path',a.go_path]
    write(out/'launch.json',dict(command=command,plan_sha256=sha(a.plan),no_fallback=True,no_retry=True))
    with (out/'service.log').open('x') as f:status=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT).returncode
    state=subprocess.check_output(['systemctl','--user','show',a.unit,'--property=ActiveState','--property=MainPID','--property=Result','--property=ExecMainStatus'],text=True)
    write(out/'service_receipt.json',dict(returncode=status,terminal=state,record_exists=(out/'record.json').exists(),
        caps_receipt_exists=(out/'caps_before_compile.json').exists(),mode='PROBE' if a.probe else 'RUN'))
    return status


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepare',action='store_true');ap.add_argument('--probe',action='store_true')
    ap.add_argument('--worker',action='store_true');ap.add_argument('--plan');ap.add_argument('--out',required=True)
    ap.add_argument('--unit');ap.add_argument('--go-commit');ap.add_argument('--go-path');a=ap.parse_args()
    if a.prepare:prepare(Path(a.out));return 0
    assert a.plan and a.unit
    return worker(a) if a.worker else launch(a)

if __name__=='__main__':raise SystemExit(main())
