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
  return [ot_cf_wire_transition $pin $clock [ot_cf_active $pin] $scene]
}
# Also supports clock-buffer outputs, which have no sequential active-edge arc.
proc ot_cf_wire_transition {pin clock transition {scene {}}} {
  if {$transition ni {rise fall}} {error "OT_CLOCK_FAMILY: invalid transition $transition"}
  if {$scene eq ""} {set scene [get_property [sta::cmd_scene] name]}
  set cn [get_full_name $clock]; set waveform {}
  foreach time [$clock waveform] {lappend waveform [sta::time_sta_ui $time]}
  if {[llength $waveform] != 2} {error "OT_CLOCK_FAMILY: invalid waveform $cn"}
  foreach time $waveform {if {![string is double -strict $time] || [regexp -nocase {inf|nan} $time]} {error "OT_CLOCK_FAMILY: nonfinite waveform $cn"}}
  set marker [expr {$transition eq "rise" ? "^max" : "vmax"}]
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

# Canonical boundary register membership for signoff, pre-route gate and pad.
# Async reset/set endpoints do not make every downstream control flop a pin reg.
proc ot_cf_pinregs {} {
  set regs {}; set data {}; set async {}; set boundary {}
  foreach pin [all_registers -clock_pins] {
    dict set regs [regsub {/[^/]+$} [get_full_name $pin] {}] $pin
  }
  foreach pin [all_registers -async_pins] { dict set async [get_full_name $pin] 1 }
  foreach pin [all_registers -data_pins] {
    set name [get_full_name $pin]
    if {![dict exists $async $name]} { dict set data $name 1 }
  }
  set inputs [all_inputs -no_clocks]
  if {[llength $inputs]} {
    foreach pin [get_fanout -from $inputs -flat -endpoints_only -trace_arcs all] {
      set name [get_full_name $pin]
      if {![dict exists $data $name]} continue
      set inst [regsub {/[^/]+$} $name {}]
      if {[dict exists $regs $inst]} { dict set boundary $inst [dict get $regs $inst] }
    }
  }
  if {[llength [all_outputs]]} {
    foreach pin [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
      set inst [regsub {/[^/]+$} [get_full_name $pin] {}]
      if {[dict exists $regs $inst]} { dict set boundary $inst [dict get $regs $inst] }
    }
  }
  return $boundary
}

# Leaf groups are actual ODB clock nets, never planned tap/bundle centroids.
proc ot_cf_pinreg_groups {boundary} {
  set groups {}
  dict for {inst pin} $boundary {
    set term [sta::sta_to_db_pin $pin]
    if {$term eq "" || $term eq "NULL" || [$term getNet] eq "NULL"} {
      error "OT_CLOCK_FAMILY: pin-register clock has no physical net: $inst"
    }
    dict lappend groups [[$term getNet] getName] [list $term $pin]
  }
  return $groups
}

# Stats map: group -> {mean count ...}. Pure guard also supports Tcl fixtures.
proc ot_cf_pinreg_limits {stats bound tol {balance 20.0}} {
  set means {}; set reasons {}
  dict for {group values} $stats {
    set mean [lindex $values 0]
    if {![string is double -strict $mean] || [regexp -nocase {inf|nan} $mean]} {
      lappend reasons "nonfinite group $group"; continue
    }
    lappend means $mean
  }
  if {![llength $means] || [llength $means] != [dict size $stats]} {
    return [dict create verdict FAIL reasons [concat $reasons {missing_pinreg_group_measurement}] min -1 max -1 spread -1]
  }
  set means [lsort -real $means]; set lo [lindex $means 0]; set hi [lindex $means end]
  set spread [expr {$hi-$lo}]
  if {$spread > $balance+1e-6} { lappend reasons "pinreg group spread $spread exceeds $balance ps" }
  if {$hi > $bound+$tol+1e-6} { lappend reasons "pinreg group maximum $hi exceeds bound+tol [expr {$bound+$tol}] ps" }
  return [dict create verdict [expr {[llength $reasons] ? "FAIL" : "PASS"}] reasons $reasons min $lo max $hi spread $spread]
}

proc ot_cf_pinreg_measure {clock} {
  set boundary [ot_cf_pinregs]
  set groups {}; set arrivals {}
  dict for {net entries} [ot_cf_pinreg_groups $boundary] {
    set values {}
    foreach entry $entries {
      set pin [lindex $entry 1]
      set clocks [get_property $pin clocks]
      if {[llength $clocks] != 1} { error "OT_CLOCK_FAMILY: ambiguous pin-register clock [get_full_name $pin]" }
      set value [ot_cf_wire $pin [lindex $clocks 0]]
      if {![string is double -strict $value] || [regexp -nocase {inf|nan} $value]} {
        error "OT_CLOCK_FAMILY: missing finite pin-register arrival on $net"
      }
      lappend values $value; lappend arrivals $value
    }
    if {[llength $values] != [llength $entries]} { error "OT_CLOCK_FAMILY: incomplete pin-register group $net" }
    set sorted [lsort -real $values]
    dict set groups $net [list [expr {[tcl::mathop::+ {*}$values]/[llength $values]}] [llength $values] $entries [lindex $sorted 0] [lindex $sorted end]]
  }
  set n [llength $arrivals]
  if {!$n} { error "OT_CLOCK_FAMILY: no measured boundary pin registers" }
  set sorted [lsort -real $arrivals]
  return [dict create n $n mean [expr {[tcl::mathop::+ {*}$arrivals]/$n}] min [lindex $sorted 0] max [lindex $sorted end] groups $groups]
}

# FF-only callers use this before/after boundary clock padding. It reports actual
# negative register-to-output-register hold endpoints, with no clock/SDC mutation.
proc ot_cf_output_hold_census {} {
  set outputs {}; set data {}; set async {}; set starts {}
  if {![llength [all_outputs]]} { return [dict create status NO_TARGETS n 0 worst_ps 0] }
  foreach pin [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
    dict set outputs [regsub {/[^/]+$} [get_full_name $pin] {}] 1
  }
  foreach pin [all_registers -async_pins] { dict set async [get_full_name $pin] 1 }
  foreach pin [all_registers -data_pins] {
    set name [get_full_name $pin]; set inst [regsub {/[^/]+$} $name {}]
    if {[dict exists $outputs $inst] && ![dict exists $async $name]} { lappend data $pin }
  }
  foreach pin [all_registers -output_pins] {
    set inst [regsub {/[^/]+$} [get_full_name $pin] {}]
    if {![dict exists $outputs $inst]} { lappend starts $pin }
  }
  if {![llength $starts] || ![llength $data]} { return [dict create status NO_TARGETS n 0 worst_ps 0] }
  set paths [find_timing_paths -from $starts -to $data -path_delay min -group_path_count 1000000 -endpoint_path_count 1 -slack_max 0]
  set endpoints {}; set worst 0.0
  foreach path $paths {
    set slack [get_property $path slack]
    if {![string is double -strict $slack] || [regexp -nocase {inf|nan} $slack]} { error "OT_CLOCK_FAMILY: output hold census unavailable" }
    if {$slack < 0} {
      dict set endpoints [get_full_name [get_property $path endpoint]] 1
      set worst [expr {min($worst,$slack)}]
    }
  }
  return [dict create status MEASURED n [dict size $endpoints] worst_ps $worst]
}
