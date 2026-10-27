#!/usr/bin/env python3
"""MODEL-REFIT-3 GRT->RCX terms (T8 via R, T9 wire scale) on the points with BOTH GRT and RCX measurements.
The GRT-basis parameters are frozen from fit3_grt.json (fits.max / fits.min); only KR_RCX, KC_RCX, KVIA are fitted here,
with the routed via count per clock net (vias_rcx.tsv, = what a layer/route plan must state).  Leave-one-build-out.
usage: fit_rcx.py LIBDIR fit3_grt.json OUT.json   PLAN MODEL, UNCHECKED."""
import hashlib, itertools, json, statistics as st, sys
from pathlib import Path
sys.path.insert(0, sys.path[0])
import uf_phys3 as V
import points as PT
from uf_phys3 import U, common

LIBS = U.load_libs(sys.argv[1])
G = json.load(open(sys.argv[2]))
OUT = sys.argv[3]
KLEAF = G["kleaf"]
B = [b for b, p in PT.POINTS.items() if p.get("rcx")]
PL = {b: V.load_plan(PT.POINTS[b]["spec"], PT.POINTS[b]["geo"], PT.POINTS[b]["seg"]) for b in B}


def vias_of(f):
    """tree nets only (ot_ms_*_n): leaf-net vias are per-sink pin-access stacks in series with one sink each (~4 x
    0.0145 kOhm x 0.41 fF = 0.02 ps), not on a shared path, so they carry no T8 term."""
    return {ln.split("\t")[0]: int(ln.split("\t")[1]) for ln in open(f) if not ln.startswith("#") and ln.split("\t")[0].endswith("_n")}


VIAS = {b: vias_of(PT.POINTS[b]["vias_rcx"]) for b in B}
MR = {b: {C: common.parse_sinks(PT.POINTS[b]["rcx"][i])[0] for i, C in enumerate(("TT", "FF"))} for b in B}
MG = {b: {C: common.parse_sinks(PT.POINTS[b]["grt"][i])[0] for i, C in enumerate(("TT", "FF"))} for b in B}
KR = [0.7, 0.8, 0.9, 1.0, 1.1]
KC = [0.85, 0.9, 0.95, 1.0, 1.05, 1.1]
KV = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]


def pred(b, kind, C, kr, kc, kv, basis="RCX"):
    p = dict(G["fits"][kind]["params"])
    ks = p.pop("kstage")
    d = V.depth(PL[b])
    r = V.basis_leaf(PL[b], LIBS, C, kind, dict(p, kleaf=KLEAF, kstage=ks, kr=kr, kc=kc, kvia=kv), basis=basis, vias=VIAS[b])
    return r


TAB = {}
for b in B:
    for kind in ("max", "min"):
        for kr, kc, kv in itertools.product(KR, KC, KV):
            TAB[(b, kind, kr, kc, kv)] = {C: pred(b, kind, C, kr, kc, kv) for C in ("TT", "FF")}
BASIS = {"max": "rise", "min": "early"}


def resid(b, kind, kr, kc, kvia):
    kv = kvia
    o = []
    for C in ("TT", "FF"):
        pr = TAB[(b, kind, kr, kc, kv)][C]
        o += [(C, k, MR[b][C][k][BASIS[kind]] - pr[k], MR[b][C][k][BASIS[kind]]) for k in MR[b][C]]
    return o


def fit(bs, kind, kvs=KV):
    best = None
    for kr, kc, kv in itertools.product(KR, KC, kvs):
        rms, mx = [], 0
        for b in bs:
            v = [x[2] for x in resid(b, kind, kr, kc, kv)]
            rms.append((sum(x * x for x in v) / len(v)) ** 0.5)
            mx = max(mx, max(abs(x) for x in v))
        s = st.mean(rms) + 0.25 * mx
        if best is None or s < best[0]:
            best = (s, dict(kr=kr, kc=kc, kvia=kv))
    return best[1]


def summ(e):
    o = {}
    for C in ("TT", "FF"):
        w = [x for x in e if x[0] == C]
        r = [x[2] for x in w]; m = [x[3] for x in w]; p = [x[3] - x[2] for x in w]
        o[C] = dict(mean=round(st.mean(r), 2), sd=round(st.pstdev(r), 2), maxabs=round(max(abs(x) for x in r), 2),
                    meas_mean=round(st.mean(m), 2), pred_mean=round(st.mean(p), 2), meas_window=round(max(m) - min(m), 2),
                    pred_window=round(max(p) - min(p), 2), window_err=round(max(p) - min(p) - max(m) + min(m), 2))
    return o


if __name__ == "__main__":
    out = dict(scope="MODEL-REFIT-3 GRT->RCX (T8 KVIA x setRC via R x routed via count, T9 KR/KC wire scale); GRT params frozen "
                     "from fit3_grt.json; RCX = meas_ck.tcl with the routed SPEF; UNCHECKED", builds=B, grid=dict(kr=KR, kc=KC, kvia=KV),
               rvia_kohm=V.RVIA, fits={}, loo={}, novia={}, novia_loo={})
    for kind in ("max", "min"):
        p = fit(B, kind)
        out["fits"][kind] = dict(params=p, per_build={b: summ(resid(b, kind, **p)) for b in B})
        p0 = fit(B, kind, [0.0])
        out["novia"][kind] = dict(params=p0, per_build={b: summ(resid(b, kind, **p0)) for b in B})
        for h in B:
            tr = [b for b in B if b != h]
            p2 = fit(tr, kind); p3 = fit(tr, kind, [0.0])
            out["loo"].setdefault(kind, {})[h] = dict(params=p2, test=summ(resid(h, kind, **p2)))
            out["novia_loo"].setdefault(kind, {})[h] = dict(params=p3, test=summ(resid(h, kind, **p3)))
    files = [__file__, V.__file__, sys.argv[2]] + [x for b in B for x in PT.POINTS[b]["rcx"] + (PT.POINTS[b]["vias_rcx"],)]
    out["provenance"] = dict(argv=sys.argv, sha256={str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files})
    json.dump(out, open(OUT, "w"), indent=1)
    for kind, C in (("max", "TT"), ("min", "FF")):
        print(kind, "fit", out["fits"][kind]["params"], "| no-via fit", out["novia"][kind]["params"])
        for b in B:
            t = out["loo"][kind][b]["test"][C]; t0 = out["novia_loo"][kind][b]["test"][C]
            print("  LOO %-8s %s via: mean %+.2f sd %.2f max %.2f win meas %.1f pred %.1f | no-via: mean %+.2f sd %.2f max %.2f pred win %.1f" % (
                b, C, t["mean"], t["sd"], t["maxabs"], t["meas_window"], t["pred_window"], t0["mean"], t0["sd"], t0["maxabs"], t0["pred_window"]))
