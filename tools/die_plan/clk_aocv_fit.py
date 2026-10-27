#!/usr/bin/env python3
"""CLK-AOCV fit: ASAP7 MC raw (clk_aocv_mc.py parse) + process-only global corner sims -> clock_aocv block.

    clk_aocv_fit.py --mc mc_raw.json --glob glob.json --out tools/die_plan/clk_aocv_table.json

Per class (A = die-tree BUFx24 + 450 um stage, B = core-tree BUFx8 + 40 um + fanout 4) and corner (TT, FF):
  stages 2..D of the simulated chain (stage 1 sees the ideal pre-driver slew and is dropped);
  mu_cell / mu_stage from the nominal sample 0; s_cell = pooled per-stage delay sigma / mu_cell;
  rho = lag-1/2 stage-delay correlations (pooled); path check sigma_N^2 = a N + b N^2 fitted on N = 1..D-1
  (b = the non-averaging part inside one chain; independent mismatch gives b ~ 0).
Distance: g_per_mm = 2 * spread / r_wafer, spread = (SS - FF) / TT process-only delay of the class-A cell
(whole global spread taken as a radial across-wafer parabola, die at the wafer edge: an UPPER BOUND).
"""
import argparse
import json
import math
import statistics as st
from pathlib import Path

import clk_aocv as A

R_WAFER_MM = 150.0


