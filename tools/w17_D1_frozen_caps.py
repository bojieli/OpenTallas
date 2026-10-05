# Additive D1 cap variant derived from retained owner-progress cap checker.
# New 12GiB/900s/2GiB budget and CPUs0-1; old cap file remains byte-identical.
import os,re,resource,subprocess,time,json,hashlib
from pathlib import Path
OUTPUT_PEAK=0
CAPS={'MemoryMax':12884901888,'MemorySwapMax':0,'CPUAffinity':[0,1],'LimitFSIZE':268435456,'LimitCORE':0,'RuntimeMaxSec':900,'KillMode':'control-group','KillSignal':9,'OOMPolicy':'stop'}
BUDGET={'generated_output_total_bytes':2147483648}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def parse_cpu_set(value):
    ids=[]
    for part in value.split():
        match=re.fullmatch(r'(\d+)(?:-(\d+))?',part)
        if not match:raise ValueError('CPU affinity syntax')
        first=int(match.group(1));last=int(match.group(2) or first)
        if last<first or last-first>4096:raise ValueError('CPU affinity range')
        ids.extend(range(first,last+1))
    return sorted(set(ids))

def caps_receipt(unit):
    fields=['ControlGroup','MemoryMax','MemorySwapMax','CPUAffinity','LimitFSIZE','LimitCORE','RuntimeMaxUSec','KillMode','KillSignal','OOMPolicy']
    raw=subprocess.check_output(['systemctl','--user','show',unit]+['--property='+k for k in fields],text=True)
    got=dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
    for k,v in CAPS.items():
        if k=='RuntimeMaxSec':
            if got.get('RuntimeMaxUSec') not in ('15min','900000000'):raise ValueError('hardstop cap')
        elif k=='CPUAffinity':
            if parse_cpu_set(got.get(k,''))!=v:raise ValueError('CPU cap')
        elif str(got.get(k))!=str(v):raise ValueError('cgroup cap: '+k)
    if sorted(os.sched_getaffinity(0))!=CAPS['CPUAffinity']:raise ValueError('actual affinity')
    if resource.getrlimit(resource.RLIMIT_FSIZE)!=(CAPS['LimitFSIZE'],CAPS['LimitFSIZE']):raise ValueError('actual FSIZE')
    # Validate kernel cgroup values, not only requested systemd properties.
    relative=next(line.split('::',1)[1] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
    cgroup=Path('/sys/fs/cgroup')/relative.lstrip('/')
    if got.get('ControlGroup')!=relative:raise ValueError('worker not in declared aggregate cgroup')
    if (cgroup/'memory.max').read_text().strip()!=str(CAPS['MemoryMax']) or (cgroup/'memory.swap.max').read_text().strip()!='0':raise ValueError('actual aggregate memory/swap cap')
    return {'systemd':got,'kernel_cgroup':str(cgroup),'memory_max':(cgroup/'memory.max').read_text().strip(),
            'swap_max':(cgroup/'memory.swap.max').read_text().strip(),'affinity':sorted(os.sched_getaffinity(0))}

def output_size(out):
    global OUTPUT_PEAK
    total=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    OUTPUT_PEAK=max(OUTPUT_PEAK,total)
    return total

def supervised(command,log,seconds,out):
    start=time.monotonic()
    write(out/'active_stage.json',{'command':command,'log':str(log),'seconds':seconds,'state':'RUNNING_NO_RETRY'})
    with log.open('x') as stream:
        p=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while p.poll() is None:
                elapsed=time.monotonic()-start;live=output_size(out)
                if elapsed>seconds or live>BUDGET['generated_output_total_bytes'] or log.stat().st_size>16777216:
                    predicate='log_cap' if log.stat().st_size>16777216 else ('aggregate_output_cap' if live>BUDGET['generated_output_total_bytes'] else 'stage_time_cap')
                    write(out/'first_failure_stage.json',{'predicate':predicate,'command':command,'wall_seconds':elapsed,'live_output_bytes':live,'sampled_peak_bytes':OUTPUT_PEAK,'no_retry':True})
                    raise RuntimeError(predicate+'; no retry')
                time.sleep(.1)
        except BaseException:
            import signal
            os.killpg(p.pid,signal.SIGKILL);p.wait();raise
    if output_size(out)>BUDGET['generated_output_total_bytes'] or log.stat().st_size>16777216:
        write(out/'first_failure_stage.json',{'predicate':'aggregate_output_cap_at_stage_exit','command':command,'live_output_bytes':output_size(out),'no_retry':True})
        raise RuntimeError('aggregate output cap at stage exit; no retry')
    return {'command':command,'returncode':p.returncode,'wall_seconds':time.monotonic()-start,
            'log':str(log),'log_sha256':sha(log)}

def read_clean_runtime_events(cgroup):
    events={k:int(v) for k,v in (line.split() for line in (Path(cgroup)/'memory.events').read_text().splitlines())}
    if any(events.get(k,-1)!=0 for k in ('max','oom','oom_kill','oom_group_kill')):
        raise ValueError('runtime memory cap/OOM event; no semantic qualification')
    return events
