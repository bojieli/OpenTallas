read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib
read_verilog /home/ubuntu/OpenTallas/build/state_apply_counter_synth/mapped.v
link_design ot_a3_state_controller
source /home/ubuntu/OpenTallas/build/state_apply_counter_synth/constraint.sdc
report_checks -to [get_pins {_44299_/D _44300_/D _44301_/D _44302_/D _44303_/D _44304_/D _44305_/D _44306_/D _44307_/D _44308_/D _44309_/D _44310_/D _44311_/D _44312_/D _44313_/D _44314_/D _44315_/D _44316_/D _44317_/D _44318_/D _44319_/D _44320_/D _44321_/D _44322_/D _44323_/D _44324_/D _44325_/D _44326_/D _44327_/D _44328_/D _44329_/D _44330_/D}] -path_delay max -digits 4 -group_path_count 1
exit
