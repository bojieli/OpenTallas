# PRE_DETAIL_PLACE hook (STW-S81e-XR 10-23): release the register-floorplan flops fixed by reg_floorplan_place.tcl to
# PLACED so detailed placement legalises them inside their boxes.
set ot_rf_blk [ord::get_db_block]
set ot_rf_f $::env(RESULTS_DIR)/ot_reg_floorplan.txt
set ot_rf_n 0
if {[file exists $ot_rf_f]} {
  set fh [open $ot_rf_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$ot_rf_blk findInst $n]
    if {$i eq "NULL" || $i eq ""} continue
    $i setPlacementStatus PLACED
    incr ot_rf_n
  }
  close $fh
}
puts "OT_REG_PLACE released $ot_rf_n flops for DPL"
