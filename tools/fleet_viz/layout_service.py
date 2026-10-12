"""Layout viewer tiling service for fleet-viz (/api/layout/...).  See tools/fleet_viz/LAYOUT_VIEWER.md.

An element's routed DB stays on the fleet host that holds it.  On the first request (or from the background
precompute) the service ships tools/layout_viewer/{lv_extract,lv_tile,lv_lint}.py + child_lint.py to that host, runs
the lossless OpenDB extraction in the ORFS container and the tile cutter beside it, both under ot-heavy with a memory
cap sized from the DB, and fetches the finished pack (<element>.lvp) into a bounded on-disk LRU cache here.  The HTTP
side only reads blobs out of cached packs: brotli bytes passed straight through (Content-Encoding: br) or decompressed
for a client that does not accept br.

  GET /api/layout/<el>/status[?prepare=1]   state: none | queued | running | ready | failed | nodb (+ stage, error)
  GET /api/layout/<el>/b/<blob>?v=<pack>    one pack blob: header, names, lint, cong, ibb, nbb, t/<x>_<y>, r/<l>/<x>_<y>
  GET /api/layout/<el>/search?q=&k=net|inst|pin   names containing q (case-insensitive), with bbox
  GET /api/layout/_cache                    cache + queue summary
Elements on ot-epyc4 (saturated) are extracted on a relay host: the ODB is streamed through this host to ot-epyc3.
"""
import collections, fcntl, json, os, pathlib, shlex, shutil, struct, subprocess, threading, time

try:
    import brotli
except ImportError:  # pragma: no cover
    brotli = None

HERE = pathlib.Path(__file__).resolve().parent
ELEM_DATA = HERE / 'explorer' / 'element' / 'data'
TOOLS = pathlib.Path(os.environ.get('LV_TOOLS', HERE / 'layout_viewer'))   # deployed copy of tools/layout_viewer + child_lint.py
CACHE = pathlib.Path(os.environ.get('LV_CACHE', pathlib.Path.home() / '.cache' / 'layout-viewer'))
CACHE_GB = float(os.environ.get('LV_CACHE_GB', '24'))
STATE = pathlib.Path(os.environ.get('LV_STATE', pathlib.Path.home() / '.local' / 'state' / 'layout-viewer'))
IMAGE = 'openroad/orfs:asap7lock'
OPENROAD = '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
AVOID = set(filter(None, os.environ.get('LV_AVOID_HOSTS', 'ot-epyc4').split(',')))
RELAY = os.environ.get('LV_RELAY_HOST', 'ot-epyc3')
RELAY_DIR = os.environ.get('LV_RELAY_DIR', '/srv/opentallas-scratch/claude/layout-viewer-store/relay')
PRECOMPUTE = os.environ.get('LV_PRECOMPUTE', '1') == '1'
PRE_MAX_MEM = int(os.environ.get('LV_PRECOMPUTE_MAX_MEM', '31'))    # background work stays in ot-heavy's small slots
EXTRACT_VERSION = 'e1'   # bump when lv_extract.py output changes (forces re-extraction)
TILE_VERSION = 't2'      # bump when lv_tile.py / lv_lint.py output changes (re-cut from the kept extraction)


def _log(*a):
    print(time.strftime('%H:%M:%S'), '[layout]', *a, flush=True)


def ssh(host, cmd, inp=None, timeout=1800, binary=False):
    args = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=30', '-o', 'ControlPath=none', host, cmd]
    return subprocess.run(args, input=inp, capture_output=True, text=not binary, timeout=timeout)


class Pack:
    """read-only view of one .lvp file"""
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
        """decompressed blob bytes, cached while the pack is open"""
        k = '_d_' + name
        if k not in self._json:
            b = self.raw(name)
            self._json[k] = None if b is None else brotli.decompress(b)
        return self._json[k]

    def lines(self, name):
        """(bytes, line-start offsets) of a newline-joined name blob"""
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
        """indices of lines containing q (case-insensitive)"""
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


