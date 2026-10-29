
# ---- DIE-QC-35 PROG QC-020 ffh10 (COORD [DIE-QC-34-PARK] 4): FF-frame hold repair on measured arrivals, margin 10 ps,
# vclk FF rebound to sdc_lint 381.14 and TT to 496.03 (= constraint.sdc), slew margin 40 (QC generator post-GRT DRV value)
override export POST_GLOBAL_ROUTE_TCL = /work/post_grt_ffh.tcl
override export HOLD_SLACK_MARGIN = 10
export OT_HOLD_FF_MARGIN = 10
override export SLEW_MARGIN = 40
