#!/usr/bin/env python3
"""OpenTallas Explorer server: the static app (web/) and the /api/v1 contract (tools/explorer/DESIGN.md section 7).

    python3 -I server.py [--port 8770] [--bind 127.0.0.1]

A thin read-only adapter over the data engines in tools/fleet_viz (design_service / design_index, layout_service /
layout_store, die_compose, coverage) and the token / data-flow records.  Environment (same file as the old service,
explorer2.env): FLEET_VIZ_STATE, FLEET_VIZ_REPO, LV_STORE, DESIGN_INDEX, TOKEN_DESIGN_MAP; optional EXPLORER_STATE (own
cache dir for composition manifests), DATAFLOW_DATA, TOKEN_DATA.  No pollers, no ssh, standard library + brotli.
"""
import argparse, gzip, hashlib, json, os, pathlib, re, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

HERE = pathlib.Path(__file__).resolve().parent
FV = HERE.parent / 'fleet_viz'
sys.path.insert(0, str(FV))
import design_service, layout_service, coverage, die_compose   # noqa: E402  (the engines)

WEB = HERE / 'web'
ENGINE = FV / 'explorer' / 'element'            # lv_worker.js, lv_decode.js, vendor/deck.gl (loaded as-is)
STATE = design_service.STATE
OWN = pathlib.Path(os.environ.get('EXPLORER_STATE', STATE / 'explorer_v1'))
DATAFLOW = pathlib.Path(os.environ.get('DATAFLOW_DATA', FV / 'explorer' / 'dataflow' / 'data'))
TOKEN = pathlib.Path(os.environ.get('TOKEN_DATA', FV / 'explorer' / 'token' / 'data'))
REPO = os.environ.get('FLEET_VIZ_REPO', str(HERE.parents[1]))
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
         '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
         '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.map': 'application/json'}
STALE_S = {'design_index': 3 * 3600, 'plan_now': 3 * 3600, 'compose': 3 * 3600, 'token_map': 26 * 3600,
           'token': 7 * 86400, 'dataflow': 7 * 86400, 'coverage': 7 * 86400, 'store': None}
LEGACY = {'/explorer': 'plan', '/explorer/': 'plan', '/explorer/design': 'plan', '/explorer/design/': 'plan',
          '/explorer/design/diemap.html': 'layout', '/explorer/element/': 'element', '/explorer/element': 'element',
          '/explorer/dataflow/': 'dataflow', '/explorer/dataflow': 'dataflow', '/explorer/token/': 'token', '/explorer/token': 'token',
          '/explorer/coverage/': 'closure', '/explorer/coverage': 'closure'}


class _NoElements:
    def snapshot(self, legacy=False): return {'rows': []}


DS = design_service.Service(log=lambda *a: None)
LS = layout_service.Service(log=lambda *a: None)
COV = coverage.Coverage(REPO, _NoElements(), TOKEN.parent, log=lambda *a: None)
LOCK = threading.RLock()
CACHE = {}          # key -> (stamp, raw, gz)


def _sha():
    try: return subprocess.run(['git', '-C', str(HERE), 'rev-parse', '--short=10', 'HEAD'], capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception: return None


SERVICE = dict(sha=_sha(), started=time.time())


def _mtime(p):
    try: return pathlib.Path(p).stat().st_mtime
    except OSError: return None


def _iso(v):
    """ISO-8601 / 'YYYY-MM-DD HH:MM PT' / epoch -> epoch seconds (None when unknown)"""
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v).strip()
    m = re.match(r'^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d)(?::(\d\d))?(?:\.\d+)?\s*(Z|PT|[+-]\d\d:?\d\d)?', s)
    if not m: return None
    import calendar
    t = calendar.timegm((int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6] or 0)))
    z = m[7]
    if z == 'PT': t += 8 * 3600
    elif z and z != 'Z': sign = 1 if z[0] == '+' else -1; z = z[1:].replace(':', ''); t -= sign * (int(z[:2]) * 3600 + int(z[2:]) * 60)
    return float(t)


