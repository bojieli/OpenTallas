# Streamed to each host over one persistent ssh session; prints one JSON line per tick.
# Reads /proc, cgroupfs, `docker ps`/`docker inspect` (new containers only) and nvidia-smi.
# Every JOBS_EVERY ticks it also lists the host's job inventory (owner 2026-10-15: the monitor showed only closure-loop
# routes, so a host running ~100 ot-heavy units looked idle): ot-heavy scopes (cgroup memory/peak/limit/CPU, argv, cwd,
# tag), docker containers (cgroup memory/CPU, name, image, bind-mount sources), ot-heavy waiters (admission queue) and,
# on the coordinator, ot-run processes held by its load hold.  All from cgroupfs and /proc: no systemctl, no extra ssh.
import calendar, glob, json, os, re, shutil, subprocess, sys, time
IV = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
def stat():
    out = []
    for l in open('/proc/stat'):
        if not l.startswith('cpu'): break
        if l.startswith('cpu '): continue
        v = list(map(int, l.split()[1:9])); out.append((sum(v), v[3] + v[4]))
    return out
def docker_n():
    for cmd in (['docker', 'ps', '-q'], ['sudo', '-n', 'docker', 'ps', '-q']):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            if r.returncode == 0: return len(r.stdout.split())
        except Exception: pass
    return None
