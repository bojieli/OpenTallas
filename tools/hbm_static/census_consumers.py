#!/usr/bin/env python3
# For each census violation net: consumer cells -> nearest named downstream signals (BFS through unnamed nets).
import json, re, sys, collections
net_v, census, out = sys.argv[1], sys.argv[2], sys.argv[3]
txt = open(net_v).read()
cells = re.findall(r'^\s*(\w+)\s+(\\?\S+)\s*\((.*?)\);', txt, re.M | re.S)
pin_re = re.compile(r'\.(\w+)\((.*?)\)\s*(?:,|$)', re.S)
users = collections.defaultdict(list); drv = {}
OUTP = {'Y', 'QN', 'Q', 'CON', 'SN', 'CO', 'S'}
for typ, inst, body in cells:
    for p, n in pin_re.findall(body):
        n = n.strip()
        if p in OUTP: drv.setdefault(inst, []).append(n)
        else: users[n].append((inst, typ, p))
outs = {i: ns for i, ns in drv.items()}
def named(n): return not re.fullmatch(r'_\d+_', n)
r = json.load(open(census)); res = []
for v in r['violations']:
    seen = set(); front = [v['net']]; found = collections.Counter(); depth = 0
    while front and depth < 4:
        nxt = []
        for n in front:
            for inst, typ, p in users.get(n, []):
                if inst in seen: continue
                seen.add(inst)
                if 'DFF' in typ or 'SDF' in typ:
                    found['FF:' + re.sub(r'\[\d+\]', '[]', inst.lstrip('\\').split('$')[0])] += 1; continue
                for o in outs.get(inst, []):
                    if named(o): found['N:' + re.sub(r'\[\d+\]', '[]', o.lstrip('\\'))] += 1
                    else: nxt.append(o)
        front = nxt; depth += 1
    res.append({'driver': v['driver'], 'loads': v['loads'], 'role': v['driver_role'], 'consumers': found.most_common(6)})
json.dump(res, open(out, 'w'), indent=0)
