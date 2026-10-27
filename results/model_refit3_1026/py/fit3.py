#!/usr/bin/env python3
"""MODEL-REFIT-3 GRT-basis fit of uf_phys3 (T7 KSTAGE, T10 BLEAF on the uf_phys kernel) on every GRT calibration point,
leave-one-build-out AND leave-one-family-out validation.  Per-leaf mean CK arrival; max analysis fitted on TT+FF
arrival_max_rise, min analysis on TT+FF early (as MODEL-REFIT-2).  Builds weighted equally (HEAD has 512 leaves).
usage: fit3.py LIBDIR OUT.json [--no-stage] [--no-bleaf]   PLAN MODEL, UNCHECKED."""
import hashlib, itertools, json, os, statistics as st, sys
from pathlib import Path
sys.path.insert(0, sys.path[0])
import uf_phys3 as V
import points as PT
from uf_phys3 import U, common

LIBDIR = sys.argv[1]
OUT = sys.argv[2]
NOSTAGE = "--no-stage" in sys.argv
NOBLEAF = "--no-bleaf" in sys.argv
LIBS = U.load_libs(LIBDIR)
B = [b for b in PT.POINTS if not os.environ.get("OT_REFIT3_BUILDS") or b in os.environ["OT_REFIT3_BUILDS"].split(",")]
PL = {b: V.load_plan(PT.POINTS[b]["spec"], PT.POINTS[b]["geo"], PT.POINTS[b]["seg"]) for b in B}
DEP = {b: V.depth(PL[b]) for b in B}
MEAS = {b: {C: common.parse_sinks(PT.POINTS[b]["grt"][i])[0] for i, C in enumerate(("TT", "FF"))} for b in B}
FAM = {b: PT.POINTS[b]["family"] for b in B}


def kleaf_all():
    v = []
    for b in B:
        nc = PT.POINTS[b].get("netcap")
        if not nc:
            continue
        N = common.parse_nets(nc)
        P = PL[b]
        v += [N[f"ot_ms_{n}_clk"]["cw"] / (U.C23 * U.mst_len([P.nodes[n]["xy"]] + P.nodes[n]["sinks"])) for n in MEAS[b]["TT"]]
    return round(st.mean(v), 4)


KLEAF = kleaf_all()
AL = [0.0, 0.2]
BE = [0.35, 0.4, 0.45, 0.5, 0.55, 0.6]
GS = [3.0, 4.0, 5.0, 6.0]
BL = [None] if NOBLEAF else [0.15, 0.25, 0.35, 0.45, 0.6]
KS = [0.0] if NOSTAGE else [x / 4 for x in range(-12, 13)]


def one(args):
    b, kind, a, be, g, bl = args
    p = dict(alpha=a, beta=be, gslew=g, kleaf=KLEAF, bleaf=bl)
    out = []
    for C in ("TT", "FF"):
        prd = V.basis_leaf(PL[b], LIBS, C, kind, p)
        basis = "rise" if kind == "max" else "early"
        out += [(C, k, MEAS[b][C][k][basis] - prd[k], DEP[b][k], MEAS[b][C][k][basis]) for k in MEAS[b][C]]
    return args, out


TAB = {}


def table():
    import multiprocessing as mp
    jobs = [(b, kind, a, be, g, bl) for b in B for kind in ("max", "min") for a in AL for be in BE for g in GS for bl in BL]
    with mp.Pool(int(os.environ.get("OT_REFIT3_PROCS", "8"))) as pool:
        for args, out in pool.imap_unordered(one, jobs, chunksize=4):
            TAB[args] = out


def res(b, kind, p):
    """residuals (C, leaf, meas - pred, meas) with the stage term applied."""
    return [(C, k, r - p["kstage"] * d, m) for C, k, r, d, m in TAB[(b, kind, p["alpha"], p["beta"], p["gslew"], p["bleaf"])]]


def score(bs, kind, p):
    rms, mx = [], 0.0
    for b in bs:
        v = [x[2] for x in res(b, kind, p)]
        rms.append((sum(x * x for x in v) / len(v)) ** 0.5)
        mx = max(mx, max(abs(x) for x in v))
    return st.mean(rms) + 0.25 * mx


NP = {}


