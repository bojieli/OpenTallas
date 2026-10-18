# Q-CLUSTER PRE_DETAIL_PLACE: release the fabric stage flops placed FIRM by fabric_sites_place.tcl for DPL.
set blk [ord::get_db_block]
set n 0
set f [open $::env(RESULTS_DIR)/ot_qc_sites_firm.txt r]
foreach l [split [read $f] "\n"] {
  if {$l eq ""} continue
  set i [$blk findInst $l]
  if {$i eq "NULL" || $i eq ""} continue
  $i setPlacementStatus PLACED
  incr n
}
close $f
puts "OT_QC_SITES released $n flops for DPL"
