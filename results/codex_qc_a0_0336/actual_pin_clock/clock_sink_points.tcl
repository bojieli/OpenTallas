read_db /work/clock_installed.odb
set b [ord::get_db_block]
set f [open /work/leaf_sinks.txt r];set o [open /work/clock_sink_points.tsv w]
puts $o "sink\tx\ty"
set n 0
while {[gets $f name]>=0} {
 set cut [string last / $name];set inst [string range $name 0 [expr {$cut-1}]];set pin [string range $name [expr {$cut+1}] end]
 set i [$b findInst $inst];if {$i eq "NULL"} {error "PIN_GEOMETRY_MISSING_INST $name"}
 set it [$i findITerm $pin];if {$it eq "NULL"} {error "PIN_GEOMETRY_MISSING_PIN $name"}
 set v [$it getAvgXY]
 if {[llength $v]==3} {lassign $v ok x y;if {!$ok} {error "PIN_GEOMETRY_NO_AVERAGE $name"}} elseif {[llength $v]==2} {lassign $v x y} else {error "PIN_GEOMETRY_INVALID $name $v"}
 puts $o "$name\t$x\t$y";incr n
}
close $o;close $f
puts "A0_ACTUAL_CLOCK_SINK_PIN_GEOMETRY_PASS $n"
