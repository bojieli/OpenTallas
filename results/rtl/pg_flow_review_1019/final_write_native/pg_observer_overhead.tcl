source /proof/native_pg_binding.tcl
read_db /clone/source_order_clone.odb
set ::env(OT_PG_STRICT) 1
ot_pg_install_rc_observers
set block [ord::get_db_block]
puts "OVERHEAD_DIMENSIONS instances=[llength [$block getInsts]] pg_terms=[dict get [ot_pg_collect_all_native $block [ot_pg_prepare $block]] checked]"
foreach mode {raw wrapped} {
  for {set n 0} {$n < 3} {incr n} {
    set begin [clock milliseconds]
    if {$mode eq "raw"} {ot_pg_native_global_connect} else {global_connect}
    puts "OVERHEAD_GLOBAL $mode sample=$n elapsed_ms=[expr {[clock milliseconds]-$begin}]"
  }
}
foreach mode {raw wrapped} {
  for {set n 0} {$n < 3} {incr n} {
    set begin [clock milliseconds]
    if {$mode eq "raw"} {
      ot_pg_native_add_global_connection -net VDD -inst_pattern .* -pin_pattern {^VDD$} -power
    } else {
      add_global_connection -net VDD -inst_pattern .* -pin_pattern {^VDD$} -power
    }
    puts "OVERHEAD_RULE $mode sample=$n elapsed_ms=[expr {[clock milliseconds]-$begin}]"
  }
}
if {$::ot_pg_bindings_dirty != 0} {error "NOOP_RULE_CHANGED_BINDINGS $::ot_pg_bindings_dirty"}
puts NATIVE_OBSERVER_OVERHEAD_PASS
exit
