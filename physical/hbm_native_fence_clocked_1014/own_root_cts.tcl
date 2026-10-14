# OpenROAD -clk_nets selects the real own-root network. Child roots remain direct wires.
rename clock_tree_synthesis ::ot_fence_cts_original
proc clock_tree_synthesis {args} {
  set bt [[ord::get_db_block] findBTerm clk]
  if {$bt eq "NULL"} { error "FENCE_CTS: own clk has no actual BTerm" }
  set net [$bt getNet]
  if {$net eq "NULL"} { error "FENCE_CTS: own clk has no actual net" }
  set name [$net getName]
  puts "FENCE_CTS own root $name; 164 hard bank entries independent"
  ::ot_fence_cts_original {*}$args -clk_nets $name
}
