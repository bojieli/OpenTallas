# HBM-CORE-LAT-R3 hcroot: plan-model geometry from 3_place.odb (format of results/qc_su_kits/r2/prog_m0_kit/dump_geo_m0.tcl;
# clock port name from OT_CLK_PORT, written as 'PIN ck' for core_infra_htree).  SINK = every clock-pin std cell on the port net.
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
proc um {v} { return [format %.3f [expr {$v / double($::u)}]] }
set d [$b getDieArea]; puts $f "DIE [um [$d xMin]] [um [$d yMin]] [um [$d xMax]] [um [$d yMax]]"
set c [$b getCoreArea]; puts $f "CORE [um [$c xMin]] [um [$c yMin]] [um [$c xMax]] [um [$c yMax]]"
set bt [$b findBTerm $::env(OT_CLK_PORT)]; set bb [$bt getBBox]
puts $f "PIN ck [um [expr {([$bb xMin]+[$bb xMax])/2}]] [um [expr {([$bb yMin]+[$bb yMax])/2}]]"
set net [$bt getNet]; set ns 0; set nm 0; set other 0
foreach it [$net getITerms] {
  set i [$it getInst]; set m [$i getMaster]
  set ib [$it getBBox]; set x [um [expr {([$ib xMin]+[$ib xMax])/2}]]; set y [um [expr {([$ib yMin]+[$ib yMax])/2}]]
  if {[$m isBlock]} {
    set r [$i getBBox]
    puts $f "MACRO [$i getName] [$m getName] [um [$r xMin]] [um [$r yMin]] [um [$r xMax]] [um [$r yMax]] [[$it getMTerm] getName] $x $y"; incr nm; continue
  }
  if {[[$it getMTerm] getSigType] ne "CLOCK" && ![$it isInputSignal]} continue
  puts $f "SINK $x $y [$m getName] [$i getName] [[$it getMTerm] getName]"; incr ns
}
close $f
puts "DUMP_GEO sinks $ns macros $nm"
exit
