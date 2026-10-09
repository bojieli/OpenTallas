# Unchanged unprotected source765470589, eight real38.016x62.910um ROMs.
# Fixed4x2 geometry at real input-pin centroid; gapX12.084/gapY12.090um.
set eng_block [ord::get_db_block]
set eng_dbu [$eng_block getDbUnitsPerMicron]
set eng_index 0
foreach eng_inst [lsort -dictionary [$eng_block getInsts]] {
  # Names retain escaped Verilog array brackets in actual synthesized ODB.
  set eng_name [$eng_inst getName]
  if {![regexp {^map\.m\\?\[([0-7])\\?\]\.rom$} $eng_name -> eng_bank]} {continue}
  set eng_x [expr {70.0 + ($eng_bank % 4) * 50.1}]
  set eng_y [expr {68.0 + ($eng_bank / 4) * 75.0}]
  $eng_inst setPlacementStatus PLACED
  $eng_inst setOrient R0
  $eng_inst setLocation [expr {int(round($eng_x*$eng_dbu))}] [expr {int(round($eng_y*$eng_dbu))}]
  $eng_inst setPlacementStatus LOCKED
  incr eng_index
}
if {$eng_index != 8} {error "Engram placement matched $eng_index ROMs, expected8"}
# Defensive hard blockage for every residual positive gap<12um, if this
# placement is later changed. The current gapX/gapY geometry creates none.
set eng_macros {}
foreach eng_i [$eng_block getInsts] {
 if {[[$eng_i getMaster] getType] ne "BLOCK"} {continue}
 lappend eng_macros $eng_i
}
set eng_n 0
foreach eng_a $eng_macros {
 set eng_ab [$eng_a getBBox]
 foreach eng_b $eng_macros {
  if {[string compare [$eng_a getName] [$eng_b getName]] >= 0} {continue}
  set eng_bb [$eng_b getBBox]
  set eng_rect {}
  set eng_lo [expr {max([$eng_ab yMin],[$eng_bb yMin])}]
  set eng_hi [expr {min([$eng_ab yMax],[$eng_bb yMax])}]
  if {$eng_hi>$eng_lo} {
   set eng_xlo [expr {min([$eng_ab xMax],[$eng_bb xMax])}]
   set eng_xhi [expr {max([$eng_ab xMin],[$eng_bb xMin])}]
   if {$eng_xhi>$eng_xlo && $eng_xhi-$eng_xlo<12*$eng_dbu} {set eng_rect [list $eng_xlo $eng_lo $eng_xhi $eng_hi]}
  }
  set eng_lo [expr {max([$eng_ab xMin],[$eng_bb xMin])}]
  set eng_hi [expr {min([$eng_ab xMax],[$eng_bb xMax])}]
  if {$eng_hi>$eng_lo} {
   set eng_ylo [expr {min([$eng_ab yMax],[$eng_bb yMax])}]
   set eng_yhi [expr {max([$eng_ab yMin],[$eng_bb yMin])}]
   if {$eng_yhi>$eng_ylo && $eng_yhi-$eng_ylo<12*$eng_dbu} {set eng_rect [list $eng_lo $eng_ylo $eng_hi $eng_yhi]}
  }
  if {[llength $eng_rect]} {
   lassign $eng_rect eng_lx eng_ly eng_hx eng_hy
   odb::dbBlockage_create $eng_block $eng_lx $eng_ly $eng_hx $eng_hy
   incr eng_n
  }
 }
}
puts "ENGRAM_GEOMETRY macros=$eng_index residual_slivers_blocked=$eng_n"

