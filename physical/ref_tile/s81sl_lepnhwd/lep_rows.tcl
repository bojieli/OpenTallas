# S81-RTLFIX 10-20: keep only the 120 full-width rows of the band y 259.2..291.6; must precede tapcell (sourced from place.tcl)
set ot_lr_b [ord::get_db_block]
set ot_lr_u [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_lr_rm {}; set ot_lr_keep 0
foreach r [$ot_lr_b getRows] {
  set bb [$r getBBox]
  if {[$bb yMin] < round(259.2*$ot_lr_u) || [$bb yMax] > round(291.6*$ot_lr_u)} { lappend ot_lr_rm $r; continue }
  if {[$bb xMin] > round(2.16*$ot_lr_u) || [$bb xMax] < round(473.04*$ot_lr_u)} { error "LEP_ROWS not full-width [$r getName]" }
  incr ot_lr_keep
}
foreach r $ot_lr_rm { odb::dbRow_destroy $r }
if {$ot_lr_keep != 120} { error "LEP_ROWS expected 120 band rows, got $ot_lr_keep" }
puts "LEP_ROWS kept=$ot_lr_keep removed=[llength $ot_lr_rm] band=2.16 259.2 473.04 291.6"
