"""/api/v1 contract (no browser): status, top-level keys, errors, gzip, ETag / 304, path traversal."""
import gzip, json, pytest
from helpers import http, http_noredirect, api, ALL_DIES, ROUTED_TYPE, SMALL_CORE, closure_rows


def jget(path, headers=None):
    st, h, b = http(path, headers)
    if h.get('content-encoding') == 'gzip': b = gzip.decompress(b)
    return st, h, json.loads(b)


def test_health():
    st, h, j = jget('/health')
    assert st == 200 and j['ok'] is True, j
    assert set(['ok', 'missing', 'service', 'datasets']) <= set(j)
    assert j['service'].get('sha')


def test_meta():
    st, h, j = jget('/api/v1/meta')
    assert st == 200
    assert set(['schema', 'service', 'states', 'dies', 'datasets']) <= set(j)
    assert [d['id'] for d in j['dies']] == ALL_DIES or set(d['id'] for d in j['dies']) == set(ALL_DIES)
    assert j['service']['now'] > 1e9 and 'sha' in j['service']
    for d in j['dies']: assert set(['id', 'label', 'plan']) <= set(d) and d['plan'].get('sha')
    for d in j['datasets']: assert set(['id', 'label', 'generated', 'age_s', 'state', 'source', 'used_by']) <= set(d), d
    assert 'design_index' in [d['id'] for d in j['datasets']]


def test_dies():
    st, h, j = jget('/api/v1/dies')
    assert st == 200 and set(['schema', 'generated', 'states', 'dies', 'sources']) <= set(j)
    assert set(d['id'] for d in j['dies']) == set(ALL_DIES)
    for d in j['dies']:
        assert set(['plan', 'counts', 'packs', 'cores', 'instances', 'area_um2', 'types']) <= set(d), (d['id'], sorted(d))


@pytest.mark.parametrize('die', ALL_DIES)
def test_die_compose_closure(die):
    st, _, j = jget('/api/v1/die/' + die)
    assert st == 200 and set(['die', 'states', 'generated', 'nodes', 'plan']) <= set(j)
    assert j['die']['id'] == die and j['die']['plan']['partitions'] and j['plan']['sha']
    st, _, c = jget('/api/v1/compose/' + die)
    assert st == 200 and set(['schema', 'die', 'label', 'outline', 'dbu', 'plan', 'packs', 'instances', 'summary']) <= set(c)
    assert c['instances'] and c['summary']
    st, _, k = jget('/api/v1/closure/' + die)
    assert st == 200 and set(['die', 'label', 'plan', 'states', 'counts', 'generated', 'rows']) <= set(k)
    assert k['rows'] and set(['id', 'name', 'level', 'state', 'pack']) <= set(k['rows'][0])


@pytest.mark.parametrize('nid', [ROUTED_TYPE, SMALL_CORE])
def test_node(nid):
    st, _, j = jget('/api/v1/node/' + nid)
    assert st == 200 and set(['node', 'die', 'children', 'users', 'placements', 'states', 'plan', 'packs']) <= set(j)
    if '.c.' in nid: assert 'uses' in j
    assert j['node']['id'] == nid and j['packs'] and j['packs']['latest']


def test_search_resolve():
    st, _, j = jget('/api/v1/search?q=iqf')
    assert st == 200 and set(['q', 'total', 'results']) <= set(j) and j['results']
    assert set(['kind', 'id', 'name', 'die']) <= set(j['results'][0])
    assert jget('/api/v1/search?q=iqf&die=hbm')[0] == 200
    assert jget('/api/v1/search?q=')[2]['results'] == []
    st, _, r = jget('/api/v1/resolve?q=iqf__t1')
    assert st == 200 and r.get('iqf__t1')


def test_layout_and_store():
    st, _, j = jget('/api/v1/layout/%s/search?q=clk' % ROUTED_TYPE)
    assert st == 200 and 'results' in j
    st, _, ix = jget('/api/v1/store/elements/%s/index.json' % ROUTED_TYPE)
    assert st == 200 and set(['element', 'latest', 'history']) <= set(ix)
    st, _, m = jget('/api/v1/store/elements/%s/%s.json' % (ROUTED_TYPE, ix['latest']))
    assert st == 200 and isinstance(m, dict)


