set ::env(OT_GATE_SIGNOFF_SDC) /src/physical/ref_tile/dsfd_gth_rw/signoff.sdc
# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    set w [string map {_tt.lib _tt.lib} $w]
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}
read_db /work/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_gate/base/3_4_place_resized.odb
set ::env(RESULTS_DIR) /probe
set ::env(S81_MIDPOINT_REPORT) /probe/anchor.tsv
source /src/physical/dsrom_window_source/leaf_inhold_release.tcl
source /src/physical/qwen_die_masters/out_flop_release.tcl
source /probe/anchor.tcl
set_placement_padding -global -left 0 -right 0
detailed_placement
improve_placement
optimize_mirroring
check_placement -verbose
write_db /probe/probe.odb
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set n 0;set worst 0.0;set bad 0
set f [open /probe/reach.tsv w]
puts $f "output\tinput\tflop\tmaster\torient\tD_x\tD_y\tQ_x\tQ_y\tinput_to_D_manhattan\tQ_to_output_manhattan\tinput_to_D_euclidean\tQ_to_output_euclidean"
foreach i [$b getInsts] {
 if {![regexp {^DFF} [[$i getMaster] getName]]} continue
 regsub -all {\\} [$i getName] {} name
 if {[regexp {^u_l\.lo\[([0-9]+)\]\$_DFF} $name -> bit]} {set output "lo\[$bit\]";set input "li\[[expr {$bit+276}]\]"} elseif {[regexp {^u_l\.co(?:_state)?\[([0-9]+)\]\$_DFF} $name -> bit] && $bit>=212} {set output "co\[$bit\]";set input "ci\[[expr {$bit-212}]\]"} else {continue}
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
