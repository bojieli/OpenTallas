#!/usr/bin/env python3
"""Live native pin audit + die-bindable margin file for the fleet-viz element table (FLEETVIZ-ELEM 2026-10-18).

The element table used to read the STATIC results/arch/margin_thin_1016.json (one audit of 1,348 main views, 10-16 18:40),
so every view recorded since (closure-record branches never merged to main, lane audit receipts) read 'native unaudited'.
This tool is run hourly by the user timer fleet-viz-elem-sync.timer and rebuilds the file the viewer reads:

  1. views    every <cell>.lef + <cell>_tt.lib(.gz) directory under physical/ (memory / PHY macro abstracts excluded) on
              origin/main, plus the recorded view directories of every CLOSED closure-loop job's record branch
              origin/codex/closure-record-<job> (spec.record 'to' paths under physical/).  A main view whose loop job is
              known and NOT CLOSED is dropped (same rule as native_pin_audit.py --out).
  2. audit    tools/hier_contract/native_pin_audit.py audit_one (taken from origin/main at run time) on each view, keyed
              by the view directory's git TREE id: only new or changed views are audited (cache in the state dir).
  3. receipts committed lane audit receipts (any JSON under results/arch/ changed on any ref in the last RECEIPT_DAYS
              days whose list items are native_pin_audit records: cell, view, pass, launch_ps).  CTS probes
              (cts-native-probe schema) are diagnostics, not routed qualifications, and are ignored.  Per job / view the
              own audit stands; a committed receipt fills a job the own audit does not cover, and a relative-mode
              receipt PASS (owner 10-17 0dq clock rule: --relative-to parent compensation / neighbour) or a case-pin
              receipt PASS (native_pin_audit --case: strap pins the die SDC set_case_analysis-es; record case_pins, or
              the superseded S81-MISC static_pins) overrides an own-R FAIL of the same view.
  4. margin   margin_thin.native_of per record -> {state}/margin_live.json (schema opentallas.margin_thin.v1, 'views'
              list: the input of elements.py apply_die_bindable).  The viewer prefers this file over the committed one.

    native_sync.py [--repo /home/ubuntu/OpenTallas] [--state ~/.local/state/fleet-viz] [--jobs 6] [--limit N]
"""
import argparse, collections, datetime, gzip, importlib, json, multiprocessing as mp, os, pathlib, re, shutil, subprocess, sys, \
    tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import margin_thin  # noqa: E402

JOBS = pathlib.Path(os.environ.get('CL_STATE', str(pathlib.Path.home() / '.local/state/closure_loop'))) / 'jobs'
RECEIPT_DAYS = 6
REC_PREFIX = 'refs/remotes/origin/codex/closure-record-'
MACRO_RE = re.compile(r'(asap7_memory_macros|_macros_v\d|pdie_macros|/hard_ip/|/phy/|qwen_missing_phy/)')
VIEW_FILES = ('{c}_tt.lib', '{c}_tt.lib.gz', '{c}_ff.lib', '{c}_ff.lib.gz', 'insertion.json', 'abstract.json', 'export.json')
JOB_RE = re.compile(r'/closure-loop/([^/]+)/')


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


class Git:
    def __init__(self, repo):
        self.gd = str(pathlib.Path(repo) / '.git') if (pathlib.Path(repo) / '.git').exists() else str(repo)
        self.batch = None

    def run(self, *a, timeout=600):
        return subprocess.run(['git', '--git-dir', self.gd, *a], capture_output=True, text=True, timeout=timeout).stdout

    def blob(self, spec):
        """bytes of <rev>:<path> or a blob id; None when absent."""
        if self.batch is None or self.batch.poll() is not None:
            self.batch = subprocess.Popen(['git', '--git-dir', self.gd, 'cat-file', '--batch'], stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE)
        p = self.batch
        p.stdin.write((spec + '\n').encode()); p.stdin.flush()
        head = p.stdout.readline().decode().split()
        if len(head) != 3:
            return None
        data = p.stdout.read(int(head[2])); p.stdout.read(1)
        return data if head[1] == 'blob' else None


