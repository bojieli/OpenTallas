read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_512x128_m4_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_512x128_m4_r2c2_tt.lib
read_db /diag/6_final.odb
set ::ot_ce_corner ss
read_sdc /diag/6_final.sdc
read_spef /diag/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /diag/w18_extra.sdc
read_sdc /diag/routed_ioref_tt.sdc

foreach phase {raw compensated} {
 if {$phase eq "compensated"} {
  set_clock_latency -source -0.3045000 [get_clocks core_clk]
  set_clock_latency -source -0.1780000 [get_clocks tx_clk]
 }
 foreach mode {max min} {
  set fr [all_registers -clock core_clk -output_pins]
  set to [all_registers -clock tx_clk -data_pins]
  set ps [find_timing_paths -from $fr -to $to -path_delay $mode -group_path_count 100000 -endpoint_path_count 1]
  set worst INF
  foreach p $ps {set v [get_property $p slack];if {$worst eq "INF" || $v<$worst} {set worst $v}}
  puts "OT_TX_PHASE tt $phase $mode paths=[llength $ps] worst_s=$worst"
  report_checks -from $fr -to $to -path_delay $mode -group_path_count 3 -format full_clock_expanded -digits 6
 }
}
puts "OT_TX_PHASE_DONE"
exit
