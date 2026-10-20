# Native PG contract: optional protection hooks, read-only audit, final-write guard.
# Rebuild after cell insertion or any rule/region change. getInsts uses OpenDB's
# native instance regex; exact dbRegion identity is checked separately below.
# Pin patterns are deliberately
# restricted to exact literals: unsupported syntax REFUSES rather than guessing.
proc ot_pg_prepare {block} {
  set mapping [dict create]
  foreach rule [$block getGlobalConnects] {
    set pattern [$rule getPinPattern]
    if {![regexp {^\^?([A-Za-z_][A-Za-z0-9_]*)\$?$} $pattern -> pin]} {
      error "OT_PG_UNSUPPORTED_PIN_PATTERN $pattern"
    }
    set net [$rule getNet]
    if {$net eq "NULL" || [$net getSigType] ni {POWER GROUND}} {
      error "OT_PG_RULE_NET_ROLE $pattern"
    }
    set region [$rule getRegion]
    foreach inst [$rule getInsts] {
      if {$region ne "NULL" && [$inst getRegion] ne $region} continue
      set term [$inst findITerm $pin]
      if {$term eq "NULL"} continue
      set role [[$term getMTerm] getSigType]
      if {$role ni {POWER GROUND}} {
        error "OT_PG_RULE_SIGNAL_PIN [$inst getName]/$pin"
      }
      if {$role ne [$net getSigType]} {
        error "OT_PG_RULE_ROLE [$inst getName]/$pin"
      }
      set key [list [$inst getName] $pin]
      dict lappend mapping $key $net
    }
  }
  # All overlap, including differently named native voltage supplies, refuses.
  dict for {key nets} $mapping {
    set nets [lsort -unique $nets]
    if {[llength $nets] != 1} { error "OT_PG_AMBIGUOUS_DOMAIN $key" }
    dict set mapping $key [lindex $nets 0]
  }
  return $mapping
}
# Targeted insertion batches avoid expanding all instances for every tap/pad.
# Only the explicitly supported native all-instance rule is admitted here;
# arbitrary regex continues to use the independent whole-block native census.
proc ot_pg_prepare_targets {block instances} {
  set mapping [dict create]
  foreach inst $instances {
    if {[$inst getBlock] ne $block || [regexp {[\r\n]} [$inst getName]]} {error OT_PG_TARGET_INSTANCE_REFUSED}
    foreach row [ot_pg_master_census $inst] {
      lassign $row mt term why
      if {$why ne ""} {error "$why [$inst getName]/[$mt getName]"}
    }
  }
  foreach rule [$block getGlobalConnects] {
    if {[$rule getInstPattern] ne ".*"} {error "OT_PG_TARGET_UNSUPPORTED_INSTANCE_PATTERN [$rule getInstPattern]"}
    set pattern [$rule getPinPattern]
    if {![regexp {^\^?([A-Za-z_][A-Za-z0-9_]*)\$?$} $pattern -> pin]} {error "OT_PG_UNSUPPORTED_PIN_PATTERN $pattern"}
    set net [$rule getNet]
    if {$net eq "NULL" || [$net getSigType] ni {POWER GROUND}} {error "OT_PG_RULE_NET_ROLE $pattern"}
    set region [$rule getRegion]
    foreach inst $instances {
      if {$region ne "NULL" && [$inst getRegion] ne $region} continue
      set term [$inst findITerm $pin]
      if {$term eq "NULL"} continue
      set role [[$term getMTerm] getSigType]
      if {$role ni {POWER GROUND}} {error "OT_PG_RULE_SIGNAL_PIN [$inst getName]/$pin"}
      if {$role ne [$net getSigType]} {error "OT_PG_RULE_ROLE [$inst getName]/$pin"}
      dict lappend mapping [list [$inst getName] $pin] $net
    }
  }
  dict for {key nets} $mapping {
    set nets [lsort -unique $nets]
    if {[llength $nets] != 1} {error "OT_PG_AMBIGUOUS_DOMAIN $key"}
    dict set mapping $key [lindex $nets 0]
  }
  return $mapping
}
proc ot_pg_expected {mapping inst term} {
  set key [list [$inst getName] [[$term getMTerm] getName]]
  if {![dict exists $mapping $key]} {error "OT_PG_UNKNOWN_DOMAIN $key"}
  return [dict get $mapping $key]
}
# Census is driven by the MASTER, never by the possibly incomplete ITerm list.
proc ot_pg_master_census {inst} {
  set rows {}
  foreach mt [[$inst getMaster] getMTerms] {
    set role [$mt getSigType]
    if {$role ni {POWER GROUND}} continue
    set pin [$mt getName]
    set term [$inst findITerm $pin]
    set why ""
    if {$term eq "NULL"} {
      set why OT_PG_MISSING_ITERM
    } elseif {[$term getMTerm] ne $mt || [$term getSigType] ne $role} {
      set why OT_PG_ITERM_TYPE_MISMATCH
    }
    lappend rows [list $mt $term $why]
  }
  return $rows
}
# A whole source-owned insertion batch must preflight before any PG mutation.
# Existing protected-unbound cells refuse; no flags, rules or wrong nets change.
proc ot_pg_bind_batch_before_protect {block instances} {
  set targeted 1
  foreach rule [$block getGlobalConnects] {
    if {[$rule getInstPattern] ne ".*"} {set targeted 0; break}
  }
  if {$targeted} {set mapping [ot_pg_prepare_targets $block $instances]} else {set mapping [ot_pg_prepare $block]}
  foreach inst $instances {
    if {[$inst getBlock] ne $block} {error OT_PG_TARGET_INSTANCE_REFUSED}
    foreach row [ot_pg_master_census $inst] {
      lassign $row mt term why
      if {$why ne ""} {error "$why [$inst getName]/[$mt getName]"}
      set actual [$term getNet]
      set expected [ot_pg_expected $mapping $inst $term]
      if {$actual ne "NULL" && $actual ne $expected} {error "OT_PG_WRONG_DOMAIN [$inst getName]/[$mt getName]"}
      if {$actual eq "NULL" && [$inst isDoNotTouch]} {error "OT_PG_ORDER_PROTECTED_UNBOUND [$inst getName]"}
    }
  }
  set bound 0
  foreach inst $instances {incr bound [ot_pg_bind_before_protect $mapping $inst]}
  return $bound
}
proc ot_pg_bind_before_protect {mapping inst} {
  set pending {}
  # Preflight every terminal before changing any connection. No force or
  # temporary clearing of protection is permitted in this SOURCE prototype.
  foreach row [ot_pg_master_census $inst] {
    lassign $row mt term why
    if {$why ne ""} {error "$why [$inst getName]/[$mt getName]"}
    set expected [ot_pg_expected $mapping $inst $term]
    set actual [$term getNet]
    if {$actual ne "NULL" && $actual ne $expected} {
      error "OT_PG_WRONG_DOMAIN [$inst getName]/[[$term getMTerm] getName]"
    }
    if {$actual eq "NULL"} {lappend pending [list $term $expected]}
  }
  if {[llength $pending] && [$inst isDoNotTouch]} {
    error "OT_PG_ORDER_PROTECTED_UNBOUND [$inst getName]"
  }
  foreach pair $pending {lassign $pair term net; $term connect $net}
  if {[llength $pending]} {
    if {![info exists ::ot_pg_bindings_dirty]} {set ::ot_pg_bindings_dirty 0}
    incr ::ot_pg_bindings_dirty [llength $pending]
  }
  foreach row [ot_pg_master_census $inst] {
    lassign $row mt term why
    if {$why ne ""} {error "$why [$inst getName]/[$mt getName]"}
    if {[$term getNet] ne [ot_pg_expected $mapping $inst $term]} {
      error "OT_PG_BIND_VERIFY [$inst getName]"
    }
  }
  return [llength $pending]
}
# Run after final global_connect, independently BEFORE/alongside PSM. This
# asserts every native PG MTerm, without clock/physical-only/name exemptions.
proc ot_pg_collect_all_native {block mapping} {
  set checked 0; set failures {}; set counts [dict create POWER 0 GROUND 0]
  foreach inst [$block getInsts] {
    foreach row [ot_pg_master_census $inst] {
      lassign $row mt term census_why
      set role [$mt getSigType]
      incr checked; dict incr counts $role
      set actual "NULL"
      if {$census_why eq ""} {set actual [$term getNet]}
      set actual_name ""; set actual_role ""
      if {$actual ne "NULL"} {set actual_name [$actual getName]; set actual_role [$actual getSigType]}
      set why ""; set expected_name ""
      if {$census_why ne ""} {
        set why $census_why
      } elseif {[catch {ot_pg_expected $mapping $inst $term} expected]} {
        set why $expected
      } else {
        set expected_name [$expected getName]
        if {$actual ne $expected} {set why OT_PG_FINAL_BINDING}
      }
      if {$why ne ""} {
        lappend failures [dict create instance [$inst getName] master [[$inst getMaster] getName] pin [$mt getName] role $role actual_net $actual_name actual_role $actual_role expected_net $expected_name reason $why]
      }
    }
  }
  return [dict create checked $checked roles $counts failures $failures failure_count [llength $failures]]
}
proc ot_pg_assert_all_native {block mapping} {
  set report [ot_pg_collect_all_native $block $mapping]
  if {[dict get $report failure_count]} {
    error "OT_PG_FINAL_FAIL count=[dict get $report failure_count] checked=[dict get $report checked] first=[lindex [dict get $report failures] 0]"
  }
  puts "OT_PG_FINAL_PASS native_pg_terminals=[dict get $report checked]"
  return [dict get $report checked]
}


