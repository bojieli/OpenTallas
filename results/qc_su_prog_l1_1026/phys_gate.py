#!/usr/bin/env python3
"""QC-SU-PROG-L1 (COORD RULING MODEL-REFIT-2 15:59): uf_phys_predict as the QC SU GATING predictor, with the guard band.

Gate (12.3 common core latency 250 TT / 202.5 FF +- 20, shrunk by the predictor's LOO max per-leaf error):
  TT rise (max analysis) tap-mean mean in 250 +- (20 - 8) = [238, 262]
  FF early (min analysis) tap-mean mean in 202.5 +- (20 - 5) = [187.5, 217.5]
  TT rise window <= 20 and FF early window <= 20 (predicted; uf_phys over-predicts windows by +1.4..+4.8 = safe side)
Every prediction json records the command line, sha256 of every input + model file, and the TEXTBOOK-parameter
sensitivity (the fitted beta / gslew sit at the grid edge): the same plan re-predicted with
  textbook : alpha 0, beta ln2 = 0.693 (lumped 50% RC), gslew ln9 = 2.197 (10-90 Elmore slew), both analyses
  ln2_fit  : fit_ln2.json (beta fixed at 0.69, alpha/gslew refitted): max a0/b.69/g3.0, min a.2/b.69/g2.2
Sensitivity is REPORTED, not gated.  PLAN MODEL, UNCHECKED.
usage: phys_gate.py SPEC.tcl ASBUILT.json GEO LIBDIR OUT.json
"""
import hashlib
import json
import math
import os
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
UFDIR = HERE.parent / "model_refit2_1026" / "py"
sys.path.insert(0, str(UFDIR))
import uf_phys as U  # noqa: E402
import uf_phys_predict as UP  # noqa: E402

# buffer list the plan may choose from (per-branch sizing, 12.8 d1); uf_phys parses these NLDM tables
SIZES_ALL = ["BUFx4_ASAP7_75t_R", "BUFx4f_ASAP7_75t_R", "BUFx5_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "BUFx8_ASAP7_75t_R",
             "BUFx10_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R", "BUFx16f_ASAP7_75t_R", "BUFx24_ASAP7_75t_R"]
for _s in SIZES_ALL:
    if _s not in U.SIZES:
        U.SIZES.append(_s)

PMAX, PMIN = dict(UP.PMAX), dict(UP.PMIN)           # frozen MODEL-REFIT-2 fit (3d6754e1f4)
LOO_MAX = {"TT": 8.0, "FF": 5.0}                     # LOO max per-leaf |err| 7.1 TT / 4.8 FF, rounded up (ruling)
TARGET = {"TT": 250.0, "FF": 202.5}
BAND = 20.0
WMAX = 20.0
SENS = {
    "textbook": (dict(alpha=0.0, beta=math.log(2), gslew=math.log(9), kleaf=1.2955),
                 dict(alpha=0.0, beta=math.log(2), gslew=math.log(9), kleaf=1.2955)),
    "ln2_fit": (dict(alpha=0.0, beta=0.69, gslew=3.0, kleaf=1.2955), dict(alpha=0.2, beta=0.69, gslew=2.2, kleaf=1.2955)),
}

_LIBS = {}


def libs(libdir):
    if libdir not in _LIBS:
        _LIBS[libdir] = U.load_libs(libdir)
    return _LIBS[libdir]


