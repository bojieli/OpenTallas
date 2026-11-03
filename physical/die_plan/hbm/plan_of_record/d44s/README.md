# HBM plan event d44s (DIE-HBM-59, 2026-11-02)

Metadata-only event on d44q (die_plan 3171b0fc3732 -> a28b88a14d72; only `clock.tap_window` changes):
`clock.tap_window.per_type_ps = {q_hub_nw: 120, q_hub_ne: 120}` (was 80 since d44p).

Why: d44p set 80 ps from the GRT-RC hub mesh needed W (NW 64.98 / NE 70.39). On the full-hub DRT routes
(NW_v2 + NE_v2, NDR w0.12, DRC 0) the same a3e6s mesh needs NW 85.23 / NE 109.50 ps (main die_sta_related, CPPR LCA,
HB4, nominal single, physical feed A; results/die_hbm_1102/clk/gate_A_main_nev2). With 80 the die clock gate FAILS on
d44q: 179 block arrival-contract violations, intra kit-contract hold -29.5 ps. With 120 (d44s): contract violations 0,
TT setup +93.69, CA 773/773 (TT lo 109.3 / FF lo 144.2), worst intra (W160 types) NE_b101 153.16, seam 155.63;
verdict BLOCKED(kits) only (hold pairs without signed real views). NE margin +10.50, NW +34.77.
120 is the measured DRT need plus ~10 ps, below the die-wide 160 (OWNER 12.28b: measured value, no unmeasured tightening).

Consumers: gen_phys.tap_window_ps (hub type kits; HBM types are held, OWNER 11-02) and die_sta_related per_type_ps.
Core kits do not read tap_window, so every d44o/d44q core kit stays valid. Designs: d44c = d44o_cm = d44q design set
(84 designs, same module/outline/pins sha; release_tree_plan.plan_designs, CHECKED 11-02 23:3x).
