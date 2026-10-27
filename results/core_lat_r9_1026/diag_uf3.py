#!/usr/bin/env python3
"""R9: per-leaf uf_phys3 TT breakdown (trunk arrival at the leaf driver input vs leaf stage) for an R8-format plan."""
import gzip, json, statistics as st, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "core_lat_r8_1026"))
import l0r_r8_uf3 as A
U, V3 = A.U, A.V3
rj, geo, libdir, fit = sys.argv[1:5]
op = gzip.open if rj.endswith(".gz") else open
rec = json.load(op(rj, "rt"))[0]
F = json.load(open(fit)); pmax = dict(F["PMAX"])
for c in sorted({n[3] for n in rec["nodes_xy"]}):
    if c not in U.SIZES: U.SIZES.append(c)
L = U.load_libs(libdir)
P = A.PlanFromRecord(rec, geo)
out, arr = V3.predict3(P, L, "TT", edge="rise", **pmax)
rows = []
for k, v in out.items():
    t0 = arr[k][0]
    rows.append((round(v, 1), k, round(t0, 1), round(v - t0, 1), len(P.nodes[k]["sinks"]), P.nodes[k]["cell"], rec["leaf_spread_um"].get(k), rec.get("leaf_mst_um", {}).get(k)))
rows.sort()
tr = [r[2] for r in rows]; lf = [r[3] for r in rows]
print("leaves", len(rows), "total w %.1f | trunk %.1f..%.1f (w %.1f) | leaf stage %.1f..%.1f (w %.1f)" % (rows[-1][0] - rows[0][0], min(tr), max(tr), max(tr) - min(tr), min(lf), max(lf), max(lf) - min(lf)))
print("min:"); [print(" ", r) for r in rows[:8]]
print("max:"); [print(" ", r) for r in rows[-10:]]
# per L1/L2 subtree trunk mean
par = {n[0]: n[1] for n in rec["nodes_xy"]}
def anc(k, d):
    ch = [k]
    while par.get(ch[-1]) is not None: ch.append(par[ch[-1]])
    ch = ch[::-1]; return ch[min(d, len(ch) - 1)]
for d in (3, 5, 7):
    g = {}
    for r in rows: g.setdefault(anc(r[1], d), []).append(r[2])
    print("depth", d, "trunk mean by subtree:", sorted((round(st.mean(v), 1), k) for k, v in g.items())[:3], "...", sorted((round(st.mean(v), 1), k) for k, v in g.items())[-3:])