def test_dataflow_token_coverage():
    st, _, j = jget('/api/v1/dataflow/index')
    assert st == 200 and set(['schema', 'records']) <= set(j)
    if j['records']:
        rid = j['records'][0].get('id') or j['records'][0].get('record')
        if rid:
            st, h, b = http('/api/v1/dataflow/record/' + rid, {'Accept-Encoding': 'gzip'})
            assert st == 200 and h.get('content-encoding') == 'gzip'
            st2, h2, b2 = http('/api/v1/dataflow/record/' + rid)   # a client that did not ask gets plain JSON
            assert st2 == 200 and 'content-encoding' not in h2 and json.loads(b2)
            json.loads(gzip.decompress(b))
    st, _, t = jget('/api/v1/token/index')
    assert st == 200 and set(['index', 'map_generated', 'mapped']) <= set(t)
    recs = t['index'].get('records') or t['index'].get('designs') or []
    if recs and isinstance(recs[0], dict):
        rid = recs[0].get('id') or recs[0].get('record')
        if rid: assert http('/api/v1/token/record/' + rid)[0] == 200
    st, _, c = jget('/api/v1/coverage')
    assert st == 200 and isinstance(c, dict) and c
    if t['mapped']:
        st, _, m = jget('/api/v1/token/map/' + t['mapped'][0])
        assert st == 200 and 'error' not in m, m


def test_token_map_unknown_design_is_404():
    """every other unknown id answers 404 {error, detail}; token/map/<unknown> answers 200 {error}"""
    st, h, m = jget('/api/v1/token/map/zzz_no_such_design')
    assert st == 404 and set(['error', 'detail']) <= set(m), (st, m)


@pytest.mark.parametrize('path', ['/api/v1/die/zzz', '/api/v1/node/zzz.t.nope', '/api/v1/compose/zzz', '/api/v1/closure/zzz', '/api/v1/nope', '/api/v1/', '/api/v1/dataflow/record/zzznone', '/api/v1/token/record/zzznone'])
def test_404_json(path):
    st, h, j = jget(path)
    assert st == 404, (path, st, j)
    assert 'json' in h['content-type'] and set(['error', 'detail']) <= set(j)


def test_bad_record_id_400():
    st, _, j = jget('/api/v1/dataflow/record/..%2f..%2fserver')
    assert st in (400, 404) and 'error' in j


def test_unknown_static_404_json():
    st, h, j = jget('/no/such/file.js')
    assert st == 404 and set(['error', 'detail']) <= set(j)


def test_gzip_and_vary():
    st, h, b = http('/api/v1/closure/s81', {'Accept-Encoding': 'gzip'})
    assert st == 200 and h.get('content-encoding') == 'gzip' and 'accept-encoding' in h.get('vary', '').lower()
    assert json.loads(gzip.decompress(b))['rows']
    st, h2, b2 = http('/api/v1/closure/s81', {'Accept-Encoding': 'identity'})
    assert 'content-encoding' not in h2 and json.loads(b2) == json.loads(gzip.decompress(b))


@pytest.mark.parametrize('path', ['/', '/js/app.js', '/css/app.css', '/css/tokens.css', '/js/core/store.js'])
def test_static_etag_304(path):
    st, h, b = http(path)
    assert st == 200 and h.get('etag'), (path, h)
    st2, h2, b2 = http(path, {'If-None-Match': h['etag']})
    assert st2 == 304 and b2 == b'' and h2.get('etag') == h['etag']
    st3, _, _ = http(path, {'If-None-Match': '"nope"'})
    assert st3 == 200
    st, h, b = http(path, {'Accept-Encoding': 'gzip'})
    if len(gzip.decompress(b) if h.get('content-encoding') == 'gzip' else b) > 1024: assert h.get('content-encoding') == 'gzip'


def test_static_content_types():
    assert http('/js/app.js')[1]['content-type'].startswith('text/javascript')
    assert http('/css/app.css')[1]['content-type'].startswith('text/css')
    assert http('/')[1]['content-type'].startswith('text/html')
    assert http('/js/app.js')[1].get('x-content-type-options') == 'nosniff'


@pytest.mark.parametrize('path', ['/../server.py', '/engine/../../server.py', '/api/v1/store/../x', '/%2e%2e/server.py', '/js/../../server.py',
                                  '/engine/%2e%2e/%2e%2e/server.py', '/fv/../../explorer/server.py', '/api/v1/store/%2e%2e/%2e%2e/server.py', '/js/..%2f..%2fserver.py',
                                  '//etc/passwd', '/../../../../etc/passwd', '/api/v1/store/../../../../etc/passwd'])
def test_path_traversal(path):
    import socket
    # raw request so the client does not normalise the dot segments
    host, port = __import__('helpers').BASE.split('//')[1].split(':'); port = int(port.split('/')[0])
    s = socket.create_connection((host, port), timeout=30)
    s.sendall(('GET %s HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n' % path).encode())
    buf = b''
    while True:
        c = s.recv(65536)
        if not c: break
        buf += c
    s.close()
    head, _, body = buf.partition(b'\r\n\r\n')
    assert b'import design_service' not in body and b'class H(BaseHTTPRequestHandler)' not in body and b'root:x:0:0' not in body, 'leaked file via ' + path
    # an index.html fallback or a 4xx is fine; a 200 with the server source is not
    assert head.split(b' ')[1] in (b'200', b'301', b'302', b'400', b'403', b'404'), head[:80]
