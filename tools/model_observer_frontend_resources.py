"""Metadata-only budget preflight; never launches a compiler or reads build payloads."""
import hashlib,json,os,re,shlex,subprocess,time
from pathlib import Path
SOURCE='4e38326d6f361bc85e660f48c59c355e2bb95274'
OUT='results/rtl/observer_frontend_resource_model_4e383_20261002'
GiB=1024**3

def digest(b):return hashlib.sha256(b).hexdigest()

def headroom():
    mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.split()[0] in ('MemTotal:','MemAvailable:','SwapTotal:','SwapFree:')}
    st=os.statvfs('/tmp'); group=Path('/proc/self/cgroup').read_text().strip().split('::')[-1]
    p=Path('/sys/fs/cgroup')/group.lstrip('/'); ancestors=[]
    while True:
        entry={'path':str(p)}
        for name in ('memory.max','memory.current','cpu.max','cpuset.cpus.effective'):
            f=p/name
            if f.exists():entry[name]=f.read_text().strip()
        ancestors.append(entry)
        if p==Path('/sys/fs/cgroup'):break
        p=p.parent
    return dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),memory=mem,disk_available_bytes=st.f_bavail*st.f_frsize,cpu_affinity=sorted(os.sched_getaffinity(0)),load=os.getloadavg(),cgroup_ancestors=ancestors)

def admit(h):
    """Reserve is additional to isolated cap; swap is never credited."""
    if h['memory']['MemAvailable']<96*GiB:raise ValueError('host memory reserve insufficient')
    if h['disk_available_bytes']<18*GiB:raise ValueError('disk scratch plus reserve insufficient')
    n=len(h['cpu_affinity'])
    if n<10 or max(h['load'])>n-10:raise ValueError('two CPUs plus eight CPU headroom unavailable')
    for c in h['cgroup_ancestors']:
        if 'memory.max' in c and c['memory.max']!='max':
            if int(c['memory.max'])-int(c['memory.current'])<96*GiB:raise ValueError('cgroup memory reserve insufficient')
        if 'cpu.max' in c:
            quota,period=c['cpu.max'].split()
            if quota!='max' and int(quota)/int(period)<10:raise ValueError('cgroup CPU quota insufficient')
    return True

def validate_evidence(repo):
    repo=Path(repo); out=repo/OUT
    launch=json.loads((out/'retained_launch.json').read_bytes())
    if launch['source_commit']!=SOURCE or launch['launch']['source_commit']!=SOURCE:raise ValueError('wrong source authority')
    records=json.loads((out/'retained_frontends.json').read_bytes())
    if len(records)!=4:raise ValueError('missing retained measurements')
    for rank,r in enumerate(records):
        b=(out/f'verilate_die{rank}.log').read_bytes()
        if len(b)>4*1024**2 or digest(b)!=r['retained_sha256']:raise ValueError('retained metadata pin mismatch')
        text=b.decode(); argv=shlex.split(re.search(r'Command being timed: "(.*)"',text).group(1))
        if argv!=r['argv'] or r['source_commit']!=SOURCE:raise ValueError('command authority mismatch')
        if '--cc' not in argv or '--build' in argv or argv[argv.index('--top-module')+1]!='ot_v41_rt_die':raise ValueError('wrong frontend phase')
        if r['parameters']!=dict(SUN=256,SUM=64,ROM_PHW=6,CL_LANES=16,CL_DEPTH=512,CL_RELAY=0):raise ValueError('different hierarchy binding')
        required=[f'-GRANK={rank}','-GROM_PHW=6','-GCL_LANES=16','-GCL_DEPTH=512','-GCL_RELAY=0','-DV41_ATT_CUT','-fno-gate']
        if any(x not in argv for x in required):raise ValueError('binding command mismatch')
        if any(x.startswith('-GSUN=') or x.startswith('-GSUM=') for x in argv):raise ValueError('different lane binding')
        rss=int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',text).group(1))
        if r['peak_rss_kib']!=rss or r['exit_status']!=0 or 'Exit status: 0' not in text:raise ValueError('measurement mismatch')
        expected={str(Path(a).relative_to(launch['source'])) for a in argv if a.endswith(('.sv','.v','.vlt'))}
        if expected!=set(r['source_sha256']):raise ValueError('source argument census mismatch')
        if any(launch['source_sha256'].get(p)!=s for p,s in r['source_sha256'].items()):raise ValueError('archived manifest mismatch')
        for p,s in r['source_sha256'].items():
            b=subprocess.check_output(['git','show',SOURCE+':'+p],cwd=repo)
            if digest(b)!=s or launch['source_sha256'].get(p)!=s:raise ValueError('source authority mismatch')
    wrapper=subprocess.check_output(['git','show',SOURCE+':rtl/test/v41_runtime/ot_v41_rt_die.sv'],cwd=repo).decode()
    for key,n in [('SUN',256),('SUM',64)]:
        if not re.search(r'parameter\s+integer\s+'+key+r'\s*=\s*'+str(n)+r'\b',wrapper):raise ValueError('original default mismatch')
    return records

def validate_selected_counts(repo):
    """Check selected generate groups only; does not pretend to elaborate RTL."""
    repo=Path(repo); record=json.loads((repo/OUT/'hierarchy_cost.json').read_bytes()); text={}
    if record['source_commit']!=SOURCE:raise ValueError('hierarchy source mismatch')
    for p,s in record['source_sha256'].items():
        b=subprocess.check_output(['git','show',SOURCE+':'+p],cwd=repo)
        if digest(b)!=s:raise ValueError('hierarchy pin mismatch')
        text[p]=b.decode()
    vec=text['rtl/hdc/v41x/ot_hdc_v41x_vec.sv'];lane=text['rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv'];ckv=text['rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv']
    for expression in ['for (l = 0; l < N; l = l + 1)','KIND((l == 0) ? 2 : (l < M) ? 1 : 0)']:
        if expression not in vec:raise ValueError('lane generate contract changed')
    for name in ['u_m1','u_m2','u_q','u_e1m','u_me2']:
        if len(re.findall(r'ot_hdc_qmul_lat\s*#\(MLAT\)\s+'+name+r'\s*\(',lane))!=1:raise ValueError('base multiplier census mismatch')
    for name in ['u_ad','u_e1a','u_den']:
        if not re.search(r'ot_hdc_qadd_lat[^;]*\b'+name+r'\s*\(',lane):raise ValueError('adder census mismatch')
    if 'if (HAS_SFU != 0) begin : g_sfu' not in lane or not re.search(r'NSLOT\s*=\s*64',ckv) or 'for (s = 0; s < NSLOT; s = s + 1)' not in ckv:raise ValueError('conditional group mismatch')
    expected=dict(vector_lanes=256,full_lanes=1,sfu_only_lanes=63,light_lanes=192,base_qmul_instances=1280,base_qadd_instances=512,additional_sfu_den_adds=64,additional_sfu_exp_blocks=64)
    if record['counts']!=expected:raise ValueError('selected unrolled count mismatch')
    return expected
