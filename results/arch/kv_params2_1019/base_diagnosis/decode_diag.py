import json, re, sys, collections
t = open(sys.argv[1]).read()
t = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', t)
d = json.loads(t)
sig = {}
for s in d['signal']:
    if not isinstance(s, dict) or 'name' not in s: continue
    w = s.get('wave', ''); data = s.get('data', [])
    vals, cur, di = [], None, 0
    for ch in w:
        if ch == '.': vals.append(cur); continue
        if ch in '=2345': cur = data[di] if di < len(data) else None; di += 1
        else: cur = ch
        vals.append(cur)
    sig[s['name']] = vals
print('trigger', sig.get('trigger'))
gold = {n[5:]: v for n, v in sig.items() if n.startswith('gold_')}
gate = {n[5:]: v for n, v in sig.items() if n.startswith('gate_')}
print('gold', len(gold), 'gate', len(gate))
bad = collections.defaultdict(list)
for k in gold:
    if k in gate:
        g, h = gold[k], gate[k]
        for i in range(min(len(g), len(h))):
            if g[i] != h[i]: bad[i].append((k, g[i], h[i]))
for i in sorted(bad):
    c = collections.Counter(re.sub(r'_\d+_$', '', re.sub(r'_\d+__', '_*__', x[0])) for x in bad[i])
    print('idx', i, len(bad[i]), c.most_common(10), bad[i][:4])
for k in ('rst_n',):
    print(k, [sig[n] for n in sig if n.endswith(k)][:2])
