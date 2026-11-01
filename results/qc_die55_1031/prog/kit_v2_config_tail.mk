
# ---- DIE-QC-55 PROG rebuild (COORD 15:5x): the lost DIE-QC-34/35 recipe re-assembled (results/qc_die34_1029/prog):
# cand-2 route hooks (prep_prog.tcl input = re-created native pin-reach DB, pre_grt_leaf.tcl, ORFS GRT 50 iterations,
# incremental repair on) + ffh10 (vclk binding repair, FF-frame hold margin 10, SLEW_MARGIN 40, post_grt_ffh.tcl)
override export OT_VCLK_TT = 496.03
override export OT_VCLK_FF = 381.14
override export PRE_GLOBAL_ROUTE_TCL = /work/pre_grt_leaf.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/post_grt_ffh.tcl
export GLOBAL_ROUTE_ARGS = -congestion_iterations 50 -verbose
override export SKIP_INCREMENTAL_REPAIR = 0
override export HOLD_SLACK_MARGIN = 10
export OT_HOLD_FF_MARGIN = 10
override export SLEW_MARGIN = 40

# ---- SIGNOFF-MODES-1 per-mode binding (tools/die_plan/kit_modes.py stage): scene tc (mode ss) TT setup vclk 496.03 / scene BC (mode ff) FF hold vclk 381.14
override export CORNERS = tc BC
override export OT_HOLD_MM = 1
override export OT_MM_SETUP_CORNER = tc
override export OT_MM_FF_SDC = /work/vclk_ff.sdc
override export OT_MM_MEASURED_HOLD = 1
