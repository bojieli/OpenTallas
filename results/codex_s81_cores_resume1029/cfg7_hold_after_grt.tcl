# One deterministic data-delay buffer, inside the existing GRT process.
set ot_cfg7_hold_ep {u_ld.u.st[0]$_DFF_PN0_/D}
set ot_cfg7_hold_pin [get_pins -quiet $ot_cfg7_hold_ep]
if {[llength $ot_cfg7_hold_pin] != 1} {error "CFG7 classified hold target must be exactly one pin"}
if {[llength [get_cells -quiet ot_cfg7_st0_hold1029]]} {error "CFG7 deterministic hold correction already exists"}
set ot_cfg7_hold_dbi [sta::sta_to_db_inst [$ot_cfg7_hold_pin instance]]
set ot_cfg7_hold_loc [$ot_cfg7_hold_dbi getLocation]
set ot_cfg7_hold_xy [list [ord::dbu_to_microns [lindex $ot_cfg7_hold_loc 0]] [ord::dbu_to_microns [lindex $ot_cfg7_hold_loc 1]]]
set ot_cfg7_hold_cells [get_lib_cells -quiet */BUFx2_ASAP7_75t_R]
if {![llength $ot_cfg7_hold_cells]} {error "CFG7 classified hold buffer master missing"}
global_route -start_incremental
unset_dont_use $ot_cfg7_hold_cells
insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins [list $ot_cfg7_hold_pin] -location $ot_cfg7_hold_xy -buffer_name ot_cfg7_st0_hold1029
set_dont_use $ot_cfg7_hold_cells
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
report_checks -to $ot_cfg7_hold_pin -path_delay min -format full_clock_expanded > /work/cfg7_classified_hold_after.rpt
puts "OT_CFG7_CLASSIFIED_HOLD inserted1 BUFx2 endpoint $ot_cfg7_hold_ep"
