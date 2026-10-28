#!/usr/bin/env python3
"""PG-CORECONN-3: summarise a tile PDNSim pair (volt_<tag>_VDD/VSS.rpt): worst VDD drop, worst VSS bounce, co-located
(same instance, VDD drop + VSS bounce) worst overall / at distributed core loads (pgl_*) per macro / at std cells.
  ir_summ.py DIR TAG [VDD_V]"""
import csv, json, re, sys
from collections import defaultdict
d, tag = sys.argv[1], sys.argv[2]; vdd = float(sys.argv[3]) if len(sys.argv) > 3 else 0.70
def rd(net):
    r = {}
    with open(f"{d}/volt_{tag}_{net}.rpt") as f:
        for row in csv.DictReader(f):
            v = float(row["Voltage"]); i = row["Instance"]
            dv = (vdd - v) if net == "VDD" else v
            if dv > r.get(i, (-1,))[0]: r[i] = (dv, float(row["X location"]), float(row["Y location"]))
    return r
A, B = rd("VDD"), rd("VSS")
def key(i):
    m = re.match(r"pgl_(VDD|VSS)_(.*)_\d+$", i)
    return ("core", m.group(2)) if m else ("cell", i)
# co-located: std cells by instance; cores by macro (max VDD load drop + max VSS load bounce of that macro)
cv = defaultdict(lambda: [0.0, 0.0])
for net, R in (("VDD", A), ("VSS", B)):
    for i, (dv, x, y) in R.items():
        k = key(i); j = 0 if net == "VDD" else 1
        cv[k][j] = max(cv[k][j], dv)
cells = {k: v for k, v in cv.items() if k[0] == "cell"}; cores = {k: v for k, v in cv.items() if k[0] == "core"}
wc = max(cells.items(), key=lambda kv: sum(kv[1])) if cells else None
wk = max(cores.items(), key=lambda kv: sum(kv[1])) if cores else None
out = dict(tag=tag, vdd_worst_mV=round(1e3 * max(v[0] for v in A.values()), 3), vss_worst_mV=round(1e3 * max(v[0] for v in B.values()), 3),
           cell_colo_worst=dict(inst=wc[0][1], vdd_mV=round(1e3 * wc[1][0], 3), vss_mV=round(1e3 * wc[1][1], 3), sum_mV=round(1e3 * sum(wc[1]), 3)) if wc else None,
           core_colo_worst=dict(core=wk[0][1], vdd_mV=round(1e3 * wk[1][0], 3), vss_mV=round(1e3 * wk[1][1], 3), sum_mV=round(1e3 * sum(wk[1]), 3)) if wk else None,
           n_cells=len(cells), n_cores=len(cores),
           cores_top5=sorted(((k[1], round(1e3 * sum(v), 3)) for k, v in cores.items()), key=lambda t: -t[1])[:5])
print(json.dumps(out, indent=1))
