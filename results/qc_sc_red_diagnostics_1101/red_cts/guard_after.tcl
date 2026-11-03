# Normal fixed-tree CTS may lift original face-flop dont_touch. Restore exact
# input flags before writing the retained result; never waive a changed graph.
dict for {name state} $::red_before_cells {
 set i [$::red_guard_block findInst $name]
 if {$i eq "NULL"} {error "RED_CTS_MISSING_CELL $name"}
 $i setPlacementStatus [lindex $state 3]
 $i setDoNotTouch [lindex $state 4]
}
dict for {name state} $::red_before_nets {
 set n [$::red_guard_block findNet $name]
 if {$n eq "NULL"} {error "RED_CTS_MISSING_NET $name"}
 $n setDoNotTouch [lindex $state 2]
}
if {[red_cells] ne $::red_before_cells} {error RED_CTS_CHANGED_CELL_MASTER_POSE_STATUS}
if {[red_incidence] ne $::red_before_inc} {error RED_CTS_CHANGED_CLOCK_OR_SIGNAL_GRAPH}
if {[red_terms] ne $::red_before_terms || [red_nets] ne $::red_before_nets} {error RED_CTS_CHANGED_TERMS_NETS_FLAGS}
puts "RED_CTS_FIXED_IDENTITY_PASS all_original_cells_poses_graph_flags"
