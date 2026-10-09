# hfd_svc_SW_s2: forwarded input clocks (two-clock FIFO writes, asynchronous to ck); forwarded-clock output bits
create_clock -name fkq3 -period 833 [get_ports {kq3[3]}]
for {set i 0} {$i < 3} {incr i} { set_input_delay -clock fkq3 166.6 [get_ports [format {kq3[%d]} $i]] }
set_false_path -to [get_ports -quiet {ks3[1099] ks3[1100] ks3[1101]}]
set_clock_uncertainty -setup 60 [get_clocks {fkq3}]
set_clock_uncertainty -hold 25 [get_clocks {fkq3}]
set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] -group [get_clocks fkq3]
