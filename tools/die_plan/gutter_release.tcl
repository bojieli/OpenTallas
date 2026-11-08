# GENERATED copy of tools/die_plan/gutter_release.tcl (sourced by face_flops_release.tcl, PRE_DETAIL_PLACE).
# S81-TYPES-5 11-07 NARROW-GUTTER: gutter_block.tcl's placement blockages steer global placement only; they are removed
# before DPL, because tap cells and FIRM landing cells inside a gutter fail check_placement ("placed in rows",
# COLH10 vS DPL-0033 on 40592 cells).  Only the blockages listed in ot_gutter_block.txt are removed.
uplevel #0 {
set gr_f $::env(RESULTS_DIR)/ot_gutter_block.txt
if {[file exists $gr_f]} {
  set gr_blk [ord::get_db_block]
  set gr_u [[ord::get_db_tech] getDbUnitsPerMicron]
  set gr_want {}
  set fh [open $gr_f r]
  foreach ln [split [read $fh] "\n"] {
    if {$ln eq ""} continue
    lassign [split $ln "\t"] a b c d
    dict set gr_want "[expr {round($a * $gr_u)}],[expr {round($b * $gr_u)}],[expr {round($c * $gr_u)}],[expr {round($d * $gr_u)}]" 1
  }
  close $fh
  set gr_n 0
  foreach k [$gr_blk getBlockages] {
    set bb [$k getBBox]
    if {[dict exists $gr_want "[$bb xMin],[$bb yMin],[$bb xMax],[$bb yMax]"]} { odb::dbBlockage_destroy $k; incr gr_n }
  }
  puts "OT_GUTTER_BLOCK removed $gr_n of [dict size $gr_want] gutter placement blockages before DPL"
}
}
