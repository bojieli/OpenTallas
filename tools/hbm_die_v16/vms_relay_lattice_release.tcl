# vms_relay_lattice_release.tcl -- VM hub-glue g7 (L2H-PGVM-G7 2026-10-19), PRE_DETAIL_PLACE (kit pre_dpl_extra): the
# relays fixed on the lattice by vms_relay_lattice.tcl go back to PLACED so detailed placement legalises them in place.
set rlr_blk [ord::get_db_block]
set rlr_f $::env(RESULTS_DIR)/ot_relay_lattice.txt
if {![file exists $rlr_f]} { error "OT_RLAT release: $rlr_f missing (vms_relay_lattice.tcl did not run)" }
set rlr_n 0
set rlr_h [open $rlr_f r]
foreach n [split [read $rlr_h] "\n"] {
  if {$n eq ""} continue
  set i [$rlr_blk findInst $n]
  if {$i eq "NULL" || $i eq ""} continue
  $i setPlacementStatus PLACED
  incr rlr_n
}
close $rlr_h
puts "OT_RLAT released $rlr_n lattice relays for DPL"
