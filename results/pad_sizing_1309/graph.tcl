read_db /head/run/results/asap7/dp_hd_turn_a/base/6_final.odb
set b [ord::get_db_block];set d [$b getDbUnitsPerMicron];set a [$b getDieArea]
set f [open /out/graph.tsv w]
puts $f "DIE\t[expr {[$a xMax]/double($d)}]\t[expr {[$a yMax]/double($d)}]"
foreach i [$b getInsts] {
 set n [$i getName];set m [[$i getMaster] getName]
 if {![string match ot_prp_d* $n] && ![string match DFF* $m]} continue
 set bb [$i getBBox]
 puts $f "I\t$n\t$m\t[expr {([$bb xMin]+[$bb xMax])/2.0/$d}]\t[expr {([$bb yMin]+[$bb yMax])/2.0/$d}]"
}
close $f
