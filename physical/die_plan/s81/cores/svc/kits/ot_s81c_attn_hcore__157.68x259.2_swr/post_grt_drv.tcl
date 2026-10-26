# PATH-S81/HCORE swr 10-25: post-GRT DRV only.  FF hold is repaired in its own one-scene OpenROAD process after CTS
# (repair_ff.tcl, run_swr.sh); the former mixed tc+bc `repair_timing -hold` here was the hcore_eh1 stall (pads the FF corner
# against the TT bound, 6k pin-reg endpoints, hours).  Setup is checked independently at TT after the FF repair.
global_route -start_incremental
# Match the placement-stage cap; do not split legal 17-24-load data nets.
# One max_fanout (24) for placement (drv.tcl) and post-GRT.  Clock nets are excluded from post-GRT DRV: the CTS tree
# (leaf fanout up to ~30) is owned by CTS; repair_design must never split / buffer it (PATH-S81 10-25).
set_max_fanout 24 [current_design]
set_max_transition 200 [current_design]
set ot_clk_dnt {}
foreach n [[ord::get_db_block] getNets] {
  if {[$n getSigType] eq "CLOCK" && ![$n isDoNotTouch]} { $n setDoNotTouch 1; lappend ot_clk_dnt $n }
}
puts "OT_POST_GRT_DRV clock_nets_excluded [llength $ot_clk_dnt]"
if {![llength $ot_clk_dnt]} { error "OT_POST_GRT_DRV: no CLOCK-typed nets found; refusing to run DRV over an unprotected clock tree" }
repair_design -slew_margin 20 -cap_margin 20
foreach n $ot_clk_dnt { $n setDoNotTouch 0 }
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
