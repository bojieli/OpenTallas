#!/usr/bin/env python3
"""MODEL-REFIT-3 GRT->RCX transfer (T8 per-via + T9 per-um/per-stage), fitted on STAGE increments, validated per leaf.

Stage increment of a clock buffer k fed by net n (driver d):  D_k = (A_rcx(k) - A_rcx(d)) - (A_grt(k) - A_grt(d)),
A = TT rise arrival at the buffer input (nodes_{grt,rcx}_TT.tsv, routed DB, same instances).  Linear physical form
    D_k = C0 + CV * n_via(n) + CL * L_plan(n)
n_via = routed vias of the tree net (vias_rcx.tsv; for a new plan = the layer/route plan's count), L_plan = plan net
length (uf_phys Steiner edges).  Leaf nets (sinks) get D_leaf = CLEAF0 + CLEAFL * MST (pin-access vias excluded).
Fit: least squares on the F4A builds that have node dumps; validation: (a) leave-one-build-out vmr<->rp1 on per-leaf
RCX-GRT shift, (b) btab_r5 (never fitted) per-leaf: meas_GRT + predicted shift vs meas_RCX.  FF: the TT shift times one
fitted ratio RFF (leaf level).  usage: transfer.py OUT.json   UNCHECKED."""
import hashlib, json, statistics as st, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, sys.path[0])
import uf_phys3 as V
import points as PT
from uf_phys3 import U, common

FIT_B = ["vmr_f4a", "rp1_f4a"]
TEST_B = ["btab_r5"]


def nodes(f):
    d = {}
    for ln in open(f):
        x = ln.rstrip("\n").split("\t")
        if len(x) >= 6:
            d[x[0]] = dict(arr=float(x[4]), net=x[5])
    return d


def vias(f):
    return {ln.split("\t")[0]: int(ln.split("\t")[1]) for ln in open(f) if not ln.startswith("#")}


def plan_len(P):
    return {V.net_name(drv): sum(e[2] for e in P.nets[drv]["edges"]) for drv in P.nets}


def inst(n):
    return "ot_ms_root" if n == "root" else f"ot_ms_{n}_nd"


DATA = {}
for b in FIT_B + TEST_B:
    p = PT.POINTS[b]
    P = V.load_plan(p["spec"], p["geo"], p["seg"])
    DATA[b] = dict(P=P, via=vias(p["vias_rcx"]), L=plan_len(P),
                   g={C: common.parse_sinks(p["grt"][i])[0] for i, C in enumerate(("TT", "FF"))},
                   r={C: common.parse_sinks(p["rcx"][i])[0] for i, C in enumerate(("TT", "FF"))})
    pd = Path(p["spec"]).parent
    if (pd / "nodes_grt_TT.tsv").exists():
        DATA[b]["ng"], DATA[b]["nr"] = nodes(pd / "nodes_grt_TT.tsv"), nodes(pd / "nodes_rcx_TT.tsv")


def stage_rows(b):
    D = DATA[b]; P = D["P"]; rows = []
    for k, v in P.nodes.items():
        if k == "root" or v["kind"] == "macro":
            continue
        a, d = inst(k), inst(v["par"])
        if a not in D["ng"] or d not in D["ng"] or a not in D["nr"] or d not in D["nr"]:
            continue
        net = V.net_name(v["par"])
        inc = (D["nr"][a]["arr"] - D["nr"][d]["arr"]) - (D["ng"][a]["arr"] - D["ng"][d]["arr"])
        rows.append((inc, D["via"].get(net, 0), D["L"][net]))
    return rows


def leaf_rows(b):
    """leaf-net shift = sink-mean RCX-GRT shift minus the leaf buffer's input shift (TT rise)."""
    D = DATA[b]; P = D["P"]; rows = []
    for k in D["g"]["TT"]:
        a = inst(k)
        if a not in D["ng"] or a not in D["nr"] or k not in D["r"]["TT"]:
            continue
        s = (D["r"]["TT"][k]["rise"] - D["g"]["TT"][k]["rise"]) - (D["nr"][a]["arr"] - D["ng"][a]["arr"])
        rows.append((s, U.mst_len([P.nodes[k]["xy"]] + P.nodes[k]["sinks"])))
    return rows


