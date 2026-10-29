# what-if: fclk_in_i port carries the measured sender forwarded insertion (DH20 spec, TT min 186.1)
set_clock_latency -source 186.1 [get_clocks fclk_in_i]
report_checks -path_delay max -group_path_count 3 -endpoint_path_count 1 -format end -digits 1
set n 0
foreach p [get_pins -hierarchical *s_d*/D] { set s [get_property $p slack_max]; if {$s < 0} {incr n} }
puts "RINGD_NEG_LAT186 $n"
