#!/usr/bin/env python3
"""S81-CORE-LAT-R9 step 0: check the R8 plan-record -> uf_phys3 adapter (core_lat_r8_1026/l0r_r8_uf3.py) against
measured calibration builds.  Each POINT's as-built mscts spec is written as a plan RECORD (nodes_xy, leaf_sinks,
macro stages copied from the native Plan (adapter has no macro kind; macro taps are not in the leaf compare); wire_paths: one 2-pin segment per single-child driver = its seg_um; multi-child drivers have no wire path -> adapter
entry/fan branch, Manhattan star, no detour), run through the adapter's PlanFromRecord + predict(), and compared with
(a) the native uf_phys3 Plan (spec -> Steiner x detour) and (b) the measured GRT meas_ck per leaf.
usage: adapter_check.py LIBDIR FIT OUT.json [points...]   PLAN MODEL vs measured, UNCHECKED."""
import json, statistics as st, sys, tempfile, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "core_lat_r8_1026"))
sys.path.insert(0, str(HERE.parents[0] / "model_refit3_1026" / "py"))
import l0r_r8_uf3 as A
import uf_phys3 as V, points as PT
from uf_phys3 import U, common

def record_from_point(p):
    S = common.parse_spec(p["spec"])
    P = V.load_plan(p["spec"], p["geo"], p["seg"])
    nodes = [["root", None, list(S["root"]), "BUFx24_ASAP7_75t_R", "entry"]]
    for n, v in S["tree"].items():
        nodes.append([n, v["par"], list(v["xy"]), v["cell"], "branch"])
    for n, v in S["leaves"].items():
        nodes.append([n, v["par"], list(v["xy"]), v["cell"], "leaf"])
    ls = {n: ["%s/%s" % r for r in v["regs"]] for n, v in S["leaves"].items()}
    for n, v in P.nodes.items():          # macro stages: node + parent net via the adapter; the stage itself = native
        if v["kind"] == "macro":
            nodes.append([n, v["par"], list(v["xy"]), v["cell"], "leaf"]); ls[n] = []
    wp = []
    for d, ch in P.kids.items():
        if len(ch) == 1:
            wp.append(dict(edge=d, segs=[P._seglen(ch[0])], paths=[[list(P.nodes[d]["xy"]), list(P.nodes[ch[0]]["xy"])]]))
    return dict(name=p["spec"], nodes_xy=nodes, leaf_sinks=ls, wire_paths=wp), P

def stats(pred, meas, b):
    ks = [k for k in meas if k in pred]
    r = [pred[k] - meas[k][b] for k in ks]
    mm = [meas[k][b] for k in ks]; pp = [pred[k] for k in ks]
    return dict(n=len(ks), meas_mean=round(st.mean(mm), 2), meas_w=round(max(mm) - min(mm), 2),
                pred_mean=round(st.mean(pp), 2), pred_w=round(max(pp) - min(pp), 2),
                mean_err=round(st.mean(r), 2), maxabs=round(max(abs(x) for x in r), 2),
                win_err=round((max(pp) - min(pp)) - (max(mm) - min(mm)), 2))

def main():
    libdir, fit, out = sys.argv[1:4]
    names = sys.argv[4:] or list(PT.POINTS)
    F = json.load(open(fit)); pmax, pmin = dict(F["PMAX"]), dict(F["PMIN"])
    L = None
    res = {}
    for nm in names:
        p = PT.POINTS[nm]
        rec, P = record_from_point(p)
        for c in {v["cell"] for v in P.nodes.values()}:
            if c not in U.SIZES:
                U.SIZES.append(c)
        if L is None:
            L = U.load_libs(libdir)
        if rec is None:
            res[nm] = "skip: macros "; print(nm, res[nm]); continue
        geo = p["geo"] if Path(p["geo"]).exists() else p["geo"] + ".gz"
        AP = A.PlanFromRecord(rec, geo)
        for n, v in P.nodes.items():
            if v["kind"] == "macro":
                AP.nodes[n] = dict(v)
        mt = common.parse_sinks(p["grt"][0])[0]; mf = common.parse_sinks(p["grt"][1])[0]
        o = {}
        for tag, plan in (("adapter", AP), ("native", P)):
            tt = V.basis_leaf(plan, L, "TT", "max", pmax)
            ff = V.basis_leaf(plan, L, "FF", "min", pmin)
            o[tag] = dict(TT=stats(tt, mt, "rise"), FF=stats(ff, mf, "early"))
        nmulti = sum(1 for d, ch in P.kids.items() if len(ch) > 1)
        o["multi_child_nets"] = nmulti; o["nets"] = len(P.kids)
        res[nm] = o
        print(nm, "nets", len(P.kids), "multi", nmulti)
        for tag in ("adapter", "native"):
            for C in ("TT", "FF"):
                s = o[tag][C]
                print("  %-7s %s meas %.2f w%.2f pred %.2f w%.2f err mean %+.2f max|%.2f| win %+.2f" % (tag, C, s["meas_mean"], s["meas_w"], s["pred_mean"], s["pred_w"], s["mean_err"], s["maxabs"], s["win_err"]))
    Path(out).write_text(json.dumps(dict(scope="adapter check vs measured GRT, PLAN MODEL, UNCHECKED", fit=F["name"], points=res), indent=1))

main()
