# QC-CQB2 s5 POST_GLOBAL_ROUTE (all on RC-calibrated GRT parasitics, OT_RC_CAL via cf/rc_cal.tcl):
#  1 DRV (slew/cap) repair + max wire length OT_S5_MAX_WIRE_UM (100; pass 1: 190 um unbuffered AO222 -> F6 landing reg nets read 576 ps slew at RCX); 2 F5 tap + macro-leaf balance (<= OT_MSCTS_WIN_PS); 3 the IO virtual clock bound in-session
#  to the GRT pin-register mean I (METHODOLOGY 9.7 form; the routed RCX I is bound after route, F1);
#  4 TT record /work/s5_grt_tt.txt + I in /work/s5_I_grt.txt; the FF hold repair + gate is hold_grt_s5.tcl (FF-only session).
source /work/cf/mscts_core.tcl
source /work/drv.tcl
set_propagated_clock [all_clocks]
proc s5_ps {v} { return [format %.2f [sta::time_sta_ui $v]] }
proc s5_I {} {
  # pin-register mean TT clock arrival, RCX-corrected per tap when OT_MSCTS_CORR is set (pass 2)
  set f [open $::env(RESULTS_DIR)/ot_face_flops.txt r]; set pins {}
  ot_ms_pinmap
  foreach ln [split [read $f] "\n"] { if {$ln ne ""} { lappend pins "[lindex [split $ln "\t"] 0]/CLK" } }
  close $f
  set n 0; foreach p $pins { if {[ot_ms_arr $p max] ne ""} { incr n } }
  return [list [ot_ms_cmean $pins max [ot_ms_regions] tt] $n]
}
estimate_parasitics -global_routing
puts "S5_PRE slew_viol [sta::max_slew_violation_count] cap_viol [sta::max_capacitance_violation_count] hold [s5_ps [sta::worst_slack_cmd min]]/[sta::endpoint_violation_count min] setup [s5_ps [sta::worst_slack_cmd max]]"
global_route -start_incremental
repair_design -slew_margin 20 -cap_margin 20 -max_wire_length [expr {[info exists ::env(OT_S5_MAX_WIRE_UM)] ? $::env(OT_S5_MAX_WIRE_UM) : 100}]
detailed_placement
global_route -end_incremental
ot_ms_balance grt
estimate_parasitics -global_routing
lassign [s5_I] s5_i s5_n
set_clock_latency -source $s5_i [get_clocks vclk]
puts [format "S5_I_GRT pin-register mean TT %.2f ps over %d pin registers (vclk source latency bound in-session)" $s5_i $s5_n]
set f [open /work/s5_I_grt.txt w]; puts $f [format "%.2f %d" $s5_i $s5_n]; close $f
# FF hold repair is NOT done here: this ORFS session is MCMM (tc + bc) and repair_timing -hold would also fix TT-corner
# hold, which sign-off never checks (TT setup / FF hold).  hold_grt_s5.tcl does it in an FF-only session next.
set s5_s [s5_ps [sta::worst_slack_cmd max]]; set s5_se [sta::endpoint_violation_count max]
set s5_sl [sta::max_slew_violation_count]; set s5_cp [sta::max_capacitance_violation_count]
set s5_win [ot_ms_report grt]
puts "S5_GRT_TT setup $s5_s ep $s5_se slew $s5_sl cap $s5_cp tap_window [expr {$s5_win ? "PASS" : "FAIL"}] I_grt [format %.2f $s5_i]"
set f [open /work/s5_grt_tt.txt w]
puts $f "S5_GRT_TT setup_tt $s5_s ep $s5_se slew $s5_sl cap $s5_cp tap_window [expr {$s5_win ? "PASS" : "FAIL"}] I_grt [format %.2f $s5_i] rc_cal $::env(OT_RC_CAL) [clock format [clock seconds]]"
close $f
report_clock_skew -setup
write_guides $::env(RESULTS_DIR)/route.guide
