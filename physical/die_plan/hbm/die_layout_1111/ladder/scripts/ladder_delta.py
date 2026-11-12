"""DIE-LAYOUT-HBM ladder plan delta: make / apply.
  ladder_delta.py make  BASE.json NEW.json DELTA.json.gz    record every changed top-level object by key
  ladder_delta.py apply BASE.json DELTA.json.gz OUT.json     rebuild NEW (byte-identical json.dumps(indent=1))
Keyed sections: partition_types (by name), partitions (name), ports (id), lanes (id), latency.lanes (lane id);
any other changed top-level key is carried whole."""
import gzip, json, sys, hashlib
KEYED = {'partitions': 'name', 'ports': 'id', 'lanes': 'id'}
def load(p):
    return json.load(gzip.open(p, 'rt') if p.endswith('.gz') else open(p))
def make(a, b):
    d = {'schema': 'die_layout_hbm.ladder_delta.v1', 'base_sha256': None}
    for k in set(a) | set(b):
        if a.get(k) == b.get(k):
            continue
        if k in KEYED:
            key = KEYED[k]
            A = {x[key]: x for x in a[k]}; B = {x[key]: x for x in b[k]}
            d[k] = {'order': [x[key] for x in b[k]], 'set': {n: B[n] for n in B if A.get(n) != B[n]}}
        elif k == 'partition_types':
            d[k] = {'order': list(b[k]), 'set': {n: v for n, v in b[k].items() if a[k].get(n) != v},
                    'del': [n for n in a[k] if n not in b[k]]}
        elif k == 'latency':
            la, lb = a[k], b[k]
            d[k] = {'lanes_order': list(lb['lanes']), 'lanes_set': {n: v for n, v in lb['lanes'].items() if la['lanes'].get(n) != v},
                    'rest': {x: lb[x] for x in lb if x != 'lanes' and la.get(x) != lb[x]}}
        else:
            d[k] = {'whole': b.get(k)}
    return d
def apply(a, d):
    b = dict(a)
    for k, v in d.items():
        if k in ('schema', 'base_sha256', '_key_order'):
            continue
        if k in KEYED:
            key = KEYED[k]; A = {x[key]: x for x in a.get(k, [])}
            A.update(v['set']); b[k] = [A[n] for n in v['order']]
        elif k == 'partition_types':
            A = dict(a[k]); A.update(v['set'])
            for n in v.get('del', []): A.pop(n, None)
            b[k] = {n: A[n] for n in v['order']}
        elif k == 'latency':
            L = dict(a[k]); ln = dict(a[k]['lanes']); ln.update(v['lanes_set'])
            L['lanes'] = {n: ln[n] for n in v['lanes_order']}; L.update(v['rest']); b[k] = L
        else:
            b[k] = v['whole']
    # keep the NEW key order
    return {k: b[k] for k in d.get('_key_order', list(b))}
if __name__ == '__main__':
    if sys.argv[1] == 'make':
        a, b = load(sys.argv[2]), load(sys.argv[3])
        d = make(a, b); d['_key_order'] = list(b)
        d['base_sha256'] = hashlib.sha256(open(sys.argv[2], 'rb').read()).hexdigest()
        with gzip.open(sys.argv[4], 'wt') as f:
            json.dump(d, f)
        r = apply(a, d)
        print('roundtrip equal', r == b, 'sections', {k: (len(v.get('set', v.get('lanes_set', {}))) if isinstance(v, dict) else '') for k, v in d.items() if k not in ('schema', 'base_sha256', '_key_order')})
    else:
        a, d = load(sys.argv[2]), load(sys.argv[3])
        r = apply(a, d)
        open(sys.argv[4], 'w').write(json.dumps(r, indent=1) + '\n')
        print('wrote', sys.argv[4], hashlib.sha256(open(sys.argv[4], 'rb').read()).hexdigest()[:12])
