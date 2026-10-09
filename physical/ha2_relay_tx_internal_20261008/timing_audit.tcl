# Executed after routed ODB/SPEF and propagated real core_clk are loaded.
puts "HA2_SCOPE INTERNAL_ONLY NOT_LEAF_CLOSURE"
set launch_clocks {};set tx_data {};set tx_payload_data {}
foreach p [all_registers -clock_pins] {
 set n [get_full_name $p]
 set role other
 if {[string match {*u_launch*} $n]} {set role launch;lappend launch_clocks $p}
 if {[string match {*u_tx*} $n]} {set role tx}
 puts "HA2_BRANCH_CLOCK $role $n [get_property $p arrival_min_rise] [get_property $p arrival_max_rise]"
}
foreach p [all_registers -data_pins] {
 set n [get_full_name $p]
 # D pins only: all_registers -data_pins also returns the async SETN/RESETN pins of the 128 reset flops
 # (256 pins, census 1472 != 1216); those are recovery/removal checks, still covered by all_reg2reg below
 if {![regexp {/D$} $n]} {continue}
 if {[string match {*u_tx*} $n]} {lappend tx_data $p}
 if {[string match {*u_tx.send_data*} $n]} {lappend tx_payload_data $p}
}
puts "HA2_REGISTER_COUNTS launch=[llength $launch_clocks] tx=[llength $tx_data] tx_payload=[llength $tx_payload_data] total=[llength [all_registers -clock_pins]]"
if {[llength $launch_clocks]!=1090 || [llength $tx_data]!=1216 || [llength $tx_payload_data]!=1088} {error "Full shape source/capture register census mismatch"}
foreach delay {max min} {
 foreach {label from to} [list local_join $launch_clocks $tx_data payload_join $launch_clocks $tx_payload_data all_reg2reg [all_registers -clock_pins] [all_registers -data_pins]] {
  set paths [find_timing_paths -path_delay $delay -from $from -to $to -group_path_count 1]
  if {![llength $paths]} {error "Missing measured $label $delay path"}
  puts "HA2_INTERNAL_SLACK $label $delay [get_property [lindex $paths 0] slack]"
  report_checks -path_delay $delay -from $from -to $to -group_path_count 1 -format full_clock_expanded -digits 3
 }
 set paths [find_timing_paths -path_delay $delay -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 10000 -endpoint_path_count 1]
 set seen {}
 foreach path $paths {dict set seen [get_full_name [get_property $path endpoint]] 1}
 puts "HA2_REG2REG_COVERAGE $delay timed_endpoints=[dict size $seen] all_register_data_pins=[llength [all_registers -data_pins]]"
 foreach p [all_registers -data_pins] {
  set n [get_full_name $p]
  if {![dict exists $seen $n]} {puts "HA2_UNQUALIFIED_REGISTER_ENDPOINT $delay $n"}
 }
}
foreach p [all_inputs -no_clocks] {puts "HA2_UNQUALIFIED_EXTERNAL INPUT [get_full_name $p]"}
foreach p [all_outputs] {puts "HA2_UNQUALIFIED_EXTERNAL OUTPUT [get_full_name $p]"}
puts "HA2_EXTERNAL_CENSUS inputs=[llength [all_inputs -no_clocks]] outputs=[llength [all_outputs]]"
check_setup -verbose
report_clock_latency -clock core_clk -digits 3
