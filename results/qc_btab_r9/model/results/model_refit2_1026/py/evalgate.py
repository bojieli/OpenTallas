import json, sys, statistics as st
sys.path.insert(0, sys.path[0])
from common import *
from decomp import BUILDS, D
import os
LIBDIR = os.environ.get("OT_INVBUF_LIBDIR", "/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor")  # invbuf_tt/ff.lib
import uf_phys_predict as G
for b, (sp, aj, geo) in BUILDS.items():
    o = G.gate(sp, aj, geo, LIBDIR)
    for C, k in (("TT", "rise"), ("FF", "early"), ("TT", "late")):
        m = parse_sinks(D + b + f"/meas_ck_{C}.tsv")[0]; v = [x[k] for x in m.values()]
        print(b, C, k, "meas %.2f w%.2f" % (st.mean(v), max(v) - min(v)), "pred %(mean).2f w%(window).2f" % o[f"{C}_{k}"])
