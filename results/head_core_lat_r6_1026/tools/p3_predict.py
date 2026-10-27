#!/usr/bin/env python3
"""HEAD-CORE-LAT-R6: uf_phys3 v1 (MODEL-REFIT-3 claude/model-refit3-1026@c46af260b) prediction of a plan spec, GRT basis.
TT = arrival_max_rise (max analysis, PMAX), FF = early = min(rise, fall) of the min analysis (PMIN); per-leaf values.
Guard (COORD 10-26 18:xx): build only if TT mean 250+-9, FF mean 202.5+-10, predicted window <=14 (both corners).
usage: p3_predict.py MR3_ROOT SPEC.tcl SEG.json GEO LIBDIR [OUT.json] [MEAS_TT.tsv MEAS_FF.tsv]   PLAN MODEL, UNCHECKED"""
import hashlib, json, statistics as st, sys
from pathlib import Path
root = Path(sys.argv[1]); sys.path.insert(0, str(root / "results/model_refit3_1026/py"))
import uf_phys3 as V
from uf_phys3 import U, common
spec, seg, geo, libdir = sys.argv[2:6]
out = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != "-" else None
F = json.loads((root / "results/model_refit3_1026/uf_phys3_v1.json").read_text())
LIBS = U.load_libs(libdir)
P = V.load_plan(spec, geo, seg)
dp = V.depth(P)
o = dict(model=F["name"], basis="GRT", numbers="UNCHECKED", guard=dict(TT=[241, 259], FF=[192.5, 212.5], window=14))
ok = True
for C, kind, band in (("TT", "max", (241, 259)), ("FF", "min", (192.5, 212.5))):
    pr = V.basis_leaf(P, LIBS, C, kind, F["PMAX"] if kind == "max" else F["PMIN"])
    v = list(pr.values())
    r = dict(mean=round(st.mean(v), 2), min=round(min(v), 2), max=round(max(v), 2), window=round(max(v) - min(v), 2),
             leaves=len(v), depth=sorted({dp[k] for k in pr}))
    worst = sorted(pr.items(), key=lambda kv: kv[1])
    r["lo"] = [(k, round(x, 2)) for k, x in worst[:4]]; r["hi"] = [(k, round(x, 2)) for k, x in worst[-4:]]
    r["in_guard"] = band[0] <= r["mean"] <= band[1] and r["window"] <= 14
    ok &= r["in_guard"]
    o[C] = r
    o[C + "_leaf"] = {k: round(x, 2) for k, x in pr.items()}
    if len(sys.argv) > 8:
        m = common.parse_sinks(sys.argv[7] if C == "TT" else sys.argv[8])[0]
        b = "rise" if C == "TT" else "early"
        ks = [k for k in m if k in pr]
        mm = [m[k][b] for k in ks]
        o[C]["meas"] = dict(mean=round(st.mean(mm), 2), window=round(max(mm) - min(mm), 2), n=len(ks))
o["verdict"] = "IN_GUARD" if ok else "OUT_OF_GUARD"
o["provenance"] = dict(argv=sys.argv, sha={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16] for p in (spec, geo)})
if out:
    json.dump(o, open(out, "w"), indent=1)
print("P3", Path(spec).name, "TT %(mean).2f w%(window).2f" % o["TT"], "| FF %(mean).2f w%(window).2f" % o["FF"], o["verdict"],
      "| meas", o["TT"].get("meas"), o["FF"].get("meas"))
