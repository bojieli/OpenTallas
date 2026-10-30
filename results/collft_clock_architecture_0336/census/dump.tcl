read_db /odb/3_place.odb
set b [ord::get_db_block]
set db [ord::get_db]
set f [open /work/census/sinks.txt r];set o [open /work/census/clock_pins.tsv w]
puts $o "name\tmaster\tpin\tx_dbu\ty_dbu\tnet"
set n 0
while {[gets $f name]>=0} {
 set i [$b findInst $name];if {$i eq "NULL"} {error "MISSING_ACTUAL_SINK $name"}
 set it [$i findITerm CLK];if {$it eq "NULL"} {error "MISSING_ACTUAL_CLK $name"}
 set v [$it getAvgXY]
 if {[llength $v]==3} {lassign $v ok x y;if {!$ok} {error "NO_CLK_GEOMETRY $name"}} elseif {[llength $v]==2} {lassign $v x y} else {error "BAD_CLK_GEOMETRY $name"}
 puts $o "$name\t[[$i getMaster] getName]\tCLK\t$x\t$y\t[[$it getNet] getName]";incr n
}
close $f;close $o
set o [open /work/census/all_bodies.tsv w];puts $o "name\tmaster\tstatus\torient\tx0\ty0\tx1\ty1"
foreach i [$b getInsts] {set q [$i getBBox];puts $o "[$i getName]\t[[$i getMaster] getName]\t[$i getPlacementStatus]\t[$i getOrient]\t[$q xMin]\t[$q yMin]\t[$q xMax]\t[$q yMax]"}
close $o
set o [open /work/census/rows.tsv w];puts $o "ordinal\tname\trx\try\torient\tsite_width\tsite_height\tx0\ty0\tx1\ty1"
set k 0
foreach r [$b getRows] {lassign [$r getOrigin] x y;set s [$r getSite];set q [$r getBBox];puts $o "$k\t[$r getName]\t$x\t$y\t[$r getOrient]\t[$s getWidth]\t[$s getHeight]\t[$q xMin]\t[$q yMin]\t[$q xMax]\t[$q yMax]";incr k}
close $o
set o [open /work/census/buffer_masters.tsv w];puts $o "master\twidth\theight"
foreach name {BUFx6f_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx16f_ASAP7_75t_R BUFx24_ASAP7_75t_R} {set m [$db findMaster $name];if {$m eq "NULL"} {error "MISSING_BUFFER_MASTER $name"};puts $o "$name\t[$m getWidth]\t[$m getHeight]"}
close $o
puts "COLLFT_ACTUAL_CLOCK_PINS_PASS sinks=$n rows=$k no_placement_or_STA"
