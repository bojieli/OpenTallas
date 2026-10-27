# QC-SU-KITS-2: plan-model geometry from the MIF0 3_place.odb (same format as master-plan-r4 su_refloor *.geo):
# DIE / CORE / PIN ck / MACRO inst master bbox CK pin / SINK clk-pin-xy master inst pin (every clock-pin std cell on net ck)
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
proc um {v} { return [format %.3f [expr {$v / double($::u)}]] }
set d [$b getDieArea]; puts $f "DIE [um [$d xMin]] [um [$d yMin]] [um [$d xMax]] [um [$d yMax]]"
set c [$b getCoreArea]; puts $f "CORE [um [$c xMin]] [um [$c yMin]] [um [$c xMax]] [um [$c yMax]]"
set bt [$b findBTerm ck]; set bb [$bt getBBox]
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
  if {[string match ot_ms_* [$i getName]]} { incr other; continue }
  puts $f "SINK $x $y [$m getName] [$i getName] [[$it getMTerm] getName]"; incr ns
}
puts $f "ISLCOUNT 0"
close $f
puts "DUMP_GEO sinks $ns macros $nm skipped_ot_ms $other"
exit
