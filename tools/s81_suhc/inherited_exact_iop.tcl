# Reapply the DIE-assigned immutable inherited face after ORFS automatic IO placement.
# PG pins remain untouched; save the changed IO database for global placement.
if {![info exists ::env(OT_HC_NATIVE_IO_TCL)]} { error "missing official inherited die pin grant" }
set hc_blk [ord::get_db_block]
foreach bt [$hc_blk getBTerms] {
  if {[$bt getSigType] in {POWER GROUND}} continue
  foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp }
}
source $::env(OT_HC_NATIVE_IO_TCL)
set hc_assigned 0
foreach bt [$hc_blk getBTerms] {
  if {[llength [$bt getBPins]] == 0} { error "inherited exact IO missing [$bt getName]" }
  if {[$bt getSigType] ni {POWER GROUND}} { incr hc_assigned }
}
puts "HC_NATIVE_ASSIGNED_IO exact_signal_pins=$hc_assigned source=$::env(OT_HC_NATIVE_IO_TCL)"
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl
