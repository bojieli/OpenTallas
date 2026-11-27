#!/usr/bin/env python3
"""OpenTallas Explorer server: the static app (web/) and the /api/v1 contract (tools/explorer/DESIGN.md section 7).

    python3 -I server.py [--port 8770] [--bind 127.0.0.1]

A thin read-only adapter over the data engines in tools/fleet_viz (design_service / design_index, layout_service /
layout_store, die_compose, coverage) and the token / data-flow records.  Environment (same file as the old service,
explorer2.env): FLEET_VIZ_STATE, FLEET_VIZ_REPO, LV_STORE, DESIGN_INDEX, TOKEN_DESIGN_MAP; optional EXPLORER_STATE (own
cache dir for composition manifests), DATAFLOW_DATA, TOKEN_DATA.  No pollers, no ssh, standard library + brotli.
"""
import argparse, gzip, hashlib, json, os, pathlib, re, subprocess, sys, threading, time
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

HERE = pathlib.Path(__file__).resolve().parent
FV = HERE.parent / 'fleet_viz'
sys.path.insert(0, str(FV))
import design_service, layout_service, coverage, die_compose   # noqa: E402  (the engines)
import any_plan_records as APR, design_index   # noqa: E402  (EXPLORER-STORE-R1: signed records of every plan)
sys.path.insert(0, str(HERE))
import refresh_data   # noqa: E402

WEB = HERE / 'web'
ENGINE = FV / 'explorer' / 'element'            # lv_worker.js, lv_decode.js, vendor/deck.gl (loaded as-is)
STATE = design_service.STATE
OWN = pathlib.Path(os.environ.get('EXPLORER_STATE', STATE / 'explorer_v1'))
CENSUS = OWN / 'signoff_census.json'
DATAFLOW = pathlib.Path(os.environ.get('DATAFLOW_DATA', FV / 'explorer' / 'dataflow' / 'data'))
TOKEN = pathlib.Path(os.environ.get('TOKEN_DATA', FV / 'explorer' / 'token' / 'data'))
REPO = os.environ.get('FLEET_VIZ_REPO', str(HERE.parents[1]))
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
         '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
         '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.map': 'application/json'}
STALE_S = {'design_index': 3 * 3600, 'plan_now': 3 * 3600, 'compose': 3 * 3600, 'token_map': 26 * 3600,
           'token': 7 * 86400, 'dataflow': None, 'coverage': 7 * 86400, 'store': None, 'fleet': 120, 'signed_audit': None, 'count': 6 * 3600, 'signoff_census': 6 * 3600, 'archive_index': None}
LEGACY = {'/explorer': 'plan', '/explorer/': 'plan', '/explorer/design': 'plan', '/explorer/design/': 'plan',
          '/explorer/design/diemap.html': 'layout', '/explorer/element/': 'element', '/explorer/element': 'element',
          '/explorer/dataflow/': 'dataflow', '/explorer/dataflow': 'dataflow', '/explorer/token/': 'token', '/explorer/token': 'token',
          '/explorer/coverage/': 'closure', '/explorer/coverage': 'closure'}


LEGACY_WORDS = [('element', 'element'), ('diemap', 'layout'), ('layout', 'layout'), ('dataflow', 'dataflow'), ('token', 'token'), ('coverage', 'closure'), ('release', 'closure'),
                ('closure', 'closure'), ('status', 'closure'), ('design', 'plan'), ('plan', 'plan'), ('explorer', 'plan'), ('fleet', 'fleet'), ('overview', 'overview')]


def legacy_target(path, q):
    """an old bookmark path (/release, /element?name=X, /explorer/element/X, /dataflow, /token, ...) -> the new app URL, or None
    for a path that looks like a missing asset.  The browser keeps the #fragment across the redirect; app.js rewrites it."""
    segs = [x for x in path.split('/') if x]
    last = segs[-1] if segs else ''
    if '.' in last and not last.endswith(('.html', '.htm')): return None
    words = [x.lower().replace('.html', '').replace('.htm', '') for x in segs]
    view = next((v for w, v in LEGACY_WORDS if w in words), 'overview')
    name = next((q[k][0] for k in ('name', 'element', 'el', 'node', 'n', 'q', 'id', 'design', 'die') if q.get(k) and q[k][0]), None)
    if not name and 'element' in words and words.index('element') < len(segs) - 1: name = segs[-1]
    from urllib.parse import quote
    return '/?legacy=' + view + ('&q=' + quote(name, safe='') if name else '')


class _NoElements:
    def snapshot(self, legacy=False): return {'rows': []}


DS = design_service.Service(log=lambda *a: None)
LS = layout_service.Service(log=lambda *a: None)
COV = coverage.Coverage(REPO, _NoElements(), TOKEN.parent, log=lambda *a: None)
COMPOSE_V = 4
LOCK = threading.RLock()
CACHE = {}          # key -> (stamp, raw, gz)


