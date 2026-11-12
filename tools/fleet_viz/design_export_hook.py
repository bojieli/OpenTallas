#!/usr/bin/env python3
"""Export-before-delete hook for the design explorer (EXPLORER-2, 2026-11-12; COORD: "every signed run is cut before
deletion").  Three commands, all light; the cuts themselves run under ot-run on the build hosts:

  snapshot  (localhost, ot-autoclean drive --design-export-hook THIS): -> <snapshot>/design_export.json
              ledger   db labels ("host:path") whose IDENTICAL pack is in the store (<store>/cuts.json, design_export publish)
              names    normalised names of every type and core of the current plans (design_index.json)
            ot-autoclean `run` on each host then HOLDS a class a attempt (finished or superseded), a class b trim or a
            class s signed unit while it holds a routed / CTS ODB of a current design that is not in the ledger, and
            prints one DXREQ line per held ODB.  DEFAULT ON (OWNER 11-12 "export before cleanup"): a failed snapshot
            or a missing gate file holds EVERY routed ODB; holds only ever add refusals.
  ledger-sync (store host): fold published manifests into <store>/cuts.json (publish keeps it current after that)
  enqueue   (localhost, drive): DXREQ lines on stdin -> <state>/design_export_queue.tsv (unique by label)
  drain     (localhost, cron or drive): every queued label not yet in the ledger -> resolve the design node, cut on the
            DB's host (in place, DB read-only) or on a runtime host after a copy, publish into the store; the ledger
            entry then releases the hold on the next autoclean run.

    design_export_hook.py snapshot --index I --store S --out F
    design_export_hook.py enqueue  --queue Q < DXREQ lines
    design_export_hook.py drain    --queue Q --index I --store-host H --store S --work W [--max N]
"""
import argparse, json, os, pathlib, re, shlex, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
SCHEMA = 'opentallas.fleet_viz.design_export_gate.v1'
# routed stages, best first (the same order ot-autoclean's host check uses: DX_STAGES there)
STAGES = ['6_final', '5_3_fillcell', '5_2_route', '5_1_grt', '5_route', '6_1_fill', '4_1_cts', '4_cts']
# where the store and its node index live until the localhost fleet-viz deploy (then LV_STORE / FLEET_VIZ_STATE there)
DX_STORE = os.environ.get('DX_STORE', 'epyc8:/srv/opentallas-scratch2/claude/explorer-2-work/store')
DX_INDEX = os.environ.get('DX_INDEX', 'epyc8:/srv/opentallas-scratch2/claude/explorer-2-work/state/design_index.json')
DX_WORK = os.environ.get('DX_WORK', '/srv/opentallas-scratch2/claude/explorer-2-work')          # on the store host: rt/, code/, cut/, db/
DX_TOOLS = os.environ.get('DX_TOOLS', '/srv/opentallas-scratch2/claude/explorer-2/tools')      # a fleet_viz checkout on the store host


