"""One reviewed native design compile phase, aggregate-capped; no simulation API."""
import argparse,hashlib,json,os,selectors,shutil,signal,subprocess,time,uuid
from pathlib import Path
import price_w17_owned_progress_parallel_compile as pricing
ROOT=Path(__file__).resolve().parents[1]

def docker_argv(root,scratch,phase,image,name):
    cpus=sorted(os.sched_getaffinity(0))[:phase['CPU']]
    if len(cpus)!=phase['CPU']:raise ValueError('CPU affinity headroom')
    mem=phase['aggregate_memory_GiB']
    argv=['docker','run','--rm','--init','--name',name,'--network','none','--cpus',str(phase['CPU']),'--cpuset-cpus',','.join(map(str,cpus)),'--memory',f'{mem}g','--memory-swap',f'{mem}g','--pids-limit','512','--read-only','--tmpfs','/tmp:rw,size=1g','--user',f'{os.getuid()}:{os.getgid()}', '--volume',f'{root}:/source:ro','--volume',f'{scratch}:/build:rw','--volume','/home/ubuntu/.local/opentallas-tools:/home/ubuntu/.local/opentallas-tools:ro','--workdir','/source','--env','OMP_NUM_THREADS=1']
    if phase['kind']=='frontend':argv+=['--ulimit',f'as={64<<30}:{64<<30}']
    return argv+[image]+phase['argv']

def admit(phase,scratch):
    text=Path('/proc/meminfo').read_text();free=int(text.split('MemAvailable:')[1].split()[0])/(1<<20)
    if free<phase['aggregate_memory_GiB']+24:raise ValueError('fresh live RAM reserve')
    if shutil.disk_usage(scratch).free<56*(1<<30):raise ValueError('fresh disk reserve56GiB')
    if os.getloadavg()[0]>len(os.sched_getaffinity(0))-phase['CPU']-8:raise ValueError('fresh CPU/load reserve')
    return dict(free_RAM_GiB=free,disk_free_bytes=shutil.disk_usage(scratch).free,load=os.getloadavg(),affinity_CPUs=len(os.sched_getaffinity(0)))

def reviewed(plan_path,go_path,phase_index):
    plan=json.loads(plan_path.read_text());go=json.loads(go_path.read_text())
    if plan!=pricing.price(ROOT):raise ValueError('exact source-identical plan')
    if go.get('schema')!='w17.owned_progress.native_compile_GO.v1' or go.get('plan_sha256')!=hashlib.sha256(plan_path.read_bytes()).hexdigest() or go.get('source_commit')!=plan['source_commit'] or go.get('scope')!='NATIVE_COMPILE_ONLY' or go.get('execution_allowed') is not True or phase_index not in go.get('phase_indices',[]):raise ValueError('fresh independent compile GO binding')
    if go.get('owner_interface_policy')!='ORIGINAL_4E_OBSERVATION_ONLY_NO_CANCELLATION_SELECTION':raise ValueError('unreviewed cancellation selection')
    base=json.loads((ROOT/pricing.BASE/'native_commands.json').read_text())
    for p,h in {**base['source_sha256'],**base['host_helper_sha256']}.items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('source/helper pin '+p)
    return plan,plan['phases'][phase_index]

def run(plan_path,go_path,index,scratch):
    plan,phase=reviewed(plan_path,go_path,index)
    scratch.mkdir(exist_ok=True)
    prefix=scratch/f'phase{index:02d}'
    if prefix.with_suffix('.json').exists() or prefix.with_suffix('.log').exists():raise FileExistsError('preserve prior phase')
    if any(json.loads(p.read_text()).get('status')!='NATIVE_COMPILE_PHASE_PASS' for p in scratch.glob('phase*.json') if not p.name.endswith('.handle.json')):raise ValueError('stop first failure; no retry')
    for prior in range(index):
        path=scratch/f'phase{prior:02d}.json'
        if not path.exists() or json.loads(path.read_text())['status']!='NATIVE_COMPILE_PHASE_PASS':raise ValueError('ordered serial phase prerequisite')
    admission=admit(phase,scratch)
    actual=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',plan['container_image']],text=True).strip()
    if actual!=plan['container_image']:raise ValueError('exact immutable host image')
    name='w17-owned-native-'+uuid.uuid4().hex[:12];argv=docker_argv(ROOT,scratch,phase,actual,name)
    used=sum(p.stat().st_size for p in scratch.glob('phase*.log'));remaining=(16<<20)-used
    if remaining<=0:raise ValueError('shared log cap')
    def stop_owned(signum,frame):raise SystemExit('owned supervisor signal '+str(signum))
    signal.signal(signal.SIGTERM,stop_owned)
    start=time.monotonic();status='NATIVE_COMPILE_PHASE_FAIL';terminal=None
    process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    handle=dict(container=name,local_supervisor_PID=os.getpid(),docker_client_PID=process.pid,argv=argv,phase=index,admission=admission)
    with prefix.with_suffix('.handle.json').open('x') as f:f.write(json.dumps(handle,indent=2)+'\n')
    # Handles are immutable and remain available while compiler runs.
    print(json.dumps(handle),flush=True)
    try:
        sel=selectors.DefaultSelector();sel.register(process.stdout,selectors.EVENT_READ)
        with prefix.with_suffix('.log').open('xb') as log:
            while sel.get_map():
                if time.monotonic()-start>phase['wall_seconds']:raise TimeoutError('phase wall cap')
                for key,_ in sel.select(0.5):
                    chunk=os.read(key.fileobj.fileno(),65536)
                    if not chunk:sel.unregister(key.fileobj);continue
                    if len(chunk)>remaining:raise RuntimeError('shared16MiB log cap')
                    log.write(chunk);log.flush();remaining-=len(chunk)
        terminal=process.wait(timeout=5)
        if terminal==0:status='NATIVE_COMPILE_PHASE_PASS'
    except BaseException as error:
        status='NATIVE_COMPILE_CAP_OR_SUPERVISOR_FAIL';terminal=str(error)
    finally:
        # Stop THIS named owned container, including descendants, after all
        # terminal paths. Never kill unrelated jobs or retry a compile.
        try:
            subprocess.run(['docker','kill',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
        except Exception as error:
            status='NATIVE_COMPILE_CLEANUP_FAIL';terminal=str(error)
        if process.poll() is None:process.kill()
        process.wait(timeout=10)
    receipt=dict(status=status,terminal=terminal,wall_seconds=time.monotonic()-start,handle=handle,plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),go_sha256=hashlib.sha256(go_path.read_bytes()).hexdigest(),log_sha256=hashlib.sha256(prefix.with_suffix('.log').read_bytes()).hexdigest(),source_commit=plan['source_commit'],runtime_or_fulltoken_credit=False)
    with prefix.with_suffix('.json').open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
    return 0 if status=='NATIVE_COMPILE_PHASE_PASS' else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--go',type=Path,required=True);ap.add_argument('--phase',type=int,choices=range(16),required=True);ap.add_argument('--scratch',type=Path,required=True);args=ap.parse_args()
    raise SystemExit(run(args.plan,args.go,args.phase,args.scratch))
