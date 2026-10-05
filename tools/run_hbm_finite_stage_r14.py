#!/usr/bin/env python3
"""Single reviewed finite RTL invocation. Preparation is the default; no retries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'results/uarch/qwen_hbm_endpoint_r14_20261002'
TOOLROOT = Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050')
IMAGE = 'ot-host22.04@sha256:760104a7f8f31f970fb3c1ff5bf91cfa0cb79ace21ada4454b157421df715555'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sources():
    front = ['rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv', 'rtl/abi3/ot_a3_pkg.sv']
    others = sorted(str(p.relative_to(ROOT)) for p in (ROOT/'rtl/model_ready_hbm_r14').glob('*.sv') if str(p.relative_to(ROOT)) not in front)
    bench = sorted(str(p.relative_to(ROOT)) for p in (ROOT/'rtl/test/model_ready_hbm_r14').glob('*.sv'))
    ram = [f'physical/asap7_memory_macros/{n}/{n}.v' for n in ['ot_sram_1r1w_64x512_m1_r2c2', 'ot_sram_1r1w_128x256_m1_r2c2']]
    return front + others + ['rtl/abi3/ot_a3_issue_record_store.sv'] + ram + bench

def manifest():
    extra = ['rtl/test/model_ready_hbm_r14/qwen_stage_metadata_r14.svh',
             'tools/run_hbm_finite_stage_r14.py', 'tools/qwen_hbm_r14_journal_audit.py',
             'tools/qwen_hbm_r14_metadata.py', 'tools/qwen_hbm_endpoint_preflight_r14.py',
             'tests/test_qwen_hbm_endpoint_r14_preflight.py']
    return {p: digest(ROOT/p) for p in sources()+extra}

def compile_argv(out):
    return [str(TOOLROOT/'bin/verilator'), '--binary', '--timing', '-j', '1', '--threads', '1',
            '--top-module', 'tb_hbm_finite_stage', '--Mdir', str(out/'obj'),
            '-I'+str(ROOT/'rtl/test/model_ready_hbm_r14')] + [str(ROOT/p) for p in sources()]

def save(out, record):
    (out/'receipt.json').write_text(json.dumps(record, indent=2, sort_keys=True)+'\n')

def run_logged(argv, cwd, timeout, log):
    with log.open('wb') as stream:
        return subprocess.run(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                              timeout=timeout, check=False).returncode

def inner(out):
    # Every build/sim process is born inside this cgroup. Verify BEFORE compile.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    cg=Path('/sys/fs/cgroup')
    caps={n:(cg/n).read_text().strip() for n in ['memory.max','memory.swap.max','cpuset.cpus.effective']}
    assert int(caps['memory.max']) == 4*1024**3 and caps['memory.swap.max']=='0', caps
    assert len(os.sched_getaffinity(0))==1, caps
    record={'status':'STARTED', 'caps':caps, 'affinity':sorted(os.sched_getaffinity(0)),
            'compile_argv':compile_argv(out), 'cases':[], 'RTL_qualification':False}
    save(out,record)
    try:
        rc=run_logged(record['compile_argv'],ROOT,120,out/'compile.log')
        record['compile_rc']=rc
        if rc:
            record['status']='COMPILE_FAILED'; return
        binary=out/'obj/Vtb_hbm_finite_stage'; record['binary_SHA256']=digest(binary)
        deadline=time.monotonic()+30
        # One binary, one all-sims deadline, no rebuild/retry/fallback.
        for case, mutant in [(0,0),(1,0),(2,0),(3,0),(4,0),(0,1),(0,2),(0,3),(0,4)]:
            folder=out/f'case{case}_mutant{mutant}';folder.mkdir()
            remaining=deadline-time.monotonic()
            if remaining<=0: raise subprocess.TimeoutExpired('all simulations',30)
            argv=[str(binary),f'+CASE={case}',f'+MUTANT={mutant}','+MAX_CYCLES=500000']
            rc=run_logged(argv,folder,remaining,folder/'run.log')
            # A nonzero mutant run alone is NOT evidence of the intended detection.
            record['cases'].append({'case':case,'mutant':mutant,'rc':rc,'argv':argv,
                                   'expected_nonzero':bool(case==4 or mutant),
                                   'journal_SHA256':digest(folder/'journal.tsv') if (folder/'journal.tsv').exists() else None})
            save(out,record)
        record['status']='TERMINAL_REQUIRES_INDEPENDENT_JOURNAL_AND_FAILURE_REASON_REVIEW'
    except subprocess.TimeoutExpired as exc:
        record['status']='TIMEOUT';record['timeout_command']=str(exc.cmd)
    except Exception as exc:
        record['status']='INFRASTRUCTURE_FAILED';record['error']=repr(exc)
    finally:
        save(out,record)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',action='store_true');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--execute-go',type=Path);p.add_argument('--source-commit');p.add_argument('--cpu',type=int)
    p.add_argument('--inner',action='store_true');a=p.parse_args()
    if a.inner:
        inner(a.output);return
    if a.execute_go is None:
        a.output.mkdir(parents=True,exist_ok=False)
        plan={'status':'PREPARED_NOT_EXECUTED', 'source_manifest':manifest(),
              'compile_argv':compile_argv(a.output), 'image':IMAGE,
              'caps':{'CPU_affinity_count':1,'memory_bytes':4*1024**3,'swap_bytes':0,
                      'compile_seconds':120,'all_sim_seconds':30,'whole_seconds':150,'cycles_per_case':500000},
              'execution_admission':'Requires parent GO after inventory/quarantine blockers close. No current GO inferred.'}
        save(a.output,plan);return
    assert a.source_commit and a.cpu is not None, 'Exact clean source commit and reviewed CPU required'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert head==a.source_commit
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(), 'Clean pin required'
    go=json.loads(a.execute_go.read_text())
    serialized=json.dumps(manifest(),sort_keys=True,separators=(',',':')).encode()
    assert go['allow_execute'] is True and go['source_commit']==head
    assert go['source_manifest_SHA256']==hashlib.sha256(serialized).hexdigest()
    assert go['inventory_and_tag_quarantine_admitted'] is True
    assert go['cpu']==a.cpu and go['image']==IMAGE
    for toolname in ['verilator','verilator_bin']:
        assert go['tool_SHA256'][toolname]==digest(TOOLROOT/'bin'/toolname), 'Reviewed tool hash mismatch'
    # Require an already installed image. No pulling or alternate image.
    subprocess.run(['docker','image','inspect',IMAGE],check=True,stdout=subprocess.DEVNULL)
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'execution_GO.json').write_bytes(a.execute_go.read_bytes())
    name='ot-hbm-r14-'+uuid.uuid4().hex[:12]
    argv=['docker','run','--name',name,'--network','none','--memory','4g','--memory-swap','4g',
          '--cpuset-cpus',str(a.cpu),'--pids-limit','128','--ulimit','core=0',
          '-v',f'{ROOT}:{ROOT}:ro','-v',f'{TOOLROOT}:{TOOLROOT}:ro',
          '-v',f'{a.output}:{a.output}:rw','--entrypoint','python3',IMAGE,
          str(ROOT/'tools/run_hbm_finite_stage_r14.py'),'--inner','--output',str(a.output)]
    outer={'source_commit':head,'argv':argv,'container':name,'status':'STARTED','source_manifest':manifest()}
    try:
        outer['rc']=run_logged(argv,ROOT,150,a.output/'container.log');outer['status']='TERMINAL'
    except subprocess.TimeoutExpired:
        # Only our uniquely named container. Existing fleet work is untouched.
        subprocess.run(['docker','kill',name],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        outer['status']='WHOLE_CGROUP_HARDSTOP'
    finally:
        (a.output/'outer_receipt.json').write_text(json.dumps(outer,indent=2,sort_keys=True)+'\n')

if __name__=='__main__': main()
