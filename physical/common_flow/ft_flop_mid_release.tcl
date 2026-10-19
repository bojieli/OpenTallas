# PRE_DETAIL_PLACE hook (HKV-HROOTK1 2026-10-19): release the feed-through relay flops fixed by ft_flop_mid.tcl
# (PRE_GLOBAL_PLACE) back to PLACED so detailed_placement legalises them at their mid-span sites.
set ot_ft_blk [ord::get_db_block]
set ot_ft_f $::env(RESULTS_DIR)/ot_ft_flop_mid.txt
set ot_ft_n 0
if {[file exists $ot_ft_f]} {
  set fh [open $ot_ft_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$ot_ft_blk findInst $n]
    if {$i eq "NULL" || $i eq ""} continue
    $i setPlacementStatus PLACED
    incr ot_ft_n
  }
  close $fh
}
puts "OT_FTMID released $ot_ft_n feed-through relay flops for DPL"
