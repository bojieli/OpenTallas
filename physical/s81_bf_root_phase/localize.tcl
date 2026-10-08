# PRE_CTS for ROOT_PHASE=1 only. Fail closed if the physical branch disappears.
# Coordinates are read from the actual ICG, never guessed from a reduced block.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set gates {}; set phases {}; set inversions {}
foreach inst [$b getInsts] {
  set n [string map {/ .} [$inst getName]]
  if {[string match {*g_half.u_hcg.u_icg} $n]} {lappend gates $inst}
  if {[string match {*g_half.ph*} $n] && [string match {DFF*} [[$inst getMaster] getName]]} {lappend phases $inst}
  if {[string match {*g_half.g_root.u_inv?.u_inv} $n]} {lappend inversions $inst}
}
if {[llength $gates]!=1 || [llength $phases]!=1 || [llength $inversions]!=2} {
  error "BF_ROOT_PHASE expected 1 ICG/1 phase FF/2 inverters; got [llength $gates]/[llength $phases]/[llength $inversions]"
}
set gate [lindex $gates 0]
lassign [$gate getLocation] gx gy
set k 0
foreach inst [concat $inversions $phases] {
  # Let the legalizer select valid rows and resolve overlaps at the existing root.
  $inst setLocation [expr {$gx+int((5+5*$k)*$dbu)}] $gy
  $inst setPlacementStatus PLACED
  incr k
}
detailed_placement
foreach inst [concat $inversions $phases] {
  lassign [$inst getLocation] x y
  set span [expr {(abs($x-$gx)+abs($y-$gy))/double($dbu)}]
  if {$span>100.0} {error "BF_ROOT_PHASE legalization moved [$inst getName] $span um from ICG"}
  $inst setPlacementStatus FIRM
  # FIRM preserves physical locality. CTS must still disconnect/reconnect clock
  # pins; dont_touch here caused ODB-0370 on the first inverter's A pin.
  # Generated-clock and post-CTS/route census checks fail if CTS loses the branch.
  unset_dont_touch [get_cells [$inst getName]]
}
puts "BF_ROOT_PHASE_LOCALIZED 1 phase FF + 2 inverters within 100um of actual ICG"
