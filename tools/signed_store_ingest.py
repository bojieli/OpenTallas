#!/usr/bin/env python3
"""Hourly ingest of new signed records into ~/coord/signed-store, no agent, independent of the ot-autoclean drive and
timers (COORD 11-09 01:1x).  Runs on localhost only: the AGIdock key never leaves it.

  scan     every host for sign-off records (the counter's own scan), read only
  select   records the store does not have, generated in the last OT_INGEST_WINDOW_H hours (default 96).  Every SIGNED
           record, versioned or not: entering the store grants nothing, the counter still applies its own rules.
  archive  the record's unit to AGIdock, host -> localhost -> archive, throttled; existing archive files are never rewritten
  verify   sha256 of every file, archive against a fresh hash on the host
  ingest   signed_store.ingest, then commit the new entries through coord-commit.sh

A record that fails any step is logged and picked up again next run.  Exit 1 when anything failed.
Host paths appear here only as the source of a copy: the counter reads the store and never a host.
"""
import collections, fcntl, json, os, pathlib, shlex, subprocess, sys, time

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
ORDER = ('epyc6', 'epyc5', 'epyc4', 'intel1', 'intel2', 'epyc2')   # hosts that go away first come first

PROBE = r'''
import importlib.util, json, os, sys
spec = importlib.util.spec_from_file_location('otac', os.path.expanduser('~/.local/share/ot-autoclean-auto/ot-autoclean.py'))
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


def archive_host(h, cands, fails):
    """-> {path: {file: sha}} for the records whose every file is on the archive and equal to the host copy"""
    r = run(SSH + [h, 'python3 -I -c ' + shlex.quote(PROBE)], '\n'.join(sorted({c[0]['path'] for c in cands})) + '\n', 1800)
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
    H = json.loads(run(SSH + [h, 'nice -n 15 ionice -c2 -n7 python3 -I %s hash' % HOST_TOOL], lst, 7200).stdout)
    good = {p: A[p] for p in files if A.get(p) is not None and A.get(p) == H.get(p)}
    bad = [p for p in files if p not in good]
    if bad: say(h, 'hash differs on', len(bad), 'files, first', bad[0])
    return good, P


def main():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    lock = open(LOCK, 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        say('another ingest is running'); return 0
    dry = '--dry' in sys.argv
    t0 = time.time(); fails = []; new = []; unreachable = []
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
            say(h, 'ingested so far', len(new), 'fails', len(fails))
    commit = None
    if new:
        rel = [str(pathlib.Path(ss.entry_path(e)).relative_to(COORD)) for e in new]
        c = run([str(COORD / 'bin/coord-commit.sh'), 'signed-store: hourly ingest, %d new entries' % len(rel)] + rel, None, 280)
        commit = c.returncode
    res = dict(time=time.ctime(), secs=int(time.time() - t0), scanned=len(recs), selected=len(sel), new=new, fails=fails,
               unreachable=unreachable, commit_rc=commit, dry=dry)
    LAST.write_text(json.dumps(res, indent=1))
    say('DONE new', len(new), 'fails', len(fails), 'unreachable', unreachable, 'commit rc', commit, '%d s' % res['secs'])
    return 1 if fails or unreachable else 0


if __name__ == '__main__':
    sys.exit(main())
