# HBM-CORES-REBAL-9: lanes__canon MLAT5/WCOPY1 post-CTS TT setup (propagated clock, vclk bound TT, kit RCX RC):
# WNS/TNS, reg2reg, reset recovery paths, multiplier stage-1 (REBAL-8: m2 -254 m1 -243 e1m -214 me2 -167 q -118).
foreach f {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib} { read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$f }
read_liberty /work/macros/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
read_db [glob /work/run/results/asap7/*/base/4_cts.odb]
read_sdc [glob /work/run/results/asap7/*/base/4_cts.sdc]
set_propagated_clock [get_clocks clk]
if {[info exists ::env(OT_VCLK_TT)] && $::env(OT_VCLK_TT) ne ""} { source /work/vclk_corner.tcl; ot_vclk_bind tt }
source /work/setRC_rcx.tcl
estimate_parasitics -placement
puts "WNS_ALL [sta::worst_slack_cmd max]"
report_tns
puts "NCELLS [llength [get_cells *]]"
puts "WORST_FULL"; report_checks -path_delay max -group_path_count 1 -fields {fanout cap slew} -digits 1
puts "REG2REG"; report_checks -path_delay max -from [all_registers] -to [all_registers] -format end -group_path_count 5
puts "RESET_PATHS"; report_checks -path_delay max -from [get_ports {rst_lane_n* rst_n}] -format end -group_path_count 3
report_checks -path_delay max -from [get_ports {rst_lane_n* rst_n}] -digits 1
foreach u {u_m1 u_m2 u_q u_e1m u_me2} {
  set ps [get_pins -hierarchical -quiet *u_lane.${u}.*/D]
  if {[llength $ps]} { set p [lindex [find_timing_paths -path_delay max -to $ps -group_path_count 1] 0]
    puts "MULALL $u [llength $ps] [get_property $p slack] [get_full_name [get_property $p endpoint]] from [get_full_name [get_property $p startpoint]]" }
}
set nneg 0; foreach p [find_timing_paths -path_delay max -group_path_count 100000 -endpoint_path_count 1 -slack_max 0] { incr nneg }
puts "NEG_ENDPOINTS $nneg"
puts "TOP40"; report_checks -path_delay max -group_path_count 40 -endpoint_path_count 1 -unique_paths_to_endpoint -format end