def read_any(spec, timeout=300):
    """'host:/path' (over ssh) or a local path -> text"""
    if ':' in spec and not spec.startswith('/'):
        host, path = spec.split(':', 1)
        r = subprocess.run(['timeout', str(timeout), 'ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes', host, 'cat ' + shlex.quote(path)],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if r.returncode: raise OSError('%s: rc %d %s' % (spec, r.returncode, r.stderr.strip()[-200:]))
        return r.stdout
    return pathlib.Path(spec).read_text()


def norm(name):
    """a results/<platform>/<design> dir or signed-view name -> the plan name it builds (= ot-autoclean dx_norm):
    kl_ / dp_ / hbc_ / hd_ / ds_ prefixes, __clXXXXXXXX clone and _rt* / _cv* / _r<digit>* view suffixes dropped"""
    n = re.sub(r'^(kl|dp|hbc|hd|ds)_', '', name or '')
    n = re.sub(r'(__cl[0-9a-f]{8})+$', '', n)
    return re.sub(r'_(rt\w+|cv\w+|r\d\w*)$', '', n)


def ledger(store):
    """cuts.json (design_export publish) plus every published manifest's design.db (packs published before the ledger)"""
    st = pathlib.Path(store)
    try: d = json.loads((st / 'cuts.json').read_text())
    except Exception: d = {}
    out = {k: v for k, v in d.items() if (v or {}).get('verdict') == 'IDENTICAL'}
    for m in st.glob('elements/*/*.json'):
        if m.name == 'index.json': continue
        try: j = json.loads(m.read_text())
        except Exception: continue
        db = (j.get('design') or {}).get('db')
        if db and (j.get('verify') or {}).get('verdict') == 'IDENTICAL': out.setdefault(db, dict(verdict='IDENTICAL', node=j.get('element'), job=j.get('job')))
    return out


def ledger_sync(a):
    """fold every published manifest (packs published before the ledger existed) into <store>/cuts.json"""
    st = pathlib.Path(a.store); led = ledger(st)
    tmp = st / 'cuts.json.tmp'; tmp.write_text(json.dumps(led, sort_keys=True)); os.replace(tmp, st / 'cuts.json')
    print('ledger-sync: %d IDENTICAL cuts in %s' % (len(led), st / 'cuts.json'))


def snapshot(a):
    """the gate file; any failure raises (exit != 0) and the drive then writes HOLD ALL"""
    idx = json.loads(read_any(a.index))
    names = set()
    for n in idx['nodes'].values():
        if n['level'] in ('type', 'core') and n['status']['state'] != 'hard ip':
            names.add(n['name']); names.add(norm(n['name']))
    if ':' in a.store and not a.store.startswith('/'):
        led = {k: v for k, v in json.loads(read_any(a.store.rstrip('/') + '/cuts.json')).items() if (v or {}).get('verdict') == 'IDENTICAL'}
    else:
        led = ledger(a.store)
    out = dict(schema=SCHEMA, created=time.time(), ledger=sorted(led), ledger_paths=sorted({k.split(':', 1)[-1] for k in led}),
               names=sorted(names), stages=STAGES)
    tmp = pathlib.Path(a.out + '.tmp'); tmp.write_text(json.dumps(out)); os.replace(tmp, a.out)
    print('design_export snapshot: %d ledger DBs, %d design names -> %s' % (len(led), len(names), a.out))


def enqueue(a):
    q = pathlib.Path(a.queue); q.parent.mkdir(parents=True, exist_ok=True)
    have = {l.split('\t')[0] for l in q.read_text().splitlines()} if q.exists() else set()
    new = 0
    with open(q, 'a') as fh:
        for ln in sys.stdin:
            f = ln.rstrip('\n').split('\t')
            if len(f) < 4 or f[0] != 'DXREQ' or f[1] in have: continue
            kind = f[4] if len(f) > 4 else 'newest'
            fh.write('\t'.join([f[1], f[2], f[3], time.strftime('%F %T'), kind]) + '\n'); have.add(f[1]); new += 1
    print('design_export enqueue: %d new, %d queued' % (new, len(have)))


def sh(host, cmd, timeout=120):
    r = subprocess.run(['timeout', str(timeout), 'ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes', host, cmd],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout, r.stderr


def host_free_gb(host):
    """lowest free GB over / and the scratch disks of a host (None when unreachable)"""
    rc, out, _ = sh(host, 'df -BG --output=avail / /srv/opentallas-scratch* 2>/dev/null | tail -n +2', 30)
    vals = [int(x.rstrip('G')) for x in out.split() if x.rstrip('G').isdigit()]
    return min(vals) if rc == 0 and vals else None


def order_queue(pend, free, floor_gb, cap, cap_starved):
    """queued rows -> (rows to cut now, starved hosts).  Rows from hosts under the floor first (lowest free GB first, then
    oldest queued), up to cap_starved; then the rest, oldest first, up to cap.  Unreachable hosts sort last."""
    host = lambda r: r[0].split(':', 1)[0]
    starved = {h for h, g in free.items() if g is not None and g < floor_gb}
    key = lambda r: (free.get(host(r)) if free.get(host(r)) is not None else 1e9, r[3] if len(r) > 3 else '')
    first = sorted((r for r in pend if host(r) in starved), key=key)[:cap_starved]
    rest = sorted((r for r in pend if host(r) not in starved), key=lambda r: r[3] if len(r) > 3 else '')[:cap]
    return first + rest, starved


def drain(a):
    """cut + publish every queued DB not in the ledger (serially, a.max per call; ot-run admits each cut); one at a time"""
    import fcntl
    q = pathlib.Path(a.queue); q.parent.mkdir(parents=True, exist_ok=True)
    lk = open(str(q) + '.lock', 'w')
    try: fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError: print('drain: another drain holds the lock'); return
    idx = json.loads(read_any(a.index))
    byname = {}
    for nid, n in idx['nodes'].items():
        if n['level'] in ('type', 'core'):
            for k in (n['name'], norm(n['name'])): byname.setdefault((n['die'], k), nid); byname.setdefault(('*', k), nid)
    rc, out, _ = sh(a.store_host, 'cat %s/cuts.json 2>/dev/null' % shlex.quote(a.store), 60)
    try: led = {k for k, v in json.loads(out or '{}').items() if v.get('verdict') == 'IDENTICAL'}
    except ValueError: led = set()
    q = pathlib.Path(a.queue)
    rows = [l.split('\t') for l in q.read_text().splitlines()] if q.exists() else []
    pend = [r for r in rows if r[0] not in led]
    # COORD 11-12: disk-starved hosts first.  Order by the source host's lowest free GB (root + scratch disks); hosts
    # under the floor get a larger per-drive cap and are never cut in place (their DB is copied to the store host).
    free = {h: host_free_gb(h) for h in sorted({r[0].split(':', 1)[0] for r in pend})}
    todo, starved = order_queue(pend, free, a.floor_gb, a.max, a.max_starved)
    if free: print('drain: host free GB ' + ' '.join('%s %s%s' % (h, g, '*' if h in starved else '') for h, g in sorted(free.items(), key=lambda x: x[1] if x[1] is not None else 1e9))
                   + ' (* under %d GB: first, cap %d, cut on %s)' % (a.floor_gb, a.max_starved, a.store_host))
    runtime = set(a.runtime_hosts.split(',')) - starved
    py, node_bin = a.work + '/rt/venv/bin/python', a.work + '/rt/node'
    for row in todo:
        label, design, stage = row[:3]; kind = row[4] if len(row) > 4 else 'newest'
        host, path = label.split(':', 1)
        nid = byname.get(('*', norm(design)))
        if not nid: print('drain: %s: %s is not a current design; dropped' % (label, design)); continue
        dbp, local = path, host in runtime
        cut_host = host if local else a.store_host
        if not local:   # copy the DB to the store host (our own copy, removed after the cut)
            dbp = '%s/db/%s/%s' % (a.work, nid, os.path.basename(path))
            sh(cut_host, 'mkdir -p %s' % shlex.quote(os.path.dirname(dbp)))
            r = subprocess.run(['timeout', '7200', 'ssh', '-o', 'BatchMode=yes', host, 'nice -n 19 scp -q -o BatchMode=yes %s %s:%s' %
                                (shlex.quote(path), cut_host, shlex.quote(dbp))], stdin=subprocess.DEVNULL)
            if r.returncode: print('drain: %s: copy failed' % label); continue
        code = (a.repo_tools + '/fleet_viz/design_export.py') if cut_host == a.store_host else (a.work + '/code/tools/fleet_viz/design_export.py')
        mem = 40 if '.t.' in nid else 16
        r = subprocess.run(['ot-run', '--mem', str(mem), '--threads', '3', '--hosts', cut_host, '--dir', a.work, '--', 'nice', '-n', '19', py, '-I', code,
                            'cut', '--node', nid, '--db', dbp, '--work', '%s/cut/%s' % (a.work, nid), '--py', py, '--node-bin', node_bin,
                            '--db-label', label, '--stage', stage, '--drop-raw'], stdin=subprocess.DEVNULL)
        if not local: sh(cut_host, 'rm -f %s' % shlex.quote(dbp))
        if r.returncode: print('drain: %s: cut rc %d' % (label, r.returncode)); continue
        pack = '%s/cut/%s/%s.lvp' % (a.work, nid, nid)
        rc, out, err = sh(a.store_host, 'cd %s/fleet_viz && %s -I design_export.py publish --node %s --pack %s --index %s --store %s 2>&1 | tail -1' % (
            shlex.quote(a.repo_tools), py, nid, (pack if cut_host == a.store_host else cut_host + ':' + pack), shlex.quote(a.store_index or a.index.split(':', 1)[-1]), shlex.quote(a.store))
            + (' --keep-latest' if kind == 'superseded' else ''), 1800)   # an older attempt goes into history only
        print('drain: %s -> %s: %s' % (label, nid, (out or err).strip()[-200:]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('snapshot'); s.add_argument('--index', default=DX_INDEX, help='host:path or path')
    s.add_argument('--store', default=DX_STORE, help='host:path (reads <store>/cuts.json) or a local store'); s.add_argument('--out', required=True)
    g = sp.add_parser('ledger-sync'); g.add_argument('--store', default=os.environ.get('LV_STORE', str(HERE / 'layout_store')))
    e = sp.add_parser('enqueue'); e.add_argument('--queue', default=str(STATE / 'design_export_queue.tsv'))
    d = sp.add_parser('drain'); d.add_argument('--queue', default=str(STATE / 'design_export_queue.tsv'))
    d.add_argument('--index', default=DX_INDEX, help='host:path or path'); d.add_argument('--store-index', default='')
    d.add_argument('--store-host', default=DX_STORE.split(':', 1)[0]); d.add_argument('--store', default=DX_STORE.split(':', 1)[-1])
    d.add_argument('--work', default=DX_WORK); d.add_argument('--repo-tools', default=DX_TOOLS, help='tools/ dir of a fleet_viz checkout on the store host')
    d.add_argument('--runtime-hosts', default='epyc7,epyc8,intel1', help='hosts with <work>/rt (venv + node) and <work>/code')
    d.add_argument('--max', type=int, default=20, help='DBs per drain from hosts at or above the floor')
    d.add_argument('--max-starved', type=int, default=60, help='DBs per drain from hosts under the floor (cut on the store host)')
    d.add_argument('--floor-gb', type=int, default=150, help='free-GB floor (OWNER 11-06: 150 GB on every host)')
    a = ap.parse_args()
    {'snapshot': snapshot, 'enqueue': enqueue, 'drain': drain, 'ledger-sync': ledger_sync}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
