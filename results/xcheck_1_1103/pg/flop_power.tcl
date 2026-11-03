read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_verilog top.v
link_design top
create_clock -name clk -period 833 [get_ports clk]
set_load 1.0 [get_nets n]
set_load 1.0 [get_ports q]
set_power_activity -input -activity 0.1
set_power_activity -input_port clk -activity 2.0
report_power -instances [get_cells *] -digits 6
