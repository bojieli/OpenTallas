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


# ------------------------------------------------------------------------------------------ count-aligned crossings
# Two crossing windows (COORD-REVIEW-QUEUE 2026-10-27):
#
# count_aligned  (COORD 20:35 ruling on MESO-COUNT-1 + 21:10 bug report OSS-CLOCK-2; THE count-aligned form)
#     The count-aligned ring (generic form: a DEPTH-slot ring written by the sender clock, read BY COUNT in the receiver
#     domain, guards at slots 0 / DEPTH fail closed) delivers sender word n at receiver count n + K, at ANY static phase.
#     Lag of the word  L = K_eff T + rel,  rel in [rel_lo, rel_hi] with
#         rel_lo = min over corners (d_c - p_dn_c) - X T - w,   rel_hi = max over corners (d_c + p_up_c) + Y T + w
#     (d = nominal capture - launch clock latency, p_up / p_dn = derated growth / shrink on the unshared clock,
#      X / Y = whole-cycle origin ambiguity from the start tree, w = post-start wander = wander_frac x unshared).
#     Correct iff  0.5 T <= L <= (DEPTH - 0.5) T ; the plan keeps an aperture ap from each guard edge:
#         K_eff = smallest integer with  K_eff T + rel_lo >= 0.5 T + ap          (least latency, picked from the
#                                                                                  DERATED lag, one K for all corners)
#         DEPTH = 4 if K_eff T + rel_hi <= 3.5 T - ap, else 8 if <= 7.5 T - ap, else FAIL
#         margin_lo = L_lo - 0.5 T,  margin_hi = (DEPTH - 0.5) T - L_hi   (ap included; gate >= min margin, 100 ps)
#     Receiver latency K_eff + 1 cycles (read register).  ap default T/8 (= the formal proof's time step, covers the
#     guard-sampler aperture).  Same model as OpenTallas tools/die_plan/count_align_plan.py (MESO-COUNT-2).
#
# ring_phase     (COORD 20:26, WITHDRAWN 20:35 for the count-aligned ring; kept ONLY for a one-period sampler with a
#     design-time count, e.g. a phase-placed landing flop): window = full period minus the placement flop's setup + hold,
#     centred +-(T - ap_c)/2; the count absorbs whole cycles only (or half cycles with half-cycle placement):
#     residual r_c = d_c - K step, margin_c = (T - ap_c)/2 - max(|r_c + p_up_c|, |r_c - p_dn_c|); ONE K for all corners.
CA_DEPTHS = (4, 8)


def count_aligned_margin(per_corner, T_ps, ap_ps=None, depths=CA_DEPTHS, origin_cycles=(0, 0), wander_ps=0.0):
    """per_corner = {corner: (d_ps, p_up_ps, p_dn_ps)}; ap_ps = guard-edge aperture (default T/8).
    -> dict(K (= K_eff, lag in whole cycles), depth (None = FAIL), latency_cycles, L_lo/L_hi, margin_lo/hi, margin_ps,
            corners{c: lag / margins at the common K and DEPTH})."""
    cs = list(per_corner)
    if not cs:
        raise ValueError("no corners")
    ap = T_ps / 8.0 if ap_ps is None else float(ap_ps)
    X, Y = origin_cycles
    lo_c = {c: per_corner[c][0] - per_corner[c][2] - X * T_ps - wander_ps for c in cs}
    hi_c = {c: per_corner[c][0] + per_corner[c][1] + Y * T_ps + wander_ps for c in cs}
    rel_lo, rel_hi = min(lo_c.values()), max(hi_c.values())
    K = math.ceil((0.5 * T_ps + ap - rel_lo) / T_ps - 1e-9)
    L_lo, L_hi = K * T_ps + rel_lo, K * T_ps + rel_hi
    depth = next((D for D in sorted(depths) if L_hi <= (D - 0.5) * T_ps - ap + 1e-9), None)
    Dm = depth or max(depths)
    m_lo, m_hi = L_lo - 0.5 * T_ps, (Dm - 0.5) * T_ps - L_hi
    corners = {c: dict(lag_lo_ps=K * T_ps + lo_c[c], lag_hi_ps=K * T_ps + hi_c[c],
                       margin_lo_ps=K * T_ps + lo_c[c] - 0.5 * T_ps, margin_hi_ps=(Dm - 0.5) * T_ps - K * T_ps - hi_c[c])
               for c in cs}
    for e in corners.values():
        e["margin_ps"] = min(e["margin_lo_ps"], e["margin_hi_ps"])
    return dict(form="count_aligned", K=K, depth=depth, latency_cycles=K + 1 if depth else None, aperture_ps=ap,
                wander_ps=wander_ps, origin_cycles=(X, Y), L_lo_ps=L_lo, L_hi_ps=L_hi, margin_lo_ps=m_lo,
                margin_hi_ps=m_hi, margin_ps=min(m_lo, m_hi), corners=corners)


def ring_phase_margin(per_corner, T_ps, ap, half_cycle=False, k_range=None):
    """superseded one-period window (see above).  ap = {corner: setup + hold of the placement flop}.
    -> dict(K, step_ps, margin_ps, corners{c: residual / margin}) with the ONE K maximising the worst-corner margin."""
    cs = list(per_corner)
    if not cs:
        raise ValueError("no corners")
    step = T_ps / 2.0 if half_cycle else T_ps

    def ev(K):
        out = {}
        for c in cs:
            d, pu, pd = per_corner[c]
            r = d - K * step
            w2 = (T_ps - ap[c]) / 2.0
            out[c] = dict(residual_ps=r, half_window_ps=w2, margin_ps=w2 - max(abs(r + pu), abs(r - pd)))
        return out
    guess = sum(per_corner[c][0] for c in cs) / len(cs) / step
    ks = range(*k_range) if k_range else range(math.floor(guess) - 4, math.ceil(guess) + 5)
    best = None
    for K in ks:
        e = ev(K)
        w = min(v["margin_ps"] for v in e.values())
        if best is None or w > best[0] + 1e-9:
            best = (w, K, e)
    w, K, e = best
    return dict(form="ring_phase", K=K, step_ps=step, half_cycle=bool(half_cycle), margin_ps=w, corners=e)
