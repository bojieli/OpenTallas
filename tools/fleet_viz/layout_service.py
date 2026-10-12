"""Layout viewer service for fleet-viz.  See tools/fleet_viz/LAYOUT_VIEWER.md.

Closed elements are served from the static layout store (layout_store.py: content-addressed objects + one manifest per
closure, cut once at closure / by the backfill): plain static files, nothing is cut at view time.

  GET /layout_store/elements/<el>/index.json        latest closure + history (static)
  GET /layout_store/elements/<el>/<job>.json        manifest of one closure (static)
  GET /layout_store/objects/<h2>/<hash>.br          an immutable blob (Content-Encoding: br, or decoded for a client
                                                    that does not accept br)

Elements that are not in the store (not closed, or not yet exported) fall back to an on-demand cut into a bounded LRU
cache of packs (cut on the fleet host holding the DB, layout_store.cut_pack):
  GET /api/layout/<el>/status[?prepare=1]   state: static | ready | none | queued | running | failed | nodb
  GET /api/layout/<el>/b/<blob>?v=<pack>    one blob of the on-demand pack
Both: GET /api/layout/<el>/search?q=&k=net|inst|all, /api/layout/<el>/names?k=net|inst&ids=..   (name tables stay on
the server), GET /api/layout/_cache.
"""
import collections, json, os, pathlib, struct, threading, time

try:
    import brotli
except ImportError:  # pragma: no cover
    brotli = None
import layout_store as LS
from layout_store import Pack, StorePack, ssh

HERE = pathlib.Path(__file__).resolve().parent
ELEM_DATA = LS.ELEM_DATA
CACHE = pathlib.Path(os.environ.get('LV_CACHE', pathlib.Path.home() / '.cache' / 'layout-viewer'))
CACHE_GB = float(os.environ.get('LV_CACHE_GB', '8'))
STATE = pathlib.Path(os.environ.get('LV_STATE', pathlib.Path.home() / '.local' / 'state' / 'layout-viewer'))


def _log(*a):
    print(time.strftime('%H:%M:%S'), '[layout]', *a, flush=True)


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
        man = self.static_manifest(el)
        if man is not None:
            return dict(state='static', job=man['job'], id=man['id'], manifest='/layout_store/elements/%s/%s.json' % (el, man['job']),
                        index='/layout_store/elements/%s/index.json' % el)
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
        try:
            with self.total_sem, self.host_sem[db['host']]:
                t0 = time.time()
                self._mark(el, state='running', stage='locate', started=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
                src = LS.locate(el)
                if src is None: raise RuntimeError('routed DB not found (closed archive or %s)' % db['host'])
                dst = self.pack_path(el); tmp = dst.with_suffix('.part')
                LS.cut_pack(el, src, tmp, lambda **k: self._mark(el, **k))
                os.replace(tmp, dst)
                with self.lock:
                    old = self.packs.pop(el, None)
                    if old: old.close()
                    self.safe_hdr.pop(el, None)
                self._mark(el, state='ready', stage='ready', finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'), seconds=round(time.time() - t0, 1),
                           host=src.get('host') or 'archive', bytes=dst.stat().st_size)
                self.log('%s on-demand pack ready in %.0f s (%.1f MB)' % (el, time.time() - t0, dst.stat().st_size / 1e6))
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

    # ------------------------------------------------------------------ serving
    def static_manifest(self, el, job=None):
        try:
            i = json.loads((LS.STORE / 'elements' / el / 'index.json').read_text())
            return json.loads((LS.STORE / 'elements' / el / ((job or i['latest']) + '.json')).read_text())
        except Exception:
            return None

    def pack(self, el, job=None):
        key = el + '@' + (job or '')
        try:
            i = json.loads((LS.STORE / 'elements' / el / 'index.json').read_text())
            mp = LS.STORE / 'elements' / el / ((job or i['latest']) + '.json')
        except Exception:
            mp = None
        with self.lock:
            pk = self.packs.get(key)
            fresh = pk is not None and ((mp is None and not isinstance(pk, StorePack)) or
                                        (isinstance(pk, StorePack) and mp is not None and pk.path == mp and mp.stat().st_mtime <= pk._mt))
            if fresh:
                self.packs.move_to_end(key); return pk
        if mp is not None and mp.exists():
            pk = StorePack(mp); pk._mt = mp.stat().st_mtime
        else:
            p = self.pack_path(el)
            if not p.exists(): return None
            pk = Pack(p); pk._mt = 0
        with self.lock:
            self.packs[key] = pk
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
    def static(self, h, rel, safe):
        """/layout_store/<rel>: plain files of the store.  Objects are immutable (content hash); manifests and indexes are
        small JSON.  The share-safe view reads closures through /api/layout (redacted), never the raw manifests."""
        try:
            p = (LS.STORE / rel).resolve()
            ok = p.is_relative_to(LS.STORE.resolve()) and p.is_file() and (rel.startswith('objects/') or rel.startswith('elements/'))
        except (OSError, ValueError):
            ok = False
        if not ok: return h.send(404, b'not found', 'text/plain')
        if safe and rel.startswith('elements/'): return h.send(403, b'{"safe":true}', 'application/json')
        b = p.read_bytes()
        if p.suffix == '.br':
            br = 'br' in (h.headers.get('Accept-Encoding') or '')
            body = b if br else brotli.decompress(b)
            h.send_response(200); h.send_header('Content-Type', 'application/octet-stream'); h.send_header('Content-Length', str(len(body)))
            if br: h.send_header('Content-Encoding', 'br')
            h.send_header('Vary', 'Accept-Encoding'); h.send_header('Cache-Control', 'public, max-age=31536000, immutable')
            h.send_header('X-Content-Type-Options', 'nosniff'); h.end_headers()
            if h.command != 'HEAD': h.wfile.write(body)
            return
        return h.send(200, b, 'application/json')

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
