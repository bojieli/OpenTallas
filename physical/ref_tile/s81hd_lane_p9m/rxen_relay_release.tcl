# PRE_DETAIL_PLACE hook (STW-S81c-DIE4-LANE3 10-22): release the rxen relay flops fixed by rxen_relay_place.tcl so DPL
# legalises them at their stations.
set ot_rx_blk [ord::get_db_block]
set ot_rx_n 0
set ot_rx_f $::env(RESULTS_DIR)/ot_rxen_relay_place.txt
if {[file exists $ot_rx_f]} {
  set fh [open $ot_rx_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    foreach i [$ot_rx_blk getInsts] { if {[string map {\\ {}} [$i getName]] eq $n} { $i setPlacementStatus PLACED; incr ot_rx_n } }
  }
  close $fh
}
puts "OT_RXEN_RELAY released $ot_rx_n relay flops for DPL"
