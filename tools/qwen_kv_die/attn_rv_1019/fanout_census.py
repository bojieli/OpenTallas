#!/usr/bin/env python3
"""KV-ATTN2 10-19: BUF/INV-transparent fan-out census of a synthesized ASAP7 netlist (yosys 1_2_yosys.v).
For every non-buffer driver (cell output or input port): terminal loads reached through BUF/INV/HB cells, split into
data pins / RESETN-SETN pins (clock pins excluded).  Prints the top N and every driver over --max; JSON with --json.
  fanout_census.py NETLIST [--max 32] [--top 40] [--json OUT]"""
import argparse, json, re, sys
from collections import defaultdict
OUT_PINS = {'Y', 'QN', 'Q', 'CON', 'SN', 'H', 'L'}
CLK_PINS = {'CLK'}
RST_PINS = {'RESETN', 'SETN', 'RESET', 'SET'}
BUF_RE = re.compile(r'^(BUF|INV|HB|CKINV|CKBUF)')
ap = argparse.ArgumentParser(); ap.add_argument('netlist'); ap.add_argument('--max', type=int, default=32)
ap.add_argument('--top', type=int, default=40); ap.add_argument('--json')
a = ap.parse_args()
txt = open(a.netlist).read()
inst_re = re.compile(r'^\s*([A-Za-z0-9_]+)\s+(\\\S+|[A-Za-z_][\w$]*)\s*\((.*?)\);', re.S | re.M)
pin_re = re.compile(r'\.(\w+)\s*\(\s*([^()]*?)\s*\)')
cells = []
drv = {}; loads = defaultdict(list)
for m in inst_re.finditer(txt):
    typ, name, body = m.group(1), m.group(2), m.group(3)
    if typ in ('module', 'input', 'output', 'wire', 'assign'):
        continue
    ci = len(cells); cells.append((typ, name))
    for p, n in pin_re.findall(body):
        n = n.strip()
        if not n or n.startswith("1'b") or n.startswith("1'h"):
            continue
        if p in OUT_PINS:
            drv[n] = (ci, p)
        else:
            loads[n].append((ci, p))
ports_in = set()
for m in re.finditer(r'^\s*input\s+(?:\[(\d+):(\d+)\]\s*)?(\\\S+|\w+)\s*;', txt, re.M):
    hi, lo, nm = m.groups()
    if hi is None: ports_in.add(nm)
    else:
        for i in range(min(int(hi), int(lo)), max(int(hi), int(lo)) + 1): ports_in.add(f'{nm}[{i}]')
outs = defaultdict(list)
for ci, (typ, name) in enumerate(cells):
    pass
# cell outputs by cell
cell_out = defaultdict(list)
for n, (ci, p) in drv.items():
    cell_out[ci].append(n)
def terminals(net):
    data = rst = 0; seen = {net}; st = [net]
    while st:
        y = st.pop()
        for ci, p in loads.get(y, ()):
            if BUF_RE.match(cells[ci][0]):
                for z in cell_out[ci]:
                    if z not in seen: seen.add(z); st.append(z)
                continue
            if p in CLK_PINS: continue
            if p in RST_PINS: rst += 1
            else: data += 1
    return data, rst
rows = []
roots = [n for n, (ci, p) in drv.items() if not BUF_RE.match(cells[ci][0])] + sorted(ports_in)
for n in roots:
    d, r = terminals(n)
    who = cells[drv[n][0]] if n in drv else ('PORT', n)
    rows.append(dict(net=n, driver=f'{who[1]} ({who[0]})', data=d, reset=r, total=d + r))
rows.sort(key=lambda x: -x['total'])
over = [x for x in rows if x['total'] > a.max]
print(f'FANOUT_CENSUS cells={len(cells)} drivers={len(rows)} max_total={rows[0]["total"] if rows else 0} over_{a.max}={len(over)}')
for x in rows[:a.top]:
    print(f"{x['total']:6d} data {x['data']:6d} reset {x['reset']:5d}  {x['net']}  <- {x['driver']}")
if a.json:
    json.dump(dict(max=a.max, cells=len(cells), over=over, top=rows[:200]), open(a.json, 'w'), indent=1)
