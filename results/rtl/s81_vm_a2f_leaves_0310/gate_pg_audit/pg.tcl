read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_db $::env(AUDIT_ODB)
set block [ord::get_db_block]
array set counts {}
foreach n [$block getNets] {
 if {[$n getSigType] ni {POWER GROUND}} {continue}
 foreach sw [$n getSWires] {
  foreach s [$sw getWires] {
   if {[$s isVia]} {continue}
   set l [$s getTechLayer]
   set key "[$n getName]/[$l getName]"
   if {![info exists counts($key)]} {set counts($key) 0}
   incr counts($key)
  }
 }
}
foreach key [lsort [array names counts]] {puts "ACTUAL_PG $key $counts($key)"}
exit
