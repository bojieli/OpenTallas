set ::ot_ce_require_wire 1
# OT_CLOCK_ENTRY_DOMAIN_API_VERSION 1
# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.
set ::ot_ce_refs [dict create {ot_hgi_sm_pub_vmcore/clk} {tt {113.5 117.5 124.9} ff {93.0 97.1 104.1} ss {146.5 150.4 158.4}} {ot_hgi_sm_pub_vmport/clk} {tt {77.6 80.6 83.2} ff {61.8 64.7 67.3} ss {105.4 108.9 111.7}} {ot_hgi_sm_pub_cmd_relay/clk} {tt {50.9 51.5 52.3} ff {38.3 39.0 39.8} ss {72.5 73.1 74.0}} {ot_hgi_sm_pub_credit4/clk} {tt {42.3 42.4 42.4} ff {32.5 32.6 32.6} ss {58.9 58.9 59.0}} {ot_hgi_sm_pub_smrg_l1/clk} {tt {97.9 106.0 115.3} ff {78.0 86.6 96.2} ss {132.7 140.2 149.4}} {ot_hgi_sm_pub_smrg_l2/clk} {tt {95.6 103.1 111.1} ff {75.7 83.5 91.8} ss {130.4 137.6 146.0}} {ot_hgi_sm_pub_smrg_l3/clk} {tt {98.1 102.1 106.3} ff {78.3 82.1 86.2} ss {132.5 136.7 141.1}} {ot_hgi_sm_pub_return_d1/clk} {tt {42.7 42.7 42.8} ff {31.9 32.0 32.0} ss {61.0 61.0 61.1}} {ot_hgi_sm_pub_reset_hop/clk} {tt {0.3 0.3 0.3} ff {0.3 0.3 0.3} ss {0.3 0.3 0.3}} {ot_hgi_sm_pub_slice/clk} {tt {362.6 384.2 425.8} ff {291.4 311.4 350.9} ss {481.5 505.3 550.7}} {ot_hgi_sm_pub_cmd_quiet/clk} {tt {78.2 82.3 84.8} ff {62.6 66.7 69.2} ss {106.1 110.5 113.1}} {ot_hgi_sm_pub_reset/clk} {tt {44.0 44.1 44.1} ff {33.0 33.1 33.1} ss {62.7 62.8 62.9}} {ot_hgi_sm_pub_stream_edge/clk} {tt {51.8 53.0 54.7} ff {39.6 40.8 42.1} ss {72.9 74.4 76.6}}]
set ::ot_ce_counts [dict create {ot_hgi_sm_pub_vmcore} 4 {ot_hgi_sm_pub_vmport} 4 {ot_hgi_sm_pub_cmd_relay} 3 {ot_hgi_sm_pub_credit4} 8 {ot_hgi_sm_pub_smrg_l1} 4 {ot_hgi_sm_pub_smrg_l2} 2 {ot_hgi_sm_pub_smrg_l3} 1 {ot_hgi_sm_pub_return_d1} 20 {ot_hgi_sm_pub_reset_hop} 11 {ot_hgi_sm_pub_slice} 8 {ot_hgi_sm_pub_cmd_quiet} 1 {ot_hgi_sm_pub_reset} 1 {ot_hgi_sm_pub_stream_edge} 2]
set ::ot_ce_domains [dict create {core} {clock core_clk io_budget_ps 166.667 inputs {{*}} outputs {{*}}}]
set ::ot_ce_source_domains [dict create {clk_rst} {core} {clk_cmd} {core} {clk_reset_hops[0]} {core} {clk_reset_hops[1]} {core} {clk_reset_hops[2]} {core} {clk_reset_hops[3]} {core} {clk_reset_hops[4]} {core} {clk_reset_hops[5]} {core} {clk_reset_hops[6]} {core} {clk_reset_hops[7]} {core} {clk_reset_hops[8]} {core} {clk_reset_hops[9]} {core} {clk_reset_hops[10]} {core} {clk_stream_edge[0]} {core} {clk_stream_edge[1]} {core} {clk_credit[0]} {core} {clk_credit[1]} {core} {clk_credit[2]} {core} {clk_credit[3]} {core} {clk_credit[4]} {core} {clk_credit[5]} {core} {clk_credit[6]} {core} {clk_credit[7]} {core} {clk_cmd_relay[0]} {core} {clk_cmd_relay[1]} {core} {clk_cmd_relay[2]} {core} {clk_slice[0]} {core} {clk_slice[1]} {core} {clk_slice[2]} {core} {clk_slice[3]} {core} {clk_slice[4]} {core} {clk_slice[5]} {core} {clk_slice[6]} {core} {clk_slice[7]} {core} {clk_return[0]} {core} {clk_return[1]} {core} {clk_return[2]} {core} {clk_return[3]} {core} {clk_return[4]} {core} {clk_return[5]} {core} {clk_return[6]} {core} {clk_return[7]} {core} {clk_return[8]} {core} {clk_return[9]} {core} {clk_return[10]} {core} {clk_return[11]} {core} {clk_return[12]} {core} {clk_return[13]} {core} {clk_return[14]} {core} {clk_return[15]} {core} {clk_return[16]} {core} {clk_return[17]} {core} {clk_return[18]} {core} {clk_return[19]} {core} {clk_vm_core[0]} {core} {clk_vm_core[1]} {core} {clk_vm_core[2]} {core} {clk_vm_core[3]} {core} {clk_vm_port[0]} {core} {clk_vm_port[1]} {core} {clk_vm_port[2]} {core} {clk_vm_port[3]} {core} {clk_tree[0]} {core} {clk_tree[1]} {core} {clk_tree[2]} {core} {clk_tree[3]} {core} {clk_tree[4]} {core} {clk_tree[5]} {core} {clk_tree[6]} {core}]
set ::ot_ce_explicit_domains 0
set ::ot_ce_ports {{clk_rst} {clk_cmd} {clk_reset_hops[0]} {clk_reset_hops[1]} {clk_reset_hops[2]} {clk_reset_hops[3]} {clk_reset_hops[4]} {clk_reset_hops[5]} {clk_reset_hops[6]} {clk_reset_hops[7]} {clk_reset_hops[8]} {clk_reset_hops[9]} {clk_reset_hops[10]} {clk_stream_edge[0]} {clk_stream_edge[1]} {clk_credit[0]} {clk_credit[1]} {clk_credit[2]} {clk_credit[3]} {clk_credit[4]} {clk_credit[5]} {clk_credit[6]} {clk_credit[7]} {clk_cmd_relay[0]} {clk_cmd_relay[1]} {clk_cmd_relay[2]} {clk_slice[0]} {clk_slice[1]} {clk_slice[2]} {clk_slice[3]} {clk_slice[4]} {clk_slice[5]} {clk_slice[6]} {clk_slice[7]} {clk_return[0]} {clk_return[1]} {clk_return[2]} {clk_return[3]} {clk_return[4]} {clk_return[5]} {clk_return[6]} {clk_return[7]} {clk_return[8]} {clk_return[9]} {clk_return[10]} {clk_return[11]} {clk_return[12]} {clk_return[13]} {clk_return[14]} {clk_return[15]} {clk_return[16]} {clk_return[17]} {clk_return[18]} {clk_return[19]} {clk_vm_core[0]} {clk_vm_core[1]} {clk_vm_core[2]} {clk_vm_core[3]} {clk_vm_port[0]} {clk_vm_port[1]} {clk_vm_port[2]} {clk_vm_port[3]} {clk_tree[0]} {clk_tree[1]} {clk_tree[2]} {clk_tree[3]} {clk_tree[4]} {clk_tree[5]} {clk_tree[6]}}

