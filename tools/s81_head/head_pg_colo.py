#!/usr/bin/env python3
"""co-located effective-supply loss per instance = max VDD drop + max VSS bounce over that instance's terminals.
usage: h5_colo.py KIT... (window kits: region split like h5_irsum) | h5_colo.py --slice DIR (ir_VDD.csv/ir_VSS.csv)"""
import csv, json, sys
from pathlib import Path
E = 450.0
def per_inst(p, vdd):
    d, xy = {}, {}
    for r in csv.DictReader(open(p)):
        v = (0.7 - float(r["Voltage"]) if vdd else float(r["Voltage"])) * 1e3
        n = r["Instance"]
        if v > d.get(n, -1): d[n] = v; xy[n] = (float(r["X location"]), float(r["Y location"]))
    return d, xy
if sys.argv[1] == "--slice":
    k = Path(sys.argv[2]); a, _ = per_inst(k / "ir_VDD.csv", True); b, _ = per_inst(k / "ir_VSS.csv", False)
    s = sorted(a[n] + b.get(n, 0) for n in a)
    print(f"slice {k}: insts {len(s)} colocated VDD+VSS max {s[-1]:.2f} p99.9 {s[int(.999*len(s))]:.2f} p99 {s[int(.99*len(s))]:.2f}; VDD max {max(a.values()):.2f} VSS max {max(b.values()):.2f}")
    sys.exit()
for k in map(Path, sys.argv[1:]):
    m = json.loads((k / "irwin.json").read_text()); x0, y0, x1, y1 = m["window_um"]; W, H = x1 - x0, y1 - y0
    a, xy = per_inst(k / "psm" / "ir_VDD.csv", True); b, _ = per_inst(k / "psm" / "ir_VSS.csv", False)
    rows = [(xy[n][0], xy[n][1], a[n] + b.get(n, 0.0), n) for n in a]
    if "edgeW" in m["window"]:
        sel = [r for r in rows if min(r[1], H - r[1], W - r[0]) >= E]
        out = {"die_edge_band": max(sel, key=lambda r: r[2] if r[0] < E else -1), "inner": max(sel, key=lambda r: r[2] if r[0] >= E else -1)}
    else:
        out = {"interior": max((r for r in rows if min(r[0], r[1], W - r[0], H - r[1]) >= E), key=lambda r: r[2])}
    print(k.name, " | ".join(f"{key} colocated {r[2]:.2f} mV at {r[3]} ({r[0] + x0:.0f},{r[1] + y0:.0f})" for key, r in out.items()))
