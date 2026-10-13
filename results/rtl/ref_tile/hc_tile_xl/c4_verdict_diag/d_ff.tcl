
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.lef
read_lef /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef
read_lef /src/physical/ref_tile/hc_lanes_ref/views/ot_hdc_v41x_hcp_lanes/ot_hdc_v41x_hcp_lanes.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_ff.lib
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_ff.lib
read_liberty /src/physical/ref_tile/hc_lanes_ref/views/ot_hdc_v41x_hcp_lanes/ot_hdc_v41x_hcp_lanes_ff.lib
read_db /work/results/asap7/opentallas_ot_hgi_hc_tile_asap7_ref_hc_tile_xl_c4_550082537_hs/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_hgi_hc_tile_asap7_ref_hc_tile_xl_c4_550082537_hs/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hgi_hc_tile_asap7_ref_hc_tile_xl_c4_550082537_hs/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc

read_sdc /meas/app0_io_ref_routed.sdc
puts "=====H_OUT"
report_checks -path_delay min -to [get_ports {o_nv[0]}] -group_path_count 1 -format full_clock_expanded
puts "=====H_MAC"
report_checks -path_delay min -to [get_pins {g_xm[1].u_x/wd_in[142]}] -group_path_count 1 -format full_clock_expanded
puts "=====H_I2R"
report_checks -path_delay min -from [get_ports {hr_data[980]}] -group_path_count 1 -format full_clock_expanded
exit
