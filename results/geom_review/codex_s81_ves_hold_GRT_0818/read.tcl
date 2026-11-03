read_db /input.odb
set b [ord::get_db_block]
set f [open /out/targets.tsv w]
set wanted {{chunk_kk.term[6].operand_line.g_ring.u.q[24]$_DFF_P_} {chunk_kk.term[6].add.u.x_bexp[1]$_DFF_P_} {_104726_}}
foreach i [$b getInsts] {
 set name [$i getName]
 regsub -all {\\} $name {} clean
 if {$clean ni $wanted} continue
 set bb [$i getBBox]
 puts $f [list CELL $name [[$i getMaster] getName] [$i getPlacementStatus] [$i getOrient] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
 foreach it [$i getITerms] {set nn [$it getNet];set nm NULL;if {$nn ne "NULL"} {set nm [$nn getName]};puts $f [list PIN $name [[$it getMTerm] getName] $nm]}
}
close $f
set fi [open /out/all_instances.tsv w]
foreach i [$b getInsts] {puts $fi [list INST [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]}
close $fi
set fp [open /out/PG_upper.tsv w]
foreach n [$b getNets] {
 if {[$n getSigType] ni {POWER GROUND}} continue
 foreach sw [$n getSWires] {
  foreach sh [$sw getWires] {
   if {[$sh isVia]} {set v [$sh getTechVia];if {$v eq "NULL"} {set v [$sh getBlockVia]};set ty "VIA:[$v getName]"} else {set ty [[$sh getTechLayer] getName]}
   puts $fp [list PG [$n getName] $ty [$sh xMin] [$sh yMin] [$sh xMax] [$sh yMax]]
  }
 }
}
close $fp
source /out/geom_dump.tcl
exit
