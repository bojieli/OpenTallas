"""Per-element (block) closure status for the fleet visualiser (/api/elements, recorder 'elem', ELEMENTS.md).

Groups closure-loop jobs by element: the job's spec.block, with variant blocks (re-cuts, sign-off re-runs, SAFE/HALF
twins, _s2/_t/_split/... alternatives) folded into their master. Each element gets one status category:

  closed (TT era)            a loop-CLOSED job judged at TT (setup_corner tt) or closed after the option-B switch
  closed (TT re-verified)    an earlier closure (or a non-loop route) listed closed by the option-B restatus
  closed (earlier)           an earlier (SS-line) loop closure the restatus neither re-verified nor revoked
  first trial in flight      live jobs, no failure yet
  failed, re-running         failures and a live job
  revoked, re-running        an earlier closure revoked by the link budget (option-B status), with a live job
  revoked (no live job)      ... and nothing running
  needs redesign (no live job)  NEEDS_RTL / NEEDS_BUDGET and nothing running
  flow failure (no live job) NEEDS_HUMAN / INVALID / REFUSED only, nothing running
  cancelled only             every job was cancelled

Sources: ~/.local/state/closure_loop/jobs/*.json (mtime-cached), <repo>/results/closure_loop/option_b_status_*/status.json
and tt_restatus_*.json (latest by name), descriptions from the repo (die-master .env headers, RTL module headers,
abstract manifests) falling back to the cleaned job purpose, cached in <state>/element_descriptions.json (entries with
"src": "manual" are never regenerated). Area comes from the best job's ORFS report (6_report.json, else the route
metrics) fetched over ssh in the background and cached in <state>/element_area.json.
"""
import collections, datetime, glob, json, os, pathlib, re, subprocess, threading, time

T0 = datetime.datetime.fromisoformat('2026-10-07T20:45:00-07:00').timestamp()   # option-B (TT) switch
LIVE = {'QUEUED', 'SYNC', 'READY', 'RUNNING', 'ECO', 'MIGRATING'}
FAIL = {'NEEDS_RTL', 'NEEDS_HUMAN', 'INVALID', 'NEEDS_BUDGET', 'REFUSED'}
CATS = ['closed (TT era)', 'closed (TT re-verified)', 'closed (earlier)', 'first trial in flight', 'failed, re-running',
        'revoked, re-running', 'revoked (no live job)', 'needs redesign (no live job)', 'flow failure (no live job)',
        'cancelled only']
TARGETS = ['Qwen ROM', 'DeepSeek ROM', 'HBM accelerator', 'Other']

# ---------------------------------------------------------------- naming
STRONG = [('Qwen ROM', re.compile(r'^(qfd|ot_qwen|ot_qfd|qwen)')),
          ('HBM accelerator', re.compile(r'^(hfd|ot_hbm|ot_ha2|ot_su\d|ot_attn|hbm|smh|w2_)')),
          ('DeepSeek ROM', re.compile(r'^(dsfd|ot_dsrom|ot_s81|s81|dshead|dsrom|ot_v41_|bf_|pq_)'))]
WEAK = [('Qwen ROM', re.compile(r'qwen')), ('HBM accelerator', re.compile(r'hbm|ha2')),
        ('DeepSeek ROM', re.compile(r's81|dsrom|ds-|deepseek|v41|dshead'))]

def target(block, owner='', branch=''):
    n = block.lower()
    for t, rx in STRONG:
        if rx.search(n): return t
    for key in (owner.lower(), branch.lower(), n):
        for t, rx in WEAK:
            if rx.search(key): return t
    return 'Other'

# (pattern, replacement, forced): a non-forced rule applies only when the result is itself a known block
VARIANT = [(r'_signoff\d+$', '', True), (r'_(parent|retained)$', '', False), (r'_(numeric|padded)$', '', False),
           (r'_split$', '', False), (r'_s2$', '', False), (r'_t$', '', False), (r'_(ab|bv|sq)$', '', False),
           (r'_l$', '', False), (r'_w\d+$', '', False), (r'_fr$', '', False), (r'_credit$', '', False),
           (r'^(ot_qwen_stream4_cdc_pc)_.+$', r'\1', True), (r'^(ot_hbm_native_frame_station_rb_NO\d)_(HALF|SAFE)$', r'\1', True),
           (r'_c12[hs]$', '', True), (r'_halfwrite_distributed$', '_halfwrite', False), (r'_root_phase$', '', False)]

