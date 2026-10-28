read_db $::env(ODB)
set blk [ord::get_db_block]
set fh [open $::env(OUT) w]
set die [$blk getDieArea]
puts $fh "DIE [$die xMin] [$die yMin] [$die xMax] [$die yMax] [$blk getDefUnits]"
set net [$blk findNet ck]
foreach it [$net getITerms] {
  set inst [$it getInst]; set m [[$inst getMaster] getName]
  set bb [$it getBBox]
  set x [expr {([$bb xMin]+[$bb xMax])/2}]; set y [expr {([$bb yMin]+[$bb yMax])/2}]
  puts $fh "SINK [$inst getName] $m [[$it getMTerm] getName] $x $y [$it isInputSignal]"
}
foreach inst [$blk getInsts] {
  if {[[$inst getMaster] isBlock]} { set b [$inst getBBox]; puts $fh "MACRO [$inst getName] [[$inst getMaster] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax] [$inst getOrient]" }
}
foreach r [$blk getRows] { set b [$r getBBox]; puts $fh "ROW [$b xMin] [$b yMin] [$b xMax] [$b yMax]" ; break}
puts $fh "NROWS [llength [$blk getRows]]"
close $fh
