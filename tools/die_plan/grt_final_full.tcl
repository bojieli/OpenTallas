# Explicit final full-route diagnostic after all post-GRT data mutations.
# Default OFF. Source last in a fresh reviewed POST_GLOBAL_ROUTE chain; normal
# ORFS writes the resulting ODB/SDC after the chain returns. Existing configured
# signal/clock layers, adjustment and capacity remain unchanged.
if {![info exists ::env(OT_GRT_FINAL_FULL)] || $::env(OT_GRT_FINAL_FULL) ne "1"} {return}
set ot_gff_iters 50
if {[info exists ::env(GRT_OVERFLOW_ITERS)]} {set ot_gff_iters $::env(GRT_OVERFLOW_ITERS)}
if {![string is integer -strict $ot_gff_iters] || $ot_gff_iters < 50} {
  error "OT_GRT_FINAL_FULL requires >=50 congestion iterations"
}
set ot_gff_clocks 0
foreach ot_gff_net [[ord::get_db_block] getNets] {
  if {[$ot_gff_net getSigType] ne "CLOCK"} {continue}
  incr ot_gff_clocks
  if {[$ot_gff_net isSpecial]} {
    error "OT_GRT_FINAL_FULL clock excluded as SPECIAL: [$ot_gff_net getName]"
  }
}
if {!$ot_gff_clocks} {error "OT_GRT_FINAL_FULL no CLOCK nets in the actual database"}
foreach ot_gff_var {RESULTS_DIR REPORTS_DIR} {
  if {![info exists ::env($ot_gff_var)] || $::env($ot_gff_var) eq ""} {
    error "OT_GRT_FINAL_FULL missing $ot_gff_var"
  }
}
puts "OT_GRT_FINAL_FULL begin clocks=$ot_gff_clocks iterations=$ot_gff_iters configured layers/capacity unchanged"
# No -allow_congestion: an unconverged final graph fails the ordinary stage.
# No -end_incremental: this is a full route of the final graph.
global_route -congestion_iterations $ot_gff_iters \
  -congestion_report_file $::env(REPORTS_DIR)/grt_final_full_congestion.rpt -verbose
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
puts "OT_GRT_FINAL_FULL done clocks=$ot_gff_clocks iterations=$ot_gff_iters"
