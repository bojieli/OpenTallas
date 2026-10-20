set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef /w/hard.lef
read_liberty /w/hard.lib
read_verilog /w/top.v
link_design top
create_clock -name ot_frame_xk0 -period 833.333 [get_ports {xk[0]}]
create_clock -name ot_frame_xk1 -period 833.333 [get_ports {xk[1]}]
create_clock -name ot_frame_xk2 -period 833.333 [get_ports {xk[2]}]
create_clock -name ot_frame_xk3 -period 833.333 [get_ports {xk[3]}]
set_input_delay -clock ot_frame_xk0 0 [get_ports {d[*]}]
create_generated_clock -name out0 -combinational -source [get_ports {xk[0]}] [get_ports {xok[0]}]
create_generated_clock -name out1 -combinational -source [get_ports {xk[1]}] [get_ports {xok[1]}]
create_generated_clock -name out2 -combinational -source [get_ports {xk[2]}] [get_ports {xok[2]}]
create_generated_clock -name out3 -combinational -source [get_ports {xk[3]}] [get_ports {xok[3]}]
set_propagated_clock [all_clocks]
report_lib_cell relay
report_checks -unconstrained -path_delay min_max
source /w/audit.tcl
ot_frame_clock_audit tt
puts "NATIVE_FRAME_CLOCK_PASS"
