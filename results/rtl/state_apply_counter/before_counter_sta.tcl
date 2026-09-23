read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib
read_verilog /home/ubuntu/OpenTallas/build/state_apply_overlap_synth/mapped.v
link_design ot_a3_state_controller
source /home/ubuntu/OpenTallas/build/state_apply_overlap_synth/constraint.sdc
report_checks -to [get_pins {_44175_/D _44176_/D _44177_/D _44178_/D _44179_/D _44180_/D _44181_/D _44182_/D _44183_/D _44184_/D _44185_/D _44186_/D _44187_/D _44188_/D _44189_/D _44190_/D _44191_/D _44192_/D _44193_/D _44194_/D _44195_/D _44196_/D _44197_/D _44198_/D _44199_/D _44200_/D _44201_/D _44202_/D _44203_/D _44204_/D _44205_/D _44206_/D}] -path_delay max -digits 4 -group_path_count 1
exit
