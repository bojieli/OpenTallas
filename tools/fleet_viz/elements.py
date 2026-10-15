"""Per-element (block) closure status for the fleet visualiser (/api/elements, recorder 'elem', ELEMENTS.md).

Groups closure-loop jobs by element: the job's spec.block, with variant blocks (re-cuts, sign-off re-runs, SAFE/HALF
twins, _s2/_t/_split/... alternatives) folded into their master. Each element gets one status category:

  closed (TT era)            a loop-CLOSED job judged at TT (setup_corner tt) or closed after the option-B switch
  closed (TT re-verified)    an earlier closure (or a non-loop route) listed closed by the option-B restatus
  closed (earlier)           an earlier (SS-line) loop closure the restatus neither re-verified nor revoked
  first trial in flight      live jobs, no failure yet
  failed, re-running         failures and a live job
  revoked, re-running        every closure revoked (link budget via option-B status, or a per-job entry in
                             revoked_closures.json, any era), with a live job
  revoked (no live job)      ... and nothing running
  needs redesign (no live job)  NEEDS_RTL / NEEDS_BUDGET and nothing running
  flow failure (no live job) NEEDS_HUMAN / INVALID / REFUSED only, nothing running
  cancelled only             every job was cancelled
  superseded                 listed in $FLEET_VIZ_SUPERSEDED (default ~/claude-takeover-20261007/superseded_elements.json,
                             {element: {by, reason}}): replaced by another element or not used by any die; overrides every
                             category (closed included, owner 10-11) and is excluded from totals; cancelled jobs retain the requirement in totals

Overrides from $FLEET_VIZ_OVERRIDES (default ~/claude-takeover-20261007/element_overrides.json):
  variants   {block: {of, kind, reason}}: fold a differently named block into element `of` (checked before the VARIANT
             regexes). kind 'alternative' (default; a/b cuts, wide fallbacks, a candidate successor still on trial):
             any closure closes the element. kind 'instance' (parameter instances that are ALL instantiated, e.g. the
             LANE0 taps): the element is closed only when every instance block has a closure of its own, otherwise it
             takes the category of the unclosed instances' jobs.
  owner_map  {owner prefix: owner}: re-owns rows whose owner string starts with the prefix (longest match wins).
  owners     {element: owner}: per-element owner, applied last. The original owner stays in `owner_orig`.

Sources: ~/.local/state/closure_loop/jobs/*.json (mtime-cached), <repo>/results/closure_loop/option_b_status_*/status.json
and tt_restatus_*.json (latest by name), per-job revocations from $FLEET_VIZ_REVOKED (default
~/claude-takeover-20261007/revoked_closures.json, {job: {reason, ff_ps, by, at}}; applies to any CLOSED job), descriptions from the repo (die-master .env headers, RTL module headers,
abstract manifests) falling back to the cleaned job purpose, cached in <state>/element_descriptions.json (entries with
"src": "manual" are never regenerated). Hand-written descriptions in <repo>/results/fleet_viz/element_descriptions_manual.json
({families: {name: blurb}, elements: {el: {summary, about, family}}}) load first and override the cache; rows carry summary, about,
family and family_about (empty about/family when no manual entry). Throughput qualification (AGENTS.md, owner 2026-10-10) comes from the latest
<repo>/results/arch/throughput_budget_*/budget.json (working tree, else origin/main): each row gets `throughput`
(status QUALIFIED / UNMEASURED (a price, no measured ratio) / UNQUALIFIED / UNQUALIFIED_NO_BENCH, worst measured/price ratio, limiting op, owner) and `gate`
('CLOSED-TIMING, THROUGHPUT-UNQUALIFIED' until the unit's production-shape bench is within 1.10 of its price). Area comes from the best job's ORFS report (6_report.json, else the route
metrics) fetched over ssh in the background and cached in <state>/element_area.json.
"""
import collections, datetime, glob, json, os, pathlib, re, subprocess, threading, time
import flow_state
import die_contracts
import master_identity

T0 = datetime.datetime.fromisoformat('2026-10-07T20:45:00-07:00').timestamp()   # option-B (TT) switch
LIVE = {'QUEUED', 'SYNC', 'READY', 'RUNNING', 'ECO', 'ECO_RESULT', 'ECO_INSTALL', 'SUMMARY', 'MIGRATING'}
REDESIGN = {'NEEDS_RTL', 'NEEDS_BUDGET', 'FLOORPLAN_MARGIN', 'PREROUTE_MARGIN',
            'EARLY_FAIL_SETUP', 'EARLY_FAIL_HOLD', 'EARLY_FAIL_CONGESTION', 'EARLY_FAIL_DRC', 'EARLY_FAIL_STALL'}
FAIL = REDESIGN | {'NEEDS_HUMAN', 'INVALID', 'REFUSED'}
CATS = ['closed (TT era)', 'closed (TT re-verified)', 'closed (earlier)', 'first trial in flight', 'failed, re-running',
        'revoked, re-running', 'revoked (no live job)', 'needs redesign (no live job)', 'flow failure (no live job)',
        'cancelled only', 'superseded', 'implementation recorded (no physical job)', 'not started (open)']
NOT_STARTED = 'not started (open)'   # registry-sync 10-15: a current die-contract element with no physical job yet
# per-design count buckets (fleet header): every non-superseded category is closed, in flight, failed or not started
BUCKET = {'first trial in flight': 'in_flight', 'failed, re-running': 'in_flight', 'revoked, re-running': 'in_flight',
          'revoked (no live job)': 'failed', 'needs redesign (no live job)': 'failed', 'flow failure (no live job)': 'failed',
          'cancelled only': 'failed', 'implementation recorded (no physical job)': 'not_started', NOT_STARTED: 'not_started'}
