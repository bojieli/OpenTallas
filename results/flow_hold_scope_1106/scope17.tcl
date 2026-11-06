# PRIVATE prototype only: restore complete active-mode SDC after repair-only port exclusions.
proc ot_scope_read {p} {set f [open $p r];set s [read $f];close $f;return $s}
proc ot_hold_scope {body} {
  set entry [sta::cmd_mode_name]
  set_mode ff
  set stem [file join $::env(RESULTS_DIR) scope_[pid]_[clock clicks]]
  set before ${stem}_before.sdc
  write_sdc -mode ff -digits 17 -no_timestamp $before
  set inputs [all_inputs];set outputs [all_outputs]
  puts "OT_HOLD_SCOPE begin input_ports=[llength $inputs] output_ports=[llength $outputs] full=[ot_hold_stats]"
  try {
    if {[llength $inputs]} {set_false_path -hold -from $inputs}
    if {[llength $outputs]} {set_false_path -hold -to $outputs}
    puts "OT_HOLD_SCOPE internal=[ot_hold_stats]"
    set_mode $entry
    return [uplevel 1 $body]
  } finally {
    set_mode ff
    if {[llength $inputs]} {unset_path_exceptions -hold -from $inputs}
    if {[llength $outputs]} {unset_path_exceptions -hold -to $outputs}
    read_sdc -mode ff $before
    set after ${stem}_after.sdc
    write_sdc -mode ff -digits 17 -no_timestamp $after
    if {[ot_scope_read $before] ne [ot_scope_read $after]} {error "PRIVATE_SCOPE_RESTORE_FAIL: original SDC differs ($before $after)"}
    puts "OT_HOLD_SCOPE restored EXACT_SDC full=[ot_hold_stats]"
    set_mode $entry
  }
}
if {[llength [info commands ot_repair_hold_guarded]] && ![llength [info commands ot_repair_hold_guarded_unscoped]]} {
  rename ot_repair_hold_guarded ot_repair_hold_guarded_unscoped
  proc ot_repair_hold_guarded {args} {return [ot_hold_scope {ot_repair_hold_guarded_unscoped {*}$args}]}
}
