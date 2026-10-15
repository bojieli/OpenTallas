set ::ot_ce_require_wire 1
# OT_CLOCK_ENTRY_DOMAIN_API_VERSION 1
# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.
set ::ot_ce_refs [dict create {qvm_su_bank_ctrl_native/clk} {tt {54.3 54.9 55.3} ff {40.6 41.1 41.4} ss {77.9 78.8 79.3}} {qvm_data256_native/clk} {tt {67.2 69.3 71.9} ff {52.5 54.7 57.2} ss {93.0 95.2 97.8}}]
set ::ot_ce_counts [dict create {qvm_su_bank_ctrl_native} 1 {qvm_data256_native} 4]
set ::ot_ce_domains [dict create {core} {clock core_clk io_budget_ps 166.667 inputs {{*}} outputs {{*}}}]
set ::ot_ce_source_domains [dict create {ck_ctrl} {core} {ck_in_lo} {core} {ck_in_hi} {core} {ck_mem_lo} {core} {ck_mem_hi} {core} {ck_cap_lo} {core} {ck_cap_hi} {core} {ck_out_lo} {core} {ck_out_hi} {core}]
set ::ot_ce_explicit_domains 0
set ::ot_ce_cts_roots {{ck_cap_lo} {ck_cap_hi}}
set ::ot_ce_ports {{ck_ctrl} {ck_in_lo} {ck_in_hi} {ck_mem_lo} {ck_mem_hi} {ck_cap_lo} {ck_cap_hi} {ck_out_lo} {ck_out_hi}}
set ::ot_ce_direct_masters {ot_sram_1r1w_1024x256_m2_r2c2}
set ::ot_ce_direct_entries {{{ot_sram_1r1w_1024x256_m2_r2c2} {u_lo} {ck_mem_lo} {clk} {{tt} {ot_sram_1r1w_1024x256_m2_r2c2_tt} {ff} {ot_sram_1r1w_1024x256_m2_r2c2_ff} {ss} {ot_sram_1r1w_1024x256_m2_r2c2_ss}}} {{ot_sram_1r1w_1024x256_m2_r2c2} {u_hi} {ck_mem_hi} {clk} {{tt} {ot_sram_1r1w_1024x256_m2_r2c2_tt} {ff} {ot_sram_1r1w_1024x256_m2_r2c2_ff} {ss} {ot_sram_1r1w_1024x256_m2_r2c2_ss}}}}

# Return existing CE row shape. Zero internal OFFSET means Liberty-pin reference;
# it is not a measured zero SRAM insertion and does not modify any macro arcs.
proc ot_ce_direct_rows {corner} {
  set rows {}; set cells_seen {}
  foreach entry $::ot_ce_direct_entries {
    lassign $entry master pattern name libpin libraries
    set cells [get_cells -quiet -hierarchical $pattern]
    if {[llength $cells] != 1} { error "OT_DIRECT_MACRO: instance ownership is not unique: $pattern" }
    set cell [lindex $cells 0]; set cellname [get_full_name $cell]
    if {[dict exists $cells_seen $cellname] || [get_property $cell ref_name] ne $master} {
      error "OT_DIRECT_MACRO: duplicate/wrong actual macro $cellname"
    }
    dict set cells_seen $cellname 1
    set libs [get_lib_cells -quiet -of_objects $cell]
    set actual {}
    foreach lib $libs { lappend actual [get_full_name $lib] }
    set expected "[dict get $libraries $corner]/$master"
    if {$expected ni $actual} { error "OT_DIRECT_MACRO: actual corner mismatch: $actual expected $expected" }
    set pins {}
    foreach p [get_pins -of_objects $cell] {
      if {[get_property $p lib_pin_name] eq $libpin} { lappend pins $p }
    }
    if {[llength $pins] != 1} { error "OT_DIRECT_MACRO: missing actual clock pin $cellname/$libpin" }
    set pin [lindex $pins 0]
    set net [get_nets -quiet -of_objects $pin]
    set sources [get_ports -quiet -of_objects $net]
    set sinks [get_pins -quiet -of_objects $net]
    if {[llength $sources] != 1 || [get_full_name [lindex $sources 0]] ne $name ||
        [llength $sinks] != 1 || [get_full_name [lindex $sinks 0]] ne [get_full_name $pin]} {
      error "OT_DIRECT_MACRO: actual exclusive direct source/pin ownership mismatch $name -> $cellname/$libpin"
    }
    set i [lsearch -exact $::ot_ce_ports $name]
    if {$i < 0 || $name in $::ot_ce_cts_roots} { error "OT_DIRECT_MACRO: undeclared/nonhard source $name" }
    set clock [get_clocks ot_entry_$i]
    if {[llength $clock] != 1} { error "OT_DIRECT_MACRO: missing source clock $name" }
    set wire [ot_ce_clock_wire $pin $clock]
    if {![ot_ce_finite $wire]} { error "OT_DIRECT_MACRO: nonfinite clock wire $name" }
    if {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire && $wire <= 0} {
      error "OT_DIRECT_MACRO: actual positive propagated source-to-SRAM wire required $name"
    }
    set domain [dict get $::ot_ce_source_domains $name]
    set vc [get_clocks [dict get $::ot_ce_domains $domain clock]]
    if {abs([get_property $vc period]-[get_property $clock period])>0.001} {
      error "OT_DIRECT_MACRO: domain/source period mismatch $name"
    }
    lappend rows [list [lindex $sources 0] $pin $wire 0 0 0 $clock 0 $domain]
    puts "OT_DIRECT_MACRO RAW_LIBERTY_PIN $corner $name -> [get_full_name $pin] wire=$wire library=$expected (internal arcs retained)"
  }
  return $rows
}

proc ot_ce_corner {} {
  if {[info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC"} { return ff }
  if {[info exists ::ot_ce_corner]} { return $::ot_ce_corner }
  # WC is a scene label, not an actual library corner: option-B overlays WC
  # with TT. Bind the reference to actual loaded child Liberty objects.
  set found {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master] && $master ni $::ot_ce_direct_masters} continue
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
  foreach row [ot_ce_direct_rows $corner] {
    set name [get_full_name [lindex $row 0]]
    if {[dict exists $seen $name]} {error "OT_DIRECT_MACRO: duplicate hard-source ownership $name"}
    dict set seen $name 1
    lappend rows $row
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
