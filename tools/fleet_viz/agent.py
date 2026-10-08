# Streamed to each host over one persistent ssh session; prints one JSON line per tick.
# Reads only /proc, `docker ps -q` and nvidia-smi. Never exports paths, args or names.
import json, os, shutil, subprocess, sys, time
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
def gpu():
    if not shutil.which('nvidia-smi'): return []
    try:
        r = subprocess.run(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu',
                            '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=4)
        g = []
        for l in r.stdout.splitlines():
            v = [x.strip() for x in l.split(',')]
            g.append(dict(name=v[0].replace('NVIDIA ', ''), util=float(v[1]), mem_used=float(v[2]) / 1024,
                          mem_total=float(v[3]) / 1024, power=float(v[4]), temp=float(v[5])))
        return g
    except Exception: return []
prev = stat(); n = 0; dk = None
while True:
    time.sleep(IV)
    cur = stat()
    cores = [round(100 * (1 - (ci - pi) / max(1, ct - pt))) for (ct, ci), (pt, pi) in zip(cur, prev)]
    prev = cur
    m = {}
    for l in open('/proc/meminfo'):
        k, v = l.split(':', 1); m[k] = int(v.split()[0])
    if n % 3 == 0: dk = docker_n()
    n += 1
    sys.stdout.write(json.dumps(dict(t=time.time(), cores=[max(0, min(100, c)) for c in cores],
        mem_total=m['MemTotal'] / 2**20, mem_avail=m['MemAvailable'] / 2**20,
        load=os.getloadavg()[0], docker=dk, gpu=gpu())) + '\n')
    sys.stdout.flush()