def fit(bs):
    S = [r for b in bs for r in stage_rows(b)]
    A = np.c_[np.ones(len(S)), [r[1] for r in S], [r[2] for r in S]]
    c, *_ = np.linalg.lstsq(A, np.array([r[0] for r in S]), rcond=None)
    Lr = [r for b in bs for r in leaf_rows(b)]
    A2 = np.c_[np.ones(len(Lr)), [r[1] for r in Lr]]
    c2, *_ = np.linalg.lstsq(A2, np.array([r[0] for r in Lr]), rcond=None)
    sres = np.array([r[0] for r in S]) - A @ c
    m = dict(C0=float(c[0]), CV=float(c[1]), CL=float(c[2]), CLEAF0=float(c2[0]), CLEAFL=float(c2[1]),
             n_stage=len(S), n_leaf=len(Lr), stage_resid_sd=float(sres.std()), stage_resid_max=float(np.abs(sres).max()))
    # FF ratio at leaf level
    num = den = 0.0
    for b in bs:
        sh = shift_pred(b, m)
        for k, v in sh.items():
            ff = DATA[b]["r"]["FF"][k]["early"] - DATA[b]["g"]["FF"][k]["early"]
            num += ff * v; den += v * v
    m["RFF"] = num / den if den else 1.0
    return m


def shift_pred(b, m, vias_override=None):
    D = DATA[b]; P = D["P"]; via = vias_override or D["via"]
    sh = {"root": 0.0}
    order = ["root"]; i = 0
    while i < len(order):
        for c in P.kids.get(order[i], []):
            net = V.net_name(order[i])
            sh[c] = sh[order[i]] + m["C0"] + m["CV"] * via.get(net, 0) + m["CL"] * D["L"][net]
            order.append(c)
        i += 1
    return {k: sh[k] + m["CLEAF0"] + m["CLEAFL"] * U.mst_len([P.nodes[k]["xy"]] + P.nodes[k]["sinks"])
            for k in D["g"]["TT"] if k in sh}


def test(b, m):
    o = {}
    sh = shift_pred(b, m)
    for C, basis, f in (("TT", "rise", 1.0), ("FF", "early", m["RFF"])):
        g, r = DATA[b]["g"][C], DATA[b]["r"][C]
        ks = [k for k in sh if k in r]
        e = [r[k][basis] - (g[k][basis] + f * sh[k]) for k in ks]
        e0 = [r[k][basis] - g[k][basis] for k in ks]
        pr = [g[k][basis] + f * sh[k] for k in ks]; ms = [r[k][basis] for k in ks]
        o[C] = dict(err_mean=round(st.mean(e), 2), err_sd=round(st.pstdev(e), 2), err_max=round(max(abs(x) for x in e), 2),
                    noterm_mean=round(st.mean(e0), 2), noterm_max=round(max(abs(x) for x in e0), 2),
                    rcx_meas_mean=round(st.mean(ms), 2), rcx_meas_window=round(max(ms) - min(ms), 2),
                    rcx_pred_mean=round(st.mean(pr), 2), rcx_pred_window=round(max(pr) - min(pr), 2))
    return o


if __name__ == "__main__":
    out = dict(scope=__doc__.splitlines()[0], fit_builds=FIT_B, test_builds=TEST_B)
    out["fit"] = fit(FIT_B)
    out["loo"] = {h: dict(model=fit([b for b in FIT_B if b != h]), test=None) for h in FIT_B}
    for h in FIT_B:
        out["loo"][h]["test"] = test(h, out["loo"][h]["model"])
    out["in_sample"] = {b: test(b, out["fit"]) for b in FIT_B}
    out["holdout"] = {b: test(b, out["fit"]) for b in TEST_B}
    out["holdout_by_single_f4a"] = {f"{h}->{b}": test(b, out["loo"][[x for x in FIT_B if x != h][0]]["model"]) for h in FIT_B for b in TEST_B}
    fl = [__file__, V.__file__] + [x for b in FIT_B + TEST_B for x in list(PT.POINTS[b]["grt"]) + list(PT.POINTS[b]["rcx"]) + [PT.POINTS[b]["vias_rcx"]]]
    fl += [str(Path(PT.POINTS[b]["spec"]).parent / f) for b in FIT_B for f in ("nodes_grt_TT.tsv", "nodes_rcx_TT.tsv")]
    out["provenance"] = dict(argv=sys.argv, sha256={str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in fl})
    json.dump(out, open(sys.argv[1], "w"), indent=1)
    print(json.dumps(dict(fit=out["fit"], loo={h: dict(model={k: round(v, 4) for k, v in x["model"].items()}, test=x["test"]) for h, x in out["loo"].items()},
                          holdout=out["holdout"], single=out["holdout_by_single_f4a"]), indent=0))