TARGETS = ['Qwen ROM', 'DeepSeek ROM', 'HBM accelerator', 'Other']

# ---------------------------------------------------------------- naming
STRONG = [('Qwen ROM', re.compile(r'^(qfd|qkd|ot_qwen|ot_qfd|ot_qkvd|qwen|ot_nhb_|ot_qkh_)')),   # qkd / ot_qkvd: the KV die (kv-die 2026-10-09)
          ('HBM accelerator', re.compile(r'^(hfd|ot_hbm|ot_ha2|ot_su\d|ot_attn|hbm|smh|w2_|hgi|ot_hgi|ot_hcoll|ot_gpu_rf_)')),
          ('DeepSeek ROM', re.compile(r'^(dsfd|ot_dsrom|ot_s81|s81|dshead|dsrom|ot_v41_|bf_|pq_|ot_mtp_)'))]
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
           (r'_c12[hs]$', '', True), (r'^(qfd_sysctl_stn)_pb2$', r'\1', True), (r'_halfwrite_distributed$', '_halfwrite', False), (r'_root_phase$', '', False)]

def master(block, known, vmap=None):
    if vmap and block in vmap: return vmap[block]
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
    try: return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
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
        # hand-written descriptions committed to the repo (element-desc-1011): loaded first, survive redeploys
        self.manual_path = self.repo / 'results/fleet_viz/element_descriptions_manual.json'
        self.manual_t = None; self.manual = {}; self.families = {}
        self.load_manual()

    def load_manual(self):
        # working tree first, else origin/main (the shared checkout can lag main)
        try: t = self.manual_path.stat().st_mtime; src = None
        except OSError:
            rel = str(self.manual_path.relative_to(self.repo))
            try: t = subprocess.run(['git', '-C', str(self.repo), 'rev-parse', 'origin/main:' + rel],
                                    capture_output=True, text=True, timeout=20).stdout.strip(); src = rel
            except Exception: return
            if not t: return
        if t == self.manual_t: return
        try:
            d = json.loads(self.manual_path.read_text() if src is None else subprocess.run(
                ['git', '-C', str(self.repo), 'show', 'origin/main:' + src], capture_output=True, text=True, timeout=30).stdout)
        except Exception: return
        self.manual_t = t; self.manual = d.get('elements', {}); self.families = d.get('families', {})
        for m, e in self.manual.items():
            if e.get('summary'):
                self.cache[m] = dict(text=e['summary'], src='manual', summary=e['summary'],
                                     about=e.get('about', ''), family=e.get('family', ''))

    def info(self, mname):
        self.load_manual()
        c = self.cache.get(mname) or {}
        if c.get('src') != 'manual': return dict(summary=c.get('text', ''), about='', family='', family_about='')
        f = c.get('family', '')
        return dict(summary=c.get('summary') or c.get('text', ''), about=c.get('about', ''), family=f,
                    family_about=self.families.get(f, ''))


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
        self.flow = flow_state.FlowState(repo, log)   # flow / version state (ref_tile M5 = current flow)
        self.cache = {}; self.optb = (None, {}); self.rest = (None, {}); self.revk = (None, {}); self.supk = (None, {})
        self.superseded_path = pathlib.Path(os.environ.get('FLEET_VIZ_SUPERSEDED', os.path.expanduser(
            '~/claude-takeover-20261007/superseded_elements.json')))
        self.ovk = (None, {})
        self.tpk = (None, {})
        self.overrides_path = pathlib.Path(os.environ.get('FLEET_VIZ_OVERRIDES', os.path.expanduser(
            '~/claude-takeover-20261007/element_overrides.json')))
        self.revoked_path = pathlib.Path(os.environ.get('FLEET_VIZ_REVOKED', os.path.expanduser(
            '~/claude-takeover-20261007/revoked_closures.json')))
        self.desc = Describer(repo, self.state / 'element_descriptions.json')
        self.contracts = die_contracts.Contracts(repo, log)   # top-down element list from the current die contracts
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
                    source_commit=(s.get('source') or {}).get('commit'),
                    created=ts(j.get('created', '')), updated=ts(j.get('updated', '')), et=et or ts(j.get('updated', '')), event=etext[:300],
                    closed_t=closed_t, host=j.get('host'), tt_corner=tt,
                    tt=_f(m.get('ss_ps')) if tt else None, ss=_f(m.get('ss_sensitivity_ps')) if tt else _f(m.get('ss_ps')),
                    ff=_f(m.get('ff_ps')), drc=m.get('drc'), has_m=bool(m),
                    drc_metrics=(m.get('drc_metrics') or [None])[0], orfs_dir=m.get('orfs_dir'),
                    ref_tile=bool(s.get('ref_tile')), kit=flow_state.kit_of(((s.get('stages') or {}).get('route') or {}).get('cmd')))

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

    def revoked_jobs(self):
        try: key = self.revoked_path.stat().st_mtime
        except OSError: key = None
        if key != self.revk[0]:
            d = {}
            if key is not None:
                try: d = {k: v for k, v in json.loads(self.revoked_path.read_text()).items() if isinstance(v, dict)}
                except Exception as e: self.log('elements: revoked closures: %s' % e)
            self.revk = (key, d)
        return self.revk[1]

    def superseded(self):
        try: key = self.superseded_path.stat().st_mtime
        except OSError: key = None
        if key != self.supk[0]:
            d = {}
            if key is not None:
                try: d = {k: v for k, v in json.loads(self.superseded_path.read_text()).items() if isinstance(v, dict)}
                except Exception as e: self.log('elements: superseded: %s' % e)
            self.supk = (key, d)
        return self.supk[1]

    def overrides(self):
        try: key = self.overrides_path.stat().st_mtime
        except OSError: key = None
        if key != self.ovk[0]:
            d = dict(variants={}, owner_map={}, owners={})
            if key is not None:
                try:
                    raw = json.loads(self.overrides_path.read_text())
                    d['variants'] = {k: v for k, v in (raw.get('variants') or {}).items()
                                     if isinstance(v, dict) and isinstance(v.get('of'), str) and v['of'] and v['of'] != k}
                    for f in ('owner_map', 'owners'):
                        d[f] = {k: v for k, v in (raw.get(f) or {}).items() if isinstance(v, str) and v}
                except Exception as e: self.log('elements: overrides: %s' % e)
            self.ovk = (key, d)
        return dict(dict(variants={}, owner_map={}, owners={}), **self.ovk[1])

    @staticmethod
    def remap_owner(owner, ov):
        best = None
        for k in ov.get('owner_map', {}):
            if owner == k or (owner.startswith(k) and not re.match(r'[A-Za-z0-9_-]', owner[len(k)])):
                if best is None or len(k) > len(best): best = k
        return ov['owner_map'][best] if best else owner

    def throughput(self):
        """Per-element throughput qualification from the latest committed budget (results/arch/throughput_budget_*/
        budget.json 'elements'): working tree first, else origin/main (the shared checkout can lag main)."""
        files = sorted(glob.glob(str(self.repo / 'results/arch/throughput_budget_*/budget.json')))
        key = None; text = None; src = None
        try:
            if files:
                key = (files[-1], os.stat(files[-1]).st_mtime)
                if key == self.tpk[0]: return self.tpk[1]
                text = open(files[-1]).read(); src = os.path.relpath(files[-1], self.repo)
            else:
                sha = subprocess.run(['git', '-C', str(self.repo), 'rev-parse', 'origin/main'], capture_output=True,
                                     text=True, timeout=20).stdout.strip()
                key = ('origin/main', sha)
                if key == self.tpk[0]: return self.tpk[1]
                ls = subprocess.run(['git', '-C', str(self.repo), 'ls-tree', '-r', '--name-only', 'origin/main',
                                     'results/arch/'], capture_output=True, text=True, timeout=60).stdout.split()
                cands = sorted(x for x in ls if re.match(r'results/arch/throughput_budget_[^/]+/budget\.json$', x))
                if cands:
                    text = subprocess.run(['git', '-C', str(self.repo), 'show', 'origin/main:' + cands[-1]],
                                          capture_output=True, text=True, timeout=60).stdout
                    src = 'origin/main:' + cands[-1]
            d = {}
            if text:
                doc = json.loads(text)
                for e, v in (doc.get('elements') or {}).items():
                    if isinstance(v, dict) and v.get('status'):
                        d[e] = dict(honest_throughput(v), budget=src, qualify_ratio=doc.get('qualify_ratio', 1.10))
        except Exception as e:
            self.log('elements: throughput budget: %s' % e); d = self.tpk[1]
        self.tpk = (key, d)
        return d

    def registry(self):
        """Read additive, committed implementation evidence; never infer physical closure."""
        history = collections.defaultdict(list); errors = []
        for p in sorted((self.repo / 'results/fleet_viz/element_registry').glob('*.json')):
            rel = str(p.relative_to(self.repo))
            try:
                document = json.loads(p.read_text())
                if not isinstance(document, dict) or document.get('schema_version') != 1 or not isinstance(document.get('records'), list):
                    raise ValueError('expected schema_version 1 and records list')
                accepted = []
                for record in document['records']:
                    if not isinstance(record, dict) or not isinstance(record.get('element'), str) or not record['element']:
                        raise ValueError('record requires element')
                    source = record.get('source') or {}
                    if not isinstance(source, dict): raise ValueError('source must be an object')
                    if not re.fullmatch(r'[0-9a-f]{9,40}', str(source.get('commit', ''))):
                        raise ValueError('record requires pinned source.commit')
                    if not isinstance(source.get('paths'), list) or not source['paths'] or not all(isinstance(x, str) and x for x in source['paths']):
                        raise ValueError('record requires source.paths')
                    if record.get('target') not in TARGETS:
                        raise ValueError('record requires canonical target')
                    for field in ('recorded_at', 'owner', 'description'):
                        if field in record and not isinstance(record[field], str):
                            raise ValueError('%s must be a string' % field)
                    if 'dependencies' in record and (not isinstance(record['dependencies'], list) or
                            not all(isinstance(x, str) for x in record['dependencies'])):
                        raise ValueError('dependencies must be a list of strings')
                    for field in ('implementation', 'model', 'exactness', 'physical', 'integration'):
                        if field in record and not isinstance(record[field], dict):
                            raise ValueError('%s must be an object' % field)
                    for field in ('positive', 'negative'):
                        if field in record.get('exactness', {}) and not isinstance(record['exactness'][field], dict):
                            raise ValueError('exactness.%s must be an object' % field)
                    accepted.append(dict(record, registry_path=rel))
                for record in accepted: history[record['element']].append(record)
            except (OSError, ValueError, TypeError) as e:
                errors.append(dict(path=rel, error=str(e)))
        return history, errors

    # ---- classification
    def compute(self):
        js = self.jobs(); ob, rest = self.option_b(); rj = self.revoked_jobs(); sup = self.superseded()
        ov = self.overrides() if hasattr(self, 'overrides_path') else dict(variants={}, owner_map={}, owners={})
        registry, registry_errors = self.registry()
        tput = self.throughput() if hasattr(self, 'tpk') else {}
        known = {j['block'] for j in js} | set(ob.get('closed', {})) | set(ob.get('revoked', {})) | set(registry)
        vmap = {b: master(v['of'], known) for b, v in ov['variants'].items()}
        vmap = {b: m for b, m in vmap.items() if m not in sup}   # never fold into a superseded parent (it would count nowhere)
        instances = collections.defaultdict(set); tiles = collections.defaultdict(set)
        for b, v in ov['variants'].items():
            # fill-9 2026-10-10: a fold whose parent is superseded is dropped from vmap above; indexing it raised KeyError
            # and froze /api/elements from 11:06 to 16:37 (dsfd_mtp_seq_rtt instance of superseded dsrom_mtp_seq_native_binding)
            if v.get('kind') == 'instance' and b in vmap: instances[vmap[b]].update((b, vmap[b]))   # the master block is an instance too
            # owner 10-11 two-level rule: kind 'tile' = a hardened tile of a composed element. The element closes when every
            # tile block has a closure (the composition bench gates adding the fold); the master's own flat jobs do not
            # block it, but a closure of the master itself (dual-track flat line) still closes it.
            if v.get('kind') == 'tile' and b in vmap: tiles[vmap[b]].add(b)
        groups = collections.defaultdict(list)
        for j in js: groups[master(j['block'], known, vmap)].append(j)
        for b in ob.get('closed', {}):   # option-B closed blocks with no loop job (routes judged outside the loop)
            groups.setdefault(master(b, known, vmap), [])
        evidence = collections.defaultdict(list)
        for b, records in registry.items():
            key = master(b, known, vmap); groups.setdefault(key, []); evidence[key].extend(records)
        rows = []
        for m, g in groups.items():
            gg = g
            if tiles.get(m) and not any(j['block'] == m and j['status'] == 'CLOSED' and j['name'] not in rj for j in g):
                gg = [j for j in g if j['block'] in tiles[m]]
                closed_blocks = {j['block'] for j in gg if j['status'] == 'CLOSED' and j['name'] not in rj} | set(ob.get('closed', {}))
                missing = sorted(b for b in tiles[m] if b not in closed_blocks)
            r = self.element(m, gg or g, ob, rest, rj)
            if gg is not g and missing:
                if r['category'].startswith('closed'):
                    r['category'] = self.element(m, [j for j in gg if j['block'] in missing], ob, rest, rj)['category'] if any(j['block'] in missing for j in gg) else CATS[7]
                    r['closed_t'] = None
                r['via'] = 'tiles not closed: %s' % ', '.join(missing)
            elif gg is not g:
                r['via'] = 'closed via tiles: %s' % ', '.join(sorted(tiles[m]))
            if r['category'].startswith('closed') and instances.get(m):
                closed_blocks = {j['block'] for j in g if j['status'] == 'CLOSED' and j['name'] not in rj} | set(ob.get('closed', {}))
                missing = sorted(b for b in instances[m] if b not in closed_blocks)
                if missing:   # an instance-variant element is closed only when every instance closed
                    sub = [j for j in g if j['block'] in missing]
                    r['category'] = self.element(m, sub, ob, rest, rj)['category'] if sub else CATS[7]
                    r['closed_t'] = None
                    r['via'] = 'instances not closed: %s' % ', '.join(missing)
            records = sorted(evidence[m], key=lambda x: (ts(x.get('recorded_at', '')), x['registry_path']))
            r['evidence_history'] = records
            r['qualification'] = records[-1] if records else None
            if records:
                q = records[-1]
                r['target'] = q['target']; r['owner'] = q.get('owner') or r['owner']
                r['purpose'] = q.get('description') or r['purpose']
                if not g and m not in ob.get('closed', {}):
                    r['category'] = 'implementation recorded (no physical job)'
            r['owner_orig'] = r['owner']
            r['owner'] = ov['owners'].get(m) or self.remap_owner(r['owner'] or '', ov)
            sv = sup.get(m) or next((sup[b] for b in [m] + r['variants'] if b in sup), None)
            r['superseded'] = None
            r['supersession_source_evidence_missing'] = None
            if sv:   # owner 10-11: superseded overrides closed too; such rows are not counted anywhere
                r['category'] = 'superseded'; r['superseded'] = dict(by=sv.get('by'), reason=sv.get('reason'))
                # Preserve historical declarations, expose their proof gap; never invent a successor.
                r['supersession_source_evidence_missing'] = not isinstance(sv.get('source_evidence'), dict)
                r['via'] = 'superseded by %s' % sv.get('by')
            tq = tput.get(m) or next((tput[b] for b in r['variants'] if b in tput), None)
            r['throughput'] = tq
            r['gate'] = gate_text(r['category'], tq)
            rows.append(r)
        dsum, dsrc = self.apply_contracts(rows) if hasattr(self, 'contracts') else ({}, None)
        flow = self.flow.annotate(rows, groups, TARGETS)   # r['flow'] / flow_label / die_used / m5_reroute
        rows.sort(key=lambda r: (TARGETS.index(r['target']), CATS.index(r['category']), r['element']))
        independent, integration, identity = (master_identity.classify(rows, self.contracts.repo)
            if hasattr(self, 'contracts') else (rows, [], {}))
        # Die headers use the same independent-master scope as the default list.
        for design, summary in dsum.items():
            summary['integration_records'] = sum(any(d['design'] == design for d in (r.get('dies') or [])) for r in integration)
            count = collections.Counter()
            for r in independent:
                if not any(d['design'] == design for d in (r.get('dies') or [])): continue
                category = r['category']
                count['closed' if category.startswith('closed') else ('superseded' if category == 'superseded' else BUCKET.get(category, 'failed'))] += 1
            for k in ('closed', 'superseded', 'in_flight', 'failed', 'not_started'): summary[k] = count[k]
            summary['open'] = sum(count[k] for k in ('in_flight', 'failed', 'not_started'))
            summary['total'] = summary['closed'] + summary['open']
        summ = collections.defaultdict(lambda: collections.Counter())
        tsum = collections.defaultdict(lambda: collections.Counter())
        for r in independent:
            summ[r['target']][r['category']] += 1
            if r['category'].startswith('closed'):
                tsum[r['target']][(r.get('throughput') or {}).get('status') or 'NO_BUDGET_ROW'] += 1
        self.desc.save()
        return dict(t=time.time(), rows=rows, independent_rows=independent, integration_rows=integration, master_identity=identity, cats=CATS, targets=TARGETS, flow=flow,
                    summary={t: dict(summ[t]) for t in TARGETS if t in summ},
                    throughput_summary={t: dict(tsum[t]) for t in TARGETS if t in tsum},
                    designs=dsum, contracts=dsrc,
                    sources=dict(option_b=ob.get('path'), option_b_decided=ob.get('decided'), jobs=len(js),
                                 revoked_jobs=str(self.revoked_path) if rj else None, n_revoked_jobs=len(rj),
                                 registry='results/fleet_viz/element_registry', registry_records=sum(map(len, registry.values())),
                                 registry_errors=registry_errors,
                                 superseded=str(self.superseded_path) if sup else None, n_superseded=len(sup)))

    # ---- top-down: current die contracts (die_contracts.py, results/fleet_viz/die_contracts.json)
    def apply_contracts(self, rows):
        """Annotate rows with their die / role / owner stream / native check, add every contract element that has no
        row as NOT_STARTED, supersede (with the contract as evidence) rows a contract retired and, for designs whose
        contract is complete, non-closed rows with no live job that no current contract (or contract master's RTL
        hierarchy) contains.  Returns (per-design summary, contract sources)."""
        known = {n for r in rows for n in [r['element']] + r['variants']}
        try:
            ct = self.contracts.load(known)
        except Exception as e:
            self.log('elements: die contracts: %s' % e); return {}, dict(error=str(e)[:300])
        E, L, R, designs = ct['elements'], ct['rtl_leaves'], ct['retired'], ct['designs']
        dz = {d['design']: d for d in designs}
        complete = {d['target'] for d in designs if d.get('complete')}
        contract_targets = {d['target'] for d in designs}
        def evid(ds):
            return dict(contracts=[dict(design=d['design'], revision=d['revision'], doc=d.get('doc'),
                                        sources=[x['path'] for x in d['sources']]) for d in ds])
        def native(x):
            out = [dict(c) for c in x.get('checks', [])[:3]]
            return out or None
        def die_rows(x, ds, role=None, parents=None, via=None):
            return [dict(design=d, label=dz[d]['label'], revision=dz[d]['revision'], role=role or x['roles'].get(d),
                         parents=sorted(parents if parents is not None else x['parents'].get(d, ())), via=via) for d in ds]
        by_name = {}
        for r in rows:
            for n in [r['element']] + r['variants']: by_name.setdefault(n, r)
        for r in rows:
            names = [r['element']] + r['variants']
            r['dies'] = None; r['owner_stream'] = None; r['native'] = None; r['contract'] = None
            mem = next(((n, E[n]) for n in names if n in E), None)
            leaf = next(((n, L[n]) for n in names if n in L), None)
            if mem:
                n, x = mem
                r['dies'] = die_rows(x, x['designs'], via=n if n != r['element'] else None)
                r['owner_stream'] = die_contracts.Contracts.stream(designs, x['designs'][0], r['element'], x['stream'])
                r['native'] = native(x)
                r['contract'] = 'in current contract'
            elif leaf:
                n, x = leaf; ds = sorted(x['designs'])
                r['dies'] = die_rows(x, ds, role='leaf (RTL hierarchy)', parents=x['parents'], via=n if n != r['element'] else None)
                r['owner_stream'] = die_contracts.Contracts.stream(designs, ds[0], r['element'])
                r['contract'] = 'in current contract (RTL hierarchy of %s)' % ', '.join(sorted(x['parents'])[:4])
            if r['dies']:
                if r['category'] == CATS[11]: r['category'] = NOT_STARTED; r['via'] = r['via'] or 'implementation recorded, no physical job'
                continue
            ret = next(((n, R[n]) for n in names if n in R), None)
            if ret and r['category'] != 'superseded':
                n, v = ret
                r['category'] = 'superseded'; r['closed_t'] = None
                r['superseded'] = dict(by=v.get('by'), reason='retired by the current %s contract: %s' % (v.get('label'), v.get('evidence')),
                                       source_evidence=evid([dz[v['design']]]))
                r['supersession_source_evidence_missing'] = False; r['via'] = 'superseded by %s (die contract)' % v.get('by')
                r['contract'] = 'retired by contract'
            elif r['target'] in complete and r['category'] != 'superseded':
                if r['category'].startswith('closed') or r['live']:
                    r['contract'] = 'not linked to a current contract master (kept: %s)' % ('closed' if r['category'].startswith('closed') else 'live job')
                else:
                    ds = [d for d in designs if d['target'] == r['target']]
                    r['category'] = 'superseded'
                    r['superseded'] = dict(by='current %s die contracts' % r['target'],
                                           reason='not in any current die contract (%s) nor in a contract master\'s RTL hierarchy; no live job, not closed'
                                           % '; '.join('%s %s' % (d['label'], d['revision']) for d in ds), source_evidence=evid(ds))
                    r['supersession_source_evidence_missing'] = False; r['via'] = 'not in current die contract'
                    r['contract'] = 'not in current contract'
            elif r['target'] in contract_targets and r['category'] != 'superseded':
                r['contract'] = 'not in current contract (contract incomplete: unlisted rows keep their loop state)'
        added = 0
        for e, x in E.items():
            if e in by_name or all(v in ('macro', 'soft') for v in x['roles'].values()): continue
            d0 = x['designs'][0]
            kids = [by_name[k] for k, y in E.items() if k in by_name and any(e in y['parents'].get(d, ()) for d in y['designs'])]
            kids += [by_name[k] for k, y in L.items() if k in by_name and e in y['parents']]
            nk = len(kids); nc = sum(1 for k in kids if k['category'].startswith('closed'))
            stream = die_contracts.Contracts.stream(designs, d0, e, x['stream'])
            rows.append(dict(element=e, target=dz[d0]['target'], variants=[], category=NOT_STARTED,
                             via=('%d of %d contract leaves closed' % (nc, nk)) if nk else 'no closure-loop job yet',
                             purpose=self.desc.get(e, [e], []) or ('%s %s of %s' % (dz[d0]['label'], x['roles'].get(d0), ', '.join(x['evidence'][:2]))),
                             **self.desc.info(e), jobs=0, live=0, failed=0, closed_jobs=0,
                             best=dict(tt=None, ff=None, ss=None, drc=None, job=None, corner=None, source_commit=None),
                             area=None, revoked=None, latest=None, closed_t=None, owner=stream or '', owner_orig='',
                             evidence_history=[], qualification=None, superseded=None, supersession_source_evidence_missing=None,
                             throughput=None, gate=gate_text(NOT_STARTED, None), _host=None, _base=None,
                             dies=die_rows(x, x['designs']), owner_stream=stream, native=native(x), contract='in current contract'))
            added += 1
        dsum = {}
        for d in designs:
            c = collections.Counter()
            for r in rows:
                if not r.get('dies') or not any(x['design'] == d['design'] for x in r['dies']): continue
                if r['category'] == 'superseded': c['superseded'] += 1; continue
                b = 'closed' if r['category'].startswith('closed') else BUCKET.get(r['category'], 'failed')
                c[b] += 1
            c['open'] = c['in_flight'] + c['failed'] + c['not_started']
            dsum[d['design']] = dict(label=d['label'], target=d['target'], revision=d['revision'], lead=d.get('lead'),
                                     complete=bool(d.get('complete')), closed=c['closed'], open=c['open'],
                                     in_flight=c['in_flight'], failed=c['failed'], not_started=c['not_started'],
                                     superseded=c['superseded'], total=c['closed'] + c['open'], errors=d['errors'])
        unlinked = {}
        for t in sorted(contract_targets):
            c = collections.Counter(r['contract'] or '' for r in rows if r['target'] == t)
            unlinked[t] = {k: v for k, v in c.items() if k.startswith('not linked') or k.startswith('not in current contract (')}
        src = dict(config=ct['config'], added_not_started=added, unlinked=unlinked, designs=[dict(design=d['design'], sources=d['sources'], errors=d['errors'],
                   complete=bool(d.get('complete')), note=d.get('note')) for d in designs])
        return dsum, src

    def element(self, m, g, ob, rest, rj=None):
        rj = rj or {}
        blocks = sorted({j['block'] for j in g} | ({m} if not g else set()))
        rev_blocks = ob.get('revoked', {}); okb = ob.get('closed', {})
        for j in g:   # option-B judgements on the job itself
            r = rest.get(j['name'])
            if r and j['tt'] is None:
                j['tt'] = _f(r.get('setup_verdict_ws_ps') if r.get('setup_verdict_ws_ps') is not None else r.get('ttlb_ws_ps'))
        live = [j for j in g if j['status'] in LIVE]
        # An unknown/diagnostic status is a coverage gap, never evidence of cancellation.
        unclassified = [j for j in g if j['status'] not in LIVE | FAIL | {'CLOSED', 'CANCELLED'}]
        failed = [j for j in g if j['status'] in FAIL] + unclassified
        closed = [j for j in g if j['status'] == 'CLOSED']
        job_rev = [j for j in closed if j['name'] in rj]   # per-job revocations (any era)
        closed_ok = [j for j in closed if j['name'] not in rj]
        tt_closed = [j for j in closed_ok if j['tt_corner'] or (j['closed_t'] or 0) >= T0]
        early = [j for j in closed_ok if j not in tt_closed]
        def revoked(j):
            r = rest.get(j['name'])
            return (j['block'] in rev_blocks and rev_blocks[j['block']].get('job') in (None, j['name'])) or \
                   (r is not None and r.get('verdict') != 'CLOSED_TT') or (j['block'] in rev_blocks and j['block'] not in okb)
        early_rev = [j for j in early if revoked(j)]
        early_ok = [j for j in early if j not in early_rev]
        reverified = [j for j in early_ok if j['block'] in okb or (rest.get(j['name']) or {}).get('verdict') == 'CLOSED_TT']
        ob_only = [b for b in blocks if b in okb and okb[b].get('job') not in rj]
        best = None; closed_t = None; via = ''
        if tt_closed:
            cat = CATS[0]; best = max(tt_closed, key=lambda j: j['closed_t'] or 0); closed_t = best['closed_t']
        elif reverified or ob_only:
            cat = CATS[1]
            if reverified: best = max(reverified, key=lambda j: j['closed_t'] or 0); closed_t = best['closed_t']
            via = 'option-B restatus'
        elif early_ok:
            cat = CATS[2]; best = max(early_ok, key=lambda j: j['closed_t'] or 0); closed_t = best['closed_t']
        elif early_rev or job_rev or any(b in rev_blocks for b in blocks):
            cat = CATS[5] if live else CATS[6]
            via = ' + '.join(x for x in (('link budget' if early_rev or any(b in rev_blocks for b in blocks) else ''),
                                         ('per-job revocation' if job_rev else '')) if x)
        elif live and not failed: cat = CATS[3]
        elif live: cat = CATS[4]
        elif failed:
            cat = CATS[7] if any(j['status'] in REDESIGN for j in failed) else CATS[8]
            if unclassified: via = 'unclassified job states: ' + ', '.join(sorted({j['status'] for j in unclassified}))
        elif g and all(j['status'] == 'CANCELLED' for j in g): cat = CATS[9]
        else:
            cat = CATS[8]; via = 'no classified physical job evidence'
        jr = max(job_rev, key=lambda j: j['closed_t'] or 0) if job_rev else None
        if best is None and jr and cat in CATS[5:7]:   # show the revoked closure with its re-timed FF
            best = dict(jr, ff=_f(rj[jr['name']].get('ff_ps')))
        if best is None:
            cand = [j for j in g if j['has_m'] and (j['tt'] is not None or j['ss'] is not None or j['ff'] is not None)]
            def score(j):
                s = j['tt'] if j['tt'] is not None else j['ss']
                return (j['drc'] == 0, min(x for x in (s, j['ff'], 1e9) if x is not None), j['updated'])
            best = max(cand, key=score) if cand else None
        tm = dict(tt=None, ff=None, ss=None, drc=None, job=None, corner=None, source_commit=None)
        if best:
            tm = dict(tt=best['tt'], ff=best['ff'], ss=best['ss'], drc=best['drc'], job=best['name'],
                      corner='TT' if best['tt_corner'] else 'SS', source_commit=best.get('source_commit'))
        elif ob_only:
            o = okb[ob_only[0]]
            tm = dict(tt=_f(o.get('tt_lb_ps') if o.get('tt_lb_ps') is not None else o.get('tt_ps')), ff=_f(o.get('ff_ps')),
                      ss=_f(o.get('ss_sensitivity_ps')), drc=o.get('drc'), job=o.get('job'), corner='TT', source_commit=o.get('source_commit'))
        lj = max(g, key=lambda j: j['et']) if g else None
        a = self.area.get(tm['job'] or '') or {}
        rv = rev_blocks.get(m) or next((rev_blocks[b] for b in blocks if b in rev_blocks), None)
        revd = None
        if cat in CATS[5:7]:
            if jr:
                e = rj[jr['name']]
                revd = dict(verdict='revoked', reason=e.get('reason'), ff=_f(e.get('ff_ps')), by=e.get('by'), at=e.get('at'),
                            jobs={j['name']: _f(rj[j['name']].get('ff_ps')) for j in job_rev},
                            tt_lb=rv.get('tt_link_budget_ps') if rv else None)
            elif rv: revd = dict(verdict=rv.get('verdict'), tt_lb=rv.get('tt_link_budget_ps'))
        latest = dict(t=lj['et'], job=lj['name'], status=lj['status'], text=lj['event']) if lj else None
        if jr and cat in CATS[5:7]:
            e = rj[jr['name']]
            rt = 'REVOKED %s: %s (re-timed FF %s ps)' % (jr['name'], e.get('reason', ''), e.get('ff_ps'))
            latest = dict(t=max(ts(e.get('at', '')), lj['et'] if lj else 0), job=lj['name'] if lj else jr['name'],
                          status=lj['status'] if lj else 'REVOKED', text=(rt + (' | ' + lj['event'] if lj else ''))[:400])
        return dict(element=m, target=target(m, *(next(((j['owner'], j['branch']) for j in g), ('', '')))),
                    variants=[b for b in blocks if b != m], category=cat, via=via,
                    purpose=self.desc.get(m, blocks, [j['purpose'] for j in sorted(g, key=lambda j: j['created'])]),
                    **self.desc.info(m),
                    jobs=len(g), live=len(live), failed=len(failed), closed_jobs=len(closed),
                    best=tm, area=dict(die=a.get('die'), core=a.get('core'), util=a.get('util')) if 'err' not in a and a else None,
                    revoked=revd, latest=latest,
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
            return dict(t=d['t'], safe=True, cats=CATS, targets=TARGETS, summary=d['summary'], flow=d.get('flow'),
                        designs=d.get('designs'), v=v)
        return dict(d, rows=[public(r) for r in d['rows']],
                    independent_rows=[public(r) for r in d.get('independent_rows', d['rows'])],
                    integration_rows=[public(r) for r in d.get('integration_rows', [])], v=v)

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
        if d.get('designs'):
            L += ['', '## Per die (current contracts, %s)' % die_contracts.CONFIG, '',
                  '| die | revision | closed | open | in flight | failed | not started | superseded |', '|---|---|---:|---:|---:|---:|---:|---:|']
            for k, s in d['designs'].items():
                L.append('| %s | %s | %d | %d | %d | %d | %d | %d |' % (s['label'], _md(s['revision']), s['closed'], s['open'],
                         s['in_flight'], s['failed'], s['not_started'], s['superseded']))
        for t in TARGETS:
            rs = [r for r in d.get('independent_rows', d['rows']) if r['target'] == t]
            if not rs: continue
            L += ['', '## %s (%d)' % (t, len(rs)), '',
                  '| element | status | throughput | what it is | qualification | TT | FF | SS | DRC | die µm² | util | jobs live/failed/total | closed | latest |',
                  '|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|']
            for r in rs:
                b = r['best']; a = r['area'] or {}
                fmt = lambda x: '' if x is None else ('%+.1f' % x)
                L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %d/%d/%d | %s | %s |' % (
                    r['element'] + (' (+%d variants)' % len(r['variants']) if r['variants'] else ''), r['category'],
                    _md(throughput_text(r.get('throughput'))),
                    _md(r['purpose'][:120]), _md(qualification_text(r.get('qualification'))), fmt(b['tt']), fmt(b['ff']), fmt(b['ss']), '' if b['drc'] is None else b['drc'],
                    '' if a.get('die') is None else '%.0f' % a['die'], '' if a.get('util') is None else '%.0f%%' % (100 * a['util']),
                    r['live'], r['failed'], r['jobs'],
                    datetime.datetime.fromtimestamp(r['closed_t']).strftime('%m-%d %H:%M') if r['closed_t'] else '',
                    _md(('%s %s: %s' % (datetime.datetime.fromtimestamp(r['latest']['t']).strftime('%m-%d %H:%M'), r['latest']['status'],
                                          r['latest']['text']))[:140]) if r['latest'] else ''))
        if d.get('integration_rows'):
            L += ['', '## Integration backlog (excluded from independent-master closure counts)', '']
            for r in d['integration_rows']:
                L.append('- %s: %s; %s. Evidence: %s' % (r['element'], r['category'], r['integration_status'],
                         ', '.join(r['identity_evidence'].get('evidence', []))))
        try:
            self.md_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.md_path.with_suffix('.tmp'); tmp.write_text('\n'.join(L) + '\n'); tmp.replace(self.md_path)
        except OSError as e:
            self.log('elements md: %s' % e)

