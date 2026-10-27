# FF-only hold ECO on the reviewed R10 checkpoint. No clock edits or period/uncertainty changes.
set R /work/run/results/asap7/kq_qfd_dv_s8x_btab_mif0r7/base
set ::env(RESULTS_DIR) $R
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] {read_liberty $f}
read_liberty /work/macros/ot_sram_1r1w_128x256_m1_r2c2_ff.lib
read_db $R/5_1_grt.odb
read_sdc /work/constraint.sdc
source /work/cf/rc_cal.tcl
set_routing_layers -signal M2-M5 -clock M4-M5
set_global_routing_layer_adjustment M2-M5 0.0
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
set_placement_padding -global -left 0 -right 0
pin_access
global_route -congestion_iterations 30
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
source /work/cf/mscts_core.tcl
# New-process FF session on the R10 GRT checkpoint: rebuild the mscts bookkeeping (tap nets, macro leaves) from the
# ot_ms_* names in the DB and the R10 spec, exactly as the established FF-only session (hold_grt_s6.tcl) does via
# ot_ms_assign_corr; the CTS/GRT (TT) session had it in memory from the build. No clock change.
ot_ms_assign_corr ff
if {![info exists ::ot_ms_macros]} { uplevel #0 [list source $::env(OT_MSCTS_SPEC)] }
if {![llength $::ot_ms_tapnets]} { error "BTAB_R10_FF: no ot_ms_*_clk tap nets recovered from 5_1_grt.odb" }
puts "BTAB_R10_FF_RECOVER tapnets [llength $::ot_ms_tapnets] macleaf [llength $::ot_ms_macleaf] spec $::env(OT_MSCTS_SPEC)"
ot_ms_report hold_ff
ot_ms_pinmap
set f [open $R/ot_face_flops.txt r];set pins {}
foreach ln [split [read $f] "\n"] {if {$ln ne ""} {lappend pins "[lindex [split $ln "\t"] 0]/CLK"}}
close $f
set ffmean [ot_ms_cmean $pins max [ot_ms_regions] ff]
set_clock_latency -source $ffmean [get_clocks vclk]
puts "BTAB_R10_FF_VCLK measured_pinmean $ffmean sinks [llength $pins] period833 setup60 hold25 unchanged"
set before [sta::time_sta_ui [sta::worst_slack_cmd min]]
set ep [sta::endpoint_violation_count min]
puts "CQB_HOLD_BEFORE $before endpoints$ep"
if {$before < -100.0 || $ep > 2000} {error "Structural FF hold failure: no DRT"}
set_max_fanout 24 [current_design]
global_route -start_incremental
repair_timing -hold -hold_margin 5 -allow_setup_violations -max_buffer_percent 40
detailed_placement
global_route -end_incremental
estimate_parasitics -global_routing
set after [sta::time_sta_ui [sta::worst_slack_cmd min]]
set ep [sta::endpoint_violation_count min]
puts "CQB_HOLD_AFTER $after endpoints$ep"
if {$after < 0.0 || $ep > 0} {error "FF hold not closed: no DRT"}
write_guides $R/route.guide
write_db $R/5_1_grt.odb
write_verilog $R/5_1_grt.v
write_sdc -no_timestamp $R/5_1_grt_ff.sdc
puts "BTAB_R10_FF_DONE"
