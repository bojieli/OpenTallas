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
source [file join [file dirname [info script]] sliver_block.tcl]
