# QC-SU-LAT-R2 read-only geometry dump: core, macros (+clk pin), register clock sinks, cells in island window.
# env: P_ODB P_OUT P_IX P_IY (island centre um) P_IS (island side um)
read_db $::env(P_ODB)
set blk [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
proc um {v} { return [format %.3f [expr {double($v)/$::u}]] }
set fo [open $::env(P_OUT) w]
set c [$blk getCoreArea]; set d [$blk getDieArea]
puts $fo "DIE [um [$d xMin]] [um [$d yMin]] [um [$d xMax]] [um [$d yMax]]"
puts $fo "CORE [um [$c xMin]] [um [$c yMin]] [um [$c xMax]] [um [$c yMax]]"
set h [expr {$::env(P_IS)/2.0}]; set ix0 [expr {$::env(P_IX)-$h}]; set ix1 [expr {$::env(P_IX)+$h}]; set iy0 [expr {$::env(P_IY)-$h}]; set iy1 [expr {$::env(P_IY)+$h}]
foreach bt [$blk getBTerms] { if {[$bt getName] in {ck rst_n}} { foreach bp [$bt getBPins] { set b [$bp getBBox]; puts $fo "PIN [$bt getName] [um [$b xMin]] [um [$b yMin]]" } } }
set nin 0
foreach i [$blk getInsts] {
  set m [$i getMaster]; set b [$i getBBox]
  set x0 [um [$b xMin]]; set y0 [um [$b yMin]]; set x1 [um [$b xMax]]; set y1 [um [$b yMax]]
  if {[$m isBlock]} {
    set ck ""
    foreach it [$i getITerms] { if {[[$it getMTerm] getName] in {clk CLK ck}} { set bb [$it getBBox]; set ck "[um [expr {([$bb xMin]+[$bb xMax])/2}]] [um [expr {([$bb yMin]+[$bb yMax])/2}]]" } }
    puts $fo "MACRO [$i getName] [$m getName] $x0 $y0 $x1 $y1 CK $ck"; continue
  }
  if {$x1 > $ix0 && $x0 < $ix1 && $y1 > $iy0 && $y0 < $iy1} { incr nin; puts $fo "ISL [$i getName] [$m getName] [$i getPlacementStatus]" }
  foreach it [$i getITerms] {
    if {[[$it getMTerm] getSigType] eq "CLOCK" || ([[$it getMTerm] getName] eq "CLK" && [string match DFF* [$m getName]])} {
      puts $fo "SINK [um [expr {([$b xMin]+[$b xMax])/2}]] [um [expr {([$b yMin]+[$b yMax])/2}]] [$m getName]"
    }
  }
}
puts $fo "ISLCOUNT $nin"
close $fo
exit
