#!/usr/bin/env python3
"""CLK-AOCV: depth- and distance-based clock OCV derate (METHODOLOGY 12.4a b1, OWNER 10-26 17:4x).  DRAFT, opt-in.

Replaces, ONLY when a caller opts in, the flat clock-path derate of die_ci_margins.json (cell 1.05/0.95, net
1.03/0.97).  Data paths keep the flat derates; nets keep the flat net derate (this table derates cells only).

Model (per clock branch = launch or capture clock path below the last common point, CPPR node):
  random      sigma_r^2 = sum_k mu_k^2 s_k^2 (N_k + 2 sum_{l=1..N_k-1} (N_k - l) rho_k,l)
              s_k = per-stage delay sigma / nominal CELL delay of stage class k, rho_k,l = stage-to-stage correlation
              (slew coupling) at lag l, both fitted from the ASAP7 BSIM-CMG Monte Carlo (clk_aocv_mc.py) with Pelgrom
              mismatch A_VT = 1.2 mV.um (ASSUMED, cited: Clark et al. MSE 2017 / Giles et al. VLSI 2015).
  systematic  g * d / 2 per side (pair total g * d): deterministic across-wafer gradient (Cheng et al., IEEE TCAD 2011:
              within-die "spatial correlation" is the across-wafer systematic trend; random within-die spatial part is
              not significant), d = diagonal of the bounding box of all clock cells of both branches (AOCV distance).
              g = gradient per mm, bounded from the ASAP7 process-only global corner spread (SS/FF model cards at TT
              V/T, ngspice) assuming the whole global spread is a radial across-wafer parabola, die at the wafer edge.
  derate      late  = 1 + 3 sigma_r / mu_cell + g d / 2       early = 1 - 3 sigma_r / mu_cell - g d / 2
              (random and systematic added linearly: conservative, the gradient is a bound not a sigma)
Supply droop on the clock (COORD 10-26 owner correction): only the DIFFERENTIAL droop between the two branches is
charged: 0 when both branches sit in the same mesh / PDN region, else the full one-sided stated +5.1 % late (die_ci
ir) until a PDNSim / region-droop result gives the real differential.  Data paths keep +5.1 % late.

API
  T = load(path)                                   # the 'clock_aocv' block (die_ci_margins.json or a sibling file)
  cell_derate(T, corner, stages={cls: N}, dist_um) -> (late, early)
  branch_pessimism(T, corner, side_a, side_b, dist_um, same_region, check) -> ps   (see docstring)
  table(T) -> rendered grid for review
"""
import json
import math
from pathlib import Path

SCHEMA = "opentallas.clk_aocv.v1-draft"


def load(path):
    d = json.loads(Path(path).read_text())
    t = d.get("clock_aocv", d)
    if t.get("schema") != SCHEMA:
        raise SystemExit(f"{path}: no {SCHEMA} clock_aocv block")
    return t


def _var_units(n, rho):
    """sum of N unit-variance stages with lag correlations rho[l-1] (l = 1..)."""
    v = float(n)
    for l, r in enumerate(rho, 1):
        if l >= n:
            break
        v += 2.0 * (n - l) * r
    return max(v, 0.0)


def random_frac(T, corner, stages):
    """3 sigma_r / mu_cell of a branch with stages = {class: count} at corner (fraction of the branch cell delay)."""
    var = mu = 0.0
    for cls, n in stages.items():
        if n <= 0:
            continue
        c = T["classes"][cls][corner]
        m = c["mu_cell_ps"]
        var += (m * c["s_cell"]) ** 2 * _var_units(n, c.get("rho", []))
        mu += n * m
    return 0.0 if mu <= 0 else T["k_sigma"] * math.sqrt(var) / mu


def sys_frac(T, dist_um):
    return T["systematic"]["g_per_mm"] * max(0.0, dist_um) / 1000.0 / 2.0


def cell_derate(T, corner, stages, dist_um):
    f = random_frac(T, corner, stages) + sys_frac(T, dist_um)
    return 1.0 + f, max(0.0, 1.0 - f)


def droop_late(T, same_region):
    """clock-path droop late factor - 1 under the shared-droop rule."""
    return 0.0 if same_region else T["droop"]["one_sided_late_frac"]


def branch_pessimism(T, corner, a, b, dist_um, same_region, check):
    """OCV pessimism (ps) a pair's non-common clock carries, cells by the table, nets flat.
    a / b = dict(cell_ps, net_ps, stages={cls: N}) of the launch (a) and capture (b) branch below the CPPR node.
    check 'setup': launch late + capture early; 'hold': capture late + launch early (+ droop on the late branch)."""
    late_br, early_br = (a, b) if check == "setup" else (b, a)
    fl = random_frac(T, corner, late_br["stages"]) + sys_frac(T, dist_um)
    fe = random_frac(T, corner, early_br["stages"]) + sys_frac(T, dist_um)
    n = T["net_flat"]
    return (late_br["cell_ps"] * (fl + droop_late(T, same_region)) + early_br["cell_ps"] * fe
            + late_br["net_ps"] * (n["late"] - 1.0) + early_br["net_ps"] * (1.0 - n["early"]))


def flat_pessimism(m, a, b, check, same_region=None, shared_droop=False):
    """the same quantity under the flat die_ci_margins.json derates (cell +-5 %, net +-3 %, IR +5.1 % late on cells:
    additive convention of QC-MP-REGION).  shared_droop=True applies the droop rule above (0 in one region)."""
    o, irf = m["ocv"], m["ir"]["vdd_drop_frac"] * 1.022
    late_br, early_br = (a, b) if check == "setup" else (b, a)
    ir = 0.0 if (shared_droop and same_region) else irf
    return (late_br["cell_ps"] * (o["cell_late"] - 1.0 + ir) + early_br["cell_ps"] * (1.0 - o["cell_early"])
            + late_br["net_ps"] * (o["net_late"] - 1.0) + early_br["net_ps"] * (1.0 - o["net_early"]))


def table(T, depths=(1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 80), dists_mm=(0, 0.5, 1, 2, 4, 8, 16, 24)):
    out = {}
    for cls in T["classes"]:
        for corner in T["classes"][cls]:
            rows = []
            for n in depths:
                r = random_frac(T, corner, {cls: n})
                rows.append([n] + [round(1.0 + r + sys_frac(T, d * 1000.0), 4) for d in dists_mm])
            out[f"{cls}_{corner}"] = dict(late_rows=rows, early_rows=[[x[0]] + [round(2.0 - v, 4) for v in x[1:]]
                                                                      for x in rows])
    return dict(depths=list(depths), dists_mm=list(dists_mm), grids=out,
                note="late = 1 + 3 sigma_r(N)/mu_cell + g d/2; early = 2 - late (symmetric); cells only")
