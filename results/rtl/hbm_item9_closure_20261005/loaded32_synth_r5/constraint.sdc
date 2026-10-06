set clk_period 833
create_clock -name core_clk -period $clk_period [get_ports clk_sm]
create_clock -name ingress_clk -period $clk_period [get_ports clk_link]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set non_clock_inputs [all_inputs -no_clocks]
set core_inputs [get_ports {por_n issue issue_mode issue_count issue_va}]
set ingress_inputs [get_ports {switch_rx_v switch_rx_rec}]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $core_inputs
set_input_delay -min 166.6 -clock ingress_clk $ingress_inputs
set_input_delay -max 166.6 -clock ingress_clk $ingress_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_max_fanout 32 [current_design]
# ASAP7 ps units. Actual unchanged reset-controller clocks; no clock/reset waivers.
create_clock -name mem_clk -period 833 -waveform {0 416.5} [get_ports clk_mem]
create_clock -name host_clk -period 833 -waveform {0 416.5} [get_ports clk_host]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# These are synchronous same-frequency source roots. No asynchronous clock groups.
