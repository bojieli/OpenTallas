#!/usr/bin/env python3
"""OpenTallas live fleet visualisation: collector + HTTP/SSE server in one process.

One long-lived ssh session per host (ControlMaster socket, so other tools can
reuse it) runs agent.py, which streams a JSON line every POLL seconds. The
closure-loop job directory is rescanned every 10 s with an mtime cache.

Endpoints (bind 127.0.0.1:8765 by default):
  /                 the page            /api/fleet   JSON snapshot
  /replay?from=&to=&speed=   the same page playing a recorded window (/api/replay serves the data)
  /api/elements     per-element (block) closure status table (elements.py; share-safe: summary counts only)
  /api/stream       server-sent events (latest history point only; /api/fleet
                    carries the full 60-minute history)
Internal view is the default: real host aliases, job and block names, slacks
and the live job table (/api/jobs). `?safe=1` gives the share-safe view (labels
and generic categories only); requests that arrive through a proxy (forwarding
headers) or from a non-loopback address are always served share-safe.
"""
import collections, datetime, json, os, signal, pathlib, re, subprocess, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import recorder, elements, explorer, coverage

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads(pathlib.Path(os.environ.get('FLEET_VIZ_HOSTS', HERE / 'fleet_hosts.json')).read_text())
AGENT = (HERE / 'agent.py').read_text()
POLL = float(os.environ.get('FLEET_VIZ_POLL', '5'))
BIND = os.environ.get('FLEET_VIZ_BIND', '127.0.0.1')
PORT = int(os.environ.get('FLEET_VIZ_PORT', '8765'))
STATUS_MD = pathlib.Path(os.environ.get('FLEET_VIZ_STATUS_MD', '/tmp/claude-review-20261003/CLOSURE_LOOP_STATUS.md'))
LEDGER = pathlib.Path(os.environ.get('FLEET_VIZ_LEDGER', '/tmp/claude-review-20261003/CLOSURE_LOOP_LEDGER.md'))
VERDICT_RX = re.compile(r'^(CLOSED|NOT CLOSED|NEEDS_RTL|NEEDS_HUMAN|NEEDS_BUDGET|INVALID|REFUSED|FAILED|SMOKE_OK)\b')
VERDICT_ST = {'CLOSED', 'NOT CLOSED', 'NEEDS_RTL', 'NEEDS_HUMAN', 'NEEDS_BUDGET', 'INVALID', 'REFUSED', 'FAILED', 'SMOKE_OK'}
SLACK_RX = re.compile(r'SS ([+-]?[\d.]+|None) / FF ([+-]?[\d.]+|None) ps[ /]*(?:DRC (\d+))?')
ACTIVE = ('RUNNING', 'SYNC', 'ECO', 'READY', 'QUEUED')
JOBS = pathlib.Path(os.environ.get('FLEET_VIZ_JOBS', os.path.expanduser('~/.local/state/closure_loop/jobs')))
CTL = pathlib.Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / 'fleet-viz-ssh'
START = time.time()
# freshness limits (s): a source older than this, or one whose last read failed, is flagged in every payload's 'fresh'
FRESH = dict(host=120, loop_status=180, jobs=60, elements=600, explorer=300)

def log(msg):
    line = '%s %s' % (datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), msg)
    print(line, flush=True)

