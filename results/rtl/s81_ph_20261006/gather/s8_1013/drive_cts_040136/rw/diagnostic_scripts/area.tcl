read_db [lindex [glob /work/results/asap7/*/base/4_1_cts.odb] 0]
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set area [dict create];set count [dict create]
foreach i [$b getInsts] {
 set m [$i getMaster];set n [$i getName]
 set kind std
 if {[$m isBlock]} {set kind macro}
 if {[regexp {^(clkbuf|delaybuf|dummy)} $n]} {set kind clock}
 if {[regexp {^hold} $n]} {set kind replacement_hold}
 if {[regexp {^(TAP_|FILL)} $n]} {set kind tap_fill}
 set a [expr {[$m getWidth]*[$m getHeight]/double($dbu*$dbu)}]
 if {![dict exists $area $kind]} {dict set area $kind 0.0}
 dict set area $kind [expr {[dict get $area $kind]+$a}]
 dict incr count $kind
}
set total 0.0
dict for {kind a} $area {incr total_dummy 0;set total [expr {$total+$a}];puts "S81_AREA $kind [dict get $count $kind] $a"}
set r [$b getCoreArea];set core [expr {([$r xMax]-[$r xMin])*([$r yMax]-[$r yMin])/double($dbu*$dbu)}]
puts "S81_AREA total $total core $core util [expr {$total/$core}]"
exit
