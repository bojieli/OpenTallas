# PRE_DETAIL_PLACE hook for qfd_crom48 "-cl" (drive-0158): release every flop fixed by crom48cl_pre_gpl.tcl.
source $::env(QDM_SDC_DIR)/rom_cap_release.tcl
source $::env(QDM_SDC_DIR)/out_flop_release.tcl
set ot_blk [ord::get_db_block]
set ot_f $::env(RESULTS_DIR)/ot_crom48cl_band.txt
set ot_n 0
if {[file exists $ot_f]} {
  set fh [open $ot_f r]
  foreach n [split [read $fh] "\n"] {
    if {$n eq ""} continue
    set i [$ot_blk findInst $n]
    if {$i eq "NULL" || $i eq ""} continue
    $i setPlacementStatus PLACED
    incr ot_n
  }
  close $fh
}
puts "OT_CROMCL released $ot_n band flops for DPL"