# ---------------------------------------------------------------- hosts
class Host:
    def __init__(self, cfg):
        self.cfg = cfg; self.last = None; self.state = 'pending' if cfg.get('pending') else 'connecting'
        self.since = time.time(); self.lock = threading.Lock()
        self.ok_t = None; self.err = None; self.err_t = None; self.errq = collections.deque(maxlen=4)   # last sample (local receive time), last probe failure
        threading.Thread(target=self.run, daemon=True, name='host-' + cfg['id']).start()

    def cmd(self):
        if self.cfg.get('cmd'): return list(self.cfg['cmd']) + [str(POLL)]   # test hook: a local stand-in probe
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
                                     stderr=subprocess.PIPE, text=True, errors='replace')
                threading.Thread(target=self._drain, args=(p.stderr,), daemon=True).start()
                if self.cfg['ssh'] is not None and not self.cfg.get('cmd'):
                    p.stdin.write(AGENT)
                p.stdin.close()
                for line in p.stdout:
                    try: d = json.loads(line)
                    except ValueError: continue
                    with self.lock:
                        self.last = d; self.state = 'up'; self.ok_t = time.time(); self.err = None; backoff = 5
                rc = p.wait(); time.sleep(0.2)
                with self.lock:
                    self.err = 'probe exited (rc %s)%s' % (rc, (': ' + self.errq[-1]) if self.errq else ''); self.err_t = time.time()
            except Exception as e:
                log('host %s: %s' % (self.cfg['id'], e))
                with self.lock: self.err = 'probe failed: %s' % e; self.err_t = time.time()
            with self.lock:
                if self.state == 'up' or self.last is None:
                    self.state = 'pending' if self.cfg.get('pending') and self.last is None else 'down'
            time.sleep(backoff); backoff = min(120, backoff * 2)

    def _drain(self, f):
        for line in f:
            line = line.strip()
            if line: self.errq.append(line[:200])

    def snap(self):
        with self.lock:
            d, st, ok = self.last, self.state, self.ok_t
        if st == 'up' and ok and time.time() - ok > 4 * POLL + 10:   # probe alive but silent (local receive time: no clock skew)
            st = 'stale'
        return st, d

    def fresh(self, now, safe):
        st, _ = self.snap()
        with self.lock: ok, err = self.ok_t, self.err
        pending = bool(self.cfg.get('pending')) and ok is None
        age = now - (ok or self.since)
        flagged = not pending and (st in ('down', 'stale') or (st == 'connecting' and age > FRESH['host']) or age > FRESH['host'])
        why = None
        if flagged:
            why = ('unreachable' if st == 'down' else 'no sample for %ds' % age if ok else 'never connected') + \
                  ('' if safe or not err else ' (%s)' % err)
        return dict(label=self.cfg['label'] if safe else self.cfg.get('name', self.cfg['id']), state=st, t=ok,
                    age=None if ok is None else round(age, 1), limit=FRESH['host'], ok=not flagged, pending=pending, error=why)

# ---------------------------------------------------------------- closure loop
CATS = [('Qwen ROM', re.compile(r'qwen|^q[a-z]*_|^qfd|^qrom', re.I)),
        ('HBM accelerator', re.compile(r'hbm', re.I)),
        ('DeepSeek ROM', re.compile(r's81|dsrom|dsfd|^ds[_-]|deepseek|wcol|v41', re.I))]

def category(job):
    s = job.get('spec', {})
    for key in (s.get('block', ''), job.get('name', ''), s.get('owner', '')):
        for name, rx in CATS:
            if rx.search(key or ''): return name
    return 'Other'

def parse_ts(s):
    try: return datetime.datetime.fromisoformat(s).timestamp()
    except Exception: return 0.0

def summarise(j):
    s = j.get('spec', {}); m = j.get('metrics') or {}; ev = j.get('events') or []
    tt = s.get('route_corner') == 'TC' or m.get('setup_corner') == 'tt'
    last = ev[-1] if ev else ''
    if re.match(r'\d{4}-\d\d-\d\dT\S+ ', last): last = last.split(' ', 1)[1]
    since = parse_ts(j.get('stage_started') or j.get('wait_since') or j.get('created') or '')
    return dict(name=j.get('name'), status=j.get('status'), host=j.get('host'), cat=category(j),
                block=s.get('block') or j.get('name'), updated=parse_ts(j.get('updated', '')),
                stage=j.get('stage_key') or '', since=since, wait=(j.get('wait') or '')[:300],
                reason=(j.get('reason') or '')[:300], event=last[:300], target=('TT' if tt else 'SS') + '>=0 / FF>=0',
                setup=m.get('ss_ps'), setup_corner='TT' if tt else 'SS', hold=m.get('ff_ps'), drc=m.get('drc'),
                into=s.get('merge_target') or '', owner=s.get('owner') or '', attempt=j.get('attempt'))

def status_md():
    try: txt = STATUS_MD.read_text()
    except OSError: return dict(head=[], fleet=[], terminal=[], mtime=0)
    sec = 'head'; out = dict(head=[], fleet=[], terminal=[], mtime=STATUS_MD.stat().st_mtime)
    for line in txt.splitlines():
        if line.startswith('## '):
            sec = 'fleet' if line[3:].startswith('Fleet') else 'terminal' if 'terminal' in line else 'skip'
            if sec == 'fleet': out['fleet'].append(line[3:])
            continue
        if line.strip() and sec in out: out[sec].append(line.lstrip('-# ').strip())
    out['terminal'] = out['terminal'][:60]
    return out

def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

CHECKS_RX = re.compile(r'(?<![\w-])checks? failed:\s*([A-Za-z_][\w.]*(?:\s*,\s*[A-Za-z_][\w.]*)*)')

def classify(status, setup, hold, text):
    if status in ('CLOSED', 'SMOKE_OK'): return 'closed'
    if CHECKS_RX.search(text) and not ((setup is not None and setup < 0) or (hold is not None and hold < 0)):
        return 'check'   # slacks met, a sign-off check failed: not a timing failure
    if (setup is not None and setup < 0) or (hold is not None and hold < 0) or status == 'NEEDS_BUDGET': return 'timing'
    return 'flow'

