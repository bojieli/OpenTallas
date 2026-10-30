# Scoped plan-built, fully fixed macro stage: coll_ucie zero-inset die-edge PHY.
source $::env(SCRIPTS_DIR)/load.tcl
erase_non_stage_variables floorplan
load_design 2_1_floorplan.odb 2_1_floorplan.sdc
source_step_tcl PRE MACRO_PLACE
set expected {u_bound.u_io_ucie}
set b [ord::get_db_block]
set hard {}
foreach i [$b getInsts] {
  if {[[$i getMaster] isBlock]} {lappend hard [$i getName]}
}
if {[llength $hard]!=1 || [lindex $hard 0] ne $expected} {
  error "COLLPHY_FIXED_STAGE requires only the exact planned PHY macro, got $hard"
}
source $::env(MACRO_PLACEMENT_TCL)
set i [$b findInst $expected]
if {[$i getPlacementStatus] ne "LOCKED"} {error {COLLPHY_FIXED_STAGE macro not locked}}
# The sourced native deck verifies master size, exact plan bbox and full core containment.
# With exactly one hard macro there are no hard-macro overlap pairs; all standard
# placement/tapcell/PG checks run normally after this stage.
source_step_tcl POST MACRO_PLACE
report_design_area
orfs_write_db $::env(RESULTS_DIR)/2_2_floorplan_macro.odb
write_macro_placement $::env(RESULTS_DIR)/2_2_floorplan_macro.tcl
puts {COLLPHY_FIXED_STAGE_PASS exact parent-plan rectangle; 1 macro, 0 overlap pairs}
