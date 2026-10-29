
# ---- DIE-QC-35 BTAB QC-014 V1d (one structural route from V1c ROUTED DB; clock wires FIXED): GRT M4 region adjustment
# 1.0 over each macro body + pin-face strip, full signal re-route, post-route DRV + hold repair on V1c routed RC
override export PRE_GLOBAL_ROUTE_TCL = /work/pre_v1d.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/eco_v1d.tcl
override export SKIP_INCREMENTAL_REPAIR = 1
# FF-only routed-RC ECO frame (main mk_eco b form, 94d520e42): the copied two-mode overrides are replaced
override export OT_HOLD_MM = 0
override export CORNERS = bc
override export CORNER = BC
override export GLOBAL_ROUTE_ARGS = -congestion_iterations 50 -verbose
