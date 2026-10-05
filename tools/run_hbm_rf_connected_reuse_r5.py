#!/usr/bin/env python3
"""Execute sequential native DS/Qwen only under a source-bound fresh parent GO.
No cgroup, permissions, affinity, systemd or configuration changes are made here.
Parent supplies the named capped service and hard inherited CPU affinity.
"""
import argparse,json,os,resource,signal,subprocess,sys,time
from pathlib import Path
import full_sm_rf_verilator_gate as G
import prepare_hbm_rf_connected_reuse_r5 as P
ROOT=P.ROOT
CAPS=P.RUNNER_CAPS
GO_SCHEMA=P.GO_SCHEMA

def validate_go(go,proposal_path,commit):
    if go.get('schema')!=GO_SCHEMA or go.get('admitted') is not True:raise ValueError('fresh parent GO required')
    if go.get('source_commit')!=commit or go.get('proposal_sha256')!=G.sha(proposal_path):raise ValueError('GO source/proposal mismatch')
    if go.get('runner_caps')!=CAPS:raise ValueError('GO runner caps mismatch')
    proposal=json.loads(proposal_path.read_text());reuse=proposal['reuse_inventory_pin']
    if go.get('reuse_inventory_sha256')!=reuse['sha256'] or go.get('prior_frontend_GO_commit')!=reuse['prior_frontend_GO_commit'] or go.get('frontend_end_sha256')!=reuse['frontend_end_sha256']:raise ValueError('fresh GO must bind inventory/priorGO/successfulfrontend')
    for key in ('frontend_argv_sha256','frontend_source_bundle_sha256','frontend_tool_bundle_sha256'):
        if go.get(key)!=reuse[key]:raise ValueError('fresh GO must bind exactfrontend '+key)
    output=Path(go.get('output_path',''))
    if not output.is_absolute() or output.resolve().is_relative_to(ROOT.resolve()):raise ValueError('GO must bind fresh external absolute output')
    if not go.get('unit','').endswith('.service'):raise ValueError('GO must bind named service')
    record=go.get('admission_record_path','')
    if not record.startswith('results/') or not record.endswith('.json') or '..' in Path(record).parts:raise ValueError('invalid committed GO path')

def validate_limits(unit,cg,mem,swap,affinity,info):
    if unit not in cg.split('/'):raise ValueError('runner outside admitted named cgroup')
    if mem=='max' or int(mem)<=0 or int(mem)>CAPS['memory_bytes'] or swap=='max' or int(swap)!=0:raise ValueError('memory/swap cap mismatch')
    if set(affinity)!=set(CAPS['cpus']):raise ValueError('hard affinity must be exactly CPUs24-27')
    if info.get('RuntimeMaxUSec') not in ('37min','37min 0s','2220s'):raise ValueError('whole service runtime must be2220s')
    if int(info.get('LimitFSIZE','0'))!=CAPS['per_file_bytes'] or info.get('OOMPolicy')!='stop':raise ValueError('FSIZE/OOM policy mismatch')
    return dict(cgroup=cg,memory_max=mem,memory_swap_max=swap,hard_affinity=sorted(affinity),systemd=info,
                cpu_quota_enforced=False,cpu_policy='hard sched affinity24-27; cpu.max is not required or inferred')

