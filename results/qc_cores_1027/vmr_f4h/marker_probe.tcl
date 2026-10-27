read_db /work/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m0/base/5_1_grt_f4g_clk.odb
set blk [ord::get_db_block]; set u [$blk getDbUnitsPerMicron]
proc um {v} { global u; return [format %.4f [expr {$v/double($u)}]] }
foreach nn {_02281_ _04805_ ot_ms_Q4B1L1_clk _02289_ net1183} {
  set n [$blk findNet $nn]
  puts "NET $nn sig [$n getSigType] nterms [llength [$n getITerms]]"
  foreach it [$n getITerms] {
    set i [$it getInst]; set b [$i getBBox]
    if {[$it isOutputSignal]} {set d O} else {set d I}
    set xy [$it getAvgXY]
    puts "  $d [$i getName] [[$i getMaster] getName] [[$it getMTerm] getName] bbox [um [$b xMin]] [um [$b yMin]] [um [$b xMax]] [um [$b yMax]]"
  }
}
# instances near the two markers
foreach {x y} {83.82 13.42 118.94 15.39} {
  set X [expr {int($x*$u)}]; set Y [expr {int($y*$u)}]
  foreach i [$blk getInsts] { set b [$i getBBox]
    if {[$b xMin] <= $X+300 && [$b xMax] >= $X-300 && [$b yMin] <= $Y+300 && [$b yMax] >= $Y-300} {
      puts "NEAR $x $y [$i getName] [[$i getMaster] getName] [um [$b xMin]] [um [$b yMin]] [um [$b xMax]] [um [$b yMax]] [$i getPlacementStatus]" } }
}
# VDD special shapes near marker 2
set n [$blk findNet VDD]
foreach sw [$n getSWires] { foreach bx [$sw getWires] {
  set X [expr {int(118.94*$u)}]; set Y [expr {int(15.39*$u)}]
  if {[$bx xMin] <= $X+400 && [$bx xMax] >= $X-400 && [$bx yMin] <= $Y+400 && [$bx yMax] >= $Y-400} {
    if {[$bx isVia]} {set l "via:[[$bx getBlockVia] getName][[$bx getTechVia] getName]"} else {set l [[$bx getTechLayer] getName]}
    puts "VDDSHAPE $l [um [$bx xMin]] [um [$bx yMin]] [um [$bx xMax]] [um [$bx yMax]]" } } }
# clock wire shapes near marker 1
set w [[$blk findNet ot_ms_Q4B1L1_clk] getWire]
if {$w ne "NULL"} { set dec [odb::dbWireDecoder]; }