def tree_views(git, ref, paths):
    """-> {view_dir: (tree_id, {file: blob})} for directories holding <c>.lef + <c>_tt.lib(.gz) under paths."""
    out = git.run('ls-tree', '-r', '-t', ref, '--', *paths)
    trees, files = {}, collections.defaultdict(dict)
    for ln in out.splitlines():
        meta, _, path = ln.partition('\t')
        parts = meta.split()
        if len(parts) != 3: continue
        if parts[1] == 'tree': trees[path] = parts[2]
        elif parts[1] == 'blob':
            d, _, f = path.rpartition('/')
            files[d][f] = parts[2]
    views = {}
    for d, fs in files.items():
        if MACRO_RE.search(d + '/') or '/work/' in d or '/routes/' in d: continue
        for f in fs:
            if f.endswith('.lef'):
                c = f[:-4]
                if (c + '_tt.lib' in fs or c + '_tt.lib.gz' in fs) and d in trees:
                    views.setdefault(d, []).append((c, trees[d], fs))
    return views


def job_status(name, cache={}):
    if not name: return None
    if name not in cache:
        try: cache[name] = json.loads((JOBS / (name + '.json')).read_text()).get('status')
        except (OSError, ValueError): cache[name] = 'UNKNOWN_JOB'
    return cache[name]


def closed_jobs():
    """CLOSED loop jobs -> (block, record 'to' paths under physical/)."""
    out = {}
    for f in os.scandir(JOBS):
        if not f.name.endswith('.json'): continue
        try: d = json.loads(pathlib.Path(f.path).read_text())
        except (OSError, ValueError): continue
        if d.get('status') != 'CLOSED': continue
        s = d.get('spec') or {}
        tos = sorted({str(r.get('to')) for r in s.get('record') or [] if isinstance(r, dict)
                      and str(r.get('to', '')).startswith('physical/')})
        out[d.get('name') or f.name[:-5]] = (s.get('block'), tos)
    return out


_NPA = None


def _init(tools_dir):
    global _NPA
    sys.path.insert(0, tools_dir)
    _NPA = importlib.import_module('native_pin_audit')


def _audit(arg):
    root, cell, view = arg
    try:
        return _NPA.audit_one((root, cell, view, None))
    except Exception as e:  # noqa: BLE001
        return dict(cell=cell, view=view, error='%s: %s' % (type(e).__name__, str(e)[:200]))


def stage_tools(git, state, ref='origin/main'):
    rev = git.run('rev-parse', ref).strip()
    d = state / 'native_tools' / rev[:12]
    if not (d / 'native_pin_audit.py').exists():
        tmp = d.with_suffix('.tmp'); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
        for ln in git.run('ls-tree', ref, 'tools/hier_contract/').splitlines():
            meta, _, path = ln.partition('\t')
            if path.endswith('.py'):
                (tmp / os.path.basename(path)).write_bytes(git.blob(meta.split()[2]) or b'')
        shutil.rmtree(d, ignore_errors=True); tmp.rename(d)
        for old in sorted((state / 'native_tools').iterdir())[:-3]:
            if old != d: shutil.rmtree(old, ignore_errors=True)
    return d, rev


def harvest_receipts(git, days=RECEIPT_DAYS):
    """-> list of (commit time, path, record) from committed audit receipts on every ref."""
    raw = git.run('log', '--all', '--since=%d.days' % days, '--format=C %H %ct', '--raw', '--no-abbrev', '--diff-filter=AM',
                  '--', 'results/arch/', timeout=900)
    cand, ct = {}, 0
    for ln in raw.splitlines():
        if ln.startswith('C '):
            ct = int(ln.split()[2]); continue
        if not ln.startswith(':'): continue
        meta, _, path = ln.partition('\t')
        if not path.endswith('.json') or not re.search(r'native|audit|owners_', path, re.I): continue
        blob = meta.split()[3]
        if blob not in cand or ct > cand[blob][0]: cand[blob] = (ct, path)
    out = []
    for blob, (t, path) in cand.items():
        data = git.blob(blob)
        if not data or len(data) > 20e6 or b'"launch_ps"' not in data or b'"pass"' not in data: continue
        try: doc = json.loads(data)
        except ValueError: continue
        if isinstance(doc, dict) and 'cts-native-probe' in str(doc.get('schema', '')): continue
        lists = [doc] if isinstance(doc, list) else [v for v in doc.values() if isinstance(v, list)] if isinstance(doc, dict) else []
        for L in lists:
            for r in L:
                if isinstance(r, dict) and r.get('cell') and r.get('view') and 'pass' in r and 'launch_ps' in r:
                    out.append((t, path, r))
    return out


