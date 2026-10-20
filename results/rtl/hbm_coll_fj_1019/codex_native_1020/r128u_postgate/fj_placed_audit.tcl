read_db $::env(AUDIT_ODB)
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set die [$b getDieArea]
set x0 1e30;set y0 1e30;set x1 -1e30;set y1 -1e30;set outside 0;set missing 0;set protectedmissing 0;set macropg {}
foreach i [$b getInsts] {
 set z [$i getBBox];set x0 [expr {min($x0,[$z xMin])}];set y0 [expr {min($y0,[$z yMin])}];set x1 [expr {max($x1,[$z xMax])}];set y1 [expr {max($y1,[$z yMax])}]
 if {[$z xMin]<[$die xMin] || [$z yMin]<[$die yMin] || [$z xMax]>[$die xMax] || [$z yMax]>[$die yMax]} {incr outside}
 set bad 0
 foreach t [$i getITerms] {if {[$t getSigType] ni {POWER GROUND}} continue;set n [$t getNet];if {$n eq "NULL" || $n eq ""} {incr missing;set bad 1}}
 if {$bad && [$i isDoNotTouch]} {incr protectedmissing}
 if {[[$i getMaster] isBlock]} {set ns {};foreach t [$i getITerms] {if {[$t getSigType] ni {POWER GROUND}} continue;set n [$t getNet];lappend ns [list [[$t getMTerm] getName] [expr {$n eq "NULL" || $n eq "" ? "" : [$n getName]}]]};lappend macropg [list [$i getName] [$i getOrient] [$i getLocation] $ns]}
}
puts "FJ_PLACED_GEOMETRY insts=[llength [$b getInsts]] bbox_um=[list [expr {$x0/double($u)}] [expr {$y0/double($u)}] [expr {$x1/double($u)}] [expr {$y1/double($u)}]] die_um=[list [expr {[$die xMax]/double($u)}] [expr {[$die yMax]/double($u)}]] outside=$outside all_bbox_pair_L1_upper_um=[expr {(($x1-$x0)+($y1-$y0))/double($u)}]"
puts "FJ_PG_BIRTH_PHASE missing_iterms=$missing donttouch_instances_with_missing=$protectedmissing macro=$macropg"