proc ot_ce_corner {} {
  if {[info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC"} { return ff }
  if {[info exists ::ot_ce_corner]} { return $::ot_ce_corner }
  # WC is a scene label, not an actual library corner: option-B overlays WC
  # with TT. Bind the reference to actual loaded child Liberty objects.
  set found {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    set libcells [get_lib_cells -quiet -of_objects $cell]
    if {![llength $libcells]} { error "OT_ENTRIES: $master has no loaded Liberty association" }
    foreach lc $libcells {
      set full [get_full_name $lc]
      if {![regexp -nocase {_(tt|ff|ss)/} $full -> corner]} { error "OT_ENTRIES: unknown actual child Liberty corner $full" }
      dict set found [string tolower $corner] 1
    }
  }
  if {[dict size $found] == 1} { return [lindex [dict keys $found] 0] }
  # A multi-mode database needs its actual setup corner or BC scene shim.
  if {[info exists ::env(OT_MM_SETUP_CORNER)]} {
    switch -nocase -- $::env(OT_MM_SETUP_CORNER) {
      TC - tt {set corner tt} BC - ff {set corner ff} WC - ss {set corner ss}
      default { error "OT_ENTRIES: unknown actual setup corner" }
    }
    if {[dict exists $found $corner]} { return $corner }
  }
  error "OT_ENTRIES: ambiguous actual loaded child corners [dict keys $found]"
}
# get_property pin arrival_max_rise is a DATA arrival query. On a clock-only
# macro pin it returns an infinity sentinel even with a finite propagated clock
# path. Read the actual rising clock path in the current analysis scene instead.
proc ot_ce_finite {value} {
  return [expr {[string is double -strict $value] && ![regexp -nocase {inf|nan} $value]}]
}
proc ot_ce_clock_wire {pin clock} {
  set scene [get_property [sta::cmd_scene] name]
  set clock_name [get_full_name $clock]
  set values {}
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    set paths [$vertex path_iterator rise max]
    while {[$paths has_next]} {
      set path [$paths next]
      # OpenSTA's Path tag identifies scene, rise/max, clock and propagation.
      # Match the complete fixed fields, never accept another scene's path.
      set tag [$path tag]
      if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne "^max" ||
          [lindex $tag 3] ne $clock_name || [lindex $tag 4] ne "^" ||
          [string first "(clock prop)" $tag] < 0} continue
      set arrival [sta::time_sta_ui [$path arrival]]
      if {![ot_ce_finite $arrival]} {
        $paths finish
        error "OT_ENTRIES: nonfinite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
      }
      lappend values $arrival
    }
    $paths finish
  }
  if {[llength $values] != 1} {
    # Synthesis/floorplan have no extracted entry wire. This is solely a finite
    # pre-CTS diagnostic reference; routed gates must measure a clock path.
    if {![llength $values] && [info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts &&
        (![info exists ::ot_ce_require_wire] || !$::ot_ce_require_wire)} {
      puts "OT_ENTRIES PRE_CTS_ZERO_WIRE [get_full_name $pin] scene=$scene"
      return 0.0
    }
    error "OT_ENTRIES: missing unique finite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
  }
  return [lindex $values 0]
}
proc ot_ce_apply {} {
  set corner [ot_ce_corner]
  set clk [get_clocks core_clk]
  if {[llength $clk] != 1} { error "OT_ENTRIES: core_clk missing" }
  # Wires-only parents have no CTS tree to set this flag for us.
  # Ideal clocks silently report zero network arrival despite real entry wires.
  set_propagated_clock [get_clocks ot_entry_*]
  set sources {}; set names {}
  foreach c [get_clocks ot_entry_*] {
    foreach p [get_property $c sources] { lappend sources $p; lappend names [get_full_name $p] }
  }
  if {[lsort $names] ne [lsort $::ot_ce_ports]} { error "OT_ENTRIES: source clock coverage differs from spec" }
  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }
  sta::worst_slack_cmd max
  set rows {}; set seen {}; set counts {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    dict incr counts $master
    foreach pin [get_pins -quiet -of_objects $cell] {
      set key "$master/[get_property $pin lib_pin_name]"
      if {![dict exists $::ot_ce_refs $key]} continue
      set ports [get_ports -quiet -of_objects [get_nets -quiet -of_objects $pin]]
      if {[llength $ports] != 1} { error "OT_ENTRIES: [get_full_name $pin] lacks one direct top clock port" }
      set port [lindex $ports 0]; set name [get_full_name $port]
      if {$name ni $::ot_ce_ports || [dict exists $seen $name]} { error "OT_ENTRIES: duplicate or undeclared source $name" }
      dict set seen $name 1
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set wire [ot_ce_clock_wire $pin $clock]
      if {![ot_ce_finite $wire]} { error "OT_ENTRIES: nonfinite entry wire clock arrival on [get_full_name $pin]" }
      if {abs($wire) < 1.0e-9 && [info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
        # A zero arrival is admissible only if actual source and child pin are
        # physically coincident. Missing parasitics/ideal clocks cannot qualify.
        if {![llength [info commands ord::get_db_block]]} { error "OT_ENTRIES: zero wire lacks physical source/pin proof" }
        set block [ord::get_db_block]
        set bt [$block findBTerm $name]
        set it [$block findITerm [get_full_name $pin]]
        if {$bt eq "NULL" || $it eq "NULL"} { error "OT_ENTRIES: missing physical source/child clock pin" }
        set pb [$bt getBBox]; set ib [$it getBBox]
        set distance [expr {(abs(([$pb xMin]+[$pb xMax])-([$ib xMin]+[$ib xMax])) + abs(([$pb yMin]+[$pb yMax])-([$ib yMin]+[$ib yMax]))) / 2.0 / [$block getDbUnitsPerMicron]}]
        if {$distance > 0.001} { error "OT_ENTRIES: zero clock wire arrival despite $distance um source/pin separation on $name" }
        puts "OT_ENTRIES ZERO_WIRE_PROVEN $name [get_full_name $pin] distance=$distance"
      }
      lassign [dict get $::ot_ce_refs $key $corner] lo mean hi
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set ttmean [lindex [dict get $::ot_ce_refs $key tt] 1]
      set domain [dict get $::ot_ce_source_domains $name]
      set vc [get_clocks [dict get $::ot_ce_domains $domain clock]]
      if {abs([get_property $vc period]-[get_property $clock period])>0.001} { error "OT_ENTRIES: domain/source period mismatch $name" }
      lappend rows [list $port $pin $wire $lo $mean $hi $clock $ttmean $domain]
    }
  }
  dict for {m n} $::ot_ce_counts {
    if {![dict exists $counts $m] || [dict get $counts $m] != $n} { error "OT_ENTRIES: bound child count mismatch $m" }
  }
  if {[dict size $seen] != [llength $::ot_ce_ports]} { error "OT_ENTRIES: incomplete actual child/source coverage" }
  set ref 0
  foreach row $rows { lassign $row p pin wire lo mean hi; set ref [expr {max($ref, $wire + $mean)}] }
  set low {}; set high {}; set lowclocks {}; set highclocks {}; set domain_low {}; set domain_high {}
  foreach row $rows {
    lassign $row p pin wire lo mean hi clock ttmean domain
    # Physical source level includes the entry wire, not just the hard
    # child's internal insertion. Only a TT scene measures the TT wire.
    # Other physical scenes conservatively reserve the deep pair budget;
    # they must not guess TT wire delay from FF/SS or an ideal zero arrival.
    set deep [expr {$ttmean > 300}]
    set level_basis "zero-wire diagnostic"
    if {$corner eq "tt"} {
      set deep [expr {$ttmean + $wire > 300}]
      set level_basis "TT timing-graph entry arrival + child R (physical proof required for route/signoff)"
    } elseif {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
      set deep 1
      set level_basis "TT wire level not measured in this scene; conservative210ps setup"
    }
    if {$deep} { lappend highclocks $clock } else { lappend lowclocks $clock }
    puts "OT_ENTRIES LEVEL [get_full_name $p] deep=$deep basis=$level_basis"
    set latency [expr {$ref - $wire - $mean}]
    if {![ot_ce_finite $ref] || ![ot_ce_finite $latency]} { error "OT_ENTRIES: nonfinite reference/source latency on [get_full_name $p]" }
    set_clock_latency -source $latency $clock
    lappend low [expr {$ref + $lo - $mean}]; lappend high [expr {$ref + $hi - $mean}]
    dict lappend domain_low $domain [expr {$ref + $lo - $mean}]
    dict lappend domain_high $domain [expr {$ref + $hi - $mean}]
    puts "OT_ENTRIES COMP $corner [get_full_name $p] -> [get_full_name $pin] wire=$wire R=$mean latency=$latency phi=$ref"
  }
  # Every entry is synchronous and related. Reserve die skew on internal hops;
  # no asynchronous groups, false paths or ETM insertion add-back.
  set_clock_uncertainty -setup 150 -from [get_clocks ot_entry_*] -to [get_clocks ot_entry_*]
  # H1 authoritative pair_check.HOLD_TREE =50ps hold margin+50ps die skew.
  # Tile-local25ps uncertainty is not the composed pair margin.
  set_clock_uncertainty -hold 100 -from [get_clocks ot_entry_*] -to [get_clocks ot_entry_*]
  # Each deep tile has its own earlier trunk tap. The authoritative TREE
  # pair budget uses150ps die skew when either reference exceeds300ps,
  # including deep-to-deep pairs (pair_check.SKEW_DEEP).
  if {[llength $highclocks]} {
    set_clock_uncertainty -setup 210 -from $highclocks -to [get_clocks ot_entry_*]
    set_clock_uncertainty -setup 210 -from [get_clocks ot_entry_*] -to $highclocks
  }
  # Preserve measured boundary spread: balancing the mean does not erase the
  # earliest/latest physical boundary arrivals or change ETM setup/hold arcs.
  set lmin [lindex [lsort -real $low] 0]; set lmax [lindex [lsort -real $high] end]
  unset_input_delay [all_inputs]; unset_output_delay [all_outputs]
  set sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  set covered_in {}; set covered_out {}
  dict for {domain info} $::ot_ce_domains {
    if {![dict exists $domain_low $domain]} { error "OT_ENTRIES: domain $domain has no actual child clock pins" }
    set dlmin [lindex [lsort -real [dict get $domain_low $domain]] 0]
    set dlmax [lindex [lsort -real [dict get $domain_high $domain]] end]
    set vc [get_clocks [dict get $info clock]]
    set budget [dict get $info io_budget_ps]
    set inputs {}; set outputs {}
    foreach pattern [dict get $info inputs] {
      foreach p [get_ports -quiet $pattern -filter "direction == input"] {
        set n [get_full_name $p]
        if {$n in $::ot_ce_ports} continue
        if {[dict exists $covered_in $n]} { error "OT_ENTRIES: input $n has duplicate IO domains" }
        dict set covered_in $n $domain; lappend inputs $p
      }
    }
    foreach pattern [dict get $info outputs] {
      foreach p [get_ports -quiet $pattern -filter "direction == output"] {
        set n [get_full_name $p]
        if {[dict exists $covered_out $n]} { error "OT_ENTRIES: output $n has duplicate IO domains" }
        dict set covered_out $n $domain; lappend outputs $p
      }
    }
    if {[llength $inputs]} {
      set_input_delay [expr {$budget+$dlmax+$sk}] -max -clock $vc $inputs
      set_input_delay [expr {$dlmin-$hki}] -min -clock $vc $inputs
    }
    if {[llength $outputs]} {
      set_output_delay [expr {$budget-$dlmax+$sk}] -max -clock $vc $outputs
      set_output_delay [expr {-$dlmin-$hk}] -min -clock $vc $outputs
    }
    if {[info exists ::env(OT_IO_INTER)] && $::env(OT_IO_INTER) ne ""} {
      foreach pattern [split $::env(OT_IO_INTER) ","] {
        foreach p [get_ports -quiet $pattern] {
          set n [get_full_name $p]
          if {[dict exists $covered_in $n] && [dict get $covered_in $n] eq $domain} {
            set_input_delay [expr {$budget+$dlmax+150}] -max -clock $vc $p
          }
          if {[dict exists $covered_out $n] && [dict get $covered_out $n] eq $domain} {
            set_output_delay [expr {$budget-$dlmax+150}] -max -clock $vc $p
          }
        }
      }
    }
    puts "OT_ENTRIES DOMAIN $domain [get_property $vc period]ps IO[llength $inputs]/[llength $outputs] boundary=$dlmin..$dlmax"
  }
  if {[dict size $covered_in] != [llength [all_inputs -no_clocks]] || [dict size $covered_out] != [llength [all_outputs]]} {
    error "OT_ENTRIES: incomplete actual IO domain coverage (resets must also have a domain)"
  }
  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"
}
ot_ce_apply
