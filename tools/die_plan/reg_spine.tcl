# GENERATED-COPY of tools/die_plan/reg_spine.tcl (PRE_CTS, opt-in partition_types.<t>.reg_spine; DIE-HEAD-17).
# Register clock as a plan-placed SPINE + LOCAL TREES (METHODOLOGY 12.13b / 12.16e local form) and the hard-core EARLY
# TAPS (12.3 v5.0) as dedicated branches; plan data /work/reg_spine.json, planned by /work/reg_spine.py:
#   (0) the placed register clock sinks of the entry net are dumped; reg_spine.py writes reg_spine_plan.tcl (cfg, core
#       branches, trunk, k-means taps with per-tap pads) and reg_spine_assign.txt;
#   (1) root split: every sink of the clock entry net moves to net rsp_regs behind one root_cell at root_split_xy;
#   (2) per core tap: the core clock pin gets its own branch off the entry net: repeaters (root_cell) -> `stages` x
#       pad_cell abutted at xy -> root_cell driver -> the pin (stage count = plan data);
#   (3) trunk nodes (trunk_cell); per tap: pad x pad_cell + tap_cell driver -> net rsp_t<i>; sinks re-hung;
#   (4) CTS_ARGS: TritonCTS builds ONLY the tap nets (local trees) + cts_extra_nets.
# The kit tap_balance pass runs report-only (config.mk OT_TAP_REPORT_ONLY=1): the spine is balanced by the plan.
set rsp_blk [ord::get_db_block]
set rsp_db [ord::get_db]
set rsp_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
# (0) plan on the placed sinks
set fh [open /work/reg_spine_sinks.txt w]
set rsp_bt [$rsp_blk findBTerm clk]
foreach it [[$rsp_bt getNet] getITerms] {
  if {[$it isOutputSignal]} continue
  set i [$it getInst]; set r [$i getBBox]
  puts $fh "clk [$i getName] [[$i getMaster] getName] [[$it getMTerm] getName] [expr ([$r xMin]+[$r xMax])/2000.0] [expr ([$r yMin]+[$r yMax])/2000.0] [$i getPlacementStatus]"
}
close $fh
puts [exec python3 /work/reg_spine.py /work/reg_spine.json /work/reg_spine_sinks.txt /work]
source /work/reg_spine_plan.tcl
set rsp_status PLACED
if {[dict exists $rsp_cfg placement_status]} {
  set rsp_status [dict get $rsp_cfg placement_status]
}
if {$rsp_status ni {PLACED FIRM}} { error "REG_SPINE: invalid placement_status $rsp_status" }
lassign [dict get $rsp_cfg site_um] rsp_sw rsp_sh
lassign [dict get $rsp_cfg core_origin_um] rsp_ox rsp_oy
set rsp_pitch [dict get $rsp_cfg pad_pitch_um]
proc rsp_inst {name master x y} {
  global rsp_blk rsp_db rsp_dbu rsp_sw rsp_sh rsp_ox rsp_oy rsp_status
  set m [$rsp_db findMaster $master]
  if {$m eq "NULL"} { error "REG_SPINE: no master $master" }
  set i [odb::dbInst_create $rsp_blk $m $name]
  set sx [expr {$rsp_ox + round(($x - $rsp_ox) / $rsp_sw) * $rsp_sw}]
  set sy [expr {$rsp_oy + round(($y - $rsp_oy) / $rsp_sh) * $rsp_sh}]
  # setOrient transforms the existing origin/bbox. Set the orientation FIRST,
  # then ask OpenDB for the planned lower-left location; reversing these calls
  # shifts every MX body down one row and overlaps adjacent folded pad rows.
  if {(round(($sy - $rsp_oy) / $rsp_sh) % 2) == 1} { $i setOrient MX } else { $i setOrient R0 }
  $i setLocation [expr {round($sx * $rsp_dbu)}] [expr {round($sy * $rsp_dbu)}]
  $i setPlacementStatus $rsp_status
  return $i
}
proc rsp_net {name} { global rsp_blk; set n [odb::dbNet_create $rsp_blk $name]; $n setSigType CLOCK; return $n }
proc rsp_conn {inst pin net} { [$inst findITerm $pin] connect $net }
set rsp_entry [[$rsp_blk findBTerm [dict get $rsp_cfg entry_port]] getNet]
# (1) root split
set rsp_regs [rsp_net rsp_regs]
foreach it [$rsp_entry getITerms] { $it disconnect; $it connect $rsp_regs }
lassign [dict get $rsp_cfg root_split_xy] rsp_rx rsp_ry
set rsp_rs [rsp_inst rsp_rs [dict get $rsp_cfg root_cell] $rsp_rx $rsp_ry]
rsp_conn $rsp_rs A $rsp_entry; rsp_conn $rsp_rs Y $rsp_regs
# (2) core early-tap branches
foreach c $rsp_cores {
  lassign $c iname pinn x0 y0 ns reps
  set core [$rsp_blk findInst $iname]
  if {$core eq "NULL"} { error "REG_SPINE: core tap inst $iname not found" }
  set pin [$core findITerm $pinn]
  if {[$pin getNet] ne "NULL"} { $pin disconnect }
  set tag [regsub -all {[^A-Za-z0-9_]} [lindex [split $iname .] end] _]
  set src $rsp_entry; set k 0
  foreach r $reps {
    lassign $r rx ry
    set b [rsp_inst rsp_${tag}_r$k [dict get $rsp_cfg root_cell] $rx $ry]; set n [rsp_net rsp_${tag}_rn$k]
    rsp_conn $b A $src; rsp_conn $b Y $n; set src $n; incr k
  }
  for {set s 0} {$s < $ns} {incr s} {
    set b [rsp_inst rsp_${tag}_d$s [dict get $rsp_cfg pad_cell] [expr {$x0 + $s * $rsp_pitch}] $y0]; set n [rsp_net rsp_${tag}_dn$s]
    rsp_conn $b A $src; rsp_conn $b Y $n; set src $n
  }
  set b [rsp_inst rsp_${tag}_drv [dict get $rsp_cfg root_cell] [expr {$x0 + $ns * $rsp_pitch + 0.3}] $y0]; set n [rsp_net rsp_${tag}_pin]
  rsp_conn $b A $src; rsp_conn $b Y $n; $pin connect $n
  puts "REG_SPINE core tap $iname/$pinn: [llength $reps] repeaters + $ns x [dict get $rsp_cfg pad_cell] + driver at ([format %.2f $x0],[format %.2f $y0])"
}
# (3) trunk, taps, pads, sinks
set rsp_sinks [$rsp_regs getITerms]
array set rsp_netof {}
set rsp_netof(CLK) $rsp_entry
foreach t $rsp_trunk {
  lassign $t nm x y par
  if {$par eq "-"} { set rsp_netof($nm) $rsp_regs; continue }
  set b [rsp_inst rsp_n_$nm [dict get $rsp_cfg trunk_cell] $x $y]; set n [rsp_net rsp_nn_$nm]
  rsp_conn $b A $rsp_netof($par); rsp_conn $b Y $n; set rsp_netof($nm) $n
}
set rsp_tapnets {}; array set rsp_tapnet {}; set rsp_padtot 0
foreach t $rsp_taps {
  lassign $t id x y node pad padxy
  set src $rsp_netof($node)
  for {set s 0} {$s < $pad} {incr s} {
    # optional 6th field: folded pad chain coordinates from reg_spine.py tap_footprint (same pads, same order)
    if {[llength $padxy] == $pad} { lassign [lindex $padxy $s] px py } else { set px [expr {$x - ($pad - $s) * $rsp_pitch - 0.3}]; set py $y }
    set b [rsp_inst rsp_t${id}_d$s [dict get $rsp_cfg pad_cell] $px $py]; set n [rsp_net rsp_t${id}_dn$s]
    rsp_conn $b A $src; rsp_conn $b Y $n; set src $n; incr rsp_padtot
  }
  set b [rsp_inst rsp_t${id}_drv [dict get $rsp_cfg tap_cell] $x $y]; set n [rsp_net rsp_t$id]
  rsp_conn $b A $src; rsp_conn $b Y $n
  set rsp_tapnet($id) $n; lappend rsp_tapnets rsp_t$id
}
array set rsp_asg {}
set fh [open /work/reg_spine_assign.txt]; while {[gets $fh l] >= 0} { set f [split $l " "]; set rsp_asg([lindex $f 0]) [lindex $f 1] }; close $fh
set rsp_moved 0; set rsp_left 0
foreach it $rsp_sinks {
  if {[$it isOutputSignal]} continue
  set iname [[$it getInst] getName]
  if {[info exists rsp_asg($iname)]} { $it disconnect; $it connect $rsp_tapnet($rsp_asg($iname)); incr rsp_moved } else { incr rsp_left; puts "REG_SPINE UNASSIGNED $iname/[[$it getMTerm] getName]" }
}
puts "REG_SPINE spine: [llength $rsp_trunk] trunk entries, [llength $rsp_taps] taps, $rsp_padtot pad stages, sinks moved $rsp_moved, left on root $rsp_left"
# (4) TritonCTS builds the local trees only
set ::env(CTS_ARGS) "-sink_clustering_enable -repair_clock_nets -clk_nets {$rsp_tapnets [dict get $rsp_cfg cts_extra_nets]}"
puts "REG_SPINE CTS_ARGS $::env(CTS_ARGS)"