def validate_cgroup(go):
    cg=next((x.split(':',2)[2] for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::')),None)
    if not cg:raise ValueError('unified cgroup required')
    base=Path('/sys/fs/cgroup')/cg.lstrip('/')
    info=dict(x.split('=',1) for x in G.query(['systemctl','--user','show',go['unit'],'--property=RuntimeMaxUSec,LimitFSIZE,OOMPolicy']).splitlines() if '=' in x)
    # CPU controller is not delegated to user@; never require/read cpu.max.
    return validate_limits(go['unit'],cg,(base/'memory.max').read_text().strip(),
                           (base/'memory.swap.max').read_text().strip(),os.sched_getaffinity(0),info)

def check_process_affinity(pid):
    """Read-only verification of leader plus currently observed descendants/threads."""
    seen=set();todo=[pid];count=0
    while todo:
        n=todo.pop()
        if n in seen:continue
        seen.add(n)
        tasks=Path('/proc')/str(n)/'task'
        try:threads=list(tasks.iterdir())
        except FileNotFoundError:continue
        for t in threads:
            try:
                affinity=os.sched_getaffinity(int(t.name))
                if not affinity or not set(affinity)<=set(CAPS['cpus']):raise RuntimeError('child/thread affinity exceeds24-27')
                count+=1
                todo.extend(int(x) for x in (t/'children').read_text().split())
            except (ProcessLookupError,FileNotFoundError):continue
    return count

def commands(proposal,out,go_commit=None):
    for target in ('DS','Qwen'):
        for phase in proposal['commands'][target]:
            argv=[x.replace('<fresh-output>',str(out)).replace('<fresh-GO-commit>',go_commit or '<required-fresh-GO-commit>').replace('<pinned-python>',sys.executable) for x in phase['argv']]
            argv[0]={'make':'/usr/bin/make','python3':sys.executable}.get(argv[0],argv[0])
            yield target,phase['phase'],phase['timeout_s'],argv

def signal_failure(signum,frame):raise RuntimeError('TERMINATED_SIGNAL_'+str(signum))

def execute(proposal_path,go_path,go_commit,out):
    if not go_path or not go_commit:raise ValueError('committed parent GO and --go-commit required; no retry')
    proposal=json.loads(proposal_path.read_text());go=json.loads(go_path.read_text());commit=G.git('rev-parse','HEAD')
    validate_go(go,proposal_path,commit)
    if str(out)!=go['output_path']:raise ValueError('output differs from fresh GO binding')
    admitted=G.git('rev-parse',go_commit+'^{commit}')
    if subprocess.check_output(['git','show',admitted+':'+go['admission_record_path']],cwd=ROOT)!=go_path.read_bytes():raise ValueError('GO bytes differ from parent commit')
    if G.git('status','--porcelain','--untracked-files=normal'):raise ValueError('clean pinned run worktree required')
    if not out.is_absolute() or out.exists() or out.resolve().is_relative_to(ROOT.resolve()):raise ValueError('fresh absolute external output required')
    out.mkdir();G.write_new(out/'proposal.json',proposal_path.read_bytes());G.write_new(out/'GO.json',go_path.read_bytes())
    receipt=dict(schema='opentallas.hbm-RF-connected.run.v1',source_commit=commit,GO_commit=admitted,
                 proposal_sha256=G.sha(proposal_path),GO_sha256=G.sha(go_path),source_sha256=proposal['source_sha256'],
                 phases=[],verdict='FAIL_INCOMPLETE',connected_measurement=False,physical_credit=False,token_credit=False)
    G.write_new(out/'run_start.json',G.json_bytes(receipt))
    started=time.monotonic();proc=None
    old_signals={s:signal.signal(s,signal_failure) for s in (signal.SIGTERM,signal.SIGINT)}
    try:
        if proposal!=P.prepare():raise ValueError('reviewed source/tool/model/caps drift')
        for key in ('VERILATOR_ROOT','VERILATOR_BIN','VERILATOR_FLAGS','MAKEFLAGS','CXX','CC','CFLAGS','CXXFLAGS','LDFLAGS','OPT_FAST','OPT_SLOW','OPT_GLOBAL','LD_PRELOAD','LD_LIBRARY_PATH','PYTHONPATH','CPATH','CPLUS_INCLUDE_PATH','CPPFLAGS','LIBRARY_PATH','GCC_EXEC_PREFIX','COMPILER_PATH','OBJCACHE'):
            val=os.environ.get(key)
            if val and not (key=='VERILATOR_ROOT' and val==str(G.VROOT)):raise ValueError('unreviewed tool environment: '+key)
        receipt['admission']=validate_cgroup(go)
        disk=os.statvfs(out.parent)
        if disk.f_bavail*disk.f_frsize<CAPS['disk_headroom_bytes']:raise ValueError('insufficient fresh disk headroom')
        resource.setrlimit(resource.RLIMIT_FSIZE,(CAPS['per_file_bytes'],CAPS['per_file_bytes']))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        for target,name,limit,cmd in commands(proposal,out,admitted):
            target_dir=out/target;target_dir.mkdir(exist_ok=True)
            logpath=target_dir/('actual_sim.log' if name=='simulation' else name+'.log')
            phase=dict(target=target,name=name,argv=cmd,wall_limit_s=limit);receipt['phases'].append(phase)
            G.write_new(out/f'{target}-{name}-start.json',G.json_bytes(phase))
            t=time.monotonic();reason=None
            with logpath.open('xb') as log:
                proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                phase['pid']=proc.pid
                try:
                    while True:
                        now=time.monotonic();rc=proc.poll()
                        if now-t>=limit:reason='PHASE_TIMEOUT'
                        elif now-started>=CAPS['whole_wall_s']-10:reason='WHOLE_TIMEOUT'
                        elif G.directory_bytes(out)>CAPS['aggregate_output_bytes']:reason='OUTPUT_CAP'
                        if reason:G.terminate_group(proc);break
                        if rc is not None:break
                        phase['affinity_thread_checks']=phase.get('affinity_thread_checks',0)+check_process_affinity(proc.pid)
                        time.sleep(CAPS['poll_s'])
                finally:
                    if proc.poll() is None:G.terminate_group(proc)
                    phase.update(exit_code=proc.returncode,wall_s=time.monotonic()-t,termination_reason=reason)
                    proc=None
            G.write_new(out/f'{target}-{name}-end.json',G.json_bytes(phase))
            if reason or phase['exit_code']!=0:raise RuntimeError(target+'/'+name+' failed: '+str(reason or phase['exit_code']))
            if name=='reuse_frontend':
                reuse=json.loads((target_dir/'reuse_receipt.json').read_text());pin=proposal['reuse_inventory_pin']
                if reuse['verdict']!='PASS_EXCLUSIVE_COMPLETE_FRONTEND_COPY_ONLY' or reuse['inventory_sha256']!=pin['sha256'] or reuse['files']!=pin['file_count']:raise RuntimeError('complete reusedfrontend receipt mismatch')
            if name=='simulation':
                text=logpath.read_text()
                if 'CONNECTED_RF_FENCE_PASS' not in text or 'RESET_RF_FENCE_PASS' not in text:raise RuntimeError('missing connected/reset actual markers')
            if name=='trace':
                v=json.loads((target_dir/'trace_verdict.json').read_text())
                q=0 if target=='DS' else 1
                if v['verdict']!='PASS_DIRECTED_CONNECTED_TRACE_ONLY' or len(v['cases'])!=4 or any(c['qwen']!=q for c in v['cases']):raise RuntimeError('actual trace target/verdict mismatch')
            G.write_new(out/f'progress-{target}-{name}.json',G.json_bytes(receipt))
        if G.directory_bytes(out)>CAPS['aggregate_output_bytes']:raise RuntimeError('OUTPUT_CAP final')
        receipt.update(verdict='PASS_DIRECTED_NATIVE_DS_QWEN_CONNECTED_ONLY',connected_measurement=True)
    except Exception as exc:receipt['failure']=str(exc)
    finally:
        if proc is not None and proc.poll() is None:G.terminate_group(proc)
        receipt['wall_s']=time.monotonic()-started;receipt['output_bytes']=G.directory_bytes(out)
        receipt['logs_sha256']={str(p.relative_to(out)):G.sha(p) for p in out.rglob('*.log')}
        receipt['binary_sha256']={str(p.relative_to(out)):G.sha(p) for p in out.glob('*/obj/Vconnected')}
        receipt['trace_sha256']={str(p.relative_to(out)):G.sha(p) for p in out.glob('*/trace_verdict.json')}
        G.write_new(out/'verdict.json',G.json_bytes(receipt))
        for s,h in old_signals.items():signal.signal(s,h)
    if receipt['verdict']!='PASS_DIRECTED_NATIVE_DS_QWEN_CONNECTED_ONLY':raise RuntimeError(receipt.get('failure','incomplete'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--proposal',type=Path,required=True)
    p.add_argument('--go',type=Path,required=True);p.add_argument('--go-commit',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    try:execute(a.proposal,a.go,a.go_commit,a.out)
    except Exception as exc:raise SystemExit(str(exc))
if __name__=='__main__':main()
