#!/usr/bin/env python3
"""design_export: routed-layout packs for the die -> type -> core explorer (EXPLORER-2, 2026-11-11).  Replaces the October
element/closure-job keyed export of layout_store.py (its store format, viewer decoder and round-trip check are reused).

Two halves:

  cut      ON THE BUILD HOST, under ot-run (never on the fleet-viz host or the hub).  One design node: lossless OpenDB
           extraction (lv_extract.py in the ORFS container), the tiled pack (lv_tile.py), the round trip (lv_verify.js,
           IDENTICAL required), all inside one work dir:
             design_export.py cut --node s81.t.slice_station__t48 --db /path/6_final.odb --work DIR
                 [--stage 6_final] [--py PYTHON(brotli+numpy)] [--node-bin NODE] [--mem GB]
           -> DIR/<node>.lvp, DIR/verify.json, DIR/cut.json (seconds, sizes, counts, verdict).  Reuses an extraction /
           pack of the current versions left by an earlier cut of the same DB (mtime + version files).

  publish  ON THE STORE HOST (light: the blobs are already brotli; this only splits the pack into content-addressed
           objects and writes the manifest):
             design_export.py publish --node N --pack HOST:DIR/N.lvp|LOCAL --index design_index.json [--store DIR]
           Refuses a pack whose verify.json is not IDENTICAL.  Store layout (unchanged from layout_store.py, so the
           viewer and layout_service.py serve it as before; the namespace is now the node id):
             <store>/objects/<h[:2]>/<h>.br
             <store>/elements/<node id>/<job>.json   manifest: node, level, die, status at cut time, db, stage, signed
                                                     record, verify verdict, objects
             <store>/elements/<node id>/index.json   {latest, history (newest first, 3)}

  plan     ON THE CONTROLLER (fleet-viz host): the export queue from the design index: every signed type and core whose
           store entry is missing or older than its signed record, and the newest routed attempt of failed types.
             design_export.py plan --index design_index.json [--die s81] [--level type,core] [--limit N] -> TSV
           columns: node, level, state, stage, db (host:path | archive path), bytes, reason

Hooks (proposed, not installed): signed_store.ingest() calls `plan --node <key>` for each verified archive; the
kit-wave FAIL transition calls it for the attempt DB before ot-autoclean may delete the run.
"""
import argparse, hashlib, json, os, pathlib, shlex, shutil, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
TOOLS = pathlib.Path(os.environ.get('LV_TOOLS', HERE.parent / 'layout_viewer'))
DECODE = pathlib.Path(os.environ.get('LV_DECODE', HERE / 'explorer' / 'element' / 'lv_decode.js'))
ELEM_TOOLS = pathlib.Path(os.environ.get('OR_EXPORT_TOOLS', HERE.parent / 'explorer_elem'))   # or_export.py (paths + clock tree)
TIMING_VERSION = 'x1'
IMAGE = os.environ.get('LV_IMAGE', 'openroad/orfs:asap7lock')
OPENROAD = '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
EXTRACT_VERSION = 'e2'   # = layout_store.EXTRACT_VERSION
TILE_VERSION = 't4'      # = layout_store.TILE_VERSION
SCHEMA = 'opentallas.layout_viewer.store.v1'
HISTORY = 3


def log(*a):
    print(time.strftime('%Y-%m-%dT%H:%M:%S'), '[design_export]', *a, flush=True)


