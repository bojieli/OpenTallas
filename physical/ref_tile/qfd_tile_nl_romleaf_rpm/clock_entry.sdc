set ::ot_ce_require_wire 1
# OT_CLOCK_ENTRY_DOMAIN_API_VERSION 1
# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.
set ::ot_ce_refs [dict create {ot_qwen_tile_romleaf/clk} {tt {184.1 206.9 228.0} ff {152.0 173.9 194.9} ss {237.6 261.9 282.2}} {ot_qwen_tile_lsl_fp1/clk} {tt {160.1 165.7 172.0} ff {128.7 133.9 140.2} ss {214.5 221.0 227.1}}]
set ::ot_ce_counts [dict create {ot_qwen_tile_romleaf} 10 {ot_qwen_tile_lsl_fp1} 8]
set ::ot_ce_domains [dict create {core} {clock core_clk io_budget_ps 166.667 inputs {{*}} outputs {{*}}}]
set ::ot_ce_source_domains [dict create {ck} {core} {ck_rs} {core} {ck_rn} {core} {ck_rsw} {core} {ck_rnw} {core} {ck_dw} {core} {ck_de} {core} {ck_tx0} {core} {ck_tx1} {core} {ck_tx2} {core} {ck_tx3} {core} {ck_tx4} {core} {ck_tx5} {core} {ck_tx6} {core} {ck_tx7} {core} {ck_rp0} {core} {ck_rp1} {core} {ck_rp2} {core} {ck_rp3} {core} {ck_rp4} {core} {ck_rp5} {core} {ck_rp6} {core} {ck_rp7} {core} {ck_rp8} {core} {ck_rp9} {core} {ck_fa2} {core} {ck_fa4} {core} {ck_lsl0} {core} {ck_lsl1} {core} {ck_lsl2} {core} {ck_lsl3} {core} {ck_lsl4} {core} {ck_lsl5} {core} {ck_lsl6} {core} {ck_lsl7} {core}]
set ::ot_ce_explicit_domains 0
set ::ot_ce_cts_roots {{ck} {ck_rn} {ck_rs} {ck_rsw} {ck_rnw} {ck_dw} {ck_de} {ck_tx0} {ck_tx1} {ck_tx2} {ck_tx3} {ck_tx4} {ck_tx5} {ck_tx6} {ck_tx7} {ck_fa2} {ck_fa4}}
set ::ot_ce_ports {{ck} {ck_rs} {ck_rn} {ck_rsw} {ck_rnw} {ck_dw} {ck_de} {ck_tx0} {ck_tx1} {ck_tx2} {ck_tx3} {ck_tx4} {ck_tx5} {ck_tx6} {ck_tx7} {ck_rp0} {ck_rp1} {ck_rp2} {ck_rp3} {ck_rp4} {ck_rp5} {ck_rp6} {ck_rp7} {ck_rp8} {ck_rp9} {ck_fa2} {ck_fa4} {ck_lsl0} {ck_lsl1} {ck_lsl2} {ck_lsl3} {ck_lsl4} {ck_lsl5} {ck_lsl6} {ck_lsl7}}
# Actual OpenSTA clock ancestry and physical propagated-clock measurements.
# OpenSTA's Clock wrapper has no master accessor. Its canonical SDC exporter
# resolves inferred masters; evaluate only its generated-clock declarations in
# an isolated safe interpreter, never replay constraints in the live session.
proc ot_cf_record {args} {
  set ni [lsearch -exact $args -name]; set mi [lsearch -exact $args -master_clock]
  set si [lsearch -exact $args -source]
  if {$ni < 0 || $mi < 0 || $si < 0} {error "OT_CLOCK_FAMILY: canonical generated clock lacks resolved name/master/source"}
  set name [lindex $args [expr {$ni+1}]]
  set master [lindex $args [expr {$mi+1}]]; set source [lindex $args [expr {$si+1}]]
  if {[llength $master] != 1 || [llength $source] != 1 || [dict exists $::ot_cf_master $name]} {
    error "OT_CLOCK_FAMILY: ambiguous generated clock $name"
  }
  set parent [get_full_name $master]
  if {[sta::object_type $source] eq "Port"} {set source [sta::get_port_pin $source]}
  set owners {}; foreach c [get_property $source clocks] {lappend owners [get_full_name $c]}
  if {[lsort -unique $owners] ne [list $parent]} {
    error "OT_CLOCK_FAMILY: generated source of $name has owners $owners, expected $parent"
  }
  dict set ::ot_cf_master $name $parent
}
proc ot_cf_refresh {} {
  set ::ot_cf_master {}; set ::ot_cf_active_cache {}; set generated {}
  foreach c [all_clocks] {if {[$c is_generated]} {lappend generated [get_full_name $c]}}
  if {![llength $generated]} {return}
  sta::update_generated_clks
  # Iterating paths alone does not initialize generated source insertion.
  # A native timing search fills the complete root-to-bank physical arrivals.
  find_timing_paths -group_path_count 1
  set fd [file tempfile path ot-clock-family-]; close $fd
  set ip [interp create -safe]
  try {
    write_sdc $path
    foreach cmd {get_ports get_pins get_clocks} {interp alias $ip $cmd {} $cmd}
    interp alias $ip create_generated_clock {} ot_cf_record
    set fd [open $path r]; set text [read $fd]; close $fd
    set command {}
    foreach line [split $text \n] {
      append command $line \n
      if {![info complete $command]} continue
      if {[regexp {^\s*create_generated_clock\s} $command]} {interp eval $ip $command}
      set command {}
    }
    if {[string trim $command] ne ""} {error "OT_CLOCK_FAMILY: incomplete canonical SDC"}
    if {[lsort [dict keys $::ot_cf_master]] ne [lsort $generated]} {error "OT_CLOCK_FAMILY: incomplete generated-clock ancestry"}
    foreach c $generated {ot_cf_root $c}
  } finally {interp delete $ip; file delete -force $path}
}
proc ot_cf_root {name} {
  set seen {}
  while {[dict exists $::ot_cf_master $name]} {
    if {$name in $seen} {error "OT_CLOCK_FAMILY: ancestry cycle $name"}
    lappend seen $name; set name [dict get $::ot_cf_master $name]
  }
  set c [get_clocks -quiet $name]
  if {[llength $c] != 1 || [$c is_generated]} {error "OT_CLOCK_FAMILY: unresolved root $name"}
  return $name
}
proc ot_cf_pins {root} {
  set name [get_full_name $root]
  if {[ot_cf_root $name] ne $name} {error "OT_CLOCK_FAMILY: requested root $name is generated"}
  # Ordinary roots retain the existing all_registers ownership query. In
  # pre-CTS ideal sessions get_property(pin, clocks) can be empty on check-only
  # macro entries; all_registers -clock still proves actual graph membership.
  if {![dict size $::ot_cf_master]} {
    set pins [all_registers -clock_pins -clock $root]; set owners {}
    foreach p $pins {dict set owners [get_full_name $p] $root}
    return [list $pins $owners]
  }
  set pins {}; set owners {}
  foreach c [all_clocks] {
    if {[ot_cf_root [get_full_name $c]] ne $name} continue
    foreach p [all_registers -clock_pins -clock $c] {
      set pn [get_full_name $p]
      set actual {}; foreach owner [get_property $p clocks] {lappend actual [get_full_name $owner]}
      if {[llength [lsort -unique $actual]] != 1} {
        error "OT_CLOCK_FAMILY: ambiguous clock sink $pn ($actual)"
      }
      if {[ot_cf_root [lindex $actual 0]] ne $name} {error "OT_CLOCK_FAMILY: foreign sink $pn"}
      if {[lindex $actual 0] ne [get_full_name $c]} continue
      if {[dict exists $owners $pn]} {error "OT_CLOCK_FAMILY: duplicate sink $pn"}
      dict set owners $pn $c; lappend pins $p
    }
  }
  return [list $pins $owners]
}
proc ot_cf_active {p} {
  set cell [get_cells -of_objects $p]
  set key [list [get_property $cell ref_name] [get_property $p lib_pin_name]]
  if {[dict exists $::ot_cf_active_cache $key]} {return [dict get $::ot_cf_active_cache $key]}
  sta::redirect_string_begin
  set failed [catch {report_edges -from $p} message]
  set report [sta::redirect_string_end]; set on 0; set edges {}
  if {$failed} {error "OT_CLOCK_FAMILY: active-edge query failed [get_full_name $p]: $message"}
  foreach line [split $report \n] {
    if {[regexp {^\S} $line]} {set on [regexp {(Clk|En) to Q} $line]; continue}
    if {$on && [regexp {^\s+([\^v])\s+->} $line -> edge] && $edge ni $edges} {lappend edges $edge}
  }
  if {![llength $edges] && [llength [info commands ord::get_db]]} {
    # Check-only hard entries (notably SRAM write clocks) have no clock-to-Q
    # arc. Only an actual physical BLOCK with unique loaded Liberty clock
    # timing-check edges is supported; missing soft-register arcs still fail.
    set master [[ord::get_db] findMaster [get_property $cell ref_name]]
    if {$master ne "NULL" && [$master isBlock]} {
      set on 0
      foreach line [split $report \n] {
        if {[regexp {^\S} $line]} {set on [regexp { (setup|hold|recovery|removal)$} $line]; continue}
        if {$on && [regexp {^\s+([\^v])\s+->} $line -> edge] && $edge ni $edges} {lappend edges $edge}
      }
    }
  }
  if {[llength $edges] != 1} {error "OT_CLOCK_FAMILY: missing unique active clock edge [get_full_name $p] ($edges)"}
  set active [expr {[lindex $edges 0] eq "^" ? "rise" : "fall"}]
  dict set ::ot_cf_active_cache $key $active
  return $active
}
proc ot_cf_wire {pin clock {scene {}}} {
  if {$scene eq ""} {set scene [get_property [sta::cmd_scene] name]}
  set cn [get_full_name $clock]; set waveform {}
  foreach time [$clock waveform] {lappend waveform [sta::time_sta_ui $time]}
  if {[llength $waveform] != 2} {error "OT_CLOCK_FAMILY: invalid waveform $cn"}
  foreach time $waveform {if {![string is double -strict $time] || [regexp -nocase {inf|nan} $time]} {error "OT_CLOCK_FAMILY: nonfinite waveform $cn"}}
  set transition [ot_cf_active $pin]; set marker [expr {$transition eq "rise" ? "^max" : "vmax"}]
  set values {}
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    set paths [$vertex path_iterator $transition max]
    while {[$paths has_next]} {
      set path [$paths next]; set tag [$path tag]; set edge [lindex $tag 4]
      if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne $marker || [lindex $tag 3] ne $cn || $edge ni {^ v} || [string first "(clock prop)" $tag] < 0} continue
      set arrival [sta::time_sta_ui [$path arrival]]
      if {![string is double -strict $arrival] || [regexp -nocase {inf|nan} $arrival]} {$paths finish; error "OT_CLOCK_FAMILY: nonfinite clock arrival [get_full_name $pin]"}
      lappend values [expr {$arrival-[lindex $waveform [expr {$edge eq "^" ? 0 : 1}]]}]
    }
    $paths finish
  }
  if {[llength $values] != 1} {error "OT_CLOCK_FAMILY: missing unique physical clock arrival [get_full_name $pin] clock=$cn scene=$scene"}
  return [lindex $values 0]
}

