"""Opt-in native-only relink/pilot. No make, frontend, RTL or original binary writes."""
import argparse, hashlib, json, os, re, resource, shutil, signal, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'results/uarch/w17_D1_native_affinity_observability_20261002'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def inverse(s):
    return re.sub(r'// D1_OBSERVE_BEGIN\n.*?// D1_OBSERVE_END\n','',s,flags=re.S)
def validate_package():
    plan=load(EV/'plan.json')
    if sha(Path(__file__))!=plan['runner_sha256']:raise ValueError('runner pin')
    if inverse((EV/'observed_main.cpp').read_text())!=(EV/'original_main.cpp').read_text():raise ValueError('driver inverse')
    for f,k in [('original_main.cpp','original_main_sha256'),('observed_main.cpp','observed_main_sha256'),('input_pins.json','input_pins_sha256')]:
        if sha(EV/f)!=plan[k]:raise ValueError('package pin')
    if sha(EV/'full_object_inventory.json')!=plan['full_object_inventory_sha256']:raise ValueError('full object inventory pin')
    return plan
def verify_inputs(pins):
    for p,v in pins.items():
        if Path(p).stat().st_size!=v['bytes'] or sha(p)!=v['sha256']:raise ValueError('input/ABI/tool pin '+p)
def validate_go(go,head):
    if go!=dict(approved=True,plan_sha256=sha(EV/'plan.json'),scope=validate_package()['claim'],single_use=True,execution_commit=head):raise ValueError('fresh exact GO required')
def headroom(plan):
    mem={k:int(v.split()[0])*1024 for k,v in (s.split(':',1) for s in Path('/proc/meminfo').read_text().splitlines())}
    disk=shutil.disk_usage('/tmp').free
    if mem['MemAvailable']<plan['caps']['memory']+plan['headroom']['memory_reserve'] or disk<plan['caps']['output_bytes']+plan['headroom']['disk_reserve']:raise ValueError('headroom reserve')
    return dict(available_memory=mem['MemAvailable'],available_disk=disk)
def caps(unit,plan):
    raw=subprocess.check_output(['systemctl','--user','show',unit,'-p','ControlGroup','-p','RuntimeMaxUSec','-p','KillMode','-p','KillSignal'],text=True)
    d=dict(s.split('=',1) for s in raw.splitlines() if '=' in s)
    rel=next(s.split('::')[1] for s in Path('/proc/self/cgroup').read_text().splitlines() if s.startswith('0::'))
    cg=Path('/sys/fs/cgroup')/rel.lstrip('/')
    if d.get('ControlGroup')!=rel or d.get('RuntimeMaxUSec') not in ('1min 30s','90s','90000000') or d.get('KillMode')!='control-group' or d.get('KillSignal')!='9':raise ValueError('systemd hardstop')
    if (cg/'memory.max').read_text().strip()!=str(plan['caps']['memory']) or (cg/'memory.swap.max').read_text().strip()!='0':raise ValueError('aggregate caps')
    if sorted(os.sched_getaffinity(0))!=[1,2] or resource.getrlimit(resource.RLIMIT_FSIZE)!=(268435456,268435456):raise ValueError('affinity/filesize')
    return dict(systemd=d,cgroup=str(cg),kernel_affinity=sorted(os.sched_getaffinity(0)),cpu_enforcement='kernel_affinity_only_no_quota',memory_max=(cg/'memory.max').read_text().strip(),swap_max=(cg/'memory.swap.max').read_text().strip())
def child_caps():
    if sorted(os.sched_getaffinity(0))!=[1,2]:raise ValueError("child affinity mismatch")
    resource.setrlimit(resource.RLIMIT_AS,(4294967296,4294967296))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def stage(cmd,log,seconds,out,plan):
    begin=time.monotonic()
    with log.open('xb') as f:
        p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=child_caps)
        write(out/'active_stage.json',dict(pid=p.pid,command=cmd,seconds=seconds,log=str(log)))
        reason=None
        while p.poll() is None:
            total=sum(x.stat().st_size for x in out.rglob('*') if x.is_file())
            if time.monotonic()-begin>=seconds:reason='stage_time_cap'
            elif log.stat().st_size>plan['caps']['log_bytes']:reason='log_cap'
            elif total>plan['caps']['output_bytes']:reason='output_cap'
            if reason:
                os.killpg(p.pid,signal.SIGKILL);p.wait();break
            time.sleep(.05)
    total=sum(x.stat().st_size for x in out.rglob('*') if x.is_file())
    if total>plan['caps']['output_bytes'] or log.stat().st_size>plan['caps']['log_bytes']:reason='exit_output_cap'
    return dict(command=cmd,returncode=p.returncode,wall_seconds=time.monotonic()-begin,stop=reason,log_sha256=sha(log),output_bytes=total)
