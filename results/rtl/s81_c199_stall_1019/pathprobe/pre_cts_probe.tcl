source /work/hooks/pre_cts_ot_cts_fix.tcl
rename repair_timing ::s81_c199_original_repair
proc repair_timing {args} {
  puts "C199_REPAIR_POINT args=$args"
  if {[lsearch -exact $args -hold]>=0} {
    puts "C199_INITIAL_FF_HOLD_REPORT_BEGIN"
    report_checks -path_delay min -format full_clock_expanded -group_count 8 -endpoint_count 1 -digits 4
    puts "C199_INITIAL_FF_HOLD_REPORT_END"
    set b [ord::get_db_block]
    set c 0
    foreach i [$b getInsts] {if {[$i isDoNotTouch]} {incr c}}
    puts "C199_PROTECTED_INSTANCES $c"
    write_db /work/c199_before_hold.odb
    write_sdc /work/c199_before_hold.sdc
    error "C199_DIAGNOSTIC_STOP_BEFORE_HOLD_REPAIR"
  }
  return [::s81_c199_original_repair {*}$args]
}
