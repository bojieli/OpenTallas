# Deterministic one-buffer hold correction of the classified k3->k5 short path.
# Read only the original GRT; outputs belong to this new continuation.
source /work/postcts_gate.tcl
set ep {g_aqx.u_aq.u_scale.genblk1.genblk1.g_l5.u.u.u_k5.g_r.r[131]$_DFF_P_/D}
set pin [get_pins -quiet $ep]
if {[llength $pin] != 1} { error "VQ hold target is not exactly one pin" }
report_checks -to $pin -path_delay max -format full_clock_expanded > /work/vq_hold_target_inc_ff_max_before.rpt
report_checks -to $pin -path_delay min -format full_clock_expanded > /work/vq_hold_target_inc_ff_min_before.rpt
set dbi [sta::sta_to_db_inst [$pin instance]]
set loc [$dbi getLocation]
set xy [list [ord::dbu_to_microns [lindex $loc 0]] [ord::dbu_to_microns [lindex $loc 1]]]
set cells [get_lib_cells -quiet */BUFx2_ASAP7_75t_R]
if {![llength $cells]} {error "missing measured delay buffer"}
# read_db does not initialize Opendp's site grid. The insert-buffer
# postprocessor needs it even when the loaded checkpoint is already legal.
detailed_placement
check_placement -verbose
unset_dont_use $cells
set_routing_layers -signal M2-M5 -clock M2-M5
read_guides /work/run/results/asap7/kl_ot_s81sl_vq_planned_macro/base/route.guide
global_route -start_incremental
insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins [list $pin] -location $xy -buffer_name ot_vq_k5_hold1029
set_dont_use $cells
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
report_checks -to $pin -path_delay min -format full_clock_expanded > /work/vq_hold_target_inc_ff_min_after.rpt
report_checks -path_delay min -group_path_count 20 -format full_clock_expanded > /work/vq_hold_inc_ff_paths_after.rpt
puts "VQ_HOLD_ECO WNS_MIN [sta::worst_slack_cmd min]"
write_db /work/vq_hold1029_inc.odb
write_sdc -no_timestamp /work/vq_hold1029_inc.sdc
write_verilog /work/vq_hold1029_inc.v
write_guides /work/vq_hold1029_inc.guide
