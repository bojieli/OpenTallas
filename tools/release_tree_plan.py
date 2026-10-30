#!/usr/bin/env python3
"""Current-plan element layer for the release tree (INFRA lane, 2026-10-24; replaces the obsolete 10-21 element list).

Per die plan on origin/main:
  * G0C-clean partition types / total types   -- tools/die_plan/check.py --completeness, run from a git archive of
    origin/main in a tmp dir (cheap: ~90 s, < 1 GB, all five plans in sequence)
  * partition types and hard cores with a SIGNED signoff view -- signoff.py records (schema opentallas.signoff.v1,
    verdict SIGNED) found on origin/main (*signoff.json) and on every fleet host under /srv/opentallas-scratch{,2}
    (KIT/signoff/signoff.json, <kit>/signoff_tt_ff/signoff.json, ...). A record counts for a type when its
    face_guard top (or its name without the dp_/kr_ prefix) is the type's module/key, for a hard core when it is the
    core's module.
Closure order rule 3 (owner 2026-10-25 18:45, INFRA2): a SIGNED record counts only when it names its source commit +
flow release tag -- 'src_commit'/'flow_tag' in the signoff.json itself, else in the nearest PROVENANCE.json (verdict
SIGNED, written by the autopilot archive) or AUTOPILOT.json up to 6 directories above it.  Every record carries
'versioned'; signed_types/signed_cores hold versioned records only, unversioned_types/unversioned_cores the rest;
the cache says provenance_rule 'v1' (tools/autopilot/ownership.py counts only such caches).
RE-SIGN (COORD ruling 2026-10-30 02:03 (3b)): a hand-built SIGNED block counts when its SAME routed DB is re-signed
(signoff.py TT/FF/DRC + post-route LEC) with tools at a released flow tag; the re-sign dir holds signoff.json and a
PROVENANCE.json {kind: 'resign', verdict: 'SIGNED', src_commit: <tag commit>, flow_tag, routed_db, build_commit, lec}.
It counts only with all fields, LEC verdict EQUIVALENT, the routed DB present and flow_tag -> src_commit on origin.
GRANDFATHER (COORD ruling 2026-10-25 19:13): a SIGNED record completed before the first flow-* tag on origin (or while
no flow tag exists) counts as SIGNED-LEGACY -- in signed_types/signed_cores, ref suffixed 'SIGNED-LEGACY' -- when it
names a source commit or a run dir (its scanned path is the run dir; origin/main records name main).  The
src_commit + flow_tag requirement applies only to records generated after the first tag.
Cached in ~/.local/state/fleet-viz/release_tree_plan_cache.json; refreshed when older than REFRESH_S (the hourly
release-tree-render.timer calls this through release_tree_render.py). On any failure the last good per-die values are
kept and the error is reported (the page keeps rendering).
Run alone: python3 tools/release_tree_plan.py [--force] [--print]
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time, concurrent.futures as cf

REPO = pathlib.Path('/home/ubuntu/OpenTallas')
CACHE = pathlib.Path.home() / '.local/state/fleet-viz/release_tree_plan_cache.json'
REFRESH_S = 50 * 60
# release-tree die key -> plan dir under physical/die_plan (five dies; HBM = current B2n lineage on main; epyc3 retired 10-25)
PLANS = [('s81', 's81'), ('s81_head', 's81_head'), ('qwen_compute', 'qwen_compute'), ('qwen_kvsys', 'qwen_kvsys'),
         ('hbm', 'hbm_arch/B2n')]
HOSTS = ['local', 'epyc2', 'intel1', 'intel2']
SCAN_ROOTS = '/srv/opentallas-scratch /srv/opentallas-scratch2'
# RETIRED sign-offs (HEAD-CORE-R13 2026-10-27): a SIGNED record of a superseded build (older RTL / flow) that must not
# count for the current design. One line per record: '<scan_host>:<path>\t<date>\t<lane>\t<reason>' ('#' = comment).
# Matching records are dropped from signed_records / signed_* and listed in retired_records (visible, not deleted).
RETIRED = pathlib.Path(__file__).resolve().parent.parent / 'RETIRED_SIGNOFFS.tsv'


def retired_refs():
    try: lines = RETIRED.read_text().splitlines()
    except Exception: return {}
    out = {}
    for ln in lines:
        if not ln.strip() or ln.startswith('#'): continue
        f = ln.split('\t')
        out[f[0].strip()] = '\t'.join(f[1:]).strip()
    return out
PROV_PY = r'''
RESIGN_KEYS = ('src_commit', 'flow_tag', 'routed_db', 'build_commit', 'lec')
def resign(f, x, load):
    # COORD ruling 2026-10-30 02:03 (3b): RE-SIGN record = a routed DB re-checked (signoff.py TT/FF/DRC + post-route LEC)
    # with tools at a released flow tag.  PROVENANCE.json {kind: resign, src_commit: tag commit, flow_tag, routed_db,
    # build_commit: original build commit, lec: post-route lec.json}.  Counts only when every field is present, the
    # routed DB exists and the LEC verdict is EQUIVALENT; the tag -> src_commit match is checked on the hub (refresh).
    miss = [k for k in RESIGN_KEYS if not x.get(k)]
    if miss:
        return dict(resign_error='re-sign PROVENANCE %s lacks %s' % (f, ','.join(miss)), prov_file=f)
    lp = x['lec'] if os.path.isabs(x['lec']) else os.path.join(os.path.dirname(f), x['lec'])
    db = x['routed_db'] if os.path.isabs(x['routed_db']) else os.path.join(os.path.dirname(f), x['routed_db'])
    try:
        lv = (load(lp) or {}).get('verdict')
    except Exception:
        lv = None
    if lv != 'EQUIVALENT':
        return dict(resign_error='re-sign LEC %s verdict %s' % (lp, lv), prov_file=f)
    if not os.path.exists(db):
        return dict(resign_error='re-sign routed DB %s missing' % db, prov_file=f)
    return dict(src_commit=x['src_commit'], flow_tag=x['flow_tag'], prov_file=f, resign=True, routed_db=db,
                build_commit=x['build_commit'], lec=lp)
def prov(p, d, load):
    if d.get('src_commit') and d.get('flow_tag'):
        return dict(src_commit=d['src_commit'], flow_tag=d['flow_tag'], prov_file=p)
    q = os.path.dirname(p)
    for _ in range(6):
        for n in ('PROVENANCE.json', 'AUTOPILOT.json'):
            f = os.path.join(q, n)
            try:
                x = load(f)
            except Exception:
                continue
            if not isinstance(x, dict):
                continue
            if n == 'PROVENANCE.json' and x.get('verdict') not in (None, 'SIGNED'):
                return {}
            if n == 'PROVENANCE.json' and x.get('kind') == 'resign':
                return resign(f, x, load)
            if x.get('src_commit') and x.get('flow_tag'):
                return dict(src_commit=x['src_commit'], flow_tag=x['flow_tag'], prov_file=f)
            return {}
        nq = os.path.dirname(q)
        if nq == q: break
        q = nq
    return {}
'''
SCAN_PY = r'''
import json, os, sys
''' + PROV_PY + r'''
out = []
for p in sys.stdin.read().split():
    try:
        if os.path.getsize(p) > 8 << 20: continue
        d = json.load(open(p))
    except Exception: continue
    if not isinstance(d, dict) or d.get('verdict') != 'SIGNED': continue
    fg = d.get('face_guard') or {}
    r = dict(path=p, name=d.get('name'), top=fg.get('top') if isinstance(fg, dict) else None,
             generated=d.get('generated'), host=d.get('host'))
    r.update(prov(p, d, lambda f: json.load(open(f))))
    r['versioned'] = bool(r.get('src_commit') and r.get('flow_tag'))
    out.append(r)
print(json.dumps(out))
'''


def sh(cmd, timeout, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kw)


def scan_host(h):
    find = "nice -n 15 ionice -c3 find %s -xdev \\( -name signoff.json -o -name '*.signoff.json' \\) -size -8M 2>/dev/null" % SCAN_ROOTS
    if h == 'local':
        cmd = ['bash', '-c', find + ' | python3 -c %s' % shlex_quote(SCAN_PY)]
    else:
        cmd = ['ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes', '-o', 'ControlPath=none', h,
               find + ' | python3 -c %s' % shlex_quote(SCAN_PY)]
    r = sh(cmd, 300)
    if r.returncode != 0 and not r.stdout.strip():
        raise RuntimeError('%s: rc %d %s' % (h, r.returncode, r.stderr.strip()[-200:]))
    recs = json.loads(r.stdout.strip().splitlines()[-1])
    for x in recs: x['scan_host'] = h
    return recs


def shlex_quote(s):
    import shlex
    return shlex.quote(s)


def first_flow_tag_ts():
    """unix time of the oldest flow-* tag on origin, or None when no flow release exists yet (GRANDFATHER cutoff)."""
    sh(['git', '-C', str(REPO), 'fetch', '-q', '--tags', 'origin'], 180)
    r = sh(['git', '-C', str(REPO), 'for-each-ref', '--sort=creatordate', '--format=%(creatordate:unix)', 'refs/tags/flow-*'], 30)
    ts = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
    return min(ts) if ts else None


def tag_commit(tag):
    r = sh(['git', '-C', str(REPO), 'rev-parse', '-q', '--verify', 'refs/tags/%s^{commit}' % tag], 30)
    return r.stdout.strip() if r.returncode == 0 else ''


def check_resign_tag(r, tag_commit=tag_commit):
    """a RE-SIGN record counts only when its flow_tag is a flow release tag on origin whose commit is its src_commit
    (the re-sign tools ran at the released flow); otherwise it is unversioned with the reason."""
    if not r.get('resign'): return r
    full = tag_commit(r['flow_tag']) if re.match(r'^flow-\d{8}-[a-z](?:-(qc|s81|head|kv|hbm))?$', r['flow_tag'] or '') else ''
    sc = str(r.get('src_commit') or '')
    if not full or len(sc) < 7 or not full.startswith(sc):
        r['resign_error'] = 're-sign flow_tag %s %s src_commit %s' % (r['flow_tag'], 'is at ' + full[:12] if full else 'not a flow tag on origin', sc[:12])
        r['versioned'] = False
    return r


def gen_ts(r):
    g = r.get('generated')
    if isinstance(g, (int, float)): return float(g)
    if isinstance(g, str):
        try:
            import datetime
            return datetime.datetime.fromisoformat(g.replace('Z', '+00:00')).timestamp()
        except Exception:
            return None
    return None


def is_legacy(r, cutoff):
    """GRANDFATHER: unversioned SIGNED record made before the first flow tag that names a src commit or run dir."""
    if r.get('versioned') or r.get('resign_error'): return False
    names = bool(r.get('src_commit') or r.get('source_commit') or r.get('path'))
    if not names: return False
    if cutoff is None: return True
    t = gen_ts(r)
    return t is not None and t < cutoff


_PROV_NS = {'os': os}
exec(PROV_PY, _PROV_NS)


def main_records(tree):
    out = []
    for p in tree.rglob('*signoff.json'):
        try: d = json.loads(p.read_text())
        except Exception: continue
        if isinstance(d, dict) and d.get('verdict') == 'SIGNED':
            fg = d.get('face_guard') or {}
            r = dict(path='origin/main:' + str(p.relative_to(tree)), name=d.get('name'), top=fg.get('top') if isinstance(fg, dict) else None,
                     generated=d.get('generated'), host=d.get('host'), scan_host='origin/main')
            r.update(_PROV_NS['prov'](str(p), d, lambda f: json.loads(pathlib.Path(f).read_text())))
            if r.get('prov_file', '').startswith(str(tree)):
                r['prov_file'] = 'origin/main:' + str(pathlib.Path(r['prov_file']).relative_to(tree))
            r['versioned'] = bool(r.get('src_commit') and r.get('flow_tag'))
            out.append(r)
    return out


def rec_keys(r):
    ks = set()
    for v in (r.get('top'), r.get('name')):
        if not v: continue
        ks.add(v)
        m = re.match(r'^(dp|kr)_(.+)$', v)
        if m:
            ks.add(m.group(2)); ks.add(re.sub(r'_(lfp|r\d+|c\d+)$', '', m.group(2)))
    return ks


def refresh(log=lambda *a: None):
    errs = []
    res = dict(generated=time.time(), errors=errs, dies={}, plans={}, provenance_rule='v1')
    sha = None
    r = sh(['git', '-C', str(REPO), 'fetch', '-q', 'origin', 'main'], 180)
    if r.returncode: errs.append('git fetch origin main failed: %s' % r.stderr.strip()[-200:])
    sha = sh(['git', '-C', str(REPO), 'rev-parse', '--short=10', 'origin/main'], 30).stdout.strip()
    res['origin_main'] = sha
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='release-tree-plan.'))
    try:
        paths = ['tools'] + ['physical/die_plan/' + d for _, d in PLANS]
        p1 = subprocess.Popen(['git', '-C', str(REPO), 'archive', 'origin/main'] + paths, stdout=subprocess.PIPE)
        r = subprocess.run(['tar', '-x', '-C', str(tmp)], stdin=p1.stdout, capture_output=True, timeout=600)
        p1.wait(60)
        if r.returncode or p1.returncode: raise RuntimeError('git archive origin/main failed')
        # SIGNED records: fleet scan in parallel while the G0C checks run here
        with cf.ThreadPoolExecutor(len(HOSTS)) as ex:
            futs = {ex.submit(scan_host, h): h for h in HOSTS}
            for key, d in PLANS:
                pj = tmp / 'physical/die_plan' / d / 'die_plan.json'
                ent = dict(plan=d)
                try:
                    P = json.loads(pj.read_text())
                    T = P.get('partition_types') or {}
                    ent['types'] = len(T); ent['partitions'] = len(P.get('partitions') or [])
                    ent['type_modules'] = {k: (v.get('module') or k) for k, v in T.items()}
                    ent['hard_cores'] = sorted({h.get('module') for v in T.values() for h in (v.get('hard_cores') or []) if h.get('module')})
                    out = tmp / ('g0c_' + d.replace('/', '_'))
                    t0 = time.time()
                    rr = sh([sys.executable, str(tmp / 'tools/die_plan/check.py'), str(pj), '--completeness', '--quiet', '--out', str(out)],
                            900, cwd=str(tmp))
                    rep = json.loads((out / 'g0_report.json').read_text())
                    g = (rep.get('summary') or {}).get('g0c') or {}
                    ent.update(g0c_verdict=rep.get('verdict'), g0c_errors=rep.get('errors'), g0c_clean=g.get('clean'),
                               g0c_types=g.get('types'), g0c_die_level=g.get('die_level') or {},
                               g0c_bad_types={k: v for k, v in (g.get('by_type') or {}).items()}, check_s=round(time.time() - t0, 1))
                    log('G0C %s: %s/%s clean (%s, %s errors, %.0fs)' % (d, ent['g0c_clean'], ent['g0c_types'], ent['g0c_verdict'], ent['g0c_errors'], ent['check_s']))
                except Exception as e:
                    errs.append('plan %s: %s' % (d, e)); ent['error'] = str(e)
                res['plans'][d] = dict(ent, die=key)
            recs = main_records(tmp)
            scanned = ['origin/main']
            for f, h in futs.items():
                try:
                    recs += f.result(timeout=600); scanned.append(h)
                except Exception as e:
                    errs.append('SIGNED scan %s: %s' % (h, e))
        cutoff = first_flow_tag_ts(); res['first_flow_tag_ts'] = cutoff
        for r_ in recs:
            check_resign_tag(r_)
        for r_ in recs:
            r_['legacy'] = is_legacy(r_, cutoff)
        ret = retired_refs()
        res['retired_records'] = [dict(r_, retired=ret[r_['scan_host'] + ':' + r_['path']]) for r_ in recs
                                  if r_['scan_host'] + ':' + r_['path'] in ret]
        recs = [r_ for r_ in recs if r_['scan_host'] + ':' + r_['path'] not in ret]
        res['signed_records'] = recs; res['scanned'] = scanned
        # match SIGNED records to plan types / hard cores
        for d, ent in res['plans'].items():
            if 'types' not in ent: continue
            tm = ent.pop('type_modules')
            st, sc, ut, uc = {}, {}, {}, {}
            for r_ in recs:
                ks = rec_keys(r_)
                ref = r_['scan_host'] + ':' + r_['path'] if r_['scan_host'] != 'origin/main' else r_['path']
                if r_.get('versioned'):
                    ref += ' src %s flow %s' % (str(r_['src_commit'])[:12], r_['flow_tag'])
                    if r_.get('resign'):
                        ref += ' RE-SIGN build %s db %s' % (str(r_['build_commit'])[:12], r_['routed_db'])
                elif r_.get('resign_error'):
                    ref += ' RE-SIGN-INVALID ' + r_['resign_error']
                elif r_.get('legacy'):
                    ref += ' SIGNED-LEGACY'
                T, C = (st, sc) if (r_.get('versioned') or r_.get('legacy')) else (ut, uc)
                for k, m in tm.items():
                    if k in ks or m in ks: T.setdefault(k, []).append(ref)
                for m in ent['hard_cores']:
                    if m in ks: C.setdefault(m, []).append(ref)
            ent['signed_types'] = st; ent['signed_cores'] = sc
            ent['unversioned_types'] = {k: v for k, v in ut.items() if k not in st}
            ent['unversioned_cores'] = {k: v for k, v in uc.items() if k not in sc}
    except Exception as e:
        errs.append('refresh: %s' % e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def merge_with_cache(new, old):
    """keep the last good per-plan values when this refresh failed for a plan or for the SIGNED scan"""
    if not old: return new
    cur = {pd for _, pd in PLANS}
    for d, ent in (old.get('plans') or {}).items():
        if d not in cur: continue   # plan dir no longer tracked (e.g. hbm_arch/B2l -> B2n): drop, never carry it forward
        n = new['plans'].get(d)
        if (not n or 'g0c_clean' not in n) and 'g0c_clean' in ent:
            ent = dict(ent, stale_since=ent.get('stale_since') or old.get('generated'))
            if old.get('provenance_rule') not in (new.get('provenance_rule'), None):   # GRANDFATHER: pre-rule-3 (None) lists are SIGNED-LEGACY
                for a in ('types', 'cores'):
                    ent['unversioned_' + a] = dict(ent.get('unversioned_' + a) or {}, **(ent.get('signed_' + a) or {}))
                    ent['signed_' + a] = {}
            new['plans'][d] = ent
    return new


def load(force=False, log=lambda *a: None, refresh_stale=True):
    """returns (cache dict or None, error string or None); refreshes when the cache is older than REFRESH_S."""
    old = None
    try: old = json.loads(CACHE.read_text())
    except Exception: pass
    if not force and old and time.time() - old.get('generated', 0) < REFRESH_S:
        return old, None
    if not force and not refresh_stale:
        return old, ('plan layer cache stale; scheduled refresh pending' if old else 'plan layer not cached; run with --refresh-plan')
    try:
        new = merge_with_cache(refresh(log), old)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE.with_suffix('.tmp'); tmp.write_text(json.dumps(new, indent=1)); os.replace(tmp, CACHE)
        return new, ('; '.join(new['errors']) or None)
    except Exception as e:
        return old, 'plan layer refresh failed (%s); %s' % (e, 'using the cached copy' if old else 'no cache')


def die_counts(cache, key):
    """per release-tree die key: list of per-plan rows"""
    rows = []
    for d, ent in sorted(((cache or {}).get('plans') or {}).items()):
        if ent.get('die') != key: continue
        rows.append(dict(plan=d, types=ent.get('types'), clean=ent.get('g0c_clean'), verdict=ent.get('g0c_verdict'),
                         errors=ent.get('g0c_errors'), bad=ent.get('g0c_bad_types') or {}, die_level=ent.get('g0c_die_level') or {},
                         signed_types=len(ent.get('signed_types') or {}), cores=len(ent.get('hard_cores') or []),
                         signed_cores=len(ent.get('signed_cores') or {}), signed_list=sorted(ent.get('signed_types') or {}) + sorted(ent.get('signed_cores') or {}),
                         stale=ent.get('stale_since'), error=ent.get('error')))
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--force', action='store_true'); ap.add_argument('--print', action='store_true')
    a = ap.parse_args()
    c, err = load(a.force, log=lambda *x: print(*x, file=sys.stderr))
    if err: print('WARN', err, file=sys.stderr)
    if a.print:
        for key in ('s81', 's81_head', 'qwen_compute', 'qwen_kvsys', 'hbm'):
            for r in die_counts(c, key):
                print('%-13s %-14s G0C %s/%s clean (%s) ; SIGNED types %d/%s ; SIGNED hard cores %d/%d %s' % (
                    key, r['plan'], r['clean'], r['types'], r['verdict'], r['signed_types'], r['types'], r['signed_cores'], r['cores'], r['signed_list'][:8]))
