# Opt-in optimization schedule: setup at SS during CTS/GRT; FF hold after DRT.
# This changes no clock, IO delay, uncertainty, false path, or final acceptance.
if {![llength [info commands ot_w2_repair_timing]]} {
  rename repair_timing ot_w2_repair_timing
  proc repair_timing {args} {
    if {[lsearch -exact $args -hold] >= 0} {
      error "W2 hold repair must run in the separate post-route FF session"
    }
    if {[lsearch -exact $args -recover_power] < 0 && [lsearch -exact $args -setup] < 0} {
      set args [linsert $args 0 -setup]
    }
    puts "W2_SETUP_ONLY repair_timing $args"
    return [uplevel 1 [list ot_w2_repair_timing {*}$args]]
  }
}
