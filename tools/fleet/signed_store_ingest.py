#!/usr/bin/env python3
"""Hourly ingest of new signed records into ~/coord/signed-store, no agent, independent of the ot-autoclean drive and
timers (COORD 11-09 01:1x).  Runs on localhost only: the AGIdock key never leaves it.

  scan     every host for sign-off records (the counter's own scan), read only
  select   records the store does not have, generated in the last OT_INGEST_WINDOW_H hours (default 96).  Every SIGNED
           record, versioned or not: entering the store grants nothing, the counter still applies its own rules.
  archive  the record's unit to AGIdock, host -> localhost -> archive, throttled; existing archive files are never rewritten
  verify   sha256 of every file, archive against a fresh hash on the host
  ingest   signed_store.ingest, then commit the new entries through coord-commit.sh
  sweep    a new DO_NOT_COUNT marker in a counted record's own sign-off / routed-DB dirs becomes a HOLD row in
           lanes/COUNT-DO-NOT-COUNT.tsv, which the counter reads (a dir already listed keeps its state)

A record that fails any step is logged and picked up again next run.  Exit 1 when anything failed.
Host paths appear here only as the source of a copy: the counter reads the store and never a host.
"""
import collections, fcntl, json, os, pathlib, re, shlex, subprocess, sys, time

os.environ['OT_COUNT_SOURCE'] = 'hosts'     # this tool's scan uses the counter's ssh; the counter itself stays on the store
TOOLS = str(pathlib.Path(__file__).resolve().parent)
sys.path.insert(0, TOOLS)
import release_tree_plan as rtp    # noqa: E402
import signed_store as ss          # noqa: E402

