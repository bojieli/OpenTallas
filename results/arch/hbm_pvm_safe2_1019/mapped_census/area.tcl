read_db /work/1_synth_tie_split.odb
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set std 0.0;set mac 0.0;set counts [dict create]
foreach inst [$b getInsts] {
 set m [$inst getMaster];set a [expr {double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]
 if {[$m isBlock]} {set mac [expr {$mac+$a}]} else {set std [expr {$std+$a}]}
 dict incr counts [$m getName]
}
set f [open /work/actual_area.tsv w];puts $f "std_area_um2\t$std\nmacro_area_um2\t$mac\ninstances\t[llength [$b getInsts]]";close $f
set f [open /work/master_counts.tsv w];dict for {n c} $counts {puts $f "$n\t$c"};close $f
exit