def _sha():
    try: return subprocess.run(['git', '-C', str(HERE), 'rev-parse', '--short=10', 'HEAD'], capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception: return None


SERVICE = dict(sha=_sha(), started=time.time())


_GIT_DATES = {}


def git_date(path):
    """commit time (epoch) of the last change of a repo file: the honest date of committed data records"""
    path = pathlib.Path(path); key = str(path)
    if key not in _GIT_DATES:
        try:
            out = subprocess.run(['git', '-C', str(path.parent), 'log', '-1', '--format=%ct', '--', path.name], capture_output=True, text=True, timeout=20).stdout.strip()
            _GIT_DATES[key] = float(out) if out else None
        except Exception:
            _GIT_DATES[key] = None
    return _GIT_DATES[key]


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
    pp = pathlib.Path(path or ''); stem = pp.name.replace('.json.gz', '').replace('.json', '')
    m = re.search(r'([0-9a-f]{12})$', stem)
    if m: return m.group(1)
    return pp.parent.name if stem in ('die_plan', 'source_plan', 'plan') and pp.parent.name else stem


def plan_ref(p):
    w = p.get('wave')
    return dict(wave=w, basis='kit wave plan, as counted' if w else 'plan of record on main', path=p.get('path'), sha=plan_sha(p.get('path')), commit=(p.get('commit') or '')[:10] or None, date=p.get('date'), subject=p.get('subject'))


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
        if m.get('index_generated') == idx.get('generated') and m.get('v') == COMPOSE_V: return m
    except (OSError, ValueError):
        pass
    with LOCK:
        m = die_compose.build(die, idx)
        m['plan']['sha'] = plan_sha(m['plan']['path']); m['v'] = COMPOSE_V
        # every hard core of the die that has a pack, not only the cores of types that have one: the viewer draws the cores of
        # an unsigned type at their PLAN placement (labelled so), which is most of the routed metal on S81 / KV / HBM today
        extra = 0
        for nid, n in idx['nodes'].items():
            if n['die'] != die or n['level'] != 'core' or nid in m['packs'] or not (n.get('layout') or {}).get('store'): continue
            p = die_compose.pack_info(nid)
            if p and p['die'][:2] == [0, 0]:
                m['packs'][nid] = dict({k: v for k, v in p.items() if k != 'macros'}, level='core', state=n['status']['state'], cores=[]); extra += 1
        # (1) block identity: a type without a pack under its own name takes the pack of a type with the SAME block sha (the kit
        #     identity the wave and the count's dedup credit use), so a renamed master keeps its routed view.
        # (2) a pack whose outline differs from the plan slot (the plan grew the slot after the sign-off) is still drawn, anchored
        #     at the slot's lower-left, and flagged; hiding a signed layout because the slot changed would be wrong.
        pn = _json_file(STATE / 'plan_now.json') or {}
        sha_of = {e['element']: (e.get('kw') or {}).get('block_sha') for e in pn.get('elements') or [] if e.get('die') == die and e.get('kind') == 'type'}
        by_sha = {}
        for nid, n in idx['nodes'].items():
            if n['die'] == die and n['level'] == 'type' and (n.get('layout') or {}).get('store') and sha_of.get(n['name']): by_sha.setdefault(sha_of[n['name']], nid)
        ident = resized = 0
        for r in m['instances']:
            if r['ok'] or r['orient'] not in die_compose.SIGN: continue
            src = r['node']; via = None
            if r.get('why') == 'no pack':
                src = by_sha.get(sha_of.get(src.split('.t.', 1)[-1])); via = 'block'
                if not src or src == r['node']: continue
            p = die_compose.pack_info(src)
            if not p or p['die'][:2] != [0, 0]: continue
            pw, ph = p['die'][2], p['die'][3]
            if src not in m['packs']:
                m['packs'][src] = dict({k: v for k, v in p.items() if k != 'macros'}, level='type', state=idx['nodes'][src]['status']['state'],
                                       cores=[dict(core=('%s.c.%s' % (die, q['master'])) if ('%s.c.%s' % (die, q['master'])) in m['packs'] else None, name=q['name'], master=q['master'], origin=q['origin'], orient=q['orient'], bbox=q['bbox']) for q in p['macros']])
            r.update(ok=True, pack=src, pw=pw, ph=ph)
            if via: r['by_identity'] = dict(block_sha=sha_of.get(r['node'].split('.t.', 1)[-1]), pack_of=src); ident += 1
            if [pw, ph] != [r['w'], r['h']]: r['outline_differs'] = dict(pack=[pw, ph], slot=[r['w'], r['h']]); resized += 1
            r.pop('why', None)
        S = m['summary']; S['by_identity'] = ident; S['outline_differs'] = resized
        S['with_pack'] = sum(1 for r in m['instances'] if r['ok']); S['signed_with_pack'] = sum(1 for r in m['instances'] if r['ok'] and r['state'] == 'signed')
        S['unique_block_shas'] = len(set(v for v in sha_of.values() if v)); S['types_with_block_sha'] = sum(1 for v in sha_of.values() if v)
        m['summary']['core_packs_all'] = sum(1 for p in m['packs'].values() if p['level'] == 'core')
        m['summary']['pack_bytes'] = sum(p['bytes'] or 0 for p in m['packs'].values())
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix('.tmp'); tmp.write_text(json.dumps(m, separators=(',', ':'))); os.replace(tmp, f)
    return m


def _json_file(p):
    try: return json.loads(pathlib.Path(p).read_text())
    except (OSError, ValueError): return None


_CENSUS = (None, None, {})


def signoff_census():
    global _CENSUS
    stamp = _mtime(CENSUS)
    if stamp != _CENSUS[0]:
        data = _json_file(CENSUS) or {}
        if data.get('schema') != 'opentallas.signoff_census.v1':
            data = None
        names = {}
        for die, entry in (data or {}).get('dies', {}).items():
            for bucket in ('current', 'deferred', 'retired'):
                for item in entry.get(bucket, []):
                    aliases = (item['name'],) if bucket == 'retired' else (item['name'], item.get('module'))
                    for level in census_levels(item):
                        for name in aliases:
                            if name:
                                names.setdefault((die, level, name), bucket)
        _CENSUS = (stamp, data, names)
    return _CENSUS[1]


def census_levels(item):
    if 'level' in item:
        return [item['level']]
    return ['core' if k in ('c', 'core') else 'type' for k in item['kinds']]


def signoff_basis(n, *, include_retired=False):
    signoff_census()
    die, level = n.get('die'), n.get('level')
    matches = [_CENSUS[2].get((die, level, name))
               for name in (n.get('name'), (n.get('plan') or {}).get('module')) if name]
    if 'current' in matches:
        return 'current'
    if 'deferred' in matches:
        return 'deferred'
    # The index can lag the census plan. Credit an exact visible name at the
    # same level, but don't transfer retired sign-offs through module aliases.
    if include_retired and _CENSUS[2].get((die, level, n.get('name'))) == 'retired':
        return 'retired'
    return None


def signoff_display_state(n, basis):
    state = (n.get('status') or {}).get('state')
    if basis:
        return 'signed'
    if state == 'signed' and signoff_census():
        return 'uncredited'
    return state


def signoff_display_node(n):
    basis = signoff_basis(n, include_retired=True)
    return dict(n, signoff_basis=basis, signoff_display_state=signoff_display_state(n, basis))


def any_plan_counts(nodes, states):
    counts = {level: dict.fromkeys([*states, 'uncredited'], 0) for level in ('type', 'core')}
    for n in nodes:
        c = counts[n['level']]
        state = n['signoff_display_state'] or 'not built'
        c[state] = c.get(state, 0) + 1
    return counts


def datasets():
    now = time.time(); idx = DS.index(); out = []
    census = signoff_census()

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
    rc = ((_json_file(pn) or {}).get('sources') or {}).get('release_cache_mtime')
    add('count', 'Sign-off count cache (release_tree count, COUNT-DIRECT, AUTO-RESIGN, dedup credits)', rc, 'intel2 release_tree_plan.py; the index is rebuilt within about two minutes of every count', ['overview', 'closure', 'plan'])
    add('store', 'Routed layout packs (cut at sign-off, immutable)', _mtime(layout_service.LS.STORE / 'cuts.json') or _mtime(layout_service.LS.STORE / 'elements'), 'layout store (lv_extract + lv_tile, lv_verify IDENTICAL)', ['layout', 'element'],
        note='packs do not go stale: each is the geometry of one closure')
    cm = [_json_file(p) for p in sorted((OWN / 'compose').glob('*.json'))] if (OWN / 'compose').is_dir() else []
    cm = [m for m in cm if m]
    add('compose', 'Die composition manifests (placements + packs)', min((_iso(m.get('made')) or 0) for m in cm) if cm else (idx and idx.get('generated')), 'die_compose.py', ['layout'],
        note='%d of %d dies composed' % (len(cm), len(idx['dies']) if idx else 0) if idx else None)
    ti = _json_file(TOKEN / 'index.json')
    tgen = None; tnote = None
    if ti:
        gens = [g for g in (git_date(TOKEN / r['file']) for r in ti.get('designs') or [] if isinstance(r, dict) and r.get('file')) if g]
        tgen = min(gens) if gens else None
        tnote = 'token records are exported from the simulator at a repo head; they describe the die revision named in each record'
    add('token', 'Token path records (simulator export)', tgen, 'tools/token_path_export.py', ['token'], note=tnote, missing=ti is None)
    tm = _json_file(design_service.TOKEN_MAP)
    add('signoff_census', 'Sign-off census', census and _iso(census.get('generated')), 'count_hourly.py', ['overview', 'closure'], missing=census is None)
    add('token_map', 'Token class to design node map', tm and _iso(tm.get('generated')), 'token_design_map.py', ['token'], missing=tm is None)
    dataflow_refresh()
    own = (_json_file(DF_OWN / 'index.json') or {}).get('records') or []
    gens = [g for g in (_iso(r.get('generated')) for r in own) if g]
    add('dataflow', 'Data-flow link records of the plans of record', min(gens) if gens else None, 'tools/explorer/refresh_data.py (plan_now.plan_geometry + dataflow_links.py), rebuilt when a plan changes', ['dataflow'],
        note='%d of %d dies have a current record; older revisions stay selectable and are labelled' % (len(own), len(idx['dies']) if idx else 0), missing=not own)
    f = _FLEET.get('fleet')
    try:
        fleet_get('fleet'); f = _FLEET.get('fleet'); ferr = None
    except ApiError as e: ferr = e.detail
    add('fleet', 'Fleet hosts and jobs (fleet-viz collectors, 5 s poll)', f[2] if f and not ferr else None, 'tools/fleet_viz server.py pollers via ' + FLEET_API, ['fleet'], note=ferr, missing=bool(ferr))
    ai = archive_index()['meta']
    add('archive_index', 'Signed-layout archive index (rtx-pro signed-export-1114 + closed_archive)', ai.get('generated'), 'tools/explorer/tools/archive_index.py on the archive host', ['element', 'closure'], note='%s export entries, %s closed rows' % (ai.get('export'), ai.get('closed')) if ai else None)
    au = signed_audit()
    add('signed_audit', 'Signed-layout archive table (SIGNED-DB-AUDIT)', au.get('mtime'), AUDIT_SRC, ['element'], note=au.get('error') or ('%d rows' % au.get('n', 0)), missing=False)
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
    s = DS.summary(); idx = index(); census = signoff_census()
    by_die, totals = defaultdict(Counter), Counter()
    signed_packs = defaultdict(Counter)
    # Use the same records as /api/v1/records, including historical entries.
    for record in records().values():
        if census:
            by_die[record['die']][record['level']] += 1
            totals[record['level']] += 1
        if record.get('pack'):
            signed_packs[record['die']][record['level']] += 1

    def with_levels(summary, counts):
        return dict(summary, by_level=dict(type=counts['type'], core=counts['core'])) if summary else None

    s['signoff_census'] = with_levels(census['summary'], totals) if census else None
    for d in s['dies']:
        p = idx['nodes'][d['id']]['plan']
        d['plan'] = plan_ref(p); d['period_ps'] = p.get('period_ps'); d['reach_um'] = p.get('reach_um')
        nodes = {nid: signoff_display_node(n) for nid, n in idx['nodes'].items()
                 if n['die'] == d['id'] and n['level'] != 'die'}
        ns = nodes.values()
        d['counts_any_plan'] = any_plan_counts(ns, idx['states'])
        d['packs'] = dict(type=sum(1 for n in ns if n['level'] == 'type' and (n.get('layout') or {}).get('store')),
                          core=sum(1 for n in ns if n['level'] == 'core' and (n.get('layout') or {}).get('store')))
        # a pack of a design that is not signed off is a view of a build in progress (wave run, any stage): shown, never counted
        d['packs_unsigned'] = dict(type=sum(1 for n in ns if n['level'] == 'type' and (n.get('layout') or {}).get('store') and (n.get('status') or {}).get('state') not in ('signed', 'pending archive')),
                                   core=sum(1 for n in ns if n['level'] == 'core' and (n.get('layout') or {}).get('store') and (n.get('status') or {}).get('state') not in ('signed', 'pending archive')))
        unsigned_packs = Counter(n['level'] for n in ns if (n.get('layout') or {}).get('store')
                                 and n['signoff_display_state'] != 'signed')
        d['packs_signed_any_plan'] = {level: signed_packs[d['id']][level] for level in ('type', 'core')}
        d['packs_unsigned_any_plan'] = {level: unsigned_packs[level] for level in ('type', 'core')}
        d['cores'] = sum(1 for n in ns if n['level'] == 'core')
        summary = ((census or {}).get('dies', {}).get(d['id']) or {}).get('summary')
        d['any_plan'] = with_levels(summary, by_die[d['id']])
        st, st_any, area, area_any = Counter(), Counter(), Counter(), Counter()
        for q in p['partitions']:
            n = nodes.get(q[1]) or {}
            raw = (n.get('status') or {}).get('state', 'not built')
            display = n.get('signoff_display_state') or raw
            size = q[4] * q[5]
            st[raw] += 1
            st_any[display] += 1
            area[raw] += size
            area_any[display] += size
        d['instances'] = dict(total=len(p['partitions']), by_state=st, by_state_any_plan=st_any)
        d['area_um2'] = dict(die=p['outline'][0] * p['outline'][1], by_state=area, by_state_any_plan=area_any)
    return s


def die(d):
    idx = index()
    if d not in idx['dies']: raise ApiError(404, 'no such die', d)
    r = DS.die(d); r['plan'] = plan_ref(r['die']['plan'])
    r['nodes'] = {nid: signoff_display_node(n) for nid, n in r['nodes'].items()}
    r['die'] = dict(r['die'], counts_any_plan=any_plan_counts(r['nodes'].values(), r['states']))
    return r


def history(nid):
    ix = _json_file(layout_service.LS.STORE / 'elements' / nid / 'index.json')
    if not ix: return None
    return dict(latest=ix.get('latest'), history=ix.get('history') or [], updated=ix.get('updated'))


def node(nid):
    idx = index()
    if nid not in idx['nodes']: return record_node(nid)
    r = DS.node(nid); n = r['node']
    display = r['node'] = signoff_display_node(n)
    r['signoff_basis'] = display['signoff_basis']
    r['signoff_display_state'] = display['signoff_display_state']
    r['children'] = {cid: signoff_display_node(c) for cid, c in r['children'].items()}
    r['record'] = records().get(nid)   # the any-plan record of this node (plan label, archive rows), if any
    r['plan'] = plan_ref(idx['nodes'][n['die']]['plan'])
    r['packs'] = history(nid)
    r['archive'] = audit_rows(n)   # SIGNED-DB-AUDIT: where the signed routed database lives now
    r['sources'] = db_sources(n)
    if n['level'] == 'core':   # where the core sits: every (type, core instance) that places it
        uses = []
        for u in (n.get('plan') or {}).get('used_by') or []:
            t = idx['nodes'].get(u)
            if t: uses.append(dict(type=u, name=t['name'], state=t['status']['state'], signoff_display_state=signoff_display_node(t)['signoff_display_state'], count=sum(1 for h in t['plan']['hard_cores'] if h[1] == nid),
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
        basis = signoff_basis(n, include_retired=True)
        rows.append(dict(id=n['id'], name=n['name'], level=n['level'], state=st.get('state'), signoff_basis=basis,
                         display_state=signoff_display_state(n, basis),
                         label=st.get('label'), basis=st.get('basis'), cls=st.get('cls'), stage=st.get('stage'),
                         attempt=st.get('attempt'), reason=st.get('reason'), tt_wns=m.get('tt_wns'), ff_wns=m.get('ff_wns'),
                         drc=m.get('drt_drc') if m.get('drt_drc') is not None else m.get('drc'), grt_overflow=m.get('grt_overflow'), lec=m.get('lec'),
                         cells=m.get('cells'), verdict=m.get('verdict'), instances=p.get('instances') if n['level'] == 'type' else p.get('placements'),
                         area_um2=(p['outline'][0] * p['outline'][1]) if p.get('outline') else None, cores=len(n.get('children') or []) if n['level'] == 'type' else None,
                         pack=bool(s), pack_verify=s.get('verify'), pack_shapes=s.get('shapes'), pack_made=s.get('made'), layout_stage=lay.get('stage'),
                         layout_source=lay.get('source'), db_cls=db_sources(n)['cls'], db_host=((db_sources(n)['resolved'] or {}).get('where') or (db_sources(n)['recorded'] or {}).get('host')), vis=v.get('verdict'), vis_cls=v.get('cls'), vis_cause=v.get('cause'), hard=bool(p.get('hard'))))
    dn = idx['nodes'][d]
    sup = [dict(id=r['id'], name=r['name'], level=r['level'], plan=r['plan'], plan_label=r['plan_label'], tt_wns=None, ff_wns=None, drc=None, pack=bool(r['pack']), pack_verify=(r['pack'] or {}).get('verify'),
                archived=r['archive']['agi'] or r['archive']['rtx'], index_status=r['archive']['status']) for r in records().values() if r['die'] == d and r['superseded']]
    census = (signoff_census() or {}).get('dies', {}).get(d)
    if census:
        ids = {r['id']: r['signoff_basis'] for r in rows}
        for r in records().values():
            if r['die'] != d or r['id'] in ids or (ids.get(r['node']) == r['signoff_basis'] == 'current'):
                continue
            rows.append(dict(id=r['id'], name=r['name'], level=r['level'], state=None, signoff_basis=r['signoff_basis'],
                             label=r['plan_label'], tt_wns=None, ff_wns=None, drc=None, pack=bool(r['pack']), pack_verify=(r['pack'] or {}).get('verify'),
                             db_cls='archive' if r['archive']['agi'] or r['archive']['rtx'] else None))
    return dict(die=d, label=dn['label'], plan=plan_ref(dn['plan']), states=idx['states'], counts=dn['counts'], generated=idx['generated'], rows=rows,
                signoff_census=census and census['summary'], superseded_records=sorted(sup, key=lambda x: x['id']))


def elements_compat():
    """/api/elements for scripts that used the old fleet-viz endpoint: one row per type and core of the current plans, with the
    status of the design index (count cache -> plan_now -> design_index, rebuilt whenever the count runs)"""
    idx = index(); pn = _json_file(STATE / 'plan_now.json') or {}
    rows = []
    for n in idx['nodes'].values():
        if n['level'] == 'die': continue
        st = n.get('status') or {}
        rows.append(dict(element=n['name'], node=n['id'], die=n['die'], kind=n['level'], target=idx['nodes'][n['die']].get('target'), category=st.get('label'), state=st.get('state'),
                         cls=st.get('cls'), stage=st.get('stage'), attempt=st.get('attempt'), reason=st.get('reason'), m=st.get('metrics') or {}, layout=bool((n.get('layout') or {}).get('store'))))
    return dict(schema='opentallas.explorer.elements_compat.v1', t=idx.get('generated'), generated=idx.get('generated'), cats=pn.get('cats'), rows=rows,
                source=dict(design_index=idx.get('generated'), plan_now=pn.get('generated'), count_cache_mtime=((pn.get('sources') or {}).get('release_cache_mtime'))),
                note='status = count cache (release_tree count incl. COUNT-DIRECT, AUTO-RESIGN and dedup credits) -> plan_now -> design index; use /api/v1/closure/<die> for the full rows')


def search(q, d=None, limit=40):
    idx = index(); q = (q or '').strip().lower()
    if not q: return dict(q=q, results=[])
    terms = q.split(); out = []
    for nid, n in idx['nodes'].items():
        if d and n['die'] != d and len(out) > limit * 4: continue
        name = (n.get('name') or n.get('label') or nid).lower(); hay = nid.lower() + ' ' + name + ' ' + str((n.get('plan') or {}).get('module') or '').lower()
        if not all(t in hay for t in terms): continue
        score = (0 if name == q or nid.lower() == q else 1 if name.startswith(q) else 2) + (0 if not d or n['die'] == d else 3) + {'die': 0, 'type': 0.1, 'core': 0.2}[n['level']]
        out.append((score, len(name), dict(kind=n['level'], id=nid, name=n.get('name') or n.get('label'), die=n['die'], state=signoff_display_state(n, signoff_basis(n)),
                                           pack=bool((n.get('layout') or {}).get('store')))))
    for dd in idx['dies']:
        if dd not in idx['nodes']: continue
        for p in idx['nodes'][dd]['plan']['partitions']:
            nm = p[0].lower()
            if not all(t in nm for t in terms): continue
            score = (0 if nm == q else 1 if nm.startswith(q) else 2) + (0 if not d or dd == d else 3) + 0.3
            tn = idx['nodes'].get(p[1]) or {}
            out.append((score, len(nm), dict(kind='instance', id=p[1], inst=p[0], name=p[0], die=dd, of=tn.get('name'), state=signoff_display_state(tn, signoff_basis(tn)),
                                             pack=bool((tn.get('layout') or {}).get('store')))))
    for rid, r in records().items():   # superseded records (no current-plan node): listed with their plan label
        if rid in idx['nodes']: continue
        hay = rid.lower() + ' ' + r['name'].lower()
        if not all(t in hay for t in terms): continue
        nm = r['name'].lower()
        score = (0 if nm == q else 1 if nm.startswith(q) else 2) + (0 if not d or r['die'] == d else 3) + 0.5
        out.append((score, len(nm), dict(kind=r['level'], id=rid, name=r['name'], die=r['die'], state='signed', superseded=r['superseded'], plan_label=r['plan_label'], tt_wns=None, ff_wns=None, drc=None, pack=bool(r['pack']))))
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
    dates = {r['design']: git_date(TOKEN / r['file']) for r in ti.get('designs') or [] if isinstance(r, dict) and r.get('file')}
    return dict(index=ti, dates=dates, map_generated=_iso(tm.get('generated')), mapped=sorted((tm.get('designs') or {}).keys()))


def token_map(design):
    o = DS.token(design)
    if o.get('error'): raise ApiError(404, 'no token map for this design', o['error'])
    return o


DF_OWN = OWN / 'dataflow'      # plan_<die> link records of the current plans of record (refresh_data.py)
_DF = dict(stamp=None, thread=None, result=None)


def dataflow_refresh():
    """rebuild the plan_<die> link records in the background when the design index changed"""
    idx = DS.index()
    if idx is None or _DF['stamp'] == idx.get('generated') or (_DF['thread'] and _DF['thread'].is_alive()): return
    _DF['stamp'] = idx.get('generated')

    def run():
        try: _DF['result'] = refresh_data.refresh(idx, DF_OWN)
        except Exception as e: _DF['result'] = dict(error='%s: %s' % (type(e).__name__, e))
    _DF['thread'] = threading.Thread(target=run, daemon=True); _DF['thread'].start()


def dataflow_index():
    dataflow_refresh()
    own = (_json_file(DF_OWN / 'index.json') or {}).get('records') or []
    old = (_json_file(DATAFLOW / 'index.json') or {}).get('records') or []
    have = {r['id'] for r in own}
    for r in own: r['current'] = True
    recs = own + [dict(r, role='previous' if r.get('role') == 'canonical' else r.get('role'), current=False) for r in old if r['id'] not in have]
    if not recs: raise ApiError(404, 'no data-flow records', str(DATAFLOW))
    return dict(schema='opentallas.dataflow.links_index.v1', records=recs, refresh=_DF['result'], building=bool(_DF['thread'] and _DF['thread'].is_alive()))


# ---------------------------------------------------------------------------------------------- signed-layout archives
# Owner rule: signed records live on the archive host (rtx-pro: signed-export-1114 and closed_archive) and on AGIdock /archive,
# never on the fleet.  The explorer resolves every design to its archive copy and shows that path; the build path recorded at
# sign-off (often a fleet host, some of them gone or off limits) is kept only as provenance.  Nothing here opens a database.
ARCHIVE_INDEX = pathlib.Path(os.environ.get('ARCHIVE_INDEX', OWN / 'archive_index.json'))   # tools/archive_index.py, run on the archive host
OFF_LIMITS = set(os.environ.get('OFF_LIMITS_HOSTS', 'epyc4,epyc5,epyc6').split(','))
ARCHIVE_HOSTS = {'rtx-pro', 'localhost', 'agidock', 'AGIdock'}
EXPORT_DIES = dict(s81=('s81', 'DeepSeek_ROM', '_'), s81_head=('s81_head', 'DeepSeek_ROM', '_'), qwen_compute=('qwen_compute', 'Qwen_ROM', '_'), qwen_kvsys=('qwen_kvsys', 'Qwen_ROM', '_'), hbm=('hbm', 'HBM_accelerator', '_'))
_ARCH = dict(mt=None, exp={}, closed={}, meta={})


def archive_index():
    mt = _mtime(ARCHIVE_INDEX)
    if mt != _ARCH['mt']:
        d = _json_file(ARCHIVE_INDEX) or {}
        exp, closed = {}, {}
        for e in d.get('export') or []: exp.setdefault(e['name'], []).append(e)
        for c in d.get('closed') or []:
            if c.get('status') == 'archived' and c.get('name'): closed.setdefault(c['name'], []).append(c)
        # AGIdock listing of /archive/opentallas-signed-1114 (the archive of record): (die dir, name) -> has a routed database
        agi = {(e.get('die'), e.get('name')): any(str(f if isinstance(f, str) else (f or {}).get('name') or (f or [''])[0]).endswith(('.odb', '.odb.zst')) for f in (e.get('files') or [])) for e in d.get('agidock') or []}
        _ARCH.update(mt=mt, exp=exp, closed=closed, agi=agi, meta=dict(generated=d.get('generated'), host=d.get('host'), export=len(d.get('export') or []), closed=len(d.get('closed') or [])))
    return _ARCH


# ---------------------------------------------------------------------------------------------- any-plan signed records
# EXPLORER-STORE-R1 (OWNER 2026-11-22): the archive and the explorer cover ALL closures on any plan.  The index nodes are the
# current plan; every archived signed unit of an older block or a retired plan is a record (any_plan_records.py) with its plan
# label, its archive rows and its routed-layout pack (the same store, keyed <die>.<t|c>.<name>), so it is listed and viewable.
_REC = dict(key=None, recs={})


def records():
    idx = index()
    key = (idx.get('generated'), _mtime(CENSUS), _mtime(ARCHIVE_INDEX), _mtime(layout_service.LS.STORE / 'elements'), int(time.time() // 120))
    if key != _REC['key']:
        d = _json_file(ARCHIVE_INDEX) or {}
        census = signoff_census()
        exact_retired_ids = {
            '%s.%s.%s' % (die, 'c' if level == 'core' else 't', item['name'])
            for die, entry in (census or {}).get('dies', {}).items()
            for item in entry.get('retired', [])
            for level in census_levels(item)
        }
        layouts = APR.build(idx['nodes'], d.get('agidock_index_tsv'), d.get('export'), design_index.store_entry,
                            exact_retired_ids=exact_retired_ids)
        source_refs = Counter((die, item['level'], ref)
                              for die, entry in (census or {}).get('dies', {}).items()
                              for item in entry.get('current', [])
                              for ref in set(item.get('source_refs') or ()))
        source_archives = APR.source_archives(d.get('agidock_index_tsv'),
                                              {key for key, n in source_refs.items() if n == 1})
        recs = census_records(census, idx['nodes'], layouts, source_archives) if census else layouts
        _REC.update(key=key, recs=recs)
    return _REC['recs']


def census_records(census, nodes, layouts, source_archives=None):
    recs = {}
    node_names = {}
    for node in nodes.values():
        level = node['level']
        if level not in ('type', 'core'):
            continue
        for name in (node['name'], (node.get('plan') or {}).get('module')):
            if name:
                node_names.setdefault((node['die'], level, name), node['id'])
    for die, entry in census['dies'].items():
        for bucket, label in (('current', 'current'), ('deferred', 'resign'), ('retired', 'retired')):
            for item in entry.get(bucket, []):
                name = item['name']
                levels = census_levels(item)
                nid = next((node_names[die, level, name] for level in levels if (die, level, name) in node_names), None)
                level = nodes[nid]['level'] if nid else levels[0]
                raw_id = '%s.%s.%s' % (die, 'c' if level == 'core' else 't', name)
                rid = (nid or raw_id) if bucket != 'retired' else raw_id
                if rid in recs or (bucket == 'retired' and rid in nodes):
                    suffix = hashlib.sha256((bucket + ':' + item['key']).encode()).hexdigest()[:12]
                    rid += '--signoff-' + suffix
                existing = layouts.get(raw_id) or layouts.get(nid) or {}
                # A build of a current node is layout evidence only for its own plan state.
                pack = existing.get('pack') if rid in (nid, raw_id) and existing.get('superseded') == (bucket != 'current') else None
                archive = existing.get('archive') or dict(agi=False, rtx=False, status=None, units=[])
                if source_archives and not (archive['agi'] or archive['rtx']):
                    matches = {}
                    for ref in item.get('source_refs') or ():
                        match = source_archives.get((die, level, ref))
                        if match:
                            matches[match['record'], match['odb_sha256']] = match
                    if len(matches) == 1:
                        archive = next(iter(matches.values()))
                recs[rid] = dict(id=rid, die=die, name=name, level=level, node=nid, plan='current' if bucket == 'current' else 'superseded',
                                 plan_label=APR.LABEL[label], superseded=bucket != 'current', signoff_basis=bucket,
                                 census_key=item['key'], node_state=((nodes.get(nid) or {}).get('status') or {}).get('state'),
                                 archive=archive, pack=pack)
    return recs


def records_list(d=None, plan=None):
    R = records()
    rows = [r for r in R.values() if (not d or r['die'] == d) and (not plan or r['plan'] == plan)]
    rows.sort(key=lambda r: (r['die'], r['superseded'], r['id']))
    return dict(schema='opentallas.explorer.records.v1', rule='every signed-off record on any plan: current-plan sign-offs (index nodes) and archived sign-offs of superseded or retired plan blocks; '
                'id = <die>.<t|c>.<name> (re-sign suffix dropped); pack = routed-layout pack in the layout store', summary=APR.summary(R), census=(signoff_census() or {}).get('summary'), total=len(rows), records=rows)


def record_node(nid):
    """a superseded record (no node of the current plan) as a node response, so the element view opens its layout pack"""
    idx = index(); r = records().get(nid)
    if not r: raise ApiError(404, 'no such node', nid)
    dn = idx['nodes'].get(r['die']) or {}
    n = dict(id=nid, level=r['level'], die=r['die'], name=r['name'], parent=r['die'], superseded=r['superseded'], plan_label=r['plan_label'],
             status=dict(state='signed', label='signed off (%s)' % r['plan_label'], archive=r['archive']), layout=dict(stage='6_final', source='archived signed record', store=r['pack']),
             plan=dict(outline=None, hard_cores=[], buses=[], ft_slots=[], stations=[]), children=[])
    arch = [dict(where='AGIdock' if r['archive']['agi'] else 'rtx-pro', kind='opentallas-signed-1114', path=u, odb=True) for u in r['archive']['units']]
    return dict(node=n, die=dict(id=r['die'], label=dn.get('label'), outline=(dn.get('plan') or {}).get('outline'), reach_um=(dn.get('plan') or {}).get('reach_um')),
                children={}, users={}, placements=[], states=idx['states'], generated=idx['generated'], plan=plan_ref(dn['plan']) if dn.get('plan') else None,
                packs=history(nid), archive=[], record=r, signoff_basis=r.get('signoff_basis'), uses=[],
                sources=dict(recorded=None, archives=arch, resolved=arch[0] if arch else None, on_rtx_pro=r['archive']['rtx'], on_agidock=r['archive']['agi'], cls='archive' if arch else 'none'))


def host_class(h):
    h = (h or '').lower().replace('ot-', '')
    return 'none' if not h else 'archive' if h in {x.lower() for x in ARCHIVE_HOSTS} else 'off-limits' if h in OFF_LIMITS else 'fleet'


def db_sources(n):
    """where the routed database of a design is: the archive copies (resolved, preferred) and the build path recorded at sign-off"""
    lay = n.get('layout') or {}; A = archive_index(); out = dict(recorded=None, archives=[], resolved=None)
    rec = lay.get('db') or lay.get('kit')
    if rec:
        host, _, path = rec.partition(':') if ':' in rec.split('/')[0] else ('', '', rec)
        out['recorded'] = dict(host=host or None, path=path, cls=host_class(host))
    names = [x for x in dict.fromkeys([n.get('name'), (n.get('plan') or {}).get('module')]) if x]
    dies = EXPORT_DIES.get(n['die'], (n['die'], '_'))
    for nm in names:
        for e in A['exp'].get(nm, []):
            if e['die'] in dies: out['archives'].append(dict(where='rtx-pro', kind='signed-export-1114', path=e['path'] + ('/' + e['odb'] if e.get('odb') else ''), odb=bool(e.get('odb')), signoff=bool(e.get('signoff')), bytes=e.get('bytes')))
            if e['die'] in dies and A.get('agi', {}).get((e['die'], nm)): out['archives'].append(dict(where='AGIdock', kind='opentallas-signed-1114', path='/archive/opentallas-signed-1114/%s/%s/6_final.odb' % (e['die'], nm), odb=True))
    if lay.get('archive_odb'): out['archives'].append(dict(where='AGIdock', kind='archive', path=str(lay['archive_odb']), odb=True))
    for nm in names:
        for c in A['closed'].get(nm, [])[-2:]:
            here = c.get('present', True)   # REMOTE_ONLY closed-archive jobs keep only links on rtx-pro: the database itself is on AGIdock
            out['archives'].append(dict(where='rtx-pro' if here else 'AGIdock', kind='closed_archive' if here else 'closed_archive (remote only, links on rtx-pro)', path=c['path'] + ('/' + c['odb'] if c.get('odb') else ''), odb=bool(c.get('odb')), job=c.get('job'), local=here))
    for a in audit_rows(n) or []:
        pth = next((v for k, v in a.items() if 'path' in k or 'archive' in k), None)
        if pth: out['archives'].append(dict(where=a.get('host') or 'archive', kind='SIGNED-DB-AUDIT', path=pth, odb=pth.endswith(('.odb', '.odb.zst'))))
    out['resolved'] = next((a for a in out['archives'] if a['odb'] and a['where'] == 'rtx-pro'), None) or next((a for a in out['archives'] if a['odb']), None) or (out['archives'][0] if out['archives'] else None)
    out['on_rtx_pro'] = any(a['odb'] and a['where'] == 'rtx-pro' for a in out['archives']); out['on_agidock'] = any(a['odb'] and a['where'] == 'AGIdock' for a in out['archives'])
    out['cls'] = 'archive' if out['resolved'] else (out['recorded'] or {}).get('cls', 'none')
    return out


def archive_summary():
    idx = index(); A = archive_index(); rows = []
    for n in idx['nodes'].values():
        if n['level'] == 'die': continue
        st = (n.get('status') or {}).get('state'); s = db_sources(n)
        if st != 'signed' and not (n.get('layout') or {}).get('store'): continue
        rows.append(dict(id=n['id'], die=n['die'], level=n['level'], state=st, pack=bool((n.get('layout') or {}).get('store')), cls=s['cls'], recorded=s['recorded'], resolved=s['resolved'], rtx=s['on_rtx_pro'], agi=s['on_agidock']))
    signed = [r for r in rows if r['state'] == 'signed']
    def tally(R):
        out = {}
        for r in R: out[r['cls']] = out.get(r['cls'], 0) + 1
        return out
    rec_cls = {}
    for r in signed:
        k = (r['recorded'] or {}).get('cls', 'none'); rec_cls[k] = rec_cls.get(k, 0) + 1
    where = {}
    for r in signed:
        k = (r['resolved'] or {}).get('where', 'none') if r['cls'] == 'archive' else 'none'; where[k] = where.get(k, 0) + 1
    R = records()
    return dict(index=A['meta'], any_plan=APR.summary(R), any_plan_rule='signed = every signed-off record on any plan (current plan + superseded blocks + retired plans); archived = a row in the AGIdock INDEX or a full record on rtx-pro; viewable = a routed-layout pack in the layout store',
                any_plan_not_viewable=sorted(r['id'] for r in R.values() if not r['pack']), any_plan_not_archived=sorted(r['id'] for r in R.values() if not (r['archive']['agi'] or r['archive']['rtx'])),
                signed=len(signed), signed_by_source=tally(signed), signed_resolved_where=where, signed_recorded_host_class=rec_cls,
                signed_recorded_hosts={h: sum(1 for r in signed if (r['recorded'] or {}).get('host') == h) for h in sorted({(r['recorded'] or {}).get('host') or '-' for r in signed})},
                signed_not_in_archive=[dict(id=r['id'], recorded=r['recorded'], pack=r['pack']) for r in signed if r['cls'] != 'archive'],
                signed_on_both=sum(1 for r in signed if r['rtx'] and r['agi']), signed_rtx_pro_only=sum(1 for r in signed if r['rtx'] and not r['agi']), signed_agidock_only=sum(1 for r in signed if r['agi'] and not r['rtx']),
                signed_agidock_only_list=[r['id'] for r in signed if r['agi'] and not r['rtx']],
                signed_rtx_pro_only_list=[dict(id=r['id'], kind=(r['resolved'] or {}).get('kind'), path=(r['resolved'] or {}).get('path')) for r in signed if r['rtx'] and not r['agi']],
                signed_pack_missing_but_archived=[r['id'] for r in signed if not r['pack'] and r['cls'] == 'archive'],
                off_limits=sorted(OFF_LIMITS), rule='signed records live on rtx-pro (signed-export-1114, closed_archive) and AGIdock /archive; fleet paths are provenance only and are never read by the explorer')


# ---------------------------------------------------------------------------------------------- fleet
# The Fleet view reuses the old fleet-viz collectors: /api/fleet, /api/fleetjobs, /api/jobs, /api/verdicts of the fleet-viz
# service (FLEET_API; on epyc8 a reverse tunnel to the owner's host).  Added here: per-job die / item / stage parsed from the
# job's directory and command, and a light probe of RAM admission (ot-heavy-reconcile --free) and disks (df) per host.
FLEET_API = os.environ.get('FLEET_API', 'http://127.0.0.1:8764')
FLEET_TTL = dict(fleet=4, fleetjobs=12, jobs=12, verdicts=45)
PROBE_HOSTS = [h for h in os.environ.get('FLEET_PROBE_HOSTS', 'intel1,intel2,epyc2,epyc7,epyc8,epyc9,epyc10,epyc11,epyc12').split(',') if h]
_FLEET = {}; _FLEET_FAIL = dict(t=0, err=None); _PROBE = dict(t=0, hosts={}, thread=None); _AUDIT = dict(t=0, rows=None, error=None)
DIE_RE = re.compile(r'/runs/(s81_head|s81|qwen_compute|qwen_kvsys|hbm)/|[/_-](s81_head|qwen_compute|qwen_kvsys)[/_-]|/(?:die-)?(s81|hbm|head|kv|qc)[-_/]', re.I)
ITEM_RE = re.compile(r'/items/([^/\s"\']+)/attempt_(\d+)(?:/([a-z0-9_]+))?')
STAGE_RE = re.compile(r'(?:^|[-_ /])(synth|floorplan|place|cts|grt|route|drt|fill|final|signoff|sta|lec|drc|rcx|gen|bind|export|verify)(?:[-_ /.]|$)', re.I)
DIE_ALIAS = dict(head='s81_head', kv='qwen_kvsys', qc='qwen_compute')


def job_fields(r):
    """die / item / attempt / stage of one fleet job row, from its directory, name and command (best effort, None when unknown)"""
    import base64
    text = ' '.join(str(r.get(k) or '') for k in ('cwd', 'name', 'detail'))
    spec = re.search(r'--spec-b64 ([A-Za-z0-9+/=_-]{40,})', text)
    if spec:
        try:
            raw = spec.group(1); o = json.loads(base64.b64decode(raw + '=' * (-len(raw) % 4)))
            text += ' ' + str(o.get('name') or '') + ' ' + ' '.join(str(i.get('path') or '') for i in o.get('inputs') or [])
            r['job'] = o.get('name')
        except Exception:
            pass
    m = ITEM_RE.search(text); d = DIE_RE.search(text)
    die = next((g for g in d.groups() if g), None).lower() if d else None
    out = dict(die=DIE_ALIAS.get(die, die), item=m.group(1) if m else None, attempt=int(m.group(2)) if m else None, stage=None)
    # the job name says the stage best (<item>-place); the directory after attempt_N is the kit dir ("gen"), used only as a last resort
    for c in [str(r.get('job') or ''), str(r.get('name') or ''), str(r.get('detail') or '')[-500:], m.group(3) if m and m.group(3) else '']:
        st = [x.lower() for x in STAGE_RE.findall(c)]
        real = [x for x in st if x != 'gen']
        if real: out['stage'] = real[-1]; break
        if st and not out['stage']: out['stage'] = 'kit gen'
    return out


def fleet_get(name):
    import urllib.request
    if name not in FLEET_TTL: raise ApiError(404, 'unknown fleet endpoint', name)
    now = time.time(); c = _FLEET.get(name)
    if c and now - c[0] < FLEET_TTL[name]: return c[1]
    if now - _FLEET_FAIL['t'] < 20 and not (c and now - c[0] < 180): raise ApiError(502, 'the fleet collector did not answer', _FLEET_FAIL['err'])   # do not hammer a dead collector
    try:
        o = json.loads(urllib.request.urlopen(FLEET_API + '/api/' + name, timeout=8).read())
    except Exception as e:
        _FLEET_FAIL.update(t=now, err='%s (%s: %s)' % (FLEET_API, type(e).__name__, e))
        if c and now - c[0] < 180: return c[1]   # a short outage: the last answer, its own generated_at says how old it is
        raise ApiError(502, 'the fleet collector did not answer', '%s (%s: %s)' % (FLEET_API, type(e).__name__, e))
    if name == 'fleetjobs':
        for r in o.get('rows') or []:
            r.update(job_fields(r)); d = str(r.get('detail') or '')
            if len(d) > 600: r['detail'] = d[:600] + ' …'
    if name == 'fleet': o.pop('regions', None)
    raw = json.dumps(o, separators=(',', ':')).encode(); body = gzip.compress(raw, 4)
    _FLEET[name] = (now, body, o.get('generated_at') or o.get('t'))
    return body


def _probe_one(host):
    me = os.uname().nodename
    cmd = 'ot-heavy-reconcile --free 2>/dev/null | tail -1; echo ---; df -BG --output=target,size,avail,pcent / /srv/opentallas-scratch* 2>/dev/null | tail -n +2 | sort -u'
    local = host == os.environ.get('FLEET_PROBE_SELF', 'epyc8')
    argv = ['bash', '-c', cmd] if local else ['ssh', '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6', '-o', 'ControlPath=none', host, cmd]
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=20).stdout
        a, _, d = out.partition('---')
        try: adm = json.loads(a.strip().splitlines()[-1])
        except Exception: adm = None
        disks = []; seen = set()
        for ln in d.strip().splitlines():
            f = ln.split()
            if len(f) == 4 and f[1].endswith('G'):
                key = (f[1], f[2])   # scratch2/scratch3 are often one file system
                disks.append(dict(mount=f[0], size_gb=int(f[1][:-1]), avail_gb=int(f[2][:-1]), pct=int(f[3].rstrip('%')), same_as=None if key not in seen or f[0] == '/' else True)); seen.add(key)
        keep = ('total_gb', 'avail_gb', 'used_gb', 'reserved_gb', 'floor_gb', 'headroom_gb', 'admit_gb', 'free_gb', 'cpu_load1', 'ncpu', 'running', 'waiting', 'waiting_gb', 'disk_gb', 'plenty')
        return dict(t=time.time(), admit={k: adm.get(k) for k in keep} if adm else None, disks=disks, error=None if (adm or disks) else 'no answer')
    except Exception as e:
        return dict(t=time.time(), admit=None, disks=[], error='%s: %s' % (type(e).__name__, str(e)[:120]))


def fleet_probe():
    """RAM admission + disks per host, refreshed in the background at most every 90 s while somebody looks at the Fleet view"""
    now = time.time()
    if now - _PROBE['t'] > 90 and not (_PROBE['thread'] and _PROBE['thread'].is_alive()):
        _PROBE['t'] = now

        def run():
            ths = []
            def one(h): _PROBE['hosts'][h.upper()] = _probe_one(h)
            for h in PROBE_HOSTS: t = threading.Thread(target=one, args=(h,), daemon=True); t.start(); ths.append(t)
            for t in ths: t.join(25)
        _PROBE['thread'] = threading.Thread(target=run, daemon=True); _PROBE['thread'].start()
    return dict(t=_PROBE['t'], hosts=_PROBE['hosts'], probed=[h.upper() for h in PROBE_HOSTS], note='hosts not listed are not reachable from the service host (the owner machine is not probed)')


# signed-layout archive table (SIGNED-DB-AUDIT lane): where the signed routed databases live after they left the fleet hosts
AUDIT_SRC = os.environ.get('SIGNED_DB_AUDIT', 'intel2:coord/lanes/SIGNED-DB-AUDIT.tsv')


def signed_audit():
    now = time.time()
    if now - _AUDIT['t'] > 600:
        _AUDIT['t'] = now

        def run():
            try:
                f = OWN / 'SIGNED-DB-AUDIT.tsv'
                if ':' in AUDIT_SRC and not os.path.exists(AUDIT_SRC):
                    host, path = AUDIT_SRC.split(':', 1)
                    r = subprocess.run(['ssh', '-n', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', '-o', 'ControlPath=none', host, 'cat ' + path], capture_output=True, text=True, timeout=40)
                    if r.returncode == 0 and r.stdout.strip(): OWN.mkdir(parents=True, exist_ok=True); f.write_text(r.stdout)
                    elif not f.is_file(): _AUDIT['error'] = 'not posted yet (%s)' % AUDIT_SRC; return
                else: f = pathlib.Path(AUDIT_SRC)
                lines = [ln for ln in f.read_text().splitlines() if ln.strip() and not ln.startswith('#')]
                head = [h.strip().lower() for h in lines[0].split('\t')]
                rows = {}
                for ln in lines[1:]:
                    o = dict(zip(head, [c.strip() for c in ln.split('\t')]))
                    for v in set(o.values()):   # index by every cell: node id, die/name, bare name
                        if v and len(v) < 160 and re.match(r'^[A-Za-z0-9_./-]+$', v): rows.setdefault(v.split('/')[-1] if '/' in v and len(v.split('/')) == 2 else v, []).append(o)
                _AUDIT['rows'] = rows; _AUDIT['error'] = None; _AUDIT['mtime'] = f.stat().st_mtime; _AUDIT['n'] = len(lines) - 1
            except Exception as e:
                _AUDIT['error'] = '%s: %s' % (type(e).__name__, str(e)[:160])
        threading.Thread(target=run, daemon=True).start()
    return _AUDIT


def audit_rows(n):
    a = signed_audit()
    if not a.get('rows'): return None
    hits = a['rows'].get(n['id']) or a['rows'].get(n['name']) or a['rows'].get((n.get('plan') or {}).get('module') or '') or []
    hits = [h for h in hits if not h.get('die') or h['die'] in (n['die'], DIE_SHORT.get(n['die'], ''))] or hits
    return hits[:4] or None


DIE_SHORT = dict(s81='S81', s81_head='HEAD', qwen_compute='QC', qwen_kvsys='KV', hbm='HBM')


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

    def gz(self, body, cache='no-cache'):
        """a gzip body, plain for a client that did not ask for gzip"""
        if 'gzip' in (self.headers.get('Accept-Encoding') or ''): return self.send(200, body, 'application/json', (('Content-Encoding', 'gzip'), ('Cache-Control', cache), ('Vary', 'Accept-Encoding')))
        return self.send(200, gzip.decompress(body), 'application/json', (('Cache-Control', cache),))

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
            if path == '/api/elements': return self.json('compat:elements', DS.index() and DS.index().get('generated'), elements_compat)
            if path == '/api/plan_now':
                f = STATE / 'plan_now.json'
                if not f.is_file(): raise ApiError(404, 'no plan_now.json', str(f))
                return self.json('compat:plan_now', _mtime(f), lambda: json.loads(f.read_text()))
            if path in LEGACY and not q:
                self.send_response(302); self.send_header('Location', '/?legacy=' + LEGACY[path]); self.send_header('Content-Length', '0'); self.end_headers(); return
            if path.startswith('/engine/'): return self.file(ENGINE, path[8:], immutable='/vendor/' in path)
            if path.startswith('/explorer/') and path.endswith('.js') and path.split('/')[2] in ('element', 'token', 'dataflow', 'coverage'):
                return self.file(FV / 'explorer', path[len('/explorer/'):])   # kept engine modules at the paths they import each other by
            rel = path.lstrip('/') or 'index.html'
            if not (WEB / rel).is_file():   # an old bookmark: land on the matching view, never a 404 page
                to = legacy_target(path, q)
                if to: self.send_response(302); self.send_header('Location', to); self.send_header('Cache-Control', 'no-store'); self.send_header('Content-Length', '0'); self.end_headers(); return
            return self.file(WEB, rel)
        except ApiError as e:
            return self.fail(e.code, e.msg, e.detail)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as e:   # one broken dataset must not take the page down
            return self.fail(500, 'server error', '%s: %s' % (type(e).__name__, e))

    def api(self, p, q):
        g = lambda k, d='': (q.get(k, [d])[0] or d)
        idx = DS.index(); stamp = (idx.get('generated') if idx else None, _mtime(CENSUS))
        if p == 'meta': return self.send(200, json.dumps(meta(), separators=(',', ':')).encode(), 'application/json', (('Cache-Control', 'no-store'),))
        if p == 'dies': return self.json('dies', (stamp, _mtime(ARCHIVE_INDEX), _mtime(layout_service.LS.STORE / 'elements'), int(time.time() // 120)), dies)
        if p.startswith('die/'): d = p[4:]; return self.json('die:' + d, stamp, lambda: die(d))
        if p.startswith('node/'): n = p[5:]; return self.json('node:' + n, (stamp, _mtime(layout_service.LS.STORE / 'elements' / n / 'index.json'), _mtime(ARCHIVE_INDEX), _AUDIT.get('mtime'), int(time.time() // 120)), lambda: node(n))
        if p.startswith('compose/'): d = p[8:]; return self.json('compose:' + d, stamp, lambda: compose_of(d))
        if p.startswith('closure/'): d = p[8:]; return self.json('closure:' + d, (stamp, _mtime(ARCHIVE_INDEX), _mtime(layout_service.LS.STORE / 'elements'), int(time.time() // 120)), lambda: closure(d))
        if p == 'resolve': return self.send(200, json.dumps(resolve([x for x in g('q').split(',') if x][:400])).encode(), 'application/json', (('Cache-Control', 'no-cache'),))
        if p == 'search': return self.send(200, json.dumps(search(g('q'), g('die') or None, min(200, int(g('limit', '40') or 40)))).encode(), 'application/json', (('Cache-Control', 'no-cache'),))
        if p.startswith('layout/'): return LS.handle(self, p[7:], q, False)
        if p.startswith('store/'): return LS.static(self, p[6:], False)
        if p == 'dataflow/index': return self.send(200, json.dumps(dataflow_index(), separators=(',', ':')).encode(), 'application/json', (('Cache-Control', 'no-cache'),))
        if p.startswith('dataflow/record/'):
            rid = p[len('dataflow/record/'):]
            if not layout_service.valid_name(rid): raise ApiError(400, 'bad record id', rid)
            f = DF_OWN / (rid + '.links.json.gz')
            if not f.is_file(): f = DATAFLOW / (rid + '.links.json.gz')
            if not f.is_file(): raise ApiError(404, 'no such data-flow record', rid)
            return self.gz(f.read_bytes())
        if p == 'token/index': return self.json('tok:index', (_mtime(TOKEN / 'index.json'), _mtime(design_service.TOKEN_MAP)), token_index)
        if p.startswith('token/record/'):
            rid = p[len('token/record/'):]
            if not layout_service.valid_name(rid): raise ApiError(400, 'bad record id', rid)
            f = TOKEN / (rid + '.json')
            if not f.is_file(): raise ApiError(404, 'no such token record', rid)
            return self.json('tok:rec:' + rid, _mtime(f), lambda: json.loads(f.read_text()))
        if p.startswith('token/map/'):
            k = p[len('token/map/'):]
            return self.json('tok:map:' + k, (stamp, _mtime(design_service.TOKEN_MAP)), lambda: token_map(k))
        if p == 'count':   # the archive-gated count: signed = credited by the count AND archived on AGIdock; the rest is pending archive
            def count():
                i = index(); g = (i.get('count_overlay') or {}).get('archive_gate') or {}
                return dict(schema='opentallas.explorer.count.v1', rule='signed = credited by the sign-off count AND database + view files + signoff.json present (non-empty) in the AGIdock archive; otherwise pending archive, not counted',
                            census=(signoff_census() or {}).get('summary'), generated=i.get('generated'), count_generated=(i.get('count_overlay') or {}).get('count_generated'), archive_listed=g.get('index_listed'), index_tsv=g.get('index_tsv'), error=g.get('error'),
                            dies={d: dict(types=i['nodes'][d].get('type_count'), signed_types=v['type']['counted'], pending_archive_types=v['type']['pending'], credited_types=v['type']['before'],
                                          signed_cores=v['core']['counted'], pending_archive_cores=v['core']['pending'], credited_cores=v['core']['before'], pending=v['pending_list']) for d, v in (g.get('dies') or {}).items()})
            return self.json('count', stamp, count)
        if p == 'records': return self.json('records:%s:%s' % (g('die'), g('plan')), (stamp, _mtime(ARCHIVE_INDEX), _mtime(layout_service.LS.STORE / 'elements'), int(time.time() // 120)), lambda: records_list(g('die') or None, g('plan') or None))
        if p == 'archive/summary': return self.json('archive:summary', (stamp, _mtime(ARCHIVE_INDEX), _AUDIT.get('mtime'), _mtime(layout_service.LS.STORE / 'elements'), int(time.time() // 120)), archive_summary)
        if p == 'fleet/probe': return self.send(200, json.dumps(fleet_probe(), separators=(',', ':')).encode(), 'application/json', (('Cache-Control', 'no-store'),))
        if p.startswith('fleet/'): return self.gz(fleet_get(p[6:]), 'no-store')
        if p == 'coverage':
            now = time.time(); o = dict(COV.api(), generated_at=now)
            return self.gz(gzip.compress(json.dumps(o, separators=(',', ':')).encode(), 5))
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