def plan_sha(path):
    """short plan id of a plan-of-record path: the 12-hex content tag in the file name when there is one, else the stem"""
    stem = pathlib.Path(path or '').name.replace('.json.gz', '').replace('.json', '')
    m = re.search(r'([0-9a-f]{12})$', stem)
    return m.group(1) if m else stem


def plan_ref(p):
    return dict(path=p.get('path'), sha=plan_sha(p.get('path')), commit=(p.get('commit') or '')[:10] or None, date=p.get('date'), subject=p.get('subject'))


def cached(key, stamp, fn):
    with LOCK:
        c = CACHE.get(key)
        if c and c[0] == stamp: return c[1], c[2]
    raw = json.dumps(fn(), separators=(',', ':')).encode()
    val = (stamp, raw, gzip.compress(raw, 5))
    with LOCK: CACHE[key] = val
    return val[1], val[2]


class ApiError(Exception):
    def __init__(self, code, msg, detail=None): self.code, self.msg, self.detail = code, msg, detail


def index():
    idx = DS.index()
    if idx is None: raise ApiError(503, 'design index not built', 'design_index.py has not written %s' % design_service.INDEX)
    return idx


# ---------------------------------------------------------------------------------------------- datasets / freshness
def compose_of(die):
    """die composition manifest (die_compose.build), rebuilt when the node index changes; kept on disk under OWN"""
    idx = index()
    if die not in idx['dies']: raise ApiError(404, 'no such die', die)
    f = OWN / 'compose' / (die + '.json')
    try:
        m = json.loads(f.read_text())
        if m.get('index_generated') == idx.get('generated'): return m
    except (OSError, ValueError):
        pass
    with LOCK:
        m = die_compose.build(die, idx)
        m['plan']['sha'] = plan_sha(m['plan']['path'])
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix('.tmp'); tmp.write_text(json.dumps(m, separators=(',', ':'))); os.replace(tmp, f)
    return m


def _json_file(p):
    try: return json.loads(pathlib.Path(p).read_text())
    except (OSError, ValueError): return None


def datasets():
    now = time.time(); idx = DS.index(); out = []

    def add(i, label, generated, source, used_by, note=None, plans=None, missing=False):
        age = None if generated is None else max(0, now - generated)
        lim = STALE_S.get(i)
        state = 'missing' if missing or generated is None else ('stale' if lim and age > lim else 'fresh')
        out.append(dict(id=i, label=label, generated=generated, age_s=age, stale_after_s=lim, state=state, source=source, used_by=used_by, note=note, plans=plans))

    plans = {d: plan_ref(idx['nodes'][d]['plan']) for d in idx['dies'] if d in idx['nodes']} if idx else None
    add('design_index', 'Design index (dies, types, cores, sign-off state)', idx and idx.get('generated'), 'design_index.py over plan_now, the die plans of record and the signed store',
        ['overview', 'plan', 'layout', 'element', 'closure'], plans=plans, missing=idx is None)
    pn = STATE / 'plan_now.json'
    add('plan_now', 'Plan-now status (kit wave + signed store)', _mtime(pn), 'plan_now.py', ['overview', 'closure'])
    add('store', 'Routed layout packs (cut at sign-off, immutable)', _mtime(layout_service.LS.STORE / 'cuts.json') or _mtime(layout_service.LS.STORE / 'elements'), 'layout store (lv_extract + lv_tile, lv_verify IDENTICAL)', ['layout', 'element'],
        note='packs do not go stale: each is the geometry of one closure')
    cm = [_json_file(p) for p in sorted((OWN / 'compose').glob('*.json'))] if (OWN / 'compose').is_dir() else []
    cm = [m for m in cm if m]
    add('compose', 'Die composition manifests (placements + packs)', min((_iso(m.get('made')) or 0) for m in cm) if cm else (idx and idx.get('generated')), 'die_compose.py', ['layout'],
        note='%d of %d dies composed' % (len(cm), len(idx['dies']) if idx else 0) if idx else None)
    ti = _json_file(TOKEN / 'index.json')
    tgen = None; tnote = None
    if ti:
        recs = ti.get('records') or ti.get('designs') or []
        gens = [_iso(r.get('generated') or r.get('exported')) for r in recs if isinstance(r, dict)]
        gens = [g for g in gens if g]
        tgen = min(gens) if gens else _mtime(TOKEN / 'index.json')
        tnote = 'token records are exported from the simulator at a repo head; they describe the die revision named in each record'
    add('token', 'Token path records (simulator export)', tgen, 'tools/token_path_export.py', ['token'], note=tnote, missing=ti is None)
    tm = _json_file(design_service.TOKEN_MAP)
    add('token_map', 'Token class to design node map', tm and _iso(tm.get('generated')), 'token_design_map.py', ['token'], missing=tm is None)
    di = _json_file(DATAFLOW / 'index.json')
    dgen = None
    if di:
        gens = [g for g in (_iso(r.get('generated')) for r in di.get('records', [])) if g]
        dgen = max(gens) if gens else None
    add('dataflow', 'Data-flow link records', dgen, 'tools/fleet_viz/dataflow_links.py', ['dataflow'],
        note='link records are generated per die revision; the revision is named in each record', missing=di is None)
    try:
        cv = COV.version()
        add('coverage', 'Architecture coverage ledger', None if cv.get('err') else now, cv.get('source') or 'results/arch/coverage', ['closure'], note=cv.get('err'))
    except Exception as e:   # the ledger needs the repo; the rest of the app does not
        add('coverage', 'Architecture coverage ledger', None, 'results/arch/coverage', ['closure'], note=str(e), missing=True)
    return out