RECEIPT_OVERRIDE_KEYS = ('pass', 'fail_why', 'relative_to', 'relative', 'launch_ps', 'launch_pin', 'capture_ps', 'capture_pin',
                         'launch_over', 'capture_over', 'comb_pins', 'case_patterns', 'case_pins', 'case_pins_raw_capture_ps',
                         'case_evidence', 'static_pins', 'static_evidence')


def apply_receipts(views, receipts):
    """merge committed receipts into the own audit records (in place) -> (n_fill, n_override).  Newest receipt per
    job / view / cell.  A receipt fills a job the own audit does not cover; a receipt PASS overrides an own FAIL of the
    same view only when it carries what the own audit cannot know: relative_to (parent / neighbour reference, owner
    10-17 0dq) or non-empty case_pins / static_pins (die-SDC case-analysed straps, NS-CASE 10-18).  A plain
    own-R receipt PASS never beats an own FAIL."""
    by_job_view = {(v.get('job'), v['view'], v['cell']): v for v in views}
    own_jobs = {v.get('job') for v in views if v.get('job')}
    n_fill = n_rel = 0
    best = {}
    for t, path, r in sorted(receipts, key=lambda x: x[0]):
        best[(r.get('job'), r['view'], r['cell'])] = (t, path, r)    # newest receipt per job/view
    for (job, view, cell), (t, path, r) in best.items():
        own = by_job_view.get((job, view, cell))
        if own is None:
            if job and job in own_jobs: continue
            v = dict(r); v.update(src='receipt ' + path, receipt=path); views.append(v); n_fill += 1
        elif own.get('pass') is False and r.get('pass') is True and (r.get('relative_to') or r.get('case_pins') or r.get('static_pins')):
            own_why = own.get('fail_why')
            own.update({k: r.get(k) for k in RECEIPT_OVERRIDE_KEYS if k in r or k in ('pass', 'fail_why')})
            own['receipt'] = path; own['own_fail_why'] = own_why; n_rel += 1
    return n_fill, n_rel


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo', default='/home/ubuntu/OpenTallas')
    ap.add_argument('--state', default=os.path.expanduser('~/.local/state/fleet-viz'))
    ap.add_argument('--jobs', type=int, default=6)
    ap.add_argument('--limit', type=int, default=0, help='audit at most N new views this run (0 = all)')
    a = ap.parse_args(argv)
    t0 = time.time(); state = pathlib.Path(a.state); state.mkdir(parents=True, exist_ok=True)
    git = Git(a.repo)
    tools, tools_rev = stage_tools(git, state)
    main_rev = git.run('rev-parse', 'origin/main').strip()
    cache_p = state / 'native_audit_cache.json'
    try: cache = json.loads(cache_p.read_text())
    except (OSError, ValueError): cache = {}
    if cache.get('tool_sha') != _tool_sha(tools):
        cache = dict(records={})          # the audit code changed: re-audit everything
    cache['tool_sha'] = _tool_sha(tools); cache['tools_rev'] = tools_rev[:12]
    recs = cache.setdefault('records', {})

    # ---- 1. views
    todo = []   # (src, ref, view_dir, cell, tree, files, job)
    for d, lst in tree_views(git, 'origin/main', ['physical']).items():
        for c, tree, fs in lst:
            todo.append(('main', 'origin/main', d, c, tree, fs, None))
    cj = closed_jobs()
    refs = set(git.run('for-each-ref', '--format=%(refname)', REC_PREFIX + '*').split())
    n_rec = 0
    for job, (block, tos) in cj.items():
        ref = REC_PREFIX + job
        if ref not in refs or not tos: continue
        n_rec += 1
        for d, lst in tree_views(git, ref, tos).items():
            for c, tree, fs in lst:
                todo.append(('record', ref, d, c, tree, fs, job))
    log('views: %d (main + %d record branches of %d CLOSED jobs)' % (len(todo), n_rec, len(cj)))

    # ---- 2. audit new trees
    key = lambda x: '%s:%s' % (x[4], x[3])
    new = {}
    for x in todo:
        if key(x) not in recs and key(x) not in new: new[key(x)] = x
    new = list(new.values())
    if a.limit: new = new[:a.limit]
    log('audit: %d new view trees (cache %d)' % (len(new), len(recs)))
    if new:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix='nsync-', dir=str(state)))
        try:
            args = []
            for i, x in enumerate(new):
                src, ref, d, c, tree, fs, job = x
                vd = tmp / str(i) / d; vd.mkdir(parents=True, exist_ok=True)
                for pat in VIEW_FILES:
                    f = pat.format(c=c)
                    if f in fs: (vd / f).write_bytes(git.blob(fs[f]) or b'')
                args.append((str(tmp / str(i)), c, d))
            with mp.Pool(a.jobs, initializer=_init, initargs=(str(tools),)) as pool:
                res = pool.map(_audit, args, chunksize=2)
            for x, r, (root, c, d) in zip(new, res, args):
                src, ref, d, c, tree, fs, job = x
                if not job:
                    for n in ('abstract.json', 'export.json'):
                        p = pathlib.Path(root) / d / n
                        if p.exists():
                            m = JOB_RE.search(p.read_text(errors='replace')[:20000])
                            if m: job = m.group(1); break
                r['job_from_view'] = job
                recs[key(x)] = r
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    cache['updated'] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    tmpc = cache_p.with_suffix('.tmp'); tmpc.write_text(json.dumps(cache)); tmpc.replace(cache_p)

    # ---- 3. assemble own records (+ CLOSED filter for main views), then receipts
    views, seen = [], set()
    dropped = collections.Counter()
    for x in todo:
        src, ref, d, c, tree, fs, job = x
        r = recs.get(key(x))
        if r is None: continue
        job = job or r.get('job_from_view')
        st = job_status(job) if src == 'main' else 'CLOSED'
        if src == 'main' and job and st not in ('CLOSED', 'UNKNOWN_JOB'):
            dropped[st] += 1; continue
        k = (job or '', d, c)
        if k in seen: continue
        seen.add(k)
        v = dict(r); v.update(job=job, src='main' if src == 'main' else ref.replace('refs/remotes/', ''), tree=tree)
        views.append(v)
    receipts = harvest_receipts(git)
    n_fill, n_rel = apply_receipts(views, receipts)
    log('receipts: %d records, %d fill uncovered jobs, %d relative/case PASS over own FAIL' % (len(receipts), n_fill, n_rel))

    # ---- 4. margin file
    out = []
    for v in views:
        nat, why = margin_thin.native_of(v)
        out.append(dict(cell=v.get('cell'), view=v.get('view'), job=v.get('job'), native=nat, native_why=why,
                        launch_ps=v.get('launch_ps'), capture_ps=v.get('capture_ps'), spread_ps=v.get('spread_ps'),
                        ff_spread_ps=v.get('ff_spread_ps'), R_ps=v.get('R_ps'), src=v.get('src'), receipt=v.get('receipt'),
                        relative_to=v.get('relative_to'), case_pins=v.get('case_pins') or v.get('static_pins')))
    c = collections.Counter(x['native'] for x in out)
    doc = dict(schema='opentallas.margin_thin.v1', generator='tools/fleet_viz/native_sync.py',
               generated=datetime.datetime.now().astimezone().isoformat(timespec='seconds'), source_main=main_rev,
               audit_tool='tools/hier_contract/native_pin_audit.py @ ' + tools_rev[:12],
               rule=dict(native='launch<=220, capture<=190 ps TT, no comb pin, TT/FF pin-flop spread<=80 ps, insertion.json present',
                         binding='native PASS only', note='closure is NOT revoked'),
               counts=dict(views=len(out), native_pass=c['PASS'], native_fail=c['FAIL'], dropped_not_closed=dict(dropped),
                           record_branches=n_rec, receipts=len(receipts), receipt_fill=n_fill, receipt_relative_pass=n_rel),
               views=out)
    p = state / 'margin_live.json'; tmpm = p.with_suffix('.tmp')
    tmpm.write_text(json.dumps(doc, indent=0) + '\n'); tmpm.replace(p)
    log('margin_live.json: %d views, PASS %d / FAIL %d, %.0f s' % (len(out), c['PASS'], c['FAIL'], time.time() - t0))
    return 0


def _tool_sha(d):
    import hashlib
    h = hashlib.sha256()
    for n in ('native_pin_audit.py', 'pinreg_audit.py'):
        try: h.update((pathlib.Path(d) / n).read_bytes())
        except OSError: pass
    return h.hexdigest()[:16]


if __name__ == '__main__':
    sys.exit(main())
