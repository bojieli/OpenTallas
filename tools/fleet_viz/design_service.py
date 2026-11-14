"""Design explorer service (EXPLORER-2): the die -> type -> core pages and their API, served from the one node index
(design_index.py -> <state>/design_index.json) and the static layout store (layout_service.py, unchanged).

  GET /explorer/design/            the page (die / type / core by #n=<node id>)
  GET /api/design/index            dies with labels, plan facts and per-state counts (small)
  GET /api/design/die/<die>        the die node + every type and core node of that die
  GET /api/design/node/<id>        one node + its die summary + its child nodes (a type's cores)
  GET /api/design/token/<design>   token step classes -> current type / core nodes (token_design_map.py), with each
                                   node's status; the token page's "runs on" panel
  GET /api/design/compose/<die>    die composition manifest of the routed die map (die_compose.py)
  GET /api/design/resolve?q=<name> name (type, core module, partition, old element name) -> node ids, for the token,
                                   dataflow and coverage pages
"""
import gzip, json, os, pathlib, re, threading

HERE = pathlib.Path(__file__).resolve().parent
STATE = pathlib.Path(os.environ.get('FLEET_VIZ_STATE', os.path.expanduser('~/.local/state/fleet-viz')))
INDEX = pathlib.Path(os.environ.get('DESIGN_INDEX', STATE / 'design_index.json'))
TOKEN_MAP = pathlib.Path(os.environ.get('TOKEN_DESIGN_MAP', INDEX.parent / 'token_design_map.json'))   # token_design_map.py
PAGE_DIR = HERE / 'explorer' / 'design'
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
         '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png'}


