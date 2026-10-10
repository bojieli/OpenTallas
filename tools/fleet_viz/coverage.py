"""Coverage view for the fleet visualiser (/explorer/coverage, /api/coverage, /api/coverage/token).

Source of truth: results/arch/coverage_20261008/ in the repository: the four node ledgers T1..T4.json (one per target),
MATRIX.json and gen_matrix.py (row normalisation, owners, token-path mapping).  They are read from the git tree
`origin/main` (every push from any worktree of the repo moves that ref), or from $FLEET_VIZ_COVERAGE_DIR when set.  When
the tree hash changes, gen_matrix.build() re-derives the matrix, so a stream that edits its ledger moves the view
within one poll.  The live closure status of each cell's elements is joined from the Elements collector on every request.
"""
import json, os, pathlib, subprocess, threading, time, types

REL = 'results/arch/coverage_20261008'
CLOSED_CATS = ('closed (TT era)', 'closed (TT re-verified)', 'closed (earlier)')
INFLIGHT_CATS = ('first trial in flight', 'failed, re-running', 'revoked, re-running')

class Coverage:
    def __init__(self, repo, elements, token_dir, log=print, ref='origin/main', period=15):
        self.repo, self.elements, self.token_dir, self.log, self.ref, self.period = str(repo), elements, pathlib.Path(token_dir), log, ref, period
        self.fsdir = os.environ.get('FLEET_VIZ_COVERAGE_DIR')
        self.lock = threading.Lock()
        self.key = None; self.checked = 0; self.mod = None; self.matrix = None; self.err = None; self.tok = {}; self.src = None

    # ---- source
    def _git(self, *a):
        return subprocess.run(['git', '-C', self.repo] + list(a), capture_output=True, timeout=20, check=True).stdout

    def _source(self):
        """(key, reader) of the current ledger set."""
        if self.fsdir:
            d = pathlib.Path(self.fsdir)
            key = tuple(sorted((p.name, p.stat().st_mtime_ns) for p in d.glob('*') if p.suffix in ('.json', '.py')))
            return ('fs', key), (lambda n: (d / n).read_text() if (d / n).exists() else None), str(d)
        tree = self._git('rev-parse', '%s:%s' % (self.ref, REL)).decode().strip()
        def read(n, tree=tree):
            try: return self._git('show', '%s:%s' % (tree, n)).decode()
            except subprocess.CalledProcessError: return None
        return ('git', tree), read, '%s:%s (tree %s)' % (self.ref, REL, tree[:10])

    def refresh(self, force=False):
        now = time.time()
        with self.lock:
            if not force and self.matrix is not None and now - self.checked < self.period: return
            self.checked = now
        try:
            key, read, label = self._source()
        except Exception as e:
            with self.lock: self.err = 'coverage source: %s' % e
            return
        if key == self.key and self.matrix is not None: return
        try:
            code = read('gen_matrix.py')
            if code is None: raise RuntimeError('gen_matrix.py not in %s' % label)
            mod = types.ModuleType('gen_matrix'); mod.__file__ = 'gen_matrix.py'
            exec(compile(code, '%s/gen_matrix.py' % REL, 'exec'), mod.__dict__)
            led = mod.load_ledgers(read)
            names = []
            try: names = [r['element'] for r in self.elements.snapshot(False).get('rows', [])]
            except Exception: pass
            m = mod.build(led, names)
            try:
                stored = json.loads(read('MATRIX.json') or '{}')
                m['streams'] = {k: dict(v, **{kk: vv for kk, vv in stored.get('streams', {}).get(k, {}).items() if kk not in v})
                                for k, v in m['streams'].items()}
                m['plan'] = REL + '/PLAN.md'
                m['token_paths'] = stored.get('token_paths')
            except ValueError:
                pass
            try: m['streams_live'] = mod.verify_streams()
            except Exception: m['streams_live'] = {}
            m['source'] = label; m['loaded'] = time.strftime('%Y-%m-%d %H:%M:%S')
            m['v'] = str(key[1])[:16] if key[0] == 'git' else str(abs(hash(key[1])))[:12]
            with self.lock:
                self.key, self.mod, self.matrix, self.err, self.tok, self.src = key, mod, m, None, {}, label
            self.log('coverage: loaded %s (%d rows)' % (label, len(m['rows'])))
        except Exception as e:
            with self.lock: self.err = 'coverage build: %s: %s' % (type(e).__name__, e)
            self.log(self.err)

    # ---- API
    def _live(self):
        try: rows = self.elements.snapshot(False).get('rows', [])
        except Exception: rows = []
        return {r['element']: r for r in rows}

    def version(self):
        self.refresh()
        with self.lock:
            return dict(v=self.matrix and self.matrix['v'], err=self.err, source=self.src)

    def api(self):
        self.refresh()
        with self.lock: m, err = self.matrix, self.err
        if m is None: return dict(error=err or 'coverage not loaded')
        live = self._live()
        out = dict(m, rows=[], error=err)
        for r in m['rows']:
            rr = dict(r, cells={})
            for t, c in r['cells'].items():
                c = dict(c)
                els = []
                for e in c.get('elements') or []:
                    x = live.get(e)
                    if not x: continue
                    b = x.get('best') or {}
                    lt = x.get('latest') or {}
                    els.append(dict(element=e, category=x.get('category'), tt=b.get('tt'), ff=b.get('ff'), ss=b.get('ss'), drc=b.get('drc'),
                                    live=x.get('live'), failed=x.get('failed'), owner=x.get('owner'), latest=lt.get('status'), latest_job=lt.get('job')))
                c['live'] = els
                if els:
                    nc = sum(1 for e in els if e['category'] in CLOSED_CATS)
                    nf = sum(1 for e in els if e['category'] in INFLIGHT_CATS)
                    c['live_summary'] = dict(closed=nc, inflight=nf, other=len(els) - nc - nf, total=len(els),
                                             state='closed' if nc == len(els) else 'open')
                rr['cells'][t] = c
            out['rows'].append(rr)
        out['live_t'] = time.time()
        return out

    def token(self, design):
        """{node id: [fids]} for one token-path record, plus the cells those rows have on the design's target."""
        self.refresh()
        with self.lock: m, mod = self.matrix, self.mod
        if m is None or mod is None: return dict(error=self.err or 'coverage not loaded')
        if design not in getattr(mod, 'TP_MAP', {}): return dict(error='no coverage map for %s' % design, design=design)
        p = self.token_dir / 'data' / (design + '.json')
        if not p.is_file(): return dict(error='no token data %s' % design)
        key = (m['v'], design, p.stat().st_mtime_ns)
        with self.lock:
            hit = self.tok.get(design)
            if hit and hit[0] == key: return hit[1]
        rec = json.loads(p.read_text())
        t = mod.TP_MAP[design]['target']
        nodes = {n['id']: mod.tp_rows(design, n) for n in rec['nodes']}
        used = {f for fs in nodes.values() for f in fs}
        rows = {}
        for r in m['rows']:
            if r['fid'] not in used: continue
            c = r['cells'][t]
            rows[r['fid']] = dict(function=r['function'], group=r['group'], state=c.get('state'), owner=c.get('owner'),
                                  gaps=[dict(cls=g['cls'], owner=g['owner'], nodes=g.get('nodes')) for g in c.get('gaps') or []],
                                  ledger_nodes=c.get('nodes'), closure=c.get('closure'))
        res = dict(v=m['v'], design=design, target=t, uncovered=m.get('uncovered_classes'), gap_classes=m.get('gap_classes'),
                   nodes=nodes, rows=rows)
        with self.lock: self.tok[design] = (key, res)
        return res
