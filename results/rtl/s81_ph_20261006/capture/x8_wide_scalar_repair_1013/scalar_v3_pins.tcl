read_db /base/3_2_place_iop.odb
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set n 0
foreach bt [$block getBTerms] {
 if {[$bt getName] ni {ck ck[0] ckv ckv[0] rst rst[0] rsv rsv[0] t_ho t_ho[0] f_w[1] f_w[248]}} continue
 incr n
 foreach bp [$bt getBPins] {
  foreach box [$bp getBoxes] {
   puts "PIN_RECT [$bt getName] [[$box getTechLayer] getName] [expr {[$box xMin]/double($dbu)}] [expr {[$box yMin]/double($dbu)}] [expr {[$box xMax]/double($dbu)}] [expr {[$box yMax]/double($dbu)}]"
  }
 }
}
if {$n != 7} {error "expected 7 actual assigned pins, got $n"}
exit
