#!/usr/bin/env python3
"""Serial short native-host comparison; completed model/archive reuse only."""
import argparse, hashlib, json, os
from pathlib import Path
import subprocess, threading, time
from run_full import fresh, observe, stage


def child(a):
    out=a.output
    fresh(out,a.phase,1 if a.phase=='link' else 16)
    stop=threading.Event(); monitor=threading.Thread(target=observe,args=(out,a.phase,stop));monitor.start()
    try:
        r=json.loads((out/'commands.json').read_text())
        if a.phase=='link': stage(out,'driver_link',r['link'])
        else:
            for name, enabled in [('baseline',False),('patch',True)]:
                fresh(out,name,16)
                env=os.environ.copy(); env.update(RT_THREADS='16',RT_PROGRESS='128',QWEN_P0_NATIVE_PROFILE='1',
                    QWEN_P0_NATIVE_DIRTY=str(int(enabled)),QWEN_P0_NATIVE_REENTRY_SKIP=str(int(enabled)))
                command=[r['binary'],*r['runtime_args']]
                command[command.index(r['old_run'])]=str(out/name)
                (out/name).mkdir()
                (out/(name+'_command.json')).write_text(json.dumps(dict(command=command,env={k:v for k,v in env.items() if k.startswith(('RT_','QWEN_P0_'))}),indent=2))
                with (out/(name+'.log')).open('x') as log:
                    p=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT)
                    (out/(name+'_pid.json')).write_text(json.dumps(dict(pid=p.pid,time=time.time())))
                    rc=p.wait()
                (out/(name+'.exit')).write_text(str(rc)+'\n')
                if rc: raise RuntimeError(name+' failed; preserve, no replay')
            traces=[(out/n/'events.txt').read_bytes() for n in ['baseline','patch']]
            import re
            logs=[(out/(n+'.log')).read_text() for n in ['baseline','patch']]
            terminal=[re.findall(r'P0_NATIVE_GATE terminal .*',s)[-1] for s in logs]
            kv=[re.search(r'kv_hash=(\w+)',s).group(1) for s in terminal]
            walls=[float(re.search(r'wall=([\d.]+)',s).group(1)) for s in terminal]
            exact=traces[0]==traces[1] and kv[0]==kv[1]
            result=dict(status='PASS_EQUIVALENCE' if exact else 'FAIL_EQUIVALENCE',
                trace_sha256=[hashlib.sha256(t).hexdigest() for t in traces],kv_hash=kv,
                terminal=terminal,wall_seconds=walls,speedup=walls[0]/walls[1],
                adopted=exact and walls[1]<walls[0],full_token_pass=False,physical_qualified=False)
            (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
            if not exact: raise RuntimeError('trace or KV mismatch; no adoption')
    finally:stop.set();monitor.join()


def dispatch(a):
    phases=[('relink-driver',1),('runtime',16)] if a.full else [('link',1),('run',16)]
    for phase,cpus in phases:
        # Wait only before admission, never restart an admitted failing child.
        while True:
            try: fresh(a.output,phase+'_pre',cpus);break
            except RuntimeError: print('WAIT_CPU '+phase,flush=True);time.sleep(20)
        if a.full:
            cmd=['/srv/opentallas-scratch/admit.sh','16','--','python3',str(Path(__file__).with_name('run_full.py')),
                 '--output',str(a.output),'--source',str(a.output/'src'),'--stage',phase]
        else:
            cmd=['/srv/opentallas-scratch/admit.sh','16','--','python3',__file__,'--output',str(a.output),'--phase',phase]
        (a.output/(phase+'_guard_command.json')).write_text(json.dumps(cmd)+'\n')
        env=os.environ.copy()
        if a.full:
            env.update(RT_THREADS='16',QWEN_P0_NATIVE_REENTRY_SKIP='1',QWEN_P0_NATIVE_PROFILE='1')
        with (a.output/(phase+'_supervisor.log')).open('x') as log: rc=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
        (a.output/(phase+'_supervisor.exit')).write_text(str(rc)+'\n')
        if rc:raise RuntimeError(phase+' stopped; no replay/rebuild')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--phase',choices=['dispatch','link','run'],required=True)
    p.add_argument('--full',action='store_true',help='one final full36/head smoke, only after trace gate PASS')
    a=p.parse_args()
    if a.full:
        gate=json.loads((a.output/'qualified_native_gate.json').read_text())
        if gate['status']!='PASS_EQUIVALENCE' or not gate['adopted']:
            raise RuntimeError('changed-host trace and speed gate must pass before final smoke')
        prepared=json.loads((a.output/'prepared.json').read_text())
        if prepared.get('qualified_hot_gate'):
            hot=json.loads(Path(prepared['qualified_hot_gate']).read_text())
            if hot['status'] not in ('PASS_COMPILER_EQUIVALENCE', 'PASS_NATIVE_SOURCE_EQUIVALENCE') or not hot['adopted']:
                raise RuntimeError('changed native archive trace and speed qualification required')
            if hot['new_archive_sha256']!=prepared['completed_top_sha256']:
                raise RuntimeError('selected optimized archive differs from qualified compiler candidate')
    try: dispatch(a) if a.phase=='dispatch' else child(a)
    except Exception as e:
        (a.output/(a.phase+'_terminal.json')).write_text(json.dumps(dict(status='FAIL_'+a.phase.upper(),reason=str(e),full_token_pass=False))+'\n');raise
