# QC-CQB2 s5 FF-only GRT hold step (after do-5_1_grt; standalone openroad, FF libs only = the sign-off hold corner).
# Reads 5_1_grt.odb, the kit SDC with vclk bound to the GRT pin-register mean I (s5_I_grt.txt), RC-calibrated estimates
# (cf/rc_cal.tcl, OT_RC_CAL), re-runs the same global route, repairs FF hold with margin OT_S5_HOLD_MARGIN (15 ps >= the
# F2 estimate-vs-RCX p95 hold error 11.4 ps), ORFS pattern (repair outside incremental, then DPL inside incremental).
# Gate /work/s5_grt_gate.txt: PASS only if FF hold >= 0 with 0 endpoints and the tap window PASS (s5_grt_tt.txt).
set R $::env(RESULTS_DIR)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] { read_liberty $f }
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_ff.lib
read_db $R/5_1_grt.odb
read_sdc /work/constraint.sdc
lassign [split [string trim [read [set f [open /work/s5_I_grt.txt]]]]] s5_i s5_n; close $f
set_clock_latency -source $s5_i [get_clocks vclk]
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
proc s5_ps {v} { return [format %.2f [sta::time_sta_ui $v]] }
set s5_m [expr {[info exists ::env(OT_S5_HOLD_MARGIN)] ? $::env(OT_S5_HOLD_MARGIN) : 15}]
set h0 [s5_ps [sta::worst_slack_cmd min]]; set e0 [sta::endpoint_violation_count min]
puts "S5_HOLD_FF_BEFORE $h0 ep $e0 (vclk I $s5_i, margin $s5_m)"
report_checks -path_delay min -group_path_count 5 -format full_clock_expanded > /work/s5_hold_before.rpt
if {$h0 < -100.0 || $e0 > 2000} { error "S5 structural FF hold failure ($h0 / $e0): stop before route" }
repair_timing -hold -hold_margin $s5_m -max_buffer_percent 20 -verbose
global_route -start_incremental
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
set h1 [s5_ps [sta::worst_slack_cmd min]]; set e1 [sta::endpoint_violation_count min]
set ins [llength [get_cells -quiet hold*]]
puts "S5_HOLD_FF_AFTER $h1 ep $e1 hold buffers $ins"
report_checks -path_delay min -group_path_count 5 -format full_clock_expanded > /work/s5_hold_after.rpt
set tt [string trim [read [set f [open /work/s5_grt_tt.txt]]]]; close $f
set win [expr {[string first "tap_window PASS" $tt] >= 0}]
set ok [expr {$h1 >= 0 && $e1 == 0 && $win}]
set f [open /work/s5_grt_gate.txt w]
puts $f "S5_GRT_GATE [expr {$ok ? "PASS" : "FAIL"}] hold_ff_before $h0 ep $e0 hold_ff $h1 ep $e1 hold_bufs $ins margin $s5_m | $tt | [clock format [clock seconds]]"
close $f
file copy -force $R/5_1_grt.odb $R/5_1_grt_prehold.odb
write_guides $R/route.guide
write_db $R/5_1_grt.odb
puts "S5_GATE [expr {$ok ? "PASS" : "FAIL"}]"
