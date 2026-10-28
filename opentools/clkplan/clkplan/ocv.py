"""Clock OCV on the UNSHARED part of a crossing pair: depth- and distance-based (AOCV-style) table + shared droop.

Same math as OpenTallas tools/die_plan/clk_aocv.py (METHODOLOGY 12.4a b1, approved table g = 0.21 %/mm) and
tools/s81_head/landed_phase_ocv.py (LAND-HEAD-2), generalised to a PLANNED tree (no routed arrivals needed):

  per branch (launch a / capture b below the last common tree cell = LCA):
      unshared u   = arrival(sink) - arrival(LCA)                          (die-tree part, class A stages)
      macro part   = the sink's own internal insertion (class B stages, its signed/real view)
      cell_ps      = cell_share_A * u + cell_share_B * insertion;  net_ps = the rest
  random  3 sigma_r / mu_cell, sigma_r^2 = sum_k mu_k^2 s_k^2 (N_k + 2 sum_l (N_k - l) rho_k,l)
  systematic   g * d / 2 per side, d = bounding-box diagonal of a, b and the LCA
  droop        0 if a and b share a clock / PDN region, else one-sided +5.11 % late on the late branch
  pessimism(late, early) = late.cell (f_late + droop) + early.cell f_early + nets x flat net derate
  landed crossing:  derated |d| = max(|d + p(b late, a early)|, |d - p(a late, b early)|),
                    margin = budget (default P/2) - derated |d|;   plan FAILS a pair below min margin (100 ps)
"""
import math


def _var_units(n, rho):
    v = float(n)
    for l, r in enumerate(rho, 1):
        if l >= n:
            break
        v += 2.0 * (n - l) * r
    return max(v, 0.0)


def random_frac(T, corner, stages):
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


def droop_late(T, same_region):
    return 0.0 if same_region else T["droop"]["one_sided_late_frac"]


def branch_pessimism(T, corner, late_br, early_br, dist_um, same_region):
    fl = random_frac(T, corner, late_br["stages"]) + sys_frac(T, dist_um)
    fe = random_frac(T, corner, early_br["stages"]) + sys_frac(T, dist_um)
    n = T["net_flat"]
    return (late_br["cell_ps"] * (fl + droop_late(T, same_region)) + early_br["cell_ps"] * fe
            + late_br["net_ps"] * (n["late"] - 1.0) + early_br["net_ps"] * (1.0 - n["early"]))


def branch(T, corner, unshared_ps, n_die_stages, insertion_ps):
    fa = T["classes"]["A"][corner]["cell_share"]
    B = T["classes"]["B"][corner]
    nB = max(1, round(insertion_ps / B["mu_stage_ps"])) if insertion_ps > 0 else 0
    st = {"A": max(0, int(n_die_stages))}
    if nB:
        st["B"] = nB
    return dict(cell_ps=fa * unshared_ps + B["cell_share"] * insertion_ps,
                net_ps=(1 - fa) * unshared_ps + (1 - B["cell_share"]) * insertion_ps, stages=st, unshared_ps=unshared_ps)


def landed_margin(T, corner, d_ps, bra, brb, dist_um, same_region, budget_ps):
    """d_ps = nominal latency(b) - latency(a).  -> (p_up, p_dn, derated_abs, margin)"""
    p_up = branch_pessimism(T, corner, brb, bra, dist_um, same_region)   # b late, a early: d grows
    p_dn = branch_pessimism(T, corner, bra, brb, dist_um, same_region)   # a late, b early: d shrinks
    der = max(abs(d_ps + p_up), abs(d_ps - p_dn))
    return p_up, p_dn, der, budget_ps - der
