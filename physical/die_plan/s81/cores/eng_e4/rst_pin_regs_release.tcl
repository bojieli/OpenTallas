# PATH-S81/E4 PRE_DETAIL_PLACE: release rst_pin_regs.tcl anchors to PLACED for DPL
set rr_blk [ord::get_db_block]; set rr_n 0
set rr_f $::env(RESULTS_DIR)/ot_rst_pin_regs.txt
if {[file exists $rr_f]} {
  set fh [open $rr_f]
  foreach n [split [read $fh] "\n"] { if {$n eq ""} continue; set i [$rr_blk findInst $n]; if {$i ne "NULL" && $i ne "" && [$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED; incr rr_n } }
  close $fh
}
puts "OT_RPR released $rr_n reset pin registers for DPL"
