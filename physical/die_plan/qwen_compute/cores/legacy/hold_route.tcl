# ELEM-QK 10-24 warm hold ECO on a COMPLETED route (POST_GLOBAL_ROUTE_TCL hook).  4_cts.odb is the original
# 5_2_route.odb (pre-filler); 6_final.spef in RESULTS_DIR is that route's extraction.  Variant knobs (env):
#   OT_HOLD_MARGIN (ps), OT_HOLD_ALLOW_SETUP (1 = FF-only run may break FF setup; final TT setup is still gated),
#   OT_HOLD_MAXBUF (max_buffer_percent).  No RTL / cycle / clock / SDC change; final verdict = signoff.py TT/FF.
read_spef $::env(RESULTS_DIR)/6_final.spef
global_route -start_incremental
set args [list -hold -hold_margin $::env(OT_HOLD_MARGIN) -max_buffer_percent $::env(OT_HOLD_MAXBUF)]
if {$::env(OT_HOLD_ALLOW_SETUP) == 1} { lappend args -allow_setup_violations }
puts "ELEMQK_HOLD repair_timing $args"
repair_timing {*}$args
detailed_placement
global_route -end_incremental
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
