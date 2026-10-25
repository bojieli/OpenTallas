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
Cached in ~/.local/state/fleet-viz/release_tree_plan_cache.json; refreshed when older than REFRESH_S (the hourly
release-tree-render.timer calls this through release_tree_render.py). On any failure the last good per-die values are
kept and the error is reported (the page keeps rendering).
Run alone: python3 tools/release_tree_plan.py [--force] [--print]
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time, concurrent.futures as cf

REPO = pathlib.Path('/home/ubuntu/OpenTallas')
CACHE = pathlib.Path.home() / '.local/state/fleet-viz/release_tree_plan_cache.json'
REFRESH_S = 50 * 60
# release-tree die key -> plan dirs under physical/die_plan (s81 section also carries the head dies)
PLANS = [('s81', 's81'), ('s81', 's81_head'), ('qwen_compute', 'qwen_compute'), ('qwen_kvsys', 'qwen_kvsys'),
         ('hbm', 'hbm_arch/B2l')]
HOSTS = ['local', 'epyc1', 'epyc2', 'epyc3', 'intel1', 'intel2']
SCAN_ROOTS = '/srv/opentallas-scratch /srv/opentallas-scratch2'
SCAN_PY = r'''
import json, os, sys
out = []
for p in sys.stdin.read().split():
    try:
        if os.path.getsize(p) > 8 << 20: continue
        d = json.load(open(p))
    except Exception: continue
    if not isinstance(d, dict) or d.get('verdict') != 'SIGNED': continue
    fg = d.get('face_guard') or {}
    out.append(dict(path=p, name=d.get('name'), top=fg.get('top') if isinstance(fg, dict) else None,
                    generated=d.get('generated'), host=d.get('host')))
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


def main_records(tree):
    out = []
    for p in tree.rglob('*signoff.json'):
        try: d = json.loads(p.read_text())
        except Exception: continue
        if isinstance(d, dict) and d.get('verdict') == 'SIGNED':
            fg = d.get('face_guard') or {}
            out.append(dict(path='origin/main:' + str(p.relative_to(tree)), name=d.get('name'), top=fg.get('top') if isinstance(fg, dict) else None,
                            generated=d.get('generated'), host=d.get('host'), scan_host='origin/main'))
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
    res = dict(generated=time.time(), errors=errs, dies={}, plans={})
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
        res['signed_records'] = recs; res['scanned'] = scanned
        # match SIGNED records to plan types / hard cores
        for d, ent in res['plans'].items():
            if 'types' not in ent: continue
            tm = ent.pop('type_modules')
            st, sc = {}, {}
            for r_ in recs:
                ks = rec_keys(r_)
                for k, m in tm.items():
                    if k in ks or m in ks: st.setdefault(k, []).append(r_['scan_host'] + ':' + r_['path'] if r_['scan_host'] != 'origin/main' else r_['path'])
                for m in ent['hard_cores']:
                    if m in ks: sc.setdefault(m, []).append(r_['scan_host'] + ':' + r_['path'] if r_['scan_host'] != 'origin/main' else r_['path'])
            ent['signed_types'] = st; ent['signed_cores'] = sc
    except Exception as e:
        errs.append('refresh: %s' % e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def merge_with_cache(new, old):
    """keep the last good per-plan values when this refresh failed for a plan or for the SIGNED scan"""
    if not old: return new
    for d, ent in (old.get('plans') or {}).items():
        n = new['plans'].get(d)
        if (not n or 'g0c_clean' not in n) and 'g0c_clean' in ent:
            new['plans'][d] = dict(ent, stale_since=ent.get('stale_since') or old.get('generated'))
    return new


def load(force=False, log=lambda *a: None):
    """returns (cache dict or None, error string or None); refreshes when the cache is older than REFRESH_S."""
    old = None
    try: old = json.loads(CACHE.read_text())
    except Exception: pass
    if not force and old and time.time() - old.get('generated', 0) < REFRESH_S:
        return old, None
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
        for key in ('s81', 'qwen_compute', 'qwen_kvsys', 'hbm'):
            for r in die_counts(c, key):
                print('%-13s %-14s G0C %s/%s clean (%s) ; SIGNED types %d/%s ; SIGNED hard cores %d/%d %s' % (
                    key, r['plan'], r['clean'], r['types'], r['verdict'], r['signed_types'], r['types'], r['signed_cores'], r['cores'], r['signed_list'][:8]))
