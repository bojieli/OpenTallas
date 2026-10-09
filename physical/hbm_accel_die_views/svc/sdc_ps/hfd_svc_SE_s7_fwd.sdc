# hfd_svc_SE_s7: forwarded input clocks (two-clock FIFO writes, asynchronous to ck); forwarded-clock output bits
create_clock -name fkq7 -period 833 [get_ports {kq7[1]}]
set_input_delay -clock fkq7 166.6 [get_ports {kq7[0]}]
set_false_path -to [get_ports -quiet {ks7[1099] ks7[1100] ks7[1101]}]
set_output_delay -clock vclk 254.7 [get_ports -quiet {ks7[*]}]
set_false_path -to [get_ports -quiet {ks7[1099] ks7[1100] ks7[1101]}]
set_clock_uncertainty -setup 60 [get_clocks {fkq7}]
set_clock_uncertainty -hold 25 [get_clocks {fkq7}]
set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] -group [get_clocks fkq7]
