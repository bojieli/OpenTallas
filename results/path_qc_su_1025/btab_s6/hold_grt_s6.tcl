# PATH-QC-SU btab_s6 copy of QC-CQB3 vmr_s6 hold_grt_s6.tcl (only change: btab SRAM FF lib). On btab_s6 5_1_grt.odb (pre-hold) after the s5 POST_GRT step.
# QC-CQB3 vmr_s6 FF-only GRT hold step on the pass-2 pre-hold GRT DB (5_1_grt.odb := vmr_s5 5_1_grt_prehold.odb).
# Successor of hold_grt_s5.tcl.  The ONE structural change: the FF hold repair runs at the FF basis.
#   vmr_s5 pass 2 bound vclk = 389.59 (the TT GRT pin-register mean) in the FF session and signed off at the SDC 359.64
#   for both corners; the routed pass-2 RCX pin-register means are TT 386.48 / FF 296.50 (n 1509).  Per METHODOLOGY 9.7 /
#   decision 5e (main FLOW vclk_corner.tcl): constraint.sdc carries the TT bound (386.48, setup), every FF-only step
#   rebinds vclk to the FF bound (OT_VCLK_FF = 296.50).
# Clock basis unchanged from pass 2: RC-calibrated GRT estimate (cf/rc_cal.tcl, OT_RC_CAL 0.8,0.9) with the per-tap
#   RCX correction on the trunk arcs (OT_MSCTS_CORR, ot_ms_assign_corr ff; the pass-2 route shows it worked: RCX tap
#   window TT 10.2 / FF 13.1 ps).  Hold margin OT_S6_HOLD_MARGIN (15 >= F2 FF hold-estimate p95 error 11.4 ps).
# NOTE: get_property slack is already in ps; the 07:2x run still applied time_sta_ui in s6_class/s6_hist (class worst +
# histogram values x1e12) -> post-processed /1e12 into s6_hold_hist_{before,after}.tsv.  Fixed here.
# Writes $O/s6_grt_gate.txt, s6_hold_census.txt, s6_hold_{before,after}.rpt, s6_hold_hist_{before,after}.tsv.
set R $::env(RESULTS_DIR)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] { read_liberty $f }
read_liberty /work/macros/ot_sram_1r1w_128x256_m1_r2c2_ff.lib
read_db $R/5_1_grt.odb
read_sdc /work/constraint.sdc
set ::env(OT_VCLK_CORNER) ff
source /work/cf/main/vclk_corner.tcl
# what-if knobs (diagnostic only, OT_S6_DRY=1 writes to OT_S6_OUT and never touches the kit DB):
#   OT_S6_IN_MIN  : input -min delay (default = kit SDC -40; PROPOSAL IO-HOLD 06:54 asks -30)
#   OT_S6_IO_M0=1 : IO paths carry no hold margin: repair margin 0 + reg->reg margin as +margin hold uncertainty clk->clk
set O [expr {[info exists ::env(OT_S6_OUT)] ? $::env(OT_S6_OUT) : "/work"}]
set dry [expr {[info exists ::env(OT_S6_DRY)] && $::env(OT_S6_DRY)}]
if {[info exists ::env(OT_S6_IN_MIN)]} { set_input_delay -min $::env(OT_S6_IN_MIN) -clock vclk [all_inputs -no_clocks]; puts "S6_WHATIF input -min $::env(OT_S6_IN_MIN)" }
source /work/cf/rc_cal.tcl
set_global_routing_layer_adjustment M2-M5 0.25
set_routing_layers -clock M4-M5
set_routing_layers -signal M2-M5
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
set_placement_padding -global -left 0 -right 0
pin_access
global_route -congestion_iterations 30
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
source /work/cf/mscts_core.tcl
ot_ms_assign_corr ff
ot_ms_report hold_ff
proc s6_ps {v} { return [format %.2f [sta::time_sta_ui $v]] }
set s6_m [expr {[info exists ::env(OT_S6_HOLD_MARGIN)] ? $::env(OT_S6_HOLD_MARGIN) : 15}]
if {[info exists ::env(OT_S6_IO_M0)] && $::env(OT_S6_IO_M0)} {
  set_clock_uncertainty -hold [expr {25.0 + $s6_m}] -from [get_clocks clk] -to [get_clocks clk]
  puts "S6_WHATIF IO margin 0: clk->clk hold uncertainty [expr {25.0 + $s6_m}], repair margin 0"; set s6_m 0
}
# hold census by class: in = input port -> reg, out = reg -> output port, int = reg -> reg / macro
proc s6_class {tag} {
  set ins [all_inputs -no_clocks]; set outs [all_outputs]
  set res {}
  foreach {cl args} [list in [list -from $ins] out [list -to $outs] int [list -from [all_registers] -to [all_registers]]] {
    set ps [find_timing_paths -path_delay min {*}$args -group_path_count 100000 -endpoint_path_count 1 -slack_max 0.0]
    set n [llength $ps]; set w 0.0
    foreach p $ps { set s [get_property $p slack]; if {$s < $w} { set w $s } }
    lappend res $cl [format "%d %.2f" $n $w]
  }
  puts "S6_HOLD_CLASS $tag $res"
  return $res
}
proc s6_hist {fn} {
  set h [dict create]
  foreach p [find_timing_paths -path_delay min -group_path_count 200000 -endpoint_path_count 1 -slack_max 0.100] {
    set s [get_property $p slack]
    set b [expr {int(floor($s / 5.0)) * 5}]
    dict incr h $b
  }
  set f [open $fn w]; puts $f "bin_ps\tcount"
  foreach b [lsort -integer [dict keys $h]] { puts $f "$b\t[dict get $h $b]" }
  close $f
}
set h0 [s6_ps [sta::worst_slack_cmd min]]; set e0 [sta::endpoint_violation_count min]
puts "S6_HOLD_FF_BEFORE $h0 ep $e0 (vclk FF $::env(OT_VCLK_FF), margin $s6_m)"
set c0 [s6_class before]
s6_hist $O/s6_hold_hist_before.tsv
report_checks -path_delay min -group_path_count 5 -format full_clock_expanded > $O/s6_hold_before.rpt
if {$h0 < -150.0 || $e0 > 4000} { error "S6 structural FF hold failure ($h0 / $e0): stop before route" }
set nb0 [llength [get_cells -quiet hold*]]
repair_timing -hold -hold_margin $s6_m -max_buffer_percent [expr {[info exists ::env(OT_S6_MAXBUF)] ? $::env(OT_S6_MAXBUF) : 30}] -verbose
global_route -start_incremental
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
set h1 [s6_ps [sta::worst_slack_cmd min]]; set e1 [sta::endpoint_violation_count min]
# hold-buffer census: walk each new hold buffer chain up to its source (port / register / other) and down to its sinks
set blk [ord::get_db_block]
set cen [dict create in 0 out 0 int 0]
set newh {}
foreach c [get_cells -quiet hold*] { lappend newh [get_full_name $c] }
foreach n $newh {
  set i [$blk findInst $n]
  set src ""; set cur $i; set guard 0
  while {$src eq "" && [incr guard] < 200} {
    set inet ""
    foreach it [$cur getITerms] { if {[$it isInputSignal]} { set inet [$it getNet] } }
    if {$inet eq "" || $inet eq "NULL"} { set src other; break }
    if {[llength [$inet getBTerms]]} { set src in; break }
    set drv ""
    foreach it [$inet getITerms] { if {[$it isOutputSignal]} { set drv [$it getInst] } }
    if {$drv eq ""} { set src other; break }
    if {[string match hold* [$drv getName]]} { set cur $drv } else { set src reg }
  }
  # sink side: output port on the downstream net of the chain end
  set onet ""
  foreach it [$i getITerms] { if {[$it isOutputSignal]} { set onet [$it getNet] } }
  set toport [expr {$onet ne "" && $onet ne "NULL" && [llength [$onet getBTerms]]}]
  if {$src eq "in"} { dict incr cen in } elseif {$toport} { dict incr cen out } else { dict incr cen int }
}
set ins [llength $newh]
set c1 [s6_class after]
s6_hist $O/s6_hold_hist_after.tsv
puts "S6_HOLD_FF_AFTER $h1 ep $e1 hold buffers $ins census $cen"
report_checks -path_delay min -group_path_count 5 -format full_clock_expanded > $O/s6_hold_after.rpt
set ws [s6_ps [sta::worst_slack_cmd max]]
set tt [string trim [read [set f [open /work/s5_grt_tt.txt]]]]; close $f
set win [expr {[string first "tap_window PASS" $tt] >= 0}]
set ok [expr {$h1 >= 0 && $e1 == 0 && $win}]
set f [open $O/s6_hold_census.txt w]
puts $f "vclk_ff $::env(OT_VCLK_FF) margin $s6_m hold_bufs_pre $nb0 new_chain_cells $ins by_chain_source $cen"
puts $f "before $c0"
puts $f "after $c1"
close $f
set f [open $O/s6_grt_gate.txt w]
puts $f "S6_GRT_GATE [expr {$ok ? "PASS" : "FAIL"}] vclk_ff $::env(OT_VCLK_FF) hold_ff_before $h0 ep $e0 hold_ff $h1 ep $e1 hold_bufs $ins census $cen margin $s6_m setup_ff_est $ws | pass2 pre-hold TT record: $tt | [clock format [clock seconds]]"
close $f
if {!$dry} {
  write_guides $R/route.guide
  write_db $R/5_1_grt.odb
}
puts "S6_GATE [expr {$ok ? "PASS" : "FAIL"}]"
