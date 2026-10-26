# S-NET dsfd_r2l_vr_1024x1__ha_SW (--hend-static): fixed-calendar crossing, no FIFO / credit / ready
create_clock -name w_fi0 -period 833.331 [get_ports {fi0[0]}]
create_clock -name core_clk -period 1111.108 [get_ports {ck[0]}]
create_clock -name vw -period 833.331
create_clock -name vclk -period 1111.108
set_clock_latency 0 [get_clocks {vclk vw}]
set_clock_uncertainty -setup 123 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_max_delay -ignore_clock_latency 1190.0 -from [get_clocks w_fi0] -to [get_clocks core_clk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks w_fi0] -to [get_clocks core_clk]
set_false_path -from [get_clocks vw] -to [get_clocks {core_clk vclk}]
set_false_path -from [get_clocks w_fi0] -to [get_clocks vclk]
set_input_delay 166.666 -clock vw [get_ports {di*}]
set_input_delay -min 0 -clock vw [get_ports {di*}]
set_output_delay 372.222 -clock vclk [get_ports {o*}]
set_output_delay -min 0 -clock vclk [get_ports {o*}]
set_false_path -from [get_ports {rs*}]
set_max_fanout 32 [current_design]
