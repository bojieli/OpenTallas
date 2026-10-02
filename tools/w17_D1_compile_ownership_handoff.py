#!/usr/bin/env python3
"""Plan-only native compiler ownership checks and a small GNU make race repro.
No engine compiler, frontend, simulator or production process is launched/stopped.
"""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time


def targets(classes):
    groups={}
    for key in ('VM_CLASSES_FAST','VM_SUPPORT_FAST','VM_CLASSES_SLOW','VM_SUPPORT_SLOW'):
        match=re.search(r'^'+key+r' \+= \\\n((?:  .*\n)*)',classes,re.M)
        if match is None:raise ValueError('Missing make list: '+key)
        groups[key]=[x.strip().rstrip('\\').strip()+'.o' for x in match.group(1).splitlines() if x.strip().rstrip('\\').strip()]
    ordered=sum(groups.values(),[])
    if len(ordered)!=len(set(ordered)):raise ValueError('Duplicate archive target')
    return ordered


def exclusive(local_targets,remote_targets):
    overlap=sorted(set(local_targets)&set(remote_targets))
    if overlap:raise ValueError('Concurrent target ownership overlap: '+','.join(overlap[:3]))
    return True


def handoff_admission(remote_checks,local_supervisor,local_compilers,retained_verified,wall_limit=None,AS_limit=None,file_limit=None):
    required=('source','compiler','headers_CRT_runtime','PCH_fast','PCH_slow','input_hashes','capacity','fleet_lease','fresh_GO')
    if any(remote_checks.get(key) is not True for key in required):raise ValueError('Remote admission incomplete')
    if local_supervisor!=0 or local_compilers:raise ValueError('Local owner not quiescent')
    if retained_verified is not True:raise ValueError('Final completed-object snapshot unverified')
    if wall_limit is not None or AS_limit is not None or file_limit is not None:raise ValueError('Forbidden guessed build restriction')
    return {'state':'READY_FOR_DISJOINT_DISPATCH','frontend':False,'cold_PCH':False,'runtime':False,'build_wall_limit':None,'per_process_AS':None,'FSIZE':'unlimited'}


def assignments(all_targets):
    local, remote = [], []
    for target in all_targets:
        if not re.fullmatch(r'[A-Za-z0-9_]+\.o', target):
            raise ValueError('Unsafe target name')
        to_remote = ('_ot_hdc_v41x_attn_tile' in target
                     or ('___024root' in target and '__Slow' in target)
                     or ('_ot_hdc_v41x_vec_lane' in target and '__Slow' in target)
                     or '_ot_hdc_v41x_vsq' in target or '_ot_hdc_v41x_vred_op' in target)
        (remote if to_remote else local).append(target)
    if len(all_targets) != len(set(all_targets)):
        raise ValueError('Duplicate archive target')
    exclusive(local, remote)
    if set(local) | set(remote) != set(all_targets):
        raise ValueError('Target coverage hole')
    return local, remote


def shard_makefile(targets, name):
    if name not in ('D1_LOCAL_SHARD', 'D1_VM_SHARD'):
        raise ValueError('Invalid shard goal')
    if len(targets) != len(set(targets)) or any(not re.fullmatch(r'[A-Za-z0-9_]+\.o', x) for x in targets):
        raise ValueError('Unsafe or duplicate shard targets')
    return '.PHONY: ' + name + '\n' + name + ': ' + ' '.join(targets) + '\n'


def make_repro(queued):
    """The only execution here is a tiny Python/file-writing make harness."""
    with tempfile.TemporaryDirectory(prefix='D1-make-ownership-test-') as name:
        root=Path(name)
        (root/'gate.py').write_text('from pathlib import Path\nimport sys,time\nn=sys.argv[1]\nPath(n+".ready").write_text("ready")\nwhile not Path("release").exists():time.sleep(.005)\nPath(n+".o").write_text("local gate")\n')
        (root/'late.py').write_text('from pathlib import Path\nPath("local_late_started").write_text("yes")\nPath("late.o").write_text("LOCAL_LATE")\n')
        gates=['first','second'] if queued else ['first']
        mk='all: '+''.join(x+'.o ' for x in gates)+'late.o\n'
        for gate in gates:mk+=gate+'.o:\n\t'+sys.executable+' gate.py '+gate+'\n'
        mk+='late.o:\n\t'+sys.executable+' late.py\n'
        (root/'Makefile').write_text(mk)
        proc=subprocess.Popen(['make','-j'+str(len(gates)),'all'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:
            # Cleanup/readiness deadlines apply only to this synthetic test, never to native builds.
            deadline=time.monotonic()+10
            while not all((root/(g+'.ready')).exists() for g in gates):
                if time.monotonic()>deadline:raise RuntimeError('Synthetic harness did not start')
                time.sleep(.005)
            if queued:time.sleep(.1)  # allow make to queue late.o with both slots occupied
            (root/'late.o').write_text('REMOTE_LATE')
            (root/'release').write_text('release')
            stdout,stderr=proc.communicate(timeout=10)
            if proc.returncode:raise RuntimeError(stderr.decode())
            return dict(jobs=len(gates),exit_code=proc.returncode,remote_object_written_before_release=True,local_late_started=(root/'local_late_started').exists(),final_late_object=(root/'late.o').read_text(),stdout=stdout.decode(),stderr=stderr.decode())
        finally:
            (root/'release').write_text('release')
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM);proc.communicate()


def frozen_dispatch_repro():
    """Freeze only synthetic make dispatch; allow its active recipe to finish."""
    with tempfile.TemporaryDirectory(prefix='D1-frozen-dispatch-test-') as name:
        root = Path(name)
        (root/'worker.py').write_text('from pathlib import Path\nimport time\nPath("started").touch()\nwhile not Path("release").exists():time.sleep(.005)\nPath("first.o").write_text("complete")\n')
        (root/'Makefile').write_text('all: first.o later.o\nfirst.o:\n\t'+sys.executable+' worker.py\nlater.o:\n\t@echo later > later.o\n')
        proc = subprocess.Popen(['make', '-j1', 'all'], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            deadline = time.monotonic()+10  # tiny harness cleanup only
            while not (root/'started').exists():
                if time.monotonic()>deadline: raise RuntimeError('Harness readiness')
                time.sleep(.005)
            os.kill(proc.pid, signal.SIGSTOP)  # not the worker process group
            (root/'release').touch()
            while not (root/'first.o').exists():
                if time.monotonic()>deadline: raise RuntimeError('Harness completion')
                time.sleep(.005)
            time.sleep(.05)
            before = {'active_recipe_completed': (root/'first.o').read_text()=='complete', 'later_target_started_while_dispatch_frozen': (root/'later.o').exists()}
            os.kill(proc.pid, signal.SIGCONT)
            proc.communicate(timeout=10)
            return dict(before, resumed_exit=proc.returncode, later_target_completed_after_resume=(root/'later.o').exists())
        finally:
            (root/'release').touch()
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGCONT)
                os.killpg(proc.pid, signal.SIGTERM)
                proc.communicate()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--make-race-repro',action='store_true');a=p.parse_args()
    if not a.make_race_repro:p.error('Only synthetic ownership evidence generation is supported')
    print(json.dumps({'before_visit':make_repro(False),'already_queued':make_repro(True)},indent=2,sort_keys=True))
