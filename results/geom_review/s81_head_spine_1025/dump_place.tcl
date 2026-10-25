read_db $::env(ODB)
set f [open $::env(OUT) w]
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set die [$b getDieArea]
puts $f "DIE\t[expr {[$die xMax]/double($dbu)}]\t[expr {[$die yMax]/double($dbu)}]"
foreach i [$b getInsts] { set m [[$i getMaster] getName]; if {[regexp {^(TAPCELL|FILLER|DECAP)} $m]} continue; set bb [$i getBBox]; puts $f "I\t[$i getName]\t$m\t[expr {[$bb xMin]/double($dbu)}]\t[expr {[$bb yMin]/double($dbu)}]\t[expr {[$bb xMax]/double($dbu)}]\t[expr {[$bb yMax]/double($dbu)}]" }
foreach t [$b getBTerms] { foreach p [$t getBPins] { set bb [$p getBBox]; puts $f "P\t[$t getName]\t[$t getIoType]\t[expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}]\t[expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}]" } }
proc ctr {i dbu} { set bb [$i getBBox]; return [list [expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}] [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}]] }
proc isbuf {i} { return [regexp {^(BUF|INV|HB)} [[$i getMaster] getName]] }
proc isff {i} { return [string match *DFF* [[$i getMaster] getName]] }
proc ffsinks {n depth} {
  set out {}
  if {$depth > 40} { return $out }
  foreach it [$n getITerms] {
    if {[$it isOutputSignal]} continue
    set i [$it getInst]
    if {[isff $i]} { lappend out $i } elseif {[isbuf $i]} {
      foreach o [$i getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { set out [concat $out [ffsinks [$o getNet] [expr {$depth+1}]]] } } }
  }
  return $out
}
proc ffsrc {n depth} {
  if {$depth > 40} { return "" }
  foreach it [$n getITerms] {
    if {![$it isOutputSignal]} continue
    set i [$it getInst]
    if {[isff $i]} { return $i }
    if {[isbuf $i]} { foreach x [$i getITerms] { if {[$x isInputSignal] && [$x getNet] ne "NULL"} { return [ffsrc [$x getNet] [expr {$depth+1}]] } } }
    return "LOGIC:[$i getName]"
  }
  return ""
}
foreach t [$b getBTerms] {
  set n [$t getNet]; if {$n eq "NULL"} continue
  if {[$t getSigType] ne "SIGNAL"} continue
  set bb [[lindex [$t getBPins] 0] getBBox]
  set px [expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}]; set py [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}]
  if {[$t getIoType] eq "INPUT"} { set l [ffsinks $n 0]; set i [lindex $l 0] } else { set i [ffsrc $n 0] }
  if {$i eq "" || [string match LOGIC:* $i]} { puts $f "PR\t[$t getName]\t[$t getIoType]\t$px\t$py\t-\t-1\t-1\t-1\t$i"; continue }
  set c [ctr $i $dbu]; puts $f "PR\t[$t getName]\t[$t getIoType]\t$px\t$py\t[$i getName]\t[lindex $c 0]\t[lindex $c 1]\t[expr {abs($px-[lindex $c 0])+abs($py-[lindex $c 1])}]"
}
foreach i [$b getInsts] {
  if {![isff $i]} continue
  set a [ctr $i $dbu]
  foreach o [$i getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} {
    foreach s [ffsinks [$o getNet] 0] { set c [ctr $s $dbu]; puts $f "RR\t[$i getName]\t[lindex $a 0]\t[lindex $a 1]\t[$s getName]\t[lindex $c 0]\t[lindex $c 1]\t[expr {abs([lindex $a 0]-[lindex $c 0])+abs([lindex $a 1]-[lindex $c 1])}]" } } }
}
close $f
