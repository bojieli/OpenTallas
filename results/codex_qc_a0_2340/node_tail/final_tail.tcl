# Warm final FF repair: retain completed global routes and all clock geometry.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 4_cts.sdc
set_propagated_clock [all_clocks]
set minck $::env(MIN_ROUTING_LAYER)
if {[info exists ::env(MIN_CLK_ROUTING_LAYER)]} {set minck $::env(MIN_CLK_ROUTING_LAYER)}
set maxck $::env(MAX_ROUTING_LAYER)
if {[info exists ::env(MAX_CLK_ROUTING_LAYER)]} {set maxck $::env(MAX_CLK_ROUTING_LAYER)}
set_routing_layers -signal $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER) -clock ${minck}-${maxck}
set_global_routing_layer_adjustment $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER) 0.25
source $::env(LAYER_PARASITICS_FILE)
estimate_parasitics -global_routing
source /work/final_ff_hold.tcl
source /work/clk_freeze.tcl
proc codex_clock_guides {} {
 set lines {}
 foreach n [ot_clk_dbnets] {
  foreach g [$n getGuides] {
   set bb [$g getBox]
   lappend lines "[$n getName] [[$g getLayer] getName] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]"
  }
 }
 return [lsort $lines]
}
set cg_before [codex_clock_guides]
set f [open /work/clock_guides_before.txt w];puts $f [join $cg_before "\n"];close $f
ot_final_ff_hold
set cg_after [codex_clock_guides]
set f [open /work/clock_guides_after.txt w];puts $f [join $cg_after "\n"];close $f
if {$cg_before ne $cg_after} {error "CODEX_NODE_FINAL_TAIL: global clock route guides changed"}
puts "CODEX_NODE_FINAL_TAIL clock guide rectangles unchanged: [llength $cg_after]"

source /work/pg_connect.tcl
ot_pg_connect_all codex_final_tail
ot_pg_require_bound codex_final_tail
write_db $::env(RESULTS_DIR)/5_1_grt.odb
write_sdc -no_timestamp $::env(RESULTS_DIR)/5_1_grt.sdc
write_guides $::env(RESULTS_DIR)/route.guide
puts "CODEX_NODE_FINAL_TAIL complete: completed GRT reused; frozen clocks; TT/FF hold check passed"
