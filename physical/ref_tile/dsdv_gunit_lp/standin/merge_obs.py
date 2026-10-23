#!/usr/bin/env python3
"""stand-in LEF = exact abstract (EXACT) with implant OBS (RVTN/RVTP) -> one outline rect, M1/M2 OBS -> one bbox rect
(same form as the PL-GUNIT 10-18 stand-ins); M3+ OBS exact.  usage: merge_obs.py EXACT.lef OUT.lef"""
import re, sys
t = open(sys.argv[1]).read()
m = re.search(r"\n(\s*)OBS\s*\n(.*?)\n\s*END\s*\n", t, re.S)
size = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
W, H = size.group(1), size.group(2)
layers, cur = {}, None
order = []
for ln in m.group(2).splitlines():
    s = ln.strip()
    if s.startswith("LAYER"):
        cur = s.split()[1]
        if cur not in layers: layers[cur] = []; order.append(cur)
    elif s.startswith("RECT"):
        layers[cur].append([float(v) for v in s.replace(";", "").split()[1:5]])
out = []
for L in order:
    rs = layers[L]
    if not rs: continue
    out.append(f"    LAYER {L} ;")
    if L in ("RVTN", "RVTP", "LVTN", "LVTP", "SLVTN", "SLVTP"):
        out.append(f"     RECT  0 0 {W} {H} ;")
    elif L in ("M1", "M2", "V1"):
        x0 = min(r[0] for r in rs); y0 = min(r[1] for r in rs); x1 = max(r[2] for r in rs); y1 = max(r[3] for r in rs)
        out.append(f"     RECT  {x0:g} {y0:g} {x1:g} {y1:g} ;")
    else:
        out += [f"     RECT  {r[0]:g} {r[1]:g} {r[2]:g} {r[3]:g} ;" for r in rs]
new = t[:m.start()] + "\n" + m.group(1) + "OBS\n" + "\n".join(out) + "\n" + m.group(1) + "END\n" + t[m.end():]
open(sys.argv[2], "w").write(new)
print("merged", {L: len(layers[L]) for L in order})
