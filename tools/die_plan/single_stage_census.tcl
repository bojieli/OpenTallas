# Independent exhaustive structural census for a partition with no internal register-to-register data paths.
# No skew value is inferred here. A zero-related-pair result is usable only when this separate census PASSes.
# Run after libraries/netlist/SDC/parasitics are loaded, with propagated clocks. Async reset/set pins are excluded;
# all data fan-in arcs (including disabled/false paths and inter-clock paths) remain part of the structure.

proc ot_ss_inst {name} {return [regsub {/[^/]+$} $name {}]}

proc ot_ss_has_arrival {pin clk mode} {
  set clock_name [get_full_name $clk]
  set vals {}
  if {[catch {
    foreach v [$pin vertices] {
      if {$v eq "NULL"} continue
      set it [$v path_iterator rise $mode]
      while {[$it has_next]} {
        set p [$it next]
        set tag [$p tag]
        if {[lindex $tag 3] ne $clock_name || [string first "(clock prop)" $tag]<0} continue
        set a [$p arrival]
        if {![string is double -strict $a] || [regexp -nocase {inf|nan} $a]} continue
        if {[lsearch -real $vals $a]<0} {lappend vals $a}
      }
      $it finish
    }
  }]} {return 0}
  return [expr {[llength $vals]==1}]
}

proc ot_ss_census {} {
  # All timing queries finish before any caller starts a PathEnd search (OpenSTA invalidates live PathEnds).
  set out [dict create done 0 status FAIL registers 0 clocked 0 missing_clock 0 missing_arrival 0 internal_pairs_any 0 data_pins 0]
  set problems {}
  if {[catch {
    sta::worst_slack_cmd max
    sta::worst_slack_cmd min
    set regs {}
    foreach c [all_registers] {dict set regs [get_full_name $c] 1}
    dict set out registers [dict size $regs]
    set pins {}
    foreach p [all_registers -clock_pins] {dict lappend pins [ot_ss_inst [get_full_name $p]] $p}
    dict for {name _} $regs {
      set cp [expr {[dict exists $pins $name] ? [dict get $pins $name] : {}}]
      if {[llength $cp]!=1} {
        dict incr out missing_clock
        lappend problems "$name: [llength $cp] clock pins, require exactly one"
        continue
      }
      set p [lindex $cp 0]
      set cl [get_property $p clocks]
      if {[llength $cl]!=1} {
        dict incr out missing_clock
        lappend problems "$name: [llength $cl] clocks, require exactly one"
        continue
      }
      dict incr out clocked
      if {![ot_ss_has_arrival $p [lindex $cl 0] max] || ![ot_ss_has_arrival $p [lindex $cl 0] min]} {
        dict incr out missing_arrival
        lappend problems "$name: absent or ambiguous propagated clock arrival"
      }
    }
    set async {}
    foreach p [all_registers -async_pins] {dict set async [get_full_name $p] 1}
    set pairs {}
    foreach d [all_registers -data_pins] {
      set dn [get_full_name $d]
      if {[dict exists $async $dn]} continue
      dict incr out data_pins
      set capture [ot_ss_inst $dn]
      foreach p [get_fanin -to $d -flat -startpoints_only -trace_arcs all] {
        set launch [ot_ss_inst [get_full_name $p]]
        if {[dict exists $regs $launch]} {dict set pairs "$launch\t$capture" 1}
      }
    }
    dict set out internal_pairs_any [dict size $pairs]
    if {[dict size $pairs]} {lappend problems "internal data pairs exist: [dict size $pairs]"}
    dict set out done 1
    if {[dict get $out registers]>0 && [dict get $out missing_clock]==0 && [dict get $out missing_arrival]==0 && [dict get $out internal_pairs_any]==0} {
      dict set out status PASS
    }
  } err]} {lappend problems "census query failed: $err"}
  dict set out problems $problems
  return $out
}
