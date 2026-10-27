# HBM-CORE-LAT-R3: placed planned clock-tree cells (mp_ck_*) + clk net summary.  env ODB OUT
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
proc um {v} { return [format %.3f [expr {$v / double($::u)}]] }
set f [open $::env(OUT) w]; set n 0
foreach i [$b getInsts] { if {![string match mp_ck_* [$i getName]]} continue
  set q [$i getBBox]; puts $f "TREE [$i getName] [um [expr {([$q xMin]+[$q xMax])/2}]] [um [expr {([$q yMin]+[$q yMax])/2}]] [[$i getMaster] getName] [$i getPlacementStatus] [$i isDoNotTouch]"; incr n }
close $f; puts "DUMP_TREE $n"; exit
