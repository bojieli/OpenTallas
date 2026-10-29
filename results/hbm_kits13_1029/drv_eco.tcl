# HBM-CORES-KITS-13 ring V1b/V2b (ECO_PINS env): local near-miss ECO on V1 routed slew pins (4 pins <=13.8 ps over 320 ps at TT RCX):
# upsize the weak drivers of the long nets (BUFx3 -> BUFx6f, DFFHQNx1 -> DFFHQNx2), legalize, incremental GRT, then full DRT.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 5_1_grt.sdc
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
foreach i [$block getInsts] { if {[string match {clkbuf_*} [$i getName]] || [string match {mp_isl*} [$i getName]]} { if {[$i getPlacementStatus] ne "FIRM"} {$i setPlacementStatus FIRM} } }
set_routing_layers -signal M2-M5 -clock M2-M5
estimate_parasitics -global_routing
global_route -start_incremental
set done {}
foreach p $::env(ECO_PINS) {
  set n [get_nets -of_objects [get_pins $p]]
  foreach d [get_pins -of_objects $n -filter "direction==output"] {
    set c [get_cells -of_objects $d]; set cn [get_full_name $c]
    if {[lsearch -exact $done $cn] >= 0} continue
    set m [get_property $c ref_name]
    set nm [string map {BUFx2_ BUFx4f_ BUFx3_ BUFx6f_ BUFx4_ BUFx6f_ BUFx4f_ BUFx6f_ DFFHQNx1_ DFFHQNx2_} $m]
    if {$nm eq $m} { puts "V1B_SKIP $cn $m"; continue }
    replace_cell $c $nm
    puts "V1B_UPSIZE $p net=[get_full_name $n] $cn $m -> $nm"
    lappend done $cn
  }
}
detailed_placement
check_placement -verbose
global_route -end_incremental -resistance_aware
source /work/core_grt_post.tcl
estimate_parasitics -global_routing
foreach p $::env(ECO_PINS) { puts "V1B_SLEW_GRT $p [get_property [get_pins $p] slew_max_rise] [get_property [get_pins $p] slew_max_fall]" }
report_worst_slack -max
report_worst_slack -min
write_db $::env(RESULTS_DIR)/5_1_grt.odb
exit
