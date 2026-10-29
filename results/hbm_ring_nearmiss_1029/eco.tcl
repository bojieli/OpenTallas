source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 4_cts.sdc
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
set loadpins {}
foreach it [[$block findNet _000088_] getITerms] {
 set name "[[$it getInst] getName]/[[$it getMTerm] getName]"
 if {$name ni {_243472_/SN _146785_/A}} {lappend loadpins $name}
}
if {[llength $loadpins] != 11} {error "wrong SN fanout"}
insert_buffer -buffer_cell BUFx4_ASAP7_75t_R -load_pins $loadpins -buffer_name codex_ring_sn_loadsplit -net_name codex_ring_sn_aux -location {118.8 69.66}
set loadpins {}
foreach it [[$block findNet _000080_] getITerms] {
 set name "[[$it getInst] getName]/[[$it getMTerm] getName]"
 if {$name ne {_243711_/CON}} {lappend loadpins $name}
}
if {[llength $loadpins] != 10} {error "wrong CON fanout"}
insert_buffer -buffer_cell BUFx4_ASAP7_75t_R -load_pins $loadpins -buffer_name codex_ring_con_loadsplit -net_name codex_ring_con_aux -location {116.64 67.5}
detailed_placement
check_placement -verbose
set_routing_layers -signal M2-M5 -clock M2-M5
set_global_routing_layer_adjustment * 0.25
global_route -congestion_iterations 50 -congestion_report_file /out/eco_congestion.rpt
estimate_parasitics -global_routing
ot_mm_sync
report_checks -path_delay max -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} > /out/eco_setup.rpt
report_checks -path_delay min -group_path_count 4 -format full_clock_expanded -fields {slew cap fanout} > /out/eco_hold.rpt
report_worst_slack -max
report_worst_slack -min
write_db /out/eco_grt.odb
write_verilog /out/eco.v
exit
