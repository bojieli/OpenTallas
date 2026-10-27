#!/usr/bin/env python3
"""R7 diagnostic: per-leaf decomposition of uf_phys3 TT arrival = upstream (leaf input) + leaf stage; MST, n, xy. UNCHECKED."""
import json, sys, statistics as st
from pathlib import Path
root = Path(sys.argv[1]); sys.path.insert(0, str(root / "results/model_refit3_1026/py"))
import uf_phys3 as V
from uf_phys3 import U
spec, seg, geo, libdir = sys.argv[2:6]
F = json.loads((root / "results/model_refit3_1026/uf_phys3_v1.json").read_text())
LIBS = U.load_libs(libdir); P = V.load_plan(spec, geo, seg)
out, arr = V.predict3(P, LIBS, "TT", edge="rise", **F["PMAX"])
rows = []
for n, t in out.items():
    v = P.nodes[n]; pts = [v["xy"]] + list(v["sinks"])
    rows.append((t, arr[n][0], t - arr[n][0], len(v["sinks"]), U.mst_len(pts), v["xy"], n))
rows.sort()
up = [r[1] for r in rows]; lf = [r[2] for r in rows]
print("TT mean %.1f w %.1f | upstream range %.1f..%.1f | leaf stage %.1f..%.1f" % (st.mean(r[0] for r in rows), rows[-1][0]-rows[0][0], min(up), max(up), min(lf), max(lf)))
for r in rows[:6] + rows[-12:]:
    print("%7.2f up %6.2f leaf %6.2f n %3d mst %6.1f xy (%.0f,%.0f) %s" % (r[0], r[1], r[2], r[3], r[4], r[5][0], r[5][1], r[6]))