def meta():
    idx = DS.index()
    dies = [dict(id=d, label=idx['nodes'][d]['label'], plan=plan_ref(idx['nodes'][d]['plan'])) for d in idx['dies'] if d in idx['nodes']] if idx else []
    return dict(schema='opentallas.explorer.meta.v1', service=dict(SERVICE, now=time.time(), repo_main=(_json_file(STATE / 'plan_now.json') or {}).get('repo')),
                states=idx['states'] if idx else [], dies=dies, datasets=datasets())


# ---------------------------------------------------------------------------------------------- design
def dies():
    s = DS.summary(); idx = index()
    for d in s['dies']:
        p = idx['nodes'][d['id']]['plan']
        d['plan'] = plan_ref(p); d['period_ps'] = p.get('period_ps'); d['reach_um'] = p.get('reach_um')
        ns = [n for n in idx['nodes'].values() if n['die'] == d['id'] and n['level'] != 'die']
        d['packs'] = dict(type=sum(1 for n in ns if n['level'] == 'type' and (n.get('layout') or {}).get('store')),
                          core=sum(1 for n in ns if n['level'] == 'core' and (n.get('layout') or {}).get('store')))
        d['cores'] = sum(1 for n in ns if n['level'] == 'core')
        d['instances'] = dict(total=len(p['partitions']))
        st = {}
        for q in p['partitions']:
            k = ((idx['nodes'].get(q[1]) or {}).get('status') or {}).get('state', 'not built'); st[k] = st.get(k, 0) + 1
        d['instances']['by_state'] = st
        area = {}
        for q in p['partitions']:
            k = ((idx['nodes'].get(q[1]) or {}).get('status') or {}).get('state', 'not built'); area[k] = area.get(k, 0) + q[4] * q[5]
        d['area_um2'] = dict(die=p['outline'][0] * p['outline'][1], by_state=area)
    return s


def die(d):
    idx = index()
    if d not in idx['dies']: raise ApiError(404, 'no such die', d)
    r = DS.die(d); r['plan'] = plan_ref(r['die']['plan'])
    return r


def history(nid):
    ix = _json_file(layout_service.LS.STORE / 'elements' / nid / 'index.json')
    if not ix: return None
    return dict(latest=ix.get('latest'), history=ix.get('history') or [], updated=ix.get('updated'))


def node(nid):
    idx = index()
    if nid not in idx['nodes']: raise ApiError(404, 'no such node', nid)
    r = DS.node(nid); n = r['node']
    r['plan'] = plan_ref(idx['nodes'][n['die']]['plan'])
    r['packs'] = history(nid)
    if n['level'] == 'core':   # where the core sits: every (type, core instance) that places it
        uses = []
        for u in (n.get('plan') or {}).get('used_by') or []:
            t = idx['nodes'].get(u)
            if t: uses.append(dict(type=u, name=t['name'], state=t['status']['state'], count=sum(1 for h in t['plan']['hard_cores'] if h[1] == nid),
                                   insts=[h[0] for h in t['plan']['hard_cores'] if h[1] == nid][:24], placements=t['plan'].get('instances')))
        r['uses'] = uses
    return r


