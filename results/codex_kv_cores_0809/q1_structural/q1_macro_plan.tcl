# Fixed, data-flow-reviewed Q1 macro plan; lower SRAM pair shifted as one pinless-S/N stack.
proc q1_macro_site {name x y orient} {
 set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set i [$b findInst $name]
 if {$i eq "NULL"} {error "missing planned SRAM $name"}
 $i setPlacementStatus PLACED;$i setOrient $orient;$i setLocation 0 0;set q [$i getBBox]
 set xx [expr {int(round($x*$u))-[$q xMin]}];set yy [expr {int(round($y*$u))-[$q yMin]}]
 $i setLocation $xx $yy;$i setPlacementStatus LOCKED
 puts "Q1_PLANNED_SRAM $name $x $y $orient"
}
q1_macro_site {u_ref.u_leaf.u_a.u.u.g_static_rows.u_rows.g_data.g_macro\[0\].u_s} 112.104 127.404 R0
q1_macro_site {u_ref.u_leaf.u_a.u.u.g_static_rows.u_rows.g_data.g_macro\[1\].u_s} 8.64 127.404 R0
q1_macro_site {u_ref.u_leaf.u_b.u.g_static_rows.u_rows.g_data.g_macro\[0\].u_s} 12.961 73.98 MY
q1_macro_site {u_ref.u_leaf.u_b.u.g_static_rows.u_rows.g_data.g_macro\[1\].u_s} 12.961 32.892 R180
