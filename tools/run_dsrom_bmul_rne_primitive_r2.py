#!/usr/bin/env python3
"""Default read-only preflight; fresh parent GO required for one capped primitive attempt."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import threading
import time
ROOT=Path(__file__).resolve().parents[1]
BASE='results/rtl/dsrom_bmul_rne_primitive_runner_prepare_r2_20261002'
MODEL_PATH='results/rtl/dsrom_bmul_rne_primitive_prepare_20261002/model.json'
SOURCEPLAN_PATH=BASE+'/sourceplan.json'
PLAN_PATH=BASE+'/runner_plan.json'
RUNNER_PATH='tools/run_dsrom_bmul_rne_primitive_r2.py'
GO_PATH=BASE+'/parent_GO.json'
GO_LITERAL='BOUNDED_BF_RNE_PRIMITIVE_VERIFICATION_ONLY'
PREPARED_SOURCE_COMMIT='dc8c535b61fc8f5bccd5eb271d8fe2e2124f7e4d'
VERILATOR='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def write(path,record):
    data=(json.dumps(record,indent=2,sort_keys=True)+'\n').encode()
    if len(data)>4*1024*1024:raise RuntimeError('receipt exceeds4MiB bound')
    with path.open('xb') as f:f.write(data)
def prepare_module():
    s=importlib.util.spec_from_file_location('primitive_preparer',ROOT/'tools/prepare_dsrom_bmul_rne_primitive.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def package_sha(pins):return sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())
def reviewed_plan():
    p=json.loads((ROOT/PLAN_PATH).read_text())
    if p['prepared_source_commit']!=PREPARED_SOURCE_COMMIT:raise ValueError('prepared source commit changed')
    for path,pin in p['artifact_pins'].items():
        if sha((ROOT/path).read_bytes())!=pin:raise ValueError('runner pin changed '+path)
    return p
def tool_preflight(plan):
    e=plan['verilator'];path=Path(VERILATOR)
    if str(path.resolve())!=e['resolved_path'] or not os.access(path,os.X_OK):raise ValueError('Verilator path mismatch')
    for name,pin in e['installation_files_sha256'].items():
        if sha(Path(name).read_bytes())!=pin:raise ValueError('Verilator installation changed '+name)
    for name in ('VERILATOR_ROOT','VERILATOR_BIN'):
        if os.environ.get(name)!=e['environment'].get(name):raise ValueError('Verilator environment changed '+name)
    v=subprocess.run([VERILATOR,'--version'],capture_output=True,text=True,timeout=10,check=True)
    if v.stdout.strip()!=e['version']:raise ValueError('Verilator version mismatch')
    h=subprocess.run([VERILATOR,'--help'],capture_output=True,text=True,timeout=10,check=True);help_text=h.stdout+h.stderr
    for token in e['help_option_tokens']:
        if token not in help_text:raise ValueError('Verilator option unavailable '+token)
    if sha(help_text.encode())!=e['help_sha256']:raise ValueError('Verilator help changed')
    s=json.loads((ROOT/SOURCEPLAN_PATH).read_text())
    for key in ('compile_plan_proposed_only','simulate_plan_proposed_only'):
        if s[key]!=plan[key]:raise ValueError('reviewed options changed '+key)
    return dict(compiled=False,path=VERILATOR,version=v.stdout.strip(),help_sha256=sha(help_text.encode()),installation_files_sha256=e['installation_files_sha256'])
def preflight(go_commit=None):
    m=prepare_module().verify();p=reviewed_plan()
    if package_sha(m['generated_files_sha256'])!=p['generated_package_sha256']:raise ValueError('package pin mismatch')
    if go_commit:
        raw=git('show',go_commit+':'+GO_PATH);go=json.loads(raw)
        if go.get('GO')!=GO_LITERAL:raise ValueError('fresh explicit primitive parent GO required')
        required=dict(prepared_model_sha256=sha((ROOT/MODEL_PATH).read_bytes()),bench_sha256=m['new_artifact_pins'][m['bench']],generated_package_sha256=p['generated_package_sha256'],runner_sha256=sha((ROOT/RUNNER_PATH).read_bytes()),runner_plan_sha256=sha((ROOT/PLAN_PATH).read_bytes()),sourceplan_sha256=sha((ROOT/SOURCEPLAN_PATH).read_bytes()),semantic_contract_sha256=sha((ROOT/(BASE+'/expected_contract.json')).read_bytes()))
        for name,pin in required.items():
            if go.get(name)!=pin:raise ValueError('GO pin mismatch '+name)
        if go.get('caps')!=p['caps'] or go.get('expected_completion')!=p['expected_completion']:raise ValueError('GO caps or coverage changed')
        commit=go.get('prepared_commit')
        if not isinstance(commit,str) or not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('full40hex reviewed prepared commit required')
        for path in {MODEL_PATH,SOURCEPLAN_PATH,PLAN_PATH,RUNNER_PATH,*m['new_artifact_pins'],*p['artifact_pins']}:
            if (ROOT/path).read_bytes()!=git('show',commit+':'+path):raise ValueError('reviewed commit file changed '+path)
        return m,p,raw
    return m,p,None

def completion(text,mode,plan,returncode):
    target=plan['expected_completion']
    found=re.findall(r'^PASS primitive RNE mode=(\d+) product_assertions=(\d+) encoder_assertions=(\d+) baseline_witnesses=(\d+)$',text,re.M)
    counts=[list(map(int,x)) for x in found]
    expected=[[mode,target['product_assertions'],target['encoder_assertions'],target['baseline_negative_witnesses']]]
    pattern=r'DIFF primitive mutant=(\d+) (product|encoder)_vector=(\d+) expected=([0-9a-fA-F]+) actual=([^\n]+)'
    diff_lines=re.findall('^'+pattern+'$',text,re.M)
    all_diff=bool(re.search(r'\bDIFF\b',text))
    proper_diff=len(diff_lines)==1 and int(diff_lines[0][0])==mode
    if proper_diff:
        _,kind,index,expected_hex,actual=diff_lines[0]
        index=int(index)
        m=prepare_module()
        vectors=m.inputs() if kind=='product' else m.encoder_inputs()
        bound=target['product_vectors'] if kind=='product' else target['encoder_vectors']
        proper_diff=0<=index<bound and len(vectors)==bound
        if proper_diff:
            if kind=='product':
                bits,flag=m.expected(*vectors[index]);oracle_bits=(flag<<32)|bits
                format_ok=bool(re.fullmatch(r'[0-9a-fA-F]{9}',expected_hex) and re.fullmatch(r'[0-9a-fA-F]{8}/[01]',actual))
                actual_bits=(int(actual[-1])<<32)|int(actual[:8],16) if format_ok else None
            else:
                sign,be,sig=vectors[index]
                oracle_bits=m.O.round32((-1 if sign else 1)*sig*m.O.pow2(be-150))
                format_ok=bool(re.fullmatch(r'[0-9a-fA-F]{8}',expected_hex) and re.fullmatch(r'[0-9a-fA-F]{8}',actual))
                actual_bits=int(actual,16) if format_ok else None
            proper_diff=format_ok and int(expected_hex,16)==oracle_bits and actual_bits!=oracle_bits
    malformed_diff=any('DIFF' in line and not re.fullmatch(pattern,line) for line in text.splitlines())
    proper_diff=proper_diff and not malformed_diff
    pass_pattern=r'PASS primitive RNE mode=\d+ product_assertions=\d+ encoder_assertions=\d+ baseline_witnesses=\d+'
    malformed_pass=any('PASS' in line and not re.fullmatch(pass_pattern,line) for line in text.splitlines())
    fatal=bool(re.search(r'%Fatal|%Error|Assertion failed|Aborting|\b(?:Segmentation fault|core dumped)\b',text))
    return dict(valid=returncode==0 and not fatal and not malformed_pass and not malformed_diff and counts==expected and (not all_diff if mode==0 else proper_diff),pass_counts=counts,expected_counts=expected,explicit_mutant_DIFF=proper_diff if mode else False,DIFF_lines=diff_lines,fatal_or_crash=fatal)
def cap_receipt(cg,cpus):
    result={n:(cg/n).read_text().strip() if (cg/n).exists() else None for n in ('memory.max','memory.swap.max','memory.swap.current','memory.current','memory.peak','memory.events','cpu.max','cgroup.procs')}
    result['cpu_affinity']=sorted(cpus)
    if result['memory.max']!='536870912' or result['memory.swap.max']!='0' or result['cpu_affinity']!=[0]:raise RuntimeError('exact512MiB/swap0/CPU0 caps not applied')
    if not (cg/'cgroup.kill').exists() or not os.access(cg/'cgroup.kill',os.W_OK):raise RuntimeError('whole cgroup kill unavailable')
    return result

def bounded_output(proc,log,limit,kill):
    """Never store more thanlimit bytes; receipt precedes cgroup kill on overflow."""
    written=0
    with log.open('xb') as f:
        while True:
            block=proc.stdout.read(4096)
            if not block:break
            remaining=limit-written
            f.write(block[:remaining]);written+=min(len(block),remaining)
            if len(block)>remaining:
                f.flush();kill('LOG_BYTES',dict(limit_bytes=limit,stored_bytes=written,discarded_chunk_bytes=len(block)-remaining));raise RuntimeError('unreachable after cgroup kill')
    return proc.wait()
def inventory(work,limit_files=4096,limit_bytes=536870912):
    files=[p for p in work.rglob('*') if p.is_file()];total=sum(p.stat().st_size for p in files)
    if len(files)>limit_files or total>limit_bytes:raise RuntimeError('work artifact bound exceeded')
    return dict(files=len(files),bytes=total,sha256={str(p.relative_to(work)):sha(p.read_bytes()) for p in sorted(files)})

def capped_run(a):
    start=time.monotonic();m,p,raw=preflight(a.go_commit)
    cg=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
    initial=cap_receipt(cg,os.sched_getaffinity(0));a.output.mkdir(parents=True,exist_ok=False)
    # Inherited hard8MiB perregularfile limit, covering compiler objects/logs/corefiles.
    resource.setrlimit(resource.RLIMIT_FSIZE,(8388608,8388608));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    record=dict(status='RUNNING',prepared_commit=json.loads(raw)['prepared_commit'],GO_commit=a.go_commit,GO_sha256=sha(raw),GO=json.loads(raw),runner_commit=git('rev-parse','HEAD').decode().strip(),initial_caps=initial,runs=[],used_seconds=dict(build=0.0,simulate=0.0),caps=p['caps'],versions={t:subprocess.check_output([t,'--version'],text=True).splitlines()[0] for t in (VERILATOR,'g++','make','systemd-run')},claims={'full_element':False,'physical':False,'fulltoken':False,'adoption':False})
    def kill(kind,detail):
        try:write(a.output/('hard_kill_'+kind+'.json'),dict(kind=kind,detail=detail,elapsed_seconds=time.monotonic()-start,caps=cap_receipt(cg,os.sched_getaffinity(0))))
        finally:(cg/'cgroup.kill').write_text('1')
    signal.signal(signal.SIGTERM,lambda *args:kill('WHOLE_OR_TERMINATION',{'whole_limit_seconds':70}))
    whole=threading.Timer(max(0,70-(time.monotonic()-start)),lambda:kill('WHOLE',{'limit_seconds':70}));whole.daemon=True;whole.start()
    stop_monitor=threading.Event()
    def monitor_work():
        # Aggregate disk cap is sampled; perfile8MiB cap is inherited hardRLIMIT.
        while not stop_monitor.wait(.1):
            try:
                files=[f for f in a.work.rglob('*') if f.is_file()];size=sum(f.stat().st_size for f in files if f.exists())
                if len(files)>4096 or size>536870912:kill('WORK_BYTES',dict(observed_files=len(files),observed_bytes=size,poll_interval_seconds=.1))
                outputs=[f for f in a.output.iterdir() if f.is_file()];obytes=sum(f.stat().st_size for f in outputs)
                if len(outputs)>64 or obytes>33554432:kill('OUTPUT_BYTES',dict(observed_files=len(outputs),observed_bytes=obytes,poll_interval_seconds=.1))
            except FileNotFoundError:pass # Compiler mayunlink temporaryobject duringinventory.
    monitor=threading.Thread(target=monitor_work,daemon=True);monitor.start()
    def run(case,phase,argv,mode=None):
        remaining=(60 if phase=='build' else 10)-record['used_seconds'][phase]
        if remaining<=0:kill('BUDGET',dict(phase=phase,remaining_seconds=remaining))
        begun=time.monotonic();log=a.output/(case+'_'+phase+'.log')
        timer=threading.Timer(remaining,lambda:kill('PHASE',dict(case=case,phase=phase,remaining_seconds=remaining)));timer.daemon=True;timer.start()
        try:
            proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            rc=bounded_output(proc,log,8388608 if phase=='build' else 262144,kill)
        finally:timer.cancel()
        elapsed=time.monotonic()-begun
        if elapsed>=remaining:kill('PHASE',dict(case=case,phase=phase,remaining_seconds=remaining,elapsed_seconds=elapsed))
        record['used_seconds'][phase]+=elapsed
        result=dict(case=case,phase=phase,argv=argv,mode=mode,returncode=rc,elapsed_seconds=elapsed,remaining_seconds_at_start=remaining,log_sha256=sha(log.read_bytes()),caps=cap_receipt(cg,os.sched_getaffinity(0)))
        if phase=='simulate':result['completion']=completion(log.read_text(errors='replace'),mode,p,rc)
        record['runs'].append(result);write(a.output/(case+'_'+phase+'_receipt.json'),result)
        return result
    try:
        record['tool_preflight']=tool_preflight(p);write(a.output/'tool_preflight.json',record['tool_preflight'])
        write(a.output/'initial_cap_receipt.json',initial)
        receipt=prepare_module().prepare(a.work)
        if receipt['files_sha256']!=m['generated_files_sha256']:raise ValueError('fresh package changed')
        record['generated']=receipt;os.chdir(a.work)
        built=run('shared','build',p['compile_plan_proposed_only']['shared'])
        if built['returncode']:record['failure']='BUILD_FAILED_STOP_NO_RETRY';record['status']='FAIL_UNQUALIFIED'
        else:
            record['status']='PASS_BOUNDED_PRIMITIVE_ONLY'
            for mode,name in enumerate(['positive',*p['expected_completion']['mutant_modes']]):
                e=run(name,'simulate',p['simulate_plan_proposed_only'][name],mode)
                if not e['completion']['valid']:
                    record['status']='FAIL_UNQUALIFIED';record['failure']=dict(first_mode=mode,case=name,reason='Nonzero/crash, bad/missing PASS counts, unexpected DIFF or missing explicit mutant DIFF');break
    except Exception as e:record['status']='FAIL_RUNNER';record['failure']=repr(e)
    finally:
        try:
            record['final_caps']=cap_receipt(cg,os.sched_getaffinity(0))
            try:record['artifacts']=inventory(a.work)
            except Exception as error:record['status']='FAIL_RUNNER';record['artifact_inventory_failure']=repr(error)
            write(a.output/'record.json',record)
        finally:stop_monitor.set();whole.cancel()
    return 0 if record['status']=='PASS_BOUNDED_PRIMITIVE_ONLY' else 1

def service_argv(a,unit):
    return ['systemd-run','--user','--wait','--pipe','--unit='+unit,'-p','MemoryMax=536870912','-p','MemorySwapMax=0','-p','CPUQuota=100%','-p','CPUAffinity=0','-p','TasksMax=32','-p','OOMPolicy=kill','-p','RuntimeMaxSec=70s','-p','TimeoutStopSec=1s','-p','KillMode=control-group',sys.executable,str(Path(__file__).resolve()),'--capped-child','--execute','--go-commit',a.go_commit,'--output',str(a.output),'--work',str(a.work)]
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');parser.add_argument('--capped-child',action='store_true');parser.add_argument('--go-commit');parser.add_argument('--output',type=Path);parser.add_argument('--work',type=Path);a=parser.parse_args()
    if not a.execute:
        m,p,_=preflight();print(json.dumps(dict(status='PREFLIGHT_ONLY_NO_HDL_EXECUTION',model_sha256=sha((ROOT/MODEL_PATH).read_bytes()),generated_package_sha256=p['generated_package_sha256'],tool_preflight=tool_preflight(p)),indent=2));sys.exit(0)
    if not a.go_commit or not a.output or not a.work:parser.error('execute requiresfreshGO/output/work')
    a.output=a.output.resolve();a.work=a.work.resolve()
    if a.output.exists() or a.work.exists():parser.error('freshwork/outputrequired')
    if a.capped_child:sys.exit(capped_run(a))
    preflight(a.go_commit)
    if git('status','--porcelain').strip():raise RuntimeError('clean pinned worktree required')
    tool_preflight(reviewed_plan());unit='dsrom-bmul-rne-primitive-'+str(os.getpid());argv=service_argv(a,unit)
    resource.setrlimit(resource.RLIMIT_FSIZE,(8388608,8388608));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    with Path(str(a.output)+'_launcher.log').open('x') as f:rc=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT).returncode
    props=subprocess.run(['systemctl','--user','show',unit,'-p','Result','-p','ExecMainCode','-p','ExecMainStatus','-p','ControlGroup','-p','MemoryMax','-p','MemorySwapMax','-p','CPUQuotaPerSecUSec','-p','RuntimeMaxUSec'],capture_output=True,text=True)
    write(Path(str(a.output)+'_launcher.json'),dict(unit=unit,argv=argv,returncode=rc,properties=props.stdout,properties_returncode=props.returncode,properties_stderr=props.stderr));sys.exit(rc)
