import json, os, hashlib, sys
B, D = sys.argv[1], sys.argv[2]
a = json.load(open(B + '/gates.json'))['gates']; b = json.load(open(D + '/gates.json'))['gates']
for k in a:
    ka = {x: y for x, y in a[k].items() if not isinstance(y, (list, dict))}
    kb = {x: y for x, y in b.get(k, {}).items() if not isinstance(y, (list, dict))}
    d = {x: (ka.get(x), kb.get(x)) for x in set(ka) | set(kb) if ka.get(x) != kb.get(x)}
    print(k, a[k]['verdict'], '->', b[k]['verdict'], d if d else '')
def h(p):
    s = json.load(open(p)); [s.pop(k, None) for k in ('plan', 'plan_sha256', 'master_plan_sha256')]
    return hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest()
sa = sorted(os.listdir(B + '/slices'))
print('slices', len(sa), 'differing:', [f for f in sa if h(B + '/slices/' + f) != h(D + '/slices/' + f)])
