#!/usr/bin/env python3
"""KVJ-A3: per-child port table of the generated cluster (port, dir, width, the children/die ports on that net).
usage: port_table.py rtl/qwen_sys/host_cluster_20261017/qkd_hr_cluster.v OUT.json"""
import json, re, sys, collections
import glob, os
txt = ''.join(open(f).read() for f in sorted(glob.glob(os.path.join(os.path.dirname(sys.argv[1]), 'qkd_hr_*.v'))))
mods = {m.group(1): m.group(2) for m in re.finditer(r'\nmodule (\w+)\((.*?)\nendmodule', txt, re.S)}
def ports(body):
    out = {}
    for m in re.finditer(r'^\s*(input|output|inout)\s*(?:wire|reg)?\s*(\[(\d+):(\d+)\])?\s*(\w+)\s*;', body, re.M):
        out[m.group(5)] = (m.group(1), int(m.group(3)) - int(m.group(4)) + 1 if m.group(2) else 1)
    return out
top = mods['qkd_hr_cluster']
tports = ports(top)
inst = {}
for m in re.finditer(r'^  (qkd_hr_\w+|qfd_link_adp128|\w+) (?:#\(.*?\)\s*)?(u_\w+)\s*\((.*?)\);', top, re.S | re.M):
    conns = dict((a, b.strip()) for a, b in re.findall(r'\.(\w+)\(([^()]*)\)', m.group(3)))
    inst[m.group(2)] = (m.group(1), conns)
def nets(expr):
    return set(re.findall(r'[A-Za-z_]\w*', re.sub(r"\d+'[bhd][0-9a-fA-FxXzZ_]+", '', expr)))
users = collections.defaultdict(set)
for i, (t, c) in inst.items():
    for p, e in c.items():
        for n in nets(e):
            users[n].add(i)
alias = {}
for m in re.finditer(r'^\s*assign\s+(\w+)\s*=\s*([^;]+);', top, re.M):
    for n in nets(m.group(2)):
        alias.setdefault(m.group(1), set()).add(n); alias.setdefault(n, set()).add(m.group(1))
def closure(n):
    seen, st = {n}, [n]
    while st:
        x = st.pop()
        for y in alias.get(x, ()):
            if y not in seen: seen.add(y); st.append(y)
    return seen
res = {}
for i, (t, c) in inst.items():
    if not t.startswith('qkd_hr_'): continue
    P = ports(mods[t]); rows = []
    for p, (d, w) in P.items():
        e = c.get(p, '')
        nb = set()
        for n in nets(e):
            for x in closure(n):
                nb |= users.get(x, set())
                if x in tports: nb.add('DIE:' + x)
        nb.discard(i)
        rows.append(dict(port=p, dir=d, width=w, peers=sorted(nb)))
    res[t] = dict(inst=i, ports=rows, bits_in=sum(r['width'] for r in rows if r['dir'] == 'input'),
                  bits_out=sum(r['width'] for r in rows if r['dir'] == 'output'))
json.dump(res, open(sys.argv[2], 'w'), indent=1)
for t, r in res.items():
    print(t, len(r['ports']), r['bits_in'], r['bits_out'])
