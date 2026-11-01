read_db /work/kernel_b/base.odb
set b [ord::get_db_block]
foreach i [$b getInsts] {
 if {![[$i getMaster] isBlock]} continue
 set bb [$i getBBox];set counts [dict create];set samples [dict create]
 foreach it [$i getITerms] {
  set mt [$it getMTerm]
  if {[$mt getSigType] in {POWER GROUND}} continue
  set p [$it getBBox];set x [expr {([$p xMin]+[$p xMax])/2.0}];set y [expr {([$p yMin]+[$p yMax])/2.0}]
  set candidates [list [list [expr {abs($x-[$bb xMin])}] W] [list [expr {abs($x-[$bb xMax])}] E] [list [expr {abs($y-[$bb yMin])}] S] [list [expr {abs($y-[$bb yMax])}] N]]
  set face [lindex [lindex [lsort -real -index 0 $candidates] 0] 1]
  dict incr counts $face
  if {![dict exists $samples $face]} {dict set samples $face [$mt getName]}
 }
 puts "MACRO_FACES [$i getName] $counts samples=$samples"
}
