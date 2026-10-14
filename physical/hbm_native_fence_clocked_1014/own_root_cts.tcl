# OpenROAD -clk_nets selects the real own-root network. Child roots remain direct wires.
rename clock_tree_synthesis ::ot_fence_cts_original
proc clock_tree_synthesis {args} {
  set nets [get_nets -quiet -of_objects [get_ports clk]]
  if {[llength $nets] != 1} { error "FENCE_CTS: own clk has no unique actual net" }
  set name [get_full_name [lindex $nets 0]]
  puts "FENCE_CTS own root $name; 164 hard bank entries independent"
  ::ot_fence_cts_original {*}$args -clk_nets $name
}
