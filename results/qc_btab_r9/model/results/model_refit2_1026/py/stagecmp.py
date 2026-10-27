import json, sys, statistics as st
sys.path.insert(0, sys.path[0])
from common import *
import uf_phys as U
from decomp import BUILDS, D
import os
LIBDIR = os.environ.get("OT_INVBUF_LIBDIR", "/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor")  # invbuf_tt/ff.lib
LIBS = U.load_libs(LIBDIR)
kw = eval("dict(" + sys.argv[1] + ")")
for b, (sp, aj, geo) in BUILDS.items():
    P = U.Plan(sp, geo, json.load(open(aj))["seg_um"])
    stg = parse_stage(D + b + "/meas_stage_TT.tsv")
    _, arr = U.predict(P, LIBS, "TT", edge="rise", **kw)
    def inst(n): return {"root": "ot_ms_root"}.get(n) or (f"ot_ms_{n}_tap" if P.nodes[n]["kind"] == "leaf" else (f"ot_ms_{n}_leaf" if P.nodes[n]["kind"] == "macro" else f"ot_ms_{n}_nd"))
    # stage = parent output -> child input (wire), parent A->Y (cell); compare to model via arrival differences
    cat = {}
    for n, v in P.nodes.items():
        if v["par"] is None or v["kind"] == "macro": continue
        p = v["par"]; fo = len(P.kids[p])
        mA_c, mA_p = stg[(inst(n), "A")]["ar"], stg[(inst(p), "A")]["ar"]
        e_stage = (arr[n][0] - arr[p][0]) - (mA_c - mA_p)
        es = arr[n][1] - stg[(inst(n), "A")]["sr"]
        k = ("fo1" if fo == 1 else "foN") + ("_root" if p == "root" else "")
        L = P.seg.get(n, 0)
        cat.setdefault(k, []).append((e_stage, es, L))
    print(b, " ".join("%s n%d dly%+.2f slew%+.1f L%.0f" % (k, len(v), st.mean(x[0] for x in v), st.mean(x[1] for x in v), st.mean(x[2] for x in v)) for k, v in sorted(cat.items())))
