#!/usr/bin/env python3
"""QC-SU-F4B: uf_phys3 v1 (OT_PHYS_FIT, GRT basis) via phys_gate.predict_file on the F4A placed plan; --layers m56 swaps
the tree-leg RC to the M5/M6 average (F4B layer plan).  seg = Manhattan (one-L legs).  Prints the pre-build guard band
(COORD: TT 250+-9, FF 202.5+-10, window <= 14) and per-island leaf counts.  PLAN MODEL, UNCHECKED."""
import json, sys, collections, tempfile
from pathlib import Path
R = Path(sys.argv[1]); spec, geo, libdir, out, lay = sys.argv[2:7]
sys.path.insert(0, str(R / "results/qc_su_prog_l1_1026"))
import phys_gate as G
U = G.U
if lay == "m56":
    U.R45 = 0.5 * (1.89935e-2 + 1.18796e-2) * U.KR; U.C45 = 0.5 * (1.64264e-1 + 1.87426e-1) * U.KC
P0 = U.Plan(spec, geo, {})
seg = {n: U.man(v["xy"], P0.nodes[v["par"]]["xy"]) for n, v in P0.nodes.items() if v["par"]}
tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(dict(seg_um=seg), tf); tf.close()
o = G.predict_file(spec, tf.name, geo, libdir)
isl = collections.Counter(); sinks = collections.Counter()
for n, v in P0.nodes.items():
    if v["kind"] == "leaf":
        q = n[:2]; isl[q] += 1; sinks[q] += len(v["sinks"])
t, f = o["TT_rise"], o["FF_early"]
band = abs(t["mean"] - 250) <= 9 and abs(f["mean"] - 202.5) <= 10 and t["window"] <= 14 and f["window"] <= 14
o["coord_band_1026"] = dict(TT="250+-9", FF="202.5+-10", window=14, inside=band)
o["island_leaves"] = dict(isl); o["island_sinks"] = dict(sinks); o["layers"] = lay
for k in [k for k in o if k.endswith("_leaf")]: o.pop(k)
json.dump(o, open(out, "w"), indent=1, default=str)
print("%s TT %.2f w%.2f | FF early %.2f w%.2f | band %s | leaves/island %s | sinks/island %s | fit %s" % (
    lay, t["mean"], t["window"], f["mean"], f["window"], "IN" if band else "OUT", dict(sorted(isl.items())), dict(sorted(sinks.items())), o["params"]["fit"][:30]))
