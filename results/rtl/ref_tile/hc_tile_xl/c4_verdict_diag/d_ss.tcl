
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.lef
read_lef /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef
read_lef /src/physical/ref_tile/hc_lanes_ref/views/ot_hdc_v41x_hcp_lanes/ot_hdc_v41x_hcp_lanes.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_tt.lib
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
read_liberty /src/physical/ref_tile/hc_lanes_ref/views/ot_hdc_v41x_hcp_lanes/ot_hdc_v41x_hcp_lanes_tt.lib
read_db /work/results/asap7/opentallas_ot_hgi_hc_tile_asap7_ref_hc_tile_xl_c4_550082537_hs/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_hgi_hc_tile_asap7_ref_hc_tile_xl_c4_550082537_hs/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hgi_hc_tile_asap7_ref_hc_tile_xl_c4_550082537_hs/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc

read_sdc /meas/app0_io_ref_routed.sdc
puts "DIAG_PERIOD [get_property [get_clocks core_clk] period]"
puts "=====I2R"
report_checks -path_delay max -from [get_ports hq_rdy[2]] -group_path_count 1 -format full_clock_expanded -fields {fanout cap slew}
puts "=====R2O"
report_checks -path_delay max -to [get_ports hq_addr[74]] -group_path_count 1 -format full_clock_expanded -fields {fanout cap}
puts "=====BASEQ"
report_checks -path_delay max -from [get_pins {base_q[0]$_DFF_P_/CLK}] -group_path_count 1 -format full_clock_expanded -fields {fanout cap}
puts "=====WADDR"
report_checks -path_delay max -from [get_pins {u_st.w_addr[0]$_DFF_P_/CLK}] -group_path_count 1 -format full_clock_expanded -fields {fanout cap}
puts "=====HRTL fan"
report_checks -path_delay max -from [get_pins {hr_tl[32]$_DFF_P_/CLK}] -group_path_count 1 -format full -fields {fanout cap}
puts "=====SKEW"
report_clock_skew -setup
report_clock_skew -hold
set lo 1e9; set hi -1e9
foreach p [all_registers -clock_pins] { set a [get_property $p arrival_max_rise]; if {$a eq ""} {continue}; if {$a<$lo} {set lo $a; set lp [get_full_name $p]}; if {$a>$hi} {set hi $a; set hp [get_full_name $p]} }
catch {puts "DIAG_CKARR min $lo $lp max $hi $hp"}
foreach n {first hr_tag[0] hr_v[0] hq_rdy[2]} { catch {report_checks -path_delay max -from [get_ports $n] -group_path_count 1 -format short} }
exit