def public(r):
    return {k: ([public(x) for x in v] if k == 'replica_records' else v)
            for k, v in r.items() if not k.startswith('_')}

def change_key(d):
    """What makes an element snapshot worth recording now (not the per-minute latest-event churn)."""
    return hash((tuple((r['element'], r['category'], r['live'], r['failed'], r['jobs'], r['best']['job'], r.get('contract'),
                       json.dumps(r.get('evidence_history', []), sort_keys=True),
                       (r.get('throughput') or {}).get('status'), (r.get('throughput') or {}).get('ratio')) for r in d['rows']), json.dumps(d.get('master_identity', {}), sort_keys=True)))

def honest_throughput(v):
    """Registry honesty (owner 2026-10-13, el1013-rule-enforcement): a unit with a price but no measured production
    ratio is UNMEASURED, never QUALIFIED.  Applied to the element entry, its limiting op and every op row of a budget
    entry as read (the committed budget.json predates the rule; tools/throughput_budget/build.py now writes it too)."""
    def fix(o):
        if isinstance(o, dict) and o.get('status') == 'QUALIFIED' and not isinstance(o.get('ratio'), (int, float)):
            o = dict(o, status='UNMEASURED', status_was='QUALIFIED')
        return o
    if not isinstance(v, dict): return v
    v = dict(v)
    if isinstance(v.get('ops'), list): v['ops'] = [fix(o) for o in v['ops']]
    if isinstance(v.get('limiting'), dict): v['limiting'] = fix(v['limiting'])
    return fix(v)

