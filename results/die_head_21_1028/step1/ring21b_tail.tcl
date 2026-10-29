report_checks -path_delay max -from [get_ports {i[*]}] -group_path_count 3 -endpoint_path_count 1 -format end -digits 1
report_checks -path_delay max -from [get_ports {i[*]}] -format full_clock_expanded -digits 1
report_checks -path_delay max -to [get_pins {u_cland_i/u_ring.r_v$_DFF_P_/D}] -format full_clock_expanded -digits 1
set n 0
foreach p [get_pins -hierarchical *s_d*/D] { set s [get_property $p slack_max]; if {$s < 0} {incr n} }
puts "RINGD_NEG $n"