class Service:
    def __init__(self, log=print):
        self.log = log; self.lock = threading.RLock(); self.mt = None; self.idx = None; self.cache = {}

    def index(self):
        try: mt = INDEX.stat().st_mtime
        except OSError: return None
        with self.lock:
            if mt != self.mt:
                self.idx = json.loads(INDEX.read_text()); self.mt = mt; self.cache = {}
                self.names = {}
                for nid, n in self.idx['nodes'].items():
                    if n['level'] != 'die': self.names.setdefault(n['name'], []).append(nid)
                    if n['level'] == 'die':
                        for p in n['plan']['partitions']: self.names.setdefault(p[0], []).append(p[1])
            return self.idx

    def _gz(self, key, fn):
        with self.lock:
            if key not in self.cache:
                raw = json.dumps(fn(), separators=(',', ':')).encode()
                self.cache[key] = (raw, gzip.compress(raw, 6))
            return self.cache[key]

    def summary(self):
        idx = self.index()
        out = []
        for d in idx['dies']:
            n = idx['nodes'].get(d)
            if not n: continue
            p = n['plan']
            out.append(dict(id=d, label=n['label'], target=n.get('target'), counts=n['counts'], outline=p['outline'], partitions=len(p['partitions']),
                            types=n.get('type_count', len(n['children'])), hard_ip=n.get('hard_ip') or [], plan=p['path'], plan_date=p.get('date'), release_header=p.get('release_header'),
                            exported=sum(1 for x in idx['nodes'].values() if x['die'] == d and (x.get('layout') or {}).get('store'))))
        return dict(schema=idx['schema'], generated=idx['generated'], states=idx['states'], dies=out, sources=idx.get('sources'))

    def die(self, d):
        idx = self.index()
        return dict(die=idx['nodes'][d], states=idx['states'], generated=idx['generated'],
                    nodes={k: v for k, v in idx['nodes'].items() if v['die'] == d and v['level'] != 'die'})

    def node(self, nid):
        idx = self.index(); n = idx['nodes'][nid]
        d = idx['nodes'][n['die']]
        kids = {c: idx['nodes'][c] for c in n.get('children') or [] if c in idx['nodes']} if n['level'] != 'die' else {}
        users = {u: dict(id=u, name=idx['nodes'][u]['name'], status=idx['nodes'][u]['status']) for u in (n.get('plan') or {}).get('used_by') or [] if u in idx['nodes']}
        places = [[p[0], p[2], p[3], p[4], p[5], p[6]] for p in d['plan']['partitions'] if p[1] == nid] if n['level'] == 'type' else []
        return dict(node=n, die=dict(id=d['id'], label=d['label'], outline=d['plan']['outline'], reach_um=d['plan'].get('reach_um')),
                    children=kids, users=users, placements=places, states=idx['states'], generated=idx['generated'])

    def token(self, design):
        idx = self.index()
        try: m = json.loads(TOKEN_MAP.read_text())
        except Exception: return dict(error='token design map not built yet (token_design_map.py)')
        d = (m.get('designs') or {}).get(design)
        if not d: return dict(error='no token design map for %s' % design)
        ids = {i for c in d['classes'].values() for i in c['nodes']}
        nodes = {i: dict(level=idx['nodes'][i]['level'], die=idx['nodes'][i]['die'], name=idx['nodes'][i]['name'], state=idx['nodes'][i]['status']['state'],
                         layout=bool((idx['nodes'][i].get('layout') or {}).get('store'))) for i in ids if i in idx['nodes']}
        return dict(d, steps=None, nodes=nodes, generated=m.get('generated'))

    def resolve(self, q):
        self.index()
        q = (q or '').strip()
        if not q: return []
        hit = list(self.names.get(q, []))
        if not hit:   # old element names: kl_/dp_/hbc_ prefixes, __clXXXX clones, _rtNN / _cvB suffixes of signed view names
            base = re.sub(r'^(kl|dp|hbc|hd|ds)_', '', q)
            for k in (base, re.sub(r'__cl[0-9a-f]{8}$', '', base), re.sub(r'_(rt\w+|cv\w+|r\d\w*)$', '', base)):
                hit = list(self.names.get(k, []))
                if hit: break
        return sorted(set(hit))

    # ------------------------------------------------------------------ HTTP glue (server.py / design_dev_server.py)
    def send_json(self, h, key, fn):
        try:
            raw, gz = self._gz(key, fn)
        except KeyError:
            return h.send(404, b'{"error":"no such node"}', 'application/json')
        if 'gzip' in (h.headers.get('Accept-Encoding') or ''):
            return h.send(200, gz, 'application/json', (('Content-Encoding', 'gzip'), ('Cache-Control', 'no-cache')))
        return h.send(200, raw, 'application/json')

    def handle(self, h, path, q):
        """path after /api/design/"""
        if self.index() is None: return h.send(503, b'{"error":"design index not built yet (design_index.py)"}', 'application/json')
        if path == 'index': return self.send_json(h, 'index', self.summary)
        if path.startswith('die/'): d = path[4:]; return self.send_json(h, 'die:' + d, lambda: self.die(d))
        if path.startswith('node/'): n = path[5:]; return self.send_json(h, 'node:' + n, lambda: self.node(n))
        if path.startswith('token/'):
            k = path[6:]
            try: mt = TOKEN_MAP.stat().st_mtime
            except OSError: mt = 0
            return self.send_json(h, 'token:%s:%s' % (k, mt), lambda: self.token(k))
        if path.startswith('compose/'):   # die composition manifest (die_compose.py): plan + pinned packs + placements; EXPLORER-P1
            d = path[8:]
            f = STATE / 'die_compose' / d / 'latest.json'
            if not re.fullmatch(r'[a-z0-9_]+', d) or not f.is_file(): return h.send(404, b'{"error":"no die composition (run die_compose.py)"}', 'application/json')
            raw = f.read_bytes()
            if 'gzip' in (h.headers.get('Accept-Encoding') or ''): return h.send(200, gzip.compress(raw, 5), 'application/json', (('Content-Encoding', 'gzip'), ('Cache-Control', 'no-cache')))
            return h.send(200, raw, 'application/json', (('Cache-Control', 'no-cache'),))
        if path == 'resolve':
            names = [x for x in (q.get('q', [''])[0] or '').split(',') if x][:400]
            return h.send(200, json.dumps({n: self.resolve(n) for n in names}).encode(), 'application/json')
        return h.send(404, b'{"error":"unknown design endpoint"}', 'application/json')

    def page(self, h, rel):
        try:
            p = (PAGE_DIR / (rel or 'index.html')).resolve()
            ok = p.is_relative_to(PAGE_DIR.resolve()) and p.is_file() and p.suffix in TYPES
        except (OSError, ValueError):
            ok = False
        if not ok: return h.send(404, b'not found', 'text/plain')
        return h.send(200, p.read_bytes(), TYPES[p.suffix], (('Cache-Control', 'no-cache'),))
