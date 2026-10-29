# DIE-QC-35 PROG QC-020 ffh10 POST_GLOBAL_ROUTE (COORD [DIE-QC-34-PARK] item 4, METHODOLOGY 12.19 / 12.4a a1):
# after the ORFS GRT-stage repair (two-mode orfs_hold_mm session: scene tc = TT setup vclk 496.03, scene BC = FF hold
# vclk 381.14 rebound on MEASURED pin-flop arrivals, vclk_measured_hold.tcl; HOLD_SLACK_MARGIN 10), the existing main
# fixed-point step tools/die_plan/final_ff_hold.tcl ot_final_ff_converge: TT setup guard + FF hold (OT_HOLD_FF_MARGIN 10)
# + slew/cap (repair_design_helper, kit SLEW_MARGIN) on the selected RC, clock frozen and clock geometry diffed (no clock
# ECO, no pads/trims, no skew targets).  Then the PG bind + 0-open check of the cand-2 route.
source /work/final_ff_hold.tcl
ot_final_ff_converge
source /work/post_grt_pg.tcl
