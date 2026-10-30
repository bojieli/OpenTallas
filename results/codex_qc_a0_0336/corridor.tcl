read_db /work/diag/cts_prehold.odb
set b [ord::get_db_block]
set db [ord::get_db]
set tech [$db getTech]
foreach name {BUFx8_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx24_ASAP7_75t_R} {
 set m [$db findMaster $name]
 puts "MASTER $name [$m getWidth] [$m getHeight]"
}
foreach l [$tech getLayers] {
 if {[$l getRoutingLevel]>0} {puts "LAYER [$l getName] width[$l getWidth] spacing[$l getSpacing] pitch[$l getPitch]"}
}
set nstd 0;set nclk 0
foreach i [$b getInsts] {
 set m [$i getMaster];set loc [$i getLocation];lassign $loc x y
 if {$x<131328 || $x>=142152 || $y<834432 || $y>=974832} continue
 if {[$m isBlock]} continue
 incr nstd
 if {[string match mp_* [$i getName]]} {incr nclk}
}
puts "CORRIDOR_ACTUAL std$nstd clocks$nclk dbu[$b getDbUnitsPerMicron]"
set nrow 0
foreach r [$b getRows] {
 set box [$r getBBox]
 if {[$box xMin]<=136620 && [$box xMax]>=137592 && [$box yMin]<=906120 && [$box yMax]>=906120} {
  incr nrow;puts "ROW [$r getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax] site[[$r getSite] getWidth]"
 }
}
puts "ROW_COUNT $nrow"

set f [open /out/corridor_rows.tsv w]
puts $f "x0\ty0\tx1\ty1"
foreach r [$b getRows] {
 set q [$r getBBox]
 if {[$q xMax]-[$q xMin]>=1620 && [$q xMax]-[$q xMin]<=12000 && [$q yMin]>=660000} {puts $f "[$q xMin]\t[$q yMin]\t[$q xMax]\t[$q yMax]"}
}
close $f
set n 0;set area 0.
foreach i [$b getInsts] {
 set m [$i getMaster];lassign [$i getLocation] x y
 if {$x>=135648 && $x<137808 && $y>=834432 && $y<974832 && ![$m isBlock]} {incr n;set area [expr {$area+double([$m getWidth])*[$m getHeight]/1e6}]}
}
puts "NARROW_CORRIDOR std$n area$area nominal_area303.264"
