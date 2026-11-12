#!/usr/bin/env python3
"""Export-before-delete hook for the design explorer (EXPLORER-2, 2026-11-12; COORD: "every signed run is cut before
deletion").  Three commands, all light; the cuts themselves run under ot-run on the build hosts:

  snapshot  (localhost, ot-autoclean drive --design-export-hook THIS): -> <snapshot>/design_export.json
              ledger   db labels ("host:path") whose IDENTICAL pack is in the store (<store>/cuts.json, design_export publish)
              names    normalised names of every type and core of the current plans (design_index.json)
            ot-autoclean `run` on each host then HOLDS a class a attempt (finished, not superseded: the newest attempt
            of a failed design) or a class s signed unit while it holds a routed ODB of a current design that is not in
            the ledger, and prints one DXREQ line per held ODB.  Fail-safe: holds only ever add refusals; no snapshot
            file = no hold (the gate is off).
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
STAGES = ['6_final', '5_3_fillcell', '5_2_route', '5_1_grt', '4_1_cts', '4_cts']


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


def snapshot(a):
    idx = json.loads(pathlib.Path(a.index).read_text())
    names = set()
    for n in idx['nodes'].values():
        if n['level'] in ('type', 'core') and n['status']['state'] != 'hard ip':
            names.add(n['name']); names.add(norm(n['name']))
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
            fh.write('\t'.join([f[1], f[2], f[3], time.strftime('%F %T')]) + '\n'); have.add(f[1]); new += 1
    print('design_export enqueue: %d new, %d queued' % (new, len(have)))


def sh(host, cmd, timeout=120):
    r = subprocess.run(['timeout', str(timeout), 'ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes', host, cmd],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout, r.stderr


def drain(a):
    """cut + publish every queued DB not in the ledger (serially, a.max per call; ot-run admits each cut)"""
    idx = json.loads(pathlib.Path(a.index).read_text())
    byname = {}
    for nid, n in idx['nodes'].items():
        if n['level'] in ('type', 'core'):
            for k in (n['name'], norm(n['name'])): byname.setdefault((n['die'], k), nid); byname.setdefault(('*', k), nid)
    rc, out, _ = sh(a.store_host, 'cat %s/cuts.json 2>/dev/null' % shlex.quote(a.store), 60)
    try: led = {k for k, v in json.loads(out or '{}').items() if v.get('verdict') == 'IDENTICAL'}
    except ValueError: led = set()
    q = pathlib.Path(a.queue)
    rows = [l.split('\t') for l in q.read_text().splitlines()] if q.exists() else []
    todo = [r for r in rows if r[0] not in led][:a.max]
    runtime = set(a.runtime_hosts.split(','))
    py, node_bin = a.work + '/rt/venv/bin/python', a.work + '/rt/node'
    for label, design, stage, _t in todo:
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
            shlex.quote(a.repo_tools), py, nid, (pack if cut_host == a.store_host else cut_host + ':' + pack), shlex.quote(a.store_index or a.index), shlex.quote(a.store)), 1800)
        print('drain: %s -> %s: %s' % (label, nid, (out or err).strip()[-200:]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('snapshot'); s.add_argument('--index', default=str(STATE / 'design_index.json'))
    s.add_argument('--store', default=os.environ.get('LV_STORE', str(HERE / 'layout_store'))); s.add_argument('--out', required=True)
    e = sp.add_parser('enqueue'); e.add_argument('--queue', default=str(STATE / 'design_export_queue.tsv'))
    d = sp.add_parser('drain'); d.add_argument('--queue', default=str(STATE / 'design_export_queue.tsv'))
    d.add_argument('--index', default=str(STATE / 'design_index.json')); d.add_argument('--store-index', default='')
    d.add_argument('--store-host', default='epyc8'); d.add_argument('--store', required=True); d.add_argument('--work', required=True)
    d.add_argument('--repo-tools', required=True, help='tools/ dir of a fleet_viz checkout on the store host')
    d.add_argument('--runtime-hosts', default='epyc2,epyc7,epyc8,intel1', help='hosts with <work>/rt (venv + node) and <work>/code')
    d.add_argument('--max', type=int, default=20)
    a = ap.parse_args()
    {'snapshot': snapshot, 'enqueue': enqueue, 'drain': drain}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
