set ::ot_ce_require_wire 1
# OT_CLOCK_ENTRY_DOMAIN_API_VERSION 1
# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.
set ::ot_ce_leaf_roots 1
set ::ot_ce_related_data 1
set ::ot_ce_refs [dict create ]
set ::ot_ce_counts [dict create ]
set ::ot_ce_domains [dict create {core} {clock core_clk io_budget_ps 166.667 inputs {{rst} {f_collective} {f_lf} {f_sseq_st} {f_wfc_ft} {hc}} outputs {{t_collective} {hw}}} {serial} {clock ot_io_serial io_budget_ps 222.222 inputs {{rsv}} outputs {{t_sseq_pw} {t_pq_pw} {t_sseq_plen}}} {ingest_host} {clock ot_io_ingest_host io_budget_ps 166.667 inputs {} outputs {}} {ingest_core} {clock ot_io_ingest_core io_budget_ps 166.667 inputs {} outputs {}}]
set ::ot_ce_source_domains [dict create {ck} {core} {ckv} {serial} {ck_ingest[0]} {ingest_host} {ck_ingest[1]} {ingest_core}]
set ::ot_ce_explicit_domains 1
set ::ot_ce_cts_roots {{ck} {ckv} {ck_ingest[0]} {ck_ingest[1]}}
set ::ot_ce_ports {{ck} {ckv} {ck_ingest[0]} {ck_ingest[1]}}

