# One deterministic data-delay buffer, inside the existing GRT process.
set ot_vq_hold_ep {g_aqx.u_aq.u_scale.genblk1.genblk1.g_l5.u.u.u_k5.g_r.r[131]$_DFF_P_/D}
set ot_vq_hold_pin [get_pins -quiet $ot_vq_hold_ep]
if {[llength $ot_vq_hold_pin] != 1} {error "VQ classified hold target must be exactly one pin"}
if {[llength [get_cells -quiet ot_vq_k5_hold1029]]} {error "VQ deterministic hold correction already exists"}
set ot_vq_hold_dbi [sta::sta_to_db_inst [$ot_vq_hold_pin instance]]
set ot_vq_hold_loc [$ot_vq_hold_dbi getLocation]
set ot_vq_hold_xy [list [ord::dbu_to_microns [lindex $ot_vq_hold_loc 0]] [ord::dbu_to_microns [lindex $ot_vq_hold_loc 1]]]
set ot_vq_hold_cells [get_lib_cells -quiet */BUFx2_ASAP7_75t_R]
if {![llength $ot_vq_hold_cells]} {error "VQ classified hold buffer master missing"}
global_route -start_incremental
unset_dont_use $ot_vq_hold_cells
insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins [list $ot_vq_hold_pin] -location $ot_vq_hold_xy -buffer_name ot_vq_k5_hold1029
set_dont_use $ot_vq_hold_cells
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
report_checks -to $ot_vq_hold_pin -path_delay min -format full_clock_expanded > /work/vq_classified_hold_after.rpt
puts "OT_VQ_CLASSIFIED_HOLD inserted1 BUFx2 endpoint $ot_vq_hold_ep"
