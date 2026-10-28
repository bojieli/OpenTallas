#!/usr/bin/env python3
"""QC-PG-MAP: per-block upper (linear combo of class solves) + below-M7 of the signed core under the block.
usage: su_total.py WIN_X0 WIN_Y0 cores.json dA dF S_dir A_dir F_dir [keepoff]"""
import csv, re, sys, json
from collections import defaultdict
x0, y0 = float(sys.argv[1]), float(sys.argv[2]); cores = json.load(open(sys.argv[3]))["cores"]
dA, dF = float(sys.argv[4]), float(sys.argv[5]); dirs = dict(S=sys.argv[6], A=sys.argv[7], F=sys.argv[8])
ko = float(sys.argv[9]) if len(sys.argv) > 9 else 450.0
dens = dict(S=1.0, A=dA, F=dF)
below = {"qfd_dv_s5_su8_rst3": 6.602, "qfd_dv_s8x_prog": 5.989, "qfd_dv_s8x_vmr": 4.390, "qfd_dv_s8x_crh": 4.282}
blk = {n: defaultdict(float) for n in ("VDD", "VSS")}
for c, d in dirs.items():
    for net in blk:
        per = defaultdict(lambda: -1e9)
        for r in csv.DictReader(open(f"{d}/ir_{net}.csv")):
            v = float(r["Voltage"]); mv = (v if net == "VSS" else 0.7 - v) * 1e3; per[r["Instance"]] = max(per[r["Instance"]], mv)
        for k, v in per.items(): blk[net][k] += dens[c] * v   # one node per block (4761 rows) -> exact
t = open(dirs["S"] + "/psm.tcl").read()
pl = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(r"^ot_pl (\S+) (\S+) (\S+)", t, re.M)}
sz = float(re.search(r"SIZE (\S+) BY", open(dirs["S"] + "/irblk.lef").read())[1])
W = max(x for x, y in pl.values()) + sz
best = {}; up = []
for k, (x, y) in pl.items():
    cx, cy = x + sz / 2, y + sz / 2
    if not (ko <= cx <= W - ko and ko <= cy <= W - ko): continue
    u = blk["VDD"][k] + blk["VSS"][k]; up.append((u, k))
    gx, gy = cx + x0, cy + y0
    m = next((c["module"] for c in cores if c["rect"][0] <= gx <= c["rect"][2] and c["rect"][1] <= gy <= c["rect"][3]), None)
    if m in below:
        tot = u + below[m]
        if m not in best or tot > best[m][0]: best[m] = (round(tot, 3), round(u, 3), below[m], k)
up.sort(reverse=True)
print(json.dumps(dict(dA=dA, dF=dF, upper_interior_worst=[round(up[0][0], 3), up[0][1]], per_core_total=best)))
