read_db /in/run/results/asap7/dp_slw_hc0__cl1bc59e1c/base/3_place.odb
set b [ord::get_db_block];set du [$b getDbUnitsPerMicron]
set f [open /out/hc0w_north_strip.tsv w]
foreach i [$b getInsts] {
 set bb [$i getBBox];set x [expr {([$bb xMin]+[$bb xMax])/2.0/$du}];set y [expr {([$bb yMin]+[$bb yMax])/2.0/$du}]
 if {$x<514.3 || $x>544.3 || $y<1314.3 || $y>1324.3} continue
 puts $f [join [list [$i getName] [[$i getMaster] getName] $x $y [$i getPlacementStatus]] "\t"]
}
close $f