proc ot_ce_clock_wire {pin clock} {
  if {[info exists ::ot_cf_master] && [dict size $::ot_cf_master]} {
    set owners [get_property $pin clocks]
    if {[llength $owners] != 1 || [ot_cf_root [get_full_name $owners]] ne [ot_cf_root [get_full_name $clock]]} {
      error "OT_CLOCK_FAMILY: wrong/ambiguous source ownership [get_full_name $pin]"
    }
    return [ot_cf_wire $pin $owners]
  }
  return [ot_ce_legacy_clock_wire $pin $clock]
}

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
# path. Read propagated clock tags in the current scene and remove the
# source waveform edge time; falling-edge-only registers include that phase.
proc ot_ce_finite {value} {
  return [expr {[string is double -strict $value] && ![regexp -nocase {inf|nan} $value]}]
}
proc ot_ce_legacy_clock_wire {pin clock} {
  set scene [get_property [sta::cmd_scene] name]
  set clock_name [get_full_name $clock]
  set by_transition [dict create rise {} fall {}]
  set waveform {}
  foreach time [$clock waveform] {lappend waveform [sta::time_sta_ui $time]}
  if {[llength $waveform] != 2 || ![ot_ce_finite [lindex $waveform 0]] ||
      ![ot_ce_finite [lindex $waveform 1]]} {
    error "OT_ENTRIES: invalid source clock waveform $clock_name"
  }
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    foreach transition {rise fall} marker {^ v} {
      set paths [$vertex path_iterator $transition max]
      while {[$paths has_next]} {
        set path [$paths next]
        # Sink transition and source clock edge are distinct (inverting trees).
        # Exclude data, ideal, other-scene and other-clock paths as before.
        set tag [$path tag]
        set edge [lindex $tag 4]
        if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne "${marker}max" ||
            [lindex $tag 3] ne $clock_name || $edge ni {^ v} ||
            [string first "(clock prop)" $tag] < 0} continue
        set arrival [sta::time_sta_ui [$path arrival]]
        if {![ot_ce_finite $arrival]} {
          $paths finish
          error "OT_ENTRIES: nonfinite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
        }
        set phase [lindex $waveform [expr {$edge eq "^" ? 0 : 1}]]
        dict lappend by_transition $transition [expr {$arrival - $phase}]
      }
      $paths finish
    }
  }
  # Preserve the rising pin-transition reference. An inverted/negedge clock
  # may associate it with the falling source edge; remove that actual phase.
  # Fall-only pins remain measurable. Multiple same-transition tags fail.
  set values [dict get $by_transition rise]
  if {![llength $values]} {set values [dict get $by_transition fall]}
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
# Match the structural IO boundary population in ck_insertion.py and io_ref_routed.sdc.
proc ot_ce_boundary_cells {} {
  set regs {}
  foreach p [all_registers -clock_pins] {
    set n [get_full_name $p]
    dict set regs [regsub {/[^/]+$} $n {}] $n
  }

set bnd {}
set ot_ck_data {}
set ot_ck_async {}
foreach p [all_registers -async_pins] { dict set ot_ck_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] {
  set n [get_full_name $p]
  if {![dict exists $ot_ck_async $n]} { dict set ot_ck_data $n 1 }
}
set din [all_inputs -no_clocks]
if {[llength $din]} {
  foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $ot_ck_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
}
set dout [all_outputs]
if {[llength $dout]} {
  foreach p [get_fanin -to $dout -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
}

  return $bnd
}
# Owner 2026-10-17 0dq clock rule for one glue CTS root in the current scene: FAIL iff the pin-flop spread
# (pin_hi - pin_lo over the boundary registers, or every sink when none is at the boundary) exceeds 80 ps at
# TT or FF; SS is sensitivity only.  > 15k sinks and > 300 ps insertion only WARN.
proc ot_ce_clock_rule {corner name sinks all_mean pin_mean pin_lo pin_hi scope} {
  set spread [expr {$pin_hi - $pin_lo}]
  set warn {}
  if {$sinks > 15000} { lappend warn "sinks $sinks > 15000 (guidance)" }
  if {$all_mean > 300 || $pin_mean > 300} {
    lappend warn "insertion all_mean [format %.1f $all_mean] / pin_mean [format %.1f $pin_mean] ps > 300 (guidance)"
  }
  if {[string tolower $corner] in {tt ff} && $spread > 80} {
    set level FAIL
  } elseif {[llength $warn]} {
    set level WARN
  } else {
    set level PASS
  }
  puts "OT_HYBRID CLOCK_RULE $corner $name $level pin_spread=[format %.1f $spread] scope=$scope sinks=$sinks[expr {[llength $warn] ? " WARN: [join $warn {; }]" : ""}]"
  return $level
}

proc ot_ce_boundary_pins {pins boundary_cells} {
  set regs {}; set boundary {}
  foreach pin $pins {dict set regs [regsub {/[^/]+$} [get_full_name $pin] {}] $pin}
  dict for {name unused} $boundary_cells {
    if {[dict exists $regs $name]} {dict set boundary $name [dict get $regs $name]}
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
  # Before CTS, a standard-cell root is still one unbuffered high-fanout
  # net. Propagating that net invents multi-ns skew and clock-pin slew;
  # its delay is not the tree that CTS will build. Keep only these declared
  # CTS roots ideal during the explicit pre-CTS diagnostic. Raw macro and
  # hardened-child entries retain actual entry-wire propagation. Routed
  # require-wire checks always propagate and measure every physical root.
  if {[info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts &&
      (![info exists ::ot_ce_require_wire] || !$::ot_ce_require_wire)} {
    foreach name $::ot_ce_cts_roots {
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      unset_propagated_clock $clock
      puts "OT_ENTRIES PRE_CTS_IDEAL_CTS_ROOT $name"
    }
  }
  set sources {}; set names {}
  foreach c [get_clocks ot_entry_*] {
    foreach p [get_property $c sources] { lappend sources $p; lappend names [get_full_name $p] }
  }
  if {[lsort $names] ne [lsort $::ot_ce_ports]} { error "OT_ENTRIES: source clock coverage differs from spec" }
  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }
  ot_cf_refresh
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
  # Source latencies are zero for this whole measurement loop, and no STA
  # constraints/netlist change until rows are complete. Query the same bounded
  # boundary population once per apply/current corner, never across calls.
  set boundary_cells {}; set boundary_cells_ready 0
  # Each glue root owns a real CTS tree. Measure every propagated standard-cell
  # clock sink in the current scene; never substitute a declared/common phase.
  foreach name $::ot_ce_cts_roots {
    set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
    lassign [ot_cf_pins $clock] pins ot_ce_family_owners
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
    if {!$boundary_cells_ready} {
      set boundary_cells [ot_ce_boundary_cells]; set boundary_cells_ready 1
    }
    set boundary [ot_ce_boundary_pins $pins $boundary_cells]
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
    # Clock rule (owner 2026-10-17 0dq, textbook_lint.clock_rule_eval): FAIL only on the pin-flop (boundary
    # register; child-flop on a region-rooted parent) spread > 80 ps at TT or FF.  > 15k sinks on one root and
    # insertion > 300 ps are guidance (WARN): the neighbour boundary is matched by the source-latency
    # compensation below / a ring crossing and judged by native_pin_audit --relative-to.
    if {[ot_ce_clock_rule $corner $name [llength $pins] $tree_mean $mean $lo $hi $scope] eq "FAIL"} {
      error "OT_HYBRID: glue root $name pin-flop spread [format %.1f [expr {$hi-$lo}]] ps > 80 at $corner ($scope, [llength $boundary] of [llength $pins] sinks)"
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
  # H1 authoritative pair_check.HOLD_TREE =50ps hold margin+50ps die skew (hold 100, setup 150).
  # Each deep tile has its own earlier trunk tap. The authoritative TREE
  # pair budget uses150ps die skew when either reference exceeds300ps,
  # including deep-to-deep pairs (pair_check.SKEW_DEEP) (setup 210).
  # S-ELEM-PQ 2026-10-15: a register pair on ONE glue CTS root of this tile shares one die tap and one
  # propagated standard-cell tree whose real skew STA already sees, so it is timed like every single-root
  # tile (base uncertainty); the die-skew reserve applies to every pair of DIFFERENT entries and to hard-
  # child entries (dsfd_bf_front_static: the uniform rule put hold 100 / setup 210 on all 12,276 core-root
  # paths -> 15,826 hold endpoints, 119k buffers).
  set ot_ce_glue {}
  foreach name $::ot_ce_cts_roots { lappend ot_ce_glue [get_full_name [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]] }
  set ot_ce_high {}
  foreach c $highclocks { lappend ot_ce_high [get_full_name $c] }
  set ot_ce_family_clocks {}
  foreach c [all_clocks] {
    if {[ot_cf_root [get_full_name $c]] in [lmap x [get_clocks ot_entry_*] {get_full_name $x}]} {lappend ot_ce_family_clocks $c}
  }
  foreach a $ot_ce_family_clocks {
    foreach b $ot_ce_family_clocks {
      set an [ot_cf_root [get_full_name $a]]; set bn [ot_cf_root [get_full_name $b]]
      if {$an eq $bn && $an in $ot_ce_glue} { continue }
      set_clock_uncertainty -setup [expr {($an in $ot_ce_high || $bn in $ot_ce_high) ? 210 : 150}] -from $a -to $b
      set_clock_uncertainty -hold 100 -from $a -to $b
    }
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
    # Optional composition-derived output budget (domain "io_budget": {"out": f}, f >= 0.2): the outside share of the
    # cycle on this domain's outputs; larger = a TIGHTER launch (flop -> pin) inside the child, never a relaxation.
    set budget_out [expr {[dict exists $info io_budget_out_ps] ? [dict get $info io_budget_out_ps] : $budget}]
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
      set_output_delay [expr {$budget_out-$dlmax+$sk}] -max -clock $vc $outputs
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
            set_output_delay [expr {$budget_out-$dlmax+150}] -max -clock $vc $p
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
