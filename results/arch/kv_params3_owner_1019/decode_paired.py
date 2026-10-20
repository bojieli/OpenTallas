import json, re, sys, collections
t = open(sys.argv[1]).read()
t = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', t)
d = json.loads(t)
sig = {}
for s in d['signal']:
    if not isinstance(s, dict) or 'name' not in s: continue
    w = s.get('wave', ''); data = s.get('data', [])
    # expand wave: '1','0','x','.', '=' consumes data
    vals, cur, di = [], None, 0
    for ch in w:
        if ch == '.': vals.append(cur); continue
        if ch in '=2345': cur = data[di] if di < len(data) else None; di += 1
        else: cur = ch
        vals.append(cur)
    sig[s['name']] = vals
trig = sig.get('trigger'); print('trigger', trig)
steps = len(trig)
mism = collections.defaultdict(list)
for n, v in sig.items():
    if n.startswith('gold_'):
        g = sig.get('gate_' + n[5:])
        if g is None: continue
        for i in range(min(len(v), len(g))):
            if v[i] is not None and g[i] is not None and v[i] != g[i] and 'x' not in str(v[i]) + str(g[i]):
                mism[i].append(n[5:])
for i in sorted(mism):
    c = collections.Counter(re.sub(r'_\d+_$', '', re.sub(r'g_n_\d+__', 'g_n_*__', x)) for x in mism[i])
    print('step', i + 1, len(mism[i]), c.most_common(12))
pairs = [n for n in sig if n.startswith('gold_') and 'gate_' + n[5:] in sig]
print('pairs', len(pairs), 'gold_', sum(1 for n in sig if n.startswith('gold_')), 'gate_', sum(1 for n in sig if n.startswith('gate_')))
ex = [n for n in sig if not n.startswith(('gold_', 'gate_'))][:20]; print('other', ex)
xs = collections.Counter()
for n in pairs:
    g, h = sig[n], sig['gate_' + n[5:]]
    if len(g) > 7 and (g[7] != h[7]): xs[(str(g[7]), str(h[7]))] += 1
print('step7 diffs incl x', xs.most_common(10))
lst = [n for n in pairs if len(sig[n]) > 7 and sig[n][7] != sig['gate_' + n[5:]][7]][:15]; print(lst)
pc = collections.Counter(re.match(r'^(\$flatten\\\\)?[a-z_]+[._]', n).group(0) if re.match(r'^(\$flatten\\\\)?[a-z_]+[._]', n) else n[:12] for n in sig)
print(pc.most_common(12))
g2 = {n[5:]: n for n in sig if n.startswith('gold.S__')}; h2 = {n[5:]: n for n in sig if n.startswith('gate.S__')}
print('gold.S__', len(g2), 'gate.S__', len(h2))
ks = [k for k in g2 if k in h2]
bad = collections.defaultdict(list)
for k in ks:
    g, h = sig[g2[k]], sig[h2[k]]
    for i in range(1, min(len(g), len(h))):
        if g[i] != h[i]: bad[i].append(k)
for i in sorted(bad):
    c = collections.Counter(re.sub(r'_\d+_$', '', re.sub(r'g_n_\d+__', 'g_n_*__', x)) for x in bad[i])
    print('idx', i, len(bad[i]), c.most_common(10))
gold_only = {n[5:]: n for n in sig if n.startswith('gold_S__')}
print('gold_S__ sample', list(gold_only)[:3])
