# S81-CORE-LAT-R6: plan-model geometry (su_tree_uf / su_kit_gate GEO format) from a placed core ODB.
# env ODB OUT CLK [ENTRY "x y" = plan clock entry, default outline centre (12.8a centre entry)]
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
proc um {v} { return [format %.3f [expr {$v / double($::u)}]] }
set d [$b getDieArea]; puts $f "DIE [um [$d xMin]] [um [$d yMin]] [um [$d xMax]] [um [$d yMax]]"
set c [$b getCoreArea]; puts $f "CORE [um [$c xMin]] [um [$c yMin]] [um [$c xMax]] [um [$c yMax]]"
if {[info exists ::env(ENTRY)] && $::env(ENTRY) ne ""} { lassign $::env(ENTRY) ex ey } else {
  set ex [um [expr {([$d xMin]+[$d xMax])/2}]]; set ey [um [expr {([$d yMin]+[$d yMax])/2}]] }
puts $f "PIN ck $ex $ey"
set bt [$b findBTerm $::env(CLK)]
set net [$bt getNet]; set ns 0; set nm 0; set nb 0
foreach it [$net getITerms] {
  set i [$it getInst]; set m [$i getMaster]
  set ib [$it getBBox]; set x [um [expr {([$ib xMin]+[$ib xMax])/2}]]; set y [um [expr {([$ib yMin]+[$ib yMax])/2}]]
  if {[$m isBlock]} {
    set r [$i getBBox]
    puts $f "MACRO [$i getName] [$m getName] [um [$r xMin]] [um [$r yMin]] [um [$r xMax]] [um [$r yMax]] [[$it getMTerm] getName] $x $y"; incr nm; continue
  }
  if {[[$it getMTerm] getSigType] ne "CLOCK" && ![$it isInputSignal]} continue
  if {[string match {*BUF*} [$m getName]] || [string match {*INV*} [$m getName]]} { incr nb; continue }
  puts $f "SINK $x $y [$m getName] [$i getName] [[$it getMTerm] getName]"; incr ns
}
puts $f "ISLCOUNT 0"
close $f
puts "DUMP_GEO sinks $ns macros $nm skipped_buf $nb"
exit
