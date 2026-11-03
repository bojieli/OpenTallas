#!/usr/bin/env python3
"""NKP bit1 graph-home remap: XTX rung 0 (g_r[0]) gains the 4*G=16 round/mask select bits at [128,144), so every rung-0
bit >= 128 moves up by 16; homes kept at the same coordinates under the new name; the new select bits take the home of
their leaf's rung-0 bit 0; homes whose cell no longer exists are dropped (listed).  usage: remap_homes.py HOMES_IN NETLIST OUT DROPLIST"""
import re, sys
hin, net, out, dl = sys.argv[1:5]
t = open(net).read()
names = set(n.lstrip('\\') for _, n in re.findall(r"^\s*(\w+)\s+(\S+)\s+\(", t, re.M))
def esc(n): return n.replace('[', '\\[').replace(']', '\\]')
def raw(n): return n.replace('\\[', '[').replace('\\]', ']')
rx = re.compile(r"^(.*\.g_tx\.g_r\[0\]\.(?:di|u_tx/q))\[(\d+)\](\$.*)$")
keep, drop, seen, leaf0 = [], [], set(), {}
suff = {}
for n in names:
    m = rx.match(n)
    if m: suff[(m.group(1), int(m.group(2)))] = m.group(3)
for ln in open(hin):
    nm, x, y = ln.rstrip('\n').split('\t')[:3]
    r = raw(nm); m = rx.match(r)
    if m:
        base, i = m.group(1), int(m.group(2))
        if i == 0: leaf0[base.split('.g_tx')[0]] = (x, y)
        j = i + 16 if i >= 128 else i
        s = suff.get((base, j))
        if s: r = f"{base}[{j}]{s}"
    if r in names and r not in seen:
        keep.append(f"{esc(r)}\t{x}\t{y}"); seen.add(r)
    else:
        drop.append(nm)
add = 0
for (base, j), s in suff.items():
    if 128 <= j < 144:
        n = f"{base}[{j}]{s}"; lf = base.split('.g_tx')[0]
        if n not in seen and lf in leaf0:
            keep.append(f"{esc(n)}\t{leaf0[lf][0]}\t{leaf0[lf][1]}"); seen.add(n); add += 1
open(out, 'w').write('\n'.join(keep) + '\n'); open(dl, 'w').write('\n'.join(drop) + '\n')
print(f"REMAP homes_in={len(keep)-add+len(drop)} kept={len(keep)-add} added_sel={add} dropped={len(drop)}")
