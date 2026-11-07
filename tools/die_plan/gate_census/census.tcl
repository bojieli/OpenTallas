# Read-only dump of instances, signal nets and pins for gate_rehome.py.  env ODB, OT_OUT.
read_db $::env(ODB)
set blk [ord::get_db_block]
set o [open $::env(OT_OUT) w]
foreach i [$blk getInsts] {
  set m [[$i getMaster] getName]
  if {[$i isBlock]} { set kind M } elseif {[regexp {^(DFF|DHL|DLL|ICG)} $m]} { set kind F } elseif {[regexp {^(BUF|HB)} $m]} { set kind B } elseif {[regexp {^(TIE|FILLER|TAP)} $m]} { continue } else { set kind G }
  set b [$i getBBox]
  set ins {}; set outs {}
  foreach it [$i getITerms] { set n [$it getNet]; if {$n eq "NULL"} continue; if {[$n getSigType] ne "SIGNAL"} continue
    if {[$it isInputSignal]} { lappend ins [$n getName] } elseif {[$it isOutputSignal]} { lappend outs [$n getName] } }
  puts $o "I\t[$i getName]\t$m\t$kind\t[$b xMin]\t[$b yMin]\t[$b xMax]\t[$b yMax]\t[join $ins ,]\t[join $outs ,]\t[$i getPlacementStatus]\t[$i isDoNotTouch]"
}
foreach bt [$blk getBTerms] { set n [$bt getNet]; if {$n eq "NULL"} continue; set bb [$bt getBBox]; puts $o "P\t[$bt getName]\t[$n getName]\t[$bt getIoType]\t[$bb xMin]\t[$bb yMin]" }
set r [$blk getCoreArea]; puts $o "C\t[$r xMin]\t[$r yMin]\t[$r xMax]\t[$r yMax]"
close $o
