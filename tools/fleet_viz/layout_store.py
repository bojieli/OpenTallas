#!/usr/bin/env python3
"""Layout viewer export pipeline and the static layout store (owner design 2026-10-11: static export at closure).

When a job CLOSES (and is the element's adopted closure), its routed DB is cut once into an immutable, content-addressed
export that fleet-viz serves as plain static files; nothing is cut at view time for closed elements.  The store is the
authoritative layout reference after fleet scratch is cleaned (48 h rule).

  <store>/objects/<h[:2]>/<h>.br   brotli blobs named by the sha256 of their (compressed) bytes; shared across elements
  <store>/elements/<el>/<job>.json  manifest of one closure: closure record (job, status, commit, slacks, bench), the
                                    logical blob names -> object hashes (header, lint, cong, tiles per layer, rasters,
                                    name tables, the element page's own data: element JSON, cells, clock wires, RTL)
  <store>/elements/<el>/index.json  {latest, history (newest first, at most HISTORY closures)}
  <store>/STATUS.json               per-element export state, closed elements whose DB is gone, store size vs budget

Source of the DB, in order: the closed-layout archive on this host (<archive>/<el>/<job>/, closed-archive-1011), cut
here in the ORFS container (nice 19, memory- and CPU-capped: one at a time); else the job's fleet host (cut there under
ot-heavy; ot-epyc4 relayed to ot-epyc3).  Every pack is verified (decoded and compared with the DB truth summary,
tools/layout_viewer/lv_verify.js) before it is published.

CLI (deployed copy: ~/.local/share/fleet-viz/layout_store.py):
  export  --element E [--job J]   cut + verify + publish one closure (the post-record hook runs this)
  backfill [--limit N] [--only a,b] [--workers 4]   every CLOSED element of the registry, priority order
  gc | status | audit     (audit: re-run the round trip on every published closure, from the store files -> AUDIT.json)
"""
import argparse, collections, concurrent.futures as cf, fcntl, hashlib, json, os, pathlib, shlex, shutil, struct, subprocess, sys, threading, time, traceback

import brotli

HOME = pathlib.Path.home()
HERE = pathlib.Path(__file__).resolve().parent
ELEM_DATA = HERE / 'explorer' / 'element' / 'data'
TOOLS = pathlib.Path(os.environ.get('LV_TOOLS', HERE / 'layout_viewer'))
STORE = pathlib.Path(os.environ.get('LV_STORE', HERE / 'layout_store'))
ARCHIVE = pathlib.Path(os.environ.get('LV_ARCHIVE', HOME / 'closed_archive'))
WORK = pathlib.Path(os.environ.get('LV_WORK', HOME / '.cache' / 'layout-viewer' / 'work'))
JOBS = HOME / '.local/state/closure_loop/jobs'
REPO = pathlib.Path(os.environ.get('LV_REPO', '/home/ubuntu/OpenTallas'))
BUDGET_GB = float(os.environ.get('LV_STORE_GB', '20'))
HISTORY = 3
IMAGE = 'openroad/orfs:asap7lock'
OPENROAD = '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
AVOID = set(filter(None, os.environ.get('LV_AVOID_HOSTS', 'ot-epyc4').split(',')))
RELAY = os.environ.get('LV_RELAY_HOST', 'ot-epyc4')   # EPYC3 terminated 2026-10-12
RELAY_DIR = os.environ.get('LV_RELAY_DIR', '/srv/opentallas-scratch/claude/layout-viewer-store/relay')
LOCAL_LOCK = WORK / '.local_cut.lock'    # cuts on this host run one at a time
LOCAL_MAX_DB = float(os.environ.get('LV_LOCAL_MAX_DB', 400e6))   # archive DBs up to this (raw) size are cut on this host
# active fleet only (EPYC1 terminated 2026-10-16, EPYC2/3 2026-10-12)
STREAM_ROOT = {'ot-epyc4': '/srv/opentallas-scratch2/claude',
               'ot-epyc7': '/srv/opentallas-scratch/claude', 'ot-epyc8': '/srv/opentallas-scratch/claude', 'ot-epyc9': '/srv/opentallas-scratch/claude', 'ot-gold2': '/srv/opentallas-scratch/claude', 'ot-gold1': '/srv/opentallas-scratch/claude',
               'ot-agidock128': '/srv/opentallas-scratch/claude',
               'ot-pve1': '/srv/opentallas-scratch/claude'}
