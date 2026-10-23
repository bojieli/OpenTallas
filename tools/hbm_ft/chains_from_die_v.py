#!/usr/bin/env python3
"""FT-HBM: relay chains of the HBM die netlist -> per-row (stage) bits + driver/load blocks. Usage: die.v insts.tsv out.json"""
import re, sys, json, collections
dv, tsv, out = sys.argv[1:4]
RLY = re.compile(r'^hbfd_')
inst_re = re.compile(r'^\s+(\S+)\s+(\S+)\s+\($')
pin_re = re.compile(r'^\s+\.(\w+)\((.*)\),?$')
def nets(s):
    s = s.strip()
    if s.startswith('{'): s = s[1:-1]
    return [t.strip() for t in s.split(',') if t.strip()]
# pass 1: relay instances
rows = {}           # inst -> dict(m, a=[...], b=[...])
cur = None
others_lines = []
with open(dv) as f:
    for line in f:
        m = inst_re.match(line)
        if m:
            cur = (m.group(1), m.group(2)); continue
        if cur is None: continue
        if line.strip() == ');': cur = None; continue
        if RLY.match(cur[0]):
            p = pin_re.match(line)
            if p and p.group(1) in ('a', 'b', 'i', 'o'):
                rows.setdefault(cur[1], {'m': cur[0]})[{'i': 'a', 'o': 'b'}.get(p.group(1), p.group(1))] = nets(p.group(2))
relay_net = {}
for i, r in rows.items():
    for n in r.get('a', []): relay_net.setdefault(n, []).append((i, 'a'))
    for n in r.get('b', []): relay_net.setdefault(n, []).append((i, 'b'))
# pass 2: non-relay pins touching relay nets
ext = collections.defaultdict(list)   # net -> [(inst, pin)]
cur = None
with open(dv) as f:
    for line in f:
        m = inst_re.match(line)
        if m: cur = (m.group(1), m.group(2)); continue
        if cur is None: continue
        if line.strip() == ');': cur = None; continue
        if RLY.match(cur[0]): continue
        p = pin_re.match(line)
        if not p: continue
        for n in nets(p.group(2)):
            if n in relay_net: ext[n].append((cur[1], p.group(1)))
pos = {}
for l in open(tsv):
    f = l.split('\t'); pos[f[0]] = [float(f[2]), float(f[3]), float(f[4]), float(f[5])]
res = {}
for i, r in rows.items():
    A = collections.Counter(); B = collections.Counter(); up = collections.Counter(); dn = collections.Counter()
    for n in r.get('a', []):
        for (j, d) in relay_net.get(n, []):
            if d == 'b' and j != i: up[j] += 1
        for (j, p) in ext.get(n, []): A[j] += 1
    for n in r.get('b', []):
        for (j, d) in relay_net.get(n, []):
            if d == 'a' and j != i: dn[j] += 1
        for (j, p) in ext.get(n, []): B[j] += 1
    res[i] = dict(m=r['m'], bits=len(r.get('a', [])), xy=pos.get(i), up=dict(up), dn=dict(dn), src=dict(A), dst=dict(B))
json.dump(res, open(out, 'w'))
print('relay insts', len(res))