_GPU = {'t': -1e9, 'v': []}
def gpu():
    # nvidia-smi at most once a minute: each call logs NVRM 'Reset required' asserts on a wedged GPU (owner: no reset), which filled kern.log/syslog (10-12)
    if not shutil.which('nvidia-smi'): return []
    if time.time() - _GPU['t'] < 60: return _GPU['v']
    _GPU['t'] = time.time()
    try:
        r = subprocess.run(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu',
                            '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=4)
        g = []
        for l in r.stdout.splitlines():
            v = [x.strip() for x in l.split(',')]
            g.append(dict(name=v[0].replace('NVIDIA ', ''), util=float(v[1]), mem_used=float(v[2]) / 1024,
                          mem_total=float(v[3]) / 1024, power=float(v[4]), temp=float(v[5])))
        _GPU['v'] = g
        return g
    except Exception: return []
JOBS_EVERY = 3
HZ = os.sysconf('SC_CLK_TCK'); BOOT = time.time() - float(open('/proc/uptime').read().split()[0])
def rd(p, n=4096):
    try:
        with open(p, 'rb') as f: return f.read(n).decode('utf-8', 'replace')
    except OSError: return ''
def num(p):
    v = rd(p, 64).strip()
    return int(v) if v.isdigit() else None
def cpu_us(d):
    for l in rd(d + '/cpu.stat', 512).splitlines():
        if l.startswith('usage_usec'): return int(l.split()[1])
    return None
def argv(pid):
    return [a for a in rd('/proc/%s/cmdline' % pid, 2048).split('\0') if a]
def cwd(pid):
    try: return os.readlink('/proc/%s/cwd' % pid)
    except OSError: return ''
def pstat(pid):   # (comm, ppid, start epoch)
    s = rd('/proc/%s/stat' % pid, 1024); i = s.rfind(')')
    if i < 0: return None
    f = s[i + 2:].split()
    return s[s.find('(') + 1:i], int(f[1]), BOOT + int(f[19]) / HZ
_DK = {}   # container id -> inspect summary (inspected once)
_PCPU = {}  # cgroup dir -> (t, usage_usec)
def cg_stats(d, now):
    mem = num(d + '/memory.current'); peak = num(d + '/memory.peak'); mx = num(d + '/memory.max'); u = cpu_us(d)
    cpu = None; p = _PCPU.get(d)
    if u is not None:
        if p and now > p[0]: cpu = round(max(0, u - p[1]) / 1e6 / (now - p[0]), 2)
        _PCPU[d] = (now, u)
    g = lambda b: None if b is None else round(b / 2**30, 2)
    return dict(mem=g(mem), peak=g(peak), max=g(mx), cpu=cpu)
def docker_run(args, timeout=8):
    for pre in ([], ['sudo', '-n']):
        try:
            r = subprocess.run(pre + ['docker'] + args, capture_output=True, text=True, timeout=timeout)
            if r.returncode == 0: return r.stdout
        except Exception: pass
    return None
def jobs():
    now = time.time(); units = []; ctrs = []; waiters = []; held = []; seen = set()
    for d in glob.glob('/sys/fs/cgroup/user.slice/user-*.slice/user@*.service/app.slice/oth-*.scope'):
        seen.add(d); u = os.path.basename(d)[:-6]
        procs = rd(d + '/cgroup.procs', 256).split()
        if not procs: continue
        m = re.match(r'oth-(.+)-(\d+)-(\d+)$', u)
        pid = m.group(2) if m and m.group(2) in procs else procs[0]
        a = argv(pid); st = pstat(pid)
        par = argv(st[1]) if st else []
        tag = re.search(r'--tag (\S+)', ' '.join(par)); tag = tag and tag.group(1)
        units.append(dict(unit=u, user=m and m.group(1), start=int(m.group(3)) if m else (st and st[2]),
                          argv=' '.join(a)[:600], cwd=cwd(pid), tag=tag, nproc=len(procs), **cg_stats(d, now)))
    out = docker_run(['ps', '--no-trunc', '-q'])
    if out is not None:
        ids = out.split(); new = [i for i in ids if i not in _DK]
        if new:
            fmt = '{{.Id}}\t{{.Name}}\t{{.Config.Image}}\t{{.State.StartedAt}}\t{{range .Mounts}}{{.Source}} {{end}}\t{{json .Config.Cmd}}'
            for l in (docker_run(['inspect', '--format', fmt] + new[:60], 20) or '').splitlines():
                f = l.split('\t')
                if len(f) < 6: continue
                try: t0 = calendar.timegm(time.strptime(f[3][:19], "%Y-%m-%dT%H:%M:%S"))
                except ValueError: t0 = None
                _DK[f[0]] = dict(name=f[1].lstrip('/'), image=f[2], start=t0, mounts=f[4].split(), cmd=f[5][:300])
        for i in list(_DK):
            if i not in ids: del _DK[i]
        for i in ids:
            d = '/sys/fs/cgroup/system.slice/docker-%s.scope' % i; seen.add(d)
            ctrs.append(dict(_DK.get(i, dict(name=i[:12])), id=i[:12], **cg_stats(d, now)))
    for d in list(_PCPU):
        if d not in seen: del _PCPU[d]
    kids = {}; ot = []
    for pid in os.listdir('/proc'):
        if not pid.isdigit(): continue
        st = pstat(pid)
        if not st: continue
        if st[0] == 'ot-heavy': waiters.append((pid, st))
        elif st[0] == 'ot-run': ot.append((pid, st))
        elif st[0] == 'ssh': kids.setdefault(st[1], []).append(pid)
    wq = []
    for pid, st in waiters:
        s = ' '.join(argv(pid))
        mm = re.search(r'--mem (\S+)', s); tg = re.search(r'--tag (\S+)', s)
        wq.append(dict(pid=int(pid), start=round(st[2]), mem_req=mm and mm.group(1), tag=tg and tg.group(1),
                       argv=(s.split(' -- ', 1)[1] if ' -- ' in s else s)[:600], cwd=cwd(pid)))
    for pid, st in ot:   # coordinator: an ot-run with no ssh child carrying ot-heavy is held by the load hold
        if any('ot-heavy' in ' '.join(argv(k)) for k in kids.get(int(pid), [])): continue
        a = argv(pid); s = ' '.join(a); mm = re.search(r'--mem (\S+)', s)
        if '--status' in a or '--pick' in a or '--selftest' in a: continue
        held.append(dict(pid=int(pid), start=round(st[2]), mem_req=mm and mm.group(1),
                         argv=(s.split(' -- ', 1)[1] if ' -- ' in s else s)[:600], cwd=cwd(pid)))
    return dict(t=now, units=units, containers=ctrs if out is not None else None, waiters=wq, held=held)
prev = stat(); n = 0; dk = None; jb = None
while True:
    time.sleep(IV)
    cur = stat()
    cores = [round(100 * (1 - (ci - pi) / max(1, ct - pt))) for (ct, ci), (pt, pi) in zip(cur, prev)]
    prev = cur
    m = {}
    for l in open('/proc/meminfo'):
        k, v = l.split(':', 1); m[k] = int(v.split()[0])
    jb = None
    if n % JOBS_EVERY == 0:
        try: jb = jobs(); dk = None if jb['containers'] is None else len(jb['containers'])
        except Exception as e: jb = dict(error=str(e)[:200]); dk = docker_n()
    n += 1
    sys.stdout.write(json.dumps(dict(t=time.time(), cores=[max(0, min(100, c)) for c in cores],
        mem_total=m['MemTotal'] / 2**20, mem_avail=m['MemAvailable'] / 2**20,
        load=os.getloadavg()[0], docker=dk, gpu=gpu(), **({'jobs': jb} if jb else {}))) + '\n')
    sys.stdout.flush()
