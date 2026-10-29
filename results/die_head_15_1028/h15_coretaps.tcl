# DIE-HEAD-15 DIAGNOSTIC (kit-local prototype, NOT a shared fix): hd_tile EARLY CORE TAPS (METHODOLOGY 12.3 v5.0) in the
# one-entry kit. Plan (results ESTIMATE): register leaf target T = 450 TT / 380 FF (parent budget); each hard-core clock
# pin is tapped EARLY by its SIGNED internal mean: pin target = T - L (eA 450-255.24 = 194.8 TT; eB 450-230.71 = 219.3 TT).
# Structure (fixed by the plan, not by CTS repair): the clk entry net (port at the channel cross 353.76,354.21) drives
#   (1) one root-split BUFx24 'h15_rs' at the cross -> net h15_regs = every register/latch clock sink; TritonCTS builds
#       ONLY this net (-clk_nets), so no macro tree and no CTS-0033 macro latency balancing;
#   (2) per eA core: nA x BUFx4 delay stages abutted at the core's channel-cross corner + one BUFx24 driver -> the
#       over-core M6/M7 leg (~363 um) to the core-centre pin ft_mstrap_i;
#   (3) eB: 2 x BUFx24 channel repeaters (<=182 um hops) -> nB x BUFx4 at eB's bottom edge -> BUFx24 driver -> 146 um leg.
# Every delay stage drives only the abutted next stage (input slew <= ~40 ps by construction); only a BUFx24 drives a
# long leg. All h15_* cells/nets dont_touch; their status stays PLACED (CTS-stage DPL legalises them, < 5 um).
set h15_nA [expr {[info exists ::env(H15_NA)] ? $::env(H15_NA) : 5}]
set h15_nB [expr {[info exists ::env(H15_NB)] ? $::env(H15_NB) : 3}]
set h15_blk [ord::get_db_block]
set h15_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set h15_db [ord::get_db]
set h15_clk [[$h15_blk findBTerm clk] getNet]
proc h15_inst {name master x y} {
  global h15_blk h15_dbu h15_db
  set m [$h15_db findMaster $master]
  set i [odb::dbInst_create $h15_blk $m $name]
  # snap to the ASAP7 site grid of the core rows (site 0.054 x 0.27 um, core origin 4.32)
  set sx [expr {4.32 + round(($x - 4.32) / 0.054) * 0.054}]
  set sy [expr {4.32 + round(($y - 4.32) / 0.27) * 0.27}]
  $i setLocation [expr {round($sx * $h15_dbu)}] [expr {round($sy * $h15_dbu)}]
  if {(round(($sy - 4.32) / 0.27) % 2) == 1} { $i setOrient MX } else { $i setOrient R0 }
  $i setPlacementStatus PLACED
  return $i
}
proc h15_net {name} { global h15_blk; set n [odb::dbNet_create $h15_blk $name]; $n setSigType CLOCK; return $n }
proc h15_conn {inst pin net} { [$inst findITerm $pin] connect $net }
# (1) root split
set h15_regs [h15_net h15_regs]
set h15_moved 0
foreach it [$h15_clk getITerms] { $it disconnect; $it connect $h15_regs; incr h15_moved }
set rs [h15_inst h15_rs BUFx24_ASAP7_75t_R 351.0 356.0]
h15_conn $rs A $h15_clk; h15_conn $rs Y $h15_regs
puts "H15 root split: $h15_moved clk sinks -> h15_regs"
# (2)/(3) core branches: {inst pin_core chain_x chain_y dir repeaters{x y}}
set h15_cores {
  {u_core.u_b.g_cv.u_eA0 A 340.0 330.0 1 {}}
  {u_core.u_b.g_cv.u_eA1 A 358.0 330.0 1 {}}
  {u_core.u_b.g_cv.u_eA2 A 340.0 377.5 1 {}}
  {u_core.u_b.g_cv.u_eA3 A 358.0 377.5 1 {}}
  {u_core.u_b.g_cvb.u_eB B 351.0 718.0 1 {{352.0 537.0} {352.0 716.0}}}
}
set h15_cells {}
foreach c $h15_cores {
  lassign $c iname kind x0 y0 dir reps
  set core [$h15_blk findInst $iname]
  set pin [$core findITerm ft_mstrap_i]
  set tag [lindex [split $iname .] end]
  set old [$pin getNet]
  if {$old ne "NULL"} { $pin disconnect }
  set src $h15_clk; set k 0
  foreach r $reps {
    lassign $r rx ry
    set b [h15_inst h15_${tag}_r$k BUFx24_ASAP7_75t_R $rx $ry]; set n [h15_net h15_${tag}_rn$k]
    h15_conn $b A $src; h15_conn $b Y $n; set src $n; lappend h15_cells $b; incr k
  }
  set ns [expr {$kind eq "A" ? $h15_nA : $h15_nB}]
  for {set s 0} {$s < $ns} {incr s} {
    set b [h15_inst h15_${tag}_d$s BUFx4_ASAP7_75t_R [expr {$x0 + $s * 0.81}] $y0]; set n [h15_net h15_${tag}_dn$s]
    h15_conn $b A $src; h15_conn $b Y $n; set src $n; lappend h15_cells $b
  }
  set b [h15_inst h15_${tag}_drv BUFx24_ASAP7_75t_R [expr {$x0 + $ns * 0.81 + 0.3}] $y0]; set n [h15_net h15_${tag}_pin]
  h15_conn $b A $src; h15_conn $b Y $n; $pin connect $n; lappend h15_cells $b
  puts "H15 core tap $iname/ft_mstrap_i: [llength $reps] repeaters + $ns x BUFx4 + BUFx24 driver at ([format %.2f $x0],[format %.2f $y0])"
}
lappend h15_cells $rs
# no dont_touch: repair_clock_nets may only insert repeaters on over-reach wires; any h15_* net it buffers is reported (H15_RCN)
set ::env(CTS_ARGS) "-sink_clustering_enable -repair_clock_nets -clk_nets {h15_regs fclk_in_i}"
puts "H15 CTS_ARGS $::env(CTS_ARGS)"
