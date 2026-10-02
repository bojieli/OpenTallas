#!/usr/bin/env python3
"""Future explicit retained-binary execution; admission estimates are not limits.
No memory/swap/time/file/AS/CPU-time ceilings, no retry, no implicit build/run.
Historical capped I66 receipts and binaries remain unchanged.
"""
import argparse,hashlib,json,os,resource,shutil,subprocess,time
from pathlib import Path

def measured_headroom(out):
    mem={x.split(':')[0]:x.split(':')[1].strip() for x in Path('/proc/meminfo').read_text().splitlines()}
    parent=out.parent
    while not parent.exists():parent=parent.parent
    return dict(MemAvailable=mem['MemAvailable'],SwapFree=mem['SwapFree'],loadavg=Path('/proc/loadavg').read_text().strip(),disk_free_bytes=shutil.disk_usage(parent).free,caller_affinity=sorted(os.sched_getaffinity(0)),inherited_rlimits={name:list(resource.getrlimit(getattr(resource,name))) for name in ['RLIMIT_AS','RLIMIT_CPU','RLIMIT_FSIZE']})

def plan(a):
    digest=hashlib.sha256(a.binary.read_bytes()).hexdigest()
    if digest!=a.binary_sha256:raise ValueError('binary identity mismatch')
    if not a.images.is_dir():raise ValueError('images missing')
    cmd=[str(a.binary),str(a.images),str(a.out/'actual.jsonl')]
    if a.cpus:
        cpus=[int(x) for x in a.cpus.split(',')]
        if not set(cpus)<=set(os.sched_getaffinity(0)):raise ValueError('CPU allocation outside current affinity')
        cmd=['taskset','-c',a.cpus,*cmd]
    return dict(command=cmd,binary_sha256=digest,headroom=measured_headroom(a.out),limits_imposed=[],CPU_affinity_role='explicit resource allocation only; no CPU-time ceiling',admission='owner compares measured headroom/reservations/build inventory; no copied pilot hard thresholds',historical_profile=dict(host_link_seconds=9.417,runtime_seconds=5.412,aggregate_peak_bytes=616964096,scope='prior exact I66 native consumer cone only; estimate is not a process limit'),execution_requested=a.execute)

def main(a):
    rec=plan(a)
    if not a.execute:print(json.dumps(rec,indent=2,sort_keys=True));return 0
    if not a.build_receipt:raise ValueError('future binary needs reviewed build receipt; historical capped binary cannot be relaunched')
    built=json.loads(a.build_receipt.read_text())
    if built['binary_sha256']!=rec['binary_sha256'] or built['imposed_process_limits']!=[] or built['host_preallocation_rejection_removed'] is not True:
        raise ValueError('build receipt does not bind uncapped successor')
    rec['build_receipt_sha256']=hashlib.sha256(a.build_receipt.read_bytes()).hexdigest()
    a.out.mkdir(parents=True,exist_ok=False)
    receipt=a.out/'launch_receipt.json'
    def save():receipt.write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
    save();started=time.monotonic()
    with (a.out/'runtime.log').open('w') as f:
        proc=subprocess.Popen(rec['command'],stdout=f,stderr=subprocess.STDOUT)
        rec['PID']=proc.pid;save()
        while proc.poll() is None:
            # Reporting only: free space/headroom never become copied stop limits.
            rec['latest_headroom']=measured_headroom(a.out);save()
            time.sleep(1)
    rec.update(returncode=proc.returncode,elapsed_seconds=time.monotonic()-started,retries=0);save()
    return proc.returncode

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--binary-sha256',required=True);p.add_argument('--images',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--cpus');p.add_argument('--build-receipt',type=Path);p.add_argument('--execute',action='store_true')
    raise SystemExit(main(p.parse_args()))
