"""Unbounded supervisor with capacity-based disk monitoring and raw failure receipts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def main(proposal, admission, go_commit):
    go=json.loads(Path(admission).read_text());root=Path(go['job_root']);start=time.monotonic();reason=None
    if hashlib.sha256(Path(proposal).read_bytes()).hexdigest()!=go['proposal_sha256']:raise ValueError('proposal bytes before child')
    if root.resolve()!=Path(admission).resolve().parent:raise ValueError('owned job root')
    def save(name,value):
        with (root/name).open('x')as f:json.dump(value,f,indent=2);f.write('\n')
    save('service_start.json',dict(pid=os.getpid(),source_commit=go['additive_source_commit'],GO_commit=go_commit,
        cpus=sorted(os.sched_getaffinity(0)),cgroup=Path('/proc/self/cgroup').read_text(),time=time.time(),
        wall_limit=None,FSIZE='unlimited',AS='unlimited',memory_limit=None,swap_limit=None,
        memory_reservation_bytes=go['memory_reservation_bytes'],native_decode=False))
    command=[sys.executable,'-B','-u',str(Path(go['additive_source_root'])/'tools/qwen_kv_campaign_run.py'),
        '--proposal',str(proposal),'--admission',str(admission),'--go-commit',go_commit]
    with (root/'actual_operator.log').open('xb')as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        def stopped(sig,frame):
            nonlocal reason
            reason='TERMINATED_SIGNAL_'+str(sig)
            if child.poll()is None:child.terminate()
        signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
        while child.poll()is None:
            st=os.statvfs(go['output_parent']);free=st.f_bavail*st.f_frsize
            cg=next(line.split('::',1)[1]for line in Path('/proc/self/cgroup').read_text().splitlines()if line.startswith('0::'));p=Path('/sys/fs/cgroup')/cg.lstrip('/')
            counters={}
            for name in ('memory.current','memory.peak','memory.events','memory.max','memory.swap.max'):
                try:counters[name]=(p/name).read_text().strip()
                except OSError:counters[name]='unavailable'
            with(root/'resources.jsonl').open('a')as f:f.write(json.dumps(dict(elapsed_s=time.monotonic()-start,disk_available_bytes=free,counters=counters))+'\n')
            if free<go['disk_reserve_bytes']:
                reason='FLEET_DISK_RESERVE';child.terminate()
            time.sleep(5)
        rc=child.wait()
    raw=Path(go['output'])/'terminal.json';result=json.loads(raw.read_text())if raw.is_file()else None
    status='PASS_RELEASED_CHECKPOINT_KV_OPERATOR_AND_PRIOR_READ_HASHES'if rc==0 and reason is None and result and result['status']=='PASS_RELEASED_CHECKPOINT_KV_OPERATOR_AND_PRIOR_READ_HASHES'else 'FAIL_INCOMPLETE_PRESERVED'
    save('terminal.json',dict(status=status,exit_code=rc,termination_reason=reason,elapsed_s=time.monotonic()-start,
        source_commit=go['additive_source_commit'],GO_commit=go_commit,child_terminal=result,
        child_terminal_sha256=hashlib.sha256(raw.read_bytes()).hexdigest()if raw.is_file()else None,
        actual_log_sha256=hashlib.sha256((root/'actual_operator.log').read_bytes()).hexdigest(),
        native_decode=False,production_lifecycle_qualified=False,actual_RTL=False,physical_credit=False,no_automatic_retry=True))
    return 0 if status.startswith('PASS_')else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--proposal',type=Path,required=True);p.add_argument('--admission',type=Path,required=True);p.add_argument('--go-commit',required=True);a=p.parse_args();sys.exit(main(a.proposal,a.admission,a.go_commit))
