"""Shared helpers for the Explorer UI tests (no fixtures here: see conftest.py)."""
import hashlib, json, os, pathlib, re, urllib.request, urllib.error

BASE = os.environ.get('EXPLORER_URL', 'http://127.0.0.1:8770').rstrip('/')
HERE = pathlib.Path(__file__).resolve().parent
SHOTS = pathlib.Path(os.environ.get('EXPLORER_SHOTS', str(HERE / '_shots')))
SRC = pathlib.Path(os.environ.get('EXPLORER_SRC', str(HERE.parent)))     # tools/explorer (server.py, web/)
VIEWS = ['overview', 'plan', 'layout', 'element', 'dataflow', 'token', 'closure']
ALL_DIES = ['s81', 's81_head', 'qwen_compute', 'qwen_kvsys', 'hbm']
DIES = ['s81', 'hbm', 'qwen_kvsys']          # the dies the per-view tests run on
SIGNED_TYPE = 's81.t.slice_station__t38'     # signed, placed once as instance S_INST
S_INST = 's_0S_x05'
S_INST_CAM = (8800.0, 9420.0, 3.6)
ROUTED_TYPE = 's81.t.slice_station__t14'     # signed, routed pack with timing paths + clock
SMALL_CORE = 's81.c.dsfd_qbank_S'
FAILED_TYPE = 's81.t.col_h10_r0_p4__t1'      # failed, no pack of its own, hard cores at plan placement
BUILDING_TYPE = 's81.t.iqf__t1'


