#!/usr/bin/env python3
"""COUNT-ARCHIVE-2: re-verify every signed-store entry on AGIdock (archive sha256 vs manifest) and write the per-host list
of host records AUTOCLEAN-13 may release.  Localhost only (AGIdock key).

  release_list.py OUTDIR [--workers 2]

OUTDIR/verify.jsonl     one line per entry: id, ok, bad files
OUTDIR/RELEASE-<host>.tsv   host  path  kind  entry_id  size  sha256
    kind=unit-file   a file of the record's unit on its origin host, byte-equal on the archive (sha listed: re-check before delete)
    kind=alias-signoff   another host's copy of the same sign-off record (same name/top/generated); its unit is a copy,
                         release only files whose sha equals the listed store sha for the same relative path
OUTDIR/HOLD.tsv         entries NOT released and why (archive mismatch, abstract-only, main-only, store entry newer than verify)
"""
import concurrent.futures as cf, json, os, shlex, subprocess, sys, time
sys.path.insert(0, os.path.expanduser('~/coord/tools'))
import signed_store as ss

out = sys.argv[1]
W = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 2
os.makedirs(out, exist_ok=True)
AGI = ['ssh', '-o', 'ControlPath=none', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', '-i',
       os.path.expanduser('~/.ssh/agidock_ot'), 'ubuntu@155.103.253.53']


def check(e):
    fl = ss.entry_files(e)
    bad = []
    for base in sorted({f[3] for f in fl}):
        chk = ''.join('%s  %s\n' % (f[2], f[0]) for f in fl if f[3] == base)
        for t in range(2):
            try:
                r = subprocess.run(AGI + ['cd %s && nice -n 15 sha256sum -c - 2>&1 | grep -v ": OK$"; true' % shlex.quote(base)],
                                   input=chk, capture_output=True, text=True, timeout=7200)
                if r.returncode == 255: raise RuntimeError('ssh 255 ' + r.stderr[-200:])
                bad += [ln for ln in r.stdout.splitlines() if ln.strip()]
                break
            except Exception as x:
                if t: bad.append('ERROR %s' % str(x)[:200])
                else: time.sleep(20)
    return dict(id=e['id'], ok=not bad, bad=bad[:20], nbad=len(bad), files=len(fl))


man = ss.read_manifest()
t0 = time.time()
done = {}
vf = os.path.join(out, 'verify.jsonl')
if os.path.exists(vf):
    for ln in open(vf):
        o = json.loads(ln); done[o['id']] = o
todo = [e for e in man if e['id'] not in done and not str(e.get('origin', '')).startswith('origin/')]
with open(vf, 'a') as f, cf.ThreadPoolExecutor(W) as ex:
    for o in ex.map(check, todo):
        done[o['id']] = o; f.write(json.dumps(o) + '\n'); f.flush()
        print(time.strftime('%T'), len(done), 'ok' if o['ok'] else 'BAD %d' % o['nbad'], o['id'][:12], flush=True)

hold = []
rel = {}
for e in man:
    rows = ';'.join('%s/%s' % (r.get('die'), r.get('key')) for r in e.get('rows') or []) or '-'
    if str(e.get('origin', '')).startswith('origin/'):
        hold.append((e['id'], rows, 'main-only (counts from origin/main git)')); continue
    v = done.get(e['id'])
    if not v or not v['ok']:
        hold.append((e['id'], rows, 'archive verify failed: %s' % ((v or {}).get('bad') or ['not verified'])[:2])); continue
    if not e.get('netlist_sha'):
        hold.append((e['id'], rows, 'no routed netlist in the archived set (abstract-only): keep host routed views')); continue
    h = e['origin'].split(':', 1)[0]
    for fpath, size, sha in e.get('files') or []:
        rel.setdefault(h, []).append((h, '/' + fpath, 'unit-file', e['id'], size, sha))
    for x in e.get('extra') or []:
        xh = x['archive'].rstrip('/').rsplit('/', 1)[-1]
        for fpath, size, sha in x['files']:
            rel.setdefault(xh, []).append((xh, '/' + fpath, 'unit-file-extra', e['id'], size, sha))
    for a in e.get('aliases') or []:
        ah, ap = a.split(':', 1)
        if a == e['origin'] or '/' in ah: continue
        rel.setdefault(ah, []).append((ah, ap, 'alias-signoff', e['id'], '', ''))
for h, rows in rel.items():
    with open(os.path.join(out, 'RELEASE-%s.tsv' % h), 'w') as f:
        f.write('#host\tpath\tkind\tentry_id\tsize\tsha256   (COUNT-ARCHIVE-2 %s; re-check sha on the host before any delete)\n' % time.ctime())
        for r in sorted(set(rows)): f.write('\t'.join(map(str, r)) + '\n')
with open(os.path.join(out, 'HOLD.tsv'), 'w') as f:
    f.write('#entry_id\trows\treason\n')
    for r in hold: f.write('\t'.join(map(str, r)) + '\n')
ok = sum(1 for v in done.values() if v['ok'])
print('entries', len(man), 'verified ok', ok, 'bad', len(done) - ok, 'hold', len(hold), 'secs', int(time.time() - t0))
for h, rows in sorted(rel.items()):
    print(h, 'unit-files', sum(1 for r in rows if r[2].startswith('unit')), '%.1f GB' % (sum(r[4] for r in rows if r[4] != '') / 1e9),
          'alias-signoffs', sum(1 for r in rows if r[2] == 'alias-signoff'))
