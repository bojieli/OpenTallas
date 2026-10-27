#!/usr/bin/env python3
"""MODEL-REFIT-2 gate predictor: uf_phys with the frozen fit (fit_ext.json / fit2.json, 3 builds, LOO-validated).
usage: uf_phys_predict.py SPEC.tcl ASBUILT.json GEO LIBDIR [OUT.json]
prints TT rise (max analysis) and FF early (min analysis) tap-mean mean / window, the 12.3 gate bases.  PLAN MODEL, UNCHECKED."""
import hashlib, json, statistics as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import uf_phys as U
PMAX = dict(alpha=0.2, beta=0.5, gslew=5.0, kleaf=1.2955)   # fit2.json fits.max (TT+FF arrival_max_rise)
PMIN = dict(alpha=0.2, beta=0.4, gslew=4.0, kleaf=1.2955)   # fit_ext.json fits.min (TT+FF early)
def gate(spec, asb, geo, libdir):
    LIBS = U.load_libs(libdir)
    P = U.Plan(spec, geo, json.load(open(asb))["seg_um"])
    o = {}
    for C in ("TT", "FF"):
        b = U.leaf_basis(P, LIBS, C, PMAX, PMIN)
        for k in ("rise", "early", "late"):
            v = list(b[k].values())
            o[f"{C}_{k}"] = dict(mean=round(st.mean(v), 2), min=round(min(v), 2), max=round(max(v), 2), window=round(max(v) - min(v), 2))
        o[f"{C}_leaf"] = {k: {kk: round(vv[k], 2) for kk, vv in b.items()} for k in b["rise"]}
    return o
if __name__ == "__main__":
    spec, asb, geo, libdir = sys.argv[1:5]
    o = gate(spec, asb, geo, libdir)
    o["params"] = dict(max=PMAX, min=PMIN)
    o["provenance"] = dict(argv=sys.argv, sha={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16] for p in (spec, asb, geo, __file__, U.__file__)})
    if len(sys.argv) > 5:
        json.dump(o, open(sys.argv[5], "w"), indent=1)
    print("PRED TT rise %(mean).2f w%(window).2f" % o["TT_rise"], "| FF early %(mean).2f w%(window).2f" % o["FF_early"], "| TT late %(mean).2f w%(window).2f" % o["TT_late"])