def gate_text(category, tq):
    """AGENTS.md throughput qualification: timing closure alone never qualifies a unit."""
    timing = 'CLOSED-TIMING' if category.startswith('closed') else 'OPEN-TIMING'
    if not tq: return timing + ', NO-THROUGHPUT-BUDGET-ROW'
    st = tq.get('status')
    return timing + (', THROUGHPUT-QUALIFIED' if st == 'QUALIFIED' else ', THROUGHPUT-QUALIFIED-BY-BOUND' if st == 'QUALIFIED_BY_BOUND'
                     else ', THROUGHPUT-ACCEPTED' if st == 'ACCEPTED' else ', THROUGHPUT-EXEMPT' if st == 'EXEMPT'
                     else ', THROUGHPUT-UNMEASURED' if st == 'UNMEASURED'
                     else ', THROUGHPUT-UNQUALIFIED')

def throughput_text(tq):
    if not tq: return ''
    lim = tq.get('limiting') or {}
    r = tq.get('ratio')
    return '%s%s (%s %s)' % (tq['status'], '' if r is None else ' %.2fx' % r, lim.get('model', ''), lim.get('op', ''))

def qualification_text(q):
    if not q: return ''
    exact = q.get('exactness') or {}
    status = lambda x: (x or {}).get('status', 'unrecorded')
    return 'source %s; RTL %s; model %s; exact +%s / -%s; physical %s; corners %s; dependencies %s; integration %s; record %s' % (
        q['source']['commit'], status(q.get('implementation')), status(q.get('model')),
        status(exact.get('positive')), status(exact.get('negative')), status(q.get('physical')),
        json.dumps((q.get('physical') or {}).get('corners', {}), sort_keys=True), ', '.join(q.get('dependencies', [])),
        status(q.get('integration')), q['registry_path'])

def _md(s):
    return str(s).replace('|', '\\|').replace('\n', ' ')

def _shq(s):
    return "'" + s.replace("'", "'\\''") + "'"
