#!/usr/bin/env python3
"""Classify every flop D pin of a mapped (yosys) ASAP7 netlist: driver kind of its D net, through <=N buffers.
pure  = D driven by a flop Q (optionally through BUF/INV cells) -> pure flop->flop hop (hold critical, no logic)
port  = D driven by an input port (through buffers)
logic = anything else. Grouped by hierarchy prefix. usage: relay_class.py netlist.v [top]"""
import re, sys, collections
txt = open(sys.argv[1]).read()
inst_re = re.compile(r'^\s*([A-Za-z0-9_]+)\s+(\\\S+|\S+)\s*\((.*?)\);', re.S | re.M)
pin_re = re.compile(r'\.(\w+)\(\s*([^()]*?)\s*\)')
drv = {}      # net -> (cell type, inst, pin)
flops = []    # (inst, type, dnet)
cells = {}
inputs = set()
for m in re.finditer(r'^\s*input\s+(?:wire\s+)?(\[[^\]]+\]\s*)?([^;]+);', txt, re.M):
    rng = m.group(1); names = [n.strip() for n in m.group(2).split(',')]
    for n in names:
        if rng:
            a, b = [int(x) for x in rng.strip()[1:-1].split(':')]
            for i in range(min(a, b), max(a, b) + 1): inputs.add(f'{n}[{i}]')
        else: inputs.add(n)
def norm(n):
    n = n.strip()
    return n[1:].strip() if n.startswith('\\') else n
for m in inst_re.finditer(txt):
    typ, inst, body = m.group(1), norm(m.group(2)), m.group(3)
    if typ in ('module', 'input', 'output', 'wire', 'assign'): continue
    pins = {p: norm(n) for p, n in pin_re.findall(body)}
    cells[inst] = (typ, pins)
    for p, n in pins.items():
        if p in ('Y', 'Q', 'QN', 'CON', 'SN', 'H', 'L'):
            drv[n] = (typ, inst, p)
    if typ.startswith(('DFF', 'DHL', 'DLL', 'SDF', 'ASYNC')) and 'D' in pins:
        flops.append((inst, typ, pins['D']))
def kind(net, depth=0):
    if net in inputs: return 'port'
    d = drv.get(net)
    if d is None: return 'const' if "'" in net else 'undriven'
    typ, inst, p = d
    if typ.startswith(('DFF', 'DHL', 'DLL', 'SDF', 'ASYNC')): return 'pure'
    if (typ.startswith('BUF') or typ.startswith('INV') or typ.startswith('HB')) and depth < 4:
        return kind(cells[inst][1].get('A', ''), depth + 1)
    return 'logic'
def grp(inst):
    s = re.sub(r'\[\d+\]', '', inst); s = re.sub(r'\$.*', '', s)
    a = s.split('.')
    return '.'.join(a[:3]) if a[0] == 'u_core' else a[0]
tot = collections.Counter(); g = collections.defaultdict(collections.Counter)
for inst, typ, dn in flops:
    k = kind(dn); tot[k] += 1; g[grp(inst)][k] += 1
print('flops', len(flops), dict(tot))
for k, c in sorted(g.items(), key=lambda kv: -sum(kv[1].values()))[:70]:
    print(f'{sum(c.values()):7d} pure {c["pure"]:6d} port {c["port"]:5d} logic {c["logic"]:6d}  {k}')
