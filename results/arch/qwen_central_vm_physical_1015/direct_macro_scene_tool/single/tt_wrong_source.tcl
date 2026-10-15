read_lef {/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef}
read_lef {/probe/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.lef}
read_liberty {/probe/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1_tt.lib}
read_verilog {/probe/single_final/probe.v}
link_design probe
# OT_CLOCK_ENTRY_DOMAIN_API_VERSION 1
create_clock -name core_clk -period 833.333000000
create_clock -name ot_entry_0 -period 833.333000000 [get_ports {ca}]
create_clock -name ot_entry_1 -period 833.333000000 [get_ports {cb}]
read_spef {/probe/single_final/probe.spef}
set_propagated_clock [get_clocks ot_entry_*]
set_input_delay 0 -clock core_clk [get_ports en]
set_output_delay 0 -clock core_clk [get_ports q*]

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
set ::ot_ce_direct_entries {{{ot_sram_1r1w_32x546_m1} {u_0} {ca} {clk} {{tt} {ot_sram_1r1w_32x546_m1_tt} {ff} {ot_sram_1r1w_32x546_m1_ff} {ss} {ot_sram_1r1w_32x546_m1_ss}}} {{ot_sram_1r1w_32x546_m1} {u_1} {cb} {clk} {{tt} {ot_sram_1r1w_32x546_m1_tt} {ff} {ot_sram_1r1w_32x546_m1_ff} {ss} {ot_sram_1r1w_32x546_m1_ss}}}}

# get_lib_cells -of_objects returns the network's first-linked Liberty cell,
# even when the active delay scene uses another library. Audit the successful
# native scene definition instead. This trace observes arguments without
# changing the command, its result, the scene, or any timing arcs.
proc ot_ce_direct_scene_defined {command code result operation} {
  if {$code != 0} { return }
  if {[llength $command] != 7} { error "OT_DIRECT_MACRO: unknown native scene definition API" }
  lassign $command ignored scene mode libs_min libs_max spef_min spef_max
  if {[llength [get_scenes $scene]] != 1} { error "OT_DIRECT_MACRO: defined scene not present $scene" }
  dict set ::ot_ce_direct_scene_libraries $scene [list $libs_min $libs_max]
}
if {[llength $::ot_ce_direct_entries] && ![info exists ::ot_ce_direct_scene_trace_installed]} {
  set ::ot_ce_direct_scene_libraries {}
  if {![llength [info commands ::sta::define_scene_cmd]]} {
    error "OT_DIRECT_MACRO: native scene definition API unavailable"
  }
  trace add execution ::sta::define_scene_cmd leave ot_ce_direct_scene_defined
  set ::ot_ce_direct_scene_trace_installed 1
}
proc ot_ce_direct_actual_libcell {cell master libraries corner} {
  set expected "[dict get $libraries $corner]/$master"
  if {![sta::multi_scene]} {
    set actual {}
    foreach lib [get_lib_cells -quiet -of_objects $cell] { lappend actual [get_full_name $lib] }
    if {$actual ne [list $expected]} { error "OT_DIRECT_MACRO: actual corner mismatch: $actual expected $expected" }
    return $expected
  }
  # A requested hold scene must be explicit; never infer it from the desired
  # corner or from the presence of an expected library elsewhere in memory.
  if {[info exists ::ot_ioref_scene]} {
    set scene $::ot_ioref_scene
  } else {
    set scene [get_property [sta::cmd_scene] name]
  }
  if {[llength [get_scenes $scene]] != 1 || ![dict exists $::ot_ce_direct_scene_libraries $scene]} {
    error "OT_DIRECT_MACRO: unobserved actual scene definition $scene"
  }
  foreach bindings [dict get $::ot_ce_direct_scene_libraries $scene] {
    set actual {}; set files {}
    foreach binding $bindings {
      set matched {}
      foreach lib [get_libs -quiet *] {
        set name [get_property $lib name]; set filename [get_property $lib filename]
        if {$binding eq $name || $binding eq $filename} { lappend matched $lib }
      }
      if {[llength $matched] != 1} { error "OT_DIRECT_MACRO: stale/missing/ambiguous scene library $scene $binding" }
      set lib [lindex $matched 0]; set name [get_property $lib name]
      foreach lc [get_lib_cells -quiet "$name/$master"] {
        lappend actual [get_full_name $lc]
        lappend files [get_property $lib filename]
      }
    }
    if {$actual ne [list $expected]} {
      error "OT_DIRECT_MACRO: actual scene corner mismatch: $scene $actual expected $expected"
    }
    puts "OT_DIRECT_MACRO SCENE_LIBRARY $scene $actual files=$files"
  }
  return $expected
}
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
    set expected [ot_ce_direct_actual_libcell $cell $master $libraries $corner]
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
set ::ot_ce_ports {ca cb}
set ::ot_ce_cts_roots {}
set ::ot_ce_source_domains {ca core cb core}
set ::ot_ce_domains {core {clock core_clk}}
set ::ot_ce_require_wire 1
set e [lindex $::ot_ce_direct_entries 0]; lset e 2 cb; lset ::ot_ce_direct_entries 0 $e

sta::worst_slack_cmd max
set rows [ot_ce_direct_rows tt]
if {[llength $rows] != 2} {error "probe missing rows"}
set phi 0; set wires {}
foreach row $rows {
  lassign $row port pin wire lo mean hi clock ttmean domain
  if {$wire <= 0 || $mean != 0 || $lo != 0 || $hi != 0} {error "probe incorrect raw pin algebra"}
  lappend wires $wire; set phi [expr {max($phi,$wire)}]
}
if {abs([lindex $wires 0]-[lindex $wires 1]) < 1} {error "probe failed to measure unequal RC wires"}
set before {}
foreach row $rows {
  lassign $row port pin wire lo mean hi clock
  set paths [find_timing_paths -from $pin -to [all_outputs] -path_delay max -group_path_count 1]
  if {![llength $paths]} {error "probe missing real SRAM clock-to-Q path"}
  lappend before [get_property [lindex $paths 0] slack]
  set_clock_latency -source [expr {$phi-$wire}] $clock
}
sta::worst_slack_cmd max
set i 0
foreach row $rows {
  lassign $row port pin wire lo mean hi clock
  set actual [ot_ce_clock_wire $pin $clock]
  if {abs($actual-$phi)>0.02} {error "probe source balancing failed $actual != $phi"}
  set paths [find_timing_paths -from $pin -to [all_outputs] -path_delay max -group_path_count 1]
  set after [get_property [lindex $paths 0] slack]
  if {abs($after-[lindex $before $i]+($phi-$wire))>0.02} {error "probe modified internal SRAM arcs"}
  incr i
}
puts "RAW_MACRO_PROBE_PASS tt wires=$wires phi=$phi SRAM-clock-to-Q-arcs-retained"

exit
