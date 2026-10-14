# S81 HC candidate: enforce the existing actual pin windows with 10 ps implementation margin.
# MAX constraints only. Existing input/output MIN delays, hold uncertainty, period and false paths are untouched.
set pw_clock [get_clocks -quiet core_clk]
if {[llength $pw_clock] != 1 || [llength [all_clocks]] != 1} { error "PIN_WINDOW_MAX requires one explicit core_clk" }
catch {sta::worst_slack_cmd max}
set pw_refs {}
foreach pw_pin [all_registers -clock_pins] {
  set pw_arr [get_property $pw_pin arrival_max_rise]
  if {[string is double -strict $pw_arr] && $pw_arr > 0 && $pw_arr < 1.0e9} { lappend pw_refs $pw_arr }
}
if {![llength $pw_refs]} { error "PIN_WINDOW_MAX: no propagated register clock arrivals" }
set pw_refs [lsort -real $pw_refs]
set pw_R [lindex $pw_refs [expr {[llength $pw_refs] / 2}]]
set pw_T [get_property $pw_clock period]
# Generator uses 60 ps setup uncertainty; 180/210 are stricter than owner capture190/launch220.
set pw_in [expr {$pw_T - 60.0 - 180.0 + $pw_R}]
set pw_out [expr {$pw_T - 60.0 - 210.0 - $pw_R}]
set_input_delay $pw_in -max -clock core_clk [all_inputs -no_clocks]
set_output_delay $pw_out -max -clock core_clk [all_outputs]
puts [format "PIN_WINDOW_MAX: T %.3f R_median %.3f in_max %.3f out_max %.3f target_capture180 target_launch210; MIN/hold unchanged" $pw_T $pw_R $pw_in $pw_out]