def closure(d):
    idx = index()
    if d not in idx['dies']: raise ApiError(404, 'no such die', d)
    rows = []
    for n in idx['nodes'].values():
        if n['die'] != d or n['level'] == 'die': continue
        st = n.get('status') or {}; m = st.get('metrics') or {}; lay = n.get('layout') or {}; s = lay.get('store') or {}; v = n.get('vis') or {}; p = n.get('plan') or {}
        rows.append(dict(id=n['id'], name=n['name'], level=n['level'], state=st.get('state'), label=st.get('label'), cls=st.get('cls'), stage=st.get('stage'),
                         attempt=st.get('attempt'), reason=st.get('reason'), tt_wns=m.get('tt_wns'), ff_wns=m.get('ff_wns'),
                         drc=m.get('drt_drc') if m.get('drt_drc') is not None else m.get('drc'), grt_overflow=m.get('grt_overflow'), lec=m.get('lec'),
                         cells=m.get('cells'), verdict=m.get('verdict'), instances=p.get('instances') if n['level'] == 'type' else p.get('placements'),
                         area_um2=(p['outline'][0] * p['outline'][1]) if p.get('outline') else None, cores=len(n.get('children') or []) if n['level'] == 'type' else None,
                         pack=bool(s), pack_verify=s.get('verify'), pack_shapes=s.get('shapes'), pack_made=s.get('made'), layout_stage=lay.get('stage'),
                         layout_source=lay.get('source'), vis=v.get('verdict'), vis_cls=v.get('cls'), vis_cause=v.get('cause'), hard=bool(p.get('hard'))))
    dn = idx['nodes'][d]
    return dict(die=d, label=dn['label'], plan=plan_ref(dn['plan']), states=idx['states'], counts=dn['counts'], generated=idx['generated'], rows=rows)


def search(q, d=None, limit=40):
    idx = index(); q = (q or '').strip().lower()
    if not q: return dict(q=q, results=[])
    terms = q.split(); out = []
    for nid, n in idx['nodes'].items():
        if d and n['die'] != d and len(out) > limit * 4: continue
        name = (n.get('name') or n.get('label') or nid).lower(); hay = nid.lower() + ' ' + name + ' ' + str((n.get('plan') or {}).get('module') or '').lower()
        if not all(t in hay for t in terms): continue
        score = (0 if name == q or nid.lower() == q else 1 if name.startswith(q) else 2) + (0 if not d or n['die'] == d else 3) + {'die': 0, 'type': 0.1, 'core': 0.2}[n['level']]
        out.append((score, len(name), dict(kind=n['level'], id=nid, name=n.get('name') or n.get('label'), die=n['die'], state=(n.get('status') or {}).get('state'),
                                           pack=bool((n.get('layout') or {}).get('store')))))
    for dd in idx['dies']:
        if dd not in idx['nodes']: continue
        for p in idx['nodes'][dd]['plan']['partitions']:
            nm = p[0].lower()
            if not all(t in nm for t in terms): continue
            score = (0 if nm == q else 1 if nm.startswith(q) else 2) + (0 if not d or dd == d else 3) + 0.3
            tn = idx['nodes'].get(p[1]) or {}
            out.append((score, len(nm), dict(kind='instance', id=p[1], inst=p[0], name=p[0], die=dd, of=tn.get('name'), state=(tn.get('status') or {}).get('state'),
                                             pack=bool((tn.get('layout') or {}).get('store')))))
    out.sort(key=lambda x: (x[0], x[1]))
    return dict(q=q, total=len(out), results=[x[2] for x in out[:limit]])


def resolve(names):
    idx = index(); out = {}
    for nm in names:
        hits = DS.resolve(nm)
        if not hits and nm in idx['nodes']: hits = [nm]
        out[nm] = hits
    return out


