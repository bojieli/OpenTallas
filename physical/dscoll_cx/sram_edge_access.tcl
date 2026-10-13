# Keep VIA45 landing pads out of the M4 SRAM interior obstruction at the E edge.
# M4 OBS ends 0.072um before the edge; pins occupy the last 0.024um. Restrict
# the interior M5 via track and retain M4 planar access and exterior M5 access.
set cx_caller [dict get [info frame -1] file]
puts "CX_COLL SRAM access hook caller $cx_caller"
if {[string match {*pre_grt.tcl} [file tail $cx_caller]] || [string match {*post_drt.tcl} [file tail $cx_caller]]} {
  set b [ord::get_db_block]
  set t [[ord::get_db] getTech]
  set u [$b getDbUnitsPerMicron]
  set rects {}
  foreach i [$b getInsts] {
    if {[[$i getMaster] getName] ne "ot_sram_1r1w_512x128_m4_r2c2"} continue
    set r [$i getBBox]
    lappend rects [list [expr {[$r xMax]-round(0.30*$u)}] [$r yMin] [expr {[$r xMax]-round(0.024*$u)}] [$r yMax]]
  }
  if {[llength $rects] != 10} { error "CX_COLL expected 10 SRAM access strips, got [llength $rects]" }
  set count 0
  if {[string match {*pre_grt.tcl} [file tail $cx_caller]]} {
    foreach r $rects { odb::dbObstruction_create $b [$t findLayer M5] {*}$r; incr count }
    puts "CX_COLL SRAM E access keepout created $count"
  } else {
    foreach o [$b getObstructions] {
      set r [$o getBBox]
      if {[[$r getTechLayer] getName] ne "M5"} continue
      set k [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
      if {[lsearch -exact $rects $k] >= 0} { odb::dbObstruction_destroy $o; incr count }
    }
    if {$count != 10} { error "CX_COLL expected removal of 10 SRAM access strips, got $count" }
    puts "CX_COLL SRAM E access keepout removed $count"
  }
}
