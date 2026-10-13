# Keep VIA45 landing pads out of the M4 SRAM interior obstruction at the vertical edges.
# M4 OBS ends 0.072um before the edge; pins occupy the last 0.024um. Restrict
# the interior M5 via track and retain M4 planar access and exterior M5 access.
set cx_caller [dict get [info frame -1] file]
set cx_stage [file tail $cx_caller]
puts "CX_SU_SWE SRAM hook invoked caller=$cx_stage"
if {[string match *pre_grt.tcl $cx_stage] || [string match *post_drt.tcl $cx_stage]} {
  set b [ord::get_db_block]
  set t [[ord::get_db] getTech]
  set u [$b getDbUnitsPerMicron]
  set rects {}
  foreach i [$b getInsts] {
    if {[[$i getMaster] getName] ne "ot_sram_1r1w_128x256_m1_r2c2"} continue
    set r [$i getBBox]
    lappend rects [list [expr {[$r xMax]-round(0.30*$u)}] [$r yMin] [expr {[$r xMax]-round(0.024*$u)}] [$r yMax]]
  }
  foreach i [$b getInsts] {
    if {[[$i getMaster] getName] ne "ot_sram_1r1w_128x256_m1_r2c2"} continue
    set r [$i getBBox]
    lappend rects [list [expr {[$r xMin]+round(0.024*$u)}] [$r yMin] [expr {[$r xMin]+round(0.30*$u)}] [$r yMax]]
  }
  set count 0
  if {[string match *pre_grt.tcl $cx_stage]} {
    foreach r $rects { odb::dbObstruction_create $b [$t findLayer M5] {*}$r; incr count }
    if {$count != 4} { error "CX_SU_SWE expected 4 guards, created $count" }
    puts "CX_SU_SWE SRAM access keepout created $count"
  } else {
    foreach o [$b getObstructions] {
      set r [$o getBBox]
      if {[[$r getTechLayer] getName] ne "M5"} continue
      set k [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
      if {[lsearch -exact $rects $k] >= 0} { odb::dbObstruction_destroy $o; incr count }
    }
    if {$count != 4} { error "CX_SU_SWE expected 4 guards, removed $count" }
    puts "CX_SU_SWE SRAM access keepout removed $count"
  }
}
