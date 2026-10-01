#!/usr/bin/env python3
"""Local-only source-pinned checkpoint worker with owner-specific memory guards."""
import argparse
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
QUEUE=Path('/tmp/claude-1000/queue')
GIB=1<<30

def utc():return datetime.now(timezone.utc).isoformat()
def available():
    fields={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.split(':')[0] in ('MemAvailable',)}
    return fields['MemAvailable']
def admission_ok(memory_bytes,disk_bytes):return memory_bytes>=112*GIB and disk_bytes>=80*GIB
def runtime_ok(rss_bytes,memory_bytes):return rss_bytes<=12*GIB and memory_bytes>=80*GIB
def process(pid):
    try:
        fields=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()
        return dict(pid=pid,start_ticks=int(fields[19]),ppid=int(fields[1]),rss_bytes=int(fields[21])*os.sysconf('SC_PAGE_SIZE'),cwd=str(Path(f'/proc/{pid}/cwd').resolve()),state=fields[0])
    except (OSError,IndexError,ValueError):return None
def group_rss(pgid):
    total=0
    for directory in Path('/proc').iterdir():
        if directory.name.isdigit():
            try:
                if os.getpgid(int(directory.name))==pgid:
                    item=process(int(directory.name))
                    if item:total+=item['rss_bytes']
            except ProcessLookupError:pass
    return total
def write(path,value):
    temporary=path.with_suffix(path.suffix+'.new');temporary.write_text(json.dumps(value,indent=2)+'\n');os.replace(temporary,path)
def supervise(args):
    QUEUE.mkdir(parents=True,exist_ok=True)
    with (QUEUE/'QwenHBM.complete.local.lock').open('a') as reservation:
        try:fcntl.flock(reservation,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('existing live Qwen complete reservation; no duplicate')
        if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise RuntimeError('pinned worktree must be clean')
        free=available();disk=os.statvfs('/home/ubuntu');disk_free=disk.f_bavail*disk.f_frsize
        if not admission_ok(free,disk_free):raise RuntimeError('launch requires MemAvailable112GiB and disk80GiB')
        cpu_affinity=sorted(os.sched_getaffinity(0))[-4:]
        os.sched_setaffinity(0,cpu_affinity)
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        source_paths=['tools/qwen_hbm_complete_program.py','tools/qwen_hbm_complete_executor.py','tools/qwen_hbm_complete_reference.py','tools/qwen_hbm_complete_checkpoint.py','tools/qwen_hbm_complete_launch.py','tools/qwen3_deployment_quality.py','compiler/models/qwen3-8b/config.json','compiler/models/qwen3-8b/checkpoint_source.json']
        admission=dict(timestamp=utc(),host='local',source_commit=revision,cwd=str(ROOT),MemAvailable_bytes=free,disk_available_bytes=disk_free,load=os.getloadavg(),cpu_count=os.cpu_count(),cpu_budget=4,RSS_limit_bytes=12*GIB,MemAvailable_runtime_floor_bytes=80*GIB,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths},existing_manifest=str(QUEUE/'W12b.manifest'),AGI_dispatch=False,PVE_dispatch=False,checkpoint_readonly=True,images_written=False)
        admission.update(cpu_affinity=cpu_affinity,runtime_guard_sample_seconds=2)
        write(args.out/'admission.json',admission)
        gate=args.out/'execution_gate.json'
        command=[sys.executable,str(ROOT/'tools/qwen_hbm_complete_checkpoint.py'),'--snapshot',str(args.snapshot),'--out',str(args.out/'execution'),'--token',str(args.token),'--steps',str(args.steps),'--layers',str(args.layers),'--admission-gate',str(gate)]
        env=os.environ.copy()
        for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):env[key]='4'
        env['HF_HUB_OFFLINE']='1';env['TRANSFORMERS_OFFLINE']='1';env['PYTHONUNBUFFERED']='1'
        with (args.out/'run.log').open('xb') as log:
            child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            identity=process(child.pid)
            if identity is None:raise RuntimeError('child lost before identity admission')
            job=dict(**identity,source_commit=revision,command=command,supervisor=process(os.getpid()),timestamp=utc(),status='LIVE',out=str(args.out),CPU_budget=4,RSS_budget_bytes=12*GIB)
            write(args.out/'identity.json',job);write(QUEUE/'QwenHBM.complete.local.json',job)
            with (QUEUE/'W12b.manifest').open('a') as manifest:
                manifest.write('\nlocal | '+utc()+' | QwenHBM complete checkpoint software PID'+str(child.pid)+'/start'+str(identity['start_ticks'])+' supervisor'+str(os.getpid())+' source'+revision+' clean '+str(ROOT)+' nice10 OMP/BLAS4 RSS12GiB | '+str(args.out)+' | launch MemAvailable>=112GiB; runtime global>=80GiB; ownRSS<=12GiB; noimages/noAGI/noPVE; actualRTLfalse\n')
            write(gate,identity)
            peak=0;breach=None
            while child.poll() is None:
                rss=group_rss(child.pid);peak=max(peak,rss);free=available()
                if not runtime_ok(rss,free):
                    breach=dict(timestamp=utc(),own_group_RSS_bytes=rss,MemAvailable_bytes=free)
                    write(args.out/'guard_failure.json',breach)
                    os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(timeout=10)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                    break
                time.sleep(2)
            terminal=dict(timestamp=utc(),actual_returncode=child.wait(),pid=child.pid,start_ticks=identity['start_ticks'],peak_owned_RSS_bytes=peak,guard_breach=breach,source_commit=revision,actual_RTL_executed=False)
            write(args.out/'execution_rc.json',terminal)
            job.update(status='TERMINAL',execution=terminal);write(QUEUE/'QwenHBM.complete.local.json',job)
            with (QUEUE/'W12b.manifest').open('a') as manifest:manifest.write('# '+utc()+' QwenHBM complete software terminal PID'+str(child.pid)+' actualRC'+str(terminal['actual_returncode'])+' receipt '+str(args.out/'execution_rc.json')+'\n')
            return terminal['actual_returncode']

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--token',type=int,default=9707);parser.add_argument('--steps',type=int,default=2);parser.add_argument('--layers',type=int,default=36)
    parser.add_argument('--supervise',action='store_true');args=parser.parse_args()
    if args.supervise:
        try:sys.exit(supervise(args))
        except BaseException as error:
            if isinstance(error,SystemExit):raise
            write(args.out/'supervisor_failure.json',dict(timestamp=utc(),error_type=type(error).__name__,error=str(error)))
            raise
    args.out.mkdir(parents=True,exist_ok=False)
    command=[sys.executable,str(Path(__file__).resolve()),'--supervise','--snapshot',str(args.snapshot),'--out',str(args.out),'--token',str(args.token),'--steps',str(args.steps),'--layers',str(args.layers)]
    with (args.out/'supervisor.log').open('xb') as log:
        supervisor=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:os.nice(10))
    write(args.out/'supervisor_identity.json',dict(identity=process(supervisor.pid),command=command))
    print(json.dumps(dict(supervisor_pid=supervisor.pid,out=str(args.out))))
