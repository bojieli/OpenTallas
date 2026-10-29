# HNX m10b understood data-only residual ECO. All source/state/cycles/clocks unchanged.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 6_final.odb 5_1_grt.sdc
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
remove_fillers
source /work/clk_freeze.tcl
file mkdir /work/eco_clock
# Locks and hashes routed clock wires plus all clock cells/sink flops.
ot_clk_freeze /work/eco_clock
set_routing_layers -signal M2-M5 -clock M2-M5
estimate_parasitics -placement
global_route -start_incremental
foreach {name master} {place4396 BUFx12f_ASAP7_75t_R place4267 BUFx6f_ASAP7_75t_R place4258 BUFx6f_ASAP7_75t_R} {
 set c [get_cells -quiet $name]
 if {[llength $c]!=1} {error "missing driver $name"}
 puts "HNX_ECO_UPSIZE $name [get_property $c ref_name] -> $master"
 replace_cell $c $master
}
# A newly loaded DRT ODB has no live GRT estimator cache; use placement RC during edits, then routed/GRT RC after routing.
estimate_parasitics -placement
set data_pins [dict create]
foreach p [all_registers -data_pins] {dict set data_pins [get_full_name $p] $p}
set hd 0
set pname {gt[0]$_DFF_P_/D}
if {![dict exists $data_pins $pname]} {error "missing exact capture pin $pname"}
set p [dict get $data_pins $pname]
insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins $p -location [list 276.858 27.270] -buffer_name cx_hnx_hd_$hd -net_name cx_hnx_hd_net_$hd
incr hd
set pname {u_tcc.u_h1.g_lane[1].u_add.u.s1_exp[2]$_DFF_P_/D}
if {![dict exists $data_pins $pname]} {error "missing exact capture pin $pname"}
set p [dict get $data_pins $pname]
insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins $p -location [list 35.100 190.350] -buffer_name cx_hnx_hd_$hd -net_name cx_hnx_hd_net_$hd
incr hd
set pname {u_tcc.u_h1.g_lane[1].u_add.u.y[17]$_DFF_P_/D}
if {![dict exists $data_pins $pname]} {error "missing exact capture pin $pname"}
set p [dict get $data_pins $pname]
insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins $p -location [list 55.458 186.300] -buffer_name cx_hnx_hd_$hd -net_name cx_hnx_hd_net_$hd
incr hd
detailed_placement
check_placement -verbose
global_route -end_incremental -resistance_aware
source /work/core_grt_post.tcl
estimate_parasitics -global_routing
ot_clk_freeze_assert hnx_eco_legal
# Both native TT and FF scenes stay active through all normal data checks.
report_worst_slack -max
report_worst_slack -min
ot_clk_dump /work/eco_clock/clock_final.tsv final /work/eco_clock/clk_freeze_nets.txt
write_db $::env(RESULTS_DIR)/5_1_grt.odb
write_sdc -no_timestamp $::env(RESULTS_DIR)/5_1_grt.sdc
puts HNX_DATA_ECO_DONE
exit
