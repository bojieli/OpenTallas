import json, sys
sys.path.insert(0, sys.path[0])
from common import *
import uf_phys as U
from decomp import BUILDS, D
import os
LIBDIR = os.environ.get("OT_INVBUF_LIBDIR", "/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor")  # invbuf_tt/ff.lib
LIBS = U.load_libs(LIBDIR)
for b, (sp, aj, geo) in BUILDS.items():
    P = U.Plan(sp, geo, json.load(open(aj))["seg_um"]); M = parse_sinks(D + b + "/meas_ck_TT.tsv")[0]
    stg = parse_stage(D + b + "/meas_stage_TT.tsv")
    pr, arr = U.predict(P, LIBS, "TT", edge="rise", alpha=0, beta=0.7, gslew=3.0, kleaf=1.2955)
    e = sorted(((M[k]["rise"] - pr[k], k) for k in M))
    for x, k in e[:3] + e[-2:]:
        # path breakdown: tap input arrival error, leaf-stage error
        a = stg[(f"ot_ms_{k}_tap", "A")]["ar"]
        print(b, k, "err %.1f" % x, "tapA err %.1f" % (a - arr[k][0]), "leafstage err %.1f" % ((M[k]["rise"] - a) - (pr[k] - arr[k][0])), "n", len(P.nodes[k]["sinks"]), "xy", P.nodes[k]["xy"], "par", P.nodes[k]["par"])
