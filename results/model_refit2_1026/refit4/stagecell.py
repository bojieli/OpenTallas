#!/usr/bin/env python3
"""QC-SU-PROG-L2: measured vs uf_phys per-STAGE delay (parent A -> child A, TT rise) grouped by DRIVER cell, 4 builds. UNCHECKED.
usage: stagecell.py LIBDIR 'alpha=..,beta=..,gslew=..,kleaf=..'"""
import json, sys, statistics as st
sys.path.insert(0, sys.path[0] + "/../py")
from common import *
import uf_phys as U
from decomp import BUILDS, D
LIBS = U.load_libs(sys.argv[1]); kw = eval("dict(" + sys.argv[2] + ")")
for b, (sp, aj, geo) in BUILDS.items():
    P = U.Plan(sp, geo, json.load(open(aj))["seg_um"])
    stg = parse_stage(D + b + "/meas_stage_TT.tsv")
    _, arr = U.predict(P, LIBS, "TT", edge="rise", **kw)
    def inst(n): return {"root": "ot_ms_root"}.get(n) or (f"ot_ms_{n}_tap" if P.nodes[n]["kind"] == "leaf" else (f"ot_ms_{n}_leaf" if P.nodes[n]["kind"] == "macro" else f"ot_ms_{n}_nd"))
    cat = {}
    for n, v in P.nodes.items():
        if v["par"] is None or v["kind"] == "macro": continue
        p = v["par"]
        try: mA_c, mA_p = stg[(inst(n), "A")]["ar"], stg[(inst(p), "A")]["ar"]
        except KeyError: continue
        e = (mA_c - mA_p) - (arr[n][0] - arr[p][0])     # meas - pred
        cat.setdefault(P.nodes[p]["cell"].split("_")[0], []).append(e)
    print(b, " | ".join("%s n%d %+.2f (sd %.2f)" % (k, len(x), st.mean(x), st.pstdev(x)) for k, x in sorted(cat.items())))
    # leaf part (tap A -> sink CK mean) and path part (root -> tap A)
    m = parse_sinks(D + b + "/meas_ck_TT.tsv")[0]
    pr, _ = U.predict(P, LIBS, "TT", edge="rise", **kw)
    lf, pa, ns = [], [], []
    for k in m:
        tA = stg[(inst(k), "A")]["ar"]
        lf.append((m[k]["rise"] - tA) - (pr[k] - arr[k][0])); pa.append(tA - arr[k][0])
        n, c = k, 0
        while n != "root": n = P.nodes[n]["par"]; c += 1
        ns.append(c)
    print("   leaf-part %+.2f (sd %.2f) | root->tap A %+.2f (sd %.2f) | stages/path mean %.1f" % (st.mean(lf), st.pstdev(lf), st.mean(pa), st.pstdev(pa), st.mean(ns)))