STREAM_HOSTS = sorted(STREAM_ROOT)       # larger archive DBs are streamed (zstd) to one of these and cut there
EXTRACT_VERSION = 'e2'   # bump when lv_extract.py output changes (forces re-extraction)
TILE_VERSION = 't4'      # bump when lv_tile.py / lv_lint.py output changes (re-cut from the kept extraction)
SCHEMA = 'opentallas.layout_viewer.store.v1'


def log(*a):
    print(time.strftime('%Y-%m-%dT%H:%M:%S'), *a, flush=True)


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def ssh(host, cmd, inp=None, timeout=1800, binary=False):
    args = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=30', '-o', 'ControlPath=none', host, cmd]
    return subprocess.run(args, input=inp, capture_output=True, text=not binary, timeout=timeout)


def mem_for(size):
    return int(min(160, max(8, -(-(8 * size) // 10 ** 9) + 6)))   # measured: a 2.95 GB DB extracts within 31 GB (ot-heavy small slot)


# ------------------------------------------------------------------ where is the DB
def archive_db(el, job):
    """the closed-archive copy of a job's final DB (closed-archive-1011: <archive>/<el>/<job>/final/6_final.odb[.zst],
    raw size in its manifest.json) -> (path, raw bytes) or None"""
    d = ARCHIVE / el / job
    if not d.is_dir(): return None
    for p in (d / 'final' / '6_final.odb', d / 'final' / '6_final.odb.zst'):
        if p.exists():
            size = None
            try:
                m = json.loads((d / 'manifest.json').read_text())
                size = next((f.get('raw_size') for f in m.get('files', []) if f.get('role') == 'final_odb'), None)
            except Exception: pass
            return p, size or p.stat().st_size
    return None


def element_json(el):
    try: return json.loads((ELEM_DATA / (el + '.json')).read_text())
    except Exception: return None


def locate(el, job=None):
    """-> dict(kind='archive', path) | dict(kind='host', host, path) | None, plus the job"""
    d = element_json(el) or {}
    job = job or d.get('job')
    if not job:   # no element page: the archive's best closure for the element
        try: job = next((r['job'] for r in json.loads((ARCHIVE / 'INDEX.json').read_text()).get('rows', [])
                         if r.get('element') == el and r.get('scope') == 'best' and r.get('status') == 'archived'), None)
        except Exception: job = None
    if job:
        a = archive_db(el, job)
        if a: return dict(kind='archive', path=str(a[0]), size=a[1], job=job)
    db = d.get('db') or ''
    if ':' in db and (not job or job == d.get('job')):
        host, path = db.split(':', 1)
        if host in ('localhost', '127.0.0.1'):
            if os.path.exists(path): return dict(kind='archive', path=path, size=os.path.getsize(path), job=job or d.get('job'))
        else:
            r = ssh(host, 'stat -c "%%s" %s' % shlex.quote(path), timeout=60)
            if r.returncode == 0:
                return dict(kind='host', host=host, path=path, size=int(r.stdout.strip() or 0), job=job or d.get('job'))
    # the job's own run dir (the registry's best closure can differ from the job the element page was built from)
    try: st = json.loads((JOBS / (job + '.json')).read_text()) if job else {}
    except Exception: st = {}
    host, run = st.get('host'), (st.get('run') or '').rstrip('/')
    if host and run:
        od = (st.get('metrics') or {}).get('orfs_dir') or ''
        probe = ('for d in %s %s/cl/eco*/pass*/orfs %s/routes/*/work/orfs %s/routes/*/signoff; do for f in $d/results/asap7/*/base/6_final.odb; do '
                 '[ -f "$f" ] && { stat -c "%%s %%n" "$f"; exit 0; }; done; done; exit 1') % (shlex.quote(od) if od else '', run, run, run)
        r = ssh(host, probe, timeout=120)
        if r.returncode == 0 and r.stdout.strip():
            size, path = r.stdout.strip().split(' ', 1)
            if host in ('localhost', '127.0.0.1'):   # a DB on this host is cut here, like an archive copy
                return dict(kind='archive', path=path, size=int(size), job=job)
            return dict(kind='host', host=host, path=path, size=int(size), job=job)
    return None


# ------------------------------------------------------------------ cutting a pack
def remote_store_dir(odb, el):
    p = pathlib.PurePosixPath(odb); parts = p.parts
    if 'closure-loop' in parts:
        return str(pathlib.PurePosixPath(*parts[:parts.index('closure-loop')]) / 'layout-viewer-store' / el)
    return str(p.parent / 'layout-viewer-store' / el)


def cut_pack(el, src, dst, mark=lambda **k: None):
    """cut <el>'s pack from src (locate() result) into the local file dst.  Reuses an extraction / pack of the current
    versions left by an earlier cut.  Raises on failure."""
    meta = json.dumps(dict(db=src['path'] if src['kind'] == 'archive' else '%s:%s' % (src['host'], src['path']), job=src.get('job'),
                           source=src['kind']))
    if src['kind'] == 'archive':
        if (src.get('size') or 0) <= LOCAL_MAX_DB:   # small DBs are cut here; larger ones go to a fleet host
            return _cut_local(el, pathlib.Path(src['path']), dst, meta, mark)
        host = STREAM_HOSTS[int(hashlib.sha1(el.encode()).hexdigest(), 16) % len(STREAM_HOSTS)]
        return _cut_remote(el, host, None, src.get('size') or 0, dst, meta, mark, stream=pathlib.Path(src['path']))
    return _cut_remote(el, src['host'], src['path'], src.get('size') or 0, dst, meta, mark)


def _cut_local(el, odb, dst, meta, mark):
    w = WORK / el; (w / 'raw').mkdir(parents=True, exist_ok=True)
    if odb.suffix == '.zst':   # archive copies are zstd-compressed
        plain = w / '6_final.odb'
        if not (plain.exists() and plain.stat().st_mtime >= odb.stat().st_mtime):
            mark(stage='decompress archived DB')
            r = subprocess.run(['bash', '-c', 'zstd -dcq < %s > %s.tmp && mv %s.tmp %s' % (shlex.quote(str(odb.resolve())), plain, plain, plain)], capture_output=True, text=True)
            if r.returncode: raise RuntimeError('zstd: %s' % r.stderr[-200:])
        odb = plain
    mem = mem_for(odb.stat().st_size)
    WORK.mkdir(parents=True, exist_ok=True)
    with open(LOCAL_LOCK, 'w') as lk:
        mark(stage='waiting for the local cut slot')
        fcntl.flock(lk, fcntl.LOCK_EX)
        ver = lambda n: (w / n).read_text().strip() if (w / n).exists() else ''
        fresh = (w / 'raw/meta.json').exists() and (w / 'raw/meta.json').stat().st_mtime > odb.stat().st_mtime
        if not (fresh and ver('ext.version') == EXTRACT_VERSION):
            mark(stage='extract (OpenDB, %d GB cap) on this host' % mem)
            for n in ('ext.version', 'tile.version'): (w / n).unlink(missing_ok=True)
            cmd = ['nice', '-n', '19', 'docker', 'run', '--rm', '--memory', '%dg' % mem, '--cpus', '2', '--user', '%d:%d' % (os.getuid(), os.getgid()),
                   '-v', '%s:/db:ro' % odb.parent, '-v', '%s:/exp:ro' % TOOLS, '-v', '%s:/out' % (w / 'raw'), '-e', 'OT_DB=/db/' + odb.name,
                   '-e', 'OT_OUT=/out', '-e', 'HOME=/tmp', IMAGE, OPENROAD, '-python', '-exit', '/exp/lv_extract.py']
            with open(w / 'extract.log', 'w') as lg:
                r = subprocess.run(cmd, stdout=lg, stderr=subprocess.STDOUT, timeout=8 * 3600)
            if r.returncode: raise RuntimeError('local extract rc %d (see %s)' % (r.returncode, w / 'extract.log'))
            (w / 'ext.version').write_text(EXTRACT_VERSION)
        if not ((w / (el + '.lvp')).exists() and ver('tile.version') == TILE_VERSION):
            mark(stage='cut tiles on this host')
            cmd = ['systemd-run', '--user', '--scope', '-q', '-p', 'MemoryMax=%dG' % int(min(120, mem * 1.6)), '-p', 'CPUQuota=200%', '--',
                   'nice', '-n', '19', sys.executable, str(TOOLS / 'lv_tile.py'), '--raw', str(w / 'raw'), '--out', str(w / (el + '.lvp')),
                   '--element', el, '--meta-json', meta]
            with open(w / 'tile.log', 'w') as lg:
                r = subprocess.run(cmd, stdout=lg, stderr=subprocess.STDOUT, timeout=8 * 3600)
            if r.returncode: raise RuntimeError('local tile cut rc %d (see %s)' % (r.returncode, w / 'tile.log'))
            (w / 'tile.version').write_text(TILE_VERSION)
    shutil.copy(w / (el + '.lvp'), dst)
    return dst


def _cut_remote(el, host, odb, size, dst, meta, mark, stream=None):
    work_host = RELAY if host in AVOID else host
    mem = mem_for(size)
    if stream is not None:
        store = '%s/layout-viewer-store/%s' % (STREAM_ROOT[work_host], el)
    else:
        store = remote_store_dir(odb, el) if work_host == host else '%s/%s' % (RELAY_DIR, el)
    src_odb = odb
    ssh(work_host, 'mkdir -p %s/tools %s/raw' % (store, store), timeout=120)
    if stream is not None:   # an archived DB: stream it (compressed) from this host
        mark(stage='stream archived DB to %s (%.1f GB)' % (work_host, size / 1e9))
        src_odb = '%s/6_final.odb' % store
        chk = ssh(work_host, 'stat -c %%s %s 2>/dev/null' % src_odb, timeout=60)
        if chk.returncode or int(chk.stdout.strip() or 0) != size:
            dec = 'zstd -dcq' if stream.suffix == '.zst' else 'cat'
            with open(stream, 'rb') as fin:
                r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ControlPath=none', work_host,
                                    '%s > %s.tmp && mv %s.tmp %s' % (dec, src_odb, src_odb, src_odb)], stdin=fin, capture_output=True, timeout=6 * 3600)
            if r.returncode: raise RuntimeError('stream to %s failed: %s' % (work_host, r.stderr[-300:]))
    elif work_host != host:   # relay: stream the DB through this host (fleet hosts have no ssh to each other)
        mark(stage='relay %s -> %s (%.1f GB)' % (host, work_host, size / 1e9))
        src_odb = '%s/6_final.odb' % store
        chk = ssh(work_host, 'stat -c %%s %s 2>/dev/null' % src_odb, timeout=60)
        if chk.returncode or int(chk.stdout.strip() or 0) != size:
            cmd = 'ssh -o BatchMode=yes -o ControlPath=none %s "cat %s" | ssh -o BatchMode=yes -o ControlPath=none %s "cat > %s.tmp && mv %s.tmp %s"' % (
                host, shlex.quote(odb), work_host, src_odb, src_odb, src_odb)
            r = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True, timeout=6 * 3600)
            if r.returncode: raise RuntimeError('relay copy failed: %s' % r.stderr[-300:])
    mark(stage='ship tools to %s' % work_host)
    tar = subprocess.run(['tar', '-C', str(TOOLS), '-cf', '-', '.'], capture_output=True)
    r = ssh(work_host, 'tar -C %s/tools -xf -' % store, inp=tar.stdout, binary=True, timeout=300)
    if r.returncode: raise RuntimeError('ship tools: %s' % r.stderr[-300:])
    pk = '%s/%s.lvp' % (store, el)
    have = ssh(work_host, 'cd %s && test raw/meta.json -nt %s && cat ext.version 2>/dev/null; echo /; test -f %s.lvp && cat tile.version 2>/dev/null' % (
        store, shlex.quote(src_odb), shlex.quote(el)), timeout=60).stdout.split('/')
    ext_ok = have[0].strip() == EXTRACT_VERSION
    tile_ok = ext_ok and len(have) > 1 and have[1].strip() == TILE_VERSION
    if not ext_ok:
        mark(stage='extract (OpenDB, %d GB cap) on %s' % (mem, work_host))
        cmd = ('cd {st} && rm -f ext.version tile.version && nice -n 19 ot-heavy --mem {m} -- docker run --rm --memory {m}g --cpu-shares 128 --user $(id -u):$(id -g) '
               '-v {dbd}:/db:ro -v {st}/tools:/exp:ro -v {st}/raw:/out -e OT_DB=/db/{dbn} -e OT_OUT=/out -e HOME=/tmp {img} '
               '{orr} -python -exit /exp/lv_extract.py > {st}/extract.log 2>&1; r=$?; echo rc $r; tail -3 {st}/extract.log; [ $r = 0 ] && echo {v} > ext.version').format(
            st=store, m=mem, dbd=shlex.quote(os.path.dirname(src_odb)), dbn=shlex.quote(os.path.basename(src_odb)), img=IMAGE, orr=OPENROAD, v=EXTRACT_VERSION)
        r = ssh(work_host, cmd, timeout=8 * 3600)
        if 'rc 0' not in r.stdout: raise RuntimeError('extract failed on %s: %s %s' % (work_host, r.stdout[-400:], r.stderr[-200:]))
    if not tile_ok:
        mark(stage='cut tiles on %s' % work_host)
        tm = int(min(120, max(8, mem * 1.6)))
        cmd = ('cd {st} && nice -n 19 ot-heavy --mem {m} -- python3 tools/lv_tile.py --raw raw --out {el}.lvp --element {el} --meta-json {mj} '
               '> tile.log 2>&1; r=$?; echo rc $r; tail -3 tile.log; [ $r = 0 ] && echo {v} > tile.version').format(
            st=store, m=tm, el=shlex.quote(el), mj=shlex.quote(meta), v=TILE_VERSION)
        r = ssh(work_host, cmd, timeout=8 * 3600)
        if 'rc 0' not in r.stdout: raise RuntimeError('tile cut failed on %s: %s %s' % (work_host, r.stdout[-400:], r.stderr[-200:]))
    mark(stage='fetch pack from %s' % work_host)
    tmp = pathlib.Path(str(dst) + '.part')
    r = subprocess.run(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ControlPath=none', '%s:%s' % (work_host, pk), str(tmp)], capture_output=True, text=True, timeout=3600)
    if r.returncode: raise RuntimeError('fetch: %s' % r.stderr[-300:])
    os.replace(tmp, dst)
    return dst


# ------------------------------------------------------------------ packs
class Pack:
    """read-only view of one .lvp file (or of a store manifest: StorePack)"""
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.fh = open(self.path, 'rb')
        h = self.fh.read(24)
        if h[:8] != b'OTLVPK01': raise ValueError('not a layout pack: %s' % path)
        io, il = struct.unpack('<QQ', h[8:24])
        self.fh.seek(io); self.index = json.loads(brotli.decompress(self.fh.read(il)))
        st = self.path.stat()
        self.version = '%x%x' % (int(st.st_mtime), st.st_size)
        self.lock = threading.Lock()
        self._json = {}

    def raw(self, name):
        e = self.index.get(name)
        if e is None: return None
        with self.lock:
            self.fh.seek(e[0]); return self.fh.read(e[1])

    def json(self, name):
        if name not in self._json:
            b = self.raw(name)
            self._json[name] = None if b is None else json.loads(brotli.decompress(b))
        return self._json[name]

    def dec(self, name):
        k = '_d_' + name
        if k not in self._json:
            b = self.raw(name)
            self._json[k] = None if b is None else brotli.decompress(b)
        return self._json[k]

    def lines(self, name):
        k = '_l_' + name
        if k not in self._json:
            import numpy as np
            b = self.dec(name) or b''
            ends = np.flatnonzero(np.frombuffer(b, dtype=np.uint8) == 10)
            starts = np.concatenate([[0], ends[:-1] + 1]) if len(ends) else np.zeros(0, dtype=np.int64)
            self._json[k] = (b, starts, ends)
        return self._json[k]

    def line(self, name, i):
        b, st, en = self.lines(name)
        return b[st[i]:en[i]].decode('utf-8', 'replace') if 0 <= i < len(st) else None

    def find(self, name, q, limit):
        import numpy as np, re
        k = '_lc_' + name
        if k not in self._json: self._json[k] = self.lines(name)[0].lower()
        bl = self._json[k]; st = self.lines(name)[1]
        out, seen = [], set()
        for m in re.finditer(re.escape(q.lower().encode()), bl):
            i = int(np.searchsorted(st, m.start(), side='right') - 1)
            if i in seen: continue
            seen.add(i); out.append(i)
            if len(out) >= limit: break
        return out

    def close(self):
        try: self.fh.close()
        except Exception: pass


class StorePack(Pack):
    """a published closure: blobs are objects in the store"""
    def __init__(self, manifest_path):
        self.path = pathlib.Path(manifest_path)
        self.manifest = json.loads(self.path.read_text())
        self.index = self.manifest['objects']
        self.version = self.manifest['id']
        self.lock = threading.Lock()
        self._json = {}

    def raw(self, name):
        h = self.index.get(name)
        if h is None: return None
        try: return obj_path(h).read_bytes()
        except OSError: return None

    def close(self):
        pass


# ------------------------------------------------------------------ the store
def obj_path(h):
    return STORE / 'objects' / h[:2] / (h + '.br')


def put_object(b):
    h = hashlib.sha256(b).hexdigest()
    p = obj_path(h)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix('.tmp%d' % os.getpid()); tmp.write_bytes(b); os.replace(tmp, p)
    return h


def write_json(p, o):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp%d' % os.getpid()); tmp.write_text(json.dumps(o, separators=(',', ':'))); os.replace(tmp, p)


def closure_record(el, job, d):
    """what the manifest says about the closure: job state + committed verdict + bench record + the element page facts"""
    st = {}
    try: st = json.loads((JOBS / (job + '.json')).read_text())
    except Exception: pass
    verdict, vref = None, None
    p = REPO / 'results/closure_loop' / job / 'verdict.json'
    if p.exists():
        try: verdict = json.loads(p.read_text()); vref = 'main:results/closure_loop/%s/verdict.json' % job
        except Exception: pass
    m = (verdict or {}).get('metrics') or st.get('metrics') or {}
    spec = st.get('spec') or {}
    return dict(job=job, status=(verdict or st).get('status'), record=vref, host=st.get('host'),
                commit=(verdict or {}).get('source_commit') or st.get('commit_full') or (spec.get('source') or {}).get('commit'),
                closed_at=(verdict or {}).get('finished') or st.get('finished') or st.get('updated'),
                metrics={k: m.get(k) for k in ('setup_corner', 'ss_ps', 'ff_ps', 'drc', 'ss_tns_ps', 'ss_sensitivity_ps', 'orfs_dir') if k in m},
                bench=dict(spec={k: v for k, v in spec.items() if 'bench' in k.lower()}, stages=(spec.get('stages') or {}).get('bench') or [],
                           state=st.get('benches') or {}),
                facts=(d or {}).get('facts'))


def publish(el, job, pack_path, verify):
    """pack -> objects + manifest; index update (latest + history cap); returns the manifest"""
    pk = Pack(pack_path)
    objs = {}
    for name in pk.index:
        objs[name] = put_object(pk.raw(name))
    pk.close()
    d = element_json(el)
    # the element page's own data travels with the layout (it is the record the page is built from)
    for nm, fn in (('meta/element.json', el + '.json'), ('meta/cells.bin', el + '.cells.bin'), ('meta/clk.bin', el + '.clk.bin'),
                   ('meta/rtl.json', el + '.rtl.json')):
        f = ELEM_DATA / fn
        if f.exists(): objs[nm] = put_object(brotli.compress(f.read_bytes(), quality=9))
    hdr = json.loads(brotli.decompress(obj_path(objs['header']).read_bytes()))
    ident = hashlib.sha256(json.dumps(objs, sort_keys=True).encode()).hexdigest()[:16]
    man = dict(schema=SCHEMA, id=ident, element=el, job=job, made=now(), closure=closure_record(el, job, d),
               db=hdr.get('db'), source=hdr.get('source'), die=hdr.get('die'), dbu=hdr.get('dbu'),
               counts=hdr.get('counts'), lint=hdr.get('lint_summary'), verify=verify, objects=objs,
               bytes=sum(obj_path(h).stat().st_size for h in set(objs.values())))
    edir = STORE / 'elements' / el
    write_json(edir / (job + '.json'), man)
    with open(STORE / '.index.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        idx = {}
        try: idx = json.loads((edir / 'index.json').read_text())
        except Exception: pass
        hist = [j for j in idx.get('history', []) if j != job]
        hist.insert(0, job)
        drop = hist[HISTORY:]
        hist = hist[:HISTORY]
        write_json(edir / 'index.json', dict(element=el, latest=job, history=hist, updated=now(),
                                             manifests={j: '%s.json' % j for j in hist}))
        for j in drop: (edir / (j + '.json')).unlink(missing_ok=True)
    return man


def gc():
    """delete objects no manifest references"""
    ref = set()
    for m in (STORE / 'elements').glob('*/*.json'):
        if m.name == 'index.json': continue
        try: ref.update(json.loads(m.read_text())['objects'].values())
        except Exception: pass
    n = b = 0
    for p in (STORE / 'objects').glob('*/*.br'):
        if p.stem not in ref:
            b += p.stat().st_size; p.unlink(); n += 1
    return dict(deleted=n, bytes=b, referenced=len(ref))


def size_report():
    tot = sum(p.stat().st_size for p in (STORE / 'objects').glob('*/*.br')) if (STORE / 'objects').exists() else 0
    per = {}
    for idx in (STORE / 'elements').glob('*/index.json'):
        try:
            i = json.loads(idx.read_text()); m = json.loads((idx.parent / (i['latest'] + '.json')).read_text())
            per[i['element']] = dict(job=i['latest'], bytes=m.get('bytes'), history=len(i.get('history', [])), verify=(m.get('verify') or {}).get('verdict'))
        except Exception: pass
    return dict(bytes=tot, budget_bytes=BUDGET_GB * 1e9, elements=len(per), per_element=per)


def status_update(el, **kw):
    with open(STORE / '.status.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        p = STORE / 'STATUS.json'
        try: s = json.loads(p.read_text())
        except Exception: s = dict(schema=SCHEMA + '.status', elements={})
        e = s['elements'].setdefault(el, {}); e.update(kw, updated=now())
        s['no_db'] = sorted(k for k, v in s['elements'].items() if v.get('state') == 'nodb')
        s['generated'] = now()
        write_json(p, s)


def verify_pack(pack):
    node = shutil.which('node') or str(HOME / '.local/bin/node')
    r = subprocess.run([node, str(TOOLS / 'lv_verify.js'), str(pack)], capture_output=True, text=True, timeout=3600,
                       env=dict(os.environ, LV_DECODE=str(HERE / 'explorer' / 'element' / 'lv_decode.js')))
    try: o = json.loads(r.stdout)
    except Exception: return dict(verdict='ERROR', error=(r.stderr or r.stdout)[-300:])
    return dict(verdict=o['verdict'], shapes=o['shapes'], db_shapes=o['db_shapes'], tiles=o['tiles'], clipped_pieces=o['clipped_pieces'])


def cleanup(el, src):
    """the store is the record: drop the cut's working files (extraction ~ the DB's size, relay copy, pack)"""
    try:
        if src['kind'] == 'archive':
            shutil.rmtree(WORK / el, ignore_errors=True)
            if (src.get('size') or 0) > LOCAL_MAX_DB:
                host = STREAM_HOSTS[int(hashlib.sha1(el.encode()).hexdigest(), 16) % len(STREAM_HOSTS)]
                ssh(host, 'rm -rf %s/layout-viewer-store/%s' % (STREAM_ROOT[host], shlex.quote(el)), timeout=600)
        else:
            host = RELAY if src['host'] in AVOID else src['host']
            d = remote_store_dir(src['path'], el) if host == src['host'] else '%s/%s' % (RELAY_DIR, el)
            if d.rstrip('/').endswith('/' + el) and 'layout-viewer-store' in d:
                ssh(host, 'rm -rf %s' % shlex.quote(d), timeout=600)
    except Exception:
        pass


def export(el, job=None, log=log, force=False):
    """cut + verify + publish one closure; never raises.  A closure already published is skipped unless force."""
    t0 = time.time()
    if job and not force and (STORE / 'elements' / el / (job + '.json')).exists():
        log('%s: %s already published' % (el, job)); return True
    WORK.mkdir(parents=True, exist_ok=True)
    lk = open(WORK / ('.%s.lock' % el), 'w')
    try:   # one cut per element at a time across processes (hook, backfill, manual)
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log('%s: another export of this element is running' % el); lk.close(); return False
    try:
        STORE.mkdir(parents=True, exist_ok=True)
        status_update(el, state='running', stage='locate', job=job, error=None)
        src = locate(el, job)
        if src is None:
            status_update(el, state='nodb', stage='no routed DB: neither in the closed archive nor on the fleet host', job=job)
            log('%s: no DB' % el); return False
        job = src.get('job') or job
        mark = lambda **k: status_update(el, **k)
        status_update(el, source=src['kind'], host=src.get('host'), job=job)
        tmp = WORK / (el + '.export.lvp'); WORK.mkdir(parents=True, exist_ok=True)
        cut_pack(el, src, tmp, mark)
        mark(stage='verify (round trip against the DB truth)')
        ver = verify_pack(tmp)
        if ver.get('verdict') != 'IDENTICAL':
            status_update(el, state='failed', stage='verify', error='round trip %s' % json.dumps(ver)[:300]); return False
        mark(stage='publish')
        man = publish(el, job, tmp, ver)
        tmp.unlink(missing_ok=True)
        cleanup(el, src)
        status_update(el, state='done', stage='published', job=job, id=man['id'], bytes=man['bytes'], seconds=round(time.time() - t0),
                      shapes=ver.get('shapes'))
        log('%s: published %s (%s, %.1f MB, %d shapes, %.0f s)' % (el, job, src['kind'], man['bytes'] / 1e6, ver.get('shapes', 0), time.time() - t0))
        return True
    except Exception as e:
        status_update(el, state='failed', error=('%s: %s' % (type(e).__name__, e))[:600], trace=traceback.format_exc()[-800:])
        log('%s: FAILED %s' % (el, e))
        return False


# ------------------------------------------------------------------ backfill
def closed_elements():
    """registry rows of every CLOSED element (best closing job), in priority order"""
    import urllib.request
    d = json.loads(urllib.request.urlopen('http://127.0.0.1:8765/api/elements', timeout=120).read())
    rows = [r for r in d['rows'] if str(r.get('category', '')).startswith('closed') and (r.get('best') or {}).get('job')]
    pages = set()
    try: pages = set((json.loads((HERE / 'explorer/element/pages.json').read_text()).get('elements') or {}).keys())
    except Exception: pass
    def prio(r):   # element pages first, then the DeepSeek array (owner: array outranks wafer), HBM, Qwen, the rest
        t = str(r.get('target') or '').lower()
        tk = 0 if 'deepseek' in t or t.startswith('ds') else 1 if 'hbm' in t else 2 if 'qwen' in t else 3
        return (0 if r['element'] in pages else 1, tk, r['element'])
    return sorted(rows, key=prio)


def backfill(limit=None, only=None, workers=4, redo=False):
    rows = closed_elements()
    if only: rows = [r for r in rows if r['element'] in only]
    done = {}
    for idx in (STORE / 'elements').glob('*/index.json'):
        try: i = json.loads(idx.read_text()); done[i['element']] = i['latest']
        except Exception: pass
    todo = [r for r in rows if redo or done.get(r['element']) != r['best']['job']]
    if limit: todo = todo[:limit]
    log('backfill: %d of %d closed elements to export' % (len(todo), len(rows)))
    # one queue per DB source (each fleet host, the relay host, this host's archive), 2 cuts at a time per queue
    # (the local archive cuts are serialised by LOCAL_LOCK), so a run of elements on one host never idles the others
    queues = collections.OrderedDict()
    for r in todo:
        el, job = r['element'], r['best']['job']
        d = element_json(el) or {}
        host = (d.get('db') or ':').split(':', 1)[0]
        if not host:
            try: host = json.loads((JOBS / (job + '.json')).read_text()).get('host') or 'local'
            except Exception: host = 'local'
        a_ = archive_db(el, job)
        if a_: key = 'archive' if a_[1] <= LOCAL_MAX_DB else 'stream:' + STREAM_HOSTS[int(hashlib.sha1(el.encode()).hexdigest(), 16) % len(STREAM_HOSTS)]
        else: key = RELAY if host in AVOID else host
        queues.setdefault(key, []).append((el, job))
    log('backfill queues: ' + ', '.join('%s %d' % (k, len(v)) for k, v in queues.items()))
    res = []
    def run_queue(items):
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            return list(ex.map(lambda t: export(*t), items))
    with cf.ThreadPoolExecutor(max_workers=max(1, len(queues))) as ex:
        for r in ex.map(run_queue, queues.values()): res += r
    g = gc(); s = size_report()
    write_json(STORE / 'SIZE.json', s)
    log('backfill done: %d ok, %d not exported; store %.2f GB of %.0f GB budget; gc %s' % (sum(res), len(res) - sum(res), s['bytes'] / 1e9, BUDGET_GB, g))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    e = sp.add_parser('export'); e.add_argument('--element'); e.add_argument('--job'); e.add_argument('--force', action='store_true')
    b = sp.add_parser('backfill'); b.add_argument('--limit', type=int); b.add_argument('--only'); b.add_argument('--workers', type=int, default=4); b.add_argument('--redo', action='store_true')
    sp.add_parser('gc'); sp.add_parser('status'); sp.add_parser('audit', help='re-verify every published latest closure from the store files')
    a = ap.parse_args()
    if a.cmd == 'export':
        el = a.element
        if not el and a.job:   # the post-record hook knows the job only: the element whose page / registry row carries it
            el = next((p.stem for p in ELEM_DATA.glob('*.json') if p.name != 'index.json' and not p.name.endswith('.rtl.json')
                       and (element_json(p.stem) or {}).get('job') == a.job), None)
            if not el:
                try: el = next((r['element'] for r in closed_elements() if (r.get('best') or {}).get('job') == a.job), None)
                except Exception: el = None
            if not el:
                st = json.loads((JOBS / (a.job + '.json')).read_text())
                el = (st.get('spec') or {}).get('block') or a.job
        sys.exit(0 if export(el, a.job, force=a.force) else 1)
    if a.cmd == 'backfill': return backfill(a.limit, set(a.only.split(',')) if a.only else None, a.workers, a.redo)
    if a.cmd == 'gc': print(json.dumps(gc())); return
    if a.cmd == 'audit':
        out = {}
        for idx in sorted((STORE / 'elements').glob('*/index.json')):
            i = json.loads(idx.read_text()); out[i['element']] = verify_pack(idx.parent / (i['latest'] + '.json'))
            log(i['element'], out[i['element']].get('verdict'), out[i['element']].get('shapes'))
        write_json(STORE / 'AUDIT.json', dict(made=now(), elements=out, identical=sum(1 for v in out.values() if v.get('verdict') == 'IDENTICAL'), total=len(out)))
        return
    s = size_report(); write_json(STORE / 'SIZE.json', s); print(json.dumps(s, indent=1)[:4000])


if __name__ == '__main__':
    main()