proc ot_pg_strict_enabled {} {
  return [expr {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"}]
}
# Call prepare once AFTER the final insertion/master/rule/region change in each
# batch; discard mapping after that protection loop. Never cache across batches.
# STANDARD mode (OT_PG_STRICT unset): bind PG at every protection site BEFORE
# setDoNotTouch, with the design's own global_connect rules. OpenROAD
# global_connect skips dont_touch instances (dbGlobalConnect.cpp:163), so cells
# protected before the final global_connect stayed unbound (S81 STA.PG). This
# runs exactly the connection the final global_connect would have made, earlier;
# it adds no strict-mode stage/RC/coverage refusals. No rules yet (pre-PDN) ->
# no-op. Strict mode keeps its own source-owned per-instance binder.
proc ot_pg_standard_bind {where} {
  if {[ot_pg_strict_enabled]} {return 0}
  set block [ord::get_db_block]
  if {$block eq "NULL" || $block eq ""} {return 0}
  set rules [llength [$block getGlobalConnects]]
  if {!$rules} {puts "OT_PG_STANDARD_BIND $where rules=0 skipped"; return 0}
  global_connect
  puts "OT_PG_STANDARD_BIND $where rules=$rules"
  return $rules
}
proc ot_pg_bind_instance_before_protect {mapping inst} {
  if {![ot_pg_strict_enabled]} {return 0}
  return [ot_pg_bind_before_protect $mapping $inst]
}
proc ot_pg_final_guard {} {
  if {![ot_pg_strict_enabled]} {return}
  # Final timing/extraction already ran. A late global_connect must not repair
  # any missing binding and invalidate that RC state. Refuse BEFORE touching it.
  set block [ord::get_db_block]
  set mapping [ot_pg_prepare $block]
  set report [ot_pg_collect_all_native $block $mapping]
  if {[dict get $report failure_count]} {
    error "OT_PG_FINAL_LATE_BINDING_REFUSED count=[dict get $report failure_count] first=[lindex [dict get $report failures] 0]"
  }
  if {[info exists ::ot_pg_bindings_dirty] && $::ot_pg_bindings_dirty > 0} {
    error "OT_PG_FINAL_RC_DIRTY_REFUSED changes=$::ot_pg_bindings_dirty"
  }
  global_connect
  return [ot_pg_assert_all_native $block [ot_pg_prepare $block]]
}
proc ot_pg_json_string {value} {
  return "\"[string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t \b \\b \f \\f] $value]\""
}
proc ot_pg_json_strings {values} {
  set items {}; foreach value $values {lappend items [ot_pg_json_string $value]}
  return "\[[join $items ,]\]"
}
proc ot_pg_json_object {row} {
  set items {}
  dict for {key value} $row {lappend items "[ot_pg_json_string $key]:[ot_pg_json_string $value]"}
  return "\{[join $items ,]\}"
}
# Audit never repairs, clears protection, or invokes global_connect. The caller
# binds the resulting receipt to exact ODB/source bytes. Exclusive create keeps
# failed and prior reports immutable.
proc ot_pg_audit_snapshot {block output_path} {
  return [ot_pg_write_snapshot $block [open $output_path {WRONLY CREAT EXCL}]]
}
proc ot_pg_write_snapshot {block fh} {
  try {
    set rules {}; set regions {}; set masters [dict create]
    foreach rule [$block getGlobalConnects] {
      set net [$rule getNet]; set region [$rule getRegion]
      set rn ""; if {$region ne "NULL"} {set rn [$region getName]}
      set nn ""; set role ""; if {$net ne "NULL"} {set nn [$net getName]; set role [$net getSigType]}
      lappend rules [ot_pg_json_object [dict create inst_pattern [$rule getInstPattern] pin_pattern [$rule getPinPattern] net $nn role $role region $rn]]
    }
    foreach region [$block getRegions] {
      set members {}; foreach inst [$region getRegionInsts] {lappend members [$inst getName]}
      set boxes {}; foreach box [$region getBoundaries] {
        lappend boxes "\[[$box xMin],[$box yMin],[$box xMax],[$box yMax]\]"
      }
      lappend regions "\{\"name\":[ot_pg_json_string [$region getName]],\"members\":[ot_pg_json_strings [lsort $members]],\"boundaries\":\[[join [lsort $boxes] ,]\]\}"
    }
    # Mapping errors are a failure receipt too, never an empty success census.
    set mapping_error ""
    if {[catch {ot_pg_prepare $block} mapping]} {set mapping_error $mapping; set mapping [dict create]}
    set report [ot_pg_collect_all_native $block $mapping]
    set failures {}; foreach row [dict get $report failures] {lappend failures [ot_pg_json_object $row]}
    foreach inst [$block getInsts] {
      if {[llength [ot_pg_master_census $inst]]} {dict set masters [[$inst getMaster] getName] 1}
    }
    set counts [dict get $report roles]
    set status [expr {$mapping_error eq "" && [dict get $report failure_count] == 0 ? "PASS" : "FAIL"}]
    puts $fh "\{\"schema\":\"native_pg_audit.v1\",\"status\":[ot_pg_json_string $status],\"block\":[ot_pg_json_string [$block getName]],\"instance_count\":[llength [$block getInsts]],\"pg_master_count\":[dict size $masters],\"checked\":[dict get $report checked],\"roles\":\{\"POWER\":[dict get $counts POWER],\"GROUND\":[dict get $counts GROUND]\},\"failure_count\":[dict get $report failure_count],\"failures\":\[[join $failures ,]\],\"mapping_error\":[ot_pg_json_string $mapping_error],\"domain_rules\":\[[join [lsort $rules] ,]\],\"regions\":\[[join [lsort $regions] ,]\]\}"
  } finally {close $fh}
  if {$mapping_error ne ""} {error "OT_PG_AUDIT_MAPPING $mapping_error"}
  return $report
}
proc ot_pg_install_final_write_guard {} {
  if {![ot_pg_strict_enabled] || [info commands ot_pg_original_write_db] ne ""} {return}
  if {[info commands write_db] eq ""} {error OT_PG_WRITE_DB_UNAVAILABLE}
  rename write_db ot_pg_original_write_db
  proc ::write_db {args} {
    foreach arg $args {
      if {[file tail $arg] eq "6_final.odb"} {ot_pg_final_guard; break}
    }
    return [ot_pg_original_write_db {*}$args]
  }
}

# Actual native rule APIs may connect immediately. Track terminal state deltas,
# rather than assuming that the explicit binder's own count captures all changes.
proc ot_pg_binding_state {block} {
  set state [dict create]
  foreach inst [$block getInsts] {
    foreach row [ot_pg_master_census $inst] {
      lassign $row mt term why
      set net_name NULL
      if {$why ne ""} {set net_name $why} elseif {[$term getNet] ne "NULL"} {set net_name [[$term getNet] getName]}
      dict set state [list [$inst getName] [[$inst getMaster] getName] [$mt getName]] $net_name
    }
  }
  return $state
}
proc ot_pg_note_binding_delta {before after} {
  set changed 0
  foreach key [lsort -unique [concat [dict keys $before] [dict keys $after]]] {
    if {![dict exists $before $key] || ![dict exists $after $key] || [dict get $before $key] ne [dict get $after $key]} {incr changed}
  }
  if {$changed} {
    if {![info exists ::ot_pg_bindings_dirty]} {set ::ot_pg_bindings_dirty 0}
    incr ::ot_pg_bindings_dirty $changed
  }
  return $changed
}

# The protection hook runs in CTS after ORFS estimated placement parasitics.
# Observe the actual API, not a caller-supplied stage/model declaration. These
# observers never substitute another RC model. Any database or SPEF reload
# invalidates placement admission, including a failed attempted reload.
proc ot_pg_install_rc_observers {{standard_cts 0}} {
  if {(![ot_pg_strict_enabled] && !$standard_cts) || [info commands ot_pg_native_estimate_parasitics] ne ""} {return}
  set ::ot_pg_rc_model unknown
  if {![info exists ::ot_pg_bindings_dirty]} {set ::ot_pg_bindings_dirty 0}
  set ::ot_pg_spef_seen 0
  rename estimate_parasitics ot_pg_native_estimate_parasitics
  proc ::estimate_parasitics {args} {
    set ::ot_pg_rc_model unknown
    set result [ot_pg_native_estimate_parasitics {*}$args]
    if {[lsearch -exact $args -placement] >= 0} {set ::ot_pg_rc_model placement}
    if {[lsearch -exact $args -global_routing] >= 0} {set ::ot_pg_rc_model routed}
    set ::ot_pg_bindings_dirty 0
    return $result
  }
  foreach command {add_global_connection global_connect} {
    if {[info commands $command] eq ""} continue
    rename $command ot_pg_native_$command
    proc ::$command {args} [format {
      set block [ord::get_db_block]
      set before [ot_pg_binding_state $block]
      try {return [ot_pg_native_%s {*}$args]} finally {
        ot_pg_note_binding_delta $before [ot_pg_binding_state $block]
      }
    } $command]
  }
  foreach command {read_spef read_db} {
    if {[info commands $command] eq ""} continue
    rename $command ot_pg_native_$command
    proc ::$command {args} [format {
      set ::ot_pg_rc_model %s
      set ::ot_pg_spef_seen 1
      set result [ot_pg_native_%s {*}$args]
      if {"%s" eq "read_db" && [ot_pg_nonpg_wire_count [ord::get_db_block]] == 0} {set ::ot_pg_spef_seen 0}
      set ::ot_pg_bindings_dirty 0
      return $result
    } $command $command $command]
  }
}
proc ot_pg_nonpg_wire_count {block} {
  set count 0
  foreach net [$block getNets] {
    if {[$net getSigType] ni {POWER GROUND} && [$net getWire] ne "NULL"} {incr count}
  }
  return $count
}
proc ot_pg_require_cts_source_context {} {
  if {[info exists ::ot_pg_spef_seen] && $::ot_pg_spef_seen} {error OT_PG_PARASITICS_SPEF_PROVENANCE_REFUSED}
  set wires [ot_pg_nonpg_wire_count [ord::get_db_block]]
  if {$wires > 0} {error "OT_PG_PARASITICS_ROUTED_DB_REFUSED wires=$wires"}
  if {[info commands grt::have_routes] ne "" && [grt::have_routes]} {error OT_PG_PARASITICS_GLOBAL_ROUTES_REFUSED}
  set context_ok 0
  if {[info exists ::env(SCRIPTS_DIR)]} {
    set expected [file normalize [file join $::env(SCRIPTS_DIR) cts.tcl]]
    # OpenSTA include_file executes top-level commands with uplevel; its native
    # info script retains the real source path even when info frame lacks file.
    if {[info script] ne "" && [file normalize [info script]] eq $expected} {set context_ok 1}
    for {set level 0} {$level <= [info frame]} {incr level} {
      if {[catch {info frame -$level} frame]} continue
      if {[dict exists $frame file] && [file normalize [dict get $frame file]] eq $expected} {set context_ok 1; break}
    }
  }
  if {!$context_ok} {error OT_PG_PARASITICS_STAGE_REFUSED}
}

proc ot_pg_require_cts_placement_context {} {
  ot_pg_require_cts_source_context
  if {![info exists ::ot_pg_rc_model] || $::ot_pg_rc_model ne "placement"} {
    error "OT_PG_PARASITICS_MODEL_REFUSED [expr {[info exists ::ot_pg_rc_model] ? $::ot_pg_rc_model : {unknown}}]"
  }
}
# Initial spine/tap estimates precede the standard CTS placement estimate.
# Native annotation coverage distinguishes a genuinely empty cache from SPEF
# loaded before these observers. An unknown nonempty model is never downgraded.
proc ot_pg_require_cts_placement_or_empty_context {} {
  ot_pg_require_cts_source_context
  set model [expr {[info exists ::ot_pg_rc_model] ? $::ot_pg_rc_model : {unknown}}]
  if {$model ni {unknown read_db placement}} {error "OT_PG_PARASITICS_MODEL_REFUSED $model"}
  set pins [get_pins -hierarchical *]
  foreach port [get_ports *] {lappend pins [sta::get_port_pin $port]}
  set scenes [sta::scenes]
  if {![llength $pins] || ![llength $scenes]} {error OT_PG_PARASITICS_EMPTY_COVERAGE_REFUSED}
  foreach scene $scenes {
    foreach pin $pins {
      if {[sta::parasitics_annotated $pin $scene]} {error OT_PG_PARASITICS_EXISTING_ANNOTATION_REFUSED}
    }
  }
  return $model
}

# Current pinned engine has no admitted native birth/analysis transaction guard.
# Wrapping command RETURN cannot cover internal CTS/resizer estimates. Strict
# mode therefore refuses these native inserters BEFORE they execute. This is
# deliberately not bypassed by an environment capability name or image label.
proc ot_pg_install_unsupported_birth_guards {} {
  if {![ot_pg_strict_enabled]} {return}
  foreach command {buffer_ports repair_clock_inverters clock_tree_synthesis repair_timing repair_design global_placement} {
    if {[info commands $command] eq "" || [info commands ot_pg_unsupported_$command] ne ""} continue
    rename $command ot_pg_unsupported_$command
    proc ::$command {args} [format {
      error "OT_PG_NATIVE_BIRTH_CAPABILITY_REQUIRED command=%s"
    } $command]
  }
}
