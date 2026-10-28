#!/usr/bin/env python3
"""QC-PG-MAP combine: exact linear superposition of class PDNSim solves (same window kit except loads).
total_net(node) = sum_c d_c * V_c(node); co-located per load block = max_nodes VDD drop + max_nodes VSS bounce
(as pg_act5 coloc.py), canonical interior = block centre >= keepoff from the open window edges.
usage: combine.py OUT.json KEEPOFF CLASS=psm_dir:density ...  [--eval x0,y0,x1,y1 window-local]"""
import csv, re, sys, json
from collections import defaultdict
out, ko = sys.argv[1], float(sys.argv[2]); args = sys.argv[3:]
ER = None
if "--eval" in args:
    i = args.index("--eval"); ER = [float(v) for v in args[i + 1].split(",")]; args = args[:i] + args[i + 2:]
runs = []
for a in args:
    c, rest = a.split("="); d, dens = rest.rsplit(":", 1); runs.append((c, d, float(dens)))
node = {"VDD": defaultdict(float), "VSS": defaultdict(float)}
for c, d, dens in runs:
    for net in ("VDD", "VSS"):
        for r in csv.DictReader(open(f"{d}/ir_{net}.csv")):
            v = float(r["Voltage"]); mv = (v if net == "VSS" else 0.7 - v) * 1e3
            node[net][(r["Instance"], r["Layer"], r["X location"], r["Y location"])] += dens * mv
blk = {net: defaultdict(lambda: -1e9) for net in node}
for net in node:
    for (inst, *_), v in node[net].items(): blk[net][inst] = max(blk[net][inst], v)
d0 = runs[0][1]
t = open(d0 + "/psm.tcl").read()
pl = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(r"^ot_pl (\S+) (\S+) (\S+)", t, re.M)}
sz = float(re.search(r"SIZE (\S+) BY", open(d0 + "/irblk.lef").read())[1])
W = max(x for x, y in pl.values()) + sz; H = max(y for x, y in pl.values()) + sz
res = []
for k, (x, y) in pl.items():
    if k not in blk["VDD"] or k not in blk["VSS"]: continue
    cx, cy = x + sz / 2, y + sz / 2
    inter = (ER[0] <= cx <= ER[2] and ER[1] <= cy <= ER[3]) if ER else (ko <= cx <= W - ko and ko <= cy <= H - ko)
    res.append((blk["VDD"][k] + blk["VSS"][k], k, cx, cy, inter, blk["VDD"][k], blk["VSS"][k]))
res.sort(reverse=True); I = [r for r in res if r[4]]
o = dict(runs=[dict(cls=c, dir=d, w_mm2=dens) for c, d, dens in runs], blocks=len(res), interior=len(I),
         interior_worst=[round(v, 3) if isinstance(v, float) else v for v in (I[0][:4] + I[0][5:])],
         all_worst=[round(v, 3) if isinstance(v, float) else v for v in (res[0][:4] + res[0][5:])])
json.dump(o, open(out, "w"), indent=1); print(json.dumps(o))