def parse_markers(text):
    pattern=r'^D1_HOST phase=([A-Z_]+) mono_s=(\d+) mono_ns=(\d+) simtime=(\d+) evals=(\d+)$'
    events=[]
    for line in text.splitlines():
        if not line.startswith('D1_HOST '):continue
        hit=re.fullmatch(pattern,line)
        if not hit:raise ValueError('incomplete host marker')
        phase,sec,ns,sim,ev=hit.groups();ns=int(ns)
        if ns>=1000000000:raise ValueError('monotonic ns range')
        e=dict(phase=phase,mono_ns=int(sec)*1000000000+ns,simtime=int(sim),evals=int(ev))
        if events and any(e[k]<events[-1][k] for k in ['mono_ns','simtime','evals']):raise ValueError('marker regression')
        events.append(e)
    timings={}
    for name in ['CONTEXT','CONSTRUCTOR','FINAL']:
        start=[e for e in events if e['phase']==name+'_ENTER'];end=[e for e in events if e['phase']==name+'_RETURN']
        if len(start)>1 or len(end)>1 or (end and not start):raise ValueError('phase ownership')
        timings[name.lower()+'_seconds']=(end[0]['mono_ns']-start[0]['mono_ns'])/1e9 if start and end else None
    completed=[e for e in events if e['phase']=='EVAL_RETURN']
    rate=None
    if len(completed)>1:
        a,b=completed[0],completed[-1]
        if b['evals']>a['evals']:rate=(b['mono_ns']-a['mono_ns'])/1e9/(b['evals']-a['evals'])
    return dict(events=events,phase_seconds=timings,observed_seconds_per_eval=rate,
        cycles_per_second=None,scope='HOST_EVAL_COST_ONLY_SCHEDULER_SLOTS_NOT_SOURCE_CYCLES',
        qualification=False,unfinished_eval_possible=bool(events and events[-1]['phase']=='EVAL_ENTER'))
def execute(a):
    plan=validate_package();pins=load(EV/'input_pins.json')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):raise ValueError('execution owner must be clean')
    validate_go(load(a.go),head)
    out=Path(a.out).resolve()
    if out.exists():raise ValueError('fresh scratch only')
    capreceipt=caps(a.unit,plan);verify_inputs(pins);verify_inputs(load(EV/'full_object_inventory.json'));hr=headroom(plan)
    with Path(str(Path(a.go).resolve())+'.used').open('x') as f:f.write(head+'\n')
    out.mkdir();write(out/'admission.json',dict(caps=capreceipt,headroom=hr,head=head,plan_sha256=sha(EV/'plan.json')))
    receipt=dict(scope=plan['claim'],steps=[],status='FAIL_PRESERVED_NO_RETRY',runtime_started=False)
    try:
        obj=Path(plan['obj']);archive=out/'model.a';main=out/'observed_main.cpp';shutil.copyfile(EV/'observed_main.cpp',main)
        # All members retained. Rename only original main; it shares a member with model code.
        commands=[([plan['objcopy'],'--redefine-sym','main=D1_retained_main',str(obj/'Vtb_D1__ALL.a'),str(archive)],10),
          ([plan['cxx'],*plan['compile_flags'],'-c',str(main),'-o',str(out/'main.o')],20),
          ([plan['cxx'],str(out/'main.o'),*[str(obj/n) for n in ['observer_dpi.o','verilated.o','verilated_dpi.o','verilated_timing.o','verilated_threads.o']],str(archive),'-pthread','-lpthread','-latomic','-o',str(out/'pilot')],30)]
        for i,(cmd,seconds) in enumerate(commands):
            verify_inputs(pins);write(out/f'headroom_{i}.json',headroom(plan))
            r=stage(cmd,out/f'native_{i}.log',seconds,out,plan);receipt['steps'].append(r)
            if r['returncode'] or r['stop']:raise RuntimeError('native stage stopped; no retry')
        symbols=subprocess.check_output([plan['nm'],'--defined-only',str(archive)],text=True,timeout=5)
        if not re.search(r' T D1_retained_main$',symbols,re.M) or re.search(r' T main$',symbols,re.M):raise ValueError('archive main rename')
        receipt['binary_sha256']=sha(out/'pilot');verify_inputs(pins);write(out/'headroom_runtime.json',headroom(plan))
        receipt['runtime_started']=True
        r=stage([str(out/'pilot'),*plan['argv']],out/'pilot.log',20,out,plan);receipt['steps'].append(r)
        write(out/'cost_observation.json',parse_markers((out/'pilot.log').read_text(errors='replace')))
        receipt['status']='PILOT_TIME_CAP_STOP_COST_ONLY' if r['stop']=='stage_time_cap' else ('PILOT_EXIT_COST_ONLY' if not r['stop'] and r['returncode']==0 else 'FAIL_PRESERVED_NO_RETRY')
    except Exception as e:receipt['error']=str(e)
    finally:
        try:verify_inputs(pins);verify_inputs(load(EV/'full_object_inventory.json'));receipt['input_postcheck']=True
        except Exception as e:receipt['input_postcheck']=False;receipt['postcheck_error']=str(e);receipt['status']='FAIL_PRESERVED_NO_RETRY'
        write(out/'receipt.json',receipt)
    return 0 if receipt['status']!='FAIL_PRESERVED_NO_RETRY' else 1
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--go');ap.add_argument('--out');ap.add_argument('--unit');a=ap.parse_args()
    if a.execute:
        if not all([a.go,a.out,a.unit]):ap.error('GO/output/unit required')
        raise SystemExit(execute(a))
    print(json.dumps(validate_package(),indent=2))
