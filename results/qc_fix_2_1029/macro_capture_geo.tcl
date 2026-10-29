# QC-FIX-2 probe (read-only): capture-drift census for hard-macro read captures (same definition as
# shared macro_pin_flops.tcl case (a): macro output pin -> <=4 single-fanout INV/BUF/HB -> one flop D).
# Reports per capture: macro, pin xy, flop xy, Manhattan distance (um). ENV: ODB OUT
read_db $::env(ODB)
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc isff {i} { set m [[$i getMaster] getName]; expr {[string match "DFF*" $m] || [string match "ASYNC_DFF*" $m] || [string match "SDF*" $m]} }
proc isbuf {i} { set m [[$i getMaster] getName]; expr {[string match "INV*" $m] || [string match "BUF*" $m] || [string match "HB*" $m]} }
set fh [open $::env(OUT) w]
puts $fh "macro\tmaster\tpin\tpx\tpy\tflop\tfx\tfy\tdist"
foreach m [$b getInsts] {
  if {![[$m getMaster] isBlock]} continue
  foreach it [$m getITerms] {
    if {![$it isOutputSignal]} continue
    set net [$it getNet]; if {$net eq "NULL"} continue
    set p [$it getAvgXY]; if {![lindex $p 0]} { set bb [$it getBBox]; set p [list 1 [expr {([$bb xMin]+[$bb xMax])/2}] [expr {([$bb yMin]+[$bb yMax])/2}]] }
    set ff ""
    for {set h 0} {$h <= 4} {incr h} {
      if {[llength [$net getBTerms]]} break
      set s {}; foreach x [$net getITerms] { if {[$x isInputSignal]} { lappend s $x } }
      if {[llength $s] != 1} break
      set i [[lindex $s 0] getInst]
      if {[isff $i]} { if {[[[lindex $s 0] getMTerm] getName] eq "D"} { set ff $i }; break }
      if {![isbuf $i]} break
      set net ""; foreach x [$i getITerms] { if {[$x isOutputSignal]} { set net [$x getNet] } }
      if {$net eq "" || $net eq "NULL"} break
    }
    if {$ff eq ""} continue
    set fb [$ff getBBox]
    set fx [expr {([$fb xMin]+[$fb xMax])/2.0/$dbu}]; set fy [expr {([$fb yMin]+[$fb yMax])/2.0/$dbu}]
    set px [expr {[lindex $p 1]/double($dbu)}]; set py [expr {[lindex $p 2]/double($dbu)}]
    puts $fh "[$m getName]\t[[$m getMaster] getName]\t[[$it getMTerm] getName]\t$px\t$py\t[$ff getName]\t$fx\t$fy\t[expr {abs($fx-$px)+abs($fy-$py)}]"
  }
}
close $fh
puts "MCG_DONE"
exit
