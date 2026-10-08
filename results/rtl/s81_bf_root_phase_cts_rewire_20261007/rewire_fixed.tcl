read_lef /tmp/bf_phase_sta_fixture/asap7_tech_1x_201209.lef
read_lef /tmp/bf_phase_sta_fixture/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /home/ubuntu/OpenTallas/results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /home/ubuntu/OpenTallas/results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_verilog /tmp/bf_phase_sta_fixture/top.v
link_design top
create_clock -name core_clk -period 833.333 [get_ports clk]
foreach p [get_pins -hierarchical *] {puts "PIN [get_full_name $p]"}
source /home/ubuntu/OpenTallas/physical/s81_bf_root_phase/clock.sdc
initialize_floorplan -site asap7sc7p5t -die_area {0 0 60 60} -core_area {2.16 2.16 57.84 57.84}
set k 0
foreach i [[ord::get_db_block] getInsts] {
 $i setLocation [expr {10000+1000*$k}] 10000
 $i setPlacementStatus PLACED
 incr k
}
source /home/ubuntu/OpenTallas/physical/s81_bf_root_phase/localize.tcl
source /home/ubuntu/OpenTallas/physical/s81_bf_root_phase/check_placement.tcl
report_clock_properties [all_clocks]
set b [ord::get_db_block]
set inv [$b findInst g_half.g_root.u_inv0/u_inv]
set pin [$inv findITerm A]
set old_net [$pin getNet]
$pin disconnect
$pin connect $old_net
source /home/ubuntu/OpenTallas/physical/s81_bf_root_phase/check_placement.tcl
if {[$inv getPlacementStatus] ne "FIRM"} {error "lost FIRM placement"}
puts "BF_CTS_REWIRE_PASS"
exit
