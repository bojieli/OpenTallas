set ::codex_pch_rects {{122.526 23.946 125.118 77.262} {125.118 23.946 125.28 25.38} {125.118 76.14 125.28 77.262} {125.28 23.946 129.6 77.262} {224.424 23.946 228.744 77.358} {228.744 23.946 228.906 25.38} {228.744 76.14 228.906 77.358} {228.906 23.946 231.498 77.358} {122.526 80.106 125.118 133.422} {125.118 80.106 125.28 81.54} {125.118 132.3 125.28 133.422} {125.28 80.106 129.6 133.422} {224.424 80.106 228.744 133.518} {228.744 80.106 228.906 81.54} {228.744 132.3 228.906 133.518} {228.906 80.106 231.498 133.518} {122.526 136.266 125.118 189.582} {125.118 136.266 125.28 137.7} {125.118 188.46 125.28 189.582} {125.28 136.266 129.6 189.582} {224.424 136.266 228.744 189.678} {228.744 136.266 228.906 137.7} {228.744 188.46 228.906 189.678} {228.906 136.266 231.498 189.678} {122.526 192.426 125.118 245.742} {125.118 192.426 125.28 193.86} {125.118 244.62 125.28 245.742} {125.28 192.426 129.6 245.742} {224.424 192.426 228.744 245.838} {228.744 192.426 228.906 193.86} {228.744 244.62 228.906 245.838} {228.906 192.426 231.498 245.838}}
# Preserve physical TAP/PG cells while applying pin-access placement strips.
set pb [ord::get_db_block];set pu [$pb getDbUnitsPerMicron];set pc [$pb getCoreArea]
set eligible {}
foreach r $::codex_pch_rects {
 lassign $r x0 y0 x1 y1
 set q [list [expr {max(round($x0*$pu),[$pc xMin])}] [expr {max(round($y0*$pu),[$pc yMin])}] [expr {min(round($x1*$pu),[$pc xMax])}] [expr {min(round($y1*$pu),[$pc yMax])}]]
 dict set eligible $q 1
}
set taps {}
foreach i [$pb getInsts] {if {[string match TAPCELL* [[$i getMaster] getName]]} {set q [$i getBBox];lappend taps [list [expr {[$q xMin]-54}] [$q yMin] [expr {[$q xMax]+54}] [$q yMax]]}}
proc codex_subrect {r h} {
 lassign $r x y X Y;lassign $h a b A B
 if {$X<=$a || $x>=$A || $Y<=$b || $y>=$B} {return [list $r]}
 set a [expr {max($x,$a)}];set A [expr {min($X,$A)}];set b [expr {max($y,$b)}];set B [expr {min($Y,$B)}]
 set out {};foreach q [list [list $x $y $a $Y] [list $A $y $X $Y] [list $a $y $A $b] [list $a $B $A $Y]] {lassign $q x0 y0 x1 y1;if {$x1>$x0 && $y1>$y0} {lappend out $q}}
 return $out
}
set moved 0
foreach blk [$pb getBlockages] {
 set q [$blk getBBox];set r [list [$q xMin] [$q yMin] [$q xMax] [$q yMax]]
 if {![dict exists $eligible $r]} continue
 set pieces [list $r]
 foreach t $taps {set next {};foreach p $pieces {lappend next {*}[codex_subrect $p $t]};set pieces $next}
 if {$pieces eq [list $r]} continue
 odb::dbBlockage_destroy $blk
 foreach p $pieces {odb::dbBlockage_create $pb {*}$p}
 incr moved
}
puts "R9_TAP_HOLES reshaped $moved pin-strip blockages; all TAP cells/PG retained"
