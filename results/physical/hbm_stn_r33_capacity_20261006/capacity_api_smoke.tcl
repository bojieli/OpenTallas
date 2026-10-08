read_db /base/4_1_cts.odb
set ::env(OT_STN_R33_CAPACITY) 1
proc repair_timing_helper {args} {
  sta::check_percent -max_buffer_percent [lindex $args end]
  if {![catch {sta::check_percent -repair_tns 101}]} {error "other validation lost"}
  puts "R33_CAPACITY_API_PASS $args"
}
source /src/physical/hbm_accel_die_views/stations/bench/stn_repair_capacity.tcl
repair_timing_helper -hold_margin 35
if {![catch {sta::check_percent -max_buffer_percent 300}]} {error "checker not restored"}
proc ot_orig_repair_timing_helper {args} {error "deliberate helper failure"}
if {![catch {repair_timing_helper -hold_margin 35}]} {error "failure masked"}
if {![catch {sta::check_percent -max_buffer_percent 300}]} {error "checker not restored after error"}
puts R33_CAPACITY_RESTORE_PASS
exit
