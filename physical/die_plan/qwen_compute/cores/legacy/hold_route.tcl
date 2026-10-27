# (QC-CORES copy of tools/elem_qk/hold_eco/hold_route.tcl @ claude/elem-qk-1024; + optional OT_HOLD_DRV=1 post-route slew repair)
# ELEM-QK 10-24 warm hold ECO on a COMPLETED route (POST_GLOBAL_ROUTE_TCL hook).  4_cts.odb is the original
# 5_2_route.odb (pre-filler); 6_final.spef in RESULTS_DIR is that route's extraction.  Variant knobs (env):
#   OT_HOLD_MARGIN (ps), OT_HOLD_ALLOW_SETUP (1 = FF-only run may break FF setup; final TT setup is still gated),
#   OT_HOLD_MAXBUF (max_buffer_percent).  No RTL / cycle / clock / SDC change; final verdict = signoff.py TT/FF.
read_spef $::env(RESULTS_DIR)/6_final.spef
# FLOW-CLKFREEZE 2026-10-27: lock the routed clock network (FIXED wires, FIXED + dont_touch clock-net instances)
# before any repair, so incremental GRT / DRT never re-route a clock net (tools/die_plan/clk_freeze.tcl; blocking
# geometry diff = tools/die_plan/clk_freeze_check.sh in the chain).  Staged next to this file by every ECO chain.
set _ckf [file join [file dirname [info script]] clk_freeze.tcl]
if {![file exists $_ckf]} { error "OT_CLK_FREEZE FAIL: $_ckf not staged (ECO refuses to run without the clock lock)" }
source $_ckf
ot_clk_freeze
global_route -start_incremental
if {[info exists ::env(OT_HOLD_DRV)] && $::env(OT_HOLD_DRV) == 1} { puts "QCCORES_HOLD repair_design -slew_margin 40 -cap_margin 20"; repair_design -slew_margin 40 -cap_margin 20 }
set args [list -hold -hold_margin $::env(OT_HOLD_MARGIN) -max_buffer_percent $::env(OT_HOLD_MAXBUF)]
if {$::env(OT_HOLD_ALLOW_SETUP) == 1} { lappend args -allow_setup_violations }
puts "ELEMQK_HOLD repair_timing $args"
repair_timing {*}$args
detailed_placement
global_route -end_incremental
ot_clk_freeze_assert post_grt
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
# Preserve the exact incremental route map across the ORFS stage/process boundary.
# Fixed pre-routed clock nets intentionally have no guides; DB-guide completeness
# then prevents GlobalRouter::loadGuidesFromDB from restoring any data routes.
write_global_route_segments $::env(RESULTS_DIR)/eco_global_route.segments
