"""Uncapped source-pinned existing-engine elaboration, separate from sole run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[3]
    book=json.loads((Path(__file__).parent/'ports.json').read_text())
    if a.out.exists():raise RuntimeError('retain previous output; new exclusive directory required')
    if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True):
        raise RuntimeError('source worktree must be clean')
    for name in ('RLIMIT_CPU','RLIMIT_AS','RLIMIT_FSIZE'):
        limit=getattr(resource,name)
        resource.setrlimit(limit,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
    pins={path:hashlib.sha256((root/path).read_bytes()).hexdigest() for path in book['source_sha256']}
    if pins!=book['source_sha256']:raise RuntimeError('actual compiled source pin mismatch')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    a.out.mkdir(parents=True)
    command=['verilator','--lint-only','--timing','-Wno-fatal','--top-module',book['top'],'-GENABLE=1','-f','rtl/model/qwen_hbm_integrated_20261003/sources.f']
    receipt=dict(supervisor_pid=os.getpid(),source_HEAD=head,command=command,source_sha256=pins,
                 meminfo=Path('/proc/meminfo').read_text(),
                 free_bytes=os.statvfs(a.out).f_bavail*os.statvfs(a.out).f_frsize,
                 affinity=sorted(os.sched_getaffinity(0)),
                 reserved_peer_DS_constructor_bytes=806000000000,
                 scope='existing-engine full-dimension elaboration only; no runtime or physical qualification')
    (a.out/'launch.json').write_text(json.dumps(receipt,indent=2)+'\n')
    started=time.monotonic()
    with (a.out/'lint.log').open('w') as log:
        child=subprocess.Popen(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
        (a.out/'child.pid').write_text(str(child.pid)+'\n')
        rc=child.wait()
    after={path:hashlib.sha256((root/path).read_bytes()).hexdigest() for path in pins}
    (a.out/'terminal.json').write_text(json.dumps(dict(returncode=rc,elapsed_seconds=time.monotonic()-started,
                 source_unchanged=after==pins,status='PASS_ELABORATION' if rc==0 and after==pins else 'FAIL_ELABORATION',
                 token_qualified=False,physical_qualified=False),indent=2)+'\n')
    raise SystemExit(rc if rc else (0 if after==pins else 1))

if __name__=='__main__':main()
