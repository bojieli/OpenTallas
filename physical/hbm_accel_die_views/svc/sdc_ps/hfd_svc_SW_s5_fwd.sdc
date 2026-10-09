# hfd_svc_SW_s5: forwarded input clocks (two-clock FIFO writes, asynchronous to ck); forwarded-clock output bits
create_clock -name fkq5 -period 833 [get_ports {kq5[3]}]
for {set i 0} {$i < 3} {incr i} { set_input_delay -clock fkq5 166.6 [get_ports [format {kq5[%d]} $i]] }
set_false_path -to [get_ports -quiet {ks5[1099] ks5[1100] ks5[1101]}]
set_clock_uncertainty -setup 60 [get_clocks {fkq5}]
set_clock_uncertainty -hold 25 [get_clocks {fkq5}]
set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] -group [get_clocks fkq5]
