import json, re, sys
def canon(name, pair):
    n = name.split('$')[0] if name.startswith('$') else name
    if not pair: return name
    m = re.match(r'u_p(\d+)\.(u_s|u_link_)(\w+)$', name)
    if not m: return name
    c = int(m.group(1)); kind = m.group(2); x = m.group(3)
    if kind == 'u_s': return f'u_s{2*c+int(x)}'
    return {'n': f'u_link_{2*c}_{2*c+1}', 's': f'u_link_{2*c+1}_{2*c}'}[x]
def load(fn, top, pair):
    d = json.load(open(fn))['modules'][top]
    drv = {}   # bit id -> canonical driver
    for p, v in d['ports'].items():
        if v['direction'] == 'input':
            for k, b in enumerate(v['bits']): drv[b] = ('port', p, k)
    cells = {}
    for cn, c in d['cells'].items():
        ci = canon(cn, pair); cells[ci] = c
        for p, bits in c['connections'].items():
            if c['port_directions'][p] == 'output':
                for k, b in enumerate(bits):
                    if isinstance(b, int): drv[b] = ('cell', ci, p, k)
    sig = lambda b: ('const', b) if isinstance(b, str) else drv.get(b, ('undriven',))
    loads = {}
    for ci, c in cells.items():
        for p, bits in c['connections'].items():
            if c['port_directions'][p] == 'input':
                for k, b in enumerate(bits): loads[(ci, p, k)] = sig(b)
        loads[(ci, 'TYPE')] = (c['type'], json.dumps(c.get('parameters', {}), sort_keys=True))
    for p, v in d['ports'].items():
        if v['direction'] == 'output':
            for k, b in enumerate(v['bits']): loads[('OUT', p, k)] = sig(b)
    return loads
a = load('dsdv_svc_group72.json', 'dsdv_svc_group72', False)
b = load('dsdv_svc_group72p.json', 'dsdv_svc_group72p', True)
print('sinks', len(a), len(b))
diff = [k for k in set(a) | set(b) if a.get(k) != b.get(k)]
print('diffs', len(diff))
for k in sorted(diff, key=str)[:20]: print(k, a.get(k), b.get(k))