COORD = pathlib.Path(TOOLS).parent
WINDOW_H = float(os.environ.get('OT_INGEST_WINDOW_H', 96))
RATE = float(os.environ.get('OT_INGEST_MBPS', 40)) * 1e6
HOST_TOOL = '~/.local/share/ot-autoclean-auto/ot-autoclean.py'
LOCK = pathlib.Path.home() / '.local/state/fleet-viz/signed_store_ingest.lock'
LAST = pathlib.Path.home() / '.local/state/fleet-viz/signed_store_ingest_last.json'
SSH = ['ssh', '-o', 'ControlPath=none', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20']
AGI = SSH + ['-i', os.path.expanduser('~/.ssh/agidock_ot'), 'ubuntu@155.103.253.53']
ORDER = tuple(h for h in ('epyc6', 'epyc5', 'epyc4', 'intel1', 'intel2', 'epyc2') if h in rtp.HOSTS) + tuple(h for h in rtp.HOSTS if h not in ('local', 'epyc6', 'epyc5', 'epyc4', 'intel1', 'intel2', 'epyc2'))   # hosts that go away first come first; any host the counter scans (epyc7 11-09) is ingested too

PROBE = r'''
import importlib.util, json, os, sys
spec = importlib.util.spec_from_file_location('otac', os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else '~/.local/share/ot-autoclean-auto/ot-autoclean.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for p in sys.stdin.read().split('\n'):
    if not p: continue
    o = dict(path=p)
    try:
        o['files'] = m.unit_files(m.unit_of(p))
    except Exception as e:
        o['err'] = str(e)[:200]
    print(json.dumps(o), flush=True)
'''


def say(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def identity(r):
    return r.get('name'), r.get('top'), str(r.get('generated'))


def select(recs, have, now, window_h=WINDOW_H):
    """-> {identity: [records]} not in the store and generated inside the window.  A record with no readable time is left
    to a backfill: 'recent' cannot be decided for it."""
    out = collections.defaultdict(list)
    for r in recs:
        k = identity(r)
        if k in have: continue
        t = rtp.gen_ts(r)
        if t is None or now - t > window_h * 3600: continue
        out[k].append(r)
    return dict(out)


MARKER_PY = r'''
import json, os, sys, time
o = {}
for d in sys.stdin.read().split('\n'):
    if not d: continue
    try:
        p = os.path.join(d, 'DO_NOT_COUNT')
        if os.path.isfile(p): o[d] = [open(p, errors='replace').read(160), time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(p)))]
    except Exception: pass
print(json.dumps(o))
'''
STOP = re.compile(r'/srv/opentallas-scratch\d*(/claude)?|/home/ubuntu(/scratch-root)?(/claude)?|/mnt.*')


def ancestors(p):
    out, d = [], os.path.dirname(p)
    while d and d != '/' and not STOP.fullmatch(d):
        out.append(d); d = os.path.dirname(d)
    return out


def marker_sweep(fails, cache=None):
    """-> new HOLD rows written.  Own dirs only: a marker on another copy of the view says nothing about this record."""
    cache = json.load(open(cache or rtp.CACHE))
    by_alias = {}
    for e in ss.read_manifest():
        for a in [e.get('origin')] + (e.get('aliases') or []):
            if a: by_alias[a] = e
    need = collections.defaultdict(set)
    for v in cache['plans'].values():
        for kind in ('signed_designs', 'signed_types', 'signed_cores'):
            for refs in (v.get(kind) or {}).values():
                for ref in refs:
                    m = re.match(r'(\S+?):(\S+signoff\.json)', ref if isinstance(ref, str) else '')
                    e = by_alias.get('%s:%s' % m.groups()) if m else None
                    if not e or str(e.get('origin', '')).startswith('origin/'): continue
                    h, p = e['origin'].split(':', 1)
                    need[h].update(ancestors(p))
                    db = (e.get('scan') or {}).get('routed_db')
                    if db: need[h].update(ancestors(db))
    known = {'%s:%s' % (r['host'], r['dir'].rstrip('/')) for r in rtp.dnc_rows()}
    add = []
    for h, ds in sorted(need.items()):
        try:
            r = run(SSH + [h, 'python3 -I -c ' + shlex.quote(MARKER_PY)], '\n'.join(sorted(ds)) + '\n', 600)
            found = json.loads(r.stdout)
        except Exception as e:
            fails.append([h, '*', 'marker sweep', str(e)[:200]]); continue
        for d, (text, date) in found.items():
            if '%s:%s' % (h, d) not in known:
                add.append('%s:%s\tHOLD\t%s\t%s' % (h, d, text.replace('\n', ' ').replace('\t', ' ')[:180], date))
    if add:
        with open(rtp.COUNT_DNC, 'a') as f:
            f.write('\n'.join(add) + '\n')
        c = run([str(COORD / 'bin/coord-commit.sh'), 'COUNT-DO-NOT-COUNT: %d new marker holds' % len(add), 'lanes/COUNT-DO-NOT-COUNT.tsv'], None, 280)
        if c.returncode: fails.append(['coord', '*', 'marker commit rc %d' % c.returncode])
        for a in add: say('HOLD', a[:160])
    return add


def run(cmd, inp=None, timeout=3600):
    return subprocess.run(cmd, input=inp, capture_output=True, text=True, timeout=timeout)


def stream(host, base, todo):
    """tar on the host, zstd through localhost, untar on the archive with --skip-old-files.  -> True when both ends exit 0"""
    p1 = subprocess.Popen(SSH + [host, 'set -o pipefail; nice -n 15 tar -C / --null -T - -cf - | nice -n 15 zstd -q -T2 -3 -c'],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p1.stdin.write(('\0'.join(todo) + '\0').encode()); p1.stdin.close()
    q = shlex.quote(base)
    p2 = subprocess.Popen(AGI + ['set -o pipefail; mkdir -p %s && zstd -q -d -c | tar -C %s --skip-old-files -xf -' % (q, q)],
                          stdin=subprocess.PIPE)
    t0, sent = time.time(), 0
    while True:
        b = p1.stdout.read(1 << 20)
        if not b: break
        p2.stdin.write(b); sent += len(b)
        wait = sent / RATE - (time.time() - t0)
        if wait > 0: time.sleep(wait)
    p2.stdin.close()
    return p1.wait() == 0 and p2.wait() == 0


SHIP_TOOL = '~/.cache/ot-signed-store/ot-autoclean.py'
LOCAL_TOOL = os.path.expanduser(HOST_TOOL)


def host_tool(h):
    """the unit/hash tool on host h: the installed one when its md5 equals localhost's, else a private copy shipped to
    ~/.cache/ot-signed-store (a host onboarded with autoclean off has none: epyc7 11-09, probe 'no answer')"""
    import hashlib
    want = hashlib.md5(open(LOCAL_TOOL, 'rb').read()).hexdigest()
    r = run(SSH + [h, 'md5sum %s %s 2>/dev/null' % (HOST_TOOL, SHIP_TOOL)], None, 60)
    have = {ln.split()[1]: ln.split()[0] for ln in r.stdout.splitlines() if len(ln.split()) == 2}
    for t in (HOST_TOOL, SHIP_TOOL):
        if have.get(os.path.expanduser(t).replace(os.path.expanduser('~'), '/home/ubuntu')) == want or have.get(t) == want:
            return t
    c = run(SSH + [h, 'mkdir -p ~/.cache/ot-signed-store && cat > %s.tmp && mv %s.tmp %s' % (SHIP_TOOL, SHIP_TOOL, SHIP_TOOL)], open(LOCAL_TOOL).read(), 120)
    if c.returncode: raise RuntimeError('cannot ship the unit tool to %s: %s' % (h, c.stderr[-200:]))
    return SHIP_TOOL


def archive_host(h, cands, fails):
    """-> {path: {file: sha}} for the records whose every file is on the archive and equal to the host copy"""
    try:
        tool = host_tool(h)
    except Exception as e:
        fails.append([h, '*', 'tool', str(e)[:200]]); return {}, {}
    r = run(SSH + [h, 'python3 -I -c ' + shlex.quote(PROBE) + ' ' + tool], '\n'.join(sorted({c[0]['path'] for c in cands})) + '\n', 1800)
    P = {}
    for ln in r.stdout.splitlines():
        o = json.loads(ln); P[o['path']] = o
    files = {}
    for c in cands:
        o = P.get(c[0]['path'])
        if not o or 'files' not in o:
            fails.append([h, c[0]['path'], 'probe', (o or {}).get('err', 'no answer')]); continue
        files.update({f[0]: f[1] for f in o['files']})
    if not files: return {}, P
    base = ss.ARCHIVE_ROOT + '/' + h
    lst = '\n'.join(sorted(files)) + '\n'
    hash_ = 'nice -n 10 python3 -I %s hash --base %s' % (HOST_TOOL, shlex.quote(base))
    a0 = json.loads(run(AGI + [hash_], lst, 3600).stdout)
    todo = [p for p in sorted(files) if a0.get(p) is None]
    say(h, 'files', len(files), '%.2f GB' % (sum(files.values()) / 1e9), 'to send', len(todo))
    if todo and not stream(h, base, todo):
        fails.append([h, '*', 'stream failed']); return {}, P
    A = json.loads(run(AGI + [hash_], lst, 7200).stdout)
    H = json.loads(run(SSH + [h, 'nice -n 15 ionice -c2 -n7 python3 -I %s hash' % tool], lst, 7200).stdout)
    good = {p: A[p] for p in files if A.get(p) is not None and A.get(p) == H.get(p)}
    bad = [p for p in files if p not in good]
    if bad: say(h, 'hash differs on', len(bad), 'files, first', bad[0])
    return good, P


def select_late(recs, manifest):
    """-> [(entry, fresh record)]: a stored record that is not versioned whose origin copy now has a versioned provenance (a re-sign that wrote
    PROVENANCE.json after an ingest had already taken its signoff.json).  Origin copy, or (11-09 16:5x, HBM smk so_ho) an alias copy of the same
    sign-off: the ingest took a copy whose PROVENANCE names another host's routed DB (epyc7 signed2 -> intel1 kit), so that copy scans
    unversioned while the alias on the DB's host is versioned; the alias unit is then archived in full as the extra set."""
    by = {}
    for e in manifest:
        if e.get('flow_tag') and e.get('src_commit'): continue        # versioned already (11-09: not 'has any provenance')
        k = (e.get('name'), e.get('top'), str(e.get('generated')))
        for o in [str(e.get('origin'))] + [str(x) for x in e.get('aliases') or [] if str(x) != str(e.get('origin'))]:
            by.setdefault((o, k), e)
    out = []
    for r in recs:
        if not (r.get('prov_file') and r.get('flow_tag') and r.get('src_commit')): continue
        e = by.get(('%s:%s' % (r.get('scan_host'), r.get('path')), identity(r)))
        if e: out.append((e, r))
    return out


def late_pass(late, fails, archive=None, collect=None):
    """archive + verify the unit again (new files only are sent), require every stored file unchanged, then late_provenance"""
    archive = archive or archive_host
    collect = collect or (lambda h, p: json.loads(run(SSH + [h, 'python3 -I -c ' + shlex.quote(ss.COLLECT_PY)], p + '\n', 300).stdout)[p])
    done = []
    byh = collections.defaultdict(list)
    for e, r in late: byh[r['scan_host']].append((e, r))
    for h, items in byh.items():
        good, P = archive(h, [[r] for e, r in items], fails)
        for e, r in items:
            unit = [f[0] for f in (P.get(r['path']) or {}).get('files', [])]
            # an alias copy (not the origin) has its own paths: none of the stored origin files is in its unit, so the whole alias
            # unit is the new, verified extra set; identity is still the signoff.json sha check below
            alias = '%s:%s' % (h, r['path']) != str(e.get('origin'))
            old = {} if alias else {'/' + f[0]: f[2] for f in e.get('files') or []}
            changed = [p for p, s in old.items() if p not in good or good[p][1] != s]
            # a re-sign's own log (lec.log, signoff.log) is rewritten after the first copy; the archive keeps the first version
            # (never rewritten) and the change is recorded.  Any other stored file that changed refuses.
            logs = [p for p in changed if p.endswith('.log')]
            changed = [p for p in changed if p not in logs]
            newf = [p for p in unit if p not in old]
            if changed:
                fails.append([h, r['path'], 'late: %d stored files changed or unverified, first %s' % (len(changed), changed[0])]); continue
            if any(p not in good for p in newf):
                fails.append([h, r['path'], 'late: new files unverified']); continue
            t = collect(h, r['path'])
            if not t.get('prov'):
                fails.append([h, r['path'], 'late: no PROVENANCE text']); continue
            if ss.hashlib.sha256(t['signoff'].encode()).hexdigest() != e['id']:
                fails.append([h, r['path'], 'late: signoff.json changed']); continue
            if ss.late_provenance(e['id'], r, json.loads(t['prov']), ss.ARCHIVE_ROOT + '/' + h,
                                  [[p.lstrip('/'), good[p][0], good[p][1]] for p in sorted(newf)], changed_logs=sorted(logs)):
                done.append(e['id']); say('LATE PROVENANCE', e['id'][:12], r['path'])
    return done


def main():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    lock = open(LOCK, 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        say('another ingest is running'); return 0
    if '--sweep-only' in sys.argv:
        fails = []
        add = marker_sweep(fails)
        say('marker sweep: new holds', len(add), 'fails', fails)
        return 1 if fails else 0
    dry = '--dry' in sys.argv
    t0 = time.time(); fails = []; new = []; unreachable = []; committed = 0; commit = None
    recs = []
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(len(ORDER)) as ex:
        futs = {ex.submit(rtp.scan_host, h): h for h in ORDER}
        for f in cf.as_completed(futs):
            try: recs += f.result()
            except Exception as e:
                unreachable.append(futs[f]); say('SCAN FAILED', futs[f], str(e)[:200])
    have = {identity(r) for r in ss.load_records()[0]}
    sel = select(recs, have, time.time())
    say('scanned', len(recs), 'records, store has', len(have), 'identities, new inside %.0f h:' % WINDOW_H, len(sel))
    byh = collections.defaultdict(list)
    for v in sel.values():
        byh[v[0]['scan_host']].append(v)
    if not dry:
        for h in ORDER:
            if not byh.get(h): continue
            sha, P = archive_host(h, byh[h], fails)
            for v in byh[h]:
                r = v[0]; o = P.get(r['path']) or {}
                fl = [f[0] for f in o.get('files', [])]
                if not fl: continue
                if any(f not in sha for f in fl):
                    fails.append([h, r['path'], 'unverified']); continue
                try:
                    new += ss.ingest(h, {f: sha[f] for f in fl}, ss.ARCHIVE_ROOT + '/' + h,
                                     aliases={r['path']: ['%s:%s' % (x['scan_host'], x['path']) for x in v]})
                except Exception as e:
                    fails.append([h, r['path'], 'ingest', str(e)[:200]])
            # COUNT-ARCHIVE-2 11-09: commit after every host, so a pass stopped at its time cap keeps what it ingested
            # (the 01:23 pass was killed at 40 min with 84 entries written and none committed)
            fresh = new[committed:]
            if fresh:
                rel = [str(pathlib.Path(ss.entry_path(e)).relative_to(COORD)) for e in fresh]
                c = run([str(COORD / 'bin/coord-commit.sh'), 'signed-store: hourly ingest %s, %d new entries' % (h, len(rel))] + rel, None, 280)
                commit = max(commit or 0, c.returncode)
                if c.returncode: fails.append(['coord', h, 'store commit rc %d' % c.returncode])
                else: committed = len(new)
            say(h, 'ingested so far', len(new), 'fails', len(fails))
    late = select_late(recs, ss.read_manifest())
    say('late provenance candidates', len(late), [e['id'][:12] for e, r in late])
    lated = []
    if not dry:
        lated = late_pass(late, fails)
        if lated:
            rel = [str(pathlib.Path(ss.entry_path(i)).relative_to(COORD)) for i in lated]
            c = run([str(COORD / 'bin/coord-commit.sh'), 'signed-store: late provenance on %d entries' % len(rel)] + rel, None, 280)
            if c.returncode: fails.append(['coord', '*', 'late commit rc %d' % c.returncode])
    holds = [] if dry else marker_sweep(fails)
    res = dict(holds=holds, late=lated, late_candidates=[e['id'] for e, r in late], time=time.ctime(), secs=int(time.time() - t0), scanned=len(recs), selected=len(sel), new=new, fails=fails,
               unreachable=unreachable, commit_rc=commit, dry=dry)
    LAST.write_text(json.dumps(res, indent=1))
    say('DONE new', len(new), 'fails', len(fails), 'unreachable', unreachable, 'commit rc', commit, '%d s' % res['secs'])
    return 1 if fails or unreachable else 0


if __name__ == '__main__':
    sys.exit(main())
