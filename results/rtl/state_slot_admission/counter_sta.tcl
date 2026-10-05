read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib
read_verilog /home/ubuntu/OpenTallas/build/state_slot_admission_synth/mapped.v
link_design ot_a3_state_controller
source /home/ubuntu/OpenTallas/build/state_slot_admission_synth/constraint.sdc
set regs [get_fanin -to [get_ports {count_commits[*]}] -flat -startpoints_only -only_cells]
set pins {}
foreach r $regs { lappend pins [get_full_name $r]/D }
puts "COUNTER_PINS $pins"
report_checks -to [get_pins $pins] -path_delay max -digits 4 -group_path_count 1
exit