# ------------------------------------------------------------------------------------------------ HTTP (no browser)
def http(path, headers=None, method='GET'):
    """-> (status, headers(dict, lower-case keys), body bytes); never raises on HTTP errors"""
    req = urllib.request.Request(BASE + path, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None


def http_noredirect(path, headers=None):
    op = urllib.request.build_opener(_NoRedirect)
    try:
        with op.open(urllib.request.Request(BASE + path, headers=headers or {}), timeout=60) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()


_cache = {}


def api(path):
    """JSON of an /api/v1 GET (cached per process); raises when not 200"""
    if path not in _cache:
        st, _, b = http('/api/v1/' + path.lstrip('/'))
        if st != 200: raise RuntimeError('GET /api/v1/%s -> %s %s' % (path, st, b[:200]))
        _cache[path] = json.loads(b)
    return _cache[path]


def closure_rows(die): return api('closure/' + die)['rows']


def pick_node(die, level='type', state='signed', pack=True, prefer=None):
    """a node id of the die from the closure table (rows have pack / state / level); None when there is none"""
    rows = [r for r in closure_rows(die) if r['level'] == level and r['state'] == state and bool(r['pack']) == pack]
    if prefer:
        for p in prefer:
            if any(r['id'] == p for r in rows): return p
    return rows[0]['id'] if rows else None


def pick_instance(die):
    """(compose instance row, pack row) of a signed, drawn placement of the die (the largest of the first few), or (None, None)"""
    m = api('compose/' + die)
    best = None
    for r in m['instances']:
        p = m['packs'].get(r.get('pack')) if r.get('pack') else None
        if r.get('ok') and p and p.get('state') == 'signed' and r.get('state') == 'signed':
            if best is None or r['w'] * r['h'] > best[0]['w'] * best[0]['h']: best = (r, p)
    return best or (None, None)


# ------------------------------------------------------------------------------------------------ page helpers
def url(hash_=''):
    return BASE + '/' + (hash_ if hash_.startswith('#') or not hash_ else '#/' + hash_)


_SETTLED = """(view) => {
  if (document.querySelector('#boot') || !document.querySelector('.app') || !window.otx || !otx.store) return false;
  if (view && otx.store.get().view !== view) return false;
  const st = document.querySelector('[data-testid=stage]'); if (!st) return false;
  if (st.querySelector('.busy')) return false;
  const scope = document.querySelector('[data-testid=view-scope]');
  const empty = [...st.querySelectorAll('.empty,[data-testid=element-picker]')].some((e) => e.offsetParent !== null);
  return !!((scope && scope.textContent.trim()) || empty);
}"""

_ENGINE_IDLE = """() => !!(window.otx && otx.eng && otx.eng.pending && otx.eng.pending.size === 0 && ['plan', 'raster', 'geometry'].includes(otx.eng.mode))"""


def wait_settled(page, view=None, timeout=90000):
    page.wait_for_function(_SETTLED, arg=view, timeout=timeout)


def wait_engine(page, timeout=120000):
    """the layout engine of the mounted Layout / Element view is idle (nothing pending, mode known)"""
    page.wait_for_function(_ENGINE_IDLE, timeout=timeout)


def goto(page, hash_='#/overview', engine=False, timeout=90000):
    """open a hash route, wait for the shell and for the view to settle; engine=True also waits for the layout engine"""
    page.goto(url(hash_))
    page.wait_for_selector('.app', timeout=timeout)
    m = re.match(r'#?/?([a-z]+)', hash_ or '')
    view = m.group(1) if m and m.group(1) in VIEWS else None
    wait_settled(page, view, timeout)
    if engine: wait_engine(page, timeout)


def nav_hash(page, hash_):
    """in-page navigation (no reload) to a hash route"""
    page.evaluate('(h) => { location.hash = h; }', hash_)


def store(page): return page.evaluate('() => { const s = otx.store.get(); return JSON.parse(JSON.stringify(s)); }')


def eng(page, expr):
    """evaluate an expression on otx.eng, e.g. eng(page, 'e.mode')"""
    return page.evaluate('() => { const e = otx.eng; return (%s); }' % expr)


def shot(page, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    p = SHOTS / (re.sub(r'[^A-Za-z0-9_.-]+', '_', name) + '.png')
    page.screenshot(path=str(p))
    return p


def md5(b): return hashlib.md5(b).hexdigest()


def canvas_signature(page, selector):
    """hash of a 2D canvas' pixels plus the number of distinct colours sampled on a 48x48 grid (None when there is no such canvas)"""
    return page.evaluate("""(sel) => { const c = document.querySelector(sel); if (!c) return null; const g = c.getContext('2d'); const w = c.width, h = c.height; if (!w || !h) return {hash: '0', colours: 0, w, h};
      const d = g.getImageData(0, 0, w, h).data; let hs = 2166136261; const seen = new Set();
      for (let i = 0; i < d.length; i += 4) { hs = Math.imul(hs ^ (d[i] | d[i + 1] << 8 | d[i + 2] << 16), 16777619) >>> 0; }
      for (let y = 0; y < 48; y++) for (let x = 0; x < 48; x++) { const o = ((Math.floor(y * h / 48)) * w + Math.floor(x * w / 48)) * 4; seen.add(d[o] + ',' + d[o + 1] + ',' + d[o + 2]); }
      return {hash: String(hs), colours: seen.size, w, h}; }""", selector)


def snap_state(page):
    """everything a control may legitimately change, as one string: app DOM minus canvases, form state, store, localStorage, engine switches, theme"""
    return page.evaluate("""() => {
      const app = document.querySelector('.app'); if (!app) return 'noapp';
      const c = app.cloneNode(true); c.querySelectorAll('canvas').forEach((x) => x.remove());
      const form = [...document.querySelectorAll('input,select')].map((i) => i.type + ':' + (i.type === 'checkbox' ? i.checked : i.value)).join('|');
      let ls = ''; try { ls = JSON.stringify(Object.entries(localStorage).sort()); } catch (e) {}
      const e = window.otx && otx.eng; let es = '';
      if (e && e.L) { try { es = JSON.stringify([e.L.map((l) => [l.name, l.vis, l.op]), e.kindVis, e.show, e.palette, e.rulerMode, e.items && e.items.length]); } catch (x) {} }
      return [c.outerHTML.length, c.outerHTML, form, ls, es, location.href, JSON.stringify(otx.store.get()), document.documentElement.dataset.theme || '',
        document.querySelectorAll('[data-testid=popover],.toast').length, !!document.fullscreenElement, app.dataset.focus].join('\\n#\\n'); }""")