class Service:
    def __init__(self, log=_log):
        self.log = log
        CACHE.mkdir(parents=True, exist_ok=True); STATE.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.packs = collections.OrderedDict()      # element -> Pack (open file handles, LRU 12)
        self.jobs = {}                              # element -> thread
        self.host_sem = collections.defaultdict(lambda: threading.Semaphore(2))
        self.total_sem = threading.Semaphore(4)
        self.safe_hdr = {}
        if PRECOMPUTE:
            threading.Thread(target=self._precompute, daemon=True, name='layout-precompute').start()

    # ------------------------------------------------------------------ state
    def _mark(self, el, **kw):
        p = STATE / (el + '.json')
        d = self._state(el)
        d.update(kw, updated=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
        tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(d)); os.replace(tmp, p)
        return d

    def _state(self, el):
        try: return json.loads((STATE / (el + '.json')).read_text())
        except Exception: return {}

    def element_db(self, el):
        try: d = json.loads((ELEM_DATA / (el + '.json')).read_text())
        except Exception: return None
        db = d.get('db') or ''
        if ':' not in db: return None
        host, path = db.split(':', 1)
        return dict(host=host, path=path, job=d.get('job'), label=d.get('label'))

    def pack_path(self, el):
        return CACHE / (el + '.lvp')

    def status(self, el, prepare=False, background=False):
        if not valid_name(el): return dict(state='invalid')
        p = self.pack_path(el)
        st = self._state(el)
        if p.exists():
            try: os.utime(p, None)   # LRU touch
            except OSError: pass
            pk = self.pack(el)
            return dict(state='ready', version=pk.version if pk else None, bytes=p.stat().st_size, made=st.get('finished'), host=st.get('host'))
        db = self.element_db(el)
        if db is None: return dict(state='nodb', reason='no routed DB recorded for this element (fleet-viz element data has no db field)')
        with self.lock:
            running = el in self.jobs and self.jobs[el].is_alive()
        if running: return dict(state=st.get('state', 'running'), stage=st.get('stage'), started=st.get('started'), host=st.get('host'))
        if prepare and not (st.get('state') == 'failed' and time.time() - st.get('failed_at', 0) < 600):
            self.start(el, db, background=background)
            st = self._state(el)
            return dict(state='queued', stage=st.get('stage'), host=db['host'])
        if st.get('state') == 'failed': return dict(state='failed', error=st.get('error'), stage=st.get('stage'), host=st.get('host'))
        return dict(state='none', host=db['host'])

    def start(self, el, db, background=False):
        with self.lock:
            if el in self.jobs and self.jobs[el].is_alive(): return
            self._mark(el, state='queued', stage='queued', host=db['host'], error=None, background=background)
            t = threading.Thread(target=self._run, args=(el, db, background), daemon=True, name='layout-' + el)
            self.jobs[el] = t
            t.start()

    # ------------------------------------------------------------------ pipeline
    def _run(self, el, db, background):
        host, odb = db['host'], db['path']
        work_host = RELAY if host in AVOID else host
        try:
            with self.total_sem, self.host_sem[work_host]:
                t0 = time.time()
                self._mark(el, state='running', stage='probe', started=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
                pr = ssh(host, 'stat -c "%%s %%Y" %s' % shlex.quote(odb), timeout=120)
                if pr.returncode: raise RuntimeError('routed DB not found on %s: %s' % (host, odb))
                size, mtime = map(int, pr.stdout.split())
                mem = int(min(160, max(8, -(-(12 * size) // 10 ** 9) + 6)))
                if background and mem > PRE_MAX_MEM:
                    self._mark(el, state='none', stage='deferred: DB too large for background precompute (%d GB cap); opens on demand' % mem)
                    return
                store = store_dir(work_host, odb, el) if work_host == host else '%s/%s' % (RELAY_DIR, el)
                src_odb = odb
                ssh(work_host, 'mkdir -p %s/tools/pylib314 %s/raw' % (store, store), timeout=120)
                if work_host != host:   # relay: stream the DB through this host (no ssh between fleet hosts)
                    self._mark(el, stage='relay %s -> %s (%.1f GB)' % (host, work_host, size / 1e9))
                    src_odb = '%s/6_final.odb' % store
                    chk = ssh(work_host, 'stat -c %%s %s 2>/dev/null' % src_odb, timeout=60)
                    if chk.returncode or int(chk.stdout.strip() or 0) != size:
                        cmd = 'ssh -o BatchMode=yes -o ControlPath=none %s "cat %s" | ssh -o BatchMode=yes -o ControlPath=none %s "cat > %s.tmp && mv %s.tmp %s"' % (
                            host, shlex.quote(odb), work_host, src_odb, src_odb, src_odb)
                        r = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True, timeout=6 * 3600)
                        if r.returncode: raise RuntimeError('relay copy failed: %s' % r.stderr[-300:])
                # ship the tools
                self._mark(el, stage='ship tools to %s' % work_host)
                tar = subprocess.run(['tar', '-C', str(TOOLS), '-cf', '-', '.'], capture_output=True)
                r = ssh(work_host, 'tar -C %s/tools -xf -' % store, inp=tar.stdout, binary=True, timeout=300)
                if r.returncode: raise RuntimeError('ship tools: %s' % r.stderr[-300:])
                # reuse what the host already has: the extraction when it is newer than the DB and of this extractor
                # version, the pack when it is also of this tile-cutter version
                pk = '%s/%s.lvp' % (store, el)
                have = ssh(work_host, 'cd %s && test raw/meta.json -nt %s && cat ext.version 2>/dev/null; echo /; test -f %s.lvp && cat tile.version 2>/dev/null' % (
                    store, shlex.quote(src_odb), shlex.quote(el)), timeout=60).stdout.split('/')
                ext_ok = have[0].strip() == EXTRACT_VERSION
                tile_ok = ext_ok and len(have) > 1 and have[1].strip() == TILE_VERSION
                if not ext_ok:
                    self._mark(el, stage='extract (OpenDB, %d GB cap) on %s' % (mem, work_host))
                    cmd = ('cd {st} && rm -f ext.version tile.version && nice -n 19 ot-heavy --mem {m} -- docker run --rm --memory {m}g --cpu-shares 128 --user $(id -u):$(id -g) '
                           '-v {dbd}:/db:ro -v {st}/tools:/exp:ro -v {st}/raw:/out -e OT_DB=/db/{dbn} -e OT_OUT=/out -e HOME=/tmp {img} '
                           '{orr} -python -exit /exp/lv_extract.py > {st}/extract.log 2>&1; r=$?; echo rc $r; tail -3 {st}/extract.log; [ $r = 0 ] && echo {v} > ext.version').format(
                        st=store, m=mem, dbd=shlex.quote(os.path.dirname(src_odb)), dbn=shlex.quote(os.path.basename(src_odb)), img=IMAGE, orr=OPENROAD, v=EXTRACT_VERSION)
                    r = ssh(work_host, cmd, timeout=6 * 3600)
                    if 'rc 0' not in r.stdout: raise RuntimeError('extract failed: %s %s' % (r.stdout[-400:], r.stderr[-200:]))
                if not tile_ok:
                    self._mark(el, stage='cut tiles on %s' % work_host)
                    mj = json.dumps(dict(db='%s:%s' % (host, odb), job=db.get('job'), extract_host=work_host))
                    tm = int(min(120, max(8, mem * 1.6)))
                    cmd = ('cd {st} && nice -n 19 ot-heavy --mem {m} -- python3 tools/lv_tile.py --raw raw --out {el}.lvp --element {el} --meta-json {mj} '
                           '> tile.log 2>&1; r=$?; echo rc $r; tail -3 tile.log; [ $r = 0 ] && echo {v} > tile.version').format(
                        st=store, m=tm, el=shlex.quote(el), mj=shlex.quote(mj), v=TILE_VERSION)
                    r = ssh(work_host, cmd, timeout=6 * 3600)
                    if 'rc 0' not in r.stdout: raise RuntimeError('tile cut failed: %s %s' % (r.stdout[-400:], r.stderr[-200:]))
                self._mark(el, stage='fetch pack')
                dst = self.pack_path(el); tmp = dst.with_suffix('.part')
                r = subprocess.run(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ControlPath=none', '%s:%s' % (work_host, pk), str(tmp)], capture_output=True, text=True, timeout=3600)
                if r.returncode: raise RuntimeError('fetch: %s' % r.stderr[-300:])
                os.replace(tmp, dst)
                with self.lock:
                    old = self.packs.pop(el, None)
                    if old: old.close()
                    self.safe_hdr.pop(el, None)
                self._mark(el, state='ready', stage='ready', finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'), seconds=round(time.time() - t0, 1),
                           store='%s:%s' % (work_host, store), bytes=dst.stat().st_size)
                self.log('%s ready in %.0f s (%s, %.1f MB)' % (el, time.time() - t0, work_host, dst.stat().st_size / 1e6))
                self.evict()
        except Exception as e:
            self._mark(el, state='failed', error=('%s: %s' % (type(e).__name__, e))[:600], failed_at=time.time())
            self.log('%s FAILED: %s' % (el, e))

    def evict(self):
        files = sorted(CACHE.glob('*.lvp'), key=lambda p: p.stat().st_mtime)
        tot = sum(p.stat().st_size for p in files)
        while files and tot > CACHE_GB * 1e9:
            p = files.pop(0); tot -= p.stat().st_size
            with self.lock:
                pk = self.packs.pop(p.stem, None)
                if pk: pk.close()
            try: p.unlink()
            except OSError: pass
            self.log('evicted %s' % p.name)

    def _precompute(self):
        time.sleep(90)
        while True:
            try:
                idx = json.loads((ELEM_DATA / 'index.json').read_text()).get('elements', {})
                todo = []
                for el, e in sorted(idx.items()):
                    if not e.get('layout') or self.pack_path(el).exists(): continue
                    st = self._state(el)
                    if st.get('state') == 'failed' or str(st.get('stage', '')).startswith('deferred'): continue   # failures retry on demand only
                    db = self.element_db(el)
                    if db and db['host'] not in AVOID: todo.append((el, db))
                for el, db in todo:
                    if self.pack_path(el).exists(): continue
                    self.start(el, db, background=True)
                    while el in self.jobs and self.jobs[el].is_alive(): time.sleep(5)
                    time.sleep(20)
            except Exception as e:
                self.log('precompute: %s' % e)
            time.sleep(1800)

    # ------------------------------------------------------------------ serving
    def pack(self, el):
        with self.lock:
            pk = self.packs.get(el)
            if pk is not None:
                self.packs.move_to_end(el); return pk
        p = self.pack_path(el)
        if not p.exists(): return None
        pk = Pack(p)
        with self.lock:
            self.packs[el] = pk
            while len(self.packs) > 12:
                _, o = self.packs.popitem(last=False); o.close()
        return pk

    def blob(self, el, name, safe):
        """(compressed bytes or None, decompressed-JSON-for-safe or None)"""
        pk = self.pack(el)
        if pk is None: return None
        if safe:
            if name in ('names', 'ibb', 'nbb', 'nn', 'ni', 'nns'): return b'FORBIDDEN'
            if name in ('header', 'lint'):
                k = (el, name, pk.version)
                if k not in self.safe_hdr:
                    o = redact(name, pk.json(name))
                    self.safe_hdr[k] = brotli.compress(json.dumps(o, separators=(',', ':')).encode(), quality=5)
                return self.safe_hdr[k]
        return pk.raw(name)

    def _net(self, pk, i):
        nm = pk.json('names'); sig = pk.dec('nns'); nbb = pk.dec('nbb')
        return dict(k='net', id=i, name=pk.line('nn', i - 1), sig=nm['sig_codes'][sig[i - 1]] if sig else None,
                    bbox=list(struct.unpack_from('<4i', nbb, 16 * i)) if nbb else None)

    def _inst(self, pk, i):
        if '_ibb' not in pk._json:
            import numpy as np
            b = pk.dec('ibb')
            a = np.frombuffer(b, dtype='<i4').reshape(5, -1) if b else None
            pk._json['_ibb'] = None if a is None else (np.cumsum(a[0], dtype=np.int64), np.cumsum(a[1], dtype=np.int64), a[2], a[3], a[4])
        c = pk._json['_ibb']
        if c is None: return dict(k='inst', id=i, name=pk.line('ni', i))
        x0, y0 = int(c[0][i]), int(c[1][i])
        return dict(k='inst', id=i, name=pk.line('ni', i), bbox=[x0, y0, x0 + int(c[2][i]), y0 + int(c[3][i])], master=int(c[4][i]))

    def search(self, el, q, kind, limit=40):
        pk = self.pack(el)
        if pk is None or not q: return []
        out = []
        if kind in ('net', 'all'):
            out += [self._net(pk, i + 1) for i in pk.find('nn', q, limit)]
        if kind in ('inst', 'all') and len(out) < limit:
            out += [self._inst(pk, i) for i in pk.find('ni', q, limit - len(out))]
        if kind in ('pin', 'all') and len(out) < limit:
            nm = pk.json('names'); ql = q.lower()
            for i, n in enumerate(nm['bterms']):
                if ql in n.lower():
                    out.append(dict(k='pin', id=i, name=n, io=nm['bterm_io'][i]))
                    if len(out) >= limit: break
        return out

    def names_of(self, el, kind, ids):
        pk = self.pack(el)
        if pk is None: return []
        nm = pk.json('names')
        if kind == 'net': return [self._net(pk, i) for i in ids[:500] if 1 <= i <= nm['n_nets']]
        if kind == 'inst': return [self._inst(pk, i) for i in ids[:500] if 0 <= i < nm['n_insts']]
        return []

    def cache_summary(self):
        files = list(CACHE.glob('*.lvp'))
        with self.lock: running = [k for k, t in self.jobs.items() if t.is_alive()]
        return dict(packs=len(files), bytes=sum(p.stat().st_size for p in files), cap_bytes=CACHE_GB * 1e9, running=running)

    # ------------------------------------------------------------------ HTTP glue (called from server.py)
    def handle(self, h, path, q, safe):
        """h: the BaseHTTPRequestHandler; path after /api/layout/"""
        parts = path.split('/', 2)
        el = parts[0]
        def js(o, code=200):
            return h.send(code, json.dumps(o, separators=(',', ':')).encode(), 'application/json')
        if el == '_cache': return js(self.cache_summary())
        if not valid_name(el): return js(dict(error='bad element'), 400)
        what = parts[1] if len(parts) > 1 else 'status'
        if what == 'status':
            return js(self.status(el, prepare=q.get('prepare', ['0'])[0] == '1'))
        if what == 'search':
            if safe: return js(dict(error='share-safe view: no name search'), 403)
            return js(dict(results=self.search(el, (q.get('q', [''])[0] or '')[:200], q.get('k', ['all'])[0])))
        if what == 'names':
            if safe: return js(dict(error='share-safe view: names hidden'), 403)
            try: ids = [int(x) for x in (q.get('ids', [''])[0] or '').split(',') if x][:500]
            except ValueError: return js(dict(error='bad ids'), 400)
            return js(dict(items=self.names_of(el, q.get('k', ['net'])[0], ids)))
        if what == 'b' and len(parts) == 3:
            name = parts[2]
            b = self.blob(el, name, safe)
            if b is None: return js(dict(error='no such blob'), 404)
            if b == b'FORBIDDEN': return js(dict(error='share-safe view'), 403)
            ctype = 'application/json' if name in ('header', 'names', 'lint') else 'application/octet-stream'
            br = 'br' in (h.headers.get('Accept-Encoding') or '')
            body = b if br else brotli.decompress(b)
            h.send_response(200); h.send_header('Content-Type', ctype); h.send_header('Content-Length', str(len(body)))
            if br: h.send_header('Content-Encoding', 'br')
            h.send_header('Vary', 'Accept-Encoding')
            h.send_header('Cache-Control', 'private, max-age=31536000, immutable' if q.get('v') else 'no-store')
            h.send_header('X-Content-Type-Options', 'nosniff'); h.end_headers()
            if h.command != 'HEAD': h.wfile.write(body)
            return
        return js(dict(error='unknown layout endpoint'), 404)


def valid_name(el):
    return bool(el) and len(el) < 200 and all(c.isalnum() or c in '_-.' for c in el) and not el.startswith('.')


def store_dir(host, odb, el):
    p = pathlib.PurePosixPath(odb)
    parts = p.parts
    if 'closure-loop' in parts:
        root = pathlib.PurePosixPath(*parts[:parts.index('closure-loop')])
        return str(root / 'layout-viewer-store' / el)
    return str(p.parent / 'layout-viewer-store' / el)


def redact(name, o):
    o = json.loads(json.dumps(o))
    if name == 'header':
        o.pop('db', None); o.pop('job', None); o.pop('extract_host', None)
        for k, m in enumerate(o.get('macros') or []):
            m['name'] = 'macro %d' % (k + 1); m['master'] = 'macro master'
        for m in o.get('masters') or []:
            if m.get('block'): m['name'] = 'macro master'
        o['top'] = 'element'
    if name == 'lint':
        for f in o.get('findings') or []:
            if f.get('inst'): f['inst'] = 'macro'
            f['title'] = f.get('title', '').split(' (')[0]
            f['reason'] = '(names hidden in the share-safe view) ' + f.get('reason', '').split(', e.g.')[0]
        o.pop('summary', None)
    return o
