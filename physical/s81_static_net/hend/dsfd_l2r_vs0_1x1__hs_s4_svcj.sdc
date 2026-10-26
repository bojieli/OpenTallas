# S-NET dsfd_l2r_vs0_1x1__hs_s4_svcj (--hend-static): fixed-calendar crossing, no FIFO / credit / ready
create_clock -name core_clk -period 833.333 [get_ports {ck[0]}]
create_clock -name w_cks -period 833.333 [get_ports {cks[0]}]
create_clock -name vclk -period 833.333
create_clock -name vw -period 833.333
set_clock_latency 0 [get_clocks {vclk vw}]
set_clock_uncertainty -setup 123 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_false_path -from [get_clocks vclk] -to [get_clocks w_cks]
set_false_path -from [get_clocks core_clk] -to [get_clocks vw]
set_input_delay 166.667 -clock vclk [get_ports {i*}]
set_input_delay -min 0 -clock vclk [get_ports {i*}]
set_output_delay 316.667 -clock vw [get_ports {od*}]
set_output_delay -min 0 -clock vw [get_ports {od*}]
set_false_path -to [get_ports {fo*}]
set_input_delay 166.667 -clock vclk [get_ports {xf*}]
set_input_delay -min 0 -clock vclk [get_ports {xf*}]
set_false_path -from [get_ports {rs*}]
set_max_fanout 32 [current_design]
