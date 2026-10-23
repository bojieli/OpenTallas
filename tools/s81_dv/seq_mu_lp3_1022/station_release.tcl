# pre_dpl_extra (STW-S81c-COLLA4-SEQ 10-22): release the cells station_place.tcl fixed (FIRM -> PLACED) so DPL legalises them.
set ot_st_blk [ord::get_db_block]
set ot_st_f $::env(RESULTS_DIR)/ot_station_place.txt
set ot_st_n 0
if {[file exists $ot_st_f]} {
  set fh [open $ot_st_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$ot_st_blk findInst $n]
    if {$i ne "NULL" && [$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED; incr ot_st_n }
  }
  close $fh
}
puts "OT_STATION_RELEASE released $ot_st_n station cells for DPL"