def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    sx, sy = st.pstdev(x), st.pstdev(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / len(x) / (sx * sy)


def fit_class(rec):
    S = rec["samples"]
    nom = next(s for s in S if s["s"] == 0)
    mc = [s for s in S if s["s"] > 0]
    D = len(nom["stage"])
    use = list(range(1, D))
    mu_cell = st.mean(nom["cell"][i] for i in use)
    mu_stage = st.mean(nom["stage"][i] for i in use)
    sig = [st.stdev([s["stage"][i] for s in mc]) for i in use]
    s_stage = math.sqrt(st.mean(v * v for v in sig))
    rho = []
    for lag in (1, 2):
        xs, ys = [], []
        for i in use:
            if i + lag < D:
                xs += [s["stage"][i] for s in mc]
                ys += [s["stage"][i + lag] for s in mc]
        rho.append(round(corr(xs, ys), 4))
    # path sigma vs N (prefix sums of the used stages) and a N + b N^2 least squares
    pts = []
    for n in range(1, len(use) + 1):
        tot = [sum(s["stage"][i] for i in use[:n]) for s in mc]
        pts.append((n, st.pvariance(tot)))
    S2 = sum(n ** 2 for n, _ in pts)
    S3 = sum(n ** 3 for n, _ in pts)
    S4 = sum(n ** 4 for n, _ in pts)
    B1 = sum(n * v for n, v in pts)
    B2 = sum(n * n * v for n, v in pts)
    det = S2 * S4 - S3 * S3
    a_ = (B1 * S4 - B2 * S3) / det if det else 0.0
    b_ = (S2 * B2 - S3 * B1) / det if det else 0.0
    skew = st.mean(((s["stage"][2] - st.mean(x["stage"][2] for x in mc)) / sig[1]) ** 3 for s in mc)
    return dict(mu_cell_ps=round(mu_cell, 3), mu_stage_ps=round(mu_stage, 3), cell_share=round(mu_cell / mu_stage, 4),
                sigma_stage_ps=round(s_stage, 4), s_cell=round(s_stage / mu_cell, 5),
                rho=[max(0.0, r) for r in rho], rho_measured=rho,
                rho_note="negative measured lag correlations clamped to 0 (conservative: no credit for slew anti-correlation)",
                mc_samples=len(mc), stages_used=len(use),
                path_fit=dict(a_ps2_per_stage=round(a_, 4), b_ps2_per_stage2=round(b_, 5),
                              sigma_N_ps={str(n): round(math.sqrt(v), 3) for n, v in pts},
                              note="sigma_N^2 = a N + b N^2 on the simulated prefix sums; b = non-averaging part"),
                stage_skewness=round(skew, 3))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mc", required=True)
    ap.add_argument("--glob", required=True, help='{"TT":{"A":ps,"B":ps},"SS":{..},"FF":{..}} process-only, TT V/T')
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    mc = json.loads(Path(a.mc).read_text())
    gl = json.loads(Path(a.glob).read_text())
    classes = {}
    meta = {}
    for k, rec in mc.items():
        cls, corner = k.split("_")
        classes.setdefault(cls, {})[corner] = fit_class(rec)
        meta[k] = {x: rec["meta"][x] for x in ("cell", "depth", "samples", "seed", "avt_mv_um", "weff_fin_nm", "l_nm",
                                               "sigma_vt_mv", "chain_def", "corner_def")}
    spread = {c: (gl["SS"][c] - gl["FF"][c]) / gl["TT"][c] for c in ("A", "B")}
    g = 2.0 * spread["A"] / R_WAFER_MM
    T = dict(schema=A.SCHEMA, status="DRAFT for OWNER review (METHODOLOGY 12.4a b1); not a gate; numbers UNCHECKED",
             k_sigma=3.0, classes=classes,
             systematic=dict(g_per_mm=round(g, 6), model="deterministic across-wafer gradient, pair differential g*d "
                             "(d = bounding-box diagonal of both clock branches), half charged to each side",
                             basis=dict(process_only_delay_ps=gl, spread_frac=spread, r_wafer_mm=R_WAFER_MM,
                                        bound="whole SS..FF process spread = radial parabola centre->edge; die at the "
                                              "wafer edge (max slope 2*spread/r_wafer). UPPER BOUND, ASSUMED."),
                             source="Cheng, Gupta, Spanos, Qian, He, 'Physically Justifiable Die-Level Modeling of "
                                    "Spatial Variation in View of Systematic Across Wafer Variability', IEEE TCAD 30(3) "
                                    "2011 (within-die spatial correlation = across-wafer systematic; random spatial part "
                                    "not significant); Friedberg, Cheung, Spanos, SPIE 2006 (gate-length spatial data)"),
             droop=dict(one_sided_late_frac=0.0511, rule="clock: differential droop only; 0 in one mesh/PDN region, "
                        "else the stated one-sided +5.1 % late (die_ci_margins.json ir) until PDNSim/region droop; data "
                        "paths: +5.1 % late unchanged", source="COORD 10-26 owner correction to 12.4a b1"),
             net_flat=dict(late=1.03, early=0.97, note="clock nets keep the flat die_ci net derate (not tabled)"),
             mismatch=dict(avt_mv_um=1.2, sigma_vt_mv={k: v for x in meta.values() for k, v in x["sigma_vt_mv"].items()},
                           source="Clark, Vashishtha, Harris, Dietrich, Wang, 'Design Flows and Collateral for the ASAP7 "
                                  "7nm FinFET Predictive Process Design Kit', IEEE MSE 2017 (A_VT 1.2 mV.um, from "
                                  "Giles et al., 'High sigma measurement of random threshold voltage variation in 14nm "
                                  "Logic FinFET technology', VLSI Tech. 2015: 1.07 n / 1.23 p); the ASAP7 PDK itself "
                                  "has no statistical models (TT/SS/FF cards only)",
                           applied="BSIM-CMG 111 instance DELVTRAND ~ N(0, A_VT/sqrt(nfin*(2*HFIN+TFIN)*L)) per "
                                   "transistor, independent; no beta/mobility mismatch (U0MULT = 1)"),
             mc=meta)
    T["table"] = A.table(T)
    Path(a.out).write_text(json.dumps(dict(clock_aocv=T), indent=1) + "\n")
    for cls, cc in classes.items():
        for c, v in cc.items():
            print(cls, c, {k: v[k] for k in ("mu_cell_ps", "mu_stage_ps", "sigma_stage_ps", "s_cell", "rho")},
                  v["path_fit"]["a_ps2_per_stage"], v["path_fit"]["b_ps2_per_stage2"], "skew", v["stage_skewness"])
    print("g_per_mm", g, spread)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
