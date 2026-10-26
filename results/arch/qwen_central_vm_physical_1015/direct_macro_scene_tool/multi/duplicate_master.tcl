read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef {/probe/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.lef}
read_liberty {/probe/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1_tt.lib}
read_liberty {/probe/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1_ff.lib}
read_verilog {/probe/results_final/probe.v}
link_design probe
read_sdc -mode ss {/probe/results_final/clock.sdc}
read_sdc -mode ff {/probe/results_final/clock.sdc}
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
define_scene TC -mode ss -liberty ot_sram_1r1w_32x546_m1_tt
define_scene BC -mode ff -liberty {ot_sram_1r1w_32x546_m1_tt ot_sram_1r1w_32x546_m1_ff}
set_mode ff
set_scene BC
set ::ot_ioref_scene BC
set actual [get_full_name [lindex [get_lib_cells -of_objects [get_cells u_0]] 0]]
if {$actual ne "ot_sram_1r1w_32x546_m1_tt/ot_sram_1r1w_32x546_m1"} {error "fixture did not reproduce first-linked TT master"}
set expected_corner ff
foreach entry $::ot_ce_direct_entries {
 lassign $entry master pattern name pin libraries
 ot_ce_direct_actual_libcell [lindex [get_cells $pattern] 0] $master $libraries $expected_corner
}
puts SCENE_PROBE_PASS_duplicate_master
exit
