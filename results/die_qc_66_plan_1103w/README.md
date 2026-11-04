# DIE-QC-66/PLAN: QC per-type tap windows re-derived on the y-shrunk die clock (11-03)

Base: plan_qc52 on main 3465966986 (shrink2 2fd11f0f94 + CA re-fix eafccfed43 + CLAND cd6ee44401), sha256 ceb1a8a86ed0 -> f720ccd567c8.
Delta: `clock.tap_window.per_type_ps` only. 23 types are raised to ceil10(need+10), capped at T/4, using the DIE-QC-56/DIE-QC-65 recipe (metadata only).
The rest of the plan is byte-identical: no geometry, RTL, cell, tap or cycle change, so plan-time GEOM is unchanged.
schema validate PASS.
Script: `delta_win66.py need_intra_shr2.json PLAN PLAN_OUT --report windows_shr2.tsv` (DIE-QC-65 delta_clk_win_1103.py with tag/note changed).

## Why

The advisory die probe on main b07b52ff0c7 used the ot_clk v3 kit, combo GRT50 TT/FF (0 overflow, byte-equal to the 13:01 shrink run), and main die_sta_related (nominal, CPPR-LCA, inv2).
It found 169 intra kit-contract violations: need 148.45 against W 120 (c_W0/E4_tf_00 clk_c0 -> clk_t16).
The windows from 1e5ed443cd were measured on the pre-shrink v3 clock (need <= 129.99). The y-shrink re-balanced the die clock, so the measured arrivals in 23 types now exceed their windows.
need_intra_shr2.json is the die_sta_related need dump (OT_NEED_DUMP) from the 13:01 shrink run. That run has the same proof as the probe.

## Result (same proof, new plan) [win66_sta_ca.log]

- intra kit-contract: 0 neg, tightest bound +0.31 ps. seam: PASS (need 90.32 / W 110). TT setup +139.90.
- die_clock_gate contract_violations 1. That 1 is the landed class judged by the T/2 fallback without --count-align, the same as in DIE-QC-65.
- The QC landed form is count-aligned. ca_judge66.py (the DIE-QC-66/CLK gate interval model, as-built DEPTH) gives 0/2525 fail: TT lo +103.9 / hi +106.5, FF lo +162.3 / hi +257.0.
- The landed T/2 FAIL (su_c -> bn_10, 2385 ps) is a real arrival gap, and it is absorbed by the CA ring.
  Example: sl_E3_hc2__cws2__3 has d 1753-2608 ps, cycles 1, depth 4, TT margin lo +1187 / hi +158.