# ---------------------------------------------------------------------------------------------- token / data flow
def token_index():
    ti = _json_file(TOKEN / 'index.json')
    if ti is None: raise ApiError(404, 'no token records', str(TOKEN))
    tm = _json_file(design_service.TOKEN_MAP) or {}
    return dict(index=ti, map_generated=tm.get('generated'), mapped=sorted((tm.get('designs') or {}).keys()))


def dataflow_index():
    di = _json_file(DATAFLOW / 'index.json')
    if di is None: raise ApiError(404, 'no data-flow records', str(DATAFLOW))
    return di


# ---------------------------------------------------------------------------------------------- HTTP
class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'OpenTallasExplorer/1'

    def log_message(self, *a): pass

    def send(self, code, body, ctype, extra=()):   # the engines' handler contract (design_service / layout_service call this)
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body)))
        for k, v in extra: self.send_header(k, v)
        self.send_header('X-Content-Type-Options', 'nosniff'); self.end_headers()
        if self.command != 'HEAD': self.wfile.write(body)

    def json(self, key, stamp, fn):
        raw, gz = cached(key, stamp, fn)
        if 'gzip' in (self.headers.get('Accept-Encoding') or ''):
            return self.send(200, gz, 'application/json', (('Content-Encoding', 'gzip'), ('Cache-Control', 'no-cache'), ('Vary', 'Accept-Encoding')))
        return self.send(200, raw, 'application/json', (('Cache-Control', 'no-cache'),))

    def fail(self, code, msg, detail=None):
        return self.send(code, json.dumps(dict(error=msg, detail=detail)).encode(), 'application/json', (('Cache-Control', 'no-store'),))

    def file(self, base, rel, immutable=False):
        try:
            p = (base / rel).resolve(); ok = p.is_relative_to(base.resolve()) and p.is_file() and p.suffix in TYPES
        except (OSError, ValueError):
            ok = False
        if not ok: return self.fail(404, 'not found', rel)
        st = p.stat(); tag = '"%x-%x"' % (int(st.st_mtime), st.st_size)
        cc = 'public, max-age=31536000, immutable' if immutable else 'no-cache'
        if self.headers.get('If-None-Match') == tag:
            self.send_response(304); self.send_header('ETag', tag); self.send_header('Cache-Control', cc); self.send_header('Content-Length', '0'); self.end_headers(); return
        b = p.read_bytes(); extra = [('ETag', tag), ('Cache-Control', cc)]
        if p.suffix in ('.js', '.mjs', '.css', '.html', '.json', '.svg') and len(b) > 1024 and 'gzip' in (self.headers.get('Accept-Encoding') or ''):
            key = ('gz', str(p), tag)
            with LOCK:
                z = CACHE.get(key)
                if z is None: z = CACHE[key] = gzip.compress(b, 6)
            b = z; extra += [('Content-Encoding', 'gzip'), ('Vary', 'Accept-Encoding')]
        return self.send(200, b, TYPES[p.suffix], extra)

    def do_HEAD(self): self.do_GET()

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query); path = unquote(u.path)
        try:
            if path.startswith('/api/v1/'): return self.api(path[8:], q)
            if path == '/health': return self.health()
            if path in LEGACY and not (path.startswith('/explorer/element/') and path != '/explorer/element/'):
                self.send_response(302); self.send_header('Location', '/?legacy=' + LEGACY[path]); self.send_header('Content-Length', '0'); self.end_headers(); return
            if path.startswith('/engine/'): return self.file(ENGINE, path[8:], immutable='/vendor/' in path)
            if path.startswith('/explorer/element/'): return self.file(ENGINE, path[len('/explorer/element/'):])   # the worker's importScripts path
            if path.startswith('/fv/'): return self.file(FV / 'explorer', path[4:])   # kept view modules (token / data-flow models)
            rel = path.lstrip('/') or 'index.html'
            return self.file(WEB, rel)
        except ApiError as e:
            return self.fail(e.code, e.msg, e.detail)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as e:   # one broken dataset must not take the page down
            return self.fail(500, 'server error', '%s: %s' % (type(e).__name__, e))

    def api(self, p, q):
        g = lambda k, d='': (q.get(k, [d])[0] or d)
        idx = DS.index(); stamp = idx.get('generated') if idx else None
        if p == 'meta': return self.send(200, json.dumps(meta(), separators=(',', ':')).encode(), 'application/json', (('Cache-Control', 'no-store'),))
        if p == 'dies': return self.json('dies', stamp, dies)
        if p.startswith('die/'): d = p[4:]; return self.json('die:' + d, stamp, lambda: die(d))
        if p.startswith('node/'): n = p[5:]; return self.json('node:' + n, (stamp, _mtime(layout_service.LS.STORE / 'elements' / n / 'index.json')), lambda: node(n))
        if p.startswith('compose/'): d = p[8:]; return self.json('compose:' + d, stamp, lambda: compose_of(d))
        if p.startswith('closure/'): d = p[8:]; return self.json('closure:' + d, stamp, lambda: closure(d))
        if p == 'resolve': return self.send(200, json.dumps(resolve([x for x in g('q').split(',') if x][:400])).encode(), 'application/json', (('Cache-Control', 'no-cache'),))
        if p == 'search': return self.send(200, json.dumps(search(g('q'), g('die') or None, min(200, int(g('limit', '40') or 40)))).encode(), 'application/json', (('Cache-Control', 'no-cache'),))
        if p.startswith('layout/'): return LS.handle(self, p[7:], q, False)
        if p.startswith('store/'): return LS.static(self, p[6:], False)
        if p == 'dataflow/index': return self.json('df:index', _mtime(DATAFLOW / 'index.json'), dataflow_index)
        if p.startswith('dataflow/record/'):
            rid = p[len('dataflow/record/'):]
            if not layout_service.valid_name(rid): raise ApiError(400, 'bad record id', rid)
            f = DATAFLOW / (rid + '.links.json.gz')
            if not f.is_file(): raise ApiError(404, 'no such data-flow record', rid)
            return self.send(200, f.read_bytes(), 'application/json', (('Content-Encoding', 'gzip'), ('Cache-Control', 'no-cache')))
        if p == 'token/index': return self.json('tok:index', (_mtime(TOKEN / 'index.json'), _mtime(design_service.TOKEN_MAP)), token_index)
        if p.startswith('token/record/'):
            rid = p[len('token/record/'):]
            if not layout_service.valid_name(rid): raise ApiError(400, 'bad record id', rid)
            f = TOKEN / (rid + '.json')
            if not f.is_file(): raise ApiError(404, 'no such token record', rid)
            return self.json('tok:rec:' + rid, _mtime(f), lambda: json.loads(f.read_text()))
        if p.startswith('token/map/'):
            k = p[len('token/map/'):]
            return self.json('tok:map:' + k, (stamp, _mtime(design_service.TOKEN_MAP)), lambda: DS.token(k))
        if p == 'coverage':
            now = time.time(); o = dict(COV.api(), generated_at=now)
            return self.send(200, gzip.compress(json.dumps(o, separators=(',', ':')).encode(), 5), 'application/json', (('Content-Encoding', 'gzip'), ('Cache-Control', 'no-cache')))
        raise ApiError(404, 'unknown endpoint', p)

    def health(self):
        ds = datasets(); need = ('design_index', 'store')
        bad = [d['id'] for d in ds if d['id'] in need and d['state'] == 'missing']
        body = json.dumps(dict(ok=not bad, missing=bad, service=SERVICE, datasets={d['id']: d['state'] for d in ds})).encode()
        return self.send(200 if not bad else 503, body, 'application/json', (('Cache-Control', 'no-store'),))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', type=int, default=8770); ap.add_argument('--bind', default='127.0.0.1')
    a = ap.parse_args()
    s = ThreadingHTTPServer((a.bind, a.port), H); s.daemon_threads = True
    print('OpenTallas Explorer on http://%s:%d/ (index %s, store %s, sha %s)' % (a.bind, a.port, design_service.INDEX, layout_service.LS.STORE, SERVICE['sha']), flush=True)
    s.serve_forever()


if __name__ == '__main__':
    main()
