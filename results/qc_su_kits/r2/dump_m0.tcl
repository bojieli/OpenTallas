read_db [lindex [glob /work/run/results/asap7/*/base/5_1_grt.odb] 0]
set f [open /work/m0_grt_dump.txt w]
set b [ord::get_db_block]
set die [$b getDieArea]; puts $f "DIE [expr {[$die xMax]/1000.0}] [expr {[$die yMax]/1000.0}]"
foreach i [$b getInsts] {
  set bb [$i getBBox]; set m [$i getMaster]
  set x [expr {([$bb xMin]+[$bb xMax])/2000.0}]; set y [expr {([$bb yMin]+[$bb yMax])/2000.0}]
  if {[$m isBlock]} { puts $f "MACRO [$i getName] [expr {[$bb xMin]/1000.0}] [expr {[$bb yMin]/1000.0}] [expr {[$bb xMax]/1000.0}] [expr {[$bb yMax]/1000.0}]"; continue }
  set mn [$m getName]
  if {[string match ot_ms_* [$i getName]]} {
    set in ""; set out ""
    foreach it [$i getITerms] { set n [$it getNet]; if {$n eq "NULL" || [$it isInputSignal]==0 && [$it isOutputSignal]==0} continue
      if {[$it isInputSignal]} {set in [$n getName]} elseif {[$it isOutputSignal]} {set out [$n getName]} }
    puts $f "CLK [$i getName] $x $y $mn $in $out"; continue
  }
  if {[string match DFF* $mn]} {
    set cn ""; foreach it [$i getITerms] { if {[[$it getMTerm] getName] eq "CLK"} { set n [$it getNet]; if {$n ne "NULL"} {set cn [$n getName]} } }
    puts $f "FF $x $y $cn"; continue
  }
  if {[$m getType] eq "CORE"} { puts $f "STD $x $y" }
}
close $f
exit
