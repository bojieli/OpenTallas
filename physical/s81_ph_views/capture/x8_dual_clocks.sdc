# Related 3:4 stream/serial clocks; keep every crossing timed.
set capx_p [get_property [get_clocks core_clk] period]
create_clock -name ser_clk -period [expr {$capx_p * 4.0 / 3.0}] [get_ports {ckv ckv[*]}]
set_clock_uncertainty -setup 60 [get_clocks ser_clk]
set_clock_uncertainty -hold 25 [get_clocks ser_clk]
unset_input_delay [get_ports {ckv ckv[*]}]
set_false_path -from [get_ports {rsv rsv[*]}]
unset_output_delay [get_ports {t_vm[*] t_st[*]}]
set_output_delay [expr {0.2 * $capx_p * 4.0 / 3.0}] -clock ser_clk [get_ports {t_vm[*] t_st[*]}]
