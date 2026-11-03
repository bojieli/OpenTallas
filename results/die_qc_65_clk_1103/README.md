# DIE-QC-65/CLK QC clock plan event (11-03): v2 die clock form + per-type window re-derive

Base plan: plan_qc52 on main f256075f040 (post-RED 8247ff4ce24), sha256 91ece1ff06b0 -> new 6331b0559332.
Delta: clock.tap_window.per_type_ps only (12 types raised to ceil10(need+10), DIE-QC-56 recipe, metadata only);
everything else in the plan byte-identical (no geometry, RTL, cell, tap or cycle change -> plan-time GEOM unchanged).
Script: delta_clk_win_1103.py need_intra_v3.json PLAN PLAN_OUT --report windows_v3.tsv.

Die clock form (ot_clk config, not a plan field): config_v3.yaml = config_v2.yaml on the post-RED plan
(link_htree + region DME delay; early-merge + snake on sl_{E,W}{0..5}_su_l{0,1}; merge on all sl_{E,W}{0..5}_su_c).
v1 = v2 without sl_W0_su_c merge. Built epyc2 /home/ubuntu/scratch-root/claude/die-qc-6{4,5}-clk/v{1,2,3} (chain.sh).

Per-type need (main die_sta_related, nominal single arrival, CPPR-LCA, inv2, diagnostic need dump):
types over W: base 15, v1 11, v2 11, v3 12 (RED added slw_su_c__cl92142dac 108.2/100). need_vs_window_base_v1_v2.tsv, windows_v3.tsv.
CLASS 1 su_l0/l1 early core taps 160-179 -> 32-87 ps (early-merge); CLASS 2 sl_W0_su_c 102.1 -> 87.6 (v2) / 89.8 (v3);
CLASS 3 ordinary spread unchanged. Winner v2 (<= v1 everywhere).

v3 + new windows (summary_sta_v3w_*): combo GRT50 TT/FF 0 overflow; TT setup +156.82; intra kit contract PASS
(0 neg, tightest bound +0.22); seam contract PASS (need 74.67 / W 110, TT +228.24); FF hold BLOCKED(kits).
die_clock_gate contract_violations 1 = landed class judged without --count-align (plan_landing window 416.5);
the QC landed gate form is count-aligned (DIE-QC-57: --count-align + as-built depth on a START physical-paths proof),
which is the die owner's next step, not part of this window event.
