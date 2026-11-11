#!/usr/bin/env python3
"""CPL-QC-2: parse a bound kit RTL (flat module of instances) into an object graph with bit widths.
usage: svgraph.py BOUND.sv [WRAPPER.sv] -> JSON {insts:{name:{mod,ports:{port:[nets..]}}}, edges:[[a,b,bits]]}
Objects: instance names; top ports as 'PORT:<name>'. Nets fanning out to >8 objects (clock/reset/tie) are dropped."""
import json, re, sys
from collections import defaultdict

src = open(sys.argv[1]).read()
src = re.sub(r'//[^\n]*', '', src)
src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
widths = {}
for m in re.finditer(r'\b(input|output|inout|wire|logic|reg)\s+(?:wire\s+|logic\s+)?(?:\[(\d+):(\d+)\]\s*)?([A-Za-z_][\w$]*(?:\s*,\s*[A-Za-z_][\w$]*)*)', src):
    w = abs(int(m.group(2)) - int(m.group(3))) + 1 if m.group(2) else 1
    for n in m.group(4).split(','):
        widths[n.strip()] = w
ports = set(re.findall(r'\b(?:input|output|inout)\s+(?:wire\s+|logic\s+)?(?:\[\d+:\d+\]\s*)?([A-Za-z_]\w*)', src))
inst_re = re.compile(r'\n\s*([A-Za-z_]\w*)\s*(#\s*\((?:[^()]|\([^()]*\))*\)\s*)?([A-Za-z_]\w*)\s*\((.*?)\)\s*;', re.S)
insts = {}
for m in inst_re.finditer(src):
    mod, name, body = m.group(1), m.group(3), m.group(4)
    if mod in ('module', 'assign', 'if', 'for', 'begin', 'always'):
        continue
    pm = {}
    for pm_ in re.finditer(r'\.(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)', body):
        expr = pm_.group(2)
        nets = []
        for t in re.finditer(r'([A-Za-z_]\w*)\s*(?:\[(\d+)(?::(\d+))?\])?', expr):
            n = t.group(1)
            if n not in widths:
                continue
            if t.group(2) is None:
                b = widths[n]
            elif t.group(3) is None:
                b = 1
            else:
                b = abs(int(t.group(2)) - int(t.group(3))) + 1
            nets.append([n, b])
        pm[pm_.group(1)] = nets
    insts[name] = {'mod': mod, 'ports': pm}
# assigns: alias nets
alias = defaultdict(set)
for m in re.finditer(r'\bassign\s+([A-Za-z_]\w*)[^=]*=\s*([^;]*);', src):
    for t in re.findall(r'[A-Za-z_]\w*', m.group(2)):
        if t in widths:
            alias[m.group(1)].add(t); alias[t].add(m.group(1))
net_objs = defaultdict(lambda: defaultdict(int))
for name, d in insts.items():
    for p, nets in d['ports'].items():
        for n, b in nets:
            net_objs[n][name + '.' + p] = max(net_objs[n][name + '.' + p], b)
for p in ports:
    net_objs[p]['PORT:' + p] = widths.get(p, 1)
# union aliases
parent = {}
def f(x):
    while parent.get(x, x) != x:
        x = parent[x]
    return x
for a, bs in alias.items():
    for b in bs:
        ra, rb = f(a), f(b)
        if ra != rb:
            parent[ra] = rb
groups = defaultdict(lambda: defaultdict(int))
for n, objs in net_objs.items():
    g = groups[f(n)]
    for o, b in objs.items():
        g[o] = max(g[o], b)
edges = defaultdict(int)
for n, objs in groups.items():
    if len({o.split('.')[0] for o in objs}) > 8 or len(objs) < 2:
        continue
    ol = sorted(objs)
    for i in range(len(ol)):
        for j in range(i + 1, len(ol)):
            if ol[i].split('.')[0] == ol[j].split('.')[0]:
                continue
            edges[(ol[i], ol[j])] += min(objs[ol[i]], objs[ol[j]])
json.dump({'insts': {k: {'mod': v['mod']} for k, v in insts.items()},
           'edges': [[a, b, w] for (a, b), w in sorted(edges.items(), key=lambda kv: -kv[1])]}, sys.stdout)