# Constants are proved from actual OpenDB connectivity and the loaded Liberty
# output functions. Cell/port names, case analysis and timing-graph constant
# pruning are never proofs. A cell output is constant when every loaded corner
# gives its master the same Liberty function and that function is a literal, or a
# combinational expression whose every variable is an input pin of the same
# instance on a net with no input port and exactly one driver that is itself
# constant (TIEHI/TIELO prove themselves through their literal function; a
# synthesis buffer/inverter or any gate of constants follows). Registers never
# qualify; unknown or unparsable functions fail closed.
proc ot_ce_constant_net {net seen remaining} {
  if {$remaining <= 0 || $net in {"" NULL}} {return 0}
  foreach port [$net getBTerms] {if {[$port getIoType] ne "OUTPUT"} {return 0}}
  set drivers {}
  foreach pin [$net getITerms] {if {[$pin isOutputSignal]} {lappend drivers $pin}}
  if {[llength $drivers] != 1} {return 0}
  return [ot_ce_constant_iterm [lindex $drivers 0] $seen $remaining]
}
proc ot_ce_constant_iterm {pin seen remaining} {
  if {$remaining <= 0 || ![$pin isOutputSignal]} {return 0}
  set inst [$pin getInst];set name "[$inst getName]/[[$pin getMTerm] getName]"
  if {[dict exists $seen $name]} {return 0}
  if {[info exists ::ot_ce_const_memo] && [dict exists $::ot_ce_const_memo $name]} {return [dict get $::ot_ce_const_memo $name]}
  dict set seen $name 1
  set result [ot_ce_constant_iterm_eval $inst $pin $seen $remaining]
  dict set ::ot_ce_const_memo $name $result
  return $result
}
proc ot_ce_constant_iterm_eval {inst pin seen remaining} {
  if {[info exists ::ot_ce_register_cells] && [dict exists $::ot_ce_register_cells [$inst getName]]} {return 0}
  set master [[$inst getMaster] getName];set output [[$pin getMTerm] getName]
  set functions {};set matched 0
  foreach library [get_libs -quiet *] {
    set cell [$library find_liberty_cell $master]
    if {$cell in {"" NULL}} continue
    set lp [$cell find_liberty_port $output]
    if {$lp in {"" NULL} || [sta::liberty_port_direction $lp] ne "output"} {return 0}
    dict set functions [string map {" " "" "\t" "" "\n" ""} [$lp function]] 1
    incr matched
  }
  if {!$matched || [dict size $functions] != 1} {return 0}
  set function [lindex [dict keys $functions] 0]
  if {$function in {0 1}} {return 1}
  if {$function eq "" || ![regexp {^[A-Za-z0-9_!'*&+|^()]+$} $function]} {return 0}
  set inputs [lsort -unique [regexp -all -inline {[A-Za-z_][A-Za-z0-9_]*} $function]]
  if {![llength $inputs]} {return 0}
  foreach input $inputs {
    set in [$inst findITerm $input]
    if {$in in {"" NULL} || ![$in isInputSignal]} {return 0}
    if {![ot_ce_constant_net [$in getNet] $seen [expr {$remaining-1}]]} {return 0}
  }
  return 1
}
# Timing startpoint -> constant proof. An output-port startpoint is followed to
# its net driver; an input port is never constant.
proc ot_ce_constant_cone {start} {
  set block [ord::get_db_block]
  if {[sta::object_type $start] eq "Port" || ([sta::object_type $start] eq "Pin" && [$start is_top_level_port])} {
    set port [$block findBTerm [get_full_name $start]]
    if {$port in {"" NULL} || [$port getIoType] ne "OUTPUT"} {return 0}
    return [ot_ce_constant_net [$port getNet] {} 64]
  }
  if {[sta::object_type $start] ne "Pin"} {return 0}
  set inst [$block findInst [get_full_name [$start instance]]]
  if {$inst in {"" NULL}} {return 0}
  set pin [$inst findITerm [get_property $start lib_pin_name]]
  if {$pin in {"" NULL}} {return 0}
  return [ot_ce_constant_iterm $pin {} 64]
}
# A multi-root leaf contains independent synchronous datapaths. Domain declarations
# are checked against the real synthesized timing graph, not trusted as metadata.
proc ot_ce_leaf_ownership {inputs outputs} {
  set expected {}
  dict for {domain info} $::ot_ce_domains {lappend expected [dict get $info clock]}
  for {set i 0} {$i < [llength $::ot_ce_ports]} {incr i} {lappend expected ot_entry_$i}
  set actual {}
  foreach c [all_clocks] {lappend actual [get_full_name $c]}
  if {[lsort $actual] ne [lsort $expected]} {error "OT_MULTI_ROOT: undeclared clock alias or relationship"}
  set cells {}; set clocks {}; set crossing_pairs {}; set domain_roots {}
  foreach root $::ot_ce_ports {
    set domain [dict get $::ot_ce_source_domains $root]
    dict set domain_roots $domain $root
    set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $root]]
    foreach pin [all_registers -clock [get_full_name $clock] -clock_pins] {
      set cell [get_full_name [get_cells -of_objects $pin]]
      if {[dict exists $cells $cell]} { error "OT_MULTI_ROOT: duplicate clock ownership $cell" }
      dict set cells $cell $domain
    }
  }
  foreach pin [all_registers -clock_pins] {
    set cell [get_full_name [get_cells -of_objects $pin]]
    if {![dict exists $cells $cell]} { error "OT_MULTI_ROOT: unowned register $cell" }
  }
  set ::ot_ce_register_cells {}
  foreach r [all_registers -cells] {dict set ::ot_ce_register_cells [get_full_name $r] 1}
  set ::ot_ce_const_memo {}
  # OpenSTA's -data_pins population includes asynchronous clear/preset
  # controls. Classify these from the actual loaded Liberty sequential arcs,
  # never from port names or reset_ports. They retain recovery/removal timing;
  # only ordinary synchronous D/control paths require data-domain ownership.
  set async_pins {}
  foreach pin [all_registers -async_pins] {dict set async_pins [get_full_name $pin] 1}
  foreach pin [all_registers -data_pins] {
    if {[dict exists $async_pins [get_full_name $pin]]} continue
    set cell [get_full_name [get_cells -of_objects $pin]]
    set expected [dict get $cells $cell]
    foreach start [get_fanin -flat -startpoints_only -to $pin] {
      set ports [get_ports -quiet [get_full_name $start]]
      if {[llength $ports]} {
        set name [get_full_name $start]
        if {![dict exists $inputs $name] || [dict get $inputs $name] ne $expected} {
          error "OT_MULTI_ROOT: input $name has wrong domain for $cell"
        }
      } else {
        set source [get_full_name [get_cells -quiet -of_objects $start]]
        if {![dict exists $cells $source]} {
          if {[ot_ce_constant_cone $start]} {
            puts "OT_MULTI_ROOT LIBERTY_CONSTANT [get_full_name $start] -> [get_full_name $pin]"
            continue
          }
          error "OT_MULTI_ROOT: unowned data path $source -> $cell"
        }
        set source_domain [dict get $cells $source]
        if {$source_domain ne $expected} {
          if {!$::ot_ce_related_data} {error "OT_MULTI_ROOT: cross-domain data path $source -> $cell requires explicit related profile"}
          dict set crossing_pairs [list $source_domain $expected] 1
        }
      }
    }
  }
  dict for {name domain} $outputs {
    foreach start [get_fanin -flat -startpoints_only -to [get_ports $name]] {
      # A die-strap tie output (contract v1.2 tie_hi/tie_lo), possibly
      # synthesis-buffered, has no clock and no data domain to own; it must be
      # proved constant above. Registers and ports keep their domain checks.
      if {[sta::object_type $start] eq "Pin" && [$start is_top_level_port]} {
        if {[ot_ce_constant_cone $start]} {
          puts "OT_MULTI_ROOT LIBERTY_CONSTANT [get_full_name $start] -> $name"
          continue
        }
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain [get_full_name $start]"
      }
      set source [get_full_name [get_cells -quiet -of_objects $start]]
      if {![dict exists $cells $source] && [ot_ce_constant_cone $start]} {
        puts "OT_MULTI_ROOT LIBERTY_CONSTANT [get_full_name $start] -> $name"
        continue
      }
      if {![dict exists $cells $source] || [dict get $cells $source] ne $domain} {
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain $source"
      }
    }
  }
  dict for {pair unused} $crossing_pairs {
    lassign $pair source_domain target_domain
    set source_root [dict get $domain_roots $source_domain]
    set target_root [dict get $domain_roots $target_domain]
    set from [all_registers -clock ot_entry_[lsearch -exact $::ot_ce_ports $source_root] -clock_pins]
    set to {}
    foreach pin [all_registers -clock ot_entry_[lsearch -exact $::ot_ce_ports $target_root] -data_pins] {
      if {![dict exists $async_pins [get_full_name $pin]]} {lappend to $pin}
    }
    foreach kind {max min} {
      set paths [find_timing_paths -from $from -to $to -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
      if {![llength $paths] && [info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1" &&
          ![info exists ::ot_mm_active]} {
        # Multi-mode route/gate (tools/orfs_hold_mm.tcl): this SDC is being read into mode ss BEFORE any scene is
        # defined, so the unscened default scene has no clocks and no path can be found yet.  The crossing population
        # above is structural (actual fanin) and unchanged; the finite-path proof runs strictly in every single-scene
        # read (non-MM stages, corner_sta / sign-off), which carries the timing claim.
        puts "OT_MULTI_ROOT RELATED_PATH_DEFERRED $source_domain -> $target_domain $kind (multi-mode read before scene definition; strict at sign-off)"
        continue
      }
      if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
        error "OT_MULTI_ROOT: related crossing lacks actual finite $kind STA path $source_domain -> $target_domain"
      }
      puts "OT_MULTI_ROOT RELATED_PATH $source_domain -> $target_domain $kind slack=[get_property [lindex $paths 0] slack] (ordinary synchronous timing retained)"
    }
  }
  puts "OT_MULTI_ROOT OWNERSHIP PASS roots=[llength $::ot_ce_cts_roots] registers=[dict size $cells] inputs=[dict size $inputs] outputs=[dict size $outputs] async_control_pins=[dict size $async_pins]"
}

proc ot_ce_corner {} {
  if {[info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC"} { return ff }
  if {[info exists ::ot_ce_corner]} { return $::ot_ce_corner }
  # WC is a scene label, not an actual library corner: option-B overlays WC
  # with TT. Bind the reference to actual loaded child Liberty objects.
  set found {}; set clock_cells {}
  # Physical-only taps/endcaps have no Liberty association. The clock corner
  # belongs to actual sequential clock sinks, not every physical instance.
  foreach pin [all_registers -clock_pins] {
    set cell [get_cells -quiet -of_objects $pin]
    if {[llength $cell] != 1 || $cell eq "NULL"} {error "OT_MULTI_ROOT: clock sink lacks one actual sequential cell"}
    dict set clock_cells [get_full_name $cell] $cell
  }
  if {![dict size $clock_cells]} {error "OT_MULTI_ROOT: no actual sequential cells for corner inference"}
  foreach cell [dict values $clock_cells] {
    set master [get_property $cell ref_name]
    set libcells [get_lib_cells -quiet -of_objects $cell]
    if {![llength $libcells] || "NULL" in $libcells} { error "OT_MULTI_ROOT: actual sequential cell $master has no loaded Liberty association" }
    foreach lc $libcells {
      set full [get_full_name $lc]
      if {![regexp -nocase {_(tt|ff|ss)/|_(tt|ff|ss)_} $full -> corner alt]} { error "OT_ENTRIES: unknown actual Liberty corner $full" }
      if {$corner eq ""} {set corner $alt}
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
  foreach a [get_clocks ot_entry_*] {
    foreach b [get_clocks ot_entry_*] {
      set an [get_full_name $a]; set bn [get_full_name $b]
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
      set match [get_ports -quiet $pattern -filter "direction == input"]
      if {$::ot_ce_leaf_roots && ![llength $match]} {set match [get_ports -quiet [format {%s\[*\]} $pattern] -filter "direction == input"]}
      if {$::ot_ce_leaf_roots && ![llength $match]} {error "OT_MULTI_ROOT: unknown input $pattern"}
      foreach p $match {
        set n [get_full_name $p]
        if {$n in $::ot_ce_ports} continue
        if {[dict exists $covered_in $n]} { error "OT_ENTRIES: input $n has duplicate IO domains" }
        dict set covered_in $n $domain; lappend inputs $p
      }
    }
    foreach pattern [dict get $info outputs] {
      set match [get_ports -quiet $pattern -filter "direction == output"]
      if {$::ot_ce_leaf_roots && ![llength $match]} {set match [get_ports -quiet [format {%s\[*\]} $pattern] -filter "direction == output"]}
      if {$::ot_ce_leaf_roots && ![llength $match]} {error "OT_MULTI_ROOT: unknown output $pattern"}
      foreach p $match {
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
  if {$::ot_ce_leaf_roots} { ot_ce_leaf_ownership $covered_in $covered_out }
  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"
}
ot_ce_apply
