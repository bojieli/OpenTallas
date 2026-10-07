read_lef /tmp/bf_phase_sta_fixture/asap7_tech_1x_201209.lef
read_lef /tmp/bf_phase_sta_fixture/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /home/ubuntu/OpenTallas/results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /home/ubuntu/OpenTallas/results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_verilog /tmp/pq-return-delay-sweep/chain0.v
link_design top
create_clock -name clk -period 833.333 [get_ports clk]
set_input_delay 0 -clock clk [get_ports din]
set_input_transition 5 [get_ports din]
set_load 0.78 [get_nets {w*}]
report_checks -from [get_ports din] -to [get_pins ff/D] -path_delay min_max -format full_clock_expanded -digits 6
exit
