# QC-PLAN-F4A: clock-tree cells (drivers of nets in the ck fanout cone that are buffers/inverters) + macros from the GRT DB
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[$b getTech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
foreach i [$b getInsts] {
  set m [$i getMaster]; set nm [$i getName]
  set bb [$i getBBox]
  set x [expr ([$bb xMin]+[$bb xMax])/2.0/$u]; set y [expr ([$bb yMin]+[$bb yMax])/2.0/$u]
  if {[$m isBlock]} { puts $f [format "MACRO %s %.3f %.3f %.3f %.3f" $nm [expr [$bb xMin]*1.0/$u] [expr [$bb yMin]*1.0/$u] [expr [$bb xMax]*1.0/$u] [expr [$bb yMax]*1.0/$u]]; continue }
  set ck 0
  foreach it [$i getITerms] { set n [$it getNet]; if {$n ne "NULL" && [$n getSigType] eq "CLOCK" && [$it isOutputSignal]} { set ck 1 } }
  if {$ck} { puts $f [format "CKBUF %s %s %.3f %.3f" $nm [$m getName] $x $y] } elseif {[string match "DFF*" [$m getName]]} { puts $f [format "FF %.3f %.3f" $x $y] }
}
close $f
puts CLK_DUMP_done
