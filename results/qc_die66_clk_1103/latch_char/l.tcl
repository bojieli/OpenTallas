set C $::env(C)
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_${C}_nldm_220123.lib
read_verilog /w/reg.v
link_design t
create_clock -name clk -period 833.0 [get_ports clk]
set_clock_transition $::env(SLEW) [get_clocks clk]
set_input_delay 0 -clock clk [get_ports d]
set_output_delay 0 -clock clk [get_ports q]
set_load 6.0 [get_nets n1]
foreach pd {max min} {
  puts "LATCHCHAR $pd"
  report_checks -from [get_pins L/CLK] -to [get_pins b/D] -path_delay $pd -digits 3 -fields {slew cap}
  report_checks -to [get_pins L/D] -path_delay $pd -digits 3
}
