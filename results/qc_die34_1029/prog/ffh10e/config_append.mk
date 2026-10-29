
# ---- DIE-QC-35 PROG QC-020 ffh10e: FF-only post-route hold repair on the ffh10 routed RC (margin 10)
override export OT_HOLD_MM = 0
override export CORNERS = bc
override export CORNER = BC
override export PRE_GLOBAL_ROUTE_TCL = /work/pre_eco.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/eco_ffh10.tcl
override export SKIP_INCREMENTAL_REPAIR = 1
