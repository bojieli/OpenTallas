#!/usr/bin/env python3
"""QC-SU-PROG-L2: per-leaf residual (meas - pred) of the 4-build refit, split by whether the leaf's root path holds a cell
below the calibrated BUFx8..x24 range (prog k5 only build with BUFx4/x6f). usage: resid4.py FIT.json LIBDIR OUT.json. UNCHECKED."""
import json, sys, statistics as st
sys.path.insert(0, sys.path[0] + "/../py")
from common import *
import uf_phys as U
from decomp import BUILDS, D
fit = json.load(open(sys.argv[1])); LIBS = U.load_libs(sys.argv[2])
SMALL = {"BUFx4_ASAP7_75t_R", "BUFx4f_ASAP7_75t_R", "BUFx5_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R"}
out = {}
for b, (sp, aj, geo) in BUILDS.items():
    P = U.Plan(sp, geo, json.load(open(aj))["seg_um"])
    pm = dict(fit["fits"]["max"]["params"], kleaf=fit["fits"]["max"]["kleaf"]); pn = dict(fit["fits"]["min"]["params"], kleaf=fit["fits"]["min"]["kleaf"])
    bas = U.leaf_basis(P, LIBS, "TT", pm, pn); basF = U.leaf_basis(P, LIBS, "FF", pm, pn)
    mT = parse_sinks(D + b + "/meas_ck_TT.tsv")[0]; mF = parse_sinks(D + b + "/meas_ck_FF.tsv")[0]
    def small(n):
        while n and n != "root":
            if P.nodes[n]["cell"] in SMALL: return True
            n = P.nodes[n]["par"]
        return False
    rows = {k: dict(small=small(k), TT=round(mT[k]["rise"] - bas["rise"][k], 2), FF=round(mF[k]["early"] - basF["early"][k], 2)) for k in mT}
    g = {}
    for s in (True, False):
        v = [r for r in rows.values() if r["small"] == s]
        if v:
            g["small_path" if s else "calibrated_path"] = dict(n=len(v), TT_mean=round(st.mean(r["TT"] for r in v), 2),
                TT_maxabs=round(max(abs(r["TT"]) for r in v), 2), FF_mean=round(st.mean(r["FF"] for r in v), 2),
                FF_maxabs=round(max(abs(r["FF"]) for r in v), 2))
    out[b] = dict(groups=g, leaf=rows)
    print(b, g)
json.dump(dict(fit=sys.argv[1], scope="per-leaf meas-pred, refit4 in-sample params; UNCHECKED", builds=out), open(sys.argv[3], "w"), indent=1)
