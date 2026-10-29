# DIE-HEAD-17: h16_spine.tcl reading h17_plan.tcl (routed-sized pads, T=525 TT).
# DIE-HEAD-16 DIAGNOSTIC (kit-local, NOT a shared fix): hd_tile register clock as a plan-placed BUFx24 SPINE + LOCAL TREES
# (METHODOLOGY 12.13b / 12.16e local form). Runs after h16_coretaps.tcl (root split h15_rs -> net h15_regs; core early
# taps with 0 delay stages). Plan data from spine16.py (h16_plan.tcl, assign16.txt):
#   trunk: every node a BUFx24 at a plan coordinate, fed from its parent node's output net (hops <= 140 um);
#   taps:  per register cluster (k-means, radius cap 150 um) a chain of PAD x BUFx4 abutted at the tap site + one BUFx24
#          tap driver -> net h16_t<i>; TritonCTS builds ONLY the tap nets (local trees) and fclk_in_i.
# PAD per tap is plan data (0 in pass 1; pass 2 = round((T - measured local insertion)/BUFx4) from pass 1).
source /work/h17_plan.tcl
set h16_blk [ord::get_db_block]
set h16_root [$h16_blk findNet h15_regs]
# snapshot the register sinks before adding any cell
set h16_sinks [$h16_root getITerms]
array set h16_net {}
set h16_net(R) $h16_root
# V2: root-level trunk drivers hang directly on the clk entry net (parent CLK)
set h16_net(CLK) [[$h16_blk findBTerm clk] getNet]
foreach t $h16_trunk {
  lassign $t nm x y par
  if {$par eq "-"} continue
  set b [h15_inst h16_n_$nm BUFx24_ASAP7_75t_R $x $y]; set n [h15_net h16_nn_$nm]
  h15_conn $b A $h16_net($par); h15_conn $b Y $n; set h16_net($nm) $n
}
set h16_tapnets {}
array set h16_tapnet {}
set h16_padtot 0
foreach t $h16_taps {
  lassign $t id x y node pad
  set src $h16_net($node)
  for {set s 0} {$s < $pad} {incr s} {
    set b [h15_inst h16_t${id}_d$s BUFx4_ASAP7_75t_R [expr {$x - ($pad - $s) * 0.81 - 0.3}] $y]; set n [h15_net h16_t${id}_dn$s]
    h15_conn $b A $src; h15_conn $b Y $n; set src $n; incr h16_padtot
  }
  set b [h15_inst h16_t${id}_drv BUFx24_ASAP7_75t_R $x $y]; set n [h15_net h16_t$id]
  h15_conn $b A $src; h15_conn $b Y $n
  set h16_tapnet($id) $n; lappend h16_tapnets h16_t$id
}
array set h16_asg {}
set fh [open /work/assign16.txt]; while {[gets $fh l] >= 0} { set f [split $l " "]; set h16_asg([lindex $f 0]) [lindex $f 1] }; close $fh
set h16_moved 0; set h16_left 0
foreach it $h16_sinks {
  if {[$it isOutputSignal]} continue
  set iname [[$it getInst] getName]
  if {[info exists h16_asg($iname)]} { $it disconnect; $it connect $h16_tapnet($h16_asg($iname)); incr h16_moved } else { incr h16_left; puts "H16 UNASSIGNED $iname/[[$it getMTerm] getName]" }
}
puts "H16 spine: [expr {[llength $h16_trunk] - 1}] trunk BUFx24, [llength $h16_taps] taps, $h16_padtot BUFx4 pad stages, sinks moved $h16_moved, left on root $h16_left"
set ::env(CTS_ARGS) "-sink_clustering_enable -repair_clock_nets -clk_nets {$h16_tapnets fclk_in_i}"
puts "H16 CTS_ARGS $::env(CTS_ARGS)"
