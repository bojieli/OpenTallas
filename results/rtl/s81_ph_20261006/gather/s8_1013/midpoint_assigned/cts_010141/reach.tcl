# Read-only actual legalized D/Q pin reach, all genuine forwarding state.
read_db /work/results/asap7/opentallas_TOP_asap7_ref_gate/base/4_1_cts.odb
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set n 0;set worst 0.0;set bad 0
set f [open /probe/reach.tsv w]
puts $f "output\tinput\tflop\tmaster\torient\tD_x\tD_y\tQ_x\tQ_y\tinput_to_D_manhattan\tQ_to_output_manhattan\tinput_to_D_euclidean\tQ_to_output_euclidean"
foreach i [$b getInsts] {
 if {![regexp {^DFF} [[$i getMaster] getName]]} continue
 regsub -all {\\} [$i getName] {} name
 if {[regexp {^u_l\.lo\[([0-9]+)\]\$_DFF} $name -> bit]} {set output "lo\[$bit\]";set input "li\[[expr {$bit+276}]\]"} elseif {[regexp {^u_l\.co\[([0-9]+)\]\$_DFF} $name -> bit] && $bit>=212} {set output "co\[$bit\]";set input "ci\[[expr {$bit-212}]\]"} else {continue}
 set dp [$i findITerm D];set qp [$i findITerm QN]
 if {$qp eq "NULL"} {set qp [$i findITerm Q]}
 if {$dp eq "NULL" || $qp eq "NULL"} {error "Missing D/Q pins on $name"}
 lassign [$dp getAvgXY] ok dx dy;if {!$ok} {error "Missing D geometry $name"}
 lassign [$qp getAvgXY] ok qx qy;if {!$ok} {error "Missing Q geometry $name"}
 foreach v {dx dy qx qy} {set $v [expr {[set $v]/double($dbu)}]}
 set ai [[$b findBTerm $input] getBBox];set ao [[$b findBTerm $output] getBBox]
 set ax [expr {([$ai xMin]+[$ai xMax])/2.0/$dbu}];set ay [expr {([$ai yMin]+[$ai yMax])/2.0/$dbu}]
 set zx [expr {([$ao xMin]+[$ao xMax])/2.0/$dbu}];set zy [expr {([$ao yMin]+[$ao yMax])/2.0/$dbu}]
 set md [expr {abs($dx-$ax)+abs($dy-$ay)}];set mq [expr {abs($qx-$zx)+abs($qy-$zy)}]
 set ed [expr {hypot($dx-$ax,$dy-$ay)}];set eq [expr {hypot($qx-$zx,$qy-$zy)}]
 set worst [expr {max($worst,$md,$mq)}];if {max($md,$mq)>100.0} {incr bad}
 puts $f "$output\t$input\t$name\t[[$i getMaster] getName]\t[$i getOrient]\t$dx\t$dy\t$qx\t$qy\t$md\t$mq\t$ed\t$eq";incr n
}
close $f
if {$n!=1464} {error "Expected1464 genuine used forwarding FFs, found$n"}
puts "S81_ACTUAL_CTS_REACH used_FFs $n max_D_Q_manhattan_um $worst pairs_above100 $bad"
exit
