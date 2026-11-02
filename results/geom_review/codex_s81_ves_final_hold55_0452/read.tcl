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
source /out/geom_dump.tcl
exit
