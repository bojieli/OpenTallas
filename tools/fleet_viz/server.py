#!/usr/bin/env python3
"""OpenTallas live fleet visualisation: collector + HTTP/SSE server in one process.

One long-lived ssh session per host (ControlMaster socket, so other tools can
reuse it) runs agent.py, which streams a JSON line every POLL seconds. The
closure-loop job directory is rescanned every 10 s with an mtime cache.

Endpoints (bind 127.0.0.1:8765 by default):
  /                 the page            /api/fleet   JSON snapshot
  /api/stream       server-sent events  /landmask.js static map mask
Share-safe mode is the default: labels and generic categories only. `?safe=0`
adds real host aliases and block names, and is honoured only for direct
loopback requests that carry no proxy forwarding headers.
"""
import collections, datetime, json, os, pathlib, re, subprocess, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / 'fleet_hosts.json').read_text())
AGENT = (HERE / 'agent.py').read_text()
POLL = float(os.environ.get('FLEET_VIZ_POLL', '5'))
BIND = os.environ.get('FLEET_VIZ_BIND', '127.0.0.1')
PORT = int(os.environ.get('FLEET_VIZ_PORT', '8765'))
JOBS = pathlib.Path(os.environ.get('FLEET_VIZ_JOBS', os.path.expanduser('~/.local/state/closure_loop/jobs')))
CTL = pathlib.Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / 'fleet-viz-ssh'

def log(msg):
    line = '%s %s' % (datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), msg)
    print(line, flush=True)

