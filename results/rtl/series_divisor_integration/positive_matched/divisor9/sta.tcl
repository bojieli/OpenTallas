read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib
read_verilog /home/ubuntu/OpenTallas/build/positive_divisor9_current_primitives/mapped.v
link_design ot_a3_fp32_exp_pos_cr_rne
source /home/ubuntu/OpenTallas/build/positive_divisor9_current_primitives/constraint.sdc
puts "OT_WNS [sta::worst_slack -max]"
puts "OT_TNS [sta::total_negative_slack -max]"
puts "OT_HOLD_WNS [sta::worst_slack -min]"
puts "OT_SETUP_VIOL [llength [find_timing_paths -path_delay max -slack_max 0 -group_count 100000]]"
puts "OT_HOLD_VIOL [llength [find_timing_paths -path_delay min -slack_max 0 -group_count 100000]]"
report_checks -path_delay max -digits 4 -group_count 1 > /home/ubuntu/OpenTallas/build/positive_divisor9_current_primitives/setup_path.rpt
report_checks -path_delay min -digits 4 -group_count 1 > /home/ubuntu/OpenTallas/build/positive_divisor9_current_primitives/hold_path.rpt
exit
