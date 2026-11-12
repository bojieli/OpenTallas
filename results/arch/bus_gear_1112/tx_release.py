#!/usr/bin/env python3
"""BUS-GEAR-2: per-slice gear-TX reset release depth (relay flops from the die reset root to each TX rst_n leaf)."""
import re, sys, json, collections
F = sys.argv[1]
drv = {}          # net -> (cell, inst, input net, stages)
inst_re = re.compile(r'^\s*(\w+)\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*(\w+)\s*\((.*)\);', re.S)
tx = {}
for line in open(F):
    if '.o(rs' not in line and '.q(rs' not in line and '.o(rsleaf' not in line and 'ot_s81_xc_gear_tx' not in line and '.q(rsleaf' not in line:
        continue
    m = inst_re.match(line)
    if not m: continue
    cell, par, inst, pins = m.groups()
    P = dict(re.findall(r'\.(\w+)\(([^()]*)\)', pins))
    if cell == 'ot_s81_xc_gear_tx':
        tx[inst] = P.get('rst_n'); continue
    out = P.get('o') or P.get('q')
    if not out or not out.startswith('rs'): continue
    n = 1
    if par:
        mm = re.search(r'\.N\((\d+)\)', par)
        if mm: n = int(mm.group(1))
    drv[out] = (cell, inst, P.get('i') or P.get('d'), n)
res = {}
for t, leaf in sorted(tx.items()):
    net, depth, path, seen = leaf, 0, [], set()
    while net in drv and net not in seen:
        seen.add(net); c, i, src, n = drv[net]; depth += n; path.append(c); net = src
    res[t] = dict(leaf=leaf, root=net, depth=depth, parity=depth % 2, cells=dict(collections.Counter(path)))
print(json.dumps(res, indent=1))
print('roots', collections.Counter(r['root'] for r in res.values()), 'parity', collections.Counter(r['parity'] for r in res.values()))
