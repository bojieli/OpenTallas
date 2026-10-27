"""HEAD-PLAN-PG NUMBER-CHECK (own parse, no import of infra_pg/head_pg_irsum): co-located VDD drop + VSS bounce per load
block from PDNSim ir_VDD.csv / ir_VSS.csv. Window coords from irwin.json. Bands: interior = >=450 um from every OPEN window
edge; for a window touching die x=0 the x0 edge is the real die edge (not open): band 'edge' = x<450 (die coords), 'inner' = x>=450.
usage: nc_ir.py KITDIR [--die-edge-x0]"""
import csv, json, sys
from pathlib import Path
K = Path(sys.argv[1]); edge = "--die-edge-x0" in sys.argv
m = json.loads((K / "irwin.json").read_text()); x0, y0, x1, y1 = m["window_um"]
def load(p, vdd):
    d = {}
    for r in csv.DictReader(open(p)):
        v = (0.7 - float(r["Voltage"])) * 1e3 if vdd else float(r["Voltage"]) * 1e3
        n = r["Instance"]; x = float(r["X location"]) + x0; y = float(r["Y location"]) + y0
        if n not in d or v > d[n][0]: d[n] = (v, x, y)
    return d
A = load(K / "psm" / "ir_VDD.csv", True); B = load(K / "psm" / "ir_VSS.csv", False)
assert set(A) == set(B), "block sets differ"
M = 450.0
def band(x, y):
    if y < y0 + M or y > y1 - M or x > x1 - M: return None
    if edge: return "edge" if x < x0 + M else "inner"
    return "interior" if x >= x0 + M else None
out = {}
for n in A:
    b = band(A[n][1], A[n][2])
    if b is None: continue
    s = A[n][0] + B[n][0]; o = out.setdefault(b, dict(colo=-1, n=0, vdd=-1, vss=-1))
    o["n"] += 1; o["vdd"] = max(o["vdd"], A[n][0]); o["vss"] = max(o["vss"], B[n][0])
    if s > o["colo"]: o["colo"] = s; o["at"] = [round(A[n][1]), round(A[n][2])]
for b, o in out.items():
    print(f"{K.name} {b}: colo {o['colo']:.2f} mV at {o['at']} (vdd max {o['vdd']:.2f}, vss max {o['vss']:.2f}, n {o['n']})"
          f" + 5.13 below-M7 = {o['colo'] + 5.13:.2f} mV -> {'PASS' if o['colo'] + 5.13 <= 35 else 'FAIL'} (<=35)")
print("blocks", len(A), "all-window colo max %.2f" % max(A[n][0] + B[n][0] for n in A))