def master(block, known):
    b = block
    for _ in range(6):
        for rx, rep, forced in VARIANT:
            nb = re.sub(rx, rep, b)
            if nb != b and (forced or nb in known):
                b = nb; break
        else:
            return b
    return b

def ts(s):
    try: return datetime.datetime.fromisoformat(s).timestamp()
    except Exception: return 0.0

def _f(x):
    try: return round(float(x), 2)
    except (TypeError, ValueError): return None

# ---------------------------------------------------------------- descriptions
BOILER = re.compile(r're-routed at|requeue of|^re-sign|re-route|resume|rerun of|re-run of', re.I)

def clean_purpose(p):
    p = p.split(' | ')[0]
    for _ in range(3):
        p = re.sub(r'^(?:[A-Z][A-Z0-9-]{2,}(?: \([^)]*\))?|FLOW-HOLD requeue of \S+(?: \([^)]*\))?):\s*', '', p).strip()
    p = re.split(r'(?<=[a-z0-9\)])\. ', p)[0]
    return p[:180]

def header_comment(path):
    try: lines = pathlib.Path(path).read_text(errors='replace').splitlines()[:30]
    except OSError: return ''
    out = []
    for ln in lines:
        s = ln.strip()
        if not s:
            if out: break
            continue
        m = re.match(r'^(?://+|#+|/\*+|\*+/?|--)\s?(.*)$', s)
        if not m:
            break
        t = m.group(1).strip().rstrip('*/').strip()
        if not t or re.match(r'(SPDX|Copyright|-\*-|!)', t): continue
        out.append(t)
        if len(' '.join(out)) > 220: break
    txt = ' '.join(out)
    txt = re.sub(r'\s+', ' ', txt)
    return txt[:220]

class Describer:
    def __init__(self, repo, cache):
        self.repo = pathlib.Path(repo); self.cache_path = pathlib.Path(cache); self.idx = None; self.idx_t = 0
        try: self.cache = json.loads(self.cache_path.read_text())
        except Exception: self.cache = {}

    def index(self):
        if self.idx is not None and time.time() - self.idx_t < 3600: return self.idx
        idx = collections.defaultdict(list)
        try:
            out = subprocess.run(['git', '-C', str(self.repo), 'ls-files', '*.env', '*.sv', '*.v', '*manifest.json'],
                                 capture_output=True, text=True, timeout=60).stdout.split('\n')
        except Exception:
            out = []
        for p in out:
            if not p: continue
            stem = os.path.basename(p).rsplit('.', 1)[0]
            if stem == 'manifest': stem = os.path.basename(os.path.dirname(p))
            idx[stem].append(p)
        self.idx, self.idx_t = idx, time.time()
        return idx

    def lookup(self, name):
        idx = self.index(); top = None
        for p in sorted(idx.get(name, []), key=lambda p: (not p.endswith('.env'), not p.endswith('.sv'), len(p))):
            fp = self.repo / p
            if p.endswith('.env'):
                try: m = re.search(r"^TOP=(\S+)", fp.read_text(errors='replace'), re.M)
                except OSError: m = None
                top = m.group(1).strip('\'"') if m else None
                h = header_comment(fp)
                if h: return h, p, top
            elif p.endswith('manifest.json'):
                try: d = json.loads(fp.read_text())
                except Exception: continue
                for k in ('purpose', 'description', 'summary'):
                    if isinstance(d.get(k), str) and d[k]: return d[k][:220], p, top
            else:
                h = header_comment(fp)
                if h and not re.search(r'station view \(tools/|generated by|auto-?generated', h, re.I): return h, p, top
        return '', '', top

    def get(self, mname, blocks, purposes):
        c = self.cache.get(mname)
        if c and (c.get('src') == 'manual' or c.get('text')): return c['text']
        text, src = '', ''
        for b in [mname] + [b for b in blocks if b != mname]:
            text, src, top = self.lookup(b)
            if not text and top and top != b: text, src, _ = self.lookup(top)
            if text: break
        if not text:
            good = [clean_purpose(p) for p in purposes if p and not BOILER.search(clean_purpose(p))]
            good = [g for g in good if len(g) > 12]
            text = good[0] if good else (clean_purpose(purposes[0]) if purposes else '')
            src = 'job purpose'
        self.cache[mname] = dict(text=text, src=src)
        return text

    def save(self):
        tmp = self.cache_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.cache, indent=1, sort_keys=True)); tmp.replace(self.cache_path)

