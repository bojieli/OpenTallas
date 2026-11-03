#!/usr/bin/env python3
"""Per-module own node count and flattened (instance-multiplied) weight from a verilator --json-only tree."""
import json, sys, collections
t = json.load(open(sys.argv[1]))
addr = {m['addr']: m for m in t['modulesp']}
own, kids = {}, {}
def scan(n, acc, cnt):
    if isinstance(n, dict):
        cnt[0] += 1
        if n.get('type') == 'CELL':
            acc.append(n.get('modp')); return
        for v in n.values():
            if isinstance(v, (list, dict)): scan(v, acc, cnt)
    elif isinstance(n, list):
        for x in n: scan(x, acc, cnt)
for m in t['modulesp']:
    acc, cnt = [], [0]; scan(m.get('stmtsp', []), acc, cnt); own[m['addr']] = cnt[0]; kids[m['addr']] = acc
sub = {}
def flat(a):
    if a in sub: return sub[a]
    s = own[a] + sum(flat(k) for k in kids[a] if k in addr); sub[a] = s; return s
top = [m for m in t['modulesp'] if m.get('level') == 1][0]['addr']
mult = collections.Counter(); 
def walk(a, k):
    mult[a] += k
    for c in kids[a]:
        if c in addr: walk(c, k)
# instance counts via DFS can explode; do counting by topological accumulation instead
inst = collections.Counter({top: 1}); order = []
seen = set()
def topo(a):
    if a in seen: return
    seen.add(a)
    for c in kids[a]:
        if c in addr: topo(c)
    order.append(a)
topo(top)
for a in reversed(order):
    for c in kids[a]:
        if c in addr: inst[c] += inst[a]
tot = sum(own[a] * inst[a] for a in order)
print(f"# top {addr[top]['name']} flattened nodes {tot} unique-module nodes {sum(own[a] for a in order)}")
rows = sorted(order, key=lambda a: -own[a] * inst[a])[:int(sys.argv[2]) if len(sys.argv) > 2 else 25]
for a in rows:
    print(f"{own[a]*inst[a]/tot*100:6.2f}% inst {inst[a]:6d} own {own[a]:9d} subtree {flat(a):10d} {addr[a]['name']}")
