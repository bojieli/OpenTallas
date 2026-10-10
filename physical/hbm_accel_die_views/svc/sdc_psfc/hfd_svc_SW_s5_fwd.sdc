# hfd_svc_SW_s5: forwarded input clocks (two-clock FIFO writes, asynchronous to ck); forwarded-clock output bits
create_clock -name fkq5 -period 833 [get_ports {kq5[1]}]
set_input_delay -clock fkq5 166.6 [get_ports {kq5[0]}]
set_false_path -to [get_ports -quiet {ks5[1099] ks5[1100] ks5[1101]}]
set_output_delay -clock vclk 254.7 [get_ports -quiet {ks5[*]}]
set_false_path -to [get_ports -quiet {ks5[1099] ks5[1100] ks5[1101]}]
set_clock_uncertainty -setup 60 [get_clocks {fkq5}]
set_clock_uncertainty -hold 25 [get_clocks {fkq5}]
set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] -group [get_clocks fkq5]
