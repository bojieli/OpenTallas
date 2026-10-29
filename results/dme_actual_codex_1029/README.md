# Coherent physical DME legs, isolated S81 bk_sel

Problem: go16 priced direct Manhattan legs then export snapped repeaters
past hard cores. Actual653.52um gap already existed before body overlay
(653.40 after), and post-DME reach17 inserted4 unpriced stages on it,
widening the FF kit window239->316.93ps. The shared opt-in planner now
prices actual snapped chains and geometry-derived paired detours during
merge and snake selection. A native-body SiteMap and R0 home allocation
finalise the homes BEFORE final physical leg costs/export. The exact
frozen chains are exported; changed endpoints/illegal homes fail closed.
A later body overlay is forbidden from moving them; actual_reach checks
the frozen-home digest, even for a move that stays inside reach.

Default behavior is unchanged. Flag: --region-dme-actual-max405 (space
between flag and value in shell). Source code6bf47b91c/5c882841e/c0e4ae487;
frozen-home guardf3df3cee7. New mode is an experiment, not a clock or
constraint relaxation. No functional data RTL or added cycle.

Exact go16 plan_s11e and inv2_stage_cal_s81_go15 calibration, ONLY51
bk_sel taps; no full global rebuild. Fleet source snapshots pinned:
- e16aebe50 baseline/point-only: baseline model TT224.78/FF189.91ps,
 2>405; point-only physical pricing58.85/19.46ps,0>405 but20 body
 overlaps (baseline12) => geometryFAIL retained, never routed.
- c0e4ae487 native-body coupon: TT67.93/FF25.23ps model window,
 0>405/max391.5um,246 cells,0 overlaps/0 macro halo hits/0 off R0 grid,
 51/51 true-polarity tap clocks. Runtime109.8s. These are analytic
 predictor numbers, NOT STA or freeze-gate values.

Actual homes/tree/netlist and logs: epyc2:/srv/opentallas-scratch2/claude/
codex-dme-actual-1029/body. Unitoth-ubuntu-144683-1793260116 exit0.
Baseline/point-only unitoth-ubuntu-48133-1793258996 exit0. No live own
coupon job after collection. Review picture/findings under
results/geom_review/dme_actual_codex_1029. Both failed point candidates
stay in their original directories. No P&R/STA has run on the new form.

Focused source checks:20 PASS after frozen-home guard; the6 physical-
leg/body/grid/endpoint/frozen-home controls PASS after it. Default-mode
DME stage-cal/inverter/join tests pass. Independent GEOM review PASS-COND received. Next: die owner one isolated
clock GRT+actual TT/FF STA, replace model
prediction with measured result and regenerate CA before any adoption.
