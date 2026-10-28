#!/usr/bin/env python3
"""PG-ACTIVITY-4: below-M7 slice co-location. Per instance: worst VDD drop (VDD_NOM - V) + worst VSS bounce (V) over its
terminals, same cell; reports max / p99.9 / p99 and the worst cell with location, plus VDD-only / VSS-only maxima.
FILLER/TAP/DECAP cells (no load) are excluded from the worst-cell pick.
  pg_colo_slice.py DIR [--vnom 0.7] [--json OUT]   (DIR has ir_VDD.csv, ir_VSS.csv from analyze_power_grid -voltage_file)"""
import argparse, csv, json, os
ap = argparse.ArgumentParser(); ap.add_argument("d"); ap.add_argument("--vnom", type=float, default=0.7); ap.add_argument("--json")
a = ap.parse_args()
SKIP = ("FILLER", "TAP", "DECAP", "PHY_", "WELLTAP")
def load(p, vdd):
    d, xy = {}, {}
    for r in csv.DictReader(open(p)):
        n = r["Instance"]
        v = ((a.vnom - float(r["Voltage"])) if vdd else float(r["Voltage"])) * 1e3
        if v > d.get(n, -1e9): d[n] = v; xy[n] = (float(r["X location"]), float(r["Y location"]))
    return d, xy
vd, xy = load(os.path.join(a.d, "ir_VDD.csv"), True); vs, _ = load(os.path.join(a.d, "ir_VSS.csv"), False)
rows = sorted(((vd[n] + vs.get(n, 0.0), n) for n in vd if not n.upper().startswith(SKIP)), reverse=True)
s = [r[0] for r in rows][::-1]
w = rows[0]
out = dict(dir=a.d, insts=len(rows), colo_max_mV=round(w[0], 3), worst_cell=w[1], worst_xy=xy[w[1]],
           worst_vdd_mV=round(vd[w[1]], 3), worst_vss_mV=round(vs.get(w[1], 0), 3),
           p999_mV=round(s[int(.999 * len(s))], 3), p99_mV=round(s[int(.99 * len(s))], 3),
           vdd_max_mV=round(max(vd.values()), 3), vss_max_mV=round(max(vs.values()), 3), vss_missing=sum(1 for n in vd if n not in vs))
print(json.dumps(out))
if a.json: json.dump(out, open(a.json, "w"), indent=1)
