#!/usr/bin/env python3
"""MODEL-REFIT-2 fit + leave-one-build-out validation of uf_phys (per-LEAF mean arrival, GRT RC basis)."""
import itertools, json, sys, statistics as st, hashlib
from pathlib import Path
sys.path.insert(0, sys.path[0])
from common import *
import uf_phys as U
from decomp import BUILDS, D
import os
LIBDIR = os.environ.get("OT_INVBUF_LIBDIR", "/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor")  # invbuf_tt/ff.lib
LIBS = U.load_libs(sys.argv[1] if len(sys.argv) > 1 else LIBDIR)
PL = {b: U.Plan(sp, geo, json.load(open(aj))["seg_um"]) for b, (sp, aj, geo) in BUILDS.items()}
MEAS = {b: {C: parse_sinks(D + b + f"/meas_ck_{C}.tsv")[0] for C in ("TT", "FF")} for b in BUILDS}
NETS = {b: parse_nets(D + b + "/netcap_TT.txt") for b in BUILDS}

def kleaf_of(bs):   # leaf routing overhead from measured leaf-net wire cap of the TRAINING builds only
    v = [NETS[b][f"ot_ms_{n}_clk"]["cw"] / (U.C23 * U.mst_len([P.nodes[n]["xy"]] + P.nodes[n]["sinks"]))
         for b in bs for P in [PL[b]] for n in MEAS[b]["TT"]]
    return st.mean(v)

import os
AL = eval(os.environ.get("FIT_AL", "[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]"))
BE = eval(os.environ.get("FIT_BE", "[0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 1.0]"))
GS = eval(os.environ.get("FIT_GS", "[1.5, 2.2, 3.0, 3.5, 4.0, 5.0]"))
KL = None
def one(args):
    b, kind, a, be, g, kl = args
    p = dict(alpha=a, beta=be, gslew=g, kleaf=kl)
    out = []
    for C in ("TT", "FF"):
        if kind == "max":
            prd, _ = U.predict(PL[b], LIBS, C, edge="rise", **p); basis = "rise"
        else:
            r, _ = U.predict(PL[b], LIBS, C, edge="rise", **p); f, _ = U.predict(PL[b], LIBS, C, edge="fall", **p)
            prd = {k: min(r[k], f[k]) for k in r}; basis = "early"
        out += [(C, k, MEAS[b][C][k][basis] - prd[k]) for k in MEAS[b][C]]
    return args, out
TAB = {}
def table(kls):
    import multiprocessing as mp
    jobs = [(b, kind, a, be, g, kl) for kl in kls for b in BUILDS for kind in ("max", "min") for a in AL for be in BE for g in GS]
    with mp.Pool(8) as pool:
        for args, out in pool.imap_unordered(one, jobs, chunksize=8):
            TAB[args] = out
def resid(b, kind, p, kl):
    return TAB[(b, kind, p["alpha"], p["beta"], p["gslew"], kl)]
def fit(bs, kind):
    kl = round(kleaf_of(bs), 4); best = None
    for a, be, g in itertools.product(AL, BE, GS):
        p = dict(alpha=a, beta=be, gslew=g)
        v = [x[2] for b in bs for x in resid(b, kind, p, kl)]
        score = (sum(x * x for x in v) / len(v)) ** 0.5 + 0.25 * max(abs(x) for x in v)
        if best is None or score < best[0]: best = (score, p)
    return best[1], kl
def summ(e):
    o = {}
    for C in ("TT", "FF"):
        w = [x[2] for x in e if x[0] == C]
        o[C] = dict(mean=round(st.mean(w), 2), sd=round(st.pstdev(w), 2), maxabs=round(max(abs(x) for x in w), 2))
    return o
if __name__ == "__main__":
  kls = sorted({round(kleaf_of(list(BUILDS)), 4)} | {round(kleaf_of([x for x in BUILDS if x != h]), 4) for h in BUILDS})
  table(kls)
  res = dict(scope="MODEL-REFIT-2 uf_phys fit; per-leaf (64/build) mean CK arrival, meas_ck.tcl on 5_1_grt.odb (GRT RC rc_cal 0.8,0.9); "
                   "max analysis fitted on TT+FF arrival_max_rise, min analysis on TT+FF early=min(rise_min,fall_min); UNCHECKED",
             grid=dict(alpha=AL, beta=BE, gslew=GS), fits={}, loo={})
  for kind in ("max", "min"):
      p, kl = fit(list(BUILDS), kind)
      res["fits"][kind] = dict(params=p, kleaf=round(kl, 4), per_build={b: summ(resid(b, kind, p, kl)) for b in BUILDS})
      for hold in BUILDS:
          tr = [b for b in BUILDS if b != hold]
          p2, kl2 = fit(tr, kind)
          res["loo"].setdefault(kind, {})[hold] = dict(params=p2, kleaf=round(kl2, 4), test=summ(resid(hold, kind, p2, kl2)))
      # no-fit physical defaults for reference
      # = {b: summ(resid(b, kind, dict(alpha=0.0, beta=1.0, gslew=U.LN9), kleaf_of(list(BUILDS)))) for b in BUILDS}
  res["provenance"] = dict(argv=sys.argv, files={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16] for p in
      [__file__, U.__file__] + [x for v in BUILDS.values() for x in v] + [D + b + f"/meas_ck_{C}.tsv" for b in BUILDS for C in ("TT", "FF")]})
  json.dump(res, open(sys.argv[2] if len(sys.argv) > 2 else "fit.json", "w"), indent=1)
  print(json.dumps({k: v for k, v in res.items() if k in ("fits", "loo")}, indent=0))
  