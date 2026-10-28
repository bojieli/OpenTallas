read_db /old/run/results/asap7/dp_coll_ftm/base/6_final.odb
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set bb [$b getDieArea]
puts "DIE [expr {[$bb xMin]/double($dbu)}] [expr {[$bb yMin]/double($dbu)}] [expr {[$bb xMax]/double($dbu)}] [expr {[$bb yMax]/double($dbu)}]"
set area 0.0; set n 0
# 20x20 um bins of functional cell area
array set B {}
foreach i [$b getInsts] {
 set m [$i getMaster];set ty [$m getType]
 if {![string match CORE* $ty] || $ty in {CORE_SPACER CORE_WELLTAP CORE_ANTENNACELL}} {continue}
 set a [expr {double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]
 set area [expr {$area+$a}]; incr n
 set bx [[$i getBBox] xMin]; set by [[$i getBBox] yMin]
 set k "[expr {int($bx/$dbu/20)}],[expr {int($by/$dbu/20)}]"
 if {[info exists B($k)]} {set B($k) [expr {$B($k)+$a}]} else {set B($k) $a}
}
puts "FUNC_CELLS $n AREA_UM2 $area"
set l {}
foreach k [array names B] {lappend l [list $k $B($k)]}
set l [lsort -real -decreasing -index 1 $l]
puts "BINS [llength $l] TOP [lrange $l 0 9]"
foreach w [$b getNets] { if {[$w getSigType] in {POWER GROUND}} {
  set cnt [dict create]
  foreach sw [$w getSWires] { foreach s [$sw getWires] { if {![$s isVia]} { set ly [[$s getTechLayer] getName]; dict incr cnt $ly } } }
  puts "PGNET [$w getName] $cnt"
}}
foreach bt [$b getBTerms] { if {[[$bt getNet] getSigType] in {POWER GROUND}} { foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] { puts "PGPIN [$bt getName] [[$bx getTechLayer] getName]"; break } } } }
exit
