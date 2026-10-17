# Cluster bounds check (tools/die_cluster, ROOT CLUSTER-FLOW 2026-10-16) -- run before global_route; fail closed.
# Counts: instances not fully inside the die (GRT-0035 / GRT-0028 source), unplaced instances, ports without a placed
# pin, port pins not inside the die or not touching the outline, nets whose every pin was dropped.  Writes a JSON report
# and returns the number of violations (0 = clean).
proc ot_cluster_bounds {report tag} {
  set block [ord::get_db_block]
  set die [$block getDieArea]
  set dx0 [$die xMin]; set dy0 [$die yMin]; set dx1 [$die xMax]; set dy1 [$die yMax]
  set n_inst 0; set out_inst 0; set unplaced 0; set out_names {}
  foreach inst [$block getInsts] {
    incr n_inst
    set st [$inst getPlacementStatus]
    if {$st eq "NONE" || $st eq "UNPLACED"} { incr unplaced; if {[llength $out_names] < 20} { lappend out_names "unplaced:[$inst getName]" }; continue }
    set bb [$inst getBBox]
    if {[$bb xMin] < $dx0 || [$bb yMin] < $dy0 || [$bb xMax] > $dx1 || [$bb yMax] > $dy1} {
      incr out_inst
      if {[llength $out_names] < 20} { lappend out_names [$inst getName] }
    }
  }
  set n_bt 0; set bt_unplaced 0; set bt_out 0; set bt_off_outline 0; set bt_names {}
  foreach bt [$block getBTerms] {
    incr n_bt
    set bps [$bt getBPins]
    if {[llength $bps] == 0} { incr bt_unplaced; if {[llength $bt_names] < 20} { lappend bt_names "unplaced:[$bt getName]" }; continue }
    foreach bp $bps {
      set st [$bp getPlacementStatus]
      if {$st eq "NONE" || $st eq "UNPLACED"} { incr bt_unplaced; continue }
      foreach box [$bp getBoxes] {
        set x0 [$box xMin]; set y0 [$box yMin]; set x1 [$box xMax]; set y1 [$box yMax]
        if {$x0 < $dx0 || $y0 < $dy0 || $x1 > $dx1 || $y1 > $dy1} {
          incr bt_out; if {[llength $bt_names] < 20} { lappend bt_names "outside:[$bt getName]" }
        } elseif {!($x0 == $dx0 || $y0 == $dy0 || $x1 == $dx1 || $y1 == $dy1)} {
          incr bt_off_outline; if {[llength $bt_names] < 20} { lappend bt_names "off_outline:[$bt getName]" }
        }
      }
    }
  }
  set n_net 0; set single 0
  foreach net [$block getNets] {
    if {[$net isSpecial]} { continue }
    incr n_net
    set k [expr {[llength [$net getITerms]] + [llength [$net getBTerms]]}]
    if {$k == 1} { incr single }
  }
  set viol [expr {$out_inst + $unplaced + $bt_unplaced + $bt_out + $bt_off_outline}]
  set f [open $report w]
  puts $f "{\"schema\": \"opentallas.die_cluster.bounds.v1\", \"tag\": \"$tag\", \"die_dbu\": \[$dx0, $dy0, $dx1, $dy1\],"
  puts $f " \"instances\": $n_inst, \"instances_outside_die\": $out_inst, \"instances_unplaced\": $unplaced,"
  puts $f " \"ports\": $n_bt, \"ports_unplaced\": $bt_unplaced, \"port_pins_outside_die\": $bt_out, \"port_pins_off_outline\": $bt_off_outline,"
  puts $f " \"signal_nets\": $n_net, \"single_terminal_nets\": $single, \"violations\": $viol,"
  set q {}
  foreach s [concat $out_names $bt_names] { lappend q "\"$s\"" }
  puts $f " \"first\": \[[join $q {, }]\]}"
  close $f
  puts "OT_CLUSTER_BOUNDS $tag instances=$n_inst outside=$out_inst unplaced=$unplaced ports=$n_bt ports_unplaced=$bt_unplaced port_pins_outside=$bt_out port_pins_off_outline=$bt_off_outline single_terminal_nets=$single violations=$viol"
  return $viol
}
