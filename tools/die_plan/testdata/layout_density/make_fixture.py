#!/usr/bin/env python3
"""Reduce a layout_render.tcl dump.tsv to a regression fixture for check_density: every std-cell / tap-cell / filler population of
a 10-um bin collapses to ONE instance at the area-weighted centroid with the summed area (the density bins stay exact), macros,
blockages, die/core lines stay.  usage: mkfix.py DUMP.tsv OUT.tsv.gz"""
import collections, gzip, math, sys
src, out = sys.argv[1:3]
BIN = 10.0
head, macros, rest = [], [], []
core = None
acc = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0, ""])
lines = open(src).read().split("\n")
for l in lines:
    if l.startswith("C\t"):
        core = [float(v) for v in l.split("\t")[1:5]]
for l in lines:
    p = l.split("\t")
    if not p or not p[0]:
        continue
    if p[0] in "HDCLB":
        head.append(l)
    elif p[0] == "I":
        if p[4] == "1":
            macros.append(l)
            continue
        x0, y0, x1, y1 = (float(v) for v in p[6:10])
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        m = p[3]
        cls = "TAP" if m.startswith("TAP") else ("FILL" if m.startswith(("FILLER", "DECAP")) else "STD")
        k = (int((cx - core[0]) // BIN), int((cy - core[1]) // BIN), cls)
        a = (x1 - x0) * (y1 - y0)
        r = acc[k]
        r[0] += cx; r[1] += cy; r[2] += a; r[3] += 1; r[4] = {"TAP": "TAPCELL_ASAP7_75t_R", "FILL": "FILLERxp5_ASAP7_75t_R", "STD": "BUFx2_ASAP7_75t_R"}[cls]
n = len(macros)
body = []
for k, (sx, sy, a, c, m) in sorted(acc.items()):
    n += 1
    cx, cy = sx / c, sy / c
    h = math.sqrt(a) / 2
    body.append("I\t%d\tagg_%d_%d_%s_n%d\t%s\t0\t0\t%.3f\t%.3f\t%.3f\t%.3f" % (n, k[0], k[1], k[2], c, m, cx - h, cy - h, cx + h, cy + h))
hd = [l for l in head if not l.startswith("H\t")]
h0 = [l for l in head if l.startswith("H\t")][0].split("\t")
h0[2] = str(n); h0[3] = "1"
with gzip.open(out, "wt") as f:
    f.write("\n".join(["\t".join(h0)] + hd + macros + body) + "\n")
