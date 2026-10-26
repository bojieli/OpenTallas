define_corners TT FF
foreach C {TT FF} {
 foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] {read_liberty -corner $C $f}
 foreach f [glob /work/macros/*_[string tolower $C].lib] {read_liberty -corner $C $f}
}
read_db /work/projected.odb
read_sdc /work/constraint.sdc
# Original GRT session's measured virtual IO latency; source SDC is unchanged.
set_clock_latency -source 518.60 [get_clocks vclk]
set ::env(OT_RC_CAL) 0.8,0.9
source /work/cf/rc_cal.tcl
set_routing_layers -signal M2-M5 -clock M4-M5
set_global_routing_layer_adjustment M2-M5 0.0
set_placement_padding -global -left 0 -right 0
pin_access
global_route -congestion_iterations 30 -congestion_report_file /out/project_congestion.rpt -allow_congestion
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
source /work/cf/mscts_core.tcl
ot_ms_pinmap
set ok [ot_ms_report projection]
puts "PROJECTION_WINDOW_RESULT $ok"
puts "PROJECTION_TT_DIAGNOSTIC setup [sta::time_sta_ui [sta::worst_slack_cmd max]] slew [sta::max_slew_violation_count] cap [sta::max_capacitance_violation_count]"
# Save the actual new graph and RC for the owning phase STA worker.
write_db /out/projected_grt.odb
write_sdc /out/projected_grt.sdc
write_spef /out/projected_grt.spef
write_guides /out/projected_route.guide
if {!$ok} {error "PROJECTION_WINDOW remains outside unchanged20ps gate"}
