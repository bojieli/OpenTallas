#!/usr/bin/env python3
"""connectivity of qkd_hr_cluster.v: bits between instances and between top ports and instances."""
import re, sys, json, collections
t = open(sys.argv[1]).read()
top = t[t.index('module qkd_hr_cluster'):]
top = top[:top.index('endmodule')]
W = {}; DIR = {}
for m in re.finditer(r'^\s*(input|output|wire)\s*(\[(\d+):(\d+)\])?\s*([\w$\\.\[\]]+)\s*;', top, re.M):
    d, _, a, b, n = m.groups()
    w = abs(int(a) - int(b)) + 1 if a else 1
    W[n] = (w, min(int(a), int(b)) if a else 0)
    if d != 'wire': DIR[n] = d
def bits(expr):
    expr = expr.strip()
    if not expr: return []
    if expr.startswith('{'):
        inner = expr[1:-1]; parts = []; dep = 0; cur = ''
        for ch in inner:
            if ch == '{': dep += 1
            if ch == '}': dep -= 1
            if ch == ',' and dep == 0: parts.append(cur); cur = ''
            else: cur += ch
        parts.append(cur); out = []
        for p in parts: out += bits(p)
        return out
    if re.match(r"^\d+'", expr) or re.match(r'^\d+$', expr): return []
    m = re.match(r'^([\w$\\.]+)\s*\[(\d+)(?::(\d+))?\]$', expr)
    if m:
        n, a, b = m.group(1), int(m.group(2)), m.group(3)
        if b is None: return [(n, a)]
        b = int(b); lo, hi = min(a, b), max(a, b); return [(n, i) for i in range(lo, hi + 1)]
    n = expr
    w, lo = W.get(n, (1, 0)); return [(n, lo + i) for i in range(w)]
inst = {}
for m in re.finditer(r'^\s*(\w+)\s*(#\(.*?\))?\s+(\w+)\s*\((.*?)\);', top, re.M | re.S):
    typ, _, nm, body = m.groups()
    if typ in ('input', 'output', 'wire', 'assign', 'module'): continue
    pins = {}
    for pm in re.finditer(r'\.(\w+)\(([^()]*(?:\{[^()]*\})?[^()]*)\)', body):
        pins[pm.group(1)] = bits(pm.group(2))
    inst[nm] = (typ, pins)
# assigns: alias
alias = {}
for m in re.finditer(r'^\s*assign\s+(.*?)\s*=\s*(.*?);', top, re.M):
    l, r = bits(m.group(1)), bits(m.group(2))
    for a, b in zip(l, r): alias[a] = b
def root(b):
    seen = 0
    while b in alias and seen < 50: b = alias[b]; seen += 1
    return b
net2 = collections.defaultdict(set)
for nm, (typ, pins) in inst.items():
    for p, bb in pins.items():
        for b in bb: net2[root(b)].add(nm)
for n in DIR:
    w, lo = W[n]
    for i in range(w): net2[root((n, lo + i))].add('PORT:' + n)
for a in list(alias):
    if a[0] in DIR: net2[root(a)].add('PORT:' + a[0])
pair = collections.Counter(); portto = collections.defaultdict(collections.Counter)
for b, s in net2.items():
    ins = sorted(x for x in s if not x.startswith('PORT:')); ps = [x[5:] for x in s if x.startswith('PORT:')]
    for i in range(len(ins)):
        for j in range(i + 1, len(ins)): pair[(ins[i], ins[j])] += 1
    for p in ps:
        for i in ins: portto[p][i] += 1
        if not ins: portto[p]['<none/port-port>'] += 1
json.dump(dict(pairs={f'{a}|{b}': c for (a, b), c in pair.items()}, ports={p: dict(c) for p, c in portto.items()},
               widths={p: W[p][0] for p in DIR}, dirs=DIR, types={k: v[0] for k, v in inst.items()}), open(sys.argv[2], 'w'), indent=1)
print(len(inst), 'instances'); 
for (a, b), c in pair.most_common(40): print(f'{c:6d} {a} {b}')

# ---- per instance-port: peers (other instances / PORT:x) ----
if len(sys.argv) > 3:
    pp = {}
    for nm, (typ, pins) in inst.items():
        d = {}
        for p, bb in pins.items():
            c = collections.Counter()
            for b in bb:
                for x in net2[root(b)]:
                    if x != nm: c[x] += 1
            d[p] = dict(c)
        pp[nm] = d
    json.dump(pp, open(sys.argv[3], 'w'), indent=0)
if len(sys.argv) > 4:
    nb = {}
    for nm, (typ, pins) in inst.items():
        nb[nm] = {p: ['%s[%d]' % root(b) for b in bb] for p, bb in pins.items()}
    portbits = {}
    for n in DIR:
        w, lo = W[n]
        portbits[n] = ['%s[%d]' % root((n, lo + i)) for i in range(w)]
    json.dump(dict(inst=nb, ports=portbits), open(sys.argv[4], 'w'))
