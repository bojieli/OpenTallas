read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/hbm_accel_sm_views/ot_hbm_accel_tc16/ot_hbm_accel_tc16.lef
read_lef /src/physical/hbm_accel_sm_views/ot_hbm_accel_bd_col/ot_hbm_accel_bd_col.lef
read_lef /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef
read_lef /src/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /src/physical/hbm_accel_sm_views/ot_hbm_accel_tc16/ot_hbm_accel_tc16_ss.lib
read_liberty /src/physical/hbm_accel_sm_views/ot_hbm_accel_bd_col/ot_hbm_accel_bd_col_ss.lib
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_ss.lib
read_liberty /src/physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2_ss.lib
read_db /retained/results/asap7/opentallas_ot_hbm_accel_sm_v_asap7_fsm_sm_r2/base/4_cts.odb
read_sdc /retained/results/asap7/opentallas_ot_hbm_accel_sm_v_asap7_fsm_sm_r2/base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set block [[[ord::get_db] getChip] getBlock]
proc cls {n} { regsub -all {\[[0-9]+\]} $n {[]} n; regsub -all {_[0-9]+_} $n {_N_} n; regsub -all {\\} $n {} n; return $n }
set mode [expr {"ss" eq "ss" ? "max" : "min"}]
set paths [find_timing_paths -path_delay $mode -group_path_count 400000 -endpoint_path_count 1 -slack_max 0 -sort_by_slack]
puts "OT_NVIOL [llength $paths]"
array set worst {}; array set cnt {}; array set wp {}
set tns 0.0
foreach p $paths {
  set s [get_property $p slack]
  set tns [expr {$tns + $s}]
  set sp [get_full_name [get_property $p startpoint]]
  set ep [get_full_name [get_property $p endpoint]]
  set k "[cls $sp] -> [cls $ep]"
  if {![info exists cnt($k)]} { set cnt($k) 0; set worst($k) $s; set wp($k) $p }
  incr cnt($k)
  if {$s < $worst($k)} { set worst($k) $s; set wp($k) $p }
}
puts "OT_TNS $tns"
foreach k [array names cnt] { puts "OT_CLASS\t$worst($k)\t$cnt($k)\t$k" }
puts "OT_DETAIL_BEGIN"
foreach k [array names cnt] {
  puts "OT_CLASS_DETAIL $k"
  report_checks -from [get_property $wp($k) startpoint] -to [get_property $wp($k) endpoint] -path_delay $mode -format full_clock_expanded -fields {slew cap fanout}
}
puts "OT_DONE"
exit
