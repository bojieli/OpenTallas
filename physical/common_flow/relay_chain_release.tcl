# PRE_DETAIL_PLACE hook (STW-S81c-COLLA2 10-22): release the relay cells fixed by relay_chain_place.tcl to PLACED so
# detailed placement legalises them at their stations.
set ot_rc_blk [ord::get_db_block]
set ot_rc_f $::env(RESULTS_DIR)/ot_relay_chain_place.txt
set ot_rc_n 0
if {[file exists $ot_rc_f]} {
  set fh [open $ot_rc_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$ot_rc_blk findInst $n]
    if {$i eq "NULL" || $i eq ""} continue
    $i setPlacementStatus PLACED
    incr ot_rc_n
  }
  close $fh
}
puts "OT_RELAY_PLACE released $ot_rc_n relay cells for DPL"