# ---------------------------------------------------------------- area (remote ORFS reports)
AREA_PY = r'''
import json, glob, sys
for line in sys.stdin:
    q = json.loads(line); r = dict(job=q['job'])
    try:
        bases = sorted(glob.glob(q['base']))
        got = {}
        for b in bases:
            for fn, pre in (('6_report.json', 'finish'), ('5_2_route.json', 'detailedroute'), ('5_1_grt.json', 'globalroute'), ('4_1_cts.json', 'cts')):
                try: d = json.load(open(b + '/' + fn))
                except Exception: continue
                for k, v in d.items():
                    for key, suf in (('die', '__design__die__area'), ('core', '__design__core__area'), ('inst', '__design__instance__area'), ('util', '__design__instance__utilization')):
                        if k.endswith(suf) and key not in got and isinstance(v, (int, float)): got[key] = v
                if got: break
            if got: break
        r.update(got if got else dict(err='no report'))
    except Exception as e:
        r['err'] = str(e)[:100]
    print(json.dumps(r), flush=True)
'''

def area_base(j):
    dm = j.get('drc_metrics')
    if dm: return os.path.dirname(dm)
    od = j.get('orfs_dir')
    return od + '/logs/asap7/*/base' if od else None

# ---------------------------------------------------------------- the model
class Elements:
    def __init__(self, jobs_dir, repo, state_dir, ssh_of, ctl, md_path, log=print, period=60, md_period=600):
        self.jobs_dir = pathlib.Path(jobs_dir); self.repo = pathlib.Path(repo); self.state = pathlib.Path(state_dir)
        self.state.mkdir(parents=True, exist_ok=True)
        self.ssh_of = ssh_of; self.ctl = ctl; self.md_path = pathlib.Path(md_path); self.log = log
        self.period = period; self.md_period = md_period
        self.cache = {}; self.optb = (None, {}); self.rest = (None, {})
        self.desc = Describer(repo, self.state / 'element_descriptions.json')
        self.area_path = self.state / 'element_area.json'
        try: self.area = json.loads(self.area_path.read_text())
        except Exception: self.area = {}
        self.lock = threading.Lock(); self.data = dict(t=0, rows=[], summary={}, cats=CATS, targets=TARGETS); self.ver = 0
        self.md_t = 0
        threading.Thread(target=self.run, daemon=True, name='elements').start()
        threading.Thread(target=self.area_loop, daemon=True, name='elements-area').start()

    # ---- inputs
    def jobs(self):
        seen = set()
        for f in os.scandir(self.jobs_dir):
            if not f.name.endswith('.json'): continue
            seen.add(f.name)
            try: mt = f.stat().st_mtime
            except OSError: continue
            c = self.cache.get(f.name)
            if c and c[0] == mt: continue
            try: j = json.loads(open(f.path).read())
            except Exception: continue
            self.cache[f.name] = (mt, self.reduce(j))
        for k in set(self.cache) - seen: del self.cache[k]
        return [v for _, v in self.cache.values() if v and v['status'] != 'SUMMARY']

    @staticmethod
    def reduce(j):
        s = j.get('spec') or {}; m = j.get('metrics') or {}; ev = j.get('events') or []
        last = ev[-1] if ev else ''
        et, etext = (ts(last.split(' ', 1)[0]), last.split(' ', 1)[1]) if re.match(r'\d{4}-\d\d-\d\dT\S+ ', last) else (0.0, last)
        closed_t = None
        if j.get('status') == 'CLOSED':
            for e in reversed(ev):
                if re.match(r'\S+ CLOSED', e): closed_t = ts(e.split(' ', 1)[0]); break
            closed_t = closed_t or ts(j.get('updated', ''))
        tt = m.get('setup_corner') == 'tt'
        name = j.get('name') or ''
        return dict(name=name, block=s.get('block') or re.sub(r'[-_][0-9a-f]{9}.*$', '', name), status=j.get('status'),
                    owner=s.get('owner') or '', branch=(s.get('source') or {}).get('branch') or '', purpose=s.get('purpose') or '',
                    created=ts(j.get('created', '')), updated=ts(j.get('updated', '')), et=et or ts(j.get('updated', '')), event=etext[:300],
                    closed_t=closed_t, host=j.get('host'), tt_corner=tt,
                    tt=_f(m.get('ss_ps')) if tt else None, ss=_f(m.get('ss_sensitivity_ps')) if tt else _f(m.get('ss_ps')),
                    ff=_f(m.get('ff_ps')), drc=m.get('drc'), has_m=bool(m),
                    drc_metrics=(m.get('drc_metrics') or [None])[0], orfs_dir=m.get('orfs_dir'))

    def latest(self, pattern):
        fs = sorted(glob.glob(str(self.repo / pattern)))
        return fs[-1] if fs else None

    def option_b(self):
        p = self.latest('results/closure_loop/option_b_status_*/status.json')
        key = (p, os.path.getmtime(p)) if p else None
        if key != self.optb[0]:
            d = {}
            try:
                s = json.loads(pathlib.Path(p).read_text())
                d = dict(path=os.path.relpath(p, self.repo), decided=s.get('decided', ''),
                         closed={b['block']: b for b in s.get('closed', [])},
                         revoked={b['block']: b for b in (s.get('revoked_previously_closed') or {}).get('blocks', [])},
                         unverified={b['block']: b for b in (s.get('unverified_forwarded_clock') or {}).get('blocks', [])})
            except Exception as e:
                self.log('elements: option-B status: %s' % e)
            self.optb = (key, d)
        p = self.latest('results/closure_loop/tt_restatus_*.json')
        key = (p, os.path.getmtime(p)) if p else None
        if key != self.rest[0]:
            d = {}
            try: d = {r['job']: r for r in json.loads(pathlib.Path(p).read_text()).get('jobs', [])}
            except Exception as e: self.log('elements: tt restatus: %s' % e)
            self.rest = (key, d)
        return self.optb[1], self.rest[1]

    # ---- classification
    def compute(self):
        js = self.jobs(); ob, rest = self.option_b()
        known = {j['block'] for j in js} | set(ob.get('closed', {})) | set(ob.get('revoked', {}))
        groups = collections.defaultdict(list)
        for j in js: groups[master(j['block'], known)].append(j)
        for b in ob.get('closed', {}):   # option-B closed blocks with no loop job (routes judged outside the loop)
            groups.setdefault(master(b, known), [])
        rows = []
        for m, g in groups.items():
            rows.append(self.element(m, g, ob, rest))
        rows.sort(key=lambda r: (TARGETS.index(r['target']), CATS.index(r['category']), r['element']))
        summ = collections.defaultdict(lambda: collections.Counter())
        for r in rows: summ[r['target']][r['category']] += 1
        self.desc.save()
        return dict(t=time.time(), rows=rows, cats=CATS, targets=TARGETS,
                    summary={t: dict(summ[t]) for t in TARGETS if t in summ},
                    sources=dict(option_b=ob.get('path'), option_b_decided=ob.get('decided'), jobs=len(js)))

    def element(self, m, g, ob, rest):
        blocks = sorted({j['block'] for j in g} | ({m} if not g else set()))
        rev_blocks = ob.get('revoked', {}); okb = ob.get('closed', {})
        for j in g:   # option-B judgements on the job itself
            r = rest.get(j['name'])
            if r and j['tt'] is None:
                j['tt'] = _f(r.get('setup_verdict_ws_ps') if r.get('setup_verdict_ws_ps') is not None else r.get('ttlb_ws_ps'))
        live = [j for j in g if j['status'] in LIVE]; failed = [j for j in g if j['status'] in FAIL]
        closed = [j for j in g if j['status'] == 'CLOSED']
        tt_closed = [j for j in closed if j['tt_corner'] or (j['closed_t'] or 0) >= T0]
        early = [j for j in closed if j not in tt_closed]
        def revoked(j):
            r = rest.get(j['name'])
            return (j['block'] in rev_blocks and rev_blocks[j['block']].get('job') in (None, j['name'])) or \
                   (r is not None and r.get('verdict') != 'CLOSED_TT') or (j['block'] in rev_blocks and j['block'] not in okb)
        early_rev = [j for j in early if revoked(j)]
        early_ok = [j for j in early if j not in early_rev]
        reverified = [j for j in early_ok if j['block'] in okb or (rest.get(j['name']) or {}).get('verdict') == 'CLOSED_TT']
        ob_only = [b for b in blocks if b in okb]
        best = None; closed_t = None; via = ''
        if tt_closed:
            cat = CATS[0]; best = max(tt_closed, key=lambda j: j['closed_t'] or 0); closed_t = best['closed_t']
        elif reverified or ob_only:
            cat = CATS[1]
            if reverified: best = max(reverified, key=lambda j: j['closed_t'] or 0); closed_t = best['closed_t']
            via = 'option-B restatus'
        elif early_ok:
            cat = CATS[2]; best = max(early_ok, key=lambda j: j['closed_t'] or 0); closed_t = best['closed_t']
        elif early_rev or any(b in rev_blocks for b in blocks):
            cat = CATS[5] if live else CATS[6]; via = 'link budget'
        elif live and not failed: cat = CATS[3]
        elif live: cat = CATS[4]
        elif failed:
            cat = CATS[7] if any(j['status'] in ('NEEDS_RTL', 'NEEDS_BUDGET') for j in failed) else CATS[8]
        else: cat = CATS[9]
        if best is None:
            cand = [j for j in g if j['has_m'] and (j['tt'] is not None or j['ss'] is not None or j['ff'] is not None)]
            def score(j):
                s = j['tt'] if j['tt'] is not None else j['ss']
                return (j['drc'] == 0, min(x for x in (s, j['ff'], 1e9) if x is not None), j['updated'])
            best = max(cand, key=score) if cand else None
        tm = dict(tt=None, ff=None, ss=None, drc=None, job=None, corner=None)
        if best:
            tm = dict(tt=best['tt'], ff=best['ff'], ss=best['ss'], drc=best['drc'], job=best['name'],
                      corner='TT' if best['tt_corner'] else 'SS')
        elif ob_only:
            o = okb[ob_only[0]]
            tm = dict(tt=_f(o.get('tt_lb_ps') if o.get('tt_lb_ps') is not None else o.get('tt_ps')), ff=_f(o.get('ff_ps')),
                      ss=_f(o.get('ss_sensitivity_ps')), drc=o.get('drc'), job=o.get('job'), corner='TT')
        lj = max(g, key=lambda j: j['et']) if g else None
        a = self.area.get(tm['job'] or '') or {}
        rv = rev_blocks.get(m) or next((rev_blocks[b] for b in blocks if b in rev_blocks), None)
        return dict(element=m, target=target(m, *(next(((j['owner'], j['branch']) for j in g), ('', '')))),
                    variants=[b for b in blocks if b != m], category=cat, via=via,
                    purpose=self.desc.get(m, blocks, [j['purpose'] for j in sorted(g, key=lambda j: j['created'])]),
                    jobs=len(g), live=len(live), failed=len(failed), closed_jobs=len(closed),
                    best=tm, area=dict(die=a.get('die'), core=a.get('core'), util=a.get('util')) if 'err' not in a and a else None,
                    revoked=dict(verdict=rv.get('verdict'), tt_lb=rv.get('tt_link_budget_ps')) if rv and cat in CATS[5:7] else None,
                    latest=dict(t=lj['et'], job=lj['name'], status=lj['status'], text=lj['event']) if lj else None,
                    closed_t=closed_t, owner=next((j['owner'] for j in sorted(g, key=lambda j: -j['updated'])), ''),
                    _host=best['host'] if best else None, _base=area_base(best) if best else None)

    # ---- loops
    def run(self):
        while True:
            try:
                d = self.compute()
                with self.lock:
                    self.data = d; self.ver += 1
                if time.time() - self.md_t >= self.md_period:
                    self.md_t = time.time(); self.write_md(d)
            except Exception as e:
                self.log('elements: %s' % e)
            time.sleep(self.period)

    def area_loop(self):
        time.sleep(20)
        while True:
            try: self.fetch_areas()
            except Exception as e: self.log('elements area: %s' % e)
            time.sleep(300)

    def fetch_areas(self):
        with self.lock: rows = list(self.data['rows'])
        now = time.time(); want = collections.defaultdict(list)
        for r in rows:
            job, host, base = r['best']['job'], r.get('_host'), r.get('_base')
            if not job or not host or not base: continue
            a = self.area.get(job)
            if a and ('err' not in a or now - a.get('t', 0) < 6 * 3600): continue
            want[host].append(dict(job=job, base=base))
        changed = False
        for host, qs in want.items():
            ssh = self.ssh_of(host)
            if ssh is False: continue
            cmd = ['python3', '-c', AREA_PY] if ssh is None else \
                ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', '-o', 'ControlMaster=auto',
                 '-o', 'ControlPath=%s/%%r@%%h:%%p' % self.ctl, '-o', 'ControlPersist=120', ssh,
                 'nice -n 10 python3 -c %s' % _shq(AREA_PY)]
            try:
                p = subprocess.run(cmd, input=''.join(json.dumps(q) + '\n' for q in qs[:150]), capture_output=True, text=True, timeout=180)
                for line in p.stdout.splitlines():
                    try: r = json.loads(line)
                    except ValueError: continue
                    job = r.pop('job'); r['t'] = now; self.area[job] = r; changed = True
            except Exception as e:
                self.log('elements area %s: %s' % (host, e))
        if changed:
            tmp = self.area_path.with_suffix('.tmp'); tmp.write_text(json.dumps(self.area)); tmp.replace(self.area_path)

    def snapshot(self, safe=False):
        with self.lock: d = self.data; v = self.ver
        if safe:
            return dict(t=d['t'], safe=True, cats=CATS, targets=TARGETS, summary=d['summary'], v=v)
        return dict(d, rows=[public(r) for r in d['rows']], v=v)

    # ---- markdown
    def write_md(self, d):
        L = ['# Element status', '',
             'Per-element closure status, written by fleet-viz (tools/fleet_viz/elements.py) every %d min; %s.' %
             (self.md_period // 60, datetime.datetime.fromtimestamp(d['t']).strftime('%Y-%m-%d %H:%M PT')),
             'Option-B status: %s. TT era since 2026-10-07 20:45 PT. Slacks in ps (TT setup / FF hold / SS sensitivity).' %
             (d.get('sources', {}).get('option_b') or 'not found'), '', '## Summary', '',
             '| target | ' + ' | '.join(CATS) + ' | total |', '|---|' + '---:|' * (len(CATS) + 1)]
        for t in TARGETS:
            s = d['summary'].get(t)
            if not s: continue
            L.append('| %s | %s | %d |' % (t, ' | '.join(str(s.get(c, '')) for c in CATS), sum(s.values())))
        for t in TARGETS:
            rs = [r for r in d['rows'] if r['target'] == t]
            if not rs: continue
            L += ['', '## %s (%d)' % (t, len(rs)), '',
                  '| element | status | what it is | TT | FF | SS | DRC | die µm² | util | jobs live/failed/total | closed | latest |',
                  '|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|']
            for r in rs:
                b = r['best']; a = r['area'] or {}
                fmt = lambda x: '' if x is None else ('%+.1f' % x)
                L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %d/%d/%d | %s | %s |' % (
                    r['element'] + (' (+%d variants)' % len(r['variants']) if r['variants'] else ''), r['category'],
                    _md(r['purpose'][:120]), fmt(b['tt']), fmt(b['ff']), fmt(b['ss']), '' if b['drc'] is None else b['drc'],
                    '' if a.get('die') is None else '%.0f' % a['die'], '' if a.get('util') is None else '%.0f%%' % (100 * a['util']),
                    r['live'], r['failed'], r['jobs'],
                    datetime.datetime.fromtimestamp(r['closed_t']).strftime('%m-%d %H:%M') if r['closed_t'] else '',
                    _md(('%s %s: %s' % (datetime.datetime.fromtimestamp(r['latest']['t']).strftime('%m-%d %H:%M'), r['latest']['status'],
                                          r['latest']['text']))[:140]) if r['latest'] else ''))
        try:
            self.md_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.md_path.with_suffix('.tmp'); tmp.write_text('\n'.join(L) + '\n'); tmp.replace(self.md_path)
        except OSError as e:
            self.log('elements md: %s' % e)

def public(r):
    return {k: v for k, v in r.items() if not k.startswith('_')}

def change_key(d):
    """What makes an element snapshot worth recording now (not the per-minute latest-event churn)."""
    return hash(tuple((r['element'], r['category'], r['live'], r['failed'], r['jobs'], r['best']['job']) for r in d['rows']))

def _md(s):
    return str(s).replace('|', '\\|').replace('\n', ' ')

def _shq(s):
    return "'" + s.replace("'", "'\\''") + "'"
