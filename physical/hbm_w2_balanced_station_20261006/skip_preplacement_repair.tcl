# Only this floorplan interpreter is affected. Later placement/CTS/route
# interpreters retain the original helper and all timing constraints/repairs.
rename repair_timing_helper item6_original_repair_timing_helper
proc repair_timing_helper {args} {
  set i [lsearch -exact $args -sequence]
  if {$i>=0 && [lindex $args [expr {$i+1}]] eq "unbuffer,sizeup,swap,vt_swap"} {
    puts "ITEM6_SKIP_OPTIONAL_PREPLACEMENT_REPAIR: keep the exact mapped netlist; full later repairs retained"
    return
  }
  return [item6_original_repair_timing_helper {*}$args]
}
