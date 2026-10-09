# hfd_svc_SE_s5: forwarded input clocks (two-clock FIFO writes, asynchronous to ck); forwarded-clock output bits
create_clock -name fq6 -period 833 [get_ports {q6[44]}]
for {set i 0} {$i < 44} {incr i} { set_input_delay -clock fq6 166.6 [get_ports [format {q6[%d]} $i]] }
create_clock -name fkq6 -period 833 [get_ports {kq6[1]}]
set_input_delay -clock fkq6 166.6 [get_ports {kq6[0]}]
set_false_path -to [get_ports -quiet {l6[1099] l6[1100] l6[1101] ks6[1099] ks6[1100] ks6[1101]}]
set_output_delay -clock vclk 254.7 [get_ports -quiet {ks6[*]}]
set_false_path -to [get_ports -quiet {ks6[1099] ks6[1100] ks6[1101]}]
set_clock_uncertainty -setup 60 [get_clocks {fq6 fkq6}]
set_clock_uncertainty -hold 25 [get_clocks {fq6 fkq6}]
set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] -group [get_clocks fq6] -group [get_clocks fkq6]
