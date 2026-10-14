# Related PLL /3 and /4 clocks. No asynchronous groups or crossing exceptions.
set ot_bound_period [expr {[get_property [get_clocks core_clk] period]*4.0/3.0}]
if {![llength [get_clocks -quiet vm_clk]]} { create_clock -name vm_clk -period $ot_bound_period [get_ports rclk] }
set_clock_uncertainty -setup 150 -from [get_clocks {core_clk vm_clk}] -to [get_clocks {core_clk vm_clk}]
set_clock_uncertainty -hold 100 -from [get_clocks {core_clk vm_clk}] -to [get_clocks {core_clk vm_clk}]
foreach {c ins outs} {core_clk {wrst_n we wdata* wepoch*} {full rd_freed* w_fault} vm_clk {rrst_n re repoch*} {rdata* empty r_fault}} {
 set cc [get_clocks $c]; set offmax 0; set offmin 0
 if {![info exists ::ot_ref_pre_cts] || !$::ot_ref_pre_cts} {
  set_propagated_clock $cc; sta::worst_slack_cmd max
  set arrivals {}
  foreach pin [all_registers -clock $cc -clock_pins] {
   set a [get_property $pin arrival_max_rise]
   if {[string is double -strict $a]} { lappend arrivals [list $a $pin] }
  }
  if {![llength $arrivals]} { error "BOUNDED_CDC: actual clock root has no timed registers $c" }
  set a [lindex [lsort -real -index 0 $arrivals] [expr {[llength $arrivals]/2}]]
  set offmax [lindex $a 0];set offmin [get_property [lindex $a 1] arrival_min_rise]
  puts "BOUNDED_CDC_BOUNDARY $c logicalclockpins=[llength $arrivals] min=$offmin max=$offmax"
 }
 set budget [expr {$c eq "core_clk" ? 166.6666 : 222.2222}]
 set ip {}; set op {}
 foreach pat $ins { foreach x [get_ports -quiet $pat] { lappend ip $x } }
 foreach pat $outs { foreach x [get_ports -quiet $pat] { lappend op $x } }
 unset_input_delay $ip;unset_output_delay $op
 set_input_delay [expr {$budget+$offmax+90}] -max -clock $cc $ip
 set_input_delay $offmin -min -clock $cc $ip
 set_output_delay [expr {$budget-$offmax+90}] -max -clock $cc $op
 set_output_delay [expr {-$offmin-50}] -min -clock $cc $op
}
