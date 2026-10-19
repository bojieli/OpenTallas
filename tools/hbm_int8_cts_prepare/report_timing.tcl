# Native clock-family active-edge wire arrival, same API as ck_insertion39021.
source /work/kit/vendor/clock_family.tcl
ot_cf_refresh
report_units
check_setup -verbose
report_checks -unconstrained -path_delay min_max -format full_clock_expanded -group_path_count 30
set f [open /work/output/clock_pins_[expr {[info exists ::env(INT8_CORNER)] ? $::env(INT8_CORNER) : "TT"}].tsv w]
puts $f "pin\tactive_edge_wire_arrival\tslew_max_rise"
foreach pin [all_registers -clock_pins] {
 set owners [get_property $pin clocks]
 if {[llength $owners] != 1} {error "AMBIGUOUS_CLOCK_OWNER [get_full_name $pin]"}
 puts $f "[get_full_name $pin]\t[ot_cf_wire $pin $owners]\t[get_property $pin slew_max_rise]"
}
close $f
# Separate actual path classes: top IO violations cannot hide internal paths.
set corner [expr {[info exists ::env(INT8_CORNER)] ? $::env(INT8_CORNER) : "TT"}]
set regs [all_registers]
set async_pins {}
foreach pin [get_pins -of_objects $regs] {
 if {[get_property $pin lib_pin_name] in {RESETN SETN}} {lappend async_pins $pin}
}
if {![llength $async_pins]} {error "MISSING_NATIVE_ASYNC_CONTROL_ENDPOINTS"}
foreach class {r2r i2r r2o reset_input async_recovery_removal} {
 foreach delay {max min} {
  set args [list -path_delay $delay -format full_clock_expanded -group_path_count 30]
  switch $class {
   r2r {lappend args -from $regs -to $regs}
   i2r {lappend args -from [all_inputs -no_clocks] -to $regs}
   r2o {lappend args -from $regs -to [all_outputs]}
   reset_input {lappend args -from [get_ports rst_n] -to $regs}
   async_recovery_removal {lappend args -to $async_pins}
  }
  sta::redirect_string_begin
  set rc [catch {report_checks {*}$args} message opts]
  set text [sta::redirect_string_end]
  set fd [open /work/output/paths_${corner}_${class}_${delay}.rpt w]
  puts $fd $text
  close $fd
  puts "NATIVE_PATH_CLASS corner=$corner class=$class delay=$delay async_control_endpoints=[llength $async_pins]"
  puts $text
  if {$rc} {return -options $opts $message}
 }
}
