set ::ot_ce_require_wire 1
# OT_CLOCK_ENTRY_DOMAIN_API_VERSION 1
# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.
set ::ot_ce_refs [dict create {ot_qwen_tile_rpair/clk} {tt {288.3 309.1 346.3} ff {236.7 256.8 293.2} ss {372.7 394.7 432.5}} {ot_qwen_tile_node/clk} {tt {231.8 246.6 259.0} ff {187.5 200.6 211.8} ss {307.6 325.2 339.3}} {ot_qwen_tile_lsl_fp1/clk} {tt {160.1 165.7 172.0} ff {128.7 133.9 140.2} ss {214.5 221.0 227.1}} {qkh_packet_v16/clk} {tt {51.8 52.4 52.9} ff {38.5 39.1 39.6} ss {74.1 75.0 75.6}} {qkh_packet_h256/clk} {tt {72.1 76.0 79.6} ff {57.1 61.0 64.8} ss {98.5 102.2 105.8}} {qkh_packet_v256/clk} {tt {71.5 73.5 75.3} ff {56.7 58.7 60.5} ss {97.6 99.6 101.3}} {qwen_glue_v508/clk} {tt {78.4 83.2 87.0} ff {61.5 66.7 70.7} ss {108.1 112.6 116.7}} {qwen_glue_v514/clk} {tt {79.9 83.7 88.8} ff {63.4 67.2 72.5} ss {109.3 113.1 118.1}} {qwen_glue_x1028/clk_o} {tt {98.7 103.1 106.3} ff {80.1 84.5 87.7} ss {130.2 134.6 137.8}} {qwen_glue_x1028/clk_i} {tt {93.2 98.2 101.5} ff {74.9 80.0 83.2} ss {124.5 129.6 133.0}}]
set ::ot_ce_counts [dict create {ot_qwen_tile_rpair} 5 {ot_qwen_tile_node} 1 {ot_qwen_tile_lsl_fp1} 8 {qkh_packet_v16} 12 {qkh_packet_h256} 18 {qkh_packet_v256} 28 {qwen_glue_v508} 1 {qwen_glue_v514} 6 {qwen_glue_x1028} 2]
set ::ot_ce_domains [dict create {core} {clock core_clk io_budget_ps 166.667 inputs {{*}} outputs {{*}}}]
set ::ot_ce_source_domains [dict create {ck} {core} {ck_bank[0]} {core} {ck_bank[1]} {core} {ck_bank[2]} {core} {ck_bank[3]} {core} {ck_bank[4]} {core} {ck_bank[5]} {core} {ck_bank[6]} {core} {ck_bank[7]} {core} {ck_bank[8]} {core} {ck_bank[9]} {core} {ck_bank[10]} {core} {ck_bank[11]} {core} {ck_bank[12]} {core} {ck_bank[13]} {core} {ck_bank[14]} {core} {ck_bank[15]} {core} {ck_bank[16]} {core} {ck_bank[17]} {core} {ck_bank[18]} {core} {ck_bank[19]} {core} {ck_bank[20]} {core} {ck_bank[21]} {core} {ck_bank[22]} {core} {ck_bank[23]} {core} {ck_bank[24]} {core} {ck_bank[25]} {core} {ck_bank[26]} {core} {ck_bank[27]} {core} {ck_bank[28]} {core} {ck_bank[29]} {core} {ck_bank[30]} {core} {ck_bank[31]} {core} {ck_bank[32]} {core} {ck_bank[33]} {core} {ck_bank[34]} {core} {ck_bank[35]} {core} {ck_bank[36]} {core} {ck_bank[37]} {core} {ck_bank[38]} {core} {ck_bank[39]} {core} {ck_bank[40]} {core} {ck_bank[41]} {core} {ck_bank[42]} {core} {ck_bank[43]} {core} {ck_bank[44]} {core} {ck_bank[45]} {core} {ck_bank[46]} {core} {ck_bank[47]} {core} {ck_bank[48]} {core} {ck_bank[49]} {core} {ck_bank[50]} {core} {ck_bank[51]} {core} {ck_bank[52]} {core} {ck_bank[53]} {core} {ck_bank[54]} {core} {ck_bank[55]} {core} {ck_bank[56]} {core} {ck_bank[57]} {core} {ck_reset[0]} {core} {ck_reset[1]} {core} {ck_reset[2]} {core} {ck_reset[3]} {core} {ck_reset[4]} {core} {ck_reset[5]} {core} {ck_reset[6]} {core} {ck_reset[7]} {core} {ck_reset[8]} {core} {ck_reset[9]} {core} {ck_reset[10]} {core} {ck_child[0]} {core} {ck_child[1]} {core} {ck_child[2]} {core} {ck_child[3]} {core} {ck_child[4]} {core} {ck_child[5]} {core} {ck_child[6]} {core} {ck_child[7]} {core} {ck_child[8]} {core} {ck_child[9]} {core} {ck_child[10]} {core} {ck_child[11]} {core} {ck_child[12]} {core} {ck_child[13]} {core}]
set ::ot_ce_explicit_domains 1
set ::ot_ce_cts_roots {{ck}}
set ::ot_ce_ports {{ck} {ck_bank[0]} {ck_bank[1]} {ck_bank[2]} {ck_bank[3]} {ck_bank[4]} {ck_bank[5]} {ck_bank[6]} {ck_bank[7]} {ck_bank[8]} {ck_bank[9]} {ck_bank[10]} {ck_bank[11]} {ck_bank[12]} {ck_bank[13]} {ck_bank[14]} {ck_bank[15]} {ck_bank[16]} {ck_bank[17]} {ck_bank[18]} {ck_bank[19]} {ck_bank[20]} {ck_bank[21]} {ck_bank[22]} {ck_bank[23]} {ck_bank[24]} {ck_bank[25]} {ck_bank[26]} {ck_bank[27]} {ck_bank[28]} {ck_bank[29]} {ck_bank[30]} {ck_bank[31]} {ck_bank[32]} {ck_bank[33]} {ck_bank[34]} {ck_bank[35]} {ck_bank[36]} {ck_bank[37]} {ck_bank[38]} {ck_bank[39]} {ck_bank[40]} {ck_bank[41]} {ck_bank[42]} {ck_bank[43]} {ck_bank[44]} {ck_bank[45]} {ck_bank[46]} {ck_bank[47]} {ck_bank[48]} {ck_bank[49]} {ck_bank[50]} {ck_bank[51]} {ck_bank[52]} {ck_bank[53]} {ck_bank[54]} {ck_bank[55]} {ck_bank[56]} {ck_bank[57]} {ck_reset[0]} {ck_reset[1]} {ck_reset[2]} {ck_reset[3]} {ck_reset[4]} {ck_reset[5]} {ck_reset[6]} {ck_reset[7]} {ck_reset[8]} {ck_reset[9]} {ck_reset[10]} {ck_child[0]} {ck_child[1]} {ck_child[2]} {ck_child[3]} {ck_child[4]} {ck_child[5]} {ck_child[6]} {ck_child[7]} {ck_child[8]} {ck_child[9]} {ck_child[10]} {ck_child[11]} {ck_child[12]} {ck_child[13]}}

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
# Match ck_insertion.py's exported insertion.json boundary population: input
# timing endpoints plus output timing launch registers, intersected with this root.
proc ot_ce_boundary_pins {pins} {
  set regs {}; set boundary {}
  foreach pin $pins { dict set regs [regsub {/[^/]+$} [get_full_name $pin] {}] $pin }
  set inputs [all_inputs -no_clocks]
  if {[llength $inputs]} {
    foreach path [find_timing_paths -path_delay max -from $inputs -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {
      set name [regsub {/[^/]+$} [get_full_name [get_property $path endpoint]] {}]
      if {[dict exists $regs $name]} { dict set boundary $name [dict get $regs $name] }
    }
  }
  if {[llength [all_outputs]]} {
    foreach path [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {
      set name [regsub {/[^/]+$} [get_full_name [get_property $path startpoint]] {}]
      if {[dict exists $regs $name]} { dict set boundary $name [dict get $regs $name] }
    }
  }
  return [dict values $boundary]
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
      if {$name ni $::ot_ce_ports || $name in $::ot_ce_cts_roots || [dict exists $seen $name]} { error "OT_ENTRIES: duplicate or undeclared source $name" }
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
  # Each glue root owns a real CTS tree. Measure every propagated standard-cell
  # clock sink in the current scene; never substitute a declared/common phase.
  foreach name $::ot_ce_cts_roots {
    set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
    set pins [all_registers -clock [get_full_name $clock] -clock_pins]
    if {![llength $pins]} { error "OT_HYBRID: glue root $name has no actual sequential clock sinks" }
    set arrivals {}; set measured {}; set total 0.0
    foreach pin $pins {
      set cell [get_cells -of_objects $pin]
      set master [get_property $cell ref_name]
      if {[dict exists $::ot_ce_counts $master]} { error "OT_HYBRID: CTS root $name reaches a hard child" }
      set arrival [ot_ce_clock_wire $pin $clock]
      lappend arrivals $arrival
      dict set measured [get_full_name $pin] $arrival
      set total [expr {$total + $arrival}]
    }
    set arrivals [lsort -real $arrivals]
    set lo [lindex $arrivals 0]; set hi [lindex $arrivals end]
    set tree_mean [expr {$total / [llength $arrivals]}]
    set mean $tree_mean
    if {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire && $mean <= 0} {
      error "OT_HYBRID: glue root $name lacks a positive actual propagated CTS insertion"
    }
    if {[llength $arrivals] > 15000 && ($tree_mean > 300 || $hi-$lo > 80)} {
      error "OT_HYBRID: glue root $name exceeds measured large-root insertion/spread limits"
    }
    set boundary [ot_ce_boundary_pins $pins]
    set scope boundary
    if {![llength $boundary]} { set boundary $pins; set scope all_internal_only }
    set arrivals {}; set total 0.0
    foreach pin $boundary {
      set arrival [dict get $measured [get_full_name $pin]]
      lappend arrivals $arrival; set total [expr {$total + $arrival}]
    }
    set arrivals [lsort -real $arrivals]
    set lo [lindex $arrivals 0]; set hi [lindex $arrivals end]
    set mean [expr {$total / [llength $arrivals]}]
    if {[llength $pins] > 15000 && $mean > 300} {
      error "OT_HYBRID: glue root $name exceeds boundary insertion limit"
    }
    set domain [dict get $::ot_ce_source_domains $name]
    lappend rows [list [get_ports $name] [lindex $pins 0] 0 $lo $mean $hi $clock $mean $domain]
    dict set seen $name 1
    puts "OT_HYBRID CTS_MEASURE $corner $name sinks=[llength $pins] reference_scope=$scope boundary_sinks=[llength $boundary] min=$lo mean=$mean max=$hi all_mean=$tree_mean"
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
