# PRE_DETAIL_PLACE (HBM-HC7-DBK 2026-10-20): release the relay / landing flops fixed by relay_anchor.tcl back to PLACED,
# so detailed placement legalises them at their station (same list file; placement only).
set ot_rar_blk [ord::get_db_block]
set ot_rar_f $::env(RESULTS_DIR)/ot_relay_anchor.txt
set ot_rar_n 0
if {[file exists $ot_rar_f]} {
  set fh [open $ot_rar_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$ot_rar_blk findInst $n]
    if {$i eq "NULL" || $i eq ""} continue
    $i setPlacementStatus PLACED
    incr ot_rar_n
  }
  close $fh
}
puts "OT_RLY_ANCHOR released $ot_rar_n relay / landing flops for DPL"