def fit(bs, kind):
    """grid over (alpha, beta, gslew, bleaf); the linear KSTAGE term is scored for all grid values at once (numpy)."""
    import numpy as np
    ks = np.array(KS)
    best = None
    for a, be, g, bl in itertools.product(AL, BE, GS, BL):
        rms, mx = 0.0, 0.0
        for b in bs:
            key = (b, kind, a, be, g, bl)
            if key not in NP:
                t = TAB[key]
                NP[key] = (np.array([x[2] for x in t]), np.array([x[3] for x in t], float))
            r, d = NP[key]
            R = r[None, :] - ks[:, None] * d[None, :]
            rms = rms + np.sqrt((R * R).mean(axis=1)) / len(bs)
            mx = np.maximum(mx, np.abs(R).max(axis=1))
        sc = rms + 0.25 * mx
        i = int(np.argmin(sc))
        if best is None or sc[i] < best[0]:
            best = (float(sc[i]), dict(alpha=a, beta=be, gslew=g, bleaf=bl, kstage=float(ks[i])))
    return best[1]


def summ(e, kind):
    o = {}
    for C in ("TT", "FF"):
        w = [x for x in e if x[0] == C]
        r = [x[2] for x in w]
        meas = [x[3] for x in w]
        pred = [x[3] - x[2] for x in w]
        o[C] = dict(mean=round(st.mean(r), 2), sd=round(st.pstdev(r), 2), maxabs=round(max(abs(x) for x in r), 2),
                    meas_mean=round(st.mean(meas), 2), pred_mean=round(st.mean(pred), 2),
                    meas_window=round(max(meas) - min(meas), 2), pred_window=round(max(pred) - min(pred), 2),
                    window_err=round((max(pred) - min(pred)) - (max(meas) - min(meas)), 2))
    return o


if __name__ == "__main__":
    table()
    out = dict(scope="MODEL-REFIT-3 uf_phys3 GRT-basis fit (T7 KSTAGE, T10 BLEAF) on %d GRT builds, per-leaf mean CK arrival "
                     "(meas_ck.tcl, 5_1_grt.odb, rc_cal 0.8/0.9); builds weighted equally; UNCHECKED" % len(B),
               builds=B, kleaf=KLEAF, grid=dict(alpha=AL, beta=BE, gslew=GS, bleaf=BL, kstage=KS), fits={}, loo={}, lofo={})
    fams = sorted(set(FAM.values()))
    for kind in ("max", "min"):
        p = fit(B, kind)
        out["fits"][kind] = dict(params=p, per_build={b: summ(res(b, kind, p), kind) for b in B})
        for h in B:
            p2 = fit([b for b in B if b != h], kind)
            out["loo"].setdefault(kind, {})[h] = dict(params=p2, test=summ(res(h, kind, p2), kind))
        for f in fams:
            p2 = fit([b for b in B if FAM[b] != f], kind)
            out["lofo"].setdefault(kind, {})[f] = dict(params=p2, test={b: summ(res(b, kind, p2), kind) for b in B if FAM[b] == f})
    files = [__file__, V.__file__, U.__file__, PT.__file__] + [x for b in B for k in ("spec", "seg", "geo") for x in [PT.POINTS[b][k]] if x] + \
        [x for b in B for x in PT.POINTS[b]["grt"]]
    out["provenance"] = dict(argv=sys.argv, sha256={str(Path(p).relative_to(PT.RES.parent)) if str(p).startswith(str(PT.RES)) else str(p):
                                                    hashlib.sha256(Path(p if Path(p).exists() else p + ".gz").read_bytes()).hexdigest()
                                                    for p in files})
    json.dump(out, open(OUT, "w"), indent=1)
    for kind, C in (("max", "TT"), ("min", "FF")):
        print(kind, out["fits"][kind]["params"])
        for b in B:
            t = out["loo"][kind][b]["test"][C]
            print("  LOO %-10s %s mean %+.2f sd %.2f max %.2f | win meas %.2f pred %.2f (%+.2f)" % (b, C, t["mean"], t["sd"], t["maxabs"], t["meas_window"], t["pred_window"], t["window_err"]))
        for f in fams:
            for b, t in out["lofo"][kind][f]["test"].items():
                t = t[C]
                print("  LOFO %-14s %-10s %s mean %+.2f max %.2f win %+.2f" % (f, b, C, t["mean"], t["maxabs"], t["window_err"]))