def mem_for(size):
    return int(min(160, max(16, -(-(8 * size) // 10 ** 9) + 6)))   # layout_store.mem_for (2.95 GB DB within 31 GB); floor 16: a 0.34 GB 4_1_cts DB hit the old 9 GB cap


# ------------------------------------------------------------------------------------------------ cut (build host)
def cut(a):
    db = pathlib.Path(a.db).resolve()
    w = pathlib.Path(a.work); (w / 'raw').mkdir(parents=True, exist_ok=True)
    node = a.node
    size = db.stat().st_size
    mem = a.mem or mem_for(size)
    t = {}
    ver = lambda n: (w / n).read_text().strip() if (w / n).exists() else ''
    fresh = (w / 'raw/meta.json').exists() and (w / 'raw/meta.json').stat().st_mtime > db.stat().st_mtime
    pack = w / (node + '.lvp')
    try: done = json.loads((w / 'cut.json').read_text())
    except Exception: done = {}
    if (done.get('verify') == 'IDENTICAL' and pack.exists() and pack.stat().st_mtime > db.stat().st_mtime and ver('tile.version') == TILE_VERSION
            and not (done.get('timing') or {}).get('file') and not a.no_timing):
        # an IDENTICAL pack of this DB is already here (its raw extraction dropped): add only the paths / clock tree
        log('%s: pack IDENTICAL already, timing only' % node)
        done['timing'] = timing(a, db, w, mem)
        (w / 'cut.json').write_text(json.dumps(done, indent=1))
        sys.exit(0)
    t0 = time.time()
    if not (fresh and ver('ext.version') == EXTRACT_VERSION):
        for n in ('ext.version', 'tile.version'): (w / n).unlink(missing_ok=True)
        log('%s: extract %s (%.2f GB, %d GB cap)' % (node, db, size / 1e9, mem))
        cmd = ['docker', 'run', '--rm', '--memory', '%dg' % mem, '--cpus', '2', '--user', '%d:%d' % (os.getuid(), os.getgid()),
               '-v', '%s:/db:ro' % db.parent, '-v', '%s:/exp:ro' % TOOLS, '-v', '%s:/out' % (w / 'raw').resolve(),
               '-e', 'OT_DB=/db/' + db.name, '-e', 'OT_OUT=/out', '-e', 'HOME=/tmp', IMAGE, OPENROAD, '-python', '-exit', '/exp/lv_extract.py']
        with open(w / 'extract.log', 'w') as lg:
            r = subprocess.run(['nice', '-n', '19'] + cmd, stdout=lg, stderr=subprocess.STDOUT)
        if r.returncode: sys.exit('extract rc %d (see %s)' % (r.returncode, w / 'extract.log'))
        (w / 'ext.version').write_text(EXTRACT_VERSION)
    t['extract_s'] = round(time.time() - t0, 1)
    pack = w / (node + '.lvp')
    t0 = time.time()
    if not (pack.exists() and ver('tile.version') == TILE_VERSION):
        meta = json.dumps(dict(db=a.db_label or str(db), job=a.job or a.stage, source='design_export', node=node, stage=a.stage))
        log('%s: tile' % node)
        with open(w / 'tile.log', 'w') as lg:
            r = subprocess.run(['nice', '-n', '19', a.py, str(TOOLS / 'lv_tile.py'), '--raw', str(w / 'raw'), '--out', str(pack),
                                '--element', node, '--meta-json', meta], stdout=lg, stderr=subprocess.STDOUT)
        if r.returncode: sys.exit('tile rc %d (see %s)' % (r.returncode, w / 'tile.log'))
        (w / 'tile.version').write_text(TILE_VERSION)
    t['tile_s'] = round(time.time() - t0, 1)
    t0 = time.time()
    log('%s: verify' % node)
    r = subprocess.run(['nice', '-n', '19', a.node_bin, str(TOOLS / 'lv_verify.js'), str(pack)], capture_output=True, text=True,
                       env=dict(os.environ, LV_DECODE=str(DECODE)))
    try:
        o = json.loads(r.stdout)
        v = dict(verdict=o['verdict'], shapes=o['shapes'], db_shapes=o['db_shapes'], tiles=o['tiles'], clipped_pieces=o['clipped_pieces'],
                 layers=o.get('layers'))
    except Exception:
        v = dict(verdict='ERROR', error=(r.stderr or r.stdout)[-600:])
    t['verify_s'] = round(time.time() - t0, 1)
    (w / 'verify.json').write_text(json.dumps(v, indent=1))
    raw = sum(p.stat().st_size for p in (w / 'raw').iterdir())
    meta = json.loads((w / 'raw/meta.json').read_text())
    rec = dict(node=node, db=a.db_label or str(db), db_bytes=size, stage=a.stage, host=os.uname().nodename, mem_gb=mem,
               extract_bytes=raw, pack_bytes=pack.stat().st_size, counts=meta.get('counts'), extract_seconds_in=meta.get('seconds'),
               verify=v['verdict'], shapes=v.get('shapes'), made=time.strftime('%Y-%m-%dT%H:%M:%S%z'), **t)
    (w / 'cut.json').write_text(json.dumps(rec, indent=1))
    log('%s: %s, pack %.1f MB, extract %.1f MB, %s shapes' % (node, v['verdict'], rec['pack_bytes'] / 1e6, raw / 1e6, v.get('shapes')))
    if v['verdict'] == 'IDENTICAL' and not a.no_timing:
        rec['timing'] = timing(a, db, w, mem)
        (w / 'cut.json').write_text(json.dumps(rec, indent=1))
    if a.drop_raw and v['verdict'] == 'IDENTICAL':
        shutil.rmtree(w / 'raw', ignore_errors=True)   # the pack holds everything the viewer needs
    sys.exit(0 if v['verdict'] == 'IDENTICAL' else 3)


# ------------------------------------------------------------------------------------------------ timing (build host)
def sta_setup(session, db_name):
    """the corner STA setup of a sign-off session.tcl (signoff.py writes one per corner): every line before read_db (the
    exact-library procs + ot_lib_load), then the top-level read_* / set_* / source lines up to the first report.  The
    PG audit loop and the 'so' report lines are left out; the DB line points at the cut's DB."""
    head, tail, seen = [], [], False
    for ln in session.splitlines():
        s = ln.strip()
        if not seen:
            if s.startswith('read_db'): seen = True; tail.append('read_db /base/' + db_name); continue
            head.append(ln); continue
        if s.startswith('so CORNER') or s.startswith('report_') or s.startswith('puts '): break
        if ln[:1].isspace() or not s or s.startswith('#') or s.startswith('so ') or s.startswith('foreach') or s.startswith('}'): continue
        if s.split()[0] in ('read_spef', 'read_sdc', 'read_parasitics', 'set_propagated_clock', 'source', 'set_timing_derate',
                            'set_clock_uncertainty', 'set_load', 'set_input_delay', 'set_output_delay', 'set_wire_rc', 'link_design'):
            tail.append(s)
    if not seen or not any(x.startswith('read_spef') for x in tail): return None
    return '\n'.join(head + tail) + '\n'


def timing(a, db, w, mem):
    """worst setup / hold paths and the clock tree with per-sink arrival (or_export.py of the element page), re-timed with
    the run's own sign-off setup when its signoff/<corner>/session.tcl is still there; else the clock topology alone
    (OT_NOSTA: from the DB's CLOCK nets, no timing).  -> {file, sta, corners, seconds} and DIR/timing.json"""
    t0 = time.time()
    so = pathlib.Path(a.signoff) if a.signoff else None
    if so is None and '/run/results/' in str(db):   # ORFS kit layout: <kit>/run/results/<platform>/<design>/base/<db>
        cand = pathlib.Path(str(db).split('/run/results/')[0]) / 'signoff'
        so = cand if cand.is_dir() else None
    jobs = []
    for c in ('tt', 'ff'):
        sess = so / c / 'session.tcl' if so else None
        cmdf = so / c / 'cmd.sh' if so else None
        if not (sess and sess.is_file() and cmdf and cmdf.is_file()): continue
        if not (db.parent / (db.stem + '.spef')).is_file(): continue   # a copied DB without its SPEF: topology only
        txt = sta_setup(sess.read_text().replace('/base/6_final.spef', '/base/%s.spef' % db.stem), db.name)
        if not txt: continue
        jobs.append((c, txt, cmdf.read_text()))
    sta = bool(jobs)
    if not sta: jobs = [('tt', 'read_db /base/%s\n' % db.name, '')]
    parts, errs = {}, []
    for c, txt, cmd in jobs:
        out = w / ('timing_' + c); out.mkdir(exist_ok=True)
        (out / 'setup.tcl').write_text(txt)
        (out / 'pre.tcl').write_text('source /out/setup.tcl\n')
        vols = ['-v', '%s:/base:ro' % db.parent, '-v', '%s:/exp:ro' % ELEM_TOOLS, '-v', '%s:/out' % out.resolve()]
        if sta:   # the same mounts the sign-off session ran with (kit as /work, its sdc dir, its config.mk), all read-only
            import re as _re
            for src, dst in _re.findall(r'-v (\S+?):(/work/config\.mk|/sdc|/work)(?::ro)?(?=\s|$)', cmd):
                vols += ['-v', '%s:%s:ro' % (src, dst)]
        env = ['-e', 'OT_PRE=/out/pre.tcl', '-e', 'OT_CORNER=' + c, '-e', 'OT_OUT=/out', '-e', 'OT_NPATH=40',
               '-e', 'OT_NOSTA=%d' % int(not sta), '-e', 'HOME=/tmp']
        dk = ['docker', 'run', '--rm', '--network=none', '--memory', '%dg' % mem, '--cpus', '2', '--user', '%d:%d' % (os.getuid(), os.getgid())] + vols + env + \
             [IMAGE, OPENROAD, '-python', '-exit', '/exp/or_export.py']
        log('%s: timing %s (%s)' % (a.node, c, 'sign-off STA' if sta else 'clock topology only'))
        with open(out / 'export.log', 'w') as lg:
            print(' '.join(dk), file=lg, flush=True)
            r = subprocess.run(['nice', '-n', '19'] + dk, stdout=lg, stderr=subprocess.STDOUT)
        f = out / (c + '.json')
        if r.returncode or not f.exists(): errs.append('%s rc %d (%s)' % (c, r.returncode, out / 'export.log')); continue
        parts[c] = json.loads(f.read_text())
        for x in ('cells.bin', 'clk.bin'): (out / x).unlink(missing_ok=True)
    tt, ff = parts.get('tt'), parts.get('ff')
    if not tt: return dict(error='; '.join(errs) or 'no tt part', sta=sta, seconds=round(time.time() - t0, 1))
    d = dict(schema='opentallas.design_explorer.timing.v1', node=a.node, version=TIMING_VERSION, sta=sta and not tt.get('nosta'),
             source=('sign-off session %s' % so) if sta else 'DB clock nets (no STA: sign-off session not available)',
             clocks=tt.get('clocks'), clock_roots=tt.get('clock_roots'), clock_tt=tt['clock_tree'],
             clock_ff_leaves=ff and [l[3] for l in ff['clock_tree']['leaves']],
             clock_ff_match=bool(ff and len(ff['clock_tree']['leaves']) == len(tt['clock_tree']['leaves'])),
             setup_paths=tt['paths'] if sta else [], hold_paths=(ff or {}).get('paths') or [], errors=errs)
    (w / 'timing.json').write_text(json.dumps(d, separators=(',', ':')))
    for c in parts: shutil.rmtree(w / ('timing_' + c) / 'unused', ignore_errors=True)
    return dict(file='timing.json', sta=d['sta'], corners=sorted(parts), setup=len(d['setup_paths']), hold=len(d['hold_paths']),
                clock_nodes=len(d['clock_tt'].get('nodes') or []), clock_leaves=len(d['clock_tt'].get('leaves') or []),
                errors=errs, seconds=round(time.time() - t0, 1))


# ------------------------------------------------------------------------------------------------ publish (store host)
def fetch(src, dst):
    if ':' in src and not os.path.exists(src):
        r = subprocess.run(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', src, str(dst)], capture_output=True, text=True, timeout=7200)
        if r.returncode: sys.exit('fetch %s: %s' % (src, r.stderr[-300:]))
    else:
        shutil.copy(src, dst)


def ledger_add(store, label, rec):
    """<store>/cuts.json {db label (host:path): {verdict, node, job, made}}: the export-before-delete gate's ledger
    (design_export_hook.py snapshot ships it to ot-autoclean, which releases a held unit once its DBs are in it)"""
    if not label: return
    import fcntl
    with open(store / 'cuts.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        f = store / 'cuts.json'
        try: d = json.loads(f.read_text())
        except Exception: d = {}
        d[label] = rec
        tmp = f.with_suffix('.tmp'); tmp.write_text(json.dumps(d, sort_keys=True)); os.replace(tmp, f)


def publish(a):
    sys.path.insert(0, str(HERE))
    os.environ['LV_STORE'] = a.store
    import layout_store as LS
    store = pathlib.Path(a.store)
    node = a.node
    tmpd = store / '.incoming'; tmpd.mkdir(parents=True, exist_ok=True)
    pk_local = tmpd / (node + '.lvp'); vj = tmpd / (node + '.verify.json'); cj = tmpd / (node + '.cut.json')
    fetch(a.pack, pk_local)
    base = a.pack[:-len(node + '.lvp')]
    fetch(base + 'verify.json', vj); fetch(base + 'cut.json', cj)
    ver = json.loads(vj.read_text()); cutr = json.loads(cj.read_text())
    tj = tmpd / (node + '.timing.json')
    if (cutr.get('timing') or {}).get('file'):
        try: fetch(base + 'timing.json', tj)
        except SystemExit: tj.unlink(missing_ok=True)
    if ver.get('verdict') != 'IDENTICAL': sys.exit('%s: round trip %s, not published' % (node, ver.get('verdict')))
    idx = json.loads(pathlib.Path(a.index).read_text()) if a.index else {'nodes': {}}
    n = idx['nodes'].get(node) or {}
    pk = LS.Pack(pk_local)
    objs = {name: LS.put_object(pk.raw(name)) for name in pk.index}
    pk.close()
    tim = None
    if tj.exists():   # worst paths + clock tree for the viewer overlays: one brotli object beside the pack's
        import brotli
        tim = dict(cutr['timing'], object=LS.put_object(brotli.compress(tj.read_bytes(), quality=9)))
    hdr = json.loads(__import__('brotli').decompress(LS.obj_path(objs['header']).read_bytes()))
    job = '%s_%s' % (cutr.get('stage') or 'db', hashlib.sha256((cutr.get('db') or '').encode()).hexdigest()[:10])
    ident = hashlib.sha256(json.dumps(objs, sort_keys=True).encode()).hexdigest()[:16]
    lay = n.get('layout') or {}
    man = dict(schema=SCHEMA, id=ident, element=node, job=job, made=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
               design=dict(node=node, level=n.get('level'), die=n.get('die'), name=n.get('name'), status=n.get('status'), stage=cutr.get('stage'),
                           db=cutr.get('db'), db_bytes=cutr.get('db_bytes'), record=lay.get('record'), archive_odb=lay.get('archive_odb'),
                           cut_host=cutr.get('host'), cut_seconds=dict(extract=cutr.get('extract_s'), tile=cutr.get('tile_s'), verify=cutr.get('verify_s'))),
               closure=dict(job=job, status=(n.get('status') or {}).get('label'), host=cutr.get('host'), record=lay.get('record'), metrics=(n.get('status') or {}).get('metrics') or {}),
               db=hdr.get('db'), source='design_export', die=hdr.get('die'), dbu=hdr.get('dbu'), counts=hdr.get('counts'), lint=hdr.get('lint_summary'),
               verify=ver, objects=objs, timing=tim, bytes=sum(LS.obj_path(h).stat().st_size for h in set(objs.values())))
    edir = store / 'elements' / node
    LS.write_json(edir / (job + '.json'), man)
    try: ix = json.loads((edir / 'index.json').read_text())
    except Exception: ix = {}
    hist = [j for j in ix.get('history', []) if j != job]; hist.insert(0, job)
    for j in hist[HISTORY:]: (edir / (j + '.json')).unlink(missing_ok=True)
    hist = hist[:HISTORY]
    LS.write_json(edir / 'index.json', dict(element=node, latest=job, history=hist, updated=man['made'], manifests={j: j + '.json' for j in hist}))
    for p in (pk_local, vj, cj, tj): p.unlink(missing_ok=True)
    ledger_add(store, cutr.get('db'), dict(verdict=ver.get('verdict'), node=node, job=job, made=man['made']))
    log('%s: published %s (%.1f MB objects, %s shapes)' % (node, job, man['bytes'] / 1e6, ver.get('shapes')))


# ------------------------------------------------------------------------------------------------ plan (controller)
def plan(a):
    idx = json.loads(pathlib.Path(a.index).read_text())
    levels = set(a.level.split(','))
    rows = []
    for nid, n in idx['nodes'].items():
        if n['level'] not in levels or (a.die and n['die'] not in a.die.split(',')): continue
        if a.node and nid not in a.node.split(','): continue
        st = n['status']['state']; lay = n.get('layout') or {}
        if st == 'signed':
            have = (lay.get('store') or {})
            if have and not a.redo: continue
            db = lay.get('db') or lay.get('archive_odb')
            if not db: rows.append([nid, n['level'], st, '6_final', '', 0, 'no routed DB in the signed record (view only)']); continue
            rows.append([nid, n['level'], st, '6_final', db, lay.get('odb_bytes') or 0, 'signed; archive %s' % (lay.get('archive_odb') or '-')])
        elif st == 'failed' and lay.get('kit'):
            rows.append([nid, n['level'], st, lay.get('stage') or '?', lay['kit'], 0, 'newest attempt (%s): resolve 6_final/5_2_route/5_1_grt in the kit' % n['status'].get('cls')])
    rows.sort(key=lambda r: (r[2] != 'signed', r[1] != 'core', r[0]))
    if a.limit: rows = rows[:a.limit]
    print('\t'.join(['node', 'level', 'state', 'stage', 'db', 'bytes', 'reason']))
    for r in rows: print('\t'.join(str(x) for x in r))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('cut'); c.add_argument('--node', required=True); c.add_argument('--db', required=True); c.add_argument('--work', required=True)
    c.add_argument('--stage', default='6_final'); c.add_argument('--job'); c.add_argument('--db-label')
    c.add_argument('--py', default=sys.executable); c.add_argument('--node-bin', default=shutil.which('node') or 'node'); c.add_argument('--mem', type=int)
    c.add_argument('--drop-raw', action='store_true')
    c.add_argument('--signoff', help="the run's signoff/ dir (tt/ff session.tcl + cmd.sh): worst paths re-timed with its own setup")
    c.add_argument('--no-timing', action='store_true', help='skip the paths / clock-tree export')
    p = sp.add_parser('publish'); p.add_argument('--node', required=True); p.add_argument('--pack', required=True); p.add_argument('--index')
    p.add_argument('--store', default=os.environ.get('LV_STORE', str(HERE / 'layout_store')))
    q = sp.add_parser('plan'); q.add_argument('--index', required=True); q.add_argument('--die'); q.add_argument('--node'); q.add_argument('--level', default='type,core')
    q.add_argument('--limit', type=int); q.add_argument('--redo', action='store_true')
    a = ap.parse_args()
    {'cut': cut, 'publish': publish, 'plan': plan}[a.cmd](a)


if __name__ == '__main__':
    main()
