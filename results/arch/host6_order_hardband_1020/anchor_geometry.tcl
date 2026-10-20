read_db /stage/cases/$::env(VARIANT)_none/out/hardband.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set f [open /stage/cases/$::env(VARIANT)_none/out/ot_out_flop_at_pins.txt r]
set anchors [split [string trim [read $f]] "\n"];close $f
set csv [open /stage/anchors_$::env(VARIANT).tsv w]
puts $csv "instance\txmin_um\tymin_um\txmax_um\tymax_um\toutside_model_band"
set xmin 1e9; set ymin 1e9; set xmax -1e9;set ymax -1e9;set outside 0;set area 0
set bandright [expr {$::env(VARIANT) eq "e" ? 300.24 : 343.44}]
foreach name $anchors {
 set i [$b findInst $name];set z [$i getBBox]
 set x0 [expr {[$z xMin]/double($u)}];set y0 [expr {[$z yMin]/double($u)}]
 set x1 [expr {[$z xMax]/double($u)}];set y1 [expr {[$z yMax]/double($u)}]
 set off [expr {$x0<2.16-1e-6 || $x1>$bandright+1e-6 || $y0<216-1e-6 || $y1>300.24+1e-6}]
 incr outside $off
 set xmin [expr {min($xmin,$x0)}];set ymin [expr {min($ymin,$y0)}]
 set xmax [expr {max($xmax,$x1)}];set ymax [expr {max($ymax,$y1)}]
 set area [expr {$area+($x1-$x0)*($y1-$y0)}]
 puts $csv "$name\t$x0\t$y0\t$x1\t$y1\t$off"
}
close $csv
puts "ORDER_ACTUAL_ANCHOR_GEOMETRY variant=$::env(VARIANT) count=[llength $anchors] bbox_um=$xmin,$ymin,$xmax,$ymax std_area_um2=$area outside_approved_band=$outside"
