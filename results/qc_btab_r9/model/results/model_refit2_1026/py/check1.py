import json, sys, statistics as st
sys.path.insert(0, sys.path[0])
from common import *
import uf_phys as U
from decomp import BUILDS, D
import os
LIBDIR = os.environ.get("OT_INVBUF_LIBDIR", "/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor")  # invbuf_tt/ff.lib
LIBS = U.load_libs(LIBDIR)
import os; os.environ
for b, (sp, aj, geo) in BUILDS.items():
    A = json.load(open(aj)); P = U.Plan(sp, geo, A["seg_um"])
    nets = parse_nets(D + b + "/netcap_TT.txt")
    rr = []
    for d, net in P.nets.items():
        nm = "ot_ms_root_n" if d == "root" else f"ot_ms_{d}_n"
        if len(P.kids[d]) > 1:
            Lw = sum(l for _, _, l in net["edges"]); rr.append((d, len(P.kids[d]), round(Lw*U.C45, 2), nets[nm]["cw"]))
    print(b, "multi-pin nets model cw vs meas: ratio mean %.3f min %.3f max %.3f" % (st.mean(r[3]/r[2] for r in rr), min(r[3]/r[2] for r in rr), max(r[3]/r[2] for r in rr)))
    print("  ", sorted(rr, key=lambda r: -r[3])[:5])
    tm, mac = parse_sinks(D + b + "/meas_ck_TT.tsv"); fm, _ = parse_sinks(D + b + "/meas_ck_FF.tsv")
    for C, meas, basis in (("TT", tm, "rise"), ("FF", fm, "early")):
        pr = U.leaf_basis(P, LIBS, C)[basis]
        dd = [meas[k][basis] - pr[k] for k in meas]
        print("  ", C, basis, "meas mean %.1f pred %.1f resid mean %.2f sd %.2f min %.1f max %.1f" % (st.mean(meas[k][basis] for k in meas), st.mean(pr[k] for k in meas), st.mean(dd), st.pstdev(dd), min(dd), max(dd)))
