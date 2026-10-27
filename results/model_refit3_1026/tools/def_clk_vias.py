#!/usr/bin/env python3
"""MODEL-REFIT-3: per clock net (ot_ms_*) routed via count + wire um per layer from a DEF (read-only). usage: def_clk_vias.py DEF OUT.tsv"""
import re, sys
d, out = sys.argv[1:3]
dbu = 1000.0
nets = {}; cur = None; innets = False
for ln in open(d):
    if ln.startswith("UNITS DISTANCE MICRONS"): dbu = float(ln.split()[3])
    if ln.startswith("NETS "): innets = True; continue
    if ln.startswith("END NETS"): break
    if not innets: continue
    s = ln.strip()
    if s.startswith("- "):
        nm = s.split()[1]; cur = nm if nm.startswith("ot_ms_") else None
        if cur: nets[cur] = dict(vias=0, wire={})
    if cur is None: continue
    m = re.search(r"(?:ROUTED|NEW)\s+(M\d+)\s+(.*)", s)
    if not m: continue
    lay, rest = m.groups()
    pts = re.findall(r"\(\s*(\S+)\s+(\S+)(?:\s+\S+)?\s*\)", rest)
    if len(pts) >= 2:
        x0, y0 = float(pts[0][0]), float(pts[0][1]); x1 = x0 if pts[1][0] == "*" else float(pts[1][0]); y1 = y0 if pts[1][1] == "*" else float(pts[1][1])
        nets[cur]["wire"][lay] = nets[cur]["wire"].get(lay, 0) + (abs(x1 - x0) + abs(y1 - y0)) / dbu
    toks = re.sub(r"\([^)]*\)", " ", rest).split()
    nets[cur]["vias"] += sum(1 for t in toks if not re.match(r"^(M\d+|NEW|MASK|RECT|VIRTUAL|\d+|;|\+)$", t) and not t.startswith("+"))
with open(out, "w") as f:
    f.write("#net\tvias\twire_um\t" + "\t".join(f"M{i}" for i in range(1, 10)) + "\n")
    for n, v in sorted(nets.items()):
        f.write(f"{n}\t{v['vias']}\t{sum(v['wire'].values()):.2f}\t" + "\t".join(f"{v['wire'].get(f'M{i}', 0):.2f}" for i in range(1, 10)) + "\n")
print("nets", len(nets))
