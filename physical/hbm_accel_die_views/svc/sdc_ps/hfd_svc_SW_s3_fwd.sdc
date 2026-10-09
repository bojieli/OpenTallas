# hfd_svc_SW_s3: forwarded input clocks (two-clock FIFO writes, asynchronous to ck); forwarded-clock output bits
create_clock -name fq4 -period 833 [get_ports {q4[44]}]
for {set i 0} {$i < 44} {incr i} { set_input_delay -clock fq4 166.6 [get_ports [format {q4[%d]} $i]] }
create_clock -name fe -period 833 [get_ports {e[128]}]
for {set i 0} {$i < 128} {incr i} { set_input_delay -clock fe 166.6 [get_ports [format {e[%d]} $i]] }
create_clock -name fkq4 -period 833 [get_ports {kq4[1]}]
set_input_delay -clock fkq4 166.6 [get_ports {kq4[0]}]
set_false_path -to [get_ports -quiet {l4[1099] l4[1100] l4[1101] ks4[1099] ks4[1100] ks4[1101] kd[2]}]
set_output_delay -clock vclk 254.7 [get_ports -quiet {ks4[*]}]
set_false_path -to [get_ports -quiet {ks4[1099] ks4[1100] ks4[1101]}]
set_output_delay -clock vclk 254.7 [get_ports -quiet {kd[0] kd[1]}]
set_clock_uncertainty -setup 60 [get_clocks {fq4 fe fkq4}]
set_clock_uncertainty -hold 25 [get_clocks {fq4 fe fkq4}]
set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] -group [get_clocks fq4] -group [get_clocks fe] -group [get_clocks fkq4]
