read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_256x256_m2_r2c2.lef
read_lef /mv1/qvm_bank_ctrl_native.lef
read_lef /mv2/qvm_data256_native.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_256x256_m2_r2c2_tt.lib
read_liberty /mv1/qvm_bank_ctrl_native_tt.lib
read_liberty /mv2/qvm_data256_native_tt.lib
read_db /work/results/asap7/opentallas_qvm_bank_banked_native_asap7_ref_qvm_bank_entries_my_native_ne3_4ad880d2b/base/6_final.odb
set ::ot_ce_corner tt
read_sdc /work/results/asap7/opentallas_qvm_bank_banked_native_asap7_ref_qvm_bank_entries_my_native_ne3_4ad880d2b/base/6_final.sdc
read_spef /work/results/asap7/opentallas_qvm_bank_banked_native_asap7_ref_qvm_bank_entries_my_native_ne3_4ad880d2b/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
puts "WIRE_Q475_BEGIN"
report_checks -to [get_ports {q[475]}] -path_delay max -group_path_count 1 -endpoint_path_count 1 -format full_clock_expanded -fields {slew cap fanout nets} -digits 5
puts "WIRE_RE_BEGIN"
report_checks -from [get_ports {re}] -to [get_pins {u_ctrl/re}] -path_delay max -group_path_count 1 -endpoint_path_count 1 -format full_clock_expanded -fields {slew cap fanout nets} -digits 5
puts "WIRE_DIAG_DONE"
exit
