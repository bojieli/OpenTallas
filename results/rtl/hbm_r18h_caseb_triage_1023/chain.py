import json, re, sys
from collections import Counter
I = json.load(open('/home/ubuntu/scratch/tokd-hbm2/slice_inst.json'))
def chain(expr):
    path = []
    seen = set()
    while True:
        m = re.search(r'\b((?:rf|rh)\d+_\w+?|l12p_\w+?)__(o|b|eb|ck_o)\b', expr)
        if not m: return path, expr
        n = m.group(1)
        if n in seen or n not in I: return path, expr
        seen.add(n)
        master, ports = I[n]
        path.append(master)
        expr = ports.get('i') or ports.get('a') or ''
for tgt, port in [(a.split('.')[0], a.split('.')[1]) for a in sys.argv[1:]]:
    if tgt not in I: print(tgt, 'missing'); continue
    e = I[tgt][1].get(port, '')
    p, root = chain(e)
    c = Counter(re.sub(r'_(EW|WE|NS|SN).*', '', x) for x in p)
    print(f"{tgt}.{port}: {len(p)} stages {dict(c)} root={root[:60]}")
