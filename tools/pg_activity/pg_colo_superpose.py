#!/usr/bin/env python3
"""PG-ACTIVITY-4: exact superposition for PDNSim runs whose explicit loads (set_pdnsim_inst_power) are ADDED to PSM's
own STA instance power (EM-checked 10-27). Same PDN + same sources => linear network: drop(load) = drop(A) - drop(B),
A = explicit+STA run, B = STA-only run, per terminal (Instance, Terminal, Layer, X, Y). Then co-located per instance:
worst VDD drop + worst VSS bounce, same cell.
  pg_colo_superpose.py A_DIR B_DIR [--vnom 0.7] [--json OUT]"""
import argparse, csv, json, os
ap = argparse.ArgumentParser(); ap.add_argument("a"); ap.add_argument("b"); ap.add_argument("--vnom", type=float, default=0.7); ap.add_argument("--json")
a = ap.parse_args()
SKIP = ("FILLER", "TAP", "DECAP", "PHY_", "WELLTAP")
def term(p):
    d = {}
    for r in csv.DictReader(open(p)):
        d[(r["Instance"], r["Terminal"], r["Layer"], r["X location"], r["Y location"])] = float(r["Voltage"])
    return d
def per_inst(net, vdd):
    A = term(os.path.join(a.a, f"ir_{net}.csv")); B = term(os.path.join(a.b, f"ir_{net}.csv"))
    miss = sum(1 for k in A if k not in B); d, xy = {}, {}
    for k, va in A.items():
        if k not in B: continue
        v = ((B[k] - va) if vdd else (va - B[k])) * 1e3   # load-only drop / bounce
        if v > d.get(k[0], -1e9): d[k[0]] = v; xy[k[0]] = (float(k[3]), float(k[4]))
    return d, xy, miss
vd, xy, m1 = per_inst("VDD", True); vs, _, m2 = per_inst("VSS", False)
rows = sorted(((vd[n] + vs.get(n, 0.0), n) for n in vd if not n.upper().startswith(SKIP)), reverse=True)
s = [r[0] for r in rows][::-1]; w = rows[0]
out = dict(a=a.a, b=a.b, insts=len(rows), unmatched_terms=[m1, m2], colo_max_mV=round(w[0], 3), worst_cell=w[1], worst_xy=xy[w[1]],
           worst_vdd_mV=round(vd[w[1]], 3), worst_vss_mV=round(vs.get(w[1], 0), 3), p999_mV=round(s[int(.999 * len(s))], 3),
           p99_mV=round(s[int(.99 * len(s))], 3), vdd_max_mV=round(max(vd.values()), 3), vss_max_mV=round(max(vs.values()), 3))
print(json.dumps(out))
if a.json: json.dump(out, open(a.json, "w"), indent=1)
