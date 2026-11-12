#!/usr/bin/env python3
"""lefpins.py LEF : pin groups (bus base name) with count, face span, layer."""
import sys, re, collections
txt = open(sys.argv[1]).read()
sz = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt); W, H = float(sz.group(1)), float(sz.group(2))
g = collections.defaultdict(list)
for n, b in re.findall(r"PIN (\S+)(.*?)END \1", txt, re.S):
    m = re.search(r"LAYER (\S+)\s*;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", b)
    if not m: continue
    x = (float(m.group(2)) + float(m.group(4))) / 2; y = (float(m.group(3)) + float(m.group(5))) / 2
    f = "S" if y < 1 else "N" if y > H - 1 else "W" if x < 1 else "E" if x > W - 1 else "I"
    g[(re.sub(r"\[\d+\]", "", n), f, m.group(1))].append((x, y))
print("SIZE", W, H)
for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])):
    print("%-28s %s %-3s %4d x %.1f-%.1f y %.1f-%.1f" % (k[0], k[1], k[2], len(v), min(a for a, b in v), max(a for a, b in v), min(b for a, b in v), max(b for a, b in v)))
