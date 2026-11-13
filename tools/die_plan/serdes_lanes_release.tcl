# serdes_lanes_release.tcl (HARD-S81-SERDES-1; PRE_DETAIL_PLACE, sourced from face_flops_release.tcl): remove the GPL-only
# placement blockages of serdes_lanes.tcl so repair buffers, CTS cells and DPL may use the whole lot.
uplevel #0 {
set slr_f $::env(RESULTS_DIR)/ot_serdes_lane_blocks.txt
if {[file exists $slr_f]} {
  set slr_want {}; set fh [open $slr_f r]; foreach l [split [read $fh] "\n"] { if {$l ne ""} { dict set slr_want $l 1 } }; close $fh
  set slr_n 0
  foreach k [[ord::get_db_block] getBlockages] {
    set bb [$k getBBox]
    if {[dict exists $slr_want "[$bb xMin],[$bb yMin],[$bb xMax],[$bb yMax]"]} { odb::dbBlockage_destroy $k; incr slr_n }
  }
  puts "OT_SERDES_LANES released $slr_n placement blockages"
}
}
