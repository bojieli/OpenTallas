"""Sole uncapped b3 source-bound alignment + k16 GRT runner; never retries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def execute(work,source):
    work=Path(work).resolve()
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=source:
        raise ValueError('actual source HEAD mismatch')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('actual source worktree dirty')
    for name in ['verdict.json','start.json']:
        if (work/name).exists():raise ValueError('refuse prior execution receipt')
    man=json.loads((work/'manifest.json').read_text())
    if man['producer_sha256']!=sha(ROOT/'tools/qwen_rom_fulldie_b3.py'):raise ValueError('producer pin mismatch')
    avail=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
    disk=shutil.disk_usage(work).free
    # Reservation derived from retained 13GiB peak + real alignment stage,
    # sequential; scheduling estimates only, no process/cgroup hard caps.
    if avail<64*2**30 or disk<40*2**30:raise ValueError('actual host capacity insufficient for 32GiB reservation plus host headroom')
    start=dict(source_commit=source,source_root=str(ROOT),PID=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21],
      wall_start=time.time(),MemAvailable_bytes=avail,disk_available_bytes=disk,
      reserve_memory_bytes=32*2**30,reserve_disk_bytes=8*2**30,threads=8,
      policy='no imposed memory/swap/CPU-time/wall/FSIZE/AS caps; host headroom reservations',
      manifest_sha256=sha(work/'manifest.json'),inventory_sha256={str(p.relative_to(work)):sha(p) for p in work.rglob('*') if p.is_file()},
      compiler_image=subprocess.check_output(['sudo','-n','docker','image','inspect','openroad/orfs:asap7lock','--format','{{.Id}}'],text=True).strip())
    (work/'start.json').write_text(json.dumps(start,indent=2)+'\n')
    phases=[];verdict='FAIL_INCOMPLETE';failure=None
    try:
        args=json.loads((work/'macro_gate_args.json').read_text())
        for i,x in enumerate(args):
            if x=='--macro-view':args[i+1]=args[i+1].split('=',1)[0]+'='+str(work/'guard_views'/args[i+1].split('=',1)[0])
        gate=[sys.executable,str(ROOT/'tools/run_abi3_physical_aligned_guarded.py'),'--macro-track-gate','--gate-only','--macro-track-gate-record',str(work/'macro_gate.json'),*args]
        with (work/'macro_gate.log').open('w') as log:subprocess.run(gate,stdout=log,stderr=subprocess.STDOUT,check=True)
        for name,directory in [('real_alignment',work/'real_alignment'),('k16_GRT',work)]:
            t=time.time();receipt=dict(phase=name,wall_start=t)
            (work/(name+'-start.json')).write_text(json.dumps(receipt,indent=2)+'\n')
            # Named container ensures ownership verification. No Docker --memory
            # /--cpus, no shell ulimit overrides or elapsed-time deadline.
            cmd=['sudo','-n','docker','run','--rm','--name','qfd_b3_'+name,'-v',str(directory)+':/work','-w','/work',
              'openroad/orfs:asap7lock','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec /usr/bin/time -v openroad -threads 8 -no_init -exit /work/run.tcl']
            logpath=work/(name+'.log')
            with logpath.open('w') as log:
                child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
                (work/(name+'-process.json')).write_text(json.dumps(dict(argv=cmd,PID=child.pid,start_ticks=Path(f'/proc/{child.pid}/stat').read_text().split()[21]),indent=2)+'\n')
                rc=child.wait()
            receipt.update(exit_code=rc,wall_s=time.time()-t,log_sha256=sha(logpath));phases.append(receipt)
            (work/(name+'-end.json')).write_text(json.dumps(receipt,indent=2)+'\n')
            if rc:raise RuntimeError(f'{name} exit {rc}')
        verdict='COMPLETE_K16_GRT_RAW_REQUIRES_OVERFLOW_REVIEW'
    except Exception as exc:failure=str(exc)
    result=dict(verdict=verdict,failure=failure,phases=phases,source_commit=source,wall_s=time.time()-start['wall_start'],
      IR_qualified=False,SSFF_qualified=False,numerical_system_qualified=False,no_retry=True)
    (work/'verdict.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    return int(failure is not None)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True,type=Path);p.add_argument('--source',required=True)
    a=p.parse_args();sys.exit(execute(a.work,a.source))
