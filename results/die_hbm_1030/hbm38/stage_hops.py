#!/usr/bin/env python3
"""DIE-HBM-38: per slot/hop max Manhattan length on planned targets of a G2 probe. usage: stage_hops.py PROBE_DIR [slot..]"""
import sys, re, collections
d = sys.argv[1]; only = set(sys.argv[2:])
t = open(d + "/probe.tcl").read()
pins = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(r"place_pin -pin_name \{(\S+)\} -layer \S+ -location \{([\d.]+) ([\d.]+)\}", open(d + "/io.tcl").read())}
ch = collections.defaultdict(dict)
for m in re.finditer(r"place_inst -name st_(.+?)_(\d+)_(\d+) -location \{([\d.]+) ([\d.]+)\}", t):
    ch[(m[1], int(m[2]))][int(m[3])] = (float(m[4]) + 0.54, float(m[5]) + 0.135)
agg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, None]))
for (s, b), c in ch.items():
    if only and s not in only: continue
    pts = [("in", pins.get(f"{s}_i[{b}]"))] + [(f"st{k}", c[k]) for k in sorted(c)] + [("out", pins.get(f"{s}_o[{b}]"))]
    pts = [(n, p) for n, p in pts if p]
    for (n0, a), (n1, q) in zip(pts, pts[1:]):
        h = abs(a[0] - q[0]) + abs(a[1] - q[1]); r = agg[s][f"{n0}->{n1}"]
        if h > r[0]: r[0], r[2] = h, (b, a, q)
        if h > 405: r[1] += 1
for s in sorted(agg):
    if max(v[0] for v in agg[s].values()) > 400 or only:
        print(s, {k: (round(v[0], 1), v[1], v[2]) for k, v in agg[s].items()})
