# PRE_DETAIL_PLACE hook (spec pre_dpl_extra, HBM-ELEMOWN3/SFUPS 2026-10-19): release the r11 relay flops fixed by
# relay_place.tcl back to PLACED so detailed_placement legalises them at their channel points.
set ot_rl_blk [ord::get_db_block]
set ot_rl_f $::env(RESULTS_DIR)/ot_relay_place.txt
set ot_rl_n 0
if {[file exists $ot_rl_f]} {
  set fh [open $ot_rl_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$ot_rl_blk findInst $n]
    if {$i eq "NULL" || $i eq ""} continue
    $i setPlacementStatus PLACED
    incr ot_rl_n
  }
  close $fh
}
puts "OT_RELAY_PLACE released $ot_rl_n relay flops for DPL"
