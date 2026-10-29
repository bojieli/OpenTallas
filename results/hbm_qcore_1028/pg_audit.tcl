read_db /work/kit/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base/3_place.odb
set b [ord::get_db_block]
set u [expr {double([$b getDbUnitsPerMicron])}]
set m5 [[ord::get_db_tech] findLayer M5]
set tg [$b findTrackGrid $m5]
if {$tg ne "NULL"} {
 set tx [$tg getGridX]
 puts "TRACKX_FIRST [lrange $tx 0 4] DBU $u"
}
foreach bt [$b getBTerms] {
 set nm [$bt getName]
 if {![string match mp_isl* $nm]} continue
 foreach bp [$bt getBPins] {foreach bx [$bp getBoxes] {
  puts "PIN $nm [[$bx getTechLayer] getName] [expr {[$bx xMin]/$u}] [expr {[$bx yMin]/$u}] [expr {[$bx xMax]/$u}] [expr {[$bx yMax]/$u}]"
 }}
}
foreach n [$b getNets] {
 if {[$n getSigType] ni {POWER GROUND}} continue
 foreach sw [$n getSWires] {foreach bx [$sw getWires] {
  if {[$bx isVia]} continue
  set l [$bx getTechLayer]
  if {$l eq "NULL" || [$l getName] ne "M5"} continue
  set x0 [expr {[$bx xMin]/$u}];set y0 [expr {[$bx yMin]/$u}]
  set x1 [expr {[$bx xMax]/$u}];set y1 [expr {[$bx yMax]/$u}]
  foreach {cx cy} {56.16 86.4 151.176 112.32 168.48 103.68} {
   if {$x0<$cx+4 && $x1>$cx-4 && $y0<$cy+6 && $y1>$cy-6} {
    puts "PG [$n getName] M5 $x0 $y0 $x1 $y1";break
   }
  }
 }}
}