def verdict(t, name, block, status, text, host, detail, job):
    m = SLACK_RX.search(text)
    setup, hold, drc = (_num(m.group(1)), _num(m.group(2)), _num(m.group(3))) if m else (None, None, None)
    if job and job['status'] == status and job.get('setup') is not None and setup is None:
        setup, hold, drc = job['setup'], job['hold'], job['drc']
    tt = bool(job and job['setup_corner'] == 'TT') or bool(re.search(r'(-|_)(tt|tc)(-|_|$)', name or ''))
    why = text[len(status):].lstrip(': ')
    if status == 'CLOSED': why = re.sub(r'^SS \S+ / FF \S+ ps DRC \d+ \|?\s*', '', why)
    return dict(t=t, name=name, block=block, status=status, why=why[:400], detail=(detail or '')[:300], host=host,
                setup=setup, hold=hold, drc=drc, corner='TT' if tt else 'SS', target=('TT' if tt else 'SS') + '>=0 / FF>=0',
                kind=classify(status, setup, hold, text), check=(lambda m: m.group(1).strip()[:160] if m else '')(CHECKS_RX.search(text)), cat=job['cat'] if job else 'Other')

class Closures:
    def __init__(self):
        self.cache = {}; self.data = {}; self.active = []; self.verdicts = []; self.vver = 0
        self.lmt = None; self.lrows = []; self.lock = threading.Lock(); self.scan_t = None; self.err = None
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
            self.cache[f.name] = (mt, summarise(j))
        for k in set(self.cache) - seen: del self.cache[k]
        jobs = [v for _, v in self.cache.values()]
        midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        counts = collections.Counter(j['status'] for j in jobs)
        running = collections.Counter(j['host'] for j in jobs if j['status'] == 'RUNNING')
        run_cat = collections.Counter(j['cat'] for j in jobs if j['status'] == 'RUNNING')
        closed = sorted((j for j in jobs if j['status'] == 'CLOSED'), key=lambda j: j['updated'])
        today = [j for j in closed if j['updated'] >= midnight]
        now = time.time(); day_ago = now - 86400
        hour0 = (int(now) // 3600) * 3600   # 24 hourly bins, the last one is the current hour
        bins = {name: [0] * 24 for name, _ in CATS + [('Other', None)]}
        for j in closed:
            k = 23 - (hour0 - (int(j['updated']) // 3600) * 3600) // 3600
            if 0 <= k < 24: bins[j['cat']][k] += 1
        self.scan_verdicts(now)
        active = sorted((j for j in jobs if j['status'] in ACTIVE), key=lambda j: (j['host'] or '~', j['name']))
        with self.lock:
            self.active = active
            self.data = dict(counts=dict(counts), running_by_host=dict(running), running_by_cat=dict(run_cat),
                             closed_today=len({j['block'] for j in today}), closed_today_jobs=len(today),
                             closed_24h_by_cat=dict(collections.Counter(j['cat'] for j in closed if j['updated'] >= day_ago)),
                             closed_total=len(closed), recent=closed[-30:][::-1],
                             closed_hourly=dict(start=hour0 - 23 * 3600, bins={k: v for k, v in bins.items() if any(v)}))

    def scan_verdicts(self, now):
        try: mt = LEDGER.stat().st_mtime
        except OSError: mt = None
        if mt != self.lmt:   # (t, name, block, status, text, host, detail) from the ledger verdict lines
            rows = []
            try: lines = LEDGER.read_text(errors='replace').splitlines()
            except OSError: lines = []
            for i, line in enumerate(lines):
                if not line.startswith('- 20'): continue
                f = line[2:].split(' | ')
                if len(f) < 4: continue
                last = f[-1] if ':/' in f[-1] else ''
                text = ' | '.join(f[3:-1] if last else f[3:]).strip()
                mm = VERDICT_RX.match(text)
                if not mm: continue
                det = lines[i + 1].strip()[7:].strip() if i + 1 < len(lines) and lines[i + 1].lstrip().startswith('detail:') else ''
                rows.append((parse_ts(f[0]), f[1], f[2].split(' @ ')[0], mm.group(1), text, last.split(':', 1)[0], det))
            self.lmt, self.lrows = mt, rows
        byname = {j['name']: j for _, j in self.cache.values()}
        seen = {(r[1], r[3]) for r in self.lrows}
        out = [verdict(*r, byname.get(r[1])) for r in self.lrows]
        for j in byname.values():   # final states the ledger does not carry
            if j['status'] in VERDICT_ST and (j['name'], j['status']) not in seen:
                out.append(verdict(j['updated'], j['name'], j['block'], j['status'],
                                   j['status'] + ': ' + (j['reason'] or ''), j['host'] or '', '', j))
        out.sort(key=lambda v: -v['t'])
        day = now - 86400
        out = [v for i, v in enumerate(out) if i < 200 or v['t'] >= day][:600]
        key = hash(tuple((v['t'], v['name'], v['status']) for v in out))   # any added/removed verdict bumps vver
        with self.lock:
            if key != getattr(self, '_vkey', None): self._vkey = key; self.vver += 1
            self.verdicts = out

    def run(self):
        while True:
            try:
                self.scan(); self.scan_t = time.time(); self.err = None
            except Exception as e:
                log('closure scan: %s' % e); self.err = '%s: %s' % (type(e).__name__, e)
            time.sleep(10)

# ---------------------------------------------------------------- snapshot
HOSTS = [Host(h) for h in CFG['hosts']]
CLOSURES = Closures()
HIST_SPAN = 3600
HISTORY = collections.deque(maxlen=int(HIST_SPAN / POLL) + 2)
HIST_FILE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz'))) / 'history.json'
HIST_HOSTS = [h['label'] for h in CFG['hosts']]
try:   # survive restarts: reload samples still inside the window
    _h = json.loads(HIST_FILE.read_text())
    if _h.get('hosts') == HIST_HOSTS:
        HISTORY.extend(x for x in _h['rows'] if x[0] > time.time() - HIST_SPAN and len(x) == 6 and x[4] > 0)
except Exception:
    pass
_snap = {}; _cond = threading.Condition()
_SSH = {h['id']: h['ssh'] for h in CFG['hosts']}
ELEMENTS = elements.Elements(JOBS, os.environ.get('FLEET_VIZ_REPO', '/home/ubuntu/OpenTallas'), HIST_FILE.parent,
                             lambda host: _SSH.get(host, host), CTL,
                             os.environ.get('FLEET_VIZ_ELEMENTS_MD', '/home/ubuntu/claude-takeover-20261007/ELEMENTS.md'), log=log)
EXPLORER = explorer.Explorer(os.environ.get('FLEET_VIZ_REPO', '/home/ubuntu/OpenTallas'), HIST_FILE.parent, JOBS, ELEMENTS, log=log)

def _src(t, limit, now, err=None, label=None, warm=False):
    """one freshness record: t = last good (server epoch), flagged when the read failed or t is older than limit"""
    age = None if t is None else now - t
    flagged = bool(err) or (age is None and not warm) or (age is not None and age > limit)
    why = err if err else None if not flagged else 'never read' if age is None else 'last update %ds ago (limit %ds)' % (age, limit)
    return dict(label=label, t=t, age=None if age is None else round(age, 1), limit=limit, ok=not flagged, error=why)

def fresh_block(safe, now=None, explorer=False, coverage=None):
    """per-source freshness carried by every API payload (hosts, closure-loop status file, jobs scan, element registry)"""
    now = time.time() if now is None else now; warm = now - START < 90
    src = {}
    for h in HOSTS: src['host:' + h.cfg['id'] if not safe else 'host:' + h.cfg['label']] = h.fresh(now, safe)
    try: mt = STATUS_MD.stat().st_mtime; e = None
    except OSError as x: mt = None; e = 'status file unreadable' if safe else 'status file unreadable (%s)' % x.strerror
    src['loop_status'] = _src(mt, FRESH['loop_status'], now, e, 'closure-loop status file')
    src['jobs'] = _src(CLOSURES.scan_t, FRESH['jobs'], now, CLOSURES.err and ('scan failed' if safe else 'scan failed: ' + CLOSURES.err),
                       'closure-loop jobs scan', warm)
    et = ELEMENTS.data.get('t') or None; ee = getattr(ELEMENTS, 'err', None)
    src['elements'] = _src(et, FRESH['elements'], now, ee and ('element scan failed' if safe else 'element scan failed: ' + ee),
                           'element registry', warm or now - START < 180)
    if explorer:
        src['explorer'] = _src(EXPLORER.meta_t or None, FRESH['explorer'], now, None, 'explorer map', now - START < 300)
    if coverage is not None:
        src['coverage'] = _src(now, 1e9, now, coverage or None, 'coverage matrix')
    return dict(sources=src, flagged=sorted(k for k, v in src.items() if not v['ok']))

def stamp(o, safe, **kw):
    """add generated_at / sent_at / fresh to a per-request payload (returns a new dict)"""
    now = time.time()
    return dict(o, generated_at=now, sent_at=now, fresh=fresh_block(safe, now, **kw))

def build(safe):
    hosts = []; alias_to_label = {h.cfg['id']: h.cfg['label'] if safe else h.cfg.get('name', h.cfg['id']) for h in HOSTS}
    with CLOSURES.lock: cl = dict(CLOSURES.data)
    tot = dict(cores=0, busy=0.0, mem_total=0.0, mem_used=0.0, docker=0, hosts_up=0)
    for h in HOSTS:
        st, d = h.snap(); c = h.cfg
        e = dict(label=c['label'] if safe else c.get('name', c['id']), kind=c['kind'], region=c['region'], state=st,
                 routes=cl.get('running_by_host', {}).get(c['id'], 0))
        if not safe: e['alias'] = c['id']
        e.update(t=h.ok_t, error=h.err if not safe else None)   # last good sample (server epoch), last probe failure
        if d and st == 'up':   # a stale or unreachable host carries no numbers: the page must not show old ones as live
            used = d['mem_total'] - d['mem_avail']
            e.update(cores=d['cores'], mem_total=round(d['mem_total'], 1), mem_used=round(used, 1),
                     load=round(d['load'], 1), docker=d['docker'],
                     gpu=[dict(name=g['name'], util=g['util'], mem_used=round(g['mem_used'], 1),
                               mem_total=round(g['mem_total'], 1), power=round(g['power']), temp=g['temp']) for g in d.get('gpu', [])])
            tot['hosts_up'] += 1; tot['cores'] += len(d['cores']); tot['busy'] += sum(d['cores']) / 100
            tot['mem_total'] += d['mem_total']; tot['mem_used'] += used; tot['docker'] += d['docker'] or 0
        hosts.append(e)
    recent = []
    for j in cl.get('recent', []):
        r = dict(t=j['updated'], cat=j['cat'], host=alias_to_label.get(j['host'], 'fleet'))
        if not safe:
            r.update({k: j[k] for k in ('block', 'name', 'setup', 'setup_corner', 'hold', 'drc', 'target', 'into')})
        recent.append(r)
    counts = cl.get('counts', {})
    now = time.time()
    return dict(t=now, generated_at=now, fresh=fresh_block(safe, now), poll=POLL, safe=safe, regions=CFG['regions'], hosts=hosts,
                totals=dict(tot, busy=round(tot['busy'], 1), mem_total=round(tot['mem_total'], 1), mem_used=round(tot['mem_used'], 1)),
                loop=dict(running=counts.get('RUNNING', 0), queued=counts.get('QUEUED', 0) + counts.get('READY', 0),
                          closed_today=cl.get('closed_today', 0), closed_today_jobs=cl.get('closed_today_jobs', 0),
                          closed_total=cl.get('closed_total', 0), running_by_cat=cl.get('running_by_cat', {}),
                          closed_24h_by_cat=cl.get('closed_24h_by_cat', {}),
                          closed_hourly=cl.get('closed_hourly', dict(start=0, bins={}))),
                vver=None if safe else CLOSURES.vver, hist_hosts=HIST_HOSTS if safe else [h.cfg.get('name', h.cfg['id']) for h in HOSTS], history=list(HISTORY), recent=recent)

# ---------------------------------------------------------------- recording (recorder.py; replay + export)
REC_DIR = pathlib.Path(os.environ.get('FLEET_VIZ_RECORDINGS', os.path.expanduser('~/.local/state/fleet-viz/recordings')))
_rec = dict(loop=None, recent=None, md=None, jobs={}, jobs_full=0, vkeys=set(), elem=None, elem_key=None, elem_t=0)
ELEM_EVERY = 300   # element table: on a status change, else every 5 min

def _rec_meta():
    return dict(k='meta', t=time.time(), poll=POLL, regions=CFG['regions'],
                hosts=[dict(id=h.cfg['id'], name=h.cfg.get('name', h.cfg['id']), label=h.cfg['label'], kind=h.cfg['kind'],
                            region=h.cfg['region']) for h in HOSTS])

def _rec_keyframes(t):
    with CLOSURES.lock: act, vs = list(CLOSURES.active), list(CLOSURES.verdicts)
    _rec.update(jobs={j['name']: j for j in act}, jobs_full=t, vkeys={(v['t'], v['name'], v['status']) for v in vs})
    out = [_rec_meta(), dict(k='jobs', t=t, full=1, rows=act), dict(k='verd', t=t, full=1, rows=vs)]
    for k in ('loop', 'recent', 'md', 'elem'):
        if _rec[k] is not None: out.append(_rec[k])
    return out

RECORDER = None
_same_job = lambda x, y: y is not None and all(x[k] == y.get(k) for k in x if k != 'updated')   # 'updated' is a heartbeat

def record(s0):
    global RECORDER
    t = round(s0['t'], 1); recs = []
    if RECORDER is None: RECORDER = recorder.Recorder(REC_DIR, _rec_keyframes); _rec['jobs_full'] = -1
    recs.append(dict(k='s', t=t, h=[[h['state'], recorder.pack_cores(h['cores']) if h.get('cores') else None,
                                     h.get('mem_total'), h.get('mem_used'), h.get('load'), h.get('docker'),
                                     h.get('gpu') or None, h['routes']] for h in s0['hosts']]))
    for k, val in (('loop', s0['loop']), ('recent', s0['recent']), ('md', status_md())):
        if _rec[k] is None or _rec[k][k if k != 'recent' else 'rows'] != val:
            _rec[k] = {'k': k, 't': t, ('rows' if k == 'recent' else k): val}; recs.append(_rec[k])
    with CLOSURES.lock: act, vs = list(CLOSURES.active), list(CLOSURES.verdicts)
    cur = {j['name']: j for j in act}
    if _rec['jobs_full'] < 0: _rec.update(jobs=cur, jobs_full=t)   # first sample: the file-opening keyframe carries the table
    if t - _rec['jobs_full'] >= recorder.JOB_KEYFRAME:
        recs.append(dict(k='jobs', t=t, full=1, rows=act)); _rec['jobs_full'] = t
    else:
        up = [j for n, j in cur.items() if not _same_job(j, _rec['jobs'].get(n))]; rm = [n for n in _rec['jobs'] if n not in cur]
        if up or rm: recs.append(dict(k='jobs', t=t, up=up, rm=rm))
    _rec['jobs'] = cur
    new = [v for v in vs if (v['t'], v['name'], v['status']) not in _rec['vkeys']]
    if new:
        recs.append(dict(k='verd', t=t, add=new)); _rec['vkeys'].update((v['t'], v['name'], v['status']) for v in new)
    ed = ELEMENTS.snapshot()
    if ed['rows']:
        ek = elements.change_key(ed)
        if ek != _rec['elem_key'] or t - _rec['elem_t'] >= ELEM_EVERY:
            _rec.update(elem=dict(k='elem', t=t, d=ed), elem_key=ek, elem_t=t); recs.append(_rec['elem'])
    RECORDER.write(t, recs)

def ticker():
    n = 0
    while True:
        time.sleep(POLL)
        try:
            s1 = build(True)
            # history row: t, busy threads, threads, routes running, fleet RAM used GB, per-host RAM used GB
            mem = [h.get('mem_used', 0) if h['state'] == 'up' else 0 for h in s1['hosts']]
            if not any(h['state'] == 'connecting' for h in s1['hosts']):   # skip the start-up ramp
              HISTORY.append([round(s1['t']), s1['totals']['busy'], s1['totals']['cores'], s1['loop']['running'],
                              s1['totals']['mem_used'], mem])
            s0 = build(False)
            if not any(h['state'] == 'connecting' for h in s1['hosts']):
                try: record(s0)
                except Exception as e: log('record: %s' % e)
            full = {}; live = {}
            for k, s in ((True, s1), (False, s0)):
                s['history'] = list(HISTORY); full[k] = json.dumps(s, separators=(',', ':'))
                s['history'] = list(HISTORY)[-1:]; s['delta'] = True; live[k] = json.dumps(s, separators=(',', ':'))
            with _cond:
                _snap.update(full=full, live=live); _cond.notify_all()
            n += 1
            if n % 12 == 0:
                HIST_FILE.parent.mkdir(parents=True, exist_ok=True)
                tmp = HIST_FILE.with_suffix('.tmp'); tmp.write_text(json.dumps(dict(hosts=HIST_HOSTS, rows=list(HISTORY))))
                tmp.replace(HIST_FILE)
        except Exception as e:
            log('snapshot: %s' % e)

# ---------------------------------------------------------------- http
STATIC = {'/': ('index.html', 'text/html; charset=utf-8'), '/index.html': ('index.html', 'text/html; charset=utf-8'),
          '/replay': ('index.html', 'text/html; charset=utf-8'), '/explorer': ('explorer.html', 'text/html; charset=utf-8'),
          '/explorer.html': ('explorer.html', 'text/html; charset=utf-8'),
          '/explorer.js': ('explorer.js', 'text/javascript; charset=utf-8'),
          '/explorer_story.js': ('explorer_story.js', 'text/javascript; charset=utf-8'),
          '/fv_stale.js': ('fv_stale.js', 'text/javascript; charset=utf-8')}
# /explorer/token/...: mount point for the token-path views (a separate stream ships them into explorer/token/)
TOKEN_DIR = HERE / 'explorer' / 'token'
TOKEN_TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
               '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp'}
TOKEN_PLACEHOLDER = (b'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                     b'<title>Token path</title><body style="background:#05070d;color:#e8eefc;font:15px system-ui;padding:32px">'
                     b'<h1 style="font-size:20px">Token path views</h1><p>Not installed yet: the token-path stream mounts its views '
                     b'here (tools/fleet_viz/explorer/token/).</p><p><a style="color:#5ee7ff" href="/explorer">&larr; Chip Explorer</a></p>')
# /explorer/coverage/...: the coverage matrix view (results/arch/coverage_20261008 ledgers, joined with /api/elements)
COVERAGE_DIR = HERE / 'explorer' / 'coverage'
COVERAGE = coverage.Coverage(os.environ.get('FLEET_VIZ_REPO', '/home/ubuntu/OpenTallas'), ELEMENTS, TOKEN_DIR, log=log)

def with_sent(body):
    """a pre-serialised snapshot plus sent_at: the page measures generated_at against the server's own clock"""
    return b'{"sent_at":%.3f,' % time.time() + body.encode()[1:]

class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def safe(self, q):
        local = self.client_address[0] in ('127.0.0.1', '::1')
        proxied = any(self.headers.get(k) for k in ('X-Forwarded-For', 'X-Real-IP', 'Forwarded', 'CF-Connecting-IP'))
        return q.get('safe', ['0'])[0] == '1' or not local or proxied

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
            with _cond: body = _snap.get('full', {}).get(safe)
            if body is None: return self.send(503, json.dumps(stamp(dict(warming=True), safe)).encode(), 'application/json')
            return self.send(200, with_sent(body), 'application/json')
        if u.path == '/api/replay':
            try:
                now = time.time(); t1 = recorder.parse_time(q.get('to', ['now'])[0], now)
                t0 = recorder.parse_time(q.get('from', ['-30m'])[0], t1 if q.get('from', [''])[0].startswith('-') else now)
                if t1 - t0 > 7 * 86400 or t1 <= t0: raise ValueError('window must be 0 < span <= 7 days')
                pkg = recorder.load_window(REC_DIR, t0, t1, safe=safe, max_frames=int(q.get('max', ['3000'])[0]))
            except Exception as e:
                return self.send(400, json.dumps(dict(error=str(e))).encode(), 'application/json')
            if pkg is None: return self.send(404, b'{"error":"no recording in that window"}', 'application/json')
            return self.send(200, json.dumps(pkg, separators=(',', ':')).encode(), 'application/json')
        if u.path == '/api/jobs':
            if safe: return self.send(403, b'{"safe":true}', 'application/json')
            lab = {h.cfg['id']: h.cfg.get('name', h.cfg['id']) for h in HOSTS}
            with CLOSURES.lock: act = list(CLOSURES.active)
            rows = [dict(j, label=lab.get(j['host'], j['host'] or 'unplaced')) for j in act]
            body = json.dumps(stamp(dict(t=time.time(), jobs=rows, status=status_md(), hosts=[h.cfg.get('name', h.cfg['id']) for h in HOSTS]), safe), separators=(',', ':'))
            return self.send(200, body.encode(), 'application/json')
        if u.path == '/api/verdicts':
            if safe: return self.send(403, b'{"safe":true}', 'application/json')
            lab = {h.cfg['id']: h.cfg.get('name', h.cfg['id']) for h in HOSTS}
            with CLOSURES.lock: vs, ver = list(CLOSURES.verdicts), CLOSURES.vver
            rows = [dict(v, host=lab.get(v['host'], v['host'])) for v in vs]
            return self.send(200, json.dumps(stamp(dict(v=ver, verdicts=rows), safe), separators=(',', ':')).encode(), 'application/json')
        if u.path == '/api/elements':
            return self.send(200, json.dumps(stamp(ELEMENTS.snapshot(safe), safe), separators=(',', ':')).encode(), 'application/json')
        if u.path in ('/api/coverage', '/api/coverage/version', '/api/coverage/token'):
            if safe: return self.send(403, b'{"safe":true,"error":"coverage is not part of the share-safe view"}', 'application/json')
            if u.path == '/api/coverage/version': o = COVERAGE.version()
            elif u.path == '/api/coverage/token': o = COVERAGE.token(q.get('design', [''])[0])
            else: o = COVERAGE.api()
            if u.path != '/api/coverage/token': o = stamp(o, safe, coverage=COVERAGE.err or '')
            return self.send(200, json.dumps(o, separators=(',', ':')).encode(), 'application/json')
        if u.path == '/explorer/coverage' or u.path.startswith('/explorer/coverage/'):
            if u.path == '/explorer/coverage': return self.redirect('/explorer/coverage/')
            return self.static_dir(COVERAGE_DIR, u.path[len('/explorer/coverage'):].lstrip('/') or 'index.html', None)
        if u.path == '/explorer/token' or u.path.startswith('/explorer/token/'):
            return self.token(u.path[len('/explorer/token'):].lstrip('/') or 'index.html')
        if u.path.startswith('/api/explorer/'):
            return self.explorer(u.path[len('/api/explorer/'):], q, safe)
        if u.path == '/api/stream':
            self.send_response(200); self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store'); self.send_header('X-Accel-Buffering', 'no'); self.end_headers()
            self.close_connection = True
            try:
                with _cond: body = _snap.get('live', {}).get(safe)
                while True:
                    if body: self.wfile.write(b'data: ' + with_sent(body) + b'\n\n'); self.wfile.flush()
                    with _cond:
                        _cond.wait(POLL * 3); body = _snap.get('live', {}).get(safe)
            except (BrokenPipeError, ConnectionResetError, OSError):
                return
        self.send(404, b'not found', 'text/plain')

    def redirect(self, loc):
        self.send_response(302); self.send_header('Location', loc); self.send_header('Content-Length', '0'); self.end_headers()

    def static_dir(self, base, rel, placeholder):
        try:
            p = (base / rel).resolve()
            ok = p.is_relative_to(base.resolve()) and p.is_file()
        except (OSError, ValueError):
            ok = False
        if not ok:
            if placeholder is not None and rel == 'index.html': return self.send(200, placeholder, 'text/html; charset=utf-8')
            return self.send(404, b'not found', 'text/plain')
        return self.send(200, p.read_bytes(), TOKEN_TYPES.get(p.suffix, 'application/octet-stream'))

    def token(self, rel):
        try:
            p = (TOKEN_DIR / rel).resolve()
            ok = p.is_relative_to(TOKEN_DIR.resolve()) and p.is_file()
        except (OSError, ValueError):
            ok = False
        if not ok:
            if rel == 'index.html': return self.send(200, TOKEN_PLACEHOLDER, 'text/html; charset=utf-8')
            return self.send(404, b'not found', 'text/plain')
        return self.send(200, p.read_bytes(), TOKEN_TYPES.get(p.suffix, 'application/octet-stream'))

    def explorer(self, what, q, safe):
        arg = lambda k: q.get(k, [None])[0]
        js = lambda o, code=200: self.send(code, json.dumps(o, separators=(',', ':')).encode(), 'application/json')
        if what == 'meta':
            return js(stamp(EXPLORER.api_meta(safe), safe, explorer=True))
        if what == 'geom':
            b = EXPLORER.geom_bytes(arg('die') or '', safe)
            if b is None: return js(dict(error='no geometry for this die yet'), 404)
            if 'gzip' not in (self.headers.get('Accept-Encoding') or ''):
                import gzip as _gz
                return self.send(200, _gz.decompress(b), 'application/json')
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(b))); self.send_header('Cache-Control', 'no-store'); self.end_headers()
            if self.command != 'HEAD': self.wfile.write(b)
            return
        if what == 'card':
            if safe and arg('element') is not None and arg('master') is None:
                return js(dict(error='share-safe view: cards open from the map'), 403)
            return js(EXPLORER.card(element=arg('element'), master=arg('master'), die=arg('die'), safe=safe) if not safe
                      else EXPLORER.card_safe_by_index(arg('die'), arg('mi')))
        if what == 'story':
            c = EXPLORER.story(arg('id') or '')
            if c and safe: c = {k: v for k, v in c.items() if k not in ('attach', '_file')}
            return js(c) if c else js(dict(error='no such story'), 404)
        return js(dict(error='unknown explorer endpoint'), 404)

    def log_message(self, *a): pass

class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

if __name__ == '__main__':
    CTL.mkdir(mode=0o700, parents=True, exist_ok=True)
    threading.Thread(target=ticker, daemon=True, name='ticker').start()
    log('fleet-viz serving http://%s:%d (%d hosts, poll %gs)' % (BIND, PORT, len(HOSTS), POLL))
    def _stop(*_):
        if RECORDER: RECORDER.close()   # finish the gzip member cleanly
        os._exit(0)
    signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGINT, _stop)
    Server((BIND, PORT), H).serve_forever()