def sha(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    except OSError:
        return None


def summ(vals):
    v = list(vals)
    return dict(mean=round(st.mean(v), 2), min=round(min(v), 2), max=round(max(v), 2), window=round(max(v) - min(v), 2))


def gate_bases(plan, L, pmax=PMAX, pmin=PMIN):
    """the two gate bases only (cheap: 3 predicts per corner): TT rise (max), FF early (min); + TT late info."""
    o = {}
    for C in ("TT", "FF"):
        b = U.leaf_basis(plan, L, C, pmax, pmin)
        for k in ("rise", "early", "late"):
            o[f"{C}_{k}"] = summ(b[k].values())
        o[f"{C}_leaf"] = {k: {kk: round(vv[k], 2) for kk, vv in b.items()} for k in b["rise"]}
    return o


def fast_obj(plan, L):
    """TT rise + FF early leaf arrivals only (sizing objective)."""
    r, _ = U.predict(plan, L, "TT", edge="rise", **PMAX)
    rm, _ = U.predict(plan, L, "FF", edge="rise", **PMIN)
    fm, _ = U.predict(plan, L, "FF", edge="fall", **PMIN)
    return r, {k: min(rm[k], fm[k]) for k in rm}


def verdict(pred):
    tt, ff = pred["TT_rise"], pred["FF_early"]
    lo_tt, hi_tt = TARGET["TT"] - (BAND - LOO_MAX["TT"]), TARGET["TT"] + (BAND - LOO_MAX["TT"])
    lo_ff, hi_ff = TARGET["FF"] - (BAND - LOO_MAX["FF"]), TARGET["FF"] + (BAND - LOO_MAX["FF"])
    checks = dict(TT_mean=lo_tt <= tt["mean"] <= hi_tt, FF_mean=lo_ff <= ff["mean"] <= hi_ff,
                  TT_window=tt["window"] <= WMAX, FF_window=ff["window"] <= WMAX)
    return dict(verdict="PASS" if all(checks.values()) else "FAIL", checks=checks,
                band=dict(TT_rise_mean=[lo_tt, hi_tt], FF_early_mean=[lo_ff, hi_ff], window_max=WMAX),
                rule="build only if predicted TT rise mean in 250+-(20-8), FF early mean in 202.5+-(20-5), both windows <=20 "
                     "(COORD RULING MODEL-REFIT-2; guard = LOO max per-leaf error 7.1 TT / 4.8 FF)")


def predict_file(spec, asb, geo, libdir, extra_inputs=()):
    L = libs(libdir)
    plan = U.Plan(spec, geo, json.load(open(asb))["seg_um"])
    o = gate_bases(plan, L)
    o["gate"] = verdict(o)
    o["sensitivity"] = {}
    for nm, (pa, pi) in SENS.items():
        s = gate_bases(plan, L, pa, pi)
        o["sensitivity"][nm] = dict(params=dict(max=pa, min=pi),
                                    TT_rise=s["TT_rise"], FF_early=s["FF_early"],
                                    delta_vs_gate=dict(TT_rise_mean=round(s["TT_rise"]["mean"] - o["TT_rise"]["mean"], 2),
                                                       TT_rise_window=round(s["TT_rise"]["window"] - o["TT_rise"]["window"], 2),
                                                       FF_early_mean=round(s["FF_early"]["mean"] - o["FF_early"]["mean"], 2),
                                                       FF_early_window=round(s["FF_early"]["window"] - o["FF_early"]["window"], 2)),
                                    gate_under_these_params=verdict(s)["verdict"])
    o["params"] = dict(max=PMAX, min=PMIN, fit="claude/model-refit2-1026@3d6754e1f4 uf_phys_predict (frozen)")
    files = [spec, asb, geo, str(Path(libdir) / "invbuf_tt.lib"), str(Path(libdir) / "invbuf_ff.lib"), __file__,
             U.__file__, UP.__file__, str(UFDIR / "common.py"), str(UFDIR / "lib.py")] + list(extra_inputs)
    o["provenance"] = dict(argv=[sys.executable] + list(sys.argv), cwd=os.getcwd(),
                           predictor_call=["phys_gate.predict_file", spec, asb, geo, libdir],
                           sha256={p: sha(p) for p in files})
    o["scope"] = "PLAN MODEL uf_phys (MODEL-REFIT-2), UNCHECKED"
    return o


def line(o):
    return ("PHYS TT rise %.2f w%.2f | FF early %.2f w%.2f | TT late %.2f w%.2f | %s | textbook dTT %+.2f dwTT %+.2f dFF %+.2f"
            % (o["TT_rise"]["mean"], o["TT_rise"]["window"], o["FF_early"]["mean"], o["FF_early"]["window"],
               o["TT_late"]["mean"], o["TT_late"]["window"], o["gate"]["verdict"],
               o["sensitivity"]["textbook"]["delta_vs_gate"]["TT_rise_mean"],
               o["sensitivity"]["textbook"]["delta_vs_gate"]["TT_rise_window"],
               o["sensitivity"]["textbook"]["delta_vs_gate"]["FF_early_mean"]))


if __name__ == "__main__":
    spec, asb, geo, libdir, out = sys.argv[1:6]
    o = predict_file(spec, asb, geo, libdir)
    Path(out).write_text(json.dumps(o, indent=1))
    print(line(o))
