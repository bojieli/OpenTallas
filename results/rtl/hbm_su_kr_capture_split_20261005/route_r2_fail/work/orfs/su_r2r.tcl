
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_hdc_v41x_vec_light1024rk_asap7_su_kr40_capture_split_r2/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_hdc_v41x_vec_light1024rk_asap7_su_kr40_capture_split_r2/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hdc_v41x_vec_light1024rk_asap7_su_kr40_capture_split_r2/base/6_final.spef
set_propagated_clock [all_clocks]

set ps [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 3 -endpoint_path_count 1 -unique_paths_to_endpoint]
foreach p $ps { puts "R2R [get_property $p slack] [get_full_name [get_property $p startpoint]] -> [get_full_name [get_property $p endpoint]]" }
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -fields {fanout}
exit
