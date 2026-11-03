#!/usr/bin/env python3
"""List hierarchical instance paths (from the top) to modules whose name matches a regex, from a verilator --json-only tree."""
import json, re, sys
t = json.load(open(sys.argv[1])); pat = re.compile(sys.argv[2])
mods = {}
def cells(n, acc, prefix):
    if isinstance(n, dict):
        if n.get('type') == 'CELL':
            acc.append((prefix + n['name'], n.get('modp'))); return
        if n.get('type') == 'BEGIN' and n.get('name'):
            prefix = prefix + n['name'] + '.'
        for k, v in n.items():
            if isinstance(v, (list, dict)): cells(v, acc, prefix)
    elif isinstance(n, list):
        for x in n: cells(x, acc, prefix)
addr = {}
for m in t['modulesp']:
    addr[m['addr']] = m; acc = []; cells(m.get('stmtsp', []), acc, ''); m['_cells'] = acc
top = [m for m in t['modulesp'] if m.get('level') == 2 or m.get('isTop')] or t['modulesp'][:1]
def walk(m, path):
    for nm, mp in m['_cells']:
        c = addr.get(mp)
        if c is None: continue
        p = path + '.' + nm if path else nm
        if pat.search(c.get('origName', c['name'])): print(p, c['name'])
        else: walk(c, p)
print('# top', top[0]['name'], file=sys.stderr)
walk(top[0], '')
