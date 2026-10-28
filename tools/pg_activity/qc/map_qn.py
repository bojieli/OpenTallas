#!/usr/bin/env python3
"""QC-PG-3: gate-level register activity for the power annotator: every clocked cell instance NAME$_... gets the toggle
rate of the net on its QN (or Q) pin, from vcd_activity output (needs --trace-underscore for _NNN_ nets).
  map_qn.py NETLIST.v ACT_IN.txt ACT_OUT.txt"""
import re, sys
net, ain, aout = sys.argv[1:4]
A = {}
for ln in open(ain):
    k, v = ln.rsplit(" ", 1); A[k.replace("\\", "")] = float(v)
txt = open(net).read()
hit = miss = 0; out = dict(A)
for m in re.finditer(r"^\s*(\w+)\s+\\(\S+\$_\S*)\s+\((.*?)\);", txt, re.S | re.M):
    cell, inst, body = m.groups()
    if "DFF" not in cell and "DHL" not in cell and "DLL" not in cell: continue
    q = re.search(r"\.QN?\(([^)]*)\)", body)
    if not q: miss += 1; continue
    n = q.group(1).strip().lstrip("\\").strip()
    n = re.sub(r"\s+", "", n)
    key = inst.split("$_")[0]
    if n in A: out[key] = A[n]; hit += 1
    else: miss += 1
with open(aout, "w") as f:
    for k in sorted(out): f.write(f"{k} {out[k]}\n")
print(f"QN_MAP hit {hit} miss {miss}")
