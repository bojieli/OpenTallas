source $::env(SCRIPTS_DIR)/load.tcl
load_design frozen_grt.odb 4_cts.sdc
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
foreach i [$block getInsts] {
 if {[string match {clkbuf_*} [$i getName]] || [string match {mp_isl*} [$i getName]]} {$i setPlacementStatus FIRM}
}
set target {}
foreach i [$block getInsts] {
 set norm [string map {"\\" ""} [$i getName]]
 if {$norm eq {u_fcore.u_core.u_ring.u_ctl.pin_p[0][246]$_DFF_P_}} {set target $i;break}
}
if {$target eq {}} {error "exact residual hold capture missing"}
lassign [$target getLocation] tx ty
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set px [expr {double($tx)/$dbu-1.08}];set py [expr {double($ty)/$dbu}]
set target_pin {}
foreach pi [get_pins -quiet -hierarchical {*pin_p*/D}] {
 set nm [string map {"\\" ""} [get_full_name $pi]]
 if {$nm eq {u_fcore.u_core.u_ring.u_ctl.pin_p[0][246]$_DFF_P_/D}} {set target_pin $pi;break}
}
if {$target_pin eq {}} {error "exact STA residual capture missing"}
insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins [list $target_pin] -buffer_name codex_ring_residual_hold -net_name codex_ring_residual_hold_net -location [list $px $py]
detailed_placement
check_placement -verbose
set_routing_layers -signal M2-M5 -clock M2-M5
set_global_routing_layer_adjustment * 0.25
global_route -congestion_iterations 50 -congestion_report_file /out/pad1v2_congestion.rpt
estimate_parasitics -global_routing
ot_mm_unsync
ot_mm_sync
global_route -start_incremental
# Exact one-buffer deterministic hold repair; no global repair pass.
ot_mm_unsync
detailed_placement
check_placement -verbose
global_route -end_incremental -resistance_aware
estimate_parasitics -global_routing
ot_mm_unsync
ot_mm_sync
report_checks -path_delay max -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} > /out/pad1v2_setup.rpt
report_checks -path_delay min -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} > /out/pad1v2_hold.rpt
report_worst_slack -max
report_worst_slack -min
write_guides /out/pad1v2_route.guide
ot_mm_unsync
write_db /out/pad1v2_grt.odb
write_verilog /out/eco.v
exit