# ---------------------------------------------------------------- hosts
class Host:
    def __init__(self, cfg):
        self.cfg = cfg; self.last = None; self.state = 'pending' if cfg.get('pending') else 'connecting'
        self.since = time.time(); self.lock = threading.Lock()
        threading.Thread(target=self.run, daemon=True, name='host-' + cfg['id']).start()

    def cmd(self):
        if self.cfg['ssh'] is None:
            return ['python3', '-u', '-c', AGENT, str(POLL)]
        return ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=3',
                '-o', 'ControlMaster=auto', '-o', 'ControlPath=%s/%%r@%%h:%%p' % CTL, '-o', 'ControlPersist=120',
                self.cfg['ssh'], 'exec nice -n 10 python3 -u - %s' % POLL]

    def run(self):
        backoff = 5
        while True:
            try:
                p = subprocess.Popen(self.cmd(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True)
                if self.cfg['ssh'] is not None:
                    p.stdin.write(AGENT); p.stdin.close()
                for line in p.stdout:
                    try: d = json.loads(line)
                    except ValueError: continue
                    with self.lock:
                        self.last = d; self.state = 'up'; backoff = 5
                p.wait()
            except Exception as e:
                log('host %s: %s' % (self.cfg['id'], e))
            with self.lock:
                if self.state == 'up' or self.last is None:
                    self.state = 'pending' if self.cfg.get('pending') and self.last is None else 'down'
            time.sleep(backoff); backoff = min(120, backoff * 2)

    def snap(self):
        with self.lock:
            d, st = self.last, self.state
        if d and time.time() - d['t'] > 4 * POLL + 10:
            st = 'stale'
        return st, d

# ---------------------------------------------------------------- closure loop
CATS = [('Qwen ROM', re.compile(r'qwen|^q[a-z]*_|^qfd|^qrom', re.I)),
        ('HBM accelerator', re.compile(r'hbm', re.I)),
        ('DeepSeek S81', re.compile(r's81|dsrom|dsfd|^ds[_-]|deepseek|wcol|v41', re.I))]

def category(job):
    s = job.get('spec', {})
    for key in (s.get('block', ''), job.get('name', ''), s.get('owner', '')):
        for name, rx in CATS:
            if rx.search(key or ''): return name
    return 'Other'

def parse_ts(s):
    try: return datetime.datetime.fromisoformat(s).timestamp()
    except Exception: return 0.0

class Closures:
    def __init__(self):
        self.cache = {}; self.data = {}; self.lock = threading.Lock()
        threading.Thread(target=self.run, daemon=True, name='closures').start()

    def scan(self):
        seen = set()
        for f in os.scandir(JOBS):
            if not f.name.endswith('.json'): continue
            seen.add(f.name)
            try: mt = f.stat().st_mtime
            except OSError: continue
            c = self.cache.get(f.name)
            if c and c[0] == mt: continue
            try: j = json.loads(open(f.path).read())
            except Exception: continue
            s = j.get('spec', {})
            self.cache[f.name] = (mt, dict(status=j.get('status'), host=j.get('host'), cat=category(j),
                                         block=s.get('block') or j.get('name'), updated=parse_ts(j.get('updated', ''))))
        for k in set(self.cache) - seen: del self.cache[k]
        jobs = [v for _, v in self.cache.values()]
        midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        counts = collections.Counter(j['status'] for j in jobs)
        running = collections.Counter(j['host'] for j in jobs if j['status'] == 'RUNNING')
        run_cat = collections.Counter(j['cat'] for j in jobs if j['status'] == 'RUNNING')
        closed = sorted((j for j in jobs if j['status'] == 'CLOSED'), key=lambda j: j['updated'])
        today = [j for j in closed if j['updated'] >= midnight]
        day_ago = time.time() - 86400
        with self.lock:
            self.data = dict(counts=dict(counts), running_by_host=dict(running), running_by_cat=dict(run_cat),
                             closed_today=len({j['block'] for j in today}), closed_today_jobs=len(today),
                             closed_24h_by_cat=dict(collections.Counter(j['cat'] for j in closed if j['updated'] >= day_ago)),
                             closed_total=len(closed), recent=closed[-30:][::-1])

    def run(self):
        while True:
            try: self.scan()
            except Exception as e: log('closure scan: %s' % e)
            time.sleep(10)

# ---------------------------------------------------------------- snapshot
HOSTS = [Host(h) for h in CFG['hosts']]
CLOSURES = Closures()
HISTORY = collections.deque(maxlen=180)  # 15 min at 5 s
_snap = {}; _cond = threading.Condition()

def build(safe):
    hosts = []; alias_to_label = {h.cfg['id']: h.cfg['label'] for h in HOSTS}
    with CLOSURES.lock: cl = dict(CLOSURES.data)
    tot = dict(cores=0, busy=0.0, mem_total=0.0, mem_used=0.0, docker=0, hosts_up=0)
    for h in HOSTS:
        st, d = h.snap(); c = h.cfg
        e = dict(label=c['label'], kind=c['kind'], region=c['region'], state=st,
                 routes=cl.get('running_by_host', {}).get(c['id'], 0))
        if not safe: e['alias'] = c['id']
        if d and st in ('up', 'stale'):
            used = d['mem_total'] - d['mem_avail']
            e.update(cores=d['cores'], mem_total=round(d['mem_total'], 1), mem_used=round(used, 1),
                     load=round(d['load'], 1), docker=d['docker'],
                     gpu=[dict(name=g['name'], util=g['util'], mem_used=round(g['mem_used'], 1),
                               mem_total=round(g['mem_total'], 1), power=round(g['power']), temp=g['temp']) for g in d.get('gpu', [])])
            if st == 'up':
                tot['hosts_up'] += 1; tot['cores'] += len(d['cores']); tot['busy'] += sum(d['cores']) / 100
                tot['mem_total'] += d['mem_total']; tot['mem_used'] += used; tot['docker'] += d['docker'] or 0
        hosts.append(e)
    recent = []
    for j in cl.get('recent', []):
        r = dict(t=j['updated'], cat=j['cat'], host=alias_to_label.get(j['host'], 'fleet'))
        if not safe: r['block'] = j['block']
        recent.append(r)
    counts = cl.get('counts', {})
    return dict(t=time.time(), poll=POLL, safe=safe, regions=CFG['regions'], hosts=hosts,
                totals=dict(tot, busy=round(tot['busy'], 1), mem_total=round(tot['mem_total'], 1), mem_used=round(tot['mem_used'], 1)),
                loop=dict(running=counts.get('RUNNING', 0), queued=counts.get('QUEUED', 0) + counts.get('READY', 0),
                          closed_today=cl.get('closed_today', 0), closed_today_jobs=cl.get('closed_today_jobs', 0),
                          closed_total=cl.get('closed_total', 0), running_by_cat=cl.get('running_by_cat', {}),
                          closed_24h_by_cat=cl.get('closed_24h_by_cat', {})),
                history=list(HISTORY), recent=recent)

def ticker():
    while True:
        time.sleep(POLL)
        try:
            s1 = build(True)
            HISTORY.append([round(s1['t']), s1['totals']['busy'], s1['totals']['cores'], s1['loop']['running']])
            s1['history'] = list(HISTORY)
            s0 = build(False); s0['history'] = s1['history']
            with _cond:
                _snap[True] = json.dumps(s1, separators=(',', ':')); _snap[False] = json.dumps(s0, separators=(',', ':'))
                _cond.notify_all()
        except Exception as e:
            log('snapshot: %s' % e)

# ---------------------------------------------------------------- http
STATIC = {'/': ('index.html', 'text/html; charset=utf-8'), '/index.html': ('index.html', 'text/html; charset=utf-8'),
          '/landmask.js': ('landmask.js', 'application/javascript')}

class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def safe(self, q):
        local = self.client_address[0] in ('127.0.0.1', '::1')
        proxied = any(self.headers.get(k) for k in ('X-Forwarded-For', 'X-Real-IP', 'Forwarded', 'CF-Connecting-IP'))
        return not (q.get('safe', ['1'])[0] == '0' and local and not proxied)

    def send(self, code, body, ctype):
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store'); self.send_header('X-Content-Type-Options', 'nosniff'); self.end_headers()
        if self.command != 'HEAD': self.wfile.write(body)

    def do_HEAD(self): self.do_GET()

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query); safe = self.safe(q)
        if u.path in STATIC:
            name, ctype = STATIC[u.path]
            return self.send(200, (HERE / name).read_bytes(), ctype)
        if u.path == '/api/fleet':
            with _cond: body = _snap.get(safe)
            if body is None: return self.send(503, b'{"warming":true}', 'application/json')
            return self.send(200, body.encode(), 'application/json')
        if u.path == '/api/stream':
            self.send_response(200); self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store'); self.send_header('X-Accel-Buffering', 'no'); self.end_headers()
            self.close_connection = True
            try:
                with _cond: body = _snap.get(safe)
                while True:
                    if body: self.wfile.write(b'data: ' + body.encode() + b'\n\n'); self.wfile.flush()
                    with _cond:
                        _cond.wait(POLL * 3); body = _snap.get(safe)
            except (BrokenPipeError, ConnectionResetError, OSError):
                return
        self.send(404, b'not found', 'text/plain')

    def log_message(self, *a): pass

class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

if __name__ == '__main__':
    CTL.mkdir(mode=0o700, parents=True, exist_ok=True)
    threading.Thread(target=ticker, daemon=True, name='ticker').start()
    log('fleet-viz serving http://%s:%d (%d hosts, poll %gs)' % (BIND, PORT, len(HOSTS), POLL))
    Server((BIND, PORT), H).serve_forever()
